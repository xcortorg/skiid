import humanize
import asyncio

from .base import Reposter
from discord import Client, Embed, File, Message, Color
from ..regexes import INSTAGRAM_POST
from DataProcessing.models.Instagram.raw_post import InstagramPost, Item  # type: ignore
from lib.patch.context import Context
from typing import Union, List
from ext.socials.util import guess_extension, download_data
from datetime import timezone, datetime
from io import BytesIO
from lib.classes.builtins import get_error


def to_embed(self: Item, ctx: Context) -> Union[Embed, List[Embed]]:
    embed = Embed(description=self.caption.text, color=Color.from_str("#DD829B"))
    embed.set_author(
        name=f"{str(self.owner.full_name)} (@{str(self.owner.username)})",
        icon_url=self.owner.profile_pic_url
        or "https://eros.rest/static/Default_pfp.jpg",
    )
    icon_url = (
        "https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png"
    )
    footer_text = f"""❤️ {self.like_count.humanize() if self.like_count else 0} 👀 {self.play_count.humanize() if self.play_count else 0} 💬 {self.comment_count.humanize() if self.comment_count else 0} ∙ {str(ctx.author)} ∙ {humanize.naturaltime(datetime.datetime.fromtimestamp(self.taken_at, tz=timezone.utc), when = datetime.datetime.now(tz=timezone.utc))}"""
    if self.media_type == 8:
        embeds = []
        for i, media in enumerate(self.carousel_media, start=1):
            e = embed.copy()
            e.set_image(url=media.image_versions2.candidates[0].url)
            e.set_footer(
                text=f"{footer_text} ∙ Page {i}/{len(self.carousel_media)}",
                icon_url=icon_url,
            )
            embeds.append(e)
        return embeds
    elif self.media_type == 2:
        embed.set_footer(text=footer_text, icon_url=icon_url)
        return embed
    else:
        embed.set_image(url=self.image_versions2.candidates[0].url)
        embed.set_footer(text=footer_text, icon_url=icon_url)
        return embed


Item.to_embed = to_embed


async def post_to_message(ctx: Context, post: InstagramPost):
    post = post.items[0]
    embed = post.to_embed(ctx)
    if post.media_type == 2:
        video_url = post.video_versions[0].url
        path = await download_data(video_url)
        filename = guess_extension(video_url)
        file = File(fp=BytesIO(path), filename=filename.name)
        return await ctx.send(embed=embed, file=file)
    elif post.media_type == 1:
        return await ctx.send(embed=embed)
    elif post.media_type == 8:
        return await ctx.paginate(embed)
    else:
        return await ctx.fail("That post has no **MEDIA**")


class Instagram(Reposter):
    def __init__(self, bot: Client):
        super().__init__(bot, name="Instagram")
        self.log = self.logger
        self.lock: asyncio.Lock = asyncio.Lock()

    async def download(self, url: str) -> tuple:
        try:
            post = await self.bot.services.instagram.get_post(str(url))
            if post:
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
                    f"**Instagram** returned a malformed response for [this post]({str(result)})"
                )
            await post_to_message(ctx, post)
            return await ctx.message.delete()

    async def repost(self, message: Message):
        if not (results := INSTAGRAM_POST.findall(message.content)):
            return None
        ctx = await self.bot.get_context(message)
        key = self.make_key(
            f"instagram-{message.guild.id}-{message.channel.id}-{message.id}"
        )

        def task_done_callback(future):
            self.tasks.pop(key, None)

        async with self.locks[key]:

            for result in results:
                task = asyncio.create_task(self.create_task(ctx, str(result)))
                task.add_done_callback(task_done_callback)
                self.tasks[key] = task
