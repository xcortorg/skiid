from io import BytesIO
from secrets import token_urlsafe
import logging
import re
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
import discord
from discord import Message, File, Embed

from cogs.social.reposters.base import Reposter, Information
from main import Evict
from core.client.context import Context
import config

log = logging.getLogger("evict.reposters.tiktok")

class TikTokStats(BaseModel):
    likes: int = 0
    views: int = 0
    comments: int = 0
    shares: Optional[int] = 0

class TikTokInfo(Information):
    class Config:
        arbitrary_types_allowed = True

    success: bool
    type: str
    url: Optional[str] = None
    urls: Optional[List[str]] = None
    title: Optional[str] = None
    description: Optional[str] = None
    creator: Optional[str] = None
    creatorUrl: Optional[str] = None
    thumbnail: Optional[str] = None
    stats: Optional[TikTokStats] = None
    duration: Optional[int] = None
    uploadDate: Optional[str] = None

class TikTok(Reposter):
    def __init__(self, bot: Evict, add_listener: bool = True):
        super().__init__(
            bot,
            name="TikTok",
            regex=[
                r"https?://(?:vm|vt|www)\.tiktok\.com/\S+",
                r"https?://(?:www\.)?tiktok\.com/@[\w.-]+/photo/\d+",
            ],
            add_listener=add_listener,
        )
        log.info(f"TikTok reposter initialized with patterns: {self.regex}")

    def match(self, url: str) -> Optional[re.Match[str]]:
        for pattern in self.regex:
            if match := re.search(pattern, url):
                log.info(f"[TikTok] Matched URL: {url}")
                return match
        return None

    async def fetch(self, url: str) -> Optional[TikTokInfo]:
        try:
            log.info(f"[TikTok] Attempting to fetch: {url}")
            
            response = await self.bot.session.post(
                "http://localhost:7700/download",
                headers={"Authorization": "r2aq4t9ma69OiC51t"},
                json={"url": url}
            )
            
            log.info(f"[TikTok] API Response Status: {response.status}")
            data = await response.json()
            log.info(f"[TikTok] API Response Data: {data}")
            
            return TikTokInfo(**data)

        except Exception as e:
            log.error(f"[TikTok] Download failed: {str(e)}")
            raise

    async def dispatch(self, ctx: Context, data: TikTokInfo) -> Optional[Message]:
        log.info(f"[TikTok] Dispatching content type: {data.type}")
        
        if not data.success:
            return await ctx.warn("Failed to process TikTok content")

        title = data.description or data.title
        if title and len(title) > 100:
            title = title[:97] + "..."

        embed = Embed(
            title=title,
            url=ctx.message.content,
            timestamp=datetime.now(),
        )
        
        if data.creator:
            embed.set_author(
                name=data.creator,
                url=data.creatorUrl
            )

        if data.stats:
            embed.set_footer(
                text=f"❤️ {data.stats.likes:,} 👀 {data.stats.views:,} 💬 {data.stats.comments:,}"
            )

        if data.type == "video" and data.url:
            async with self.bot.session.get(data.url) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to download video")
                
                video_data = await resp.read()
                return await ctx.send(
                    embed=embed if ctx.settings.reposter_embed else None,
                    file=File(
                        BytesIO(video_data),
                        filename=f"Evict{self.name}{token_urlsafe(4)}.mp4",
                    ),
                    no_reference=ctx.settings.reposter_delete,
                )
        
        return await ctx.warn("Unsupported content type")

class ImagePaginator:
    def __init__(self, ctx: Context, embeds: List[Embed], urls: List[str]):
        self.ctx = ctx
        self.embeds = embeds
        self.urls = urls
        self.current = 0
        
    async def get_image(self, url: str) -> File:
        for _ in range(3):  
            try:
                async with self.ctx.bot.session.get(url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        return File(BytesIO(image_data), "image.jpg")
            except:
                continue
        raise ValueError("Failed to fetch image")
        
    async def start(self) -> Message:
        file = await self.get_image(self.urls[0])
            
        view = discord.ui.View()
        view.add_item(NavigateButton(self))
        view.add_item(PreviousButton(self))
        view.add_item(NextButton(self))
        view.add_item(CancelButton(self))
        
        self.message = await self.ctx.send(
            file=file,
            embed=self.embeds[0],
            view=view
        )
        return self.message

class NavigateButton(discord.ui.Button):
    def __init__(self, paginator: ImagePaginator):
        super().__init__(emoji=config.EMOJIS.PAGINATOR.NAVIGATE)
        self.paginator = paginator
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

class PreviousButton(discord.ui.Button):
    def __init__(self, paginator: ImagePaginator):
        super().__init__(emoji=config.EMOJIS.PAGINATOR.PREVIOUS)
        self.paginator = paginator
    
    async def callback(self, interaction: discord.Interaction):
        if self.paginator.current > 0:
            self.paginator.current -= 1
            file = await self.paginator.get_image(self.paginator.urls[self.paginator.current])
            
            await interaction.response.edit_message(
                attachments=[file],
                embed=self.paginator.embeds[self.paginator.current]
            )
        else:
            await interaction.response.defer()

class NextButton(discord.ui.Button):
    def __init__(self, paginator: ImagePaginator):
        super().__init__(emoji=config.EMOJIS.PAGINATOR.NEXT)
        self.paginator = paginator
    
    async def callback(self, interaction: discord.Interaction):
        if self.paginator.current < len(self.paginator.urls) - 1:
            self.paginator.current += 1
            file = await self.paginator.get_image(self.paginator.urls[self.paginator.current])
            
            await interaction.response.edit_message(
                attachments=[file],
                embed=self.paginator.embeds[self.paginator.current]
            )
        else:
            await interaction.response.defer()

class CancelButton(discord.ui.Button):
    def __init__(self, paginator: ImagePaginator):
        super().__init__(emoji=config.EMOJIS.PAGINATOR.CANCEL)
        self.paginator = paginator
    
    async def callback(self, interaction: discord.Interaction):
        await self.paginator.message.delete()
