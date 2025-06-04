# Standard Library imports
import asyncio
import glob
import importlib
import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from contextlib import suppress
from datetime import datetime, timezone
from os import environ
from pathlib import Path
from secrets import token_urlsafe
from typing import Dict, List, Optional

# Local imports
import config
# Third-party imports
from aiohttp.client_exceptions import (ClientConnectorError,
                                       ClientResponseError, ContentTypeError)
from cashews import cache
from core.client import database
from core.client.browser import BrowserHandler
from core.client.cache.redis import Redis
from core.client.context import Context
from core.client.database.settings import Settings
from core.client.network import ClientSession
from core.managers.help import MonoHelp
from core.managers.ratelimiter import ratelimiter
from core.tools import Error, codeblock, human_join
from core.tools.logging import logger as log
from discord import (AllowedMentions, AuditLogAction, ChannelType, Forbidden,
                     Guild, HTTPException, Intents, Interaction, Invite,
                     Member, Message, NotFound, Status, User)
from discord.ext.commands import (AutoShardedBot, BadColourArgument,
                                  BadFlagArgument, BadInviteArgument,
                                  BadLiteralArgument, BadUnionArgument,
                                  BotMissingPermissions, BucketType,
                                  ChannelNotFound, CheckFailure, CommandError,
                                  CommandInvokeError, CommandNotFound,
                                  CommandOnCooldown, CooldownMapping,
                                  DisabledCommand, Flag, FlagError,
                                  MemberNotFound, MissingFlagArgument,
                                  MissingPermissions, MissingRequiredArgument,
                                  MissingRequiredAttachment,
                                  MissingRequiredFlag, NotOwner, RangeError,
                                  TooManyFlags, UserInputError, UserNotFound,
                                  when_mentioned_or)
from discord.utils import utcnow
from redis.asyncio import Redis
from tornado.ioloop import IOLoop

environ["JISHAKU_HIDE"] = "True"
environ["JISHAKU_RETAIN"] = "True"
environ["JISHAKU_NO_UNDERSCORE"] = "True"
environ["JISHAKU_SHELL_NO_DM_TRACEBACK"] = "True"

cache.setup(f"redis://{config.Redis.host}:{config.Redis.port}/{config.Redis.db}")


class Mono(AutoShardedBot):
    def __init__(self: "Mono", *args, **kwargs):
        super().__init__(
            command_prefix=self.get_prefix,
            allowed_mentions=AllowedMentions(
                replied_user=False,
                everyone=False,
                roles=False,
                users=True,
            ),
            help_command=MonoHelp(),
            shard_count=1,
            intents=Intents.all(),
            mobile_status=True,
            case_insensitive=True,
            owner_ids=config.Mono.owner,
            status=Status.dnd,
            *args,
            **kwargs,
        )
        self.check(lambda ctx: ctx.guild)
        self.redis: Redis = Redis()
        self.uptime2 = time.time()
        self.cache = cache
        self.uptime = datetime.now(timezone.utc)
        self.traceback: Dict[str, Dict] = {}
        self.global_cooldown = CooldownMapping.from_cooldown(4, 3, BucketType.user)
        self.add_check(self.global_rate_limit)
        self.browser_handler = BrowserHandler()
        self.browser = None
        self.version = "v1.5"
        self.blacktea_matches = {}
        self.blackjack_matches = []

    async def get_prefix(self: "Mono", message: Message) -> List[str]:
        try:
            prefix = await Settings.get_prefix(self, message)
        except Exception as e:
            log.error(f"Failed to fetch prefix: {e}")
            prefix = config.Mono.prefix

        return when_mentioned_or(prefix)(self, message)

    async def start_bot(self):
        token = config.Mono.token
        if not token:
            log.error("Discord token not found in environment variables.")
            return
        await self.start(token)

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

    async def setup_hook(self: "Mono"):
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
        self.browser = self.browser_handler  # Set the browser attribute

    async def load_patches(self) -> None:
        modules = [
            module.replace(os.path.sep, ".").replace("/", ".").replace(".py", "")
            for module in glob.glob("core/managers/patches/**/*.py", recursive=True)
            if not module.endswith("__init__.py")
        ]

        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            # Use asyncio.gather to load patches concurrently
            tasks = [
                loop.run_in_executor(pool, importlib.import_module, module)
                for module in modules
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for module, result in zip(modules, results):
                if isinstance(result, Exception):
                    if isinstance(result, (ModuleNotFoundError, ImportError)):
                        log.error(f"Error importing {module}: {result}")
                    else:
                        log.error(f"Unexpected error importing {module}: {result}")
                else:
                    log.info(f"Patched: {module}")

    async def on_ready(self: "Mono") -> None:
        log.info(f"Logged in as {self.user}.")

    async def global_rate_limit(self, ctx: Context) -> bool:
        #        if ctx.author.id in self.owner_ids:
        #            return True  # Exempt owners from cooldown
        bucket = self.global_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if retry_after:
            raise CommandOnCooldown(bucket, retry_after, BucketType.user)
        return True

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

    async def process_commands(self: "Mono", message: Message) -> None:
        # Check if the message is from a DM channel
        if message.guild or message.channel.type == ChannelType.private:  # Allow DMs
            if message.content.startswith(tuple(await self.get_prefix(message))):
                if not ratelimiter(
                    bucket=f"{message.channel.id}", key="globalratelimit", rate=3, per=3
                ):
                    return await super().process_commands(
                        message
                    )  # Process commands in DMs

    async def on_message_edit(self, before: Message, after: Message) -> None:
        if before.content == after.content:
            return
        return await self.process_commands(after)

    async def on_message(self, message: Message) -> None:
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
                    prefixes = [guild_prefix or config.Mono.prefix]

                # Check if the message is a command
                ctx = await self.get_context(message)
                if not ctx.command and not any(
                    message.content.startswith(prefix) for prefix in prefixes
                ):
                    response = f"Your **prefix** is: `{' '.join(prefixes)}`"
                    await message.neutral(response)
            except Exception as e:
                log.error(f"Failed to fetch prefixes or send message: {e}")

        # Check for aliases
        if message.guild:
            ctx = await self.get_context(message)
            if ctx.prefix:
                invoked_with = message.content[len(ctx.prefix) :].split()[0].lower()
                alias = await self.db.fetchval(
                    """
                    SELECT invoke
                    FROM aliases
                    WHERE guild_id = $1 AND name = $2
                    """,
                    message.guild.id,
                    invoked_with,
                )
                if alias:
                    message.content = f"{ctx.prefix}{alias} {message.content[len(ctx.prefix) + len(invoked_with):].strip()}"

        await self.process_commands(message)

    async def get_context(
        self, origin: Message | Interaction, /, *, cls=Context
    ) -> Context:
        context = await super().get_context(origin, cls=cls)
        if context.guild:  # Ensure the message is from a guild
            context.settings = await Settings.fetch(self, context.guild)
        return context

    async def on_command(self: "Mono", ctx: Context) -> None:
        log.info(
            f"{ctx.author} ({ctx.author.id}) executed {ctx.command} in {ctx.guild} ({ctx.guild.id})."
        )

    async def on_command_error(
        self: "Mono", ctx: Context, exception: CommandError
    ) -> Optional[Message]:
        exception = getattr(exception, "original", exception)
        if type(exception) in (
            NotOwner,
            CheckFailure,
            DisabledCommand,
            CommandNotFound,
            UserInputError,
        ):
            return

        if isinstance(exception, CommandOnCooldown):
            # Ensure the warning message is sent
            return await ctx.warn(
                f"This command is on cooldown. Please try again in `{int(exception.retry_after)} seconds`",
                delete_after=10,
            )

        if isinstance(exception, MemberNotFound):
            return await ctx.warn(
                f"No **member** was found matching **{exception.argument}**!"
            )

        if isinstance(exception, UserNotFound):
            return await ctx.warn(
                f"No **user** was found matching `{exception.argument}`!"
            )

        if isinstance(exception, CommandError) and len(exception.args) == 2:
            return await ctx.warn(exception.args[0], exception.args[1])

        if isinstance(exception, MissingPermissions):
            return await ctx.warn(
                f"You don't have sufficient permissions to use `{ctx.command}`!"
            )

        if isinstance(exception, RangeError):
            return await ctx.warn(
                f"The value must be between `{exception.minimum}` and `{exception.maximum}`, received `{exception.value}`!"
            )

        if isinstance(exception, BadInviteArgument):
            return await ctx.warn("The provided invite wasn't found!")

        if isinstance(exception, BotMissingPermissions):
            return await ctx.warn(f"I am missing sufficient permissions to do that!")

        if isinstance(exception, BadFlagArgument):
            flag: Flag = exception.flag
            argument: str = exception.argument

            return await ctx.warn(
                f"Failed to convert `{flag}` with input `{argument}`"
                + (f"\n> {flag.description}" if flag.description else "")
            )

        if isinstance(exception, CommandInvokeError):
            if isinstance(exception.original, (HTTPException, NotFound)):
                if "Invalid Form Body" in exception.original.text:
                    try:
                        parts = "\n".join(
                            [
                                part.split(".", 3)[2]
                                + ":"
                                + part.split(".", 3)[3]
                                .split(":", 1)[1]
                                .split(".", 1)[0]
                                for part in exception.original.text.split("\n")
                                if "." in part
                            ]
                        )
                    except IndexError:
                        parts = exception.original.text

                    if not parts or "{" not in parts:
                        parts = exception.original.text
                    await ctx.warn(f"Your **script** is malformed\n```{parts}\n```")
                elif "Cannot send an empty message" in exception.original.text:
                    await ctx.warn("Your **script** doesn't contain any **content**")
                elif "Must be 4000 or fewer in length." in exception.original.text:
                    await ctx.warn("Your **script** content is too **long**")

        if isinstance(exception, BadColourArgument):
            color: str = exception.argument

            return await ctx.warn(
                f"Color `{color}` is not valid!"
                + (
                    "\n> Ensure it starts with `#`."
                    if not color.startswith("#") and len(color) == 6
                    else ""
                )
            )

        if isinstance(exception, MissingRequiredAttachment):
            return await ctx.warn("You need to provide an attachment!")

        if isinstance(exception, MissingRequiredArgument):
            return await ctx.send_help(ctx.command)

        if isinstance(
            exception,
            (MissingRequiredFlag, BadLiteralArgument),
        ):
            return await ctx.send_help(ctx.command)

        if isinstance(exception, Error):
            return await ctx.warn(exception.message)

        if isinstance(exception, CommandInvokeError):
            original = exception.original
            if isinstance(original, HTTPException):
                if original.code == 50013:
                    if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                        return await ctx.warn(
                            "I don't have the required **permissions** to do that!"
                        )
                elif original.code == 50045:
                    return await ctx.warn(
                        "The **provided asset** is too large to be used!"
                    )
            if isinstance(original, Forbidden) and original.code == 40333:
                return await ctx.warn(
                    "Discord is experiencing an **outage** at the moment!",
                    "You can check for updates by clicking [**here**](https://discordstatus.com/).",
                )
            return await self.log_traceback(ctx, original)

        if isinstance(exception, FlagError):
            if isinstance(exception, TooManyFlags):
                return await ctx.warn(
                    f"You specified the **{exception.flag.name}** flag more than once!"
                )
            if isinstance(exception, BadFlagArgument):
                annotation = getattr(
                    exception.flag.annotation,
                    "__name__",
                    exception.flag.annotation.__class__.__name__,
                )
                return await ctx.warn(
                    f"Failed to cast **{exception.flag.name}** to `{annotation}`!",
                    *(
                        ["Make sure you provide **on** or **off** for `Status` flags!"]
                        if annotation == "Status"
                        else []
                    ),
                )
            if isinstance(exception, MissingRequiredFlag):
                return await ctx.warn(
                    f"You must specify the **{exception.flag.name}** flag!"
                )
            if isinstance(exception, MissingFlagArgument):
                return await ctx.warn(
                    f"You must specify a value for the **{exception.flag.name}** flag!"
                )

        if isinstance(exception, BadUnionArgument):
            if exception.converters == (Member, User):
                return await ctx.warn(
                    f"No **{exception.param.name}** was found matching **{ctx.current_argument}**!",
                    "If the user is not in this server, try using their **ID** instead",
                )
            if exception.converters == (Guild, Invite):
                return await ctx.warn(
                    f"No server was found matching **{ctx.current_argument}**!"
                )
            return await ctx.warn(
                f"Casting **{exception.param.name}** to {human_join([f'`{c.__name__}`' for c in exception.converters])} failed!"
            )

        if isinstance(exception, HTTPException):
            code: int = exception.code

            if code == 50045:
                return await ctx.warn("The provided asset is too large!")

            elif code == 50013:
                return await ctx.warn("I am missing sufficient permissions!")

            elif code == 60003 and self.application:
                return await ctx.warn(
                    f"`{self.application.owner}` doesn't have **2FA** enabled!"
                )

            elif code == 50035:
                return await ctx.warn(
                    f"I wasn't able to send the message!\n>>> {codeblock(exception.text)}"
                )

        elif isinstance(exception, ClientConnectorError):
            return await ctx.warn("The **API** timed out during the request!")

        elif isinstance(exception, ClientResponseError):
            return await ctx.warn(
                f"The third party **API** returned a `{exception.status}`"
                + (
                    f" [*`{exception.message}`*](https://http.cat/{exception.status})"
                    if exception.message
                    else "!"
                )
            )

        elif isinstance(exception, ContentTypeError):
            return await ctx.warn("The **API** returned malformed content!")

        # New handling for CommandError
        elif isinstance(exception, CommandError):
            if not isinstance(exception, (CheckFailure, Forbidden)) and isinstance(
                exception, (HTTPException, NotFound)
            ):
                if "Unknown Channel" in exception.text:
                    return

                return await ctx.warn(f"{exception.text.capitalize()}")

            origin = getattr(exception, "original", exception)
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

        # If we've reached this point, it's an unhandled exception
        unique_id = token_urlsafe(8)
        traceback_text = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__, 4
            )
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

        return await ctx.warn(
            f"An unhandled exception occurred while processing `{ctx.command}`!"
            f"\n> I've stored the traceback as [`{unique_id}`]({config.Mono.support})."
        )
