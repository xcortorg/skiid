from io import BytesIO
from secrets import token_urlsafe
from textwrap import shorten
from typing import Optional

from cashews import cache
from discord import Embed, File, Message

from cogs.social.reposters.base import Information, Reposter
from cogs.social.reposters.extraction import download
from main import swag
from tools import CACHE_ROOT
from tools.client import Context


class Instagram(Reposter):
    def __init__(self, bot: swag):
        super().__init__(
            bot,
            name="Instagram",
            regex=[
                r"\<?(https?://(?:www\.)?instagram\.com(?:/[^/]+)?/(?:p|tv|reel|reels)/(?P<post_id>[^/?#&]+))\>?"
            ],
        )

    @cache(ttl="1h", prefix="instagram")
    async def fetch(self, url: str) -> Optional[Information]:
        await CACHE_ROOT.mkdir(parents=True, exist_ok=True)
        return await download(url, download=True)

    async def dispatch(
        self,
        ctx: Context,
        data: Information,
        buffer: BytesIO,
    ) -> Optional[Message]:
        if not data.requested_downloads:
            return

        buffer = await data.requested_downloads[-1].read()
        embed = Embed(
            url=data.webpage_url,
            title=shorten(data.description or "", width=256),
        )
        embed.set_author(
            name=data.channel or ctx.author.display_name,
            url=f"https://instagram.com/{data.channel}",
        )
        embed.set_footer(
            text=f"💙 {data.like_count or 0:,} 💬 {data.comment_count or 0:,}",
            icon_url="https://i.imgur.com/U31ZVlK.png",
        )

        return await ctx.send(
            embed=embed if ctx.settings.reposter_embed else None,
            file=File(
                buffer,
                filename=f"{self.name}{token_urlsafe(6)}.{data.ext}",
            ),
            no_reference=ctx.settings.reposter_delete,
        )
