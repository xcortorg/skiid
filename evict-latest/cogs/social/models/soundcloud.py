from __future__ import annotations

from datetime import datetime
from logging import getLogger
from typing import List, Optional

from aiohttp import ClientSession
from discord.ext.commands import CommandError
from pydantic import BaseModel, Field
from typing_extensions import Self
from yarl import URL

from config import AUTHORIZATION
from core.client.context import Context

log = getLogger("evict/soundcloud")


class Track(BaseModel):
    id: int
    title: str
    plays: int = Field(..., alias="playback_count")
    created_at: datetime
    artwork_url: str
    url: str = Field(..., alias="permalink_url")
    user: "User"

    def __str__(self) -> str:
        return self.title

    @property
    def image_url(self) -> str:
        return self.artwork_url


class User(BaseModel):
    id: int
    username: str
    permalink: str
    created_at: Optional[datetime]
    track_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    followings_count: Optional[int] = 0
    avatar_url: str

    def __str__(self) -> str:
        return self.username

    @property
    def url(self) -> str:
        return f"https://soundcloud.com/{self.permalink}"

    @classmethod
    async def tracks(
        cls,
        session: ClientSession,
        user_id: int,
    ) -> List[Track]:
        async with session.get(
            URL.build(
                scheme="https",
                host="api-v2.soundcloud.com",
                path=f"/users/{user_id}/tracks",
                query={
                    "limit": 20,
                    "offset": 0,
                },
            ),
            headers={
                "Authorization": AUTHORIZATION.SOUNDCLOUD,
            },
        ) as response:
            if not response.ok:
                log.debug(
                    "Soundcloud raised an exception for %r: %s",
                    user_id,
                    await response.text(),
                )
                return []

            data = await response.json()
            collection = data["collection"]
            return [Track(**track) for track in collection]

    @classmethod
    async def fetch(
        cls,
        session: ClientSession,
        username: str,
    ) -> Optional[Self]:
        async with session.get(
            URL.build(
                scheme="https",
                host="api-v2.soundcloud.com",
                path="/search/users",
                query={
                    "q": username,
                },
            ),
            headers={
                "Authorization": AUTHORIZATION.SOUNDCLOUD,
            },
        ) as response:
            if not response.ok:
                return None

            data = await response.json()
            collection = data["collection"]
            return cls(**collection[0])

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        async with ctx.typing():
            if user := await cls.fetch(ctx.bot.session, argument):
                return user

        raise CommandError("No **SoundCloud user** found with that name!")


Track.update_forward_refs()
