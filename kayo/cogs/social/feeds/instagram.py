import asyncio
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timedelta
from io import BytesIO
from logging import getLogger
from random import uniform
from textwrap import shorten
from typing import Dict, List, Optional, cast
from discord.utils import utcnow
from discord import AllowedMentions, Embed, File, HTTPException, TextChannel, Thread

from cogs.social.models.instagram.post import Post
from cogs.social.reposters.extraction.instagram import (
    Instagram as InstagramClient,
    User,
    Post,
)
from main import swag

from .base import BaseRecord, Feed

log = getLogger("swag/gram")


class Record(BaseRecord):
    instagram_id: int
    instagram_name: str
    template: Optional[str]


class Instagram(Feed):
    """
    Listener for new posts & stories.
    """

    instagram_client: InstagramClient

    def __init__(self, bot: swag):
        super().__init__(
            bot,
            name="Instagram",
        )
        self.instagram_client = InstagramClient(bot)

    async def feed(self) -> None:
        """
        The feed task.
        """

        while True:
            records = await self.get_records()
            for user, records in records.items():
                await self.get_posts(*user, records)
                await asyncio.sleep(uniform(3, 6))

            if self.scheduled_deletion:
                await self.bot.db.execute(
                    """
                    DELETE FROM feeds.instagram
                    WHERE channel_id = ANY($1::BIGINT[])
                    """,
                    self.scheduled_deletion,
                )
                self.scheduled_deletion.clear()

            await asyncio.sleep(60 * 9)

    async def get_records(self) -> dict[tuple[int, str], List[Record]]:
        records = cast(
            List[Record],
            await self.bot.db.fetch(
                """
                SELECT *
                FROM feeds.instagram
                """,
            ),
        )

        result: Dict[tuple[int, str], List[Record]] = defaultdict(list)
        for record in records:
            result[record["instagram_id"], record["instagram_name"]].append(record)

        return result

    async def get_posts(
        self,
        user_id: int,
        username: str,
        records: List[Record],
    ) -> None:
        """
        Get new stories from a user.
        """

        try:
            stories = await self.instagram_client.get_stories(username)
        except Exception:
            stories = None

        if not stories:
            log.debug(
                "No stories available for %s (%s).",
                username,
                user_id,
            )

        for post in stories:
            if utcnow() - post.created_at > timedelta(hours=1):
                continue

            if await self.redis.sismember(self.key, str(post.id)):
                continue

            await self.redis.sadd(self.key, str(post.id))
            await self.dispatch(post.user, post, records)
            self.posted += 1

    async def dispatch(
        self,
        user: User,
        post: Post,
        records: List[Record],
    ) -> None:
        """
        Dispatch a post to the subscription channels.
        """

        log.debug(
            "Dispatching story item %r from %s (%s).",
            post.id,
            user.username,
            user.id,
        )

        media = post.media[0]
        buffer = await media.buffer()
        extension = media.ext

        if len(buffer) == 22:
            return

        embed = Embed(url=user.url, timestamp=post.created_at)
        embed.set_author(
            url=user.url,
            name=user.full_name or user.username,
            icon_url=user.avatar_url,
        )
        embed.set_footer(
            text=f"Instagram Story",
            icon_url="https://i.imgur.com/U31ZVlK.png",
        )

        for record in records:
            guild = self.bot.get_guild(record["guild_id"])
            if not guild:
                self.scheduled_deletion.append(record["channel_id"])
                continue

            channel = guild.get_channel_or_thread(record["channel_id"])
            if (
                not isinstance(channel, (TextChannel, Thread))
                or isinstance(channel, (TextChannel, Thread))
                and not self.can_post(channel)
            ):
                self.scheduled_deletion.append(record["channel_id"])
                continue

            with suppress(HTTPException):
                file = File(BytesIO(buffer), filename=f"story.{extension}")
                await channel.send(
                    embed=embed,
                    file=file,
                    allowed_mentions=AllowedMentions.all(),
                )
