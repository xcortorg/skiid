import asyncio
import glob
import importlib
import traceback
from asyncio import Lock
from contextlib import suppress
from datetime import datetime, timezone
from os import environ
from pathlib import Path
from secrets import token_urlsafe
from time import time
from typing import TYPE_CHECKING, Any, List, Optional

import config
from aiohttp.client_exceptions import (ClientConnectorError,
                                       ClientResponseError, ContentTypeError)
from asyncpg import Pool
from cashews import cache
from discord import (Activity, ActivityType, AllowedMentions, AuditLogAction,
                     CustomActivity, Forbidden, Guild, HTTPException, Intents,
                     Invite, Member, Message, MessageType, NotFound, Status,
                     TextChannel, User, VoiceChannel)
from discord.ext.commands import (AutoShardedBot, BadArgument,
                                  BadColourArgument, BadFlagArgument,
                                  BadInviteArgument, BadLiteralArgument,
                                  BadUnionArgument, BotMissingPermissions,
                                  BucketType, ChannelNotFound, CheckFailure,
                                  CommandError, CommandInvokeError,
                                  CommandNotFound, CommandOnCooldown)
from discord.ext.commands import Context as _Context
from discord.ext.commands import (CooldownMapping, DisabledCommand,
                                  EmojiNotFound, Flag, FlagError,
                                  GuildNotFound, MaxConcurrencyReached,
                                  MemberNotFound, MissingPermissions,
                                  MissingRequiredArgument,
                                  MissingRequiredAttachment,
                                  MissingRequiredFlag, NotOwner, RangeError,
                                  RoleNotFound, TooManyFlags, UserInputError,
                                  UserNotFound, when_mentioned_or)
from discord.utils import utcnow
from pomice import NodePool
from tools.client import database
from tools.client.browser import BrowserHandler
from tools.client.context import Context
from tools.client.database.settings import Settings
from tools.client.network import ClientSession
from tools.client.redis import Redis
from tools.managers.logging import logger as log
from tools.utilities import Plural, human_join
from tornado.ioloop import IOLoop
from tuuid import tuuid

cache.setup(f"redis://{config.Redis.host}:{config.Redis.port}/{config.Redis.db}")

environ["JISHAKU_HIDE"] = "True"
environ["JISHAKU_RETAIN"] = "True"
environ["JISHAKU_NO_UNDERSCORE"] = "True"
environ["JISHAKU_SHELL_NO_DM_TRACEBACK"] = "True"


class Bleed(AutoShardedBot):
    def __init__(self: "Bleed", *args, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix,
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            help_command=None,
            intents=Intents.all(),
            mobile_status=True,
            case_insensitive=True,
            owner_ids=config.Bleed.owner_id,
            *args,
            **kwargs,
            activity=CustomActivity(
                name="🔗 discord.gg/blee",
            ),
        )
        self.uptime = datetime.now(timezone.utc)
        self.db: Optional[Pool] = None
        self.redis: Redis = Redis()
        self.redis_pool = None
        self.browser_handler = BrowserHandler()
        self.browser = None
        self.sticky_locks = {}
        self.buckets: dict = dict(
            guild_commands=dict(
                lock=Lock(),
                cooldown=CooldownMapping.from_cooldown(
                    12,
                    2.5,
                    BucketType.guild,
                ),
                blocked=set(),
            ),
            message_reposting=CooldownMapping.from_cooldown(3, 30, BucketType.user),
            highlights=CooldownMapping.from_cooldown(
                1,
                60,
                BucketType.member,
            ),
            afk=CooldownMapping.from_cooldown(1, 60, BucketType.member),
            reaction_triggers=CooldownMapping.from_cooldown(
                1,
                2.5,
                BucketType.member,
            ),
        )

    def run(self: "Bleed"):
        super().run(
            config.Bleed.token,
            reconnect=True,
        )

    async def get_context(self: "Bleed", origin: Message, *, cls=None) -> Context:
        context = await super().get_context(
            origin,
            cls=cls or Context,
        )
        if context.guild:
            context.settings = await Settings.fetch(self, context.guild)
        return context

    async def get_prefix(self: "Bleed", message: Message) -> List[str]:
        try:
            prefix = await Settings.get_prefix(self, message)
        except Exception as e:
            log.error(f"Failed to fetch prefix: {e}")
            prefix = config.Bleed.prefix

        return when_mentioned_or(prefix)(self, message)

    async def on_guild_join(self, guild: Guild) -> None:
        user: Optional[Member | User] = None
        with suppress(HTTPException):
            async for entry in guild.audit_logs(limit=5):
                if entry.action == AuditLogAction.bot_add and entry.target == self.user:
                    user = entry.user
                    break

        response = [
            (
                f"Joined [{guild.name}]({guild.vanity_url}) (`{guild.id}`)"
                if guild.vanity_url
                else f"Joined {guild.name} (`{guild.id}`)"
            ),
            f"via {user} (`{user.id}`)" if user and user.id != guild.owner_id else "",
            f"owned by {guild.owner} (`{guild.owner_id}`)",
        ]

        message = " ".join(filter(None, response))

        try:
            for owner_id in self.owner_ids:
                owner = await self.fetch_user(owner_id)
                await owner.send(message)
        except Exception as e:
            log.error(f"Failed to send guild join message to owner(s): {e}")

    @staticmethod
    async def on_guild_remove(guild: Guild):
        log.info("Left guild %s (%s)", guild, guild.id)

    async def load_patches(self) -> None:
        patch_files = glob.glob("tools/managers/patch/**/*.py", recursive=True)

        for file in patch_files:
            if file.endswith("__init__.py"):
                continue
            module_name = file.replace(".py", "").replace("/", ".")

            try:
                importlib.import_module(module_name)
                log.info(f"Patched: {module_name}")
            except Exception as e:
                log.error(f"Error importing {module_name}: {e}")

    async def setup_hook(self: "Bleed"):
        self.session = ClientSession()
        self.ioloop = IOLoop.current()
        try:
            self.db = await database.connect()
        except Exception as e:
            log.error(f"Failed to connect to the database: {e}")
            return

        extensions = [
            ".".join(feature.parts)
            for feature in Path("extensions").iterdir()
            if feature.is_dir() and (feature / "__init__.py").is_file()
        ]

        load_tasks = [self.load_extension(ext) for ext in extensions]
        results = await asyncio.gather(*load_tasks, return_exceptions=True)

        for ext, result in zip(extensions, results):
            if isinstance(result, Exception):
                log.error(f"Failed to load extension {ext}: {result}")
            else:
                log.info(f"Loaded extension: {ext}")

        if "jishaku" not in self.extensions:
            try:
                await self.load_extension("jishaku")
                log.info("Loaded extension: jishaku")
            except Exception as e:
                log.error(f"Failed to load jishaku extension: {e}")

        await self.load_patches()
        await self.browser_handler.init()
        self.browser = self.browser_handler

    async def on_ready(self):
        log.info("Bot is ready")
        await self.connect_nodes()

    async def close(self):
        try:
            await super().close()
        except Exception as e:
            log.error(f"Error closing bot: {e}")
        if self.redis_pool:
            try:
                await self.redis_pool.close()
            except Exception as e:
                log.error(f"Error closing Redis pool: {e}")
        if hasattr(self, "session") and self.session:
            try:
                await self.session.close()
            except Exception as e:
                log.error(f"Error closing session: {e}")
        if self.browser:
            await self.browser.cleanup()

    async def on_message_edit(self, before: Message, after: Message):
        if not self.is_ready() or not before.guild or before.author.bot:
            return

        if before.content == after.content or not after.content:
            return

        await self.process_commands(after)

    async def on_message(self: "Bleed", message: Message):
        if not self.is_ready() or not message.guild or message.author.bot:
            return

        # Handle prefix display when bot is mentioned
        if self.user in message.mentions and not message.reference:
            try:
                # Fetch user-specific prefix
                user_prefix = await self.db.fetchval(
                    """
                    SELECT prefix
                    FROM selfprefix
                    WHERE user_id = $1
                    """,
                    message.author.id,
                )
                if user_prefix:
                    prefixes = [user_prefix]
                else:
                    guild_prefix = await self.db.fetchval(
                        """
                        SELECT prefix
                        FROM settings
                        WHERE guild_id = $1
                        """,
                        message.guild.id,
                    )
                    prefixes = [guild_prefix or config.Bleed.prefix]
                ctx = await self.get_context(message)
                if not ctx.command and not any(
                    message.content.startswith(prefix) for prefix in prefixes
                ):
                    response = f"Your **prefix** is: `{' '.join(prefixes)}`"
                    await message.neutral(response)
            except Exception as e:
                log.error(f"Failed to fetch prefixes or send message: {e}")

        if (
            message.guild.system_channel_flags.premium_subscriptions
            and message.type
            in (
                MessageType.premium_guild_subscription,
                MessageType.premium_guild_tier_1,
                MessageType.premium_guild_tier_2,
                MessageType.premium_guild_tier_3,
            )
        ):
            self.dispatch(
                "member_boost",
                message.author,
            )

        ctx = await self.get_context(message)
        if not ctx.command:
            self.dispatch("user_message", ctx, message)

        # Check for aliases
        if message.guild:
            ctx = await self.get_context(message)
            if ctx.prefix:
                # Add check for content after prefix
                content_after_prefix = message.content[len(ctx.prefix) :].strip()
                if content_after_prefix:  # Only process if there's content after prefix
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

    async def connect_nodes(self) -> None:
        for _ in range(config.LAVALINK.NODE_COUNT):
            await NodePool().create_node(
                bot=self,
                host=config.LAVALINK.HOST,
                port=config.LAVALINK.PORT,
                password=config.LAVALINK.PASSWORD,
                identifier=f"MAIN{tuuid()}",
                spotify_client_id=config.Authorization.SPOTIFY.CLIENT_ID,
                spotify_client_secret=config.Authorization.SPOTIFY.CLIENT_SECRET,
            )

    async def on_command_error(self, ctx: Context, error: Exception) -> Message:
        ignored = (
            CommandNotFound,
            NotOwner,
            CheckFailure,
            DisabledCommand,
            UserInputError,
        )
        if type(error) in ignored:
            return

        elif isinstance(error, MissingRequiredArgument):
            return await ctx.send_help()

        elif isinstance(error, MissingPermissions):
            return await ctx.warn(
                f"You're **missing** {Plural(error.missing_permissions, number=False):permission}: "
                + ", ".join(
                    [f"`{permission}`" for permission in error.missing_permissions]
                )
            )

        elif isinstance(error, CommandOnCooldown):
            return await ctx.neutral(
                f"{ctx.author.mention}: Please wait **{error.retry_after:.2f} seconds** before using this command again",
                color=config.Color.cooldown,
                emoji=config.Emoji.cooldown,
                delete_after=10,
            )

        elif isinstance(error, MaxConcurrencyReached):
            pass

        elif isinstance(error, BadArgument):
            return await ctx.deny(error)

        elif isinstance(error, BadUnionArgument):
            if error.converters == (Member, User):
                return await ctx.warn(
                    "I was unable to find that **member** or the **ID** is invalid"
                )

            elif error.converters == (Guild, Invite):
                return await ctx.warn("Invalid **invite code** given")

            else:
                return await ctx.warn(
                    f"Could not convert **{error.param.name}** into "
                    + human_join(
                        [f"`{converter.__name__}`" for converter in error.converters]
                    )
                )

        elif isinstance(error, MemberNotFound):
            return await ctx.warn(
                "I was unable to find that **member** or the **ID** is invalid"
            )

        if isinstance(error, BotMissingPermissions):
            return await ctx.warn(f"I am missing sufficient permissions to do that!")

        elif isinstance(error, UserNotFound):
            return await ctx.warn(
                "I was unable to find that **user** or the **ID** is invalid"
            )

        elif isinstance(error, RoleNotFound):
            return await ctx.warn(
                f"I was unable to find a role with the name: **{error.argument}**"
            )

        elif isinstance(error, ChannelNotFound):
            return await ctx.warn(
                f"I was unable to find a channel with the name: **{error.argument}**"
            )

        elif isinstance(error, GuildNotFound):
            if error.argument.isdigit():
                return await ctx.warn(
                    f"I do not **share a server** with the ID `{error.argument}`"
                )
            else:
                return await ctx.warn(
                    f"I do not **share a server** with the name `{error.argument}`"
                )

        elif isinstance(error, BadInviteArgument):
            return await ctx.warn("Invalid **invite code** given")

        elif isinstance(error, CommandInvokeError):
            if isinstance(error.original, HTTPException):
                if error.original.code == 50035:
                    return await ctx.warn(
                        "**Invalid code**" f"```\n{error.original}```"
                    )

                elif error.original.code == 50013:
                    return await ctx.warn("I'm missing necessary **permissions**!")

                elif error.original.code == 60003:
                    return await ctx.warn(
                        f"**{self.application.owner}** doesn't have **2FA** enabled!"
                    )

            elif isinstance(error.original, ClientConnectorError):
                return await ctx.warn("**API** no longer exists")

            elif isinstance(error.original, ClientResponseError):
                if error.original.status == 522:
                    return await ctx.warn(
                        "**Timed out** while requesting data - probably the API's fault"
                    )
                else:
                    return await ctx.warn(
                        f"**API** returned a `{error.original.status}` - try again later"
                    )

            elif isinstance(error.original, ContentTypeError):
                return await ctx.warn(
                    "**API** returned an error for that request - try again later"
                )

        if "*" in str(error) or "`" in str(error):
            return await ctx.warn(str(error))

        else:
            unique_id = token_urlsafe(8)
            traceback_text = "".join(
                traceback.format_exception(type(error), error, error.__traceback__, 4)
            )

            try:
                await self.db.execute(
                    """
                    INSERT INTO traceback 
                    (error_id, command, guild_id, channel_id, user_id, traceback, timestamp) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    unique_id,
                    ctx.command.qualified_name if ctx.command else "Unknown",
                    ctx.guild.id if ctx.guild else None,
                    ctx.channel.id,
                    ctx.author.id,
                    traceback_text,
                    utcnow(),
                )
                log.info(f"Stored traceback with error ID: {unique_id}")
            except Exception as db_error:
                log.error(f"Failed to store traceback in database: {db_error}")

            await ctx.send(f"`{unique_id}`")
            return await ctx.warn(
                f"Error occurred while performing command `{ctx.command}`"
                f"\nUse the given error code to report it to the developers in the [`support server`]({config.Bleed.support})."
            )
