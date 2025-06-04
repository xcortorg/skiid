from discord.ext.commands import (
    Cog,
    command,
    group,
    Expiration,
    Converter,
    SafeSnowflake,
    KickChannelConverter,
    MultipleRoles,
    CommandError,
    MaxConcurrencyReached,
    AssignedRole,
    has_permissions,
    BucketType,
    CommandConverter,
    Greedy,
    EmbedConverter,
)
from typing import Union, Optional, List, Dict
from discord import (
    Client,
    Embed,
    TextChannel,
    Member,
    User,
    VoiceChannel,
    Object,
    Thread,
    PermissionOverwrite,
    Color,
    HTTPException,
    Role,
    utils,
    Message,
)
from humanize import naturaldelta
from aiohttp import ClientSession
from discord.utils import utcnow
import asyncio
from asyncio import Event, Task, create_task
from collections import defaultdict
from asyncio import Lock
import json
from var.variables import URL
from datetime import datetime, timedelta
from lib.patch.context import Context
from lib.classes.database import Record
from lib.classes.builtins import shorten
import humanize
from lib.worker import offloaded
from pydantic import BaseModel
from enum import Enum, auto
from fast_string_match import closest_match_distance as cmd


@property
def is_deleteable(self: Message) -> bool:
    now = utils.utcnow() - datetime.timedelta(days=14)
    return int(self.created_at.timestamp()) > int(now.timestamp())


Message.is_deleteable = is_deleteable


@offloaded
def prepare_icon(data: bytes) -> bytes:
    from PIL import Image
    from io import BytesIO

    image = Image.frombytes("RGBA", data)
    image = image.resize((64, 64))

    with BytesIO() as output:
        quality = 95
        while True:
            image.save(output, format="PNG", quality=quality)
            current_size_kb = output.tell() / 1024

            if current_size_kb <= 256 or quality <= 10:
                break

            output.seek(0)
            output.truncate()

            quality -= 5
    return output.getvalue()


class ModerationStatistics(BaseModel):
    bans: Optional[int] = 0
    unbans: Optional[int] = 0
    kicks: Optional[int] = 0
    jails: Optional[int] = 0
    unjails: Optional[int] = 0
    mutes: Optional[int] = 0
    unmutes: Optional[int] = 0

    @classmethod
    async def from_data(cls, data: dict):
        return cls(**data)


class CaseType(Enum):
    bans = auto()
    unbans = auto()
    kicks = auto()
    jails = auto()
    unjails = auto()
    mutes = auto()
    unmutes = auto()


HISTORY_MAPPING = {
    "ban": "banned",
    "kick": "kicked",
    "tempban": "temp banned",
    "mute": "muted",
    "unjail": "unjailed",
    "jail": "jailed",
    "softban": "soft banned",
    "hardban": "hard banned",
    "unban": "unbanned",
    "unmute": "unmuted",
    "hardunban": "unhardbanned",
}


def get_integers(argument: str) -> int:
    integers = "".join(i for i in argument if argument.isdigit)
    return int(integers)


class DeleteHistory(Converter):
    async def convert(self, ctx: Context, argument: str):
        return get_integers(argument)


class ModerationCommand(Converter):
    async def convert(self, ctx: Context, argument: str):
        if not (action := HISTORY_MAPPING.get(argument.lower())):
            raise CommandError("that is not a valid moderation command")
        return action


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot
        self.locks = defaultdict(Lock)
        self.events: Dict[str, Event] = {}
        self.tasks: Dict[str, Task] = {}

    async def cog_before_invoke(self, ctx: Context):
        if "purge" in ctx.command.qualified_name:
            if task := self.tasks.get(f"purge-{ctx.guild.id}"):
                raise MaxConcurrencyReached(1, BucketType.guild)

    async def store_statistics(
        self, ctx: Context, member: Member, store: Optional[bool] = True
    ):
        command = ctx.command.qualified_name
        if command == "ban":
            case_type = CaseType.bans
        elif command == "kick":
            case_type = CaseType.kicks
        elif command == "unban":
            case_type = CaseType.unbans
        elif command == "jail":
            case_type = CaseType.jails
        elif command == "unjail":
            case_type = CaseType.unjails
        elif command == "untime":
            case_type = CaseType.unmutes
        elif command == "mute":
            case_type = CaseType.mutes
        elif command == "modstats":
            if not store:
                data = json.loads(
                    await self.bot.db.fetchval(
                        """SELECT data FROM moderation_statistics WHERE guild_id = $1 AND user_id = $2""",
                        ctx.guild.id,
                        member.id,
                    )
                    or "{}"
                )
                return data
            else:
                return
        else:
            return
        data = json.loads(
            await self.bot.db.fetchval(
                """SELECT data FROM moderation_statistics WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
            or "{}"
        )
        if not store:
            return data
        name = str(case_type.name)
        if not data.get(name):
            data[name] = 1
        else:
            data[name] += 1
        await self.bot.db.execute(
            """INSERT INTO moderation_statistics (guild_id, user_id, data) VALUES($1, $2, $3) ON CONFLICT(guild_id, user_id) DO UPDATE SET data = excluded.data""",
            ctx.guild.id,
            member.id,
            json.dumps(data),
        )
        return True

    async def moderation_entry(
        self,
        ctx: Context,
        target: Union[Member, User, Role, TextChannel, str],
        action: str,
        reason: str = "No reason provided",
    ):
        """Create a log entry for moderation actions"""

        jail_log = await self.bot.db.fetch_config(ctx.guild.id, "jail_log")
        channel = self.bot.get_channel(jail_log)
        if not channel:
            return

        async with self.locks["cases"]:
            case = (
                await self.bot.db.fetchval(
                    "SELECT COUNT(*) FROM cases WHERE guild_id = $1", ctx.guild.id
                )
                + 1
            )

            if type(target) in (Member, User):
                _TARGET = "Member"
            elif type(target) is Role:
                _TARGET = "Role"
            elif type(target) is TextChannel:
                _TARGET = "Channel"
            else:
                _TARGET = "Target"

            await self.bot.db.execute(
                "INSERT INTO cases (guild_id, case_id, case_type, moderator_id, target_id, moderator, target, reason, timestamp)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
                ctx.guild.id,
                case,
                action.lower(),
                ctx.author.id,
                target.id,
                str(ctx.author),
                str(target),
                reason,
                datetime.now(),
            )

    @group(
        name="kick",
        description="Kicks the mentioned user",
        example=",kick @jon",
        invoke_without_command=True,
    )
    @has_permissions(kick_members=True)
    async def kick(self, ctx: Context, *, member: SafeSnowflake):
        if isinstance(member, User):
            raise CommandError(f"user {member.mention} is not apart of this server")
        await ctx.guild.kick(member, reason=f"kicked by {str(ctx.author)}")
        self.bot.dispatch(
            f"{ctx.command.qualified_name.lower()}_create",
            member,
            ctx.guild,
            ctx.author,
        )
        await self.moderation_entry(ctx, member, "kicked")
        return await ctx.success("👍", no_embed=True)

    @group(
        name="remind",
        description="Get reminders for a duration set about whatever you choose",
        aliases=["reminder"],
        example=",remind 1h To get food",
    )
    async def remind(self, ctx: Context, timeframe: Expiration, *, reason: str):
        ts = datetime.now() + timedelta(seconds=timeframe)
        await self.bot.db.execute(
            """INSERT INTO reminders (user_id, expiration, created_at, reason) VALUES($1, $2, $3, $4)""",
            ctx.author.id,
            ts,
            datetime.now(),
            reason,
        )
        return await ctx.send(f"ok ill remind u {utils.format_dt(ts, style='R')}")

    @remind.command(
        name="remove",
        aliases=["del", "delete"],
        description="Remove a reminder",
        example=",remind remove 2",
    )
    async def remind_remove(self, ctx: Context, id: int):
        data = await self.bot.db.fetch(
            """SELECT * FROM reminders WHERE user_id = $1 ORDER BY created_at DESC""",
            ctx.author.id,
        )
        if not data:
            raise CommandError("You haven't set any reminders")
        row = data[id - 1]
        await self.bot.db.execute(
            """DELETE FROM reminders WHERE created_at = $1 AND user_id = $2""",
            row.created_at,
            row.user_id,
        )
        return await ctx.send("ok, reminder deleted")

    @remind.command(
        name="list",
        aliases=["show", "view", "ls"],
        description="View a list of your reminders",
    )
    async def remind_list(self, ctx: Context):
        data = await self.bot.db.fetch(
            """SELECT * FROM reminders WHERE user_id = $1 ORDER BY created_at DESC""",
            ctx.author.id,
        )
        if not data:
            raise CommandError("You haven't set any reminders")
        embed = Embed(title="Reminders").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = [
            f"`{i}` {shorten(r.reason, 10)} - {utils.format_dt(r.expiration, style='R')}"
            for i, r in enumerate(data, start=1)
        ]
        return await ctx.paginate(embed, rows)

    @command(name="reminders", description="View a list of your reminders")
    async def reminders(self, ctx: Context):
        return await ctx.invoke(self.bot.get_command("remind list"))

    @group(
        name="thread",
        description="Commands to manage threads and forum posts",
        example=",thread lock #thread",
        invoke_without_command=True,
    )
    @has_permissions(manage_threads=True)
    async def thread(self, ctx: Context):
        return await ctx.send_help()

    @thread.command(
        name="lock",
        description="Lock a thread or forum post",
        example=",thread lock #thread",
    )
    @has_permissions(manage_threads=True)
    async def thread_lock(
        self,
        ctx: Context,
        thread: Thread,
        *,
        reason: Optional[str] = "No Reason Provided",
    ):
        if thread.locked:
            raise CommandError(
                f"Thread [**{thread.name}**]({thread.jump_url}) is already **locked**"
            )
        await thread.edit(locked=True, reason=reason)
        return await ctx.success(
            f"successfully locked [**{thread.name}**]({thread.jump_url})"
        )

    @thread.command(
        name="unlock",
        description="Unlock a thread or forum post",
        example=",thread unlock #thread",
    )
    @has_permissions(manage_threads=True)
    async def thread_unlock(
        self,
        ctx: Context,
        thread: Thread,
        *,
        reason: Optional[str] = "No Reason Provided",
    ):
        if not thread.locked:
            raise CommandError(
                f"Thread [**{thread.name}**]({thread.jump_url}) is not **locked**"
            )
        await thread.edit(locked=False, reason=reason)
        return await ctx.success(
            f"successfully unlocked [**{thread.name}**]({thread.jump_url})"
        )

    @kick.command(
        name="remove",
        description="Remove stream notifications from a channel",
        example=",kick remove #text adinross",
        extras={"cog_name": "Kick"},
    )
    @has_permissions(manage_guild=True)
    async def kick_remove(self, ctx: Context, channel: TextChannel, username: str):
        channels = (
            await self.bot.db.fetchval(
                """SELECT channels FROM kick_notifications WHERE guild_id = $1 AND username = $2""",
                ctx.guild.id,
                username,
            )
            or []
        )
        if channel.id not in channels:
            raise CommandError(
                f"No **notification** for `{username}'s` livestreams found for {channel.mention}"
            )
        channels.remove(channel.id)
        if not len(channels) == 0:
            await self.bot.db.execute(
                """UPDATE kick_notifications SET channels = $1 WHERE guild_id = $2 AND username = $3""",
                channels,
                ctx.guild.id,
                username,
            )
        else:
            await self.bot.db.execute(
                """DELETE FROM kick_notifications WHERE guild_id = $1 AND username = $2""",
                ctx.guild.id,
                username,
            )
        return await ctx.success(
            f"**Removed** notifications for `{username}'s` livestreams from {channel.mention}"
        )

    @kick.command(
        name="add",
        description="Add stream notifications to channel",
        example=",kick add #text adinross",
        extras={"cog_name": "Kick"},
    )
    @has_permissions(manage_guild=True)
    async def kick_add(
        self, ctx: Context, channel: TextChannel, username: KickChannelConverter
    ):
        channels = (
            await self.bot.db.fetchval(
                """SELECT channels FROM kick_notifications WHERE guild_id = $1 AND username = $2""",
                ctx.guild.id,
                username,
            )
            or []
        )
        channels.append(channel.id)
        await self.bot.db.execute(
            """INSERT INTO kick_notifications (guild_id, channels, username) VALUES($1, $2, $3) ON CONFLICT(guild_id, username) DO UPDATE SET channels = excluded.channels""",
            ctx.guild.id,
            channels,
            username,
        )
        return await ctx.success(
            f"**Added** notifications for `{username}'s` livestreams to {channel.mention}"
        )

    @kick.command(
        name="list",
        description="View all Kick stream notifications",
        extras={"cog_name": "Kick"},
    )
    @has_permissions(manage_guild=True)
    async def kick_list(self, ctx: Context):
        records = await self.bot.db.fetch(
            """SELECT username, channels FROM kick_notifications WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not records:
            raise CommandError("No **kick notifications** setup")
        rows = []
        for record in records:
            for channel_id in record.channels:
                if not (channel := ctx.guild.get_channel(channel_id)):
                    continue
                rows.append(f"**{record.username}** - {channel.mention}")
        if not rows:
            raise CommandError("No **kick notifications** setup")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        embed = Embed(color=self.bot.color, title="Kick Notifications").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(embed, rows)

    @kick.group(
        name="message",
        description="Set a message for Kick notifications",
        example=",kick message adinross {embed}{description:...}",
        invoke_without_command=True,
        extras={"cog_name": "Kick"},
    )
    @has_permissions(manage_guild=True)
    async def kick_message(self, ctx: Context, username: str, *, message: str):
        try:
            await self.bot.db.execute(
                """UPDATE kick_notifications SET message = $1 WHERE guild_id = $2 AND username = $3""",
                message,
                ctx.guild.id,
                username,
            )
        except Exception:
            return await ctx.fail(
                f"no **notification** added for `{username}'s` livestreams"
            )
        return await ctx.success(
            f"**Updated** the message for `{username}'s` livestream notifications"
        )

    @kick_message.command(
        name="view",
        description="View Kick message for new streams",
        example=",kick message view adinross",
        extras={"cog_name": "Kick"},
    )
    @has_permissions(manage_guild=True)
    async def kick_message_view(self, ctx: Context, username: str):
        message = await self.bot.db.fetchval(
            """SELECT message FROM kick_notifications WHERE guild_id = $1""",
            ctx.guild.id,
        )
        return await ctx.send(
            embed=Embed(
                color=self.bot.color,
                title=f"{username}'s notification message",
                description=f"```{message}```",
            ).set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        )

    @group(
        name="ban",
        description="Bans the mentioned user",
        example=",ban @jon 7d",
        invoke_without_command=True,
    )
    @has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: Context,
        member: SafeSnowflake,
        delete_history: Optional[Expiration] = None,
        reason: Optional[str] = "No Reason Provided",
    ):
        if not delete_history:
            delete_history = await self.bot.db.fetchval(
                """SELECT ban_purge FROM config WHERE guild_id = $1""", ctx.guild.id
            )
        await ctx.guild.ban(
            member,
            reason=f"{reason} | {str(ctx.author)}",
            delete_message_seconds=delete_history,
        )
        self.bot.dispatch(
            f"{ctx.command.qualified_name.lower()}_create",
            member,
            ctx.guild,
            ctx.author,
        )
        await self.moderation_entry(ctx, member, "banned", reason)
        return await ctx.success("👍", no_embed=True)

    @ban.command(
        name="purge",
        description="Set default ability to delete message history upon ban",
        example=",ban purge 7d",
    )
    @has_permissions(manage_guild=True, ban_members=True)
    async def ban_purge(self, ctx: Context, *, delete_history: Expiration):
        tf = humanize.naturaldelta(timedelta(seconds=delete_history))
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, ban_purge) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET ban_purge = excluded.ban_purge""",
            ctx.guild.id,
            delete_history,
        )
        return await ctx.success(f"successfully set the default ban purge to `{tf}`")

    @command(
        name="softban",
        description="Softbans the mentioned user and deleting 1 day of messages",
        example=",softban @jon",
    )
    @has_permissions(ban_members=True)
    async def softban(self, ctx: Context, *, member: SafeSnowflake):
        await ctx.guild.ban(
            member, delete_message_days=1, reason=f"softbanned by {str(ctx.author)}"
        )
        await ctx.guild.unban(member, reason=f"softbanned by {str(ctx.author)}")
        self.bot.dispatch("softban_create", member, ctx.guild, ctx.author)
        await self.moderation_entry(ctx, member, "soft banned")
        return await ctx.success("👍", no_embed=True)

    @command(
        name="tempban",
        description="Temporarily ban members",
        example=",tempban @jon 1h breaking the rules",
    )
    @has_permissions(ban_members=True)
    async def tempban(
        self,
        ctx: Context,
        member: SafeSnowflake,
        Expiration: Expiration,
        *,
        reason: Optional[str] = "No Reason Provided",
    ):
        tf = humanize.naturaldelta(timedelta(seconds=Expiration))
        ban_time = utils.utcnow() + timedelta(seconds=Expiration)
        await ctx.guild.ban(
            member, reason=f"TempBanned for {tf} by {str(ctx.author)} for {reason[:25]}"
        )
        self.bot.dispatch(
            f"{ctx.command.qualified_name.lower()}_create",
            member,
            ctx.guild,
            ctx.author,
            ban_time,
            reason,
        )
        await self.bot.db.execute(
            """INSERT INTO tempbans (guild_id, user_id, moderator_id, expiration, reason) VALUES($1, $2, $3, $4, $5) ON CONFLICT(guild_id, user_id) DO UPDATE SET expiration = excluded.expiration""",
            ctx.guild.id,
            member.id,
            ctx.author.id,
            ban_time,
            reason,
        )
        await self.moderation_entry(ctx, member, "temp banned", reason)
        return await ctx.success(
            f"successfully tempbanned {member.mention} for {tf} with the reason `{reason}`"
        )

    def find_ban(self, argument: str, users: List[User]):
        user_globals = {u.global_name.lower(): u for u in users}
        user_names = {u.name.lower(): u for u in users}
        matches = {}
        if match1 := cmd(argument.lower(), list(user_globals.keys())):
            matches[match1.lower()] = user_globals[match1.lower()]
        if match2 := cmd(argument.lower(), list(user_names.keys())):
            matches[match2.lower()] = user_names[match2.lower()]
        return matches[cmd(argument.lower(), list(matches.keys()))]

    @command(
        name="unban", description="Unbans the mentioned user", example=",unban jon"
    )
    @has_permissions(ban_members=True)
    async def unban(self, ctx: Context, *, member: Union[User, int, str]):
        if isinstance(member, User):
            member = member.id
        bans = []
        user = None
        unbanned = False
        if isinstance(member, int):
            try:
                banned_entry = await ctx.guild.fetch_ban(Object(id=member))
                await ctx.guild.unban(
                    banned_entry.user, reason=f"unbanned by {str(ctx.author)}"
                )
                await self.moderation_entry(ctx, banned_entry.user, "unban")
                await self.store_statistics(ctx, ctx.author)
                unbanned = True
            except Exception:
                pass
        try:
            async for ban in ctx.guild.bans():
                if str(ban.user.name) == member or ban.user.global_name == member:
                    user = ban.user
                    break
                else:
                    bans.append(ban.user)
        except Exception:
            pass
        if user:
            await ctx.guild.unban(user, reason=f"unbanned by {str(ctx.author)}")
            await self.moderation_entry(ctx, user, "unban")
            unbanned = True
            await self.store_statistics(ctx, ctx.author)
        else:
            if len(bans) == 0:
                raise CommandError(f"No ban found under `{member[:25]}`")
            try:
                user = await self.find_ban(member, bans)
                await ctx.guild.unban(user, reason=f"unbanned by {str(ctx.author)}")
                await self.moderation_entry(ctx, user, "unban")
                await self.store_statistics(ctx, ctx.author)
                unbanned = True
            except Exception:
                pass
        if not unbanned:
            raise CommandError(f"No ban entry matching `{member[:25]}` could be found")
        self.bot.dispatch("ban_delete", user, ctx.guild, ctx.author)
        return await ctx.success("👍", no_embed=True)

    @command(
        name="jail", description="Jails the mentioned user", example=",jail @jon 1d"
    )
    @has_permissions(manage_messages=True)
    async def jail(
        self,
        ctx: Context,
        member: SafeSnowflake,
        duration: Optional[Expiration] = None,
        *,
        reason: Optional[str] = "No Reason Provided",
    ):
        if duration:
            expiration = utils.utcnow() + timedelta(seconds=duration)
        else:
            expiration = None
        jailed = utils.get(ctx.guild.roles, name="jailed")
        if not jailed:
            raise CommandError(
                f"role for **jail** not found please run `{ctx.prefix}setup`"
            )
        roles = [m for m in member.roles if m.is_assignable()]
        ids = [r.id for r in roles]
        await self.bot.db.execute(
            """INSERT INTO jailed (guild_id, user_id, role_ids, expiration, reason, moderator_id) VALUES($1, $2, $3, $4, $5, $6) ON CONFLICT(guild_id, user_id) DO UPDATE SET expiration = excluded.expiration""",
            ctx.guild.id,
            member.id,
            ids,
            expiration,
            reason,
            ctx.author.id,
        )
        after_roles = [r for r in member.roles if not r.is_assignable()]
        after_roles.append(jailed)

        await member.edit(roles=after_roles, reason=f"jailed by {str(ctx.author)}")
        await self.moderation_entry(ctx, member, "jailed")
        self.bot.dispatch(
            "jail_create", member, ctx.guild, ctx.author, expiration, reason
        )
        return await ctx.success("👍", no_embed=True)

    @command(
        name="unjail", description="Unjails the mentioned user", example=",unjail @jon"
    )
    @has_permissions(manage_messages=True)
    async def unjail(self, ctx: Context, *, member: SafeSnowflake):
        if not (
            records := await self.bot.db.fetchval(
                """SELECT role_ids FROM jailed WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
        ):
            raise CommandError(f"no jail entry found for {member.mention}")
        after_roles = member.roles
        jailed = utils.get(ctx.guild.roles, name="jailed")
        if not jailed:
            raise CommandError(
                f"role for **jail** not found please run `{ctx.prefix}setup`"
            )
        try:
            after_roles.remove(jailed)
        except Exception:
            pass
        to_append = [ctx.guild.get_role(r) for r in records if ctx.guild.get_role(r)]
        after_roles.extend(to_append)
        await member.edit(roles=after_roles, reason=f"unjailed by {str(ctx.author)}")
        await self.bot.db.execute(
            """DELETE FROM jailed WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )
        self.bot.dispatch("jail_delete", member, ctx.guild, ctx.author)
        await self.moderation_entry(ctx, member, "unjailed")
        return await ctx.success("👍", no_embed=True)

    @command(
        name="jaillist",
        aliases=["jailed"],
        description="View a list of every current jailed member",
    )
    @has_permissions(manage_messages=True)
    async def jaillist(self, ctx: Context):
        data = await self.bot.db.execute(
            """SELECT * FROM jailed WHERE guild_id = $1""", ctx.guild.id
        )
        if not data:
            raise CommandError("No members have been jailed")
        embed = Embed(title="Jailed Members").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )

        def get_row(row: Record):
            if member := self.bot.get_user(row.user_id):
                name = f"{str(member)} ({row.user_id})"
            else:
                name = f"Unknown ({row.user_id})"
            if moderator_obj := self.bot.get_user(row.moderator_id):
                moderator = f"{str(moderator_obj)} ({row.moderator_id})"
            else:
                moderator = f"Unknown ({row.moderator_id})"
            jailed_at = utils.format_dt(row.jailed_at, style="R")
            time_left = (
                humanize.naturaldelta(seconds=row.expiration - datetime.now())
                if row.expiration
                else "Indefinite"
            )
            value = f"**Moderator:** {moderator}\n**Jailed At:** {jailed_at}\n**Reason:** {row.reason}\n**Duration:** {time_left}"
            return name, value

        chunks = utils.chunk_list(data, 2)
        embeds = []
        for chunk in chunks:
            _embed = embed.copy()
            for row in chunk:
                name, value = get_row(row)
                _embed.add_field(name=name, value=value, inline=False)
            embeds.append(_embed)
        return await ctx.alternative_paginate(embeds)

    @command(
        name="moderationhistory",
        aliases=["modhistory", "mhistory", "history"],
        description="View moderation actions from a staff member",
        example=",moderationhistory jonathan timeout",
    )
    @has_permissions(manage_messages=True)
    async def moderationhistory(
        self,
        ctx: Context,
        member: Optional[Member] = None,
        command: Optional[ModerationCommand] = None,
    ):
        if not member:
            member = ctx.author
        if not command:
            data = await self.bot.db.fetch(
                """SELECT case_type, moderator_id, target_id, reason, timestamp FROM cases WHERE guild_id = $1 AND target_id = $2""",
                ctx.guild.id,
                member.id,
            )
        else:
            data = await self.bot.db.fetch(
                """SELECT case_type, moderator_id, target_id, reason, timestamp FROM cases WHERE guild_id = $1 AND target_id = $2 AND case_type = $3""",
                ctx.guild.id,
                member.id,
                command,
            )
        chunks = utils.chunk_list(data, 2)
        embeds = []

        def get_row(row: Record):
            title = f"Case Log #{row.case_id} | {row.case_type.title()}"
            if mod := self.bot.get_user(row.target_id):
                member = f"{str(mod)} ({row.target_id})"
            else:
                member = f"Unknown ({row.target_id})"
            value = f"**Punished:** {utils.format_dt(row.timestamp, style='F')}\n**Member:** {member}\n**Reason:** {row.reason}"
            return title, value

        for chunk in chunks:
            embed = Embed(title="Moderation History").set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            )
            for row in chunk:
                title, value = get_row(row)
                embed.add_field(name=title, value=value, inline=False)
            embeds.append(embed)

        return await ctx.alternative_paginate(embeds)

    @group(
        name="lockdown",
        usage="<channel> <reason>",
        example=",lockdown #chat spamming",
        aliases=["lock"],
        invoke_without_command=True,
        description="Prevent regular members from typing",
    )
    @has_permissions(manage_channels=True)
    async def lockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel] = None,
        *,
        reason: str = "No reason provided",
    ):

        channel = channel or ctx.channel

        if channel.overwrites_for(ctx.guild.default_role).send_messages is False:
            return await ctx.warning(f"The channel {channel.mention} is already locked")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"{ctx.author}: {reason}",
        )

        await ctx.success(f"Locked channel {channel.mention}")
        await self.moderation_entry(ctx, channel, "lockdown", reason)

    @lockdown.command(
        name="all",
        usage="<reason>",
        description="Prevent regular members from typing in all channels",
    )
    @has_permissions(manage_channels=True)
    async def lockdown_all(self, ctx: Context, *, reason: str = "No reason provided"):

        ignored_channels = (
            await self.bot.db.fetchval(
                """SELECT lock_ignore FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if not ignored_channels:
            await ctx.prompt(
                f"Are you sure you want to lock all channels?\n> You haven't set any ignored channels with `{ctx.prefix}lock ignore` yet"
            )

        async with ctx.typing():
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.guild.default_role).send_messages
                    is False
                    or channel.id in ignored_channels
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = False
                await channel.set_permissions(
                    ctx.guild.default_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author}: {reason} (lockdown all)",
                )

            await ctx.success("Locked all channels")
            await self.moderation_entry(ctx, ctx.guild, "lockdown all", reason)

    @lockdown.group(
        name="ignore",
        usage="(subcommand) <args>",
        example=",lockdown ignore add #psa",
        description="Prevent channels from being altered",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore(self, ctx: Context):
        """Prevent channels from being altered"""

        await ctx.send_help()

    @lockdown_ignore.command(
        name="add",
        usage="(channel)",
        example=",lockdown ignore add #psa",
        description="Add a channel to the ignore list",
        aliases=["create"],
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_add(self, ctx: Context, *, channel: TextChannel):

        ignored_channels = (
            await self.bot.db.fetchval(
                """SELECT lock_ignore FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if channel.id in ignored_channels:
            return await ctx.warning(f"{channel.mention} is already ignored")

        ignored_channels.append(channel.id)
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, lock_ignore) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET lock_ignore = excluded.lock_ignore""",
            ctx.guild.id,
            ignored_channels,
        )
        await ctx.success(f"Now ignoring {channel.mention}")

    @lockdown_ignore.command(
        name="remove",
        example=",lockdown ignore remove #psa",
        description="Remove a channel from the ignore list",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_remove(self, ctx: Context, *, channel: TextChannel):

        ignored_channels = (
            await self.bot.db.fetchval(
                """SELECT lock_ignore FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if channel.id not in ignored_channels:
            return await ctx.warning(f"{channel.mention} isn't ignored")

        ignored_channels.remove(channel.id)
        await self.bot.db.execute(
            """INSERT INTO config (guild_id, lock_ignore) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET lock_ignore = excluded.lock_ignore""",
            ctx.guild.id,
            ignored_channels,
        )

        await ctx.success(f"No longer ignoring {channel.mention}")

    @lockdown_ignore.command(
        name="list",
        aliases=["show", "all"],
        description="List all ignored channels",
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_list(self, ctx: Context):
        lock_ignore = (
            await self.bot.db.fetchval(
                """SELECT lock_ignore FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        channels = [
            ctx.guild.get_channel(channel_id).mention
            for channel_id in lock_ignore
            if ctx.guild.get_channel(channel_id)
        ]
        if not channels:
            return await ctx.warning("No **ignored channels** have been set up")

        await ctx.paginate(
            Embed(
                title="Ignored Channels",
            ).set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url),
            channels,
        )

    @group(
        name="unlockdown",
        example=",unlockdown #chat behave",
        aliases=["unlock"],
        description="Allow regular members to type",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def unlockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel] = None,
        *,
        reason: str = "No reason provided",
    ):

        channel = channel or ctx.channel

        if channel.overwrites_for(ctx.guild.default_role).send_messages is True:
            return await ctx.fail(f"The channel {channel.mention} isn't locked")

        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = True
        await channel.set_permissions(
            ctx.guild.default_role,
            overwrite=overwrite,
            reason=f"{ctx.author}: {reason}",
        )

        await ctx.success(f"Unlocked channel {channel.mention}")
        await self.moderation_entry(ctx, channel, "unlockdown", reason)

    @unlockdown.command(
        name="all",
        example=",unlockdown all raid over",
        description="Allow regular members to type in all channels",
    )
    @has_permissions(manage_channels=True)
    async def unlockdown_all(self, ctx: Context, *, reason: str = "No reason provided"):

        ignored_channels = (
            await self.bot.db.fetchval(
                """SELECT lock_ignore FROM config WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if not ignored_channels:
            await ctx.prompt(
                f"Are you sure you want to unlock all channels?\n> You haven't set any ignored channels with `{ctx.prefix}lock ignore` yet"
            )

        async with ctx.typing():
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.guild.default_role).send_messages is True
                    or channel.id in ignored_channels
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.guild.default_role)
                overwrite.send_messages = True
                await channel.set_permissions(
                    ctx.guild.default_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author}: {reason} (unlockdown all)",
                )

            await ctx.success("Unlocked all channels")
            await self.moderation_entry(ctx, ctx.guild, "unlockdown all", reason)

    @group(
        name="role",
        description="Modify a member's roles",
        example=",role jonathan member, active",
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def role(
        self,
        ctx: Context,
        member: Optional[Member] = None,
        *,
        roles: Optional[MultipleRoles] = None,
    ):
        if not member:
            return await ctx.send_help()
        if not roles:
            return await ctx.send_help()

        after_roles = [ctx.guild.default_role]
        removed: List[Role] = []
        added: List[Role] = []

        if member.premium_since:
            after_roles.append(ctx.guild.premium_subscriber_role)
        for role in roles:
            if not ctx.author.id == ctx.guild.owner_id:
                if member.top_role >= ctx.author.top_role:
                    raise CommandError(
                        f"You cannot alter the roles of {member.mention} as their top role is {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                    )
                if role >= ctx.author.top_role:
                    raise CommandError(
                        f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                    )
            if role >= ctx.guild.me.top_role:
                raise CommandError(
                    f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
                )
            if role in member.roles:
                removed.append(role)
            else:
                after_roles.append(role)
                added.append(role)

        for role in member.roles:
            if role not in removed and role not in after_roles:
                after_roles.append(role)
        await member.edit(roles=after_roles)
        text = ""
        for role in added:
            text += f"**+{role.name},** "
        for role in removed:
            if not role == removed[-1]:
                text += f"**-{role.name},** "
            else:
                text += f"**-{role.name}**"
        if len(added) == 0 or len(removed) == 0:
            if len(removed) == 1:
                await ctx.remove(f"Removed {roles[0].mention} from {member.mention}")
            elif len(added) == 1:
                await ctx.add(f"Added {roles[0].mention} to {member.mention}")
            else:
                raise CommandError(
                    f"Could not find any roles to add to {member.mention}"
                )
        else:
            return await ctx.normal(f"Changed roles for {member.mention}: {text}")

    @role.command(
        name="mentionable",
        description="Toggle mentioning a role",
        example=",role mentionable members",
    )
    @has_permissions(manage_roles=True)
    async def role_mentionable(self, ctx: Context, *, role: Role):
        if not ctx.author.id == ctx.guild.owner_id:
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        mentionable = False if role.mentionable else True
        await role.edit(mentionable=mentionable)
        await ctx.message.add_reaction(":white_check_mark:")

    @role.command(
        name="edit", description="Change a role name", example=",role edit members sup"
    )
    @has_permissions(manage_roles=True)
    async def role_edit(self, ctx: Context, role: Role, *, name: str):
        if not ctx.author.id == ctx.guild.owner_id:
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        try:
            await role.edit(name=name, reason=f"Updated by {str(ctx.author)}")
        except HTTPException:
            return await ctx.fail(
                "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.",
            )
        return await ctx.success(f"renamed {role.mention} to `{name}`")

    @role.command(
        name="remove",
        description="Removes role from a member",
        example=",role remove jonathan members",
    )
    @has_permissions(manage_roles=True)
    async def role_remove(self, ctx: Context, member: Member, role: Role):
        if role not in member.roles:
            raise CommandError(f"{member.mention} doesn't have {role.mention}")
        if not ctx.author.id == ctx.guild.owner_id:
            if member.top_role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the roles of {member.mention} as their top role is {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        await member.remove_roles(role, reason=f"Removed by {str(ctx.author)}")
        return await ctx.remove(f"Removed {role.mention} from {member.mention}")

    @role.command(
        name="create",
        aliases=["cr"],
        description="Creates a role with optional color",
        example=",role create members purple",
    )
    @has_permissions(manage_roles=True)
    async def role_create(
        self, ctx: Context, name: str, *, color: Optional[Color] = None
    ):
        if len(ctx.guild.roles) >= 250:
            raise CommandError("The server has reached its limit of **250** for roles")
        kwargs = {"color": color} if color else {}
        kwargs["reason"] = f"Created by {str(ctx.author)}"
        role = await ctx.guild.create_role(name=name, **kwargs)
        return await ctx.success(f"created {role.mention}")

    @role.group(name="all", invoke_without_command=True)
    async def role_all(self, ctx: Context):
        return await ctx.send_help()

    @role_all.group(
        name="humans",
        aliases=["users"],
        description="gives a role to all non bots",
        example=",role all humans members",
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def role_all_humans(self, ctx: Context, *, role: AssignedRole):
        """
        Add a role to all members
        """
        lock = self.locks[f"role_all:{ctx.guild.id}"]
        cancelled = False
        if not (event := self.events.get(str(ctx.guild.id))):
            self.events[str(ctx.guild.id)] = Event()
        event = self.events[str(ctx.guild.id)]
        if lock.locked():
            raise MaxConcurrencyReached(1, BucketType.guild)
        async with lock:
            users = [
                m
                for m in ctx.guild.members
                if m.is_bannable and not m.bot and role not in m.roles
            ]

            if not users:
                raise CommandError("All members have this role")

            message = await ctx.normal(f"Giving {role.mention} to `{len(users)}` users")
            # Define a batch size and delay
            batch_size = 3
            delay = 1  # seconds
            total = len(users)
            # Process users in batches
            for i in range(0, len(users), batch_size):
                batch = users[i : i + batch_size]
                tasks = []
                if event.is_set():
                    cancelled = True
                    break
                for m in batch:
                    tasks.append(m.add_roles(role))

                # Wait for all tasks in the current batch to complete
                await asyncio.gather(*tasks)
                total -= len(batch)
                embed = message.embeds[0]
                embed.description = f"Giving {role.mention} to `{min(i + batch_size, len(users))}/{total + min(i + batch_size, len(users))}` users..."
                # Optionally update the message with progress
                await message.edit(embed=embed)
                # Wait before processing the next batch
                await asyncio.sleep(delay)
        if cancelled:
            self.events.pop(str(ctx.guild.id), None)
            return
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @role_all_humans.command(name="remove")
    async def role_all_humans_remove(self, ctx: Context, *, role: AssignedRole):
        """
        Remove a role from all humans
        """
        lock = self.locks[f"role_all:{ctx.guild.id}"]
        if not (event := self.events.get(str(ctx.guild.id))):
            self.events[str(ctx.guild.id)] = Event()
        event = self.events[str(ctx.guild.id)]
        cancelled = False
        if lock.locked():
            raise MaxConcurrencyReached(1, BucketType.guild)
        async with lock:
            users = [
                m
                for m in ctx.guild.members
                if m.is_bannable and not m.bot and role in m.roles
            ]

            if not users:
                raise CommandError("No humans have this role")

            message = await ctx.normal(
                f"Removing {role.mention} from `{len(users)}` humans"
            )
            # Define a batch size and delay
            batch_size = 3
            delay = 1  # seconds
            total = len(users)
            # Process users in batches
            for i in range(0, len(users), batch_size):
                batch = users[i : i + batch_size]
                tasks = []
                if event.is_set():
                    cancelled = True
                    break
                for m in batch:
                    tasks.append(m.remove_roles(role))

                # Wait for all tasks in the current batch to complete
                await asyncio.gather(*tasks)
                total -= len(batch)
                embed = message.embeds[0]
                embed.description = f"Removing {role.mention} from `{min(i + batch_size, len(users))}/{total + min(i + batch_size, len(users))}` humans..."
                # Optionally update the message with progress
                await message.edit(embed=embed)

                # Wait before processing the next batch
                await asyncio.sleep(delay)

        if cancelled:
            self.event.pop(str(ctx.guild.id), None)
            return
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @role_all.group(
        name="bots",
        aliases=["bot", "robot", "robots"],
        description="gives a role to all bots",
        example=",role all bots members",
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def role_all_bots(self, ctx: Context, *, role: AssignedRole):
        """
        Add a role to all members
        """
        lock = self.locks[f"role_all:{ctx.guild.id}"]
        if not (event := self.events.get(str(ctx.guild.id))):
            self.events[str(ctx.guild.id)] = Event()
        event = self.events[str(ctx.guild.id)]
        cancelled = False
        if lock.locked():
            raise MaxConcurrencyReached(1, BucketType.guild)
        async with lock:
            users = [
                m
                for m in ctx.guild.members
                if m.is_bannable and m.bot and role not in m.roles
            ]

            if not users:
                raise CommandError("All bots have this role")

            message = await ctx.normal(f"Giving {role.mention} to `{len(users)}` bots")
            # Define a batch size and delay
            batch_size = 3
            delay = 1  # seconds
            total = len(users)
            # Process users in batches
            for i in range(0, len(users), batch_size):
                batch = users[i : i + batch_size]
                tasks = []
                if event.is_set():
                    cancelled = True
                    break
                for m in batch:
                    tasks.append(m.add_roles(role))

                # Wait for all tasks in the current batch to complete
                await asyncio.gather(*tasks)
                total -= len(batch)
                embed = message.embeds[0]
                embed.description = f"Giving {role.mention} to `{min(i + batch_size, len(users))}/{total + min(i + batch_size, len(users))}` bots..."
                # Optionally update the message with progress
                await message.edit(embed=embed)

                # Wait before processing the next batch
                await asyncio.sleep(delay)

        if cancelled:
            self.event.pop(str(ctx.guild.id), None)
            return
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @role_all_bots.command(name="remove")
    @has_permissions(manage_roles=True)
    async def role_all_bots_remove(self, ctx: Context, *, role: AssignedRole):
        """
        Remove a role from all bots
        """
        lock = self.locks[f"role_all:{ctx.guild.id}"]
        if not (event := self.events.get(str(ctx.guild.id))):
            self.events[str(ctx.guild.id)] = Event()
        event = self.events[str(ctx.guild.id)]
        cancelled = False
        if lock.locked():
            raise MaxConcurrencyReached(1, BucketType.guild)
        async with lock:
            users = [
                m
                for m in ctx.guild.members
                if m.is_bannable and m.bot and role in m.roles
            ]

            if not users:
                raise CommandError("No bots have this role")

            message = await ctx.normal(
                f"Removing {role.mention} from `{len(users)}` bots"
            )
            # Define a batch size and delay
            batch_size = 3
            delay = 1  # seconds
            total = len(users)
            # Process users in batches
            for i in range(0, len(users), batch_size):
                batch = users[i : i + batch_size]
                tasks = []
                if event.is_set():
                    cancelled = True
                    break
                for m in batch:
                    tasks.append(m.remove_roles(role))

                # Wait for all tasks in the current batch to complete
                await asyncio.gather(*tasks)
                total -= len(batch)
                embed = message.embeds[0]
                embed.description = f"Removing {role.mention} from `{min(i + batch_size, len(users))}/{total + min(i + batch_size, len(users))}` bots..."
                # Optionally update the message with progress
                await message.edit(embed=embed)

                # Wait before processing the next batch
                await asyncio.sleep(delay)

        if cancelled:
            self.event.pop(str(ctx.guild.id), None)
            return
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @role_all.command(name="cancel", description="cancel a role all task")
    @has_permissions(manage_roles=True)
    async def role_all_cancel(self, ctx: Context):
        if not (event := self.events.get(str(ctx.guild.id))):
            raise CommandError("there is no current `role all` task running")
        event.set()
        return await ctx.normal("cancelled the `role all` task")

    @role.command(
        name="color",
        description="Changes a roles color to a specified color",
        example=",role color members purple",
    )
    @has_permissions(manage_roles=True)
    async def role_color(self, ctx: Context, role: Role, color: Color):
        if not ctx.author.id == ctx.guild.owner_id:
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        await role.edit(color=color, reason=f"Updated by {str(ctx.author)}")
        return await ctx.success(f"Set {role.mention}'s color to `#{str(color)}`")

    @role.command(
        name="restore",
        description="Restore roles to a member",
        example=",role restore jonathan",
    )
    @has_permissions(manage_roles=True)
    async def role_restore(self, ctx: Context, *, member: Member):
        if not (
            roles := await self.bot.db.fetchval(
                """SELECT roles FROM roles.restore WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
        ):
            raise CommandError(f"No roles found to restore for {member.mention}")
        roles = [rr for r in roles if (rr := ctx.guild.get_role(r))]
        r = member.roles
        r.extend(roles)
        await member.edit(roles=r, reason=f"Restored by {str(ctx.author)}")
        _ = await ctx.success(f"Restored {member.mention}'s roles")
        asyncio.ensure_future(
            self.bot.db.execute(
                """DELETE FROM roles.restore WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
        )
        return _

    @role.command(
        name="add",
        description="Adds role to a member",
        example=",role add jonathan active",
    )
    @has_permissions(manage_roles=True)
    async def role_add(self, ctx: Context, member: Member, role: Role):
        if role in member.roles:
            raise CommandError(f"{member.mention} already has {role.mention}")
        if not ctx.author.id == ctx.guild.owner_id:
            if member.top_role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the roles of {member.mention} as their top role is {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        await member.add_roles(role, reason=f"Added by {str(ctx.author)}")
        return await ctx.success(f"Added {role.mention} to {member.mention}")

    @role.command(
        name="hoist",
        description="Toggle hoisting a role",
        example=",role hoist members",
    )
    @has_permissions(manage_roles=True)
    async def role_hoist(self, ctx: Context, role: Role):
        if not ctx.author.id == ctx.guild.owner_id:
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        await role.edit(hoist=not role.hoist, reason=f"Updated by {str(ctx.author)}")
        return await ctx.message.add_reaction(":white_check_mark:")

    @role.group(
        name="has",
        description="Add a role to members with a specific role",
        example=",role has members pic",
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def role_has(self, ctx: Context, role: Role, assigned: AssignedRole):
        lock = self.locks[f"role_all:{ctx.guild.id}"]
        if not (event := self.events.get(str(ctx.guild.id))):
            self.events[str(ctx.guild.id)] = Event()
        event = self.events[str(ctx.guild.id)]
        cancelled = False
        if lock.locked():
            raise MaxConcurrencyReached(1, BucketType.guild)
        async with lock:
            users = [
                m
                for m in ctx.guild.members
                if m.is_bannable and role in m.roles and assigned not in m.roles
            ]

            if not users:
                raise CommandError("All users have this role")

            message = await ctx.normal(f"Giving {role.mention} to `{len(users)}` users")
            # Define a batch size and delay
            batch_size = 3
            delay = 1  # seconds
            total = len(users)
            # Process users in batches
            for i in range(0, len(users), batch_size):
                batch = users[i : i + batch_size]
                tasks = []
                if event.is_set():
                    cancelled = True
                    break
                for m in batch:
                    tasks.append(m.add_roles(role))

                # Wait for all tasks in the current batch to complete
                await asyncio.gather(*tasks)
                total -= len(batch)
                embed = message.embeds[0]
                embed.description = f"Giving {role.mention} to `{min(i + batch_size, len(users))}/{total + min(i + batch_size, len(users))}` users..."
                # Optionally update the message with progress
                await message.edit(embed=embed)

                # Wait before processing the next batch
                await asyncio.sleep(delay)

        if cancelled:
            self.event.pop(str(ctx.guild.id), None)
            return
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @role_has.command(name="remove")
    @has_permissions(manage_roles=True)
    async def role_has_remove(self, ctx: Context, *, role: AssignedRole):
        """
        Remove a role from all bots
        """
        lock = self.locks[f"role_all:{ctx.guild.id}"]
        if not (event := self.events.get(str(ctx.guild.id))):
            self.events[str(ctx.guild.id)] = Event()
        event = self.events[str(ctx.guild.id)]
        cancelled = False
        if lock.locked():
            raise MaxConcurrencyReached(1, BucketType.guild)
        async with lock:
            users = [
                m
                for m in ctx.guild.members
                if m.is_bannable and m.bot and role in m.roles
            ]

            if not users:
                raise CommandError("No bots have this role")

            message = await ctx.normal(
                f"Removing {role.mention} from `{len(users)}` bots"
            )
            # Define a batch size and delay
            batch_size = 3
            delay = 1  # seconds
            total = len(users)
            # Process users in batches
            for i in range(0, len(users), batch_size):
                batch = users[i : i + batch_size]
                tasks = []
                if event.is_set():
                    cancelled = True
                    break
                for m in batch:
                    tasks.append(m.remove_roles(role))

                # Wait for all tasks in the current batch to complete
                await asyncio.gather(*tasks)
                total -= len(batch)
                embed = message.embeds[0]
                embed.description = f"Removing {role.mention} from `{min(i + batch_size, len(users))}/{total + min(i + batch_size, len(users))}` bots..."
                # Optionally update the message with progress
                await message.edit(embed=embed)

                # Wait before processing the next batch
                await asyncio.sleep(delay)

        if cancelled:
            self.event.pop(str(ctx.guild.id), None)
            return
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @role_has.command(name="cancel", description="cancel a role all task")
    @has_permissions(manage_roles=True)
    async def role_has_cancel(self, ctx: Context):
        if not (event := self.events.get(str(ctx.guild.id))):
            raise CommandError("there is no current `role all` task running")
        event.set()
        return await ctx.normal("cancelled the `role all` task")

    @role.command(
        name="delete",
        aliases=["del"],
        description="Deletes a role",
        example=",role delete active",
    )
    @has_permissions(manage_roles=True)
    async def role_delete(self, ctx: Context, *, role: Role):
        if not ctx.author.id == ctx.guild.owner_id:
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        if not role.is_assignable():
            raise CommandError(f"I cannot delete {role.mention}")
        await role.delete(reason=f"Deleted by {str(ctx.author)}")
        return await ctx.message.add_reaction(":white_check_mark:")

    @role.command(
        name="icon",
        description="Set an icon for a role",
        example=",role icon https://... members",
    )
    @has_permissions(manage_roles=True)
    async def role_icon(self, ctx: Context, icon: str, *, role: Role):
        if not ctx.guild.premium_tier >= 2:
            raise CommandError("Server boost level 2 is required for role icons")
        if not ctx.author.id == ctx.guild.owner_id:
            if role >= ctx.author.top_role:
                raise CommandError(
                    f"You cannot alter the role {role.mention} as its {'equal to' if role == ctx.author.top_role else 'higher than'} your **top role**"
                )
        if role >= ctx.guild.me.top_role:
            raise CommandError(
                f"I cannot alter {role.mention} as its {'equal to' if role == ctx.guild.me.top_role else 'higher than'} my **top role**"
            )
        async with ClientSession() as session:
            async with session.request("HEAD", icon) as check:
                if check.content_type not in ["image/png", "image/jpeg", "image/jpg"]:
                    raise CommandError("Discord only accepts a JPG or PNG")
                if int(check.headers.get("Content-Length", 50000)) > 10485760:
                    raise CommandError("The image is too large, find one below 10MB")
            async with session.get(icon) as response:
                data = await response.read()
        image = await prepare_icon(data)
        await role.edit(display_icon=image, reason=f"Updated by {str(ctx.author)}")
        return await ctx.message.add_reaction(":white_check_mark:")

    async def update_channels(self, old: TextChannel, new: TextChannel) -> None:
        old_channel_id = old.id
        new_channel_id = new.id
        guild_id = old.guild.id
        exists = await self.bot.db.fetchval(
            """
            SELECT guild_id
            FROM config
            WHERE jail_channel = $1 OR
                join_logs = $1 OR
                mod_logs = $1 OR
                dj_role = $1 OR
                premium_role = $1 OR
                $1 = ANY(staff_roles) OR
                $1 = ANY(prefixes);
        """,
            old_channel_id,
        )

        if exists:
            await self.bot.db.execute(
                """
                UPDATE config
                SET jail_channel = CASE WHEN jail_channel = $1 THEN $2 ELSE jail_channel END,
                    join_logs = CASE WHEN join_logs = $1 THEN $2 ELSE join_logs END,
                    mod_logs = CASE WHEN mod_logs = $1 THEN $2 ELSE mod_logs END,
                    dj_role = CASE WHEN dj_role = $1 THEN $2 ELSE dj_role END,
                    premium_role = CASE WHEN premium_role = $1 THEN $2 ELSE premium_role END,
                    staff_roles = ARRAY(SELECT CASE WHEN role = $1 THEN $2 ELSE role END FROM unnest(staff_roles) AS role),
                    prefixes = ARRAY(SELECT CASE WHEN prefix = $1 THEN $2 ELSE prefix END FROM unnest(prefixes) AS prefix)
                WHERE guild_id = $3;
            """,
                old_channel_id,
                new_channel_id,
                guild_id,
            )

        async def update_table(query: str, *args):
            try:
                await self.bot.db.execute(query, *args)
            except Exception:
                pass

        queries = [
            (
                """UPDATE clownboard SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE starboard SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE ignored SET object_id = $1 WHERE object_id = $2 AND guild_id = $3 AND object_type = $4""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
                "channel",
            ),
            (
                """UPDATE pagination SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE sticky_message SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE image_only SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE feeds.kick SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE feeds.twitch SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE feeds.instagram SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE feeds.tiktok SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE feeds.youtube SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE feeds.twutter SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE boost_messages SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE leave_messages SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE welcome_messages SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE text_level_settings SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE counters SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
            (
                """UPDATE timer SET channel_id = $1 WHERE channel_id = $2 AND guild_id = $3""",
                new_channel_id,
                old_channel_id,
                new.guild.id,
            ),
        ]
        tasks = [update_table(*a) for a in queries]
        await asyncio.gather(*tasks)

        return True

    @group(name="nuke", description="Clone the current channel")
    @has_permissions(administrator=True, antinuke_admin=True)
    async def nuke(self, ctx: Context):
        channel_info = [ctx.channel.category, ctx.channel.position]
        channel_id = ctx.channel.id
        await ctx.channel.clone(reason=f"Nuked by {str(ctx.author)}")
        await ctx.channel.delete(reason=f"Nuked by {str(ctx.author)}")
        new_channel = channel_info[0].text_channels[-1]
        await new_channel.edit(position=channel_info[1])
        asyncio.ensure_future(self.update_channels(ctx.channel, new_channel))
        await new_channel.send(content="first")

    @nuke.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View all scheduled nukes",
    )
    @has_permissions(administrator=True, antinuke_admin=True)
    async def nuke_list(self, ctx: Context):
        if not (
            rows := await self.bot.db.fetch(
                """SELECT channel_id, nuke_threshold FROM nuke WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No scheduled nuking channels found")

        embed = Embed(title="Scheduled Nukes", color=self.bot.color)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        values = []
        i = 0
        for row in rows:
            if channel := ctx.guild.get_channel(row.channel_id):
                i += 1
                values.append(
                    f"`{i}` {channel.mention} - {naturaldelta(row.nuke_threshold)}"
                )
        return await ctx.paginate(embed, values)

    @nuke.command(
        name="remove",
        aliases=["delete", "del", "rem", "r", "d"],
        description="Remove scheduled nuke for a channel",
        example=",nuke remove #text",
    )
    @has_permissions(administrator=True, antinuke_admin=True)
    async def nuke_remove(self, ctx: Context, *, channel: TextChannel):
        if not (
            data := await self.bot.db.fetchrow(
                """DELETE FROM nuke WHERE guild_id = $1 AND channel_id = $2 RETURNING *""",
                ctx.guild.id,
                channel.id,
            )
        ):
            raise CommandError("No scheduled nuke found for this channel")
        return await ctx.success(
            f"Removed {channel.mention} from the **scheduled nukes**"
        )

    @nuke.command(
        name="add",
        aliases=["create", "cr", "c", "a"],
        description="Schedule nuke for a channel (yes. this will reclone the channel)",
        example=",nuke add #general 2h hey sexy ass people",
    )
    @has_permissions(administrator=True, antinuke_admin=True)
    async def nuke_add(
        self,
        ctx: Context,
        channel: TextChannel,
        interval: Expiration,
        *,
        message: Optional[EmbedConverter] = "first",
    ):
        await self.bot.db.execute(
            """INSERT INTO nuke (guild_id, channel_id, last_nuke, nuke_threshold, message) VALUES($1, $2, $3, $4, $5) ON CONFLICT(guild_id, channel_id) DO UPDATE SET last_nuke = excluded.last_nuke, nuke_threshold = excluded.nuke_threshold, message = excluded.message""",
            ctx.guild.id,
            channel.id,
            datetime.now(),
            int(interval),
            message,
        )
        return await ctx.success(
            f"Added {channel.mention} as a **scheduled nuke** to be nuked every **{naturaldelta(interval)}**\nwith message: `{message}`"
        )

    @group(
        name="timeout",
        aliases=["mute", "to"],
        description="Mutes the provided member using Discords timeout feature",
        example=",timeout jonathan 1d",
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: Context,
        member: SafeSnowflake,
        interval: Expiration,
        *,
        reason: Optional[str] = "No reason provided",
    ):
        time = timedelta(seconds=interval)
        await member.timeout(time, reason=f"{reason} by {str(ctx.author)}")
        await self.moderation_entry(ctx, member, "muted")
        return await ctx.success(f"Muted {member.mention} for **{naturaldelta(time)}**")

    @timeout.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of timed out members",
    )
    @has_permissions(moderate_members=True)
    async def timeout_list(self, ctx: Context):
        members = [member for member in ctx.guild.members if member.is_timed_out()]
        if not members:
            raise CommandError("No members are **timed out**")
        rows = [
            f"`{i}` {member.mention} - {utils.format_dt(member.timed_out_until)}"
            for i, member in enumerate(members, start=1)
        ]
        embed = Embed(title="Timed Out Members").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(embed, rows)

    @group(
        name="untimeout",
        description="Removes a timeout for a member",
        example=",untimeout jonathan",
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def untimeout(self, ctx: Context, *, member: SafeSnowflake):
        if not member.is_timed_out():
            raise CommandError(f"{member.mention} isn't **timed out**")

        await member.timeout(reason=f"Untimed out by {str(ctx.author)}")
        return await ctx.send("👍")

    @untimeout.command(name="all", description="untimeout all timed out members")
    @has_permissions(moderate_members=True)
    async def untimeout_all(self, ctx: Context):
        members = [
            member
            for member in ctx.guild.members
            if member.is_timed_out() and member.is_bannable
        ]
        if not members:
            raise CommandError("No members are **timed out**")
        for member in members:
            await member.timeout(reason=f"Untimed out by {str(ctx.author)}")
        return await ctx.success(
            f"Removed timeouts for **{len(members)}** {'member' if len(members) == 1 else 'members'}"
        )

    @command(
        name="imute",
        aliases=["imagemute"],
        description="Remove a member's attach files & embed links permission",
        example=",imagemute jonathan",
    )
    @has_permissions(moderate_members=True)
    async def imute(
        self,
        ctx: Context,
        member: SafeSnowflake,
        reason: Optional[str] = "No Reason Provided",
    ):
        if not (imute_role := utils.get(ctx.guild.roles, name="imute")):
            raise CommandError(
                f"No **image mute** role found, please run `{ctx.prefix}setup`"
            )
        await member.add_roles(imute_role, reason=f"Image Muted by {str(ctx.author)}")
        return await ctx.send("👍")

    @command(
        name="iunmute",
        aliases=["unimagemute", "imageunmute"],
        description="Restores a member's attach files & embed links permission",
        example=",iunmute jonathan",
    )
    @has_permissions(moderate_members=True)
    async def iunmute(
        self,
        ctx: Context,
        member: SafeSnowflake,
        reason: Optional[str] = "No Reason Provided",
    ):
        if not (imute_role := utils.get(ctx.guild.roles, name="imute")):
            raise CommandError(
                f"No **image mute** role found, please run `{ctx.prefix}setup`"
            )
        await member.remove_roles(
            imute_role, reason=f"Image Unmuted by {str(ctx.author)}"
        )
        return await ctx.send("👍")

    @command(
        name="rmute",
        description="Remove a member's add reactions & use external emotes permission",
        aliases=["reactionmute", "reactmute"],
        example=",rmute jonathan",
    )
    @has_permissions(moderate_members=True)
    async def rmute(
        self,
        ctx: Context,
        member: SafeSnowflake,
        reason: Optional[str] = "No Reason Provided",
    ):
        if not (mute_role := utils.get(ctx.guild.roles, name="rmute")):
            raise CommandError(
                f"No **reaction mute** role found, please run `{ctx.prefix}setup`"
            )
        await member.add_roles(mute_role, reason=f"Reaction Muted by {str(ctx.author)}")
        return await ctx.send("👍")

    @command(
        name="runmute",
        aliases=["unreactionmute", "unreactmute", "reactunmute", "reactionunmute"],
        description="Restores a member's add reactions & use external emotes permission",
        example=",runmute jonathan",
    )
    @has_permissions(moderate_members=True)
    async def runmute(
        self,
        ctx: Context,
        member: SafeSnowflake,
        reason: Optional[str] = "No Reason Provided",
    ):
        if not (mute_role := utils.get(ctx.guild.roles, name="rmute")):
            raise CommandError(
                f"No **reaction mute** role found, please run `{ctx.prefix}setup`"
            )
        await member.remove_roles(
            mute_role, reason=f"Reaction UnMuted by {str(ctx.author)}"
        )
        return await ctx.send("👍")

    @group(
        name="notes",
        description="View notes on a member",
        example=",notes jonathan",
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def notes(self, ctx: Context, *, member: Member):
        if not (
            notes := await self.bot.db.fetch(
                """SELECT note_id, moderator_id, timestamp, note FROM notes WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
        ):
            raise CommandError(f"No **notes** found for {member.mention}")
        embeds = []

        def get_moderator(user_id: int):
            if moderator := ctx.guild.get_member(user_id):
                return f"{str(moderator)} (`{user_id}`)"
            else:
                return f"Unknown (`{user_id}`)"

        default_embed = Embed(title=f"Notes for {str(member)}")
        default_embed.set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        chunks = utils.chunk_list(notes, 3)
        for i, chunk in enumerate(chunks, start=1):
            embed = default_embed.copy()
            for row in chunk:
                embed.add_field(
                    name=f"**Note ID #{row.note_id}**",
                    value=f"**Date:** {utils.format_dt(chunk[0].timestamp, style='F')}\n**Moderator:** {get_moderator(chunk[0].moderator_id)}\n**Note:** {chunk[0].note}",
                    inline=False,
                )
            embed.set_footer(
                f"Page {i}/{len(chunks)} ({len(notes)} {'entries' if len(notes) > 1 else 'entry'})"
            )
            embeds.append(embed)
        return await ctx.paginate(embeds)

    @notes.command(
        name="add",
        aliases=["create", "a", "c", "cr"],
        description="Add a note for a member",
        example=",notes add jonathan cunt",
    )
    @has_permissions(manage_messages=True)
    async def notes_add(self, ctx: Context, member: Member, *, note: str):
        note_id = (
            await self.bot.db.fetchval(
                """SELECT note_id FROM notes WHERE guild_id = $1 AND user_id = $2 ORDER BY timestamp DESC LIMIT 1""",
                ctx.guild.id,
                member.id,
            )
            or 0
        )
        note_id += 1
        await self.bot.db.execute(
            """INSERT INTO notes (guild_id, user_id, note_id, moderator_id, timestamp, note) VALUES($1, $2, $3, $4, $5, $6)""",
            ctx.guild.id,
            member.id,
            note_id,
            ctx.author.id,
            datetime.now(),
            note,
        )
        return await ctx.success(f"Added note for **{str(member)}**")

    @notes.command(
        name="clear",
        aliases=["cl"],
        description="Clears all notes for a member",
        example=",notes clear jonathan",
    )
    @has_permissions(manage_messages=True)
    async def notes_clear(self, ctx: Context, *, member: Member):
        deleted = len(
            await self.bot.db.execute(
                """DELETE FROM notes WHERE guild_id = $1 AND user_id = $2 RETURNING *""",
                ctx.guild.id,
                member.id,
            )
        )
        return await ctx.success(
            f"Cleared **{deleted}** {'note' if deleted == 1 else 'notes'} for **{str(member)}**"
        )

    @notes.command(
        name="remove",
        aliases=["delete", "del", "d", "r", "rem"],
        description="Removes a note for a member",
        example=",notes remove jonathan 1",
    )
    @has_permissions(manage_messages=True)
    async def notes_remove(self, ctx: Context, member: Member, id: int):
        found = len(
            await self.bot.db.execute(
                """DELETE FROM notes WHERE guild_id = $1 AND user_id = $2 AND note_id = $3 RETURNING *""",
                ctx.guild.id,
                member.id,
                id,
            )
        )
        if found == 0:
            raise CommandError(f"Note **#{id}** not found for {member.mention}")
        else:
            return await ctx.success(f"Removed note `#{id}` for **{str(member)}**")

    @group(
        name="hardban",
        description="Keep a member banned",
        example=",hardban jonathan",
        invoke_without_command=True,
    )
    @has_permissions(administrator=True, antinuke_admin=True)
    async def hardban(
        self,
        ctx: Context,
        member: SafeSnowflake,
        *,
        reason: Optional[str] = "No Reason Provided",
    ):
        if value := await self.bot.db.fetchrow(
            """SELECT * FROM hardban WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        ):
            await self.bot.db.execute(
                """DELETE FROM hardban WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
            try:
                await ctx.guild.unban(
                    Object(member.id), reason=f"Hard Ban Undone by {str(ctx.author)}"
                )
                self.bot.dispatch("hardban_delete", member, ctx.guild, ctx.author)
            except Exception:
                pass
            return await ctx.success(f"Removed **hard ban** for **{str(member)}**")
        else:
            await self.bot.db.execute(
                """INSERT INTO hardban (guild_id, user_id, timestamp, moderator_id, reason) VALUES($1, $2, $3, $4, $5) ON CONFLICT(guild_id, user_id) DO UPDATE SET timestamp = excluded.timestamp, moderator_id = excluded.moderator_id, reason = excluded.reason""",
                ctx.guild.id,
                member.id,
                datetime.now(),
                ctx.author.id,
                reason,
            )
            self.bot.dispatch("hardban_create", member, ctx.guild, ctx.author)
            await ctx.guild.ban(Object(member.id), reason=f"Hard Banned for {reason}")
            return await ctx.success(f"Added **hard ban** for **{str(member)}**")

    @hardban.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View list of hardbanned members",
    )
    @has_permissions(administrator=True, antinuke_admin=True)
    async def hardban_list(self, ctx: Context):
        if not (
            hardbans := await self.bot.db.fetch(
                "SELECT * FROM hardban WHERE guild_id = $1"
            )
        ):
            raise CommandError("No **hard bans** found")
        embed = Embed(title="Hard Bans").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = []

        def get_user(user_id):
            if user := self.bot.get_user(user_id):
                return f"{str(user)} (`{user_id}`)"
            return f"Unknown User (`{user_id}`)"

        for i, hardban in enumerate(hardbans, start=1):
            rows.append(f"`{i}` {get_user(hardban.user_id)}")

        return await ctx.paginate(embed, rows)

    @command(name="clearinvites", description="Remove all existing invites in guild")
    @has_permissions(manage_guild=True)
    async def clearinvites(self, ctx: Context):
        invites = await ctx.guild.invites()
        message = await ctx.normal(
            f"Deleting **{len(invites)}** invites, this may take a while.."
        )
        for invite in invites:
            await invite.delete(reason=f"Invited cleared by {str(ctx.author)}")
        return await message.edit(
            embed=await ctx.success(
                f"Cleared all **{len(invites)}** {'invite' if len(invite) == 1 else 'invites'}",
                return_embed=True,
            )
        )

    @command(
        name="drag",
        description="Drag member(s) to the specified Voice Channel",
        example=",drag jonathan aiohttp vc",
    )
    @has_permissions(moderate_members=True)
    async def drag(
        self, ctx: Context, members: Greedy[Member], *, channel: VoiceChannel
    ):
        good: List[Member] = []
        bad: List[Member] = []
        for member in members:
            if member.voice:
                if member.voice.channel.id != channel.id:
                    await member.move_to(
                        channel, reason=f"Dragged by {str(ctx.author)}"
                    )
                    good.append(member)
                else:
                    bad.append(member)
            else:
                bad.append(member)
        if len(good) > 0:
            if len(bad) > 0:
                m = f". Failed to drag {', '.join(m for m in bad)}"
            else:
                m = ""
            return await ctx.success(f"dragged {', '.join(m for m in good)}{m}")
        else:
            raise CommandError("None of those members are in a **voice channel**")

    @group(
        name="unbanall",
        description="Unbans every member in a guild",
        invoke_without_command=True,
    )
    @has_permissions(server_owner=True)
    async def unbanall(self, ctx: Context):
        lock = self.locks[f"unbanall:{ctx.guild.id}"]
        if task := self.tasks.get(str(ctx.guild.id)):
            raise MaxConcurrencyReached(1, BucketType.guild)
        if lock.locked():
            raise MaxConcurrencyReached(1, BucketType.guild)
        hard_bans = [
            row.user_id
            for row in await self.bot.db.fetch(
                """SELECT user_id FROM hardban WHERE guild_id = $1""", ctx.guild.id
            )
        ]
        bans = [
            ban
            async for ban in ctx.guild.bans(limit=None)
            if ban.user.id not in hard_bans
        ]
        message = await ctx.normal(
            f"Removing **{len(bans)}** {'ban' if len(bans) == 1 else 'bans'}.. this may take a while"
        )

        async def utask(message, guild, bans):
            # Define a batch size and delay
            batch_size = 3
            delay = 1  # seconds
            total = len(bans)
            # Process users in batches
            for i in range(0, len(bans), batch_size):
                batch = bans[i : i + batch_size]
                tasks = []
                for m in batch:
                    tasks.append(
                        guild.unban(
                            Object(m.user.id),
                            reason=f"Unban all ran by {str(ctx.author)}",
                        )
                    )

                # Wait for all tasks in the current batch to complete
                await asyncio.gather(*tasks)
                total -= len(batch)
                embed = message.embeds[0]
                embed.description = f"Removing `{min(i + batch_size, len(bans))}/{total + min(i + batch_size, len(bans))}` bans..."
                # Optionally update the message with progress
                await message.edit(embed=embed)
                # Wait before processing the next batch
                await asyncio.sleep(delay)

        unban_task = create_task(utask(message, ctx.guild, bans))
        self.tasks[str(ctx.guild.id)] = unban_task
        await self.tasks[str(ctx.guild.id)]
        self.tasks.pop(str(ctx.guild.id), None)
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished removing **{len(bans)}** bans in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @unbanall.command(
        name="cancel",
        aliases=["stop", "end", "c", "s", "e"],
        description="Cancels a unban all task running",
    )
    @has_permissions(server_owner=True)
    async def unbanall_cancel(self, ctx: Context):
        if not (task := self.tasks.get(str(ctx.guild.id))):
            raise CommandError("No **unban all** task is currently running..")
        try:
            await task.cancel()
        except Exception:
            pass
        try:
            self.tasks.pop(str(ctx.guild.id), None)
        except Exception:
            pass
        return await ctx.send("👍")

    @group(
        name="temprole",
        description="Temporarily give a role to a member",
        invoke_without_command=True,
        example=",temprole jonathan 30m Birthday",
    )
    @has_permissions(manage_roles=True)
    async def temprole(
        self,
        ctx: Context,
        member: SafeSnowflake,
        duration: Expiration,
        *,
        role: AssignedRole,
    ):
        expiration = datetime.now() + timedelta(seconds=duration)
        await self.bot.db.execute(
            """INSERT INTO temproles (guild_id, user_id, role_id, expiration) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id, user_id, role_id) DO UPDATE SET expiration = excluded.expiration""",
            ctx.guild.id,
            member.id,
            role.id,
            expiration,
        )
        return await ctx.success(
            f"Added {role.mention} to **{str(member)}** which will expire {utils.format_dt(expiration, style='R')}"
        )

    @temprole.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="List all active temporary roles",
    )
    @has_permissions(manage_roles=True)
    async def temprole_list(self, ctx: Context):
        if not (
            entries := await self.bot.db.fetch(
                "SELECT * FROM temproles WHERE guild_id = $1" "", ctx.guild.id
            )
        ):
            raise CommandError("No **temporary roles** have been assigned")
        embed = Embed(title="Temporary Roles").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = []
        i = 0

        for row in entries:
            if not (member := ctx.guild.get_member(row.user_id)):
                continue
            if not (role := ctx.guild.get_role(row.role_id)):
                continue
            i += 1
            rows.append(f"`{i}` **{str(member)}** - {role.mention}")

        if not rows:
            raise CommandError("No **temporary roles** have been assigned")
        return await ctx.paginate(embed, rows)

    async def delete_messages(self, messages: List[Message]):
        async def purge(messages: List[Message]) -> None:
            channel = messages[0].channel
            bulkable = [m for m in messages if m.is_deleteable]
            non_bulk = [m for m in messages if not m.is_deletable]
            amount = len(bulkable)

            async def bulk():
                if amount > 100:
                    for chunk in utils.chunk_list(bulkable, 100):
                        await channel.delete_messages(chunk)
                        await asyncio.sleep(1)
                else:
                    await channel.delete_messages(bulkable)

            async def nonbulk():
                for message in non_bulk:
                    await message.delete()

            await bulk()
            await nonbulk()

        if task := self.tasks.get(f"purge-{messages[0].guild.id}"):
            raise MaxConcurrencyReached(1, BucketType.guild)
        task = create_task(purge(messages))
        self.tasks[f"purge-{messages[0].guild.id}"] = task
        await task
        self.tasks.pop(f"purge-{messages[0].guild.id}", None)

    @group(
        name="purge",
        description="Deletes the specified amount of messages from the current channel",
        example=",purge jonathan 100",
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def purge(
        self, ctx: Context, member: Optional[Member] = None, search: Optional[int] = 100
    ):
        if member:
            messages = [
                m
                async for m in ctx.channel.history()
                if m.author.id == member.id and m != ctx.message
            ]
            if len(messages) == 0:
                raise CommandError("No purgable messages found")
        else:
            messages = [m async for m in ctx.channel.history() if m != ctx.message]
            if len(messages) == 0:
                raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(
        name="attachments",
        aliases=["files", "attachment", "file"],
        description="Purge files/attachments from chat",
    )
    @has_permissions(manage_messages=True)
    async def purge_attachments(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            for attachment in message.attachments:
                if attachment.content_type not in (
                    "image/jpg",
                    "image/png",
                    "image/jpeg",
                    "image/gif",
                ):
                    return True
            return False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(
        name="endswith",
        description="Purge messages that ends with a given substring",
        example=",purge endswith st",
    )
    @has_permissions(manage_messages=True)
    async def purge_endswith(self, ctx: Context, *, substring: str):
        def check(message: Message) -> bool:
            return message.content.endswith(substring)

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @purge.command(
        name="mentions",
        description="Purge mentions for a member from chat",
        example=",purge mentions jonathan 100",
    )
    @has_permissions(manage_messages=True)
    async def purge_mentions(
        self, ctx: Context, member: Optional[Member] = None, search: Optional[int] = 100
    ):
        if member is None:

            def check(message: Message) -> bool:
                return True if message.mentions else False

        else:

            def check(message: Message) -> bool:
                return message.mentions and member in message.mentions

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(name="emoji", description="Purge emojis from chat")
    @has_permissions(manage_messages=True)
    async def purge_emoji(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            return True if message.emojis else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(
        name="before", description="Purge messages before a given message ID"
    )
    @has_permissions(manage_messages=True)
    async def purge_before(self, ctx: Context, message: Message):
        def check(message: Message, m: Message) -> bool:
            if message.created_at <= m.created_at:
                return True
            else:
                return False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @purge.command(name="stickers", description="Purge stickers from chat")
    @has_permissions(manage_messages=True)
    async def purge_stickers(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            return True if message.stickers else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(
        name="contains", description="Purges messages containing given substring"
    )
    @has_permissions(manage_messages=True)
    async def purge_contains(self, ctx: Context, *, substring: str):
        def check(message: Message) -> bool:
            if substring.endswith("*"):
                return True if substring in str(message.content) else False
            else:
                return True if substring in str(message.content).split(" ") else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @purge.command(name="between", description="Purge between two messages")
    @has_permissions(manage_messages=True)
    async def purge_between(self, ctx: Context, start_id: Message, finish_id: Message):
        def check(message: Message) -> bool:
            return (
                True
                if start_id.created_at <= message.created_at <= finish_id.created_at
                else False
            )

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @purge.command(name="webhooks", description="Purge messages from webhooks in chat")
    @has_permissions(manage_messages=True)
    async def purge_webhooks(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            return True if message.author.webhook_id else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(name="bots", description="Purge messages from bots in chat")
    @has_permissions(manage_messages=True)
    async def purge_bots(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            return True if message.author.bot else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(
        name="reactions", description="Purge reactions from messages in chat"
    )
    @has_permissions(manage_messages=True)
    async def purge_reactions(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            return True if message.reactions else False

        async def remove_reactions(messages: List[Message]) -> None:
            for message in messages:
                await message.clear_reactions()

        if task := self.tasks.get(f"purge-{ctx.guild.id}"):
            raise MaxConcurrencyReached(1, BucketType.guild)
        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        task = create_task(remove_reactions(messages))
        self.tasks[f"purge-{ctx.guild.id}"] = task
        await task
        self.tasks.pop(f"purge-{ctx.guild.id}", None)
        return await ctx.send("👍")

    @purge.command(
        name="images", description="Purge images (including links) from chat"
    )
    @has_permissions(manage_messages=True)
    async def purge_images(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            if URL.findall(message.content):
                return True
            return True if message.attachments else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(name="after", description="Purge messages after a given message ID")
    @has_permissions(manage_messages=True)
    async def purge_after(self, ctx: Context, message: Message):
        def check(m: Message) -> bool:
            return True if m.created_at > message.created_at else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @purge.command(name="links", description="Purge messages containing links")
    @has_permissions(manage_messages=True)
    async def purge_links(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            if URL.findall(message.content):
                return True
            return False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @purge.command(name="embeds", description="Purge embeds from chat")
    @has_permissions(manage_messages=True)
    async def purge_embeds(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            return True if message.embeds else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(
        name="startswith",
        description="Purge messages that start with a given substring",
    )
    @has_permissions(manage_messages=True)
    async def purge_startswith(self, ctx: Context, *, substring: str):
        def check(message: Message) -> bool:
            return True if message.content.startswith(substring) else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @purge.command(name="humans", description="Purge messages from humans in chat")
    @has_permissions(manage_messages=True)
    async def purge_humans(self, ctx: Context, search: Optional[int] = 100):
        def check(message: Message) -> bool:
            return True if not message.author.bot else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages[:search])
        return await ctx.send("👍")

    @purge.command(name="upto", description="Purge messages up to a message link")
    @has_permissions(manage_messages=True)
    async def purge_upto(self, ctx: Context, message: Message):
        def check(m: Message) -> bool:
            return True if m.created_at > message.created_at else False

        messages = [
            m async for m in ctx.channel.history() if m != ctx.message and check(m)
        ]
        if not messages:
            raise CommandError("No purgable messages found")
        await self.delete_messages(messages)
        return await ctx.send("👍")

    @command(name="newusers", description="View list of recently joined members")
    async def newusers(self, ctx: Context, count: int = 100):
        def check(member: Member):
            return (
                True
                if member.joined_at > ctx.message.created_at - timedelta(days=1)
                else False
            )

        members = sorted(
            [m for m in ctx.guild.members if check(m)],
            key=lambda x: x.joined_at,
            reverse=True,
        )
        if not members:
            raise CommandError("No **members** joined recently")
        rows = [
            f"`{i}` **{str(member)}** joined {utils.format_dt(member.joined_at, style='R')}"
            for i, member in enumerate(members, start=1)
        ]
        embed = Embed(title="New users today").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        return await ctx.paginate(embed, rows)

    @group(
        name="recentban",
        description="Chunk ban recently joined members",
        aliases=["rb"],
        invoke_without_command=True,
    )
    @has_permissions(ban_members=True)
    async def recentban(
        self, ctx: Context, count: int, *, reason: Optional[str] = "No reason provided"
    ):
        if task := self.tasks.get(f"chunkban:{ctx.guild.id}"):
            raise MaxConcurrencyReached(1, BucketType.guild)

        def check(member: Member):
            if not member.is_bannable:
                return False
            return (
                True
                if member.joined_at > ctx.message.created_at - timedelta(days=1)
                else False
            )

        members = sorted(
            [m for m in ctx.guild.members if check(m)],
            key=lambda x: x.joined_at,
            reverse=True,
        )
        if not members:
            raise CommandError("No **members** joined recently")

        async def ban_members(members: List[Member]) -> None:
            for member in members[:count]:
                if member.is_bannable:
                    try:
                        await member.ban(reason=reason)
                    except Exception:
                        pass

        message = await ctx.normal(
            f"chunk banning **{len(members)}** recently joined members, this may take a while..."
        )
        task = create_task(ban_members(members))
        self.tasks[f"chunkban:{ctx.guild.id}"] = task
        await task
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @recentban.command(
        name="cancel",
        aliases=["stop", "s", "c", "end", "e"],
        description="stop a chunk banning task",
    )
    @has_permissions(ban_members=True)
    async def recentban_cancel(self, ctx: Context):
        if task := self.tasks.get(f"chunkban:{ctx.guild.id}"):
            task.cancel()
            self.tasks.pop(f"chunkban:{ctx.guild.id}", None)
            return await ctx.success("Ended chunk banning task")
        raise CommandError("No **chunkban task** has been started...")

    @command(name="talk", description="Toggle a channel to text for a role")
    @has_permissions(manage_channels=True)
    async def talk(self, ctx: Context, channel: TextChannel, *, role: Role):
        permissions = channel.overwrites_for(role)
        permissions.send_messages = True
        await channel.set_permissions(
            role, overwrite=permissions, reason=f"Updated by {str(ctx.author)}"
        )
        return await ctx.send("👍")

    @command(name="unhide", description="Unhide a channel from a role or member")
    @has_permissions(manage_channels=True)
    async def unhide(
        self,
        ctx: Context,
        channel: Union[TextChannel, VoiceChannel],
        *,
        role_or_member: Union[Member, Role],
    ):
        permissions = channel.overwrites_for(role_or_member)
        permissions.view_channel = True
        await channel.set_permissions(
            role_or_member,
            overwrite=permissions,
            reason=f"Updated by {str(ctx.author)}",
        )
        return await ctx.send("👍")

    @command(name="hide", description="Hide a channel from a role or member")
    @has_permissions(manage_channels=True)
    async def hide(
        self,
        ctx: Context,
        channel: Union[TextChannel, VoiceChannel],
        *,
        role_or_member: Union[Member, Role],
    ):
        permissions = channel.overwrites_for(role_or_member)
        permissions.view_channel = False
        await channel.set_permissions(
            role_or_member,
            overwrite=permissions,
            reason=f"Updated by {str(ctx.author)}",
        )
        return await ctx.send("👍")

    @group(
        name="slowmode",
        description="Restricts members to sending one message per interval",
        invoke_without_command=True,
    )
    async def slowmode(self, ctx: Context):
        return await ctx.send_help()

    @slowmode.command(
        name="on",
        aliases=["enable"],
        description="Enable slowmode in a channel",
        example=",slowmode on #text 5m",
    )
    @has_permissions(manage_channels=True)
    async def slowmode_on(
        self, ctx: Context, channel: TextChannel, delay_time: Expiration
    ):
        if delay_time > 21600:
            raise CommandError("Slowmode interval cannot be more than 6 hours")
        await ctx.channel.edit(
            slowmode_delay=delay_time, reason=f"Updated by {str(ctx.author)}"
        )
        return await ctx.send("👍")

    @slowmode.command(
        name="off",
        aliases=["disable"],
        description="Disables slowmode in a channel",
        example=",slowmode off #text",
    )
    @has_permissions(manage_channels=True)
    async def slowmode_off(self, ctx: Context, channel: TextChannel):
        await ctx.channel.edit(slowmode_delay=0, reason=f"Updated by {str(ctx.author)}")
        return await ctx.send("👍")

    @group(
        name="revokefiles",
        description="Removes/assigns the permission to attach files & embed links in the current channel",
        invoke_without_command=True,
    )
    async def revokefiles(self, ctx: Context):
        return await ctx.send_help()

    @revokefiles.command(
        name="off",
        aliases=["disable", "d"],
        description="Disables permissions to attach files & embed links in a channel",
        example=",revokefiles off #text",
    )
    @has_permissions(manage_channels=True)
    async def revokefiles_off(self, ctx: Context, *, channel: TextChannel):
        overwrites = {}
        for obj, overwrite in channel.overwrites:
            overwrite.attach_files = False
            overwrite.embed_links = False
            overwrites[obj] = overwrite
        if ctx.guild.default_role not in overwrites:
            overwrites[ctx.guild.default_role] = PermissionOverwrite(
                attach_files=False, embed_links=False
            )
        await channel.edit(
            overwrites=overwrites, reason=f"Updated by {str(ctx.author)}"
        )
        return await ctx.send("👍")

    @revokefiles.command(
        name="on",
        aliases=["enable", "e"],
        description="Enable permissions to attach files & embed links in a channel",
        example=",revokefiles on #text",
    )
    @has_permissions(manage_channels=True)
    async def revokefiles_on(self, ctx: Context, *, channel: TextChannel):
        overwrites = {}
        for obj, overwrite in channel.overwrites:
            overwrite.attach_files = True
            overwrite.embed_links = True
            overwrites[obj] = overwrite
        if ctx.guild.default_role not in overwrites:
            overwrites[ctx.guild.default_role] = PermissionOverwrite(
                attach_files=True, embed_links=True
            )
        await channel.edit(
            overwrites=overwrites, reason=f"Updated by {str(ctx.author)}"
        )
        return await ctx.send("👍")

    @command(name="setup", description="", aliases=["setme"])
    @has_permissions(administrator=True)
    async def setup(self, ctx: Context):
        kwargs = {"reason": "Moderation Setup"}
        deny_voice = PermissionOverwrite(connect=False)
        deny = PermissionOverwrite(
            send_messages=False, read_messages=False, view_channel=False
        )
        allow = PermissionOverwrite(
            send_messages=True, read_messages=True, view_channel=True
        )
        if not (imute := utils.get(ctx.guild.roles, name="imute")):
            imute = await ctx.guild.create_role(name="imute", **kwargs)

        if not (rmute := utils.get(ctx.guild.roles, name="rmute")):
            rmute = await ctx.guild.create_role(name="rmute", **kwargs)

        if not (jailed := utils.get(ctx.guild.roles, name="jailed")):
            jailed = await ctx.guild.create_role(name="jailed", **kwargs)

        if not (jail := utils.get(ctx.guild.text_channels, name="jail")):
            jail = await ctx.guild.create_text_channel(name="jail", **kwargs)
        for channel in ctx.guild.channels:
            if not isinstance(VoiceChannel):
                await channel.set_permissions(jailed, deny)
            else:
                await channel.set_permissions(jailed, deny_voice)
        await jail.set_permissions(
            jailed, PermissionOverwrite(send_messages=True, view_channel=True), **kwargs
        )
        await jail.set_permissions(ctx.guild.default_role, deny, **kwargs)
        return await ctx.success("successfully setup **moderation** module")

    @group(
        name="stickyrole",
        description="Reapplies a role on join",
        invoke_without_command=True,
    )
    async def stickyrole(self, ctx: Context):
        return await ctx.send_help()

    @stickyrole.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of every sticky role",
    )
    @has_permissions(server_owner=True)
    async def stickyrole_list(self, ctx: Context):
        if not (
            entries := await self.bot.db.fetch(
                """SELECT user_id, role_id FROM sticky_roles WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No **sticky roles** have been set")
        embed = Embed(title="Sticky Roles").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        entries = [e for e in entries if ctx.guild.get_role(e.role_id)]

        def get_user(user_id: int):
            if user := self.bot.get_user(user_id):
                return f"**{str(user)}** (`{user_id}`)"
            return f"**Unknown User** (`{user_id}`)"

        rows = [
            f"`{i}` {get_user(entry.user_id)} - {ctx.guild.get_role(entry.role_id).mention}"
            for i, entry in enumerate(entries, start=1)
        ]
        if not rows:
            raise CommandError("No **sticky roles** have been set")
        return await ctx.paginate(embed, rows)

    @stickyrole.command(
        name="add",
        description="Reapplies a role on join",
        example=",stickyrole add jonathan moderator",
    )
    @has_permissions(server_owner=True)
    async def stickyrole_add(self, ctx: Context, member: User, *, role: Role):
        await self.bot.db.execute(
            """INSERT INTO sticky_roles (guild_id, user_id, role_id) VALUES($1, $2, $3) ON CONFLICT(guild_id, user_id, role_id) DO NOTHING""",
            ctx.guild.id,
            member.id,
            role.id,
        )
        return await ctx.success(
            f"{role.mention} will now be reapplied when **{str(member)}** rejoins the server"
        )

    @stickyrole.command(
        name="remove",
        description="Removes a setup sticky role",
        example=",stickyrole remove jonathan moderator",
    )
    @has_permissions(server_owner=True)
    async def stickyrole_remove(self, ctx: Context, member: User, *, role: Role):
        deleted = len(
            await self.bot.db.fetch(
                """DELETE FROM sticky_roles WHERE guild_id = $1 AND user_id = $2 AND role_id = $3 RETURNING *""",
                ctx.guild.id,
                member.id,
                role.id,
            )
        )
        if deleted == 0:
            raise CommandError(
                f"**{str(member)}** does not have a sticky role setup for {role.mention}"
            )
        return await ctx.success(
            f"Removed {role.mention} from **sticky roles** for **{str(member)}**"
        )

    @group(
        name="raid",
        description="Remove all members that joined in the time provided in the event of a raid",
        example=",raid 1h kick raiding",
        invoke_without_command=True,
    )
    @has_permissions(server_owner=True)
    async def raid(
        self,
        ctx: Context,
        time: Expiration,
        action: str,
        *,
        reason: Optional[str] = "Raiding",
    ):
        if task := self.tasks.get(f"raid-{ctx.guild.id}"):
            raise MaxConcurrencyReached(1, BucketType.guild)
        if time >= 1800:
            raise CommandError("The furthest you can go back is **30 minutes**")

        members = [
            m
            for m in ctx.guild.members
            if m.joined_at >= utcnow() + timedelta(seconds=time)
        ]
        if not members:
            raise CommandError(
                f"No **members** found to **{action.lower()}** in the **time** provided"
            )

        async def rtask(members: List[Member]):
            for m in members:
                if action == "kick":
                    await m.kick(reason=reason)
                else:
                    await m.ban(reason=reason)

        if action.lower() not in ("kick", "ban"):
            raise CommandError("Valid actions are `kick` and `ban`")

        message = await ctx.normal(
            f"Executing **raid {action.lower()}** on **{len(members)}** members, this may take a while..."
        )
        task = create_task(rtask(members))
        self.tasks[f"raid-{ctx.guild.id}"] = task
        await task
        self.tasks.pop(f"raid-{ctx.guild.id}", None)
        return await message.edit(
            embed=Embed(
                color=self.bot.color,
                description=f"> {ctx.author.mention}: Finished this task in **{humanize.precisedelta(utcnow() - message.created_at, format='%0.0f')}**",
            )
        )

    @raid.command(
        name="cancel",
        aliases=["stop", "end"],
        description="End a chunkban of raid members",
    )
    @has_permissions(server_owner=True)
    async def raid_cancel(self, ctx: Context):
        if not (task := self.tasks.get(f"raid-{ctx.guild.id}")):
            raise CommandError("Theres no raid chunkban is ongoing...")
        task.cancel()
        self.tasks.pop(f"raid-{ctx.guild.id}", None)
        return await ctx.success("Cancelled the raid chunkban")

    @group(
        name="forcenickname",
        aliases=["forcenick", "fn"],
        description="Force a members current nickname",
        example=",forcenickname jonathan pussy",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True, nicknames=True)
    async def forcenickname(
        self, ctx: Context, member: Member, *, name_to_set: Optional[str] = None
    ):
        if not name_to_set:
            deleted = len(
                await self.bot.db.fetch(
                    """DELETE FROM forcenick WHERE guild_id = $1 AND user_id = $2 RETURNING *""",
                    ctx.guild.id,
                    member.id,
                )
            )
            if deleted == 0:
                raise CommandError("This member has no **nickname** forced")
            else:
                await member.edit(
                    nick=None, reason=f"Forcenick removed by {str(ctx.author)}"
                )
                return await ctx.success(
                    f"Removed **forced nickname** of {member.mention}"
                )
        else:
            if len(name_to_set) > 32:
                raise CommandError("Nickname is too long, max is 32 characters")
            await self.bot.db.execute(
                """INSERT INTO forcenick (guild_id, user_id, nickname) VALUES($1, $2, $3) ON CONFLICT(guild_id, user_id) DO UPDATE SET nickname = excluded.nickname""",
                ctx.guild.id,
                member.id,
                name_to_set,
            )
            await member.edit(
                nick=name_to_set, reason=f"Forcenick by {str(ctx.author)}"
            )
            return await ctx.success(
                f"Set **forced nickname** of {member.mention} to **{name_to_set}**"
            )

    @forcenickname.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of all forced nicknames",
    )
    @has_permissions(manage_guild=True, nicknames=True)
    async def forcenickname_list(self, ctx: Context):
        if not (
            nicknames := await self.bot.db.fetch(
                "SELECT user_id, nickname FROM forcenick WHERE guild_id = $1" "",
                ctx.guild.id,
            )
        ):
            raise CommandError("No **forced nicknames** have been applied")
        embed = Embed(title="Forced Nicknames").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )

        def get_user(record: Record):
            if user := self.bot.get_user(record.user_id):
                return f"**{str(user)}** (`{record.user_id}`)"
            else:
                return f"**Unknown User** (`{record.user_id}`)"

        rows = [
            f"`{i}` {get_user(nickname)} - {shorten(nickname.nickname, 5)}"
            for i, nickname in enumerate(nicknames, start=1)
        ]
        if not rows:
            raise CommandError("No **forced nicknames** have been applied")
        return await ctx.paginate(embed, rows)

    @command(name="topic", description="Change the current channel topic")
    @has_permissions(manage_channels=True)
    async def topic(self, ctx: Context, *, text: str):
        await ctx.channel.edit(topic=text[:1023])
        return await ctx.send("👍")

    @command(name="botclear", aliases=["bc"], description="clear messages from bots")
    @has_permissions(manage_messages=True)
    async def botclear(self, ctx: Context, search: Optional[int] = 100):
        return await self.purge_bots(ctx, search)

    @command(
        name="stfu",
        description="toggle deletion of a user's messages anytime they send one",
        example=",stfu jonathan",
    )
    @has_permissions(manage_messages=True)
    async def stfu(self, ctx: Context, user: SafeSnowflake):
        if (
            len(
                await self.bot.db.fetch(
                    """DELETE FROM silenced WHERE guild_id = $1 AND user_id = $2""",
                    ctx.guild.id,
                    user.id,
                )
            )
            > 0
        ):
            return await ctx.success(f"Allowed **{str(user)}** to speak again")
        else:
            await self.bot.db.execute(
                """INSERT INTO silenced (guild_id, user_id) VALUES($1, $2)""",
                ctx.guild.id,
                user.id,
            )
            return await ctx.success(f"Silenced **{str(user)}**")

    @group(
        name="restrictcommand",
        aliases=["restrict"],
        description="Only allows people with a certain role to use command",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def restrict(self, ctx: Context):
        return await ctx.send_help()

    @restrict.command(
        name="add",
        description="Allows the specified role exclusive permission to use a command",
        example=",restrictcommand add ban @staff",
    )
    @has_permissions(manage_guild=True)
    async def restrict_add(self, ctx: Context, cmd: CommandConverter, *, role: Role):
        try:
            await self.bot.db.execute(
                """INSERT INTO command_restrictions (guild_id, command, role_id) VALUES($1, $2, $3)""",
                ctx.guild.id,
                cmd,
                role.id,
            )
            return await ctx.success(f"Restricted **{cmd}** to {role.mention}")
        except Exception:
            raise CommandError("That restriction already **exists**")

    @restrict.command(
        name="remove",
        description="Removes the specified roles exclusive permission to use a command",
        example=",restrictcommand remove ban @staff",
    )
    @has_permissions(manage_guild=True)
    async def restrict_remove(self, ctx: Context, cmd: CommandConverter, *, role: Role):
        deleted = len(
            await self.bot.db.fetch(
                """DELETE FROM command_restrictions WHERE guild_id = $1 AND command = $2 AND role_id = $3""",
                ctx.guild.id,
                cmd,
                role.id,
            )
        )
        if deleted == 0:
            raise CommandError("That restriction **doesn't exist**")
        else:
            return await ctx.success(
                f"Removed restriction on **{cmd}** for {role.mention}"
            )

    @restrict.command(name="reset", description="Removes every restricted command")
    @has_permissions(manage_guild=True)
    async def restrict_reset(self, ctx: Context):
        deleted = len(
            await self.bot.db.fetch(
                """DELETE FROM command_restrictions WHERE guild_id = $1""", ctx.guild.id
            )
        )
        if deleted == 0:
            raise CommandError("No restrictions **exist**")
        else:
            return await ctx.success(f"Removed **{deleted}** restricted commands")

    @restrict.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of every restricted command",
    )
    @has_permissions(manage_guild=True)
    async def restrict_list(self, ctx: Context):
        if not (
            restrictions := await self.bot.db.fetch(
                """SELECT command, role_id FROM command_restrictions WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No restrictions **exist**")
        embed = Embed(title="Command Restrictions").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = []
        i = 0
        for entry in restrictions:
            if not (role := ctx.guild.get_role(entry.role_id)):
                continue
            i += 1
            rows.append(f"`{i}` **{entry.command}** - {role.mention}")
        if not rows:
            raise CommandError("No restrictions **exist**")
        return await ctx.paginate(embed, rows)

    @command(name="bans", description="View a list of the banned members")
    @has_permissions(ban_members=True)
    async def bans(self, ctx: Context):
        def get_user(user_id: int):
            if user := self.bot.get_user(user_id):
                return f"**{str(user)}** (`{user_id}`)"
            else:
                return f"**Unknown User** (`{user_id}`)"

        embed = Embed(title="Banned Members")
        rows = [
            f"`{i}` {get_user(ban.user)}"
            async for i, ban in enumerate(ctx.guild.bans())
        ]
        if not rows:
            raise CommandError("No banned members")
        return await ctx.paginate(embed, rows)
