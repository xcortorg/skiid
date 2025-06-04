from .Base import BaseService, cache
from typing import Optional
from aiohttp import ClientSession
import json
from redis.asyncio import Redis
from bs4 import BeautifulSoup
from urllib.parse import quote

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
}


class FandomService(BaseService):
    def __init__(self: "FandomService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Fandom", self.redis, self.ttl)

    async def request_url(self: "FandomService", url: str) -> bytes:
        async with ClientSession() as session:
            async with session.get(url, headers=HEADERS) as response:
                data = await response.read()
        return data

    async def scrape_page(self: "FandomService", data: bytes) -> dict:
        soup = BeautifulSoup(data, "html.parser")
        script = soup.find("script", attrs={"type": "application/ld+json"})
        if not script:
            raise ValueError("No script with the type application/ld+json found")
        data = json.loads(script.contents[0])
        return data

    async def search(self: "FandomService", subdomain: str, query: str):
        url = f"https://{subdomain}.fandom.com/wiki/Special:Search?query={quote(query)}&navigationSearch=true"
        html = await self.request_url(url)
        soup = BeautifulSoup(html, "html.parser")
        options = soup.find_all("a", attrs={"class": "unified-search__result__title"})
        return [option.get("href") for option in options]

    @cache()
    async def query(
        self: "FandomService",
        subdomain: str,
        query: str,
        scrape_all: Optional[bool] = False,
    ):
        matches = await self.search(subdomain, query)
        if not scrape_all:
            return await self.scrape_page(await self.request_url(matches[0]))

        async def scrape_all_results(result: str) -> dict:
            return await self.scrape_page(await self.request_url(result))

        return [await scrape_all_results(r) for r in matches]
