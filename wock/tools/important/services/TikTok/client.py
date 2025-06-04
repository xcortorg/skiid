import re
from logging import getLogger
from typing import Any, Dict, List, Optional, Tuple, Union

import aiohttp
from discord.http import iteration  # type: ignore
from TikTokApi import TikTokApi as TikTokAPI  # type: ignore
from typing_extensions import Self  # type: ignore

from .models import OldVideo, User, UserFeed, Video

logger = getLogger(__name__)
import asyncio
from functools import wraps

from aiohttp import ClientSession  # type: ignore

try:
    from rival_tools import lock, ratelimit  # type: ignore
except ModuleNotFoundError:
    from tools import lock, ratelimit

from dataclasses import dataclass

from cashews import cache  # type: ignore

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 "
    "Safari/537.36"
)

SEC_CH_UA = '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"'

HEADERS = {
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Content-Type": "text/plain;charset=UTF-8",
    "Dnt": "1",
    "Origin": "https://www.douyin.com",
    "Referer": "https://www.douyin.com/",
    "Sec-Ch-Ua": SEC_CH_UA,
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Windows"',
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "cross-site",
    "User-Agent": DEFAULT_USER_AGENT,
}


@dataclass
class File:
    name: str
    extension: str


@dataclass
class Asset:
    url: str
    data: bytes
    file: File


cache.setup("mem://")


def _cache(key_pattern: str, ttl: Union[int, str]):
    if isinstance(ttl, int):
        ttl = f"{int(ttl/60)}m"

    def decorator(func):
        def wrapped_func(self, *args, **kwargs):
            if self.cached.get(func.__name__, False):
                # Apply the cache decorator if caching is enabled

                cached_func = cache_(ttl=ttl, key=key_pattern)(func)
                return cached_func(self, *args, **kwargs)
            else:
                # Call the function directly if caching is not enabled
                return func(self, *args, **kwargs)

        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            if self.cached.get(func.__name__, False):
                # Apply the cache decorator if caching is enabled
                cached_func = cache_(ttl=ttl, key=key_pattern)(func)
                return await cached_func(self, *args, **kwargs)
            else:
                # Call the function directly if caching is not enabled
                return await func(self, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return wrapper
        else:
            return wrapped_func

    return decorator


tiktok_video1 = re.compile(
    r"(?:http\:|https\:)?\/\/(?:www\.)?tiktok\.com\/@.*\/(?:photo|video)\/\d+"
)
tiktok_video2 = re.compile(
    r"(?:http\:|https\:)?\/\/(?:www|vm|vt|m).tiktok\.com\/(?:t/)?(\w+)"
)


def is_url(var: str) -> bool:
    if tiktok_video1.match(var):
        return True  # type: ignore
    if tiktok_video2.match(var):
        return True  # type: ignore
    return False


def format_tokens(t: Union[List[str], str]) -> List[str]:
    if isinstance(t, list):
        return t
    else:
        return [t]


class TikTokClient:
    def __init__(
        self, ms_tokens: Union[List[str], str], sessions: int, sleep_after: int
    ):
        self.ms_tokens = format_tokens(ms_tokens)
        self.sessions = sessions
        self.sleep_after = sleep_after
        self.storage = dict()
        self.clients = None
        self.cached = {
            "get_video": True,
            "get_asset": False,
            "get_user": True,
            "get_user_feed": True,
        }  # this is for disabling caching of data if needed (i wouldn't personally unless its get_asset)

    def get_extension(self: Self, url: str) -> Tuple[str]:
        return url.split("/")[-1].split("?")[0].split(".")

    async def setup(self: Self) -> None:
        sessions = []
        for token in self.ms_tokens:
            session = TikTokAPI()
            await session.create_sessions(
                ms_tokens=[token],
                num_sessions=self.sessions,
                sleep_after=self.sleep_after,
            )
            self.storage[token] = session
            sessions.append(session)
        self.clients = iteration(sessions)

    async def check(self: Self):
        if not self.clients:
            await self.setup()
        return

    async def get_asset(self: Self, url: str) -> Optional[Asset]:
        """Gets an asset class that can be reused internally and cached if wanted"""
        kwargs = {"url": url, "file": {}}
        async with ClientSession() as session:
            async with session.get(url, headers=HEADERS) as response:
                if response.status != 200:
                    raise TypeError(
                        f"response got a status of {response.status} for {url}"
                    )
                kwargs["data"] = await response.read()
        kwargs["file"]["filename"], kwargs["file"]["extension"] = self.get_extension(
            url
        )
        return Asset(**kwargs)

    @cache(key="tiktok:user:{username}", ttl=1500)
    async def get_user(self: Self, username: str) -> Optional[User]:
        await self.check()
        session = next(self.clients)

        @ratelimit("tiktok_request:{session}", 2, 5, True)
        @lock("tiktok_request:{session}")
        async def pull(session: TikTokAPI, username: str):
            user = session.user(username)
            if data := await user.info():
                return data
            else:
                return None

        data = await pull(session, username)
        return User(**data)

    @cache(key="tiktok:feed:{username}", ttl=300)
    async def get_user_feed(
        self: Self, username: str, count: int
    ) -> Optional[UserFeed]:
        await self.check()
        session = next(self.clients)

        @ratelimit("tiktok_request:{session}", 2, 5, True)
        @lock("tiktok_request:{session}")
        async def pull(session: TikTokAPI, username: str, count: int):
            user = session.user(username)
            videos = [v async for v in user.videos(count=count)]
            return videos

        data = await pull(session, username, count)
        return UserFeed(**data)

    async def get_id(self: Self, url: str) -> str:
        if "tiktok.com/@" not in url:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    url = str(response.url)
        return url.split("?")[0].split("/")[-1]

    @cache(key="tiktok:video:{url}", ttl=1500)
    async def get_video(
        self: Self, url: str, with_obj: bool = True
    ) -> Optional[Union[OldVideo, Tuple[OldVideo, Any]]]:
        video_id = await self.get_id(url)
        params = {
            "iid": "7318518857994389254",
            "device_id": "7318517321748022790",
            "version_code": "300904",
            "aweme_id": video_id,
            "channel": "googleplay",
            "app_name": "musical_ly",
            "device_platform": "android",
            "device_type": "SM-ASUS_Z01QD",
            "os_version": "9",
        }
        async with aiohttp.ClientSession() as session:
            async with session.request(
                "OPTIONS",
                "https://api22-normal-c-alisg.tiktokv.com/aweme/v1/feed/",
                params=params,
            ) as response:
                data = await response.json()
        try:
            video = OldVideo(**data)
            if int(video.aweme_list[0].aweme_id) is not int(video_id):
                return None
        except Exception:
            return None
