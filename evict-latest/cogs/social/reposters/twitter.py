from datetime import datetime
from io import BytesIO
from secrets import token_urlsafe
from discord import File, Message
from cogs.social.reposters.base import Reposter
from main import Evict
from core.client.context import Context
from tools.handlers.downloader import create_downloader


class Twitter(Reposter):
    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="Twitter",
            regex=[
                r"(?:https?://)?(?:www\.)?(twitter|x)\.com/(?:\w+)/status/(\d+)",
                r"(?:https?://)?(?:www\.)?x\.com/(?:\w+)/status/(\d+)",
            ],
        )
        self.downloader = create_downloader()

    async def fetch(self, url: str):
        try:
            filename, embed = await self.downloader.download(url)
            return {"filename": filename, "embed": embed}
        except Exception as e:
            raise Exception(f"Failed to download: {str(e)}")

    async def dispatch(
        self,
        ctx: Context,
        data: dict,
        buffer: BytesIO,
    ) -> Message:
        return await ctx.send(
            embed=data["embed"] if ctx.settings.reposter_embed else None,
            file=File(buffer, filename=f"{self.name}{token_urlsafe(6)}.mp4"),
            no_reference=ctx.settings.reposter_delete,
        )
