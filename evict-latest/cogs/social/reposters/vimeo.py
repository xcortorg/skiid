from io import BytesIO
from secrets import token_urlsafe
from typing import Optional
from discord import File, Message
from tools.handlers.downloader import create_downloader
from cogs.social.reposters.base import Reposter
from main import Evict
from core.client.context import Context


class Vimeo(Reposter):
    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="Vimeo",
            regex=[
                r"(?:https?://)?(?:www\.)?vimeo\.com/(?:channels/(?:\w+/)?|groups/(?:[^/]+/)*|)(\d+)",
                r"(?:https?://)?player\.vimeo\.com/video/(\d+)",
            ],
        )
        self.downloader = create_downloader()

    async def fetch(self, url: str) -> Optional[dict]:
        filename, embed = None, None
        try:
            result = await self.downloader.download(url)
            if result is not None:
                filename, embed = result
                return {"filename": filename, "embed": embed}
            else:
                raise Exception("Download returned no result")
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
