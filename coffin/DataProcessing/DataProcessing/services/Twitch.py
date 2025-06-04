from asyncio import ensure_future, sleep
from os import environ
from typing import Any

from aiohttp import ClientSession

from ..models.Twitch import Channel, ChannelResponse, Stream, StreamResponse
from .Base import BaseService, Optional, Redis, cache, logger

USER_URL = "https://api.twitch.tv/helix/users?login={}"
STREAM_URL = "https://api.twitch.tv/helix/streams?user_id={}"
AUTH_URL = "https://id.twitch.tv/oauth2/token?client_id={}&client_secret={}&grant_type=client_credentials"


class TwitchService(BaseService):
    def __init__(self: "TwitchService", redis: Redis, ttl: Optional[int] = 300):
        self.redis = redis
        self.ttl = ttl
        self.bearer = None
        super().__init__(self.redis, self.ttl)

    @property
    def client_id(self: "TwitchService") -> str:
        return environ.get("twitch_client_id")

    @property
    def client_secret(self: "TwitchService") -> str:
        return environ.get("twitch_client_secret")

    @property
    def base_headers(self: "TwitchService") -> dict:
        data = {"Client-Id": self.client_id}
        if self.bearer:
            data["Authorization"] = f"Bearer {self.bearer}"
        return data

    async def reauthorize(self):
        await sleep(86400 * 30)
        return await self.authorize()

    async def authorize(self: "TwitchService"):
        async with ClientSession() as session:
            async with session.request(
                "POST",
                AUTH_URL.format(self.client_id, self.client_secret),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as response:
                data = await response.json()
                self.bearer = data["access_token"]
                ensure_future(self.reauthorize())

    @cache()
    async def get_channel(self: "TwitchService", username: str, **kwargs: Any):
        """Get a channel's information from Twitch API."""
        if not self.bearer:
            await self.authorize()
        async with ClientSession() as session:
            async with session.get(
                USER_URL.format(username), headers=self.base_headers
            ) as response:
                data = await response.json()
        return ChannelResponse(**data)

    async def get_streams(
        self: "TwitchService",
        *,
        username: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        """Get a channel's streams from Twitch API."""
        if not self.bearer:
            await self.authorize()

        if username:
            user = await self.get_channel(username)
            user_id = user.channel.id

        async with ClientSession() as session:
            async with session.get(
                STREAM_URL.format(user_id), headers=self.base_headers
            ) as response:
                data = await response.json()
        return StreamResponse(**data)
