import json
from asyncio import get_running_loop
from typing import Any, Optional

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from playwright.async_api import Request, async_playwright
from redis.asyncio import Redis

from .._impl.exceptions import InvalidUser
from ..models.SoundCloud import SoundCloudSearch, SoundCloudUser
from .Base import BaseService, cache

HEADERS = {
    "User-Agent": "",
}


class SoundCloudService(BaseService):
    def __init__(self: "SoundCloudService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("SoundCloud", self.redis, self.ttl)

    @cache()
    async def fetch_raw_user(
        self: "SoundCloudService",
        username: str,
        cookie: Optional[str] = None,
        **kwargs: Any,
    ) -> bytes:
        if cookie:
            HEADERS["Cookie"] = cookie
        async with ClientSession() as session:
            async with session.get(
                f"https://soundcloud.com/{username}", headers=HEADERS
            ) as response:
                if response.status == 404:
                    raise InvalidUser(
                        f"No **{self.__class__.__name__.replace('Service', '')} User** found under username `{username}`"
                    )
                data = await response.read()
        return data

    async def fetch_user(
        self: "SoundCloudService",
        username: str,
        cookie: Optional[str] = None,
        **kwargs: Any,
    ) -> SoundCloudUser:
        raw_data = await self.fetch_raw_user(username, cookie, **kwargs)
        soup = BeautifulSoup(raw_data, "html.parser")
        script = json.loads(soup.find("script", attrs={"id": "__NEXT_DATA__"}).text)
        return SoundCloudUser(**script)

    @cache()
    async def search(
        self: "SoundCloudService", query: str, **kwargs: Any
    ) -> SoundCloudSearch:
        loop = get_running_loop()
        future = loop.create_future()

        async def on_request(request: Request):
            if "https://api-v2.soundcloud.com/search?" in str(request.url):
                response = await request.response()
                data = await response.body()
                future.set_result(data)
            else:
                return

        async with async_playwright() as launcher:
            browser = await launcher.chromium.launch(headless=True)
            page = await browser.new_page()
            page.on("request", on_request)
            await page.goto(
                f"https://soundcloud.com/search?q={query.replace(' ', '+')}"
            )
            await page.close()
            await browser.close()
        await launcher.stop()
        return SoundCloudSearch.parse_raw(future.result())
