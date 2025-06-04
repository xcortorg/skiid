import asyncio
import datetime
import humanize
import re
import typing
import string
import aiohttp
import discord
import orjson
import asyncpg
import humanfriendly
from discord.ext import commands
from discord.ext.commands import Cog, CommandError
from contextlib import suppress
from discord import Member, Embed, NotFound, Thread, User
from collections import defaultdict
from typing import Union, List, Type, Optional, Callable, List, Dict, Any, Literal
from tool.important import Context  # type: ignore
from tool.important.subclasses.command import (  # type: ignore
    Role,
    Member,
    CategoryChannel,
    TextChannel,
    VoiceChannel,
    Argument,
)
import json
from loguru import logger
from tool.views import Confirmation  # type: ignore
from tools import lock, timeit  # type: ignore
from tool.aliases import CommandConverter  # type: ignore
from dataclasses import dataclass, field
from fast_string_match import closest_match
from num2words import num2words
from enum import Enum, auto
from pydantic import BaseModel
import uuid
from asyncpg import exceptions
from tool.important.subclasses.parser import EmbedConverter
from datetime import timedelta
from math import ceil


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
    warns = auto()


def create_dataclass(class_name: str, fields: List[str]) -> Type:
    """
    Dynamically creates a dataclass with given field names, making all fields optional.

    :param class_name: Name of the dataclass to be created.
    :param fields: List of field names for the dataclass.
    :return: A new dataclass type.
    """
    # Create annotations where each field is Optional[str] and default is None
    annotations: Dict[str, Type[Optional[str]]] = {
        field_name: Optional[str] for field_name in fields
    }

    # Create a dictionary of default values (None) for each field
    defaults = {field_name: field(default=None) for field_name in fields}

    # Create the dataclass dynamically
    dynamic_dataclass = dataclass(
        type(class_name, (object,), {"__annotations__": annotations, **defaults})
    )

    return dynamic_dataclass


def make_dataclass(class_name: str, count: int) -> Type:
    numbers = [
        num2words(i, to="ordinal").replace("-", "_") for i in range(1, (count + 1))
    ]
    return create_dataclass(class_name, numbers)


class InvalidError(TypeError):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class GuildChannel(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        # Check if the argument is a channel ID
        if argument.isdigit():
            channel = ctx.guild.get_channel(int(argument))
            if channel and isinstance(channel, discord.abc.GuildChannel):
                return channel

        match = re.match(r"<#(\d+)>", argument)
        if match:
            channel_id = int(match.group(1))
            channel = ctx.guild.get_channel(channel_id)
            if channel and isinstance(channel, discord.abc.GuildChannel):
                return channel

        channels = {
            c.name.lower(): c.id
            for c in ctx.guild.channels
            if isinstance(c, discord.abc.GuildChannel)
        }
        if match := closest_match(argument.lower(), list(channels.keys())):
            return ctx.guild.get_channel(channels[match])

        raise commands.CommandError(f"Channel `{argument}` not found")


class Args:
    def __init__(self, count: Optional[int] = 2):
        self.count = count

    async def convert(self, ctx: Context, argument: str):
        if "," in argument:
            args = [i.strip() for i in argument.split(",", (self.count - 1))]
        else:
            if argument.count(" ") == 1:
                args = argument.split(" ", (self.count - 1))
            else:
                raise commands.CommandError("please include a `,` between arguments")
        return_type = make_dataclass("Arguments", self.count)
        return return_type(*args)


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


class RandomConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        args = await Argument().convert(ctx, argument)
        return args


class Restriction(commands.Converter):
    async def convert(
        self, ctx: Context, argument: str
    ) -> Optional[CommandRestriction]:
        args = await Argument().convert(ctx, argument)
        command = await CommandConverter().convert(ctx, args.first)
        role = await Role(assign=False).convert(ctx, args.second)
        return CommandRestriction(command=command, role=role[0])


if typing.TYPE_CHECKING:
    from tool.greed import Greed  # type: ignore


class Moderation(Cog):
    def __init__(self, bot: "Greed") -> None:
        self.bot = bot
        self.user_id = 930383131863842816
        self.locks = defaultdict(asyncio.Lock)
        self.tasks = {}

    async def invoke_msg(
        self,
        ctx: Context,
        member: Union[User, Member],
        message: Optional[discord.Message] = None,
    ):
        """Send a custom invoke message if configured, return True if sent, False otherwise"""
        if not (
            msg := await self.bot.db.fetchval(
                """SELECT message FROM invoke WHERE guild_id = $1 AND cmd = $2""",
                ctx.guild.id,
                ctx.command.qualified_name.lower(),
            )
        ):
            return False

        kw = {"message": message} if message else {}
        await self.bot.send_embed(ctx.channel, msg, user=member, **kw)
        return True

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
            members = ctx.guild.members
            members = [
                m
                for m in ctx.guild.members
                if m.top_role < ctx.guild.me.top_role
                if (m.bot if bots else not m.bot)
                and (role in m.roles if remove else role not in m.roles)
                and (role.mentionable if mentionable else True)
            ]
            if not members:
                return await message.edit(
                    embed=discord.Embed(
                        color=self.bot.color,
                        description=f"No users found to {'remove' if remove else 'add'} {role.mention} {'from' if remove else 'to'}",
                    )
                )

            chunk_size = 10
            member_chunks = [
                members[i : i + chunk_size] for i in range(0, len(members), chunk_size)
            ]
            processed = 0

            for chunk in member_chunks:
                tasks = [
                    (
                        member.remove_roles(
                            role, reason=f"Mass role removal by {ctx.author}"
                        )
                        if remove
                        else member.add_roles(
                            role, reason=f"Mass role addition by {ctx.author}"
                        )
                    )
                    for member in chunk
                ]
                await asyncio.gather(*tasks, return_exceptions=True)
                processed += len(chunk)

                if processed % 50 == 0:
                    await message.edit(
                        embed=discord.Embed(
                            color=self.bot.color,
                            description=f"Progress: {processed}/{len(members)} members processed...",
                        )
                    )

            await message.edit(
                embed=discord.Embed(
                    color=self.bot.color,
                    description=f"Successfully {'removed' if remove else 'added'} {role.mention} {'from' if remove else 'to'} {processed} members",
                )
            )

            self.tasks.pop(f"role-all-{ctx.guild.id}", None)

    async def disable_slowmode(self, sleep_time: int, channel: discord.TextChannel):
        await asyncio.sleep(sleep_time)
        await channel.edit(slowmode_delay=0)
        return True

    async def setup_database(self):
        """Ensure the report_whitelist table exists."""
        try:
            # This query will create the table if it doesn't exist
            await self.bot.db.execute(
                """CREATE TABLE IF NOT EXISTS report_whitelist (
                    user_id BIGINT PRIMARY KEY
                )"""
            )
            logger.info("Report whitelist table is ready.")
        except Exception as e:
            logger.info(f"Error creating table: {e}")

    async def moderator_logs(self, ctx: Context, description: str):
        try:
            await self.bot.db.execute(
                """INSERT INTO moderation_logs (id, guild_id, user_id, action_type, created_at) VALUES ($1, $2, $3, $4, $5)""",
                ctx.message.id,
                ctx.guild.id,
                ctx.author.id,
                description,
                datetime.datetime.now(),
            )
        except exceptions.UniqueViolationError:
            logger.info(
                f"Record with id {ctx.message.id} already exists. Skipping insertion."
            )
        return

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ensure the bot doesn't respond to itself and only listens to your messages
        if message.author.bot or message.author.id != self.user_id:
            return

        # Match the exact phrase format "I sentence @user to jail"
        pattern = r"I sentence <@!?(\d+)> to jail"
        match = re.fullmatch(pattern, message.content.strip())

        if match:
            user_id = int(match.group(1))
            member = message.guild.get_member(user_id)

            if not member:
                return

            # Check if user is protected
            user_ids = (
                await self.bot.db.fetchval(
                    "SELECT user_ids FROM protected WHERE guild_id = $1",
                    message.guild.id,
                )
                or []
            )
            if member.id in user_ids:
                await self.send_fail(
                    message.channel,
                    f"You cannot **jail** {member.mention} as they are **protected**",
                )
                return

            # Fetch jail role
            jail_data = await self.bot.db.fetchrow(
                "SELECT role_id FROM jail_config WHERE guild_id = $1", message.guild.id
            )
            if not jail_data:
                await self.send_fail(message.channel, "**Jailed** role not configured")
                return

            role = message.guild.get_role(jail_data["role_id"])
            if not role:
                await self.send_fail(message.channel, "**Jailed** role not found")
                return

            if role in member.roles:
                await self.send_fail(
                    message.channel, f"{member.mention} is already **jailed**"
                )
                return

            # Jail the user
            try:
                await member.add_roles(role, reason="Sentenced to jail")
                await self.send_success(
                    message.channel, f"{member.mention} has been **jailed**"
                )
            except discord.Forbidden:
                await self.send_fail(
                    message.channel, "I do not have permission to jail this user."
                )

    async def send_success(self, channel, message):
        embed = discord.Embed(description=f"{message}", color=self.bot.color)
        await channel.send(embed=embed)

    async def send_fail(self, channel, message):
        embed = discord.Embed(description=f"{message}", color=self.bot.color)
        await channel.send(embed=embed)

    @commands.command(
        description="pin a message by replying to it",
        brief="manage messages",
        usage="[message id]",
    )
    @commands.has_permissions(manage_messages=True)
    async def pin(self, ctx: commands.Context, message_id: int = None):

        if ctx.message.reference:
            message_id = ctx.message.reference.message_id

        if not message_id:
            await ctx.warning(
                "You need to provide a **message ID** or **reply** to the message"
            )
            return

        message = await ctx.channel.fetch_message(message_id)

        await message.pin()
        await ctx.success(f"pinned message.")

    @commands.command(
        description="unpin a message by replying to it",
        brief="manage messages",
        usage="[message id]",
    )
    @commands.has_permissions(manage_messages=True)
    async def unpin(self, ctx: commands.Context, message_id: int = None):

        if ctx.message.reference:
            message_id = ctx.message.reference.message_id

        if not message_id:
            await ctx.warning(
                "You need to provide a **message ID** or **reply** to the message"
            )
            return

        message = await ctx.channel.fetch_message(message_id)

        await message.unpin()
        await ctx.success(f"unpinned message.")

    @commands.command(
        description="Make a channel NSFW for 10 seconds",
        brief="Manage channels",
        usage="[chan]",
        aliases=["nsfw"],
    )
    @commands.has_permissions(manage_channels=True)
    async def naughty(self, ctx):
        channel: discord.TextChannel = ctx.channel

        # Check if the channel is already NSFW
        if channel.is_nsfw():
            return await ctx.warning("The channel is already marked as NSFW.")

        # Create an embed to prompt the user for confirmation
        embed = discord.Embed(
            title="NSFW Channel Confirmation",
            description=(
                "Do you want to make this channel NSFW\n"
                "The channel will be deleted after the time limit or if manually changed back to SFW. "
                "**(yes/no)**"
            ),
            color=self.bot.color,
        )

        # Send the embed
        await ctx.send(embed=embed)

        # Define a check for the response to be from the same user, with "yes" or "no" as valid inputs
        def check(message):
            return message.author == ctx.author and message.content.lower() in [
                "yes",
                "no",
            ]

        try:
            # Wait for the user's response
            response = await self.bot.wait_for("message", check=check, timeout=30.0)

            if response.content.lower() == "yes":
                try:
                    # Make the channel NSFW
                    await channel.edit(nsfw=True, reason=f"requested by {ctx.author}")
                    await ctx.success(
                        f"The channel {channel.mention} has been marked as NSFW for 10 minutes."
                    )

                    # Wait for either the timeout or manual change to SFW
                    await self.wait_for_channel_reset(channel, ctx)

                except discord.Forbidden:
                    await ctx.warning(
                        "I don't have the required permissions to manage channels."
                    )
            else:
                await ctx.fail(
                    "Cancelled the action. The channel will not be marked as NSFW."
                )

        except asyncio.TimeoutError:
            await ctx.fail("You took too long to respond. Action cancelled.")

    async def wait_for_channel_reset(self, channel, ctx):
        """Wait for 10 seconds or when the channel is manually changed back to SFW."""
        try:
            # Run both tasks concurrently: wait for the manual channel change OR timeout
            await asyncio.gather(
                self.check_channel_update(channel, ctx),
                self.delete_channel_after_timeout(channel, ctx, timeout=600),
            )

        except asyncio.TimeoutError:
            pass  # Timeout handled elsewhere, you don't need to worry about this exception.

    async def check_channel_update(self, channel, ctx):
        """Check for manual change in channel to non-NSFW."""

        def check_channel_edit(before, after):
            if after.id == channel.id and not after.is_nsfw():
                return True
            return False

        # Wait for the channel update event
        await self.bot.wait_for("on_channel_update", check=check_channel_edit)

    async def delete_channel_after_timeout(self, channel, ctx, timeout):
        """Delete channel after the given timeout."""
        await asyncio.sleep(timeout)  # Wait for the timeout duration.
        # Check again if the channel is still NSFW before deleting.
        if channel.is_nsfw():
            await channel.delete(reason=f"NSFW timer expired for {channel.name}.")
            await ctx.success(
                f"The channel {channel.mention} has been deleted after the NSFW timer ended."
            )

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

    @commands.command(
        name="invoke",
        brief="set or clear an invoke message for a command",
        example=",invoke ban {embed}{description: bye {user.mention}}\n,invoke ban clear",
    )
    @commands.has_permissions(manage_guild=True)
    async def invoke(self, ctx: Context, command: str, *, option: str):
        if not (command := self.bot.get_command(command)):
            raise commands.CommandError("command not found")
        command = command.qualified_name.lower()
        if command.lower() not in (
            "ban",
            "unban",
            "kick",
            "timeout",
            "untimeout",
            "jail",
            "unjail",
        ):
            raise commands.CommandError("that is not a valid moderation command")
        if option.lower() in ("remove", "clear", "cl", "reset", "delete", "del"):
            await self.bot.db.execute(
                """DELETE FROM invoke WHERE guild_id = $1 AND cmd = $2""",
                ctx.guild.id,
                command,
            )
            return await ctx.success(
                f"successfully cleared the invoke message for {command}"
            )
        else:
            await EmbedConverter().convert(ctx, option)
            await self.bot.db.execute(
                """INSERT INTO invoke (guild_id, cmd, message) VALUES($1, $2, $3) ON CONFLICT(guild_id, cmd) DO UPDATE SET message = excluded.message""",
                ctx.guild.id,
                command,
                option,
            )
            return await ctx.success(
                f"successfully set the invoke message for {command}"
            )

    async def setup_mute_roles(self, ctx: Context):
        rmute = discord.PermissionOverwrite(
            add_reactions=False, use_external_emojis=False, use_external_stickers=False
        )
        imute = discord.PermissionOverwrite(embed_links=False, attach_files=False)
        imute_role = discord.utils.get(
            ctx.guild.roles, name="imute"
        ) or await ctx.guild.create_role(name="imute")
        rmute_role = discord.utils.get(
            ctx.guild.roles, name="rmute"
        ) or await ctx.guild.create_role(name="rmute")
        for channel in ctx.guild.channels:
            if not isinstance(channel, (discord.VoiceChannel, discord.StageChannel)):
                if rmute_role not in channel.overwrites:
                    await channel.set_permissions(rmute_role, overwrite=rmute)
                if imute_role not in channel.overwrites:
                    await channel.set_permissions(imute_role, overwrite=imute)
        return True

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
        name="banned",
        brief="view the reason a user is banned",
        example=",banned sudosql",
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
        if channel.is_nsfw() or getattr(channel, "is_community_channel", False):
            return await ctx.fail(
                "This channel cannot be deleted as it is a community channel."
            )
        await ctx.confirm(f"Are you sure you want to **nuke** this channel?")
        position = channel.position
        new = await channel.clone(
            reason=f"nuked by {str(ctx.author)} | {ctx.author.id}"
        )
        if await self.bot.db.fetchrow(
            """SELECT message FROM vanity_status WHERE guild_id = $1 AND channel_id = $2""",
            ctx.guild.id,
            channel.id,
        ):
            await self.bot.db.execute(
                """UPDATE vanity_status SET channel_id = $2 WHERE guild_id = $1""",
                new.id,
                ctx.guild.id,
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
        try:
            await channel.delete(
                reason=f"Channel nuked by {str(ctx.author)} | {ctx.author.id}"
            )
        except discord.HTTPException as e:
            await ctx.fail(str(e))
        await self.moderator_logs(ctx, f"nuked {channel.mention}")
        await new.edit(position=position, reason=f"invoked by author | {ctx.author.id}")
        return await new.send(
            embed=discord.Embed(
                description=f"first",
                color=self.bot.color,
            )
        )

    @commands.command(
        name="reactionmute",
        aliases=["rmute", "reactmute"],
        brief="mute a member from reacting to messages",
        example=",rmute @sudosql toxic",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def reactionmute(self, ctx: Context, *, member: Member):
        role = discord.utils.get(ctx.guild.roles, name="rmute")
        if not role:
            return await ctx.fail(
                f"reaction mute **role** not found please run `{ctx.prefix}setme`"
            )
        if member.guild_permissions.administrator:
            return await ctx.fail(
                f"{member.mention} has administrator so this won't work"
            )
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        if role in member.roles:
            await member.remove_roles(role)
            return await ctx.success(
                f"**reaction mute** for **{member.mention}** has been **REMOVED**"
            )
        else:
            await member.add_roles(role)
            return await ctx.success(
                f"**{member.mention}** has been **reaction muted**"
            )

    @commands.command(
        name="imagemute",
        aliases=["imute", "im", "imgmute"],
        brief="mute a member from sending images",
        example="imute @sudosql nsfw",
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
        if member.guild_permissions.administrator:
            return await ctx.fail(
                f"{member.mention} has administrator so this won't work"
            )
        if role in member.roles:
            await member.remove_roles(role)
            return await ctx.success(
                f"**image mute** for **{member.mention}** has been **REMOVED**"
            )
        else:
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
            f"**{args.command.qualified_name}** has been **restricted** from {args.role.mention}"
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
        brief="reset all comfmand restrictions",
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
        example=",topic general sudosql is the best",
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
            name = member.name
        else:
            member = member[0]
            icon = member.display_icon.url if member.display_icon else None
            permissions = dict(member.permissions)
            name = member.name

        embed = discord.Embed(
            title=f"{name}'s Permissions",
            color=self.bot.color
        )

        if icon:
            embed.set_thumbnail(url=icon)

        if permissions.get("administrator"):
            rows = ["✅ Administrator (Grants all permissions)"]
        else:
            rows = []
            for perm, value in permissions.items():
                if value:
                    formatted_perm = perm.replace('_', ' ').title()
                    rows.append(f"✅ {formatted_perm}")

            if not rows:
                return await ctx.fail(f"**{name}** has no permissions")

        return await self.bot.dummy_paginator(ctx, embed, rows, type="permission")
        return await self.bot.dummy_paginator(ctx, embed, perms, type="permission")
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
        example=",role @sudosql owner",
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

            if (
                ctx.guild.me.top_role < role_input[0]
                and ctx.guild.me.top_role < ctx.author.top_role
            ):
                return await ctx.fail(
                    f"**{role_input[0].mention}** is **higher than me**"
                )

            if not role_input:
                return await ctx.warning("You must **mention a role**")

            removed = []
            added = []
            roles = member.roles
            for role in role_input:
                if ctx.guild.me.guild_permissions.manage_roles is False:
                    return await ctx.fail(
                        f"I do not have permission to **manage** roles"
                    )
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

    @commands.command(name="modstats", brief="see statistics of a moderator")
    async def modstats(
        self, ctx: Context, *, moderator: Optional[Member] = commands.Author
    ):
        if data := await self.store_statistics(ctx, moderator, False):
            data = ModerationStatistics(**data)
            e = discord.Embed(
                color=self.bot.color, title=f"{moderator.name}'s mod stats"
            )
            for key, value in data.dict().items():
                e.add_field(name=key, value=value, inline=True)
            return await ctx.send(embed=e)
        return await ctx.fail(f"no moderation stats stored for {moderator.mention}")

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
                color=0x42B37F,
            )
        )
        await self.moderator_logs(
            ctx, f"<:yes:1342777287615057931> removed {role.mention} from all bots"
        )
        await self.role_all_task(ctx, message, role, True, False, True)
        return

    @commands.after_invoke
    async def after_invoke(self, ctx: Context):
        return await self.store_statistics(ctx, ctx.author)

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
                description=f"<:yes:1342777287615057931> giving {role.mention} to all humans... this may take a while...",
                color=0x42B37F,
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
                description=f"<:yes:1342777287615057931> removing {role.mention} from all humans... this may take a while...",
                color=0x42B37F,
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
        example=",role color 010101, @com",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_color(self, ctx, color: Union[discord.Color, str], *, role: Role):
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
    async def role_create(self, ctx, *, name: str):
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
        brief="Change the icon of a role.",
        example=",role icon <role> <emoji|URL|attachment>",
    )
    @commands.bot_has_permissions(manage_roles=True)
    @commands.has_permissions(manage_roles=True)
    async def role_icon(
        self,
        ctx,
        role_input: str,
        *,
        icon: Union[discord.PartialEmoji, discord.Emoji, str, None] = None,
    ):
        """
        Change the icon of a role with an emoji, URL, or attachment.
        Allows role mention, ID, or name for identifying the role.
        """
        # Resolve role input by mention, ID, or name
        role = None
        if role_input.isdigit():
            # If input is a number, try fetching by ID
            role = ctx.guild.get_role(int(role_input))
        elif role_input.startswith("<@&") and role_input.endswith(">"):
            # If it's a mention, extract the role ID
            role_id = int(role_input[3:-1])
            role = ctx.guild.get_role(role_id)
        else:
            # Fallback to fetching by name (case-insensitive match)
            role = discord.utils.get(ctx.guild.roles, name=role_input)

        if not role:
            return await ctx.fail(
                "Could not find the specified role. Please check your input."
            )

        icon_data = None

        if icon is None:
            # No icon provided, check for attachments
            if not ctx.message.attachments:
                return await ctx.fail(
                    "Provide a **URL**, **attachment**, or **emoji**."
                )

            # Read attachment as icon
            attachment = ctx.message.attachments[0]
            icon_data = await attachment.read()

        elif isinstance(icon, (discord.PartialEmoji, discord.Emoji)):
            # Handle custom emojis
            async with aiohttp.ClientSession() as session:
                async with session.get(icon.url) as resp:
                    if resp.status == 200:
                        icon_data = await resp.read()
                    else:
                        return await ctx.fail("Failed to fetch the emoji image.")

        elif isinstance(icon, str):
            # Handle image URL
            if not icon.startswith(("http://", "https://")):
                return await ctx.fail("Please provide a **valid image URL**.")

            async with aiohttp.ClientSession() as session:
                async with session.get(icon) as resp:
                    if resp.status == 200:
                        icon_data = await resp.read()
                    else:
                        return await ctx.fail("Failed to fetch the image from the URL.")
        else:
            return await ctx.fail("Invalid **input** for a **role icon**.")

        # Attempt to update the role icon
        try:
            await role.edit(
                display_icon=icon_data,
                reason=f"Updated by {ctx.author} ({ctx.author.id})",
            )
            await ctx.success(
                f"The **icon** of {role.mention} has been successfully updated!"
            )
        except discord.HTTPException as e:
            await ctx.fail(f"An error occurred while updating the role icon: {e}")

    @commands.group(name="channel", brief="List of Channel commands")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel(self, ctx):
        if ctx.subcommand_passed is not None:
            return
        return await ctx.send_help(ctx.command)

    def clean_name(self, name: str):
        logger.info(name)
        if "--category" in name:
            return name.split("--category")[0]
        if "—category" in name:
            return name.split("—category")[0]
        if "-category" in name:
            return name.split("-category")[0]
        return name

    @channel.command(
        name="create",
        brief="Create a new channel in a guild",
        parameters={
            "category": {
                "converter": str,
                "description": "the category to make the channel under",
                "default": None,
            }
        },
    )
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel_create(self, ctx, type: str = "text", *, name: str):
        if category := ctx.parameters.get("category"):
            obj = await CategoryChannel().convert(ctx=ctx, argument=category)
            name = self.clean_name(name)
        else:
            obj = ctx.guild
        type = type.lower()
        if "text" in type:
            c = await obj.create_text_channel(
                name=name, reason=f"invoked by author | {ctx.author.id}"
            )
        elif "forum" in type:
            try:
                c = await obj._create_channel(
                    name=name,
                    channel_type=discord.ChannelType.forum,
                    reason=f"invoked by author | {ctx.author.id}",
                )
                c = discord.ForumChannel(
                    state=self.bot._connection, guild=ctx.guild, data=c
                )
            except Exception:
                return await ctx.fail(
                    f"your guild doesn't have access to forum channels"
                )
        elif "media" in type:
            try:
                c = await obj._create_channel(
                    name=name,
                    channel_type=discord.ChannelType.media,
                    reason=f"invoked by author | {ctx.author.id}",
                )
                c = discord.MediaChannel(
                    state=self.bot._connection, guild=ctx.guild, data=c
                )
            except Exception:
                return await ctx.fail(
                    f"your guild doesn't have access to media channels"
                )
        elif "stage" in type:
            try:
                c = await obj._create_channel(
                    name=name,
                    channel_type=discord.ChannelType.stage,
                    reason=f"invoked by author | {ctx.author.id}",
                )
                c = discord.StageChannel(
                    state=self.bot._connection, guild=ctx.guild, data=c
                )
            except Exception:
                return await ctx.fail(
                    f"your guild doesn't have access to stage channels"
                )
        elif "news" in type:
            try:
                c = await obj._create_channel(
                    name=name,
                    channel_type=discord.ChannelType.news,
                    reason=f"invoked by author | {ctx.author.id}",
                )
                c = discord.NewsChannel(
                    state=self.bot._connection, guild=ctx.guild, data=c
                )
            except Exception:
                return await ctx.fail(
                    f"your guild doesn't have access to news channels"
                )
        else:
            c = await obj.create_voice_channel(
                name=name, reason=f"invoked by author | {ctx.author.id}"
            )
        return await ctx.success(f"**Created [#{name}]({c.jump_url}) channel**")

    @channel.command(name="delete", brief="Delete a channel in the current guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def channel_delete(
        self,
        ctx,
        *,
        channel: Union[TextChannel, VoiceChannel, discord.abc.GuildChannel],
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
    async def channel_duplicate(
        self, ctx, *, channel: Union[TextChannel, VoiceChannel]
    ):
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

    async def send_ban_dm(self, user, guild, moderator, reason, ctx):
        """Send an embedded DM to the banned user."""
        embed = discord.Embed(
            title="Banned",
            description=f"You have been banned from **{guild.name}**.",
            color=self.bot.color,
        )
        embed.add_field(
            name="Banned by", value=f"{moderator.mention} ({moderator})", inline=False
        )
        embed.add_field(
            name="Reason", value=reason or "No reason provided.", inline=False
        )
        embed.set_footer(
            text="If you believe this was a mistake, contact the server staff."
        )

        try:
            await user.send(embed=embed)
        except discord.HTTPException:
            # Send a message in the chat if the user could not be DM'd
            await ctx.send(f"could not DM this user.")
            pass  # Ignore if user has DMs disabled

    @commands.command(name="ban", aliases=["exile"], brief="Ban a user from the guild")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def ban_member(self, ctx, user: discord.Member, *, reason=None):
        """Ban a member from the server and send them a DM."""
        if not (r := await self.bot.hierarchy(ctx, user)):
            return r

        user_ids = (
            await self.bot.db.fetchval(
                """SELECT user_ids FROM protected WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if user.id in user_ids:
            raise CommandError(
                f"You cannot **ban** {user.mention} as they are **protected**"
            )

        # Handling user boosting the server
        if isinstance(user, discord.Member) and user.premium_since:
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
                await self.store_statistics(ctx, ctx.author)

                if not await self.invoke_msg(ctx, user, message):
                    await message.edit(
                        embed=discord.Embed(
                            description=f"{ctx.author.mention}: {user.mention} has been **Banned**",
                            color=self.bot.color,
                        )
                    )
                await ctx.message.add_reaction("<:check:1336689145216766015>")
                await self.send_ban_dm(
                    user, ctx.guild, ctx.author, reason, ctx
                )  # Replace with your custom emoji
                return

        try:
            await ctx.guild.ban(user, reason=f"{reason} | {ctx.author.id}")
            await self.store_statistics(ctx, ctx.author, True)
            await ctx.message.add_reaction("<:check:1336689145216766015>")

            if not await self.invoke_msg(ctx, user):
                await ctx.success(f"{user.mention} has been **Banned**")

            await self.send_ban_dm(user, ctx.guild, ctx.author, reason, ctx)
        # Replace with your custom emoji

        except discord.Forbidden:
            return await ctx.warning(
                "I don't have the **necessary permissions** to ban that member."
            )
        except discord.NotFound:
            return await ctx.fail(f"{user.name} is already **banned** from the server.")

    async def do_unban(self, ctx, u: Union[discord.Member, discord.User, str]):
        if isinstance(u, discord.User):
            pass  # type: ignore
        elif isinstance(u, discord.Member):
            pass  # type: ignore
        else:
            async for ban in ctx.guild.bans():
                if ban.user.name == u or ban.user.global_name == u:
                    await ctx.guild.unban(discord.Object(ban.user.id))
                    return ban
            return None
        await ctx.guild.unban(discord.Object(u.id))
        return u

    @commands.command(name="unban", brief="Unban a banned user from the guild")
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    async def unban_member(self, ctx, *, user: Union[discord.User, int, str]):
        """Unban a user from the guild by ID, mention, or name."""
        try:
            # Convert string mention/ID to int if needed
            if isinstance(user, str):
                if user.isdigit():
                    user = int(user)
                elif "<@" in user:
                    user = int("".join(filter(str.isdigit, user)))

            # Check if user is hardbanned
            if isinstance(user, (int, discord.User)):
                user_id = user.id if isinstance(user, discord.User) else user
                res = await self.bot.db.fetchval(
                    """SELECT user_id FROM hardban WHERE guild_id = $1 AND user_id = $2""",
                    ctx.guild.id,
                    user_id,
                )
                if res:
                    await ctx.confirm(
                        f"**{user}** is **hardbanned**, would you like to **unban?**"
                    )
                    await self.bot.db.execute(
                        """DELETE FROM hardban WHERE guild_id = $1 AND user_id = $2""",
                        ctx.guild.id,
                        user_id,
                    )

            # Get banned users list
            banned_users = [ban.user async for ban in ctx.guild.bans()]
            if not banned_users:
                return await ctx.fail("There are no banned users")

            if isinstance(user, int):
                # Search by ID
                banned_user = discord.utils.get(banned_users, id=user)
            elif isinstance(user, discord.User):
                # Direct user object
                banned_user = user if user in banned_users else None
            else:
                # Search by name
                banned_user = discord.utils.get(banned_users, name=user)

            if not banned_user:
                return await ctx.fail("That user is not banned")

            # Unban the user
            await ctx.guild.unban(banned_user, reason=f"Unbanned by {ctx.author}")
            await self.store_statistics(ctx, ctx.author)

            if not await self.invoke_msg(ctx, banned_user):
                return await ctx.success(f"{banned_user.mention} has been **unbanned**")

        except discord.Forbidden:
            return await ctx.fail("I don't have the **necessary permissions** to unban")
        except discord.NotFound:
            return await ctx.fail("That user was not found")
        except Exception as e:
            return await ctx.fail(f"An error occurred: {str(e)}")

    @commands.command(
        name="kick", aliases=["deport"], brief="Kick a user from the guild"
    )
    @commands.bot_has_permissions(kick_members=True)
    @commands.has_permissions(kick_members=True)
    async def kick_member(self, ctx, user: discord.Member):
        if not (r := await self.bot.hierarchy(ctx, user)):
            return r
        user_ids = (
            await self.bot.db.fetchval(
                """SELECT user_ids FROM protected WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if user.id in user_ids:
            raise CommandError(
                f"You cannot **kick** {user.mention} as they are **protected**"
            )
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
                await self.store_statistics(ctx, ctx.author)

                if not await self.invoke_msg(ctx, user):
                    await message.edit(
                        embed=discord.Embed(
                            description=f"{ctx.author.mention}: **kicked** {user.mention}",
                            color=self.bot.color,
                        )
                    )
                return
        try:
            await ctx.guild.kick(user, reason=f"invoked by author | {ctx.author.id}")
            await self.store_statistics(ctx, ctx.author)

            if not await self.invoke_msg(ctx, user):
                await ctx.success(f"**kicked** {user.mention}")
            return
        except discord.Forbidden:
            await ctx.warning(
                "I don't have the **necessary permissions** to kick that member."
            )
            raise InvalidError()
        except discord.NotFound:
            await ctx.fail(f"**{user.name}** is already **kicked** from the server.")
            raise InvalidError()

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
        from pytz import timezone

        timezone = timezone("America/New_York")

        members = [
            f"{m.mention} - {naturaltime(m.timed_out_until.replace(tzinfo=None)).strip(' from now')}"
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

    @commands.group(
        name="mute",
        aliases=["timeout", "shutup"],
        brief="Mute a member in the guild for a duration",
        example=",mute @sudosql 30m",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(manage_roles=True)
    async def timeout(
        self,
        ctx,
        member: discord.Member,
        time: str = "20m",
        *,
        reason: str = "No reason provided",
    ):
        user_ids = (
            await self.bot.db.fetchval(
                """SELECT user_ids FROM protected WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if member.id in user_ids:
            raise CommandError(
                f"You cannot **mute** {member.mention} as they are **protected**"
            )
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        else:
            try:
                converted = humanfriendly.parse_timespan(time)
            except Exception:
                converted = humanfriendly.parse_timespan("20m")
            tf = humanize.naturaldelta(datetime.timedelta(seconds=converted))
            try:
                if converted >= 2419200:
                    return await ctx.fail("you can only mute for up to **28 days**")
                mute_time = discord.utils.utcnow() + datetime.timedelta(
                    seconds=converted
                )
            except OverflowError:
                return await ctx.fail(
                    "time length is too high, maximum mute time of **28 days**"
                )
            await member.edit(
                timed_out_until=mute_time,
                reason=f"muted by {str(ctx.author)} | {reason}",
            )
            await self.store_statistics(ctx, ctx.author)
            datetime.datetime.now() + datetime.timedelta(seconds=converted)  # type: ignore
            if kwargs := await self.invoke_msg(ctx, member):
                return
            await ctx.success(
                f"{member.mention} has been **muted** for **{tf}** | **{reason}**"
            )

    @timeout.command(
        name="list", brief="View list of timed out members", example=",timeout list"
    )
    @commands.has_permissions(moderate_members=True)
    @commands.bot_has_permissions(moderate_members=True)
    async def timeout_list(self, ctx: Context):
        """List all timed out members in the guild"""
        timed_out = [m for m in ctx.guild.members if m.is_timed_out()]
        if not timed_out:
            return await ctx.fail("No members are timed out")

        rows = []
        for i, member in enumerate(timed_out, start=1):
            timeout_until = discord.utils.format_dt(member.timed_out_until, style="t")
            rows.append(f"`{i}` {member.mention} - {timeout_until}")

        return await self.bot.dummy_paginator(
            ctx,
            discord.Embed(title="Timed out members", color=self.bot.color),
            rows,
            type="member",
        )

    async def do_jail(self, ctx: Context, member: discord.Member):
        jail_data = await self.bot.db.fetchrow(
            """SELECT role_id FROM jail_config WHERE guild_id = $1""", ctx.guild.id
        )

        if not jail_data:
            raise CommandError(
                f"Jail role not configured. Please run `{ctx.prefix}setme`"
            )

        jailed = ctx.guild.get_role(jail_data["role_id"])
        if not jailed:
            raise CommandError(f"Jail role not found. Please run `{ctx.prefix}setme`")

        roles = [m for m in member.roles if m.is_assignable()]
        ids = [r.id for r in roles]
        ids_str = ",".join(str(i) for i in ids)

        try:
            await self.bot.db.execute(
                """INSERT INTO jailed (guild_id, user_id, roles) VALUES ($1, $2, $3)""",
                ctx.guild.id,
                member.id,
                ids_str,
            )
        except asyncpg.exceptions.UniqueViolationError:
            await self.bot.db.execute(
                """UPDATE jailed SET roles = $3 WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
                ids_str,
            )

        if jailed not in member.roles:
            after_roles = [r for r in member.roles if not r.is_assignable()]
            after_roles.append(jailed)
            await member.edit(roles=after_roles, reason=f"jailed by {ctx.author.name}")
            await self.moderator_logs(ctx, f"jailed **{member.name}**")

        return True

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
        elif command == "warn":
            case_type = CaseType.warns
        elif command == "modstats":
            if not store:
                data = await self.bot.db.fetchval(
                    """SELECT data FROM moderation_statistics WHERE guild_id = $1 AND user_id = $2""",
                    ctx.guild.id,
                    member.id,
                )
                if data:
                    try:
                        return json.loads(data)
                    except (json.JSONDecodeError, TypeError):
                        return {}
                return {}
            else:
                return
        else:
            return

        existing_data = await self.bot.db.fetchval(
            """SELECT data FROM moderation_statistics WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )
        try:
            data = json.loads(existing_data) if existing_data else {}
        except (json.JSONDecodeError, TypeError):
            data = {}

        if not store:
            return data

        name = str(case_type.name)
        if not data.get(name):
            data[name] = 1
        else:
            data[name] += 1

        try:
            json_data = json.dumps(data)
        except (TypeError, ValueError):
            json_data = "{}"

        await self.bot.db.execute(
            """INSERT INTO moderation_statistics (guild_id, user_id, data) 
                VALUES($1, $2, $3) ON CONFLICT(guild_id, user_id) 
                DO UPDATE SET data = $3""",
            ctx.guild.id,
            member.id,
            json_data,
        )
        return True

    async def do_unjail(self, ctx: Context, member: discord.Member):
        jail_data = await self.bot.db.fetchrow(
            """SELECT role_id FROM jail_config WHERE guild_id = $1""", ctx.guild.id
        )

        if not jail_data:
            raise CommandError(
                f"Jail role not configured. Please run `{ctx.prefix}setme`"
            )

        jailed = ctx.guild.get_role(jail_data["role_id"])
        if not jailed:
            raise CommandError(f"Jail role not found. Please run `{ctx.prefix}setme`")

        if jailed not in member.roles:
            raise CommandError(f"{member.mention} isn't **jailed**")

        stored_roles = await self.bot.db.fetchval(
            """SELECT roles FROM jailed WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )

        if not stored_roles:
            await member.remove_roles(jailed)
            await self.bot.db.execute(
                """DELETE FROM jailed WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )
            await self.moderator_logs(ctx, f"unjailed **{member.name}**")
            return True

        try:
            roles_to_add = []
            if stored_roles:  # Only process if there are stored roles
                for role_id in stored_roles.split(","):
                    if role := ctx.guild.get_role(int(role_id)):
                        if role.is_assignable():
                            roles_to_add.append(role)

            current_roles = [
                r for r in member.roles if r != jailed and not r.is_default()
            ]

            final_roles = list(set(roles_to_add + current_roles))

            final_roles.append(ctx.guild.default_role)

            await member.edit(
                roles=final_roles, reason=f"unjailed by {ctx.author.name}"
            )

            await self.bot.db.execute(
                """DELETE FROM jailed WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                member.id,
            )

            await self.moderator_logs(ctx, f"unjailed **{member.name}**")
            return True

        except discord.Forbidden:
            raise CommandError("I don't have permission to manage roles")
        except discord.HTTPException as e:
            raise CommandError(f"Failed to unjail member: {str(e)}")

    @commands.group(
        name="jail",
        brief="jail a member",
        example=",jail @sudosql laddering",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(moderate_members=True)
    async def jail(self, ctx: Context, *, member: Member):
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        user_ids = (
            await self.bot.db.fetchval(
                """SELECT user_ids FROM protected WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if member.id in user_ids:
            raise CommandError(
                f"You cannot **jail** {member.mention} as they are **protected**"
            )
        jail_data = await self.bot.db.fetchrow(
            """SELECT role_id FROM jail_config WHERE guild_id = $1""", ctx.guild.id
        )

        if not jail_data:
            return await ctx.fail("**jailed** role not configured")

        role = ctx.guild.get_role(jail_data["role_id"])
        if not role:
            return await ctx.fail("**jailed** role not found")

        if role.position > ctx.guild.me.top_role.position:
            return await ctx.fail("**jailed** role is higher than my **top role**")
        if (
            role.position > ctx.author.top_role.position
            and ctx.author != ctx.guild.owner
        ):
            return await ctx.fail("**jailed** role is higher than your **top role**")
        if role in member.roles:
            return await ctx.fail(f"{member.mention} is already **jailed**")
        await self.do_jail(ctx, member)
        await self.store_statistics(ctx, ctx.author)
        if kwargs := await self.invoke_msg(ctx, member):
            return
        await ctx.success(f"{member.mention} has been **jailed**")
        return

    @jail.command(
        name="channel", brief="Set the jail channel", example=",jail channel #jail"
    )
    @commands.has_permissions(administrator=True)
    async def jail_channel(self, ctx, channel: TextChannel):
        jail_data = await self.bot.db.fetchrow(
            """SELECT channel_id FROM jail_config WHERE guild_id = $1""", ctx.guild.id
        )
        if not jail_data:
            await self.bot.db.execute(
                """INSERT INTO jail_config (guild_id, channel_id) VALUES ($1, $2)""",
                ctx.guild.id,
                channel.id,
            )
            return await ctx.success(
                f"**Jail channel** has been set to {channel.mention}"
            )
        await self.bot.db.execute(
            """UPDATE jail_config SET channel_id = $1 WHERE guild_id = $2""",
            channel.id,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**Jail channel** has been updated to {channel.mention}"
        )

    @jail.command(name="role", brief="Set the jail role", example=",jail role @jailed")
    @commands.has_permissions(administrator=True)
    async def jail_role(self, ctx, role: Role):
        role = role[0]
        if role.position > ctx.guild.me.top_role.position:
            return await ctx.fail("**jailed** role is higher than my **top role**")
        if role.position > ctx.author.top_role.position:
            return await ctx.fail("**jailed** role is higher than your **top role**")
        await self.bot.db.execute(
            """INSERT INTO jail_config (guild_id, role_id) VALUES ($1, $2)
            ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"**Jailed** role has been set to {role.mention}")

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
        await self.setup_mute_roles(ctx)

        category = discord.utils.get(
            ctx.guild.categories, name=f"{self.bot.user.name}-mod"
        )
        if not category:
            category = await ctx.guild.create_category_channel(
                name=f"{self.bot.user.name}-mod",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        view_channel=False
                    )
                },
            )

        jail_role = discord.utils.get(ctx.guild.roles, name="jailed")
        if not jail_role:
            jail_role = await ctx.guild.create_role(name="jailed")

        logs = next((ch for ch in ctx.guild.text_channels if ch.name == "logs"), None)
        if not logs:
            logs = await ctx.guild.create_text_channel(
                name="logs",
                overwrites={
                    ctx.guild.default_role: discord.PermissionOverwrite(
                        view_channel=False
                    )
                },
            )
        await logs.edit(category=category)

        jail_channel = next(
            (ch for ch in ctx.guild.text_channels if "jail" in ch.name.lower()), None
        )
        if jail_channel:
            await jail_channel.set_permissions(
                jail_role, view_channel=True, send_messages=True
            )
            await jail_channel.set_permissions(
                ctx.guild.default_role, view_channel=False, send_messages=False
            )
        else:
            jail_channel = await ctx.guild.create_text_channel(name="jail")
            await jail_channel.set_permissions(
                jail_role, view_channel=True, send_messages=True
            )
            await jail_channel.set_permissions(
                ctx.guild.default_role, view_channel=False, send_messages=False
            )

        await jail_channel.edit(category=category)

        for channel in ctx.guild.text_channels:
            if channel != jail_channel and channel != logs:
                await channel.set_permissions(
                    jail_role, view_channel=False, send_messages=False
                )

        # Store jail role and channel IDs
        await self.bot.db.execute(
            """INSERT INTO jail_config (guild_id, role_id, channel_id) 
            VALUES($1, $2, $3) ON CONFLICT(guild_id) 
            DO UPDATE SET role_id = excluded.role_id, channel_id = excluded.channel_id""",
            ctx.guild.id,
            jail_role.id,
            jail_channel.id,
        )

        await self.bot.db.execute(
            """INSERT INTO moderation_channel (guild_id, category_id, channel_id)
            VALUES($1, $2, $3)
            ON CONFLICT(guild_id)
            DO UPDATE SET channel_id = excluded.channel_id, category_id = excluded.category_id""",
            ctx.guild.id,
            category.id,
            logs.id,
        )

        return await ctx.success(
            "**Jail channel**, the **jailed role**, and **mod logs** have been **created** for this guild"
        )

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

        # Clear jail config
        await self.bot.db.execute(
            """DELETE FROM jail_config WHERE guild_id = $1""", ctx.guild.id
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
        return await ctx.success("**Jail and logs** setup has been **reset**")

    @commands.group(
        name="protect",
        aliases=["protected"],
        brief="protect a user from being punished using the bot",
        invoke_without_command=True,
    )
    @commands.has_permissions(administrator=True)
    async def protect(self, ctx: Context, *, user: Union[User, Member]):
        user_ids = (
            await self.bot.db.fetchval(
                """SELECT user_ids FROM protected WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if user.id in user_ids:
            user_ids.remove(user.id)
            message = f"Removed **{str(user)}** from the protected list"
        else:
            user_ids.append(user.id)
            message = f"Added **{str(user)}** to the protected list"
        await self.bot.db.execute(
            """INSERT INTO protected (guild_id, user_ids) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET user_ids = excluded.user_ids""",
            ctx.guild.id,
            user_ids,
        )
        return await ctx.success(message)

    @protect.command(name="list", brief="view the protected users")
    @commands.has_permissions(administrator=True)
    async def protect_list(self, ctx: Context):
        if not (
            user_ids := await self.bot.db.fetchval(
                """SELECT user_ids FROM protected WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("No users have been **protected**")
        rows = [f"`{i}` <@!{user_id}" for i, user_id in enumerate(user_ids, start=1)]
        return await self.bot.dummy_paginator(
            ctx,
            discord.Embed(title="protected members", color=self.bot.color),
            rows,
            type="members",
        )

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
        example=",unjail @sudosql",
        invoke_without_command=True,
    )
    @commands.bot_has_permissions(moderate_members=True)
    @commands.has_permissions(moderate_members=True)
    async def unjail(self, ctx: Context, *, member: Member):
        await self.do_unjail(ctx, member)
        await self.store_statistics(ctx, ctx.author)
        if kwargs := await self.invoke_msg(ctx, member):
            return
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
            await self.store_statistics(ctx, ctx.author)
        return await ctx.success("unjailed all **jailed** members")

    @commands.command(
        name="unmute",
        aliases=[
            "untime",
            "untimeout",
        ],
        brief="Unmute a user in the guild",
        example=",unmute @sudosql",
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
        await self.store_statistics(ctx, ctx.author)
        if kwargs := await self.invoke_msg(ctx, member):
            return
        await ctx.success(f"{member.mention} has been **unmuted**.")
        await self.moderator_logs(ctx, f"unmuted **{member.name}**")

    @commands.command(
        name="nickname",
        aliases=["nick"],
        brief="Change a users nickname in the guild",
    )
    @commands.has_permissions(manage_nicknames=True)
    async def nickname(self, ctx, member: discord.Member, *, nickname: str = None):
        if not (r := await self.bot.hierarchy(ctx, member)):
            return r
        if member.top_role >= ctx.author.top_role:
            return await ctx.fail(f"you aren't higher then {member.mention} is")
        if member == ctx.guild.owner:
            return await ctx.fail("you can't change the nickname of the owner")
        if nickname is None:
            await member.edit(nick=None)
            return await ctx.success(f"**Reset** {member.mention}'s nickname")
        await member.edit(nick=nickname)
        return await ctx.success(
            f"**Changed** {member.mention}'s nickname to **{nickname}**"
        )

    @commands.command(
        name="forcenick",
        aliases=["fn"],
        brief="Force/Remove the force of a users nickname in a guild",
        example="forcenick @sudosql catboy",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def forcenick(self, ctx, member: discord.Member, *, name: str = None):
        if member.top_role >= ctx.author.top_role:
            return await ctx.fail(f"you aren't higher then {member.mention} is")
        if member == ctx.guild.owner:
            return await ctx.fail("you can't forcenick the owner")

        try:
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
                    return await ctx.fail(
                        f"theres no forcenick entry for {member.mention}"
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
                return await ctx.success(
                    f"**Unlocked** {member.mention}'s forced nickname"
                )
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
        except discord.Forbidden:
            return await ctx.fail(
                "I don't have permission to change that member's nickname"
            )

    @commands.group(name="lock", brief="Lock the channel in a guild")
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def lock(self, ctx):
        if ctx.invoked_subcommand is None:
            channel = ctx.channel
            if isinstance(channel, Thread):
                await channel.edit(locked=True)
            else:
                permissions = channel.overwrites_for(ctx.guild.default_role)
                permissions.send_messages = False
                permissions.add_reactions = False
                permissions.view_channel = True
                await channel.set_permissions(
                    ctx.guild.default_role, overwrite=permissions
                )
                if role_id := await self.bot.db.fetchval(
                    """SELECT role_id FROM lock_role WHERE guild_id = $1""",
                    ctx.guild.id,
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
        if isinstance(channel, Thread):
            await channel.edit(locked=False)
        else:
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

    @commands.command(
        name="strip",
        aliases=["stripstaff"],
        brief="Remove moderation roles from a user in a guild",
    )
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(administrator=True)
    async def strip(self, ctx: Context, *, member: discord.Member):
        user_ids = (
            await self.bot.db.fetchval(
                """SELECT user_ids FROM protected WHERE guild_id = $1""", ctx.guild.id
            )
            or []
        )
        if member.id in user_ids:
            raise CommandError(
                f"You cannot **strip** {member.mention} as they are **protected**"
            )
        if (
            member.top_role > ctx.author.top_role
            and ctx.author.id != ctx.guild.owner_id
        ):
            return await ctx.fail(f"you couldn't strip {member.mention}")
        if (
            not ctx.author == ctx.guild.owner
            and not ctx.author.top_role > member.top_role
        ):
            return await ctx.fail(f"you couldn't strip {member.mention}")

        # Get roles with mod permissions
        mod_roles = [
            role
            for role in member.roles
            if role != ctx.guild.premium_subscriber_role
            and role != ctx.guild.default_role
            and (
                role.permissions.kick_members
                or role.permissions.ban_members
                or role.permissions.manage_messages
                or role.permissions.manage_roles
                or role.permissions.administrator
                or role.permissions.manage_guild
                or role.permissions.manage_channels
                or role.permissions.manage_webhooks
                or role.permissions.manage_threads
                or role.permissions.manage_events
                or role.permissions.manage_nicknames
                or role.permissions.manage_roles
                or role.permissions.view_audit_log
                or role.permissions.manage_emojis
            )
            and role < ctx.author.top_role
        ]

        if not mod_roles:
            return await ctx.fail(f"{member.mention} has no moderation roles")

        # Store roles for potential restoration
        role_ids = [r.id for r in mod_roles]
        await self.bot.redis.set(
            f"r-{ctx.guild.id}-{member.id}", orjson.dumps(role_ids), ex=9000
        )

        # Remove the roles
        await member.remove_roles(
            *mod_roles, atomic=False, reason=f"mod roles stripped by {ctx.author}"
        )

        return await ctx.success(
            f"**Stripped** `{len(mod_roles)}` moderation roles from {member.mention}"
        )

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
        parameters={"channel": {"converter": TextChannel, "default": None}},
    )
    @commands.has_permissions(manage_guild=True)
    async def disable_command(self, ctx: commands.Context, *, command: str):
        if command in ["disable", "enable"]:
            raise commands.CommandError(f"You can't disable **{command}**")
        command = command.split("--channel")
        if len(command[0]) > 0:
            command = command[0]
        else:
            command = command[1].split(" ", 2)[-1]
        if cmd := self.bot.get_command(command):
            data = json.loads(
                await self.bot.db.fetchval(
                    """SELECT channels FROM disabled_commands where guild_id = $1 AND command = $2""",
                    ctx.guild.id,
                    cmd.qualified_name,
                )
                or "[]"
            )
            if channel := ctx.parameters.get("channel"):
                data.append(channel.id)
            await self.bot.db.execute(
                """INSERT INTO disabled_commands (guild_id, command, channels) VALUES($1,$2,$3) ON CONFLICT(guild_id, command) DO UPDATE SET channels = excluded.channels""",
                ctx.guild.id,
                cmd.qualified_name.lower(),
                json.dumps(data),
            )
            await ctx.success(f"`{cmd.qualified_name}` has been **disabled**")
        else:
            await ctx.fail(f"`{command}` doesn't exist as a command")

    @command_group.command(
        name="list",
        brief="List all disabled commands in a guild",
        example=",command list",
    )
    @commands.has_permissions(manage_guild=True)
    async def list_commands(self, ctx: commands.Context):
        data = await self.bot.db.fetch(
            "SELECT command FROM disabled_commands WHERE guild_id = $1", ctx.guild.id
        )
        if not data:
            return await ctx.fail("No commands are disabled in this guild")
        disabled_commands = [record["command"] for record in data]
        return await ctx.success(
            f"**Disabled commands** in this guild:\n{', '.join(disabled_commands)}"
        )

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
        await ctx.message.delete()
        return await self.cleanup_bot_messages(ctx, amount)

    @commands.group(
        name="purge",
        aliases=["clear", "c"],
        invoke_without_command=True,
        brief="Mass delete messages in a guild",
        example=",purge @sudosql 100",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: Context,
        member: typing.Optional[discord.Member] = None,
        limit: int = 10,
    ):
        await ctx.message.delete()
        if limit > 100:
            return await ctx.fail("You can only delete up to **100 messages** at a time.")

        def check(message: discord.Message):
            if member:
                return message.author.id == member.id
            return True

        try:
            deleted = await ctx.channel.purge(limit=limit, check=check)
            await ctx.success(f"Deleted **{len(deleted)}** messages.", delete_after=5)
        except discord.Forbidden:
            await ctx.fail("I don't have permission to delete messages in this channel.")
        except discord.HTTPException as e:
            await ctx.fail(f"An error occurred while deleting messages: {e}")

    @purge.command(
        name="bots",
        invoke_without_command=True,
        brief="Mass delete messages sent by bots",
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

    @purge.command(
        name="images",
        aliases=["image"],
        brief="Mass delete Images sent in a channel",
        example=",purge images 100",
    )
    @commands.bot_has_permissions(manage_messages=True)
    @commands.has_permissions(manage_messages=True)
    async def purge_images(self, ctx, limit: int = 10):
        def check(message: discord.Message):
            if message.created_at < (
                discord.utils.utcnow() - datetime.timedelta(days=14)
            ):
                return False
            if len(message.attachments) > 0:
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
        now = discord.utils.utcnow()
        cutoff = now - datetime.timedelta(days=14)

        async for message in ctx.channel.history(limit=200):
            if message.created_at < cutoff:
                continue

            if message.author == self.bot.user or message.content.startswith(
                ctx.prefix
            ):
                bot_messages.append(message)
                if len(bot_messages) == 100:
                    break

        bot_messages.append(ctx.message)

        if bot_messages:
            await ctx.channel.delete_messages(set(bot_messages))
            message = await ctx.send("👍🏼")
            await message.delete()
        else:
            message = await ctx.send("No messages to clean up")
            await message.delete(delay=3)

    @commands.group(
        name="warn",
        brief="Warn a member in a guild",
        example=",warn @sudosql being rude",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_messages=True)
    async def warn(
        self, ctx: Context, member: Member, *, reason: str = "No reason provided"
    ) -> discord.Message:
        if member.top_role >= ctx.author.top_role:
            return await ctx.fail("you can't warn someone higher than you")
        if member == ctx.guild.owner:
            return await ctx.fail("you can't warn the owner")
        if member == ctx.guild.me:
            return await ctx.fail("you can't warn me")
        if member == ctx.author:
            return await ctx.fail("you can't warn yourself")

        # Add warning
        warn_id = str(uuid.uuid4())[:6]
        await self.bot.db.execute(
            """INSERT INTO warnings (guild_id, user_id, reason, created_at, moderator_id, id) 
            VALUES($1, $2, $3, $4, $5, $6)""",
            ctx.guild.id,
            member.id,
            reason,
            discord.utils.utcnow().replace(tzinfo=None),
            ctx.author.id,
            warn_id,
        )

        # Get warning count
        warning_count = await self.bot.db.fetchval(
            """SELECT COUNT(*) FROM warnings WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )

        # Check for punishments at current warning count
        punishments = await self.bot.db.fetch(
            """SELECT type, duration FROM warning_punishments 
            WHERE guild_id = $1 AND threshold = $2
            ORDER BY CASE 
                WHEN type = 'ban' THEN 1
                WHEN type = 'kick' THEN 2
                WHEN type = 'jail' THEN 3
                WHEN type = 'timeout' THEN 4
            END""",  # Order punishments so ban is always last
            ctx.guild.id,
            warning_count,
        )

        await self.store_statistics(ctx, ctx.author)
        response = (
            f"**Warned** {member.mention} for `{reason}` (Warning #{warning_count})"
        )

        if punishments:
            for punishment in punishments:
                punishment_type = punishment["type"]
                duration = punishment["duration"]

                try:
                    if punishment_type == "kick":
                        await member.kick(
                            reason=f"Reached warning threshold ({warning_count})"
                        )
                        response += f"\nAutomatically kicked for reaching {warning_count} warnings"

                    elif punishment_type == "ban":
                        await member.ban(
                            reason=f"Reached warning threshold ({warning_count})"
                        )
                        response += f"\nAutomatically banned for reaching {warning_count} warnings"
                        # Only reset warnings on ban
                        await self.bot.db.execute(
                            """DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2""",
                            ctx.guild.id,
                            member.id,
                        )
                        response += "\nWarning count has been reset due to ban"
                        break  # Stop processing other punishments after ban

                    elif punishment_type == "timeout":
                        until = discord.utils.utcnow() + timedelta(seconds=duration)
                        await member.timeout(
                            until, reason=f"Reached warning threshold ({warning_count})"
                        )
                        response += f"\nAutomatically timed out for {humanize.naturaldelta(timedelta(seconds=duration))} for reaching {warning_count} warnings"

                    elif punishment_type == "jail":
                        await self.do_jail(ctx, member)
                        response += f"\nAutomatically jailed for reaching {warning_count} warnings"

                except discord.Forbidden:
                    response += f"\nFailed to apply punishment ({punishment_type}) - Missing Permissions"
                except Exception as e:
                    response += (
                        f"\nFailed to apply punishment ({punishment_type}) - {str(e)}"
                    )

        return await ctx.success(response)

    @warn.command(
        name="list",
        brief="List all warnings for a member",
        example=",warn list @sudosql",
    )
    @commands.has_permissions(manage_messages=True)
    async def warn_list(self, ctx: Context, member: discord.Member) -> discord.Message:
        warnings = await self.bot.db.fetch(
            """SELECT id, reason, moderator_id, created_at FROM warnings WHERE guild_id = $1 AND user_id = $2 ORDER BY created_at DESC""",
            ctx.guild.id,
            member.id,
        )
        if not warnings:
            return await ctx.fail(f"{member.mention} has no warnings.")

        embed = discord.Embed(
            title=f"Warnings for {member}",
            color=self.bot.color,
            timestamp=discord.utils.utcnow(),
        )

        for warning in warnings:
            moderator = ctx.guild.get_member(warning["moderator_id"])
            embed.add_field(
                name=f"Warning **{warning['id']}** - {discord.utils.format_dt(warning['created_at'], style='R')}",
                value=f"**Reason:** {warning['reason']}\n**Moderator:** {moderator.mention if moderator else 'Unknown'}",
                inline=False,
            )

        return await ctx.send(embed=embed)

    @warn.command(
        name="remove",
        brief="Remove a warning from a member",
        example=",warn remove @sudosql 1",
    )
    @commands.has_permissions(manage_messages=True)
    async def warn_remove(
        self, ctx: Context, member: discord.Member, id: str
    ) -> discord.Message:
        if member.top_role >= ctx.author.top_role:
            return await ctx.fail("you can't warn someone higher than you")
        if member == ctx.guild.owner:
            return await ctx.fail("you can't warn the owner")
        if member == ctx.guild.me:
            return await ctx.fail("you can't warn me")
        if member == ctx.author:
            return await ctx.fail("you can't warn yourself")
        warning = await self.bot.db.fetchrow(
            """SELECT id FROM warnings WHERE guild_id = $1 AND user_id = $2 AND id = $3""",
            ctx.guild.id,
            member.id,
            id,
        )
        if not warning:
            return await ctx.fail(
                f"{member.mention} doesn't have a warning with ID `{id}`."
            )

        await self.bot.db.execute(
            """DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2 AND id = $3""",
            ctx.guild.id,
            member.id,
            id,
        )
        await self.store_statistics(ctx, ctx.author)
        return await ctx.success(f"Removed warning `{id}` from {member.mention}")

    @warn.command(
        name="clear",
        brief="Clear all warnings for a member",
        example=",warn clear @sudosql",
    )
    @commands.has_permissions(manage_messages=True)
    async def warn_clear(self, ctx: Context, member: discord.Member) -> discord.Message:
        if member.top_role >= ctx.author.top_role:
            return await ctx.fail("you can't warn someone higher than you")
        if member == ctx.guild.owner:
            return await ctx.fail("you can't warn the owner")
        if member == ctx.guild.me:
            return await ctx.fail("you can't warn me")
        if member == ctx.author:
            return await ctx.fail("you can't warn yourself")
        await self.bot.db.execute(
            """DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )
        await self.store_statistics(ctx, ctx.author)
        return await ctx.success(f"Cleared all warnings for {member.mention}")

    @commands.command(
        name="warnings",
        brief="List all warnings for a member",
        example=",warnings @sudosql",
    )
    @commands.has_permissions(manage_messages=True)
    async def warnings(self, ctx: Context, member: discord.Member) -> discord.Message:
        await self.warn_list(ctx, member)

    @commands.hybrid_command(brief="manage messages", aliases=["pic"])
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def picperms(
        self,
        ctx,
        member: discord.Member,
        *,
        channel: discord.TextChannel = commands.CurrentChannel,
    ):
        """
        Give a member permissions to post attachments in a channel
        """

        overwrite = channel.overwrites_for(member)

        if (
            channel.permissions_for(member).attach_files
            and channel.permissions_for(member).embed_links
        ):
            overwrite.attach_files = False
            overwrite.embed_links = False
            await channel.set_permissions(
                member,
                overwrite=overwrite,
                reason=f"Picture permissions removed by {ctx.author}",
            )
            return await ctx.success(
                f"Removed pic perms from {member.mention} in {channel.mention}"
            )
        else:
            overwrite.attach_files = True
            overwrite.embed_links = True
            await channel.set_permissions(
                member,
                overwrite=overwrite,
                reason=f"Picture permissions granted by {ctx.author}",
            )
            return await ctx.success(
                f"Added pic perms to {member.mention} in {channel.mention}"
            )

    @commands.group(name="report", invoke_without_command=True)
    async def report(self, ctx):
        """Base command for the report system."""
        await ctx.send_help(ctx.command.qualified_name)

    @report.command(name="add")
    @commands.is_owner()
    async def report_add(self, ctx, user: commands.MemberConverter):
        """Adds a mentioned user to the whitelist so they can send reports."""
        try:
            # Ensure the table exists before proceeding
            await self.setup_database()

            user_id = user.id  # Get the mentioned user's ID

            # Check if the user is already whitelisted
            result = await self.bot.db.fetchrow(
                "SELECT user_id FROM report_whitelist WHERE user_id = $1", user_id
            )
            if result:
                return await ctx.warning(f"User {user.mention} is already whitelisted.")

            # Add the user to the whitelist
            await self.bot.db.execute(
                "INSERT INTO report_whitelist (user_id) VALUES ($1)", user_id
            )

            await ctx.success(f"User {user.mention} has been added to the whitelist.")
        except Exception as e:
            await ctx.fail(f"Error adding user: {e}")
            logger.info(f"Error adding user {user.id} to whitelist: {e}")

    @report.command(name="remove")
    @commands.is_owner()
    async def report_remove(self, ctx, user: commands.MemberConverter):
        """Removes a mentioned user from the whitelist."""
        try:
            # Ensure the table exists before proceeding
            await self.setup_database()

            user_id = user.id  # Get the mentioned user's ID

            # Check if the user is whitelisted
            result = await self.bot.db.fetchrow(
                "SELECT user_id FROM report_whitelist WHERE user_id = $1", user_id
            )
            if not result:
                return await ctx.fail(f"User {user.mention} is not whitelisted.")

            # Remove the user from the whitelist
            await self.bot.db.execute(
                "DELETE FROM report_whitelist WHERE user_id = $1", user_id
            )

            await ctx.success(
                f"User {user.mention} has been removed from the whitelist."
            )
        except Exception as e:
            await ctx.fail(f"Error removing user: {e}")
            logger.info(f"Error removing user {user.id} from whitelist: {e}")

    @report.command(name="send")
    async def report_send(self, ctx, *, message: str):
        """Allows a whitelisted user to send a report."""
        try:
            # Ensure the table exists before proceeding
            await self.setup_database()

            # Check if the user is whitelisted
            result = await self.bot.db.fetchrow(
                "SELECT user_id FROM report_whitelist WHERE user_id = $1", ctx.author.id
            )
            if not result:
                return await ctx.fail("You are not whitelisted to send reports.")

            # Prepare the embed for the webhook
            embed = {
                "embeds": [
                    {
                        "title": "New Report Submitted",
                        "description": message,
                        "color": self.bot.color,
                        "fields": [
                            {
                                "name": "User",
                                "value": f"{ctx.author.mention} (`{ctx.author.id}`)",
                                "inline": True,
                            },
                            {
                                "name": "Server",
                                "value": f"{ctx.guild.name} (`{ctx.guild.id}`)",
                                "inline": True,
                            },
                            {
                                "name": "Channel",
                                "value": f"{ctx.channel.name} (`{ctx.channel.id}`)",
                                "inline": True,
                            },
                        ],
                        "footer": {
                            "text": f"Report submitted on {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                        },
                    }
                ]
            }

            # Try to get the server invite link (if the bot has permission)
            try:
                invites = await ctx.guild.invites()
                if invites:
                    invite_link = invites[0].url  # Get the first invite link
                    embed["embeds"][0]["fields"].append(
                        {
                            "name": "Server Invite",
                            "value": f"[Click here to join]({invite_link})",
                            "inline": False,
                        }
                    )
            except discord.Forbidden:
                # If the bot doesn't have permission to fetch invites
                pass

            # Webhook URL (replace with your actual webhook URL)
            webhook_url = "https://discord.com/api/webhooks/1316476312633999441/XP8d_WYaNuoizHkVP1ThcwYTPQYd3cJiDbqnpLB7nIzh36NNNVn9I6sbi5CvHi_Ujy9T"

            # Send the webhook with the report embed
            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=embed) as response:
                    if response.status == 204:
                        await ctx.success(
                            "Your report has been successfully submitted!"
                        )
                    else:
                        await ctx.fail(
                            "Failed to submit the report. Please try again later."
                        )
                        logger.info(
                            f"Failed to send webhook, status code: {response.status}"
                        )

        except Exception as e:
            await ctx.fail(f"Error sending report: {e}")
            logger.info(f"Error sending report: {e}")

    @warn.group(
        name="punishment",
        brief="Manage warning punishments",
        invoke_without_command=True,
    )
    @commands.has_permissions(administrator=True)
    async def warn_punishment(self, ctx: Context):
        """View current warning punishments"""
        punishments = await self.bot.db.fetch(
            """SELECT threshold, type, duration FROM warning_punishments WHERE guild_id = $1 ORDER BY threshold ASC""",
            ctx.guild.id,
        )

        if not punishments:
            return await ctx.fail("No warning punishments configured")

        embed = discord.Embed(
            title="Warning Punishments",
            color=self.bot.color,
            description="List of automated punishments when warning threshold is reached",
        )

        for p in punishments:
            duration = (
                f" for {humanize.naturaldelta(timedelta(seconds=p['duration']))}"
                if p["duration"]
                else ""
            )
            embed.add_field(
                name=f"Threshold: {p['threshold']} warnings",
                value=f"Punishment: **{p['type']}**{duration}",
                inline=False,
            )

        await ctx.send(embed=embed)

    @warn_punishment.command(name="add", brief="Add a warning punishment")
    @commands.has_permissions(administrator=True)
    async def warn_punishment_add(
        self,
        ctx: Context,
        threshold: int,
        type: Literal["kick", "timeout", "ban", "jail"],
        duration: str = None,
    ):
        """
        Add a punishment for reaching a warning threshold
        """
        if type not in ["kick", "timeout", "ban", "jail"]:
            return await ctx.fail(
                "Invalid punishment type. Use 'kick', 'timeout', 'ban', or 'jail'."
            )
        if threshold < 1:
            return await ctx.fail("Threshold must be at least 1")

        # Convert duration if provided
        seconds = None
        if duration and type in ("timeout", "jail"):
            try:
                seconds = humanfriendly.parse_timespan(duration)
                if type == "timeout" and seconds > 2419200:  # 28 days
                    return await ctx.fail("Timeout duration cannot exceed 28 days")
            except:
                return await ctx.fail("Invalid duration format. Example: 1h, 2d")
        else:
            duration = None

        # Store in database
        await self.bot.db.execute(
            """INSERT INTO warning_punishments (guild_id, threshold, type, duration)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, threshold) 
            DO UPDATE SET type = excluded.type, duration = excluded.duration""",
            ctx.guild.id,
            threshold,
            type,
            seconds,
        )

        duration_text = (
            f" for {humanize.naturaldelta(timedelta(seconds=seconds))}"
            if seconds
            else ""
        )
        await ctx.success(
            f"Added punishment: **{type}**{duration_text} at **{threshold}** warnings"
        )

    @warn_punishment.command(name="remove", brief="Remove a warning punishment")
    @commands.has_permissions(administrator=True)
    async def warn_punishment_remove(self, ctx: Context, threshold: int):
        """Remove a punishment for a specific warning threshold"""
        result = await self.bot.db.execute(
            """DELETE FROM warning_punishments WHERE guild_id = $1 AND threshold = $2""",
            ctx.guild.id,
            threshold,
        )

        if result == "DELETE 0":
            return await ctx.fail(f"No punishment found for threshold **{threshold}**")

        await ctx.success(f"Removed punishment for threshold **{threshold}**")

    @warn_punishment.command(name="clear", brief="Clear all warning punishments")
    @commands.has_permissions(administrator=True)
    async def warn_punishment_clear(self, ctx: Context):
        """Remove all warning punishments"""
        await self.bot.db.execute(
            """DELETE FROM warning_punishments WHERE guild_id = $1""", ctx.guild.id
        )
        await ctx.success("Cleared all warning punishments")

    @commands.group(
        name="warn",
        brief="Warn a member in a guild",
        example=",warn @sudosql being rude",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_messages=True)
    async def warn(
        self, ctx: Context, member: Member, *, reason: str = "No reason provided"
    ) -> discord.Message:
        if member.top_role >= ctx.author.top_role:
            return await ctx.fail("you can't warn someone higher than you")
        if member == ctx.guild.owner:
            return await ctx.fail("you can't warn the owner")
        if member == ctx.guild.me:
            return await ctx.fail("you can't warn me")
        if member == ctx.author:
            return await ctx.fail("you can't warn yourself")

        # Add warning
        warn_id = str(uuid.uuid4())[:6]
        await self.bot.db.execute(
            """INSERT INTO warnings (guild_id, user_id, reason, created_at, moderator_id, id) 
            VALUES($1, $2, $3, $4, $5, $6)""",
            ctx.guild.id,
            member.id,
            reason,
            discord.utils.utcnow().replace(tzinfo=None),
            ctx.author.id,
            warn_id,
        )

        # Get warning count
        warning_count = await self.bot.db.fetchval(
            """SELECT COUNT(*) FROM warnings WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )

        # Check for punishments at current warning count
        punishments = await self.bot.db.fetch(
            """SELECT type, duration FROM warning_punishments 
            WHERE guild_id = $1 AND threshold = $2
            ORDER BY CASE 
                WHEN type = 'ban' THEN 1
                WHEN type = 'kick' THEN 2
                WHEN type = 'jail' THEN 3
                WHEN type = 'timeout' THEN 4
            END""",  # Order punishments so ban is always last
            ctx.guild.id,
            warning_count,
        )

        await self.store_statistics(ctx, ctx.author)
        response = (
            f"**Warned** {member.mention} for `{reason}` (Warning #{warning_count})"
        )

        if punishments:
            for punishment in punishments:
                punishment_type = punishment["type"]
                duration = punishment["duration"]

                try:
                    if punishment_type == "kick":
                        await member.kick(
                            reason=f"Reached warning threshold ({warning_count})"
                        )
                        response += f"\nAutomatically kicked for reaching {warning_count} warnings"

                    elif punishment_type == "ban":
                        await member.ban(
                            reason=f"Reached warning threshold ({warning_count})"
                        )
                        response += f"\nAutomatically banned for reaching {warning_count} warnings"
                        # Only reset warnings on ban
                        await self.bot.db.execute(
                            """DELETE FROM warnings WHERE guild_id = $1 AND user_id = $2""",
                            ctx.guild.id,
                            member.id,
                        )
                        response += "\nWarning count has been reset due to ban"
                        break  # Stop processing other punishments after ban

                    elif punishment_type == "timeout":
                        until = discord.utils.utcnow() + timedelta(seconds=duration)
                        await member.timeout(
                            until, reason=f"Reached warning threshold ({warning_count})"
                        )
                        response += f"\nAutomatically timed out for {humanize.naturaldelta(timedelta(seconds=duration))} for reaching {warning_count} warnings"

                    elif punishment_type == "jail":
                        await self.do_jail(ctx, member)
                        response += f"\nAutomatically jailed for reaching {warning_count} warnings"

                except discord.Forbidden:
                    response += f"\nFailed to apply punishment ({punishment_type}) - Missing Permissions"
                except Exception as e:
                    response += (
                        f"\nFailed to apply punishment ({punishment_type}) - {str(e)}"
                    )

        return await ctx.success(response)


async def setup(bot: "Greed") -> None:
    await bot.add_cog(Moderation(bot))
