from datetime import datetime
from io import BytesIO
from secrets import token_urlsafe
from typing import Optional
from pydantic import BaseModel
import logging
from discord import File, Message, Embed

from cogs.social.reposters.base import Reposter, Information
from main import Evict
from core.client.context import Context

log = logging.getLogger("evict.reposters.instagram")

class InstagramMetadata(BaseModel):
    title: str
    stats: dict = {}  # Empty for now
    thumbnail: Optional[str] = None
    duration: Optional[float] = None

class InstagramInfo(Information):
    class Config:
        arbitrary_types_allowed = True

    success: bool
    type: str
    url: Optional[str] = None
    metadata: Optional[InstagramMetadata] = None
    fileInfo: Optional[dict] = None

class Instagram(Reposter):
    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="Instagram",
            regex=[
                r"(?:https?://)?(?:www\.)?(?:instagram\.com)/reel/([^\s/]+)",
            ],
        )
        log.info(f"Instagram reposter initialized with patterns: {self.regex}")

    async def fetch(self, url: str) -> Optional[InstagramInfo]:
        try:
            log.info(f"[Instagram] Attempting to fetch: {url}")
            
            response = await self.bot.session.post(
                "http://localhost:7700/download",
                headers={"Authorization": "r2aq4t9ma69OiC51t"},
                json={"url": url}
            )
            
            log.info(f"[Instagram] API Response Status: {response.status}")
            data = await response.json()
            log.info(f"[Instagram] API Response Data: {data}")
            
            return InstagramInfo(**data)

        except Exception as e:
            log.error(f"[Instagram] Download failed: {str(e)}")
            raise

    async def dispatch(self, ctx: Context, data: InstagramInfo) -> Optional[Message]:
        log.info(f"[Instagram] Dispatching content type: {data.type}")
        
        if not data.success:
            return await ctx.warn("Failed to process Instagram content")

        if data.url:
            async with self.bot.session.get(data.url) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to download video")
                
                video_data = await resp.read()
                return await ctx.send(
                    file=File(
                        BytesIO(video_data),
                        filename=f"Evict{self.name}{token_urlsafe(4)}.mp4",
                    ),
                    no_reference=ctx.settings.reposter_delete,
                )
