"""
rival- An IPC based on Websockets. Fast, Stable, and easy-to-use,
for inter-communication between your processes or discord.py bots.
"""

# pylint: disable=E0401,W0718,C0301
import asyncio
import logging
import traceback
import typing
import uuid
from types import FunctionType
from typing import (
    Any,
    Callable,
    Coroutine,
    TypeVar,
    Union,
)

import orjson
import websockets

from .lib.errors import (
    ClientNotReadyError,
    ClientRuntimeError,
    InvalidRouteType,
    UnauthorizedError,
    MissingUUIDError,
    UUIDNotFoundError,
)
from .lib.events import Events
from .lib.message import WsMessage
from .lib.payload import (
    Payloads,
    MessagePayload,
    rivalObject,
    responseObject,
    PayloadTypes as PayloadType,
)
import loguru

logger = loguru.logger
Coro = TypeVar("Coro", bound=Callable[..., Coroutine[Any, Any, Any]])


class Connection:
    def __init__(
        self,
        local_name: str,
        host: str = "localhost",
        port: int = 13254,
        reconnect: bool = True,
    ):
        self.uri: str = f"ws://{host}:{port}"
        self.local_name: str = local_name
        self.reconnect: bool = reconnect
        self.reconnect_threshold: int = 60
        self.max_data_size: float = 2  # MiB
        self.websocket = None
        self.__routes = {}
        self.__sub_routes = {}
        self.listeners = {}

        self._authorized: bool = False
        self._on_hold = False
        self.__events = Events(logger)
        self.event = self.__events.event

    @property
    def authorized(self) -> bool:
        return self._authorized

    @property
    def on_hold(self) -> bool:
        return self._on_hold

    @property
    def routes(self):
        return self.__routes

    async def send_message(self, data: Union[Any, WsMessage]):
        if not isinstance(data, WsMessage):
            data = data.__dict__
        logger.debug(data)
        await self.websocket.send(orjson.dumps(data).decode("utf-8"))

    def __send_message(self, data):
        asyncio.create_task(self.send_message(data))

    async def __verify_client(self):
        payload = MessagePayload(
            type=Payloads.verification, id=self.local_name, uuid=str(uuid.uuid4())
        )
        await self.send_message(payload)
        logger.info("Verification request sent")

    async def __connect(self) -> None:
        if self.websocket is None or self.websocket.closed:
            logger.info("Connecting to Websocket")
            self.websocket = await websockets.connect(
                self.uri,
                close_timeout=0,
                ping_interval=None,
                max_size=int(self.max_data_size * 1048576),
            )
            self._authorized = False
            self.__events.dispatch_event("rival_connect")
            logger.info("Connected to Websocket")

    async def __reconnect_client(self) -> bool:
        while True:
            try:
                await self.__connect()
                await self.__verify_client()
                return True
            except Exception as error:
                logger.debug(
                    "Failed to reconnect. Retrying in {}s.", self.reconnect_threshold
                )
                logger.error(
                    "While trying to reconnect there has been an error. {}", str(error)
                )
                await asyncio.sleep(self.reconnect_threshold)

    async def start(self) -> None:
        if self.websocket is None or self.websocket.closed:
            await self.__connect()
            await self.__verify_client()
            asyncio.create_task(self.__on_message())
        else:
            raise ConnectionError("Websocket is already connected!")

    def route(self, name: str = None):
        def route_decorator(_route_func):
            route_name = name or _route_func.__name__
            if route_name in self.__routes:
                raise ValueError("Route name is already registered!")

            if not asyncio.iscoroutinefunction(_route_func):
                raise InvalidRouteType("Route function must be a coro.")

            self.__routes[route_name] = _route_func
            return _route_func

        if isinstance(name, FunctionType):
            return route_decorator(name)
        else:
            return route_decorator

    async def add_route(self, callback: typing.Callable, name: str = None):
        route_name = name or callback.__name__
        if route_name in self.__routes:
            raise KeyError(
                f"Route name is already registered!\nRoutes: {self.__routes}"
            )
        if not asyncio.iscoroutinefunction(callback):
            raise InvalidRouteType("Route callback must be an asyncio coro.")

        self.__routes[route_name] = callback
        return callback

    def remove_route(self, name: str):
        if name in self.__routes:
            del self.__routes[name]
        else:
            raise KeyError(f"Route name {name} does not exist!")

    async def __purge_sub_routes(self, timeout, _uuid):
        await asyncio.sleep(timeout)
        del self.__sub_routes[_uuid]

    def __register_object_funcs(self, rival_object: rivalObject):
        self.__sub_routes[rival_object.uuid] = rival_object.functions
        asyncio.create_task(
            self.__purge_sub_routes(rival_object.object_expiry, rival_object.uuid)
        )

    async def ping(self, client=None, timeout: int = 60) -> bool:
        if self._on_hold or self.websocket is None or not self.websocket.open:
            raise ClientNotReadyError(
                "The client is currently not ready to send or accept requests."
            )
        if not self._authorized:
            raise UnauthorizedError("Client is not authorized!")
        logger.debug("Pinging IPC Server")

        _uuid = str(uuid.uuid4())
        payload = MessagePayload(
            type=Payloads.ping, id=self.local_name, destination=client, uuid=_uuid
        )
        await self.send_message(payload)
        resp = await self.__get_response(
            _uuid, asyncio.get_event_loop(), timeout=timeout
        )
        return resp.get("success", False)

    async def _call_function(
        self, destination, object_identifier, func_name, *args, **kwargs
    ) -> bool:
        if self._on_hold or self.websocket is None or not self.websocket.open:
            raise ClientNotReadyError(
                "The client is currently not ready to send or accept requests."
            )
        if not self._authorized:
            raise UnauthorizedError("Client is not authorized!")
        logger.debug("Calling a function IPC Server")

        _uuid = str(uuid.uuid4())
        payload = MessagePayload(
            type=Payloads.function_call,
            id=self.local_name,
            destination=destination,
            uuid=_uuid,
            data={
                "__uuid__": object_identifier,
                "__func__": func_name,
                "__args__": list(args),
                "__kwargs__": dict(kwargs),
            },
        )
        await self.send_message(payload)
        recv = await self.__get_response(_uuid, asyncio.get_event_loop(), timeout=30)
        return recv

    def __get_response(
        self, _uuid: str, loop: asyncio.AbstractEventLoop, timeout: int = 60
    ):
        future = loop.create_future()
        self.listeners[_uuid] = future
        return asyncio.wait_for(future, timeout)

    async def request(
        self, route: str, source: str, timeout: int = 60, **kwargs
    ) -> Any:
        if self.websocket is not None and self.websocket.open:
            if self._on_hold:
                raise ClientNotReadyError(
                    "The client is currently not ready to send or accept requests."
                )
            if not self._authorized:
                raise UnauthorizedError("Client is not authorized!")

            if not route or not source:
                raise ValueError("Missing required information for this request")

            logger.info("Requesting IPC Server for {}", route)

            _uuid = str(uuid.uuid4())
            payload = MessagePayload(
                type=Payloads.request,
                id=self.local_name,
                destination=source,
                route=route,
                data=kwargs,
                uuid=_uuid,
            )

            # Register the listener before sending the message
            future = asyncio.get_event_loop().create_future()
            self.listeners[_uuid] = future

            await self.send_message(payload)
            try:
                recv = await asyncio.wait_for(future, timeout=timeout)
                return recv
            except asyncio.TimeoutError:
                logger.warning(f"Request timed out for UUID {_uuid}")
                raise
            finally:
                # Only remove the listener if we got a response or timed out
                if _uuid in self.listeners:
                    self.listeners.pop(_uuid)

        else:
            await self.start()
            raise ClientNotReadyError(
                "The client has not been started or has disconnected"
            )

    async def get_clients(self, timeout: int = 60):
        if self.websocket is not None and self.websocket.open:
            if self._on_hold:
                raise ClientNotReadyError(
                    "The client is currently not ready to send or accept requests."
                )
            if not self._authorized:
                raise UnauthorizedError("Client is not authorized!")

            logger.info("Requesting IPC Server for {}", "get_clients")
            _uuid = str(uuid.uuid4())
            payload = MessagePayload(
                type=Payloads.client_list, id=self.local_name, uuid=_uuid
            )
            await self.send_message(payload)
            recv = await self.__get_response(
                _uuid, asyncio.get_event_loop(), timeout=timeout
            )
            return recv
        else:
            await self.start()
            raise ClientNotReadyError(
                "The client has not been started or has disconnected"
            )

    async def inform(self, data: Any, destinations: list):
        if self.websocket is not None and self.websocket.open:
            if self._on_hold:
                raise ClientNotReadyError(
                    "The client is currently not ready to send or accept requests."
                )
            if not self._authorized:
                raise UnauthorizedError("Client is not authorized!")

            logger.info("Informing IPC Server to redirect to routes {}", destinations)
            if not isinstance(destinations, list):
                destinations = [destinations]

            payload = MessagePayload(
                type=Payloads.information,
                id=self.local_name,
                route=destinations,
                data=data,
            )

            await self.send_message(payload)
        else:
            raise ClientNotReadyError(
                "The client has not been started or has disconnected"
            )

    async def wait_until_ready(self):
        await self.wait_for("rival_ready", None)

    async def wait_until_disconnected(self):
        await self.wait_for("rival_disconnect", None)

    def wait_for(
        self,
        event: str,
        timeout: Union[int, None] = None,
    ):
        future = asyncio.get_event_loop().create_future()

        _event = event.lower()
        listeners = self.__events.listeners.setdefault(_event, [])
        listeners.append(future)
        return asyncio.wait_for(future, timeout)

    async def __on_message(self):
        logger.info("Listening to messages")
        while True:
            try:
                message = WsMessage(orjson.loads(await self.websocket.recv()))
            except websockets.exceptions.ConnectionClosedError:
                self.__events.dispatch_event("rival_disconnect")
                if self.reconnect:
                    if not await self.__reconnect_client():
                        break
                else:
                    break

            if message.type.success and not self._authorized:
                logger.info("Authorized Successfully")
                self.__events.dispatch_event("rival_ready")
                self._authorized = True
                self._on_hold = False
            elif message.type.success and self._on_hold:
                logger.info("Connection reactivated after being on hold")
                self._on_hold = False
                self.__events.dispatch_event("rival_ready")
                
            elif message.type.ping:
                logger.debug("Received a ping from server")
                asyncio.create_task(self._dispatch(message))

            elif message.type.request:
                if message.route not in self.__routes:
                    logger.info("Failed to fulfill request, route not found")
                    payload = MessagePayload(
                        type=Payloads.error,
                        id=self.local_name,
                        data="Route not found",
                        traceback="Route not found",
                        destination=message.id,
                        uuid=message.uuid,
                    )
                    self.__send_message(payload)
                    return
                logger.info("Fulfilling request @ route: {}", message.route)
                asyncio.create_task(self._fulfill_request(message))
                self.__events.dispatch_event("rival_request")

            elif message.type.response:
                logger.info("Received a response from server @ uuid: {}", message.uuid)
                asyncio.create_task(self._dispatch(message))
                self.__events.dispatch_event("rival_response")

            elif message.type.error:
                if message.data == "Already authorized.":
                    self._on_hold = True
                    logger.warning(
                        "Another client is already connected. Requests will be enabled when the other is disconnected."
                    )
                else:
                    logger.debug("Failed to fulfill request: {}", message.data)
                    self.__events.dispatch_event("rival_error", message.data)

                if message.uuid is not None:
                    asyncio.create_task(self._dispatch(message))

            elif message.type.information:
                if message.data:
                    logger.debug(
                        "Received an information bit from client: {}", message.id
                    )
                    self.__events.dispatch_event(
                        "rival_information", message.data, message.id
                    )

            elif message.type.function_call:
                logger.debug("Received an object function call.")
                logger.debug(message.data)
                payload = MessagePayload(
                    type=Payloads.response,
                    id=self.local_name,
                    destination=message.id,
                    uuid=message.uuid,
                )
                try:
                    called_function = self.__sub_routes[message.data["__uuid__"]][
                        message.data["__func__"]
                    ]
                    asyncio.create_task(
                        self._fulfil_callback(
                            payload,
                            called_function,
                            *message.data["__args__"],
                            **message.data["__kwargs__"],
                        )
                    )
                except KeyError:
                    payload = MessagePayload(
                        type=Payloads.error,
                        id=self.local_name,
                        data="The called function has either expired or has never been registered",
                        traceback="The called function has either expired or has never been registered",
                        destination=message.id,
                        uuid=message.uuid,
                    )
                    self.__send_message(payload)

    def __parse_object(self, payload):
        payload.pseudo_object = True
        dummy_object = payload.data
        payload.data = dummy_object.serialize()
        self.__register_object_funcs(dummy_object)

    async def _fulfil_callback(self, payload, function, *args, **kwargs):
        try:
            payload.data = await function(*args, **kwargs)
            if not isinstance(
                payload.data, (int, float, str, bool, type(None), list, tuple, dict)
            ):
                payload.data = rivalObject(payload.data)

            if isinstance(payload.data, rivalObject):
                self.__parse_object(payload)

            self.__send_message(payload)
        except Exception as error:
            logger.exception("Failed to run the registered method")
            self.__events.dispatch_event("rival_error", error)
            payload.type = Payloads.error
            payload.data = str(error)
            payload.traceback = "".join(
                traceback.format_exception(TypeError, error, error.__traceback__)
            )

    async def _fulfill_request(self, message: WsMessage):
        route = message.route
        func = self.__routes[route]
        data = message.data
        payload = MessagePayload().from_message(message)
        payload.type = Payloads.response
        payload.id = self.local_name
        payload.destination = message.id  # Send back to original requester
        payload.uuid = message.uuid  # Keep the same UUID

        try:
            payload.data = await func(message.destination, **data)
            if isinstance(payload.data, rivalObject):
                self.__parse_object(payload)
        except Exception as error:
            logger.exception(error)
            self.__events.dispatch_event("rival_error", error)
            etype = type(error)
            trace = error.__traceback__
            lines = traceback.format_exception(etype, error, trace)
            traceback_text = "".join(lines)

            payload.type = Payloads.error
            payload.data = str(error)
            payload.traceback = traceback_text
        finally:
            try:
                await self.send_message(payload)
            except TypeError as error:
                logger.exception("Failed to convert data to json")
                self.__events.dispatch_event("rival_error", error)
                payload.type = Payloads.error
                payload.data = str(error)
                payload.traceback = "".join(
                    traceback.format_exception(TypeError, error, error.__traceback__)
                )
                self.__send_message(payload)

    async def _dispatch(self, msg: WsMessage):
        data = msg.data
        _uuid = msg.uuid
        if _uuid is None:
            raise MissingUUIDError("UUID is missing.")

        try:
            future: asyncio.Future = self.listeners[_uuid]
            if not msg.type.error:
                if msg.pseudo_object:
                    future.set_result(responseObject(self, msg.id, data))
                else:
                    future.set_result(data)
            else:
                future.set_exception(ClientRuntimeError(msg.data))
        except KeyError:
            # Log the issue but don't raise an error
            logger.warning(
                f"Received response for UUID {_uuid} but no listener found. Message type: {msg.type}"
            )
            logger.debug(f"Current listeners: {list(self.listeners.keys())}")
            return
