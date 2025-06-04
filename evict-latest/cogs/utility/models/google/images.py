import re
from cashews import cache
from typing import Any, Dict, List, Optional
from enum import Enum
from lxml import html
from lxml.html import HtmlElement
from discord.ext.commands import CommandError
from aiohttp import ClientSession


DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}


class SafeSearchLevel(Enum):
    OFF = "off"
    MODERATE = "moderate"
    STRICT = "strict"


class SearchResult:
    url: str
    title: str
    description: str
    citation: str


class KnowledgePanel:
    title: str
    subtitle: str
    description: str
    additional_info: Dict[str, Any]


class GoogleResponse:
    search_results: List[SearchResult]
    knowledge_panel: Optional[KnowledgePanel]

    def __len__(self) -> int:
        return len(self.search_results) + 1 if self.knowledge_panel else 0


class ImageResult:
    url: str
    title: str
    website_name: str
    image_url: str


class Google:
    def __init__(
        self,
        session: ClientSession,
        safe_search: Optional[SafeSearchLevel] = SafeSearchLevel.STRICT,
        max_results: Optional[int] = 100,
    ):
        self.session = session
        self.safe_search = SafeSearchLevel.STRICT
        self.max_results = max_results

    @cache(ttl="5m", key="GOOGLE:IMAGE:{query}")
    async def images(
        self, query: str, safe_search: Optional[SafeSearchLevel] = None
    ) -> List[str]:
        safe_search = SafeSearchLevel.STRICT

        response = await self.session.request(
            method="GET",
            url="https://www.google.com/search",
            headers={
                **DEFAULT_HEADERS,
                "safe": "strict",
            },
            params={
                "q": query,
                "num": self.max_results,
                "hl": "en",
                "start": 0,
                "tbm": "isch",
                "safe": "strict",
                "safesearch": "on",
            },
        )

        if response.status == 429:
            raise CommandError("Evict has been rate limited.")

        response_text = await response.text()
        image_urls = re.findall(
            r'https?://[^"\s]+(?:\.jpg|\.jpeg|\.png|\.gif)', response_text
        )

        return list(set(image_urls))

    def _extract_knowledge_panel(
        self, tree: html.HtmlElement
    ) -> Optional[KnowledgePanel]:
        kp_divs = tree.xpath(
            '//div[contains(@class, "kp-blk") or contains(@class, "osrp-blk")]'
        )

        if not kp_divs:
            return None

        kp_div = kp_divs[0]

        def get_text(xpath_expr: str, default: str) -> str:
            result = kp_div.xpath(xpath_expr + "/text()")
            return result[0].strip() if result else default

        title = get_text('.//div[@data-attrid="title"]', "No title")
        subtitle = get_text('.//div[@data-attrid="subtitle"]', "No subtitle")

        description = " ".join(
            [
                text.strip()
                for text in kp_div.xpath('.//div[@jsname="g7W7Ed"]//span/text()')
            ]
        ).strip()

        additional_info = {
            info.xpath('.//div[contains(@class, "w8qArf")]/text()')[0].rstrip(
                ":"
            ): info.xpath('.//div[contains(@class, "LrzXr")]/text()')[0]
            for info in kp_div.xpath('.//div[contains(@class, "rVusze")]')
            if info.xpath('.//div[contains(@class, "w8qArf")]/text()')
            and info.xpath('.//div[contains(@class, "LrzXr")]/text()')
        }

        return KnowledgePanel(
            title=title,
            subtitle=subtitle,
            description=description,
            additional_info=additional_info,
        )

    @cache(ttl="5m", key="GOOGLE:SEARCH:{query}")
    async def search(self, query: str) -> GoogleResponse:
        response = await self.session.request(
            method="GET",
            url="https://www.google.com/search",
            headers=DEFAULT_HEADERS,
            params={
                "q": query,
                "num": self.max_results,
                "hl": "en",
                "start": 0,
                "safe": "active" if self.safe_search else "off",
            },
        )

        if response.status == 429:
            raise CommandError("Evict has been rate limited.")

        if not isinstance(response, HtmlElement):
            raise CommandError(f"Invalid response for query `{query}`.")

        results: List[HtmlElement] = response.xpath(
            '//div[@id="search"]//div[@id="rso"]//div[@jscontroller]'
        )

        return GoogleResponse(
            search_results=[
                SearchResult(
                    url=(
                        result.xpath(".//a/@href")[0]
                        if result.xpath(".//a/@href")
                        else "https://unknown.com/unknown"
                    ),
                    title=(
                        result.xpath(".//h3[1]/text()")[0]
                        if result.xpath(".//h3[1]")
                        else "Unknown"
                    ),
                    description=" ".join(
                        result.xpath(".//span[not(@class)]//text()")
                    ).strip(),
                    citation=" ".join(
                        sorted(
                            set(result.xpath('.//cite[@role="text"]//text()')),
                            key=result.xpath('.//cite[@role="text"]//text()').index,
                        )
                    ).strip(),
                )
                for result in results
                if result.xpath(".//h3[1]/text()")
                and result.xpath(".//a/@href")
                and result.xpath('.//cite[@role="text"]//text')
                and "Description" not in result.xpath(".//h3[1]/text()")
            ],
            knowledge_panel=self._extract_knowledge_panel(response),
        )

    def _extract_image_id_to_base64(self, tree: HtmlElement) -> Dict[str, str]:
        image_id_to_base64 = {}

        image_data_regex = re.compile(
            r"data:image/(png|jpeg|jpg|webp|gif);base64,([A-Za-z0-9+/=]+)"
        )

        script_tags = tree.xpath('//script[contains(text(), "data:image/")]')
        for script in script_tags:
            script_content = script.text
            if not script_content:
                continue

            image_ids = re.findall(r"\[\s*\'(dimg_\d+)\'\s*\]", script_content)

            for match in image_data_regex.finditer(script_content):
                image_format = match.group(1)
                base64_data = match.group(2)

                full_data_uri = f"data:image/{image_format};base64,{self._correct_base64_padding(base64_data)}"

                for img_id in image_ids:
                    image_id_to_base64[img_id] = full_data_uri

        return image_id_to_base64

    def _correct_base64_padding(self, base64_string: str) -> str:
        padding_needed = (4 - len(base64_string) % 4) % 4
        if padding_needed:
            base64_string += "=" * padding_needed
        return base64_string
