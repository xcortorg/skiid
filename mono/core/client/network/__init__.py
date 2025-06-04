"""
Copyright 2024 Samuel Davis

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

from http.cookies import SimpleCookie
from typing import Any, Dict, Literal, Optional, Self, TypedDict, Union, Unpack

from aiohttp import ClientResponse, ClientResponseError, ClientSession
from cashews import cache
from lxml import html
from lxml.html import HtmlElement

from .errors import CommandFailure
from .types import JSON


class RequestKwargs(TypedDict, total=False):
    """
    A TypedDict to specify additional request keyword arguments.
    Includes optional cookies, headers, params, and proxy.
    """

    cookies: Dict[str, str]
    headers: Dict[str, str]
    params: Dict[str, Any]
    proxy: str


class Network(ClientSession):
    """
    Network class extending aiohttp.ClientSession for a customized HTTP request coroutine
    with additional options and error handling.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def request(
        self: Self,
        url: str,
        method: Optional[Literal["GET", "PUT", "DELETE", "POST"]] = "GET",
        **kwargs: Unpack[RequestKwargs],
    ) -> Union[ClientResponse, JSON, bytes, HtmlElement]:
        """
        Make an HTTP request using the specified method and URL, with additional options.

        Args:
            url (str): The URL to send the request to.
            method (Optional[Literal["GET", "PUT", "DELETE", "POST"]]): The HTTP method to use.
            **kwargs: Additional request options specified in RequestKwargs.

        Returns:
            Union[ClientResponse, JSON, bytes, HtmlElement]: The response object, parsed according to its content type.

        Raises:
            CommandFailure: If any client response error occurs.
        """
        headers: Dict[str, str] = kwargs.get(
            "headers",
            {
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.5",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            },
        )

        kwargs["headers"] = headers

        try:
            response: ClientResponse = await super().request(
                method=method, url=url, **kwargs
            )
            response.raise_for_status()  # Raises an error for bad responses
        except ClientResponseError as exception:
            raise CommandFailure(
                f"API returned **{exception.status}** - Please try again later."
            )

        if "tiktok" in url:
            cookies = {
                key: morsel.value
                for header in response.headers.getall("Set-Cookie", [])
                for key, morsel in SimpleCookie(header).items()
            }

            await cache.set(
                "TIKTOK:COOKIE",
                ";".join(f"{k}={v}" for k, v in cookies.items()),
                expire="5h",
            )

        if response.content_type in ["application/json", "text/javascript"]:
            return await response.json()
        if response.content_type == "text/html":
            return html.fromstring(await response.text(encoding="utf-8"))
        elif response.content_type.startswith(("image/", "video/", "audio/")):
            return await response.read()

        return response
