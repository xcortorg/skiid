import string
import random
import os
import orjson
import dotenv
import asyncio
import asyncpg
import logging
import discord
import datetime
import json
import aiohttp
import discord_android
import humanize
import httpx

from io import BytesIO
from copy import copy
from time import time
from typing import Any, List, Optional, Set
from pathlib import Path

from num2words import num2words
from loguru import logger
from humanize import precisedelta

from discord import NotFound, Forbidden
from discord.ext import commands

from modules import helpers, config
from modules.styles import emojis, colors
from modules.misc import utils
# from modules.handlers.twitch import TwitchHelper
from modules.handlers.social import SocialHelper
from modules.checks import func
from modules.misc.misc import Misc
from .misc.tasks import oneminute_loop, fiveminutes_loop, tenminutes_loop
from .misc.session import Session
from .helpers import EvelinaContext, EvelinaHelp, guild_perms, CustomInteraction, Cache, EvelinaContext, EvelinaHelp
from .measures import AntiraidMeasures, AntinukeMeasures, LevelingMeasures, ManageMeasures, LoggingMeasures
from .handlers.embed import EmbedScript
from .handlers.s3 import S3Handler
from .persistent.vm import VoiceMasterView
from .persistent.tickets import TicketButtonView, DeleteTicketRequestView
from .persistent.giveaway import GiveawayView, GiveawayEndedView
from .persistent.suggestion import SuggestionView
from .persistent.pagination import PaginationView
from .persistent.checkout import PaypalView, PaysafecardView, LTCView, BTCView, ETHView, USDTView, BinanceView, BankTransferView, PaysafecardCopyView, AmazonCopyView, OrderButton
from .persistent.confessions import confessView, confessReplyView
from .persistent.economy import InviteView
from .persistent.feedback import FeedbackView
from .persistent.appeal import AppealsView, AppealsModerationView
from .persistent.application import ApplicationModerationView

dotenv.load_dotenv(verbose=True)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s | %(name)-12s: %(levelname)-8s %(message)s", "%Y-%m-%d %H:%M:%S")

commands.has_guild_permissions = guild_perms

intents = discord.Intents.all()
#intents.presences = False

discord.Interaction.error = CustomInteraction.error
discord.Interaction.warn = CustomInteraction.warn
discord.Interaction.approve = CustomInteraction.approve
discord.Interaction.add = CustomInteraction.add
discord.Interaction.remove = CustomInteraction.remove
discord.Interaction.embed = CustomInteraction.embed
discord_android

class Record(asyncpg.Record):
    def __getattr__(self, name: str):
        return self[name]

class Evelina(commands.AutoShardedBot):
    def __init__(self, shard_count: int, shard_ids: List[int], db: asyncpg.Pool = None):
        super().__init__(
            help_command=EvelinaHelp(),
            activity=discord.CustomActivity(name="🔗 evelina.bot"),
            command_prefix=getprefix,
            case_insensitive=True,
            chunk_guilds_at_startup=False,
            strip_after_prefix=True,
            enable_debug_events=True,
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, replied_user=False),
            member_cache=discord.MemberCacheFlags(joined=True, voice=True),
            max_messages=25000,
            heartbeat_timeout=120,
            owner_ids=config.EVELINA.OWNER_IDS,
            client_id=config.EVELINA.CLIENT_ID,
            intents=intents,
            shard_count=shard_count,
            shard_ids=shard_ids
        )
        self.start_time = time()
        self.db = db
        self.login_data = {
            'host': config.POSTGRES.HOST,
            'password': config.POSTGRES.PASSWORD,
            'database': config.POSTGRES.DATABASE,
            'user': config.POSTGRES.USER,
            'port': int(config.POSTGRES.PORT),
        }
        self.log = None
        self.debug = False
        self.version = "1.0"
        self.extensions_loaded = False
        self.boot_up_time: float | None = None
        self.trace_config = aiohttp.TraceConfig
        self.time = datetime.datetime.now()
        self.mcd = commands.CooldownMapping.from_cooldown(3, 5, commands.BucketType.user)
        self.ccd = commands.CooldownMapping.from_cooldown(4, 5, commands.BucketType.channel)
        self.global_cd = commands.CooldownMapping.from_cooldown(15, 60, commands.BucketType.member)
        self.transcript = "transcripts.evelina.bot"
        self.prefix_cache = {"guilds": {}, "users": {}}
        self._session = None
        self._redis = None
        self._db = None
        self._closing = False
        self._connection_locks = {}
        self._connection_tasks = set()
        # Class Objects
        self.session = None  
        self.r2 = None  
        # self.twitch = None
        self.social = None  
        self.cache = None
        self.an = None
        self.ar = None
        self.level = None
        self.manage = None
        self.embed_build = None
        self.misc = None
        # Logging
        self.logging_guild = config.LOGGING.LOGGING_GUILD
        self.logging_joinleave = config.LOGGING.JOIN_LEAVE
        self.logging_report = config.LOGGING.REPORT
        self.logging_keys = config.LOGGING.KEYS
        self.logging_money = config.LOGGING.MONEY
        self.logging_blacklist = config.LOGGING.BLACKLIST
        self.logging_system = config.LOGGING.SYSTEM
        self.logging_feedback = config.LOGGING.FEEDBACK
        self.logging_ready = config.LOGGING.LOGGING_READY
        # Variables
        self.pfps_send = True
        self.banners_send = True
        self.register_hoocks()

    def run(self):
        return super().run(os.environ["BOT_TOKEN"])

    def ordinal(self, number: int) -> str:
        return num2words(number, to="ordinal_num")

    @property
    def uptime(self) -> str:
        return precisedelta(self.time, format="%0.0f")

    @property
    def chunked_guilds(self) -> int:
        return len([g for g in self.guilds if g.chunked])

    @property
    def lines(self) -> int:
        lines = 0
        for d in [x[0] for x in os.walk("./") if not ".git" in x[0]]:
            for file in os.listdir(d):
                if file.endswith(".py"):
                    lines += len(open(f"{d}/{file}", "r").read().splitlines())
        return lines

    async def getbyte(self, url: str) -> BytesIO:
        return BytesIO(await self.session.get_bytes(url))

    async def get_context(self, message: discord.Message, cls=EvelinaContext) -> EvelinaContext:
        return await super().get_context(message, cls=cls)

    async def create_db(self) -> asyncpg.Pool:
        logger.info("Creating PostgreSQL db connection")
        return await asyncpg.create_pool(**self.login_data)

    async def start_loops(self) -> None:
        try:
            loops = [oneminute_loop,
            #  fiveminutes_loop,
              tenminutes_loop,]
            for loop in loops:
                loop.start(self)
        except Exception as e:
            logger.error(f"Error starting loops: {e}")

    async def setup_hook(self) -> None:
        """
        Initialize bot connections and services.
        """
        try:
            from .redis import EvelinaRedis
            
            self.session = Session()
            await self.session._create_session()
            
            self.redis = await EvelinaRedis.from_url()
            
            if not self.db:
                self.db = await self.create_db()
                
            self.r2 = S3Handler()
            # self.twitch = TwitchHelper(self.session)
            self.social = SocialHelper(self)
            self.cache = Cache()
            self.an = AntinukeMeasures(self)
            self.ar = AntiraidMeasures(self)
            self.level = LevelingMeasures(self)
            self.manage = ManageMeasures(self)
            self.embed_build = EmbedScript()
            self.misc = Misc(self)
            
            logger.info("Starting bot")
            self.bot_invite = discord.utils.oauth_url(client_id=self.user.id, permissions=discord.Permissions(8))
            boot_up_time = time() - self.start_time
            await self.load()
            logger.info(f"Setup hook done in {helpers.stringfromtime(boot_up_time)}")
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            await self.close()
            raise

    def register_hoocks(self):
        self.check(func.disabled_command_check)
        self.check(func.disabled_module_check)
        self.check(func.restricted_command_check)
        self.check(func.restricted_module_check)
        self.check(func.blacklisted_check)
        # self.check(func.availability_check)

    async def load(self) -> None:
        try:
            await self.load_extension("jishaku")
            logger.info("Loaded jishaku")
        except Exception as e:
            logger.warning(f"Unable to load jishaku: {e}")
        for file in [f[:-3] for f in os.listdir("./cogs") if f.endswith(".py")]:
            try:
                await self.load_extension(f"cogs.{file}")
                logger.info(f"Loaded cogs.{file}")
            except Exception as e:
                logger.warning(f"Unable to load cogs.{file}: {e}")
        for file in [f[:-3] for f in os.listdir("./events") if f.endswith(".py")]:
            try:
                await self.load_extension(f"events.{file}")
                logger.info(f"Loaded events.{file}")
            except Exception as e:
                logger.warning(f"Unable to load events.{file}: {e}")
        logger.info("Loaded all cogs and events")
        try:
            await self.load_views()
            logger.info("Loaded views")
        except Exception as e:
            logger.warning(f"Unable to load views: {e}")

    async def load_views(self) -> None:
        vm_results = await self.db.fetch("SELECT * FROM voicemaster_buttons")
        self.add_view(VoiceMasterView(self, vm_results))
        self.add_view(GiveawayView(self))
        self.add_view(GiveawayEndedView(self))
        self.add_view(TicketButtonView(self, True))
        self.add_view(DeleteTicketRequestView(self))
        self.add_view(SuggestionView())
        self.add_view(PaypalView())
        self.add_view(PaysafecardView())
        self.add_view(LTCView())
        self.add_view(BTCView())
        self.add_view(ETHView())
        self.add_view(USDTView())
        self.add_view(BinanceView())
        self.add_view(BankTransferView())
        self.add_view(PaysafecardCopyView())
        self.add_view(AmazonCopyView())
        self.add_view(OrderButton())
        self.add_view(PaginationView())
        self.add_view(confessView(self))
        self.add_view(confessReplyView(self))
        self.add_view(InviteView(self))
        self.add_view(FeedbackView(self))
        self.add_view(AppealsView(self))
        self.add_view(AppealsModerationView(self))
        self.add_view(ApplicationModerationView(self))

    async def __chunk_guilds(self):
        for guild in self.guilds:
            try:
                await asyncio.sleep(5)
                await guild.chunk(cache=True)
            except Exception:
                pass

    async def __cache_invites(self) -> None:
        for guild in self.guilds:
            try:
                invites = await guild.invites()
                invites_data = [
                    {
                        "code": invite.code,
                        "uses": invite.uses,
                        "inviter_id": invite.inviter.id if invite.inviter else None
                    }
                    for invite in invites
                ]
                await self.redis.set(f"invites_{guild.id}", orjson.dumps(invites_data).decode("utf-8"))
            except Exception:
                pass

    async def on_ready(self):
        latencies = self.latencies
        if self.boot_up_time is None:
            self.boot_up_time = time() - self.start_time
        logger.info(f"Connected in {helpers.stringfromtime(self.boot_up_time)}")
        logger.info(f"Loading complete | running {len(latencies)} shards")
        for shard_id, latency in latencies:
            logger.info(f"Shard [{shard_id}] - HEARTBEAT {latency:.2f}s")
        #asyncio.ensure_future(self.__chunk_guilds())
        #logger.info(f"Chunked Guilds")
        asyncio.ensure_future(self.__cache_invites())
        logger.info(f"Cached Invites")
        await self.load_prefixes()
        logger.info(f"Cached Prefixes")
        await self.start_loops()
        logger.info(f"Started Loops & Tasks")
        self.log = LoggingMeasures(self)
        logger.info(f"Started Logging Measures")
        logger.info("Evelina booted successfully")
        # try:
        #     guild = self.get_guild(self.logging_guild)
        #     channel = guild.get_channel_or_thread(self.logging_ready)
        #     await channel.send(f"**Evelina** has successfully booted up in **{helpers.stringfromtime(self.boot_up_time)}**")
        # except Exception:
        #     pass

        for k in ("HTTP_PROXY","HTTPS_PROXY","http_proxy","https_proxy"):
            os.environ.pop(k, None)
        
        _orig = httpx.AsyncClient.init
        def _patched_init(self, args, **kwargs):
            kwargs.pop("proxies", None)
            return _orig(self,args, **kwargs)
        httpx.AsyncClient.init = _patched_init

    async def on_command_error(self, ctx: EvelinaContext, error: commands.CommandError) -> Any:
        if ctx.guild is None or ctx.channel is None:
            return
        if ctx.guild.me is None or not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            return
        ignored = [commands.CheckFailure, commands.NotOwner]
        if type(error) in ignored:
            return
        try:
            if isinstance(error, commands.MemberNotFound):
                return await ctx.send_warning(f"Member not found")
            elif isinstance(error, commands.UserNotFound):
                return await ctx.send_warning(f"User not found")
            elif isinstance(error, commands.RoleNotFound):
                return await ctx.send_warning(f"Role not found")
            elif isinstance(error, commands.ChannelNotFound):
                return await ctx.send_warning(f"Channel not found")
            elif isinstance(error, commands.GuildNotFound):
                return await ctx.send_warning(f"Guild not found")
            elif isinstance(error, commands.MissingPermissions):
                return await ctx.send_warning(f"You are **missing** the following permission: `{', '.join(permission for permission in error.missing_permissions)}`")
            elif isinstance(error, commands.BadUnionArgument):
                if error.converters == (discord.Member, discord.User):
                    return await ctx.send_warning(f"Member not found")
                elif error.converters == (discord.Guild, discord.Invite):
                    return await ctx.send_warning(f"Invalid invite code")
                else:
                    return await ctx.send_warning(f"Couldn't convert **{error.param.name}** into " + f"`{', '.join(converter.__name__ for converter in error.converters)}`")
            elif isinstance(error, commands.BadArgument):
                return await ctx.send_warning(error)
            elif isinstance(error, commands.MissingRequiredArgument):
                return await ctx.send_help(ctx.command)
            elif isinstance(error, commands.CommandNotFound):
                if check := await self.db.fetchrow("SELECT * FROM selfaliases WHERE user_id = $1 AND alias = $2", ctx.author.id, ctx.invoked_with):
                    message = copy(ctx.message)
                    args = ctx.message.content[len(ctx.prefix + ctx.invoked_with):].strip().split()
                    formatted_command = utils.replace_placeholders(check['command'], args)
                    formatted_args = " ".join(args) if check["args"] is None else utils.replace_placeholders(check['args'], args)
                    new_command = f"{formatted_command} {formatted_args}".strip()
                    message.content = f"{ctx.prefix}{new_command}"
                    return await self.process_commands(message)
                elif check := await self.db.fetchrow("SELECT * FROM aliases WHERE guild_id = $1 AND alias = $2", ctx.guild.id, ctx.invoked_with):
                    message = copy(ctx.message)
                    args = ctx.message.content[len(ctx.prefix + ctx.invoked_with):].strip().split()
                    formatted_command = utils.replace_placeholders(check['command'], args)
                    formatted_args = " ".join(args) if check["args"] is None else utils.replace_placeholders(check['args'], args)
                    new_command = f"{formatted_command} {formatted_args}".strip()
                    message.content = f"{ctx.prefix}{new_command}"
                    return await self.process_commands(message)
                else:
                    return
            elif isinstance(error, commands.CommandOnCooldown):
                return await ctx.cooldown_send(f"Wait **{humanize.precisedelta(datetime.timedelta(seconds=error.retry_after), format='%0.0f')}** before using `{ctx.clean_prefix}{ctx.command.qualified_name}` again")
            elif isinstance(error, discord.HTTPException):
                if error.code == 50035:
                    return await ctx.send_warning(f"Failed to send **embed**\n```{error}```")
            elif isinstance(error, discord.Forbidden):
                if error.code == 50013:
                    return await ctx.send_warning(f"I **missing** permissions to complete this action")
                if error.code == 50001:
                    return await ctx.send_warning(f"Missing **Access** to this guild")
            elif isinstance(error, discord.NotFound):
                if error.code == 10008:
                    return await ctx.send_warning(f"Message not found")
                elif error.code == 10007:
                    return await ctx.send_warning(f"Member not found")
                elif error.code == 0:
                    return await ctx.send_warning(f"Object not found")
            elif isinstance(error, KeyError):
                return await ctx.send_warning(f"API returned an **invalid response**, please try again later")
            elif isinstance(error, commands.CommandError):
                if not "Command raised an exception: " in str(error):
                    return await ctx.send_warning(f"{error}")
                else:
                    if ctx.channel is None or not ctx.channel.permissions_for(ctx.guild.me).send_messages:
                        return
                    code = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
                    now = discord.utils.format_dt(datetime.datetime.now(), style="R")
                    j = {
                        "guild_id": ctx.guild.id,
                        "channel_id": ctx.channel.id,
                        "user_id": ctx.author.id,
                        "timestamp": now,
                        "error": str(error),
                        "code": code,
                        "command": str(ctx.command.qualified_name) or "N/A",
                    }
                    await self.db.execute("INSERT INTO error_codes (code, info) VALUES ($1, $2)", code, json.dumps(j))
                    user_embed = discord.Embed(
                        description=f"{emojis.WARNING} {ctx.author.mention}: An error occurred while running the **{ctx.command.qualified_name}** command."
                        + f"\nPlease report the attached code to a developer in the [Evelina Server](https://discord.gg/evelina)",
                        color=colors.WARNING,
                    )
                    # try:
                    #     await ctx.send(embed=user_embed, content=f"`{code}`")
                    #     developer_embed = (
                    #         discord.Embed(description=str(error), color=colors.NEUTRAL)
                    #         .add_field(name="Guild", value=f"{ctx.guild.name}\n`{ctx.guild.id}`", inline=True)
                    #         .add_field(name="Channel", value=f"<#{ctx.channel.id}>\n`{ctx.channel.id}`", inline=True)
                    #         .add_field(name="User", value=f"<@{ctx.author.id}>\n`{ctx.author.id}`", inline=True)
                    #         .add_field(name="Command", value=f"**{ctx.command.qualified_name}**")
                    #         .add_field(name="Timestamp", value=now)
                    #         .set_author(name=f"Error Code: {code}")
                    #     )
        #                 developer_channel = self.get_channel(self.logging_report)
        #                 if developer_channel:
        #                     return await developer_channel.send(embed=developer_embed)
        #             except NotFound:
        #                 pass
        except NotFound:
            pass
        except Forbidden:
            pass
    
    async def load_prefixes(self):
        guild_prefixes = await self.db.fetch("SELECT guild_id, prefix FROM prefixes")
        for row in guild_prefixes:
            self.prefix_cache["guilds"][row["guild_id"]] = row["prefix"]
        user_prefixes = await self.db.fetch("SELECT user_id, prefix FROM selfprefix")
        for row in user_prefixes:
            self.prefix_cache["users"][row["user_id"]] = row["prefix"]
    
    async def get_prefixes(self, message: discord.Message) -> Set[str]:
        prefixes = set()
        user_prefix = self.prefix_cache["users"].get(message.author.id)
        if user_prefix:
            prefixes.add(user_prefix)
        guild_prefix = self.prefix_cache["guilds"].get(message.guild.id) if message.guild else None
        if guild_prefix:
            prefixes.add(guild_prefix)
        else:
            prefixes.update([";"])
        return prefixes

    def member_cooldown(self, message: discord.Message) -> Optional[int]:
        bucket = self.mcd.get_bucket(message)
        return bucket.update_rate_limit()

    def channel_cooldown(self, message: discord.Message) -> Optional[int]:
        bucket = self.ccd.get_bucket(message)
        return bucket.update_rate_limit()
        
    async def process_commands(self, message: discord.Message) -> Any:
        if message.content.startswith(tuple(await self.get_prefixes(message))) or message.content.startswith(f"<@{self.user.id}>"):
            channel_rl = self.channel_cooldown(message)
            member_rl = self.member_cooldown(message)
            if channel_rl or member_rl:
                return
            return await super().process_commands(message)
        
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> Any:
        if not after.guild:
            return
        if before.content != after.content:
            if not await self.db.fetchrow("SELECT * FROM blacklist_user WHERE user_id = $1", after.author.id):
                if after.content.startswith(tuple(await self.get_prefixes(after))) or after.content.startswith(f"<@{self.user.id}>"):
                    return await self.process_commands(after)
        
    async def on_message(self, message: discord.Message) -> Any:
        if not message.author.bot and message.guild:
            perms = message.channel.permissions_for(message.guild.me)
            if perms.send_messages and perms.embed_links:
                if not await self.db.fetchrow("SELECT * FROM blacklist_user WHERE user_id = $1", message.author.id):
                    if message.content == f"<@{self.user.id}>":
                        channel_rl = self.channel_cooldown(message)
                        member_rl = self.member_cooldown(message)
                        if not channel_rl and not member_rl:
                            ctx = await self.get_context(message)
                            prefixes = " & ".join(f"`{p}`" for p in await self.get_prefixes(message))
                            try:
                                return await ctx.send(embed=discord.Embed(color=colors.NEUTRAL, description=f"Your {'prefix is' if len(await self.get_prefixes(message)) == 1 else 'prefixes are'}: {prefixes}"))
                            except Exception:
                                pass
                    try:
                        await self.process_commands(message)
                    except Exception:
                        pass
    
    async def get_connection_lock(self, key: str) -> asyncio.Lock:
        if key not in self._connection_locks:
            self._connection_locks[key] = asyncio.Lock()
        return self._connection_locks[key]

    async def track_connection_task(self, task: asyncio.Task):
        self._connection_tasks.add(task)
        try:
            await task
        finally:
            self._connection_tasks.discard(task)

    async def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        
        logger.info("Bot is shutting down, closing connections...")
        
        for task in self._connection_tasks:
            task.cancel()
        
        try:
            await asyncio.gather(*self._connection_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error while canceling tasks: {e}")

        if self.session:
            logger.info("Closing aiohttp session...")
            try:
                await asyncio.shield(self.session.close())
                logger.info("Session closed successfully")
            except Exception as e:
                logger.error(f"Error closing session: {e}")

        if self.redis:
            logger.info("Closing Redis connection...")
            try:
                await asyncio.shield(self.redis.close())
                logger.info("Redis connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Redis: {e}")

        if self.db:
            logger.info("Closing PostgreSQL connection pool...")
            try:
                await asyncio.shield(self.db.close())
                logger.info("Database pool closed successfully")
            except Exception as e:
                logger.error(f"Error closing database: {e}")

        logger.info("Calling parent close method...")
        try:
            await asyncio.shield(super().close())
        except Exception as e:
            logger.error(f"Error in parent close method: {e}")
        finally:
            self._closing = False
        
        logger.info("Bot shutdown complete")

async def getprefix(bot: Evelina, message: discord.Message) -> List[str]:
    if message.guild:
        prefixes = list(map(lambda x: x, await bot.get_prefixes(message)))
        return commands.when_mentioned_or(*prefixes)(bot, message)