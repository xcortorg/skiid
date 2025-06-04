import humanize
import asyncio

from .base import Reposter
from discord import Client, Embed, File, Message, Color
from unidecode_rs import decode as unidecode_rs
from lib.patch.context import Context
from lib.services.compress import compress
from aiohttp import ClientSession
from io import BytesIO
from tools import timeit
from typing import Optional
from lib.classes.builtins import get_error
from pydantic import BaseModel
from lib.services.YouTube.models.response import YouTubeVideo
from lib.services.YouTube.main import download
from os import remove
from var.variables import YOUTUBE_WILDCARD


class Download(BaseModel):
    time_taken: float
    post: Optional[YouTubeVideo] = None
    error: Optional[str] = None


class YouTube(Reposter):
    def __init__(self, bot: Client):
        super().__init__(bot, name="YouTube")
        self.log = self.logger
        self.lock: asyncio.Lock = asyncio.Lock()

    async def download(self, url: str) -> Download:
        try:
            async with timeit() as timer:
                post = await download(url, download=True)
                post = YouTubeVideo(**post)
            return Download(time_taken=timer.elapsed, post=post)
        except Exception as error:
            return Download(time_taken=timer.elapsed, error=get_error(error))

    async def create_task(self, ctx: Context, result: str):
        self.posted += 1
        async with self.lock:
            download = await self.download(result)
            if download.error:
                self.log.error(
                    f"Failed to download post {result} with error {download.error}"
                )
                return await ctx.fail(
                    f"**YouTube** returned a malformed response for [this post]({result})"
                )
            else:
                self.log.info(f"Downloaded post {result} in {download.time_taken:.2f}")
            post = download.post
            embed = (
                Embed(
                    description=f"[{post.title}]({result})",
                )
                .set_author(
                    name=f"{post.channel.name}",
                    icon_url=post.channel.avatar.url,
                    url=post.channel.url,
                )
                .set_footer(
                    text=f"💬 {post.statistics.comments.humanize()} 👀 {post.statistics.views.humanize()} ❤️ {post.statistics.likes.humanize()} ∙ {str(ctx.author)}"
                )
            )

            if post.filesize >= ctx.guild.filesize_limit:
                await compress(post.file, ctx.guild.filesize_limit)
            file = File(post.file)
            await ctx.channel.send(embed=embed, file=file)
            remove(post.file)
            return await ctx.message.delete()

    async def repost(self, message: Message):
        if not (match := YOUTUBE_WILDCARD.search(message.content)):
            return None
        ctx = await self.bot.get_context(message)
        key = self.make_key(
            f"youtube-{message.guild.id}-{message.channel.id}-{message.id}"
        )

        def task_done_callback(future):
            self.cache.pop(key, None)

        async with self.locks[key]:
            task = asyncio.create_task(self.create_task(ctx, str(match.string)))
            task.add_done_callback(task_done_callback)
            self.tasks[key] = task
