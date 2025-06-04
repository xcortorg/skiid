from __future__ import annotations

from typing import Any, Union, List, TYPE_CHECKING, Optional
from asyncio import Future
from asyncio import ensure_future as future
from discord import Interaction, Member, Role
import string
import random
from discord.ui import Button as OriginalButton
from discord.ui import View as OriginalView
from xxhash import xxh128_hexdigest
from collections.abc import Sequence
from discord.ext.commands import CommandError, check
import humanize
from config import Emojis
import urllib.parse
from discord.ext.commands import Converter
from datetime import timedelta
import re

DURATION_PATTERN = r"\s?".join(
    [
        r"((?P<years>\d+?)\s?(years?|y))?",
        r"((?P<months>\d+?)\s?(months?|mo))?",
        r"((?P<weeks>\d+?)\s?(weeks?|w))?",
        r"((?P<days>\d+?)\s?(days?|d))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))?",
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)


if TYPE_CHECKING:
    from base.context import Context


def hash(text: str):
    return xxh128_hexdigest(text)


def codeblock(value: str, language: str = "") -> str:
    return f"```{language}\n{value}```"


def comma(value: int):
    return humanize.intcomma(value)


def ordinal(value: int):
    return humanize.ordinal(value)


def hidden(value: str) -> str:
    return (
        "||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||"
        f" _ _ _ _ _ _ {value}"
    )


def shorten(texts: Union[str, List[str]], length: int = 2000) -> str:
    """
    Shorten a string or a shortened list that appends '...' at the end if it exceeds the length.
    Return the shortened string or a comma-seperated list of strings shortened to a max length of a specified length.
    """
    if isinstance(texts, str):
        return texts if len(texts) <= length else texts[:length] + "..."
    elif isinstance(texts, list):
        if len(texts) <= length:
            return conjoin(texts)
        else:
            return conjoin(texts) + "..."

    raise TypeError("Input must be a string or a list of strings")


def shorten_lower(value: str, length: int = 20) -> str:
    if len(value) > length:
        value = value[: length - 2] + (".." if len(value) > length else "").strip()

    return value


def conjoin(texts: List[str]) -> str:
    """
    Joins a list of strings with commas, and adds 'and' before the last item.

    Args:
        texts (List[str]): A list of strings to join.

    Returns:
        str: The formatted string with commas and 'and' before the last element.
    """
    return ", ".join(texts[:-1]) + (" and " + texts[-1] if len(texts) > 1 else texts[0])


def pluralize(text: str, count: int) -> str:
    """
    Pluralize a string based on the count.

    Args:
        text (str): The string to pluralize.
        count (int): The count to determine if the string should be pluralized.

    Returns:
        str: The pluralized string.
    """
    return text + ("s" if count != 1 else "")


class Plural:
    def __init__(
        self, value: int | list, number: bool = True, code: bool = False, md: str = ""
    ):
        """
        Pluralize a value.

        Args:
            value (int | list): The value to pluralize.
            number (bool): Whether to format the value as a number.
            code (bool): Whether to format the value as a code block.
            md (str): The markdown to wrap the value in.

        Returns:
            str: The pluralized value.
        """

        self.value: int = len(value) if isinstance(value, list) else value
        self.number: bool = number
        self.code: bool = code
        self.md: str = md

    def __format__(self, format_spec: str) -> str:
        v = self.value
        singular, _, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"

        if self.number:
            result = f"`{v}` " if self.code else f"{v} "
        else:
            result = ""

        text = plural if abs(v) != 1 else singular
        if self.md:
            text = f"{self.md}{text}{self.md}"

        result += text
        return result


def hierachy(role: Role, ctx: "Context") -> bool:
    """Check if the role is below the author's top role and the bot's top role.

    Args:
        role (Role): The role to check.
        ctx (Context): The context to check.

    Returns:
        bool: True if the role is below the author's top role and the bot's top role.
    """
    assert isinstance(ctx.author, Member), "Guild must be a guild"

    return (
        role.position < ctx.author.top_role.position
        or ctx.guild.owner_id == ctx.author.id
    ) and role.position < ctx.guild.me.top_role.position


def vowel(value: str) -> str:
    """
    Pluralize a value.
    """
    return f"{'an' if value[0].lower() in 'aeiou' else 'a'} {value}"


def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    """
    Join a sequence of strings with a delimiter, and add a final word before the last item.
    """
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return f"{delim.join(seq[:-1])} {final} {seq[-1]}"


def manageable(role: Role, ctx: "Context") -> bool:
    """Check if the role is the default guild role, or managed"""
    assert isinstance(ctx.author, Member), "Guild must be a guild"

    return not (role.managed or role == ctx.guild.default_role)


def unique_id(lenght: int = 6):
    return "".join(random.choices(string.ascii_letters + string.digits, k=lenght))


def concatenate(*texts: str, seperator: str = "\n") -> str:
    """
    Concatenate a list of strings with a provided separator.
    """
    return seperator.join(texts)


def title_format(input: str):
    """Formats a string from `blah_blah` to `Blah Blah`"""
    return input.title().replace("_", " ").replace("-", " ")


def format_overwrites(overwrites):
    formatted = ""
    for entry in overwrites:
        formatted += f"{entry[0].name} \n"

        for permission in list(entry[1]):
            formatted += f"{title_format(permission[0])} - {permission[1]}\n"

        formatted += "\n\n"

    return formatted


def format_duration(time_input: Union[int, float], is_milliseconds: bool = True) -> str:
    """
    Convert a given duration (in seconds or milliseconds) into a formatted duration string.

    Args:
        time_input (Union[int, float]): The total duration, either in seconds or milliseconds.
        is_milliseconds (bool): Specifies if the input is in milliseconds (default is True).

    Returns:
        str: The formatted duration in hours, minutes, seconds, and milliseconds.
    """
    if is_milliseconds:
        total_seconds = time_input / 1000
    else:
        total_seconds = time_input

    seconds = int(total_seconds)

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}"


class View(OriginalView):
    ctx: "Context"

    async def callback(self, interaction: Interaction, button: Button):
        raise NotImplementedError

    async def interaction_check(self, interaction: Interaction) -> bool:
        """
        Check if the interaction is from the author of the embed.
        """

        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                **self.ctx.create(
                    description=f"{Emojis.Embeds.warn} {interaction.user}: You're not the **author** of this embed!"
                ),
                ephemeral=True,
            )
        return interaction.user.id == self.ctx.author.id


class Button(OriginalButton):
    view: View  # type: ignore

    async def callback(self, interaction: Interaction) -> Any:
        return await self.view.callback(interaction, self)


class Error(CommandError):
    def __init__(self, message: str):
        self.message: str = message

    def __str__(self) -> str:
        return self.message


def percentage(small: int, big: int = 100):
    return f"{int((small / big) * 100)}%"


def format_uri(text: str):
    return urllib.parse.quote(text, safe="")


class Duration(Converter[timedelta]):
    def __init__(
        self,
        min: Optional[timedelta] = None,
        max: Optional[timedelta] = None,
        units: Optional[List[str]] = None,
    ):
        self.min = min
        self.max = max
        self.units = units or ["weeks", "days", "hours", "minutes", "seconds"]

    async def convert(self, ctx: Context, argument: str) -> timedelta:
        matches = re.fullmatch(DURATION_PATTERN, argument, re.IGNORECASE)
        if not matches:
            raise CommandError("The duration provided didn't pass validation!")

        units = {
            unit: int(amount) for unit, amount in matches.groupdict().items() if amount
        }
        for unit in units:
            if unit not in self.units:
                raise CommandError(f"The unit `{unit}` is not valid for this command!")

        try:
            duration = timedelta(**units)
        except OverflowError as exc:
            raise CommandError("The duration provided is too long!") from exc

        if self.min and duration < self.min:
            raise CommandError("The duration provided is too short!")
        if self.max and duration > self.max:
            raise CommandError("The duration provided is too long!")

        return duration


async def ensure_future(coro, silent: bool = True):
    task: Future = future(coro)

    try:
        return await task
    except Exception:
        if not silent:
            raise
