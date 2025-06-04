import unicodedata
from contextlib import asynccontextmanager, contextmanager, suppress
from io import BytesIO
from logging import Logger, getLogger
from time import time
from typing import (TYPE_CHECKING, AsyncGenerator, Callable, Generator, List,
                    Optional, Tuple)

import dateparser
import humanize
from anyio import Path as AsyncPath
from colorthief import ColorThief
from core.client.context import Context
from discord import Color, HTTPException, Member, Message, PartialMessage, Role
from discord.ext.commands import CommandInvokeError
from discord.ext.commands import FlagConverter as OriginalFlagConverter
from discord.utils import run_in_executor
from typing_extensions import Self
from wand.image import Image

from .human import fmtseconds

TMP_ROOT = AsyncPath("/tmp")
CACHE_ROOT = TMP_ROOT / "mono"


class FlagConverter(
    OriginalFlagConverter,
    case_insensitive=True,
    prefix="--",
    delimiter=" ",
):
    @property
    def values(self):
        return self.get_flags().values()

    async def convert(self, ctx: Context, argument: str):
        argument = argument.replace("—", "--")
        return await super().convert(ctx, argument)

    async def find(
        self,
        ctx: Context,
        argument: str,
        *,
        remove: bool = True,
    ) -> Tuple[str, Self]:
        """
        Run the conversion and return the
        result with the remaining string.
        """
        argument = argument.replace("—", "--")
        flags = await self.convert(ctx, argument)

        if remove:
            for key, values in flags.parse_flags(argument).items():
                aliases = getattr(self.get_flags().get(key), "aliases", [])
                for _key in aliases:
                    argument = argument.replace(f"--{_key} {' '.join(values)}", "")
                argument = argument.replace(f"--{key} {' '.join(values)}", "")

        return argument.strip(), flags


class Error(CommandInvokeError):
    def __init__(self, message: str):
        self.message: str = message


async def quietly_delete(message: Message | PartialMessage) -> None:
    if not message.guild:
        return

    if message.channel.permissions_for(message.guild.me).manage_messages:
        with suppress(HTTPException):
            await message.delete()


@run_in_executor
def convert_image(buffer: bytes, format: str) -> bytes:
    image = Image(blob=buffer)
    return image.make_blob(format)  # type: ignore


@run_in_executor
def enlarge_emoji(buffer: bytes, suffix: str) -> Tuple[Optional[bytes], str]:
    try:
        with Image(blob=buffer) as img:
            img.resize(128, 128)
            if suffix.lower() != "png":
                img.format = "png"
                suffix = "png"
            enlarged_buffer = img.make_blob()
        return enlarged_buffer, suffix
    except Exception:
        return None, suffix


def is_dangerous(role: Role) -> bool:
    dangerous_permissions = {
        "administrator",
        "kick_members",
        "ban_members",
        "manage_guild",
        "manage_roles",
        "manage_channels",
        "manage_emojis",
        "manage_webhooks",
        "manage_nicknames",
        "mention_everyone",
    }
    return any(
        value and permission in dangerous_permissions
        for permission, value in role.permissions
    )


async def strip_roles(
    member: Member,
    *,
    dangerous: bool = False,
    reason: Optional[str] = None,
) -> bool:
    """
    Remove all roles from a member.
    """
    bot = member.guild.me
    if member.top_role >= bot.top_role and bot.id != member.guild.owner_id:
        return False

    roles: List[Role] = [
        role
        for role in member.roles[1:]
        if role.is_assignable() and (not dangerous or is_dangerous(role))
    ]

    if roles:
        with suppress(HTTPException):
            await member.remove_roles(*roles, reason=reason)
            return True

    return False


async def aenumerate(asequence, start=0):
    n = start
    async for elem in asequence:
        yield n, elem
        n += 1


def get_timestamp(value: str):
    return dateparser.parse(str(value))


def ordinal(value: int) -> str:
    return humanize.ordinal(value)


def duration(value: float, ms: bool = True) -> str:
    h = int((value / (1000 * 60 * 60)) % 24) if ms else int((value / (60 * 60)) % 24)
    m = int((value / (1000 * 60)) % 60) if ms else int((value / 60) % 60)
    s = int((value / 1000) % 60) if ms else int(value % 60)

    result = f"{h}:" if h else ""
    result += f"{m}:" if m else "00:"
    result += f"{str(s).zfill(2)}" if s else "00"

    return result


def unicode_emoji(emoji: str) -> tuple[str, str]:
    characters: list[str] = []
    name: list[str] = []
    for character in emoji:
        characters.append(hex(ord(character))[2:])
        try:
            name.append(unicodedata.name(character))
        except ValueError:
            ...

    if len(characters) == 2 and "fe0f" in characters:
        characters.remove("fe0f")
    if "20e3" in characters:
        characters.remove("fe0f")

    return (
        (
            "https://cdn.jsdelivr.net/gh/jdecked/"
            "twemoji@latest/assets/svg/" + "-".join(characters) + ".svg"
        ),
        "_".join(name),
    )


@contextmanager
def capture_time(
    msg: Optional[str] = None,
    log: Optional[Callable | Logger] = None,
) -> Generator:
    start = time()

    if not msg:
        msg = getLogger().findCaller()[2]

    try:
        yield
    finally:
        duration = time() - start
        log_message = f"{msg} {fmtseconds(duration)}."
        if log:
            if callable(log):
                log(log_message)
            elif isinstance(log, Logger):
                log.info(log_message)
            else:
                # Provide a default logger if log is not valid
                getLogger().warning("Invalid log type provided; using default logger.")
                getLogger().info(log_message)
        else:
            getLogger().info(log_message)


@run_in_executor
def dominant_color(buffer: BytesIO | bytes) -> Color:
    if isinstance(buffer, bytes):
        buffer = BytesIO(buffer)

    thief = ColorThief(buffer)
    color = thief.get_color()
    return Color.from_rgb(*color)
