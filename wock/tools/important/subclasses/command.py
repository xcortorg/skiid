import re
import typing
import unicodedata
from contextlib import suppress
from dataclasses import dataclass
from typing import List, Optional, Union

import discord
from aiohttp import ClientSession as Session
from discord import GuildSticker
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.converter import (GuildStickerConverter,
                                            GuildStickerNotFound)
from fast_string_match import closest_match
from loguru import logger


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
        else:
            return argument


def has_permissions(**permissions):
    """Check if the user has permissions to execute the command (fake permissions included)"""

    async def predicate(ctx: commands.Context):
        if isinstance(ctx, int):
            return [
                permission for permission, value in permissions.items() if value is True
            ]
        if ctx.author.id in ctx.bot.owner_ids:
            return True

        if ctx.author.guild_permissions.administrator:
            return True

        for permission in permissions:
            missing_permissions = []
            if getattr(ctx.author.guild_permissions, permission) is not True:
                missing_permissions.append(permission)
            if missing_permissions:
                mroles = [r.id for r in ctx.author.roles if r.is_assignable()]
                data = await ctx.bot.db.fetch(
                    """SELECT role_id, perms FROM fakeperms WHERE guild_id = $1""",
                    ctx.guild.id,
                )
                if data:
                    for role_id, perms in data:
                        perm = perms
                        if role_id in mroles:
                            if "," in perm:
                                dperm = perm.split(",")
                                for sperm in dperm:
                                    try:
                                        missing_permissions.remove(str(sperm))
                                    except ValueError:
                                        continue
                            else:
                                for role_id, perm in data:
                                    if int(role_id) in mroles:
                                        try:
                                            missing_permissions.remove(str(perm))
                                        except ValueError:
                                            continue
            if missing_permissions:
                raise commands.MissingPermissions(missing_permissions)
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
        if perms in permissions:
            return True
        else:
            raise commands.CommandError(f"`{perms}` is not a valid permission")
    else:
        for p in perms:
            if p not in permissions:
                raise commands.CommandError(f"`{perms}` is not a valid permission")
    return True


class FakePermissionConverter(commands.Converter):
    async def convert(
        self, ctx: Context, argument: str
    ) -> Optional[FakePermissionEntry]:
        if "," in argument:
            args = argument.split(",", 1)
            args[0] = args[0].lstrip().rstrip()
            args[1] = args[1].lstrip().rstrip()
        else:
            if argument.count(" ") == 1:
                args = argument.split(" ", 1)
            else:
                raise commands.CommandError("please include a `,` between arguments")
        args[0] = await Role().convert(ctx, args[0])
        if "," in args[1]:
            perms = []
            for p in args[1].split(","):
                perms.append(p.lstrip().rstrip().replace(" ", "_").lower())
            args[1] = perms
        validate_permissions(args[1])
        return FakePermissionEntry(role=args[0], permissions=args[1])


class Argument(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> Optional[MultipleArguments]:
        if "," in argument:
            args = argument.split(",", 1)
            args[0] = args[0].lstrip().rstrip()
            args[1] = args[1].lstrip().rstrip()
        else:
            if argument.count(" ") == 1:
                args = argument.split(" ", 1)
            else:
                raise commands.CommandError("please include a `,` between arguments")
        return MultipleArguments(first=args[0], second=args[1])


class Location(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        argument = str(argument)
        async with ctx.typing():
            response = await ctx.bot.session.get(
                "https://api.weatherapi.com/v1/timezone.json",
                params=dict(key="0c5b47ed5774413c90b155456223004", q=argument),
            )

            if response.status == 200:
                data = await response.json()
                return data.get("location")
            else:
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
        """
        Convert the given argument to a GuildSticker object.

        Parameters:
            ctx (Context): The context of the command.
            argument (str): The argument to be converted.

        Returns:
            Optional[GuildSticker]: The converted GuildSticker object, or None if not found.

        Raises:
            GuildStickerNotfound: If the argument couldn't be converted.
        """

        if argument.isnumeric():
            int(argument)

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
        if match := DISCORD_ID.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        if match := DISCORD_CHANNEL_MENTION.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        else:
            channel = discord.utils.find(
                lambda m: m.name.lower() == argument.lower(),
                ctx.guild.text_channels,
            ) or discord.utils.find(
                lambda m: argument.lower() in m.name.lower(),
                ctx.guild.text_channels,
            )

            if channel:
                return channel
            else:
                raise discord.ext.commands.errors.ChannelNotFound(
                    f"channel `{channel}` not found"
                )


class CategoryChannel(commands.TextChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            return await super().convert(ctx, argument)
        except Exception:
            pass
        if match := DISCORD_ID.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        if match := DISCORD_CHANNEL_MENTION.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        else:
            channel = discord.utils.find(
                lambda m: m.name.lower() == argument.lower(),
                ctx.guild.categories,
            ) or discord.utils.find(
                lambda m: argument.lower() in m.name.lower(),
                ctx.guild.categories,
            )
            if channel:
                return channel
            else:
                raise discord.ext.commands.errors.ChannelNotFound(
                    f"channel `{channel}` not found"
                )


class VoiceChannel(commands.TextChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            return await super().convert(ctx, argument)
        except Exception:
            pass
        if match := DISCORD_ID.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        if match := DISCORD_CHANNEL_MENTION.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        else:
            channel = discord.utils.find(
                lambda m: m.name.lower() == argument.lower(),
                ctx.guild.voice_channels,
            ) or discord.utils.find(
                lambda m: argument.lower() in m.name.lower(),
                ctx.guild.voice_channels,
            )
            if channel:
                return channel
            else:
                raise discord.ext.commands.errors.ChannelNotFound(
                    f"channel `{channel}` not found"
                )


class User(commands.UserConverter):
    async def convert(self, ctx: Context, argument: str):
        member = None
        argument = str(argument)
        if match := DISCORD_ID.match(argument):
            member = ctx.bot.get_user(int(match.group(1)))
            if member is None:
                member = await ctx.bot.fetch_user(int(match.group(1)))
        elif match := DISCORD_USER_MENTION.match(argument):
            member = ctx.bot.get_user(int(match.group(1)))
            if member is None:
                member = await ctx.bot.fetch_user(int(match.group(1)))
        else:
            member = (
                discord.utils.find(
                    lambda m: m.name.lower() == argument.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.name.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower() == argument.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.display_name.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower() == argument.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in str(m).lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower().startswith(argument.lower()),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.name.lower() == argument.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.name.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower() == argument.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.display_name.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower() == argument.lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in str(m).lower(),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower().startswith(argument.lower()),
                    sorted(
                        ctx.bot.users,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
            )
        if not member:
            raise commands.UserNotFound(argument)
        return member


class Member(commands.MemberConverter):
    async def convert(self, ctx: Context, argument: str):
        member = None
        #        try: return await commands.MemberConverter().convert(ctx, argument)
        #       except Exception: pass
        argument = str(argument)
        if match := DISCORD_ID.match(argument):
            member = ctx.guild.get_member(int(match.group(1)))
        elif match := DISCORD_USER_MENTION.match(argument):
            member = ctx.guild.get_member(int(match.group(1)))
        else:
            return await commands.MemberConverter().convert(ctx, argument)
            member = (
                discord.utils.find(
                    lambda m: m.name.lower() == argument.lower(),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.name.lower(),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower() == argument.lower(),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.display_name.lower(),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower() == argument.lower(),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in str(m).lower(),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower().startswith(argument.lower()),
                    sorted(
                        ctx.channel.members,
                        key=lambda m: int(
                            m.discriminator
                            if not isinstance(m, discord.ThreadMember)
                            else 0
                        ),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.name.lower() == argument.lower(),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.name.lower(),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower() == argument.lower(),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.display_name.lower(),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: m.display_name.lower().startswith(argument.lower()),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower() == argument.lower(),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: argument.lower() in str(m).lower(),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
                or discord.utils.find(
                    lambda m: str(m).lower().startswith(argument.lower()),
                    sorted(
                        ctx.guild.members,
                        key=lambda m: int(m.discriminator),
                        reverse=False,
                    ),
                )
            )
        if not member:
            raise commands.MemberNotFound(argument)
        return member


class RolePosition(commands.CommandError):
    def __init__(self, message, **kwargs):
        self.message = message
        self.kwargs = kwargs
        super().__init__(self.message)


link = re.compile(
    r"https?:\/\/(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*(?:\.png|\.jpe?g|\.gif|\.jpg|))"
)


async def get_file_ext(url: str) -> str:
    file_ext1 = url.split("/")[-1].split(".")[1]
    if "?" in file_ext1:
        return file_ext1.split("?")[0]
    else:
        return file_ext1[:3]


class Image(commands.Converter):
    async def convert(self, ctx: Context, argument: str = None) -> Optional[bytes]:
        if argument is None:
            if len(ctx.message.attachments) == 0:
                raise commands.BadArgument("No image was provided.")
            else:
                return await ctx.message.attachments[0].to_file()
        else:
            #            if "discord.com" in argument or "discordapp.com" in argument:
            async with Session() as session:
                async with session.request("GET", f"{argument}") as response:
                    data = await response.read()
            #           else:
            #              async with Session() as session:
            #                 async with session.request(
            #                    "GET", f"https://proxy.rival.rocks?url={argument}"
            #               ) as response:
            #                 data = await response.read()
            if not data:
                raise commands.BadArgument("No image was provided.")
            return data


class VoiceMessage(commands.Converter):
    async def convert(
        self, ctx: "Context", argument: str = None, fail: bool = True
    ) -> typing.Optional[str]:
        """
        Convert the given argument to a link if it matches the link pattern.

        Parameters:
            ctx (Context): The context object representing the current execution context.
            argument (str): The argument to be converted.
            fail (bool, optional): Whether to raise an exception if the conversion fails. Defaults to True.

        Returns:
            Optional[str]: The converted link if the argument matches the link pattern, None otherwise.

        Raises:
            AssertionError: If fail is True and no link is found.
        """

        if match := link.match(argument):
            return match.group()

        if fail is True:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)

            assert False

    @staticmethod
    async def search(ctx: "Context", fail: bool = True) -> typing.Optional[str]:
        """
        Retrieves the URL of the first attachment in the last 50 messages in the given context's channel.

        Parameters:
            ctx (Context): The context object representing the current execution context.
            fail (bool, optional): Specifies whether an error should be raised if no attachment is found. Defaults to True.

        Returns:
            Optional[str]: The URL of the first attachment found, or None if no attachment is found.

        Raises:
            AssertionError: If fail is True and no link is found.
        """

        async for message in ctx.channel.history(limit=50):
            if message.attachments:
                return message.attachments[0].url

        if fail is True:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)

            assert False


class Stickers(commands.Converter):
    async def convert(
        self, ctx: "Context", argument: str, fail: bool = True
    ) -> typing.Optional[str]:
        """
        Convert the given argument to a link if it matches the link pattern.

        Parameters:
            ctx (Context): The context object representing the current execution context.
            argument (str): The argument to be converted.
            fail (bool, optional): Whether to raise an exception if the conversion fails. Defaults to True.

        Returns:
            Optional[str]: The converted link if the argument matches the link pattern, None otherwise.

        Raises:
            AssertionError: If fail is True and no link is found.
        """

        if match := link.match(argument):
            return match.group()

        if fail is True:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)

            assert False

    @staticmethod
    async def search(ctx: "Context", fail: bool = True) -> typing.Optional[str]:
        """
        Retrieves the URL of the first attachment in the last 50 messages in the given context's channel.

        Parameters:
            ctx (Context): The context object representing the current execution context.
            fail (bool, optional): Specifies whether an error should be raised if no attachment is found. Defaults to True.

        Returns:
            Optional[str]: The URL of the first attachment found, or None if no attachment is found.

        Raises:
            AssertionError: If fail is True and no link is found.
        """
        if ctx.message.reference:
            return ctx.message.reference.resolved.stickers[0].url
        async for message in ctx.channel.history(limit=50):
            if message.stickers:
                return message.stickers[0].url

        if fail is True:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)

            assert False


class Attachment(commands.Converter):
    async def convert(
        self, ctx: "Context", argument: str, fail: bool = True
    ) -> typing.Optional[str]:
        """
        Convert the given argument to a link if it matches the link pattern.

        Parameters:
            ctx (Context): The context object representing the current execution context.
            argument (str): The argument to be converted.
            fail (bool, optional): Whether to raise an exception if the conversion fails. Defaults to True.

        Returns:
            Optional[str]: The converted link if the argument matches the link pattern, None otherwise.

        Raises:
            AssertionError: If fail is True and no link is found.
        """

        if match := link.match(argument):
            return match.group()

        if fail is True:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)

            assert False

    @staticmethod
    async def search(ctx: "Context", fail: bool = False) -> typing.Optional[str]:
        """
        Retrieves the URL of the first attachment in the last 50 messages in the given context's channel.

        Parameters:
            ctx (Context): The context object representing the current execution context.
            fail (bool, optional): Specifies whether an error should be raised if no attachment is found. Defaults to True.

        Returns:
            Optional[str]: The URL of the first attachment found, or None if no attachment is found.

        Raises:
            AssertionError: If fail is True and no link is found.
        """
        if ref := ctx.message.reference:
            if channel := ctx.guild.get_channel(ref.channel_id):
                if message := await channel.fetch_message(ref.message_id):
                    try:
                        return message.attachments[0].url
                    except Exception as e:
                        logger.info(f"attachment.search failed with {str(e)}")
                        pass

        async for message in ctx.channel.history(limit=50):
            if message.attachments:
                return message.attachments[0].url

        if fail is True:
            with suppress(Exception):
                await ctx.send_help(ctx.command.qualified_name)

            assert False
        return None


class Message(commands.MessageConverter):
    async def convert(self, ctx: Context, argument: str):
        if "discord.com/channels/" in argument:
            arguments = argument.split("/channels/")
            guild_id, channel_id, message_id = arguments[1].split("/")
            if guild := ctx.bot.get_guild(guild_id):
                if channel := guild.get_channel(channel_id):
                    return await channel.fetch_message(message_id)
        else:
            return await ctx.channel.fetch_message(argument)


class NonAssignedRole(commands.RoleConverter):
    async def convert(self, ctx: Context, arg: str):
        role = None
        if " , " in arg:
            arguments = arg.split(" , ")
        elif "," in arg:
            arguments = arg.split(",")
        else:
            arguments = [arg]
        roles = []
        for argument in arguments:
            if match := DISCORD_ID.match(argument):
                role = ctx.guild.get_role(int(match.group(1)))
            elif match := DISCORD_ROLE_MENTION.match(argument):
                role = ctx.guild.get_role(int(match.group(1)))
            else:
                role = (
                    discord.utils.find(
                        lambda r: r.name.lower() == argument.lower(), ctx.guild.roles
                    )
                    or discord.utils.find(
                        lambda r: argument.lower() in r.name.lower(), ctx.guild.roles
                    )
                    or discord.utils.find(
                        lambda r: r.name.lower().startswith(argument.lower()),
                        ctx.guild.roles,
                    )
                )
            if not role or role.is_default():
                for role in ctx.guild.roles:
                    if (
                        argument.lower() in role.name.lower()
                        or role.name.lower() == argument.lower()
                        or role.name.lower().startswith(argument.lower())
                    ):
                        role = role
                if not role:
                    raise commands.RoleNotFound(argument)
            roles.append(role)
        return roles


class Role(commands.RoleConverter):
    def __init__(self, assign: bool = True):
        self.assign = assign

    async def convert(self, ctx: Context, arg: str):
        role = None
        if " , " in arg:
            arguments = arg.split(" , ")
        elif "," in arg:
            arguments = arg.split(",")
        else:
            arguments = [arg]
        roles = []
        for argument in arguments:
            role = None
            argument = argument.lstrip().rstrip()
            try:
                role = await super().convert(ctx, argument)
            except Exception:
                pass
            _roles = {r.name: r for r in ctx.guild.roles if r.is_assignable()}
            if role is None:
                if match := DISCORD_ID.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                elif match := DISCORD_ROLE_MENTION.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                else:
                    # role = (
                    #     discord.utils.find(
                    #         lambda r: r.name.lower() == argument.lower(), _roles
                    #     )
                    #     or discord.utils.find(
                    #         lambda r: argument.lower() in r.name.lower(), _roles
                    #     )
                    #     or discord.utils.find(
                    #         lambda r: r.name.lower().startswith(argument.lower()),
                    #         _roles,
                    #     )
                    # )
                    if match := closest_match(argument.lower(), list(_roles.keys())):
                        role = _roles[match]
                    else:
                        role = None
                if not role or role.is_default():
                    for role in ctx.guild.roles:
                        if (
                            argument.lower() in role.name.lower()
                            or role.name.lower() == argument.lower()
                            or role.name.lower().startswith(argument.lower())
                        ):
                            if role.is_assignable():
                                role = role
                    if not role:
                        raise commands.RoleNotFound(argument)
            if self.assign is True:
                if role < ctx.author.top_role or ctx.author.id == ctx.guild.owner_id:
                    #                    await ctx.send
                    if (
                        role <= ctx.guild.me.top_role
                        or ctx.author.id in ctx.bot.owner_ids
                        or ctx.author.id == ctx.guild.owner_id
                    ):
                        roles.append(role)
                    else:
                        #                        await ctx.fail(f"Role position is higher then my top role position")
                        #                        await ctx.send(f"{role.position} is higher then {ctx.guild.me.top_role.position}")

                        raise RolePosition(f"{role.mention} is **above my role**")
                else:
                    # await ctx.fail(f"Role position is higher then your top role position")
                    #                  await ctx.send(f"{role.position} is higher then {ctx.guild.me.top_role.position}")
                    #
                    if role == ctx.author.top_role and ctx.author != ctx.guild.owner:
                        m = "the same as your top role"
                    else:
                        m = "above your top role"
                    raise RolePosition(f"{role.mention} is **{m}**")
            else:
                roles.append(role)
        return roles


class Command(commands.Command):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def invoke_command(self, ctx):
        await super().invoke(ctx)

    async def invoke(self, ctx: commands.Context, /):
        data = await ctx.bot.db.fetchrow(
            "SELECT * FROM disabled_commands WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            ctx.command.qualified_name,
        )

        if data and data.status and data.whitelist and ctx.author.id in data.whitelist:
            return await self.invoke_command(ctx)
        elif data and data.status:
            return await ctx.reply("This command is disabled in this server.")
        else:
            return await self.invoke_command(ctx)


def Feature(*args, **kwargs):
    return commands.command(cls=Command, *args, **kwargs)
