from pathlib import Path
from discord.ext.commands.context import Context
from discord.ext.commands.errors import CommandError
from loguru import logger as log
from cashews import cache
import importlib
import glob
from typing import (
    TYPE_CHECKING,
)
from tuuid import tuuid
from psutil import Process
from discord.ext.commands import (
    AutoShardedBot,
    MissingRequiredArgument,
    CommandNotFound,
    when_mentioned_or,
    NotOwner,
    EmojiNotFound,
    PartialEmojiConverter,
    BadUnionArgument,
    CommandOnCooldown,
    CheckFailure,
    DisabledCommand,
    UserInputError,
    MissingPermissions,
    BadInviteArgument,
)
from discord.utils import utcnow
from discord import (
    AllowedMentions,
    Intents,
    CustomActivity,
    PartialEmoji,
    Status,
    Message,
)
from pomice import NodePool
import time


from system.base import Database, ClientSession
from system.base.context import Context
from system.tools import BrowserHandler
from system.base.settings import Settings
from config import Marly as BotConfig
from config import Redis as RedisConfig
from system.tools.redis import Redis
from system.tools.converters.emojis import EmojiFinder, ImageFinder
import config

cache.setup(f"redis://{RedisConfig.host}:{RedisConfig.port}/{RedisConfig.db}")


class Marly(AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=self.get_prefix,
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            help_command=None,
            activity=CustomActivity(
                name=f"🔗 marly.bot/discord",
            ),
            intents=Intents.all(),
            #            shard_count=3,
            mobile_status=True,
            case_insensitive=True,
            owner_ids=BotConfig.OWNER_ID,
            status=Status.idle,
        )
        self.version = "v/0.0.1"
        self.uptime = utcnow()
        self.uptime2 = time.time()
        self.color = BotConfig.COLOR
        self.db = Database()
        self.redis = None
        self.process = Process()

    async def start(self) -> None:
        await super().start(BotConfig.BOT_TOKEN, reconnect=True)

    async def get_prefix(self, message: Message):
        if not message.guild:
            return BotConfig.PREFIX

        settings = await Settings.fetch(self, message.guild)
        user_prefix = await settings.fetch_user_prefix(message.author.id)
        prefixes = filter(None, [user_prefix, settings.prefix, BotConfig.PREFIX])
        return when_mentioned_or(*prefixes)(self, message)

    async def get_context(self, origin: Message, *, cls=None) -> Context:
        context = await super().get_context(
            origin,
            cls=cls or Context,
        )
        if context.guild:
            context.settings = await Settings.fetch(self, context.guild)
        return context

    async def load_patches(self) -> None:
        patch_files = glob.glob("system/patch/**/*.py", recursive=True)

        for file in patch_files:
            if file.endswith("__init__.py"):
                continue
            module_name = file.replace(".py", "").replace("/", ".")

            try:
                importlib.import_module(module_name)
                log.info(f"Patched: {module_name}")
            except Exception as e:
                log.error(f"Error importing {module_name}: {e}")

    async def setup_hook(self) -> None:
        await self.db.connect()
        self.browser = BrowserHandler()
        await self.browser.init()
        self.session = ClientSession()
        self.add_check(self.blacklisted)
        self.add_check(self.disabled_check)
        await self.load_patches()
        await self.load_extension("jishaku")
        self.redis = await Redis.from_url()

        for extension in [
            ".".join(feature.parts)
            for feature in Path("extensions").iterdir()
            if feature.is_dir() and (feature / "__init__.py").is_file()
        ]:
            try:
                await self.load_extension(extension)
                log.info(f"Loaded extension: {extension}")
            except Exception as e:
                log.error(f"Failed to load extension {extension}: {e}")

    async def blacklisted(self, ctx: Context) -> bool:
        return not await self.db.fetchrow(
            "SELECT * FROM blacklist WHERE user_id = $1", ctx.author.id
        )

    async def disabled_check(self, ctx: Context) -> bool:
        if not ctx.guild or ctx.author.guild_permissions.administrator:
            return True
        command_name = ctx.command.qualified_name
        parent_name = ctx.command.parent.qualified_name if ctx.command.parent else None

        ignored = await self.db.fetchrow(
            """
            SELECT 1 FROM commands.ignored 
            WHERE guild_id = $1 AND target_id = ANY($2::BIGINT[])
            LIMIT 1
            """,
            ctx.guild.id,
            [ctx.author.id, ctx.channel.id],
        )
        if ignored:
            return False

        disabled = await self.db.fetchrow(
            """
            SELECT 1 FROM commands.disabled 
            WHERE guild_id = $1 
            AND channel_id = $2 
            AND command = ANY($3::TEXT[])
            LIMIT 1
            """,
            ctx.guild.id,
            ctx.channel.id,
            [command_name, parent_name] if parent_name else [command_name],
        )
        if disabled:
            raise CommandError(
                f"Command `{command_name}` is disabled in {ctx.channel.mention}"
            )

        role_ids = [role.id for role in ctx.author.roles]
        restricted = await self.db.fetchrow(
            """
            SELECT command FROM commands.restricted 
            WHERE guild_id = $1
            AND command = ANY($2::TEXT[])
            AND NOT role_id = ANY($3::BIGINT[])
            LIMIT 1
            """,
            ctx.guild.id,
            [command_name, parent_name] if parent_name else [command_name],
            role_ids,
        )
        if restricted:
            cmd_name = restricted["command"]
            raise CommandError(
                f"You don't have a **permitted role** to use `{cmd_name}`"
            )

        return True

    async def connect_nodes(self) -> None:
        for _ in range(config.LAVALINK.NODE_COUNT):
            log.info(
                f"Connecting to Lavalink node at {config.LAVALINK.HOST}:{config.LAVALINK.PORT}"
            )
            try:
                await NodePool().create_node(
                    bot=self,
                    host=config.LAVALINK.HOST,
                    port=config.LAVALINK.PORT,
                    password=config.LAVALINK.PASSWORD,
                    identifier=f"MAIN{tuuid()}",
                    spotify_client_id=config.Apis.SPOTIFY.CLIENT_ID,
                    spotify_client_secret=config.Apis.SPOTIFY.CLIENT_SECRET,
                    secure=False,
                )
                log.info("Successfully connected to Lavalink node.")
            except Exception as e:
                log.error(f"Failed to connect to Lavalink node: {e}")

    async def on_command(self, ctx: Context) -> None:
        if ctx.guild:
            log.info(
                f"{ctx.author} ({ctx.author.id}) executed {ctx.command} in {ctx.guild} ({ctx.guild.id})."
            )
        else:
            log.info(f"{ctx.author} ({ctx.author.id}) executed {ctx.command} in a DM.")

    async def on_ready(self):
        log.info("Bot is ready")
        #        await self.redis.flushall()
        await self.connect_nodes()

    async def on_message(self, message: Message):
        if not self.is_ready() or not message.guild or message.author.bot:
            return
        if message.guild:
            ctx = await self.get_context(message)
            if ctx.prefix:
                content_after_prefix = message.content[len(ctx.prefix) :].strip()
                if content_after_prefix:
                    invoked_with = content_after_prefix.split()[0].lower()
                    alias = await self.db.fetchval(
                        """
                        SELECT invoke
                        FROM aliases
                        WHERE guild_id = $1 AND alias = $2
                        """,
                        message.guild.id,
                        invoked_with,
                    )
                    if alias:
                        message.content = f"{ctx.prefix}{alias} {message.content[len(ctx.prefix) + len(invoked_with):].strip()}"

        await self.process_commands(message)

    async def on_message_edit(self, before: Message, after: Message) -> None:
        if not self.is_ready() or not after.guild or after.author.bot:
            return

        if before.content != after.content:
            ctx = await self.get_context(after)
            await self.process_commands(after)

    async def on_command_error(self, ctx: Context, exception: Exception) -> None:
        ignored = (
            CommandNotFound,
            NotOwner,
            CheckFailure,
            DisabledCommand,
            UserInputError,
        )
        if type(exception) in ignored:
            return

        elif isinstance(exception, MissingRequiredArgument):
            return await ctx.send_help()

        elif isinstance(exception, CommandOnCooldown):
            return await ctx.utility(
                f" **Command** is on a `{exception.retry_after:.1f}s` **cooldown**",
                emoji=config.Emojis.Embeds.COOLDOWN,
                color=config.Color.cooldown,
                delete_after=10,
            )
        elif isinstance(exception, MissingPermissions):
            return await ctx.warn(
                f"You're **missing** permission: `{', '.join(permission for permission in exception.missing_permissions)}`"
            )
        elif isinstance(exception, BadInviteArgument):
            return await ctx.warn(
                "Invalid **invite code** provided - check and try again"
            )
        elif isinstance(exception, BadUnionArgument):
            if set(exception.converters) == {
                EmojiFinder,
                PartialEmoji,
                PartialEmojiConverter,
            }:
                return await ctx.warn(
                    f"**{ctx.current_parameter}** is not a valid emoji"
                )

        elif isinstance(exception, CommandError):
            if isinstance(exception.args, tuple) and len(exception.args) > 1:
                return await ctx.warn("\n".join(str(arg) for arg in exception.args))
            return await ctx.warn(str(exception))

    async def on_command_completion(self, ctx: Context):
        if not ctx.guild:
            return

        await self.db.execute(
            """
            INSERT INTO command_usage (guild_id, user_id, command_name, command_type)
                VALUES ($1,$2,$3,$4)
            ON CONFLICT(guild_id,user_id,command_name,command_type) DO UPDATE SET
                uses = command_usage.uses + 1
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.command.qualified_name,
            "internal",
        )
