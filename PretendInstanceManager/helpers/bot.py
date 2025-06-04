import logging
import os

import aiohttp
import discord
import dotenv
from discord.ext import commands
from helpers.context import Context

handler = logging.FileHandler(
    filename="discord.log",
    encoding="utf-8",
    mode="w",
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)

formatter = logging.Formatter(
    "%(asctime)s | %(name)-12s: %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S"
)

console.setFormatter(formatter)
logging.getLogger("").addHandler(console)

log = logging.getLogger(__name__)

dotenv.load_dotenv()


class PretendInstances(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
            allowed_mentions=discord.AllowedMentions(
                everyone=False, roles=False, users=True, replied_user=False
            ),
            owner_ids=[1161982476143575051, 930383131863842816, 863914425445908490],
        )

        self.color = 0x808080
        self.run()

    def run(self) -> None:
        super().run(token=os.getenv("token"), reconnect=True, log_handler=handler)

    async def setup_hook(self):
        await self.load_extension("jishaku")
        await self.load()
        print(f"Loaded extensions")

        self.session: aiohttp.ClientSession = self.http._HTTPClient__session

    async def on_ready(self):
        print(f"Ready as {self.user}")

    async def on_command_error(self, ctx: Context, error: Exception):
        return await ctx.reply(str(error))

    async def get_context(self, message: discord.Message, cls=None) -> None:
        return await super().get_context(message, cls=cls or Context)

    async def load(self):
        for file in os.listdir("cogs"):
            if file.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{file[:-3]}")
                    print(f"Loaded cog {file}")
                except Exception as e:
                    print(f"Failed to load {file}: {e}")
