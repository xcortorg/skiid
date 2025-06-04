import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union, cast

from discord import (
    Asset,
    Color,
    Guild,
    Member,
    Role,
    Status,
    TextChannel,
    Thread,
    User,
    VoiceChannel,
)
from humanfriendly import format_timespan, format_number
from pydantic import BaseModel

TARGET = Union[
    Member, User, Role, Guild, VoiceChannel, TextChannel, Thread, BaseModel, str
]
VARIABLE = re.compile(r"(?<!\\)\{([a-zA-Z0-9_.]+)\}")


def ordinal(n: int) -> str:
    """
    Convert an integer into its ordinal representation.
    """
    suffixes = {1: "st", 2: "nd", 3: "rd"}
    v = n % 100
    suffix = suffixes.get(v % 10, "th") if v // 10 != 1 else "th"
    return f"{n:,}{suffix}"


def to_dict(
    target: TARGET,
    _key: Optional[str] = None,
) -> Dict[str, str]:
    """
    Compile a dictionary of safe attributes.
    """

    origin = target.__class__.__name__.lower()
    key = _key or getattr(target, "_variable", origin)
    key = "user" if key == "member" else "channel" if "channel" in key else key

    data: Dict[str, str] = {
        key: str(target),
    }

    if isinstance(target, Guild):
        data[f"{key}.count"] = format_number(target.member_count)
        data[f"{key}.boost_count"] = format_number(target.premium_subscription_count)
        data[f"{key}.vanity"] = f"/{target.vanity_url_code}" if target.vanity_url_code else "N/A"
        data[f"{key}.boost_tier"] = f"Level {target.premium_tier}"
        data[f"{key}.count.format"] = ordinal(target.member_count)
        data[f"{key}.boost_count.format"] = ordinal(target.premium_subscription_count)
        return data

    for name in dir(target):
        if name.startswith("_"):
            continue

        try:
            value = getattr(target, name)
        except (ValueError, AttributeError):
            continue

        if callable(value):
            continue

        if isinstance(value, datetime):
            data[f"{key}.{name}"] = str(int(value.timestamp()))

        elif isinstance(value, timedelta):
            data[f"{key}.{name}"] = format_timespan(value)

        elif isinstance(value, int):
            data[f"{key}.{name}"] = (
                format(value, ",")
                if not name.endswith(("id", "duration"))
                else str(value)
            )

        elif isinstance(value, (str, bool, Status, Asset, Color)):
            data[f"{key}.{name}"] = str(value)

        elif isinstance(value, BaseModel):
            base_model_data = to_dict(value)
            for __key, val in base_model_data.items():
                data[f"{key}.{__key}"] = val

    return data


def parse(string: str, targets: List[TARGET | Tuple[TARGET, str]]) -> str:
    """
    Parse a string with a given environment.
    """

    variables: Dict[str, str] = {}
    for target in targets:
        if isinstance(target, tuple):
            variables.update(to_dict(*target))
            continue

        variables.update(to_dict(target))

    def replace(match: re.Match) -> str:
        name = cast(str, match[1])
        value = variables.get(name)

        return value or name

    return VARIABLE.sub(replace, string)