import humanize
import asyncio

from .base import Reposter
from discord import Client, Embed, File, Message, Color
from unidecode_rs import decode as unidecode_rs
from lib.patch.context import Context
from aiohttp import ClientSession
from io import BytesIO
from lib.classes.builtins import get_error
from DataProcessing.services.TT.models.post import TikTokPostResponse  # type: ignore
from ..regexes import TIKTOK


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
            async with ClientSession() as session:
                async with session.get(
                    self.itemInfo.itemStruct.video.playAddr,
                    **await ctx.bot.services.tiktok.tt.get_tiktok_headers(),
                ) as response:
                    data = await response.read()
            file = File(fp=BytesIO(data), filename="tiktok.mp4")
            await ctx.send(file=file, embed=embed)
        else:
            await ctx.fail("TikTok returned **malformed** content")
        return await ctx.message.delete()


TikTokPostResponse.to_message = to_message


class TikTok(Reposter):
    def __init__(self, bot: Client):
        super().__init__(bot, name="TikTok")
        self.log = self.logger
        self.lock: asyncio.Lock = asyncio.Lock()

    async def download(self, url: str) -> tuple:
        try:
            post = await self.bot.services.tiktok.fetch_post(url)
            return True, post
        except Exception as e:
            return False, e

    async def create_task(self, ctx: Context, result: str) -> Message:
        self.posted += 1
        async with self.lock:
            status, post = await self.download(result)
            if not status:
                self.log.error(
                    f"Failed to download post {result} with error {get_error(post)}"
                )
                return await ctx.fail(
                    f"**TikTok** returned a malformed response for [this post]({result})"
                )
            return await post.to_message(ctx)

    async def repost(self, message: Message):
        ctx = await self.bot.get_context(message)
        key = self.make_key(
            f"tiktok-{message.guild.id}-{message.channel.id}-{message.id}"
        )

        def task_done_callback(future):
            self.tasks.pop(key, None)

        async with self.locks[key]:
            for content in message.content.split():
                for i, regex in enumerate(TIKTOK, start=1):
                    if match := regex.match(content):
                        task = asyncio.create_task(
                            self.create_task(ctx, str(match.string))
                        )
                        task.add_done_callback(task_done_callback)
                        self.tasks[key] = task
