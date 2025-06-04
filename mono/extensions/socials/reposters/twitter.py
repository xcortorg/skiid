from io import BytesIO
from secrets import token_urlsafe
from textwrap import shorten

from core.client.context import Context
from core.Mono import Mono
from discord import Embed, File, Message
from extensions.socials.reposters.base import Information, Reposter


class Twitter(Reposter):
    def __init__(self, bot: Mono):
        super().__init__(
            bot,
            name="Twitter",
            regex=[
                r"\<?(https?://(twitter\.com|x\.com)/(?P<user>\w+)/status/(?P<id>\d+))\>?"
            ],
        )

    async def dispatch(
        self,
        ctx: Context,
        data: Information,
        buffer: BytesIO,
    ) -> Message:
        if not buffer:
            print(data.json(indent=4))

        embed = Embed(
            url=data.webpage_url,
            title=shorten(data.title or "", width=256),
        )
        embed.set_author(
            name=data.uploader or ctx.author.display_name,
            url=data.uploader_url,
        )
        embed.set_footer(
            text=f"💙 {data.like_count or 0:,} 💬 {data.comment_count or 0:,} - {ctx.author.display_name}",
            icon_url="https://i.imgur.com/thDm9LE.png",
        )

        return await ctx.send(
            embed=embed,
            file=File(
                buffer,
                filename=f"{self.name}{token_urlsafe(6)}.{data.ext}",
            ),
            no_reference=ctx.settings.reposter_delete,
        )
