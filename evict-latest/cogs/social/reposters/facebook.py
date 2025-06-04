from datetime import datetime
from io import BytesIO
from secrets import token_urlsafe
from textwrap import shorten
from typing import List, Optional
from discord import Embed, File, Message
from pydantic import BaseModel

from cogs.social.reposters.base import Reposter
from main import Evict
from core.client.context import Context
from tools.handlers.downloader import create_downloader


class Information(BaseModel):
    id: str
    title: Optional[str]
    uploader: str
    uploader_url: str
    created_at: datetime
    like_count: int
    share_count: int
    comment_count: int
    url: Optional[str]
    thumbnail: Optional[str]

    @property
    def webpage_url(self) -> str:
        return f"https://facebook.com/{self.id}"


class Facebook(Reposter):
    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="Facebook",
            regex=[
                r"(?:https?://)?(?:www\.)?facebook\.com/(?:video/)?(?:\w+/videos/|watch/\?v=)(\d+)",
                r"(?:https?://)?(?:www\.)?fb\.watch/(\w+)",
            ],
        )
        self.downloader = create_downloader()

    async def fetch(self, url: str) -> Optional[dict]:
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
