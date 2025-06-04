from redis.asyncio import Redis
from .Base import BaseService, cache
from typing import Optional
from ..models.YouTube import YouTubeChannel, YouTubeFeed
from .._impl.exceptions import InvalidUser


class YouTubeService(BaseService):
    def __init__(self: "YouTubeService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__("YouTube", self.redis, self.ttl)

    @cache()
    async def get_channel(self: "YouTubeService", url: str) -> YouTubeChannel:
        if url.startswith("https://"):
            try:
                channel = await YouTubeChannel.from_url(url)
                return channel
            except Exception:
                raise InvalidUser(f"No YouTube Channel found for `{url}`")
        else:
            try:
                return await YouTubeChannel.from_id(url)
            except Exception:
                raise InvalidUser(f"No YouTube Channel found for `{url}`")

    async def get_feed(self, youtube_id: str) -> YouTubeFeed:
        feed = await YouTubeFeed.from_id(youtube_id)
        return feed
