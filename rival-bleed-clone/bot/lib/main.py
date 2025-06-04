from .patch.context import Context, Cache
import discord
import tuuid
import os
from discord.ext import commands
from asyncio import ensure_future, gather, sleep
from discord import Message, Guild, Intents, Client, Message
from pathlib import Path
from typing import Optional, Union, Dict, Any, Type
from discord.ext.commands import (
    AutoShardedBot as DiscordBot,
    when_mentioned_or,
    CommandError,
    BotMissingPermissions,
)
from .error_handler import Errors
from .classes import Database, RivalRedis, Snipe
from .classes import converters
from typing_extensions import NoReturn
from .worker import start_dask, close_dask
from .services import setup
import traceback
from .classes import Script, Level
from var.config import CONFIG
from lib.services.YouTube import repost as repost_youtube
from lib.services.TikTok import repost as repost_tiktok
from lib.services.Twitter import repost as repost_twitter
from async_timeout import timeout
from loguru import logger
from cashews import cache
from pydantic import BaseModel
from aiohttp import ClientSession
from DataProcessing import ServiceManager
from DataProcessing.models.authentication import Credentials
import datetime
from tornado.ioloop import IOLoop

try:
    from .views import Interface
except Exception:
    pass
from .classes.watcher import RebootRunner
from .patch import *

os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
os.environ["JISHAKU_RETAIN"] = "True"

cache.setup("mem://")


def repost(bot: Client, message: Message):
    repost_youtube(bot, message)
    repost_tiktok(bot, message)
    repost_twitter(bot, message)


class MessageLink(BaseModel):
    guild_id: int
    channel_id: int
    message_id: int

    async def fetch(self: "MessageLink", bot: "Bot") -> Optional[Message]:
        if not (guild := bot.get_guild(self.guild_id)):
            return
        if not (channel := guild.get_channel(self.channel_id)):
            return
        return await bot.fetch_message(channel, self.message_id)

    @classmethod
    def from_link(cls: Type["MessageLink"], link: str):
        """Parse a message link and return a MessageLink object."""
        if "channels/" in link:
            guild_id, channel_id, message_id = link.split("channels/")[1].split("/")
            return cls(
                guild_id=int(guild_id),
                channel_id=int(channel_id),
                message_id=int(channel_id),
            )


class Bot(DiscordBot):
    def __init__(self, config: Dict[str, Any], *args, **kwargs) -> None:
        self.slow_chunking = kwargs.pop("slow_chunk", False)
        super().__init__(
            command_prefix=self.get_prefix,
            allowed_mentions=discord.AllowedMentions(
                users=True, roles=False, everyone=False
            ),
            strip_after_prefix=True,
            intents=Intents().all(),
            case_insensitive=True,
            auto_update=False,
            owner_ids=config["owners"],
            anti_cloudflare_ban=True,
            chunk_guilds_at_startup=True if not self.slow_chunking else False,
            help_command=None,
            *args,
            **kwargs,
        )
        self.config = config
        self.db = Database()
        self.ioloop: IOLoop
        self.object_cache = Cache(self)
        self.redis = RivalRedis()
        self.errors = Errors(self)
        self.snipes = Snipe(self)
        self.startup_time = datetime.datetime.now()
        self.color = 0xD6BCD0  # 0x747f8d
        self.loaded = False
        self.command_dict = None
        self.filled = False
        self.runners = RebootRunner(self, ["ext", "etc", "owner", "vip"])
        self.support_server = ""
        self._closing_task = None
        self.domain = self.config["domain"] or "https://bleed.bot"
        self._cd = commands.CooldownMapping.from_cooldown(
            5.0, 10.0, commands.BucketType.user
        )
        # self.paginators = Paginate(self)

    async def close(self: "Bot"):
        await close_dask()
        await self.db.close()
        try:
            await super().close()
        except Exception:
            pass
        os._exit(0)

    async def setup_dask(self: "Bot"):
        self.dask = await start_dask(self, "127.0.0.1:8787")

    async def guild_count(self: "Bot") -> int:
        return len(self.guilds)

    async def user_count(self: "Bot") -> int:
        return sum([i for i in self.get_all_members()])

    async def setup_database(self: "Bot") -> bool:
        with open("var/postgresql.sql", "r") as file:
            queries = file.read().split(";")
        failed = []
        for query in queries:
            query = f"{query};"
            if "EXISTS" in query:
                table_name = query.split("EXISTS ", 1)[1].split(" (")[0]
            try:
                await self.db.execute(query)
            except Exception as e:
                failed.append(table_name)
        if len(failed) == 0:
            logger.info(
                f"Exectuted All of the {len(queries)} Database Queries Successfully"
            )
        else:
            logger.info(
                f"Failed to do queries to the following tables {', '.join(f for f in failed)}"
            )
        await self.db.migrate()
        return True

    async def create_embed(self, code: str, **kwargs):
        builder = Script(code, **kwargs)
        await builder.compile()
        return builder

    async def send_embed(
        self: "Bot",
        destination: Union[Context, discord.abc.GuildChannel],
        code: str,
        **kwargs: Any,
    ):
        view = kwargs.pop("view", None)
        builder = await self.create_embed(code, **kwargs)
        try:
            return await builder.send(destination, view=view)
        except discord.HTTPException as exc:
            if exc.code == 50006:
                return await destination.send(
                    **self.build_error(
                        "Something went wrong while parsing this embed script."
                    )
                )
            raise

    async def send_exception(self, ctx: Context, exception: Exception):
        code = tuuid.tuuid()
        tb = "".join(
            traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
        )
        await self.db.execute(
            """INSERT INTO traceback (command, error_code, error_message, guild_id, channel_id, user_id, content) VALUES($1, $2, $3, $4, $5, $6, $7)""",
            ctx.command.qualified_name if ctx.command else "repost",
            code,
            tb,
            ctx.guild.id,
            ctx.channel.id,
            ctx.author.id,
            ctx.message.content,
        )
        return await ctx.send(
            content=f"{code}",
            embed=discord.Embed(
                description=f"{CONFIG['emojis']['warning']} {ctx.author.mention}: Error occurred while performing command **{ctx.command.qualified_name if ctx.command else 'repost'}**. Use the given error code to report it to the developers in the [support server](https://discord.gg/coffin)",
                color=0xE69705,
            ),
        )

    async def setup_hook(self: "Bot") -> NoReturn:
        await self.setup_emojis()
        try:
            self.add_view(Interface(self))
        except Exception:
            pass
        self.ioloop = IOLoop.current()
        await self.load_extension("jishaku")
        ensure_future(self.setup_dask())
        await self.db.connect()
        await self.redis.from_url("redis://127.0.0.1:6379")
        self.services = ServiceManager(
            self.redis,
            Credentials(
                **{
                    "instagram": {
                        "id": "",
                        "password": "",
                        "authenticator": "",
                        "mail": "",
                        "mail_pass": " ,",
                        "smtp_host": "",
                        "smtp_port": 465,
                    }
                }
            ),
            None,
        )
        self.levels = Level(0.5, self)
        await self.setup_database()
        self.check(self.command_check)
        await self.runners.start()  # await gather(*[runner.start() for runner in self.runners])

    async def __load(self, cog: str):
        try:
            await self.load_extension(cog)
            logger.info(f"[ Loaded ] {cog}")
        except commands.errors.ExtensionAlreadyLoaded:
            pass
        except Exception as e:
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.info(f"Failed to load {cog} due to exception: {tb}")

    async def slow_chunk(self: "Bot"):
        async def chunk_guild(guild: Guild, index: int, total: int):
            await sleep(1.5)

            if guild.chunked is False:
                await guild.chunk(cache=True)
                if index % 100 == 0:
                    logger.info(f"Successfully chunked {index}/{total}")

        sorted_guilds = sorted(self.guilds, key=lambda g: g.member_count, reverse=True)
        total = len(sorted_guilds)
        for i, guild in enumerate(sorted_guilds, start=1):
            if guild.id != 1 and guild.chunked is False:
                await sleep(1e-3)
                await self.loop.create_task(chunk_guild(guild, i, total))

    async def on_ready(self: "Bot"):
        try:
            await self.setup_emojis()
        except Exception:
            pass
        if not self.loaded:
            await self.levels.setup(self)
            await self.load_cogs()
            await self.load_extension("lib.classes.web")
            self.webserver = self.get_cog("WebServer")
        if self.slow_chunking:
            await self.slow_chunk()

    async def load_cogs(self: "Bot") -> bool:
        if self.loaded is not False:
            return True
        from pathlib import Path

        excluded_commands = []
        excluded_events = []

        cogs = [
            str(p).replace("/", ".").replace("//", ".").replace("\\", ".")
            for p in Path("ext/").glob("*")
            if p.is_dir() and "pycache" not in str(p)
        ]
        cogs.extend(
            [
                f'etc.{str(c).split("/")[-1].split(".")[0]}'
                for c in Path("etc/").glob("*.py")
                if str(c).split("/")[-1].split(".")[0] not in excluded_events
            ]
        )
        cogs.extend(
            [
                f'owner.{str(c).split("/")[-1].split(".")[0]}'
                for c in Path("owner/").glob("*.py")
            ]
        )
        await gather(*[self.__load(c) for c in cogs])
        self.loaded = True

    async def command_check(self: "Bot", ctx: Context):
        COOLDOWN_MAPPING = {
            "guild": ctx.guild.id,
            "channel": ctx.channel.id,
            "user": ctx.author.id,
            "member": ctx.author.id,
        }
        missing_perms = []
        if restrictions := await self.db.fetchrow(
            """SELECT role_id FROM command_restrictions WHERE guild_id = $1 AND command = $2""",
            ctx.guild.id,
            ctx.command.qualified_name.lower(),
        ):
            role_mentions = []
            val = False
            author_roles = [r.id for r in ctx.author.roles]
            for restriction in restrictions:
                if role := ctx.guild.get_role(restriction.role_id):
                    role_mentions.append(role.mention)
                if restriction.role_id in author_roles:
                    val = True
                    break
            if not val and role_mentions:
                raise CommandError(
                    f"The only **roles** that can use `{ctx.command.qualified_name.lower()}` are {', '.join(role_mentions)}"
                )
        if disabled := await self.db.fetch(
            """SELECT object_ids, object_types FROM disabled_commands WHERE guild_id = $1 AND command = $2""",
            ctx.guild.id,
            ctx.command.qualified_name,
        ):
            if ctx.author.id in disabled.object_ids:
                return False
            elif ctx.channel.id in disabled.object_ids:
                return False
        if await self.db.fetchrow(
            """SELECT * FROM blacklists WHERE object_id = $1 AND object_type = $2""",
            ctx.author.id,
            "user",
        ):
            return False
        if await self.db.fetchrow(
            """SELECT * FROM blacklists WHERE object_id = $1 AND object_type = $2""",
            ctx.guild.id,
            "guild",
        ):
            return False
        if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            missing_perms.append("send_messages")
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            missing_perms.append("embed_links")
        if not ctx.channel.permissions_for(ctx.guild.me).attach_files:
            missing_perms.append("attach_files")
        if len(missing_perms) > 0:
            raise BotMissingPermissions(missing_perms)
        if retry_after := await ctx.bot.object_cache.ratelimited(
            f"rl:user_commands{ctx.author.id}", 2, 4
        ):
            raise commands.CommandOnCooldown(None, retry_after, None)
        if cooldown_override := ctx.command.extras.get("cooldown"):

            if len(cooldown_override) == 2:
                limit, timeframe = cooldown_override
                cooldown_type = "member"
            else:
                limit, timeframe, cooldown_type = cooldown_override

            if retry_after := await ctx.bot.object_cache.ratelimited(
                f"rl:{ctx.command.qualified_name}:{COOLDOWN_MAPPING.get(cooldown_type.lower())}",
                limit,
                timeframe,
            ):
                raise commands.CommandOnCooldown(
                    ctx.command, retry_after, cooldown_type
                )
        return True

    async def on_guild_join(self: "Bot", guild: Guild):
        if not guild.owner_id == self.user.id:
            if not await self.db.fetchrow(
                """SELECT * FROM authorizations WHERE guild_id = $1""", guild.id
            ):
                return await guild.leave()
            if await self.db.fetchrow(
                """SELECT * FROM blacklists WHERE object_id = $1 AND object_type = $2""",
                guild.id,
                "guild",
            ):
                return await guild.leave()
            await self.db.execute(
                """UPDATE authorizations SET owner_id = $1 WHERE guild_id = $2""",
                guild.owner_id,
                guild.id,
            )
            self.dispatch("guild_add", guild)

    async def find_guilds(self):
        guilds = [g for g in self.guilds if g.owner_id == self.user.id]
        if len(guilds) == 2:
            return [guilds[0], guilds[1]]
        elif len(guilds) == 1:
            return [guilds[0], await self.create_guild(name="emojis2")]
        else:
            return [
                await self.create_guild(name="emojis"),
                await self.create_guild(name="emojis2"),
            ]

    async def get_image(self, url: str) -> bytes:
        async with ClientSession() as session:
            async with session.request("HEAD", url) as head:
                if int(head.headers.get("Content-Length", 5)) > 52428800:
                    raise CommandError("Content Length Too Large")
                if "image/" not in head.content_type:
                    raise CommandError(f"Invalid content type of `{head.content_type}`")
            async with session.request("GET", url) as response:
                _ = await response.read()
        return _

    @cache(key="emojis", ttl=300)
    async def get_emojis(self: "Bot"):
        return await self.fetch_application_emojis()

    async def create_emoji(self: "Bot", name: str, data: bytes):
        app_emojis = await self.get_emojis()
        for emoji in app_emojis:
            if emoji.name == name:
                return emoji
        return await self.create_application_emoji(name=name, image=data)

    async def setup_emojis(self: "Bot"):
        try:
            if CONFIG["emojis"]["interface"].get("lock", "") not in ("", ""):
                return
        except Exception:
            pass

        for p in Path("../assets/emojis").glob("*"):
            path_name = str(p).split("/")[-1]
            if path_name.lower() == "embeds":
                for image in p.glob("*"):
                    emoji_name = str(image).split("/")[-1].split(".")[0]
                    if CONFIG["emojis"].get(emoji_name, "") != "":
                        continue
                    try:
                        with open(str(image), "rb") as file:
                            image_bytes = file.read()
                        emoji = await self.create_emoji(emoji_name, image_bytes)
                        CONFIG["emojis"][emoji_name] = str(emoji)
                    except Exception:
                        pass
            else:
                try:
                    if (
                        list(CONFIG["emojis"].get(path_name.lower(), {}).values())[0]
                        != ""
                    ):
                        continue
                except Exception:
                    pass
                CONFIG["emojis"][path_name.lower()] = {}
                for image in p.glob("*"):
                    emoji_name = str(image).split("/")[-1].split(".")[0]
                    try:
                        with open(str(image), "rb") as file:
                            image_bytes = file.read()
                    except Exception:
                        continue
                    emoji = await self.create_emoji(emoji_name, image_bytes)
                    CONFIG["emojis"][path_name.lower()][emoji_name] = str(emoji)
        with open("var/config.py", "w") as file:
            value = """
from discord import Intents  
from dotenv import load_dotenv
import os

load_dotenv(verbose = True)"""
            value += f"\nCONFIG = {CONFIG}"
            file.write(value)
        logger.info("Successfully setup all Emojis and the configuration")
        await self.close()

    async def get_prefix(self: "Bot", message: Message):
        user_prefix = await self.db.fetchval(
            """SELECT prefix FROM self_prefix WHERE user_id = $1""",
            message.author.id,
        )

        server_prefixes = await self.db.fetchval(
            """SELECT prefixes FROM config WHERE guild_id = $1""",
            message.guild.id,
        )

        if not server_prefixes:
            server_prefixes = [","]

        if isinstance(server_prefixes, list):
            server_prefix = next(
                (char for char in message.content if char in server_prefixes), None
            )
            if server_prefix:
                return when_mentioned_or(server_prefix)(self, message)

        if user_prefix and message.content.strip().startswith(user_prefix):
            return when_mentioned_or(user_prefix)(self, message)

        return when_mentioned_or(server_prefixes[0])(self, message)

    def run(self: "Bot"):
        super().run(self.config["token"])

    @cache(key="fetch_message:{message_id}", ttl=300)
    async def fetch_message(
        self: "Bot", channel: discord.abc.GuildChannel, message_id: int
    ):
        if message := discord.utils.get(self.cached_messages, id=message_id):
            return message
        try:
            return await channel.fetch_message(message_id)
        except discord.HTTPException:
            return None

    async def get_reference(self: "Bot", message: discord.Message):
        if message.reference:
            if msg := message.reference.cached_message:
                return msg
            else:
                g = self.get_guild(message.reference.guild_id)
                if not g:
                    return None
                c = g.get_channel(message.reference.channel_id)
                if not c:
                    return None
                return await self.fetch_message(c, message.reference.message_id)
        return None

    async def get_message(
        self: "Bot", argument: Union[Context, str], argument2: Optional[str] = None
    ) -> Optional[Message]:
        if isinstance(argument, Context):
            if argument2:
                if "channels/" in argument2:
                    Link = MessageLink.from_link(argument2)
                    return await Link.fetch(self)
                else:
                    try:
                        message_id = int(argument2)
                        return await self.fetch_message(argument.channel, message_id)
                    except Exception:
                        pass
                return await self.fetch_message(argument.channel, argument2)
            else:
                if reference := await self.get_reference(argument.message):
                    return reference
        else:
            if "channels/" in argument:
                Link = MessageLink.from_link(argument)
                return await Link.fetch(self)
        return None

    def get_command_dict(self: "Bot") -> list:
        if self.command_dict:
            return self.command_dict

        def get_command_invocations(command, prefix=""):
            invocations = []

            base_command = prefix + command.name
            invocations.append(base_command)

            for alias in command.aliases:
                invocations.append(prefix + alias)

            if isinstance(command, commands.Group):
                for subcommand in command.commands:
                    sub_invocations = get_command_invocations(
                        subcommand, prefix=base_command + " "
                    )
                    for alias in command.aliases:
                        sub_invocations.extend(
                            get_command_invocations(
                                subcommand, prefix=prefix + alias + " "
                            )
                        )
                        invocations.extend(sub_invocations)

            return invocations

        self.command_dict = []
        for command in self.walk_commands():
            for invocation in get_command_invocations(command):
                self.command_dict.append(invocation)
        return self.command_dict

    async def on_command_error(self: "Bot", ctx: Context, exception: Exception):
        return await self.errors.handle_exceptions(ctx, exception)

    @cache(ttl="1m", key="context:{message.id}")
    async def get_context(self: "Bot", message: Message, *, cls=Context):
        context = await super().get_context(message, cls=cls)
        if not self.filled and self.is_ready():
            await self._fill(context)
            self.filled = True
        return context

    async def on_message(self: "Bot", message: Message):
        if (
            not (message.author.bot)
            and (message.channel.permissions_for(message.guild.me).send_messages)
            and (message.guild)
            and self.is_ready()
        ):
            ctx = await self.get_context(message)
            self.dispatch("context", ctx)
            if await self.db.fetchrow(
                """SELECT * FROM silenced WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                ctx.author.id,
            ):
                await message.delete()
                return
            if not ctx.valid:
                self.dispatch("valid_message", ctx)
                if message.content.lower().startswith(self.user.name.lower()):
                    self.dispatch("media_repost", ctx)
                if await self.db.fetchval(
                    """SELECT reposting FROM config WHERE guild_id = $1 AND reposting = TRUE""",
                    ctx.guild.id,
                ):
                    self.dispatch("media_repost", ctx)  # repost(self, message)
            self.dispatch("afk_check", ctx)
            if message.mentions_bot(strict=True):
                if (
                    await self.object_cache.ratelimited(
                        f"prefix_pull:{ctx.guild.id}", 1, 5
                    )
                    != 0
                ):
                    return await ctx.normal(
                        f"Guild Prefix is `{await ctx.display_prefix()}`"
                    )
        await self.process_commands(message)

    async def on_message_edit(self: "Bot", before: Message, after: Message):
        if before.content != after.content and not after.author.bot:
            await self.on_message(after)

    async def on_command_completion(self, ctx: Context) -> None:
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
        logger.info(f"{ctx.guild.id} > {ctx.author.name}: {ctx.message.content}")

    async def on_member_remove(self, member: discord.Member) -> None:
        if member.premium_since:
            self.dispatch(
                "member_unboost",
                member,
            )

    async def on_audit_log_entry_create(self, entry: discord.AuditLogEntry) -> None:
        if not self.is_ready() or not entry.guild:
            return

        event = "audit_log_entry_" + entry.action.name
        self.dispatch(
            event,
            entry,
        )

    async def on_member_update(
        self, before: discord.Member, member: discord.Member
    ) -> None:
        if before.pending and not member.pending:
            self.dispatch(
                "member_agree",
                member,
            )

        if booster_role := member.guild.premium_subscriber_role:
            if (booster_role in before.roles) and (booster_role not in member.roles):
                self.dispatch(
                    "member_unboost",
                    before,
                )

            elif (
                system_flags := member.guild.system_channel_flags
            ) and system_flags.premium_subscriptions:
                return

            elif (booster_role not in before.roles) and (booster_role in member.roles):
                self.dispatch(
                    "member_boost",
                    member,
                )
