import secrets
from contextlib import suppress
from datetime import datetime
from logging import DEBUG, getLogger
from pathlib import Path
from typing import Any, Collection, Dict, List, Optional, cast

import jishaku
import json
from aiohttp import ClientSession, TCPConnector
from asyncpraw import Reddit as RedditClient
from cashews import cache
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
    TextChannel,
    User,
    Activity,
    ActivityType,
    Role
)
from discord.ext.commands import (
    AutoShardedBot,
    BadFlagArgument,
    BadInviteArgument,
    BadLiteralArgument,
    BadUnionArgument,
    BucketType,
    ChannelNotFound,
    CooldownMapping,
    CheckFailure,
    CommandError,
    CommandInvokeError,
    CommandNotFound,
    CommandOnCooldown,
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
    NotOwner,
    RangeError,
    RoleNotFound,
    TooManyFlags,
    UserNotFound,
    when_mentioned_or,
)
from discord.message import Message
from discord.utils import utcnow
from humanize import precisedelta
from humanfriendly import format_timespan

from colorama import Fore, Style
from posthog import Posthog

import config
import os
from tools import fmtseconds
from tools.browser import BrowserHandler
from tools.client import Context, HelpCommand, Redis, database, init_logging
from tools.client.database import Database, Settings
from tools.formatter import human_join, plural
from tools.client import Interaction as CustomInteraction
from tools.parser.TagScript.exceptions import EmbedParseError, TagScriptError
from textwrap import shorten

log = getLogger("greed/bot")
cache.setup("mem://")

jishaku.Flags.HIDE = True
jishaku.Flags.RETAIN = True
jishaku.Flags.NO_UNDERSCORE = True
jishaku.Flags.NO_DM_TRACEBACK = True

posthog = Posthog(
    "phc_ds8DUIOmRamXtLOekJPgdUJ5sIYxUyagooTn3Y3ZI0k", host="https://us.i.posthog.com"
)

async def get_prefix(bot: "greed", message: Message) -> List[str]:
    """Fetch the command prefix for the bot."""
    prefix = [config.CLIENT.PREFIX]

    if message.guild:

        guild_prefixes = cast(
            Optional[List[str]],
            await bot.db.fetchval(
                """
                SELECT prefixes
                FROM settings
                WHERE guild_id = $1
                """,
                message.guild.id,
            ),
        )
        prefix = guild_prefixes or prefix


    user_prefix = await bot.db.fetchval(
        """
        SELECT prefix
        FROM selfprefix
        WHERE user_id = $1
        """,
        message.author.id,
    )
    if user_prefix:
        prefix = [user_prefix]

    return when_mentioned_or(*prefix)(bot, message)

Interaction.warn = CustomInteraction.warn
Interaction.approve = CustomInteraction.approve
Interaction.deny = CustomInteraction.deny

class greed(AutoShardedBot):
    session: ClientSession
    uptime: datetime
    traceback: Dict[str, Exception]
    global_cooldown: CooldownMapping
    database: Database
    redis: Redis
    owner_ids: Collection[int]
    user: ClientUser
    reddit: RedditClient
    version: str = "2.9"
    user_agent: str = f"greed (DISCORD BOT/{version})"
    browser: BrowserHandler

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
            intents=Intents.all(),
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            help_command=HelpCommand(),
            command_prefix=get_prefix,
            case_insensitive=True,
            max_messages=1500,
            activity=Activity(
                type=ActivityType.custom,
                name=" ",
                state="🔗 discord.gg/greedbot",
            ),
            chunk_guilds_at_startup=False
        )

        self.traceback = {}
        self.global_cooldown = CooldownMapping.from_cooldown(1, 3, BucketType.user)
        self.add_check(self.check_global_cooldown)
        self.time = datetime.now()

    async def check_global_cooldown(self, ctx: Context) -> bool:
        bucket = self.global_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            return False
        return True

    @property
    def db(self) -> Database:
        return self.database

    @property
    def owner(self) -> User:
        return self.get_user(self.owner_ids[0])  # type: ignore

    @property
    def uptime(self) -> str:
        return precisedelta(self.time, format="%0.0f")

    def get_message(self, message_id: int) -> Optional[Message]:
        return self._connection._get_message(message_id)

    async def get_or_fetch_user(self, user_id: int) -> User:
        return self.get_user(user_id) or await self.fetch_user(user_id)

    def run(self) -> None:
        log.info("Starting the bot..")
        super().run(os.environ.get("TOKEN"), reconnect=True, log_handler=None)

    async def close(self) -> None:
        await super().close()
        await self.session.close()
        await self.db.close()
        await self.redis.aclose()

    async def on_ready(self) -> None:
        log.info(
            f"Connected as {Fore.LIGHTCYAN_EX}{Style.BRIGHT}{self.user}{Fore.RESET} ({Fore.LIGHTRED_EX}{self.user.id}{Fore.RESET})."
        )
        instance_id = f"{self.user.id}_cluster_{cluster_id}"
        await self.redis.hset('guild_counts', instance_id, 0)
        await self.redis.hset('user_counts', instance_id, 0)

        user_count = sum(guild.member_count for guild in self.guilds)

        log.info(f"Setting user count to {user_count} for {instance_id}.")
        await self.redis.hset('user_counts', instance_id, user_count)

        log.info(f"Setting guild count to {len(self.guilds)} for {instance_id}.")
        await self.redis.hset('guild_counts', instance_id, len(self.guilds))

        self.browser = BrowserHandler()
        await self.browser.init()
        await self.wait_until_ready()
        await self.load_extensions()

        await self.register_shards_in_redis()


    async def register_shards_in_redis(self) -> None:
        """Register shards and cluster information in Redis."""
        shard_data = {
            'cluster_id': self.cluster_id,
            'shards': self.shard_ids
        }
        await self.redis.set(f'cluster:{self.cluster_id}', json.dumps(shard_data))

    async def update_shard_status(self, shard_id: int, status: str) -> None:
        """Update shard status in Redis."""
        await self.redis.hset(
            f'shard_status:{shard_id}', 
            mapping={'status': status, 'timestamp': datetime.utcnow().isoformat()}
        )

    async def on_shard_ready(self, shard_id: int) -> None:
        """Log when a shard is ready and update its status in Redis."""
        log.info(
            f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTGREEN_EX}spawned{Fore.RESET}."
        )
        await self.update_shard_status(shard_id, 'ready')

    async def on_shard_resumed(self, shard_id: int) -> None:
        """Log when a shard is resumed and update its status in Redis."""
        log.info(
            f"Shard ID {Fore.LIGHTGREEN_EX}{shard_id}{Fore.RESET} has {Fore.LIGHTYELLOW_EX}resumed{Fore.RESET}."
        )
        await self.update_shard_status(shard_id, 'resumed')

    async def setup_hook(self) -> None:
        self.session = ClientSession(
            headers={"User-Agent": self.user_agent},
            connector=TCPConnector(ssl=False),
        )
        self.database = await database.connect()
        self.redis = await Redis.from_url()
        await self.load_extensions()

    async def load_extensions(self) -> None:
        await self.load_extension("jishaku")
        for feature in Path("cogs").iterdir():
            if not feature.is_dir() or not (feature / "__init__.py").is_file():
                continue
            try:
                await self.load_extension(".".join(feature.parts))
            except Exception as exc:
                log.exception("Failed to load extension %s.", feature.name, exc_info=exc)

    async def log_traceback(self, ctx: Context, exc: Exception) -> Message:
        """Store an Exception in memory for future reference."""
        log.exception("Unexpected exception occurred in %s.", ctx.command.qualified_name, exc_info=exc)
        key = secrets.token_urlsafe(54)
        self.traceback[key] = exc
        return await ctx.warn(
            f"Command `{ctx.command.qualified_name}` raised an exception. Please try again later.",
            content=f"`{key}`",
        )

    async def on_command_completion(self, ctx: Context) -> None:
        duration = (utcnow() - ctx.message.created_at).total_seconds()
        guild = shorten(ctx.guild.name, width=25, placeholder="..")
        log.info(
            f" {Fore.RESET}".join(
                [
                    f"{Fore.LIGHTMAGENTA_EX}{ctx.author}",
                    f"ran {Fore.LIGHTCYAN_EX}{Style.BRIGHT}{ctx.command.qualified_name}{Style.NORMAL}",
                    f"@ {Fore.LIGHTYELLOW_EX}{guild}",
                    f"/ {Fore.LIGHTBLUE_EX}{ctx.channel}",
                    f"{Fore.LIGHTWHITE_EX}{Style.DIM}{fmtseconds(duration)}{Fore.RESET}{Style.NORMAL}.",
                ]
            )
        )
        await self.db.execute(
            """
            INSERT INTO commands.usage (
                guild_id,
                channel_id,
                user_id,
                command
            ) VALUES ($1, $2, $3, $4)
            """,
            ctx.guild.id,
            ctx.channel.id,
            ctx.author.id,
            ctx.command.qualified_name,
        )

    def is_dangerous(self, role: Role) -> bool:
        """
        Check if the role has dangerous permissions
        """

        return any(
            [
                role.permissions.ban_members,
                role.permissions.kick_members,
                role.permissions.mention_everyone,
                role.permissions.manage_channels,
                role.permissions.manage_events,
                role.permissions.manage_expressions,
                role.permissions.manage_guild,
                role.permissions.manage_roles,
                role.permissions.manage_messages,
                role.permissions.manage_webhooks,
                role.permissions.manage_permissions,
                role.permissions.manage_threads,
                role.permissions.moderate_members,
                role.permissions.mute_members,
                role.permissions.deafen_members,
                role.permissions.move_members,
                role.permissions.administrator,
            ]
        )

    async def get_context(self, origin: Message | Interaction, /, *, cls=Context) -> Context:
        context = await super().get_context(origin, cls=cls)
        context.settings = await Settings.fetch(self, context.guild)
        return context

    async def process_commands(self, message: Message) -> None:
        if not message.guild or message.author.bot:
            return
        channel = message.channel
        if not (
            channel.permissions_for(message.guild.me).send_messages
            and channel.permissions_for(message.guild.me).embed_links
            and channel.permissions_for(message.guild.me).attach_files
        ):
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
        ctx = await self.get_context(message)
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
        if (
            message.guild
            and message.guild.system_channel_flags.premium_subscriptions
            and message.type
            in (
                MessageType.premium_guild_subscription,
                MessageType.premium_guild_tier_1,
                MessageType.premium_guild_tier_2,
                MessageType.premium_guild_tier_3,
            )
        ):
            self.dispatch("member_boost", message.author)
            self.dispatch("member_activity", message.channel, message.author)
        return await super().on_message(message)

    async def on_message_edit(self, before: Message, after: Message) -> None:
        self.dispatch("member_activity", after.channel, after.author)
        if before.content == after.content:
            return
        return await self.process_commands(after)

    async def on_audit_log_entry_create(self, entry: AuditLogEntry) -> None:
        if not self.is_ready():
            return
        event = f"audit_log_entry_{entry.action.name}"
        self.dispatch(event, entry)

    async def on_typing(self, channel: TextChannel, user: Member | User, when: datetime) -> None:
        if isinstance(user, Member):
            self.dispatch("member_activity", channel, user)

    async def on_command_error(self, ctx: Context, exc: CommandError) -> Any:
        channel = ctx.channel
        if not (
            channel.permissions_for(channel.guild.me).send_messages
            and channel.permissions_for(channel.guild.me).embed_links
        ):
            return
        if isinstance(exc, (CommandNotFound, DisabledCommand, NotOwner)):
            return
        elif isinstance(exc, (MissingRequiredArgument, MissingRequiredAttachment, BadLiteralArgument)):
            return await ctx.send_help(ctx.command)
        elif isinstance(exc, TagScriptError):
            if isinstance(exc, EmbedParseError):
                return await ctx.warn("Something is wrong with your **script**!", *exc.args)
        elif isinstance(exc, FlagError):
            if isinstance(exc, TooManyFlags):
                return await ctx.warn(f"You specified the **{exc.flag.name}** flag more than once!")
            elif isinstance(exc, BadFlagArgument):
                try:
                    annotation = exc.flag.annotation.__name__
                except AttributeError:
                    annotation = exc.flag.annotation.__class__.__name__
                return await ctx.warn(
                    f"Failed to cast **{exc.flag.name}** to `{annotation}`!",
                    *["Make sure you provide **on** or **off** for `Status` flags!"] if annotation == "Status" else [],
                )
            elif isinstance(exc, MissingRequiredFlag):
                return await ctx.warn(f"You must specify the **{exc.flag.name}** flag!")
            elif isinstance(exc, MissingFlagArgument):
                return await ctx.warn(f"You must specify a value for the **{exc.flag.name}** flag!")
        elif isinstance(exc, CommandInvokeError):
            original = exc.original
            if isinstance(original, HTTPException):
                if original.code == 50013:
                    if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                        return await ctx.warn("I don't have the required **permissions** to do that!")
                elif original.code == 50045:
                    return await ctx.warn("The **provided asset** is too large to be used!")
            elif isinstance(original, Forbidden):
                if original.code == 40333:
                    return await ctx.warn(
                        "Discord is experiencing an **outage** at the moment!",
                        "You can check for updates by clicking [**here**](https://discordstatus.com/).",
                    )
            return await self.log_traceback(ctx, original)
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
                await ctx.warn(
                    "This command is currently on cooldown!",
                    f"Try again in **{format_timespan(exc.retry_after)}**",
                )
            else:
                with suppress(NotFound):
                    await ctx.message.add_reaction("⏰")

        elif isinstance(exc, BadUnionArgument):
            if exc.converters == (Member, User):
                return await ctx.warn(
                    f"No **{exc.param.name}** was found matching **{ctx.current_argument}**!",
                    "If the user is not in this server, try using their **ID** instead",
                )
            elif exc.converters == (Guild, Invite):
                return await ctx.warn(f"No server was found matching **{ctx.current_argument}**!")
            else:
                return await ctx.warn(
                    f"Casting **{exc.param.name}** to {human_join([f'`{c.__name__}`' for c in exc.converters])} failed!",
                )
        elif isinstance(exc, MemberNotFound):
            return await ctx.warn(f"No **member** was found matching **{exc.argument}**!")
        elif isinstance(exc, UserNotFound):
            return await ctx.warn(f"No **user** was found matching `{exc.argument}`!")
        elif isinstance(exc, RoleNotFound):
            return await ctx.warn(f"No **role** was found matching **{exc.argument}**!")
        elif isinstance(exc, ChannelNotFound):
            return await ctx.warn(f"No **channel** was found matching **{exc.argument}**!")
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
            permissions = human_join([f"`{permission}`" for permission in exc.missing_permissions], final="and")
            _plural = "s" if len(exc.missing_permissions) > 1 else ""
            return await ctx.warn(f"You're missing the {permissions} permission{_plural}!")
        elif isinstance(exc, CommandError):
            if not isinstance(exc, (CheckFailure, Forbidden)) and isinstance(exc, (HTTPException, NotFound)):
                if "Unknown Channel" in exc.text:
                    return
                return await ctx.warn(exc.text.capitalize())
            origin = getattr(exc, "original", exc)
            with suppress(TypeError):
                if any(
                    forbidden in origin.args[-1]
                    for forbidden in ("global check", "check functions", "Unknown Channel")
                ):
                    return
            return await ctx.warn(*origin.args)
        else:
            return await ctx.send_help(ctx.command)

    async def on_guild_join(self, guild: Guild) -> None:
        log.info(
            f"Joined guild {Fore.LIGHTGREEN_EX}{guild}{Fore.RESET} ({Fore.LIGHTRED_EX}{guild.id}{Fore.RESET})."
        )

        instance_id = f"{self.user.id}_cluster_{cluster_id}"
        await self.redis.hincrby('user_counts', instance_id, guild.member_count)
        await self.redis.hincrby('guild_counts', instance_id, 1)


        blacklist = await self.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1
                FROM guild_blacklist
                WHERE guild_id = $1
            )
            """,
            guild.id,
        )
        if blacklist:
            await guild.leave()

    async def on_guild_remove(self, guild: Guild):
        instance_id = f"{self.user.id}_cluster_{cluster_id}"
        member_count = guild.member_count or 0
        await self.redis.hincrby('guild_counts', instance_id, -1)
        await self.redis.hincrby('user_counts', instance_id, member_count)
        await self.redis.hincrby('guild_counts', instance_id, 1)

    async def get_guilds(self):
        counts = await self.redis.hvals('guild_counts')
        total_count = sum(int(count) for count in counts if count)
        return total_count

    async def get_users(self):
        counts = await self.redis.hvals('user_counts')
        total_user_count = sum(int(count) for count in counts if count)
        return total_user_count


if __name__ == '__main__':
    total_shards = 6
    shards_per_cluster = 3

    cluster_id = int(os.environ.get("CLUSTER", 1))

    offset = (cluster_id - 1) * shards_per_cluster
    shard_ids = list(range(offset, min(offset + shards_per_cluster, total_shards)))

    cluster_kwargs = {
        "shard_ids": shard_ids,
        "shard_count": total_shards,
    }

    bot = greed(
        description=config.CLIENT.DESCRIPTION,
        owner_ids=config.CLIENT.OWNER_IDS,
        **cluster_kwargs
    )

    bot.cluster_id = cluster_id
    bot.shard_ids = shard_ids
    bot.total_shards = total_shards
    init_logging(DEBUG)
    bot.run()
