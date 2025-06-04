from .Base import cache, BaseService
from redis.asyncio import Redis
from typing import Optional
from aiohttp import ClientSession
from asyncio import to_thread
from ..models.Pinterest import PinterestPinResponse, PinterestUserResponse
import subprocess
import tuuid
import os
import requests
import re
import orjson

POST_RE = re.compile(
    r"(?x) https?://(?:[^/]+\.)?pinterest\.(?: com|fr|de|ch|jp|cl|ca|it|co\.uk|nz|ru|com\.au|at|pt|co\.kr|es|com\.mx|"
    r" dk|ph|th|com\.uy|co|nl|info|kr|ie|vn|com\.vn|ec|mx|in|pe|co\.at|hu|"
    r" co\.in|co\.nz|id|com\.ec|com\.py|tw|be|uk|com\.bo|com\.pe)/pin/(?P<id>\d+)",
)

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.164 Safari/537.36",
}


class PinterestService(BaseService):
    def __init__(self: "PinterestService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Pinterest", self.redis, self.ttl)

    @cache()
    async def get_post(self, url: str) -> PinterestPinResponse:
        if "pin.it" in url.lower():
            async with ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    url = str(response.url)

        if "url_shortener" in url:
            raise Exception("Pin was **DELETED**")

        ident = POST_RE.match(url).group("id")
        async with ClientSession() as session:
            opt = {
                "options": {
                    "field_set_key": "unauth_react_main_pin",
                    "id": f"{ident}",
                },
            }
            param = {"data": orjson.dumps(opt).decode()}
            async with session.get(
                "https://www.pinterest.com/resource/PinResource/get/",
                headers=headers,
                params=param,
            ) as request:
                data = await request.json()
        return PinterestPinResponse(**data)

    @cache()
    async def get_user(self, username: str) -> PinterestUserResponse:
        headers = {
            "authority": "www.pinterest.com",
            "accept": "application/json, text/javascript, */*, q=0.01",
            "accept-language": "en-US,en;q=0.6",
            "dnt": "1",
            "referer": "https://www.pinterest.com/",
            "sec-ch-ua": '"Brave";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Mobile/15E148 Safari/604.1",
            "x-pinterest-appstate": "active",
            "x-pinterest-pws-handler": "www/[username].js",
            "x-pinterest-source-url": f"/{username}/",
            "x-requested-with": "XMLHttpRequest",
        }
        params = {
            "source_url": f"/{username}/",
            "data": '{"options":{"username":"USERNAME","field_set_key":"profile"},"context":{}}'.replace(
                "USERNAME", username
            ),
        }
        async with ClientSession() as session:
            async with session.get(
                "https://www.pinterest.com/resource/UserResource/get/",
                params=params,
                headers=headers,
            ) as response:
                data = await response.json()
        return PinterestUserResponse(**data)
