from discord.ext import commands
from discord.ext.commands import (
    MemberNotFound,
    CommandError,
    Converter,
    GuildConverter as GuildConv,
    Command,
    Group,
    PartialEmojiConverter,
)
from .embed import Script
from ..patch.context import Context
import discord
from typing import Optional, Union, List, TYPE_CHECKING, Tuple, Any, Dict
import os
from discord.ext.commands.converter import GuildStickerConverter, GuildStickerNotFound
import re
import pytz
from discord import Client, Message
import unicodedata
from aiohttp import ClientSession as Session, ClientResponse
from fast_string_match import closest_match_distance as cmd, closest_match
from dataclasses import dataclass
from .exceptions import RolePosition
from munch import Munch
from typing_extensions import Type
from .music import Filters
from loguru import logger
from lib.classes.processing import human_join
from var.variables import regions, EMOJI_REGEX, DEFAULT_EMOJIS
from var.config import CONFIG
from lib.views.roles import to_style
import humanfriendly
import humanize
from ..worker import offloaded
from datetime import datetime
from pydantic import BaseModel


class MessageLink(BaseModel):
    guild_id: int
    channel_id: int
    message_id: int

    async def fetch(self: "MessageLink", bot: Client) -> Optional[Message]:
        if not (guild := bot.get_guild(self.guild_id)):
            return
        if not (channel := guild.get_channel(self.channel_id)):
            return
        return await bot.fetch_message(channel, self.message_id)

    @classmethod
    def from_link(cls: Type["MessageLink"], link: str):
        """Parse a message link and return a MessageLink object."""
        if "channels/" in link:
            guild_id, channel_id, message_id = link.split("channels/")[1].split("/")
            return cls(
                guild_id=int(guild_id),
                channel_id=int(channel_id),
                message_id=int(channel_id),
            )
        else:
            raise CommandError(f"no valid message link detected in `{link}`")

    @classmethod
    def from_id(cls: Type["MessageLink"], ctx: Context, message_id: int):
        return cls(
            guild_id=ctx.guild.id, channel_id=ctx.channel.id, message_id=message_id
        )


_ID_REGEX = re.compile(r"([0-9]{15,20})$")
DISCORD_ROLE_MENTION = re.compile(r"<@&(\d+)>")
DISCORD_ID = re.compile(r"(\d+)")
DISCORD_USER_MENTION = re.compile(r"<@?(\d+)>")
DISCORD_CHANNEL_MENTION = re.compile(r"<#(\d+)>")
DISCORD_MESSAGE = re.compile(
    r"(?:https?://)?(?:canary\.|ptb\.|www\.)?discord(?:app)?.(?:com/channels|gg)/(?P<guild_id>[0-9]{17,22})/(?P<channel_id>[0-9]{17,22})/(?P<message_id>[0-9]{17,22})"
)
PERCENTAGE = re.compile(r"(?P<percentage>\d+)%")
BITRATE = re.compile(r"(?P<bitrate>\d+)kbps")

EVENTS = [
    "typing",
    "message",
    "message_delete",
    "bulk_message_delete",
    "message_edit",
    "reaction_add",
    "reaction_remove",
    "reaction_clear",
    "reaction_clear_emoji",
    "guild_join",
    "guild_remove",
    "guild_update",
    "guild_role_create",
    "guild_role_delete",
    "guild_role_update",
    "guild_emojis_update",
    "guild_available",
    "guild_unavailable",
    "member_join",
    "member_remove",
    "member_update",
    "user_update",
    "voice_state_update",
    "guild_channel_create",
    "guild_channel_delete",
    "guild_channel_update",
    "private_channel_create",
    "private_channel_delete",
    "private_channel_update",
    "invite_create",
    "invite_delete",
    "group_join",
    "group_remove",
    "integration_create",
    "integration_update",
    "integration_delete",
    "guild_integrations_update",
    "webhooks_update",
    "presence_update",
    "guild_scheduled_event_create",
    "guild_scheduled_event_update",
    "guild_scheduled_event_delete",
    "guild_scheduled_event_user_add",
    "guild_scheduled_event_user_remove",
    "interaction",
]

EVENT_MAPPING = {
    "on_media_repost": ["repost", "reposter"],
    "on_afk_check": ["afk"],
    "on_message_delete": ["snipe"],
    "on_message_edit": ["editsnipe"],
    "on_reaction_remove": ["reactsnipe", "reactionsnipe", "rs"],
}


def match_event(event_name: str, return_value: Optional[bool] = False):
    if match := EVENT_MAPPING.get(event_name.lower()):
        if return_value:
            return match[0]
        return event_name
    for key, values in EVENT_MAPPING.items():
        if event_name.lower() in values:
            if return_value:
                return event_name.lower()
            return key


class MessageConverter(Converter[str]):
    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Message:
        if "channels" not in argument:
            try:
                id = int(argument)
            except Exception:
                raise commands.BadArgument("Invalid message ID or URL")
            link = MessageLink.from_id(ctx, id)
        else:
            link = MessageLink.from_url(argument)
        return await link.fetch(ctx.bot)

    @classmethod
    async def fallback(cls, ctx: Context) -> Message:
        if reference := ctx.message.reference:
            if not (channel := ctx.bot.get_channel(reference.channel_id)):
                raise commands.BadArgument("Reference channel not found")
            if not (message := await channel.fetch_message(reference.message_id)):
                raise commands.BadArgument("Reference message not found")
            return message
        raise commands.BadArgument("No message reference found")


class position:
    HH_MM_SS = re.compile(r"(?P<h>\d{1,2}):(?P<m>\d{1,2}):(?P<s>\d{1,2})")
    MM_SS = re.compile(r"(?P<m>\d{1,2}):(?P<s>\d{1,2})")
    HUMAN = re.compile(r"(?:(?P<m>\d+)\s*m\s*)?(?P<s>\d+)\s*[sm]")
    OFFSET = re.compile(r"(?P<s>(?:\-|\+)\d+)\s*s")


async def get_int(argument: str):
    t = ""
    for s in argument:
        try:
            d = int(s)
            t += f"{d}"
        except Exception:
            pass
    return t


class Timeout(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        try:
            converted = humanfriendly.parse_timespan(argument)
        except Exception:
            converted = humanfriendly.parse_timespan(
                f"{await get_int(argument)} minutes"
            )
        if converted >= 40320:
            raise CommandError("discord's API is limited to `28 days` for timeouts")
        return converted


@offloaded
def get_timezone(location: str) -> str:
    from geopy.geocoders import Nominatim
    from timezonefinder import TimezoneFinder

    obj = TimezoneFinder()
    geolocator = Nominatim(user_agent="Bleed-Bot")
    lad = location
    location = geolocator.geocode(lad)
    obj = TimezoneFinder()
    result = obj.timezone_at(lng=location.longitude, lat=location.latitude)
    return result


class Timezone(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        try:
            timezone = pytz.timezone(await get_timezone(argument))
            return
        except:
            raise CommandError(f"No timezone found from query `{argument[:25]}`")


class Expiration(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        try:
            converted = humanfriendly.parse_timespan(argument)
        except Exception:
            converted = humanfriendly.parse_timespan(
                f"{await get_int(argument)} minutes"
            )
        if ctx.command:
            if ctx.command.qualified_name == "timeout":
                if converted >= 40320:
                    raise CommandError(
                        "discord's API is limited to `28 days` for timeouts"
                    )
        return converted


class EmbedConverter(commands.Converter):
    async def convert(self, ctx: Context, code: str):
        c = code
        c = c.replace("{level}", "")
        try:
            s = Script(c, ctx.author)
            await s.compile()
        except Exception as e:
            raise e
        return code


class StyleConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        if style := to_style(argument.lower()):
            return style
        raise CommandError("**Style** must be one of `blurple`, `gray`, `green`, `red`")


class AntinukeAction(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        _action_ = argument.lower().lstrip().rstrip()
        if _action_ in ("strip", "stripstaff"):
            return "stripstaff"
        elif _action_ == "ban":
            return "ban"
        elif _action_ == "kick":
            return "kick"
        else:
            raise CommandError(
                "the only valid actions are `ban`, `kick`, and `stripstaff`"
            )


class ModuleConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        cog_names = [c.name for c in ctx.bot.cogs]
        if argument.lower() in cog_names:
            return argument.lower()
        else:
            raise CommandError(f"No module found named `{argument[:25]}`")


class EventConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        if match := match_event(argument):
            return match
        else:
            raise CommandError(f"No module found named `{argument[:25]}`")


class Image(commands.Converter):
    async def convert(self, ctx: Context, argument: str = None) -> Optional[bytes]:
        if argument is None:
            if len(ctx.message.attachments) == 0:
                if ref := await ctx.bot.get_reference(ctx.message):
                    if len(ref.attachments) > 0:
                        return await ref.attachments[0].save()
                raise commands.BadArgument("No image was provided.")
            else:
                return await ctx.message.attachments[0].to_file()
        else:
            async with Session() as session:
                async with session.request("GET", f"{argument}") as response:
                    data = await response.read()

            if not data:
                raise commands.BadArgument("No image was provided.")
            return data


class Boolean(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        true = ["enable", "on", "yes", "t", "e", "y", "true"]
        false = ["disable", "off", "no", "f", "d", "n", "false"]
        if argument.lower() in true:
            return True
        elif argument.lower() in false:
            return False
        else:
            raise CommandError(f"{argument[:20]} is not a valid setting")


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

        if await ctx.bot.db.fetchrow(
            """SELECT * FROM command_allowed WHERE guild_id = $1 AND user_id = $2 AND command = $3""",
            ctx.guild.id,
            ctx.author.id,
            ctx.command.qualified_name.lower(),
        ):
            return True

        for permission in permissions:
            missing_permissions = []
            if getattr(ctx.author.guild_permissions, permission) is not True:
                missing_permissions.append(permission)
            if missing_permissions:
                mroles = [r.id for r in ctx.author.roles if r.is_assignable()]
                data = await ctx.bot.db.fetch(
                    """SELECT role_id, permissions FROM fake_permissions WHERE guild_id = $1""",
                    ctx.guild.id,
                )
                if data:
                    for row in data:
                        if row.role_id in mroles:
                            for sperm in row.permissions:
                                try:
                                    missing_permissions.remove(str(sperm))
                                except ValueError:
                                    continue
            if "server_owner" in missing_permissions:
                if ctx.author.id == ctx.guild.owner_id:
                    return True
            if "antinuke_admin" in missing_permissions:
                if ctx.author.id in ctx.bot.owner_ids:
                    return True
                admins = set(
                    await ctx.bot.db.fetchval(
                        """
                        SELECT admins FROM antinuke
                        WHERE guild_id = $1
                        """,
                        ctx.guild.id,
                    )
                    or []
                )
                admins.add(ctx.guild.owner_id)
                if ctx.author.id in admins:
                    return True
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
    async def convert(self, ctx: Context, argument: str):
        if "," in argument:
            args = argument.split(",")
        else:
            args = [argument]
        args = [arg.replace(" ", "_") for arg in args]
        perms = []
        for p in args:
            perms.append(p.lstrip().rstrip().replace(" ", "_").lower())
        args = perms
        validate_permissions(args)
        return args


class Emoji(commands.EmojiConverter):
    async def convert(
        self, ctx: "Context", argument: str
    ) -> Optional[Union[discord.Emoji, discord.PartialEmoji]]:
        try:
            return await super().convert_(ctx, argument)

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
    async def convert(
        self, ctx: "Context", argument: str
    ) -> Optional[discord.GuildSticker]:
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
                return await super().convert_(ctx, argument)

            except GuildStickerNotFound:
                raise

        return await super().convert_(ctx, argument)


class TextChannel(commands.TextChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        argument = argument.replace(" ", "-")
        try:
            return await super().convert_(ctx, argument)
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


class GuildChannel(commands.GuildChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            if c := await super().convert_(ctx, argument):
                return c
        except Exception:
            pass
        if match := DISCORD_ID.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        if match := DISCORD_CHANNEL_MENTION.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        else:
            channel = (
                discord.utils.find(
                    lambda m: m.name.lower() == argument.lower(),
                    ctx.guild.channels,
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.name.lower(),
                    ctx.guild.channels,
                )
                or discord.utils.find(
                    lambda m: str(m.id) == argument, ctx.guild.channels
                )
            )
            if channel:
                return channel
            else:
                raise discord.ext.commands.errors.ChannelNotFound(f"`{argument}`")


class CategoryChannel(commands.TextChannelConverter):
    async def convert(self, ctx: Context, argument: str):
        try:
            return await super().convert_(ctx, argument)
        except Exception:
            pass
        if match := DISCORD_ID.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        if match := DISCORD_CHANNEL_MENTION.match(argument):
            channel = ctx.guild.get_channel(int(match.group(1)))
        else:
            channel = (
                discord.utils.find(
                    lambda m: m.name.lower() == argument.lower(),
                    ctx.guild.categories,
                )
                or discord.utils.find(
                    lambda m: argument.lower() in m.name.lower(),
                    ctx.guild.categories,
                )
                or discord.utils.find(
                    lambda m: str(m.id) == argument, ctx.guild.categories
                )
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
            return await super().convert_(ctx, argument)
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


class MemberConvert(commands.MemberConverter):
    async def convert(
        self, ctx: Context, arg: Union[int, str]
    ) -> Optional[discord.Member]:
        _id = _ID_REGEX.match(arg) or re.match(r"<@!?([0-9]{15,20})>$", arg)
        if _id is not None:
            _id = int(_id.group(1))
            if member := ctx.guild.get_member(_id):
                return member
            else:
                raise MemberNotFound(arg)
        names = [
            {m.global_name: id for m in ctx.guild.members if m.global_name is not None},
            {m.nick: m.id for m in ctx.guild.members if m.nick is not None},
            {
                m.display_name: m.id
                for m in ctx.guild.members
                if m.display_name is not None
            },
            {m.name: m.id for m in ctx.guild.members if m.name is not None},
        ]
        matches = {}
        for i, obj in enumerate(names, start=0):
            if match := cmd(arg, list(obj.keys())):
                matches[match] = i
        final = cmd(arg, list(matches.keys()))
        return ctx.guild.get_member(names[matches[final]][final])


class AssignedRole(commands.RoleConverter):
    async def convert(self, ctx: Context, arg: str):
        self.assign = True
        role = None
        arguments = [arg]
        roles = []
        for argument in arguments:
            role = None
            argument = argument.lstrip().rstrip()
            try:
                role = await super().convert_(ctx, argument)
            except Exception:
                pass
            _roles = {r.name: r for r in ctx.guild.roles if r.is_assignable()}
            if role is None:
                if match := DISCORD_ID.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                elif match := DISCORD_ROLE_MENTION.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                else:
                    if match := closest_match(argument.lower(), list(_roles.keys())):
                        try:
                            role = _roles[match]
                        except Exception:
                            role = None
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
                    if (
                        role <= ctx.guild.me.top_role
                        or ctx.author.id in ctx.bot.owner_ids
                        or ctx.author.id == ctx.guild.owner_id
                    ):
                        roles.append(role)
                    else:
                        raise RolePosition(f"{role.mention} is **above my role**")
                else:
                    if role == ctx.author.top_role and ctx.author != ctx.guild.owner:
                        m = "the same as your top role"
                    else:
                        m = "above your top role"
                    raise RolePosition(f"{role.mention} is **{m}**")
            else:
                roles.append(role)
        return roles[0]


class Role(commands.RoleConverter):
    async def convert(self, ctx: Context, arg: str):
        self.assign = False
        role = None
        roles = []
        arguments = [arg]
        for argument in arguments:
            role = None
            argument = argument.lstrip().rstrip()
            try:
                role = await super().convert_(ctx, argument)
            except Exception:
                pass
            _roles = {r.name: r for r in ctx.guild.roles if r.is_assignable()}
            if role is None:
                if match := DISCORD_ID.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                elif match := DISCORD_ROLE_MENTION.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                else:
                    if match := closest_match(argument.lower(), list(_roles.keys())):
                        try:
                            role = _roles[match]
                        except Exception:
                            role = None
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
            roles.append(role)
        return roles[0]


class MultipleRoles(commands.RoleConverter):
    async def convert(self, ctx: Context, arg: str):
        self.assign = True
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
                role = await super().convert_(ctx, argument)
            except Exception:
                pass
            _roles = {r.name: r for r in ctx.guild.roles if r.is_assignable()}
            if role is None:
                if match := DISCORD_ID.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                elif match := DISCORD_ROLE_MENTION.match(argument):
                    role = ctx.guild.get_role(int(match.group(1)))
                else:
                    if match := closest_match(argument.lower(), list(_roles.keys())):
                        try:
                            role = _roles[match]
                        except Exception:
                            role = None
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
            roles.append(role)
        return roles


class Percentage(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        if argument.isdigit():
            argument = int(argument)

        elif match := PERCENTAGE.match(argument):
            argument = int(match.group(1))

        else:
            argument = 0

        if argument < 0 or argument > 100:
            raise CommandError("Please **specify** a valid percentage")

        return argument


class Position(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = argument.lower()
        player = ctx.voice_client
        ms: int = 0

        if ctx.invoked_with == "ff" and not argument.startswith("+"):
            argument = f"+{argument}"

        elif ctx.invoked_with == "rw" and not argument.startswith("-"):
            argument = f"-{argument}"

        if match := position.HH_MM_SS.fullmatch(argument):
            ms += (
                int(match.group("h")) * 3600000
                + int(match.group("m")) * 60000
                + int(match.group("s")) * 1000
            )

        elif match := position.MM_SS.fullmatch(argument):
            ms += int(match.group("m")) * 60000 + int(match.group("s")) * 1000

        elif (match := position.OFFSET.fullmatch(argument)) and player:
            ms += player.position + int(match.group("s")) * 1000

        elif match := position.HUMAN.fullmatch(argument):
            if m := match.group("m"):
                if match.group("s") and argument.endswith("m"):
                    raise CommandError(f"Position `{argument}` is not valid")

                ms += int(m) * 60000

            elif s := match.group("s"):
                if argument.endswith("m"):
                    ms += int(s) * 60000
                else:
                    ms += int(s) * 1000

        else:
            raise CommandError(f"Position `{argument}` is not valid")

        return ms


class Timeframe(Converter[str]):
    def __init__(self: "Timeframe", period: str):
        self.period = period

    def __str__(self: "Timeframe") -> str:
        if self.period == "7day":
            return "weekly"

        elif self.period == "1month":
            return "monthly"

        elif self.period == "3month":
            return "past 3 months"

        elif self.period == "6month":
            return "past 6 months"

        elif self.period == "12month":
            return "yearly"

        return "overall"

    @classmethod
    async def convert(
        cls: Type["Timeframe"], ctx: Context, argument: str
    ) -> "Timeframe":
        if argument in (
            "weekly",
            "week",
            "1week",
            "7days",
            "7day",
            "7ds",
            "7d",
        ):
            return cls("7day")

        elif argument in (
            "monthly",
            "month",
            "1month",
            "1m",
            "30days",
            "30day",
            "30ds",
            "30d",
        ):
            return cls("1month")

        elif argument in (
            "3months",
            "3month",
            "3ms",
            "3m",
            "90days",
            "90day",
            "90ds",
            "90d",
        ):
            return cls("3month")

        elif argument in (
            "halfyear",
            "6months",
            "6month",
            "6mo",
            "6ms",
            "6m",
            "180days",
            "180day",
            "180ds",
            "180d",
        ):
            return cls("6month")

        elif argument in (
            "yearly",
            "year",
            "yr",
            "1year",
            "1y",
            "12months",
            "12month",
            "12mo",
            "12ms",
            "12m",
            "365days",
            "365day",
            "365ds",
            "365d",
        ):
            return cls("12month")

        return cls("overall")


class Artist(Converter[str]):
    @classmethod
    async def fallback(self: "Artist", ctx: Context) -> str:
        lastfm = ctx.bot.get_cog("LastFM")
        if not lastfm:
            raise CommandError("No LastFM Cog Found")

        if not hasattr(ctx, "_Commands__lastfm") and not hasattr(
            ctx, "_Context__lastfm"
        ):
            logger.info(f"{dir(ctx)}")
            await lastfm.cog_check(ctx)
        tracks: List[Munch] = await lastfm.client.request(
            method="user.getrecenttracks",
            username=getattr(
                ctx, "_Commands__lastfm", getattr(ctx, "_Context__lastfm", None)
            ).username,
            slug="recenttracks.track",
            limit=1,
        )
        if not tracks:
            raise CommandError(
                f"Recent tracks aren't available for `{getattr(ctx, '_Commands__lastfm', getattr(ctx, '_Context__lastfm', None)).username}`!"
            )

        track = tracks[0]
        return track.artist["#text"]

    @classmethod
    async def convert(self: "Artist", ctx: Context, argument: str) -> str:
        lastfm = ctx.bot.get_cog("LastFM")
        if not lastfm:
            return
        if not hasattr(ctx, "_Commands__lastfm") and not hasattr(
            ctx, "_Context__lastfm"
        ):
            logger.info(f"{dir(ctx)}")
            await lastfm.cog_check(ctx)
        artist: Munch = await lastfm.client.request(
            method="artist.getinfo",
            artist=argument,
            slug="artist",
        )
        if not artist:
            raise CommandError(f"Artist matching `{argument}` not found!")

        return artist.name


class Album:
    def __init__(self: "Album", name: str, artist: str):
        self.name = name
        self.artist = artist

    @classmethod
    async def fallback(cls: Type["Album"], ctx: Context) -> "Album":
        lastfm = ctx.bot.get_cog("LastFM")
        if not lastfm:
            return
        if not hasattr(ctx, "_Commands__lastfm") and not hasattr(
            ctx, "_Context__lastfm"
        ):
            await lastfm.cog_check(ctx)

        tracks: List[Munch] = await lastfm.client.request(
            method="user.getrecenttracks",
            username=getattr(
                ctx, "_Commands__lastfm", getattr(ctx, "_Context__lastfm", None)
            ).username,
            slug="recenttracks.track",
            limit=1,
        )
        if not tracks:
            raise CommandError(
                f"Recent tracks aren't available for `{getattr(ctx, '_Commands__lastfm', getattr(ctx, '_Context__lastfm', None)).username}`!"
            )

        track = tracks[0]
        if not track.album:
            raise CommandError("Your current track doesn't have an album!")

        return cls(
            name=track.album["#text"],
            artist=track.artist["#text"],
        )

    @classmethod
    async def convert(cls: Type["Album"], ctx: Context, argument: str) -> str:
        lastfm = ctx.bot.get_cog("LastFM")
        if not lastfm:
            return
        if not hasattr(ctx, "_Commands__lastfm") and not hasattr(
            ctx, "_Context__lastfm"
        ):
            await lastfm.cog_check(ctx)

        albums: List[Munch] = await lastfm.client.request(
            slug="results.albummatches.album",
            method="album.search",
            album=argument,
        )
        if not albums:
            raise CommandError(f"Album matching `{argument}` not found!")

        album = albums[0]
        return cls(
            name=album.name,
            artist=album.artist,
        )


class Track:
    def __init__(self: "Track", name: str, artist: str):
        self.name = name
        self.artist = artist

    @classmethod
    async def fallback(cls: Type["Track"], ctx: Context) -> "Track":
        lastfm = ctx.bot.get_cog("LastFM")
        if not lastfm:
            return
        if not hasattr(ctx, "_Commands__lastfm") and not hasattr(
            ctx, "_Context__lastfm"
        ):
            await lastfm.cog_check(ctx)

        tracks: List[Munch] = await lastfm.client.request(
            method="user.getrecenttracks",
            username=getattr(
                ctx, "_Commands__lastfm", getattr(ctx, "_Context__lastfm", None)
            ).username,
            slug="recenttracks.track",
            limit=1,
        )
        if not tracks:
            raise CommandError(
                f"Recent tracks aren't available for `{getattr(ctx, '_Commands__lastfm', getattr(ctx, '_Context__lastfm', None)).username}`!"
            )

        track = tracks[0]
        return cls(
            name=track.name,
            artist=track.artist["#text"],
        )

    @classmethod
    async def convert(cls: Type["Track"], ctx: Context, argument: str) -> str:
        lastfm = ctx.bot.get_cog("LastFM")
        if not lastfm:
            return
        if not hasattr(ctx, "_Commands__lastfm") and not hasattr(
            ctx, "_Context__lastfm"
        ):
            await lastfm.cog_check(ctx)

        tracks: List[Munch] = await lastfm.client.request(
            slug="results.trackmatches.track",
            method="track.search",
            track=argument,
        )
        if not tracks:
            raise CommandError(f"Track matching `{argument}` not found!")

        track = tracks[0]
        return cls(
            name=track.name,
            artist=track.artist,
        )


class Bitrate(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        if argument.isdigit():
            argument = int(argument)

        elif match := BITRATE.match(argument):
            argument = int(match.group(1))

        else:
            argument = 0

        if argument < 8:
            raise CommandError("**Bitrate** cannot be less than `8 kbps`!")

        elif argument > int(ctx.guild.bitrate_limit / 1000):
            raise CommandError(
                f"`{argument} kbps` cannot be **greater** than `{int(ctx.guild.bitrate_limit / 1000)} kbps`!"
            )

        return argument


class Region(Converter):
    async def convert(self, ctx: Context, argument: str) -> int:
        argument = argument.lower().replace(" ", "-")
        if argument not in regions:
            raise CommandError(
                "**Voice region** must be one of "
                + human_join([f"`{region}`" for region in regions])
            )

        return argument


def validate_discord_guild_id(guild_id: str) -> bool:
    # Check if the guild_id consists only of digits and is 17 to 19 digits long
    return bool(re.fullmatch(r"^\d{17,19}$", guild_id))


async def get_a_response(response: ClientResponse):
    try:
        return await response.json()
    except Exception:

        pass
    try:
        return await response.text()
    except Exception:
        pass
    return await response.read()


async def get_response(response: ClientResponse):
    if response.content_type == "text/plain":
        return await response.text()
    elif response.content_type.startswith(("image/", "video/", "audio/")):
        return await response.read()
    elif response.content_type == "text/html":
        return await response.text()
    elif response.content_type in (
        "application/json",
        "application/octet-stream",
        "text/javascript",
    ):
        try:
            data: Dict = await response.json(content_type=None)
        except Exception:
            return response
    else:
        return None


def convert_str(s: str) -> Optional[int]:
    try:
        integer = int(s)
        if validate_discord_guild_id(s):
            return integer
        else:
            return None
    except Exception:
        return None


async def fetch_guild(guild_id: int) -> Tuple[int, Any]:
    async with Session() as session:
        async with session.get(
            f"https://discord.com/api/v10/guilds/{guild_id}",
            headers={"Authentication": f"Bot {os.environ['TOKEN']}"},
        ) as response:
            data = await get_response(response)
            status = int(response.status)
    return status, data


def get_valid_ints(message: Union[discord.Message, str]) -> list:
    content = message if isinstance(message, str) else message.content
    try:
        try:
            if " " not in content:
                g = int(content)
                if check := validate_discord_guild_id(content):
                    return [g]
        except Exception:
            pass
    except Exception:
        pass
    return [
        convert_str(d)
        for d in (part for part in content.split() for part in part.split())
        if convert_str(d) is not None
    ]


async def fetch_invite(bot: Client, invite: Union[discord.Invite, str]) -> int:
    if isinstance(invite, str):
        invite = await bot.fetch_invite(invite)
        guild = invite.guild
        if isinstance(guild, discord.Guild):
            return guild.id
        elif isinstance(guild, discord.Object):
            return guild.id
        else:
            try:
                return invite.guild.id
            except Exception:
                return invite.id
    if isinstance(invite, discord.Invite):
        guild = invite.guild
        if isinstance(guild, discord.Guild):
            return guild.id
        elif isinstance(guild, discord.Object):
            return guild.id
        else:
            try:
                return invite.guild.id
            except Exception:
                return invite.id
    return None


class GConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> Optional[int]:
        if "https://" in argument:
            invite = await ctx.bot.fetch_invite(argument)
            guild = invite.guild
            if isinstance(guild, discord.Guild):
                return guild.id
            elif isinstance(guild, discord.Object):
                return guild.id
            else:
                try:
                    return invite.guild.id
                except Exception:
                    return invite.id
        else:
            try:
                return int(argument)
            except Exception:
                return None


class GuildConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str) -> Optional[int]:
        try:
            invites = ctx.message.invites
            if invites:
                invite = await ctx.bot.fetch_invite(invites[0])
                guild = invite.guild
                if isinstance(guild, discord.Guild):
                    return guild.id
                elif isinstance(guild, discord.Object):
                    return guild.id
                else:
                    try:
                        return invite.guild.id
                    except Exception:
                        return invite.id
            else:
                try:
                    guild = await GuildConv().convert(ctx, argument)
                    if guild:
                        return guild.id
                except Exception:
                    pass
                ints = get_valid_ints(argument)
                if len(ints) == 0:
                    raise commands.CommandError("No Guild IDS were Found")
                return ints[0]
        except Exception:
            return None


GLOBAL_COMMANDS = {}


def find_command(bot, query):
    query = query.lower()
    if len(GLOBAL_COMMANDS) == 4000:
        _commands = [c for c in bot.walk_commands()]
        commands = {}
        # commands = [c for c in _commands if c.qualified_name.startswith(query) or query in c.qualified_name]
        for command in _commands:
            if isinstance(command, Group):
                aliases = command.aliases
                for cmd in command.walk_commands():
                    for a in aliases:
                        commands[
                            f"{cmd.qualified_name.replace(f'{command.qualified_name}', f'{a}')}"
                        ] = cmd
                    commands[cmd.qualified_name] = cmd
                commands[command.qualified_name] = command
            else:
                commands[command.qualified_name] = command
                for alias in command.aliases:
                    commands[alias] = command
        GLOBAL_COMMANDS.update(commands)
    if not bot.command_dict:
        bot.get_command_dict()
    if query in bot.command_dict:
        return bot.get_command(query)
    if MATCH := closest_match(query, bot.command_dict):
        return bot.get_command(MATCH)
    else:
        return None


class CommandConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        argument = argument.replace("_", " ").lower()
        if command := ctx.bot.get_command(argument):
            return command
        if not (command := find_command(ctx.bot, argument)):
            raise CommandError(f"Could not find a command named `{argument[:25]}`")
        return command


# class CommaConverter(commands.Converter):
#     async def convert(self, ctx: Context, argument: str):
#         argument = argument.split("--", 1)[0]
#         arguments = [a.lstrip().rstrip() for a in argument.split(",") if len(a) > 0]
#         if len(arguments) == 1:
#             arguments = [a.lstrip().rstrip() for a in argument.split(" ") if len(a) > 0]
#         logger.info(arguments)
#         logger.info(argument)
#         return arguments


class KickChannelConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        try:
            check = await ctx.bot.services.kick.get_channel(argument)
        except Exception:
            raise CommandError(
                f"No **[Kick User](https://kick.com/)** found under the username [`{argument}`](https://kick.com/{argument.replace(' ', '+')})"
            )
        return argument


class SafeSnowflake(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        author = ctx.author
        try:
            member = await MemberConvert().convert(ctx, argument)
        except Exception:
            try:
                member = await User().convert(ctx, argument)
            except Exception as e:
                raise e
        if isinstance(member, discord.User):
            return member

        elif ctx.guild.me.top_role <= member.top_role:
            raise CommandError(f"The role of {member.mention} is **higher than wocks**")
        elif ctx.author.id == member.id and not author:
            raise CommandError("You **can not execute** that command on **yourself**")
        elif ctx.author.id == member.id and author:
            return member
        elif ctx.author.id == ctx.guild.owner_id:
            return member
        elif member.id == ctx.guild.owner_id:
            raise CommandError(
                "**Can not execute** that command on the **server owner**"
            )
        elif ctx.author.top_role.is_default():
            raise CommandError("You are **missing permissions to use this command**")
        elif ctx.author.top_role == member.top_role:
            raise CommandError("You have the **same role** as that user")
        elif ctx.author.top_role < member.top_role:
            raise CommandError("You **do not** have a role **higher** than that user")
        else:
            return member


class Emojis(commands.Converter):
    async def convert(
        self,
        ctx: Context,
        argument: str,
        ref: Optional[bool] = False,
        multiple: Optional[bool] = False,
    ):
        if isinstance(argument, list):
            return argument
        matches = None
        emojis = []
        if ctx.message.reference and ref:
            if ctx.message.reference.cached_message:
                message = ctx.message.reference.cached_message
            else:
                message = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
            if _matches := EMOJI_REGEX.findall(message.content):
                matches = _matches
            else:
                if len(message.embeds) > 0:
                    _m = EMOJI_REGEX.findall(message.embeds[0].description or "")
                    if _m:
                        matches = _m
                    else:
                        if len(message.embeds[0].fields) > 0:
                            for f in message.embeds[0].fields:
                                if match := EMOJI_REGEX.findall(f.value):
                                    if not multiple:
                                        matches = match
                                        break
                                    else:
                                        string = "".join(
                                            f" {m.value}"
                                            for m in message.embeds[0].fields
                                        )
                                        matches = EMOJI_REGEX.findall(string)
                                        break
        else:
            matches = EMOJI_REGEX.findall(argument)
        for e in matches:
            emojis.append(
                await PartialEmojiConverter().convert(ctx, f"<{e[0]}:{e[1]}:{e[2]}>")
            )
        defaults = DEFAULT_EMOJIS.findall(argument)
        if len(defaults) > 0:
            emojis.extend(defaults)
        return emojis[0]


commands.DiscordEmoji = Emojis

commands.GuildID = GConverter

# commands.MemberConverter.convert_ = commands.MemberConverter.convert
commands.MemberConverter = MemberConvert
# commands.RoleConverter.convert_ = commands.RoleConverter.convert
commands.RoleConverter = Role
# commands.UserConverter.convert_ = commands.UserConverter.convert
commands.UserConverter = User
# commands.TextChannelConverter.convert_ = commands.TextChannelConverter.convert
commands.TextChannelConverter = TextChannel
# commands.GuildChannelConverter.convert_ = commands.GuildChannelConverter.convert
commands.GuildChannelConverter = GuildChannel
# commands.VoiceChannelConverter.convert_ = commands.VoiceChannelConverter.convert
commands.VoiceChannelConverter = VoiceChannel
# commands.CategoryChannelConverter.convert_ = commands.CategoryChannelConverter.convert
commands.CategoryChannelConverter = CategoryChannel
# commands.EmojiConverter.convert_ = commands.EmojiConverter.convert
commands.EmojiConverter = Emoji
# commands.GuildStickerConverter.convert_ = commands.GuildStickerConverter.convert
commands.GuildStickerConverter = Sticker
commands.Image = Image
commands.AssignedRole = AssignedRole
commands.MultipleRoles = MultipleRoles
commands.EmbedConverter = EmbedConverter
commands.FakePermissionConverter = FakePermissionConverter
commands.FakePermissionEntry = FakePermissionEntry
commands.Boolean = Boolean
commands.Position = Position
commands.Percentage = Percentage
commands.Bitrate = Bitrate
commands.Region = Region
commands.KickChannelConverter = KickChannelConverter
commands.StyleConverter = StyleConverter
commands.EventConverter = EventConverter
commands.ModuleConverter = ModuleConverter
# commands.CommaConverter = CommaConverter
commands.CommandConverter = CommandConverter
commands.Expiration = Expiration
commands.SafeSnowflake = SafeSnowflake
commands.MessageLinkConverter = MessageConverter
