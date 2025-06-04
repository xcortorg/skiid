"""
Author: cop-discord
Email: cop@catgir.ls
Discord: aiohttp
"""

from typing import List, Optional, Any, Union, Dict
from parsel import Selector
import re
import orjson
import json
from lxml import html
import asyncio
import httpx
from aiohttp import ClientSession
from httpx import AsyncClient
from loguru import logger
from playwright.async_api import async_playwright
from pydantic import BaseModel
from xxhash import xxh64_hexdigest as hash_


class FAQ(BaseModel):
    query: Optional[str] = None
    answer: Optional[str] = None
    title: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None


class Keywords(BaseModel):
    FAQs: Optional[List[FAQ]] = None
    related_keywords: Optional[List] = None


class Result(BaseModel):
    position: Optional[int] = None
    title: Optional[str] = None
    url: Optional[str] = None
    origin: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    date: Optional[str] = None


class KnowledgePanel(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    additional_info: Optional[Dict[str, Any]] = None


class BingResponse(BaseModel):
    keywords: Optional[Keywords] = None
    results: Optional[List[Result]] = None
    knowledge_panel: Optional[KnowledgePanel] = None
    cached: Optional[bool] = False


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


def get_url(url: str, params: Optional[dict] = {}):
    response = url
    i = 0
    if response.endswith("?"):
        response = response[:-1]
    for key, value in params.items():
        i += 1
        if i == 1:
            char = "?"
        else:
            char = "&"
        response += f"{char}{str(key)}={str(value)}"
    return response


def parse_serps(selector) -> List[dict]:
    """parse SERPs from bing search pages"""
    data = []
    position = 0
    for result in selector.xpath("//li[@class='b_algo']"):
        try:
            try:
                origin = result.xpath(".//div[1]/a/@aria-label").get()
            except Exception:
                origin = None
            url = result.xpath(".//h2/a/@href").get()
            if not url:
                raise TypeError()
            if len(url) == 0:
                raise TypeError()
        except Exception:
            url = result.xpath(".//div/a/@href").get()
            try:
                origin = result.xpath(".//div[1]/a/@aria-label").get()
            except Exception:
                origin = None
        description = result.xpath("normalize-space(.//div/p)").extract_first()
        try:
            date = result.xpath(".//span[@class='news_dt']/text()").get()
        except Exception:
            date = None
        if data is not None and date is not None and len(date) > 12:
            date_pattern = re.compile(r"\b\d{2}-\d{2}-\d{4}\b")
            date_pattern.findall(description)
            dates = date_pattern.findall(date)
            date = dates[0] if dates else None
        try:
            title = result.xpath(".//h2//text()").get()
        except Exception:
            title = "".join(result.xpath(".//h2/a//text()").extract())
        if not origin:
            try:
                origin = result.xpath(".//div[@class='tptt']/text()").get()
            except Exception:
                pass
        position += 1
        data.append(
            {
                "position": position,
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
            }
        )
    return data


def parse_keywords(selector) -> dict:
    """parse FAQs and popular keywords on bing search pages"""
    faqs = []
    for faq in selector.xpath(
        "//div[@class='b_slidebar']/div/div[contains(@data-tag, 'QnA')]"
    ):
        url = faq.xpath(".//h2/a/@href").get()
        faqs.append(
            {
                "query": faq.xpath("./@data-query").get(),
                "answer": faq.xpath(".//span[contains(@data-tag, 'QnA')]/text()").get(),
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
    related_keywords = []
    for keyword in selector.xpath(".//li[@class='b_ans']/div/ul/li"):
        related_keywords.append("".join(keyword.xpath(".//a/div//text()").extract()))

    return {"FAQs": faqs, "related_keywords": related_keywords}


def parse_rich_snippet(_selector) -> dict:
    # Parse the HTML using lxml
    doc = html.fromstring(_selector)

    # XPath queries adapted for Bing's knowledge panel
    kp_divs = doc.xpath('//div[contains(@class, "lite-entcard-main")]')
    description = doc.xpath('//*[@id="ic_desc"]/div/div/text()') or doc.xpath(
        '//*[@id="l_ecrd_blk_1_PlainHero"]/div[1]/div[3]/div/a/p/span/text()'
    )
    subtitle = doc.xpath('//*[@id="l_ecrd_blk_1_PlainHero"]/div[2]/div/a/text()')
    title = doc.xpath('//div[@class="spl_logoheader_txt hdgrd"]//span/text()')
    url = doc.xpath('//*[@id="l_ecrd_blk_1_PlainHero"]/div[2]/div/a/@href')
    for kp_div in kp_divs:
        additional_info = {}
        info_divs = kp_div.xpath('.//div[contains(@class,"l_ecrd_vqfcts_row")]')
        for div in info_divs:
            titles = div.xpath('.//a[contains(@class, "lc_expfact_title")]//text()')
            values = div.xpath(
                ".//span//text()"
            )  # Adjust the xpath for the values you need to fetch

            if titles and values:
                title_text = " ".join(titles).strip()
                value_text = " ".join(values).strip()
                if title_text and value_text:
                    additional_info[title_text] = value_text
        if not title or not subtitle or not description or not url:
            continue

    knowledge_panel = {
        "title": " ".join(title).strip() if title else "No title",
        "subtitle": " ".join(subtitle).strip() if subtitle else "No subtitle",
        "description": (
            " ".join(description).strip() if description else "No description"
        ),
        "url": url[0] if url else None,
        "additional_info": additional_info,
    }

    return knowledge_panel


async def fetch_full_page(url: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle")
        content = await page.content()
        await browser.close()
    await p.stop()
    return content


async def get_bing_results(
    bot: Any, query: str, safe: Optional[bool] = True
) -> Optional[BingResponse]:
    key = hash_(f"bingsearch-{query}-{str(safe)}")
    if data := await bot.redis.get(key):
        _ = BingResponse(**orjson.loads(data))
        _.cached = True
        return _
    url = "https://www.bing.com/search"
    URL = get_url(url, {"q": query, "adlt": "moderate" if safe else "off", "count": 50})
    _html = await fetch_full_page(URL)
    selector = Selector(text=_html, huge_tree=False)
    final = {}
    try:
        final["keywords"] = parse_keywords(selector)
    except Exception:
        pass
    final["results"] = parse_serps(selector)
    try:
        final["knowledge_panel"] = parse_rich_snippet(_html)
    except Exception:
        pass
    await bot.redis.set(key, orjson.dumps(final))
    return BingResponse(**final)
