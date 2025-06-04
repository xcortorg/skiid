from xxhash import xxh32_hexdigest
from collections import defaultdict
from typing import List, Optional, TypedDict, Any, Union, Dict
from discord import Client, Message
from redis.asyncio import Redis
from lib.managers.logger import make_dask_sink, configure_logger
import asyncio


class Reposter:
    bot: Client
    posted: int = 0
    tasks: Dict[str, asyncio.Task]

    def __init__(self, bot: Client, *, name: str = ""):
        self.bot = bot
        self.name = name
        self.locks = defaultdict(asyncio.Lock)
        self.tasks = {}
        self.task: asyncio.Task = None

    def __repr__(self) -> str:
        state: str = "inactive"
        if len(self.tasks) > 0:
            for key, value in self.tasks.items():
                state = "running" if not value.done() else "finished"
                break
        return f"<{self.name}Reposter state={state} posted={self.posted} tasks={len(self.tasks)}>"

    def __str__(self) -> str:
        return self.name

    @property
    def redis(self) -> Redis:
        return self.bot.redis

    @property
    def logger(self):
        return configure_logger(f"Reposter/{self.name.title()}")

    @property
    def key(self) -> str:
        return xxh32_hexdigest(f"reposter:{self.name}")

    def make_key(self, string: str):
        return xxh32_hexdigest(string)

    async def create_task(self, message: Message) -> Message:
        """Create a reposting task"""
        raise NotImplementedError

    async def download(self, url: str):
        """Download a social media post"""
        raise NotImplementedError

    async def repost(self, message: Message):
        """Repost a social media post from a message"""
        raise NotImplementedError
