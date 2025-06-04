from __future__ import annotations

from json import JSONDecodeError, loads
from typing import Optional
from loguru import logger
from bs4 import BeautifulSoup
from cashews import cache
from discord.ext.commands import CommandError
from pydantic import BaseModel, Field
from typing_extensions import Self

from extensions.social.models.tiktok import ClientSession
from discord.ext.commands import Context
cache.setup('mem://')
import random, string
from datetime import datetime
HEADERS = {
    "Referer": "https://www.tiktok.com/",
    "User-Agent": (
        f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(4, 10)))}-"
        f"{''.join(random.choices(string.ascii_lowercase, k=random.randint(3, 7)))}/"
        f"{random.randint(10, 300)} "
        f"({datetime.utcnow().replace(microsecond=0).timestamp()})"
    ),
}

COOKIES = {
    "tt_webid_v2": f"{random.randint(10 ** 18, (10 ** 19) - 1)}"
}

class Statistics(BaseModel):
    follower_count: int = Field(alias="followerCount")
    following_count: int = Field(alias="followingCount")
    heart_count: int = Field(alias="heart")
    video_count: int = Field(alias="videoCount")


class BasicUser(BaseModel):
    id: int
    sec_uid: str = Field(alias="secUid")
    username: str = Field(alias="uniqueId")
    full_name: str = Field(alias="nickname")
    avatar_url: str = Field(alias="avatarThumb")
    biography: str = Field(alias="signature")

    def __str__(self) -> str:
        return self.full_name or self.username

    @property
    def _variable(self) -> str:
        return "tiktok"

    @property
    def url(self) -> str:
        return f"https://www.tiktok.com/@{self.username}"


class User(BasicUser):
    is_verified: bool = Field(alias="verified")
    is_private: bool = Field(alias="privateAccount")
    statistics: Statistics = Field(alias="stats")

    @classmethod
    @cache(ttl="6h")
    async def fetch(cls, username: str) -> Optional[Self]:
        """
        Fetches a user's profile.
        """

        username = username.strip("@")
        async with ClientSession() as session:
            async with session.get(
                f"https://www.tiktok.com/@{username}", proxy="http://127.0.0.1:1137", headers = HEADERS, cookies = COOKIES
            ) as resp:
                if not resp.ok:
                    return None

                data = await resp.text()
                soup = BeautifulSoup(data, "lxml")

                script = soup.find("script", id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
                if not script:
                    return False
                try:
                    user = loads(script.contents[0])["__DEFAULT_SCOPE__"][
                        "webapp.user-detail"
                    ]["userInfo"]
                except (JSONDecodeError, KeyError):
                    return True

                return cls(
                    **user,
                    **user["user"],
                )

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        async with ctx.typing():
            _ = await cls.fetch(argument)
            if not isinstance(_, bool) and _:
                return _
            else:
                logger.info(f"tiktok lookup got type {_}")

        raise CommandError("No **TikTok user** found with that name!")
