from io import BytesIO
from secrets import token_urlsafe
from textwrap import shorten

from core.client.context import Context
from core.Mono import Mono
from discord import Embed, File, Message
from extensions.socials.reposters.base import Information, Reposter


class YouTube(Reposter):
    def __init__(self, bot: Mono):
        super().__init__(
            bot,
            name="YouTube",
            regex=[
                r"(?:http(?:s)?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/shorts\/)([a-zA-Z0-9_-]+)"
            ],
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
            text=f"✨ {data.view_count or 0:,} 💬 {data.comment_count or 0:,} - {ctx.author.display_name}",
            icon_url="https://imgur.com/prFi4Bl.png",
        )

        return await ctx.send(
            embed=embed if ctx.settings.reposter_embed else None,
            file=File(
                buffer,
                filename=f"{self.name}{token_urlsafe(6)}.{data.ext}",
            ),
            no_reference=ctx.settings.reposter_delete,
        )
