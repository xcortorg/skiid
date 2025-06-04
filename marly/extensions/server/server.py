# Standard library imports
from io import BytesIO
from typing import Optional, Literal, Union
from zipfile import ZipFile
from contextlib import suppress

# Third-party imports
from discord import (
    Embed,
    File,
    Role,
    TextChannel,
    Thread,
    HTTPException,
    AllowedMentions,
    Member,
    Message,
    Permissions,
    User,
)
from discord.ext.commands import (
    BucketType,
    Cog,
    Command,
    flag,
    BasicFlags,
    CommandError,
    UserConverter,
    Range,
    command,
    cooldown,
    group,
    has_permissions,
    parameter,
)
from typing import List
from loguru import logger as log
from discord.utils import format_dt, oauth_url
from asyncpg import UniqueViolationError
from typing import Optional, cast
from xxhash import xxh32_hexdigest
import asyncio
from discord.utils import utcnow
from humanfriendly import format_timespan

# Local imports
import config
from config import Color, Emojis, Marly
from system import Marly
from system.base.context import Context
from system.base.embed import EmbedScript
from system.base.settings import Settings
from system.tools.regex import STRING
from system.tools import ratelimiter
from system.tools.utils import vowel, codeblock, Plural, ensure_future
from system.base.embed import EmbedScriptValidator
from .invoke import invoke
from .welcome.welcome import Welcome
from system.tools.converters import CustomFlagConverter


class AutoroleFlags(BasicFlags):
    humans: bool = False
    bots: bool = False


class ResponseFlags(BasicFlags):
    self_destruct: Optional[int] = None
    not_strict: bool = False
    ignore_command_check: bool = False
    reply: bool = False
    delete: bool = False


class BoostFlags(CustomFlagConverter):
    delete_after: Range[int, 3, 120] = flag(
        aliases=["self_destruct"],
        description="Delete the message after a certain amount of time.",
        default=0,
    )


class Server(Welcome, invoke, Cog):
    def __init__(self, bot: "Marly"):
        self.bot = bot

    @Cog.listener("on_message")
    async def on_message(self, message: Message):
        """Respond to trigger words"""
        if message.author.bot:
            return

        if not message.guild:
            return

        if not message.content:
            return

        if ratelimiter(
            bucket=f"response_trigger:{message.author.id}",
            key=message.guild.id,
            rate=5,
            per=30,
        ):
            return

        message_content = message.content.lower()

        rows = await self.bot.db.fetch(
            "SELECT * FROM auto_responses WHERE guild_id = $1",
            message.guild.id,
        )

        for row in rows:
            trigger = row.get("trigger")

            if not trigger:
                continue

            if row.get("not_strict"):
                if trigger not in message_content:
                    continue
            else:
                if trigger != message_content:
                    continue

            await ensure_future(
                EmbedScript(row["response"]).send(
                    message.channel,
                    bot=self.bot,
                    guild=message.guild,
                    channel=message.channel,
                    user=message.author,
                    allowed_mentions=AllowedMentions(
                        everyone=True,
                        users=True,
                        roles=True,
                        replied_user=False,
                    ),
                    delete_after=row.get("self_destruct"),
                    reference=(message if row.get("reply") else None),
                )
            )

            if not row.get("reply") and row.get("delete"):
                with suppress(HTTPException):
                    await message.delete()

    @Cog.listener("on_message")
    async def sticky_listener(self, message: Message) -> None:
        """
        Stick messages to the bottom of a channel.
        We don't want to send sticky messages constantly, so we'll
        only send them if messages haven't been sent within 3 seconds.
        """

        if (
            not message.guild
            or message.author.bot
            or not isinstance(
                message.channel,
                (TextChannel, Thread),
            )
        ):
            return

        guild = message.guild
        channel = message.channel
        record = await self.bot.db.fetchrow(
            """
            SELECT message_id, template
            FROM sticky_message
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            guild.id,
            channel.id,
        )
        if not record:
            return

        key = xxh32_hexdigest(f"sticky:{channel.id}")
        locked = await self.bot.redis.get(key)
        if locked:
            return

        await self.bot.redis.set(key, 1, 6)
        last_message = channel.get_partial_message(record["message_id"])
        time_since = utcnow() - last_message.created_at
        time_to_wait = 6 - time_since.total_seconds()
        if time_to_wait > 1:
            await asyncio.sleep(time_to_wait)

        script = EmbedScript(record["template"])

        try:
            new_message = await script.send(
                channel,
                guild=guild,
                channel=channel,
                user=message.author,
            )
        except HTTPException:
            await self.bot.db.execute(
                """
                DELETE FROM sticky_message
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                guild.id,
                channel.id,
            )
        else:
            await self.bot.db.execute(
                """
                UPDATE sticky_message
                SET message_id = $3
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                guild.id,
                channel.id,
                new_message.id,
            )
        finally:
            await self.bot.redis.delete(key)
            await last_message.delete()

    ### auto role assigning
    @Cog.listener("on_member_join")
    async def autorole_assigning(self, member: Member):
        """Assign roles to a member which joins the server"""
        roles = [
            member.guild.get_role(row.get("role_id"))
            for row in await self.bot.db.fetch(
                "SELECT role_id, humans, bots FROM auto_roles WHERE guild_id = $1",
                member.guild.id,
            )
            if (
                # Make sure role still exists and is assignable
                member.guild.get_role(row.get("role_id"))
                and member.guild.get_role(row.get("role_id")).is_assignable()
                # Check humans flag: if humans=True, member must not be a bot
                and (row.get("humans") is None or member.bot is False)
                # Check bots flag: if bots=True, member must be a bot
                and (row.get("bots") is None or row.get("bots") == member.bot)
            )
        ]
        if roles:
            with suppress(HTTPException):
                await member.add_roles(*roles, reason="Role Assignment", atomic=False)

    @Cog.listener("on_member_boost")
    async def boost_send(self, member: Member) -> List[Message]:
        """
        Send the boost messages for the member.
        """
        guild = member.guild
        records = await self.bot.db.fetch(
            """
            SELECT channel_id, template, delete_after
            FROM boost_message
            WHERE guild_id = $1
            """,
            guild.id,
        )

        sent_messages: List[Message] = []
        scheduled_deletion: List[int] = []
        for record in records:
            channel_id = cast(
                int,
                record["channel_id"],
            )
            channel = cast(
                Optional[TextChannel | Thread],
                guild.get_channel_or_thread(channel_id),
            )
            if not channel:
                scheduled_deletion.append(channel_id)
                continue

            # Fixed: Use EmbedScript instead of Script
            script = EmbedScript(record["template"])
            try:
                message = await script.send(
                    channel,
                    guild=guild,
                    user=member,
                    channel=channel,
                    delete_after=(
                        record["delete_after"] if record["delete_after"] else None
                    ),
                )
            except HTTPException as exc:
                await self.notify_failure("boost", channel, member, script, exc)
                scheduled_deletion.append(channel_id)
            else:
                sent_messages.append(message)

        if scheduled_deletion:
            log.info(
                "Scheduled deletion of %s boost message%s for %s (%s).",
                len(scheduled_deletion),
                "s" if len(scheduled_deletion) > 1 else "",
                guild,
                guild.id,
            )

            await self.bot.db.execute(
                """
                DELETE FROM boost_message
                WHERE channel_id = ANY($1::BIGINT[])
                """,
                scheduled_deletion,
            )

        elif sent_messages:
            log.debug(
                f"Sent {len(sent_messages)} boost messages for {member.name} in {guild.name} ({guild.id})",
            )

        return sent_messages

    @group(name="prefix", invoke_without_command=True)
    async def prefix(self, ctx: Context) -> Message:
        """View guild prefix"""
        settings = await Settings.fetch(self.bot, ctx.guild)
        user_prefix = await settings.fetch_user_prefix(ctx.author.id)

        response = f"**Server** Prefix: `{settings.prefix}`"
        if user_prefix:
            response += f"\n> **Self** Prefix: `{user_prefix}`"

        return await ctx.utility(response)

    @prefix.command(
        name="self",
        usage="(prefix)",
        example="j",
    )
    async def prefix_self(self, ctx: Context, prefix: str) -> Message:
        """Set personal prefix across all servers"""
        settings = await Settings.fetch(self.bot, ctx.guild)

        if prefix.lower() == "remove":
            user_prefix = await settings.fetch_user_prefix(ctx.author.id)
            if not user_prefix:
                return await ctx.warn("You don't have a **self prefix** set to remove!")

            await settings.remove_self_prefix(ctx.author.id)
            return await ctx.approve("Removed your **self prefix**")

        if len(prefix) > 5:
            return await ctx.warn(
                "Your **prefix** cannot be longer than **5 characters**!"
            )

        await settings.update_user_prefix(ctx.author.id, prefix.lower())
        return await ctx.approve(f"**self prefix** updated to `{prefix.lower()}`")

    @prefix.command(
        name="set",
        usage="(prefix)",
        example="!",
        aliases=["add"],
    )
    @has_permissions(administrator=True)
    async def prefix_set(self, ctx: Context, prefix: str) -> Message:
        """Set command prefix for server"""
        if len(prefix) > 5:
            return await ctx.warn(
                "Your **prefix** cannot be longer than **5 characters**!"
            )

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
        """Remove command prefix for server"""
        settings = await Settings.fetch(self.bot, ctx.guild)

        if settings.prefix == config.Marly.PREFIX:
            return await ctx.warn(
                f"Your server doesn't have a prefix set! Set it using `@{self.bot.user} prefix add <prefix>`"
            )

        await settings.update(prefix=config.Marly.PREFIX)
        return await ctx.approve(
            f"Your guild's prefix has been **removed**. You can set a **new prefix** using `@{self.bot.user} prefix add (prefix)`"
        )

    @command()
    @has_permissions(manage_messages=True)
    async def pin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Pin the most recent message or by URL
        """

        message = message or ctx.replied_message
        if not message:
            async for message in ctx.channel.history(limit=1, before=ctx.message):
                break

        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.warn("That **message** is not in this server")

        elif message.pinned:
            return await ctx.warn(
                f"That [**`message`**]({message.jump_url}) is already pinned!"
            )

        elif message.is_system():
            return await ctx.warn(f"**System messages** cannot be pinned!")

        await message.pin(reason=f"{ctx.author} ({ctx.author.id})")

    @command()
    @has_permissions(manage_messages=True)
    async def unpin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Unpin a message or by URL
        """

        message = message or ctx.replied_message
        if not message:
            async for message in ctx.channel.history(limit=1, before=ctx.message):
                break

        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.warn("That **message** is not in this server")

        elif not message.pinned:
            return await ctx.warn(
                f"That [**`message`**]({message.jump_url}) is not pinned!"
            )

        await message.unpin(reason=f"{ctx.author} ({ctx.author.id})")
        return await ctx.thumbsup()

    @command(
        name="resetcases",
        aliases=["resetcs"],
    )
    @has_permissions(manage_guild=True)
    async def resetcases(self, ctx: Context):
        """Reset the all moderation cases"""
        if not await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM cases WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.warn("There aren't any **moderation cases** to reset")

        await ctx.prompt("Are you sure you want to reset all **moderation cases**?")

        await self.bot.db.execute(
            "DELETE FROM cases WHERE guild_id = $1",
            ctx.guild.id,
        )

        return await ctx.approve("Reset all **moderation cases**")

    @group(name="settings", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def settings(self, ctx: Context) -> Message:
        """Manage server settings."""
        return await ctx.send_help(ctx.command)

    @settings.command(name="silentdm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def settings_silentdm(self, ctx: Context, setting: str) -> Message:
        """Toggle silent mode for DM warning messages."""
        setting = setting.lower()
        if setting not in ("on", "off"):
            raise CommandError("Setting must be 'on' or 'off'")

        silent_mode = setting == "on"
        await ctx.settings.update(invoke_silent_mode=silent_mode)

        status = "enabled" if silent_mode else "disabled"
        return await ctx.approve(f"Silent mode for DM warning messages **{status}**")

    @command()
    @has_permissions(administrator=True)
    @cooldown(1, 30, BucketType.guild)
    async def extractemotes(self, ctx: Context):
        """
        Sends all of your servers emojis in a zip file
        """
        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, emoji in enumerate(ctx.guild.emojis):
                    name = f"{emoji.name}.{emoji.animated and 'gif' or 'png'}"
                    if name in zip.namelist():
                        name = (
                            f"{emoji.name}_{index}.{emoji.animated and 'gif' or 'png'}"
                        )

                    __buffer = await emoji.read()
                    zip.writestr(name, __buffer)

            buffer.seek(0)

        return await ctx.reply(
            file=File(
                buffer,
                filename=f"{ctx.guild.name} emojis.zip",
            ),
        )

    @command()
    @has_permissions(administrator=True)
    @cooldown(1, 30, BucketType.guild)
    async def extractstickers(self, ctx: Context):
        """
        Sends all of your servers stickers in a zip file
        """
        if not ctx.guild.stickers:
            return await ctx.warn("This server has no stickers!")

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, sticker in enumerate(ctx.guild.stickers):
                    # Determine file extension based on format type
                    extension = "png" if sticker.format.name == "PNG" else "gif"
                    name = f"{sticker.name}.{extension}"

                    # Handle duplicate names
                    if name in zip.namelist():
                        name = f"{sticker.name}_{index}.{extension}"

                    __buffer = await sticker.read()
                    zip.writestr(name, __buffer)

            buffer.seek(0)

        return await ctx.reply(
            file=File(
                buffer,
                filename=f"{ctx.guild.name} stickers.zip",
            ),
        )

    @group(
        name="alias",
        usage="(subcommand) <args>",
        example="add deport ban",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def alias(self, ctx: Context):
        """Set a custom alias for commands"""
        await ctx.send_help()

    @alias.command(
        name="add",
        usage="(alias) (command)",
        example="deport ban",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def alias_add(self, ctx: Context, alias: str, *, command: str):
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
    async def alias_remove(self, ctx: Context, alias: str):
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
    async def alias_reset(self, ctx: Context, *, command: Command = None):
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
    async def alias_list(self, ctx: Context, *, command: Command = None):
        """View all bound aliases"""
        aliases = []
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
        else:
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

        # Add index starting from 01
        indexed_aliases = [
            f"`{index:02}` {alias}" for index, alias in enumerate(aliases, start=1)
        ]

        embed = Embed(title="Command Aliases")
        await ctx.autopaginator(embed=embed, description=indexed_aliases, split=10)

    @alias.command(
        name="view",
        usage="(alias)",
        example="deport",
        aliases=["show", "check"],
    )
    @has_permissions(manage_guild=True)
    async def alias_view(self, ctx: Context, alias: str):
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
    async def alias_removeall(self, ctx: Context, *, command: Command):
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
        name="stickymessage",
        usage="(subcommand) <args>",
        example="add #selfie Oh look at me!",
        aliases=["sm"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def stickymessage(self, ctx: Context):
        """Set up sticky messages in one or multiple channels"""
        await ctx.send_help(ctx.command)

    @stickymessage.command(
        name="add",
        usage="(channel) (message)",
        example="#selfie Oh look at me!",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        script: EmbedScript,
    ) -> Message:
        """Add a sticky message to a channel"""

        try:
            message = await script.send(
                channel,
                guild=ctx.guild,
                channel=channel,
                user=ctx.author,
            )
            await self.bot.db.execute(
                """
                INSERT INTO sticky_message (
                    guild_id,
                    channel_id,
                    message_id,
                    template
                )
                VALUES ($1, $2, $3, $4)
                """,
                ctx.guild.id,
                channel.id,
                message.id,
                script.script,
            )
        except UniqueViolationError:
            return await ctx.warn(
                "A sticky message already exists for that channel!",
            )
        except HTTPException as exc:
            return await ctx.warn(
                "Your sticky message wasn't able to be sent!", codeblock(exc.text)
            )

        return await ctx.approve(
            f"Added {vowel(script.type())} sticky message to {channel.mention}",
        )

    @stickymessage.command(
        name="remove",
        usage="(channel)",
        example="#selfie",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_remove(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
    ) -> Message:
        """Remove a sticky message from a channel"""

        message_id = cast(
            Optional[int],
            await self.bot.db.fetchval(
                """
                DELETE FROM sticky_message
                WHERE guild_id = $1
                AND channel_id = $2
                RETURNING message_id
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if not message_id:
            return await ctx.warn(f"{channel.mention} doesn't have a sticky message!")

        message = channel.get_partial_message(message_id)
        await message.delete()

        return await ctx.approve(f"Removed the sticky message from {channel.mention}")

    @stickymessage.command(
        name="view",
        usage="(channel)",
        example="#selfie",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_view(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
    ) -> Message:
        """View an existing sticky message"""

        template = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT template
                FROM sticky_message
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if not template:
            return await ctx.warn(f"{channel.mention} doesn't have a sticky message!")

        script = EmbedScript(template)

        await ctx.reply(codeblock(script.script))
        return await script.send(
            ctx.channel,
            guild=ctx.guild,
            channel=channel,
            user=ctx.author,
        )

    @stickymessage.command(
        name="list",
        aliases=["show", "all"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_list(self, ctx: Context) -> Message:
        """View all channels with sticky messages"""

        channels = [
            f"{channel.mention} (`{channel.id}`) - [Message]({message.jump_url})"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, message_id
                FROM sticky_message
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(record["channel_id"]))
            and isinstance(channel, (TextChannel, Thread))
            and (message := channel.get_partial_message(record["message_id"]))
        ]
        if not channels:
            return await ctx.warn("No sticky messages exist for this server!")

        embed = Embed(title="Sticky Messages", color=ctx.bot.color)
        return await ctx.autopaginator(embed=embed, description=channels, split=10)

    # TODO: FINISH THIS LATER
    @group(
        name="settings",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def settings(self, ctx: Context):
        """Manage server settings"""
        await ctx.send_help(ctx.command)

    @settings.command(
        name="staff",
    )
    @has_permissions(manage_guild=True)
    async def settings_staff(self, ctx: Context, role: Role) -> Message:
        """Set staff role(s)"""
        pass

    @settings.command(
        name="staff_list",
        aliases=["stafflist"],
    )
    @has_permissions(manage_guild=True)
    async def settings_staff_list(self, ctx: Context) -> Message:
        """View a list of all staff roles"""
        pass

    @settings.command(
        name="muted",
    )
    @has_permissions(manage_guild=True)
    async def settings_muted(self, ctx: Context, role: Role) -> Message:
        """Set the text muted role"""
        pass

    @settings.command(
        name="imuted",
    )
    @has_permissions(manage_guild=True)
    async def settings_imuted(self, ctx: Context, role: Role) -> Message:
        """Set the image muted role"""
        pass

    @settings.command(
        name="disablecustomfms",
    )
    @has_permissions(manage_channels=True)
    async def settings_disablecustomfms(self, ctx: Context, setting: str) -> Message:
        """Disable custom Now Playing commands"""
        pass

    @settings.command(
        name="jailroles",
    )
    @has_permissions(manage_guild=True)
    async def settings_jailroles(self, ctx: Context, setting: str) -> Message:
        """Enable or disable removal of roles for jail"""
        pass

    @settings.command(
        name="rmuted",
    )
    @has_permissions(manage_guild=True)
    async def settings_rmuted(self, ctx: Context, role: Role) -> Message:
        """Set the reaction muted role"""
        pass

    @settings.command(
        name="googlesafetylevel",
    )
    @has_permissions(manage_guild=True)
    async def settings_googlesafetylevel(self, ctx: Context, setting: str) -> Message:
        """Enable or disable safety level for Google commands"""
        pass

    @settings.command(
        name="modlog",
    )
    @has_permissions(manage_guild=True)
    async def settings_modlog(self, ctx: Context, channel: TextChannel) -> Message:
        """Set mod logs for punishments in guild"""
        pass

    @settings.command(
        name="joinlogs",
    )
    @has_permissions(manage_guild=True)
    async def settings_joinlogs(self, ctx: Context, channel: TextChannel) -> Message:
        """Set a channel to log join/leaves in a server"""
        pass

    @settings.command(
        name="premiumrole",
    )
    @has_permissions(manage_guild=True)
    async def settings_premiumrole(self, ctx: Context, role: Role) -> Message:
        """Set the Premium Members role for Server Subscriptions"""
        pass

    @settings.command(
        name="config",
    )
    @has_permissions(manage_guild=True)
    async def settings_config(self, ctx: Context) -> Message:
        """View settings configuration for guild"""
        pass

    @group(
        name="fakepermissions",
        usage="(subcommand) <args>",
        example="grant @Moderator manage_messages",
        aliases=["fakeperms", "fp"],
        invoke_without_command=True,
    )
    @has_permissions(guild_owner=True)
    async def fakepermissions(self, ctx: Context):
        """Set up fake permissions for roles"""
        await ctx.send_help()

    @fakepermissions.command(
        name="grant",
        usage="(role) (permission)",
        example="@Moderator manage_messages",
        aliases=["allow", "add"],
    )
    @has_permissions(guild_owner=True)
    async def fakepermissions_grant(self, ctx: Context, role: Role, *, permission: str):
        """Grant a role a fake permission"""
        permission = permission.replace(" ", "_").lower()
        if permission not in dict(ctx.author.guild_permissions):
            return await ctx.warn(f"Permission `{permission}` doesn't exist")

        try:
            await self.bot.db.execute(
                "INSERT INTO fake_permissions (guild_id, role_id, permission) VALUES ($1, $2, $3)",
                ctx.guild.id,
                role.id,
                permission,
            )
        except Exception:
            return await ctx.warn(
                f"The role {role.mention} already has fake permission `{permission}`"
            )

        return await ctx.approve(
            f"Granted {role.mention} fake permission `{permission}`"
        )

    @fakepermissions.command(
        name="revoke",
        usage="(role) (permission)",
        example="@Moderator manage_messages",
        aliases=["remove", "delete", "del", "rm"],
    )
    @has_permissions(guild_owner=True)
    async def fakepermissions_revoke(
        self, ctx: Context, role: Role, *, permission: str
    ):
        """Revoke a fake permission from a role"""
        permission = permission.replace(" ", "_").lower()
        if permission not in dict(ctx.author.guild_permissions):
            return await ctx.warn(f"Permission `{permission}` doesn't exist")

        if not await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM fake_permissions WHERE guild_id = $1 AND role_id = $2 AND permission = $3",
            ctx.guild.id,
            role.id,
            permission,
        ):
            return await ctx.warn(
                f"The role {role.mention} doesn't have fake permission `{permission}`"
            )

        await self.bot.db.execute(
            "DELETE FROM fake_permissions WHERE guild_id = $1 AND role_id = $2 AND permission = $3",
            ctx.guild.id,
            role.id,
            permission,
        )

        await ctx.approve(f"Revoked fake permission `{permission}` from {role.mention}")

    @fakepermissions.command(name="reset", aliases=["clear"])
    @has_permissions(guild_owner=True)
    async def fakepermissions_reset(self, ctx: Context):
        """Remove every fake permission from every role"""
        await ctx.prompt("Are you sure you want to remove all **fake permissions**?")

        if not await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM fake_permissions WHERE guild_id = $1",
            ctx.guild.id,
        ):
            return await ctx.warn("There aren't any **fake permissions** to remove")

        await self.bot.db.execute(
            "DELETE FROM fake_permissions WHERE guild_id = $1",
            ctx.guild.id,
        )
        await ctx.approve("Removed all **fake permissions**")

    @fakepermissions.command(
        name="check",
        usage="(role) <permission>",
        example="@Moderator manage_messages",
        aliases=["test"],
    )
    @has_permissions(guild_owner=True)
    async def fakepermissions_check(
        self, ctx: Context, role: Role, *, permission: Optional[str] = None
    ):
        """Check fake permissions for a role"""
        if permission:
            permission = permission.replace(" ", "_").lower()
            if permission not in dict(ctx.author.guild_permissions):
                return await ctx.warn(f"Permission `{permission}` doesn't exist")

            has_perm = await self.bot.db.fetchval(
                "SELECT EXISTS(SELECT 1 FROM fake_permissions WHERE guild_id = $1 AND role_id = $2 AND permission = $3)",
                ctx.guild.id,
                role.id,
                permission,
            )

            return await ctx.approve(
                f"Role {role.mention} {'has' if has_perm else 'does not have'} fake permission `{permission}`"
            )

        perms = await self.bot.db.fetch(
            "SELECT permission FROM fake_permissions WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        )

        if not perms:
            return await ctx.warn(f"Role {role.mention} has no fake permissions")

        perm_list = [f"`{row['permission']}`" for row in perms]
        return await ctx.approve(
            f"Role {role.mention} has the following fake permissions:\n{', '.join(perm_list)}"
        )

    @fakepermissions.command(name="list", aliases=["show", "all"])
    @has_permissions(guild_owner=True)
    async def fakepermissions_list(self, ctx: Context):
        """View all roles with fake permissions"""
        roles = [
            f"`{idx:02d}` **Role:** {role.mention}\n> **Permissions:** {', '.join([f'`{permission}`' for permission in permissions])}"
            for idx, row in enumerate(
                await self.bot.db.fetch(
                    "SELECT role_id, array_agg(permission) AS permissions FROM fake_permissions WHERE guild_id = $1 GROUP BY role_id",
                    ctx.guild.id,
                ),
                start=1,
            )
            if (role := ctx.guild.get_role(row["role_id"]))
            and (permissions := row["permissions"])
        ]
        if not roles:
            return await ctx.warn("There aren't any roles with **fake permissions**")

        embed = Embed(
            title="Roles With Fake Permissions",
        )
        embed.set_author(
            name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )

        await ctx.autopaginator(embed=embed, description=roles, split=8)

    @group(
        name="command",
        usage="(subcommand) <args>",
        example="disable #spam blunt",
        aliases=["cmd"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def command(self, ctx: Context):
        """Manage command usability"""
        await ctx.send_help()

    @command.group(
        name="enable",
        usage="(channel or 'all') (command)",
        example="all blunt",
        aliases=["unlock"],
    )
    @has_permissions(manage_guild=True)
    async def command_enable(
        self,
        ctx: Context,
        channel: TextChannel | Thread | Literal["all"],
        *,
        command: str,
    ):
        """Enable a previously disabled command"""
        # Convert command string to Command object
        cmd = self.bot.get_command(command)
        if not cmd:
            return await ctx.warn(f"Command `{command}` not found")

        disabled_channels = await self.bot.db.fetch(
            "SELECT channel_id FROM commands.disabled WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            cmd.qualified_name,
        )

        if channel == "all":
            try:
                await self.bot.db.execute(
                    "DELETE FROM commands.disabled WHERE guild_id = $1 AND command = $2",
                    ctx.guild.id,
                    cmd.qualified_name,
                )
            except Exception:
                return await ctx.warn(
                    f"Command `{cmd.qualified_name}` is already enabled in every channel"
                )
        else:
            try:
                await self.bot.db.execute(
                    "DELETE FROM commands.disabled WHERE guild_id = $1 AND channel_id = $2 AND command = $3",
                    ctx.guild.id,
                    channel.id,
                    cmd.qualified_name,
                )
            except Exception:
                return await ctx.warn(
                    f"Command `{cmd.qualified_name}` is already enabled in {channel.mention}"
                )

        await ctx.approve(
            f"Command `{cmd.qualified_name}` has been enabled in "
            + (
                f"**{Plural(len(disabled_channels)):channel}**"
                if channel == "all"
                else channel.mention
            )
        )

    @command.group(
        name="disable",
        usage="(channel or 'all') (command)",
        example="#spam blunt",
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def command_disable(
        self,
        ctx: Context,
        channel: Union[TextChannel, Thread, Literal["all"]],
        *,
        command: str,
    ):
        """Disable a command in a channel"""
        # Convert command string to Command object
        cmd = self.bot.get_command(command)
        if not cmd:
            return await ctx.warn(f"Command `{command}` not found")

        if cmd.qualified_name.startswith("command"):
            return await ctx.warn("You can't disable this **command**")

        disabled_channels = await self.bot.db.fetch(
            "SELECT channel_id FROM commands.disabled WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            cmd.qualified_name,
        )

        if channel == "all":
            await self.bot.db.executemany(
                "INSERT INTO commands.disabled (guild_id, channel_id, command) VALUES($1, $2, $3) ON CONFLICT (guild_id, channel_id, command) DO"
                " NOTHING",
                [
                    (
                        ctx.guild.id,
                        _channel.id,
                        cmd.qualified_name,
                    )
                    for _channel in ctx.guild.text_channels
                ],
            )
        else:
            try:
                await self.bot.db.execute(
                    "INSERT INTO commands.disabled (guild_id, channel_id, command) VALUES($1, $2, $3)",
                    ctx.guild.id,
                    channel.id,
                    cmd.qualified_name,
                )
            except Exception:
                return await ctx.warn(
                    f"Command `{cmd.qualified_name}` is already disabled in {channel.mention}"
                )

        if channel == "all" and len(ctx.guild.text_channels) == len(disabled_channels):
            return await ctx.warn(
                f"Command `{cmd.qualified_name}` is already disabled in every channel"
            )

        await ctx.approve(
            f"Command `{cmd.qualified_name}` has been disabled in "
            + (
                f"** {Plural(len(disabled_channels) - len(ctx.guild.text_channels)):channel}** "
                + (
                    f"(already disabled in {len(disabled_channels)})"
                    if disabled_channels
                    else ""
                )
                if channel == "all"
                else channel.mention
            )
        )

    @command_disable.command(
        name="all",
        usage="(command)",
        example="blunt",
        aliases=["lockall"],
    )
    @has_permissions(manage_guild=True)
    async def command_disable_all(
        self,
        ctx: Context,
        *,
        command: str,
    ):
        """Disable a command in all channels"""
        # Convert command string to Command object
        cmd = self.bot.get_command(command)
        if not cmd:
            return await ctx.warn(f"Command `{command}` not found")

        if cmd.qualified_name.startswith("command"):
            return await ctx.warn("You can't disable this **command**")

        try:
            # Get currently disabled channels
            disabled_channels = await self.bot.db.fetch(
                """
                SELECT channel_id 
                FROM commands.disabled 
                WHERE guild_id = $1 AND command = $2
                """,
                ctx.guild.id,
                cmd.qualified_name,
            )

            if len(disabled_channels) == len(ctx.guild.text_channels):
                return await ctx.warn(
                    f"Command `{cmd.qualified_name}` is already disabled in every channel"
                )

            # Create values for batch insert
            values = [
                (ctx.guild.id, channel.id, cmd.qualified_name)
                for channel in ctx.guild.text_channels
                if channel.id not in [row["channel_id"] for row in disabled_channels]
            ]

            # Perform batch insert if there are channels to update
            if values:
                await self.bot.db.execute(
                    """
                    INSERT INTO commands.disabled (guild_id, channel_id, command)
                    SELECT d.guild_id, d.channel_id, d.command
                    FROM unnest($1::bigint[], $2::bigint[], $3::text[]) AS d(guild_id, channel_id, command)
                    ON CONFLICT (guild_id, channel_id, command) DO NOTHING
                    """,
                    [v[0] for v in values],
                    [v[1] for v in values],
                    [v[2] for v in values],
                )

            already_disabled = len(disabled_channels)
            newly_disabled = len(values)

            await ctx.approve(
                f"Command `{cmd.qualified_name}` has been disabled in **{newly_disabled:,} channels**"
                + (
                    f" (already disabled in {already_disabled:,})"
                    if already_disabled
                    else ""
                )
            )

        except Exception as e:
            await ctx.warn(f"An error occurred while disabling the command: {str(e)}")
            raise

    @command_disable.command(
        name="list",
        aliases=["show", "view"],
    )
    @has_permissions(manage_guild=True)
    async def command_disable_list(self, ctx: Context):
        """View all disabled commands"""
        commands = [
            f"`{row['command']}` - {self.bot.get_channel(row['channel_id']).mention}"
            for row in await self.bot.db.fetch(
                "SELECT channel_id, command FROM commands.disabled WHERE guild_id = $1",
                ctx.guild.id,
            )
            if self.bot.get_command(row["command"])
            and self.bot.get_channel(row["channel_id"])
        ]
        if not commands:
            return await ctx.warn("No commands have been **disabled**")

        embed = Embed(title="Disabled Commands")
        await ctx.autopaginator(embed=embed, description=commands, split=10)

    @command.group(
        name="restrict",
        usage="(role) (command)",
        example="Moderator snipe",
        aliases=["permit"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def command_restrict(self, ctx: Context, role: Role, *, command: str):
        """Restrict a command to certain roles"""
        # Convert command string to Command object
        cmd = self.bot.get_command(command)
        if not cmd:
            return await ctx.warn(f"Command `{command}` not found")

        if cmd.qualified_name.startswith("command"):
            return await ctx.warn("You can't restrict this **command**")

        try:
            await self.bot.db.execute(
                "INSERT INTO commands.restricted (guild_id, role_id, command) VALUES($1, $2, $3)",
                ctx.guild.id,
                role.id,
                cmd.qualified_name,
            )
        except Exception:
            await self.bot.db.execute(
                "DELETE FROM commands.restricted WHERE guild_id = $1 AND role_id = $2 AND command = $3",
                ctx.guild.id,
                role.id,
                cmd.qualified_name,
            )
            return await ctx.approve(
                f"Removed restriction for {role.mention} on `{cmd.qualified_name}`"
            )

        await ctx.approve(
            f"Allowing users with {role.mention} to use `{cmd.qualified_name}`"
        )

    @command_restrict.command(
        name="list",
        aliases=["show", "view"],
    )
    @has_permissions(manage_guild=True)
    async def command_restrict_list(self, ctx: Context):
        """View all restricted commands"""
        commands = [
            f"`{row['command']}` - {ctx.guild.get_role(row['role_id']).mention}"
            for row in await self.bot.db.fetch(
                "SELECT role_id, command FROM commands.restricted WHERE guild_id = $1",
                ctx.guild.id,
            )
            if self.bot.get_command(row["command"])
            and ctx.guild.get_role(row["role_id"])
        ]
        if not commands:
            return await ctx.warn("No commands have been **restricted**")

        embed = Embed(title="Restricted Commands")
        await ctx.autopaginator(embed=embed, description=commands, split=10)

    @command.command(
        name="reset",
        aliases=["clear"],
    )
    @has_permissions(manage_guild=True)
    async def command_reset(self, ctx: Context):
        """Reset all command restrictions and disabled commands"""

        # Check if there are any disabled commands or restrictions
        disabled_count = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM commands.disabled WHERE guild_id = $1", ctx.guild.id
        )

        restricted_count = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM commands.restricted WHERE guild_id = $1", ctx.guild.id
        )

        if not (disabled_count or restricted_count):
            return await ctx.warn("There aren't any **command settings** to reset")

        # Prompt for confirmation
        await ctx.prompt(
            "Are you sure you want to reset all **command settings**?\n"
            f"> This will remove {Plural(disabled_count):disabled command} and {Plural(restricted_count):command restriction}"
        )

        # Delete all command settings for the guild
        await self.bot.db.execute(
            "DELETE FROM commands.disabled WHERE guild_id = $1", ctx.guild.id
        )

        await self.bot.db.execute(
            "DELETE FROM commands.restricted WHERE guild_id = $1", ctx.guild.id
        )

        return await ctx.approve(
            f"Reset all command settings\n"
            f"> Removed {Plural(disabled_count):disabled command} and {Plural(restricted_count):command restriction}"
        )

    @group(
        name="autorole",
        usage="(subcommand) <args>",
        example="add @Member",
        aliases=["welcrole"],
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def autorole(self, ctx: Context):
        """Automatically assign roles to new members"""
        await ctx.send_help()

    @autorole.command(
        name="add",
        usage="(role) --humans --bots",
        example="@Member --humans",
        flag=AutoroleFlags,
        aliases=["create"],
    )
    @has_permissions(manage_roles=True)
    async def autorole_add(self, ctx: Context, role: Role):
        """Add a role to be assigned to new members"""
        flags = cast(AutoroleFlags, ctx.flag)

        if await self.bot.db.fetchval(
            "SELECT * FROM auto_roles WHERE guild_id = $1 AND role_id = $2",
            ctx.guild.id,
            role.id,
        ):
            return await ctx.warn(
                f"The role {role.mention} is already being **assigned** to new members"
            )

        # Check if the bot can manage this role
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot manage the role {role.mention} as it is above my highest role"
            )

        # Check if the role is dangerous (if not assigning to bots)
        if not flags.bots and role.permissions.administrator:
            raise CommandError(
                f"The role {role.mention} has dangerous permissions (Administrator)"
            )

        await self.bot.db.execute(
            "INSERT INTO auto_roles (guild_id, role_id, humans, bots) VALUES ($1, $2, $3, $4)",
            ctx.guild.id,
            role.id,
            flags.humans,
            flags.bots,
        )

        return await ctx.approve(
            f"Now assigning {role.mention} to new members"
            + (" **`(humans)`**" if flags.humans else "")
            + (" **`(bots)`**" if flags.bots else "")
        )

    @autorole.command(
        name="remove",
        usage="(role)",
        example="@Member",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_roles=True)
    async def autorole_remove(self, ctx: Context, *, role: Role):
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
    async def autorole_reset(self, ctx: Context):
        """Remove every role which is being assigned to new members"""
        if not await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM auto_roles WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.warn("No roles are being **assigned** to new members")

        await ctx.prompt("Are you sure you want to remove all **assigned roles**?")

        await self.bot.db.execute(
            "DELETE FROM auto_roles WHERE guild_id = $1",
            ctx.guild.id,
        )
        await ctx.approve("No longer **assigning** any roles to new members")

    @autorole.command(name="list", aliases=["show", "all"])
    @has_permissions(manage_roles=True)
    async def autorole_list(self, ctx: Context):
        """View all the roles being assigned to new members"""
        roles = [
            f"`{idx:02d}` {ctx.guild.get_role(row['role_id']).mention}"
            + f" {Emojis.Interface.increase} "
            + ("`Humans`" if row["humans"] else "All Members")
            + (
                " & `Bots`"
                if row["bots"] and row["humans"]
                else " Only" if row["bots"] else ""
            )
            for idx, row in enumerate(
                await self.bot.db.fetch(
                    "SELECT role_id, humans, bots FROM auto_roles WHERE guild_id = $1",
                    ctx.guild.id,
                ),
                start=1,
            )
            if ctx.guild.get_role(row["role_id"])
        ]

        if not roles:
            return await ctx.warn("No roles are being **assigned** to new members")

        embed = Embed(
            title="Auto Role Configuration",
        )
        embed.set_author(
            name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        embed.description = "\n".join(roles)
        embed.set_footer(text=f"Total Auto Roles: {len(roles)}")

        await ctx.send(embed=embed)

    @group(
        name="response",
        usage="(subcommand) <args>",
        example="add Hi, Hey {user} -reply",
        aliases=["autoresponder", "autoresponse", "ar"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def response(self, ctx: Context):
        """Set up automatic trigger responses"""
        await ctx.send_help()

    @response.command(
        name="add",
        usage="(trigger), (response)",
        example="Hi, Hey {user} --reply",
        flag=ResponseFlags,
        aliases=["create"],
    )
    @has_permissions(manage_channels=True)
    async def response_add(
        self,
        ctx: Context,
        *,
        message: str,
    ):
        """Add a response trigger"""
        flags = cast(ResponseFlags, ctx.flag)

        message = message.split(", ", 1)
        if len(message) != 2:
            return await ctx.warn("You must specify a **trigger** and **response**")

        trigger = message[0].strip().lower()
        response = message[1].strip()

        if not trigger:
            return await ctx.warn("You must specify a **trigger**")
        if not response:
            return await ctx.warn("You must specify a **response**")

        if not (response := await EmbedScriptValidator().convert(ctx, response)):
            return

        try:
            await self.bot.db.execute(
                "INSERT INTO auto_responses (guild_id, trigger, response, self_destruct, not_strict, ignore_command_check, reply, delete) VALUES ($1,"
                " $2, $3, $4, $5, $6, $7, $8)",
                ctx.guild.id,
                trigger,
                str(response),
                flags.self_destruct,
                flags.not_strict,
                flags.ignore_command_check,
                flags.reply,
                flags.delete,
            )
        except Exception:
            return await ctx.warn(
                f"There is already a **response trigger** for `{trigger}`"
            )

        flag_indicators = [
            f"({key.replace('_', ' ')})"
            for key, value in flags.__dict__.items()
            if value and key != "not_strict" and value is not None
        ]

        return await ctx.approve(
            f"Created {response.type(bold=False)} **response trigger** for `{trigger}` "
            + " ".join(flag_indicators)
            + ("" if flags.not_strict else " (strict match)")
        )

    @response.command(
        name="remove",
        usage="(trigger)",
        example="Hi",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def response_remove(self, ctx: Context, *, trigger: str):
        """Remove a response trigger"""
        try:
            await self.bot.db.execute(
                "DELETE FROM auto_responses WHERE guild_id = $1 AND lower(trigger) = $2",
                ctx.guild.id,
                trigger.lower(),
            )
        except Exception:
            await ctx.warn(f"There isn't a **response trigger** for `{trigger}`")
        else:
            await ctx.approve(f"Removed **response trigger** for `{trigger}`")

    @response.command(
        name="view",
        usage="(trigger)",
        example="Hi",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_channels=True)
    async def response_view(self, ctx: Context, *, trigger: str):
        """View a response trigger"""
        data = await self.bot.db.fetchrow(
            "SELECT * FROM auto_responses WHERE guild_id = $1 AND lower(trigger) = $2",
            ctx.guild.id,
            trigger.lower(),
        )
        if not data:
            return await ctx.warn(f"There isn't a **response trigger** for `{trigger}`")

        await EmbedScript(data["response"]).send(
            ctx.channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
        )

    @response.command(
        name="reset",
        aliases=["clear"],
    )
    @has_permissions(manage_channels=True)
    async def response_reset(self, ctx: Context):
        """Remove all response triggers"""
        await ctx.prompt("Are you sure you want to remove all **response triggers**?")

        try:
            await self.bot.db.execute(
                "DELETE FROM auto_responses WHERE guild_id = $1", ctx.guild.id
            )
        except Exception:
            return await ctx.warn("There are no **response triggers**")

        return await ctx.approve("Removed all **response triggers**")

    @response.command(name="list", aliases=["show", "all"])
    @has_permissions(manage_channels=True)
    async def response_list(self, ctx: Context):
        """View all response triggers"""
        data = await self.bot.db.fetch(
            "SELECT * FROM auto_responses WHERE guild_id = $1",
            ctx.guild.id,
        )
        if not data:
            return await ctx.warn("There are no **response triggers**")

        entries = []
        for index, trigger in enumerate(data, 1):
            flags = []
            if trigger["not_strict"]:
                flags.append("🔓 non-strict")
            if trigger["ignore_command_check"]:
                flags.append("⚡ ignore commands")
            if trigger["reply"]:
                flags.append("💬 reply")
            if trigger["delete"]:
                flags.append("🗑️ delete trigger")
            if trigger["self_destruct"]:
                flags.append(f"⏱️ self destruct {trigger['self_destruct']}s")

            entry = (
                f"`{index}` **{trigger['trigger']}**\n"
                f"> Response: {trigger['response']}\n"
                + (f"> Flags: {' • '.join(flags)}\n" if flags else "")
            )
            entries.append(entry)

        embed = Embed(
            title=f"Response Triggers ({len(data)})",
            description=(
                "View all response triggers in this server\n"
                "Use `,response add` to create a new trigger"
            ),
        ).set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

        await ctx.autopaginator(embed=embed, description=entries, split=5)

    @group(
        name="boost",
        usage="(subcommand) <args>",
        example="add #chat Thx {user.mention} :3",
        aliases=["bst"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def boost(self, ctx: Context):
        """Set up boost messages in one or multiple channels"""
        await ctx.send_help()

    @boost.command(
        name="add",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def boost_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        script: EmbedScriptValidator,
    ) -> Message:
        """
        Add a boost message to a channel.
        """

        template, flags = await BoostFlags().find(
            ctx, script.script
        )  # Changed from script.template to script.script
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
            f"Added {vowel(script.type())} boost message to {channel.mention}",
            *(
                [
                    f"> The message will be deleted after **{format_timespan(flags.delete_after)}**"
                ]
                if flags.delete_after
                else []
            ),
        )

    @boost.command(
        name="remove",
        usage="(channel)",
        example="#chat",
        aliases=["del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def boost_remove(self, ctx: Context, channel: TextChannel | Thread):
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
    async def boost_view(self, ctx: Context, channel: TextChannel | Thread):
        """View a boost message for a channel"""
        data = await self.bot.db.fetchrow(
            """
            SELECT template, delete_after 
            FROM boost_message 
            WHERE guild_id = $1 AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        if not data:
            return await ctx.warn(
                f"There isn't a **boost message** for {channel.mention}"
            )

        template = data["template"]
        delete_after = data["delete_after"]

        await EmbedScript(template).send(
            ctx.channel,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
            delete_after=delete_after,
        )

    @boost.command(
        name="deleteall",
        aliases=["clearall"],
    )
    @has_permissions(manage_guild=True)
    async def boost_deleteall(self, ctx: Context):
        """Reset all boost channels"""
        await ctx.prompt("Are you sure you want to remove all **boost channels**?")

        try:
            await self.bot.db.execute(
                "DELETE FROM boost_messages WHERE guild_id = $1", ctx.guild.id
            )
        except Exception:
            return await ctx.warn("No **boost channels** have been set up")

        return await ctx.approve("Removed all **boost channels**")

    @boost.command(
        name="list",
        aliases=["show", "all"],
    )
    @has_permissions(manage_guild=True)
    async def boost_list(self, ctx: Context):
        """View all boost message channels"""
        rows = await self.bot.db.fetch(
            """
            SELECT channel_id, template, delete_after 
            FROM boost_message 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not rows:
            return await ctx.warn("No **boost messages** have been set up")

        entries = []
        for idx, row in enumerate(rows, 1):
            channel = ctx.guild.get_channel(row["channel_id"])
            if not channel:
                continue

            entry = (
                f"`{idx:02d}` {channel.mention}\n"
                f"> Message: {row['template']}\n"
                + (
                    f"> Self Destructs: After {Plural(row['delete_after']):second}\n"
                    if row["delete_after"]
                    else ""
                )
            )
            entries.append(entry)

        if not entries:
            return await ctx.warn("No **valid boost messages** found")

        embed = Embed(
            title=f"Boost Messages ({len(entries)})",
            description=(
                "View all boost messages in this server\n"
                "Use `,boost add` to create a new message"
            ),
        ).set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

        await ctx.autopaginator(embed=embed, description=entries, split=5)
