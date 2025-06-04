import asyncio
import hashlib
import os
from typing import Dict, Optional, Union

import orjson
import pycurl
from filetype.filetype import guess_mime
from tornado.curl_httpclient import CurlAsyncHTTPClient
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPClientError as CurlError  # noqa
from tornado.httpclient import HTTPRequest as CurlRequest  # noqa
from tornado.httpclient import HTTPResponse as CurlResponse  # noqa
from tornado.httputil import url_concat  # noqa

UA = os.getenv("CURL_UA", "coffinbot/curl")
SHARED_API_HEADERS = {
    "CF-Access-Client-Id": "e263d488792e91ef3c26e324b4f8c1da.access",
    "CF-Access-Client-Secret": "579b6bd1c5a0ecff20a58a7e1accac28fc286d4865e96314e5bb657d5c99c8c4",
    "content-type": "application/json",
    "user-agent": "coffinbot",
}


DEFAULT_HEADERS: Dict[str, str] = {"User-Agent": UA}
DEBUG_CURL = bool(os.getenv("DEBUG_CURL"))


def setcurl(c: pycurl.Curl) -> None:
    if DEBUG_CURL:
        c.setopt(pycurl.VERBOSE, 1)
    c.setopt(pycurl.COOKIEFILE, "")
    c.setopt(pycurl.NOSIGNAL, 1)


try:
    INIT_DONE  # type: ignore
except NameError:
    AsyncHTTPClient.configure(
        CurlAsyncHTTPClient,
        max_clients=128,
        defaults={
            "prepare_curl_callback": setcurl,
            "user_agent": UA,
            "follow_redirects": True,
            "max_redirects": 5,
            "allow_ipv6": True,
            "request_timeout": 50,
        },
    )
    pycurl.global_init(pycurl.GLOBAL_ALL)
    C = pycurl.Curl()
    setcurl(C)
    INIT_DONE = True


get_curl = AsyncHTTPClient
global_curl = AsyncHTTPClient


def get_curl():
    return AsyncHTTPClient()


def orjson_dumps(*a, **ka):
    return orjson.dumps(*a, **ka).decode("UTF-8")


async def fetch(
    request: Union[str, CurlRequest], raise_error: bool = True, **ka
) -> CurlResponse:
    client = AsyncHTTPClient()
    return await client.fetch(request, raise_error, **ka)
