import os
import random
import time
from datetime import datetime, timedelta

import asyncpg
import discord
import discord_ios
import jishaku
from asyncpg import Pool
from discord import Message
from discord.ext import commands, tasks
from tools.config import color, emoji
from tools.context import Context

intents = discord.Intents().default()
intents.members = True
intents.message_content = True
intents.messages = True
intents.dm_messages = True


class Blare(commands.AutoShardedBot):
    def __init__(self, token):
        super().__init__(
            command_prefix=self.get_prefix,
            help_command=None,
            intents=intents,
            owner_ids=[
                394152799799345152,  # physic
                255841984470712330,  # solix
                111646804658921472,  # imtotallysolix
                236957169302372352,  # solix.holder
            ],
        )
        self.start_time = time.time()
        self.statuses = [
            "🔗 discord.gg/blare",
            "✨ Brand new revamp..",
            "🔎 Updated a lot..",
        ]
        self.pool = None
        self.message_cache = {}
        self.cache_expiry_seconds = 60
        self.run(token)

    async def load(self, directory):
        for filename in os.listdir(directory):
            if filename.endswith(".py"):
                await self.load_extension(f"{directory}.{filename[:-3]}")

    def uptime(self):
        current_time = time.time()
        uptime_seconds = int(current_time - self.start_time)
        uptime_datetime = datetime.utcfromtimestamp(self.start_time)
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

    async def get_prefix(self, message: Message):
        await self.wait_until_ready()

        result = (
            await self.pool.fetchval(  # type: ignore
                """
            SELECT prefix FROM prefixes
            WHERE user_id = $1
            """,
                message.author.id,
            )
            or "-"
        )

        return result

    async def setup_hook(self):
        await self.load_extension("jishaku")
        await self.load("cogs")
        self.pool = await self._load_database()
        if not self.rotate.is_running():
            self.rotate.start()
        print(f"[ + ] {self.user} is ready")

    async def get_context(self, origin, cls=Context):
        return await super().get_context(origin, cls=cls)

    @tasks.loop(seconds=5)
    async def rotate(self):
        status = random.choice(self.statuses)
        await self.change_presence(activity=discord.CustomActivity(name=status))

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if not hasattr(self, "message_cache"):
            self.message_cache = {}

        if not hasattr(self, "cache_expiry_seconds"):
            self.cache_expiry_seconds = 60

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
            embed = discord.Embed(
                description=f"> {emoji.deny} {message.author.mention}: **You got blacklisted,** if you think is by accident join the [support server](https://discord.gg/blare)",
                color=color.deny,
            )
            await message.channel.send(embed=embed)
        else:
            self.message_cache[author_id].append(now)
            await self.process_commands(message)

    async def _load_database(self) -> Pool:
        try:
            pool = await asyncpg.create_pool(
                **{
                    var: os.environ[
                        f"DATABASE_{var.upper()}" if var != "database" else "DATABASE"
                    ]
                    for var in ["database", "user", "password", "host"]
                },
                max_size=30,
                min_size=10,
            )
            print("Database connection established")

            with open("tools/schema/schema.sql", "r") as file:
                schema = file.read()
                if schema.strip():
                    await pool.execute(schema)
                    print("Database schema loaded")
                else:
                    print("Database schema file is empty")
                file.close()

            return pool
        except Exception as e:
            print(f"Error loading database: {e}")
            raise e
