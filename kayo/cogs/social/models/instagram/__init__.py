from __future__ import annotations

from contextlib import asynccontextmanager
from secrets import token_urlsafe
from logging import getLogger
from random import choice
from typing import Any, AsyncGenerator, Literal, TypedDict

from aiohttp import ClientResponse
from aiohttp import ClientSession as _ClientSession
from aiohttp.typedefs import StrOrURL

import config

log = getLogger("slut/gram")


class Cookies(TypedDict):
    ig_did: str
    ig_nrcb: str
    datr: str
    mid: str
    ds_user_id: str
    csrftoken: str
    sessionid: str


def get_cookies() -> dict:
    cookies = choice(config.Authorization.INSTAGRAM.COOKIES)
    return cookies


class ClientSession(_ClientSession):
    user_id: str
    session_id: str

    def __init__(self, *args, **kwargs):
        cookies = get_cookies()
        self.user_id = cookies["ds_user_id"]
        self.session_id = cookies["sessionid"]
        super().__init__(
            *args,
            cookies=cookies,  # type: ignore
            **kwargs,
        )
        self.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
                ),
            }
        )

    async def dismiss_challenge(
        self,
        resp: ClientResponse,
    ) -> ClientResponse | Literal[True]:
        if "challenge" in resp.url.path:
            log.warning("Failed to resolve challenge for session %s", self.user_id)
            raise ValueError("Failed to resolve challenge!")

            # _resp = await self.post(
            #     "https://www.instagram.com/api/v1/bloks/apps/com.instagram.challenge.navigation.take_challenge/",
            #     data={
            #         "nest_data_manifest": "true",
            #         "has_follow_up_screens": "false",
            #         "challenge_context": token_urlsafe(64),
            #     },
            # )
            # if not _resp.ok:
            #     log.warning(
            #         "Failed to resolve challenge, endpoint returned %s.", _resp.status
            #     )
            #     raise ValueError("Failed to resolve challenge.")

            # return True

        return resp

    @asynccontextmanager
    async def request(
        self,
        method: str,
        url: StrOrURL,
        *,
        allow_redirects: bool = True,
        **kwargs: Any,
    ) -> AsyncGenerator[ClientResponse, None]:
        log.debug("Using Instagram session %s", self.user_id)

        async with super().request(
            method,
            url,
            allow_redirects=allow_redirects,
            **kwargs,
        ) as resp:
            challenge = await self.dismiss_challenge(resp)
            if challenge:
                resp = await super().request(
                    method,
                    url,
                    allow_redirects=allow_redirects,
                    **kwargs,
                )

            yield resp
