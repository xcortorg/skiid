from __future__ import annotations

from typing import List, Optional
from typing_extensions import Self
from pydantic import BaseModel
import re
from aiohttp import ClientSession
from loguru import logger as log

CHANNEL_LOOKUPS = {
    "BY_ID": "https://pipedapi.kavin.rocks/channel/",
    "BY_USERNAME": "https://pipedapi.kavin.rocks/c/",
}

REGEXES = [
    re.compile(r"channel/([a-zA-Z0-9_-]+)"),  # Matches channel URLs
    re.compile(r"c/([a-zA-Z0-9_-]+)"),  # Matches custom URLs (short form)
    re.compile(r"user/([a-zA-Z0-9_-]+)"),  # Matches legacy user URLs
    re.compile(r"@([a-zA-Z0-9_-]+)"),  # Matches YouTube handles
]


class RelatedStream(BaseModel):
    url: Optional[str] = None
    type: Optional[str] = None
    title: Optional[str] = None
    thumbnail: Optional[str] = None
    uploaderName: Optional[str] = None
    uploaderUrl: Optional[str] = None
    uploaderAvatar: None = None
    uploadedDate: Optional[str] = None
    shortDescription: Optional[str] = None
    duration: Optional[int] = None
    views: Optional[int] = None
    uploaded: Optional[int] = None
    uploaderVerified: Optional[bool] = None
    isShort: Optional[bool] = None


class Tab(BaseModel):
    name: Optional[str] = None
    data: Optional[str] = None


class YouTubeChannel(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    avatarUrl: Optional[str] = None
    bannerUrl: Optional[str] = None
    description: Optional[str] = None
    nextpage: Optional[str] = None
    subscriberCount: Optional[int] = None
    verified: Optional[bool] = None
    relatedStreams: Optional[List[RelatedStream]] = None
    tabs: Optional[List[Tab]] = None

    @property
    def url(self) -> str:
        return f"https://youtube.com/channel/{self.id}"

    @classmethod
    async def from_url(cls, url: str) -> Optional[Self]:
        snowflake = None
        for r in REGEXES:
            if match := r.search(url):
                snowflake = match.group(1)
                log.info(f"got match {match} for URL {url}")
            else:
                log.info(f"couldn't get a match for URL {url}")
        if not snowflake:
            raise ValueError("Invalid channel snowflake provided")
        if snowflake.startswith("UC"):
            url = CHANNEL_LOOKUPS["BY_ID"]
        else:
            url = CHANNEL_LOOKUPS["BY_USERNAME"]
        async with ClientSession() as session:
            async with session.get(f"{url}{snowflake}") as response:
                data = await response.read()
        return cls.parse_raw(data)

    @classmethod
    async def from_id(cls, channel_id: str) -> Optional[Self]:
        async with ClientSession() as session:
            async with session.get(
                f"{CHANNEL_LOOKUPS['BY_ID']}{channel_id}"
            ) as response:
                data = await response.read()
        return cls.parse_raw(data)
