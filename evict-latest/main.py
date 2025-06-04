import os
import psutil
import onnxruntime
import discord
import secrets
import os
import importlib
import glob
import asyncpg
import time
import jishaku
import jishaku.flags
import config
import asyncio
import discord_ios
import psutil

from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from pomice import NodePool
from collections.abc import Mapping
from typing import Any, Collection, Dict, Optional, cast
from humanfriendly import format_timespan
from colorama import Fore, Style
from aiohttp import ClientSession, TCPConnector
from asyncpraw import Reddit as RedditClient
from cashews import cache
from collections import defaultdict
from multiprocessing import Pool, cpu_count
from datetime import datetime, timedelta, timezone
from typing import List

from managers.backup import BackupManager
from managers.parser.TagScript.exceptions import EmbedParseError, TagScriptError

from core.client import database
from core.client.browser import BrowserHandler
from core.client.context import Context, Redis
from core.client import logging
from core.client.database import Database, Settings
from core.client.help import EvictHelp

from cogs.config.extended.roles.dynamicrolebutton import DynamicRoleButton
from cogs.config.extended.ticket.ticket import DeleteTicket

from tools.conversion.embed1 import EmbedScript
from tools.formatter import human_join, plural

from processors.backup import run_pg_dump
from processors.listeners import process_guild_data, process_jail_permissions, process_add_role
from processors.backup import process_bunny_upload
from processors.image_generation import process_image_effect

from discord.ext import commands
from discord.message import Message
from discord.utils import utcnow
from discord.http import Route

from discord import (
    AllowedMentions,
    AuditLogEntry,
    ChannelType,
    ClientUser,
    Forbidden,
    Guild,
    HTTPException,
    Intents,
    Interaction,
    Invite,
    Member,
    MessageType,
    NotFound,
    PartialMessageable,
    StageChannel,
    TextChannel,
    User,
    VoiceState,
    Activity,
    ActivityType,
)

from discord.ext.commands import (
    BadFlagArgument,
    BadInviteArgument,
    BadLiteralArgument,
    BadUnionArgument,
    BucketType,
    ChannelNotFound,
    CheckFailure,
    CommandError,
    CommandInvokeError,
    CommandNotFound,
    CommandOnCooldown,
    CooldownMapping,
    DisabledCommand,
    FlagError,
    MaxConcurrencyReached,
    MemberNotFound,
    MessageNotFound,
    MissingFlagArgument,
    MissingPermissions,
    MissingRequiredArgument,
    MissingRequiredAttachment,
    MissingRequiredFlag,
    NSFWChannelRequired,
    NotOwner,
    RangeError,
    RoleNotFound,
    TooManyFlags,
    UserNotFound,
    when_mentioned_or,
)

async def getprefix(bot, message):
    """
    Utility function to get the bot prefix.
    """
    if not message.guild:
        return ";"

    check = await bot.db.fetchrow(
        """
        SELECT * FROM 
        selfprefix WHERE 
        user_id = $1
        """, 
        message.author.id
    )
    if check:
        selfprefix = check["prefix"]

    res = await bot.db.fetchrow(
        """
        SELECT * FROM 
        prefix WHERE 
        guild_id = $1
        """, 
        message.guild.id
    )
    if res:
        guildprefix = res["prefix"]

    else:
        guildprefix = ";"

    if not check and res:
        selfprefix = res["prefix"]
    
    elif not check and not res:
        selfprefix = ";"

    return guildprefix, selfprefix

cache.setup("mem://")

Mapping.register(asyncpg.Record)

jishaku.Flags.HIDE = True
jishaku.Flags.RETAIN = True
jishaku.Flags.NO_DM_TRACEBACK = True
jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.FORCE_PAGINATOR = True

log = logging.getLogger(__name__)

logical_cpu_count = psutil.cpu_count(logical=False)  

os.environ["OMP_NUM_THREADS"] = str(logical_cpu_count)
os.environ["ONNXRUNTIME_THREAD_COUNT"] = str(logical_cpu_count)
os.environ["OMP_WAIT_POLICY"] = "PASSIVE"
os.environ["OMP_PROC_BIND"] = "CLOSE"  
os.environ["OMP_PLACES"] = "cores"
os.environ["KMP_AFFINITY"] = "granularity=fine,compact,1,0"
os.environ["OPENBLAS_NUM_THREADS"] = str(logical_cpu_count)
os.environ["MKL_NUM_THREADS"] = str(logical_cpu_count)
os.environ["VECLIB_MAXIMUM_THREADS"] = str(logical_cpu_count)
os.environ["NUMEXPR_NUM_THREADS"] = str(logical_cpu_count)
os.environ["ONNXRUNTIME_DISABLE_THREAD_AFFINITY"] = "1"
os.environ["OMP_SCHEDULE"] = "static"
os.environ["KMP_BLOCKTIME"] = "0"
os.environ["KMP_SETTINGS"] = "0"

onnxruntime.set_default_logger_severity(3)
sess_options = onnxruntime.SessionOptions()
sess_options.intra_op_num_threads = logical_cpu_count
sess_options.inter_op_num_threads = logical_cpu_count
sess_options.execution_mode = onnxruntime.ExecutionMode.ORT_SEQUENTIAL
sess_options.enable_cpu_mem_arena = False
sess_options.enable_mem_pattern = False
sess_options.graph_optimization_level = onnxruntime.GraphOptimizationLevel.ORT_DISABLE_ALL

class MonitoredHTTPClient(discord.http.HTTPClient):
    """
    Custom HTTP client that monitors API calls.
    """
    def __init__(self, session, *, bot=None):
        """
        Custom HTTP client that monitors API calls.
        """
        super().__init__(session) 
        self.bot = bot
        self._global_over = asyncio.Event()
        self._global_over.set()
        
        if not hasattr(self.bot, 'api_stats'):
            self.bot.api_stats = defaultdict(lambda: {
                'calls': 0,
                'errors': 0,
                'total_time': 0,
                'rate_limits': 0
            })
        if not hasattr(self.bot, '_last_stats_cleanup'):
            self.bot._last_stats_cleanup = time.time()

    async def request(self, route: Route, **kwargs) -> Any:
        """
        Request a route and monitor the response.
        """
        method = route.method
        path = route.path
        endpoint = f"{method} {path}"
        
        start_time = time.time()
        try:
            response = await super().request(route, **kwargs)
            elapsed = time.time() - start_time
            
            self.bot.api_stats[endpoint]['calls'] += 1
            self.bot.api_stats[endpoint]['total_time'] += elapsed
            
            if time.time() - self.bot._last_stats_cleanup > 3600:
                self.bot.api_stats.clear()
                self.bot._last_stats_cleanup = time.time()
                
            return response
            
        except discord.HTTPException as e:
            self.bot.api_stats[endpoint]['errors'] += 1
            if e.status == 429:
                self.bot.api_stats[endpoint]['rate_limits'] += 1
            raise


class Evict(commands.AutoShardedBot):
    """
    Custom bot class that extends the AutoShardedBot.
    """
    session: ClientSession
    uptime: datetime
    traceback: Dict[str, Exception]
    global_cooldown: CooldownMapping
    owner_ids: Collection[int]
    database: Database
    redis: Redis
    user: ClientUser
    reddit: RedditClient
    version: str = "3.0"
    user_agent: str = f"Evict (DISCORD BOT/{version})"
    browser: BrowserHandler
    voice_join_times = {}
    voice_update_task = None
    start_time: float
    system_stats: defaultdict
    process: psutil.Process
    _last_system_check: float
    _is_ready: asyncio.Event

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            intents=Intents(
                guilds=True,
                members=True,
                messages=True,
                reactions=True,
                presences=True,
                moderation=True,
                voice_states=True,
                message_content=True,
                emojis_and_stickers=True,
            ),
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            shard_count=9,
            command_prefix=getprefix,
            help_command=EvictHelp(),
            case_insensitive=True,
            max_messages=1500,
            activity=Activity(
                type=ActivityType.streaming,
                name="🔗 discord.gg/evict",
                url=f"{config.CLIENT.TWITCH_URL}",
            ),
        )
        
        self.traceback = {}
        self.global_cooldown = CooldownMapping.from_cooldown(2, 3, BucketType.user)
        self.add_check(self.check_global_cooldown)
        self.uptime2 = time.time()
        self.embed_build = EmbedScript()
        self.cache = cache(self)
        self.process_pool = Pool(
            processes=min(4, logical_cpu_count),
            maxtasksperchild=100  
        )

        self.guild_ratelimit_10s = CooldownMapping.from_cooldown(
            config.RATELIMITS.PER_10S, 10, BucketType.guild
        )
        self.guild_ratelimit_30s = CooldownMapping.from_cooldown(
            config.RATELIMITS.PER_30S, 30, BucketType.guild
        )
        self.guild_ratelimit_1m = CooldownMapping.from_cooldown(
            config.RATELIMITS.PER_1M, 60, BucketType.guild
        )

        self.start_time = time.time()
        self.system_stats = defaultdict(list)
        self.process = psutil.Process()
        self._last_system_check = 0
        self.command_stats = defaultdict(lambda: {'calls': 0, 'total_time': 0})
        self._is_ready = asyncio.Event()

    @property
    def db(self) -> Database:
        """
        Convenience property to access the database.
        """
        return self.database

    @property
    def owner(self) -> User:
        """
        Convenience property to access the bot owner.
        """
        return self.get_user(self.owner_ids[0])  # type: ignore

    def get_message(self, message_id: int) -> Optional[Message]:
        """
        Fetch a message from the cache.
        """
        return self._connection._get_message(message_id)

    async def get_or_fetch_user(self, user_id: int) -> User:
        """
        Fetch a user from the cache or fetch it from the API.
        """
        return self.get_user(user_id) or await self.fetch_user(user_id)

    def run(self) -> None:
        """
        Custom run method that starts the bot.
        """
        log.info("Starting the bot...")

        super().run(
            config.DISCORD.TOKEN,
            reconnect=True,
            log_handler=None,
        )

    async def close(self) -> None:
        """
        Custom close method that cleans up resources.
        """
        try:
            if self.voice_update_task:
                self.voice_update_task.cancel()
                
            if hasattr(self, 'browser'):
                await self.browser.cleanup()
                
            if hasattr(self, 'session'):
                await self.session.close()
            
            if hasattr(self, 'process_pool'):
                self.process_pool.close()
                self.process_pool.join()
                
            await super().close()
            
        except Exception as e:
            log.error(f"Error during shutdown: {e}")
            raise

    async def on_ready(self) -> None:
        """
        Custom on_ready method that performs additional setup.
        """
        if not self._is_ready.is_set():
            self._is_ready.set()
            log.info("Bot is ready, performing final setup...")

        try:
            log.info(
                f"Connected as {Fore.LIGHTCYAN_EX}{Style.BRIGHT}{self.user}{Fore.RESET} ({Fore.LIGHTRED_EX}{self.user.id}{Fore.RESET})."
            )
            self.uptime = utcnow()
            
            await self.wait_until_ready()
            log.info("Loading extensions...")
            await self.load_extensions()
            log.info("Connecting to nodes...")
            await self.connect_nodes()
            log.info("Bot is fully operational!")

        except Exception as e:
            log.error(f"Error in on_ready: {e}", exc_info=True)

    async def on_command(self, ctx: Context) -> None:
        """
        Custom on_command method that logs command usage.
        """
        if not ctx.guild:
            return

        if not ctx.command: 
            custom_command = await self.db.fetchrow(
                """
                SELECT word 
                FROM stats.custom_commands 
                WHERE guild_id = $1 AND command = $2
                """,
                ctx.guild.id,
                ctx.invoked_with.lower()
            )
            
            if custom_command:
                ctx.command = type('CustomCommand', (), {
                    'qualified_name': f"wordstats_{ctx.invoked_with}",
                    'cog_name': "Utility"
                })
            else:
                return 
            
        await self.db.execute(
            """
            INSERT INTO statistics.daily 
                (guild_id, date, member_id, messages_sent)
            VALUES 
                ($1, CURRENT_DATE, $2, 0)
            ON CONFLICT (guild_id, date, member_id) DO UPDATE SET 
                messages_sent = statistics.daily.messages_sent
            """,
            ctx.guild.id,
            ctx.author.id
        )

        await self.db.execute(
            """
            INSERT INTO invoke_history.commands 
            (guild_id, user_id, command_name, category, timestamp)
            VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
            """,
            ctx.guild.id,
            ctx.author.id,
            ctx.command.qualified_name,
            ctx.command.cog_name or "No Category",
        )

        start_time = time.time()
        command_name = ctx.command.qualified_name
        
        try:
            log.info(
                "%s (%s) used %s in %s (%s)",
                ctx.author.name,
                ctx.author.id,
                ctx.command.qualified_name,
                ctx.guild.name,
                ctx.guild.id,
            )
        finally:
            elapsed = time.time() - start_time
            if not hasattr(self, 'command_stats'):
                self.command_stats = defaultdict(lambda: {'calls': 0, 'total_time': 0})
                
            self.command_stats[command_name]['calls'] += 1
            self.command_stats[command_name]['total_time'] += elapsed

    async def on_shard_ready(self, shard_id: int) -> None:
        """
        Custom on_shard_ready method that logs shard status.
        """
        log.info(f"Shard {shard_id} is ready, starting post-connection setup...")

        try:
            log.info(
                f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTGREEN_EX}spawned{Fore.RESET}."
            )
            
            if shard_id == self.shard_count - 1:
                log.info("All shards connected, waiting for full ready state...")
                
        except Exception as e:
            log.error(f"Error in on_shard_ready for shard {shard_id}: {e}", exc_info=True)

    async def on_shard_resumed(self, shard_id: int) -> None:
        """
        Custom on_shard_resumed method that logs shard status.
        """
        log.info(
            f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTYELLOW_EX}resumed{Fore.RESET}."
        )

    async def setup_hook(self) -> None:
        """
        Custom setup hook that initializes additional resources.
        """
        log.info("Starting setup hook...")
        try:
            self.session = ClientSession(
                headers={"User-Agent": self.user_agent},
                connector=TCPConnector(ssl=False),
            )
            log.info("Created client session")

            self._http = MonitoredHTTPClient(
                self.http._HTTPClient__session,
                bot=self
            )
            log.info("Initialized monitored HTTP client")

            self.add_dynamic_items(DynamicRoleButton)
            self.add_view(DeleteTicket())
            log.info("Added dynamic views")

            self.database = await database.connect()
            log.info("Connected to database")

            self.redis = await Redis.from_url()
            log.info("Connected to Redis")

            await self.load_patches()
            log.info("Loaded patches")

            self.start_time = time.time()
            self.system_stats = defaultdict(list)
            self.process = psutil.Process()
            self._last_system_check = 0
            self.command_stats = defaultdict(lambda: {'calls': 0, 'total_time': 0})
            log.info("Initialized monitoring systems")

            self.browser = BrowserHandler()
            await self.browser.init()
            log.info("Initialized browser")

            self.voice_update_task = self.loop.create_task(self.update_voice_times())
            log.info("Started voice update task")
            
            # self.backup_manager = BackupManager(self)
            # self.backup_task = self.loop.create_task(self._backup_task())
            # log.info("Started backup manager")

            for guild in self.guilds:
                for vc in guild.voice_channels:
                    for member in vc.members:
                        if not member.bot:
                            self.voice_join_times[member.id] = time.time()
            
            log.info("Initialized voice times")
            log.info("Setup complete!")

        except Exception as e:
            log.error(f"Error in setup_hook: {e}", exc_info=True)
            raise

    async def connect_nodes(self) -> None:
        for _ in range(config.LAVALINK.NODE_COUNT):
            identifier = "evict"
            try:
                await NodePool().create_node(
                    bot=self,  # type: ignore
                    host=config.LAVALINK.HOST,
                    port=config.LAVALINK.PORT,
                    password="youshallnotpass",
                    secure=False,
                    identifier=identifier,
                    spotify_client_id=config.Authorization.SPOTIFY.CLIENT_ID,
                    spotify_client_secret=config.Authorization.SPOTIFY.CLIENT_SECRET,
                )
                log.info(f"Successfully connected to node {identifier}")
            except Exception as e:
                log.error(f"Failed to connect to node {identifier}: {e}")

    async def connect_nodes(self) -> None:
        for _ in range(config.LAVALINK.NODE_COUNT):
            identifier = "evict"
            try:
                await NodePool().create_node(
                    bot=self,  # type: ignore
                    host="127.0.0.1",
                    port=config.LAVALINK.PORT,
                    password=config.LAVALINK.PASSWORD,
                    secure=False,
                    identifier=identifier,
                    spotify_client_id=config.AUTHORIZATION.SPOTIFY.CLIENT_ID,
                    spotify_client_secret=config.AUTHORIZATION.SPOTIFY.CLIENT_SECRET,
                )
                log.info(f"Successfully connected to node {identifier}")
            except Exception as e:
                log.error(f"Failed to connect to node {identifier}: {e}")

    async def load_extensions(self) -> None:
        """
        Load all extensions in the cogs directory.
        """
        await self.load_extension("jishaku")
        for feature in Path("cogs").iterdir():
            if feature.is_dir() and (feature / "__init__.py").is_file():
                try:
                    await self.load_extension(".".join(feature.parts))
                except Exception as exc:
                    log.exception(
                        f"Failed to load extension {feature.name}.", exc_info=exc
                    )

    async def load_patches(self) -> None:
        """
        Load all patches in the managers directory.
        """
        for module in glob.glob("managers/patches/**/*.py", recursive=True):
            if module.endswith("__init__.py"):
                continue
            module_name = (
                module.replace(os.path.sep, ".").replace("/", ".").replace(".py", "")
            )
            try:
                importlib.import_module(module_name)
                log.info(f"Patched: {module}")
            except (ModuleNotFoundError, ImportError) as e:
                log.error(f"Error importing {module_name}: {e}")

    async def log_traceback(self, ctx: Context, exc: Exception) -> Message:
        """
        Store an Exception in memory.
        This is used for future reference.
        """
        log.exception(
            "Unexpected exception occurred in %s.",
            ctx.command.qualified_name,
            exc_info=exc,
        )

        key = secrets.token_urlsafe(54)
        self.traceback[key] = exc

        return await ctx.warn(
            f"Command `{ctx.command.qualified_name}` raised an exception. Please try again later.",
            content=f"`{key}`",
        )

    async def on_command_error(self, ctx: Context, exc: CommandError) -> Any:
        """
        Custom on_command_error method that handles command errors.
        """
        if not ctx.channel:
            return
            
        if not ctx.guild:
            can_send = True
        else:
            can_send = (
                ctx.channel.permissions_for(ctx.guild.me).send_messages
                and ctx.channel.permissions_for(ctx.guild.me).embed_links
            )

        if not can_send:
            return

        if isinstance(
            exc,
            (
                CommandNotFound,
                DisabledCommand,
                NotOwner,
            ),
        ):
            return

        elif isinstance(
            exc,
            (
                MissingRequiredArgument,
                MissingRequiredAttachment,
                BadLiteralArgument,
            ),
        ):
            return await ctx.send_help(ctx.command)

        elif isinstance(exc, TagScriptError):
            if isinstance(exc, EmbedParseError):
                return await ctx.warn(
                    "Something is wrong with your **script**!",
                    *exc.args,
                )

        elif isinstance(exc, FlagError):
            if isinstance(exc, TooManyFlags):
                return await ctx.warn(
                    f"You specified the **{exc.flag.name}** flag more than once!"
                )

            elif isinstance(exc, BadFlagArgument):
                try:
                    annotation = exc.flag.annotation.__name__
                except AttributeError:
                    annotation = exc.flag.annotation.__class__.__name__

                return await ctx.warn(
                    f"Failed to cast **{exc.flag.name}** to `{annotation}`!",
                    *(
                        [
                            "Make sure you provide **on** or **off** for `Status` flags!",
                        ]
                        if annotation == "Status"
                        else []
                    ),
                )

            elif isinstance(exc, MissingRequiredFlag):
                return await ctx.warn(f"You must specify the **{exc.flag.name}** flag!")

            elif isinstance(exc, MissingFlagArgument):
                return await ctx.warn(
                    f"You must specify a value for the **{exc.flag.name}** flag!"
                )

        if isinstance(exc, CommandInvokeError):
            return await ctx.warn(exc.original)

        elif isinstance(exc, MaxConcurrencyReached):
            if ctx.command.qualified_name in ("lastfm set", "lastfm index"):
                return

            return await ctx.warn(
                f"This command can only be used **{plural(exc.number):time}**"
                f" per **{exc.per.name}** concurrently!",
                delete_after=5,
            )

        elif isinstance(exc, CommandOnCooldown):
            if exc.retry_after > 30:
                return await ctx.warn(
                    "This command is currently on cooldown!",
                    f"Try again in **{format_timespan(exc.retry_after)}**",
                )

            return await ctx.message.add_reaction("⏰")

        elif isinstance(exc, BadUnionArgument):
            if exc.converters == (Member, User):
                return await ctx.warn(
                    f"No **{exc.param.name}** was found matching **{ctx.current_argument}**!",
                    "If the user is not in this server, try using their **ID** instead",
                )

            elif exc.converters == (Guild, Invite):
                return await ctx.warn(
                    f"No server was found matching **{ctx.current_argument}**!",
                )

            else:
                return await ctx.warn(
                    f"Casting **{exc.param.name}** to {human_join([f'`{c.__name__}`' for c in exc.converters])} failed!",
                )

        elif isinstance(exc, MemberNotFound):
            return await ctx.warn(
                f"No **member** was found matching **{exc.argument}**!"
            )

        elif isinstance(exc, UserNotFound):
            return await ctx.warn(f"No **user** was found matching `{exc.argument}`!")

        elif isinstance(exc, RoleNotFound):
            return await ctx.warn(f"No **role** was found matching **{exc.argument}**!")

        elif isinstance(exc, ChannelNotFound):
            return await ctx.warn(
                f"No **channel** was found matching **{exc.argument}**!"
            )

        elif isinstance(exc, BadInviteArgument):
            return await ctx.warn("Invalid **invite code** provided!")

        elif isinstance(exc, MessageNotFound):
            return await ctx.warn(
                "The provided **message** was not found!",
                "Try using the **message URL** instead",
            )

        elif isinstance(exc, RangeError):
            label = ""
            if exc.minimum is None and exc.maximum is not None:
                label = f"no more than `{exc.maximum}`"
            elif exc.minimum is not None and exc.maximum is None:
                label = f"no less than `{exc.minimum}`"
            elif exc.maximum is not None and exc.minimum is not None:
                label = f"between `{exc.minimum}` and `{exc.maximum}`"

            if label and isinstance(exc.value, str):
                label += " characters"

            return await ctx.warn(f"The input must be {label}!")

        elif isinstance(exc, MissingPermissions):
            permissions = human_join(
                [f"`{permission}`" for permission in exc.missing_permissions],
                final="and",
            )
            _plural = "s" if len(exc.missing_permissions) > 1 else ""

            return await ctx.warn(
                f"You're missing the {permissions} permission{_plural}!"
            )
        
        elif isinstance(exc, NSFWChannelRequired):
            return await ctx.warn(
            "This command can only be used in NSFW channels!"
            )

        elif isinstance(exc, CommandError):
            if isinstance(exc, (HTTPException, NotFound)) and not isinstance(exc, (CheckFailure, Forbidden)):
                if "Unknown Channel" in exc.text:
                    return
                return await ctx.warn(exc.text.capitalize())
            
            if isinstance(exc, (Forbidden, CommandInvokeError)):
                error = exc.original if isinstance(exc, CommandInvokeError) else exc
                
                if isinstance(error, Forbidden):
                    perms = ctx.guild.me.guild_permissions
                    missing_perms = []
                    
                    if not perms.manage_channels:
                        missing_perms.append('`manage_channels`')
                    if not perms.manage_roles:
                        missing_perms.append('`manage_roles`')
                        
                    error_msg = (
                        f"I'm missing the following permissions: {', '.join(missing_perms)}\n"
                        if missing_perms else
                        "I'm missing required permissions. Please check my role's permissions and position.\n"
                    )
                    
                    return await ctx.warn(
                        error_msg,
                        f"Error: {str(error)}"
                    )
                    
                return await ctx.warn(str(error))

            origin = getattr(exc, "original", exc)
            with suppress(TypeError):
                if any(
                    forbidden in origin.args[-1]
                    for forbidden in (
                        "global check",
                        "check functions",
                        "Unknown Channel",
                    )
                ):
                    return

            return await ctx.warn(*origin.args)

        else:
            return await ctx.send_help(ctx.command)

    async def get_context(
        self,
        origin: Message | Interaction,
        /,
        *,
        cls=Context,
    ) -> Context:
        """
        Custom get_context method that adds additional attributes.
        """
        context = await super().get_context(origin, cls=cls)
        if context.guild: 
            context.settings = await Settings.fetch(self, context.guild)
        else:
            context.settings = None  

        return context

    async def check_global_cooldown(self, ctx: Context) -> bool:
        """
        Check the global cooldown for the bot.
        """
        if ctx.author.id in self.owner_ids:
            return True

        bucket = self.global_cooldown.get_bucket(ctx.message)
        if bucket:
            retry_after = bucket.update_rate_limit()
            if retry_after:
                raise CommandOnCooldown(bucket, retry_after, BucketType.user)

        return True

    async def process_commands(self, message: Message) -> None:
        """
        Custom process_commands method that handles command processing.
        """
        if message.author.bot:
            return

        blacklisted = cast(
            bool,
            await self.db.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1
                    FROM blacklist
                    WHERE user_id = $1
                )
                """,
                message.author.id,
            ),
        )
        if blacklisted:
            return

        if message.guild:
            channel = message.channel
            if not (
                channel.permissions_for(message.guild.me).send_messages
                and channel.permissions_for(message.guild.me).embed_links
                and channel.permissions_for(message.guild.me).attach_files
            ):
                return

        ctx = await self.get_context(message)

        if not ctx.valid and message.content.startswith(ctx.clean_prefix):
            try:
                command = message.content[len(ctx.clean_prefix):].strip().split()[0].lower()
                utility_cog = self.get_cog("Utility")
                if utility_cog:
                    result = await utility_cog.process_custom_command(ctx, command)
                    if result:
                        return
            except IndexError: 
                return
                
        if (
            ctx.invoked_with
            and isinstance(message.channel, PartialMessageable)
            and message.channel.type != ChannelType.private
        ):
            log.warning(
                "Discarded a command message (ID: %s) with PartialMessageable channel: %r.",
                message.id,
                message.channel,
            )
        else:
            await self.invoke(ctx)

        if not ctx.valid:
            self.dispatch("message_without_command", ctx)

    async def on_message(self, message: Message) -> None:
        """
        Custom on_message method that handles message processing.
        """
        if message.guild and not message.author.bot:
            if not await self.check_guild_ratelimit(message):
                return
                
            await self.db.execute(
                """
                INSERT INTO statistics.daily 
                    (guild_id, date, member_id, messages_sent)
                VALUES 
                    ($1, CURRENT_DATE, $2, 1)
                ON CONFLICT (guild_id, date, member_id) DO UPDATE SET 
                    messages_sent = statistics.daily.messages_sent + 1
                """,
                message.guild.id,
                message.author.id
            )
            
            await self.db.execute(
                """
                INSERT INTO statistics.daily_channels 
                    (guild_id, channel_id, date, messages_sent)
                VALUES 
                    ($1, $2, CURRENT_DATE, 1)
                ON CONFLICT (guild_id, channel_id, date) DO UPDATE SET 
                    messages_sent = statistics.daily_channels.messages_sent + 1
                """,
                message.guild.id,
                message.channel.id
            )

        if (
            message.guild
            and message.guild.system_channel_flags.premium_subscriptions
            and message.type in (
                MessageType.premium_guild_subscription,
                MessageType.premium_guild_tier_1,
                MessageType.premium_guild_tier_2,
                MessageType.premium_guild_tier_3,
            )
        ):
            self.dispatch("member_boost", message.author)

        return await super().on_message(message)

    async def on_message_edit(self, before: Message, after: Message) -> None:
        """
        Custom on_message_edit method that handles message edits.
        """
        self.dispatch("member_activity", after.channel, after.author)
        if before.content == after.content:
            return

        if after.guild and not after.author.bot:
            if not await self.check_guild_ratelimit(after):
                return

        return await self.process_commands(after)

    async def on_typing(
        self,
        channel: TextChannel,
        user: Member | User,
        when: datetime,
    ) -> None:
        """
        Custom on_typing method that handles typing events.
        """
        if isinstance(user, Member):
            self.dispatch("member_activity", channel, user)

    async def on_member_update(self, before: Member, after: Member) -> None:
        """
        Custom on_member_update method that handles member updates.
        """
        if after.guild.system_channel_flags.premium_subscriptions:
            return

        if not before.premium_since and after.premium_since:
            self.dispatch("member_boost", after)

        elif before.premium_since and not after.premium_since:
            self.dispatch("member_unboost", before)

    async def on_member_remove(self, member: Member) -> None:
        """
        Custom on_member_remove method that handles member removals.
        """
        if member == self.user:
            return

        if member.premium_since:
            self.dispatch("member_unboost", member)

    async def on_voice_state_update(
        self,
        member: Member,
        before: VoiceState,
        after: VoiceState,
    ):
        """
        Make sure the bot is a Stage Channel speaker.
        """
        if member.bot:
            if (
                member == self.user
                and after.suppress
                and after.channel
                and before.channel != after.channel
                and isinstance(after.channel, StageChannel)
            ):
                with suppress(HTTPException):
                    await member.edit(suppress=False)
            return

        if before.channel is None and after.channel is not None:
            self.voice_join_times[member.id] = time.time()

        elif before.channel is not None and after.channel is None:
            self.voice_join_times.pop(member.id, None)

    async def on_audit_log_entry_create(self, entry: AuditLogEntry):
        """
        Custom on_audit_log_entry_create method that dispatches events.
        """
        if not self.is_ready():
            return

        event = f"audit_log_entry_{entry.action.name}"
        self.dispatch(event, entry)

    async def notify(self, guild: Guild, *args, **kwargs) -> Optional[Message]:
        """
        Send a message to the first available channel.
        """
        if (
            guild.system_channel
            and guild.system_channel.permissions_for(guild.me).send_messages
        ):
            try:
                return await guild.system_channel.send(*args, **kwargs)
            except HTTPException:
                return

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                try:
                    return await channel.send(*args, **kwargs)
                except HTTPException:
                    break

    async def update_voice_times(self):
        """
        Calculate voice minutes for each guild.
        """
        await self.wait_until_ready()
        while not self.is_closed():
            current_time = time.time()
            
            voice_stats = {}  
            member_updates = {}
            
            for guild in self.guilds:
                total_minutes = 0
                
                for vc in guild.voice_channels:
                    for member in vc.members:
                        if member.bot:
                            continue
                            
                        if member.id not in self.voice_join_times:
                            member_updates[member.id] = current_time
                            continue
                            
                        join_time = self.voice_join_times[member.id]
                        minutes = int((current_time - join_time) / 60)
                        
                        if minutes > 0:
                            total_minutes += minutes
                            member_updates[member.id] = current_time
                
                if total_minutes > 0:
                    voice_stats[guild.id] = total_minutes
            
            self.voice_join_times.update(member_updates)
            
            if voice_stats:
                query = """
                INSERT INTO statistics.daily (guild_id, date, voice_minutes)
                VALUES 
                    {placeholders}
                ON CONFLICT (guild_id, date) 
                DO UPDATE SET voice_minutes = statistics.daily.voice_minutes + EXCLUDED.voice_minutes
                """
                
                values = []
                placeholders = []
                for i, (guild_id, minutes) in enumerate(voice_stats.items()):
                    values.extend([guild_id, minutes])
                    placeholders.append(f"(${i*2 + 1}, CURRENT_DATE, ${i*2 + 2})")
                
                await self.db.execute(
                    query.format(placeholders=','.join(placeholders)),
                    *values
                )
            
            await asyncio.sleep(30)

    async def check_guild_ratelimit(self, message) -> bool:
        """
        Check the guild ratelimits for the bot.
        """
        if not message.guild:
            return True
            
        bucket_10s = self.guild_ratelimit_10s.get_bucket(message)
        bucket_30s = self.guild_ratelimit_30s.get_bucket(message) 
        bucket_1m = self.guild_ratelimit_1m.get_bucket(message)

        retry_after = bucket_10s.update_rate_limit() or bucket_30s.update_rate_limit() or bucket_1m.update_rate_limit()
        
        return not bool(retry_after)

    async def update_system_stats(self):
        """
        Update system stats every minute.
        """
        current_time = time.time()
        if current_time - self._last_system_check < 60:  
            return
            
        try:
            stats = {
                'timestamp': current_time,
                'cpu_percent': self.process.cpu_percent(),
                'memory_percent': self.process.memory_percent(),
                'memory_rss': self.process.memory_info().rss,
                'threads': self.process.num_threads(),
                'handles': self.process.num_handles() if hasattr(self.process, 'num_handles') else 0,
                'commands_rate': len(self._connection._commands) / (current_time - self.start_time)
            }
            
            self.system_stats['metrics'].append(stats)
            while len(self.system_stats['metrics']) > 60:
                self.system_stats['metrics'].pop(0)
                
            self._last_system_check = current_time
            
        except Exception as e:
            log.error(f"Failed to update system stats: {e}")

    async def _backup_task(self):
        """
        Run backups every 8 hours.
        """
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                now = datetime.now(timezone.utc)
                next_run = now.replace(minute=35, second=0, microsecond=0)
                while next_run <= now:
                    next_run += timedelta(hours=8)
                
                await asyncio.sleep((next_run - now).total_seconds())
                
                if await self.backup_manager.run_backup():
                    log.info("8-hour backup completed successfully")
                else:
                    log.error("8-hour backup failed")
                    
            except Exception as e:
                log.error(f"Error in backup task: {e}")
                await asyncio.sleep(300) 

    async def process_image(self, buffer, effect_type, **kwargs):
        """
        Wrapper for asynchronous image processing using to_thread.
        """
        try:
            return await asyncio.to_thread(process_image_effect, buffer, effect_type, **kwargs)
        except Exception as e:
            log.error(f"Image processing error: {e}")
            raise

    async def process_data(self, process_type: str, *args, **kwargs):
        """
        Wrapper for process pool execution of data processing tasks.
        """        
        processors_map = {
            'guild_data': process_guild_data,
            'jail_permissions': process_jail_permissions,
            'add_role': process_add_role,
            'upload_bunny': process_bunny_upload
        }
        
        try:
            return await self.loop.run_in_executor(
                None,
                self.process_pool.apply,
                processors_map[process_type],
                args,
                kwargs
            )
        except Exception as e:
            log.error(f"Data processing error: {e}")
            raise

    async def process_backup(self, command: str):
        """
        Wrapper for process pool execution of backup tasks.
        """
        try:
            return await self.loop.run_in_executor(
                None,
                self.process_pool.apply,
                run_pg_dump,
                (command,),
                {}
            )
        finally:
            if hasattr(self, 'process_pool'):
                self.process_pool._maintain_pool()

if __name__ == "__main__":
    bot = Evict(
        description=config.CLIENT.DESCRIPTION,
        owner_ids=config.CLIENT.OWNER_IDS,
    )
    bot.run()