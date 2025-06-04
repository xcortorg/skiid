import json
from typing import Optional
from urllib.parse import quote

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from redis.asyncio import Redis

from .Base import BaseService, cache

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
}


class WikipediaService(BaseService):
    def __init__(self: "WikipediaService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Wikipedia", self.redis, self.ttl)

    async def request_url(self: "WikipediaService", url: str) -> bytes:
        async with ClientSession() as session:
            async with session.get(url, headers=HEADERS) as response:
                data = await response.read()
        return data

    async def scrape_page(self: "WikipediaService", data: bytes) -> dict:
        soup = BeautifulSoup(data, "html.parser")
        script = soup.find("script", attrs={"type": "application/ld+json"})
        if not script:
            raise ValueError("No script with the type application/ld+json found")
        data = json.loads(script.contents[0])
        return data

    @cache()
    async def search(
        self: "WikipediaService", query: str, langcode: Optional[str] = "en"
    ) -> dict:
        html = await self.request_url(
            f"https://{langcode}.wikipedia.org?search={quote(query)}"
        )
        return await self.scrape_page(html)
