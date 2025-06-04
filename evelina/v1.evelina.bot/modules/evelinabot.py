import os
import dotenv
import asyncpg
import logging
import discord
import datetime
import discord_android

from time import time

from loguru import logger
from humanize import precisedelta

from discord.ext import commands

from modules.handlers.database import EvelinaDatabase

dotenv.load_dotenv(verbose=True)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(name)-12s: %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")

intents = discord.Intents.all()

discord_android

class Record(asyncpg.Record):
    def __getattr__(self, name: str):
        return self[name]

class Evelina(commands.AutoShardedBot):
    def __init__(self, db: EvelinaDatabase = None):
        super().__init__(
            activity=discord.CustomActivity(name="🔗 discord.gg/evelina"),
            command_prefix="-",
            case_insensitive=True,
            chunk_guilds_at_startup=False,
            strip_after_prefix=True,
            enable_debug_events=True,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, replied_user=False),
            member_cache=discord.MemberCacheFlags(joined=True, voice=True),
            max_messages=25000,
            heartbeat_timeout=120,
            owner_ids=[206832952980668428, 383304634246103042, 335500798752456705, 560011836775202817, 255489039564668929, 720294426064453665, 727599616043909190], #[bender.xz, visics, curet, trave., msfo, 8pp, eivoran]
            client_id=1241789800332132562,
            intents=intents,
        )
        self.start_time = time()
        self.global_cd = commands.CooldownMapping.from_cooldown(15, 60, commands.BucketType.member)
        self.db = db
        self.login_data = {x: os.environ[x] for x in ["host", "password", "database", "user", "port"]}
        self.login_data["record_class"] = Record
        self.log = None
        self.debug = False
        self.version = "1.0"
        self.time = datetime.datetime.now()
        self.mcd = commands.CooldownMapping.from_cooldown(3, 5, commands.BucketType.user)
        self.ccd = commands.CooldownMapping.from_cooldown(4, 5, commands.BucketType.channel)
        self.extensions_loaded = False
        self.boot_up_time: float | None = None
        self.logging_guild = 1237882622110335017

    def run(self):
        return super().run(os.environ["BOT_TOKEN"])

    @property
    def uptime(self) -> str:
        return precisedelta(self.time, format="%0.0f")

    async def create_db(self) -> asyncpg.Pool:
        logger.info("Creating PostgreSQL db connection")
        return await EvelinaDatabase().__aenter__(**self.login_data)

    async def setup_hook(self) -> None:
        logger.info("Starting bot")
        if not self.db:
            self.db = await self.create_db()
        await self.load()

    async def load(self) -> None:
        for file in [f[:-3] for f in os.listdir("./events") if f.endswith(".py")]:
            try:
                await self.load_extension(f"events.{file}")
                logger.info(f"Loaded events.{file}")
            except Exception as e:
                logger.warning(f"Unable to load events.{file}: {e}")
        logger.info("Loaded all cogs and events")

    async def on_ready(self):
        latencies = self.latencies
        if self.boot_up_time is None:
            self.boot_up_time = time() - self.start_time
        logger.info(f"Loading complete | running {len(latencies)} shards")
        for shard_id, latency in latencies:
            logger.info(f"Shard [{shard_id}] - HEARTBEAT {latency:.2f}s")
        logger.info("Evelina booted successfully")