from __future__ import annotations

import asyncio
import re
import os
from contextlib import suppress
from io import BytesIO
from logging import getLogger
from typing import TYPE_CHECKING, List, Optional, TypedDict, cast

from aiohttp import ClientPayloadError
from colorama import Fore, Style
from discord import HTTPException, Message
from discord.ext.commands import BadArgument
from discord.http import Route
from discord.utils import find
import discord
from cogs.social.reposters.extraction import Information, download
from main import Evict
from core.client.context import Context

if TYPE_CHECKING:
    from cogs.social.social import Social

log = getLogger("evict/social")


class ReposterSettings(TypedDict):
    reposter_prefix: bool
    disabled: bool


class Reposter:
    """
    Base class for all Social Reposters.
    """

    bot: Evict
    name: str
    regex: List[str]

    def __init__(
        self,
        bot: Evict,
        *,
        name: str = "",
        regex: List[str] = [],
        add_listener: bool = True,
    ):
        self.bot = bot
        self.name = name
        self.regex = regex
        if add_listener:
            self.bot.add_listener(self.listener, "on_message_without_command")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"<Reposter name={self.name!r} regex={self.regex!r}>"

    async def dispatch(
        self,
        ctx: Context,
        data: Information,
        buffer: Optional[BytesIO] = None,
    ) -> Message:
        """
        The embed dispatcher.
        """

        raise NotImplementedError

    async def nsfw_error(
        self,
        ctx: Context,
        data: Information,
    ) -> Message:
        """
        The nsfw error dispatcher.
        """

        return await ctx.warn(
            f"That [**{self.name}**]({data.webpage_url}) post is marked as **NSFW**!",
            "You can only view it in **NSFW channels**",
        )

    def match(self, url: str) -> Optional[re.Match[str]]:
        """
        Match the given url against the regex.
        """

        for pattern in self.regex:
            if match := re.search(pattern, url):
                log.info(f"Matched {self.name} URL: {url}")
                return match

        return None

    async def fetch(self, url: str) -> Optional[Information]:
        """
        Fetch the information from the given url.
        """

        return await download(url)

    async def listener(self, ctx: Context) -> None:
        """
        Listener for the reposters regex.
        """

        if ctx.author.bot or not (url := self.match(ctx.message.content)):
            return

        record: Optional[ReposterSettings] = await self.bot.db.fetchrow(
            """
            SELECT
                s.reposter_prefix,
                rd.channel_id IS NOT NULL AS disabled
            FROM
                settings AS s
            LEFT JOIN
                reposters.disabled rd ON rd.guild_id = s.guild_id AND rd.channel_id = $2 AND rd.reposter = $3
            WHERE
                s.guild_id = $1
            """,
            ctx.guild.id,
            ctx.channel.id,
            self.name,
        )
        if record:
            if record["reposter_prefix"] and not ctx.message.content.lower().startswith(
                (
                    "evict",
                    ctx.guild.me.display_name,
                )
            ):
                return

            elif record["disabled"]:
                return

        key = f"reposter:{ctx.channel.id}"
        if await self.bot.redis.ratelimited(key, 2, 8):
            return

        async with ctx.typing():
            try:
                data = await asyncio.wait_for(self.fetch(url[0]), timeout=15)
                if not data:
                    return await ctx.send("Failed to fetch that post!")
                    
                await self.dispatch(ctx, data)
                
            except Exception as e:
                log.error(f"Error processing URL {url}: {e}")
                await ctx.send("Failed to fetch that post!")

        with suppress(HTTPException):
            if ctx.settings.reposter_delete:
                await ctx.message.delete()

            elif ctx.message.embeds:
                await self.bot.http.request(
                    Route(
                        "PATCH",
                        f"/channels/{ctx.channel.id}/messages/{ctx.message.id}",
                    ),
                    json={"flags": 4},  
                )

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Reposter:
        social = cast(
            Optional["Social"],
            ctx.bot.get_cog("Social"),
        )
        if not social:
            raise ValueError("Social cog is not loaded.")

        reposter = find(
            lambda reposter: reposter.name.lower() == argument.lower(),
            social.reposters,
        )
        if not reposter:
            raise BadArgument(f"Reposter `{argument}` not found!")

        return reposter

    def can_process(self, message: Message) -> bool:
        if message.author.bot:
            return False
            
        if not message.guild:
            return False
            
        return True

    async def process(self, ctx: Context, url: str) -> None:
        try:
            data = await self.fetch(url)
            if not data:
                return

            response = await self.bot.session.get(data["filename"])
            if not response.ok:
                return

            buffer = BytesIO(await response.read())
            await self.dispatch(ctx, data, buffer)
            
        except Exception as e:
            log.error(f"Error processing URL {url}: {e}")
            raise
