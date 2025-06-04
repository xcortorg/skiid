from typing import List, Optional

import aiohttp
from discord.ext import commands
from pydantic import BaseModel
from tools.helpers import AkariContext


class TikTok(BaseModel):
    """
    Model for tiktok user
    """

    username: str
    nickname: Optional[str]
    avatar: str
    bio: str
    badges: List[str]
    url: str
    followers: int
    following: int
    hearts: int


class TikTokUser(commands.Converter):
    async def convert(self, ctx: AkariContext, argument: str) -> TikTok:
        async with ctx.typing():
            async with aiohttp.ClientSession(
                headers={"api-key": ctx.bot.akari_api}
            ) as cs:
                async with cs.get(
                    "https://api.akari.bot/tiktok", params={"username": argument}
                ) as r:
                    if r.status != 200:
                        raise commands.BadArgument("Couldn't get this tiktok page")

                    data = await r.json()
                    badges = []

                    if data.get("private"):
                        badges.append("🔒")

                    if data.get("verified"):
                        badges.append("<:verified:1233237074128277637>")

                    data["badges"] = badges
                    return TikTok(**data)
