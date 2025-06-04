from __future__ import annotations
import asyncio
import contextlib
import os  # noqa: E402
import unicodedata  # noqa: E402
from datetime import datetime  # noqa: E402
from typing import Any, Dict, Optional, Tuple, Union, Coroutine  # noqa: E402
import discord  # noqa: E402
from discord.ext import commands
from discord.ext.commands import CommandError
from discord.utils import cached_property
from var.config import CONFIG
from contextlib import suppress
from discord.ui import View
from loguru import logger
from asyncio.subprocess import PIPE
import aiohttp
from lib.worker import offloaded

TUPLE = ()
SET = set()

# if not CONFIG["emojis"].get("success"):
#     CONFIG["emojis"]["success"] = CONFIG["emojis"]["approve"]


def is_unicode(emoji: str) -> bool:
    with contextlib.suppress(Exception):
        unicodedata.name(emoji)
        return True

    return False


@offloaded
async def write_file(filename: str, data: bytes):
    with open(filename, "wb") as file:
        file.write(data)
    return filename


class Cache:
    def __init__(self, bot=None) -> None:
        self.bot = bot
        self._dict = {}
        self._rl = {}
        self._delete = {}
        self._futures = {}

    async def do_expiration(self, key: str, expiration: int) -> None:
        """
        Removes an item from the dictionary after a specified expiration time.

        Parameters:
            key (str): The key of the item to be removed.
            expiration (int): The time in seconds after which the item should be removed.
        """

        await asyncio.sleep(expiration)

        if key in self._dict:
            del self._dict[key]

    async def set(self, key: Any, value: Any, expiration: Optional[int] = None) -> int:
        """
        Set the value of the given key in the dictionary.

        Parameters:
            key (Any): The key to set the value for.
            value (Any): The value to set.
            expiration (Optional[int], optional): The expiration time in seconds. Defaults to None.

        Returns:
            int: The number of items in the dictionary after setting the value.
        """

        self._dict[key] = value

        if expiration is not None:
            if key in self._futures:
                self._futures[key].cancel()

            self._futures[key] = asyncio.ensure_future(
                self.do_expiration(key, expiration)
            )

        return 1

    async def sadd(self, key: Any, *values: Any) -> int:
        """
        Add one or more values to a set stored under a given key.

        Parameters:
            key (Any): The key under which the set is stored.
            *values (Any): The values to add to the set.

        Returns:
            int: The number of values that were successfully added to the set.

        Raises:
            AssertionError: If the provided key is already in the cache as another type.
        """

        if key not in self._dict:
            self._dict[key] = set()

        assert isinstance(
            self._dict[key], set
        ), "The provided key is already in the cache as another type."

        to_add = set()

        for value in values:
            if value not in self._dict[key]:
                to_add.add(value)

        for value in to_add:
            self._dict[key].add(value)

        return len(to_add)

    async def smembers(self, key: Any) -> Tuple[Any]:
        """
        Return a set of values associated with the given key.

        Parameters:
            key (Any): The key to retrieve the values for.

        Returns:
            set: A set of values associated with the key.

        Raises:
            AssertionError: If the key belongs to a different type.
        """

        assert isinstance(
            self._dict.get(key, SET), set
        ), "That key belongs to another type."

        return tuple(self._dict.get(key, SET))

    async def scard(self, key: Any) -> int:
        """
        Retrieve the cardinality of a set in the cache.

        Parameters:
            key (Any): The key associated with the set.

        Returns:
            int: The number of elements in the set.

        Raises:
            AssertionError: If the set does not exist in the cache or if it belongs to another type.
        """

        assert isinstance(
            self._dict.get(key), set
        ), "There is no such set in this cache, or that belongs to another type."

        return len(self._dict[key])

    async def srem(self, key: Any, *members: Any) -> int:
        """
        Remove the specified members from the set stored at key.
        If a member does not exist in the set, it is ignored.

        Parameters:
            key (Any): The key of the set in the cache.
            *members (Any): The members to remove from the set.

        Returns:
            int: The number of members that were successfully removed from the set.

        Raises:
            AssertionError: If the value associated with key is not a set.
        """

        assert isinstance(
            self._dict.get(key), set
        ), "There is no such set in this cache, or that belongs to another type."

        try:
            return len(
                tuple(
                    self._dict[key].remove(member)
                    for member in members
                    if member in self._dict[key]
                )
            )

        finally:
            if not self._dict[key]:
                del self._dict[key]

    async def delete(self, *keys: Any, pattern: Optional[str] = None) -> int:
        """
        Delete one or more keys from the dictionary.

        Parameters:
            *keys (Any): The keys to be deleted.
            pattern (Optional[str], optional): A pattern to filter the keys by. Defaults to None.

        Returns:
            int: The number of keys deleted.
        """

        if not keys and pattern is not None:
            keys = tuple(filter(lambda k: pattern.rstrip("*") in k, self._dict.keys()))

        return len(tuple(self._dict.pop(key) for key in keys if key in self._dict))

    async def get(self, key: Any) -> Any:
        """
        Get the value associated with the given key from the dictionary.

        Parameters:
            key (Any): The key to search for in the dictionary.

        Returns:
            Any: The value associated with the given key. Returns None if the key is not found.
        """

        return self._dict.get(key, None)

    async def keys(self, pattern: Optional[str] = None) -> Tuple[Any]:
        """
        Retrieves all keys from the dictionary that match the given pattern.

        Parameters:
            pattern (Optional[str]): A string pattern to match keys against. Defaults to None.

        Returns:
            Tuple[Any]: A tuple containing all the keys that match the pattern.
        """

        if pattern:
            return tuple(filter(lambda k: pattern.rstrip("*") in k, self._dict.keys()))

        return tuple(self._dict.keys())

    def is_ratelimited(self, key: Any) -> bool:
        """
        Check if the given key is rate limited.

        Parameters:
            key (Any): The key to check for rate limiting.

        Returns:
            bool: True if the key is rate limited, False otherwise.
        """

        if key in self._dict:
            if self._dict[key] >= self._rl[key]:
                return True

        return False

    def time_remaining(self, key: Any) -> int:
        """
        Calculates the time remaining for the given key in the cache.

        Parameters:
            key (Any): The key to check the remaining time for.

        Returns:
            int: The time remaining in seconds. Returns 0 if the key does not exist in the cache.
        """

        if key in self._dict and key in self._delete:
            if not self._dict[key] >= self._rl[key]:
                return 0

            return (
                self._delete[key]["last"] + self._delete[key]["bucket"]
            ) - datetime.now().timestamp()

        return 0

    async def ratelimited(self, key: str, amount: int, bucket: int) -> int:
        """
        Check if a key is rate limited and return the remaining time until the next request is allowed.

        Parameters:
            key (str): The key to check for rate limiting.
            amount (int): The maximum number of requests allowed within the rate limit window.
            bucket (int): The duration of the rate limit window in seconds.

        Returns:
            int: The remaining time in seconds until the next request is allowed. Returns 0 if the key is not rate limited.
        """

        current_time = datetime.now().timestamp()
        self._rl[key] = amount
        if key not in self._dict:
            self._dict[key] = 1

            if key not in self._delete:
                self._delete[key] = {"bucket": bucket, "last": current_time}

            return 0

        try:
            if self._delete[key]["last"] + bucket <= current_time:
                self._dict[key] = 0
                self._delete[key]["last"] = current_time

            self._dict[key] += 1

            if self._dict[key] > self._rl[key]:
                return round((bucket - (current_time - self._delete[key]["last"])), 3)

            return 0

        except Exception:
            return self.ratelimited(key, amount, bucket)


class ParameterParser:
    def __init__(self: "ParameterParser", ctx: "Context") -> None:
        self.context = ctx

    def get(self: "ParameterParser", param: str, **kwargs: Dict[str, Any]) -> Any:
        self.context.message.content = self.context.message.content.replace(" —", " --")

        for parameter in (param, *kwargs.get("aliases", TUPLE)):
            sliced = self.context.message.content.split()

            if kwargs.get("require_value", True) is False:
                if f"-{parameter}" not in sliced:
                    return kwargs.get("default", None)

                return True

            try:
                index = sliced.index(f"--{parameter}")
                if kwargs.get("no_value", False) is True:
                    return True
            except ValueError:
                logger.info(f"{param} raised value error")
                continue

            result = []
            for word in sliced[index + 1 :]:
                if word.startswith("-"):
                    break

                result.append(word)

            if not (result := " ".join(result).replace("\\n", "\n").strip()):
                return kwargs.get("default", None)

            if choices := kwargs.get("choices"):
                choice = tuple(
                    choice for choice in choices if choice.lower() == result.lower()
                )

                if not choice:
                    raise CommandError(f"Invalid choice for parameter `{parameter}`.")

                result = choice[0]

            if converter := kwargs.get("converter"):
                if hasattr(converter, "convert"):
                    try:
                        result = self.context.bot.loop.create_task(
                            converter().convert(self.context, result)
                        )
                    except Exception as e:
                        logger.info(f"{parameter} failed to convert due to {e}")

                else:
                    try:
                        result = converter(result)

                    except Exception:
                        raise CommandError(f"Invalid value for parameter `{param}`.")

            if isinstance(result, int):
                if result < kwargs.get("minimum", 1):
                    raise CommandError(
                        f"The **minimum input** for parameter `{param}` is `{kwargs.get('minimum', 1)}`"
                    )

                if result > kwargs.get("maximum", 100):
                    raise CommandError(
                        f"The **maximum input** for parameter `{param}` is `{kwargs.get('maximum', 100)}`"
                    )

            return result

        return kwargs.get("default", None)


async def get_lines():
    lines = 0
    for directory in [x[0] for x in os.walk("./") if ".git" not in x[0]]:
        for file in os.listdir(directory):
            if file.endswith(".py"):
                lines += len(open(f"{directory}/{file}", "r").read().splitlines())

    return lines


def is_donator(exempted_ids=[1188282998534193152]):
    async def predicate(ctx: commands.Context):
        guild = ctx.bot.get_guild(1199041659799879762)
        if ctx.author.id in exempted_ids:
            return True
        if ctx.author in guild.premium_subscribers:
            return True
        raise discord.ext.commands.errors.CommandError(
            "You must be a **donator** to use that command"
        )
        # return False

    return commands.check(predicate)


async def normal(self: discord.TextChannel, text: str, **kwargs: Any):
    color = kwargs.pop("color", 0x6E879C)
    emoji = kwargs.pop("emoji", "")
    embed = discord.Embed(color=color, description=f"{emoji} {text}")
    if footer := kwargs.pop("footer", None):
        if isinstance(footer, tuple):
            embed.set_footer(text=footer[0], icon_url=footer[1])
        else:
            embed.set_footer(text=footer)
    if author := kwargs.pop("author", None):
        if isinstance(author, tuple):
            embed.set_author(name=author[0], icon_url=author[1])
        else:
            embed.set_author(name=author)
    if delete_after := kwargs.get("delete_after"):
        delete_after = delete_after
    else:
        delete_after = None
    if kwargs.pop("return_embed", False) is True:
        return embed
    return await self.send(embed=embed, **kwargs)


discord.TextChannel.normal = normal


class Context(commands.Context):
    flags: Dict[str, Any] = {}
    __lastfm: Optional[Any] = None

    def __init__(self, *args, **kwargs):
        self.__lastfm = kwargs.pop("lastfm", None)
        super().__init__(*args, **kwargs)

    @property
    def lastfm(self):
        if hasattr(self, "__lastfm"):
            return self.__lastfm

    @lastfm.setter
    def lastfm(self, value):
        self.__lastfm = value

    @property
    def __parameter_parser(self):
        return ParameterParser(self)

    @cached_property
    def parameters(self) -> Dict[str, Any]:
        return {
            name: self.__parameter_parser.get(name, **config)
            for name, config in self.command.parameters.items()
        }

    async def fill_lastfm(self, coroutine: Coroutine):
        self.lastfm = await coroutine

    async def send_help(
        self, option: Optional[Union[commands.Command, commands.Group]] = None
    ):
        if option is None:
            if command := self.command:
                if command.name != "help":
                    option = command
        from .help import Help

        h = Help()
        h.context = self
        if not option:
            return await h.send_bot_help(None)
        elif isinstance(option, commands.Group):
            return await h.send_group_help(option)
        else:
            return await h.send_command_help(option)

    async def success(self, text, **kwargs):
        emoji = self.bot.config["emojis"]["success"]
        color = self.bot.config["colors"]["success"]
        embed = discord.Embed(
            color=color, description=f"{emoji} {self.author.mention}: {text}"
        )
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            elif isinstance(footer, dict):
                embed.set_footer(**footer)
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            elif isinstance(author, dict):
                embed.set_author(**author)
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(
            embed=embed,
            delete_after=delete_after,
            view=kwargs.pop("view", None),
            **kwargs,
        )

    async def add(self, text: str, **kwargs: Any):
        emoji = self.bot.config["emojis"]["add"]
        color = self.bot.config["colors"]["success"]
        embed = discord.Embed(
            color=color, description=f"{emoji} {self.author.mention}: {text}"
        )
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            elif isinstance(footer, dict):
                embed.set_footer(**footer)
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            elif isinstance(author, dict):
                embed.set_author(**author)
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(
            embed=embed,
            delete_after=delete_after,
            view=kwargs.pop("view", None),
            **kwargs,
        )

    async def remove(self, text: str, **kwargs: Any):
        emoji = self.bot.config["emojis"]["remove"]
        color = self.bot.config["colors"]["success"]
        embed = discord.Embed(
            color=color, description=f"{emoji} {self.author.mention}: {text}"
        )
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            elif isinstance(footer, dict):
                embed.set_footer(**footer)
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            elif isinstance(author, dict):
                embed.set_author(**author)
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(
            embed=embed,
            delete_after=delete_after,
            view=kwargs.pop("view", None),
            **kwargs,
        )

    async def repost(self, embed: discord.Embed, file: discord.File, post: Any):
        from discord.http import handle_message_parameters  # type: ignore

        logger.info("compressing tiktok....")
        with suppress(FileNotFoundError):
            os.remove(f"{self.bot.user.name.lower()}tiktok.mp4")
            os.remove(f"{self.bot.user.name.lower()}tiktoka.mp4")
        raw = file.fp.read()
        filename = f"{self.bot.user.name.lower()}tiktok.mp4"
        filename = filename.split(".")[0]
        await write_file(f"{filename}a.mp4", raw)
        process = await asyncio.create_subprocess_shell(
            f"ffmpeg -i {filename}a.mp4 -fs 6M -preset ultrafast {filename}.mp4 -y",
            stderr=PIPE,
            stdout=PIPE,
        )
        await process.communicate()
        try:
            await process.wait()
        except Exception:
            pass
        file = discord.File(f"{filename}.mp4")
        if len(file.fp.read()) > self.guild.filesize_limit:
            await self.fail("**tiktok video** is **to large**", return_embed=True)
        else:
            kwargs = {"headers": {"Authorization": f"Bot {self.bot.config['token']}"}}
            for i in range(5):  # type: ignore
                try:
                    file = discord.File(f"{filename}.mp4")
                    with handle_message_parameters(file=file, embed=embed) as params:
                        for tries in range(5):
                            if params.files:
                                for f in params.files:
                                    f.reset(seek=tries)
                                form_data = aiohttp.FormData(quote_fields=False)
                                if params.multipart:
                                    for params in params.multipart:
                                        form_data.add_field(**params)
                                kwargs["data"] = form_data
                            async with aiohttp.ClientSession() as session:
                                async with session.request(
                                    "POST",
                                    f"https://discord.com/api/v10/channels/{self.channel.id}/messages",
                                    **kwargs,
                                ) as response:
                                    await response.json()  # pointless but do it here anyways to end off the async enter
                except AttributeError:
                    break
        await self.message.delete()
        return

    async def spotify(self, text: str, **kwargs):
        color = 0x1DD65E
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        emoji = self.bot.config["emojis"]["spotify"]
        embed = discord.Embed(
            color=color, description=f"{emoji} {self.author.mention}: {text}"
        )
        return await self.send(
            embed=embed,
            delete_after=delete_after,
            view=kwargs.pop("view", None),
            **kwargs,
        )

    async def search(self, text: str, **kwargs):
        return await self.normal(text=text, emoji="🔎", **kwargs)

    async def normal(self, text, **kwargs):
        color = 0x6E879C
        emoji = kwargs.pop("emoji", None)
        emoji = f"{emoji} " if emoji else ""
        embed = discord.Embed(
            color=color, description=f"{emoji}{self.author.mention}: {text}"
        )
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            elif isinstance(footer, dict):
                embed.set_footer(**footer)
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            elif isinstance(author, dict):
                embed.set_author(**author)
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(
            embed=embed,
            delete_after=delete_after,
            view=kwargs.pop("view", None),
            **kwargs,
        )

    async def confirm(self, message: str, **kwargs: Any):
        view = ConfirmView(self)
        message = await self.fail(message, view=view, **kwargs)

        await view.wait()
        with contextlib.suppress(discord.HTTPException):
            await message.delete()

        if view.value is False:
            raise commands.UserInputError("Prompt was denied.")
        return view.value

    @property
    def static_emoji_count(self) -> int:
        return sum([1 for e in self.guild.emojis if not e.animated])

    @property
    def animated_emoji_count(self) -> int:
        return sum([1 for e in self.guild.emojis if e.animated])

    async def fail(self, text, **kwargs):
        emoji = self.bot.config["emojis"]["fail"]
        color = self.bot.config["colors"]["fail"]
        embed = discord.Embed(
            color=color, description=f"{emoji} {self.author.mention}: {text}"
        )
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            elif isinstance(footer, dict):
                embed.set_footer(**footer)
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            elif isinstance(author, dict):
                embed.set_author(**author)
            else:
                embed.set_author(name=author)
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, view=kwargs.pop("view", None), **kwargs)

    async def warning(self, text, **kwargs):
        emoji = self.bot.config["emojis"]["warning"]
        color = self.bot.config["colors"]["warning"]
        embed = discord.Embed(
            color=color,
            description=f"{emoji or ''} {self.author.mention}: {text}",
        )
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            elif isinstance(footer, dict):
                embed.set_footer(**footer)
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            elif isinstance(author, dict):
                embed.set_author(**author)
            else:
                embed.set_author(name=author)
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, view=kwargs.pop("view", None), **kwargs)

    async def send(self, *args, **kwargs):
        if embed := kwargs.get("embed"):
            if not embed.color:
                embed.color = self.bot.color
            kwargs["embed"] = embed
        return await super().send(*args, **kwargs)

    async def pin(self, text, **kwargs):
        color = 0x6E879C
        embed = discord.Embed(
            color=color,
            description=f"<:pin:1287279568406974496> {self.author.mention}: {text}",
        )
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            elif isinstance(footer, dict):
                embed.set_footer(**footer)
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            elif isinstance(author, dict):
                embed.set_author(**author)
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after, **kwargs)

    async def display_prefix(self) -> str:
        user = await self.bot.db.fetchval(
            """SELECT prefix
            FROM self_prefix
            WHERE user_id = $1""",
            self.author.id,
        )
        server = await self.db.fetchval(
            """SELECT prefix
            FROM config
            WHERE guild_id = $1""",
            self.guild.id,
        )
        if not server:
            server = ","
        if user:
            if self.content.strip().startswith(user):
                return user
        return server

    async def alternative_paginate(
        self,
        embeds: list,
        message: Optional[discord.Message] = None,
        invoker_lock: Optional[bool] = True,
    ):
        from ..classes.paginator import Paginator

        for i in embeds:
            if not isinstance(i, discord.Embed):
                break
            if not i.color:
                i.color = self.bot.color
        if invoker_lock is True:
            paginator = Paginator(self.bot, embeds, self, invoker=self.author.id)
        else:
            paginator = Paginator(self.bot, embeds, self)
        if len(embeds) > 1:
            paginator.add_button(
                "prev",
                emoji=CONFIG["emojis"]["paginator"]["previous"],
                style=discord.ButtonStyle.blurple,
            )
            paginator.add_button(
                "next",
                emoji=CONFIG["emojis"]["paginator"]["next"],
                style=discord.ButtonStyle.blurple,
            )
            paginator.add_button(
                "goto",
                emoji=CONFIG["emojis"]["paginator"]["navigate"],
                style=discord.ButtonStyle.grey,
            )
            paginator.add_button(
                "delete",
                emoji=CONFIG["emojis"]["paginator"]["cancel"],
                style=discord.ButtonStyle.red,
            )
        elif len(embeds) == 1:
            paginator.add_button(
                "delete",
                emoji=CONFIG["emojis"]["paginator"]["cancel"],
                style=discord.ButtonStyle.red,
            )
        else:
            raise discord.ext.commands.errors.CommandError(
                "No Embeds Supplied to Paginator"
            )
        if message:
            await message.edit(view=paginator, embed=embeds[0])
            paginator.page = 0
            return
        return await paginator.start()

    async def paginate(
        self,
        embed: Union[discord.Embed, list],
        rows: Optional[list] = None,
        per_page: int = 10,
        type: str = "entry",
        plural_type: str = "entries",
    ):
        from lib.classes.builtins import chunk_list, plural  # type: ignore

        embeds = []
        if isinstance(embed, list):
            return await self.alternative_paginate(embed)
        if rows:
            if isinstance(rows[0], discord.Embed):
                embeds.extend(rows)
                return await self.alternative_paginate(embeds)
            else:
                if len(rows) > per_page:
                    chunks = chunk_list(rows, per_page)
                    for i, chunk in enumerate(chunks, start=1):
                        rows = [f"{c}\n" for c in chunk]
                        embed = embed.copy()
                        embed.description = "".join(r for r in rows)
                        embed.set_footer(
                            text=f"Page {i}/{len(chunks)} ({plural(rows).do_plural(f'{type.title()}|{plural_type}') if not type.endswith('d') else type})"
                        )
                        embeds.append(embed)
                    try:
                        del chunks
                    except Exception:
                        pass
                    return await self.alternative_paginate(embeds)
                else:
                    embed.description = "".join(f"{r}\n" for r in rows)
                    # t = plural(len(rows)):type.title()
                    embed.set_footer(
                        text=f"Page 1/1 ({plural(rows).do_plural(f'{type.title()}|{plural_type}') if not type.endswith('d') else type})"
                    )
                    return await self.send(embed=embed)


class ConfirmView(View):
    def __init__(self, ctx: Context):
        super().__init__()
        self.value = False
        self.ctx: Context = ctx
        self.bot: discord.Client = ctx.bot

    @discord.ui.button(
        emoji=CONFIG["emojis"].get("success", ""), style=discord.ButtonStyle.green
    )
    async def approve(self, interaction: discord.Interaction, _: discord.Button):
        """Approve the action"""

        self.value = True
        self.stop()

    @discord.ui.button(
        emoji=CONFIG["emojis"].get("fail", ""), style=discord.ButtonStyle.red
    )
    async def decline(self, interaction: discord.Interaction, _: discord.Button):
        """Decline the action"""

        self.value = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.ctx.author.id:
            return True
        else:
            await interaction.warning(
                "You aren't the **author** of this embed",
            )
            return False
