from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional, Union

from discord import (  # type: ignore # type: ignore # type: ignore # type: ignore
    AuditLogEntry, Embed, Member, Message, Object, Role, User, VoiceState, abc,
    utils)
from discord.ext.commands import Context
from loguru import logger
from rival_tools import lock, ratelimit  # type: ignore

change_type = Union[Role, AuditLogEntry]


def serialize(key: str, value: Any):
    if isinstance(value, list):
        return ", ".join(f"`{m}`" for m in value)
    if key in ["allow", "deny"]:
        return False
    else:
        return value


def get_channel_changes(
    before: Union[abc.GuildChannel, AuditLogEntry],
    after: Union[abc.GuildChannel, AuditLogEntry],
):
    a = None
    b = None
    target = None
    changes = {}
    string = ""
    if isinstance(before, abc.GuildChannel):
        attrs = before.__slots__
        b = {s: before.__getattribute__(s) for s in attrs}
        a = {s: after.__getattribute__(s) for s in attrs}
        for s in attrs:
            if before.__getattribute__(s) != after.__getattribute__(s):
                changes[s] = after.__getattribute__(s)

    else:
        key = list(dict(before.changes.before).keys())[0]
        if key in ["allow", "deny"]:
            b = dict(before.changes.before)[key]
            a = dict(after.changes.after)[list(dict(after.changes.after).keys())[0]]
            changes = {k: v for k, v in a.items() if b[k] != v}
            target = [t for t, v in before.target.overwrites if v == a][0]

    for key, value in changes.items():
        _ = serialize(value)
        if _ is False:
            _b = dict(value)  # type: ignore
            _a = dict(a)  # type: ignore

        string += f"**{key}:** `{serialize(value)}`\n"
    if "overwrites" in a.keys():
        __a = a["overwrites"]
        target = [t for t, v in after.overwrites if v == __a][0]
    return target, string


def get_role_changes(before: change_type, after: change_type):
    added = ""
    removed = ""
    a = None
    b = None
    if isinstance(before, Role):
        if before.permissions != after.permissions:
            b = dict(before.permissions)
            a = dict(after.permissions)
        else:
            return None
    else:
        before = before.changes.before
        after = after.changes.after
        b = dict(dict(before).get("permissions"))
        a = dict(dict(after).get("permissions"))
    if a is not None and b is not None:
        difference = {key: value for key, value in a.items() if b[key] != value}
        for k, v in difference.items():
            if v is False:
                if removed == "":
                    removed += f"`{k.replace('_',' ')}`"
                else:
                    removed += f", `{k.replace('_', ' ')}`"
            else:
                if added == "":
                    added += f"`{k.replace('_', ' ')}`"
                else:
                    added += f", `{k.replace('_', ' ')}`"
    string = ""
    if added != "":
        string += f"**added:** {added}\n"
    if removed != "":
        string += f"**removed:** {removed}"
    return string


class EventType(Enum):
    channel_create = auto()
    channel_delete = auto()
    channel_update = auto()
    category_channel_create = auto()
    category_channel_delete = auto()
    category_channel_update = auto()
    role_create = auto()
    role_delete = auto()
    role_update = auto()
    role_assign = auto()
    command_enable = auto()
    command_disable = auto()
    alias_create = auto()
    alias_delete = auto()
    ban = auto()
    kick = auto()
    time_out = auto()
    mention_everyone = auto()
    voicemaster_channel_create = auto()
    voicemaster_channel_delete = auto()
    voice_join = auto()
    voice_leave = auto()
    jail = auto()
    unjail = auto()
    strip = auto()
    fakeperms_add = auto()
    fakeperms_remove = auto()


class Handler:
    def __init__(self, bot):
        self.bot = bot

    async def check_user(self, user: Union[Member, User, Object]):
        if isinstance(user, Object):
            if u := self.bot.get_user(user.id):
                _ = u
            else:
                _ = await self.bot.fetch_user(user.id)
        else:
            _ = user
        return _.mention

    def get_parents(self, ctx: Context):
        return [c.name for c in ctx.command.parents]

    def get_kwargs(self, ctx: Context):
        kw = ctx.kwargs
        p = -1
        if len(ctx.args) > 2:
            d = [c for c in ctx.command.clean_params.keys() if c not in kw]
            for i in ctx.args[2:]:
                p += 1
                kw[d[p]] = i
        ctx.kwargs = kw
        return ctx

    def voice_embed(self, ctx: Member, before: VoiceState, after: VoiceState, **kwargs):
        ts = utils.format_dt(datetime.now(), style="R")
        embed = Embed(color=self.bot.color)
        if kwargs.get("voicemaster", False) is True:
            if after is None and len(before.members) == 1:
                embed.title = "vm channel deletion"
                embed.description = f"voicemaster channel was deleted due to **{str(ctx)}** leaving {ts}"
            if after is not None:
                if before is not None:
                    if before.channel != after.channel:
                        embed.title = "vm channel creation"
                        embed.description = (
                            f"voicemaster channel was created for **{str(ctx)}** {ts}"
                        )
                    else:
                        return None
                else:
                    embed.title = "vm channel creation"
                    embed.description = (
                        f"voicemaster channel was created for **{str(ctx)}** {ts}"
                    )
        else:
            if before.channel:
                if after.channel:
                    embed.title = "User changed voice channels"
                    embed.description = f"{ctx.mention} left **{before.channel.name}** and joined **{after.channel.name}** {ts}"
                else:
                    embed.title = "User left a voice channel"
                    embed.description = (
                        f"{ctx.mention} left **{before.channel.name}** {ts}"
                    )
            else:
                if after.channel:
                    embed.title = "User joined a voice channel"
                    embed.description = (
                        f"{ctx.mention} joined **{after.channel.name}** {ts}"
                    )
        return embed

    async def get_embed(
        self, ctx: Union[Context, Message, AuditLogEntry], event: EventType
    ):
        ts = utils.format_dt(datetime.now(), style="R")
        embed = Embed(color=self.bot.color)
        if isinstance(ctx, Context):
            ctx = self.get_kwargs(ctx)
            if event == EventType.jail:
                embed.title = "member jailed"
                embed.description = f"{ctx.author.mention} **jailed** {ctx.kwargs['member'].mention} {ts}"
            elif event == EventType.unjail:
                member = ctx.kwargs.get("member")
                if isinstance(member, str):
                    if member.lower() == "all":
                        embed.title = "members unjailed"
                        embed.description = (
                            f"{ctx.author.mention} **unjailed** all jailed members {ts}"
                        )
                    else:
                        embed.title = "Member Punishment Removed"
                        embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** unjailed\n> **User:** {ctx.kwargs['member'].mention}\n> **When:** {ts}"
                else:
                    embed.title = "Member Punished"
                    embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** `jailed`\n> **User:** {ctx.kwargs['member'].mention}\n> **When:** {ts}"
            elif event == EventType.fakeperms_add:
                embed.title = "Fake Permissions Added"
                embed.description = f"**Moderator:** {ctx.author.mention}\n**Action:** {ctx.kwargs['entry'][0].mention} was given `{ctx.kwargs['entry'][1]}`\n**When:** {ts}"
            elif event == EventType.fakeperms_remove:
                embed.title = "Fake Permissions Removed"
                embed.description = f"**Moderator:** {ctx.author.mention}\n**Action:** permissions removed from {ctx.kwargs['role'].mention}\n**When:** {ts}"
            elif event == EventType.strip:
                embed.title = "Member Punished"
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** `All roles removed`\n> **User:** {ctx.kwargs['member'].mention}\n> **When:** {ts}"
            elif event == EventType.alias_create:
                embed.title = "Bot Settings Updated"
                args = ctx.kwargs["data"]
                command = args.command
                alias = args.alias
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** Created an alias\n> **Command:** `{command}`\n> **Alias Created:** `{alias}`\n> **When:** {ts}"
            elif event == EventType.alias_delete:
                embed.title = "Bot Settings Updated"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** Deleted an alias\n> **Command:** `{command}`\n> **Alias Deleted:** `{args['alias']}`\n> **When:** {ts}"
            elif event == EventType.command_disable:
                embed.title = "Bot Settings Updated"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** Disabled a command\n> **Command:** `{args['command']}`\n> **When:** {ts}"
            elif event == EventType.command_enable:
                embed.title = "Bot Settings Updated"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** Enabled a command\n> **Command:** `{args['command']}`\n> **When:** {ts}"
            elif event == EventType.ban:
                embed.title = "Member Punished"
                args = ctx.kwargs
                #                logger.info(args)
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Punishment:** `BANNED`\n> **User:** {str(args['user'])}\n> **When:** {ts}"
            elif event == EventType.kick:
                embed.title = "user kicked"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Punishment:** `KICKED`\n> **User:** {str(args['user'])}\n> **When:** {ts}"
            elif event == EventType.time_out:
                embed.title = "Member Punished"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **User:** {str(args.get('user','member'))}\n> **Punishment:** member timeout\n> **When:** {ts}"
                embed.add_field(
                    name="Timeout Duration", value=f'**{args["time"]}**', inline=False
                )
            elif event == EventType.role_assign:
                embed.title = "Role(s) Assigned to user"
                args = ctx.kwargs
                roles = args.get("role", args.get("role_input"))
                if len(roles) > 1:
                    r = ", ".join(_.mention for _ in roles)
                else:
                    r = roles[0].mention
                e = f"{args['member'].mention}" if args.get("member") else ""
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Role(s):** {r}\n> **User:** {e}\n> **When:** {ts}"
            elif event == EventType.role_create:
                embed.title = "Role Created"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Role:** {args['name']}\n> **When:** {ts}"
            elif event == EventType.role_update:
                embed.title = "Role Updated"
                args = ctx.kwargs
                if r := args.get("args"):
                    role = r.roles[0]
                else:
                    role = args.get("role")
                embed.description = f"**Moderator:** {ctx.author.mention}\n> Role: **{role.name}**\n> **Using:** {ctx.command.qualified_name}\n> **When:** {ts}"
            elif event == EventType.category_channel_create:
                embed.title = "Category Created"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Category:** {args['name']}\n> **How:** Created through Wocks `,category create` command\n> **When:** {ts}"
            elif event == EventType.category_channel_delete:
                embed.title = "Category Deleted"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Category:** {args['category'].name}\n> **How:** Deleted through Wocks `,category delete` command\n> **When:** {ts}"
            elif event == EventType.category_channel_update:
                embed.title = "Category Updated"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Category:** {args['category'].name}\n> **Using:** {ctx.command.qualified_name}\n> **When:** {ts}"
            elif event == EventType.channel_create:
                embed.title = "Channel Created"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Channel:** {args['name']}\n> **How:** Created through Wocks `,channel create` command\n> **When:** {ts}"
            elif event == EventType.channel_delete:
                embed.title = "Channel Deleted"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Channel:** {args['channel'].name}\n> **How:** Deleted through Wocks `,channel delete` command\n> **When:** {ts}"
            elif event == EventType.channel_update:
                embed.title = "Channel Updated"
                args = ctx.kwargs
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Channel:** {args['channel'].name}\n> **Using:** {ctx.command.qualified_name}\n> **When:** {ts}"
            if embed.title is None:
                if ctx.author.name == "aiohttp":
                    logger.info(
                        f"{event} didnt get an embed {'yes' if event == EventType.ban else 'no'}"
                    )
                return None
        elif isinstance(ctx, Message):
            if event == EventType.mention_everyone:
                embed.title = "Mentioned Everyone"
                embed.description = f"**Moderator:** {ctx.author.mention}\n> **Action:** mentioned @everyone \n> **Where:** {ctx.channel.mention}\n> **When:** {ts}"
            else:
                return None
        elif isinstance(ctx, AuditLogEntry):
            if event == EventType.role_assign:
                if ctx.reason:
                    if ctx.reason.startswith(f"[ {self.bot.user.name} antinuke ]"):
                        reason = ctx.reason.split(f"[ {self.bot.user.name} antinuke ]")[
                            -1
                        ]
                        title = "member stripped"
                        description = f"**Moderator:** {ctx.user.mention}\n> **User Stripped:** {str(ctx.target)}\n> **Reason:** {reason}\n> **When:** {ts}"
                    else:
                        if ctx.user == self.bot.user:
                            return None
                        reason = ctx.reason
                        title = "Role Settings Changed"
                        description = f"**Moderator:** {ctx.user.mention}\n> **User Stripped:** {str(ctx.target)}\n **Reason:** {reason}\n> **When:** {ts}"
                else:
                    if ctx.user == self.bot.user:
                        return
                    description = f"**Moderator:** {ctx.user.mention}\n> **Action:** Changed permissions for {str(ctx.target)}\n> **When:** {ts}"
                    title = "Role Settings Changed"
                embed.title = title
                embed.description = description
            elif event == EventType.channel_create:
                if ctx.user == self.bot.user:
                    return None
                embed.title = "Channel Created"
                embed.description = f"**Moderator:** {ctx.user.mention}\n> **Channel:** `{str(ctx.target)}`\n> **How:** Created through the guild settings\n> **When:** {ts}"
            elif event == EventType.channel_delete:
                if ctx.user == self.bot.user:
                    return None
                embed.title = "Channel Deleted"
                embed.description = f"**Moderator:** {ctx.user.mention}\n> **Channel:** `{str(ctx.before.name)}`\n> **How:** Deleted through guild settings\n> **When:** {ts}"
            elif event == EventType.channel_update:
                if ctx.user == self.bot.user:
                    return None
                try:
                    target, changes = get_channel_changes(ctx, ctx)
                    t = f" for {target.mention} "
                    m = f"\n{changes}"
                except Exception:
                    t = ""
                    m = ""
                embed.title = "Channel Updated"
                embed.description = f"**Moderator:** {ctx.user.mention}\n> **Channel:** {str(ctx.target)}{t}\n> **When:**{ts}{m}"
            elif event == EventType.category_channel_create:
                if ctx.user == self.bot.user:
                    return None
                embed.title = "Category Created"
                embed.description = f"**Moderator:** {ctx.user.mention}\n> **Category:** {str(ctx.after.name)}\n> **When:** {ts}"
            elif event == EventType.category_channel_delete:
                if ctx.user == self.bot.user:
                    return None
                embed.title = "Category Deleted"
                embed.description = f"**Moderator:** {ctx.user.mention}\n> **Category:** {str(ctx.before.name)}\n> **When:** {ts}"
            elif event == EventType.category_channel_update:
                if ctx.user == self.bot.user:
                    return None
                embed.title = "Category Updated"
                embed.description = f"**Moderator:** {ctx.user.mention}\n> **Updated** {str(ctx.target)}\n> **Using:** `{ctx.command.qualified_name}`\n> **When** {ts}"
            elif event == EventType.ban:
                if ctx.reason:
                    if ctx.reason.startswith(f"[ {self.bot.user.name} antinuke ]"):
                        reason = ctx.reason.split(f"[ {self.bot.user.name} antinuke ]")[
                            -1
                        ]
                        title = "Member Punished"

                        description = f"**Moderator:** {ctx.user.mention}\n> **User Punished:** {str(ctx.target)}\n> **Punishment:** `member banned`\n> **Reason:** {reason}\n> **When:** {ts}"
                    else:
                        if ctx.user == self.bot.user:
                            return None
                        reason = ctx.reason or "no reason provided"
                        title = "Member Punished"
                        description = f"**Moderator:** {ctx.user.mention}\n> **User Punished:** {str(ctx.target)}\n> **Punishment:** `member banned`\n> **Reason:** {reason}\n> **When:** {ts}"
                else:
                    reason = ctx.reason or "no reason provided"
                    title = "Member Punished"
                    description = f"**Moderator:** {ctx.user.mention}\n> **User Punished:** {str(ctx.target)}\n> **Punishment:** `member banned`\n> **When:** {ts}"
                embed.title = title
                embed.description = description
            elif event == EventType.kick:
                if ctx.reason:
                    if ctx.reason.startswith(f"[ {self.bot.user.name} antinuke ]"):
                        reason = ctx.reason.split(f"[ {self.bot.user.name} antinuke ]")[
                            -1
                        ]
                        title = "Member Punished"
                        description = f"**Moderator:** {ctx.user.mention}\n> **User Punished:** {str(ctx.target)}\n> **Punishment:** `member kicked`\n> **Reason:** {reason}\n> **When:** {ts}"
                    else:
                        if ctx.user == self.bot.user:
                            return None
                        reason = ctx.reason or "no reason provided"
                        title = "Member Punished"
                        description = f"**Moderator:** {ctx.user.mention}\n> **User Punished:** {await self.check_user(ctx.target)}\n> **Punishment:** `member kicked`\n> **Reason:** {reason}\n> **When:** {ts}"
                else:
                    if ctx.user == self.bot.user:
                        return None
                    reason = ctx.reason or "no reason provided"
                    title = "Member Punished"
                    description = f"**Moderator:** {ctx.user.mention}\n> **User Punished:** {await self.check_user(ctx.target)}\n> **Punishment:** `member kicked`\n> **When:** {ts}"
                embed.title = title
                embed.description = description
            elif event == EventType.time_out:
                if ctx.reason:
                    if ctx.user == self.bot.user:
                        if ctx.reason.startswith("muted by"):
                            embed.title = "Auto Mod Punishment"
                            embed.description = f"**User Punished**: {str(ctx.target)}\n> **Punishment:** `member timed out`\n> **Reason:** {ctx.reason}\n> **When:** {ts}"
                    else:
                        embed.title = "Member Timed Out"
                        embed.description = f"**Moderator:** {str(ctx.user)}\n> **User Punished**: {str(ctx.target)}\n> **Punishment:** `member timed out`\n> **Reason:** {ctx.reason}\n> **When:** {ts}"
                else:
                    embed.title = "Member Timed Out"
                    reason = f"> **Reason:** {ctx.reason}" + "\n" if ctx.reason else ""
                    embed.description = f"**Moderator:** {str(ctx.user)}\n> **User Punished**: {str(ctx.target)}\n> **Punishment:** `member timed out`\n{reason}> **When:** {ts}"
            else:
                return None
        embed.description = f"> {embed.description}"
        return embed

    async def handle_log(
        self, ctx: Union[Context, Message, AuditLogEntry]
    ) -> Optional[EventType]:
        val = 0
        if isinstance(ctx, Message):
            if ctx.mention_everyone is True:
                val = EventType.mention_everyone
        elif isinstance(ctx, Context):
            if ctx.command.qualified_name == "role":
                val = EventType.role_assign
            elif ctx.command.qualified_name.startswith("role"):
                parents = self.get_parents(ctx)
                if ctx.command.name == "delete":
                    val = EventType.role_delete
                elif "all" in parents:
                    if "cancel" not in ctx.command.qualified_name:
                        val = EventType.role_assign
                else:
                    val = EventType.role_update
            elif ctx.command.qualified_name == "command disable":
                val = EventType.command_disable
            elif ctx.command.qualified_name == "command enable":
                val = EventType.command_enable
            elif ctx.command.qualified_name == "alias add":
                val = EventType.alias_create
            elif ctx.command.qualified_name == "alias remove":
                val = EventType.alias_delete
            elif ctx.command.qualified_name == "ban":
                val = EventType.ban
            elif ctx.command.qualified_name == "kick":
                val = EventType.kick
            elif ctx.command.qualified_name == "mute":
                val = EventType.time_out
            elif ctx.command.qualified_name == "fakepermissions add":
                val = EventType.fakeperms_add
            elif ctx.command.qualified_name == "fakepermissions remove":
                val = EventType.fakeperms_remove
            elif ctx.command.qualified_name == "jail":
                val = EventType.jail
            elif ctx.command.qualified_name == "unjail":
                val = EventType.unjail
            elif ctx.command.qualified_name == "strip":
                val = EventType.strip
            elif ctx.command.qualified_name.startswith("channel"):
                parents = self.get_parents(ctx)
                if ctx.command.name == "delete":
                    val = EventType.channel_delete
                elif ctx.command.name in ("duplicate", "create"):
                    val = EventType.channel_create
                else:
                    val = EventType.channel_update
            elif ctx.command.qualified_name.startswith("category"):
                if ctx.command.name == "delete":
                    val = EventType.category_channel_delete
                elif ctx.command.name in ("create", "duplicate"):
                    val = EventType.category_channel_create
                else:
                    val = EventType.category_channel_update

            else:
                return None
        else:
            if reason := ctx.reason:
                if reason.startswith("invoked by"):
                    return None
            action = int(ctx.action.value)
            if action == 10:
                val = EventType.channel_create
            elif action == 11:
                val = EventType.channel_update
            elif action == 12:
                val = EventType.channel_delete
            elif action in (13, 14, 15):
                val = EventType.channel_update
            elif action == 30:
                val = EventType.role_create
            elif action == 31:
                val = EventType.role_update
            elif action == 32:
                val = EventType.role_delete
            elif action == 24:
                if hasattr(ctx.changes.before, "timed_out_until"):
                    val = EventType.time_out
            elif action == 20:
                val = EventType.kick
            elif action == 22:
                val = EventType.ban
            elif action == 25:
                try:
                    if len(ctx.changes.before.roles) > len(ctx.changes.after.roles):
                        val = EventType.role_assign
                except Exception:
                    pass
        if val != 0:
            return EventType(val)
        else:
            return None

    @lock("logs:{c.guild.id}")
    async def do_log(self, c: Union[Context, Message, AuditLogEntry, Member], **kwargs):
        if len(kwargs) > 0:
            embed = self.voice_embed(c, kwargs["before"], kwargs["after"])
        else:
            _type = await self.handle_log(c)
            if c.guild.id == 1203455800236965958:
                logger.info(f"event got type {_type}")
            if _type is None:
                return
            embed = await self.get_embed(c, _type)
        #        if isinstance(c, AuditLogEntry):
        #            if c.user.bot:
        #                return
        if embed:

            @ratelimit("modlogs:{c.guild.id}", 3, 5, True)
            async def do_message(
                c: Union[Context, Message, AuditLogEntry, Member], embed: Embed
            ):
                if channel_id := await self.bot.db.fetchval(
                    """SELECT channel_id FROM moderation_channel WHERE guild_id = $1""",
                    c.guild.id,
                ):
                    if channel := self.bot.get_channel(channel_id):
                        await channel.send(embed=embed)

            return await do_message(c, embed)
