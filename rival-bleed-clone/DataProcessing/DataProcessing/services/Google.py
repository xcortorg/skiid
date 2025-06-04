from redis.asyncio import Redis
from .Base import BaseService, cache
from typing import Optional, Dict, Any, List
from aiohttp import ClientSession
from playwright.async_api import async_playwright
import asyncio
from urllib.parse import urlparse
import random
from pydantic import BaseModel
from typing_extensions import NoReturn, Self
from tuuid import tuuid
import re
from loguru import logger
from lxml import html

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Priority": "u=1",
}


class SearchResult(BaseModel):
    url: str
    title: str
    description: str
    citation: str
    source: str

    def reformat_citation(self: Self) -> NoReturn:
        count = self.citation.count("https://")
        if count > 1:
            self.citation = f"https://{self.citation.split('https://')[1]}"


class ImageResult(BaseModel):
    url: str
    title: str
    website_name: str
    image_url: str
    redistributed: Optional[bool] = False

    async def redistribute(self: Self, url: Optional[str] = None):
        if self.redistributed:
            return
        if self.image_url.startswith("https://"):
            self.redistributed = True
            return
        async with ClientSession() as session:
            async with session.request(
                "POST",
                url or "https://cdn.rival.rocks/decode",
                json={"image": self.image_url},
            ) as response:
                print(response.status)
                url = (await response.json())["url"]
        self.image_url = f"{url}"
        self.redistributed = True
        print("redistributed one image")


class KnowledgePanelImage(BaseModel):
    src: Optional[str] = None
    alt: Optional[str] = None


class KnowledgePanel(BaseModel):
    title: str
    subtitle: str
    description: str
    url: Optional[str] = None
    source: Optional[str] = None
    additional_info: Dict[str, Any]
    images: Optional[List[KnowledgePanelImage]] = None


class GoogleSearchResponse(BaseModel):
    search_results: List[SearchResult]
    knowledge_panel: Optional[KnowledgePanel]
    cached: Optional[bool] = False

    def __len__(self: Self) -> int:
        return len(self.search_results)

    def prepare(self: Self) -> NoReturn:
        for result in self.search_results:
            result.reformat_citation()


class GoogleImageSearchResponse(BaseModel):
    image_results: List[ImageResult]
    cached: Optional[bool] = False

    def __len__(self: Self) -> int:
        return len(self.image_results)

    async def redistribute(self: Self) -> NoReturn:
        await asyncio.gather(*[i.redistribute() for i in self.image_results])


async def get_proxy_ports():
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
    ports = await get_proxy_ports()
    port = random.choice(ports)
    return f"http://admin:admin@127.0.0.1:{port}"


def proxy_server(url: str) -> tuple:
    connection_type, url = url.split("://")
    auth, server = url.split("@")
    username, password = auth.split(":")
    server, port = server.split(":")
    return connection_type, username, password, server, port


class GoogleService(BaseService):
    def __init__(self: "GoogleService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Google", self.redis, self.ttl)

    async def get_html(self: "GoogleService", url: str, **kwargs):
        proxy = await get_random_proxy()
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            connection_type, username, password, server, port = proxy_server(proxy)
            logger.info(f"{username} - {str(username)}")
            context = await browser.new_context(
                proxy={
                    "server": f"{connection_type}://{server}:{port}",
                    "username": username,
                    "password": password,
                }
            )
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle")
            content = await page.content()
            await page.close()
            await context.close()
            await browser.close()
        await p.stop()
        return content

    @cache()
    async def search(
        self: "GoogleService", query: str, safe: Optional[bool] = True, **kwargs
    ) -> GoogleSearchResponse:
        num_results = 100
        proxy = await get_random_proxy()
        url = f"https://www.google.com/search?q={query}&num={num_results}&safe={'active' if safe else 'off'}"
        # content = await self.get_html(url)
        async with ClientSession() as session:
            async with session.get(url, proxy=proxy, headers=HEADERS) as response:
                content = await response.text()
        tree = html.fromstring(content)
        results = []
        knowledge_panel = None
        search_divs = tree.xpath('//*[@id="rso"]/div')
        for div in search_divs:
            webtitle = ""
            title_elements = div.xpath(".//h3/text()")
            url_elements = div.xpath(".//a/@href")
            description_elements = div.xpath(
                ".//div/div/div/div/div[2]/div[1]/div/text()"
            ) or div.xpath('.//div[contains(@class, "VwiC3b")]//text()')
            if not description_elements:
                description_elements = div.xpath(
                    './/div[contains(@class, "VwiC3b")]//text()'
                )
            site_info_elements = []
            site_info_elements.append(div.xpath('.//span[contains(@role, "text")]'))
            site_info_elements.append(
                div.xpath(
                    ".//div/div/div/div/div[1]/div/a/div/div[1]/div/div/span/span[2]/span[1]/div"
                )
            )
            site_info_elements.append(div.xpath("../span/text()"))
            citation_elements = div.xpath(".//cite//text()")
            web_title_element = div.xpath(".//span")
            web_title_element = [d for d in web_title_element if d.text is not None]
            if web_title_element:
                webtitle += web_title_element[0].text
            if (
                title_elements
                and url_elements
                and description_elements
                and citation_elements
            ):
                try:
                    results.append(
                        SearchResult(
                            url=url_elements[0],
                            title=title_elements[0].strip(),
                            description=" ".join(description_elements).strip(),
                            citation=" ".join(citation_elements).strip(),
                            source=webtitle,
                        )
                    )
                except Exception as e:
                    logger.info(
                        f"error inputting search result into list: {e}\n{url_elements}"
                    )

            if len(results) >= num_results:
                break

        kp_divs = tree.xpath(
            '//div[contains(@class, "kp-blk") or contains(@class, "osrp-blk")]'
        )
        if kp_divs:
            kp_div = kp_divs[0]
            title = kp_div.xpath('.//div[@data-attrid="title"]//text()')
            subtitle = kp_div.xpath('.//div[@data-attrid="subtitle"]//text()')
            description = kp_div.xpath('.//div[@jsname="g7W7Ed"]//span/span/text()')
            source = kp_div.xpath('.//div[@jsname="g7W7Ed"]/span/a/span/text()')
            url = kp_div.xpath('.//div[@jsname="g7W7Ed"]//span/a/@href')
            images = kp_div.xpath(
                ".//div[2]/div/div/div/div/div[1]/div/div/div/div/div/div/div/div/div/div[1]/div/a/div/div"
            )
            img = None
            if images:
                for image in images:
                    if not img:
                        img = []
                    for child in image.iterchildren():
                        if child.tag == "img":
                            img.append(
                                {"src": child.get("src"), "alt": child.get("alt")}
                            )

            additional_info = {}

            info_divs = kp_div.xpath('.//div[contains(@class, "rVusze")]')
            for div in info_divs:
                titles = div.xpath('.//span[contains(@class, "w8qArf")]//text()')
                values = div.xpath(
                    './/span[contains(@class, "LrzXr kno-fv wHYlTd z8gr9e")]//text()'
                )

                if titles and values:
                    title_text = " ".join(titles).strip()
                    value_text = " ".join(values).strip()
                    if title_text and value_text:
                        additional_info[title_text.rstrip(":")] = value_text

            knowledge_panel = KnowledgePanel(
                title=" ".join(title).strip() if title else "No title",
                subtitle=(" ".join(subtitle).strip() if subtitle else "No subtitle"),
                description=(
                    " ".join(description).strip() if description else "No description"
                ),
                source="".join(source).strip() if source else "No source",
                url=url[0] if url else None,
                additional_info=additional_info,
                images=img,
            )
        data = GoogleSearchResponse(
            search_results=results[:num_results],
            knowledge_panel=knowledge_panel,
        )
        data.prepare()
        return data

    def _extract_image_id_to_base64(
        self: "GoogleService", tree: html.HtmlElement
    ) -> dict:
        image_id_to_base64 = {}

        image_data_regex = re.compile(
            r"data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)"
        )

        script_tags = tree.xpath('//script[contains(text(), "data:image/")]')
        for script in script_tags:
            script_content = script.text
            if script_content:
                # Find image IDs in the script content
                image_ids = re.findall(r"\[\s*\'(dimg_\d+)\'\s*\]", script_content)

                # Find all image data matches
                for match in image_data_regex.finditer(script_content):
                    image_format = match.group(1)
                    base64_data = match.group(2)

                    # Construct the full data URI
                    full_data_uri = f"data:image/{image_format};base64,{self._correct_base64_padding(base64_data)}"

                    # Map image IDs to the full base64 data
                    for img_id in image_ids:
                        image_id_to_base64[img_id] = full_data_uri

        return image_id_to_base64

    def _correct_base64_padding(self: "GoogleService", base64_string: str) -> str:
        padding_needed = (4 - len(base64_string) % 4) % 4
        if padding_needed:
            base64_string += "=" * padding_needed
        return base64_string

    @cache()
    async def get_images(
        self: "GoogleService", query: str, safe: Optional[bool] = True, **kwargs
    ) -> GoogleImageSearchResponse:
        params = {
            "q": query,
            "num": 100,
            "start": 0,
            "tbm": "isch",
            "safe": "active" if safe else "off",
        }
        query_string = "&".join(
            f"{str(key)}={str(value)}" for key, value in params.items()
        )
        url = f"https://google.com/search?{query_string}"
        html_content = await self.get_html(url)
        tree = html.fromstring(html_content)
        results = []
        # Extract image IDs and corresponding base64 data
        image_id_to_base64 = self._extract_image_id_to_base64(tree)

        images = tree.xpath('//div[contains(@data-attrid, "images universal")]')
        for element in images:
            img_url = element.xpath(".//img/@src")
            img_id = element.xpath(".//img/@id")
            website_url = element.xpath('.//a[@target="_blank"]/@href')

            title = element.xpath(".//div[2]/div[1]/text()")
            website_name = element.xpath(".//div[3]/a/div[1]/div[2]/div/span/text()")

            if img_id and website_url and title:
                img_id = img_id[0]
                base64_data = image_id_to_base64.get(img_id)

                website_name = website_name[0].strip() if website_name else "Unknown"
                results.append(
                    ImageResult(
                        url=website_url[0],
                        title=title[0],
                        website_name=website_name,
                        image_url=(base64_data if base64_data else img_url[0].strip()),
                    )
                )
        data = GoogleImageSearchResponse(image_results=results)
        return data

    async def image_search(
        self: "GoogleService", query: str, safe: Optional[bool] = True, **kwargs
    ):
        data = await self.get_images(query, safe)
        await data.redistribute()
        return data
