import glob
import os
import time
from datetime import datetime, timedelta, timezone
from os import environ
from typing import List

import aiohttp
import asyncpg
from aiohttp import ClientSession
from asyncpg import Pool, create_pool
from config import color, emoji
from discord import CustomActivity, Embed, Intents, Message
from discord.ext.commands import AutoShardedBot
from system.base import Context


class Myth(AutoShardedBot):
    pool: Pool
    session: ClientSession

    def __init__(self, token):
        self.message_cache = {}
        self.cache_expiry_seconds = 15
        self.start_time = time.time()

        super().__init__(
            command_prefix=self.get_prefix,  # type: ignore
            help_command=None,
            intents=Intents().all(),
            owner_ids=[
                394152799799345152,  # main
                255841984470712330,  # solix
                1168186952772747364,  # alt
                1282499485536092181,  # leon the silly car developer aka the best developer on this bot >.<
            ],
            activity=CustomActivity(name=f"🔗 discord.gg/uid"),
        )
        self.run(token)

    @property
    def public_cogs(self) -> list:
        return [
            cog.qualified_name
            for cog in self.cogs.values()
            if cog.qualified_name not in ("Jishaku", "Owner", "Developer")
        ]

    @property
    def public_commands(self) -> list:
        return [
            command.name
            for command in self.walk_commands()
            if command.cog_name in self.public_cogs
        ]

    @property
    def members(self):
        return list(self.get_all_members())

    async def load_database(self) -> None:
        database = environ.get("DATABASE")

        if not database:
            raise ValueError("Failed to get database information")

        self.pool = await create_pool(  # type: ignore
            user=environ.get("DATABASE_USER", "postgres"),
            password=environ.get("DATABASE_PASSWORD", "local"),
            database=environ.get("DATABASE", "myth"),
            host=environ.get("DATABASE_HOST", "127.0.0.1"),
            max_size=10,
            min_size=10,
        )

        with open("system/schema/schema.sql", "r") as file:
            await self.pool.execute(file.read())  # type: ignore

    async def get_prefix(self, message: Message):
        await self.wait_until_ready()

        result = (
            await self.pool.fetchval(  # type: ignore
                """
            SELECT prefix FROM prefixes
            WHERE user_id = $1
            """,
                str(message.author.id),
            )
            or ";"
        )

        return result

    async def get_context(self, origin, cls=Context) -> Context:
        return await super().get_context(origin, cls=cls)

    async def setup_hook(self):
        self.session = ClientSession()
        await self.load_database()
        await self.load_extension("jishaku")
        await self.load_cogs_from_dir("cogs")

    async def close(self):
        await self.session.close()
        await super().close()

    def uptime(self):
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)
        uptime_datetime = datetime.fromtimestamp(self.start_time, timezone.utc)
        return uptime_datetime

    def lines(self):
        total_lines = 0
        for root, _, files in os.walk("."):
            for filename in files:
                if filename.endswith(".py"):
                    with open(
                        os.path.join(root, filename), "r", encoding="utf-8"
                    ) as file:
                        lines = file.readlines()
                        total_lines += len(lines)
        return total_lines

    async def on_message(self, message: Message):
        if message.author.bot:
            return

        author_id_str = str(message.author.id)

        check = await self.pool.fetchrow(
            "SELECT * FROM blacklist WHERE user_id = $1", author_id_str
        )
        if check:
            return

        prefix = await self.get_prefix(message)
        if not message.content.startswith(tuple(prefix)):
            return

        now = time.time()
        author_id = message.author.id

        if author_id not in self.message_cache:
            self.message_cache[author_id] = []

        self.message_cache[author_id] = [
            timestamp
            for timestamp in self.message_cache[author_id]
            if now - timestamp < self.cache_expiry_seconds
        ]

        if len(self.message_cache[author_id]) >= 10:
            await self.pool.execute(
                "INSERT INTO blacklist (user_id) VALUES ($1)", author_id_str
            )
            embed = Embed(
                description=f"> {emoji.deny} {message.author.mention}: **You got blacklisted,** if you think is by accident join the [support server](https://discord.gg/uid)",
                color=color.deny,
            )
            await message.channel.send(embed=embed)
        else:
            self.message_cache[author_id].append(now)
            await self.process_commands(message)

    async def uid(self, user_id):
        existing_uid = await self.pool.fetchrow(
            "SELECT uid FROM uids WHERE user_id = $1", user_id
        )
        if existing_uid:
            return existing_uid["uid"]

        new_uid = await self.pool.execute(
            "INSERT INTO uids (user_id) VALUES ($1) RETURNING uid", user_id
        )
        return new_uid

    async def on_command(self, ctx):
        user_id = ctx.author.id
        uid = await self.uid(user_id)
