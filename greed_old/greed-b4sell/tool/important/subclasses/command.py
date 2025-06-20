import discord
import re
from dataclasses import dataclass
from discord.ext import commands
from discord.ext.commands import Context
from contextlib import suppress
from aiohttp import ClientSession as Session
from discord import GuildSticker
from discord.ext.commands.converter import GuildStickerConverter, GuildStickerNotFound
from typing import Optional, Union, List, TypeVar, Any, Generic, Callable, Dict
import unicodedata
from loguru import logger
from fast_string_match import closest_match
import json


# Define type variables for generic typing
CogT = TypeVar('CogT', bound=commands.Cog, covariant=True)
BotT = TypeVar('BotT', bound=commands.Bot, covariant=True)
ContextT = TypeVar('ContextT', bound=Context, covariant=True)
P = TypeVar('P')
T = TypeVar('T')


@dataclass
class MultipleArguments:
    first: str
    second: str


DISCORD_ROLE_MENTION = re.compile(r"<@&(\d+)>")
DISCORD_ID = re.compile(r"(\d+)")
DISCORD_USER_MENTION = re.compile(r"<@?(\d+)>")
DISCORD_CHANNEL_MENTION = re.compile(r"<#(\d+)>")
DISCORD_MESSAGE = re.compile(
    r"(?:https?://)?(?:canary\.|ptb\.|www\.)?discord(?:app)?.(?:com/channels|gg)/(?P<guild_id>[0-9]{17,22})/(?P<channel_id>[0-9]{17,22})/(?P<message_id>[0-9]{17,22})"
)


class NonStrictMessage(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        if match := DISCORD_MESSAGE.match(argument):
            return match.group(3)
        return argument


def has_permissions(**permissions):
    async def predicate(ctx: commands.Context):
        if (
            ctx.author.id in ctx.bot.owner_ids
            or ctx.author.guild_permissions.administrator
        ):
            return True

        missing_permissions = {
            perm
            for perm, required in permissions.items()
            if required and not getattr(ctx.author.guild_permissions, perm, False)
        }

        if missing_permissions:
            role_ids = {role.id for role in ctx.author.roles if role.is_assignable()}
            fakeperms = await ctx.bot.db.fetch(
                "SELECT role_id, perms FROM fakeperms WHERE guild_id = $1",
                ctx.guild.id,
            )

            for role_id, perms in fakeperms:
                if role_id in role_ids:
                    perms = {perm.strip() for perm in perms.split(",")}
                    missing_permissions -= perms

        if missing_permissions:
            raise commands.MissingPermissions(list(missing_permissions))

        return True

    return commands.check(predicate)


permissions = [
    "create_instant_invite",
    "kick_members",
    "ban_members",
    "administrator",
    "manage_channels",
    "manage_guild",
    "add_reactions",
    "view_audit_log",
    "priority_speaker",
    "stream",
    "read_messages",
    "manage_members",
    "send_messages",
    "send_tts_messages",
    "manage_messages",
    "embed_links",
    "attach_files",
    "read_message_history",
    "mention_everyone",
    "external_emojis",
    "view_guild_insights",
    "connect",
    "speak",
    "mute_members",
    "deafen_members",
    "move_members",
    "use_voice_activation",
    "change_nickname",
    "manage_nicknames",
    "manage_roles",
    "manage_webhooks",
    "manage_expressions",
    "use_application_commands",
    "request_to_speak",
    "manage_events",
    "manage_threads",
    "create_public_threads",
    "create_private_threads",
    "external_stickers",
    "send_messages_in_threads",
    "use_embedded_activities",
    "moderate_members",
    "use_soundboard",
    "create_expressions",
    "use_external_sounds",
    "send_voice_messages",
]

commands.has_permissions = has_permissions


@dataclass
class FakePermissionEntry:
    role: discord.Role
    permissions: Union[str, List[str]]


def validate_permissions(perms: Union[str, List[str]]):
    if isinstance(perms, str):
        perms = [perms]
    for p in perms:
        if p not in permissions:
            raise commands.CommandError(f"`{p}` is not a valid permission")
    return True


class FakePermissionConverter(commands.Converter):
    async def convert(
        self, ctx: Context, argument: str
    ) -> Optional[FakePermissionEntry]:
        args = [arg.strip() for arg in re.split(r"[ ,]", argument, 1)]
        if len(args) != 2:
            raise commands.CommandError("please include a `,` between arguments")
        args[0] = await Role().convert(ctx, args[0])
        perms = [p.strip().replace(" ", "_").lower() for p in args[1].split(",")]
        validate_permissions(perms)
        return FakePermissionEntry(role=args[0], permissions=perms)


class Argument(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> Optional[MultipleArguments]:
        args = [arg.strip() for arg in argument.split(",", 1)]
        if len(args) != 2:
            raise commands.CommandError("please include a `,` between arguments")
        return MultipleArguments(first=args[0], second=args[1])

class Location(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        async with ctx.typing():
            response = await ctx.bot.session.get(
                "https://api.weatherapi.com/v1/timezone.json",
                params=dict(key="0c5b47ed5774413c90b155456223004", q=argument),
            )
            if response.status == 200:
                data = await response.json()
                return data.get("location")
            raise commands.CommandError(f"Location **{argument}** not found")


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: "Context", argument: str
    ) -> Optional[Union[discord.Emoji, discord.PartialEmoji]]:
        try:
            return await super().convert(ctx, argument)
        except commands.EmojiNotFound:
            try:
                unicodedata.name(argument)
            except Exception:
                try:
                    unicodedata.name(argument[0])
                except Exception:
                    raise commands.EmojiNotFound(argument)
            return argument


class Sticker(GuildStickerConverter):
    async def convert(self, ctx: "Context", argument: str) -> Optional[GuildSticker]:
        if argument.isnumeric():
            try:
                return await super().convert(ctx, argument)
            except GuildStickerNotFound:
                raise
        return await super().convert(ctx, argument)


class TextChannel(commands.TextChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        argument = argument.replace(" ", "-")

        try:
            return await super().convert(ctx, argument)
        except Exception:
            pass

        try:
            channel_id = int(argument)
            if channel := ctx.guild.get_channel(channel_id):
                return channel
        except ValueError:
            pass

        channels = [
            c for c in ctx.guild.text_channels if argument.lower() in c.name.lower()
        ]
        if channels:
            return channels[0]

        raise commands.ChannelNotFound(f"Text channel `{argument}` not found")


class CategoryChannel(commands.CategoryChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            return await super().convert(ctx, argument)
        except commands.ChannelNotFound:
            for category in ctx.guild.categories:
                if argument.lower() in category.name.lower():
                    return category
            raise commands.ChannelNotFound(f"Category '{argument}' not found")


class VoiceChannel(commands.VoiceChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            return await super().convert(ctx, argument)
        except commands.ChannelNotFound:
            for vc in ctx.guild.voice_channels:
                if argument.lower() in vc.name.lower():
                    return vc
            raise commands.ChannelNotFound(f"Voice channel '{argument}' not found")


class User(commands.UserConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            return await super().convert(ctx, argument)
        except commands.UserNotFound:
            for user in ctx.bot.users:
                if argument.lower() in (
                    user.name.lower(),
                    user.display_name.lower(),
                    str(user).lower(),
                ):
                    return user
            try:
                if argument.isdigit():
                    return await ctx.bot.fetch_user(int(argument))
            except discord.NotFound:
                pass
            raise commands.UserNotFound(f"User '{argument}' not found")


class Member(commands.MemberConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            return await super().convert(ctx, argument)
        except commands.MemberNotFound:
            for member in ctx.guild.members:
                if argument.lower() in (
                    member.name.lower(),
                    member.display_name.lower(),
                ):
                    return member
            raise commands.MemberNotFound(f"Member '{argument}' not found")


class RolePosition(commands.CommandError):
    def __init__(self, message, **kwargs):
        self.message = message
        self.kwargs = kwargs
        super().__init__(self.message)


def link(url: str) -> bool:
    try:
        return any(
            url.lower().endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif")
        )
    except:
        return False


async def get_file_ext(url: str) -> str:
    file_ext1 = url.split("/")[-1].split(".")[1]
    return file_ext1.split("?")[0] if "?" in file_ext1 else file_ext1[:3]


class Image(commands.Converter):
    async def convert(self, ctx: Context, argument: str = None) -> Optional[bytes]:
        if argument is None:
            if not ctx.message.attachments:
                raise commands.BadArgument("No image was provided.")
            return await ctx.message.attachments[
                0
            ].read()  # Changed to read() instead of to_file()
        async with Session() as session:
            async with session.get(argument) as response:  # Changed request() to get()
                if response.status != 200:
                    raise commands.BadArgument("Failed to fetch image.")
                return await response.read()


class VoiceMessage(commands.Converter):
    async def convert(
        self, ctx: "Context", argument: str = None, fail: bool = True
    ) -> Optional[str]:
        if argument and link(argument):
            return argument
        if fail:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)
            assert False

    @staticmethod
    async def search(ctx: "Context", fail: bool = True) -> Optional[str]:
        async for message in ctx.channel.history(limit=50):
            if message.attachments:
                return message.attachments[0].url
        if fail:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)
            assert False


class Stickers(commands.Converter):
    async def convert(
        self, ctx: "Context", argument: str, fail: bool = True
    ) -> Optional[str]:
        if argument and link(argument):
            return argument
        if fail:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)
            assert False

    @staticmethod
    async def search(ctx: "Context", fail: bool = True) -> Optional[str]:
        if ctx.message.reference:
            return ctx.message.reference.resolved.stickers[0].url
        async for message in ctx.channel.history(limit=50):
            if message.stickers:
                return message.stickers[0].url
        if fail:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)
            assert False


class Attachment(commands.Converter):
    async def convert(
        self, ctx: "Context", argument: str, fail: bool = True
    ) -> Optional[str]:
        if argument and link(argument):
            return argument
        if fail:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)
            assert False

    @staticmethod
    async def search(ctx: "Context", fail: bool = False) -> Optional[str]:
        if ref := ctx.message.reference:
            logger.info("attachment search has a reference")
            if channel := ctx.guild.get_channel(ref.channel_id):
                if message := await channel.fetch_message(ref.message_id):
                    if message.attachments:
                        return message.attachments[0].url
                    logger.info("attachment.search failed: message has no attachments")
        if ctx.message.attachments:
            logger.info("message attachments exist")
            return ctx.message.attachments[0].url
        if fail:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)
            assert False
        return None


class Message(commands.MessageConverter):
    async def convert(self, ctx: Context, argument: str):
        if "discord.com/channels/" in argument:
            guild_id, channel_id, message_id = argument.split("/channels/")[1].split(
                "/"
            )
            if guild := ctx.bot.get_guild(guild_id):
                if channel := guild.get_channel(channel_id):
                    return await channel.fetch_message(message_id)
        return await ctx.channel.fetch_message(argument)


class NonAssignedRole(commands.RoleConverter):
    async def convert(self, ctx: Context, arg: str):
        roles = []
        arguments = [a.strip() for a in arg.split(",")]

        for argument in arguments:
            try:
                role = await super().convert(ctx, argument)
            except commands.RoleNotFound:
                role = discord.utils.find(
                    lambda r: argument.lower() in r.name.lower(), ctx.guild.roles
                )

            if not role or role.is_default():
                raise commands.RoleNotFound(argument)

            roles.append(role)

        return roles


class Role(commands.RoleConverter):
    def __init__(self, assign: bool = True):
        self.assign = assign

    async def convert(self, ctx: Context, arg: str):
        roles = []
        arguments = [a.strip() for a in arg.split(",")]

        for argument in arguments:
            role = None

            try:
                role = await super().convert(ctx, argument)
            except commands.RoleNotFound:
                # Make role lookup more efficient by using discord.utils.get
                role = discord.utils.get(
                    ctx.guild.roles, name=argument
                ) or discord.utils.find(
                    lambda r: argument.lower() in r.name.lower(), ctx.guild.roles
                )

            if not role or role.is_default():
                raise commands.RoleNotFound(argument)

            if self.assign:
                if role >= ctx.author.top_role and ctx.author.id != ctx.guild.owner_id:
                    msg = (
                        "the same as your top role"
                        if role == ctx.author.top_role
                        else "above your top role"
                    )
                    raise RolePosition(f"{role.mention} is **{msg}**")

                if (
                    role > ctx.guild.me.top_role
                    and ctx.author.id not in ctx.bot.owner_ids
                    and ctx.author.id != ctx.guild.owner_id
                ):
                    raise RolePosition(f"{role.mention} is **above my role**")

            roles.append(role)

        return roles


class Command(commands.Command, Generic[CogT, P, T]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def invoke_command(self, ctx: commands.Context) -> None:
        await super().invoke(ctx)

    async def invoke(self, ctx: commands.Context, /) -> None:
        try:
            # Use fetchrow asynchronously
            data = await ctx.bot.db.fetchrow(
                """
                SELECT channels 
                FROM disabled_commands 
                WHERE guild_id = $1 AND command = $2
                """,
                ctx.guild.id,
                ctx.command.qualified_name,
            )

            if not data:
                return await self.invoke_command(ctx)

            channels = json.loads(data["channels"])
            
            if not channels or ctx.channel.id in channels:
                return await ctx.reply(
                    "This command is disabled in this channel.",
                    mention_author=False,
                )
                
            return await self.invoke_command(ctx)
        except Exception as e:
            logger.error(f"Error in command invoke: {e}")
            return await self.invoke_command(ctx)


def Feature(*args, **kwargs):
    return commands.command(*args, **kwargs)


async def check_command_disabled(ctx: commands.Context) -> bool:
    """
    Check if a command is disabled in the current channel.
    Returns True if the command is disabled, False otherwise.
    """
    try:
        # Skip check for bot owners
        if await ctx.bot.is_owner(ctx.author):
            return False
            
        # Use fetchrow asynchronously
        data = await ctx.bot.db.fetchrow(
            """
            SELECT channels 
            FROM disabled_commands 
            WHERE guild_id = $1 AND command = $2
            """,
            ctx.guild.id,
            ctx.command.qualified_name,
        )

        if not data:
            return False

        channels = json.loads(data["channels"])
        
        if not channels or ctx.channel.id in channels:
            await ctx.reply(
                "This command is disabled in this channel.",
                mention_author=False,
            )
            return True
            
        return False
    except Exception as e:
        logger.error(f"Error checking if command is disabled: {e}")
        return False

def setup_command_disabled_check(bot):
    """
    Add the command disabled check to the bot's command_check function.
    This should be called during bot initialization.
    """
    original_command_check = bot.command_check
    
    async def new_command_check(ctx):
        if not await original_command_check(ctx):
            return False
            
        # Check if the command is disabled
        if ctx.guild and ctx.command:
            if await check_command_disabled(ctx):
                return False
                
        return True
        
    bot.command_check = new_command_check
