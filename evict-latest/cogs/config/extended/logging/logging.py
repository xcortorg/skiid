import discord
import asyncio

from contextlib import suppress
from datetime import timedelta
from io import BytesIO
from logging import getLogger
from typing import Any, List, Optional, cast
import json

from discord import (
    AuditLogEntry,
    Colour,
    DMChannel,
    Embed,
    Emoji,
    File,
    GroupChannel,
    Guild,
    HTTPException,
    Invite,
    Member,
    Message,
    Object,
    PartialMessageable,
    Permissions,
    Role,
    StageChannel,
    TextChannel,
    Thread,
    User,
    VoiceChannel,
    VoiceState,
)
from discord.abc import GuildChannel
from discord.ext.commands import Cog, Greedy, group, has_permissions
from discord.utils import format_dt, utcnow
from discord.ext import tasks

from tools import CompositeMetaClass, MixinMeta
from core.client.context import Context
from tools.formatter import human_join, plural, shorten
from managers.paginator import Paginator

from .enums import LogType

log = getLogger("evict/logging")


class Logging(MixinMeta, metaclass=CompositeMetaClass):
    """
    The Logging mixin provides a set of tools for managing server logs.
    """
    _log_queue = asyncio.Queue()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cleanup_old_logs.start()
        self.process_log_queue.start()

    def cog_unload(self):
        super().cog_unload()
        self.cleanup_old_logs.cancel()
        self.process_log_queue.cancel()

    @tasks.loop(hours=24)  
    async def cleanup_old_logs(self):
        """Cleanup logs older than 7 days"""
        try:
            await self.bot.db.execute(
                "DELETE FROM logging_history WHERE created_at < NOW() - INTERVAL '7 days'"
            )
            await self.bot.db.execute("VACUUM logging_history;")
        except Exception as e:
            log.error(f"Failed to cleanup old logs: {e}")

    @tasks.loop(seconds=5)  
    async def process_log_queue(self):
        """Process queued logs in batches"""
        try:
            logs_to_process = []
            while len(logs_to_process) < 100:  
                try:
                    log_entry = self._log_queue.get_nowait()
                    logs_to_process.append(log_entry)
                except asyncio.QueueEmpty:
                    break

            if logs_to_process:
                await self.bot.db.executemany(
                    """
                    INSERT INTO logging_history 
                    (guild_id, channel_id, event_type, content) 
                    VALUES ($1, $2, $3, $4)
                    """,
                    logs_to_process
                )
        except Exception as e:
            log.error(f"Failed to process log queue: {e}")

    @process_log_queue.before_loop
    @cleanup_old_logs.before_loop
    async def before_tasks(self):
        """Wait for bot to be ready before starting tasks"""
        await self.bot.wait_until_ready()

    async def queue_log(self, guild_id, channel_id, event_type, content):
        """Queue a log entry instead of writing directly to DB"""
        try:
            await self._log_queue.put((guild_id, channel_id, event_type, content))
        except Exception as e:
            log.error(f"Failed to queue log: {e}")
            await self._safe_db_execute(
                """
                INSERT INTO logging_history 
                (guild_id, channel_id, event_type, content) 
                VALUES ($1, $2, $3, $4)
                """,
                guild_id, channel_id, event_type, content
            )

    @group(aliases=["log"], invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def logging(self, ctx: Context) -> Message:
        """
        The base command for managing server logs.
        """

        return await ctx.send_help(ctx.command)

    @logging.command(
        name="enable",
        aliases=[
            "create",
            "add",
        ],
        example="#logs message",
    )
    @has_permissions(manage_guild=True)
    async def logging_enable(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        events: Greedy[LogType],
    ) -> Message:
        """
        Set events to be logged in a channel.
        """

        if not events:
            events.extend(LogType.all())

        value = 0
        for event in events:
            value |= event.value

        await self.bot.db.execute(
            """
            INSERT INTO logging (guild_id, channel_id, events)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, channel_id)
            DO UPDATE SET
                channel_id = EXCLUDED.channel_id,
                events = EXCLUDED.events
            """,
            ctx.guild.id,
            channel.id,
            value,
        )

        if value == LogType.ALL():
            return await ctx.approve(f"Now logging all events in {channel.mention}")

        human_events = human_join(
            [f"`{event}`" for event in events],
            final="and",
        )
        return await ctx.approve(
            f"Now logging {human_events} events in {channel.mention}"
        )
    
    @logging.command(name="events")
    @has_permissions(manage_guild=True)
    async def logging_events(self, ctx: Context):
        """
        View all available logging events.
        """
        paginator = Paginator(
                ctx,
                entries=[
                    f"`{event}`"
                    for event in LogType.all()
                ],
                embed=Embed(title="Logging Events"),
            )
        return await paginator.start()

    @logging.command(
        name="disable",
        aliases=[
            "remove",
            "delete",
            "del",
            "rm",
        ],
        example="#logs",
    )
    @has_permissions(manage_guild=True)
    async def logging_disable(
        self,
        ctx: Context,
        *,
        channel: TextChannel | Thread,
    ) -> Message:
        """
        Remove an existing logging channel.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM logging
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(f"Logging in {channel.mention} doesn't exist!")

        return await ctx.approve(f"No longer logging in {channel.mention}")

    @logging.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def logging_list(self, ctx: Context) -> Message:
        """
        List all logging channels.
        """

        channels = [
            f"{channel.mention} (`{channel.id}`)"
            + f" - {human_join([f'`{event}`' for event in LogType.from_value(record['events'])], final='and')}"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, events
                FROM logging
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No logging channels exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="Logging Channels"),
        )
        return await paginator.start()

    @logging.group(
        name="ignore",
        aliases=["exempt"],
        invoke_without_command=True,
        example="(#channel or @role)",
    )
    @has_permissions(manage_guild=True)
    async def logging_ignore(
        self,
        ctx: Context,
        *,
        target: GuildChannel | Member,
    ) -> Message:
        """
        Ignore a channel or user from being unintentionally logged.
        """

        if target in ctx.settings.log_ignore:
            return await ctx.warn(f"{target.mention} is already ignored!")

        ctx.settings.log_ignore_ids.append(target.id)
        await ctx.settings.update()
        return await ctx.approve(f"Now ignoring {target.mention} from logging")

    @logging_ignore.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="(#channel or @role)",
    )
    @has_permissions(manage_guild=True)
    async def logging_ignore_remove(
        self,
        ctx: Context,
        *,
        target: GuildChannel | Member,
    ) -> Message:
        """
        Remove a channel or user from being ignored.
        """

        if target not in ctx.settings.log_ignore:
            return await ctx.warn(f"{target.mention} isn't ignored!")

        ctx.settings.log_ignore_ids.remove(target.id)
        await ctx.settings.update()
        return await ctx.approve(f"No longer ignoring {target.mention} from logging")

    @logging_ignore.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_channels=True)
    async def logging_ignore_list(self, ctx: Context) -> Message:
        """
        View all ignored channels and users.
        """

        if not ctx.settings.log_ignore:
            return await ctx.warn("No channels or users are being ignored!")

        paginator = Paginator(
            ctx,
            entries=[
                f"{target.mention} (`{target.id}`)"
                for target in ctx.settings.log_ignore
            ],
            embed=Embed(title="Logging Exemption"),
        )
        return await paginator.start()

    async def log(
        self,
        guild: Guild,
        event: LogType,
        embed: Embed,
        *,
        from_channel: Optional[Object | Any] = None,
        files: List[File] | None = None,
        user: Optional[Member | User | Object] = None,
    ) -> Optional[Message]:
        """Send a log to the appropriate channel."""
        if not guild.me:
            return

        if files is None:
            files = []

        try:
            log_data = {
                "event": {
                    "type": event.name,
                    "timestamp": utcnow().isoformat(),
                    "details": embed.description.encode('utf-8', 'ignore').decode('utf-8') if embed.description else None,
                    "files": [f.filename.encode('utf-8', 'ignore').decode('utf-8') for f in files] if files else None
                },
                "target": {
                    "channel_id": str(from_channel.id) if from_channel and hasattr(from_channel, "id") else None,
                    "channel_name": getattr(from_channel, "name", "").encode('utf-8', 'ignore').decode('utf-8') if from_channel and hasattr(from_channel, "name") else None,
                    "channel_type": str(getattr(from_channel, "type", None)) if from_channel else None
                },
                "user": {
                    "id": str(user.id) if user and hasattr(user, "id") else None,
                    "name": str(user).encode('utf-8', 'ignore').decode('utf-8') if user else None,
                    "bot": getattr(user, "bot", None)
                },
                "changes": [
                    {
                        "name": field.name.encode('utf-8', 'ignore').decode('utf-8'),
                        "value": field.value.encode('utf-8', 'ignore').decode('utf-8'),
                        "inline": field.inline
                    }
                    for field in embed.fields
                ] if embed.fields else []
            }

            await self.queue_log(
                guild.id,
                getattr(from_channel, "id", None),
                event.name,
                log_data
            )
        except Exception as e:
            log.error(f"Failed to log {event.name}: {e}")

        log.debug("Dispatching %s log for %s (%s).", event.name, guild, guild.id)
        channel_id = cast(
            int,
            await self.bot.db.fetchval(
                """
                SELECT channel_id
                FROM logging
                WHERE guild_id = $1
                AND events & $2 = $2
                AND channel_id = ANY($3::BIGINT[])
                """,
                guild.id,
                event.value,
                [channel.id for channel in guild.text_channels + list(guild.threads)],
            ),
        )
        if not channel_id:
            return None

        channel = cast(
            Optional[TextChannel | Thread],
            guild.get_channel_or_thread(channel_id),
        )
        if not channel:
            log.warning(
                "Logging channel %s doesn't exist in %s (%s)",
                channel_id,
                guild,
                guild.id,
            )
            return None

        elif not all(
            (
                channel.permissions_for(guild.me).send_messages,
                channel.permissions_for(guild.me).embed_links,
                channel.permissions_for(guild.me).attach_files,
            )
        ):
            return None

        targets: List[Object | Member | User] = [user] if user else []
        if from_channel and hasattr(from_channel, "id"):
            targets.append(from_channel)

        if targets:
            ignored = cast(
                Optional[bool],
                await self.bot.db.fetchval(
                    """
                    SELECT log_ignore_ids && $2
                    FROM settings
                    WHERE guild_id = $1
                    """,
                    guild.id,
                    [target.id for target in targets],
                ),
            )
            if ignored:
                return

        if user:
            if not embed.author:
                embed.set_author(
                    name=user,
                    icon_url=(
                        user.display_avatar
                        if isinstance(user, (Member, User))
                        else None
                    ),
                )

            if not embed.footer:
                embed.set_footer(text=f"{user.__class__.__name__} ID: {user.id}")

        if not embed.timestamp:
            embed.timestamp = utcnow()

        key = f"logging:{guild.id}"
        async with self.bot.redis.get_lock(key, sleep=2):
            with suppress(HTTPException):
                return await channel.send(
                    embed=embed,
                    files=files,
                    silent=True,
                )

    @Cog.listener("on_member_join")
    async def log_member_join(self, member: Member) -> None:
        """
        Log when a member joins.
        """

        embed = Embed(
            title="Member Joined",
            description=(
                "**⚠ Account is less than 1 day old!**\n"
                if member.created_at > utcnow() - timedelta(days=1)
                else ""
            ),
        )
        embed.add_field(
            name="**Creation**",
            value=f"{format_dt(member.created_at, 'F')} ({format_dt(member.created_at, 'R')})",
        )

        try:
            log_data = {
                "event": {
                    "type": "MEMBER_ADD",
                    "timestamp": utcnow().isoformat()
                },
                "member": {
                    "id": str(member.id),
                    "name": member.name.encode('utf-8', 'ignore').decode('utf-8'),
                    "display_name": member.display_name.encode('utf-8', 'ignore').decode('utf-8'),
                    "bot": member.bot,
                    "created_at": member.created_at.isoformat(),
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "roles": [str(role.id) for role in member.roles[1:]],
                    "avatar_url": str(member.display_avatar.url)
                },
                "action": "JOIN",
                "details": {
                    "new_account": member.created_at > utcnow() - timedelta(days=1)
                }
            }

            await self.queue_log(
                member.guild.id,
                None,
                "MEMBER",
                log_data
            )
        except Exception as e:
            log.error(f"Failed to log member join: {e}")

        await self.log(
            member.guild,
            LogType.MEMBER,
            embed,
            user=member,
        )

    @Cog.listener("on_member_remove")
    async def log_member_remove(self, member: Member) -> None:
        """
        Log when a member leaves.
        """

        embed = Embed(title="Member Left")
        embed.add_field(
            name="**Creation**",
            value=f"{format_dt(member.created_at, 'F')} ({format_dt(member.created_at, 'R')})",
            inline=False,
        )
        if member.joined_at:
            embed.add_field(
                name="**Joined**",
                value=f"{format_dt(member.joined_at, 'F')} ({format_dt(member.joined_at, 'R')})",
                inline=False,
            )

        try:
            log_data = {
                "event": {
                    "type": "MEMBER_REMOVE",
                    "timestamp": utcnow().isoformat()
                },
                "member": {
                    "id": str(member.id),
                    "name": member.name.encode('utf-8', 'ignore').decode('utf-8'),
                    "display_name": member.display_name.encode('utf-8', 'ignore').decode('utf-8'),
                    "bot": member.bot,
                    "created_at": member.created_at.isoformat(),
                    "joined_at": member.joined_at.isoformat() if member.joined_at else None,
                    "roles": [str(role.id) for role in member.roles[1:]],
                    "avatar_url": str(member.display_avatar.url)
                },
                "action": "LEAVE",
                "reason": None
            }

            await self.queue_log(
                member.guild.id,
                None,
                "MEMBER",
                log_data
            )
        except Exception as e:
            log.error(f"Failed to log member remove: {e}")

        await self.log(
            member.guild,
            LogType.MEMBER,
            embed,
            user=member,
        )

    @Cog.listener("on_member_update")
    async def log_member_update(self, before: Member, after: Member) -> None:
        """
        Log when a member updates.
        """

        embed = Embed(title="Member Updated")
        changes = {}

        if before.nick != after.nick:
            embed.add_field(
                name="**Nickname**",
                value=f"**{before.nick or before.name}** -> **{after.nick or after.name}**",
                inline=False,
            )
            changes["nickname"] = {
                "before": before.nick or before.name,
                "after": after.nick or after.name
            }

        if not changes:
            return

        try:
            changes = {}
            if before.nick != after.nick:
                changes["nickname"] = {
                    "before": before.nick.encode('utf-8', 'ignore').decode('utf-8') if before.nick else None,
                    "after": after.nick.encode('utf-8', 'ignore').decode('utf-8') if after.nick else None
                }

            if not changes:
                return

            log_data = {
                "event": {
                    "type": "MEMBER_UPDATE",
                    "timestamp": utcnow().isoformat()
                },
                "member": {
                    "id": str(after.id),
                    "name": after.name.encode('utf-8', 'ignore').decode('utf-8'),
                    "display_name": after.display_name.encode('utf-8', 'ignore').decode('utf-8'),
                    "bot": after.bot,
                    "created_at": after.created_at.isoformat(),
                    "joined_at": after.joined_at.isoformat() if after.joined_at else None,
                    "roles": [str(role.id) for role in after.roles[1:]],
                    "avatar_url": str(after.display_avatar.url)
                },
                "changes": changes,
                "action": "UPDATE"
            }

            await self.queue_log(
                after.guild.id,
                None,
                "MEMBER",
                log_data
            )
        except Exception as e:
            log.error(f"Failed to log member update: {e}")

        await self.log(
            after.guild,
            LogType.MEMBER,
            embed,
            user=after,
        )

    @Cog.listener("on_voice_state_update")
    async def log_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
    ) -> None:
        """
        Log when a member's voice state updates.
        """

        embed = Embed(title="Voice State Updated")
        changes = {}
        action_type = None

        if before.channel == after.channel and after.channel:
            if before.self_mute != after.self_mute:
                action_type = "SELF_MUTE_TOGGLE"
                changes["self_mute"] = {"before": before.self_mute, "after": after.self_mute}
                embed.description = f"{member.mention} {'muted' if after.self_mute else 'unmuted'} themselves"

            elif before.self_deaf != after.self_deaf:
                action_type = "SELF_DEAF_TOGGLE"
                changes["self_deaf"] = {"before": before.self_deaf, "after": after.self_deaf}
                embed.description = f"{member.mention} {'deafened' if after.self_deaf else 'undeafened'} themselves"

            elif before.self_stream != after.self_stream:
                action_type = "STREAM_TOGGLE"
                changes["self_stream"] = {"before": before.self_stream, "after": after.self_stream}
                embed.description = f"{member.mention} {'started' if after.self_stream else 'stopped'} streaming"

            elif before.self_video != after.self_video:
                action_type = "VIDEO_TOGGLE"
                changes["self_video"] = {"before": before.self_video, "after": after.self_video}
                embed.description = f"{member.mention} {'started' if after.self_video else 'stopped'} video"

        elif not before.channel and after.channel:
            action_type = "CHANNEL_JOIN"
            changes["channel"] = {"before": None, "after": str(after.channel.id)}
            embed.description = f"{member.mention} joined **{after.channel}**"

        elif before.channel and not after.channel:
            action_type = "CHANNEL_LEAVE"
            changes["channel"] = {"before": str(before.channel.id), "after": None}
            embed.description = f"{member.mention} left **{before.channel}**"

        elif before.channel and after.channel:
            action_type = "CHANNEL_MOVE"
            changes["channel"] = {
                "before": str(before.channel.id),
                "after": str(after.channel.id)
            }
            embed.description = f"{member.mention} moved from **{before.channel}** to **{after.channel}**"

        if not action_type:
            return

        try:
            log_data = {
                "event": {
                    "type": "VOICE_UPDATE",
                    "timestamp": utcnow().isoformat()
                },
                "member": {
                    "id": str(member.id),
                    "name": member.name.encode('utf-8', 'ignore').decode('utf-8'),
                    "display_name": member.display_name.encode('utf-8', 'ignore').decode('utf-8')
                },
                "action": action_type,
                "changes": changes,
                "voice_state": {
                    "channel_id": str(after.channel.id) if after.channel else None,
                    "self_mute": after.self_mute,
                    "self_deaf": after.self_deaf,
                    "self_stream": after.self_stream,
                    "self_video": after.self_video,
                    "muted": after.mute,
                    "deafened": after.deaf
                }
            }

            await self.queue_log(
                member.guild.id,
                after.channel.id if after.channel else before.channel.id if before.channel else None,
                "VOICE",
                log_data
            )
        except Exception as e:
            log.error(f"Failed to log voice state update: {e}")

        await self.log(
            member.guild,
            LogType.VOICE,
            embed,
            user=member,
            from_channel=before.channel or after.channel,
        )

    @Cog.listener("on_bulk_message_delete")
    async def log_bulk_message_delete(self, messages: List[Message]) -> None:
        """
        Log when messages are bulk deleted.
        """

        if (
            not messages
            or not messages[0].guild
            or messages[0].author.bot
            or isinstance(
                messages[0].channel,
                (
                    GroupChannel,
                    DMChannel,
                    PartialMessageable,
                ),
            )
        ):
            return

        members = list({message.author for message in messages})
        embed = Embed(
            title="Messages Deleted",
            description=(
                f"**{len(messages)} messages** deleted in {messages[0].channel.mention}"
                f"\n> They were sent between {format_dt(messages[0].created_at, 't')} and {format_dt(messages[-1].created_at, 't')}"
            ),
        )
        embed.add_field(
            name=f"**{plural(members):member}**",
            value="\n".join(
                [f"> {member.mention} (`{member.id}`)" for member in members[:10]]
                + ([f"> ... and {len(members) - 10} more"] if len(members) > 10 else [])
            ),
        )

        message_data = [
            {
                "id": str(message.id),
                "content": message.content,
                "author": {
                    "id": str(message.author.id),
                    "name": str(message.author),
                    "bot": message.author.bot
                },
                "created_at": message.created_at.isoformat(),
                "attachments": [
                    {
                        "filename": attachment.filename,
                        "url": attachment.url,
                        "size": attachment.size
                    } for attachment in message.attachments
                ] if message.attachments else []
            }
            for message in messages
        ]

        log_data = {
            "event": {
                "type": "BULK_MESSAGE_DELETE",
                "timestamp": utcnow().isoformat()
            },
            "target": {
                "channel_id": str(messages[0].channel.id),
                "channel_name": messages[0].channel.name,
                "channel_type": str(messages[0].channel.type)
            },
            "messages": message_data,
            "details": f"{len(messages)} messages deleted in #{messages[0].channel.name}",
            "files": None
        }

        await self.queue_log(
            messages[0].guild.id,
            messages[0].channel.id,
            "MESSAGE",
            log_data
        )

        await self.log(
            messages[0].guild,
            LogType.MESSAGE,
            embed,
            from_channel=messages[0].channel,
            files=[
                File(
                    BytesIO(
                        "\n".join(
                            [
                                f"[{message.created_at:%d/%m/%Y - %H:%M}] {message.author} ({message.author.id}): {message.system_content}"
                                for message in messages
                                if message.system_content
                            ]
                        ).encode()
                    ),
                    filename=f"messages{utcnow().timestamp()}.txt",
                )
            ],
        )

    @Cog.listener("on_message_delete")
    async def log_message_delete(self, message: Message) -> None:
        """
        Log when a message is deleted.
        """

        if (
            not message.guild
            or message.author.bot
            or isinstance(
                message.channel,
                (
                    GroupChannel,
                    DMChannel,
                    PartialMessageable,
                ),
            )
        ):
            return

        embed = Embed(
            title="Message Deleted",
            description=f"Message from {message.author.mention} deleted in {message.channel.mention}",
        )
        if message.system_content:
            embed.add_field(
                name="**Message Content**",
                value=message.system_content[:1024],
                inline=False,
            )

        if message.attachments:
            embed.add_field(
                name="**Attachments**",
                value="\n".join(
                    [
                        f"[{attachment.filename}]({attachment.url})"
                        for attachment in message.attachments
                    ]
                ),
                inline=False,
            )

        elif message.stickers:
            embed.set_image(url=message.stickers[0].url)

        for _embed in message.embeds:
            if _embed.image:
                embed.set_image(url=_embed.image.url)

                break

        files = []
        for attachment in message.attachments:
            try:
                files.append(
                    await attachment.to_file(
                        description=f"Attachment removed from {message.author}'s message",
                        spoiler=attachment.is_spoiler(),
                    )
                )
            
            except discord.errors.NotFound:
                log.warning(f"Attachment {attachment.url} not found, skipping.")

        try:
            log_data = {
                "event": {
                    "type": "MESSAGE_DELETE",
                    "timestamp": utcnow().isoformat()
                },
                "message": {
                    "id": str(message.id),
                    "content": message.content.encode('utf-8', 'ignore').decode('utf-8') if message.content else "",
                    "created_at": message.created_at.isoformat(),
                    "attachments": [{
                        "filename": a.filename.encode('utf-8', 'ignore').decode('utf-8'),
                        "url": str(a.url),
                        "size": a.size,
                        "is_spoiler": a.is_spoiler()
                    } for a in message.attachments],
                    "stickers": [{
                        "id": str(s.id),
                        "name": s.name.encode('utf-8', 'ignore').decode('utf-8'),
                        "url": str(s.url)
                    } for s in message.stickers],
                    "embeds": [e.to_dict() for e in message.embeds if e.type == 'rich']
                },
                "channel": {
                    "id": str(message.channel.id),
                    "name": message.channel.name.encode('utf-8', 'ignore').decode('utf-8'),
                    "type": str(message.channel.type)
                },
                "author": {
                    "id": str(message.author.id),
                    "name": str(message.author).encode('utf-8', 'ignore').decode('utf-8'),
                    "display_name": message.author.display_name.encode('utf-8', 'ignore').decode('utf-8'),
                    "bot": message.author.bot
                }
            }

            await self.queue_log(
                message.guild.id,
                message.channel.id,
                "MESSAGE",
                log_data
            )
        except Exception as e:
            log.error(f"Failed to log message delete: {e}")

        await self.log(
            message.guild,
            LogType.MESSAGE,
            embed,
            from_channel=message.channel,
            files=files,
            user=message.author,
        )

    @Cog.listener("on_message_edit")
    async def log_message_edit(self, before: Message, after: Message) -> None:
        """
        Log when a message is edited.
        """

        if (
            not after.guild
            or after.author.bot
            or isinstance(
                after.channel,
                (
                    GroupChannel,
                    DMChannel,
                    PartialMessageable,
                ),
            )
            or after.embeds
        ):
            return

        embed = Embed(
            title="Message Edited",
            description=(
                (
                    f"Message from {after.author.mention} edited"
                    if before.content != after.content
                    else (
                        f"Attachment removed from {after.author.mention}'s message"
                        if before.attachments and not after.attachments
                        else (
                            f"Embed removed from {after.author.mention}'s message"
                            if before.embeds and not after.embeds
                            else ""
                        )
                    )
                )
                + f"\n> [*Jump to the Message in #{after.channel}*]({after.jump_url})"
            ),
        )
        if before.content != after.content:
            embed.add_field(
                name="**Before**",
                value=before.system_content[:1024],
                inline=False,
            )
            embed.add_field(
                name="**After**",
                value=after.system_content[:1024],
                inline=False,
            )

        if before.attachments and not after.attachments:
            embed.add_field(
                name="**Attachments**",
                value="\n".join(
                    [
                        f"[{attachment.filename}]({attachment.url})"
                        for attachment in before.attachments
                    ]
                ),
                inline=False,
            )

        if before.embeds and not after.embeds:
            for _embed in before.embeds:
                if _embed.image:
                    embed.set_image(url=_embed.image.url)

                    break

        log_data = {
            "event": {
                "type": "MESSAGE_EDIT",
                "timestamp": utcnow().isoformat()
            },
            "message": {
                "id": str(after.id),
                "jump_url": after.jump_url,
                "changes": {
                    "content": {
                        "before": before.content.encode('utf-8', 'ignore').decode('utf-8') if before.content else "",
                        "after": after.content.encode('utf-8', 'ignore').decode('utf-8') if after.content else ""
                    } if before.content != after.content else None,
                    "attachments": {
                        "before": [{
                            "filename": a.filename.encode('utf-8', 'ignore').decode('utf-8'),
                            "url": str(a.url),
                            "size": a.size
                        } for a in before.attachments],
                        "after": [{
                            "filename": a.filename.encode('utf-8', 'ignore').decode('utf-8'),
                            "url": str(a.url),
                            "size": a.size
                        } for a in after.attachments]
                    } if before.attachments != after.attachments else None,
                    "embeds": {
                        "before": [e.to_dict() for e in before.embeds if e.type == 'rich'],
                        "after": [e.to_dict() for e in after.embeds if e.type == 'rich']
                    } if before.embeds != after.embeds else None
                }
            },
            "channel": {
                "id": str(after.channel.id),
                "name": after.channel.name.encode('utf-8', 'ignore').decode('utf-8'),
                "type": str(after.channel.type)
            },
            "author": {
                "id": str(after.author.id),
                "name": str(after.author).encode('utf-8', 'ignore').decode('utf-8'),
                "display_name": after.author.display_name.encode('utf-8', 'ignore').decode('utf-8'),
                "bot": after.author.bot
            }
        }

        try:
            await self.queue_log(
                after.guild.id,
                after.channel.id,
                "MESSAGE",
                log_data
            )
        except Exception as e:
            log.error(f"Failed to log message edit: {e}")

        await self.log(
            after.guild,
            LogType.MESSAGE,
            embed,
            from_channel=after.channel,
            files=[
                await attachment.to_file(
                    description=f"Attachment removed from {after.author}'s message",
                    spoiler=attachment.is_spoiler(),
                )
                for attachment in before.attachments
            ],
            user=after.author,
        )

    @Cog.listener("on_audit_log_entry_role_create")
    async def log_role_creation(self, entry: AuditLogEntry) -> None:
        """
        Log when a role is created.
        """

        entry.target = cast(Role, entry.target)

        embed = Embed(
            title="Role Created",
            description=(
                f"Role **{entry.target.mention}** created by {entry.user.mention}"
                if entry.user
                else f"Role **{entry.target.mention}** created"
                + (" (integration)" if entry.target.is_integration() else "")
            ),
            color=(
                entry.target.color
                if entry.target.color != Colour.default()
                else Colour.dark_embed()
            ),
        )
        embed.set_thumbnail(url=entry.target.display_icon)

        embed.add_field(
            name="**Name**",
            value=entry.target.name,
            inline=False,
        )
        embed.add_field(
            name="**Color**",
            value=entry.target.color,
            inline=False,
        )

        log_data = {
            "event": {
                "type": "ROLE_CREATE",
                "timestamp": utcnow().isoformat()
            },
            "role": {
                "id": str(entry.target.id),
                "name": entry.target.name,
                "color": str(entry.target.color),
                "position": entry.target.position,
                "permissions": entry.target.permissions.value,
                "is_integration": entry.target.is_integration(),
                "icon_url": str(entry.target.display_icon) if entry.target.display_icon else None
            },
            "moderator": {
                "id": str(entry.user.id) if entry.user else None,
                "name": str(entry.user) if entry.user else None,
                "bot": entry.user.bot if entry.user else None
            } if entry.user else None
        }

        await self.queue_log(
            entry.guild.id,
            None,
            "ROLE",
            log_data
        )

        await self.log(
            entry.guild,
            LogType.ROLE,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_role_update")
    async def log_role_updated(self, entry: AuditLogEntry) -> None:
        """
        Log when a role is updated.
        """

        entry.target = cast(Role, entry.target)

        embed = Embed(
            title="Role Updated",
            description=(
                f"Role **{entry.target.mention}** updated by {entry.user.mention}"
                if entry.user
                else f"Role **{entry.target.mention}** updated"
            ),
            color=(
                entry.target.color
                if entry.target.color != Colour.default()
                else Colour.dark_embed()
            ),
        )
        embed.set_thumbnail(url=entry.target.display_icon)

        if (
            hasattr(entry.before, "name")
            and hasattr(entry.after, "name")
            and entry.before.name != entry.after.name
        ):
            embed.add_field(
                name="**Name**",
                value=f"**{entry.before.name}** -> **{entry.after.name}**",
                inline=False,
            )

        if (
            hasattr(entry.before, "color")
            and hasattr(entry.after, "color")
            and entry.before.color != entry.after.color
        ):
            embed.add_field(
                name="**Color**",
                value=f"`{entry.before.color}` -> `{entry.after.color}`",
                inline=False,
            )

        if (
            hasattr(entry.before, "permissions")
            and hasattr(entry.after, "permissions")
            and entry.before.permissions != entry.after.permissions
        ):
            before_perms = cast(Permissions, entry.before.permissions)
            after_perms = cast(Permissions, entry.after.permissions)

            embed.add_field(
                name="**Permissions Modified**",
                value="\n".join(
                    [
                        f"`{'✅' if status else '❌'}`"
                        f" **{permission.replace('_', ' ').title()}**"
                        for permission, status in after_perms
                        if status != getattr(before_perms, permission)
                    ]
                ),
                inline=False,
            )

        if not embed.fields:
            return

        changes = {}
        if (hasattr(entry.before, "name") and hasattr(entry.after, "name") 
            and entry.before.name != entry.after.name):
            changes["name"] = {
                "before": entry.before.name,
                "after": entry.after.name
            }

        if (hasattr(entry.before, "color") and hasattr(entry.after, "color") 
            and entry.before.color != entry.after.color):
            changes["color"] = {
                "before": str(entry.before.color),
                "after": str(entry.after.color)
            }

        if (hasattr(entry.before, "permissions") and hasattr(entry.after, "permissions") 
            and entry.before.permissions != entry.after.permissions):
            before_perms = cast(Permissions, entry.before.permissions)
            after_perms = cast(Permissions, entry.after.permissions)
            
            perm_changes = []
            for permission, status in after_perms:
                if status != getattr(before_perms, permission):
                    perm_changes.append({
                        "permission": permission,
                        "before": getattr(before_perms, permission),
                        "after": status
                    })
            changes["permissions"] = perm_changes

        if not embed.fields:
            return

        log_data = {
            "event": {
                "type": "ROLE_UPDATE",
                "timestamp": utcnow().isoformat()
            },
            "role": {
                "id": str(entry.target.id),
                "name": entry.target.name,
                "color": str(entry.target.color),
                "position": entry.target.position,
                "permissions": entry.target.permissions.value,
                "icon_url": str(entry.target.display_icon) if entry.target.display_icon else None
            },
            "changes": changes,
            "moderator": {
                "id": str(entry.user.id) if entry.user else None,
                "name": str(entry.user) if entry.user else None,
                "bot": entry.user.bot if entry.user else None
            } if entry.user else None
        }

        await self.queue_log(
            entry.guild.id,
            None,
            "ROLE",
            log_data
        )

        await self.log(
            entry.guild,
            LogType.ROLE,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_role_delete")
    async def log_role_deletion(self, entry: AuditLogEntry) -> None:
        """
        Log when a role is deleted.
        """

        if isinstance(entry.target, Object):
            return

        embed = Embed(
            title="Role Deleted",
            description=(
                f"Role **{entry.target}** deleted by {entry.user.mention}"
                if entry.user
                else f"Role **{entry.target}** deleted"
            ),
        )

        log_data = {
            "event": {
                "type": "ROLE_DELETE",
                "timestamp": utcnow().isoformat()
            },
            "role": {
                "id": str(entry.target.id),
                "name": str(entry.target)
            },
            "moderator": {
                "id": str(entry.user.id) if entry.user else None,
                "name": str(entry.user) if entry.user else None,
                "bot": entry.user.bot if entry.user else None
            } if entry.user else None
        }

        await self.queue_log(
            entry.guild.id,
            None,
            "ROLE",
            log_data
        )

        await self.log(
            entry.guild,
            LogType.ROLE,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_member_role_update")
    async def log_member_role_update(self, entry: AuditLogEntry) -> None:
        """
        Log when a member's roles are updated.
        """

        if not isinstance(entry.target, Member):
            return

        roles_granted = [
            role for role in entry.after.roles if role not in entry.before.roles
        ]
        roles_removed = [
            role for role in entry.before.roles if role not in entry.after.roles
        ]
        embed = Embed(
            title="Member Roles Updated",
            description=f"{entry.target.mention} was {'granted' if roles_granted else 'removed from'} {human_join([role.mention for role in (roles_granted or roles_removed)], final='and')}",
        )

        if entry.user and entry.target != entry.user:
            embed.add_field(
                name="**Moderator**",
                value=f"{entry.user.mention} (`{entry.user.id}`)",
            )

        log_data = {
            "event": {
                "type": "MEMBER_ROLE_UPDATE",
                "timestamp": utcnow().isoformat()
            },
            "member": {
                "id": str(entry.target.id),
                "name": str(entry.target),
                "display_name": entry.target.display_name
            },
            "changes": {
                "roles_granted": [{
                    "id": str(role.id),
                    "name": role.name
                } for role in roles_granted],
                "roles_removed": [{
                    "id": str(role.id),
                    "name": role.name
                } for role in roles_removed]
            },
            "moderator": {
                "id": str(entry.user.id) if entry.user else None,
                "name": str(entry.user) if entry.user else None,
                "bot": entry.user.bot if entry.user else None
            } if entry.user else None
        }

        await self.queue_log(
            entry.guild.id,
            None,
            "MEMBER_ROLE",
            log_data
        )

        await self.log(
            entry.guild,
            LogType.ROLE,
            embed,
            user=entry.target,
        )

    @Cog.listener("on_audit_log_entry_channel_create")
    async def log_channel_creation(self, entry: AuditLogEntry) -> None:
        """
        Log when a channel is created.
        """

        entry.target = cast(GuildChannel, entry.target)
        if isinstance(
            entry.target,
            (
                Object,
                VoiceChannel,
                GroupChannel,
                DMChannel,
                PartialMessageable,
            ),
        ):
            return

        embed = Embed(
            title="Channel Created",
            description=(
                f"{entry.target.type.name.replace('_', ' ').title()} channel {entry.target.mention} created by {entry.user.mention}"
                if entry.user
                else f"{entry.target.type.name.replace('_', ' ').title()} channel {entry.target.mention} created"
            ),
        )
        embed.add_field(
            name="**ID**",
            value=f"`{entry.target.id}`",
        )

        log_data = {
            "event": {
                "type": "CHANNEL_CREATE",
                "timestamp": utcnow().isoformat()
            },
            "channel": {
                "id": str(entry.target.id),
                "name": entry.target.name,
                "type": str(entry.target.type),
                "position": entry.target.position,
                "category_id": str(entry.target.category_id) if entry.target.category_id else None
            },
            "moderator": {
                "id": str(entry.user.id) if entry.user else None,
                "name": str(entry.user) if entry.user else None,
                "bot": entry.user.bot if entry.user else None
            } if entry.user else None
        }

        await self.queue_log(
            entry.guild.id,
            entry.target.id,
            "CHANNEL",
            log_data
        )

        await self.log(
            entry.guild,
            LogType.CHANNEL,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_channel_update")
    async def log_channel_updated(self, entry: AuditLogEntry) -> None:
        """
        Log when a channel is updated.
        """

        entry.target = cast(GuildChannel, entry.target)
        if isinstance(
            entry.target,
            (
                Object,
                GroupChannel,
                DMChannel,
                PartialMessageable,
            ),
        ):
            return

        elif not entry.user:
            return

        embed = Embed(
            title="Channel Updated",
            description=(
                f"Stage channel {entry.target.mention} was {'opened' if entry.target.topic else 'closed'} by {entry.user.mention}"
                if isinstance(entry.target, StageChannel)
                else (
                    f"{entry.target.type.name.replace('_', ' ').title()} channel {entry.target.mention} updated by {entry.user.mention}"
                    if entry.user
                    else f"{entry.target.type.name.replace('_', ' ').title()} channel {entry.target.mention} updated"
                )
            ),
        )
        embed.add_field(
            name="**Creation**",
            value=f"{format_dt(entry.target.created_at, 'F')} ({format_dt(entry.target.created_at, 'R')})",
            inline=False,
        )

        if (
            hasattr(entry.before, "name")
            and hasattr(entry.after, "name")
            and entry.before.name != entry.after.name
        ):
            embed.add_field(
                name="**Name**",
                value=f"**{entry.before.name}** -> **{entry.after.name}**",
                inline=False,
            )

        if (
            hasattr(entry.before, "topic")
            and hasattr(entry.after, "topic")
            and entry.before.topic != entry.after.topic
        ):
            embed.add_field(
                name="**Topic**",
                value=f"**{shorten(entry.before.topic or 'No topic')}** -> **{shorten(entry.after.topic or 'No topic')}**",
                inline=False,
            )

        if (
            hasattr(entry.before, "nsfw")
            and hasattr(entry.after, "nsfw")
            and entry.before.nsfw != entry.after.nsfw
        ):
            embed.add_field(
                name="**NSFW**",
                value=f"`{entry.before.nsfw}` -> `{entry.after.nsfw}`",
                inline=False,
            )

        if (
            hasattr(entry.before, "bitrate")
            and hasattr(entry.after, "bitrate")
            and entry.before.bitrate != entry.after.bitrate
        ):
            embed.add_field(
                name="**Bitrate**",
                value=f"`{entry.before.bitrate / 1000}kbps` -> `{entry.after.bitrate / 1000}kbps`",
                inline=False,
            )

        if (
            hasattr(entry.before, "user_limit")
            and hasattr(entry.after, "user_limit")
            and entry.before.user_limit != entry.after.user_limit
        ):
            embed.add_field(
                name="**User Limit**",
                value=f"`{entry.before.user_limit}` -> `{entry.after.user_limit}`",
                inline=False,
            )

        if (
            hasattr(entry.before, "slowmode_delay")
            and hasattr(entry.after, "slowmode_delay")
            and entry.before.slowmode_delay != entry.after.slowmode_delay
        ):
            embed.add_field(
                name="**Slowmode Delay**",
                value=f"`{entry.before.slowmode_delay}s` -> `{entry.after.slowmode_delay}s`",
                inline=False,
            )

        if not embed.fields and not isinstance(entry.target, StageChannel):
            return

        changes = {}
        if (hasattr(entry.before, "name") and hasattr(entry.after, "name") 
            and entry.before.name != entry.after.name):
            changes["name"] = {
                "before": entry.before.name,
                "after": entry.after.name
            }

        if (hasattr(entry.before, "topic") and hasattr(entry.after, "topic") 
            and entry.before.topic != entry.after.topic):
            changes["topic"] = {
                "before": entry.before.topic,
                "after": entry.after.topic
            }

        if (hasattr(entry.before, "nsfw") and hasattr(entry.after, "nsfw") 
            and entry.before.nsfw != entry.after.nsfw):
            changes["nsfw"] = {
                "before": entry.before.nsfw,
                "after": entry.after.nsfw
            }

        if (hasattr(entry.before, "bitrate") and hasattr(entry.after, "bitrate") 
            and entry.before.bitrate != entry.after.bitrate):
            changes["bitrate"] = {
                "before": entry.before.bitrate,
                "after": entry.after.bitrate
            }

        if (hasattr(entry.before, "user_limit") and hasattr(entry.after, "user_limit") 
            and entry.before.user_limit != entry.after.user_limit):
            changes["user_limit"] = {
                "before": entry.before.user_limit,
                "after": entry.after.user_limit
            }

        if (hasattr(entry.before, "slowmode_delay") and hasattr(entry.after, "slowmode_delay") 
            and entry.before.slowmode_delay != entry.after.slowmode_delay):
            changes["slowmode_delay"] = {
                "before": entry.before.slowmode_delay,
                "after": entry.after.slowmode_delay
            }

        log_data = {
            "event": {
                "type": "CHANNEL_UPDATE",
                "timestamp": utcnow().isoformat()
            },
            "channel": {
                "id": str(entry.target.id),
                "name": entry.target.name,
                "type": str(entry.target.type),
                "created_at": entry.target.created_at.isoformat()
            },
            "changes": changes,
            "moderator": {
                "id": str(entry.user.id) if entry.user else None,
                "name": str(entry.user) if entry.user else None,
                "bot": entry.user.bot if entry.user else None
            } if entry.user else None
        }

        await self.queue_log(
            entry.guild.id,
            entry.target.id,
            "CHANNEL",
            log_data
        )

        await self.log(
            entry.guild,
            LogType.CHANNEL,
            embed,
            from_channel=entry.target,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_channel_delete")
    async def log_channel_deletion(self, entry: AuditLogEntry) -> None:
        """
        Log when a channel is deleted.
        """

        entry.target = cast(Object, entry.target)
        channel = cast(GuildChannel, entry.before)

        embed = Embed(
            title="Channel Deleted",
            description=(
                f"{channel.type.name.replace('_', ' ').title()} channel **{channel.name}** deleted by {entry.user.mention}"
                if entry.user
                else f"{channel.type.name.replace('_', ' ').title()} channel **{channel.name}** deleted"
            ),
        )
        embed.add_field(
            name="**Creation**",
            value=f"{format_dt(entry.target.created_at, 'F')} ({format_dt(entry.target.created_at, 'R')})",
        )

        log_data = {
            "event": {
                "type": "CHANNEL_DELETE",
                "timestamp": utcnow().isoformat()
            },
            "channel": {
                "id": str(entry.target.id),
                "name": channel.name,
                "type": str(channel.type),
                "created_at": entry.target.created_at.isoformat() if hasattr(entry.target, 'created_at') else None
            },
            "moderator": {
                "id": str(entry.user.id) if entry.user else None,
                "name": str(entry.user) if entry.user else None,
                "bot": entry.user.bot if entry.user else None
            } if entry.user else None
        }

        await self.queue_log(
            entry.guild.id,
            entry.target.id,
            "CHANNEL",
            log_data
        )

        await self.log(
            entry.guild,
            LogType.CHANNEL,
            embed,
            from_channel=entry.target,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_invite_create")
    async def log_invite_creation(self, entry: AuditLogEntry) -> None:
        """
        Log when an invite is created.
        """

        invite = cast(Invite, entry.target)

        embed = Embed(
            title="Invite Created",
            description=(
                f"{'Temporary' if invite.temporary else ''} Invite [`{invite.code}`]({invite.url}) created by {entry.user.mention}"
                if entry.user
                else f"{'Temporary' if invite.temporary else ''} Invite [`{invite.code}`]({invite.url}) created"
            ),
        )
        if invite.max_uses:
            embed.add_field(
                name="**Max Uses**",
                value=f"`{invite.max_uses}`",
            )

        await self.log(
            entry.guild,
            LogType.INVITE,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_invite_delete")
    async def log_invite_deletion(self, entry: AuditLogEntry) -> None:
        """
        Log when an invite is deleted.
        """

        invite = cast(Invite, entry.target)

        embed = Embed(
            title="Invite Deleted",
            description=(
                f"{'Temporary' if invite.temporary else ''} Invite [`{invite.code}`]({invite.url}) deleted by {entry.user.mention}"
                if entry.user
                else f"{'Temporary' if invite.temporary else ''} Invite [`{invite.code}`]({invite.url}) deleted"
            ),
        )
        if invite.uses:
            embed.add_field(
                name="**Uses**",
                value=f"`{invite.uses}`/`{invite.max_uses or '∞'}`",
            )

        if invite.inviter and invite.inviter != entry.user:
            embed.add_field(
                name="**Inviter**",
                value=f"{invite.inviter} (`{invite.inviter.id}`)",
            )

        await self.log(
            entry.guild,
            LogType.INVITE,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_emoji_create")
    async def log_emoji_creation(self, entry: AuditLogEntry) -> None:
        """
        Log when an emoji is created.
        """

        entry.target = cast(Emoji, entry.target)
        if not isinstance(entry.target, Emoji):
            return

        embed = Embed(
            title="Emoji Created",
            description=f"Emoji created by {entry.user.mention}" if entry.user else "",
        )
        embed.set_thumbnail(url=entry.target.url)

        embed.add_field(
            name="**Name**",
            value=entry.target.name,
        )

        await self.log(
            entry.guild,
            LogType.EMOJI,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_emoji_update")
    async def log_emoji_updated(self, entry: AuditLogEntry) -> None:
        """
        Log when an emoji is updated.
        """

        entry.target = cast(Emoji, entry.target)
        if not isinstance(entry.target, Emoji):
            return

        embed = Embed(
            title="Emoji Updated",
            description=f"Emoji updated by {entry.user.mention}" if entry.user else "",
        )
        embed.set_thumbnail(url=entry.target.url)

        if (
            hasattr(entry.before, "name")
            and hasattr(entry.after, "name")
            and entry.before.name != entry.after.name
        ):
            embed.add_field(
                name="**Name**",
                value=f"**{entry.before.name}** -> **{entry.after.name}**",
                inline=False,
            )

        await self.log(
            entry.guild,
            LogType.EMOJI,
            embed,
            user=entry.user,
        )

    @Cog.listener("on_audit_log_entry_emoji_delete")
    async def log_emoji_deletion(self, entry: AuditLogEntry) -> None:
        """
        Log when an emoji is deleted.
        """

        embed = Embed(
            title="Emoji Deleted",
            description=(
                f"Emoji **{entry.before.name}** deleted by {entry.user.mention}"
                if entry.user
                else f"Emoji {entry.before.name} deleted"
            ),
        )

        await self.log(
            entry.guild,
            LogType.EMOJI,
            embed,
            user=entry.user,
        )

    def _sanitize_dict(self, data: dict) -> dict:
        """Recursively sanitize all string values in a dictionary."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = value.encode('utf-8', 'ignore').decode('utf-8')
            elif isinstance(value, dict):
                result[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict)
                    else item.encode('utf-8', 'ignore').decode('utf-8') if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result

    async def _safe_db_execute(self, query: str, *args) -> None:
        """Execute database query with proper handling of all data types."""
        try:
            processed_args = []
            for i, arg in enumerate(args):
                if i == 0 and arg is None: 
                    continue  
                
                if isinstance(arg, dict):
                    processed_args.append(json.dumps(arg))
                elif isinstance(arg, (int, bool, type(None))):
                    processed_args.append(arg)
                elif isinstance(arg, list):
                    processed_args.append([str(x) if x is not None else None for x in arg])
                else:
                    processed_args.append(str(arg))
            
            if len(processed_args) >= 4:  
                await self.bot.db.execute(query, *processed_args)
        except Exception as e:
            log.error(f"Failed to execute db query: {e}")