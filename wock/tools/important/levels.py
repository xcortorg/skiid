import math
import random
import traceback
from asyncio import Future, Lock, Task, as_completed, create_task
from asyncio import ensure_future as do_soon
from asyncio import iscoroutinefunction
from collections import defaultdict as collection
from datetime import datetime
from typing import Any, Callable, Coroutine, Dict, Optional, TypeVar

from discord import (Client, Embed, Guild, Member, Message, VoiceChannel,
                     VoiceState)
from discord.ext import tasks
from discord.ext.commands import Context
from humanize import naturaltime
from loguru import logger
from typing_extensions import Self
from xxhash import xxh64_hexdigest as hash_

T = TypeVar("T")
Coro = Coroutine[Any, Any, T]
CoroT = TypeVar("CoroT", bound=Callable[..., Coro[Any]])


def get_timestamp():
    return datetime.now().timestamp()


class Level:
    def __init__(self, multiplier: float = 0.5, bot: Optional[Client] = None):
        self.multiplier = multiplier
        self.bot = bot
        self._events = ["on_text_level_up", "on_voice_level_up"]
        self.listeners: Dict[str, Future] = {}
        self.logger = logger
        self.locks = collection(Lock)
        self.cache = {}
        self.messages = []
        self.text_cache = {}
        self.level_cache = {}
        self.text_level_loop.start()

    async def setup(self, bot: Client) -> Self:
        self.bot = bot
        self.logger.info("Starting levelling loop")
        self.bot.loop.create_task(self.do_voice_levels())
        self.bot.loop.create_task(self.do_text_levels())
        self.bot.add_listener(self.voice_update, "on_voice_state_update")
        self.bot.add_listener(self.do_message_event, "on_message")
        self.bot.add_listener(self.member_left, "on_voice_state_update")
        self.logger.info("Levelling loop started")
        return self

    @tasks.loop(minutes=2)
    async def text_level_loop(self):
        await self.do_text_levels()

    @tasks.loop(minutes=2)
    async def voice_level_loop(self):
        await self.do_voice_levels()

    def add_listener(self, coro: Coroutine, name: str) -> None:
        """
        Registers a listener for the event.

        The available events are:
            | ``on_voice_level_up``: the user has levelled up in the guild for voice experience.
            | ``on_text_level_up``: the user has levelled up in the guild for text experience.

        Raises
        -------
            NameError
                Invalid levelling event name.
            TypeError
                The event function is not a coro.
        """
        if name not in self._events:
            raise NameError("Invalid levelling event")

        if not iscoroutinefunction(coro):
            raise TypeError("Event function must be a coro.")

        if name not in self.listeners:
            self.listeners[name] = set()

        self.listeners[name].add(do_soon(coro))

    def get_xp(self, level: int) -> int:
        """
        :param level : Level(int)
        :return      : Amount of xp(int) needed to reach the level
        """
        return math.ceil(math.pow((level - 1) / (0.05 * (1 + math.sqrt(5))), 2))

    def get_level(self, xp: int) -> int:
        """
        :param xp : XP(int)
        :return   : Level(int)
        """
        return math.floor(0.05 * (1 + math.sqrt(5)) * math.sqrt(xp)) + 1

    def xp_to_next_level(
        self, current_level: Optional[int] = None, current_xp: Optional[int] = None
    ) -> int:
        if current_xp is not None:
            current_level = self.get_level(current_xp)
        return self.get_xp(current_level + 1) - self.get_xp(current_level)

    def add_xp(self, message: Optional[Message]) -> int:
        if message:
            words = message.content.split(" ")
            eligble = len([w for w in words if len(w) > 1])
            xp = eligble + (10 * len(message.attachments))
            if xp == 0:
                xp = 1
            return min(xp, 50)
        else:
            return random.randint(1, 50) / self.multiplier

    def difference(self, ts: float) -> int:
        now = int(get_timestamp())
        return now - int(ts)

    async def validate(
        self, guild: Guild, channel: VoiceChannel, member: Member
    ) -> bool:
        async with self.locks["voice_levels"]:
            key = hash_(f"{guild.id}-{channel.id}-{member.id}")
            if key in self.cache:
                before_xp = await self.bot.db.fetchval(
                    """SELECT xp FROM voice_levels WHERE guild_id = $1 AND user_id = $2""",
                    guild.id,
                    member.id,
                )
                after_xp = await self.bot.db.execute(
                    [
                        """SELECT xp FROM voice_levels WHERE guild_id = $1 AND user_id = $2""",
                        """SELECT xp FROM voice_levels WHERE guild_id = $1 AND user_id = $2""",
                        """INSERT INTO voice_levels (guild_id,user_id,xp,time_spent) VALUES($1,$2,$3,$4) ON CONFLICT(guild_id,user_id) DO UPDATE SET xp = voice_levels.xp + excluded.xp, time_spent = time_spent + excluded.time_spent RETURNING xp""",
                    ],
                    guild.id,
                    member.id,
                    self.add_xp(),
                    self.difference(self.cache[key]),
                )
                if self.get_level(int(before_xp)) != self.get_level(int(after_xp)):
                    self.dispatch_event(
                        "on_voice_level_up",
                        guild,
                        channel,
                        member,
                        self.get_level(int(after_xp)),
                    )
                self.cache.pop(key)
            else:
                self.cache[key] = int(get_timestamp())
                return False
            return True

    async def validate_text(self, message: Message, execute: bool = False) -> bool:
        async with self.locks["text_levels"]:
            if message not in self.messages:
                self.messages.append(message)
            key = f"{message.guild.id}-{message.author.id}"
            if key in self.text_cache:
                if execute is True:
                    before_xp = await self.bot.db.fetchval(
                        """SELECT xp FROM text_levels WHERE guild_id = $1 AND user_id = $2""",
                        message.guild.id,
                        message.author.id,
                    )
                    if message not in self.text_cache[key]["messages"]:
                        self.text_cache[key]["messages"].append(message)
                        amount = self.text_cache[key]["amount"] + 1
                    else:
                        amount = self.text_cache[key]["amount"]
                    added_xp = sum(
                        [self.add_xp(m) for m in self.text_cache[key]["messages"]]
                    )
                    after_xp = await self.bot.db.execute(
                        """INSERT INTO text_levels (guild_id,user_id,xp,msgs) VALUES($1,$2,$3,$4) ON CONFLICT(guild_id,user_id) DO UPDATE SET xp = text_levels.xp + excluded.xp, msgs = text_levels.msgs + excluded.msgs RETURNING xp""",
                        message.guild.id,
                        message.author.id,
                        added_xp,
                        amount,
                    )
                    after_xp = before_xp + added_xp
                    if self.get_level(int(before_xp)) != self.get_level(int(after_xp)):
                        self.dispatch_event(
                            "on_text_level_up",
                            message.guild,
                            message.author,
                            self.get_level(int(after_xp)),
                        )
                    self.text_cache.pop(key)
                else:
                    self.text_cache[key]["amount"] += 1
                    self.text_cache[key]["messages"].append(message)
                return True
            else:
                self.text_cache[key] = {"amount": 1, "messages": [message]}
                if execute is True:
                    before_xp = await self.bot.db.fetchval(
                        """SELECT xp FROM text_levels WHERE guild_id = $1 AND user_id = $2""",
                        message.guild.id,
                        message.author.id,
                    )
                    added_xp = sum(
                        [self.add_xp(m) for m in self.text_cache[key]["messages"]]
                    )
                    amount = self.text_cache[key]["amount"]
                    after_xp = await self.bot.db.execute(
                        """INSERT INTO text_levels (guild_id,user_id,xp,msgs) VALUES($1,$2,$3,$4) ON CONFLICT(guild_id,user_id) DO UPDATE SET xp = text_levels.xp + excluded.xp, msgs = text_levels.msgs + excluded.msgs RETURNING xp""",
                        message.guild.id,
                        message.author.id,
                        added_xp,
                        amount,
                    )
                    after_xp = before_xp + added_xp
                    if self.get_level(int(before_xp)) != self.get_level(int(after_xp)):
                        self.dispatch_event(
                            "on_text_level_up",
                            message.guild,
                            message.author,
                            self.get_level(int(after_xp)),
                        )
                    self.text_cache.pop(key)
                return True

    async def get_statistics(self, member: Member, type: str) -> Optional[tuple]:
        if type.lower() == "text":
            if data := await self.bot.db.fetchval(
                """SELECT xp, messages FROM text_levels WHERE guild_id = $1 AND user_id = $2""",
                member.guild.id,
                member.id,
            ):
                return tuple(int(data[0]), int(data[1]))
            else:
                return None
        else:
            if data := await self.bot.db.fetchval(
                """SELECT xp, time_spent FROM voice_levels WHERE guild_id = $1 AND user_id = $2""",
                member.guild.id,
                member.id,
            ):
                return tuple(int(data[0]), int(data[1]))
            else:
                return None

    async def do_voice_levels(self):
        if self.bot is None:
            return
        async with self.locks["voice_levels"]:
            active_voice_channels = [
                v
                for g in self.bot.guilds
                for v in g.voice_channels
                if len(v.members) > 0
            ]
            tasks = [
                create_task(self.validate(v.guild, v, m))
                for v in active_voice_channels
                for m in v.members
            ]
            if tasks:
                for t in as_completed(tasks):
                    await t

    async def member_left(
        self, guild: Guild, channel: VoiceChannel, member: Member
    ) -> bool:
        if self.bot is None:
            return
        key = f"{guild.id}-{channel.channel.id}-{member.id}"
        if key in self.cache:
            await self.validate(guild, channel, member)
            value = True
        else:
            value = False
        return value

    async def voice_update(self, member: Member, before: VoiceState, after: VoiceState):
        if before.channel is not None:
            await self.member_left(before.channel.guild, before.channel, member)
            if after.channel is not None:
                await self.validate(before.guild, after.channel, member)
        else:
            if after.channel is not None:
                await self.validate(after.guild, after.channel, member)

    async def do_message_event(self, message: Message):
        if self.bot is None:
            return
        await self.validate_text(message)

    async def do_text_levels(self):
        if self.bot is None:
            return
        tasks = [
            create_task(self.validate_text(m, execute=True)) for m in self.messages
        ]
        if tasks:
            for t in as_completed(tasks):
                await t

    def get_voice_time(self, time: int) -> str:
        currently = int(get_timestamp())
        difference = currently + time
        return naturaltime(datetime.from_timestamp(difference))

    async def get_member_xp(self, ctx: Context, type: str, member: Member) -> Embed:
        if data := await self.get_statistics(member, type):
            xp, amount = data
        if type.lower() == "voice":
            amount = f"`{self.get_voice_time(amount)}`"
            amount_type = "vc time"
        else:
            amount_type = "messages"
        return (
            Embed(title=f"{str(member)}'s {type.lower()} level", url=self.bot.website)
            .add_field(
                name="xp",
                value=f"{xp}/{self.xp_to_next_level(current_xp=xp)}",
                inline=True,
            )
            .add_field(name="level", value=self.get_level(xp), inline=True)
            .add_field(name=amount_type.lower(), value=amount, inline=True)
        )

    def event(self, func: Coroutine, /) -> Coroutine:
        """
        Registers a function for the event.

        The available events are:
            | ``on_voice_level_up``: the user has levelled up in the guild for voice experience.
            | ``on_text_level_up``: the user has levelled up in the guild for text experience.

        Raises
        -------
            NameError
                Invalid levelling event name.
            TypeError
                The event function is not a coro.
        """
        if func.__name__ not in self._events:
            raise NameError("Invalid levelling event")

        if not iscoroutinefunction(func):
            raise TypeError("Event function must be a coro.")

        setattr(self, func.__name__, func)
        self.logger.debug(
            "%s has successfully been registered as an event", func.__name__
        )
        return func

    def dispatch_event(self, name: str, *args, **kwargs) -> None:
        """
        Dispatches an event.

        Parameters
        __________
        name
        *args
        **kwargs

        Returns:

        """
        self.logger.debug("Event Dispatch -> %r", name)
        try:
            for future in self.listeners[name]:
                future.set_result(None)
                self.logger.debug("Event %r has been dispatched", name)
        except KeyError:
            ...

        try:
            coro = getattr(self, f"on_{name}")
        except AttributeError:
            pass
        else:
            self._schedule_event(coro, f"on_{name}", *args, **kwargs)

    def _schedule_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        event_name: str,
        *args: Any,
        **kwargs: Any,
    ) -> Task:
        """

        Args:
            coro:
            event_name:
            *args:
            **kwargs:

        Returns:

        """
        wrapped = self._run_event(coro, event_name, *args, **kwargs)
        # Schedules the task
        return create_task(wrapped, name=f"levelling: {event_name}")

    async def _run_event(
        self,
        coro: Callable[..., Coroutine[Any, Any, Any]],
        name: str,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        try:
            await coro(*args, **kwargs)
        except Exception:
            # TODO
            traceback.print_exc()
