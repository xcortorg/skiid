from discord.ext.commands import CommandError, Cog, group, command, has_permissions
from discord import (
    Client,
    Embed,
    Color,
    File,
    User,
    Member,
    Guild,
    TextChannel,
    Message,
    Thread,
)
from lib.services.YouTube.main import extract, download
from lib.services.compress import compress
from os import remove
from tools import timeit
from aiohttp import ClientSession
from io import BytesIO
from var.variables import INSTAGRAM_POST
from lib.patch.context import Context
from asyncio import ensure_future
from .util import post_to_message
from typing import List
from unidecode_rs import decode as unidecode_rs
from DataProcessing.services.TT.models.post import TikTokPostResponse  # type: ignore
from loguru import logger
from lib.managers.repost import RepostManager
from .feeds import FEEDS, Feed

import re


async def to_message(self: TikTokPostResponse, ctx: Context):
    embed = Embed(
        description=unidecode_rs(
            self.itemInfo.itemStruct.contents[0].desc
            if self.itemInfo.itemStruct.contents
            else ""
        ),
        color=Color.from_str("#00001"),
    )
    embed.set_author(
        name=self.itemInfo.itemStruct.author.uniqueId,
        icon_url=self.itemInfo.itemStruct.author.avatarLarger,
    )
    footer_text = f"""❤️ {self.itemInfo.itemStruct.statsV2.diggCount.humanize() if self.itemInfo.itemStruct.statsV2.diggCount else 0} 👀 {self.itemInfo.itemStruct.statsV2.playCount.humanize() if self.itemInfo.itemStruct.statsV2.playCount else 0} 💬 {self.itemInfo.itemStruct.statsV2.commentCount.humanize() if self.itemInfo.itemStruct.statsV2.commentCount else 0} ∙ {str(ctx.author)}"""
    if self.itemInfo.itemStruct.imagePost:
        embeds = []
        total = len(self.itemInfo.itemStruct.imagePost.images)
        for i, image in enumerate(self.itemInfo.itemStruct.imagePost.images, start=1):
            e = embed.copy()
            e.set_footer(
                text=f"{footer_text} ∙ Page {i}/{total}",
                icon_url="https://seeklogo.com/images/T/tiktok-icon-logo-1CB398A1BD-seeklogo.com.png",
            )
            e.set_image(url=image.imageURL)
            embeds.append(e)
        return await ctx.paginate(embeds)
    else:
        if self.itemInfo.itemStruct.video:
            embed.set_footer(
                text=footer_text,
                icon_url="https://seeklogo.com/images/T/tiktok-icon-logo-1CB398A1BD-seeklogo.com.png",
            )
            logger.info(self.itemInfo.itemStruct.video.playAddr)
            async with ClientSession() as session:
                async with session.get(
                    self.itemInfo.itemStruct.video.playAddr,
                    **await ctx.bot.services.tiktok.tt.get_tiktok_headers(),
                ) as response:
                    data = await response.read()
            file = File(fp=BytesIO(data), filename="tiktok.mp4")
            return await ctx.send(file=file, embed=embed)
        else:
            return await ctx.fail("TikTok returned **malformed** content")


TikTokPostResponse.to_message = to_message


class Events(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.reposter = RepostManager(self.bot)
        self.tiktok_regexes = [
            re.compile(
                r"(?:http\:|https\:)?\/\/(?:www\.)?tiktok\.com\/@.*\/(?:photo|video)\/\d+"
            ),
            re.compile(
                r"(?:http\:|https\:)?\/\/(?:www|vm|vt|m).tiktok\.com\/(?:t/)?(\w+)"
            ),
        ]
        self.feeds: List[Feed] = []

    async def cog_load(self):
        for feed in FEEDS:
            self.feeds.append(feed(self.bot))

    async def cog_unload(self):
        for feed in self.feeds:
            await feed.stop()

    @Cog.listener("on_media_repost")
    async def repost_check(self, ctx: Context):
        await self.reposter.repost(ctx.message)
