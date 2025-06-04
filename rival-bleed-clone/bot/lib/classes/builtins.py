from typing import Optional, Union, Any, Dict, List, Type, Callable, Sequence
from random import uniform
import orjson
import asyncio
import contextlib
from discord import Embed, Colour, Client
from contextlib import contextmanager
import traceback
from logging import getLogger
from loguru import logger
from lib.patch.context import Context
from humanize import intword

logger_ = getLogger(__name__)

from typing import Sequence, Optional

def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or", markdown: Optional[str] = "") -> str:
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return f"{markdown}{seq[0]}{markdown}"

    if size == 2:
        return f"{markdown}{seq[0]}{markdown} {final} {markdown}{seq[1]}{markdown}"

    return delim.join(f"{markdown}{item}{markdown}" for item in seq[:-1]) + f" {final} {markdown}{seq[-1]}{markdown}"

def humanize(self: int) -> str:
	m = intword(self)
	m = (
		m.replace(" million", "m")
		.replace(" billion", "b")
		.replace(" trillion", "t")
		.replace(" thousand", "k")
		.replace(" hundred", "")
	)
	m = m.replace(".0k", "k").replace(".0m", "m").replace(".0b", "b").replace(".0t", "t")
	return m

def humanize__(self: float) -> str:
	m = intword(int(self))
	m = (
		m.replace(" million", "m")
		.replace(" billion", "b")
		.replace(" trillion", "t")
		.replace(" thousand", "k")
		.replace(" hundred", "")
	)
	m = m.replace(".0k", "k").replace(".0m", "m").replace(".0b", "b").replace(".0t", "t")
	return m

def humanize_(self: str) -> str:
	m = intword(int(self))
	m = (
		m.replace(" million", "m")
		.replace(" billion", "b")
		.replace(" trillion", "t")
		.replace(" thousand", "k")
		.replace(" hundred", "")
	)
	return m

async def suppress_error(fn: Callable, error: Type[Exception], *args, **kwargs):
    """
    Suppresses the specified error while invoking the given function or coroutine.
    
    Parameters:
        fn (Callable): The function or coroutine to invoke.
        error (Type[Exception]): The error to suppress.
        *args: Positional arguments for the function or coroutine.
        **kwargs: Keyword arguments for the function or coroutine.
    """
    with contextlib.suppress(error):
        # Check if the callable is a coroutine
        if asyncio.iscoroutinefunction(fn):
            await fn(*args, **kwargs)  # Await if it's a coroutine
        else:
            fn(*args, **kwargs)  # Call directly if it's a regular function


@contextmanager
def catch(exception_type: Optional[Exception] = Exception, raise_error: Optional[bool] = False, log_error: Optional[bool] = True):
    try:
        yield
    except exception_type as error:
        exc = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        if log_error:
            logger.info(f"error raised: {exc}")
        if raise_error:
            raise error
    


def get_error(exception: Exception) -> str:
    exc = "".join(
        traceback.format_exception(type(exception), exception, exception.__traceback__)
    )
    return exc


ordinal_ = lambda n: "%d%s" % (
    n,
    "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10 :: 4],
)

def ordinal(self: int) -> str:
    return ordinal_(self)



def boolean_to_emoji(bot: Client, boolean: bool):
    if boolean:
        return bot.config["emojis"]["success"]
    return bot.config["emojis"]["fail"]




class embed(Embed):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def colour(self) -> Optional[Colour]:
        return getattr(self, '_colour', 0x747f8d)

    @colour.setter
    def colour(self, value: Optional[Union[int, Colour]]) -> None:
        if value is None:
            self._colour = None
        elif isinstance(value, Colour):
            self._colour = value
        elif isinstance(value, int):
            self._colour = Colour(value=value)
        else:
            raise TypeError(f'Expected discord.Colour, int, or None but received {value.__class__.__name__} instead.')
        
    def style(self, ctx: Context):
        self.set_author(name = str(ctx.author), icon_url = ctx.author.display_avatar.url)

    color = colour
Embed.colour = embed.colour

def chunk_list(data: list, amount: int) -> list:
    # makes lists of a big list of values every x amount of values
    chunks = zip(*[iter(data)] * amount)
    _chunks = [list(_) for _ in list(chunks)]
    return _chunks


def codeblock(value: str, language: str = "") -> str:
    return f"```{language}\n{value}```"

class plural:
    def __init__(self, value: int, bold: bool = False, code: bool = False):
        self.value: int = value
        self.bold: bool = bold
        self.code: bool = code

    def __format__(self, format_spec: str) -> str:
        v = self.value
        if isinstance(v, list):
            v = len(v)
        if self.bold:
            value = f"**{v:,}**"
        elif self.code:
            value = f"`{v:,}`"
        else:
            value = f"{v:,}"

        singular, sep, plural = format_spec.partition("|")  # type: ignore
        plural = plural or f"{singular}s"

        if abs(v) != 1:
            return f"{value} {plural}"

        return f"{value} {singular}"

    def do_plural(self, format_spec: str) -> str:
        v = self.value
        if isinstance(v, list):
            v = len(v)
        if self.bold:
            value = f"**{v:,}**"
        elif self.code:
            value = f"`{v:,}`"
        else:
            value = f"{v:,}"

        singular, sep, plural = format_spec.partition("|")  # type: ignore
        plural = plural or f"{singular}s"

        if abs(v) != 1:
            return f"{value} {plural}"

        return f"{value} {singular}"

def shorten(value: str, length: int = 20, end: Optional[str] = ".."):
    if len(value) > length:
        value = value[: length - 2] + (end if len(value) > length else "").strip()
    return value


Numeric = Union[float, int, str]


def maximum(self: Numeric, maximum: Numeric) -> Optional[Numeric]:
    return min(float(self), float(maximum))


def maximum_(self: Numeric, maximum: Numeric) -> Optional[Numeric]:
    return int(min(float(self), float(maximum)))


def minimum(self: Numeric, minimum: Numeric) -> Optional[Numeric]:
    return max(float(minimum), float(self))


def minimum_(self: Numeric, minimum: Numeric) -> Optional[Numeric]:
    return int(max(float(minimum), float(self)))


@property
def positive(self: Numeric) -> Optional[Numeric]:
    return max(float(0.00), float(self))


@property
def positive_(self: Numeric) -> Optional[Numeric]:
    return int(max(float(0.00), float(self)))


def calculate_(chance: Numeric, total: Optional[Numeric] = 100.0) -> bool:
    roll = uniform(0.0, float(total))
    return roll < float(chance)


def hyperlink(text: str, url: str, character: Optional[str] = None) -> str:
    if character:
        return f"[{character}{text}{character}]({url})"
    else:
        return f"[{text}]({url})"



class ObjectTransformer(dict):
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError:
            raise AttributeError(f"'{self.__name__}' object has no attribute '{key}'")

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value

    def __delattr__(self, key: str) -> None:
        try:
            del self[key]
        except KeyError:
            raise AttributeError(f"'{self.__name__}' object has no attribute '{key}'")

    @classmethod
    def _convert(cls, value: Any, visited: set = None) -> Any:
        if visited is None:
            visited = set()

        if id(value) in visited:
            return value

        visited.add(id(value))

        if isinstance(value, dict):
            return cls({k: cls._convert(v, visited) for k, v in value.items()})
        elif isinstance(value, list):
            return [cls._convert(v, visited) for v in value]
        else:
            return value

    @classmethod
    async def from_data(cls, data: Union[Dict[str, Any], bytes]) -> "ObjectTransformer":
        parsed_data = orjson.loads(data) if isinstance(data, bytes) else data
        return cls(cls._convert(parsed_data))


def asDict(obj, max_depth=5) -> dict:
    """
    Recursively extract all properties from a class and its nested property classes into a dictionary.

    :param obj: The class instance from which to extract properties.
    :param max_depth: The maximum depth to recurse.
    :return: A dictionary containing the properties and their values.
    """

    def is_property(obj):
        return isinstance(obj, property)

    def get_properties(obj, depth, seen):
        if depth > max_depth or id(obj) in seen:
            return {}  # Avoid infinite recursion and limit depth
        seen.add(id(obj))

        properties = {}
        for name, value in obj.__class__.__dict__.items():
            if is_property(value):
                try:
                    prop_value = getattr(obj, name)
                    if hasattr(prop_value, "__class__") and not isinstance(
                        prop_value, (int, float, str, bool, type(None))
                    ):
                        try:
                            properties[name] = get_properties(
                                prop_value, depth + 1, seen
                            )
                        except AttributeError:
                            continue
                    else:
                        properties[name] = prop_value
                except RecursionError:
                    properties[name] = "RecursionError"
        return properties

    return get_properties(obj, 0, set())