from io import BytesIO
from secrets import token_urlsafe
from textwrap import shorten

from discord import Embed, File, Message

from cogs.social.reposters.base import Information, Reposter
from main import swag
from tools.client import Context


class Medal(Reposter):
    def __init__(self, bot: swag):
        super().__init__(
            bot,
            name="Medal",
            regex=[r"https://medal\.tv/games/(\S*?)/clips/([^\s?]*)/"],
        )

    async def dispatch(
        self,
        ctx: Context,
        data: Information,
        buffer: BytesIO,
    ) -> Message:
        embed = Embed(
            url=data.webpage_url,
            title=shorten(data.title or "", width=256),
        )
        embed.set_author(
            name=data.uploader or ctx.author.display_name,
            url=data.uploader_url,
        )
        embed.set_footer(
            text=f"✨ {data.view_count or 0:,} 💙 {data.like_count or 0:,} - {ctx.author.display_name}",
            icon_url="https://i.imgur.com/XiGofVd.png",
        )

        return await ctx.send(
            embed=embed if ctx.settings.reposter_embed else None,
            file=File(
                buffer,
                filename=f"{self.name}{token_urlsafe(6)}.{data.ext}",
            ),
            no_reference=ctx.settings.reposter_delete,
        )
