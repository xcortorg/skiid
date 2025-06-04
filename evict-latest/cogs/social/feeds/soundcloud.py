import asyncio
from collections import defaultdict
from contextlib import suppress
from datetime import timedelta
from logging import getLogger
from random import uniform
from typing import Dict, List, cast

from discord import AllowedMentions, HTTPException, TextChannel, Thread
from discord.utils import utcnow

from cogs.social.models.soundcloud import Track, User
from main import Evict
from tools.conversion.script import Script

from .base import BaseRecord, Feed

log = getLogger("evict/soundcloud")


class Record(BaseRecord):
    soundcloud_id: int
    soundcloud_name: str


class SoundCloud(Feed):
    """
    Listener for new tracks.
    """

    def __init__(self, bot: Evict):
        super().__init__(
            bot,
            name="SoundCloud",
        )

    async def feed(self) -> None:
        while True:
            records = await self.get_records()
            for soundcloud_id, records in records.items():
                self.bot.loop.create_task(self.get_tracks(soundcloud_id, records))
                await asyncio.sleep(uniform(0.5, 1.5))

            if self.scheduled_deletion:
                await self.bot.db.execute(
                    """
                    DELETE FROM feeds.soundcloud
                    WHERE channel_id = ANY($1::BIGINT[])
                    """,
                    self.scheduled_deletion,
                )
                self.scheduled_deletion.clear()

            await asyncio.sleep(60 * 9)

    async def get_records(self) -> dict[int, List[Record]]:
        records = cast(
            List[Record],
            await self.bot.db.fetch(
                """
                SELECT *
                FROM feeds.soundcloud
                """,
            ),
        )

        result: Dict[int, List[Record]] = defaultdict(list)
        for record in records:
            result[record["soundcloud_id"]].append(record)

        return result

    async def get_tracks(self, user_id: int, records: List[Record]) -> None:
        """
        Fetch and dispatch new tracks.
        """

        tracks = await User.tracks(self.bot.session, user_id)
        if not tracks:
            log.debug("No tracks found for %s.", user_id)
            return

        for track in reversed(tracks[:8]):
            if utcnow() - track.created_at > timedelta(hours=12):
                continue

            if await self.redis.sismember(self.key, str(track.id)):
                continue

            await self.redis.sadd(self.key, str(track.id))
            await self.dispatch(track.user, track, records)
            self.posted += 1

    async def dispatch(
        self,
        user: User,
        track: Track,
        records: List[Record],
    ) -> None:
        """
        Dispatch a track to the subscription channels.
        """

        log.debug(
            "Dispatching track %r from %s (%s).",
            track.id,
            user.username,
            user.id,
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
                script = Script(
                    record["template"]
                    or f"**{user}** uploaded a new track!\n{track.url}",
                    [channel.guild, channel, user, track],
                )

                await script.send(
                    channel,
                    allowed_mentions=AllowedMentions.all(),
                )
