from typing import Optional

import aiohttp
from discord.ext import commands
from pydantic import BaseModel
from tools.helpers import AkariContext


class Snapchat(BaseModel):
    """
    Model for snapchat profile
    """

    username: str
    display_name: str
    snapcode: str
    bio: Optional[str]
    avatar: str
    url: str


class SnapUser(commands.Converter):
    async def convert(self, ctx: AkariContext, argument: str) -> Snapchat:
        async with aiohttp.ClientSession(headers={"api-key": ctx.bot.akari_api}) as cs:
            async with cs.get(
                "https://api.akari.bot/snapchat", params={"username": argument}
            ) as r:
                if r.status != 200:
                    raise commands.BadArgument(
                        f"Couldn't get information about **{argument}** (`{r.status}`)"
                    )

                return Snapchat(**(await r.json()))
