import asyncio
from contextlib import suppress
from datetime import datetime, timedelta
from logging import getLogger
from typing import List, Optional, cast

from core.client.network import Network
from core.managers.parser import Script
from core.Mono import Mono
from discord import AllowedMentions, HTTPException, TextChannel, Thread
from discord.utils import utcnow
from extensions.socials.models.youtube.channel import Channel
from extensions.socials.reposters.extraction import download
from pydantic import BaseModel  # type: ignore

from .base import BaseRecord, Feed

log = getLogger("greedbot/youtube")


class Record(BaseRecord):
    youtube_id: str
    youtube_name: str
    shorts: bool


class Video(BaseModel):
    id: Optional[str]
    uploader: Optional[str]
    title: Optional[str]
    description: Optional[str]
    duration: Optional[timedelta]
    views: Optional[int] = 0
    is_short: Optional[bool] = False
    thumbnail_url: Optional[str]
    created_at: Optional[datetime]

    def __str__(self) -> Optional[str]:
        return self.title

    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.id}"


class YouTube(Feed):
    """
    Listener for new videos.
    """

    def __init__(self, bot: Mono):
        super().__init__(
            bot,
            name="YouTube",
        )
        self.bot.add_listener(self.listener, "on_pubsub")

    async def stop(self) -> None:
        self.bot.remove_listener(self.listener, "on_pubsub")
        return await super().stop()

    async def feed(self) -> None:
        while True:
            network = cast(Optional[Network], self.bot.get_cog("Network"))
            if not network:
                await asyncio.sleep(30)
                continue

            records = await self.bot.db.fetch(
                """
                SELECT DISTINCT ON (youtube_id) youtube_id
                FROM feeds.youtube
                WHERE youtube_id NOT IN (
                    SELECT id
                    FROM pubsub
                )
                """
            )
            for record in records:
                await network.pubsub_subscribe(record["youtube_id"])

            if self.scheduled_deletion:
                await self.bot.db.execute(
                    """
                    DELETE FROM feeds.youtube
                    WHERE channel_id = ANY($1::BIGINT[])
                    """,
                    self.scheduled_deletion,
                )
                self.scheduled_deletion.clear()

            await asyncio.sleep(30)

    async def listener(self, video_id: str, channel_id: str) -> None:
        """
        Extract the video ID using YouTubeDL & dispatch it.
        """

        records = cast(
            List[Record],
            await self.bot.db.fetch(
                """
                SELECT *
                FROM feeds.youtube
                WHERE youtube_id = $1
                """,
                channel_id,
            ),
        )
        if not records:
            return

        video_url = "https://www.youtube.com/watch?v=" + video_id
        data = await download(video_url)
        if not data or not all(
            [
                data.channel_id,
                data.channel,
                data.title,
                data.id,
            ]
        ):
            log.warning("Failed to extract video data from %r.", video_url)
            return

        user = Channel(
            id=data.channel_id or "Unknown",
            name=data.channel or "Unknown",
            subscribers=data.channel_follower_count,
        )
        video = Video(
            id=data.id,
            uploader=data.channel,
            title=data.title,
            description=data.description,
            duration=timedelta(seconds=data.duration or 0),
            views=data.view_count,
            is_short=(data.duration or 0) < 120,
            thumbnail_url=data.thumbnail,
            created_at=utcnow(),
        )

        await self.dispatch(user, video, records)
        self.posted += 1

    async def dispatch(
        self,
        user: Channel,
        video: Video,
        records: List[Record],
    ) -> None:
        """
        Dispatch a video to the subscription channels.
        """

        for record in records:
            if video.is_short and not record["shorts"]:
                continue

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
                script = Script(
                    record["template"]
                    or f"**{user}** uploaded a new video!\n{video.url}",
                    [channel.guild, channel, user, video],
                )

                await script.send(
                    channel,
                    allowed_mentions=AllowedMentions.all(),
                )
