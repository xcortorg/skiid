#
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import BytesIO
from random import uniform
from typing import Any, Dict, List, Optional, Union, cast

from aiohttp import ClientSession
from DataProcessing.services.TT.models.feed import TikTokPost
from discord import Client, Color, Embed, File
from loguru import logger
from unidecode_rs import decode as unidecode_rs

from .base import BaseRecord, Feed


class Record(BaseRecord):
    username: str


class TikTok(Feed):
    def __init__(self, bot: Client):
        super().__init__(
            bot,
            name="TikTok",
        )
        self.log = None

    async def get_records(self) -> Dict[int, List[Record]]:
        records = cast(
            List[Record],
            await self.bot.db.fetch(
                """
                SELECT *
                FROM feeds.tiktok
                """,
            ),
        )

        result: Dict[int, List[Record]] = defaultdict(list)
        for record in records:
            result[record["username"]].append(record)

        return result

    async def get_posts(self, username: str, records: List[Record]):
        shifted = datetime.now(tz=timezone.utc) - timedelta(minutes=62)
        shifted_ts = shifted.timestamp()
        for i in range(10):
            try:
                posts = await self.bot.services.tiktok.fetch_feed(username)
                break
            except Exception as error:
                if i == 9:
                    raise error
                else:
                    await asyncio.sleep(10)

        for post in posts.itemList:
            logger.info(f"{post.createTime} - {int(shifted_ts)}")
            if post.createTime >= int(shifted_ts):
                if await self.redis.sismember(self.key, str(post.id)):
                    logger.info(f"{post.id} has already been posted, skipping it...")
                    continue
                self.bot.loop.create_task(self.dispatch(post, records))
                self.posted += 1

        self.log.info(f"Successfully dispatched {self.posted} tiktok posts")

    async def dispatch(self, post: TikTokPost, records: List[Record]):

        async def send(embeds: List[Embed], record: Record, *, file: bytes = None):
            if not (guild := self.bot.get_guild(record.guild_id)):
                return
            if not (channel := guild.get_channel(record.channel_id)):
                return
            if not self.can_post(channel):
                return
            kwargs = {}
            if file:
                kwargs["file"] = File(fp=BytesIO(file), filename="tiktok.mp4")
            return await channel.send(embeds=embeds, **kwargs)

        kw = {}
        embed = Embed(
            title="New Post",
            description=unidecode_rs(post.desc or "No Description Provided"),
            color=Color.from_str("#000001"),
        )
        footer_text = f"""❤️ {post.statsV2.diggCount.humanize() if post.statsV2.diggCount else 0} 👀 {post.statsV2.playCount.humanize() if post.statsV2.playCount else 0} 💬 {post.statsV2.commentCount.humanize() if post.statsV2.commentCount else 0} ∙ TikTok"""
        embed.set_footer(
            text=footer_text,
            icon_url="https://seeklogo.com/images/T/tiktok-icon-logo-1CB398A1BD-seeklogo.com.png",
        )
        embed.set_author(name=post.author.uniqueId, icon_url=post.author.avatarLarger)
        embeds = []
        if post.imagePost:
            url = f"https://www.tiktok.com/@{post.author.uniqueId}/photo/{post.id}"
            embed.url = url
            for image in post.imagePost.images:
                e = embed.copy()
                e.set_image(url=image.url)
                embeds.append(e)

        else:
            url = f"https://www.tiktok.com/@{post.author.uniqueId}/video/{post.id}"
            embed.url = url
            async with ClientSession() as session:
                async with session.get(
                    post.video.playAddr,
                    **await self.bot.services.tiktok.tt.get_tiktok_headers(),
                ) as response:
                    data = await response.read()
            kw["file"] = data
            embeds.append(embed)

        for record in records:
            await send(embeds, record, **kw)
        await self.redis.sadd(self.key, str(post.id))

    async def start(self) -> None:
        self.log = self.logger
        self.log.info("Started Feed!")
        while True:
            self.posted = 0
            records = await self.get_records()
            for username, records in records.items():
                needed = False
                for record in records:
                    if self.bot.get_guild(record.guild_id):
                        needed = True
                        break
                if needed:
                    self.bot.loop.create_task(self.get_posts(username, records))
                    await asyncio.sleep(uniform(4, 9))

            if self.scheduled_deletion:
                await self.bot.db.execute(
                    """
                    DELETE FROM feeds.tiktok
                    WHERE channel_id = ANY($1::BIGINT[])
                    """,
                    self.scheduled_deletion,
                )
                self.scheduled_deletion.clear()
            await asyncio.sleep(3600)
