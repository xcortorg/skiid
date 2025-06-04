from playwright.async_api import async_playwright, Request
from redis.asyncio import Redis
from .Base import BaseService, cache
from typing import Optional
from regex.regex import Pattern
import regex as re
from bs4 import BeautifulSoup
import orjson
from aiohttp import ClientSession
from .TT import TikTok
import json
import asyncio

AWME_RE: Pattern[str] = re.compile(
    r"https?://www\.tiktok\.com/(?:embed|@(?P<user_id>[\w\.-]+)/video)/(?P<id>\d+)"
)


class TikTokService(BaseService):
    def __init__(self: "TikTokService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        self.tt = TikTok()
        super().__init__(self.redis, self.ttl)

    @cache()
    async def fetch_user_old(self: "TikTokService", username: str):
        def backup(content: bytes):
            soup = BeautifulSoup(content, "lxml")
            script = soup.find(
                "script", attrs={"id": "__UNIVERSAL_DATA_FOR_REHYDRATION__"}
            )
            text = orjson.loads(script.get_text())
            return text["__DEFAULT_SCOPE__"]["webapp.user-detail"]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            url = f"https://www.tiktok.com/@{username}"
            await page.goto(url)
            data = backup(await page.content())
            await browser.close()
        await p.stop()
        return TikTokUser(**data)

    @cache()
    async def fetch_post_old(self: "TikTokService", url: str):
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            url = f"https://www.tiktok.com/@{username}"

            async def handle_request(r: Request):
                if "api/item/detail/" in r.url:
                    data = orjson.loads(await (await r.response()).body())
                    future.set_result(data)

            page.on("request", handle_request)
            await page.goto(url, wait_until="domcontentloaded")
            while not future.done():
                await asyncio.sleep(0.01)
            await browser.close()
        await p.stop()

    @cache()
    async def fetch_user_embed(self: "TikTokService", username: str):
        async with ClientSession() as session:
            async with session.get(
                f"https://tiktok.com/embed/@{username.replace('@', '')}"
            ) as response:
                data = await response.read()
                string = await response.text()
        soup = BeautifulSoup(data, "html.parser")
        data = json.loads(
            soup.find("script", attrs={"id": "__FRONTITY_CONNECT_STATE__"}).text
        )
        from lxml import html

        tree = html.fromstring(string)
        base = data["source"]["data"]
        user = base[list(base.keys())[0]]
        for video in user["videoList"]:
            try:
                url = tree.xpath(f'//a[contains(@href, "{video["id"]}")]/@href')[0]
                video["url"] = url
            except Exception:
                pass
        return TikTokRawUser(**{"user": user["userInfo"], "videos": user["videoList"]})

    @cache()
    async def fetch_user(self: "TikTokService", username: str, **kwargs):
        return await self.tt.get_profile(username)

    @cache()
    async def fetch_post(self: "TikTokService", url: str, **kwargs):
        return await self.tt.get_post(url)

    async def fetch_feed(self: "TikTokService", username: str, **kwargs):
        return await self.tt.get_posts(username)
