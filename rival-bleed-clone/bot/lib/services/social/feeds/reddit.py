import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from html import unescape
from io import BytesIO
from logging import getLogger
from typing import Dict, List, Optional, cast
from typing_extensions import Self
from asyncpraw import Reddit as Client
from asyncpraw.models.reddit.submission import Submission
from asyncpraw.models.reddit.subreddit import Subreddit, SubredditStream
from discord import Embed, File, HTTPException, TextChannel, Thread

from ..reposters.reddit import Reddit as RedditReposter
from textwrap import shorten

from .base import BaseRecord, Feed

log = getLogger("rival/reddit")


class Record(BaseRecord):
    subreddit_name: str


class Reddit(Feed):
    """
    Listener for new submissions.
    """

    streams: Dict[str, asyncio.Task]
    reposter: RedditReposter

    def __init__(self, bot):
        super().__init__(bot, name="Reddit")
        bot.reddit = Client(
            client_id="Hb-TXxg3coz32_Xy2CTByQ",
            client_secret="nbYL91qSuDLYoLyP6d098-F16qbjSw",
            user_agent=bot.user_agent,
        )
        self.streams = {}
        self.reposter = RedditReposter(bot, add_listener=False)

    async def stop(self: Self) -> None:
        for stream in self.streams:
            self.streams[stream].cancel()

        await self.bot.reddit.close()
        return await super().stop()

    async def start_stream(self: Self, display_name: str) -> None:
        subreddit: Subreddit = await self.bot.reddit.subreddit(display_name)
        stream: SubredditStream = subreddit.stream

        log.debug("Started submission stream for r/%s.", display_name)
        async for submission in stream.submissions(skip_existing=True):
            await self.dispatch(submission)

    async def feed(self: Self) -> None:
        log.info(f"Started Reddit Feed")
        while True:
            subreddits = cast(
                List[str],
                await self.bot.db.fetchval(
                    """
                    SELECT ARRAY_AGG(subreddit_name)
                    FROM feeds_reddit
                    """,
                ),
            )
            if not subreddits:
                continue
            for subreddit in subreddits:
                if subreddit in self.streams:
                    continue

                self.streams[subreddit] = self.bot.loop.create_task(
                    self.start_stream(subreddit),
                    name=f"Reddit-{subreddit}",
                )
                self.streams[subreddit].add_done_callback(
                    lambda _: (
                        log.debug(
                            "Stopped submission stream for r/%s.",
                            _.get_name().split("-")[-1],
                        ),
                        self.streams.pop(_.get_name().split("-")[-1]),
                    ),
                )

            for stream in list(self.streams):
                if stream not in subreddits:
                    self.streams[stream].cancel()

            if self.scheduled_deletion:
                await self.bot.db.execute(
                    """
                    DELETE FROM feeds_reddit
                    WHERE channel_id = ANY($1::BIGINT[])
                    """,
                    self.scheduled_deletion,
                )
                self.scheduled_deletion.clear()

            await asyncio.sleep(60 * 10)

    async def custom_embed(self: Self, submission: Submission, record: Record, **kwargs):
        guild = self.bot.get_guild(record["guild_id"])
        if not guild:
            return

        channel = guild.get_channel_or_thread(record["channel_id"])
        if (
            not isinstance(channel, (TextChannel, Thread))
            or isinstance(channel, (TextChannel, Thread))
            and not self.can_post(channel)
        ):
            self.scheduled_deletion.append(record["channel_id"])
            return

        if submission.over_18 and not channel.is_nsfw():
            return
        if record.template:
            if submission.url:
                if (
                    hasattr(submission, "is_gallery")
                    and submission.is_gallery
                    and submission.media_metadata
                ):
                    media_url = list(submission.media_metadata.values())[0]["p"][-1]["u"]
                    embed.set_image(url=media_url)

                elif (
                    not submission.is_video
                    and submission.permalink not in submission.url
                    and submission.url
                ):
                    embed.set_image(url=submission.url)

                else:
                    data = await self.reposter.fetch(submission.url)
                    if data and data.requested_downloads:
                        buffer = await data.requested_downloads[-1].read()
                        extension = data.ext
            if buffer:
                kwargs = {"file": File(buffer, filename=f"{submission.id}.{extension}")}
            else:
                kwargs = {}

            self.posted += 1
            with suppress(HTTPException):
                await self.bot.make_embed(
                    channel, code=record.template, member=guild.me, guild=guild
                )
        else:
            embed = Embed(
                url=f"https://reddit.com{submission.permalink}",
                title=shorten(unescape(submission.title or ""), 256),
                description=shorten(unescape(submission.selftext or ""), 2048),
                timestamp=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
            )
            embed.set_author(
                name=f"u/{unescape(submission.author.name if submission.author else '[deleted]')}",
                url=f"https://reddit.com/u/{unescape(submission.author.name)}"
                if submission.author
                else None,
            )
            embed.set_footer(
                text=f"r/{unescape(submission.subreddit.display_name)}",
            )

            if submission.url:
                if (
                    hasattr(submission, "is_gallery")
                    and submission.is_gallery
                    and submission.media_metadata
                ):
                    media_url = list(submission.media_metadata.values())[0]["p"][-1]["u"]
                    embed.set_image(url=media_url)

                elif (
                    not submission.is_video
                    and submission.permalink not in submission.url
                    and submission.url
                ):
                    embed.set_image(url=submission.url)

                else:
                    data = await self.reposter.fetch(submission.url)
                    if data and data.requested_downloads:
                        buffer = await data.requested_downloads[-1].read()
                        extension = data.ext
                        guild = self.bot.get_guild(record["guild_id"])

            self.posted += 1
            with suppress(HTTPException):
                if buffer:
                    await channel.send(
                        embed=embed,
                        file=File(
                            buffer,
                            filename=f"{submission.id}.{extension}",
                        ),
                    )
                    return

                await channel.send(embed=embed)

    async def dispatch(self: Self, submission: Submission) -> None:
        """
        Dispatch a submission to the subscription channels
        """

        log.debug(
            "Dispatching submission %r from r/%s.", submission.id, submission.subreddit
        )

        buffer: Optional[BytesIO] = None
        extension: Optional[str] = None

        embed = Embed(
            url=f"https://reddit.com{submission.permalink}",
            title=shorten(unescape(submission.title or ""), 256),
            description=shorten(unescape(submission.selftext or ""), 2048),
            timestamp=datetime.fromtimestamp(submission.created_utc, tz=timezone.utc),
        )
        embed.set_author(
            name=f"u/{unescape(submission.author.name if submission.author else '[deleted]')}",
            url=f"https://reddit.com/u/{unescape(submission.author.name)}"
            if submission.author
            else None,
        )
        embed.set_footer(
            text=f"r/{unescape(submission.subreddit.display_name)}",
        )

        if submission.url:
            if (
                hasattr(submission, "is_gallery")
                and submission.is_gallery
                and submission.media_metadata
            ):
                media_url = list(submission.media_metadata.values())[0]["p"][-1]["u"]
                embed.set_image(url=media_url)

            elif (
                not submission.is_video
                and submission.permalink not in submission.url
                and submission.url
            ):
                embed.set_image(url=submission.url)

            else:
                data = await self.reposter.fetch(submission.url)
                if data and data.requested_downloads:
                    buffer = await data.requested_downloads[-1].read()
                    extension = data.ext

        records = cast(
            List[Record],
            await self.bot.db.fetch(
                """
                SELECT *
                FROM feeds_reddit
                WHERE subreddit_name = $1
                """,
                submission.subreddit.display_name,
            ),
        )

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

            if submission.over_18 and not channel.is_nsfw():
                continue

            self.posted += 1
            with suppress(HTTPException):
                if buffer:
                    await channel.send(
                        embed=embed,
                        file=File(
                            buffer,
                            filename=f"{submission.id}.{extension}",
                        ),
                    )
                    continue

                await channel.send(embed=embed)
