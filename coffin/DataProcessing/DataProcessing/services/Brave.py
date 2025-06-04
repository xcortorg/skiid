import asyncio
import random
import socket
from itertools import chain
from typing import Optional

import lxml
import psutil
from aiomisc.backoff import asyncretry
from bs4 import BeautifulSoup
from discord.http import iteration
from httpx import AsyncClient, AsyncHTTPTransport
from redis.asyncio import Redis
from tools import timeit

from ..models.Brave import BraveImageSearchResponse, BraveSearchResponse
from .Base import BaseService, cache

DICT = dict()


async def get_3proxy_ports():
    process = await asyncio.create_subprocess_exec(
        "netstat",
        "-tlnp",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if stderr:
        print(f"Error: {stderr.decode().strip()}")
        return []

    ports = []
    for line in stdout.decode().splitlines():
        if "3proxy" in line:
            parts = line.split()
            if len(parts) > 3:
                port_info = parts[3]
                port = port_info.split(":")[-1]  # Get the port number
                ports.append(port)

    return ports


async def get_random_proxy():
    ports = await get_3proxy_ports()
    port = random.choice(ports)
    return f"http://admin:admin@127.0.0.1:{port}"


def format_factsheet(data: list):
    _ = {}
    data.pop(0)
    data = [d for d in data if d != " "]
    _["subject"] = data[0]
    data.pop(-1)
    data.pop(0)
    formatted_dict = {str(data[i]): data[i + 1] for i in range(0, len(data), 2)}
    _.update(formatted_dict)
    return _


def get_ips():
    ips = [
        addr.address
        for addrs in psutil.net_if_addrs().values()
        for addr in addrs
        if addr.family == socket.AF_INET6
    ]
    if len(ips) > 0:
        return iteration(ips)
    else:
        return None


class BraveService(BaseService):
    def __init__(self: "BraveService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Brave", self.redis, self.ttl)
        self.ips = get_ips()

    def get_url(self: "BraveService", base_url: str, params: Optional[dict] = DICT):
        params_str = ""
        for key, value in params.items():
            params_str += f"{key.replace(' ', '+')}={str(value).replace(' ', '+')}&"
        if params_str.endswith("&"):
            params_str = params_str[:-1]
        return f"{base_url}?{params_str}"

    async def get_page(
        self: "BraveService", client: AsyncClient, url: str, headers: dict
    ):
        response = await client.get(url, headers=headers)
        return response.content

    async def get_transport(self: "BraveService"):
        return await get_random_proxy()

    @cache()
    async def search(
        self: "BraveService", query: str, safe: Optional[bool] = False
    ) -> BraveSearchResponse:
        return await self.do_search(query, safe)

    @asyncretry(max_tries=5, pause=0.5)
    async def do_search(
        self: "BraveService", query: str, safe: Optional[bool] = False
    ) -> BraveSearchResponse:
        safety = "moderate" if safe is True else "off"
        results = []
        headers = {
            "authority": "search.brave.com",
            "method": "GET",
            "path": f"/search?q={query.replace(' ', '%20')}",
            "scheme": "https",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, zstd",
            "accept-language": "en-US,en;q=0.6",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "referer": f"https://search.brave.com/search?q={query.replace(' ', '%20')}&source=web",
            "sec-ch-ua": '"Chromium";v="124", "Brave";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "Cookie": f"safesearch={safety}; useLocation=0",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }

        @asyncretry(max_tries=5, pause=0.1)
        async def get_page(page: int = 1):
            ret = []
            offset = f"&offset={page}&spellcheck=0"
            if page - 1 == 0:
                ref = f"https://search.brave.com/search?q={query.replace(' ', '%20')}&source=web"
            else:
                ref = f"https://search.brave.com/search?q={query.replace(' ', '%20')}&source=web&offset={page-1}&spellcheck=0"
            try:
                h = headers.copy()
                h["path"] = f"/search?q={query.replace(' ', '%20')}{offset}"
                h["referer"] = ref
                transport = await self.get_transport()
                if transport:
                    kwargs = {"proxy": transport}
                else:
                    kwargs = {}
                async with AsyncClient(**kwargs) as client:
                    resp = await client.get(
                        f"https://search.brave.com/search?q={query.replace(' ', '%20')}&source=web{offset}",
                        headers=h,
                    )
                    h = resp.text
                tree = lxml.html.fromstring(h)
                elements = tree.xpath("//div[@data-type='web']")
                for element in elements:
                    result_url = element.xpath(".//a[@target='_self']/@href")[0]
                    result_title = element.xpath(
                        ".//div[contains(@class, 'title')]/text()"
                    )[0]
                    result_description = element.xpath(
                        ".//div[contains(@class, 'snippet-content')]/div[contains(@class, 'snippet-description')]/text()"
                    )
                    result_description = " ".join(
                        r for r in result_description if r != " "
                    ).replace("   ", " ")

                    fav_icon = element.xpath(
                        ".//img[contains(@class, 'favicon')]/@src"
                    )[0]
                    site_name = element.xpath(
                        ".//div[contains(@class, 'sitename')]/text()"
                    )[0]
                    breadcrumbs = "".join(
                        m
                        for m in element.xpath(
                            ".//cite[contains(@class, 'snippet-url')]//text()"
                        )
                    )
                    breadcrumbs = breadcrumbs.lstrip().rstrip().replace("\u203a", ">")
                    breadcrumbs = breadcrumbs.replace("  ", " ").replace("  ", " ")
                    ret.append(
                        {
                            "url": result_url,
                            "title": result_title,
                            "favicon": fav_icon,
                            "source": site_name,
                            "breadcrumb": breadcrumbs,
                            "description": result_description,
                        }
                    )
            except Exception as e:
                print(f"an error occured on page {page}: {e}")
            return ret

        async with timeit() as timer:
            transport = await self.get_transport()
            if transport:
                kwargs = {"proxy": transport}
            else:
                kwargs = {}
            async with AsyncClient(**kwargs) as client:
                resp = await client.get(
                    f"https://search.brave.com/search?q={query.replace(' ', '%20').replace('+', '%20')}&source=web",
                    headers=headers,
                )
            html_str = resp.text
            tree = lxml.html.fromstring(html_str)
            main_elements = tree.xpath("//div[contains(@class, 'infobox-attr')]")
            # Initialize an empty dictionary to store the attributes and values
            main_result = {}
            result_dict = {}
            main_result_title = "//div[contains(@class, 'infobox-header-title')]"
            title_elem = tree.xpath(f"{main_result_title}/a/h1/text()")
            main_result["title"] = title_elem[0] if len(title_elem) > 0 else ""
            url_elem = tree.xpath(f"{main_result_title}/a/@href")
            main_result["url"] = url_elem[0] if len(url_elem) > 0 else ""
            extra_elem = tree.xpath(
                "//div[contains(@data-attrid, 'subtitle')]/span/text()"
            )
            main_result["extra_subtitle"] = extra_elem[0] if len(extra_elem) > 0 else ""
            subtitle_elem = tree.xpath(
                "//div[contains(@class, 'infobox-header')]/div/h2/text()"
            )
            main_result["subtitle"] = subtitle_elem[0] if len(subtitle_elem) > 0 else ""
            description_elem = tree.xpath(
                "//section[contains(@id, 'infobox')]/header/section//text()"
            )
            main_result["description"] = (
                description_elem[0].lstrip().rstrip()
                if len(description_elem) > 0
                else ""
            )
            for element in main_elements:
                # Extract the attribute name
                attr_name = element.xpath(
                    ".//span[contains(@class, 'infobox-attr-name')]//text()"
                )
                attr_name = attr_name[0] if attr_name else None

                # Extract the attribute value
                attr_value = element.xpath(
                    ".//span[contains(@class, 'attr-value')]//text()"
                )
                attr_value = attr_value[0] if attr_value else None

                # Add to the dictionary if both name and value are found
                if attr_name and attr_value:
                    result_dict[str(attr_name)] = attr_value
            main_result["full_info"] = result_dict
            elements = tree.xpath("//div[@data-type='web']")
            for element in elements:
                result_url = element.xpath(".//a[@target='_self']/@href")[0]
                result_title = element.xpath(
                    ".//div[contains(@class, 'title')]/text()"
                )[0]
                result_description = element.xpath(
                    ".//div[contains(@class, 'snippet-content')]/div[contains(@class, 'snippet-description')]/text()"
                )
                result_description = " ".join(
                    r for r in result_description if r != " "
                ).replace("   ", " ")

                fav_icon = element.xpath(".//img[contains(@class, 'favicon')]/@src")[0]
                site_name = element.xpath(
                    ".//div[contains(@class, 'sitename')]/text()"
                )[0]
                breadcrumbs = "".join(
                    m
                    for m in element.xpath(
                        ".//cite[contains(@class, 'snippet-url')]//text()"
                    )
                )
                breadcrumbs = breadcrumbs.lstrip().rstrip().replace("\u203a", ">")
                breadcrumbs = breadcrumbs.replace("  ", " ").replace("  ", " ")
                results.append(
                    {
                        "url": result_url,
                        "title": result_title,
                        "favicon": fav_icon,
                        "source": site_name,
                        "breadcrumb": breadcrumbs,
                        "description": result_description,
                    }
                )
        res = list(
            chain.from_iterable(
                await asyncio.gather(*[get_page(i) for i in range(1, 3)])
            )
        )
        results.extend(res)
        data = {
            "query_time": str(timer.elapsed),
            "query": query,
            "safe": safety,
            "main_result": main_result,
            "results": results,
        }
        return BraveSearchResponse(**data)

    @cache()
    async def image_search(
        self: "BraveService", query: str, safe: Optional[bool] = False
    ) -> BraveImageSearchResponse:
        base_url = "https://search.brave.com/images"
        safety = "moderate" if safe is True else "off"
        headers = {
            "authority": "search.brave.com",
            "method": "GET",
            "path": f"/images?q={query.replace(' ', '%20')}",
            "scheme": "https",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "accept-encoding": "gzip, deflate, zstd",
            "accept-language": "en-US,en;q=0.6",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "referer": f"https://search.brave.com/search?q={query.replace(' ', '%20')}&source=web",
            "sec-ch-ua": '"Chromium";v="124", "Brave";v="124", "Not-A.Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "sec-gpc": "1",
            "Cookie": f"safesearch={safety}; useLocation=0",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        }
        async with timeit() as timer:
            urls = [
                self.get_url(base_url, {"q": query.replace(" ", "+"), "page": i})
                for i in range(1, 3)
            ]
            if transport := await self.get_transport():
                kwargs = {"proxy": transport}
            else:
                kwargs = {}
            async with AsyncClient(**kwargs) as client:
                tasks = [self.get_page(client, url, headers) for url in urls]
                contents = await asyncio.gather(*tasks)
                results = []
                for content in contents:
                    soup = BeautifulSoup(content, "html.parser")
                    ns_ = soup.findAll("div", class_="noscript-image")
                    for ns in ns_:
                        image_src = ns.a.img["src"]
                        source_text = ns.find_next("div", class_="img-source").span.text
                        title = ns.find_next("div", class_="img-title").text
                        source = f"https://{source_text}"
                        results.append(
                            {
                                "url": image_src,
                                "domain": source_text,
                                "source": source,
                                "title": title,
                            }
                        )
        data = {
            "query_time": timer.elapsed,
            "status": "current",
            "safe": safe,
            "results": results,
        }
        return BraveImageSearchResponse(**data)
