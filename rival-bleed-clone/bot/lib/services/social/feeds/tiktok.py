import asyncio, orjson
from collections import defaultdict
from contextlib import suppress
from datetime import timedelta
from io import BytesIO
import traceback
from logging import getLogger
from random import uniform
from secrets import token_urlsafe
from textwrap import shorten
from typing import Dict, List, cast, Optional
from typing_extensions import Self, NoReturn
from discord import AllowedMentions, Embed, File, HTTPException, TextChannel, Thread
from discord.utils import utcnow
# from functions.rival_tiktok import fetch_tiktok, make_embed_channel
# from classes.browser import Controller
from ..models.tiktok.posts import BasicUser, Post, Posts

from .base import BaseRecord, Feed

log = getLogger("rival/tiktok")



class Record(BaseRecord):
    tiktok_id: int
    tiktok_name: str


class TikTok(Feed):
    """
    Listener for new posts.
    """

    def __init__(self, bot):
        super().__init__(
            bot,
            name="TikTok",
        )

    def replacements(self: Self, post: Post) -> dict:
        REPLACEMENTS = {
            "{post.description}": shorten(post.caption or "", width=256),
            "{post.date}": post.created_at,
            "{post.url}": post.url,
            "{post.media_urls}": post.video.url,
            "{post.author.name}": post.author.username,
            "{post.author.nickname}": post.author.full_name,
            "{post.author.avatar}": post.author.avatar_url,
            "{post.author.url}": post.author.url,
            "{post.stats.likes}": post.statistics.like_count,
            "{post.stats.comments}": post.statistics.comment_count,
            "{post.stats.plays}": post.statistics.play_count,
            "{post.stats.shares}": post.statistics.share_count

        }
        return REPLACEMENTS

    async def check_browser(self: Self) -> NoReturn:
        return True
        if not self.bot.browser:
             self.bot.browser = Controller()
             await self.bot.browser.setup(proxy="127.0.0.1:1137")
             self.bot.browser_ready = True

    async def feed(self: Self) -> None:
        return
        log.info(f"Started TikTok Feed")
        while True:
            await self.check_browser()
            records = await self.get_records()
            for username, records in records.items():
                self.bot.loop.create_task(self.get_posts(username, records))
                await asyncio.sleep(uniform(4, 9))

            if self.scheduled_deletion:
                await self.bot.db.execute(
                    """
                    DELETE FROM feeds_tiktok
                    WHERE channel_id = ANY($1::BIGINT[])
                    """,
                    self.scheduled_deletion,
                )
                self.scheduled_deletion.clear()

            await asyncio.sleep(60 * 30)

    async def get_records(self: Self) -> dict[str, List[Record]]:
        records = cast(
            List[Record],
            await self.bot.db.fetch(
                """
                SELECT *
                FROM feeds_tiktok
                """,
            ),
        )

        result: Dict[str, List[Record]] = defaultdict(list)
        for record in records:
            result[record["tiktok_name"]].append(record)

        return result

    async def get_posts(self: Self, username: str, records: List[Record], return_posts: Optional[bool] = False) -> Optional[Posts]:
        """
        Fetch and dispatch new posts.
        """
        cached = False
        if pull := await self.bot.redis.get(self.make_key(f"tiktok_posts:{username}")):
            cached = True
            data = Posts(**orjson.loads(pull))
        else:
            try:
                data = await Posts.fetch(self.bot.browser, username)
            except Exception as e:
                exc = "".join(
                    traceback.format_exception(type(e), e, e.__traceback__)
                )
                log.info(f"TikTok Posts Fetching raised: {e} \n{exc}")
                data = None
        if data is False:
            await self.bot.db.execute(
                """
                DELETE FROM feeds_tiktok
                WHERE tiktok_name = $1
                """,
                username,
            )
            log.warning("No TikTok user found for %s.", username)
            return False

        if not data or not data.user:
            log.debug(
                "No posts available for @%s (%s).",
                username,
                records[0]["tiktok_id"],
            )
            return False
        if not cached:
            await self.bot.redis.set(self.make_key(f"tiktok_posts:{username}"), orjson.dumps(data.dict()), ex = 60*29)
        if return_posts: 
            return data
        for post in reversed(data.posts[:3]):
            if utcnow() - post.created_at > timedelta(hours=1):
                continue

            if await self.bot.redis.sismember(self.key, str(post.id)):
                log.info(f"skipping {str(post.id)} due to it already have been sent")
                continue

            await self.bot.redis.sadd(self.key, str(post.id))
            self.bot.loop.create_task(self.dispatch(data.user, post, records))
            self.posted += 1

    async def dispatch(
        self: Self,
        user: BasicUser,
        post: Post,
        records: List[Record],
    ) -> None:
        """
        Dispatch a post to the subscription channels.
        """

        log.debug("Dispatching post %r from @%s (%s).", post.id, user.username, user.id)

        embed = Embed(
            url=post.url,
            title=shorten(post.caption or "", width=256),
            timestamp=post.created_at,
        )
        embed.set_author(
            name=user.full_name or user.username,
            icon_url=user.avatar_url,
            url=user.url,
        )

        try:
            data = await fetch_tiktok(ctx = None, url = str(post.url))
        except:
            data = None
        if not data:
            log.warning(
                "No data found for post %r from @%s (%s).",
                post.id,
                user.username,
                user.id,
            )
            return

        for record in records:
            guild = self.bot.get_guild(record["guild_id"])
            if not guild:
                continue

            channel = guild.get_channel_or_thread(record["channel_id"])
            if (
                not isinstance(channel, (TextChannel, Thread))
                or isinstance(channel, (TextChannel, Thread))
                and not self.can_post(channel)
            ):
                self.scheduled_deletion.append(record["channel_id"])
                continue

            await make_embed_channel(channel, data)
            await asyncio.sleep(uniform(1, 3.5))
