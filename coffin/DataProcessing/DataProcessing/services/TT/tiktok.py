import os
import re
from random import choice
from typing import Any, List, Literal, Optional, Union

import yaml
from aiohttp import ClientSession, TCPConnector

from .handlers import (BaseCrawler, BogusManager, PostDetail,
                       TikTokAPIEndpoints, UserPost, UserProfile, get_aweme_id)
from .models import (TikTokPostResponse, TikTokUserFeedResponse,
                     TikTokUserProfileResponse)
from .models.post import BitrateInfoItem, PlayAddrrr

path = os.path.abspath(os.path.dirname(__file__))
if "\\" in str(path):
    splitting_char = "\\"
else:
    splitting_char = "/"

with open(f"{path}{splitting_char}config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)


class TikTok:
    def __init__(self, proxies: Optional[Union[str, List[str]]] = None):
        self.proxies = proxies
        self.last_request = None
        self.proxies = None

    async def get_sid(self, username: str, headers: dict):
        html = await self.request_url(
            "GET", f"https://www.tiktok.com/@{username}", headers=headers, as_text=True
        )
        secuid_match = re.search(r'"secUid":"(.*?)"', html)
        secUid = secuid_match.group(1) if secuid_match else None
        if not secUid:
            raise Exception(f"could not find the secuid of {username}")
        return secUid

    async def get_tiktok_headers(self, **kwargs):
        proxies = kwargs.get("proxy", kwargs.get("proxies", self.proxies))
        PROXY = None
        if proxies:
            if isinstance(proxies, str):
                PROXY = {"http": None, "https": None}
                PROXY["http"] = proxies
                PROXY["https"] = proxies
            else:
                PROXY = {"http": None, "https": None}
                proxy = choice(proxies)
                PROXY["http"] = proxy
                PROXY["https"] = proxy
        tiktok_config = config["TokenManager"]["tiktok"]
        kwargs = {
            "headers": {
                "User-Agent": tiktok_config["headers"]["User-Agent"],
                "Referer": tiktok_config["headers"]["Referer"],
                "Cookie": tiktok_config["headers"]["Cookie"],
            },
        }
        if PROXY:
            kwargs["proxies"] = PROXY
        return kwargs

    async def request_url(
        self,
        method: Literal["GET", "POST", "PUT", "HEAD", "DELETE", "PATCH", "OPTIONS"],
        url: str,
        headers: dict,
        **kwargs: Any,
    ):
        as_text = kwargs.pop("as_text", False)
        self.last_request = {"method": method, "url": url, "headers": headers, **kwargs}
        data = None
        async with ClientSession(connector=TCPConnector(verify_ssl=False)) as session:
            async with session.request(
                method, url, headers=headers, **kwargs
            ) as response:
                if response.content_type == "text/plain" or as_text is True:
                    data = await response.text()
                elif response.content_type.startswith(("image/", "video/", "audio/")):
                    data = await response.read()
                elif response.content_type == "text/html":
                    data = await response.read()
                elif response.content_type in (
                    "application/json",
                    "application/octet-stream",
                    "text/javascript",
                ):
                    data = await response.json(content_type=None)
                else:
                    raise AttributeError(
                        f"Content Type `{response.content_type}` wasn't handled"
                    )
        return data

    async def get_post(self, url: str) -> TikTokPostResponse:
        kwargs = await self.get_tiktok_headers()
        base_crawler = BaseCrawler(
            proxies=kwargs.get("proxies"), crawler_headers=kwargs["headers"]
        )
        async with base_crawler as crawler:
            itemId = await get_aweme_id(url)
            params = PostDetail(itemId=itemId)
            endpoint = BogusManager.model_2_endpoint(
                TikTokAPIEndpoints.POST_DETAIL,
                params.dict(),
                kwargs["headers"]["User-Agent"],
            )
            response = await crawler.fetch_get_json(endpoint)
        # try:
        #     for i, r in enumerate(response['itemInfo']['itemStruct']['video']['bitrateInfo'], start = 0):
        #         r["PlayAddr"] = PlayAddrrr(**r["PlayAddr"])
        #         d = BitrateInfoItem(**r)
        #         response['itemInfo']['itemStruct']['video']['bitrateInfo'][i] = d
        # except Exception as e:
        #     print(f"Error: {e}")
        return TikTokPostResponse(**response)

    async def get_profile(self, uniqueId: str) -> TikTokUserProfileResponse:
        kwargs = await self.get_tiktok_headers()
        base_crawler = BaseCrawler(
            proxies=kwargs.get("proxies"), crawler_headers=kwargs["headers"]
        )
        secUid = await self.get_sid(uniqueId, kwargs["headers"])
        async with base_crawler as crawler:
            params = UserProfile(secUid=secUid, uniqueId=uniqueId)
            endpoint = BogusManager.model_2_endpoint(
                TikTokAPIEndpoints.USER_DETAIL,
                params.dict(),
                kwargs["headers"]["User-Agent"],
            )
            response = await crawler.fetch_get_json(endpoint)
        return TikTokUserProfileResponse(**response)

    async def get_posts(
        self, uniqueId: str, cursor: int = 0, count: int = 35, coverFormat: int = 2
    ) -> TikTokUserFeedResponse:
        kwargs = await self.get_tiktok_headers()
        secUid = await self.get_sid(uniqueId, kwargs["headers"])
        base_crawler = BaseCrawler(proxies=None, crawler_headers=kwargs["headers"])
        async with base_crawler as crawler:
            params = UserPost(
                secUid=secUid, cursor=cursor, count=count, coverFormat=coverFormat
            )
            endpoint = BogusManager.model_2_endpoint(
                TikTokAPIEndpoints.USER_POST,
                params.dict(),
                kwargs["headers"]["User-Agent"],
            )
            response = await crawler.fetch_get_json(endpoint)
        return TikTokUserFeedResponse(**response)
