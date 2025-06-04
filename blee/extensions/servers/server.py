# Standard library imports
import os
import sys
from asyncio import Lock, TimeoutError, sleep
from base64 import b64decode
from contextlib import suppress
from datetime import datetime
from io import BytesIO
from re import compile as re_compile
from tempfile import TemporaryDirectory
from typing import List, Literal, Optional

# Local imports
import config
# Third-party imports
from aiofiles import open as async_open
from discord import (AllowedMentions, CategoryChannel, Embed, File, Forbidden,
                     HTTPException, Member, Message, PartialMessage, Reaction,
                     Status, TextChannel, Thread, User)
from discord.ext.commands import (BucketType, Cog, Command, FlagConverter,
                                  MissingPermissions, Range, command, cooldown,
                                  flag, group, has_permissions,
                                  max_concurrency, param)
from discord.ext.tasks import loop
from discord.utils import (as_chunks, escape_markdown, escape_mentions, find,
                           format_dt, utcnow)
from jishaku.codeblocks import Codeblock, codeblock_converter
from loguru import logger as log
from munch import Munch
from orjson import dumps, loads
from tools import Bleed
from tools.client.context import Context
from tools.client.database.settings import Settings
from tools.converters.basic import (Command, Emoji, EmojiFinder, ImageFinder,
                                    TimeConverter)
from tools.converters.color import Color
from tools.converters.embed import EmbedScript, EmbedScriptValidator
from tools.converters.role import Role
from tools.utilities.checks import require_boost
from tools.utilities.process import ensure_future
from tools.utilities.regex import STRING
from tools.utilities.text import Plural, hash
from xxhash import xxh128_hexdigest
from yarl import URL


class Servers(Cog):
    def __init__(self, bot: Bleed):
        self.bot = bot

    # Listeners

    @Cog.listener("on_user_message")
    async def sticky_message_dispatcher(self, ctx: Context, message: Message):
        """Dispatch the sticky message event while waiting for the activity scheduler"""

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

    @Cog.listener("on_member_join")  # WELCOME MESSAGE
    async def welcome_message(self: "Servers", member: Member):
        """Send a welcome message for a member which joins the server"""
        for row in await self.bot.db.fetch(
            """
            SELECT * FROM join_messages
            WHERE guild_id = $1;
            """,
            member.guild.id,
        ):
            channel: TextChannel
            if not (channel := member.guild.get_channel(row["channel_id"])):
                continue

            # Get the message content and remove any self_destruct flags
            message_content = row["message"]
            if "--self_destruct" in message_content:
                message_content = message_content.split("--self_destruct")[0].strip()

            await ensure_future(
                EmbedScript(message_content).send(
                    channel,
                    bot=self.bot,
                    guild=member.guild,
                    channel=channel,
                    user=member,
                    allowed_mentions=AllowedMentions(
                        everyone=True,
                        users=True,
                        roles=True,
                        replied_user=False,
                    ),
                    delete_after=row.get("self_destruct"),
                )
            )

    @Cog.listener("on_member_remove")
    async def send_leave_message(self: "Servers", member: Member):
        for row in await self.bot.db.fetch(
            """
            SELECT * FROM leave_messages
            WHERE guild_id = $1;
            """,
            member.guild.id,
        ):
            channel: TextChannel
            if not (channel := member.guild.get_channel(row["channel_id"])):
                continue

            await ensure_future(
                EmbedScript(row["message"]).send(
                    channel,
                    bot=self.bot,
                    guild=member.guild,
                    channel=channel,
                    user=member,
                    allowed_mentions=AllowedMentions(
                        everyone=True,
                        users=True,
                        roles=True,
                        replied_user=False,
                    ),
                    delete_after=row.get("self_destruct"),
                )
            )

    @Cog.listener("on_member_boost")
    async def boost_message(self: "Servers", member: Member):
        """Send a boost message for a member which boosts the server and assign baserole if available"""
        # Try to assign the baserole if it exists
        baserole_id = await self.bot.db.fetchval(
            "SELECT baserole FROM settings WHERE guild_id = $1",
            member.guild.id,
        )
        if baserole_id and (role := member.guild.get_role(baserole_id)):
            try:
                await member.add_roles(role, reason="Member boosted server")
            except Forbidden:
                pass  # Silently fail if bot doesn't have permission

        # Send boost messages
        for row in await self.bot.db.fetch(
            """
            SELECT * FROM boost_messages
            WHERE guild_id = $1;
            """,
            member.guild.id,
        ):
            channel: TextChannel
            if not (channel := member.guild.get_channel(row["channel_id"])):
                continue

            await ensure_future(
                EmbedScript(row["message"]).send(
                    channel,
                    bot=self.bot,
                    guild=member.guild,
                    channel=channel,
                    user=member,
                    allowed_mentions=AllowedMentions(
                        everyone=True,
                        users=True,
                        roles=True,
                        replied_user=False,
                    ),
                    delete_after=row.get("self_destruct"),
                )
            )

    @Cog.listener("on_member_join")  # AUTOROLE GRANT
    async def autorole_assigning(self: "Servers", member: Member):
        """Assign roles to a member which joins the server"""
        roles = [
            member.guild.get_role(row.get("role_id"))
            for row in await self.bot.db.fetch(
                "SELECT role_id, humans, bots FROM auto_roles WHERE guild_id = $1",
                member.guild.id,
            )
            if member.guild.get_role(row.get("role_id"))
            and member.guild.get_role(row.get("role_id")).is_assignable()
            and (row.get("humans") is None or member.bot is False)
            and (row.get("bots") is None or row.get("bots") == member.bot)
        ]
        if roles:
            with suppress(HTTPException):
                await member.add_roles(*roles, reason="Role Assignment", atomic=False)

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
        example="#chat Hi {user.mention} <3",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def welcome_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: str,
    ):
        """Add a welcome message for a channel"""
        # Parse self_destruct from message if present
        self_destruct = None
        message_content = message

        if "--self_destruct" in message:
            try:
                # Split message into content and self_destruct parts
                parts = message.split("--self_destruct")
                message_content = parts[0].strip()
                self_destruct = int(parts[1].strip())

                if self_destruct < 6 or self_destruct > 120:
                    return await ctx.warn(
                        "The **self destruct** time must be between **6** and **120** seconds"
                    )
            except (IndexError, ValueError):
                return await ctx.warn(
                    "Invalid self_destruct format. Example: --self_destruct 10"
                )

        # Convert message content to EmbedScript
        try:
            embed_message = await EmbedScriptValidator().convert(ctx, message_content)
        except Exception as e:
            return await ctx.warn(f"Invalid message format: {str(e)}")

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
                str(embed_message),
                self_destruct,
            )
        except Exception:
            return await ctx.warn(
                f"There is already a **welcome message** for {channel.mention}"
            )

        await ctx.approve(
            f"Created {embed_message.type(bold=False)} **welcome message** for {channel.mention}"
            + (
                f"\n> Which will self destruct after **{Plural(self_destruct):second}**"
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
        example="#channel hello",
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
        example="#general Hi --schedule 30s",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: str,
    ):
        """Add a sticky message for a channel"""

        # Parse schedule and message content
        schedule = None
        message_content = message

        if "--schedule" in message:
            try:
                # Split message into content and schedule parts
                parts = message.split("--schedule")
                message_content = parts[0].strip()
                schedule_str = parts[1].strip().split()[0]

                schedule = await TimeConverter().convert(ctx, schedule_str)
                if schedule.seconds < 30 or schedule.seconds > 3600:
                    return await ctx.warn(
                        "The **activity schedule** must be between **30 seconds** and **1 hour**"
                    )
            except (IndexError, ValueError):
                return await ctx.warn(
                    "Invalid schedule format. Example: --schedule 30s"
                )

        # Convert message content to EmbedScript
        try:
            embed_message = await EmbedScriptValidator().convert(ctx, message_content)
        except Exception as e:
            return await ctx.warn(f"Invalid message format: {str(e)}")

        _message = await embed_message.send(
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
                str(embed_message),
                schedule.seconds if schedule else None,
            )
        except:  # noqa: E722
            return await ctx.warn(
                f"There is already a **sticky message** for {channel.mention}"
            )

        await ctx.approve(
            f"Created {embed_message.type(bold=False)} [**sticky message**]({_message.jump_url}) for {channel.mention}"
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
            return await ctx.warn(f"No **sticky message** exists for {channel.mention}")

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

    @group(
        name="welcome",
        usage="(subcommand) <args>",
        example="add #hi Hi {user.mention}! --self_destruct 10",
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
        example="#chat Hi {user.mention} <3",
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
                f"\n> Which will self destruct after **{Plural(self_destruct):second}**"
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
        example="#general",
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
        name="goodbye",
        usage="(subcommand) <args>",
        example="add #goodbye See you soon! {user}",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def goodbye(self: "Servers", ctx: Context):
        """Set up goodbye messages in one or multiple channels"""
        await ctx.send_help()

    @goodbye.command(
        name="add",
        usage="(channel) (message)",
        example="#goodbye See you soon! {user}",
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
    async def goodbye_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: EmbedScriptValidator,
    ):
        """Add a goodbye message for a channel"""
        self_destruct = ctx.parameters.get("self_destruct")

        try:
            await self.bot.db.execute(
                "INSERT INTO leave_messages VALUES($1, $2, $3, $4)",
                ctx.guild.id,
                channel.id,
                str(message),
                self_destruct,
            )
        except Exception:
            return await ctx.warn(
                f"There is already a **goodbye message** for {channel.mention}"
            )

        return await ctx.approve(
            f"Created {message.type(bold=False)} **goodbye message** for {channel.mention}"
            + (
                f"\n> Which will self destruct after {Plural(self_destruct, bold=True):second}"
                if self_destruct
                else ""
            )
        )

    @goodbye.command(
        name="remove",
        usage="(channel)",
        example="#chat",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def goodbye_remove(
        self: "Servers", ctx: Context, channel: TextChannel | Thread
    ):
        """Remove a goodbye message for a channel"""
        ctx.parameters.get("self_destruct")

        if not await self.bot.db.fetchrow(
            "SELECT * FROM leave_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.warn(
                f"There isn't a **goodbye message** for {channel.mention}"
            )

        await self.bot.db.execute(
            "DELETE FROM leave_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )

        return await ctx.approve(
            f"Removed the **goodbye message** for {channel.mention}"
        )

    @goodbye.command(
        name="view",
        usage="(channel)",
        example="#general",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def goodbye_view(
        self: "Servers", ctx: Context, channel: TextChannel | Thread
    ):
        """View a goodbye message for a channel"""
        data = await self.bot.db.fetchrow(
            "SELECT message, self_destruct FROM leave_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        if not data:
            return await ctx.warn(
                f"There isn't a **goodbye message** for {channel.mention}"
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

    @goodbye.command(
        name="reset",
        aliases=["clear"],
    )
    @has_permissions(manage_guild=True)
    async def goodbye_reset(self: "Servers", ctx: Context):
        """Reset all goodbye channels"""
        await ctx.prompt("Are you sure you want to remove all **goodbye channels**?")

        try:
            await self.bot.db.execute(
                "DELETE FROM leave_messages WHERE guild_id = $1", ctx.guild.id
            )
        except Exception:
            return await ctx.warn("No **goodbye channels** have been set up")

        return await ctx.approve("Removed all **goodbye channels**")

    @goodbye.command(name="list")
    @has_permissions(manage_guild=True)
    async def goodbye_list(self: "Servers", ctx: Context):
        """View all goodbye channels"""
        channels = [
            self.bot.get_channel(row["channel_id"]).mention
            for row in await self.bot.db.fetch(
                "SELECT channel_id FROM leave_messages WHERE guild_id = $1",
                ctx.guild.id,
            )
            if self.bot.get_channel(row["channel_id"])
        ]

        if not channels:
            return await ctx.warn("No **goodbye channels** have been set up")

        await ctx.paginate(
            Embed(title="Goodbye Channels", description="\n".join(channels))
        )

    @goodbye.command(name="variables")
    @has_permissions(manage_guild=True)
    async def goodbye_variables(self: "Servers", ctx: Context):
        """View all goodbye variables"""
        await ctx.utility(
            f"You can view all **Variables** here:\n "
            f"{config.Bleed.docs}/resources/goodbye-variables",
            emoji="ℹ️",
        )

    @group(
        name="boost",
        usage="(subcommand) <args>",
        example="add #chat Thx {user.mention} :3",
        aliases=["bst"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def boost(self: "Servers", ctx: Context):
        """Set up boost messages in one or multiple channels"""
        await ctx.send_help()

    @boost.command(
        name="add",
        usage="(channel) (message)",
        example="#chat Thx {user.mention} :3",
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
    async def boost_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        message: EmbedScriptValidator,
    ):
        """Add a boost message for a channel"""
        self_destruct = ctx.parameters.get("self_destruct")

        try:
            await self.bot.db.execute(
                "INSERT INTO boost_messages VALUES($1, $2, $3, $4)",
                ctx.guild.id,
                channel.id,
                str(message),
                self_destruct,
            )
        except Exception:
            return await ctx.warn(
                f"There is already a **boost message** for {channel.mention}"
            )

        return await ctx.approve(
            f"Created {message.type(bold=False)} **boost message** for {channel.mention}"
            + (
                f"\n> Which will self destruct after {Plural(self_destruct, bold=True):second}"
                if self_destruct
                else ""
            )
        )

    @boost.command(
        name="remove",
        usage="(channel)",
        example="#chat",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def boost_remove(
        self: "Servers", ctx: Context, channel: TextChannel | Thread
    ):
        """Remove a boost message for a channel"""
        try:
            await self.bot.db.execute(
                "DELETE FROM boost_messages WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
        except Exception:
            return await ctx.warn(
                f"There isn't a **boost message** for {channel.mention}"
            )

        return await ctx.approve(f"Removed the **boost message** for {channel.mention}")

    @boost.command(
        name="view",
        usage="(channel)",
        example="#chat",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def boost_view(self: "Servers", ctx: Context, channel: TextChannel | Thread):
        """View a boost message for a channel"""
        data = await self.bot.db.fetchrow(
            "SELECT message, self_destruct FROM boost_messages WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        )
        if not data:
            return await ctx.warn(
                f"There isn't a **boost message** for {channel.mention}"
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

    @boost.command(
        name="reset",
        aliases=["clear"],
    )
    @has_permissions(manage_guild=True)
    async def boost_reset(self: "Servers", ctx: Context):
        """Reset all boost channels"""
        await ctx.prompt("Are you sure you want to remove all **boost channels**?")

        try:
            await self.bot.db.execute(
                "DELETE FROM boost_messages WHERE guild_id = $1", ctx.guild.id
            )
        except Exception:
            return await ctx.warn("No **boost channels** have been set up")

        return await ctx.approve("Removed all **boost channels**")

    @group(
        name="boosterrole",
        usage="(color) <name>",
        example="ff0000 sexy",
        aliases=["boostrole", "br"],
        brief="Booster Only",
        invoke_without_command=True,
    )
    @require_boost()
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 3, BucketType.member)
    async def boosterrole(
        self,
        ctx: Context,
        color: Color,
        *,
        name: str = None,
    ):
        """Create your own color role"""
        base_role = ctx.guild.get_role(
            await self.bot.db.fetchval(
                "SELECT baserole FROM settings WHERE guild_id = $1", ctx.guild.id
            )
        )
        if not base_role:
            return await ctx.warn(
                f"The **base role** has not been set yet!\n> Use `{ctx.prefix}boosterrole base` to set it"
            )

        role_id = await self.bot.db.fetchval(
            "SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        if not role_id or not ctx.guild.get_role(role_id):
            if len(ctx.guild.roles) >= 250:
                return await ctx.warn("The **role limit** has been reached")

            role = await ctx.guild.create_role(
                name=(name[:100] if name else f"booster:{hash(ctx.author.id)}"),
                color=color,
            )
            await ctx.guild.edit_role_positions(
                {
                    role: base_role.position - 1,
                }
            )

            try:
                await ctx.author.add_roles(role, reason="Booster role")
            except Forbidden:
                await role.delete(reason="Booster role failed to assign")
                return await ctx.warn(
                    "I don't have permission to **assign roles** to you"
                )

            await self.bot.db.execute(
                "INSERT INTO booster_roles (guild_id, user_id, role_id) VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id) DO UPDATE SET role_id"
                " = $3",
                ctx.guild.id,
                ctx.author.id,
                role.id,
            )
        else:
            role = ctx.guild.get_role(role_id)
            await role.edit(
                name=(name[:100] if name else role.name),
                color=color,
            )
            if role not in ctx.author.roles:
                try:
                    await ctx.author.add_roles(role, reason="Booster role")
                except Forbidden:
                    await role.delete(reason="Booster role failed to assign")
                    return await ctx.warn(
                        "I don't have permission to **assign roles** to you"
                    )

        await ctx.neutral(
            f"Your **booster role color** has been set to `{color}`",
            emoji="🎨",
            color=color,
        )

    @boosterrole.command(
        name="baserole",
        usage="(role)",
        example="Booster",
        aliases=["base"],
    )
    @has_permissions(manage_roles=True)
    async def boosterrole_baserole(self: "Servers", ctx: Context, *, role: Role):
        """Set the base role for booster roles"""
        await Role().manageable(ctx, role, booster=True)

        await self.bot.db.execute(
            """
            INSERT INTO settings (
                guild_id,
                baserole
            ) VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET
                baserole = EXCLUDED.baserole;
            """,
            ctx.guild.id,
            role.id,
        )

        await ctx.approve(f"Set the **base role** to {role.mention}")

    @boosterrole.command(
        name="color",
        usage="(color)",
        example="#BBAAEE",
        aliases=["colour"],
    )
    @require_boost()
    async def boosterrole_color(self: "Servers", ctx: Context, *, color: Color):
        """Change the color of your booster role"""
        role_id = await self.bot.db.fetchval(
            "SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        if not role_id or not ctx.guild.get_role(role_id):
            return await self.bot.get_command("boosterrole")(ctx, color=color)

        role = ctx.guild.get_role(role_id)
        await role.edit(
            color=color,
        )
        await ctx.neutral(
            f"Changed the **color** of your **booster role** to `{color}`",
            emoji="🎨",
        )

    @boosterrole.command(
        name="rename",
        usage="(name)",
        example="4PF",
        aliases=["name"],
    )
    @require_boost()
    async def boosterrole_rename(self: "Servers", ctx: Context, *, name: str):
        """Rename your booster role"""
        role_id = await self.bot.db.fetchval(
            "SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        if not role_id or not ctx.guild.get_role(role_id):
            return await ctx.warn("You don't have a **booster role** yet")

        role = ctx.guild.get_role(role_id)
        await role.edit(
            name=name[:100],
        )
        await ctx.approve(f"Renamed your **booster role** to **{name}**")

    @boosterrole.command(
        name="cleanup",
        parameters={
            "boosters": {
                "require_value": False,
                "description": "Whether to include boosters",
                "aliases": ["all"],
            }
        },
        aliases=["clean", "purge"],
    )
    @has_permissions(manage_roles=True)
    @cooldown(1, 60, BucketType.guild)
    @max_concurrency(1, BucketType.guild)
    async def boosterrole_cleanup(self: "Servers", ctx: Context):
        """Clean up booster roles which aren't boosting"""
        if ctx.parameters.get("boosters"):
            await ctx.prompt(
                "Are you sure you want to **remove all booster roles** in this server?\n> This includes members which are still **boosting** the"
                " server!"
            )

        async with ctx.typing():
            cleaned = []
            for row in await self.bot.db.fetch(
                "SELECT * FROM booster_roles WHERE guild_id = $1", ctx.guild.id
            ):
                member = ctx.guild.get_member(row["user_id"])
                role = ctx.guild.get_role(row["role_id"])
                if not role:
                    cleaned.append(row)
                    continue
                if ctx.parameters.get("boosters"):
                    with suppress(HTTPException):
                        await role.delete(reason=f"Booster role cleanup ({ctx.author})")

                    cleaned.append(row)
                elif not member or not member.premium_since:
                    with suppress(HTTPException):
                        await role.delete(reason="Member no longer boosting")

                    cleaned.append(row)
                elif role not in member.roles:
                    with suppress(HTTPException):
                        await role.delete(reason="Member doesn't have role")

                    cleaned.append(row)

            if cleaned:
                await self.bot.db.execute(
                    "DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = ANY($2)",
                    ctx.guild.id,
                    [row["user_id"] for row in cleaned],
                )
                return await ctx.approve(
                    f"Cleaned up **{Plural(cleaned):booster role}**"
                )

        await ctx.warn("There are no **booster roles** to clean up")

    @boosterrole.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @require_boost()
    async def boosterrole_remove(self: "Servers", ctx: Context):
        """Remove your booster role"""
        role_id = await self.bot.db.fetchval(
            "SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        if not role_id or not ctx.guild.get_role(role_id):
            return await ctx.warn("You don't have a **booster role** yet")

        role = ctx.guild.get_role(role_id)
        await role.delete(reason="Booster role removed")
        await self.bot.db.execute(
            "DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        await ctx.approve("Removed your **booster role**")

    @boosterrole.command(
        name="icon",
        usage="(icon)",
        example="🦅",
        aliases=["emoji"],
    )
    @require_boost()
    async def boosterrole_icon(
        self,
        ctx: Context,
        *,
        icon: Literal["remove", "reset", "off"] | EmojiFinder | ImageFinder = None,
    ):
        """Change the icon of your booster role"""
        if "ROLE_ICONS" not in ctx.guild.features:
            return await ctx.warn(
                "This server doesn't have enough **boosts** to use **role icons**"
            )
        if not icon:
            icon = await ImageFinder.search(ctx)
        elif isinstance(icon, str) and icon in ("remove", "reset", "off"):
            icon = None

        role_id = await self.bot.db.fetchval(
            "SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        if not role_id or not ctx.guild.get_role(role_id):
            return await ctx.warn("You don't have a **booster role** yet")

        role = ctx.guild.get_role(role_id)

        _icon = None
        if type(icon) in (Emoji, str):
            response = await self.bot.session.get(
                icon.url if isinstance(icon, Emoji) else icon
            )
            _icon = await response.read()
        elif not role.display_icon:
            return await ctx.warn("Your **booster role** doesn't have an **icon** yet")

        await role.edit(
            display_icon=_icon,
        )
        if icon:
            return await ctx.approve(
                f"Changed the **icon** of your **booster role** to {f'{icon}' if isinstance(icon, Emoji) else f'[**image**]({icon})'}"
            )

        return await ctx.approve("Removed the **icon** of your **booster role**")

    @group(
        name="autorole",
        usage="(subcommand) <args>",
        example="add (role)",
        aliases=["welcrole"],
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def autorole(self: "Servers", ctx: Context):
        """
        Set up automatic role assign on member join
        """
        await ctx.send_help()

    @autorole.command(
        name="add",
        usage="(role)",
        example="Member",
        parameters={
            "humans": {
                "require_value": False,
                "description": "Only assign the role to humans",
                "aliases": ["human"],
            },
            "bots": {
                "require_value": False,
                "description": "Only assign the role to bots",
                "aliases": ["bot"],
            },
        },
        aliases=["create"],
    )
    @has_permissions(manage_roles=True)
    async def autorole_add(self: "Servers", ctx: Context, role: Role):
        """Add a role to be assigned to new members"""
        if await self.bot.db.fetchval(
            "SELECT * FROM auto_roles WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        ):
            return await ctx.warn(
                f"The role {role.mention} is already being **assigned** to new members"
            )

        await Role().manageable(ctx, role)
        if not ctx.parameters.get("bots"):
            await Role().dangerous(ctx, role, "assign")

        await self.bot.db.execute(
            "INSERT INTO auto_roles (guild_id, role_id, humans, bots) VALUES ($1, $2, $3, $4)",
            ctx.guild.id,
            role.id,
            ctx.parameters.get("humans"),
            ctx.parameters.get("bots"),
        )

        return await ctx.approve(
            f"Now assigning {role.mention} to new members"
            + (" (humans)" if ctx.parameters.get("humans") else "")
            + (" (bots)" if ctx.parameters.get("bots") else "")
        )

    @autorole.command(
        name="remove",
        usage="(role)",
        example="Member",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_roles=True)
    async def autorole_remove(self: "Servers", ctx: Context, *, role: Role):
        """Remove a role from being assigned to new members"""
        if not await self.bot.db.fetchval(
            "SELECT * FROM auto_roles WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        ):
            return await ctx.warn(
                f"The role {role.mention} is not being **assigned** to new members"
            )

        await self.bot.db.execute(
            "DELETE FROM auto_roles WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        )

        await ctx.approve(f"No longer assigning {role.mention} to new members")

    @autorole.command(name="reset", aliases=["clear"])
    @has_permissions(manage_roles=True)
    async def autorole_reset(self: "Servers", ctx: Context):
        """Remove every role which is being assigned to new members"""
        if not await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM auto_roles WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.utility("No **auto roles** found", emoji="🔍")

        await ctx.prompt("Are you sure you want to remove all **auto roles**?")

        await self.bot.db.execute(
            "DELETE FROM auto_roles WHERE guild_id = $1",
            ctx.guild.id,
        )
        await ctx.approve("No longer **assigning** any **auto roles**")

    @autorole.command(name="list", aliases=["show", "all"])
    @has_permissions(manage_roles=True)
    async def autorole_list(self: "Servers", ctx: Context):
        """View all the roles being assigned to new members"""
        roles = [
            ctx.guild.get_role(row.get("role_id")).mention
            + (" (humans)" if row.get("humans") else "")
            + (" (bots)" if row.get("bots") else "")
            for row in await self.bot.db.fetch(
                "SELECT role_id, humans, bots FROM auto_roles WHERE guild_id = $1",
                ctx.guild.id,
            )
            if ctx.guild.get_role(row.get("role_id"))
        ]
        if not roles:
            return await ctx.utility("No **auto roles** found", emoji="🔍")

        await ctx.paginate(
            [  # Wrap the Embed in a list
                Embed(
                    title=f"Auto Roles ({len(roles)})",  # Add count to title
                    description="\n".join(
                        f"`{i+1}` {role}" for i, role in enumerate(roles)
                    ),  # Add index numbers
                )
            ]
        )
