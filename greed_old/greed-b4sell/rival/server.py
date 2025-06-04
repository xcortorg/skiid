import logging
from websocket_server import WebsocketServer
import orjson
import msgspec
from .lib.message import WsMessage
from .lib.payload import Payloads, MessagePayload

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


class Server:
    """
    Represents a WebSocket Server handling client connections and communication.
    Parameters:
        host (str): The server's hostname. Defaults to "127.0.0.1".
        port (int): The server's port. Defaults to 13254.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 13254):
        self.websocket = WebsocketServer(host=host, port=port)
        self.websocket.set_fn_new_client(self._on_client_connect)
        self.websocket.set_fn_message_received(self._on_message_received)
        self.websocket.set_fn_client_left(self._on_client_disconnect)

        self.active_clients = {}
        self.pending_verification = {}
        self.on_hold_connections = {}

    @property
    def client_count(self) -> int:
        """Returns the number of connected clients."""
        return len(self.active_clients)

    def _on_client_connect(self, client, _):
        logger.info(f"New client connected: {client['address']}")
        self.pending_verification[client["address"][1]] = client

    def _on_client_disconnect(self, client, _):
        logger.info(f"Client disconnected: {client['address']}")
        self._disconnect_client(client)

    def _on_message_received(self, client, _, message):
        try:
            decoded_message = msgspec.json.decode(message)
            ws_message = WsMessage(decoded_message)
            self._handle_message(client, ws_message)
        except Exception as e:
            logger.error(f"Error decoding message: {e}")
            self._send_error(
                client,
                MessagePayload(
                    type=Payloads.error,
                    data="Invalid message format.",
                    traceback=str(e),
                ),
            )

    def _handle_message(self, client, msg: WsMessage):
        payload = MessagePayload().from_message(msg)
        handlers = {
            Payloads.verification: self._handle_verification,
            Payloads.information: self._handle_information,
            Payloads.ping: self._handle_ping,
            Payloads.client_list: self._handle_client_list,
            Payloads.request: self._handle_request,
            Payloads.response: self._handle_response,
            Payloads.error: self._handle_response,
            Payloads.function_call: self._handle_response,
        }
        handler = handlers.get(msg.type, self._unhandled_message)
        handler(client, msg, payload)

    def _unhandled_message(self, client, msg: WsMessage, payload: MessagePayload):
        logger.warning(
            f"Unhandled message type from client {client['address']}: {msg.type}"
        )

    def _handle_verification(self, client, msg: WsMessage, payload: MessagePayload):
        if msg.id in self.active_clients:
            logger.info(f"Duplicate client detected: {msg.id}")
            payload.type = Payloads.error
            payload.data = "Already authorized."
            self.on_hold_connections[msg.id] = {
                "client": client,
                "id": client["address"][1],
            }
            self._send_error(client, payload)
        else:
            logger.info(f"Client verified: {msg.id}")
            self.active_clients[msg.id] = {"client": client, "id": client["address"][1]}
            del self.pending_verification[client["address"][1]]
            payload.type = Payloads.success
            payload.data = "Authorized."
            self._send_message(client, payload)

    def _handle_information(self, client, msg: WsMessage, payload: MessagePayload):
        logger.debug(f"Information message from {client['address']}")
        payload.type = Payloads.information
        if msg.route:
            for destination in msg.route:
                if destination in self.active_clients:
                    self._send_message(
                        self.active_clients[destination]["client"], payload
                    )
        else:
            for client_id, client_obj in self.active_clients.items():
                if client_id != payload.id:
                    self._send_message(client_obj["client"], payload)

    def _handle_ping(self, client, msg: WsMessage, payload: MessagePayload):
        logger.debug(f"Ping message from {client['address']}")
        payload.type = Payloads.ping
        payload.data = {
            "success": msg.destination in self.active_clients or msg.destination is None
        }
        self._send_message(client, payload)

    def _handle_client_list(self, client, payload: MessagePayload):
        logger.info(f"Client list request from {client['address']}")
        payload.type = Payloads.response
        payload.data = list(self.active_clients.keys())
        self._send_message(client, payload)

    def _handle_request(self, client, msg: WsMessage, payload: MessagePayload):
        if msg.destination not in self.active_clients:
            logger.warning(f"Invalid destination: {msg.destination}")
            payload.type = Payloads.error
            payload.data = "Destination not found."
            self._send_error(client, payload)
        else:
            payload.type = Payloads.request
            self._send_message(self.active_clients[msg.destination]["client"], payload)

    def _handle_response(self, client, msg: WsMessage, payload: MessagePayload):
        if msg.destination not in self.active_clients:
            logger.error(f"Response destination not found: {msg.destination}")
            payload.type = Payloads.error
            payload.data = "Destination not connected."
            self._send_error(client, payload)
        else:
            self._send_message(self.active_clients[msg.destination]["client"], payload)

    def _send_message(self, client, message: MessagePayload):
        try:
            self.websocket.send_message(client, msgspec.json.encode(message.to_dict()))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")

    def _send_error(self, client, payload: MessagePayload):
        payload.type = Payloads.error
        try:
            self.websocket.send_message(client, orjson.dumps(payload.to_dict()))
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

    def _disconnect_client(self, client):
        disconnected_id = None
        for cid, info in list(self.active_clients.items()):
            if info["id"] == client["address"][1]:
                disconnected_id = cid
                del self.active_clients[cid]
                break
        
        # Check if there are any on-hold connections with the same ID
        if disconnected_id and disconnected_id in self.on_hold_connections:
            logger.info(f"Activating on-hold connection for client: {disconnected_id}")
            on_hold_info = self.on_hold_connections.pop(disconnected_id)
            on_hold_client = on_hold_info["client"]
            
            # Add the on-hold client to active clients
            self.active_clients[disconnected_id] = {
                "client": on_hold_client,
                "id": on_hold_client["address"][1]
            }
            
            # Send success message to activate the client
            payload = MessagePayload(
                type=Payloads.success,
                data="Authorized.",
                id="server"
            )
            self._send_message(on_hold_client, payload)
            
        self.pending_verification.pop(client["address"][1], None)

    def start(self):
        logger.info(
            f"WebSocket Server starting on {self.websocket.host}:{self.websocket.port}"
        )
        self.websocket.run_forever()
