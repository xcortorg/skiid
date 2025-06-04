import re
from json import JSONDecodeError, loads
from typing import Optional

from aiohttp import ClientSession
from discord import Color
from discord.ext.commands import CommandError
from pydantic import BaseModel, Field
from typing_extensions import Self

from core.client.context import Context


class Avatar(BaseModel):
    url: Optional[str] = Field(..., alias="image_url")
    accent_color: str

    @property
    def color(self) -> Color:
        return Color(int(self.accent_color.strip("#"), 16))


class Model(BaseModel):
    username: str
    display_name: str
    country_code: Optional[str] = "Unknown"
    avatar: Avatar

    @property
    def url(self) -> str:
        return f"https://cash.app/${self.username}"

    @property
    def qr_code(self) -> str:
        return f"https://cash.app/qr/${self.username}?size=288&margin=0"

    @classmethod
    async def fetch(
        cls,
        session: ClientSession,
        username: str,
    ) -> Optional[Self]:
        async with session.get(f"https://cash.app/{username}") as response:
            if not response.ok:
                return None

            data = await response.text()
            match = re.search(r"var profile = ({.*?});", data, re.DOTALL)
            if not match:
                return None

            try:
                profile = loads(match[1])
            except JSONDecodeError:
                return None

            return cls(
                username=username,
                display_name=profile["display_name"],
                country_code=profile["country_code"],
                avatar=Avatar(**profile["avatar"]),
            )

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        async with ctx.typing():
            if user := await cls.fetch(ctx.bot.session, argument):
                return user

        raise CommandError("No **CashApp user** found with that name!")
