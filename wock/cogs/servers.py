import asyncio
import contextlib
#
import copy
import re
import typing
import unicodedata
from asyncio import gather, sleep
from base64 import b64decode  # type: ignore
from dataclasses import dataclass
from datetime import datetime, timedelta  # type: ignore
from io import BytesIO, StringIO
from logging import getLogger
from typing import Any, Dict, List, Optional, Union  # type: ignore

import aiohttp
import discord
from discord import TextChannel  # type: ignore  # noqa: F401
from discord import Embed
from discord.errors import HTTPException  # type: ignore
from discord.ext import commands
from discord.ext.commands import Cog, bot_has_permissions
from discord.ext.commands import group as Group
from discord.ext.commands import has_permissions
from discord.ext.commands.converter import PartialEmojiConverter
from discord.ext.commands.errors import CommandError
from loguru import logger
from pydantic import BaseModel
from tools.aliases import AliasConverter  # type: ignore # type: ignore
from tools.important import Context, is_donator  # type: ignore # type: ignore
from tools.important.database import query_limit  # type: ignore
from tools.important.subclasses.color import ColorConverter  # type: ignore
from tools.important.subclasses.command import (Argument,  # type: ignore
                                                Attachment, Emoji,
                                                FakePermissionConverter, Image,
                                                Role, Sticker, Stickers)
from tools.views import EmojiConfirmation  # type: ignore
from tuuid import tuuid

log = getLogger(__name__)


class GuildSticker(BaseModel):
    name: str
    description: str
    tags: str


if typing.TYPE_CHECKING:
    from tools.wock import Wock  # type: ignore

EMOJI_REGEX = re.compile(
    r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
)

DEFAULT_EMOJIS = re.compile(
    r"[\U0001F300-\U0001F5FF]|[\U0001F600-\U0001F64F]|[\U0001F680-\U0001F6FF]|[\U0001F700-\U0001F77F]|[\U0001F780-\U0001F7FF]|[\U0001F800-\U0001F8FF]|[\U0001F900-\U0001F9FF]|[\U0001FA00-\U0001FA6F]|[\U0001FA70-\U0001FAFF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251]|[\U0001F910-\U0001F9C0]|[\U0001F3A0-\U0001F3FF]"
)


@dataclass
class EmojiEntry:
    name: str
    id: int
    url: str
    animated: bool


class Emojis(commands.Converter):
    async def convert(
        self,
        ctx: Context,
        argument: str,
        ref: Optional[bool] = False,
        multiple: Optional[bool] = False,
    ):
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
        return emojis


def embed_creator(
    text: str,
    num: int = 1980,
    /,
    *,
    title: str = "",
    prefix: str = "",
    suffix: str = "",
    color: int = 0xB1AAD8,
) -> tuple:
    """
    Creates a list of Embed objects, each containing a portion of the input text.

    Parameters:
        text (str): The input text to be divided into portions.
        num (int, optional): The number of characters in each portion. Defaults to 1980.
        title (str, optional): The title of the Embed objects. Defaults to "".
        prefix (str, optional): The prefix to be added to each portion of the text. Defaults to "".
        suffix (str, optional): The suffix to be added to each portion of the text. Defaults to "".
        color (int, optional): The color of the Embed objects. Defaults to 0xb1aad8.

    Returns:
        tuple: A tuple of Embed objects, each containing a portion of the input text.
    """

    return tuple(
        Embed(
            title=title,
            description=prefix + (text[i : i + num]) + suffix,
            color=color if color is not None else 0x2F3136,
        )
        for i in range(0, len(text), num)
    )


def text_creator(
    text: str, num: int = 1980, /, *, prefix: str = "", suffix: str = ""
) -> tuple:
    """
    Generates a tuple of text segments from a given text string, with a specified
    maximum segment length and optional prefix and suffix.

    Parameters:
        text (str): The text string to generate segments from.
        num (int, optional): The maximum length of each segment. Defaults to 1980.
        prefix (str, optional): The prefix to add to each segment. Defaults to "".
        suffix (str, optional): The suffix to add to each segment. Defaults to "".

    Returns:
        tuple: A tuple containing the generated text segments.
    """

    return tuple(
        prefix + (text[i : i + num]) + suffix for i in range(0, len(text), num)
    )


def guild_has_vanity(guild: discord.Guild):
    if guild.vanity_url_code:
        return True
    else:
        return False


TUPLE = ()
SET = ()
DICT = {}


async def get_file_ext(url: str) -> str:
    file_ext1 = url.split("/")[-1].split(".")[1]
    if "?" in file_ext1:
        return file_ext1.split("?")[0]
    else:
        return file_ext1[:3]


async def get_asset(url: str, name: str = None):
    if name is None:
        name = str(tuuid())
    if "discord" not in url:
        url = f"https://proxy.rival.rocks?url={url}"
    ext = await get_file_ext(url)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            logger.info(f"asset {url} got a response of {response.status}")
            binary = await response.read()
    return discord.File(fp=BytesIO(binary), filename=f"{name}.{ext}")


async def get_raw_asset(url: str):
    if "discord" not in url:
        url = f"https://proxy.rival.rocks?url={url}"
    await get_file_ext(url)  # type: ignore
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            logger.info(f"asset {url} got a response of {response.status}")
            binary = await response.read()
    return binary


def multi_replace(text: str, to_replace: Dict[str, str], once: bool = False) -> str:
    """
    Replaces multiple occurrences of substrings in a given text.

    Parameters:
        text (str): The original text in which the replacements will be made.
        to_replace (Dict[str, str]): A dictionary containing the substrings to replace
            as keys and their corresponding replacement strings as values.
        once (bool, optional): If set to True, only the first occurrence of each
            substring will be replaced. Defaults to False.

    Returns:
        str: The modified text after performing the replacements.
    """

    for r1, r2 in to_replace.items():
        if r1 in text:
            if once:
                text = text.replace(str(r1), str(r2), 1)
            else:
                text = text.replace(str(r1), str(r2))

    return text


def is_unicode(emoji: str) -> bool:
    with contextlib.suppress(Exception):
        unicodedata.name(emoji)
        return True

    return False


def check_guild_boost_level():
    async def predicate(ctx: Context) -> bool:
        if not ctx.author.premium_since and not ctx.author.guild.owner:
            await ctx.fail("You need to be a **Booster** to use this command")
            return False
        if ctx.guild:
            if ctx.guild.premium_tier >= 2:
                return True
            else:
                if ctx.guild.id == 1203455800236965958:
                    return True
                await ctx.fail(
                    f"This guild is not **level 3 ** boosted\n > (**Current level: ** `{ctx.guild.premium_tier}`)"
                )
                return False

    return commands.check(predicate)


def check_br_status():
    async def predicate(ctx: Context) -> bool:
        if ctx.guild.premium_tier < 2 and ctx.guild.id != 1203455800236965958:
            await ctx.fail(
                f"This guild is **not ** currently level ** {ctx.guild.premium_tier} ** and must be ** level 2 ** to use this."
            )
            return False
        if not await ctx.bot.db.fetchval(
            "SELECT status FROM br_status WHERE guild_id = $1", ctx.guild.id
        ):
            await ctx.fail("**Booster roles** are **not** enabled in this guild.")
            return False
        if not ctx.author.premium_since and ctx.author.id not in ctx.bot.owner_ids:
            await ctx.fail("You need to be a **Booster** to use this command.")
            return False
        return True

    return commands.check(predicate)


class Servers(Cog):
    def __init__(self, bot: "Wock") -> None:
        self.bot = bot

    async def get_int(self, string: str):
        t = ""
        for s in string:
            try:
                d = int(s)
                t += f"{d}"
            except Exception:
                pass
        return t

    async def get_timeframe(self, timeframe: str):
        from datetime import timedelta

        import humanfriendly

        try:
            converted = humanfriendly.parse_timespan(timeframe)
        except Exception:
            converted = humanfriendly.parse_timespan(
                f"{await self.get_int(timeframe)} hours"
            )
        time = datetime.now() + timedelta(seconds=converted)
        return time

    async def get_emojis(self, string: str) -> Optional[EmojiEntry]:
        data = re.findall(r"<(a?):([a-zA-Z0-9_]+):([0-9]+)>", string)
        if data:
            for _a, emoji_name, emoji_id in data:
                animated = _a == "a"
                animate = False
                if animated:
                    animate = True
                    url = "https://cdn.discordapp.com/emojis/" + emoji_id + ".gif"
                else:
                    url = "https://cdn.discordapp.com/emojis/" + emoji_id + ".png"
                return EmojiEntry(
                    name=emoji_name, url=url, id=emoji_id, animated=animate
                )

    @commands.Cog.listener("on_raw_message_delete")
    async def rr_delete(self, message):
        await self.bot.db.execute(
            """DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
            message.guild_id,
            message.channel_id,
            message.message_id,
        )

    @commands.group(
        name="paginator",
        invoke_without_command=True,
        aliases=["p"],
        brief="Set up multi page embeds for your server",
        example=",paginator {embed_code}",
    )
    async def paginator(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @paginator.command(
        name="add",
        aliases=["create", "c", "a"],
        brief="make a paginator from a list of embed code objects",
        usage=",paginator add <name> <embeds>",
        example=",paginator add hello {embed}$v{description: sup}{embed}$v{description: welcome}",
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_add(self, ctx: Context, *, arg: Argument):
        name = arg.first
        embeds = arg.second
        return await self.bot.paginators.create(ctx, name, embeds)

    @paginator.command(
        name="remove",
        aliases=["rem", "r", "del", "d", "delete"],
        brief="delete an existing paginator",
        usage=",paginator remove <name>",
        example=",paginator remove hello",
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_remove(self, ctx: Context, *, name: str):
        return await self.bot.paginators.delete(ctx, name)

    @paginator.command(
        name="list", brief="list all paginators setup", example=",paginator list"
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_list(self, ctx: Context):
        return await self.bot.paginators.list(ctx)

    @paginator.command(
        name="clear", brief="Remove all existing paginators", example=",paginator clear"
    )
    @commands.has_permissions(manage_messages=True)
    async def paginator_clear(self, ctx: Context):
        await asyncio.gather(
            *[
                self.bot.db.execute(
                    """DELETE FROM paginator WHERE guild_id = $1""", ctx.guild.id
                ),
                ctx.success("reset all paginators"),
            ]
        )

    @commands.group(
        name="alias",
        invoke_without_command=True,
        brief="view alias sub commands",
        example=",alias",
    )
    async def alias(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @alias.command(
        name="add",
        aliases=["create", "a", "c"],
        brief="add an alias for a command",
        example=",alias add ban, byebye",
    )
    @commands.has_permissions(manage_guild=True)
    async def alias_add(self, ctx: Context, *, data: AliasConverter):
        self.bot.alias_kwargs = ctx.kwargs
        await self.bot.db.execute(
            "INSERT INTO aliases (guild_id, command_name, alias) VALUES ($1,$2,$3) ON CONFLICT(guild_id, alias) DO NOTHING",
            ctx.guild.id,
            data.command.qualified_name,
            data.alias,
        )
        return await ctx.success(
            f"**Added** `{data.alias}` as an **alias** for `{data.command.qualified_name}`"
        )

    @alias.command(
        name="remove",
        aliases=["delete", "r", "rem", "del", "d"],
        brief="remove an alias from a command",
        example=",alias remove ban",
    )
    @commands.has_permissions(manage_guild=True)
    async def alias_remove(self, ctx: Context, *, alias: str):
        await self.bot.db.execute(
            "DELETE FROM aliases WHERE guild_id = $1 AND alias = $2",
            ctx.guild.id,
            alias,
        )
        return await ctx.success(f"**Removed** `{alias}` custom alias")

    @alias.command(
        name="list", brief="show all your current command aliases", example="alias list"
    )
    @commands.has_permissions(manage_guild=True)
    async def alias_list(self, ctx: Context):
        data = await self.bot.db.fetch(
            """SELECT command_name, alias FROM aliases WHERE guild_id = $1""",
            ctx.guild.id,
        )
        rows = []
        for i, row in enumerate(data, start=1):
            rows.append(f"`{i}` **{row['command_name']}** - {row['alias']}")
        if len(rows) == 0:
            return await ctx.fail("no **aliases** found")
        else:
            return await self.bot.dummy_paginator(
                ctx, Embed(title="Aliases", color=self.bot.color), rows
            )

    # @Group(
    #     name="autopfp",
    #     brief="configure auto profile pictures for the server",
    #     example=",autopfp",
    # )
    # async def pfpchannel(self, ctx: Context):
    #     if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
    #         return
    #     return await ctx.send_help(ctx.command)

    # @pfpchannel.command(
    #     name="setup",
    #     aliases=["add"],
    #     brief="set a channel to send profile pictures to",
    #     example=",autopfp setup #pfps",
    # )
    # @commands.has_permissions(manage_guild=True)
    # async def pfpchannel_set(self, ctx: Context, *, channel: TextChannel):
    #     await self.bot.db.execute(
    #         """INSERT INTO pfps (guild_id,channel_id) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id""",
    #         ctx.guild.id,
    #         channel.id,
    #     )
    #     return await ctx.success(f"**Autopfp channel** was set to {channel.mention}")

    # @pfpchannel.command(
    #     name="reset",
    #     aliases=["clear", "remove"],
    #     brief="remove the channel set to send profile pictures",
    #     example=",autopfp reset",
    # )
    # @commands.has_permissions(manage_guild=True)
    # async def pfpchannel_reset(self, ctx: Context):
    #     await self.bot.db.execute(
    #         """DELETE FROM pfps WHERE guild_id = $1""", ctx.guild.id
    #     )
    #     return await ctx.success("Autopfp channel was **removed**")

    @Group(
        name="settings",
        aliases=["setting"],
        brief="Settings for your server",
        example=",settings",
    )
    async def settings(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command)

    @settings.group(name="context", invoke_without_command=True)
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @settings_context.command(name="clear", brief="reset all of your context settings")
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_reset(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM context WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("reset your **context settings**")

    @settings_context.group(
        name="success",
        brief="change the success color",
        example=",settings context success #303135",
        usage=",settings context success {color}",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_success(self, ctx: Context, *, color: ColorConverter):
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, success_color) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET success_color = excluded.success_color""",
            ctx.guild.id,
            str(color),
        )
        return await ctx.success(
            f"successfully set your **success color** to {str(color)}"
        )

    @settings_context_success.command(
        name="emoji",
        brief="change the success emoji",
        example=",settings context success emoji <:hi:1231421421412>",
        usage=",settings context success emoji {emoji}",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_success_emoji(self, ctx: Context, *, emoji: Emojis):
        emoji = emoji[0]
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, success_emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET success_emoji = excluded.success_emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set your **success emoji** to {str(emoji)}"
        )

    @settings_context.group(
        name="fail",
        brief="change the fail color",
        example=",settings context fail #303135",
        usage=",settings context fail {color}",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_fail(self, ctx: Context, *, color: ColorConverter):
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, fail_color) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET fail_color = excluded.fail_color""",
            ctx.guild.id,
            str(color),
        )
        return await ctx.success(
            f"successfully set your **fail color** to {str(color)}"
        )

    @settings_context_fail.command(
        name="emoji",
        brief="change the fail emoji",
        example=",settings fail emoji <:hi:1231421421412>",
        usage=",settings fail emoji {emoji}",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_fail_emoji(self, ctx: Context, *, emoji: Emojis):
        emoji = emoji[0]
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, fail_emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET fail_emoji = excluded.fail_emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set your **fail emoji** to {str(emoji)}"
        )

    @settings_context.group(
        name="warning",
        brief="change the warning color",
        example=",settings contextwarning #303135",
        usage=",settings contextwarning {color}",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_warning(self, ctx: Context, *, color: ColorConverter):
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, warning_color) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET warning_color = excluded.warning_color""",
            ctx.guild.id,
            str(color),
        )
        return await ctx.success(
            f"successfully set your **warning color** to {str(color)}"
        )

    @settings_context_warning.command(
        name="emoji",
        brief="change the warning emoji",
        example=",settings contextwarning emoji <:hi:1231421421412>",
        usage=",settings contextwarning emoji {emoji}",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def settings_context_warning_emoji(self, ctx: Context, *, emoji: Emojis):
        emoji = emoji[0]
        await self.bot.db.execute(
            """INSERT INTO context (guild_id, warning_emoji) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET warning_emoji = excluded.warning_emoji""",
            ctx.guild.id,
            str(emoji),
        )
        return await ctx.success(
            f"successfully set your **warning emoji** to {str(emoji)}"
        )

    async def get_attachments(self, ctx: Context):
        if reference := ctx.message.reference:
            msg = await self.bot.fetch_message(ctx.channel, reference.message_id)
            if len(msg.attachments) > 0:
                return await msg.attachments[0].read()
        if len(ctx.message.attachments) > 0:
            return await ctx.message.attachments[0].read()
        return None

    @settings.group(
        name="system",
        aliases=["sys"],
        brief="Settings for system related commands",
        example=",settings system",
        invoke_without_command=True,
    )
    async def system(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @system.command(
        name="boost",
        brief="Toggle the servers boost system message",
        example=",settings system boost true",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def system_boost(
        self, ctx: Context, *, channel: discord.abc.GuildChannel = None
    ):
        if channel is None:
            await ctx.guild.edit(
                system_channel_flags=discord.SystemChannelFlags(
                    premium_subscriptions=False,
                    join_notifications=ctx.guild.system_channel_flags.join_notifications,
                )
            )
        else:
            await ctx.guild.edit(
                system_channel=channel,
                system_channel_flags=discord.SystemChannelFlags(
                    premium_subscriptions=True,
                    join_notifications=ctx.guild.system_channel_flags.join_notifications,
                ),
            )
        state = (
            "enabled"
            if ctx.guild.system_channel_flags.premium_subscriptions
            else "disabled"
        )
        return await ctx.success(f"**System Boost messages** set to {state}")

    @system.command(
        name="welcome",
        brief="toggle the welcome system message",
        example=",settings system welcome true",
    )
    @bot_has_permissions(manage_guild=True)
    @has_permissions(manage_guild=True)
    async def system_welcome(
        self, ctx: Context, *, channel: discord.abc.GuildChannel = None
    ):
        if channel is None:
            await ctx.guild.edit(
                system_channel_flags=discord.SystemChannelFlags(
                    join_notifications=False,
                    premium_subscriptions=ctx.guild.system_channel_flags.premium_subscriptions,
                )
            )
        else:
            await ctx.guild.edit(
                system_channel=channel,
                system_channel_flags=discord.SystemChannelFlags(
                    join_notifications=True,
                    premium_subscriptions=ctx.guild.system_channel_flags.premium_subscriptions,
                ),
            )
        state = (
            "enabled"
            if ctx.guild.system_channel_flags.join_notifications
            else "disabled"
        )
        return await ctx.success(f"**System welcome message** set to {state}")

    @system.command(
        name="sticker",
        alaises=("stickers",),
        brief="auto reply to the welcome system message",
        example=",settings system sticker true",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def system_sticker(self, ctx: Context, state: bool):
        if state is True:
            await self.bot.db.execute(
                """INSERT INTO system_messages (guild_id) VALUES($1)""", ctx.guild.id
            )
        else:
            await self.bot.db.execute(
                """DELETE FROM system_messages WHERE guild_id = $1""", ctx.guild.id
            )
        return await ctx.success(f"**System sticker message reply** set to {state}")

    @settings.command(
        name="banner",
        brief="Apply an image as the guild banner",
        example=",settings system banner {image}",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_banner(self, ctx: Context, *, image: Image = None):
        if image is None:
            if image := await self.get_attachments(ctx):
                image = image
            else:
                return await ctx.fail("no image provided")
        await ctx.guild.edit(
            banner=image, reason=f"Banner updated by {str(ctx.author)}"
        )
        return await ctx.success("**Updated** the servers banner")

    @settings.command(
        name="splash",
        brief="Apply an image as the guild splash",
        example=",settings system splash {image}",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_splash(self, ctx: Context, *, image: Image = None):
        if image is None:
            if image := await self.get_attachments(ctx):
                image = image
            else:
                return await ctx.fail("no image provided")
        await ctx.guild.edit(
            splash=image, reason=f"splash updated by {str(ctx.author)}"
        )
        return await ctx.success("*Updated** the server splash")

    @settings.command(
        name="icon",
        aliases=["pfp", "av", "avatar"],
        brief="Aplly an image as the guild icon",
        example=",settings system icon {image}",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_avatar(self, ctx: Context, *, image: Image = None):
        if image is None:
            if image := await self.get_attachments(ctx):
                image = image
            else:
                return await ctx.fail("no image provided")
        await ctx.guild.edit(icon=image, reason=f"banner updated by {str(ctx.author)}")
        return await ctx.success("**Updated** the server icon")

    @settings.command(
        name="description",
        brief="Apply a message as the guild description",
        aliases=["desc"],
        example=",settings system description this is the best server",
    )
    @has_permissions(manage_guild=True)
    @bot_has_permissions(manage_guild=True)
    async def set_description(self, ctx: Context, *, text: str):
        await ctx.guild.edit(
            description=text, reason=f"description updated by {str(ctx.author)}"
        )
        return await ctx.success("**Updated** the server description")

    @Group(
        name="sticker",
        brief="Manage the servers stickers",
        example=",sticker",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker(self: "Servers", ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)

    def rerun(self, image_bytes: bytes, size=(120, 120), max_size_kb=512):
        from PIL import Image, ImageSequence

        with BytesIO(image_bytes) as input_buffer:
            with Image.open(input_buffer) as im:
                frames = [
                    frame.copy()
                    for i, frame in enumerate(ImageSequence.Iterator(im))
                    if i % 3 == 0
                ]  # Skip every other frame
                resized_frames = [frame.resize(size, Image.LANCZOS) for frame in frames]

                output_buffer = BytesIO()
                quality = 90  # Start with high quality
                resized_frames[0].save(
                    output_buffer,
                    format="GIF",
                    save_all=True,
                    append_images=resized_frames[1:],
                    loop=0,
                    optimize=True,
                    quality=quality,
                )

                while output_buffer.tell() > max_size_kb * 1024:
                    output_buffer = BytesIO()
                    quality -= 10
                    if quality < 10:
                        raise ValueError(
                            "Cannot compress the image to the required size."
                        )
                    resized_frames[0].save(
                        output_buffer,
                        format="GIF",
                        save_all=True,
                        append_images=resized_frames[1:],
                        loop=0,
                        optimize=True,
                        quality=quality,
                    )

                output_buffer.seek(0)
                return output_buffer.read()

    async def convert_sticker(self, img_url: str, svg: bool = False) -> discord.File:  # type: ignore
        from PIL import Image, ImageSequence
        from rival_tools import thread  # type: ignore
        from wand.image import Image as IMG

        @thread
        def convert_gif(
            image_bytes: bytes,
            gif: Optional[bool] = False,
            size=(320, 320),
            max_size_kb=512,
        ):
            if gif is True:
                with BytesIO(image_bytes) as input_buffer:
                    with Image.open(input_buffer) as im:
                        frames = [
                            frame.copy()
                            for i, frame in enumerate(ImageSequence.Iterator(im))
                            if i % 3 == 0
                        ]  # Skip every other frame
                        resized_frames = [
                            frame.resize(size, Image.LANCZOS) for frame in frames
                        ]

                        output_buffer = BytesIO()
                        quality = 90  # Start with high quality
                        resized_frames[0].save(
                            output_buffer,
                            format="GIF",
                            save_all=True,
                            append_images=resized_frames[1:],
                            loop=0,
                            optimize=True,
                            quality=quality,
                        )

                        while output_buffer.tell() > max_size_kb * 1024:
                            output_buffer = BytesIO()
                            quality -= 10
                            if quality < 10:
                                try:
                                    return self.rerun(image_bytes)
                                except Exception:
                                    raise ValueError(
                                        "Cannot compress the image to the required size."
                                    )
                            resized_frames[0].save(
                                output_buffer,
                                format="GIF",
                                save_all=True,
                                append_images=resized_frames[1:],
                                loop=0,
                                optimize=True,
                                quality=quality,
                            )

                        output_buffer.seek(0)
                        return output_buffer.read()
            else:
                with IMG(blob=image_bytes) as i:  #
                    i.coalesce()
                    i.optimize_layers()
                    i.compression_quality = 100
                    png_bytes = i.make_blob(format="apng" if i.animation else "png")
                    return png_bytes

        if ".gif" in img_url:
            conversion = await convert_gif(await get_raw_asset(img_url), True)
            filename = "meow.gif"
        else:
            conversion = await convert_gif(await get_raw_asset(img_url))
            filename = "meow.png"

        return discord.File(fp=BytesIO(conversion), filename=filename)

    @sticker.command(
        name="add",
        aliases=("create",),
        example=",sticker add (reply to sticker)",
        brief="Add a sticker recently posted in chat to the server",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_add(self: "Servers", ctx: Context, *, name: str):
        """
        Create a new sticker
        """
        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.fail("This server exceeds the **sticker limit**.")

        if len(name) < 2 or len(name) > 30:
            return await ctx.fail(
                "Name must be between between **2** and **30 characters**"
            )

        try:
            image = await Stickers.search(ctx)
        except Exception:
            image = None
        if not image:
            image = await Attachment.search(ctx)
            logger.info(f"getting asset from {image}")
            if image is None:
                return await ctx.fail("No image provided")
        a = await get_raw_asset(image)
        ext = await get_file_ext(image)
        #        await ctx.send(files=[a])
        try:
            sticker = await ctx.guild.create_sticker(
                name=name,
                description="...",
                file=discord.File(fp=BytesIO(a), filename=f"{name}.{ext}"),
                reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]",
                emoji="💀",
            )
        except Exception:  # type: ignore
            message = await ctx.normal(
                "please wait while I attempt to compress this asset"
            )
            embed = message.embeds[0]
            try:
                file = await self.convert_sticker(image)
                sticker = await ctx.guild.create_sticker(
                    name=name,
                    description="...",
                    file=file,
                    reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]",
                    emoji="💀",
                )
                embed.description = (
                    f"**Created** the sticker [**{sticker.name}**]({sticker.url})"
                )
            except Exception:  # type: ignore
                embed.description = "**Failed** to create the sticker with the attachment provided due to it being to large"

            return await message.edit(embed=embed)
        return await ctx.success(
            f"**Created** the sticker [**{sticker.name}**]({sticker.url})"
        )

    @sticker.command(
        name="remove",
        aliases=("delete",),
        usage="<sticker>",
        example=",sticker delete dumb_sticker",
        brief="Delete a sticker from the server",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_remove(self: "Servers", ctx: Context, *, sticker: Sticker):
        """
        Delete an existing sticker
        """
        await sticker.delete(
            reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]"
        )
        return await ctx.fail("**Deleted** that sticker")

    @sticker.command(
        name="rename",
        aliases=("name",),
        usage="<sticker>",
        example=",sticker rename dumb_sticker, new_name,",
        brief="Rename a sticker in the server",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_rename(
        self: "Servers", ctx: Context, sticker: Sticker, *, name: str
    ):
        """
        Rename an existing sticker
        """
        if len(name) < 2 or len(name) > 30:
            return await ctx.fail("Name must be between **2** and **30 characters**")
        await sticker.edit(
            name=name, reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]"
        )

        return await ctx.fail(f"**Renamed** that sticker to: **{name}**")

    @sticker.command(
        name="clean",
        aliases=("strip",),
        brief="Remove any vanity links from all stickers",
        example=",sticker clean",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_clean(self: "Servers", ctx: Context):
        """
        Remove vanity links from every sticker name
        """
        if not ctx.guild.stickers:
            return await ctx.fail("There aren't any **stickers** in this server.")

        async def clean_sticker(sticker):
            if "/" not in sticker.name:
                return

            name = multi_replace(
                sticker.name,
                {**{word: "" for word in sticker.name.split() if "/" in word}},
            )

            if len(name) < 2:
                return

            return await sticker.edit(
                name=name.strip(),
                reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]",
            )

        cleaned = tuple(
            filter(
                lambda s: s,
                await gather(
                    *(clean_sticker(sticker) for sticker in ctx.guild.stickers)
                ),
            )
        )

        return await ctx.success(f"**Cleaned** `{len(cleaned)}` stickers")

    @sticker.command(
        name="tag",
        brief="Add your vanity link to every sticker name",
        example=",sticker tag",
    )
    @bot_has_permissions(manage_emojis_and_stickers=True)
    @has_permissions(manage_emojis_and_stickers=True)
    async def sticker_tag(self: "Servers", ctx: Context):
        if guild_has_vanity(ctx.guild) is not True:
            return await ctx.fail("this guild doesn't have a vanity")
        if not ctx.guild.stickers:
            return await ctx.fail("There aren't any **stickers** in this server.")

        async def tag_sticker(sticker):
            if f".gg/{ctx.guild.vanity_url_code}" in sticker.name:
                return

            return await sticker.edit(
                name=sticker.name[: 30 - len(f" .gg/{ctx.guild.vanity_url_code}")]
                + f" .gg/{ctx.guild.vanity_url_code}".strip(),
                reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]",
            )

        tagged = tuple(
            filter(
                lambda s: s,
                await gather(*(tag_sticker(sticker) for sticker in ctx.guild.stickers)),
            )
        )

        return await ctx.success(f"**Tagged** `{len(tagged)}` stickers")

    @Group(
        name="premiumrole",
        aliases=["pr", "boosterreward"],
        brief="Premium role settings for when users boost",
        example=",premiumrole",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @premiumrole.command(
        name="add",
        aliases=["give", "set"],
        brief="set a role for all boosters to be given",
        example=",premiumrole add pic",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole_add(self, ctx: Context, role: Role):
        role = role[0]
        await self.bot.db.execute(
            """INSERT INTO premiumrole (guild_id, role_id) VALUES ($1, $2) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"**Boosters** will now be given {role.mention}")

    @premiumrole.command(
        name="remove",
        aliases=["r"],
        brief="remove the booster role",
        example=",premiumrole remove pic",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole_remove(self, ctx: Context, role: Role):  # type: ignore
        await self.bot.db.execute(
            """DELETE FROM premiumrole WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("**Removed** the **booster role**")

    @premiumrole.command(
        name="list",
        aliases=["status"],
        brief="Check which role is set as a premium reward role",
        example=",premiumrole list",
    )
    @commands.has_permissions(manage_guild=True)
    async def premiumrole_status(self, ctx: Context):
        if role_id := await self.bot.db.fetchval(
            """SELECT role_id FROM premiumrole WHERE guild_id = $1""", ctx.guild.id
        ):
            return await ctx.success(
                f"**Reward for boosting** is set to {ctx.guild.get_role(role_id).mention}"
            )
        else:
            return await ctx.fail("**Premiumrole** is **not** set")

    @commands.Cog.listener("on_guild_emojis_update")
    @commands.has_permissions(manage_guild=True)
    async def emoji_ratelimit(self, guild, before, after):
        if len(before) != len(after):
            async for audit in guild.audit_logs(
                action=discord.AuditLogAction.emoji_create,
                limit=1,
                after=discord.utils.utcnow() - timedelta(seconds=1),
            ):
                if audit.user.id == self.bot.user.id:
                    return
            await self.bot.glory_cache.ratelimited(f"emojis:{guild.id}", 49, 60 * 60)

    @Group(
        name="emoji",
        usage="<sub command>",
        example="removeduplicates",
        invoke_without_command=True,
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji(self: "Servers", ctx: Context):
        """
        Manage the server emojis
        """

        return await ctx.send_help(ctx.command.qualified_name)

    @emoji.command(
        name="steal", brief="steal the most recently used emoji", example=",emoji steal"
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_steal(self, ctx: Context):
        emoji = None
        i = 0
        if ctx.message.reference:
            emoji = await Emojis().convert(ctx, "", True)
            emoji = emoji[0]
        else:

            async for message in ctx.channel.history(limit=200):
                i += 1
                if await Emojis().convert(ctx, message.content):  # type: ignore
                    try:
                        emoj = await self.get_emojis(message.content)
                        try:
                            if get_emoji := self.bot.get_emoji(int(emoj.id)):
                                if get_emoji.guild.id != ctx.guild.id:
                                    emoji = emoj
                                    break
                                else:
                                    continue
                            else:
                                emoji = emoj
                                break
                        except Exception:  # type: ignore
                            emoji = emoj
                    except Exception:  # type: ignore
                        emoji = await self.get_emojis(message.content)
                        if emoji:
                            break
        if emoji is None:
            return await ctx.fail(f"no **emojis** found in the last {i} messages")
        embed = discord.Embed(color=self.bot.color).add_field(
            name="Emoji ID", value=emoji.id, inline=True
        )
        if get_emoji := self.bot.get_emoji(int(emoji.id)):
            embed.add_field(name="Guild", value=get_emoji.guild.name, inline=True)
        embed.add_field(
            name="Image URL",
            value=f"[**Click here to open the image**]({emoji.url})",
            inline=False,
        )
        embed.set_image(url=emoji.url)
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.title = emoji.name
        message = await ctx.send(embed=embed)
        view = EmojiConfirmation(message, emoji, ctx.author)
        await message.edit(view=view)
        await view.wait()

    @emoji.command(
        name="add",
        aliases=("create",),
        example=",emoji add :sad_bear:",
        brief="Add an emoji to the guild",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_add(
        self: "Servers",
        ctx: Context,
        *,
        name: Union[discord.Emoji, discord.PartialEmoji, str],
    ):
        """
        Create a new emoji
        """
        if len(ctx.guild.emojis) == ctx.guild.emoji_limit * 2:
            return await ctx.fail("**Server exceeds** the **emoji limit**")

        if not isinstance(name, discord.Emoji) and not isinstance(
            name, discord.PartialEmoji
        ):
            if len(name) < 2 or len(name) > 30:
                return await ctx.fail(
                    "Please provide a **valid** name between 2 and 30 characters."
                )
            if not (image := await Attachment.search(ctx)):
                return await ctx.fail("There are **no recently sent images**")
        else:
            image = await name.read()
            name = name.name
        try:
            if (
                await self.bot.glory_cache.ratelimited(
                    f"emojis:{ctx.guild.id}", 49, 60 * 60
                )
                != 0
            ):  # type: ignore
                raise CommandError("Emoji adding is ratelimited for this guild")
            emoji = await ctx.guild.create_custom_emoji(
                name=name,
                image=image,
                reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]",
            )

        except HTTPException as error:
            if "(error code: 30008)" in str(error):
                return await ctx.fail("**Server** doesn't have enough **emoji slots**")

            return await ctx.fail("Please provide a **valid** image.")

        return await ctx.success(
            f"**Created** the emoji [**{emoji.name}**]({emoji.url})"
        )

    @emoji.command(
        name="addmultiple",
        aliases=("addmany",),
        example=",emoji addmultiple [all emojis]",
        brief="Add multiple emojis to the server",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_addmultiple(
        self: "Servers",
        ctx: Context,
        *,
        emojis: Optional[Any] = None,  # Union[PartialEmoji, Emoji]],
    ):
        """
        Create multiple emojis
        """
        if ctx.message.reference:
            emojis = await Emojis().convert(ctx, "", True, True)
        else:
            if emojis:
                emojis = await Emojis().convert(ctx, emojis)
            else:
                return await ctx.fail("Please provide **Emojis**")
        if len(ctx.guild.emojis) >= ctx.guild.emoji_limit:
            return await ctx.fail("**Server exceeds** the **emoji limit**.")
        if emojis == None:
            return await ctx.fail("No **Emojis** were found")
        # I can't gather this without doing something stupid
        created = 0
        log.info(emojis)
        msg = None
        remaining = ctx.guild.emoji_limit - len(ctx.guild.emojis)
        e = emojis[:remaining]
        log.info(f"{e} {remaining}")
        for emoji in e:
            await sleep(0.001)
            # try:
            if (
                await self.bot.glory_cache.ratelimited(
                    f"emojis:{ctx.guild.id}", 49, 60 * 60
                )
                != 0
            ):  # type: ignore
                raise CommandError("Emoji adding is ratelimited for this guild")
            await ctx.guild.create_custom_emoji(
                name=emoji.name,
                image=await emoji.read(),
                reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]",
            )
            created += 1

            # except Exception as e:
            #     if msg == None:
            #         msg = await ctx.fail(f"currently ratelimited please standby until the 50 emojis per hour ratelimit is over..\e{e}")
            #     continue
        if created == 0:
            return await ctx.fail("**No emojis** could be added")

        if created != len(emojis):
            return await ctx.success(f"**Could only create** `{created}` emojis")
        if msg is not None:
            return await msg.edit(
                embed=discord.Embed(
                    color=self.bot.color, description=f"**Created** `{created}` emojis"
                )
            )
        return await ctx.success(f"**Created** `{created}` emojis")

    @emoji.command(
        name="fromfile",
        aliases=("fromattachments", "fromfiles"),
        example=",emoji fromfile (reply to the image)",
        brief="Add an emoji from a file by replying to it",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_addfromattachments(self: "Servers", ctx: Context):
        """
        Create emojis from attachments
        """
        if ctx.message.reference is not None:
            message = await self.bot.fetch_message(
                ctx.channel, ctx.message.reference.message_id
            )
        else:
            message = ctx.message
        if len(ctx.guild.emojis) == ctx.guild.emoji_limit * 2:
            return await ctx.fail("**Server exceeds** the **emoji limit**")

        if not message.attachments:
            return await ctx.fail("Message has **no attachments**")

        # I can't gather this without doing something stupid

        created = 0

        for attachment in message.attachments[
            : (ctx.guild.emoji_limit * 2) - len(ctx.guild.emojis)
        ]:
            await sleep(0.001)

            try:
                if (
                    await self.bot.glory_cache.ratelimited(
                        f"emojis:{ctx.guild.id}", 49, 60 * 60
                    )
                    != 0
                ):  # type: ignore
                    raise CommandError("Emoji adding is ratelimited for this guild")
                await ctx.guild.create_custom_emoji(
                    name=attachment.filename.replace(".", "")
                    .replace("png", "")
                    .replace("jpg", "")
                    .replace("gif", ""),
                    image=await attachment.read(),
                    reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]",
                )
                created += 1

            except Exception as e:
                logger.info(e)
                continue

        if created == 0:
            return await ctx.fail("**No emojis** could be added")

        if created != len(message.attachments):
            return await ctx.success(f"**Could only create** `{created}` emojis")

        return await ctx.success(f"**Created** `{created}` emojis")

    @emoji.command(
        name="remove",
        aliases=("delete",),
        example=",emoji remove [emoji]",
        brief="Remove an emoji from the server",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_remove(self: "Servers", ctx: Context, *, emoji: Emoji):
        """
        Delete an existing emoji
        """
        await emoji.delete(
            reason=f"{self.bot.user.name.title()} Utilities [{ctx.author}]"
        )
        return await ctx.success("**Deleted** that emoji")

    @emoji.command(
        name="rename",
        aliases=("name",),
        example=",emoji rename :sad: megasad",
        brief="Rename an emoji",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_rename(self: "Servers", ctx: Context, emoji: Emoji, *, name: str):

        if len(name) < 2 or len(name) > 30:
            return await ctx.fail("Name must be between **2** and **30 characters**")

        await emoji.edit(
            name=name, reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]"
        )

        return await ctx.success(f"Renamed** that emoji to: **{name}**")

    @emoji.command(
        name="removeduplicates",
        brief="Remove all emojis that has a duplicate",
        example=",emoji removeduplicates",
    )
    @bot_has_permissions(manage_emojis=True)
    @has_permissions(manage_emojis=True)
    async def emoji_removeduplicates(self: "Servers", ctx: Context):

        if not ctx.guild.emojis:
            return await ctx.fail("There are **no emojis**")

        duplicates = set()
        seen = set()
        emojis_bytes = await gather(*(emoji.read() for emoji in ctx.guild.emojis))

        for emoji, emoji_bytes in zip(ctx.guild.emojis, emojis_bytes):
            if emoji_bytes in seen:
                duplicates.add(emoji)

            else:
                seen.add(emoji_bytes)

        removed = await gather(
            *(
                duplicate.delete(
                    reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]: Duplicate emoji"
                )
                for duplicate in duplicates
            )
        )

        return await ctx.success(f"**Removed** `{len(removed)}` duplicated emojis")

    @Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if data := await self.bot.db.fetchrow(
            "SELECT * FROM welcome WHERE guild_id = $1", member.guild.id
        ):
            channel = self.bot.get_channel(data["channel_id"])
            message = data["message"]
            if channel:
                await self.bot.send_embed(channel, message, user=member)

    @Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if data := await self.bot.db.fetchrow(
            "SELECT * FROM leave WHERE guild_id = $1", member.guild.id
        ):
            channel = self.bot.get_channel(data["channel_id"])
            message = data["message"]
            if channel:
                await self.bot.send_embed(channel, message, user=member)

    @commands.command(
        name="embed",
        aliases=["ce", "createembed"],
        example=",embed {embed_code}",
        brief="Create an embed using an embed code",
    )
    @commands.has_permissions(manage_messages=True)
    async def embed(self, ctx: Context, *, code: str):
        from tools.rival import EmbedException  # type: ignore # type: ignore

        try:
            await self.bot.send_embed(ctx.channel, code, user=ctx.author)
        except EmbedException as e:
            raise e
            return await ctx.fail(e)
        except Exception as e:
            raise e

    @commands.group(
        name="selfprefix",
        invoke_without_command=True,
        brief="Set a self prefix thats unique to you to use for wock",
        example=",selfprefix !",
    )
    async def selfprefix(self, ctx: Context, prefix: str = None):
        if prefix and len(prefix) > 3:
            return await ctx.fail("Prefix **cannot** be longer than `2` **characters**")
        if not prefix:
            return await ctx.fail("Please provide a **prefix**")
        await self.bot.db.execute(
            "INSERT INTO selfprefix (prefix, user_id) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET prefix = $1",
            prefix,
            ctx.author.id,
        )
        self.bot.cache.self_prefixes[ctx.author.id] = prefix
        await ctx.success(f"**Selfprefix** has been changed to `{prefix}`")

    @selfprefix.command(
        name="remove",
        aliases=["reset"],
        brief="Reset the self prefix you have previously set",
        example=",selfprefix remove",
    )
    @is_donator()
    async def selfprefix_remove(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM selfprefix WHERE user_id = $1", ctx.author.id
        )
        try:
            self.bot.cache.self_prefixes.pop(ctx.author.id)
        except Exception:
            pass
        await ctx.success("**Removed** your **Selfprefix**")

    @commands.group(
        name="prefix",
        invoke_without_command=True,
        brief="Set a prefix for the bot to respond to in the guild",
        example=",prefix ;",
    )
    async def prefix(self, ctx: Context, prefix: str = None):
        if prefix is not None and len(prefix) > 2:
            await ctx.fail("Prefix **cannot** be longer than **2 characters**")
            return
        await self.bot.db.execute(
            "INSERT INTO prefixes (prefix, guild_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET prefix = EXCLUDED.prefix",
            prefix,
            ctx.guild.id,
        )
        self.bot.cache.prefixes[ctx.guild.id] = prefix
        invite_link = await ctx.channel.create_invite()
        await ctx.success(
            f"[**Guild Prefix**]({invite_link}) has been **changed** to `{prefix}`"
        )

    @prefix.command(
        name="remove",
        aliases=["reset"],
        brief="Remove the custom guild prefix from the bot",
        example=",prefix remove",
    )
    async def prefix_remove(self, ctx: Context):
        invite_link = await ctx.channel.create_invite()
        await self.bot.db.execute(
            "DELETE FROM prefixes WHERE guild_id = $1", ctx.guild.id
        )
        try:
            self.bot.prefix.pop(ctx.guild.id)
        except Exception:
            pass
        await ctx.fail(
            f"[**Guild Prefix**]({invite_link}) **removed**, mention the bot for the [**Global Prefix**]({invite_link})"
        )

    @commands.group(
        name="fakepermissions",
        aliases=["fakepermission", "fp", "fakeperms"],
        invoke_without_command=True,
        brief="Fake Permissions for roles to be used through the bot",
        example=",fakepermissions",
    )
    async def fakepermissions(self, ctx: Context):
        return await ctx.send_help(ctx.command.qualified_name)

    async def handle_fakeperm_addition(
        self, guild: discord.Guild, role: discord.Role, perms: Union[str, List[str]]
    ):
        if isinstance(perms, list):
            p = ",".join(p for p in perms)
        else:
            p = perms
        if current_perms := await self.bot.db.fetchval(
            """SELECT perms FROM fakeperms WHERE guild_id = $1 AND role_id = $2""",
            guild.id,
            role.id,
        ):
            perm = f"{current_perms},{p}"
        else:
            perm = p
        await self.bot.db.execute(
            """INSERT INTO fakeperms (guild_id, role_id, perms) VALUES($1, $2, $3) ON CONFLICT(guild_id, role_id) DO UPDATE SET perms = excluded.perms""",
            guild.id,
            role.id,
            perm,
        )
        return True

    @fakepermissions.command(
        name="add",
        brief="Add a fake permission to a role",
        example=",fakepermission add @members, manage guild",
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_add(
        self, ctx: Context, *, entry: FakePermissionConverter
    ):
        await self.handle_fakeperm_addition(ctx.guild, entry.role[0], entry.permissions)
        return await ctx.success(
            f"**Added** `{entry.permissions}` **permissions to** {entry.role[0].mention}"
        )

    @fakepermissions.command(
        name="remove",
        brief="remove fake permissions from a role",
        example=",fakepermission remove @member",
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_remove(self, ctx: Context, *, role: discord.Role):
        fake_perms = await self.bot.db.fetchrow(
            """SELECT * FROM fakeperms WHERE guild_id = $1 AND role_id = $2""",
            ctx.guild.id,
            role.id,
        )
        if not fake_perms:
            return await ctx.fail(f"**No fake permissions** are set for {role.mention}")

        await self.bot.db.execute(
            """DELETE FROM fakeperms WHERE guild_id = $1 AND role_id = $2""",
            ctx.guild.id,
            role.id,
        )
        return await ctx.success(f"**Revoked fake permissions from** {role.mention}")

    @fakepermissions.command(
        name="clear", brief="clear all fake permissions", example="fakpermissions clear"
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_clear(self, ctx: Context):
        fake_perms = await self.bot.db.fetchrow(
            """SELECT * FROM fakeperms WHERE guild_id = $1""", ctx.guild.id
        )
        if not fake_perms:
            return await ctx.fail("**No roles** have any **fake permissions** set")
        await self.bot.db.execute(
            """DELETE FROM fakeperms WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("**Revoked all fake permissions** from **all roles**")

    @fakepermissions.command(
        name="list",
        brief="show all fake permission entries",
        example=",fakepermissions list",
    )
    @commands.has_permissions(guild_owner=True)
    async def fakepermissions_list(self, ctx: Context):
        rows = []
        i = 0
        for role_id, perms in await self.bot.db.fetch(
            """SELECT role_id, perms FROM fakeperms WHERE guild_id = $1""", ctx.guild.id
        ):
            if role := ctx.guild.get_role(int(role_id)):
                i += 1
                rows.append(f"`{i}` {role.mention} - `{perms}`")
        if len(rows) == 0:
            return await ctx.fail("**No fake permissions** found for any roles")
        return await self.bot.dummy_paginator(
            ctx, Embed(title="Fake Permissions", color=self.bot.color), rows
        )

    # welcome message

    @commands.hybrid_group(
        name="welcome",
        aliases=["welc"],
        invoke_without_command=True,
        with_app_command=True,
        brief="Welcome configurations for the server",
        example=",welcome",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome(self, ctx: Context) -> discord.Message:
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @welcome.command(
        name="setup",
        aliases=["make", "create"],
        brief="setup welcome settings",
        example=",welcome setup",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_create(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchrow(
            "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Welcome settings** have **already been configured** for this server"
            )

        await self.bot.db.execute(
            "INSERT INTO welcome (guild_id, channel_id, message) VALUES ($1, $2, $3)",
            ctx.guild.id,
            ctx.channel.id,
            "welcome {user}",
        )
        self.bot.cache.welcome[ctx.guild.id] = {
            "channel": ctx.channel.id,
            "message": "welcome {user}",
        }
        await ctx.success("**Configured the welcome** for this server")

    @welcome.command(
        name="channel",
        aliases=["chan"],
        brief="Set the welcome channel",
        example=",welcome channel #welcomechannel",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_channel(
        self, ctx: Context, channel: discord.TextChannel
    ) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        if self.bot.cache.welcome.get(ctx.guild.id):
            self.bot.cache.welcome[ctx.guild.id]["channel"] = channel.id
        else:
            self.bot.cache.welcome[ctx.guild.id] = {"channel": channel.id}
        await self.bot.db.execute(
            "UPDATE welcome SET channel_id = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )
        await ctx.success(f"**Welcome channel** has been **set** to {channel.mention}")

    @welcome.command(
        name="reset",
        aliases=["remove", "delete", "off"],
        brief="Clear welcome settings",
        example=",welcome reset",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_delete(self, ctx: Context) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        self.bot.cache.welcome.pop(ctx.guild.id)
        await self.bot.db.execute(
            "DELETE FROM welcome WHERE guild_id = $1", ctx.guild.id
        )
        await ctx.success("**Deleted the welcome** for this server")

    @welcome.command(
        name="view",
        brief="View your current welcome embed code",
        example=",welcome view",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_view(self, ctx: Context):
        if not (
            data := await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        return await ctx.send(f"```{data['message']}```")

    @welcome.command(
        name="message",
        aliases=["msg"],
        brief="Set the welcome message",
        example=",welcome message wsp {user}",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_message(self, ctx: Context, *, message: str) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM welcome WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"Welcome settings have **not** been configured yet. Use `{ctx.prefix}welcome setup` first"
            )
        await self.bot.send_embed(ctx.channel, message, user=ctx.author)
        self.bot.cache.welcome[ctx.guild.id]["message"] = message
        await self.bot.db.execute(
            "UPDATE welcome SET message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        await ctx.success(f"Welcome message has been **set** to `{message}`.")

    @welcome.command(
        name="test",
        aliases=["trial"],
        brief="Test the welcome message",
        example=",welcome test",
    )
    @commands.has_permissions(manage_channels=True)
    async def welcome_test(self, ctx: Context) -> discord.Reaction:
        self.bot.dispatch("member_join", ctx.author)
        await ctx.success("**Welcome message** was sent")

    @commands.group(
        name="leave",
        aliases=["goodbye"],
        invoke_without_command=True,
        brief="Manage leave messages for when a user leaves the guild",
        example=",leave",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave(self, ctx: Context) -> discord.Message:
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @leave.command(
        name="channel",
        aliases=["chan"],
        brief="Set the leave channel",
        example=",leave channel #goodbye",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_channel(
        self, ctx: Context, channel: discord.TextChannel
    ) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )

        await self.bot.db.execute(
            "UPDATE leave SET channel_id = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )
        self.bot.cache.leave[ctx.guild.id]["channel"] = channel.id
        await ctx.success(f"Leave channel has been **set** to {channel.mention}.")

    @leave.command(name="view", brief="view your current leave embed code")
    @commands.has_permissions(manage_channels=True)
    async def leave_view(self, ctx: Context):
        if not (
            data := await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )
        return await ctx.send(f"```{data['message']}```")

    @leave.command(
        name="setup",
        aliases=["enable", "on"],
        brief="Configure leave settings",
        example=",leave setup",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_create(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchrow(
            "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Leave settings** have **already** been configured for this server"
            )

        await self.bot.db.execute(
            "INSERT INTO leave (guild_id, channel_id, message) VALUES ($1, $2, $3)",
            ctx.guild.id,
            ctx.channel.id,
            "leave {user}",
        )
        self.bot.cache.leave[ctx.guild.id] = {
            "channel": ctx.channel.id,
            "message": "leave {user}",
        }
        await ctx.success("**Leave settings** have **been configured** for this server")

    @leave.command(
        name="reset",
        aliases=["remove", "delete"],
        brief="Clear leave settings",
        example=",leave reset",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_delete(self, ctx: Context) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )

        await self.bot.db.execute("DELETE FROM leave WHERE guild_id = $1", ctx.guild.id)
        self.bot.cache.leave.pop(ctx.guild.id)
        await ctx.success("**Deleted** the leave settings")

    @leave.command(
        name="message",
        aliases=["msg"],
        brief="Set the leave message",
        example=",leave message {embed_code}",
    )
    async def leave_message(self, ctx: Context, *, message: str) -> discord.Message:
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM leave WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail(
                f"**Leave settings** have **not** been configured yet. Use `{ctx.prefix}leave setup` first"
            )
        await self.bot.send_embed(ctx.channel, message, user=ctx.author)
        self.bot.cache.leave[ctx.guild.id]["message"] = message
        await self.bot.db.execute(
            "UPDATE leave SET message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        await ctx.success(f"**Leave message** has been **set** to `{message}`")

    @leave.command(
        name="test",
        aliases=["trial"],
        brief="Test the leave message",
        example=",leave test",
    )
    @commands.has_permissions(manage_channels=True)
    async def leave_test(self, ctx: Context) -> discord.Reaction:
        self.bot.dispatch("member_remove", ctx.author)
        await ctx.success("**Leave message** has been sent")

    # boosters enable/disable and customization options for boosters in guilds.

    @commands.group(
        name="boosterroles",
        aliases=["br"],
        brief="Commands for setting up and using booster roles in your guild",
        example=",boosterroles",
    )
    async def br(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        if not (
            role_id := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE role_id = $1", role.id
            )
        ):
            return

        await self.bot.db.execute("DELETE FROM br WHERE role_id = $1", role_id)

    @commands.Cog.listener("on_member_remove")
    async def br_deletion(self, member: discord.Member):
        if role_id := await self.bot.db.fetchval(
            """SELECT role_id FROM br WHERE guild_id = $1 AND user_id = $2""",
            member.guild.id,
            member.id,
        ):
            if role := member.guild.get_role(role_id):
                await role.delete(reason="boost role auto cleanup")

    @br.command(
        name="enable",
        aliases=("on",),
        brief="Allow users to create their own role after boosting the guild",
        example=",boosterroles enable",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    @check_guild_boost_level()
    async def br_enable(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchval(
            "SELECT status FROM br_status WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Booster roles** are already **enabled** in this guild"
            )

        await self.bot.db.execute(
            "INSERT INTO br_status (guild_id, status) VALUES ($1, $2)",
            ctx.guild.id,
            True,
        )
        return await ctx.success("**Enabled booster roles** for this guild")

    @br.command(
        name="disable",
        aliases=("off",),
        brief="Disable booster roles in the guild",
        example=",boosterroles disable",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_guild=True)
    async def br_disable(self, ctx: Context) -> discord.Message:
        if not await self.bot.db.fetchval(
            "SELECT status FROM br_status WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail(
                "**Booster roles** are already **disabled** in this guild"
            )

        await self.bot.db.execute(
            "DELETE FROM br_status WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.success("**Disabled booster roles** for this guild")

    async def cleanup_boostroles(self, ctx: Context):
        for r in await self.bot.db.fetch(
            """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
        ):
            if role := ctx.guild.get_role(r):
                try:
                    await role.delete(reason="boost role cleanup")
                except Exception:
                    await self.bot.db.execute(
                        """DELETE FROM br WHERE guild_id = $1 AND role_id = $2""",
                        ctx.guild.id,
                        r,
                    )
        await self.bot.db.execute(
            """DELETE FROM br WHERE guild_id = $1""", ctx.guild.id
        )
        return True

    async def edit_position(self, ctx: Context, role: discord.Role):
        if base := await self.bot.db.fetchval(
            """SELECT role_id FROM br_base WHERE guild_id = $1""", ctx.guild.id
        ):
            if base_role := ctx.guild.get_role(base):
                return await role.edit(position=base_role.position - 1)
            else:
                return await ctx.fail(
                    f"**base role** must have been **deleted**: `{base}`"
                )
        else:
            return await ctx.fail("**No base role** set for this guild")

    async def bulk_edit_boostroles(self, ctx: Context):
        for r in await self.bot.db.fetch(
            """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
        ):
            if role := ctx.guild.get_role(r):
                await self.edit_position(ctx, role)

    @br.command(
        name="base",
        aliases=["baserole"],
        brief="Set a base role for booster roles to be created under",
        example=",boosterroles base @members",
    )
    @commands.bot_has_permissions(administrator=True)
    @commands.has_permissions(manage_roles=True)
    async def br_base(self, ctx: Context, *, role: Role = None):
        if role is None:
            await self.bot.db.execute(
                """DELETE FROM br_status WHERE guild_id = $1""", ctx.guild.id
            )
            await self.bot.db.execute(
                """DELETE FROM br_base WHERE guild_id = $1""", ctx.guild.id
            )
            await self.cleanup_boostroles(ctx)
            return await ctx.success("disabled `boost roles` and cleaned up the roles")
        else:
            role = role[0]
            if role.position >= ctx.guild.me.top_role.position:
                return await ctx.fail(
                    "**Base role** is **higher** then my **top role**"
                )
            if not await self.bot.db.fetch(
                """SELECT * FROM br_status WHERE guild_id = $1""", ctx.guild.id
            ):
                await self.bot.db.execute(
                    """INSERT INTO br_status (guild_id, status) VALUES($1,$2)""",
                    ctx.guild.id,
                    True,
                )
            await self.bot.db.execute(
                """INSERT INTO br_base (guild_id, role_id) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET role_id = excluded.role_id""",
                ctx.guild.id,
                role.id,
            )
            roles = await self.bot.db.fetch(
                """SELECT role_id FROM br WHERE guild_id = $1""", ctx.guild.id
            )
            if roles:
                msg = await ctx.success(
                    "changing all boost role positions... this may take a while..."
                )
                for rr in roles:
                    if ctx.guild.get_role(rr):  # type: ignore
                        await role.edit(position=role.position - 1)
                await msg.edit(
                    embed=discord.Embed(
                        description=f"**Base role** set to <@&{role.id}>",
                        color=self.bot.color,
                    )
                )
            else:
                return await ctx.success(f"**Base role** set to {role.mention}")

    @br.command(
        name="share",
        aliases=("give",),
        brief="Share your booster role with another user",
        example=",boosterroles share @o_5v",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_share(self, ctx: Context, *, member: discord.Member):
        if data := await self.bot.db.fetchval(
            """SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2""",
            ctx.author.id,
            ctx.guild.id,
        ):
            if role := ctx.guild.get_role(data):
                await member.add_roles(role)
            else:
                return await ctx.fail("your booster role **doesn't exist**")
        else:
            return await ctx.fail("your booster role **doesn't exist**")
        return await ctx.success(
            f"successfully shared your booster role to **{member.mention}**"
        )

    @br.command(
        "create",
        aliases=("make",),
        brief="Create a custom booster role for boosting the guild",
        example=",boosterroles create topG",
    )
    @check_br_status()
    @commands.bot_has_permissions(administrator=True)
    async def br_create(
        self, ctx: Context, *, name: str, color: int = 3447003
    ) -> discord.Message:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        rolename = f"{name}"
        exists = await self.bot.db.fetchval(
            "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
            author.id,
            ctx.guild.id,
        )
        if exists:
            return await ctx.fail("You already have a **booster role** in this guild")

        # Remove the icon parameter from create_role
        role = await ctx.guild.create_role(name=rolename, color=discord.Color(color))
        if base := await self.bot.db.fetchval(
            """SELECT role_id FROM br_base WHERE guild_id = $1""", ctx.guild.id
        ):
            if base_role := ctx.guild.get_role(base):
                await role.edit(position=base_role.position - 1)
        await author.add_roles(role, reason="BoosterRole")
        await self.bot.db.execute(
            "INSERT INTO br (user_id, role_id, guild_id) VALUES ($1, $2, $3)",
            author.id,
            role.id,
            ctx.guild.id,
        )
        return await ctx.success(
            f"**Created** your own **booster role**: {role.mention} with the color `{hex(typing.cast(int, color))}`"
        )

    @br.command(
        "delete",
        aliases=("remove", "del", "rm"),
        brief="Remove your custom booster role from the guild",
        example=",boosterroles remove",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_delete(self, ctx: Context) -> discord.Message | None:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )

        role = ctx.guild.get_role(int(role))
        if role:
            await role.delete(reason="BoosterRole")
            await self.bot.db.execute(
                "DELETE FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
            return await ctx.success("**Deleted** your **booster role** in this guild")

    @br.command(
        "rename",
        aliases=("name",),
        brief="Rename your custom booster role in this guild",
        example=",boosterroles rename littleG",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_rename(self, ctx: Context, name: str) -> discord.Message | None:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )

        role = ctx.guild.get_role(int(role))
        if role:
            await role.edit(
                name=f"{name}",
                reason="BoosterRole",
            )
            return await ctx.success(
                f"**Renamed** your **booster role** to {role.mention}"
            )

    @br.command(
        "color",
        aliases=("colour",),
        brief="Change the color or recolor your custom booster role in this guild",
        example=",boosterroles color #2b2d31",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_color(
        self, ctx: Context, *, color: ColorConverter
    ) -> discord.Message | None:
        author: discord.Member = typing.cast(discord.Member, ctx.author)
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )

        role = ctx.guild.get_role(int(role))
        if role:
            await role.edit(color=color, reason="BoosterRole")
            return await ctx.success(
                f"**Changed** your **booster role's color** to {role.mention}"
            )

    async def get_icon(
        self, url: Optional[Union[discord.Emoji, discord.PartialEmoji, str]] = None
    ):
        if url is None:
            return None
        if isinstance(url, discord.Emoji):
            return await url.read()
        elif isinstance(url, discord.PartialEmoji):
            return await url.read()
        else:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.read()
            return data

    @br.command(
        "icon",
        aliases=("icn",),
        brief="Set or Change the current icon you have set for your custom booster role in this guild",
        example=",boosterroles icon :blunt:",
    )
    @commands.bot_has_permissions(administrator=True)
    @check_br_status()
    async def br_icon(
        self,
        ctx,
        *,
        icon: Optional[Union[discord.Emoji, discord.PartialEmoji, str]] = None,
    ) -> discord.Message:
        if isinstance(icon, str):
            if not icon.startswith("https://"):
                return await ctx.fail("that is not a valid URL")
        author = ctx.author
        if not (
            role := await self.bot.db.fetchval(
                "SELECT role_id FROM br WHERE user_id = $1 AND guild_id = $2",
                author.id,
                ctx.guild.id,
            )
        ):
            return await ctx.fail(
                "You **do not** have a **booster role** in this guild"
            )
        role = ctx.guild.get_role(role)
        icon = await self.get_icon(icon)
        if icon is None:
            if not role.display_icon:
                return await ctx.fail(
                    "Your **booster role** does not have an **icon** set"
                )
        await role.edit(display_icon=icon, reason="BoosterRole")
        if icon:
            return await ctx.success("**Booster role icon changed**")
        else:
            return await ctx.success(
                "**Booster roles icon** has been **reset** for this guild"
            )

    # Autorole setup for guilds.

    @commands.group(
        name="autorole",
        aliases=["arole"],
        example=",autorole",
        brief="Configure autorole settings through wock",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    async def autorole(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @autorole.command(
        name="add",
        aliases=["set"],
        brief="Add an autorole or autoroles",
        example=",autorole add @member",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    @query_limit("autorole", 3)
    async def autorole_add(self, ctx: commands.Context, *, roles: Role):
        if not roles:
            return await ctx.fail("No valid roles were mentioned.")
        await self.bot.db.fetch(  # type: ignore
            "SELECT COUNT(*) FROM autorole WHERE guild_id = $1",
            ctx.guild.id,
        )
        for role in roles:
            if not await self.bot.db.fetch(
                "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            ):
                await self.bot.db.execute(
                    "INSERT INTO autorole (guild_id, role_id) VALUES ($1, $2)",
                    ctx.guild.id,
                    role.id,
                )
        data = await self.bot.db.fetch(
            """SELECT role_id FROM autorole WHERE guild_id = $1""", ctx.guild.id
        )
        self.bot.cache.autorole[ctx.guild.id] = [_data.role_id for _data in data]
        added_roles = [f"<@&{role.id}>" for role in roles]
        await ctx.success(
            f"**Autorole** will give {', '.join(added_roles)} to **users on join**"
        )

    @autorole.command(
        name="remove",
        aliases=["delete"],
        brief="Remove an autorole or autoroles",
        example=",autorole remove member",
    )
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    async def autorole_remove(self, ctx: commands.Context, *, roles: Role):
        for role in roles:
            if not await self.bot.db.fetch(
                "SELECT * FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            ):
                return await ctx.fail(
                    f"`{role.name}` is **not** set as an **autorole**"
                )
            await self.bot.db.execute(
                "DELETE FROM autorole WHERE guild_id = $1 AND role_id = $2",
                ctx.guild.id,
                role.id,
            )
        data = await self.bot.db.fetch(
            """SELECT role_id FROM autorole WHERE guild_id = $1""", ctx.guild.id
        )
        self.bot.cache.autorole[ctx.guild.id] = [_data.role_id for _data in data]
        return await ctx.success(
            f"**Removed** {', '.join([f'<@&{x.id}>' for x in roles])} from the **autoroles list**"
        )

    @autorole.command(name="list", brief="list all autoroles", example=",autorole list")
    @commands.has_permissions(manage_guild=True)
    @commands.bot_has_permissions(administrator=True)
    async def autorole_list(self, ctx: commands.Context):
        guild = ctx.guild
        embed = discord.Embed(title=f"{guild.name} Autoroles", color=self.bot.color)
        embed.set_author(name=guild.name, icon_url=guild.icon)
        if data := await self.bot.db.fetch(
            "SELECT * FROM autorole WHERE guild_id = $1",
            ctx.guild.id,
        ):
            roles = [
                f"``{i+1}.`` {guild.get_role(x['role_id']).mention}"
                for i, x in enumerate(data)
            ]
            embed.description = "\n".join(roles)
        else:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: There are **no autoroles** set",
                color=0x2D2B31,
            )
        await ctx.send(embed=embed)

    async def add_react(
        self,
        ctx: Context,
        _type: str,
        react: discord.Emoji | discord.PartialEmoji | str,
    ):
        emoji = react  # ((b64encode(str(reaction).encode()).decode() if isinstance(b64encode(str(reaction).encode()), bytes) else b64encode(str(reaction).encode()) if not is_unicode(reaction) else reaction ) if not is_unicode(reaction) else reaction,)
        if not self.bot.cache.autoreacts.get(ctx.guild.id):
            self.bot.cache.autoreacts[ctx.guild.id] = {}
        if not self.bot.cache.autoreacts[ctx.guild.id].get(_type):
            self.bot.cache.autoreacts[ctx.guild.id][_type] = []
        self.bot.cache.autoreacts[ctx.guild.id][_type].append(emoji)
        return True

    @commands.group(
        name="autoreact",
        aliases=(
            "reaction",
            "autoreaction",
            "autoreactions",
        ),
        brief="Configure the autoreactions for the guild",
        example=",autoreact",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact(self: "Servers", ctx: Context):
        """
        Set up automatic reactions to messages that match a trigger
        """

        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @autoreact.group(
        name="add",
        brief="Automatically react to phrases said",
        example=",autoreact add com :skull:",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add(self: "Servers", ctx: Context, *, args: Argument):
        """
        Add a reaction to a trigger
        """
        trigger = args.first
        reactions = args.second
        reactions = await Emojis().convert(ctx, reactions)
        for reaction in reactions:
            reaction = str(reaction)
            if reaction in tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact WHERE guild_id = $1 AND keyword = $2",
                    ctx.guild.id,
                    trigger,
                )
            ):
                return await ctx.fail(
                    "**That auto-reply event** reaction already exists"
                )

            if (
                await self.bot.db.fetchval(
                    "SELECT COUNT(*) FROM autoreact WHERE guild_id = $1 AND keyword = $2;",
                    ctx.guild.id,
                    trigger,
                )
                > 15
            ):
                return await ctx.fail("**Too many reactions** set for that event")

            if len(trigger) > 32:
                return await ctx.fail("Provide a trigger **under 32 characters**")
            if self.bot.cache.autoreacts.get(ctx.guild.id):
                if self.bot.cache.autoreacts[ctx.guild.id].get(trigger):
                    self.bot.cache.autoreacts[ctx.guild.id][trigger].append(reaction)
                else:
                    self.bot.cache.autoreacts[ctx.guild.id][trigger] = [reaction]
            else:
                self.bot.cache.autoreacts[ctx.guild.id] = {trigger: [reaction]}

            await self.bot.db.execute(
                "INSERT INTO autoreact (guild_id, keyword, reaction) VALUES ($1, $2, $3);",
                ctx.guild.id,
                trigger,
                reaction,
            )
        reaction_str = " ".join(str(m) for m in reactions)
        return await ctx.success(
            f"**Created** {reaction_str} as a reaction for `{trigger}`"
        )

    @autoreact_add.command(
        name="images",
        brief="Automatically react to images sent",
        example=",autoreact add images :sob:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_images(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Add a reaction for images
        """

        if reaction is None:
            return await ctx.fail("**Emoji could not** be found")
        reaction = str(reaction)
        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "images",
            )
        ):
            return await ctx.fail(
                "**That auto-reaction** for images **already exists**"
            )

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "images",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exists")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("images"):
                if isinstance(self.bot.cache.autoreacts[ctx.guild.id]["images"], str):
                    self.bot.cache.autoreacts[ctx.guild.id]["images"] = [
                        self.bot.cache.autoreacts[ctx.guild.id]["images"]
                    ]
                self.bot.cache.autoreacts[ctx.guild.id]["images"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["images"] = reaction
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"images": reaction}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "images",
            reaction,
        )

        return await ctx.success(f"**Created** {reaction} as a **reaction for images**")

    @autoreact_add.command(
        name="spoilers",
        brief="Automatically react to spoiler images",
        example=",autoreact add spoilers :shh:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_spoilers(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Add a reaction for spoilers
        """

        if reaction is None:
            return await ctx.fail("**Emoji** does not exist")
        reaction = str(reaction)
        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "spoilers",
            )
        ):
            return await ctx.fail(
                "**That auto-reaction** for spoilers **already exists**"
            )

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "spoilers",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exists")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("spoilers"):
                self.bot.cache.autoreacts[ctx.guild.id]["spoilers"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["spoilers"] = [reaction]
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"spoilers": [reaction]}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "spoilers",
            reaction,
        )

        return await ctx.success(
            f"**Created** {reaction} as a **reaction for spoilers**"
        )

    @autoreact_add.command(
        name="emojis",
        brief="Automatically react to emojis sent",
        example=",autoreaction add emojis :wave:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_emojis(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Add a reaction for emojis
        """

        if reaction is None:
            return await ctx.fail("**Emoji** could not be found")
        reaction = str(reaction)
        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "emojis",
            )
        ):
            return await ctx.fail("That is already an **auto-reaction** for emojis.")

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "emojis",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exists")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("emojis"):
                self.bot.cache.autoreacts[ctx.guild.id]["emojis"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["emojis"] = [reaction]
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"emojis": [reaction]}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "emojis",
            reaction,
        )

        return await ctx.success(f"**Created** {reaction} as a **reaction for emojis**")

    @autoreact_add.command(
        name="stickers",
        brief="Automatically react to stickers sent",
        example=",autoreact add stickers :zzz:",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_add_stickers(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Add a reaction for stickers
        """
        reaction = str(reaction)
        if reaction is None:
            return await ctx.fail("**Emoji** could **not** be found")

        if reaction in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "stickers",
            )
        ):
            return await ctx.fail("That is already an **auto-reaction** for stickers")

        if (
            await self.bot.db.fetchval(
                "SELECT COUNT(*) FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                "stickers",
            )
            > 15
        ):
            return await ctx.fail("**Too many reactions** for that event exist")
        if self.bot.cache.autoreacts.get(ctx.guild.id):
            if self.bot.cache.autoreacts[ctx.guild.id].get("stickers"):
                self.bot.cache.autoreacts[ctx.guild.id]["stickers"].append(reaction)
            else:
                self.bot.cache.autoreacts[ctx.guild.id]["stickers"] = [reaction]
        else:
            self.bot.cache.autoreacts[ctx.guild.id] = {"stickers": [reaction]}

        await self.bot.db.execute(
            "INSERT INTO autoreact_event (guild_id, event, reaction) VALUES ($1, $2, $3);",
            ctx.guild.id,
            "stickers",
            reaction,
        )

        return await ctx.success(
            f"**Created** {reaction} as a **reaction for stickers**"
        )

    @autoreact.group(
        name="remove",
        brief="Remove the autoreaction for phrases said",
        example=",reaction remove com",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove(
        self: "Servers", ctx: Context, trigger: str, reaction: Optional[Emoji] = None
    ):
        """
        Remove a reaction from an auto-react trigger
        """

        if reaction is not None:
            reaction = str(reaction)
            if reaction not in tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact WHERE guild_id = $1 AND keyword = $2",
                    ctx.guild.id,
                    trigger,
                )
            ):
                return await ctx.fail("**Auto-reaction** does not exist")

            await self.bot.db.execute(
                "DELETE FROM autoreact WHERE keyword = $1 AND reaction = $2;",
                trigger,
                reaction,
            )
            try:
                self.bot.cache.autoreacts[ctx.guild.id][trigger].remove(reaction)
            except Exception:
                try:
                    self.bot.cache.autoreacts[ctx.guild.id][trigger].remove(
                        str(reaction)
                    )
                except Exception:
                    pass

        else:
            await self.bot.db.execute(
                """DELETE FROM autoreact WHERE keyword = $1 AND guild_id = $2""",
                trigger,
                ctx.guild.id,
            )
            try:
                self.bot.cache.autoreacts[ctx.guild.id].pop(trigger)
            except Exception:
                pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="images",
        brief="Remove autoreactions for images sent",
        example=",autoreaction remove images",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_images(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Remove a reaction for images
        """
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "images",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "images",
            reaction,
        )
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["images"].remove(reaction)
        except Exception:
            pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="spoilers",
        brief="Remove autoreactions for spoilers sent",
        example=",autoreaction remove spoilers",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_spoilers(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Remove a reaction for spoilers
        """
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "spoilers",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "spoilers",
            reaction,
        )
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["spoilers"].remove(reaction)
        except Exception:
            pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="emojis",
        brief="Remove autoreactions for emojis sent",
        example=",autoreaction remove emojis",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_emojis(self: "Servers", ctx: Context, reaction: Emoji):
        """
        Remove a reaction for emojis
        """
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "emojis",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "emojis",
            reaction,
        )
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["emojis"].remove(reaction)
        except Exception:
            pass

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact_remove.command(
        name="stickers",
        usage="Remove autoreactions for stickers sent",
        example=",autoreaction remove stickers",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_remove_stickers(self: "Servers", ctx: Context, reaction: Emoji):
        reaction = str(reaction)
        if reaction not in tuple(
            record.reaction
            for record in await self.bot.db.fetch(
                "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                "stickers",
            )
        ):
            return await ctx.fail("**Auto-reaction** does not exist")
        try:
            self.bot.cache.autoreacts[ctx.guild.id]["stickers"].remove(reaction)
        except Exception:
            pass
        await self.bot.db.execute(
            "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2 AND reaction = $3;",
            ctx.guild.id,
            "stickers",
            reaction,
        )

        return await ctx.success("**Removed** that **auto-reaction**")

    @autoreact.command(
        name="clear",
        brief="remove all autoreactions from the guild",
        example="autoreaction clear",
    )
    async def autoreact_clear(
        self: "Servers", ctx: Context, type: Optional[str] = None
    ):
        if not await self.bot.db.fetch(
            "SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ) and not await self.bot.db.fetch(
            "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Auto-reaction triggers** do not exist")

        if type is not None:
            if type.lower() not in ("images", "spoilers", "emojis", "stickers"):
                return await ctx.fail("**Auto-reaction event** does not exist")

            if not await self.bot.db.fetch(
                "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
            ):
                return await ctx.fail("**Auto-reaction event** does not exist")

            if not await self.bot.db.fetch(
                "SELECT * FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                ctx.guild.id,
                type.lower(),
            ):
                return await ctx.fail("**Auto-reaction event** does not exist")
            try:
                self.bot.cache.autoreacts.pop(ctx.guild.id)
            except Exception:
                pass
            await self.bot.db.execute(
                "DELETE FROM autoreact_event WHERE guild_id = $1 AND event = $2;",
                ctx.guild.id,
                type.lower(),
            )

            return await ctx.success(
                "**Cleared** every **auto-reaction** for that event"
            )

        if await self.bot.db.fetch(
            "SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ):
            await self.bot.db.execute(
                "DELETE FROM autoreact WHERE guild_id = $1;", ctx.guild.id
            )

        if await self.bot.db.fetch(
            "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            await self.bot.db.execute(
                "DELETE FROM autoreact_event WHERE guild_id = $1;", ctx.guild.id
            )
        try:
            self.bot.cache.autoreacts.pop(ctx.guild.id)
        except Exception:
            pass
        return await ctx.success("**Cleared** every **auto-reaction trigger**")

    @autoreact.command(
        name="removeall",
        aliases=("deleteall",),
        example=",autoreact removeall",
        brief="Remove and reset every auto reaction trigger",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_removeall(self: "Servers", ctx: Context, trigger: str):
        if trigger not in tuple(
            record.keyword
            for record in await self.bot.db.fetch(
                "SELECT keyword FROM autoreact WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail("**Auto-reaction trigger** does not exist")

        await self.bot.db.execute(
            "DELETE FROM autoreact WHERE guild_id = $1 AND keyword = $2;",
            ctx.guild.id,
            trigger,
        )
        try:
            self.bot.cache.autoreacts.pop(ctx.guild.id)
        except Exception:
            pass

        return await ctx.success("**Cleared** every **auto-reaction** for that trigger")

    @autoreact.command(
        name="list",
        brief="View all autoreactions currenctly set for phrases",
        example=",autoreaction list",
    )
    @commands.has_permissions(manage_emojis=True)
    async def autoreact_list(self: "Servers", ctx: Context):
        """
        View every auto-reaction trigger
        """

        if not await self.bot.db.fetch(
            "SELECT * FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ):
            if not await self.bot.db.fetch(
                "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
            ):
                return await ctx.fail("**Auto-reaction triggers** does not exist")

        text = []
        keywords_covered = []
        events = {}
        for record in await self.bot.db.fetch(
            "SELECT event, reaction FROM autoreact_event WHERE guild_id = $1",
            ctx.guild.id,
        ):
            if record.event in events:
                events[record.event].append(record.reaction)
            else:
                events[record.event] = [record.reaction]

        for record in await self.bot.db.fetch(
            "SELECT keyword, reaction FROM autoreact WHERE guild_id = $1", ctx.guild.id
        ):
            if record.keyword in keywords_covered:
                continue

            reactions = tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact WHERE guild_id = $1 AND keyword = $2",
                    ctx.guild.id,
                    record.keyword,
                )
            )

            text.append(
                f"**{record.keyword}** - Reactions: {', '.join((str(reaction)) for reaction in reactions)}"
            )
            logger.info(text)
            keywords_covered.append(record.keyword)
        for k, v in events.items():
            text.append(
                f"**{k}** - Reactions: {', '.join((str(reaction)) for reaction in v)}"
            )
        return await self.bot.dummy_paginator(
            ctx, discord.Embed(title="Auto Reactions", color=self.bot.color), text
        )
        return await ctx.paginate(  # type: ignore
            embed_creator(
                text.getvalue(),
                1980,
                color=self.bot.color,
                title=f"Auto-Reaction Triggers in '{ctx.guild.name}'",
            )
        )

    # @autoreact.command(name="extras", aliases=("listextras", "events", "listevents"), brief='list all autoreactions set for extras (ex. images)', example=',autoreactions extras')
    ##@commands.has_permissions(manage_emojis=True)
    async def autoreact_listextras(self: "Servers", ctx: Context):
        """
        View every auto-reaction event trigger
        """

        if not await self.bot.db.fetch(
            "SELECT * FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Auto-reaction event triggers** does not exist")

        text = StringIO()
        events_covered = []

        for record in await self.bot.db.fetch(
            "SELECT event FROM autoreact_event WHERE guild_id = $1", ctx.guild.id
        ):
            if record.event in events_covered:
                continue

            reactions = tuple(
                record.reaction
                for record in await self.bot.db.fetch(
                    "SELECT reaction FROM autoreact_event WHERE guild_id = $1 AND event = $2",
                    ctx.guild.id,
                    record.event,
                )
            )

            text.write(
                f"**{record.event}** - Reactions: {', '.join((b64decode(reaction.encode()).decode() if len(tuple(reaction)) > 1 else reaction) for reaction in reactions)}"
            )
            events_covered.append(record.event)

        return await ctx.paginate(
            embed_creator(
                text.getvalue(),
                1980,
                color=self.bot.color,
                title=f"{ctx.guild.name} Auto-Reactions",
            )
        )

    @commands.group(
        name="reactionrole",
        aliases=["reactionroles", "rr", "reactrole"],
        example=",reactionrole",
        brief="Configure reaction role settings",
    )
    @commands.has_permissions(manage_roles=True)
    async def reactionrole(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @reactionrole.command(
        name="add",
        aliases=["a", "create", "c"],
        brief="Add a reaction role to a message",
        example=",autoreaction add [message_id] [emoji] [roles]",
    )
    async def reactionrole_add(
        self,
        ctx: Context,
        message: discord.Message,
        emoji: discord.Emoji | str,
        *,
        roles: Role,
    ):
        emoji = str(emoji)
        role = roles[0]
        if await self.bot.db.fetch(
            """SELECT * FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4 AND role_id = $5""",
            ctx.guild.id,
            message.channel.id,
            message.id,
            emoji,
            role.id,
        ):
            await self.bot.db.execute(
                """DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4 AND role_id = $5""",
                ctx.guild.id,
                message.channel.id,
                message.id,
                emoji,
                role.id,
            )
        await self.bot.db.execute(
            """INSERT INTO reactionrole (guild_id,channel_id,message_id,emoji,role_id,message_url) VALUES($1,$2,$3,$4,$5,$6) ON CONFLICT(guild_id,channel_id,message_id,emoji,role_id) DO UPDATE SET role_id = excluded.role_id""",
            ctx.guild.id,
            message.channel.id,
            message.id,
            emoji,
            role.id,
            message.jump_url,
        )
        await message.add_reaction(emoji)
        return await ctx.success("**Reaction role** has been **added to that meesage**")

    def get_emoji(self, emoji: str):
        try:
            emoji = emoji
            return emoji
        except Exception:
            return emoji

    @reactionrole.command(
        name="remove",
        aliases=["delete", "del", "rem", "r", "d"],
        brief="Remove a reaction role from a message",
        example=",reactionrole remove [message_id] [emoji]",
    )
    async def reactionrole_remove(
        self,
        ctx: Context,
        message: discord.Message,
        emoji: discord.Emoji | discord.PartialEmoji | str,
    ):
        if isinstance(emoji, (discord.Emoji, discord.PartialEmoji)):
            emoji = str(emoji)
        else:
            emoji = emoji
        await self.bot.db.execute(
            """DELETE FROM reactionrole WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4""",
            ctx.guild.id,
            message.channel.id,
            message.id,
            emoji,
        )
        return await ctx.success("**Removed** the **reaction role**")

    @reactionrole.command(
        name="clear",
        brief="Clear all reaction roles from a message",
        example=",reactionrole clear",
    )
    async def reactionrole_clear(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM reactionrole WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("**Cleared** all **reaction roles** if any exist")

    @reactionrole.command(
        name="list",
        brief="View a list of all reaction roles set to messages",
        example=",reactionrole list",
    )
    async def reactionrole_list(self, ctx: Context):
        rows = []
        i = 0
        for (
            channel_id,
            message_id,  # type: ignore
            emoji,
            role_id,
            message_url,
        ) in await self.bot.db.fetch(
            """SELECT channel_id,message_id,emoji,role_id,message_url FROM reactionrole WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            if ctx.guild.get_channel(channel_id):  # type: ignore
                emoji = self.get_emoji(str(emoji))
                if role := ctx.guild.get_role(role_id):
                    i += 1
                    rows.append(
                        f"`{i}.` [Message]({message_url}) - {emoji} - {role.mention}"
                    )
        embed = discord.Embed(
            title=f"{ctx.guild.name}'s reaction roles",
            url="https://wock.bot",
            color=self.bot.color,
        )
        if len(rows) == 0:
            return await ctx.fail("**No reaction roles found**")
        return await self.bot.dummy_paginator(ctx, embed, rows, 10, "reaction role")

    @commands.group(
        "autoresponder",
        aliases=["ar", "autoresponse"],
        example=",autoresponder",
        brief="Configure auto responses for your server",
    )
    @commands.has_permissions(manage_messages=True)
    async def autoresponder(self, ctx: Context):
        if ctx.subcommand_passed is not None:  # Check if a subcommand was passed
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @autoresponder.command(
        name="add",
        aliases=["a", "create"],
        brief="Add an automatic response to given phrase",
        example=",autoresponder add com, you're a troll",
    )
    async def autoresponder_add(self, ctx: Context, *, arg: Argument):
        #        if "," not in arg: return await ctx.fail('use a comma to split the trigger and response')

        trigger = arg.first
        response = arg.second
        if ctx.guild.id in self.bot.cache.autoresponders:
            if trigger in self.bot.cache.autoresponders[ctx.guild.id]:
                self.bot.cache.autoresponders[ctx.guild.id][trigger] = response
            else:
                self.bot.cache.autoresponders[ctx.guild.id][trigger] = response
        else:
            self.bot.cache.autoresponders[ctx.guild.id] = {trigger: response}
        await self.bot.db.execute(
            """INSERT INTO autoresponder (guild_id,trig,response) VALUES($1,$2,$3) ON CONFLICT (guild_id,trig) DO UPDATE SET response = excluded.response""",
            ctx.guild.id,
            trigger,
            response,
        )
        await ctx.success(f"**Auto-responder** ``{trigger}`` applied")

    @autoresponder.command(
        name="remove",
        aliases=["del", "d", "r", "rem"],
        brief="Remove an automatic response from a given phrase",
        example=",autoresponder remove hi",
    )
    async def autoresponder_remove(self, ctx: Context, *, trigger: str):
        if ctx.guild.id not in self.bot.cache.autoresponders:
            return await ctx.fail("**Auto-Response** has not been **setup**")
        if trigger not in self.bot.cache.autoresponders[ctx.guild.id]:
            return await ctx.fail(
                f"**No auto-responder** found with trigger **{trigger}**"
            )
        await self.bot.db.execute(
            """DELETE FROM autoresponder WHERE guild_id = $1 AND trig = $2""",
            ctx.guild.id,
            trigger,
        )
        self.bot.cache.autoresponders[ctx.guild.id].pop(trigger)
        return await ctx.success(
            f"**Auto-responder** with the trigger ``{trigger}`` **Removed**"
        )

    @autoresponder.command(
        name="clear",
        aliases=["cl"],
        brief="Clear all the current auto responders",
        example=",autoresponder clear",
    )
    async def autoresponder_clear(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM autoresponder WHERE guild_id = $1""", ctx.guild.id
        )
        try:
            self.bot.cache.autoresponders.pop(ctx.guild.id)
        except Exception:
            pass
        return await ctx.success("**Cleared** all **auto-responders**")

    @autoresponder.command(
        name="list",
        aliases=["l", "show"],
        brief="Show a list of all current auto responses",
        example=",autoresponder list",
    )
    async def autoresponder_list(self, ctx: Context):
        rows = [
            f"`{trig}` - `{response}`"
            for trig, response in await self.bot.db.fetch(
                """SELECT trig,response FROM autoresponder WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ]
        if len(rows) > 0:
            embed = discord.Embed(
                title=f"{ctx.guild.name}'s auto-responders",
                url="https://wock.bot",
                color=self.bot.color,
            )
            await self.bot.dummy_paginator(ctx, embed, rows, 10, "autoresponder")
        else:
            return await ctx.fail("**Server** has no **auto-responders setup**")

    @commands.group(
        name="boostmessage",
        aliases=["bm"],
        brief="Configure boost messages for the server",
        example=",boostmessage",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg(self, ctx: Context):
        if ctx.subcommand_passed is not None:
            return
        return await ctx.send_help(ctx.command.qualified_name)

    @boostmsg.command(
        name="setup",
        aliases=(
            "on",
            "enable",
        ),
        brief="Enable boost messages for the guild",
        example=",boostmessage setup",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_enable(self, ctx: Context) -> discord.Message:
        if await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are already **enabled**")

        await self.bot.db.execute(
            "INSERT INTO guild.boost (guild_id, channel_id, message) VALUES ($1, $2, $3)",
            ctx.guild.id,
            ctx.channel.id,
            "Thank you for boosting the server, {user.mention}!",
        )
        return await ctx.success("**Enabled** boost messages")

    @boostmsg.command(
        name="reset",
        aliases=(
            "off",
            "disable",
        ),
        brief="Disable boost messages for the guild",
        example=",boostmessage reset",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_disable(self, ctx: Context) -> discord.Message:
        if not await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are already **disabled**")

        await self.bot.db.execute(
            "DELETE FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        )
        return await ctx.success("**Disabled** boost messages")

    @boostmsg.command(
        name="channel",
        aliases=("chan",),
        brief="Assign a channel for boost messages to be sent",
        example=",boostmessage channel #boostchannel",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_channel(
        self, ctx: Context, channel: discord.TextChannel
    ) -> discord.Message:
        if not await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are not **enabled**")

        await self.bot.db.execute(
            "UPDATE guild.boost SET channel_id = $1 WHERE guild_id = $2",
            channel.id,
            ctx.guild.id,
        )
        return await ctx.success(f"**Boost message channel** set to {channel.mention}")

    @boostmsg.command(
        name="message",
        aliases=("msg",),
        brief="Set the message to be sent when someone boosts the guild",
        example=",boostmessage message [code]",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_message(self, ctx: Context, *, message: str) -> discord.Message:
        if not await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", ctx.guild.id
        ):
            return await ctx.fail("**Boost messages** are not **enabled**")
        await self.bot.send_embed(ctx.channel, message, user=ctx.author)
        await self.bot.db.execute(
            "UPDATE guild.boost SET message = $1 WHERE guild_id = $2",
            message,
            ctx.guild.id,
        )
        return await ctx.success(f"**Boost message** set to ``{message}``")

    @boostmsg.command(
        name="view",
        brief="View the current boost message embed code",
        example=",boostmessage view",
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchrow(
                "SELECT message FROM guild.boost WHERE guild_id = $1", ctx.guild.id
            )
        ):
            return await ctx.fail("**Boost messages** are not **enabled**")
        return await ctx.success(f"```{message}```")

    @boostmsg.command(
        name="test", brief="Test the set boost message", example=",boostmessage test"
    )
    @commands.has_permissions(manage_guild=True)
    async def boostmsg_test(self, ctx: Context):
        msg = copy.copy(ctx.message)
        msg.type = discord.MessageType.premium_guild_subscription
        msg.content = ctx.message.content.strip(ctx.prefix)
        self.bot.dispatch("message", msg)
        return await ctx.success("**Boost message** was sent")


async def setup(bot: "Wock") -> None:
    await bot.add_cog(Servers(bot))
