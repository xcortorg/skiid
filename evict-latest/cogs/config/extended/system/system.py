import discord
import datetime
from contextlib import suppress
from itertools import groupby
from logging import getLogger
from typing import List, Optional, cast
from ..joindm.joindm import InfoView
import config

from discord import (
    Embed,
    HTTPException,
    Member,
    Message,
    MessageType,
    PartialMessage,
    TextChannel,
    Thread,
)
from discord.ext.commands import Cog, Range, flag, group, has_permissions
from humanfriendly import format_timespan
from xxhash import xxh32_hexdigest

from tools import CompositeMetaClass, MixinMeta
from core.client import Context, FlagConverter
from tools.formatter import codeblock, plural, vowel
from managers.paginator import Paginator
from tools.conversion.embed import EmbedScript as Script
import psutil
import time
import asyncio

log = getLogger("evict/system")
poj_cache = {}

class Flags(FlagConverter):
    delete_after: Range[int, 3, 120] = flag(
        aliases=["self_destruct"],
        description="Delete the message after a certain amount of time.",
        default=0,
    )


class System(MixinMeta, metaclass=CompositeMetaClass):
    """
    The System mixin provides tools for automating messages.
    """

    async def _get_cached_messages(self, guild_id: int, message_type: str) -> Optional[List[dict]]:
        if not hasattr(self, '_cache_ttl'):
            self._cache_ttl = 300  
            
        try:
            cache_dict = getattr(self, f"_{message_type}_cache")
        except AttributeError:
            setattr(self, f"_{message_type}_cache", {})
            cache_dict = getattr(self, f"_{message_type}_cache")
            
        cache_key = f"{message_type}_{guild_id}"
        cached = cache_dict.get(cache_key)
        
        if cached and cached['timestamp'] + self._cache_ttl > time.time():
            return cached['data']
        
        records = await self.bot.db.fetch(
            f"""
            SELECT channel_id, template, delete_after
            FROM {message_type}_message
            WHERE guild_id = $1
            """,
            guild_id,
        )
        
        cache_dict[cache_key] = {
            'timestamp': time.time(),
            'data': records
        }
        return records

    async def _process_message_send(self, member: Member, message_type: str) -> List[Message]:
        sent_messages: List[Message] = []
        guild = member.guild
        scheduled_deletion: List[int] = []

        records = await self._get_cached_messages(guild.id, message_type)
        if not records:
            return sent_messages

        async def process_single_message(record):
            channel_id = cast(int, record["channel_id"])
            channel = cast(Optional[TextChannel | Thread], 
                         guild.get_channel_or_thread(channel_id))

            if not channel:
                scheduled_deletion.append(channel_id)
                return None

            try:
                x = await self.bot.embed_build.alt_convert(member, record["template"])
                message = await channel.send(**x)
                
                if record["delete_after"]:
                    await message.delete(delay=record["delete_after"])
                return message
            except HTTPException as exc:
                await self.notify_failure(message_type, channel, member, x, exc)
                scheduled_deletion.append(channel_id)
                return None

        messages = await asyncio.gather(
            *[process_single_message(record) for record in records],
            return_exceptions=True
        )
        
        sent_messages = [msg for msg in messages if msg and not isinstance(msg, Exception)]

        if scheduled_deletion:
            await self.bot.db.execute(
                f"""
                DELETE FROM {message_type}_message
                WHERE channel_id = ANY($1::BIGINT[])
                """,
                scheduled_deletion,
            )

        if sent_messages and message_type == 'welcome':
            key = self.welcome_key(member)
            await self.bot.redis.sadd(
                key,
                *[f"{message.channel.id}.{message.id}" for message in sent_messages],
                ex=3000,
            )

        return sent_messages

    def welcome_key(self, member: Member) -> str:
        return f"welcome.{member.guild.id}:{member.id}"

    async def notify_failure(
        self,
        system: str,
        channel: TextChannel | Thread,
        member: Member,
        script: Script,
        exc: HTTPException,
    ) -> Optional[Message]:
        """
        Notify the server owner of a system message failure.
        """

        owner = channel.guild.owner
        if not owner:
            return None

        embed = Embed(
            title=f"{system.title()} Message Failure",
            description=(
                f"Failed to send {system.lower()} message for **{member}** "
                f"in {channel.mention}\n" + codeblock(exc.text)
            ),
        )
        if len(script.template) <= 1024:
            embed.add_field(
                name="**Script**",
                value=codeblock(script.template),
            )

        with suppress(HTTPException):
            return await owner.send(
                embed=embed,
                content=(
                    codeblock(script.template) if len(script.template) > 1024 else None
                ),
            )

    @Cog.listener("on_member_join")
    async def welcome_send(self, member: Member) -> List[Message]:
        sent_messages = await self._process_message_send(member, 'welcome')
        
        if not member.bot:
            try:
                async with self.bot.db.acquire() as conn:
                    config = await conn.fetchrow(
                        """
                        SELECT * FROM joindm.config
                        WHERE guild_id = $1 AND enabled = true
                        """,
                        member.guild.id
                    )

                    if config and config['message']:
                        script = await self.bot.embed_build.alt_convert(member, config['message'])
                        view = InfoView(member.guild.id)
                        if isinstance(script, dict):
                            script['view'] = view
                        dm = await member.send(**script)
                        sent_messages.append(dm)
            except HTTPException:
                pass  

        return sent_messages

    @Cog.listener("on_member_remove")
    async def welcome_delete(self, member: Member):
        guild = member.guild
        key = self.welcome_key(member)
        
        removal, identifiers = await asyncio.gather(
            self.bot.db.fetchval(
                "SELECT welcome_removal FROM settings WHERE guild_id = $1",
                guild.id
            ),
            self.bot.redis.smembers(key)
        )
        
        if not (removal and identifiers):
            return

        channel_messages = {}
        for identifier in identifiers:
            channel_id, message_id = map(int, identifier.split("."))
            channel = guild.get_channel_or_thread(channel_id)
            if isinstance(channel, (TextChannel, Thread)):
                if channel_id not in channel_messages:
                    channel_messages[channel_id] = []
                channel_messages[channel_id].append(
                    channel.get_partial_message(message_id)
                )

        deletion_tasks = []
        for channel_id, messages in channel_messages.items():
            channel = guild.get_channel_or_thread(channel_id)
            if channel:
                deletion_tasks.append(
                    asyncio.create_task(channel.delete_messages(messages))
                )

        if deletion_tasks:
            await asyncio.gather(*deletion_tasks, return_exceptions=True)

    @Cog.listener("on_member_remove")
    async def goodbye_send(self, member: Member) -> List[Message]:
        return await self._process_message_send(member, 'goodbye')

    @Cog.listener("on_member_boost")
    async def boost_send(self, member: Member) -> List[Message]:
        return await self._process_message_send(member, 'boost')

    @Cog.listener("on_message")
    async def welcome_system(self, message: Message):
        """
        Add the system welcome message to redis.
        """

        if message.type != MessageType.new_member:
            return

        elif not isinstance(message.author, Member):
            return

        key = self.welcome_key(message.author)
        await self.bot.redis.sadd(
            key,
            f"{message.channel.id}.{message.id}",
            ex=3000,
        )

    @group(
        aliases=["greet", "welc", "wlc"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def welcome(self, ctx: Context) -> Message:
        """
        The base command for managing greet messages.

        Welcome messages are sent when a user joins the server.
        They can be configured to send in multiple channels with different messages.
        """

        return await ctx.send_help(ctx.command)

    @welcome.command(
        name="removal",
        aliases=["deletion"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_removal(self, ctx: Context) -> Message:
        """
        Toggle welcome message deletion on member removal.
        """

        await ctx.settings.update(welcome_removal=not ctx.settings.welcome_removal)
        return await ctx.approve(
            f"Welcome messages will **{'now' if ctx.settings.welcome_removal else 'no longer'}** be deleted on member removal"
        )

    @welcome.command(
        name="add",
        aliases=["create"],
        example="(#channel | #thread) ({user.mention} welcome to {guild.name}!)",
    )
    @has_permissions(manage_guild=True)
    async def welcome_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        script: Script,
    ) -> Message:
        """
        Add a greet message to a channel.
        """

        template, flags = await Flags().find(ctx, script.script)

        if not template:
            return await ctx.warn("You must provide a greet message!")

        records = len(
            [
                record
                for record in await self.bot.db.fetch(
                    """
                    SELECT channel_id
                    FROM welcome_message
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                )
                if ctx.guild.get_channel_or_thread(record["channel_id"])
            ]
        )
        if records >= 2:
            return await ctx.warn("You can't have more than `2` greet messages!")

        await self.bot.db.execute(
            """
            INSERT INTO welcome_message (
                guild_id,
                channel_id,
                template,
                delete_after
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, channel_id)
            DO UPDATE SET
                template = EXCLUDED.template,
                delete_after = EXCLUDED.delete_after
            """,
            ctx.guild.id,
            channel.id,
            template,
            flags.delete_after,
        )

        return await ctx.approve(
            f"Added greet message to {channel.mention}.",
            *(
                [
                    f"The message will be deleted after **{format_timespan(flags.delete_after)}**"
                ]
                if flags.delete_after
                else []
            ),
        )

    @welcome.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#welcome",
    )
    @has_permissions(manage_guild=True)
    async def welcome_remove(self, ctx: Context, channel: TextChannel) -> Message:
        """
        Remove an existing greet message.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM welcome_message
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"A greet message in {channel.mention} doesn't exist!"
            )

        return await ctx.approve(
            f"No longer sending greet messages in {channel.mention}"
        )

    @welcome.command(name="view", aliases=["show"], example="#welcome")
    @has_permissions(manage_guild=True)
    async def welcome_view(self, ctx: Context, channel: TextChannel) -> None:
        """

        View an existing greet message.

        """
        template = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT template
                FROM welcome_message
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if not template:
            return await ctx.warn(
                f"A greet message in {channel.mention} doesn't exist!"
            )

        script = Script(template, [ctx.guild, ctx.author, channel])
        await ctx.send(codeblock(script))

        result = await self.bot.embed_build.alt_convert(ctx.author, template)
        await ctx.send(
            result.get("content"),
            embed=result.get("embed"),
            view=result.get("view"),
            delete_after=result.get("delete_after"),
        )

    @welcome.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_clear(self, ctx: Context) -> Message:
        """
        Remove all greet messages.
        """

        await ctx.prompt(
            "Are you sure you want to remove all greet messages?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM welcome_message
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No greet messages exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):greet message}"
        )

    @welcome.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_list(self, ctx: Context) -> Message:
        """
        View all welcome channels.
        """

        channels = [
            f"{channel.mention} (`{channel.id}`)"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id
                FROM welcome_message
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No greet messages exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="Welcome Channels"),
        )
        return await paginator.start()

    @group(
        aliases=["leave", "bye"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def goodbye(self, ctx: Context) -> Message:
        """
        The base command for managing leave messages.

        Goodbye messages are sent when a user leaves the server.
        They can be configured to send in multiple channels with different messages.
        """

        return await ctx.send_help(ctx.command)

    @goodbye.command(
        name="add",
        aliases=["create"],
        example="(#channel | #thread) ({user.mention} has left the server!)",
    )
    @has_permissions(manage_guild=True)
    async def goodbye_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        script: Script,
    ) -> Message:
        """
        Add a leave message to a channel.
        """

        template, flags = await Flags().find(ctx, script.script)  # Use script.script
        if not template:
            return await ctx.warn("You must provide a leave message!")

        records = len(
            [
                record
                for record in await self.bot.db.fetch(
                    """
                    SELECT channel_id
                    FROM goodbye_message
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                )
                if ctx.guild.get_channel_or_thread(record["channel_id"])
            ]
        )

        if records >= 2:
            return await ctx.warn("You can't have more than `2` leave messages!")

        await self.bot.db.execute(
            """
            INSERT INTO goodbye_message (
                guild_id,
                channel_id,
                template,
                delete_after
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, channel_id)
            DO UPDATE SET
                template = EXCLUDED.template,
                delete_after = EXCLUDED.delete_after
            """,
            ctx.guild.id,
            channel.id,
            template,
            flags.delete_after,
        )

        return await ctx.approve(
            f"Added leave message to {channel.mention}",
            *(
                [
                    f"The message will be deleted after **{format_timespan(flags.delete_after)}**"
                ]
                if flags.delete_after
                else []
            ),
        )

    @goodbye.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#goodbye",
    )
    @has_permissions(manage_guild=True)
    async def goodbye_remove(self, ctx: Context, channel: TextChannel) -> Message:
        """
        Remove an existing leave message.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM goodbye_message
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"A leave message in {channel.mention} doesn't exist!"
            )

        return await ctx.approve(
            f"No longer sending leave messages in {channel.mention}"
        )

    @goodbye.command(
        name="view",
        aliases=["show"],
        example="#goodbye",
    )
    @has_permissions(manage_guild=True)
    async def goodbye_view(self, ctx: Context, channel: TextChannel) -> Message:
        """
        View an existing leave message.
        """

        template = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT template
                FROM goodbye_message
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if not template:
            return await ctx.warn(
                f"A leave message in {channel.mention} doesn't exist!"
            )

        script = Script(template, [ctx.guild, ctx.author, channel])
        await ctx.send(codeblock(script))

        result = await self.bot.embed_build.alt_convert(ctx.author, template)
        await ctx.send(
            result.get("content"),
            embed=result.get("embed"),
            view=result.get("view"),
            delete_after=result.get("delete_after"),
        )

    @goodbye.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_guild=True)
    async def goodbye_clear(self, ctx: Context) -> Message:
        """
        Remove all leave messages.
        """

        await ctx.prompt(
            "Are you sure you want to remove all leave messages?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM goodbye_message
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No leave messages exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):leave message}"
        )

    @goodbye.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def goodbye_list(self, ctx: Context) -> Message:
        """
        View all goodbye channels.
        """

        channels = [
            f"{channel.mention} (`{channel.id}`)"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id
                FROM goodbye_message
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No leave messages exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="Goodbye Channels"),
        )
        return await paginator.start()

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def boost(self, ctx: Context) -> Message:
        """
        The base command for managing boost messages.

        Boost messages are sent when a user boosts the server.
        They can be configured to send in multiple channels with different messages.
        """

        return await ctx.send_help(ctx.command)

    @boost.command(
        name="add",
        aliases=["create"],
        example="(#channel | #thread) ({user.mention} has boosted the server!)"
    )
    @has_permissions(manage_guild=True)
    async def boost_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        script: Script,
    ) -> Message:
        """
        Add a boost message to a channel.
        """
        template, flags = await Flags().find(ctx, script.script)
        if not template:
            return await ctx.warn("You must provide a greet message!")

        records = len(
            [
                record
                for record in await self.bot.db.fetch(
                    """
                    SELECT channel_id
                    FROM boost_message
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                )
                if ctx.guild.get_channel_or_thread(record["channel_id"])
            ]
        )
        if records >= 2:
            return await ctx.warn("You can't have more than `2` boost messages!")

        await self.bot.db.execute(
            """
            INSERT INTO boost_message (
                guild_id,
                channel_id,
                template,
                delete_after
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, channel_id)
            DO UPDATE SET
                template = EXCLUDED.template,
                delete_after = EXCLUDED.delete_after
            """,
            ctx.guild.id,
            channel.id,
            template,
            flags.delete_after,
        )

        return await ctx.approve(
            f"Added boost message to {channel.mention}",
            *(
                [
                    f"The message will be deleted after **{format_timespan(flags.delete_after)}**"
                ]
                if flags.delete_after
                else []
            ),
        )

    @boost.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#boosts",
    )
    @has_permissions(manage_guild=True)
    async def boost_remove(self, ctx: Context, channel: TextChannel) -> Message:
        """
        Remove an existing boost message.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM boost_message
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"A boost message in {channel.mention} doesn't exist!"
            )

        return await ctx.approve(
            f"No longer sending boost messages in {channel.mention}"
        )

    @boost.command(
        name="view",
        aliases=["show"],
        example="#boosts",
    )
    @has_permissions(manage_guild=True)
    async def boost_view(self, ctx: Context, channel: TextChannel) -> Message:
        """
        View an existing boost message.
        """

        template = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT template
                FROM boost_message
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if not template:
            return await ctx.warn(
                f"A boost message in {channel.mention} doesn't exist!"
            )

        script = Script(template, [ctx.guild, ctx.author, channel])
        await ctx.send(codeblock(script))

        result = await self.bot.embed_build.alt_convert(ctx.author, template)
        await ctx.send(
            result.get("content"),
            embed=result.get("embed"),
            view=result.get("view"),
            delete_after=result.get("delete_after"),
        )

    @boost.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_guild=True)
    async def boost_clear(self, ctx: Context) -> Message:
        """
        Remove all boost messages.
        """

        await ctx.prompt(
            "Are you sure you want to remove all boost messages?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM boost_message
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No boost messages exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):boost message}"
        )

    @boost.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def boost_list(self, ctx: Context) -> Message:
        """
        View all boost channels.
        """

        channels = [
            f"{channel.mention} (`{channel.id}`)"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id
                FROM boost_message
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No boost messages exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="Boost Channels"),
        )
        return await paginator.start()