import random
import string
import urllib.parse
from collections.abc import Sequence
from typing import Union

from xxhash import xxh128_hexdigest


def hash(text: str):
    return xxh128_hexdigest(text)


def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return f"{delim.join(seq[:-1])} {final} {seq[-1]}"


def format_duration(duration: int, ms: bool = True):
    if ms:
        seconds = int((duration / 1000) % 60)
        minutes = int((duration / (1000 * 60)) % 60)
        hours = int((duration / (1000 * 60 * 60)) % 24)
    else:
        seconds = int(duration % 60)
        minutes = int((duration / 60) % 60)
        hours = int((duration / (60 * 60)) % 24)

    if any((hours, minutes, seconds)):
        result = ""
        if hours:
            result += f"{hours:02d}:"
        result += f"{minutes:02d}:"
        result += f"{seconds:02d}"
        return result
    return "00:00"


def unique_id(lenght: int = 6):
    return "".join(random.choices(string.ascii_letters + string.digits, k=lenght))


def format_uri(text: str):
    return urllib.parse.quote(text, safe="")


class Plural:
    def __init__(self, value: int | list, number: bool = True, code: bool = False):
        self.value: int = len(value) if isinstance(value, list) else value
        self.number: bool = number
        self.code: bool = code

    def __format__(self, format_spec: str) -> str:
        v = self.value
        singular, _, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        if self.number:
            result = f"`{v}` " if self.code else f"{v} "
        else:
            result = ""

        result += plural if abs(v) != 1 else singular
        return result


def shorten(value: str, length: int = 20) -> str:
    if len(value) > length:
        value = value[: length - 2] + (".." if len(value) > length else "").strip()

    return value


def replace_artist(text: str, source: str, output: str):
    return (
        text.replace(f'"artist": "{source}"', f'"artist": "{output}"')
        .replace(f'"name": "{source}"', f'"name": "{output}"')
        .replace(f'"#text": "{source}"', f'"#text": "{output}"')
    )


def hidden(value: str) -> str:
    return (
        "||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||||​||"
        f" _ _ _ _ _ _ {value}"
    )


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
