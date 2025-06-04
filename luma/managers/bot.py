import datetime
import io
import logging
import mimetypes
import os
import uuid
from copy import copy

import aioboto3
import aiohttp
import discord
import discord_ios
import dotenv
import humanize
from discord.ext import commands
from discord.ext.commands import *

from .database import *
from .handlers import Embed, Session, decorators
from .helpers import *

dotenv.load_dotenv(verbose=True)
logging.basicConfig(
    level=logging.INFO,
    format="[{levelname}] ({asctime}) \x1b[37;3m@\033[0m \x1b[31m{module}\033[0m -> {message}",
    datefmt="%Y-%m-%d %H:%M",
    style="{",
)


class Luma(commands.Bot):
    def __init__(self: "Luma"):
        super().__init__(
            command_prefix=getprefix,
            intents=discord.Intents.all(),
            help_command=LumaHelp(),
            case_insensitive=True,
            strip_after_prefix=True,
            allowed_mentions=discord.AllowedMentions(
                roles=False, everyone=False, replied_user=False
            ),
            chunk_guilds_at_startup=False,
            owner_ids=[
                1188955485462872226,  # sent
                1182647110676525107,  # ap
                1280856653230505994,  # s4nica
            ],
            activity=discord.CustomActivity(name="🔗 discord.gg/luma"),
        )
        self.time = datetime.datetime.now()
        self.color = 0x729BB0
        self.cache = Cache()
        self.embed = Embed()
        self.login_data = {
            m: os.environ[m] for m in ["host", "port", "user", "database", "password"]
        }
        self.mcd = commands.CooldownMapping.from_cooldown(
            3, 5, commands.BucketType.user
        )
        self.ccd = commands.CooldownMapping.from_cooldown(
            4, 5, commands.BucketType.channel
        )

    def run(self: "Luma"):
        return super().run(token=os.environ["token"], log_handler=None, reconnect=True)

    async def setup_hook(self: "Luma"):
        await self.load_extension("jishaku")
        self.session = Session()
        self.db = await connect(**self.login_data)
        self.add_check(self.disabled_command)
        await self.load_modules()

    async def close(self: "Luma"):
        if getattr(self, "session"):
            await self.session.close()

        if getattr(self, "db"):
            await self.db.close()

        return await super().close()

    async def load_modules(self: "Luma"):
        files = [
            f"{x}.{p[:-3]}"
            for x in ["cogs", "events"]
            for p in os.listdir(f"./{x}")
            if p.endswith(".py")
        ]
        for file in files:
            try:
                await self.load_extension(file)
            except Exception as e:
                logging.warning(e)

    async def upload_cdn(self: "Luma", url: str, key: str):
        expires_at = datetime.datetime.now() + datetime.timedelta(hours=6)
        content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
        filename = uuid.uuid4().hex

        async with aiohttp.ClientSession() as cs:
            async with cs.get(url) as r:
                data = await r.read()

            async with aioboto3.Session().client(
                "s3",
                endpoint_url=os.environ["endpoint_url"],
                aws_access_key_id=os.environ["aws_access_key_id"],
                aws_secret_access_key=os.environ["aws_secret_access_key"],
            ) as cdn:
                await cdn.put_object(
                    Bucket="luma",
                    Key=filename,
                    Body=data,
                    ContentType=content_type,
                    Expires=expires_at,
                )
            return f"https://cdn.fulcrum.lol/{filename}"

    async def __chunkall(self: "Luma"):
        for guild in self.guilds:
            await guild.chunk(cache=True)

    async def on_ready(self: "Luma"):
        await self.__chunkall()
        discord.User.activity = property(
            fget=lambda a: (
                a.mutual_guilds[0].get_member(a.id).activity
                if a.mutual_guilds
                else None
            )
        )
        logging.info(f"Logged in as {self.user} {self.user.id}")

    async def get_context(
        self: "Luma", message: discord.Message, *, cls=Context
    ) -> Context:
        return await super().get_context(message, cls=cls)

    def flatten(self: "Luma", data: list):
        return [i for y in data for i in y]

    @property
    def uptime(self: "Luma") -> int:
        return humanize.precisedelta(self.time, format="%0.0f")

    @property
    def files(self) -> List[str]:
        return [
            f"{root}/{f}"
            for root, _, file in os.walk("./")
            for f in file
            if f.endswith(".py")
        ]

    @property
    def lines(self) -> int:
        return sum(len(open(f).read().splitlines()) for f in self.files)

    async def bytes(self: "Luma", url: str) -> io.BytesIO:
        return io.BytesIO(await self.session.get(url).read())

    async def on_command(self: "Luma", ctx: Context):
        logging.info(
            f"{ctx.author} ({ctx.author.id}) executed {ctx.command} in {ctx.guild} ({ctx.guild.id}). -> {ctx.message.content})"
        )

    async def on_command_error(
        self: "Luma", ctx: Context, error: CommandError
    ) -> Optional[discord.Message]:
        if isinstance(error, (NotOwner, CommandOnCooldown)):
            return

        elif isinstance(error, CommandInvokeError):
            error = error.original

        elif isinstance(
            error,
            (MissingRequiredArgument, MissingRequiredAttachment, BadLiteralArgument),
        ):
            return await ctx.send_help(ctx.command)

        elif isinstance(error, CheckFailure):
            if isinstance(error, MissingPermissions):
                return await ctx.wanr(
                    f"You're missing `{' '.join(p for p in error.missing_permissions)}` permission"
                )

        elif isinstance(error, CommandNotFound):
            check = await self.db.fetchrow(
                "SELECT * FROM aliases WHERE alias = $1 AND guild_id = $2",
                ctx.invoked_with,
                ctx.guild.id,
            )

            if check:
                msg = copy(ctx.message)
                msg.content = msg.content.replace(ctx.invoked_with, check["alias"], 1)
                return await self.process_commands(msg)
        else:
            return await ctx.warn(error.args[0])

    def member_ratelimit(self, message: discord.Message) -> Optional[int]:
        bucket = self.mcd.get_bucket(message)
        return bucket.update_rate_limit()

    def channel_ratelimit(self, message: discord.Message) -> Optional[int]:
        bucket = self.ccd.get_bucket(message)
        return bucket.update_rate_limit()

    async def process_commands(self: "Luma", message: discord.Message):
        if message.content.startswith(tuple(await getprefix(self, message))):
            mcd = self.member_ratelimit(message)
            ccd = self.channel_ratelimit(message)

            if mcd or ccd:
                return

            return await super().process_commands(message)

    async def on_message_edit(
        self: "Luma", before: discord.Message, after: discord.Message
    ):
        if before.content != after.content:
            return await self.process_commands(after)

    async def on_message(self: "Luma", message: discord.Message):
        if not message.author.bot and message.guild:
            if not await self.db.fetchrow(
                "SELECT * FROM blacklist WHERE id = $1 AND type = $2",
                message.author.id,
                "user",
            ):
                if message.content == self.user.mention:
                    mcd = self.member_ratelimit(message)
                    ccd = self.channel_ratelimit(message)

                    if not mcd and not ccd:
                        prefix = await self.get_prefix(message)
                        await message.reply(f"prefix: `{prefix[-1]}`")

                await self.process_commands(message)

    async def disabled_command(self, ctx: Context):
        if not ctx.guild:
            return True

        if check := await self.db.fetchrow(
            "SELECT * FROM disablecmd WHERE guild_id = $1 AND command = $2",
            ctx.guild.id,
            ctx.command.qualified_name,
        ):
            await ctx.warn(f"**{ctx.command.qualified_name}** is disbaled")

        return not check


async def getprefix(bot: Luma, message: discord.Message):
    prefix: str = (
        await bot.db.fetchval(
            "SELECT prefix FROM prefix WHERE guild_id = $1", message.guild.id
        )
        or ";"
    )
    return when_mentioned_or(prefix)(bot, message)
