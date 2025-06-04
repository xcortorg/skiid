from datetime import datetime
from io import BytesIO
from secrets import token_urlsafe
from typing import Optional
from pydantic import BaseModel
import logging
from discord import File, Message, Embed
import aiofiles

from cogs.social.reposters.base import Reposter, Information
from main import Evict
from core.client.context import Context

log = logging.getLogger("evict.reposters.youtube")

class YouTubeStats(BaseModel):
    likes: int = 0
    views: int = 0
    comments: int = 0

class YouTubeMetadata(BaseModel):
    title: str
    uploader: str
    stats: YouTubeStats
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    description: Optional[str] = None
    uploadDate: Optional[str] = None
    quality: Optional[str] = None

class YouTubeInfo(Information):
    class Config:
        arbitrary_types_allowed = True

    success: bool
    type: str
    url: Optional[str] = None
    title: Optional[str] = None
    stats: Optional[dict] = None
    fileInfo: Optional[dict] = None

class Youtube(Reposter):
    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="YouTube",
            regex=[
                r"(?:https?://)?(?:www\.|m\.)?youtu(?:be\.com/watch\?v=|\.be/)([\w\-_]+)(?:\S+)?",
                r"(?:https?://)?(?:www\.|m\.)?youtube(?:\.com/shorts/)([^&\n?]+)",
            ],
        )

    async def fetch(self, url: str) -> Optional[YouTubeInfo]:
        try:
            log.info(f"[YouTube] Attempting to fetch: {url}")
            
            response = await self.bot.session.post(
                "http://localhost:7700/download",
                headers={"Authorization": "r2aq4t9ma69OiC51t"},
                json={"url": url}
            )
            
            log.info(f"[YouTube] API Response Status: {response.status}")
            data = await response.json()
            log.info(f"[YouTube] API Response Data: {data}")
            
            return YouTubeInfo(**data)

        except Exception as e:
            log.error(f"[YouTube] Download failed: {str(e)}")
            raise

    async def dispatch(self, ctx: Context, data: YouTubeInfo) -> Optional[Message]:
        log.info(f"[YouTube] Dispatching content type: {data.type}")
        
        if not data.success:
            return await ctx.warn("Failed to process YouTube content")

        if data.fileInfo and data.fileInfo.get('outputPath'):
            filename = data.fileInfo['fileName'] if data.fileInfo.get('fileName') else f"EvictYouTube{token_urlsafe(4)}.mp4"
            return await ctx.send(
                file=File(
                    data.fileInfo['outputPath'],
                    filename=filename
                ),
                no_reference=ctx.settings.reposter_delete,
            )
