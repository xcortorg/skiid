import os
import sys
from asyncio import Lock, TimeoutError, sleep
from base64 import b64decode
from contextlib import suppress
from datetime import datetime
from io import BytesIO
from re import compile as re_compile
from tempfile import TemporaryDirectory
from typing import List, Optional

import config
from aiofiles import open as async_open
from discord import (CategoryChannel, Embed, File, Forbidden, HTTPException,
                     Member, Message, PartialMessage, Reaction, Status,
                     TextChannel, Thread, User)
from discord.ext.commands import (BucketType, Cog, MissingPermissions, Range,
                                  command, cooldown, flag, group,
                                  has_permissions, max_concurrency, param)
from discord.ext.tasks import loop
from discord.utils import (as_chunks, escape_markdown, escape_mentions, find,
                           format_dt, utcnow)
from jishaku.codeblocks import Codeblock, codeblock_converter
from munch import Munch
from orjson import dumps, loads
from tools import Bleed
from tools.client.context import Context
from tools.client.database.settings import Settings
from tools.converters.basic import (Command, ImageFinderStrict, Language,
                                    SynthEngine, TimeConverter)
from tools.converters.embed import EmbedScript, EmbedScriptValidator
from tools.utilities import donator, require_dm, shorten
from tools.utilities.humanize import human_timedelta
from tools.utilities.process import ensure_future
from tools.utilities.regex import STRING
from tools.utilities.text import Plural, hash
from xxhash import xxh128_hexdigest
from yarl import URL


class Servers(Cog):
    def __init__(self, bot: Bleed):
        self.bot = bot

    @Cog.listener("on_user_message")
    async def sticky_message_dispatcher(self, ctx: Context, message: Message):
        """
        Dispatch the sticky message event while waiting for the activity scheduler
        """

        data = await self.bot.db.fetchrow(
            "SELECT * FROM sticky_messages WHERE guild_id = $1 AND channel_id = $2",
            message.guild.id,
            message.channel.id,
        )
        if not data:
            return

        if data["message_id"] == message.id:
            return

        key = hash(f"{message.guild.id}:{message.channel.id}")
        if not self.bot.sticky_locks.get(key):
            self.bot.sticky_locks[key] = Lock()
        bucket = self.bot.sticky_locks.get(key)

        async with bucket:
            try:
                await self.bot.wait_for(
                    "message",
                    check=lambda m: m.channel == message.channel,
                    timeout=data.get("schedule") or 0,
                )
            except TimeoutError:
                pass
            else:
                return

            with suppress(HTTPException):
                await message.channel.get_partial_message(data["message_id"]).delete()

            message = await ensure_future(
                EmbedScript(data["message"]).send(
                    message.channel,
                    bot=self.bot,
                    guild=message.guild,
                    channel=message.channel,
                    user=message.author,
                )
            )
            await self.bot.db.execute(
                "UPDATE sticky_messages SET message_id = $3 WHERE guild_id = $1 AND channel_id = $2",
                message.guild.id,
                message.channel.id,
                message.id,
            )

    @group(name="prefix", invoke_without_command=True)
    async def prefix(self, ctx: Context) -> Message:
        """View guild prefix"""

        settings = await Settings.fetch(self.bot, ctx.guild)

        return await ctx.utility(f"Server Prefix: `{settings.prefix}`")

    @prefix.command(
        name="self",
        usage="(prefix)",
        brief="Tier 2 Only",
        example="j",
    )
    async def prefix_self(self, ctx: Context, prefix: str) -> Message:
        """
        Set personal prefix across all servers with Bleed
        """

        if prefix.lower() == "remove":
            await Settings.remove_self_prefix(self.bot, ctx.author)
            return await ctx.approve("Removed your **self prefix**")

        if len(prefix) > 5:
            return await ctx.warn(
                "Your **prefix** cannot be longer than **5 characters**!"
            )

        await Settings.set_self_prefix(self.bot, ctx.author, prefix.lower())
        return await ctx.approve(f"**self prefix** updated to `{prefix.lower()}`")

    @prefix.command(
        name="set",
        usage="(prefix)",
        example="!",
        aliases=["add"],
    )
    @has_permissions(administrator=True)
    async def prefix_set(self, ctx: Context, prefix: str) -> Message:
        """Set command prefix for guild"""

        if len(prefix) > 5:
            return await ctx.warn(
                "Your **prefix** cannot be longer than **5 characters**!"
            )

        # Ensure the prefix is stored and displayed properly
        prefix = prefix.lower()

        try:
            settings = await Settings.create_or_update(self.bot, ctx.guild, prefix)

            if settings.prefix != prefix:
                return await ctx.warn(
                    f"Failed to update prefix. Current: `{settings.prefix}`, Attempted: `{prefix}`"
                )

            return await ctx.approve(f"**Server prefix** updated to `{prefix}`")

        except Exception as e:
            return await ctx.warn(f"Failed to update prefix: {str(e)}")

    @prefix.command(
        name="remove",
        aliases=["delete", "del", "clear"],
    )
    @has_permissions(administrator=True)
    async def prefix_remove(self, ctx: Context) -> Message:
        """Remove command prefix for guild"""

        settings = await Settings.fetch(self.bot, ctx.guild)

        # Check if prefix is already default
        if settings.prefix == config.Bleed.prefix:
            return await ctx.warn(
                f"Your server doesn't have a prefix set! Set it using `@{self.bot.user} prefix add <prefix>`"
            )

        await settings.update(prefix=config.Bleed.prefix)
        return await ctx.approve(
            f"Your guild's prefix has been **removed**. You can set a **new prefix** using `@{self.bot.user} prefix add (prefix)`"
        )

    @group(
        name="welcome",
        usage="(subcommand) <args>",
        example="#hi Hi {user.mention}! --\n self_destruct 10",
        aliases=["welc"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def welcome(self: "Servers", ctx: Context):
        """Set up welcome messages in one or multiple channels"""
        await ctx.send_help()

    @welcome.command(
        name="add",
        usage="(channel) (message)",
        example="#hi Hi {user.mention}! --self_destruct 10",
        parameters={
            "self_destruct": {
                "converter": int,
                "description": "The amount of seconds to wait before deleting the message",
                "minimum": 6,
                "maximum": 120,
                "aliases": ["delete_after", "delete"],
            }
        },
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: EmbedScriptValidator,
    ):
        """Add a welcome message for a channel"""
        self_destruct = ctx.parameters.get("self_destruct")

        try:
            await self.bot.db.execute(
                """
                    INSERT INTO join_messages (
                    guild_id,
                    channel_id,
                    message,
                    self_destruct
                ) VALUES ($1, $2, $3, $4);""",
                ctx.guild.id,
                channel.id,
                str(message),
                self_destruct,
            )
        except Exception:
            return await ctx.warn(
                f"There is already a **welcome message** for {channel.mention}"
            )

        await ctx.approve(
            f"Created {message.type(bold=False)} **welcome message** for {channel.mention}"
            + (
                f"\n> Which will self destruct after {Plural(self_destruct, bold=True):second}"
                if self_destruct
                else ""
            )
        )

    @welcome.command(
        name="remove",
        usage="(channel)",
        example="#general",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_remove(
        self: "Servers", ctx: Context, channel: TextChannel | Thread
    ):
        """Remove a welcome message for a channel"""
        try:
            await self.bot.db.execute(
                "DELETE FROM join_messages WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
        except Exception:
            return await ctx.warn(
                f"There isn't a **welcome message** for {channel.mention}"
            )

        return await ctx.approve(
            f"Removed the **welcome message** for {channel.mention}"
        )

    @welcome.command(
        name="view",
        usage="(channel)",
        example="#chat",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_view(
        self: "Servers", ctx: Context, channel: TextChannel | Thread
    ):
        """View a welcome message for a channel"""
        data = await self.bot.db.fetchrow(
            "SELECT message, self_destruct FROM join_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        if not data:
            return await ctx.warn(
                f"There isn't a **welcome message** for {channel.mention}"
            )

        message = data.get("message")
        self_destruct = data.get("self_destruct")

        await EmbedScript(message).send(
            ctx.channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
            delete_after=self_destruct,
        )

    @welcome.command(
        name="reset",
        aliases=["clear"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_reset(self: "Servers", ctx: Context):
        """Reset all welcome channels"""
        await ctx.prompt("Are you sure you want to remove all **welcome channels**?")

        try:
            await self.bot.db.execute(
                "DELETE FROM join_messages WHERE guild_id = $1", ctx.guild.id
            )
        except Exception:
            return await ctx.warn("No **welcome channels** have been set up")

        return await ctx.approve("Removed all **welcome channels**")

    @welcome.command(name="list")
    @has_permissions(manage_guild=True)
    async def welcome_list(self: "Servers", ctx: Context):
        """View all welcome channels"""
        channels = [
            self.bot.get_channel(row["channel_id"]).mention
            for row in await self.bot.db.fetch(
                "SELECT channel_id FROM join_messages WHERE guild_id = $1",
                ctx.guild.id,
            )
            if self.bot.get_channel(row["channel_id"])
        ]

        if not channels:
            return await ctx.warn("No **welcome channels** have been set up")

        await ctx.paginate(
            Embed(title="Welcome Channels", description="\n".join(channels))
        )

    @welcome.command(name="variables")
    @has_permissions(manage_guild=True)
    async def welcome_variables(self: "Servers", ctx: Context):
        """View all welcome variables"""
        await ctx.utility(
            f"You can view all **Variables** here:\n "
            f"{config.Bleed.docs}/resources/welcome-variables",
            emoji="ℹ️",
        )

    @group(
        name="alias",
        usage="(subcommand) <args>",
        example="add deport ban",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def alias(self: "Servers", ctx: Context):
        """Set a custom alias for commands"""
        await ctx.send_help()

    @alias.command(
        name="add",
        usage="(alias) (command)",
        example="deport ban",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def alias_add(self: "Servers", ctx: Context, alias: str, *, command: str):
        """Add a custom alias for a command"""
        alias = alias.lower().replace(" ", "")
        if self.bot.get_command(alias):
            return await ctx.warn(f"Command for alias `{alias}` already exists")

        _command = self.bot.get_command(STRING.match(command).group())
        if not _command:
            return await ctx.warn(f"Command `{command}` does not exist")

        if not await self.bot.db.fetchval(
            "SELECT * FROM aliases WHERE guild_id = $1 AND alias = $2",
            ctx.guild.id,
            alias,
        ):
            await self.bot.db.execute(
                "INSERT INTO aliases (guild_id, alias, command, invoke) VALUES ($1, $2, $3, $4)",
                ctx.guild.id,
                alias,
                _command.qualified_name,
                command,
            )

            return await ctx.approve(f"Added alias `{alias}` for command `{_command}`")

        return await ctx.warn(f"Alias `{alias}` already exists")

    @alias.command(
        name="remove",
        usage="(alias)",
        example="deport",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def alias_remove(self: "Servers", ctx: Context, alias: str):
        """Remove a bound alias"""
        alias = alias.lower().replace(" ", "")

        if not await self.bot.db.fetchval(
            "SELECT * FROM aliases WHERE guild_id = $1 AND alias = $2",
            ctx.guild.id,
            alias,
        ):
            return await ctx.warn(f"Alias `{alias}` doesn't exist")

        await self.bot.db.execute(
            "DELETE FROM aliases WHERE guild_id = $1 AND alias = $2",
            ctx.guild.id,
            alias,
        )

        await ctx.approve(f"Removed alias `{alias}`")

    @alias.command(
        name="reset",
        usage="<command>",
        example="ban",
        aliases=["clear"],
    )
    @has_permissions(manage_guild=True)
    async def alias_reset(self: "Servers", ctx: Context, *, command: Command = None):
        """Remove every bound alias"""
        if not command:
            await ctx.prompt("Are you sure you want to remove all bound **aliases**?")
            await self.bot.db.execute(
                "DELETE FROM aliases WHERE guild_id = $1",
                ctx.guild.id,
            )
            return await ctx.approve("Reset all **aliases**")

        if not await self.bot.db.fetchval(
            "SELECT * FROM aliases WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            command.qualified_name,
        ):
            return await ctx.warn(f"There aren't any aliases for command `{command}`")

        await ctx.prompt(
            f"Are you sure you want to remove all bound **aliases** for `{command.qualified_name}`?"
        )

        await self.bot.db.execute(
            "DELETE FROM aliases WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            command.qualified_name,
        )

        await ctx.approve(f"Reset all **aliases** for `{command.qualified_name}`")

    @alias.command(
        name="list",
        usage="<command>",
        example="ban",
        aliases=["all"],
    )
    @has_permissions(manage_guild=True)
    async def alias_list(self: "Servers", ctx: Context, *, command: Command = None):
        """View all bound aliases"""
        if command:
            aliases = [
                f"`{row['alias']}` bound to `{row['command']}`"
                for row in await self.bot.db.fetch(
                    "SELECT alias, command FROM aliases WHERE guild_id = $1 AND command = $2",
                    ctx.guild.id,
                    command.qualified_name,
                )
                if not self.bot.get_command(row["alias"])
            ]
            if not aliases:
                return await ctx.warn(
                    f"No aliases have been **assigned** to command `{command.qualified_name}`"
                )

        aliases = [
            f"`{row['alias']}` bound to `{row['command']}`"
            for row in await self.bot.db.fetch(
                "SELECT alias, command FROM aliases WHERE guild_id = $1",
                ctx.guild.id,
            )
            if self.bot.get_command(row["command"])
            and not self.bot.get_command(row["alias"])
        ]
        if not aliases:
            return await ctx.warn("No aliases have been **assigned**")

        await ctx.paginate(
            Embed(title="Command Aliases", description="\n".join(aliases))
        )

    @alias.command(
        name="view",
        usage="(alias)",
        example="deport",
        aliases=["show", "check"],
    )
    @has_permissions(manage_guild=True)
    async def alias_view(self: "Servers", ctx: Context, alias: str):
        """View details about a specific alias"""
        alias = alias.lower().replace(" ", "")

        data = await self.bot.db.fetchrow(
            "SELECT command, invoke FROM aliases WHERE guild_id = $1 AND alias = $2",
            ctx.guild.id,
            alias,
        )

        if not data:
            return await ctx.warn(f"Alias `{alias}` doesn't exist")

        return await ctx.approve(
            f"Alias `{alias}` is bound to command `{data['command']}`\n"
            f"Full command: `{data['invoke']}`"
        )

    @alias.command(
        name="removeall",
        usage="(command)",
        example="ban",
        aliases=["deleteall", "rmall"],
    )
    @has_permissions(manage_guild=True)
    async def alias_removeall(self: "Servers", ctx: Context, *, command: Command):
        """Remove all aliases for a specific command"""
        aliases = await self.bot.db.fetch(
            "SELECT alias FROM aliases WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            command.qualified_name,
        )

        if not aliases:
            return await ctx.warn(f"No aliases found for command `{command}`")

        await ctx.prompt(
            f"Are you sure you want to remove all **{len(aliases)} aliases** for `{command.qualified_name}`?"
        )

        await self.bot.db.execute(
            "DELETE FROM aliases WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            command.qualified_name,
        )

        alias_list = ", ".join(f"`{row['alias']}`" for row in aliases)
        return await ctx.approve(
            f"Removed {len(aliases)} aliases for `{command}`: {alias_list}"
        )

    @group(
        usage="(subcommand) <args>",
        example="add #channel hello",
        aliases=["sticky", "sm"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def stickymessage(self: "Servers", ctx: Context):
        """Set up sticky messages in one or multiple channels"""

        await ctx.send_help()

    @stickymessage.command(
        name="add",
        usage="(channel) (message)",
        example="#general Hi",
        aliases=["create"],
    )
    @flag(
        schedule=str,
        description="Waits until chat is inactive to repost the message",
        aliases=["timer", "time", "activity"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: EmbedScriptValidator,
        schedule: str = None,
    ):
        """Add a sticky message for a channel"""

        if schedule:
            schedule = await TimeConverter().convert(ctx, schedule)
            if schedule.seconds < 30 or schedule.seconds > 3600:
                return await ctx.warn(
                    "The **activity schedule** must be between **30 seconds** and **1 hour**"
                )

        _message = await message.send(
            channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=channel,
            user=ctx.author,
        )

        try:
            await self.bot.db.execute(
                "INSERT INTO sticky_messages (guild_id, channel_id, message_id, message, schedule) VALUES ($1, $2, $3, $4, $5)",
                ctx.guild.id,
                channel.id,
                _message.id,
                str(message),
                schedule.seconds if schedule else None,
            )
        except:  # noqa: E722
            return await ctx.warn(
                f"There is already a **sticky message** for {channel.mention}"
            )

        await ctx.approve(
            f"Created {message.type(bold=False)} [**sticky message**]({_message.jump_url}) for {channel.mention}"
            + (f" with an **activity schedule** of **{schedule}**" if schedule else "")
        )

    @stickymessage.command(
        name="remove",
        usage="(channel)",
        example="#general",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_remove(
        self: "Servers", ctx: Context, channel: TextChannel | Thread
    ):
        """Remove a sticky message for a channel"""

        if not await self.bot.db.fetchval(
            "SELECT * FROM sticky_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.warn(
                f"There isn't a **sticky message** for {channel.mention}"
            )

        await self.bot.db.execute(
            "DELETE FROM sticky_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        await ctx.approve(f"Removed the **sticky message** for {channel.mention}")

    @stickymessage.command(
        name="view",
        usage="(channel)",
        example="#general",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_view(self: "Servers", ctx: Context, channel: TextChannel | Thread):
        """View a sticky message for a channel"""

        data = await self.bot.db.fetchrow(
            "SELECT message FROM sticky_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        if not data:
            return await ctx.warn(
                f"There isn't a **sticky message** for {channel.mention}"
            )

        message = data.get("message")

        await EmbedScript(message).send(
            ctx.channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
        )

    @stickymessage.command(
        name="reset",
        aliases=["clear"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_reset(self: "Servers", ctx: Context):
        """Reset all sticky messages"""

        if not await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM sticky_messages WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.warn("No **sticky messages** have been set up")

        await ctx.prompt("Are you sure you want to remove all **sticky messages**?")

        await self.bot.db.execute(
            "DELETE FROM sticky_messages WHERE guild_id = $1",
            ctx.guild.id,
        )
        await ctx.approve("Removed all **sticky messages**")

    @stickymessage.command(
        name="list",
        aliases=["show", "all"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_list(self: "Servers", ctx: Context):
        """View all sticky messages"""

        messages = [
            f"{channel.mention} - [`{row['message_id']}`]({channel.get_partial_message(row['message_id']).jump_url})"
            for row in await self.bot.db.fetch(
                "SELECT channel_id, message_id FROM sticky_messages WHERE guild_id = $1",
                ctx.guild.id,
            )
            if (channel := self.bot.get_channel(row.get("channel_id")))
        ]
        if not messages:
            return await ctx.warn("No **sticky messages** have been set up")

        await ctx.paginate(
            Embed(
                title="Sticky Messages",
                description=messages,
            )
        )
