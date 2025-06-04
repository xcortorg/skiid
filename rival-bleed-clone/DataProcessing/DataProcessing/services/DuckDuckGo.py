from lxml import html
from playwright.async_api import async_playwright
from redis.asyncio import Redis
from .Base import BaseService, cache
from typing import Optional, List, Dict, Any
from ..utils import (
    _text_extract_json,
    _extract_vqd,
    _normalize_url,
    _normalize,
    json_loads,
)
from aiohttp import ClientSession
from ..models.DuckDuckGo import DuckDuckGoImageResponse, DuckDuckGoSearchResponse
from itertools import cycle, islice

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Referer": "https://duckduckgo.com/",
}


class DuckDuckGoService(BaseService):
    def __init__(self: "DuckDuckGoService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("DuckDuckGo", self.redis, self.ttl)

    async def get_html(self: "DuckDuckGoService", query: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            await page.goto(
                f"https://duckduckgo.com?q={query.replace(' ', '+')}&hps=1&ia=web",
                wait_until="networkidle",
            )
            html = await page.content()
            try:
                await browser.close()
                await p.stop()
            except Exception:
                pass
        return html

    async def get_json(self, url: str, params: dict, keywords: Optional[str] = None):
        async with ClientSession() as session:
            async with session.get(url, params=params, headers=HEADERS) as response:
                data = await response.read()

        if keywords:
            return _text_extract_json(data, keywords)
        else:
            return json_loads(data)

    async def _get_vqd(self, keywords: str):
        async with ClientSession() as session:
            async with session.get(
                f"https://duckduckgo.com?q={keywords.replace(' ', '+')}&hps=1&ia=web",
                headers=HEADERS,
            ) as response:
                data = await response.read()
        return _extract_vqd(data, keywords)

    async def image_search(
        self,
        keywords: str,
        region: str = "us-en",
        safesearch: str = "moderate",
        timelimit: Optional[str] = None,
        size: Optional[str] = None,
        color: Optional[str] = None,
        type_image: Optional[str] = None,
        layout: Optional[str] = None,
        license_image: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> DuckDuckGoImageResponse:
        vqd = await self._get_vqd(keywords)
        safesearch_base = {"on": "1", "moderate": "1", "off": "-1"}
        timelimit = f"time:{timelimit}" if timelimit else ""
        size = f"size:{size}" if size else ""
        color = f"color:{color}" if color else ""
        type_image = f"type:{type_image}" if type_image else ""
        layout = f"layout:{layout}" if layout else ""
        license_image = f"license:{license_image}" if license_image else ""
        payload = {
            "l": region,
            "o": "json",
            "q": keywords,
            "vqd": vqd,
            "f": f"{timelimit},{size},{color},{type_image},{layout},{license_image}",
            "p": safesearch_base[safesearch.lower()],
        }
        c = set()
        results: List[Dict[str, str]] = []

        async def _images_page(s: int) -> list[dict[str, str]]:
            payload["s"] = f"{s}"
            resp_content = await self.get_json(
                "https://duckduckgo.com/i.js", params=payload
            )
            resp_json = json_loads(resp_content)

            page_data = resp_json.get("results", [])
            page_results = []
            for row in page_data:
                image_url = row.get("image")
                if image_url and image_url not in c:
                    c.add(image_url)
                    result = {
                        "title": row["title"],
                        "image": _normalize_url(image_url),
                        "thumbnail": _normalize_url(row["thumbnail"]),
                        "url": _normalize_url(row["url"]),
                        "height": row["height"],
                        "width": row["width"],
                        "source": row["source"],
                    }
                    page_results.append(result)
            return page_results

        slist = [0]
        if max_results:
            max_results = min(max_results, 500)
            slist.extend(range(100, max_results, 100))
        try:
            for i in slist:
                r = await _images_page(i)
                results.extend(r)
        except Exception as e:
            raise e

        return DuckDuckGoImageResponse(results=list(islice(results, max_results)))

    async def search(
        self,
        keywords: str,
        region: str = "us-en",
        safesearch: str = "moderate",
        timelimit: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> DuckDuckGoSearchResponse:
        """DuckDuckGo text search. Query params: https://duckduckgo.com/params.

        Args:
            keywords: keywords for query.
            region: wt-wt, us-en, uk-en, ru-ru, etc. Defaults to "wt-wt".
            safesearch: on, moderate, off. Defaults to "moderate".
            timelimit: d, w, m, y. Defaults to None.
            max_results: max number of results. If None, returns results only from the first response. Defaults to None.

        Returns:
            List of dictionaries with search results.

        Raises:
            DuckDuckGoSearchException: Base exception for duckduckgo_search errors.
            RatelimitException: Inherits from DuckDuckGoSearchException, raised for exceeding API request rate limits.
            TimeoutException: Inherits from DuckDuckGoSearchException, raised for API request timeouts.
        """
        assert keywords, "keywords is mandatory"

        vqd = await self._get_vqd(keywords)

        payload = {
            "q": keywords,
            "kl": region,
            "l": region,
            "p": "",
            "s": "0",
            "df": "",
            "vqd": vqd,
            "bing_market": f"{region[3:]}-{region[:2].upper()}",
            "ex": "",
        }
        safesearch = safesearch.lower()
        if safesearch == "moderate":
            payload["ex"] = "-1"
        elif safesearch == "off":
            payload["ex"] = "-2"
        elif safesearch == "on":  # strict
            payload["p"] = "1"
        if timelimit:
            payload["df"] = timelimit

        c = set()
        results: List[Dict[str, str]] = []

        async def _text_api_page(s: int) -> List[Dict[str, str]]:
            payload["s"] = f"{s}"
            page_data = await self.get_json(
                "https://links.duckduckgo.com/d.js", params=payload, keywords=keywords
            )
            page_results = []
            for row in page_data:
                href = row.get("u", None)
                if (
                    href
                    and href not in c
                    and href != f"http://www.google.com/search?q={keywords}"
                ):
                    c.add(href)
                    body = _normalize(row["a"])
                    if body:
                        result = {
                            "title": _normalize(row["t"]),
                            "href": _normalize_url(href),
                            "body": body,
                        }
                        page_results.append(result)
            return page_results

        slist = [0]
        if max_results:
            max_results = min(max_results, 2023)
            slist.extend(range(23, max_results, 50))
        try:
            for i in slist:
                r = await _text_api_page(i)
                results.extend(r)
        except Exception as e:
            raise e

        return DuckDuckGoSearchResponse(results=list(islice(results, max_results)))
