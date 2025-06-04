"""
  Author: cop-discord
  Email: cop@catgir.ls
  Discord: aiohttp
"""

from typing import List, Optional, Any
from parsel import Selector
import re
import json
from asyncio import gather
from lxml import html
from playwright.async_api import async_playwright
from redis.asyncio import Redis
from .Base import BaseService, cache
from ..models import BingResponse, BingImageResponse
from unidecode_rs import decode as unidecode

HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "accept-encoding": "gzip, deflate, br, zstd",
    "accept-language": "en-US,en;q=0.7",
    "cache-control": "no-cache",
    "pragma": "no-cache",
    "priority": "u=0, i",
    "sec-ch-ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Brave";v="128"',
    "sec-ch-ua-arch": '""',
    "sec-ch-ua-bitness": '"64"',
    "sec-ch-ua-full-version-list": '"Chromium";v="128.0.0.0", "Not;A=Brand";v="24.0.0.0", "Brave";v="128.0.0.0"',
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-model": '"Nexus 5"',
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua-platform-version": '"6.0"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "sec-gpc": "1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
}


def match(num: int) -> str:
    return {1: "height", 2: "width"}.get(num, "")


class BingService(BaseService):
    def __init__(self: "BingService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Bing", self.redis, self.ttl)

    def get_url(self: "BingService", url: str, params: Optional[dict] = None) -> str:
        """Construct URL with query parameters."""
        if params is None:
            params = {}
        response = url.rstrip("?")
        query_string = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{response}?{query_string}" if query_string else response

    def parse_serps(
        self: "BingService", selector: Selector, start: Optional[int] = 1
    ) -> List[dict]:
        """Parse SERPs (Search Engine Results Pages) from Bing search pages."""
        data = []
        for position, result in enumerate(
            selector.xpath("//li[@class='b_algo']"), start=1
        ):
            url = (
                result.xpath(".//h2/a/@href").get()
                or result.xpath(".//div/a/@href").get()
            )
            if not url or not len(url):
                continue

            origin = (
                result.xpath(".//div[1]/a/@aria-label").get()
                or result.xpath(".//div[@class='tptt']/text()").get()
            )
            title = result.xpath(".//h2//text()").get() or "".join(
                result.xpath(".//h2/a//text()").extract()
            )
            description = result.xpath("normalize-space(.//div/p)").get()
            date = result.xpath(".//span[@class='news_dt']/text()").get()

            if date and len(date) > 12:
                date_pattern = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
                matched_dates = date_pattern.findall(date)
                date = matched_dates[0] if matched_dates else None

            data.append(
                {
                    "title": title,
                    "url": url,
                    "origin": origin,
                    "domain": (
                        url.split("https://")[-1].split("/")[0].replace("www.", "")
                        if url
                        else None
                    ),
                    "description": description,
                    "date": date,
                    "page": start + 1,
                }
            )
        return data

    def parse_keywords(self: "BingService", selector: Selector) -> dict:
        """Parse FAQs and popular keywords on Bing search pages."""
        faqs = []
        for faq in selector.xpath(
            "//div[@class='b_slidebar']/div/div[contains(@data-tag, 'QnA')]"
        ):
            url = faq.xpath(".//h2/a/@href").get()
            faqs.append(
                {
                    "query": faq.xpath("./@data-query").get(),
                    "answer": faq.xpath(
                        ".//span[contains(@data-tag, 'QnA')]/text()"
                    ).get(),
                    "title": "".join(
                        faq.xpath(".//div[@class='b_algo']/h2/a//text()").extract()
                    ),
                    "domain": (
                        url.split("https://")[-1].split("/")[0].replace("www.", "")
                        if url
                        else None
                    ),
                    "url": url,
                }
            )

        related_keywords = [
            "".join(keyword.xpath(".//a/div//text()").extract())
            for keyword in selector.xpath(".//li[@class='b_ans']/div/ul/li")
        ]

        return {"FAQs": faqs, "related_keywords": related_keywords}

    def parse_rich_snippet(self: "BingService", data: str) -> dict:
        """Parse knowledge panel from Bing search result."""
        doc = html.fromstring(data)
        kp_divs = doc.xpath('//div[contains(@class, "lite-entcard-main")]')
        description = doc.xpath('//*[@id="ic_desc"]/div/div/text()') or doc.xpath(
            '//*[@id="l_ecrd_blk_1_PlainHero"]/div[1]/div[3]/div/a/p/span/text()'
        )
        subtitle = doc.xpath('//*[@id="l_ecrd_blk_1_PlainHero"]/div[2]/div/a/text()')
        title = doc.xpath('//div[@class="spl_logoheader_txt hdgrd"]//span/text()')
        url = doc.xpath('//*[@id="l_ecrd_blk_1_PlainHero"]/div[2]/div/a/@href')

        additional_info = {}
        for kp_div in kp_divs:
            for div in kp_div.xpath('.//div[contains(@class,"l_ecrd_vqfcts_row")]'):
                titles = div.xpath('.//a[contains(@class, "lc_expfact_title")]//text()')
                values = div.xpath(".//span//text()")
                if titles and values:
                    additional_info[" ".join(titles).strip()] = " ".join(values).strip()

        return {
            "title": " ".join(title).strip() if title else "No title",
            "subtitle": " ".join(subtitle).strip() if subtitle else "No subtitle",
            "description": (
                " ".join(description).strip() if description else "No description"
            ),
            "url": url[0] if url else None,
            "additional_info": additional_info,
        }

    async def fetch_full_page(self: "BingService", url: str, **kwargs: Any) -> str:
        """Fetch full page content using Playwright."""
        """Note: 

          Normally personally I would keep the same browser session around but that really depends on the use case
          so I figured i'd just allow people to fork it and put in their own session handling

        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(**kwargs)
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            await browser.close()
        await p.stop()
        return content

    @cache()
    async def search(
        self: "BingService",
        query: str,
        safe: Optional[bool] = True,
        pages: Optional[int] = 1,
        **kwargs: Any,
    ) -> BingResponse:
        """Fetch Bing search results and cache the response."""
        final = {}

        async def get_page(page: int):
            url = self.get_url(
                "https://www.bing.com/search",
                {
                    "q": query,
                    "adlt": "moderate" if safe else "off",
                    "count": 35,
                    "first": page if page > 1 else page * 35,
                },
            )
            html_content = await self.fetch_full_page(url, **kwargs)
            selector = Selector(text=html_content)
            if final.get("results"):
                if page == 0:
                    for d in self.parse_serps(selector, 0):
                        final["results"].insert(0, d)
                else:
                    final["results"].extend(
                        self.parse_serps(selector, page / 35 if page > 1 else page)
                    )
            else:
                if page == 0:
                    for d in self.parse_serps(selector):
                        final["results"].insert(0, d)
                else:
                    final.update(
                        {
                            "results": self.parse_serps(
                                selector, page / 35 if page > 1 else page
                            )
                        }
                    )
                if page == 0:
                    try:
                        final["keywords"] = self.parse_keywords(selector)
                    except Exception:
                        pass
                    try:
                        final["knowledge_panel"] = self.parse_rich_snippet(html_content)
                    except Exception:
                        pass

        tasks = [get_page(1)]
        for i in range(pages):
            tasks.append(get_page(i))
        await gather(*tasks)
        return BingResponse(**final)

    @cache()
    async def image_search(
        self: "BingService",
        query: str,
        safe: Optional[bool] = True,
        pages: Optional[int] = 1,
        **kwargs: Any,
    ) -> BingImageResponse:
        """Fetch Bing Image search results and cache the responses"""
        results = []

        async def get_page(page: int):
            url = self.get_url(
                "https://www.bing.com/images/async",
                {
                    "q": query,
                    "adlt": "moderate" if safe else "off",
                    "count": 50,
                    "first": page if not page > 0 else page * 35,
                },
            )

            html_content = await self.fetch_full_page(url, **kwargs)

            tree = html.fromstring(html_content)

            uls = tree.xpath('//ul[contains(@class, "dgControl_list")]/li')

            for result in uls:
                metadata_elem = result.xpath('.//a[@class="iusc"]/@m')
                if not metadata_elem:
                    continue

                metadata = json.loads(metadata_elem[0])

                title = " ".join(
                    result.xpath('.//div[@class="infnmpt"]//a/text()')
                ).strip()
                img_format = (
                    " ".join(result.xpath('.//div[@class="imgpt"]/div/span/text()'))
                    .strip()
                    .split(" · ")
                )
                source = " ".join(
                    result.xpath('.//div[@class="imgpt"]//div[@class="lnkw"]//a/text()')
                ).strip()
                description = (
                    unidecode(metadata.get("desc", metadata.get("t")))
                    if metadata.get("desc", metadata.get("t"))
                    else unidecode(
                        " ".join(
                            result.xpath('.//a[contains(@class, "inflnk")]/@aria-label')
                        ).strip()
                    )
                )
                data = {
                    "url": metadata["purl"],
                    "thumbnail": metadata["turl"],
                    "image": metadata["murl"],
                    "content": description or None,
                    "title": unidecode(title),
                    "source": source,
                    "resolution": {
                        match(i): v
                        for i, v in enumerate(img_format[0].split("\u00d7"), start=1)
                    },
                }
                if data not in results:
                    results.append(data)

        tasks = [get_page(0)]
        for i in range(pages):
            if i not in (0,):
                tasks.append(get_page(i))
        await gather(*tasks)
        _ = {"query": query, "safe": safe, "pages": pages, "results": results}
        return BingImageResponse(**_)
