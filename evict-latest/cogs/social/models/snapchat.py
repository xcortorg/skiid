from json import JSONDecodeError, loads
from typing import Optional

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from discord.ext.commands import CommandError
from pydantic import BaseModel
from typing_extensions import Self

from core.client.context import Context


class Model(BaseModel):
    username: str
    display_name: str
    description: Optional[str]
    snapcode_url: str
    bitmoji_url: Optional[str]

    @property
    def url(self) -> str:
        return f"https://story.snapchat.com/add/{self.username}"

    @classmethod
    async def fetch(
        cls,
        session: ClientSession,
        username: str,
    ) -> Optional[Self]:
        async with session.get(
            f"https://story.snapchat.com/add/{username}",
        ) as response:
            if not response.ok:
                return None

            data = await response.text()
            soup = BeautifulSoup(data, "lxml")

            script = soup.find("script", id="__NEXT_DATA__")
            if not script:
                return

            try:
                props = loads(script.text)["props"]["pageProps"]
            except (JSONDecodeError, KeyError):
                return

            profile = props["userProfile"]
            user = profile.get("publicProfileInfo") or profile.get("userInfo")
            if not user:
                return

            return cls(
                username=username,
                display_name=user.get("displayName") or user.get("title") or username,
                description=user.get("bio"),
                snapcode_url=user["snapcodeImageUrl"].replace("SVG", "PNG"),
                bitmoji_url=(
                    bitmoji.get("avatarImage").get("url")
                    if (bitmoji := user.get("bitmoji3d"))
                    else None
                ),
            )

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        async with ctx.typing():
            if user := await cls.fetch(ctx.bot.session, argument):
                return user

        raise CommandError("No **Snapchat user** found with that name!")
