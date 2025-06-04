from .Base import BaseService, cache
from redis.asyncio import Redis
from typing import Optional, Any
from ..models.Kick.channel import KickChannel
from aiohttp import ClientSession
from loguru import logger
from orjson import JSONDecodeError
from .._impl.exceptions import InvalidUser
from asyncio import sleep

HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
    "Alt-Used": "kick.com",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/109.0",
}


class KickService(BaseService):
    def __init__(self: "KickService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("Kick", self.redis, self.ttl)

    @cache()
    async def get_channel_raw(self: "KickService", username: str, **kwargs: Any):
        async with ClientSession() as session:
            async with session.get(
                f"https://kick.com/api/v1/channels/{username}",
                headers=HEADERS,
                **kwargs,
            ) as response:
                if response.status == 403:
                    logger.info(
                        f"Cloudflare blocked us from getting {username}'s channel data, retrying in 1 second"
                    )
                    await sleep(1)
                    return await self.get_channel_raw(username, **kwargs)
                data = await response.read()
        return data

    async def get_channel(
        self: "KickService", username: str, **kwargs: Any
    ) -> Optional[KickChannel]:
        data = await self.get_channel_raw(username, **kwargs)
        try:
            if isinstance(data, bytes):
                data = KickChannel.parse_raw(data)
            else:
                data = KickChannel(**data)
        except JSONDecodeError:
            raise InvalidUser(
                f"No **{self.__class__.__name__.replace('Service', '')} User** found under username `{username}`"
            )
        return data
