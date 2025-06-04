import asyncio
import datetime
import re
import typing
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, List, Optional, Union

import aiohttp
import discord
import humanfriendly
import humanize
import orjson
from discord.ext import commands
from discord.ext.commands import Cog, CommandError
from fast_string_match import closest_match
from rival_tools import lock, timeit  # type: ignore
from tools.aliases import CommandConverter  # type: ignore
from tools.important import Context  # type: ignore
from tools.important.subclasses.command import (Argument,  # type: ignore
                                                CategoryChannel, Member, Role,
                                                TextChannel, VoiceChannel)
from tools.views import Confirmation  # type: ignore


class InvalidError(TypeError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class GuildChannel(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        channels = {
            c.name: c.id for c in ctx.guild.channels if c.type.name != "category"
        }
        if match := closest_match(argument, list(channels.keys())):
            return ctx.guild.get_channel(channels[match])
        else:
            raise commands.CommandError(f"Channel `{argument}` not found")


@dataclass
class ChannelArgs:
    channel: discord.abc.GuildChannel
    arg: str


class ChannelConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> Optional[ChannelArgs]:
        args = await Argument().convert(ctx, argument)
        if "category" in ctx.command.qualified_name.lower():
            channel = await CategoryChannel().convert(ctx, args.first)
        else:
            channel = await GuildChannel().convert(ctx, args.first)
        return ChannelArgs(channel=channel, arg=args.second)


@dataclass
class CommandRestriction:
    command: Union[commands.Command, commands.Group]
    role: discord.Role


@dataclass
class RoleArguments:
    roles: List[discord.Role]
    arg: str


class RoleArgs(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> Optional[RoleArguments]:
        args = await Argument().convert(ctx, argument)
        roles = await Role().convert(ctx, args.first)
        return RoleArguments(roles=roles, arg=args.second)


class Restriction(commands.Converter):
    async def convert(
        self, ctx: Context, argument: str
    ) -> Optional[CommandRestriction]:
        args = await Argument().convert(ctx, argument)
        command = await CommandConverter().convert(ctx, args.first)
        role = await Role(assign=False).convert(ctx, args.second)
        return CommandRestriction(command=command, role=role[0])


#

if typing.TYPE_CHECKING:
    from tools.wock import Wock  # type: ignore


class Moderation(Cog):
    def __init__(self, bot: "Wock") -> None:
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)
        self.tasks = {}

    async def get_int(self, string: str):
        t = ""
        for s in string:
            try:
                d = int(s)
                t += f"{d}"
            except Exception:
                pass
        return t

    async def add_role(
        self,
        message: discord.Message,
        members: typing.List[discord.Member],
        role: discord.Role,
        remove: Optional[bool] = False,
        reason: Optional[str] = "",
    ):
        i = 0
        if remove is True:
            action = "taking"
            a = "from"
        else:
            action = "giving"
            a = "to"
        for m in members:
            if m.is_bannable:
                if remove is True:
                    await m.remove_roles(role, reason=reason)
                else:
                    await m.add_roles(role, reason=reason)
                i += 1

        self.tasks.pop(f"role-all-{message.guild.id}")
        return await message.edit(
            embed=discord.Embed(
                description=f"finished {action} {role.mention} {a} **{i}** users",
                color=self.bot.color,
            )
        )

    async def role_all_task(
        self,
        ctx: Context,
        message: discord.Message,
        role: discord.Role,
        bots: Optional[bool] = False,
        mentionable: Optional[bool] = False,
        remove: Optional[bool] = False,
    ):
        async with self.locks[f"role-all-{ctx.guild.id}"]:
            if mentionable is True:
                if remove is False:
                    members = [m for m in ctx.channel.members if role not in m.roles]
                else:
                    members = [m for m in ctx.channel.members if role in m.roles]
            elif bots is True:
                if remove is False:
                    members = [
                        m for m in ctx.guild.members if m.bot and role not in m.roles
                    ]
                else:
                    members = [
                        m for m in ctx.guild.members if m.bot and role in m.roles
                    ]
            else:
                if remove is False:
                    members = [
                        m
                        for m in ctx.guild.members
                        if m.bot is False and role not in m.roles
                    ]
                else:
                    members = [
                        m
                        for m in ctx.guild.members
                        if m.bot is False and role in m.roles
                    ]
            try:
                members.remove(ctx.guild.me)
            except Exception:
                pass
            members = [m for m in members if m.is_bannable is True]
            members = [m for m in members if m.top_role < ctx.guild.me.top_role]
            if len(members) == 0:
                return await message.edit(
                    embed=discord.Embed(
                        color=self.bot.color,
                        description=f"no users found to {'give' if remove is False else 'take'} {role.mention} {'to' if remove is False else 'from'}",
                    )
                )
            reason = f"invoked by author | {ctx.author.id}"
            future = asyncio.ensure_future(
                self.add_role(message, members, role, remove, reason)
            )
            self.tasks[f"role-all-{ctx.guild.id}"] = future

    async def disable_slowmode(self, sleep_time: int, channel: discord.TextChannel):
        await asyncio.sleep(sleep_time)
        await channel.edit(slowmode_delay=0)
        return True

    async def moderator_logs(self, ctx: Context, description: str):  # type: ignore # type: ignore
        return

    @commands.command(
        name="nsfw", brief="Toggle nsfw for a channel", example=",nsfw #channel"
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def nsfw(self, ctx: Context, *, channel: TextChannel = None):
        if channel is None:
            channel = ctx.channel
        await self.moderator_logs(ctx, f"toggled nsfw on {channel.mention}")
        if channel.is_nsfw():
            await channel.edit(
                nsfw=False, reason=f"invoked by author | {ctx.author.id}"
            )
            return await ctx.success(f"**Disabled nsfw** for {channel.mention}")
        else:
            await channel.edit(nsfw=True, reason=f"invoked by author | {ctx.author.id}")
            return await ctx.success(f"**Enabled nsfw** for {channel.mention}")

    @commands.group(
        name="slowmode",
        aliases=["sm"],
        brief="Turn slowmode for the wait time for an amount of time",
        example=",slowmode 5 20m",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(moderate_members=True)
    async def slowmode(self, ctx: Context, seconds: int, *, timeframe: str = None):
        if seconds > 21600:
            return await ctx.fail("**Slowmode cannot** be longer than **6 hours**")
        if timeframe:
            try:
                converted = humanfriendly.parse_timespan(timeframe)
                tf = humanize.naturaldelta(datetime.timedelta(seconds=converted))
            except Exception:
                return await ctx.fail(f"`{timeframe}` is an **invalid** time")
        await self.moderator_logs(ctx, f"toggled slowmode on {ctx.channel.mention}")
        await ctx.channel.edit(
            slowmode_delay=seconds, reason=f"invoked by author | {ctx.author.id}"
        )
        if timeframe:
            asyncio.ensure_future(self.disable_slowmode(converted, ctx.channel))
        return await ctx.success(
            f"Users will now have to wait **{seconds} seconds** to **send messages** {f'for **{tf}**' if timeframe else ''}"
        )

    @slowmode.command(
        name="reset",
        aliases=["off"],
        brief="reset the slowmode on the channel",
        example=",slowmode reset",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(moderate_members=True)
    async def slowmode_reset(self, ctx: Context):
        await ctx.channel.edit(
            slowmode_delay=0, reason=f"invoked by author | {ctx.author.id}"
        )
        await self.moderator_logs(ctx, f"reset slowmode on {ctx.channel.mention}")
        return await ctx.success(f"**Disabled** slowmode on {ctx.channel.mention}")

    async def find_ban(self, ctx, user: typing.Union[int, str], bans):
        if isinstance(user, int):
            banned_user = discord.utils.get(bans, user__id=user)
            if not banned_user:
                return False
            else:
                return banned_user
        if isinstance(user, str):
            if "#" in user:
                try:
                    name, tag = user.split("#")
                except Exception:
                    return await ctx.fail("That user is **not banned**")
                banned_user = discord.utils.get(
                    bans, user__name=name, user__discriminator=tag
                )
                if not banned_user:
                    return False
                return banned_user
            else:
                banned_user = discord.utils.get(bans, user__name=user)
                if not banned_user:
                    return False
                return banned_user
        else:
            if isinstance(user, int):
                banned_user = discord.utils.get(bans, user__id=user)
                if not banned_user:
                    return False
                else:
                    return banned_user
            else:
                return False

    @commands.command(
        name="banned", brief="view the reason a user is banned", example=",banned c_5n"
    )
    @commands.bot_has_permissions(ban_members=True)
    @commands.has_permissions(moderate_members=True)
    async def banned(self, ctx: Context, *, user: str):
        bans = [ban async for ban in ctx.guild.bans(limit=5000)]
        ban = await self.find_ban(ctx, user, bans)
        if ban is not False:
            try:
                us = f"**{discord.utils.escape_markdown(str(ban.user))}**"
            except Exception:
                us = f"**{str(ban.user.name)}**"
            return await ctx.send(
                embed=discord.Embed(
                    description=f"{us} is banned for `{ban.reason}`",
                    color=self.bot.color,
                )
            )
        return await ctx.fail("That user is **not banned**")

    @commands.command(
        name="nuke",
        aliases=["bomb", "destroy"],
        brief="delete and recreate the same channel with the same permissions",
        example=",nuke #>.<",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(administrator=True)
    async def nuke(self, ctx: Context, *, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel
        position = channel.position
        new = await channel.clone(
            reason=f"nuked by {str(ctx.author)} | {ctx.author.id}"
        )
        if await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            await self.bot.db.execute(
                "UPDATE guild.boost SET channel_id = $1 WHERE guild_id = $2",
                new.id,
                ctx.guild.id,
            )
        if await self.bot.db.fetchrow(
            "SELECT * FROM welcome WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            if self.bot.cache.welcome.get(ctx.guild.id):
                self.bot.cache.welcome[ctx.guild.id]["channel"] = new.id
            else:
                self.bot.cache.welcome[ctx.guild.id] = {"channel": new.id}
            await self.bot.db.execute(
                "UPDATE welcome SET channel_id = $1 WHERE guild_id = $2",
                new.id,
                ctx.guild.id,
            )
        if await self.bot.db.fetchrow(
            "SELECT * FROM leave WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            channel.id,
        ):
            await self.bot.db.execute(
                "UPDATE leave SET channel_id = $1 WHERE guild_id = $2",
                new.id,
                ctx.guild.id,
            )
            self.bot.cache.leave[ctx.guild.id]["channel"] = new.id
        await channel.delete(
            reason=f"Channel nuked by {str(ctx.author)} | {ctx.author.id}"
        )
        await self.moderator_logs(ctx, f"nuked {channel.mention}")
        await new.edit(position=position, reason=f"invoked by author | {ctx.author.id}")
        return await new.send(
            embed=discord.Embed(
                description=f"{new.mention} has been **nuked**. If any **welcomes**, **leaves**, or **booster messages** configured for the previous channel, has **been configured through wock**, it has been **reconfigured** to send **here.**",
                color=self.bot.color,
            )
        )

    @commands.command(
        name="reactionmute",
        aliases=["rmute", "reactmute"],
        brief="mute a member from reacting to messages",
        example=",rmute @c_5n toxic",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def reactionmute(self, ctx: Context, *, member: Member):
        role = discord.utils.get(ctx.guild.roles, name="rmute")
        if not role:
            return await ctx.fail(
                f"reaction mute **role** not found please run `{ctx.prefix}setme`"
            )
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        if role in member.roles:
            await member.remove_roles(role)
            return await ctx.success(
                f"**{member.mention}** has been **unreaction-muted**"
            )
        await member.add_roles(role)
        return await ctx.success(f"**{member.mention}** has been **reaction muted**")

    @commands.command(
        name="imagemute",
        aliases=["imute", "im", "imgmute"],
        brief="mute a member from sending images",
        example="imute @c_5n nsfw",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def imagemute(self, ctx: Context, *, member: Member):
        role = discord.utils.get(ctx.guild.roles, name="imute")
        if not role:
            return await ctx.fail(
                f"image mute **role** not found please run `{ctx.prefix}setme`"
            )
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        if role in member.roles:
            await member.remove_roles(role)
            return await ctx.success(f"**{member.mention}** has been **unimage-muted**")
        await member.add_roles(role)
        return await ctx.success(f"**{member.mention}** has been **image muted**")

    @commands.group(
        name="restrict",
        aliases=["restrictcommand"],
        brief="restrict a command for specific perms",
        invoke_without_command=True,
        example=",restrict ban @role",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def restrict(self, ctx: Context):
        return await ctx.send_help()

    @restrict.command(
        name="add", aliases=["create", "c", "a"], brief="add a command restriction"
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def restrict_add(self, ctx: Context, *, args: Restriction):
        await self.bot.db.execute(
            "INSERT INTO command_restriction (guild_id, command_name, role_id) VALUES ($1, $2, $3) ON CONFLICT(guild_id,command_name,role_id) DO NOTHING",
            ctx.guild.id,
            args.command.qualified_name,
            args.role.id,
        )
        return await ctx.success(
            f"**{args.command.qualified_name}** has been **restricted** to {args.role.mention}"
        )

    @restrict.command(
        name="remove",
        aliases=["rem", "delete", "del", "d", "r"],
        brief="Delete a command restriction",
        example=",restrict remove ban, @role",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def restrict_remove(self, ctx: Context, *, args: Restriction):
        await self.bot.db.execute(
            """DELETE FROM command_restriction WHERE guild_id = $1 AND command_name = $2 AND role_id = $3""",
            ctx.guild.id,
            args.command.qualified_name,
            args.role.id,
        )
        return await ctx.success(
            f"the restriction for **{args.command.qualified_name}** has been **removed** from {args.role.mention}"
        )

    @restrict.command(
        name="reset",
        aliases=["clear"],
        brief="reset all command restrictions",
        example=",restrict reset",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def restrict_reset(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM command_restriction WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.success("all command restrictions have been reset")

    @restrict.command(
        name="list",
        brief="show command restrictions",
        aliases=["show"],
        example=",restrict list",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    async def restrict_list(self, ctx: Context):
        restrictions = await self.bot.db.fetch(
            """SELECT command_name, role_id FROM command_restriction WHERE guild_id = $1""",
            ctx.guild.id,
        )
        if not restrictions:
            return await ctx.fail("no restrictions found")
        rows = []
        i = 0
        for entry in restrictions:
            if role := ctx.guild.get_role(entry.role_id):
                i += 1
                rows.append(f"`{i}` **{entry.command_name}** - {role.mention}")
        return await self.bot.dummy_paginator(
            ctx,
            discord.Embed(title="restrictions", color=self.bot.color),
            rows,
            type="restriction",
        )

    @commands.command(
        name="topic",
        brief="change the channel topic",
        example=",topic c_5n is the best",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def topic(self, ctx: Context, *, args: ChannelConverter):
        await args.channel.edit(topic=args.arg)
        return await ctx.success(
            f"**{args.channel.mention}**'s topic has been changed to **{args.arg}**"
        )

    @commands.command(
        name="permissions",
        aliases=["perms"],
        brief="show a member or role's permissions",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def permissions(self, ctx: Context, *, member: Union[discord.Member, Role]):
        if isinstance(member, discord.Member):
            permissions = dict(member.guild_permissions)
            icon = member.display_avatar.url
        else:
            member = member[0]
            icon = member.display_icon.url if member.display_icon else None
            permissions = dict(member.permissions)
        perms = []
        permissions = [k for k, v in permissions.items() if v is True]
        if len(permissions) == 0:
            return await ctx.fail(f"**{member.name}** has no permissions")
        for i, k in enumerate(permissions, start=1):
            perms.append(f"`{i}` **{k.replace('_',' ').title()}**")
        embed = discord.Embed(
            title=f"{member.name}'s permissions", color=self.bot.color
        ).set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        try:
            (embed.set_thumbnail(url=icon if icon else ctx.author.display_avatar.url),)
        except Exception:
            pass
        return await self.bot.dummy_paginator(
            ctx,
            embed,
            perms,
            type="Permission",
        )

    @commands.command(
        name="newusers",
        brief="show new users that joined the guild",
        example=",newusers",
    )
    async def newusers(self, ctx: Context):
        sorted_members = sorted(
            ctx.guild.members, key=lambda x: x.joined_at, reverse=True
        )
        content = discord.Embed(title=f"{ctx.guild.name} members", color=self.bot.color)
        rows = []
        for i, member in enumerate(sorted_members, start=1):
            jointime = discord.utils.format_dt(member.joined_at, style="R")
            rows.append(f"`{i}` **{member}** - {jointime}")
        return await self.bot.dummy_paginator(ctx, content, rows, type="member")

    @commands.group(
        name="role",
        aliases=["r"],
        invoke_without_command=True,
        brief="Give a role to a user",
        example=",role @c_5n owner",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def role(self, ctx, member: Member = None, *, role_input: Role):
        if ctx.invoked_subcommand is None:
            if (
                member.top_role > ctx.author.top_role
                and member != ctx.author
                and ctx.author != ctx.guild.owner
            ):
                if member.id != ctx.author.id:
                    return await ctx.warning(f"{member.mention} is **higher than you**")
            if not role_input:
                await ctx.warning("You must **mention a role**")
                return
            removed = []
            added = []
            roles = member.roles
            for role in role_input:
                if role in roles:
                    roles.remove(role)
                    removed.append(f"{role.mention}")
                else:
                    roles.append(role)
                    added.append(f"{role.mention}")
            await member.edit(
                roles=roles, reason=f"invoked by author | {ctx.author.id}"
            )
            text = ""
            if len(added) > 0:
                if len(added) == 1:
                    text += f"**Added** {added[0]} **role** "
                else:
                    text += f"**Added** {len(added)} **roles** "
            if len(removed) > 0:
                if len(removed) == 1:
                    t = f"{removed[0]} **role**"
                else:
                    t = f"{len(removed)} **roles**"
                if len(added) > 0:
                    text += f"and **Removed** {t} **from** {member.mention}"
                else:
                    text += f"**Removed** {t} **from** {member.mention}"
            else:
                text += f"**to** {member.mention}"
            await self.moderator_logs(ctx, f"{text}")
            return await ctx.success(text)

    @role.command(
        name="mentionable",
        brief="make a role mentionable lol",
        example=",role mentionable @owner",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_mentionable(self, ctx: Context, *, role: Role):
        role = role[0]
        mention = False
        if role.mentionable is False:
            mention = True
        await role.edit(mentionable=mention)
        return await ctx.success(
            f"{role.mention} is now {'**mentionable**' if mention is True else '**not mentionable**'}"
        )

    @role.group(
        name="all",
        invoke_without_command=True,
        brief="give a role to all members or bots",
        example=",role all @members",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def roleall(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @roleall.command(
        name="mentionable",
        brief="give a role to all users in a channel",
        example=",role all @members",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def roleall_mentionable(self, ctx: Context, *, role: Role):
        role = role[0]
        if self.tasks.get(f"role-all-{ctx.guild.id}"):
            return await ctx.fail("only one **task** can run at a time")
        message = await ctx.send(
            embed=discord.Embed(
                description=f"giving {role.mention} to all users... this may take a while...",
                color=self.bot.color,
            )
        )
        await self.moderator_logs(ctx, f"gave {role.mention} to all users")
        await self.role_all_task(ctx, message, role, False, True, False)
        return

    @roleall.group(
        name="bots",
        invoke_without_command=True,
        brief="give a role to all bots",
        example=",role all bots @botrole",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def roleall_bots(self, ctx: Context, *, role: Role):
        if self.tasks.get(f"role-all-{ctx.guild.id}"):
            return await ctx.fail("only one **task** can run at a time")
        role = role[0]
        message = await ctx.send(
            embed=discord.Embed(
                description=f"giving {role.mention} to all bots... this may take a while...",
                color=self.bot.color,
            )
        )
        await self.moderator_logs(ctx, f"gave {role.mention} to all bots")
        await self.role_all_task(ctx, message, role, True, False, False)
        return

    @roleall_bots.command(
        name="remove",
        brief="remove a role from all bots",
        example=",role all bots remove @botrole",
    )
    @commands.bot_has_permissions(administrator=True)
    async def roleall_bots_remove(self, ctx: Context, *, role: Role):
        role = role[0]
        if self.tasks.get(f"role-all-{ctx.guild.id}"):
            return await ctx.fail("only one **task** can run at a time")
        message = await ctx.send(
            embed=discord.Embed(
                description=f"removing {role.mention} from all bots... this may take a while...",
                color=self.bot.color,
            )
        )
        await self.moderator_logs(ctx, f"removed {role.mention} from all bots")
        await self.role_all_task(ctx, message, role, True, False, True)
        return

    @roleall.group(
        name="humans",
        brief="give a role to all humans",
        invoke_without_command=True,
        example=",role all humans @member",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def roleall_humans(self, ctx: Context, *, role: Role):
        if self.tasks.get(f"role-all-{ctx.guild.id}"):
            return await ctx.fail("only one **task** can run at a time")
        role = role[0]
        message = await ctx.send(
            embed=discord.Embed(
                description=f"giving {role.mention} to all humans... this may take a while...",
                color=self.bot.color,
            )
        )
        await self.moderator_logs(ctx, f"gave {role.mention} to all humans")
        await self.role_all_task(ctx, message, role, False, False, False)
        return

    @roleall_humans.command(
        name="remove",
        brief="remove a role from all humans",
        example=",role all humans remove @member",
    )
    @commands.bot_has_permissions(administrator=True)
    async def roleall_humans_remove(self, ctx: Context, *, role: Role):
        if self.tasks.get(f"role-all-{ctx.guild.id}"):
            return await ctx.fail("only one **task** can run at a time")
        role = role[0]
        message = await ctx.send(
            embed=discord.Embed(
                description=f"removing {role.mention} from all humans... this may take a while...",
                color=self.bot.color,
            )
        )
        await self.moderator_logs(ctx, f"took {role.mention} from all humans")
        await self.role_all_task(ctx, message, role, False, False, True)
        return

    @roleall.command(
        name="cancel", brief="cancel the roleall task", example=",role all cancel"
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def roleall_cancel(self, ctx: Context):
        if not self.tasks.get(f"role-all-{ctx.guild.id}"):
            return await ctx.fail("no roleall **task** running")
        try:
            self.tasks[f"role-all-{ctx.guild.id}"].cancel()
        except Exception:
            pass
        self.tasks.pop(f"role-all-{ctx.guild.id}")
        return await ctx.success("cancelled role all **task**")

    @role.command(
        name="rename",
        brief="Rename a created role",
        example=",role rename @members, com",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_rename(self, ctx, *, args: RoleArgs):
        role = args.roles[0]
        if not ctx.guild.get_role(role.id):
            return
        await role.edit(name=args.arg, reason=f"invoked by author | {ctx.author.id}")
        return await ctx.success(f"**Renamed** {role.mention} to **{args.arg}**")

    @role.command(
        name="color",
        brief="Create a color for a role",
        example=",role color @com, 010101",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_color(self, ctx, color: discord.Color | str, *, role: Role):
        role = role[0]
        if not ctx.guild.get_role(role.id):
            return
        try:
            if isinstance(color, str):
                if not color.startswith("#"):
                    color = f"#{color}"
                color = discord.Color.from_str(color)
            await role.edit(color=color, reason=f"invoked by author | {ctx.author.id}")
            return await ctx.success(
                f"Created the color **#{color}** for {role.mention}"
            )
        except Exception:
            return await ctx.fail("That **color** was **not** found")

    @role.command(
        name="hoist",
        brief="Display the role seperately from other roles",
        example=",role hoist @com",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_hoist(self, ctx, *, role: Role):
        role = role[0]
        if not ctx.guild.get_role(role.id):
            return
        state = True if not role.hoist else False
        if state is True:
            if role.hoist is False:
                await role.edit(
                    hoist=True, reason=f"invoked by author | {ctx.author.id}"
                )
            s = "**Hoisted**"
        else:
            if role.hoist is True:
                await role.edit(
                    hoist=False, reason=f"invoked by author | {ctx.author.id}"
                )
            s = "**Unhoisted**"
        return await ctx.success(f"{role.mention} has been {s}")

    @role.command(
        name="create",
        brief="Create a new role for the guild",
        example=",role create com",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_create(self, ctx, *, name):
        role = await ctx.guild.create_role(
            name=name, reason=f"invoked by author | {ctx.author.id}"
        )
        return await ctx.success(f"**Created {role.mention} role**")

    @role.command(
        name="delete",
        brief="Delete an existing role in the guild",
        example=",role delete com",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_delete(self, ctx, *, role: Role):
        role = role[0]
        if not ctx.guild.get_role(role.id):
            return
        try:
            await role.delete(reason=f"invoked by author | {ctx.author.id}")
            return await ctx.success(f"**Deleted** `{role.name}` **role**")
        except Exception:
            return await ctx.fail(f"**Couldn't delete `{role.name}` role**")

    @role.command(
        name="duplicate",
        brief="Duplicate an existing role",
        example=",role duplicate com",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_duplicate(self, ctx, *, role: Role):
        role = role[0]
        if role.permissions.value > ctx.author.guild_permissions.value:
            return await ctx.fail("That role has **higher permissions** than you")
        r = await ctx.guild.create_role(
            name=role.name,
            color=role.color,
            hoist=role.hoist,
            permissions=role.permissions,
            display_icon=role.display_icon or None,
            mentionable=role.mentionable,
            reason=f"invoked by author | {ctx.author.id}",
        )
        return await ctx.success(
            f"**Duplicated** {role.mention} and **created** `{r.name}`"
        )

    @role.command(
        name="icon",
        brief="Change the icon of a roles emoji",
        example=",role icon com, <emoji_here>",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_icon(
        self, ctx, role: Role, *, icon: Union[discord.PartialEmoji, str, None] = None
    ):
        role = role[0]
        if not ctx.guild.get_role(role.id):
            return

        if icon is None:
            if len(ctx.message.attachments) == 0:
                return await ctx.fail("Provide a **URL**, **attachment**, or **emoji**")

            attachment = ctx.message.attachments[0]
            icon = await attachment.read()
        elif isinstance(icon, (discord.PartialEmoji, discord.Emoji)):
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://proxy.rival.rocks?url={icon.url}"
                ) as f:
                    icon = await f.read()
        elif isinstance(icon, str):
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://proxy.rival.rocks?url={icon}") as f:
                    icon = await f.read()
        else:
            return await ctx.fail("This **cannot** be used for a **role icon**")

        await role.edit(
            display_icon=icon, reason=f"invoked by author | {ctx.author.id}"
        )
        return await ctx.success(f"The **icon** of {role.mention} has been **applied**")

    @commands.group(name="channel", brief="List of Channel commands")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel(self, ctx):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command)

    @channel.command(name="create", brief="Create a new channel in a guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel_create(self, ctx, type: str = "text", *, name: str):
        type = type.lower()
        if "text" in type:
            c = await ctx.guild.create_text_channel(
                name=name, reason=f"invoked by author | {ctx.author.id}"
            )
        else:
            c = await ctx.guild.create_voice_channel(
                name=name, reason=f"invoked by author | {ctx.author.id}"
            )
        return await ctx.success(f"**Created [#{name}]({c.jump_url}) channel**")

    @channel.command(name="delete", brief="Delete a channel in the current guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel_delete(
        self, ctx, *, channel: TextChannel | VoiceChannel | discord.abc.GuildChannel
    ):
        channel_name = channel.name
        await channel.delete()
        return await ctx.success(f"**Deleted `{channel_name}` channel**")

    @channel.command(
        name="rename", brief="Rename an existing channel in the current guild"
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel_rename(self, ctx, *, args: ChannelConverter):
        name = args.arg
        channel_name = args.channel.name
        channel = args.channel
        await channel.edit(name=name, reason=f"invoked by author | {ctx.author.id}")
        return await ctx.success(f"**Renamed** `{channel_name}` to {channel.mention}")

    @channel.command(
        name="duplicate",
        aliases=["copy"],
        brief="Duplicate an existing channel in the current guild",
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel_duplicate(self, ctx, *, channel: TextChannel | VoiceChannel):
        c = await channel.clone(reason=f"invoked by author | {ctx.author.id}")
        return await ctx.success(f"**Duplicated** `{channel.name}` into {c.mention}")

    # @channel.command(name = 'permissions')
    # async def channel_permissions(self, ctx, channel: TextChannel | VoiceChannel, permissions: str, state: bool):

    @commands.group(name="category", brief="List of category commands")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def category(self, ctx):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command)

    @category.command(name="create", brief="Create a category for a guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def category_create(self, ctx, *, name: str):
        c = await ctx.guild.create_category_channel(
            name=name, reason=f"invoked by author | {ctx.author.id}"
        )
        return await ctx.success(f"**Created [{name}]({c.jump_url}) category**")

    @category.command(name="rename", brief="Rename an existing category's name")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def category_rename(self, ctx, *, args: ChannelConverter):
        category_name = args.channel.name
        category = args.channel
        await args.channel.edit(
            name=args.arg, reason=f"invoked by author | {ctx.author.id}"
        )
        return await ctx.success(
            f"**Renamed `{category_name}` to [{args.arg}]({category.jump_url})**"
        )

    @category.command(name="delete", brief="Delete an existing category from the guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def category_delete(self, ctx, *, category: CategoryChannel):
        category_name = category.name
        await category.delete(reason=f"invoked by author | {ctx.author.id}")
        return await ctx.success(f"**Deleted `{category_name}` category**")

    @category.command(
        name="duplicate", brief="Duplicate an existing category in the guild"
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def category_duplicate(self, ctx, *, category: CategoryChannel):
        c = await category.clone(reason=f"invoked by author | {ctx.author.id}")
        return await ctx.success(
            f"**Duplicated** `{category.name}` into **{c.jump_url}**"
        )

    # @category.command(name = 'permissions')
    # async def category_permissions(self, ctx, category: discord.CategoryChannel, permissions: str, state: bool):
    #     pass

    @commands.command(name="ban", aliases=["exile"], brief="Ban a user from the guild")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_member(
        self, ctx, user: Union[discord.Member, discord.User], *, reason=None
    ):
        if not (r := await self.bot.hierarchy(ctx, user)):
            return r
        if isinstance(user, discord.Member):
            if user.premium_since:
                message = await ctx.send(
                    embed=discord.Embed(
                        description=f"{user.mention} is **boosting this server**, would you like to **ban?**",
                        color=self.bot.color,
                    )
                )
                await message.edit(
                    view=(view := Confirmation(message=message, invoker=ctx.author))
                )
                await view.wait()
                if not view.value:
                    await message.edit(
                        embed=discord.Embed(
                            description=f"{ctx.author.mention}: banning **cancelled**",
                            color=self.bot.color,
                        )
                    )
                    raise InvalidError()
                else:
                    await ctx.guild.ban(user, reason=reason)
                    await self.moderator_logs(ctx, f"banned **{user.name}**")
                    return await message.edit(
                        embed=discord.Embed(
                            description=f"{ctx.author.mention}: {user.mention} has been **Banned**",
                            color=self.bot.color,
                        )
                    )
        try:
            await ctx.guild.ban(user, reason=f"{reason} | {ctx.author.id}")
            await ctx.success(f"{user.mention} has been **Banned**")
        except discord.Forbidden:
            return await ctx.warning(
                "I don't have the **necessary permissions** to ban that member."
            )
            raise InvalidError()
        except discord.NotFound:
            await ctx.fail(f"{user.name} is already **banned** from the server.")
            raise InvalidError()
        await self.moderator_logs(ctx, f"banned **{user.name}**")

    async def do_unban(self, ctx, u: discord.Member | discord.User | str):
        if isinstance(u, discord.User):
            pass  # type: ignore
        elif isinstance(u, discord.Member):
            pass  # type: ignore
        else:
            async for ban in ctx.guild.bans():
                if ban.user.name == u or ban.user.global_name == u:
                    return await ctx.guild.unban(discord.Object(ban.user.id))
            return None
        return await ctx.guild.unban(discord.Object(u.id))

    @commands.command(name="unban", brief="Unban a banned user from the guild")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban_member(self, ctx, user_id: int | str):
        guild = ctx.guild
        try:
            if isinstance(user_id, int):
                banned_entry = await guild.fetch_ban(discord.Object(id=user_id))
                if banned_entry:
                    await guild.unban(banned_entry.user)
                    await ctx.success(
                        f"{banned_entry.user.mention} has been **unbanned**"
                    )
                else:
                    return await ctx.fail("That User is **not banned**")
            else:
                await self.do_unban(ctx, user_id)
                return await ctx.success(f"`{user_id}` **user** has been **unbanned**")
        except discord.Forbidden:
            await ctx.warning(
                "I don't have the **necessary permissions** to **unban** members."
            )
            raise InvalidError()
        except discord.NotFound:
            await ctx.fail("That User is **not banned**")
            raise InvalidError()
        return await self.moderator_logs(ctx, f"unbanned **{banned_entry.user.name}**")

    @commands.command(
        name="kick", aliases=["deport"], brief="Kick a user from the guild"
    )
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def kick_member(self, ctx, user: discord.Member):
        if not (r := await self.bot.hierarchy(ctx, user)):
            return r

        if user.premium_since:
            message = await ctx.send(
                embed=discord.Embed(
                    description=f"{user.mention} is **boosting this server**, would you like to **kick?**",
                    color=self.bot.color,
                )
            )
            await message.edit(
                view=(view := Confirmation(message=message, invoker=ctx.author))
            )
            await view.wait()
            if not view.value:
                await message.edit(
                    embed=discord.Embed(
                        description=f"{ctx.author.mention}: kicking **cancelled**",
                        color=self.bot.color,
                    )
                )
                raise InvalidError()
            else:
                await ctx.guild.kick(
                    user, reason=f"invoked by author | {ctx.author.id}"
                )
                await self.moderator_logs(ctx, f"kicked **{user.name}**")
                return await message.edit(
                    embed=discord.Embed(
                        description=f"{ctx.author.mention}: **kicked** {user.mention}",
                        color=self.bot.color,
                    )
                )
        try:
            await ctx.guild.kick(user, reason=f"invoked by author | {ctx.author.id}")
            await ctx.success(f"**kicked** {user.mention}")
        except discord.Forbidden:
            await ctx.warning(
                "I don't have the **necessary permissions** to kick that member."
            )
            raise InvalidError()
        except discord.NotFound:
            await ctx.fail(f"**{user.name}** is already **kicked** from the server.")
            raise InvalidError()
        return await self.moderator_logs(ctx, f"kicked **{user.name}**")

    @staticmethod
    def convert_duration(duration):
        time_convert = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        match = re.match(r"(\d+)([smhd])", duration)
        if not match:
            return None
        duration_value = int(match.group(1))
        duration_unit = match.group(2)

        if duration_unit in time_convert:
            total_duration = duration_value * time_convert[duration_unit]
            return total_duration
        return None

    @staticmethod
    def format_duration(duration_seconds):
        duration = datetime.timedelta(seconds=duration_seconds)
        minutes, seconds = divmod(duration.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        duration_text = ""
        if duration.days > 0:
            duration_text += f"{duration.days} days, "
        if hours > 0:
            duration_text += f"{hours} hours, "
        if minutes > 0:
            duration_text += f"{minutes} minutes, "
        if seconds > 0:
            duration_text += f"{seconds} seconds"
        return duration_text.rstrip(", ")

    @commands.command(
        name="muted",
        aliases=["mutes"],
        brief="show muted members and the duration left for their mute",
        example=",muted",
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    async def muted(self, ctx: Context):
        from humanize import naturaltime

        members = [
            f"{m.mention} - {naturaltime(m.timed_out_until).strip(' from now')}"
            for m in ctx.guild.members
            if m.is_timed_out()
        ]
        if len(members) == 0:
            return await ctx.fail("There are no **muted members**")
        rows = []
        for i, m in enumerate(members, start=1):
            rows.append(f"`{i}` {m}")
        return await self.bot.dummy_paginator(
            ctx, discord.Embed(title="Muted members", color=self.bot.color), rows
        )

    @commands.command(
        name="mute",
        aliases=["timeout", "shutup"],
        brief="Mute a member in the guild for a duration",
        example=",mute @c_5n 30m",
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(manage_roles=True)
    async def timeout(self, ctx, member: discord.Member, *, time: str):
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        else:
            try:
                converted = humanfriendly.parse_timespan(time)
            except Exception:
                converted = humanfriendly.parse_timespan(
                    f"{await self.get_int(time)} minutes"
                )
            tf = humanize.naturaldelta(datetime.timedelta(seconds=converted))
            try:
                if converted >= 2419200:
                    return await ctx.fail("you can only mute for up to **28 days**")
                mute_time = discord.utils.utcnow() + datetime.timedelta(
                    seconds=converted
                )
            except OverflowError:
                return await ctx.fail(
                    "time length is to high, maximum mute time of **28 days**"
                )
            await member.edit(
                timed_out_until=mute_time, reason=f"muted by {str(ctx.author)}"
            )
            datetime.datetime.now() + datetime.timedelta(seconds=converted)  # type: ignore
            await ctx.success(f"{member.mention} has been **muted** for **{tf}**")
            await self.moderator_logs(ctx, f"muted **{member.name}**")

    async def do_jail(self, ctx: Context, member: discord.Member):
        jailed = discord.utils.get(ctx.guild.roles, name="jailed")
        if not jailed:
            raise CommandError(
                f"role for **jail** not found please run `{ctx.prefix}setme`"
            )
        if await self.bot.db.fetchval(  # type: ignore
            """SELECT roles FROM jailed WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        ):
            if jailed not in member.roles:
                await member.add_roles(jailed)
        else:
            roles = [m for m in member.roles if m.is_assignable()]
            ids = [r.id for r in roles]
            ids_str = ",".join(str(i) for i in ids)
            await self.moderator_logs(ctx, f"jailed **{member.name}**")
            await self.bot.db.execute(
                """INSERT INTO jailed (guild_id, user_id, roles) VALUES ($1, $2, $3)""",
                ctx.guild.id,
                member.id,
                ids_str,
            )
            after_roles = [r for r in member.roles if not r.is_assignable()]
            after_roles.append(jailed)
            await member.edit(roles=after_roles, reason=f"jailed by {ctx.author.name}")
            return True

    async def do_unjail(self, ctx: Context, member: discord.Member):
        jailed = discord.utils.get(ctx.guild.roles, name="jailed")
        if not jailed:
            raise CommandError(
                f"role for **jail** not found please run `{ctx.prefix}setme`"
            )
        if check := await self.bot.db.fetchval(
            """SELECT roles FROM jailed WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        ):
            if jailed in member.roles:
                roles = [ctx.guild.get_role(int(r)) for r in check.split(",")]
                member_roles = [r for r in member.roles if r != jailed]
                roles.extend(member_roles)
                await member.edit(roles=roles, reason=f"unjailed by {ctx.author.name}")
                await self.bot.db.execute(
                    """DELETE FROM jailed WHERE guild_id = $1 AND user_id = $2""",
                    ctx.guild.id,
                    member.id,
                )
                return await self.moderator_logs(ctx, f"unjailed **{member.name}**")
        else:
            raise CommandError(f"{member.mention} isn't **jailed**")

    @commands.command(
        name="jail", brief="jail a member", example=",jail @c_5n laddering"
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(moderate_members=True)
    async def jail(self, ctx: Context, *, member: Member):
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        role = discord.utils.get(ctx.guild.roles, name="jailed")
        if role is None:
            return await ctx.fail("**jailed** role is not found")
        if role.position > ctx.guild.me.top_role.position:
            return await ctx.fail("**jailed** role is higher than my **top role**")
        if role.position > ctx.author.top_role.position:
            return await ctx.fail("**jailed** role is higher than your **top role**")
        if role in member.roles:
            return await ctx.fail(f"{member.mention} is already **jailed**")
        await self.do_jail(ctx, member)
        await ctx.success(f"{member.mention} has been **jailed**")
        return

    @commands.group(
        name="setup",
        aliases=["setme"],
        brief="Setup all moderation roles",
        example=",setup",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(administrator=True)
    @lock(key="setme:{ctx.guild.id}")
    async def setup(self, ctx: Context):
        # with suppress(NotFound):
        # if irole := discord.utils.get(ctx.guild.roles, name="imute"):
        #     imute_role = irole
        # else:
        #     imute_role = await ctx.guild.create_role(name="imute")
        category = discord.utils.get(ctx.guild.categories, name="wock-mod")
        if not category:
            category = await ctx.guild.create_category_channel(
                name="wock-mod",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        view_channel=False
                    )
                },
            )
        # await imute_role.edit(permissions=discord.Permissions(embed_links = False, attach_files = False))
        if jrole := discord.utils.get(ctx.guild.roles, name="jailed"):
            jail_role = jrole
        else:
            jail_role = await ctx.guild.create_role(name="jailed")
        # if rrole := discord.utils.get(ctx.guild.roles, name="rmute"):
        #     rmute_role = rrole
        # else:
        #     rmute_role = await ctx.guild.create_role(name="rmute")
        if logs_channel := discord.utils.get(ctx.guild.channels, name="logs"):
            logs = logs_channel
        else:
            logs = await ctx.guild.create_text_channel(
                name="logs",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        view_channel=False
                    )
                },
            )
        await logs.edit(category=category)
        jail_channel = None
        for channel in ctx.guild.text_channels:
            if "jail" in channel.name.lower():
                if jail_channel is None:
                    await channel.set_permissions(
                        jail_role, view_channel=True, send_messages=True
                    )
                    await channel.set_permissions(
                        ctx.guild.default_role,
                        view_channel=False,
                        send_messages=False,
                    )
                    jail_channel = channel
            else:
                await channel.set_permissions(
                    jail_role, view_channel=False, send_messages=False
                )
            # await channel.set_permissions(rmute_role, add_reactions=False)
            # await channel.set_permissions(
            #     imute_role, embed_links=False, attach_files=False
            # )
            # await channel.set_permissions(
            #     imute_role, embed_links=False, attach_files=False
            # )
        if jail_channel is None:
            jail_channel = await ctx.guild.create_text_channel(name="jail")
            await jail_channel.set_permissions(
                jail_role, view_channel=True, send_messages=True
            )
            await jail_channel.set_permissions(
                ctx.guild.default_role, view_channel=False, send_messages=False
            )
        await jail_channel.edit(category=category)
        await self.bot.db.execute(
            """INSERT INTO moderation_channel (guild_id, category_id, channel_id) VALUES($1, $2, $3) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id, category_id = excluded.category_id""",
            ctx.guild.id,
            category.id,
            logs.id,
        )
        return await ctx.success("successfully setup the **moderation module**")

    @setup.command(name="reset", brief="Reset the jail setup", example=",setup reset")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    @lock(key="setme:{ctx.guild.id}")
    async def setup_reset(self, ctx: Context):
        for user_id in await self.bot.db.fetch(
            """SELECT user_id FROM jailed WHERE guild_id = $1""", ctx.guild.id
        ):
            if member := ctx.guild.get_member(user_id):
                await self.do_unjail(ctx, member)
        await self.bot.db.execute(
            """DELETE FROM jailed WHERE guild_id = $1""", ctx.guild.id
        )

        for r in ["rmute", "imute", "jailed"]:
            _role = discord.utils.get(ctx.guild.roles, name=r)
            if _role:
                await _role.delete(reason=f"Moderation Reset by {ctx.author.name}")
        channel = discord.utils.get(ctx.guild.channels, name="jail")
        if ch := await self.bot.db.fetchrow(
            """SELECT channel_id, category_id FROM moderation_channel WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            if _channel := self.bot.get_channel(int(ch["channel_id"])):
                await _channel.delete(reason=f"setup reset by {str(ctx.author)}")
            if category := self.bot.get_channel(int(ch["category_id"])):
                await category.delete(reason=f"setup reset by {str(ctx.author)}")
        await self.bot.db.execute(
            """DELETE FROM moderation_channel WHERE guild_id = $1""", ctx.guild.id
        )

        if channel:
            await channel.delete(reason=f"Moderation Reset by {ctx.author.name}")
        return await ctx.success("moderation configuration has been **reset**")

    @commands.command(name="jailed", brief="show jailed members", example=",jailed")
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def jailed(self, ctx: Context):
        jailed = await self.bot.db.fetch(
            """SELECT user_id FROM jailed WHERE guild_id = $1""", ctx.guild.id
        )
        if not jailed:
            return await ctx.fail("no **jailed** members")
        rows = []
        for i, member in enumerate(jailed, start=1):
            if not isinstance(member, int):
                member = member["user_id"]
            if user := self.bot.get_user(member):
                rows.append(f"`{i}` **{user.name}**")
            else:
                user = await self.bot.fetch_user(member)
                rows.append(f"`{i}` **{user.name}**")
        return await self.bot.dummy_paginator(
            ctx,
            discord.Embed(title="jailed members", color=self.bot.color),
            rows,
            type="members",
        )

    @commands.group(
        name="unjail",
        brief="unjail a jailed member",
        example=",unjail @c_5n",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    async def unjail(self, ctx: Context, *, member: Member):
        await self.do_unjail(ctx, member)
        return await ctx.success(f"unjailed {member.mention}")

    @unjail.command(
        name="all", brief="unjail all jailed members", example=",unjail all"
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def unjail_all(self, ctx: Context):
        jailed = await self.bot.db.fetch(
            """SELECT user_id FROM jailed WHERE guild_id = $1""", ctx.guild.id
        )
        if not jailed:
            return await ctx.fail("no **jailed** members")
        for i in jailed:
            member = ctx.guild.get_member(i)
            if member:
                await self.do_unjail(ctx, member)
        return await ctx.success("unjailed all **jailed** members")

    @commands.command(
        name="unmute",
        aliases=[
            "untime",
            "untimeout",
        ],
        brief="Unmute a user in the guild",
        example=",unmute @c_5n",
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(manage_roles=True)
    async def untime(self, ctx, member: discord.Member):
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        if member.timed_out_until is None:
            await ctx.fail(f"{member.mention} is not currently **muted**")
            return
        await member.edit(timed_out_until=None)
        await ctx.success(f"{member.mention} has been **unmuted**.")
        await self.moderator_logs(ctx, f"unmuted **{member.name}**")

    @commands.command(
        name="forcenick",
        aliases=["nick"],
        brief="Force/Remove the force of a users nickname in a guild",
        example="forcenick @c_5n catboy",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def forcenick(self, ctx, member: discord.Member, *, name: str = None):
        if name is None:
            if guild_data := self.bot.cache.forcenick.get(ctx.guild.id):
                if guild_data.get(member.id):  # type: ignore
                    await self.bot.db.execute(
                        """DELETE FROM forcenick WHERE guild_id = $1 AND user_id = $2""",
                        ctx.guild.id,
                        member.id,
                    )
                    self.bot.cache.forcenick[ctx.guild.id].pop(member.id)
                    await member.edit(nick=None, reason="forcenicked")
                    return await ctx.success(
                        f"**Unlocked** {member.mention}'s nickname"
                    )
        else:
            if guild_data := self.bot.cache.forcenick.get(ctx.guild.id):
                if guild_data.get(member.id):  # type: ignore
                    await self.bot.db.execute(
                        """INSERT INTO forcenick (guild_id,user_id,nick) VALUES($1,$2,$3) ON CONFLICT (guild_id,user_id) DO UPDATE SET nick = excluded.nick""",
                        ctx.guild.id,
                        member.id,
                        name,
                    )
                    self.bot.cache.forcenick[ctx.guild.id][member.id] = name
                    ogname = member.display_name
                    await member.edit(nick=name, reason="forcenicked")
                    return await ctx.success(
                        f"**{ogname}** has been **locked** to `{name}`"
                    )
        if name is None:
            await self.bot.db.execute(
                """DELETE FROM forcenick WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
            return await ctx.success(f"**Unlocked** {member.mention}'s forced nickname")
        await self.bot.db.execute(
            """INSERT INTO forcenick (guild_id,user_id,nick) VALUES($1,$2,$3) ON CONFLICT DO NOTHING""",
            ctx.guild.id,
            member.id,
            name,
        )
        if ctx.guild.id not in self.bot.cache.forcenick:
            self.bot.cache.forcenick[ctx.guild.id] = {}
        self.bot.cache.forcenick[ctx.guild.id][member.id] = name
        await member.edit(nick=name, reason="forcenicked")
        return await ctx.success(
            f"**locked** {member.mention}'s nickname to **{name}**"
        )

    @commands.group(name="lock", brief="Lock the channel in a guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx):
        if ctx.invoked_subcommand is None:
            channel = ctx.channel
            permissions = channel.overwrites_for(ctx.guild.default_role)
            permissions.send_messages = False
            permissions.add_reactions = False
            permissions.view_channel = True
            await channel.set_permissions(ctx.guild.default_role, overwrite=permissions)
            if role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM lock_role WHERE guild_id = $1""", ctx.guild.id
            ):
                if role := ctx.guild.get_role(role_id):
                    await channel.set_permissions(role, overwrite=permissions)
            await ctx.success(f"Chat has been **locked** for {channel.mention}")

    @lock.command(name="permit", brief="Permit a user to speak in a locked channel")
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def permit(self, ctx, member: discord.Member):
        channel = ctx.channel
        permissions = channel.overwrites_for(member)
        permissions.send_messages = True
        await channel.set_permissions(member, overwrite=permissions)
        await ctx.success(
            f"{member.mention} can text in {channel.mention} while locked."
        )

    @lock.command(
        name="unpermit",
        brief="Remove a users permissions from speaking in locked channels",
    )
    @commands.bot_has_permissions(manage_channels=True)
    @commands.has_permissions(manage_channels=True)
    async def unpermit(self, ctx, member: discord.Member):
        overwrites = ctx.channel.overwrites
        if member in overwrites:
            overwrite = overwrites[member]
            perms = [p for p, k in dict(overwrite).items() if k is True]
            if len(perms) == 1:
                overwrites.pop(member)
                await ctx.channel.edit(overwrites=overwrites)
            else:
                overwrite.send_messages = None
                overwrites[member] = overwrite
                await ctx.channel.edit(overwrites=overwrites)
        await ctx.success(f"{member.mention} can no longer text in **locked channel**")

    @lock.command(name="role", brief="set the role to be allowed / disallowed to speak")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock_role(self, ctx, *, role: Role):
        role = role[0]
        await self.bot.db.execute(
            """INSERT INTO lock_role (guild_id,role_id) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"**Lock role** has been set to {role.mention}")

    @lock.command(name="reset", brief="Reset the lock role")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock_reset(self, ctx):
        if role_id := await self.bot.db.fetchval(
            """SELECT role_id FROM lock_role WHERE guild_id = $1""", ctx.guild.id
        ):
            if role := ctx.guild.get_role(role_id):
                for channel in ctx.guild.channels:
                    permissions = channel.overwrites_for(role)
                    if permissions.send_messages is False:
                        permissions.send_messages = None
                    elif permissions.send_messages is True:
                        permissions.send_messages = None
                        await channel.set_permissions(role, overwrite=permissions)
                await self.bot.db.execute(
                    """DELETE FROM lock_role WHERE guild_id = $1""", ctx.guild.id
                )
                await ctx.success(f"**Lock role** has been reset")
        else:
            await ctx.success("No roles are set to lock")

    @commands.command(name="unlock", brief="Unlock a locked channel in a guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def unlock(self, ctx):
        channel = ctx.channel
        permissions = channel.overwrites_for(ctx.guild.default_role)
        permissions.send_messages = True
        permissions.add_reactions = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=permissions)
        if role_id := await self.bot.db.fetchval(
            "SELECT role_id FROM lock_role WHERE guild_id = $1", ctx.guild.id
        ):
            if role := ctx.guild.get_role(role_id):
                await channel.set_permissions(role, overwrite=permissions)
        for member in ctx.message.mentions:
            member_permissions = channel.overwrites_for(member)
            member_permissions.send_messages = None
            await channel.set_permissions(member, overwrite=member_permissions)
        await ctx.success(f"Chat has been **unlocked** for {channel.mention}")

    # Most of the commands below this line will be purges, cleaning chat commands, or
    #   simple bot cleanups

    @commands.command(
        name="restore",
        brief="Restore all roles to a user who recently lost roles in a guild",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def restore(self, ctx: Context, *, member: discord.Member):
        if (
            member.top_role.position >= ctx.author.top_role.position
            and ctx.author.id != ctx.guild.owner_id
        ):
            raise discord.ext.commands.errors.CommandError(
                f"{member.mention}'s **top role** is **higher** than yours"
            )
        if check := await self.bot.redis.get(f"r-{ctx.guild.id}-{member.id}"):
            roles = orjson.loads(check)
            roles = [ctx.guild.get_role(r) for r in roles]
            try:
                roles.remove(None)
            except Exception:
                pass
            await member.add_roles(
                *roles, atomic=False, reason=f"invoked by author | {ctx.author.id}"
            )
            return await ctx.success(f"**Restored roles** to {member.mention}")
        else:
            return await ctx.fail(
                f"There are **no roles** to restore to {member.mention}"
            )

    @commands.command(name="strip", brief="Remove all roles from a user in a guild")
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(administrator=True)
    async def strip(self, ctx: Context, *, member: discord.Member):
        if (
            member.top_role > ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.fail(f"you couldn't strip {member.mention}")
        if len(member.roles) > 0:
            roles = [
                role
                for role in member.roles
                if role != ctx.guild.premium_subscriber_role
                and role != ctx.guild.default_role
            ]
            roles = [
                r.id
                for r in roles
                if r < ctx.author.top_role and r != ctx.author.top_role
            ]
            if len(roles) == 0:
                return await ctx.fail(f"you couldn't strip {member.mention}")
            await self.bot.redis.set(
                f"r-{ctx.guild.id}-{member.id}", orjson.dumps(roles), ex=9000
            )
            await member.remove_roles(
                *[
                    r
                    for r in member.roles
                    if r != ctx.guild.premium_subscriber_role
                    and r != ctx.guild.default_role
                ],
                atomic=False,
                reason=f"invoked by author | {ctx.author.id}",
            )
            return await ctx.success(
                f"**Stripped** `{len(roles)}` roles from {member.mention}"
            )
        else:
            return await ctx.fail(f"{member.mention} has **no roles**")

    @commands.group(
        name="command", brief="Group for command management", example=",command"
    )
    async def command_group(self, ctx):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @command_group.command(
        name="disable",
        brief="Disable a command for the guild",
        example=",command disable ban",
    )
    @commands.has_permissions(manage_guild=True)
    async def disable_command(self, ctx: commands.Context, *, command: str):
        if command in ["disable", "enable"]:
            raise commands.CommandError(f"You can't disable **{command}**")
        if cmd := self.bot.get_command(command):
            await self.bot.db.execute(
                """INSERT INTO disabled_commands (guild_id, command) VALUES($1,$2) ON CONFLICT DO NOTHING""",
                ctx.guild.id,
                cmd.qualified_name.lower(),
            )
            await ctx.success(f"`{command}` has been **disabled**")
        else:
            await ctx.fail(f"`{command}` doesn't exist as a command")

    @command_group.command(
        name="enable",
        brief="Enable a command for a guild",
        example=",command enable ban",
    )
    @commands.has_permissions(manage_guild=True)
    async def enable_command(self, ctx: commands.Context, *, command: str):
        if command in ["disable", "enable"]:
            raise commands.CommandError(f"`{command}` can **not** be **disabled**")
        if cmd := self.bot.get_command(command):
            await self.bot.db.execute(
                """DELETE FROM disabled_commands WHERE guild_id = $1 AND command = $2""",
                ctx.guild.id,
                cmd.qualified_name.lower(),
            )
            await ctx.success(f"`{command}` has been **enabled**")
        else:
            await ctx.fail(f"`{command}` doesn't exist as a command")

    async def purge_messages(self, ctx: Context, **kwargs):
        async with self.locks[ctx.channel.id]:
            await ctx.channel.purge(**kwargs)

    def chunk_list(self, data: list, amount: int) -> list[list]:
        # makes lists of a big list of values every x amount of values
        if len(data) < amount:
            _chunks = [data]
        else:
            chunks = zip(*[iter(data)] * amount)
            _chunks = list(list(_) for _ in chunks)
        from itertools import chain

        l = list(chain.from_iterable(_chunks))  # noqa: E741
        nul = [d for d in data if d not in l]
        if len(nul) > 0:
            _chunks.append(nul)
        return _chunks

    async def fast_purge(self, ctx: Context, amount: int, messages: list):
        async with self.locks[ctx.channel.id]:
            if amount > 100:
                chunks = self.chunk_list(messages, 100)
                for chunk in chunks:
                    await ctx.channel.delete_messages(chunk)
                    await asyncio.sleep(1)
            else:
                await ctx.channel.delete_messages(messages)

    async def cleanup_bot_messages(self, ctx: Context, amount: int = 100):
        async with self.locks[ctx.channel.id]:
            now = discord.utils.utcnow() - datetime.timedelta(days=14)
            messages = [
                _
                async for _ in ctx.channel.history()
                if _.author.bot and int(_.created_at.timestamp()) > int(now.timestamp())
            ]
            if len(messages) == 0:
                await ctx.fail("no messages found from bots", delete_after=5)
                return False
            messages = messages[: amount - 1]
            if amount > 100:
                chunks = self.chunk_list(messages, 100)
                for chunk in chunks:
                    await asyncio.sleep(0.5)
                    await ctx.channel.delete_messages(messages=chunk)
                del chunks
            else:
                await ctx.channel.delete_messages(messages=messages)
            return await ctx.success(
                f"Cleaned **{len(messages)}** messages from bots", delete_after=5
            )

    async def delete_message_list(
        self, ctx: Context, amount: int, check: Optional[Callable] = None
    ):
        async with self.locks[ctx.channel.id]:
            now = discord.utils.utcnow() - datetime.timedelta(days=14)
            messages = [
                _
                async for _ in ctx.channel.history()
                if int(_.created_at.timestamp()) > int(now.timestamp())
                and check(_) is True
            ]
            if len(messages) == 0:
                return None
            messages = messages[:amount]
            if len(messages) > 100:
                chunks = self.chunk_list(messages, 100)
                for chunk in chunks:
                    await ctx.channel.delete_messages(messages=chunk)
            else:
                await ctx.channel.delete_messages(messages=messages)

    @commands.command(
        name="botclear",
        aliases=["bc"],
        brief="clean messages from bots",
        example=",botclear 100",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def botclear(self, ctx: Context, amount: int = 100):
        return await self.cleanup_bot_messages(ctx, amount)

    @commands.group(
        name="purge",
        aliases=["clear", "c"],
        invoke_without_command=True,
        brief="Mass delete messages in a guild",
        example=",purge @o_5v 100",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: Context,
        member: typing.Optional[discord.Member] = None,
        limit: int = 10,
    ):
        async with timeit():  # type: ignore
            limit = limit + 1
            if ctx.invoked_subcommand is None:
                if member:
                    now = discord.utils.utcnow() - datetime.timedelta(days=14)
                    messages = [
                        m
                        async for m in ctx.channel.history()
                        if m.author.id == member.id
                        and m != ctx.message
                        and int(m.created_at.timestamp()) > int(now.timestamp())
                    ]
                    if len(messages) == 0:
                        return await ctx.fail("no messages found")
                else:
                    now = discord.utils.utcnow() - datetime.timedelta(days=14)
                    messages = [
                        m
                        async for m in ctx.channel.history()
                        if m != ctx.message
                        and int(m.created_at.timestamp()) > int(now.timestamp())
                    ]
                    if len(messages) == 0:
                        return await ctx.fail("no messages found")
                if len(messages) > 0:
                    messages = messages[:limit]
                    await ctx.message.delete()
                    await self.fast_purge(ctx, limit, messages)
                    pass

    @purge.command(
        name="bots",
        invoke_without_command=True,
        brief="purge bot messages",
        example=",purge bots 100",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge_bots(self, ctx: Context, amount: int = 100):
        return await self.cleanup_bot_messages(ctx, amount)

    @purge.command(
        name="webhooks",
        invoke_without_command=True,
        brief="Mass delete webhook messages in a guild",
        example=",purge webhooks 10",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge_webhooks(self, ctx: Context, limit: int = 10):
        if ctx.invoked_subcommand is None:
            names = [webhook.name for webhook in await ctx.channel.webhooks()]
            now = discord.utils.utcnow() - datetime.timedelta(days=14)
            messages = [
                m
                async for m in ctx.channel.history()
                if m.author.name not in names
                and m.author.bot
                and int(m.created_at.timestamp()) > int(now.timestamp())
            ]
            messages = messages[:limit]
            if len(messages) > 0:
                await self.fast_purge(ctx, limit, messages)
                pass

    @purge.command(
        name="reactions",
        invoke_without_command=True,
        brief="Mass delete reactions in a guild",
        example=",purge reactions 20",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge_reactions(self, ctx: Context, limit: int = 10):
        async with self.locks[ctx.channel.id]:
            now = discord.utils.utcnow() - datetime.timedelta(days=14)
            messages = [
                m
                async for m in ctx.channel.history()
                if len(m.reactions) > 0
                and int(m.created_at.timestamp()) > int(now.timestamp())
            ]
            if len(messages) > 0:
                messages = messages[:limit]
                await asyncio.gather(*[m.clear_reactions() for m in messages])
            await ctx.message.delete()

    @purge.command(
        name="emojis",
        invoke_without_command=True,
        brief="Mass delete Emojis sent in a guild",
        example=",purge emojis 100",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge_emojis(self, ctx, limit: int = 10):
        if ctx.invoked_subcommand is None:

            def check(message: discord.Message):
                if message.created_at < (
                    discord.utils.utcnow() - datetime.timedelta(days=14)
                ):
                    return False

                f = re.compile(
                    r"<(?P<animated>a)?:(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>"
                )
                ma = list(match[2] for match in f.findall(message.content))
                if ma:
                    return True
                return False

            await ctx.message.delete()
            await self.delete_message_list(ctx, limit, check)

    @commands.command(
        name="cleanup",
        aliases=["botclean", "cu"],
        brief="Cleans up all bot messages from the channel",
        example=",cleanup",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def cleanup(self, ctx):
        bot_messages = []
        async for message in ctx.channel.history(
            limit=200
        ):  # Increase the limit if needed
            if message.author == self.bot.user or message.content.startswith(
                ctx.prefix
            ):
                bot_messages.append(message)
                if len(bot_messages) == 100:
                    break
        bot_messages.append(ctx.message)
        #        if messag
        await ctx.channel.delete_messages(set(bot_messages))
        message = await ctx.send("👍🏼")
        await message.delete()


async def setup(bot: "Wock") -> None:
    await bot.add_cog(Moderation(bot))
