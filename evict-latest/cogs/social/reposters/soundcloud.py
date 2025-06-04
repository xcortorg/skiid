from io import BytesIO
from secrets import token_urlsafe
from textwrap import shorten
from typing import Optional

from discord import Embed, File, Message
from pydantic import BaseModel
import logging

from cogs.social.reposters.base import Information, Reposter
from main import Evict
from core.client.context import Context

log = logging.getLogger("evict.reposters.youtube")


class FileInfo(BaseModel):
    fileName: str
    fileSize: int
    outputPath: str
    format: str

class SoundCloudInfo(Information):
    class Config:
        arbitrary_types_allowed = True

    success: bool
    type: str
    url: str
    fileInfo: FileInfo


class SoundCloud(Reposter):
    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="SoundCloud",
            regex=[
                r"(?:http\:|https\:)?\/\/(?:www\.)?soundcloud\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_-]+)(?:\?.*)?",
                r"(?:http\:|https\:)?\/\/(?:www\.)?soundcloud\.app\.goo\.gl\/([a-zA-Z0-9_-]+)",
                r"(?:http\:|https\:)?\/\/on.soundcloud\.com\/([a-zA-Z0-9_-]+)",
            ],
        )

    async def fetch(self, url: str) -> Optional[SoundCloudInfo]:
        try:
            log.info(f"[SoundCloud] Attempting to fetch: {url}")
            
            async with self.bot.session.post(
                "http://localhost:7700/download",
                headers={"Authorization": "r2aq4t9ma69OiC51t"},
                json={"url": url}
            ) as response:
                log.info(f"[SoundCloud] API Response Status: {response.status}")
                data = await response.json()
                log.info(f"[SoundCloud] API Response Data: {data}")
                
                return SoundCloudInfo(**data)

        except Exception as e:
            log.error(f"[SoundCloud] Download failed: {str(e)}")
            raise

    async def dispatch(self, ctx: Context, data: SoundCloudInfo) -> Message:
        if not data.success:
            return await ctx.warn("Failed to process SoundCloud content")

        return await ctx.send(
            file=File(f"/root/socials/{data.fileInfo.outputPath}"),
            no_reference=ctx.settings.reposter_delete,
        )
