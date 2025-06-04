from aiohttp import (
    ClientSession as DefaultClientSession,
    ClientResponse,
    ClientRequest,
    BaseConnector,
)
from aiohttp import ClientTimeout
from bs4 import BeautifulSoup
from munch import DefaultMunch
from yarl import URL
from ssl import SSLContext

from aiohttp import ClientSession
from aiohttp.client_exceptions import (
    ClientConnectorError,
    ClientResponseError,
    ContentTypeError,
    ClientProxyConnectionError,
    ClientHttpProxyError,
)
from typing import (
    Any,
    Optional as optional,
    TypedDict,
    Type,
    Iterable,
    Dict,
    Union,
    List,
    Tuple,
    Set,
)
from typing_extensions import NotRequired as Optional
from loguru import logger
from asyncio import Lock, sleep, AbstractEventLoop, Semaphore
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class SessionResponse:
    response: Any
    headers: Dict[str, str]
    status: int


Exceptions = Union[
    Tuple[Union[Type, Exception]],
    Set[Union[Type, Exception]],
    List[Union[Type, Exception]],
]


class RequestOptions(TypedDict, total=False):
    response_type: Optional[str]
    json_model: Optional[Any]
    method: Optional[str]
    url: Optional[str]
    params: Optional[dict]
    data: Optional[dict]
    json: Optional[dict]
    headers: Optional[dict]
    cookies: Optional[dict]
    auth: Optional[ClientRequest]
    allow_redirects: Optional[bool]
    max_redirects: Optional[int]
    compress: Optional[bool]
    chunked: Optional[bool]
    expect100: Optional[bool]
    read_until_eof: Optional[bool]
    timeout: Optional[ClientTimeout]
    ssl: Optional[bool]
    proxy: Optional[str]
    proxy_auth: Optional[str]
    trace_request_ctx: Optional[dict]
    fingerprint: Optional[bytes]
    version: Optional[str]
    loop: Optional[AbstractEventLoop]
    ssl_context: Optional[SSLContext]
    client_timeout: Optional[ClientTimeout]
    client_session: Optional[ClientSession]
    read_bufsize: Optional[int]
    write_bufsize: Optional[int]
    continue100_timeout: Optional[float]
    skip_auto_headers: Optional[Iterable[str]]
    response_class: Optional[Type[ClientResponse]]
    connector: Optional[BaseConnector]
    local_addr: Optional[str]
    max_forwards: Optional[int]
    allow_proxy_headers: Optional[bool]
    expect100_timeout: Optional[float]
    raise_for_status: Optional[bool]
    request_class: Optional[Type[ClientRequest]]
    ssl_key: Optional[bytes]
    ssl_cert: Optional[bytes]
    ssl_ca: Optional[bytes]
    ssl_allow_renegotiation: Optional[bool]
    request: Optional[ClientRequest]


def catcher(
    exceptions: optional[Exceptions] = Exception, retries: int = 3, pause: int = 0
):
    def decorator(func):
        async def wrapper(*args: Any, **kwargs: Any):
            data = None
            attempt = 0
            while attempt < retries:
                try:
                    data = await func(*args, **kwargs)
                    break
                except exceptions as e:
                    attempt += 1
                    if attempt == retries:
                        raise
                    logger.debug(
                        f"Retrying {func.__name__} after exception: {type(e).__name__}. Attempt {attempt}/{retries}"
                    )
                    await sleep(pause)  # Adjust sleep time as needed
            return data

        return wrapper

    return decorator


class SessionPool:
    def __init__(self: "SessionPool"):
        self.locks = defaultdict(Lock)
        self.sessions = 0
        self.total = 0
        self.session = DefaultClientSession()
        self.request_semaphore = Semaphore(
            50
        )  # Adjust the semaphore limit as per your requirement

    def __repr__(self: "SessionPool") -> str:
        return (
            f"<SessionPool queue={self.sessions} total={self.total} at {hex(id(self))}>"
        )

    def __str__(self: "SessionPool") -> str:
        return (
            f"<SessionPool queue={self.sessions} total={self.total} at {hex(id(self))}>"
        )

    @catcher(
        (
            ClientConnectorError,
            ClientResponseError,
            ContentTypeError,
            ClientProxyConnectionError,
            ClientHttpProxyError,
        )
    )
    async def get(
        self: "SessionPool", *args: Any, **kwargs: RequestOptions
    ) -> SessionResponse:
        return await self.request("GET", *args, **kwargs)

    @catcher(
        (
            ClientConnectorError,
            ContentTypeError,
            ClientResponseError,
            ClientProxyConnectionError,
            ClientHttpProxyError,
        )
    )
    async def post(
        self: "SessionPool", *args: Any, **kwargs: RequestOptions
    ) -> SessionResponse:
        return await self.request("POST", *args, **kwargs)

    @catcher(
        (
            ClientConnectorError,
            ContentTypeError,
            ClientResponseError,
            ClientProxyConnectionError,
            ClientHttpProxyError,
        )
    )
    async def request(
        self: "SessionPool", *args: Any, **kwargs: RequestOptions
    ) -> SessionResponse:
        json_model = kwargs.pop("json_model", None)
        slug = kwargs.pop("slug", None)

        async def get_response(*args, **kwargs: Any) -> dict:
            data = {}
            response_type = kwargs.pop("response_type", "json").lower()
            async with self.request_semaphore:  # Use the semaphore to control concurrent access
                response = await self.session.request(*args, **kwargs)
                if response.status == 405:
                    args = [i for i in args if i.lower() != response.method.lower()]
                    args.insert(0, dict(response.headers).get("Allow", "GET"))
                    kwargs.pop("method", None)
                    response = await self.session.request(*args, **kwargs)
                    if response_type == "json":
                        data["response"] = await response.json()
                    elif response_type == "text":
                        data["response"] = await response.text()
                    else:
                        data["response"] = await response.read()
                    data.update(
                        {
                            "headers": dict(response.headers),
                            "status": response.status,
                        }
                    )
                else:
                    if response_type == "json":
                        data["response"] = await response.json()
                    elif response_type == "text":
                        data["response"] = await response.text()
                    else:
                        data["response"] = await response.read()
                    data.update(
                        {
                            "headers": dict(response.headers),
                            "status": response.status,
                        }
                    )

            return data

        self.sessions += 1
        self.total += 1
        if proxy := kwargs.get("proxy"):
            async with self.locks[proxy]:
                _ = await get_response(*args, **kwargs)
        else:
            _ = await get_response(*args, **kwargs)
        if json_model:
            _["response"] = json_model(**_["response"])
        else:
            munch = DefaultMunch.fromDict(_["response"])
            if slug:
                for path in slug.split("."):
                    if path.isnumeric() and isinstance(munch, list):
                        try:
                            munch = munch[int(path)]
                        except IndexError:
                            pass

                    munch = getattr(munch, path, munch)

            _["response"] = munch
        self.sessions -= 1
        return SessionResponse(**_)


class ClientSession(DefaultClientSession):
    def __init__(self, *args, **kwargs):
        super().__init__(
            timeout=ClientTimeout(total=15),
            raise_for_status=True,
            *args,
            **kwargs,
        )

    async def request(self, method, url=None, *args, **kwargs) -> Any:
        if url is None:
            url = method
            method = "GET"

        slug: optional[str] = kwargs.pop("slug", None)
        response = await super().request(
            method=method,
            url=URL(url),
            *args,
            **kwargs,
        )

        if response.content_type == "text/plain":
            return await response.text()

        elif response.content_type.startswith(("image/", "video/", "audio/")):
            return await response.read()

        elif response.content_type == "text/html":
            return BeautifulSoup(await response.text(), "html.parser")

        elif response.content_type in (
            "application/json",
            "application/octet-stream",
            "text/javascript",
        ):
            try:
                data: Dict = await response.json(content_type=None)
            except Exception:
                return response

            munch = DefaultMunch.fromDict(data)
            if slug:
                for path in slug.split("."):
                    if path.isnumeric() and isinstance(munch, list):
                        try:
                            munch = munch[int(path)]
                        except IndexError:
                            pass

                    munch = getattr(munch, path, munch)

            return munch

        return response
