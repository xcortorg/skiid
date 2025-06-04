import asyncio
import contextlib
import os
import unicodedata
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import discord
from discord.ext import commands
from discord.ext.commands import CommandError
from discord.utils import cached_property
from loguru import logger

TUPLE = ()
SET = set()


def is_unicode(emoji: str) -> bool:
    with contextlib.suppress(Exception):
        unicodedata.name(emoji)
        return True

    return False


class NonRetardedCache:
    def __init__(self, bot):
        self.bot = bot

    async def setup_forcenick(self):
        self.forcenick = {}
        for guild_id, user_id, nick in await self.bot.db.fetch(
            """SELECT guild_id, user_id, nick FROM forcenick"""
        ):
            if int(guild_id) not in self.forcenick:
                self.forcenick[int(guild_id)] = {}
            self.forcenick[int(guild_id)][int(user_id)] = str(nick)

    async def setup_autoresponders(self):
        self.autoresponders = {}
        for guild_id, trig, response in await self.bot.db.fetch(
            """SELECT guild_id, trig, response FROM autoresponder"""
        ):
            g = int(guild_id)
            trig = str(trig)
            response = str(response)
            if g not in self.autoresponders:
                self.autoresponders[g] = {}
            self.autoresponders[g][trig] = response

    async def setup_prefixes(self):
        self.prefixes = {}
        self.self_prefixes = {}
        for guild_id, prefix in await self.bot.db.fetch(
            """SELECT guild_id, prefix FROM prefixes"""
        ):
            self.self_prefixes[int(guild_id)] = str(prefix)
        for user_id, prefix in await self.bot.db.fetch(
            """SELECT user_id, prefix FROM selfprefix"""
        ):
            self.self_prefixes[int(user_id)] = str(prefix)

    async def setup_autorole(self):
        self.autorole = {}
        for guild_id, role_id in await self.bot.db.fetch(
            """SELECT guild_id, role_id FROM autorole"""
        ):
            if int(guild_id) in self.autorole:
                self.autorole[int(guild_id)].append(int(role_id))
            else:
                self.autorole[int(guild_id)] = [int(role_id)]

    async def setup_autoreacts(self):
        self.autoreacts = {}
        for guild_id, event, reaction in await self.bot.db.fetch(
            """SELECT guild_id, event, reaction FROM autoreact_event"""
        ):
            if int(guild_id) in self.autoreacts:
                if event in self.autoreacts[int(guild_id)]:
                    self.autoreacts[int(guild_id)][str(event)].append(reaction)
                else:
                    self.autoreacts[int(guild_id)][str(event)] = [reaction]
            else:
                self.autoreacts[int(guild_id)] = {str(event): [reaction]}
        for guild_id, keyword, reaction in await self.bot.db.fetch(
            """SELECT guild_id, keyword, reaction FROM autoreact"""
        ):
            if int(guild_id) in self.autoreacts:
                if keyword in self.autoreacts[int(guild_id)]:
                    self.autoreacts[int(guild_id)][str(keyword)].append(reaction)
                else:
                    self.autoreacts[int(guild_id)][str(keyword)] = [reaction]
            else:
                self.autoreacts[int(guild_id)] = {str(keyword): [reaction]}

    async def setup_filter(self):
        if hasattr(self.bot, "snipes"):
            del self.bot.snipes.data
            self.bot.snipes.data = {}
        self.filter = {}
        self.filter_event = {}
        self.filter_whitelist = {}
        for guild_id, keyword in await self.bot.db.fetch(
            """SELECT guild_id,keyword FROM filter"""
        ):
            if int(guild_id) in self.filter:
                self.filter[int(guild_id)].append(keyword)
            else:
                self.filter[int(guild_id)] = [keyword]

        for guild_id, event, is_enabled, threshold in await self.bot.db.fetch(
            """SELECT guild_id, event, is_enabled, threshold FROM filter_event"""
        ):
            if int(guild_id) in self.filter_event:
                self.filter_event[int(str(guild_id))][event] = {
                    "threshold": threshold,
                    "is_enabled": is_enabled,
                }

            else:
                self.filter_event[int(str(guild_id))] = {
                    event: {
                        "threshold": threshold,
                        "is_enabled": is_enabled,
                    }
                }

        for guild_id, user_id in await self.bot.db.fetch(
            "SELECT guild_id, user_id from filter_whitelist"
        ):
            if int(guild_id) in self.filter_whitelist:
                self.filter_whitelist[int(guild_id)].append(keyword)
            else:
                self.filter_whitelist[int(guild_id)] = [keyword]

    async def setup_welcome(self):
        self.welcome = {}
        for guild_id, channel_id, message in await self.bot.db.fetch(
            """SELECT guild_id,channel_id,message FROM welcome"""
        ):
            self.welcome[int(str(guild_id))] = {
                "channel": int(str(channel_id)),
                "message": str(message),
            }

    async def setup_leave(self):
        self.leave = {}
        for guild_id, channel_id, message in await self.bot.db.fetch(
            """SELECT guild_id,channel_id,message FROM leave"""
        ):
            self.leave[int(str(guild_id))] = {
                "channel": int(str(channel_id)),
                "message": str(message),
            }

    async def setup_cache(self):
        logger.info("Beginning Caching")
        tasks = [
            self.setup_autoreacts(),
            self.setup_welcome(),
            self.setup_leave(),
            self.setup_prefixes(),
            self.setup_filter(),
            self.setup_autorole(),
            self.setup_forcenick(),
            self.setup_autoresponders(),
        ]
        await asyncio.gather(*tasks)
        logger.info("Finished Caching")


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

    def get(self: "ParameterParser", parameter: str, **kwargs: Dict[str, Any]) -> Any:
        self.context.message.content = self.context.message.content.replace(" —", " --")

        for parameter in (parameter, *kwargs.get("aliases", TUPLE)):
            sliced = self.context.message.content.split()

            if kwargs.get("require_value", True) is False:
                if f"-{parameter}" not in sliced:
                    return kwargs.get("default", None)

                return True

            try:
                index = sliced.index(f"--{parameter}")

            except ValueError:
                return kwargs.get("default", None)

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
                    result = self.context.bot.loop.create_task(
                        converter().convert(self.context, result)
                    )

                else:
                    try:
                        result = converter(result)

                    except Exception:
                        raise CommandError(
                            f"Invalid value for parameter `{parameter}`."
                        )

            if isinstance(result, int):
                if result < kwargs.get("minimum", 1):
                    raise CommandError(
                        f"The **minimum input** for parameter `{parameter}` is `{kwargs.get('minimum', 1)}`"
                    )

                if result > kwargs.get("maximum", 100):
                    raise CommandError(
                        f"The **maximum input** for parameter `{parameter}` is `{kwargs.get('maximum', 100)}`"
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


class Context(commands.Context):
    def __init__(self, **kwargs):
        self.__parameter_parser = ParameterParser(self)
        super().__init__(**kwargs)

    @cached_property
    def parameters(self) -> Dict[str, Any]:
        return {
            name: self.__parameter_parser.get(name, **config)
            for name, config in self.command.parameters.items()
        }

    async def success(self, text, **kwargs):
        emoji = ""
        if config := await self.bot.db.fetchrow(
            """SELECT success_emoji, success_color FROM context WHERE guild_id = $1""",
            self.guild.id,
        ):
            if config.get("success_emoji"):
                emoji += config["success_emoji"]
            if config.get("success_color"):
                color = discord.Color.from_str(config["success_color"])
            else:
                color = 0x2B2D31
        else:
            color = 0x2B2D31
        embed = discord.Embed(
            color=color, description=f"{emoji} {self.author.mention}: {text}"
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)

    async def currency(self, text, **kwargs):
        color = 0x2B2D31
        embed = discord.Embed(
            color=color,
            description=f"<a:wockpayout:1251331742720200704> {self.author.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)

    async def deposit(self, text, **kwargs):
        color = 0x2B2D31
        embed = discord.Embed(
            color=color,
            description=f"<a:wockdeposit:1251342814386589787> {self.author.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)

    async def withdraw(self, text, **kwargs):
        color = 0x2B2D31
        embed = discord.Embed(
            color=color,
            description=f"<:wockwithdraw:1251342886323224596> {self.author.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)

    async def normal(self, text, **kwargs):
        color = 0x2B2D31
        embed = discord.Embed(color=color, description=f"{self.author.mention}: {text}")
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed, delete_after=delete_after)

    async def fail(self, text, **kwargs):
        emoji = ""
        if config := await self.bot.db.fetchrow(
            """SELECT fail_emoji, fail_color FROM context WHERE guild_id = $1""",
            self.guild.id,
        ):
            if config.get("fail_emoji"):
                emoji += config["fail_emoji"]
            if config.get("fail_color"):
                color = discord.Color.from_str(config["fail_color"])
            else:
                color = 0x2B2D31
        else:
            color = 0x2B2D31
        embed = discord.Embed(
            color=color, description=f"{emoji} {self.author.mention}: {text}"
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed)

    async def warning(self, text, **kwargs):
        emoji = ""
        if config := await self.bot.db.fetchrow(
            """SELECT warning_emoji, warning_color FROM context WHERE guild_id = $1""",
            self.guild.id,
        ):
            if config.get("warning_emoji"):
                emoji += config["warning_emoji"]
            else:
                if kwargs.get("emoji"):
                    emoji += kwargs.get("emoji")
            if config.get("warning_color"):
                color = discord.Color.from_str(config["warning_color"])
            else:
                color = 0xFFA500
        else:
            color = 0xFFA500
            if e := kwargs.get("emoji"):
                emoji += e
            else:
                emoji = None
        embed = discord.Embed(
            color=color,
            description=f"{emoji or '<:wockwarning:1234264951091105843>'} {self.author.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.send(embed=embed)

    # misc

    async def send(self, *args, **kwargs):
        user = await self.bot.db.fetchrow(
            """SELECT *
            FROM reskin.main
            WHERE user_id = $1""",
            self.author.id,
        )

        server = await self.bot.db.fetchrow(
            """SELECT *
            FROM reskin.server
            WHERE guild_id = $1""",
            self.guild.id,
        )

        if check := user or server:
            webhooks = [
                w
                for w in await self.channel.webhooks()
                if w.user.id == self.bot.user.id
            ]
            if len(webhooks) > 0:
                webhook = webhooks[0]
            else:
                webhook = await self.channel.create_webhook(name="zonu reskin")
            kwargs.update(
                {
                    "avatar_url": check["avatar"],
                    "username": check["username"],
                    "wait": True,
                }
            )
            return await webhook.send(*args, **kwargs)
        else:
            return await super().send(*args, **kwargs)

    #     async def send_help(self, command=None):
    #         command = self.command or self.bot.get_command(command)
    #         assert command, "Command is None"
    #         usage = f' {command.usage}' if command.usage else ''
    #         embed = discord.Embed(
    #             color=self.bot.color,
    #             description=f"""{command.description}
    # ```Syntax: {self.clean_prefix}{command.qualified_name}{usage}```"""
    #         )

    #         embed.add_field(
    #             name="Aliases",
    #             value=', '.join(alias for alias in command.aliases),
    #             inline=True
    #         )

    #         embed.set_author(
    #             name=self.bot.user.name,
    #             icon_url=self.bot.user.display_avatar
    #         )

    #         if isinstance(command, commands.Group):
    #             embed.add_field(
    #                 name="Sub commands",
    #                 value=f"\n".join(
    #                     f"**{c.qualified_name}** ``:`` *{c.short_doc or 'No description available'}*"
    #                     for c in command.walk_commands()
    #                 ),
    #                 inline=False
    #             )
    #         await self.send(embed=embed)

    async def alternative_paginate(
        self,
        embeds: list,
        message: Optional[discord.Message] = None,
        invoker_lock: Optional[bool] = True,
    ):
        import button_paginator as pg  # type: ignore

        if invoker_lock is True:
            paginator = pg.Paginator(self.bot, embeds, self, invoker=self.author.id)
        else:
            paginator = pg.Paginator(self.bot, embeds, self)
        if len(embeds) > 1:
            paginator.add_button(
                "prev",
                emoji="<:previous:1110882835167985724>",
                style=discord.ButtonStyle.blurple,
            )
            paginator.add_button(
                "next",
                emoji="<:next:1110882794416132197>",
                style=discord.ButtonStyle.blurple,
            )
            paginator.add_button(
                "goto",
                emoji="<:filter:1110883391802454066>",
                style=discord.ButtonStyle.grey,
            )
            paginator.add_button(
                "delete",
                emoji="<:stop:1110883418708901928>",
                style=discord.ButtonStyle.red,
            )
        elif len(embeds) == 1:
            paginator.add_button(
                "delete",
                emoji="<:stop:1110883418708901928>",
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

    async def paginate(self, embeds: list, message: Optional[discord.Message] = None):

        if not embeds:
            return await self.fail("I couldn't find any data to show.")

        if len(embeds) == 1:
            return await self.send(embed=embeds[0])
        return await self.alternative_paginate(embeds, message)
