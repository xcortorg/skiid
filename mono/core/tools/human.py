from datetime import datetime, timedelta, timezone
from typing import Optional, Sequence, Union

from dateutil.relativedelta import relativedelta
from humanize import intcomma, ordinal, precisedelta


def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return f"{delim.join(seq[:-1])} {final} {seq[-1]}"


def human_timedelta(
    dt: Union[datetime, timedelta],
    *,
    source: Optional[datetime] = None,
    accuracy: Optional[int] = 3,
    brief: bool = False,
    suffix: bool = True,
) -> str:
    if isinstance(dt, timedelta):
        dt = datetime.utcnow() - dt

    now = source or datetime.utcnow()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    now = now.replace(microsecond=0)
    dt = dt.replace(microsecond=0)

    if dt > now:
        delta = relativedelta(dt, now)
        output_suffix = ""
    else:
        delta = relativedelta(now, dt)
        output_suffix = " ago" if suffix else ""

    attrs = [
        ("year", "y"),
        ("month", "mo"),
        ("day", "d"),
        ("hour", "h"),
        ("minute", "m"),
        ("second", "s"),
    ]

    output = []
    for attr, brief_attr in attrs:
        elem = getattr(delta, attr + "s")
        if not elem:
            continue

        if attr == "day":
            weeks = delta.weeks
            if weeks:
                elem -= weeks * 7
                if not brief:
                    output.append(f"{weeks} week{'s' if weeks > 1 else ''}")
                else:
                    output.append(f"{weeks}w")

        if elem <= 0:
            continue

        if brief:
            output.append(f"{elem}{brief_attr}")
        else:
            output.append(f"{elem} {attr}{'s' if elem > 1 else ''}")

    if accuracy is not None:
        output = output[:accuracy]

    if len(output) == 0:
        return "now"
    else:
        if not brief:
            return human_join(output, final="and") + output_suffix
        else:
            return "".join(output) + output_suffix


def short_timespan(
    num_seconds: Union[float, timedelta], max_units: int = 3, delim: str = ""
) -> str:
    if isinstance(num_seconds, timedelta):
        num_seconds = num_seconds.total_seconds()

    units = [
        ("y", 60 * 60 * 24 * 365),
        ("w", 60 * 60 * 24 * 7),
        ("d", 60 * 60 * 24),
        ("h", 60 * 60),
        ("m", 60),
        ("s", 1),
    ]

    parts = []
    for unit, div in units:
        if num_seconds >= div:
            val = int(num_seconds // div)
            num_seconds %= div
            parts.append(f"{val}{unit}")
            if len(parts) == max_units:
                break

    return delim.join(parts)


def fmtseconds(seconds: timedelta | float | int, unit: str = "microseconds") -> str:
    if not isinstance(seconds, timedelta):
        seconds = timedelta(seconds=seconds)

    return precisedelta(seconds, minimum_unit=unit)


def comma(value: int):
    return intcomma(value)


def ordinal(value: int):
    return ordinal(value)
