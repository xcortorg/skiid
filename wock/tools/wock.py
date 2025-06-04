import log

log.make_dask_sink("rival")

import asyncio  # type: ignore
import datetime
import os
import traceback
# from loguru import logger
from logging import getLogger

import discord
import discord_ios  # type: ignore # noqa: F401
import orjson
import tuuid
from tools.views import VoicemasterInterface

logger = getLogger(__name__)
from sys import stdout
from typing import Any, Callable, Dict, Optional, Union

from aiohttp import ClientSession
from cogs.voicemaster import VmButtons
from discord import AuditLogEntry, Color, Guild, Message
from discord.ext import commands
from discord.ext.commands import AutoShardedBot as Bot
from discord.ext.commands import BotMissingPermissions, when_mentioned_or
from psutil import Process
# from tools import MemberConverter
from rival_tools import lock, ratelimit  # type: ignore
from tools.aliases import (CommandAlias, fill_commands,  # type: ignore
                           handle_aliases)
from tools.important import (Cache, Context, Database,  # type: ignore
                             MyHelpCommand, Red)
from tools.important.runner import RebootRunner  # type: ignore
from tools.important.subclasses.command import RolePosition  # type: ignore
from tools.important.subclasses.context import NonRetardedCache  # type: ignore
from tools.important.subclasses.interaction import \
    WockInteraction  # type: ignore # noqa: F401
from tools.important.subclasses.parser import Script  # type: ignore
from tools.modlogs import Handler  # type: ignore
from tools.paginate import Paginate  # type: ignore
# from cogs.tickets import TicketView
from tools.processing import Transformers
from tools.rival import RivalAPI, Statistics
from tools.rival import get_statistics as get_stats  # type: ignore
from tools.snipe import Snipe, SnipeError  # type: ignore
from tools.views import (GiveawayView,  # type: ignore # type: ignore
                         PrivacyConfirmation)

discord.Interaction.success = WockInteraction.success
discord.Interaction.fail = WockInteraction.fail
discord.Interaction.warning = WockInteraction.warning
discord.Interaction.normal = WockInteraction.normal
discord.Interaction.voice_client = WockInteraction.voice_client

get_changes = Union[
    Guild,
    AuditLogEntry,
]
loguru = False

if loguru:
    logger.remove()
    logger.add(
        stdout,
        level="INFO",
        colorize=True,
        enqueue=True,
        backtrace=True,
        format="<cyan>[</cyan><blue>{time:YYYY-MM-DD HH:MM:SS}</blue><cyan>]</cyan> (<magenta>wock:{function}</magenta>) <yellow>@</yellow> <fg #BBAAEE>{message}</fg #BBAAEE>",
    )


class iteration(object):
    def __init__(self, data: Any):
        self.data = data
        self.index = -1

    def __iter__(self):
        return self

    def __next__(self):
        self.index += 1
        if self.index > len(self.data) - 1:
            self.index = 0
        return self.data[self.index]


log = logger
user_pass = "http://envjafpk:bltpo5w914k6@"
ips = [
    "38.154.227.167:5868",
    "185.199.229.156:7492",
    "185.199.228.220:7300",
    "185.199.231.45:8382",
]
for i in ips:
    ips[ips.index(i)] = f"{user_pass}{i}"


class Wock(Bot):
    def __init__(self, config: Dict[str, Any], *args, **kwargs) -> None:
        super().__init__(
            command_prefix=self.get_prefix,
            allowed_mentions=discord.AllowedMentions(
                users=True, roles=False, everyone=False
            ),
            strip_after_prefix=True,
            intents=config["intents"],
            case_insensitive=True,
            owner_ids=config["owners"],
            anti_cloudflare_ban=True,
            enable_debug_events=True,
            delay_ready=True,
            help_command=MyHelpCommand(),
            #            proxy=f"{user_pass}{ips[1]}",
            *args,
            **kwargs,
        )
        self.proxies = ips
        self.modlogs = Handler(self)
        self.config = config
        self.paginators = Paginate(self)
        self.domain = self.config["domain"]
        self.startup_time = datetime.datetime.now()
        self.http.proxy = ""
        self.glory_cache = Cache(self)
        self.rival = RivalAPI(self)
        self.snipes = Snipe(self)
        self.avatar_limit = 50
        self.color = Color.dark_embed()
        self.afks = {}
        self.transformers = Transformers(self)
        self.process = Process(os.getpid())
        self.domain = "https://wock.bot"
        self.support_server = "https://discord.gg/kuwitty"
        self.author_only_message = "**only the `author` can use this**"
        self.cache = NonRetardedCache(self)
        self.http.iterate_local_addresses = False
        self.loaded = False
        self.guilds_maxed = True
        self.whitelisted = [
            1201627861493239919,
            1203455800236965958,
            991695158691254335,
        ]
        self.owner_channel = 1206309921654702080
        self.to_send = []
        self.authentication = [
            self.config["token"],
            "MTE4ODg1OTEwNzcwMTE2NjE2MQ.G22nb2.219btG_P7Y5MN0JlyU7OJHvIkdQ8dM9N6ybIJA",
        ]
        self.command_count = len(
            [
                cmd
                for cmd in list(self.walk_commands())
                if cmd.cog_name not in ("Jishaku", "events", "Owner")
            ]
        )
        self._cd = commands.CooldownMapping.from_cooldown(
            5.0, 10.0, commands.BucketType.user
        )
        self.eros = "52ab341c-58c0-42f2-83ba-bde19f15facc"
        self.check(self.command_check)

        self.before_invoke(self.before_all_commands)

    def get_timestamp(self, dt: Optional[datetime.datetime] = None, style: str = "R"):
        if dt is None:
            dt = datetime.datetime.now()
        return discord.utils.format_dt(dt, style=style)

    async def execute_function(self, func: Callable, *args, **kwargs) -> Optional[Any]:
        with logger.catch(reraise=True):
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

    def handle_ready(self):
        self.connected.set()

    async def before_all_commands(self, ctx: Context):
        ctx.timer = datetime.datetime.now().timestamp()
        if ctx.command is not None:
            if "purge" not in ctx.command.qualified_name:
                if (
                    ctx.channel.permissions_for(ctx.guild.me).send_messages
                    and ctx.channel.permissions_for(ctx.guild.me).embed_links
                    and ctx.channel.permissions_for(ctx.guild.me).attach_files
                ):
                    try:
                        await ctx.typing()
                    except Exception:
                        pass

    async def get_image(self, ctx: Context, *args):
        if len(ctx.message.attachments) > 0:
            return ctx.message.attachments[0].url
        elif ctx.message.reference:
            if msg := await self.get_message(
                ctx.channel, ctx.message.reference.message_id
            ):
                if len(msg.attachments) > 0:
                    return msg.attachments[0].url
                else:
                    logger.info(
                        f"there are no attachments for {msg} : {msg.attachments}"
                    )
            else:
                logger.info("could not get message")
        else:
            for i in args:
                if i.startswith("http"):
                    return i
        return None

    async def on_command_completion(self, ctx: Context):
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

    def is_touchable(self, obj: Union[discord.Role, discord.Member]) -> bool:
        def touchable(role: discord.Role) -> bool:
            guild = role.guild
            list(guild.roles)
            if role >= guild.me.top_role:
                return False
            return True

        if isinstance(obj, discord.Member):
            return touchable(obj.top_role)
        else:
            return touchable(obj)

    async def get_message(self, channel: discord.TextChannel, message_id: int):
        logger.info(f"getting message {message_id} in {channel.name}")
        if message := discord.utils.get(self.cached_messages, id=message_id):
            logger.info(f"getting it returned type {type(message)}")
            return message
        else:
            if m := await channel.fetch_message(message_id):
                logger.info(f"fetched message {m.id} in {channel.name}")
                return m
        return None

    def check_bot_hierarchy(self, guild: discord.Guild) -> bool:
        roles = sorted(guild.roles, key=lambda x: x.position, reverse=True)
        roles = roles[:5]
        if guild.me.top_role not in roles:
            del roles
            return False
        return True

    async def leave_guilds(self) -> int:
        i = 0
        for g in self.guilds:
            if g.id not in self.whitelisted and not await self.db.fetchrow(
                """SELECT * FROM auth WHERE guild_id = $1""", g.id
            ):
                if len(g.members) <= 75:
                    if owner := g.owner:
                        try:
                            await owner.send(
                                embed=discord.Embed(
                                    description=f"leaving your guild `{g.name}` due to not having above 75 members",
                                    color=self.color,
                                )
                            )
                        except Exception:
                            pass
                    await g.leave()
                    i += 1
        return i

    async def guild_count(self) -> int:
        i = 0
        if hasattr(self, "ipc"):
            i += sum([await self.ipc.guild_count(s) for s in self.sources])
        return len(self.guilds) + i

    async def user_count(self) -> int:
        i = 0
        if hasattr(self, "ipc"):
            i += sum([await self.ipc.member_count(s) for s in self.sources])
        return sum(self.get_all_members()) + i

    async def role_count(self) -> int:
        i = 0
        if hasattr(self, "ipc"):
            i = sum([await self.ipc.role_count(s) for s in self.sources])
        return sum(len(g.roles) for g in self.guilds) + i

    async def channel_count(self) -> int:
        i = 0
        if hasattr(self, "ipc"):
            i += sum([await self.ipc.channel_count(s) for s in self.sources])
        return sum(len(g.channels) for g in self.guilds) + i

    @property
    def invite_url(self, client_id: Optional[int] = None) -> str:
        if self.user.id == 1188859107701166161 and self.guilds_maxed is True:
            if len(self.guilds) <= 99:
                return discord.utils.oauth_url(
                    self.bot2.user.id,
                    scopes=["bot", "applications.commands"],
                    permissions=discord.Permissions(8),
                )
        return discord.utils.oauth_url(
            client_id or self.user.id,
            scopes=["bot", "applications.commands"],
            permissions=discord.Permissions(8),
        )

    async def limit_avatarhistory(self, user_id: int):
        data = await self.db.fetch(
            """SELECT * FROM avatars WHERE user_id = $1 ORDER BY time ASC""", user_id
        )
        if len(data) > self.avatar_limit:
            avatars_to_delete = [
                d["avatar"] for d in data[: len(data) - self.avatar_limit]
            ]
            await self.db.execute(
                """DELETE FROM avatars WHERE avatar = ANY($1::text[])""",
                avatars_to_delete,
            )
        return True

    async def get_changes(self, before: get_changes, after: get_changes):
        return

    async def process_commands(self, message: Message):
        if not message.guild:
            return

        check = await self.db.fetchrow(
            """
            SELECT * FROM blacklisted 
            WHERE (object_id = $1 AND object_type = $2) 
            OR (object_id = $3 AND object_type = $4)
        """,
            message.author.id,
            "user_id",
            message.guild.id,
            "guild_id",
        )

        if check:
            return
        if not self.is_ready():
            return

        return await super().process_commands(message)

    async def log_command(self, ctx: Context):
        log.info(
            f"{ctx.author} ({ctx.author.id}) executed {ctx.command} in {ctx.guild} ({ctx.guild.id})."
        )

    async def join_message(self, guild: discord.Guild):
        channels = [
            channel
            for channel in guild.text_channels
            if channel.permissions_for(guild.me).send_messages is True
        ]
        return await channels[0].send(
            embed=discord.Embed(
                title="Need Help?",
                url="https://wock.bot",
                description="Join our [support server](https://discord.gg/kuwitty) for help",
                color=self.color,
            )
            .add_field(
                name="Wock's default prefix is set to `,`",
                value="> To change the prefix use `,prefix (prefix)`\n> Ensure the bot's role is within the guild's top 5 roles for Wock to function correctly",
                inline=False,
            )
            .add_field(
                name="Commands to help you get started:",
                value="> **,setup** - Creates a jail and log channel along with the jail role \n> **,voicemaster setup** - Creates join to create voice channels\n> **,filter setup** - Initializes a setup for automod to moderate\n> **,antinuke setup** - Creates the antinuke setup to keep your server safe",
                inline=False,
            )
            .set_author(
                name="Wock",
                icon_url=self.user.avatar.url,  # Assuming self.user is your bot user object
            )
        )

    async def command_check(self, ctx):
        if not hasattr(self, "command_list"):
            await fill_commands(ctx)
        if await ctx.bot.is_owner(ctx.author):
            return True
        missing_perms = []
        if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
            missing_perms.append("send_messages")
        if not ctx.channel.permissions_for(ctx.guild.me).embed_links:
            missing_perms.append("embed_links")
        if not ctx.channel.permissions_for(ctx.guild.me).attach_files:
            missing_perms.append("attach_files")
        if len(missing_perms) > 0:
            raise BotMissingPermissions(missing_perms)
        check = await self.db.fetchrow(
            """
            SELECT * FROM blacklisted 
            WHERE (object_id = $1 AND object_type = $2) 
            OR (object_id = $3 AND object_type = $4)
        """,
            ctx.author.id,
            "user_id",
            ctx.guild.id,
            "guild_id",
        )
        if check:
            return False
        if restrictions := await self.db.fetch(
            """SELECT role_id FROM command_restriction WHERE guild_id = $1 AND command_name = $2""",
            ctx.guild.id,
            ctx.command.qualified_name,
        ):
            can_use = False
            for role_id in restrictions:
                if role := ctx.guild.get_role(role_id):
                    if role in ctx.author.roles:
                        can_use = True
                        break
            if can_use is False:
                roles = [
                    ctx.guild.get_role(role_id.role_id)
                    for role_id in restrictions
                    if ctx.guild.get_role(role_id.role_id) is not None
                ]
                mention = ", ".join(r.mention for r in roles)
                await ctx.fail(f"missing one of the following roles {mention}")
                return False
        if ctx.command.qualified_name == "reset":
            if retry_after := await ctx.bot.glory_cache.ratelimited(
                f"rl:user_commands{ctx.author.id}", 2, 4
            ):
                raise commands.CommandOnCooldown(None, retry_after, None)
            else:
                return True
        if (
            nodata := await self.db.fetchval(  # type: ignore  # noqa: F841
                """SELECT state FROM terms_agreement WHERE user_id = $1""",
                ctx.author.id,
            )
        ) is False:
            return False

        if not await self.db.fetch(
            """SELECT state FROM terms_agreement WHERE user_id = $1""", ctx.author.id
        ):
            message = await ctx.normal(
                f"Wock bot will store your data. **By continuing to use our services**, you agree to our **[policy]({self.domain}/terms)**"
            )
            await message.edit(
                view=(view := PrivacyConfirmation(message=message, invoker=ctx.author))
            )

            await view.wait()
            if view.value is None:
                await self.db.execute(
                    """INSERT INTO terms_agreement (user_id, state) VALUES ($1, $2) ON CONFLICT DO NOTHING;""",
                    ctx.author.id,
                    False,
                )
                return False
            elif view.value is False:
                await self.db.execute(
                    """INSERT INTO terms_agreement (user_id, state) VALUES ($1, $2) ON CONFLICT DO NOTHING;""",
                    ctx.author.id,
                    False,
                )
                await message.edit(
                    embed=discord.Embed(
                        description=f"> {ctx.author.mention} has **declined our privacy policy** and as a result you have been **blacklisted from using any wock command or feature**. Feel free to accept our [**policy**](https://wock.bot/terms) using `{ctx.prefix}reset`",
                        color=self.color,
                    )
                )
                return False
            else:
                await self.db.execute(
                    """INSERT INTO terms_agreement (user_id, state) VALUES ($1, $2) ON CONFLICT DO NOTHING;""",
                    ctx.author.id,
                    True,
                )
                await message.delete()

        if data := await self.db.fetch(  # type: ignore  # noqa: F841
            """SELECT command FROM disabled_commands WHERE guild_id = $1 AND command = $2""",
            ctx.guild.id,
            ctx.command.qualified_name.lower(),
        ):
            raise discord.ext.commands.errors.CommandError(
                f"`{ctx.command.qualified_name.lower()}` has been **disabled by moderators**"
            )
        if str(ctx.invoked_with).lower() == "help":
            if retry_after := await ctx.bot.glory_cache.ratelimited(
                f"rl:user_commands{ctx.author.id}", 5, 5
            ):
                raise commands.CommandOnCooldown(None, retry_after, None)
        else:
            if cooldown_args := ctx.command.cooldown_args:
                bucket_type = cooldown_args.get("type", "user")
                limit, interval = cooldown_args.get("limit", (1, 5))

                if bucket_type.lower() == "guild":
                    key = (
                        f"rl:user_commands:{ctx.guild.id}:{ctx.command.qualified_name}"
                    )
                else:
                    key = (
                        f"rl:user_commands:{ctx.author.id}:{ctx.command.qualified_name}"
                    )
                rl = await ctx.bot.glory_cache.ratelimited(key, limit, interval)
                if rl != 0:
                    raise commands.CommandOnCooldown(None, rl, None)
            else:
                if cog_name := ctx.command.cog_name:
                    if cog_name.lower() == "premium":
                        rl = await ctx.bot.glory_cache.ratelimited(
                            f"rl:user_commands:{ctx.author.id}:{ctx.command.qualified_name}",
                            1,
                            5,
                        )
                        if rl != 0:
                            raise commands.CommandOnCooldown(None, rl, None)
                    else:
                        rl = await ctx.bot.glory_cache.ratelimited(
                            f"rl:user_commands:{ctx.author.id}:{ctx.command.qualified_name}",
                            2,
                            5,
                        )
                        if rl != 0:
                            raise commands.CommandOnCooldown(None, rl, None)
                else:
                    rl = await ctx.bot.glory_cache.ratelimited(
                        f"rl:user_commands:{ctx.author.id}:{ctx.command.qualified_name}",
                        2,
                        5,
                    )
                    if rl != 0:
                        raise commands.CommandOnCooldown(None, rl, None)

        return True

    async def get_statistics(self, force: bool = False) -> Statistics:
        if not hasattr(self, "stats"):
            self.stats = await get_stats(self)
        if force is True:
            self.stats = await get_stats(self)
        stats = self.stats.copy()
        stats["uptime"] = str(discord.utils.format_dt(self.startup_time, style="R"))
        _ = Statistics(**stats)
        del stats
        return _

    async def paginate(
        self, ctx: Context, embed: discord.Embed, rows: list, per_page: int = 10
    ):
        from cogs.music import chunk_list

        embeds = []
        if len(rows) > per_page:
            chunks = chunk_list(rows, per_page)
            for chunk in chunks:
                rows = [f"{c}\n" for c in chunk]
                embed = embed.copy()
                embed.description = "".join(r for r in rows)
                embeds.append(embed)
            try:
                del chunks
            except Exception:
                pass
            return await ctx.alternative_paginate(embeds)
        else:
            embed.description = "".join(f"{r}\n" for r in rows)
            return await ctx.send(embed=embed)

    async def dummy_paginator(
        self,
        ctx: Context,
        embed: discord.Embed,
        rows: list,
        per_page: int = 10,
        type: str = "entry",
    ):
        from tools.music import chunk_list, plural  # type: ignore

        embeds = []
        embeds = []
        if len(rows) > per_page:
            chunks = chunk_list(rows, per_page)
            for i, chunk in enumerate(chunks, start=1):
                rows = [f"{c}\n" for c in chunk]
                embed = embed.copy()
                embed.description = "".join(r for r in rows)
                embed.set_footer(
                    text=f"Page {i}/{len(chunks)} ({plural(rows).do_plural(type.title())})"
                )
                embeds.append(embed)
            try:
                del chunks
            except Exception:
                pass
            return await ctx.alternative_paginate(embeds)
        else:
            embed.description = "".join(f"{r}\n" for r in rows)
            # t = plural(len(rows)):type.title()
            embed.set_footer(text=f"Page 1/1 ({plural(rows).do_plural(type.title())})")
            return await ctx.send(embed=embed)

    async def __load(self, cog: str):
        try:
            await self.load_extension(cog)
            logger.info(f"[ Loaded ] {cog}")
        except commands.errors.ExtensionAlreadyLoaded:
            pass
        except Exception as e:
            tb = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.info(f"Failed to load {cog} due to exception: {tb}")

    async def load_cogs(self):
        if self.loaded is not False:
            return
        from pathlib import Path

        cogs = [
            f'cogs.{str(c).split("/")[-1].split(".")[0]}'
            for c in Path("cogs/").glob("*.py")
        ]
        await asyncio.gather(*[self.__load(c) for c in cogs])
        self.loaded = True

    async def go(self, *args, **kwargs) -> None:
        self.http.proxy = ""
        await super().start(self.config["token"], *args, **kwargs)

    async def on_ready(self) -> None:
        log.info(f"Logged in as {self.user} ({self.user.id})")
        # self.browser = Browser(
        #     executable_path="/usr/bin/google-chrome",
        #     args=(
        #         "--ignore-certificate-errors",
        #         "--disable-extensions",
        #         "--no-sandbox",
        #         "--headless",
        #     ),
        # )

        # await self.browser.__aenter__()
        await self.load_cogs()
        self.runner = RebootRunner(self, "cogs")
        await self.load_cogs()
        await self.runner.start()
        log.info("Loaded all cogs")

    async def load_cog(self, cog: str):
        try:
            await self.load_extension(f"cogs.{cog}")
        except Exception:
            traceback.print_exc()

    @lock("fetch_message:{channel.id}")
    @ratelimit("rl:fetch_message:{channel.id}", 2, 5, True)
    async def fetch_message(
        self, channel: discord.TextChannel, id: int
    ) -> Optional[discord.Message]:
        if message := discord.utils.get(self.cached_messages, id=id):
            return message
        message = await channel.fetch_message(id)
        if message not in self._connection._messages:
            self._connection._messages.append(message)
        return message

    async def setup_hook(self) -> None:
        self.redis = Red(host="localhost", port=6379, db=0, decode_responses=True)
        self.session = ClientSession()
        log.info("Running poo hook")
        self.db: Database = Database()
        await self.db.connect()
        self.loop.create_task(self.cache.setup_cache())
        self.add_view(VmButtons(self))
        self.add_view(VoicemasterInterface(self))
        self.add_view(GiveawayView())
        #        self.add_view(TicketView(self, True))
        os.environ["JISHAKU_NO_UNDERSCORE"] = "True"
        os.environ["JISHAKU_RETAIN"] = "True"
        await self.load_extension("jishaku")
        await self.load_extension("tools.important.subclasses.web")

    async def create_embed(self, code: str, **kwargs):
        builder = Script(code, **kwargs)
        await builder.compile()
        return builder

    def build_error(self, message: str) -> dict:
        return {
            "embed": discord.Embed(
                color=0xFFA500,
                description=f"<:wockwarning:1234264951091105843> {message}",
            )
        }

    async def send_embed(self, destination: discord.TextChannel, code: str, **kwargs):
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

    async def get_prefix(self, message: Message):
        user = await self.db.fetchval(
            """SELECT prefix
            FROM selfprefix
            WHERE user_id = $1""",
            message.author.id,
        )
        server = await self.db.fetchval(
            """SELECT prefix
            FROM prefixes
            WHERE guild_id = $1""",
            message.guild.id,
        )
        guild = self.get_channel(1188638438539415615)
        if guild is not None:
            if guild.guild.id == message.guild.id:
                return ","
        if not server:
            server = ","
        if user:
            if message.content.strip().startswith(user):
                return when_mentioned_or(user)(self, message)
        return when_mentioned_or(server)(self, message)

    async def get_context(self, message, *, cls=Context):
        return await super().get_context(message, cls=cls)

    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content:
            return
        if not after.edited_at:
            return
        #        if after.edited_at - after.created_at > timedelta(minutes=1):
        #           return
        if not before.author.bot:
            await self.on_message(after)

    #            self.dispatch('message',after)
    #        await self.process_commands(after)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.channel.permissions_for(message.guild.me).send_messages is False:
            return
        server_prefix = await self.db.fetchval(
            """
            SELECT prefix
            FROM prefixes
            WHERE guild_id = $1""",
            message.guild.id,
        )
        user_prefix = await self.db.fetchval(
            """
            SELECT prefix
            FROM selfprefix
            WHERE user_id = $1""",
            message.author.id,
        )
        if message.mentions_bot(strict=True):
            if await self.glory_cache.ratelimited("prefix_pull", 1, 5) != 0:
                return
            ctx = await self.get_context(message)
            if vanity := ctx.channel.guild.vanity_url:
                invite_link = vanity
            else:
                if check := await self.db.fetchval(
                    """SELECT invite FROM guild_invites WHERE guild_id = $1""",
                    ctx.guild.id,
                ):
                    invite_link = check
                else:
                    invite_link = await ctx.channel.create_invite()
                    await self.db.execute(
                        """INSERT INTO guild_invites (guild_id,invite) VALUES($1,$2) ON CONFLICT(guild_id) DO UPDATE SET invite = excluded.invite""",
                        ctx.guild.id,
                        f"https://discord.gg/{invite_link.code}",
                    )
            return await ctx.normal(
                f"[**Guild Prefix**]({invite_link}) is set to ``{server_prefix or ','}``\nYour **Selfprefix** is set to `{user_prefix}`"
            )
        await self.process_commands(message)

    async def avatar_to_file(self, user: discord.User, url: str) -> str:
        return f"{user.id}.{url.split('.')[-1].split('?')[0]}"

    async def on_guild_join(self, guild: discord.Guild):
        await self.wait_until_ready()
        await guild.chunk(cache=True)
        if guild.id not in self.whitelisted and not await self.db.fetchrow(
            """SELECT * FROM auth WHERE guild_id = $1""", guild.id
        ):
            if len(guild.members) < 75:
                if owner := guild.owner:
                    try:
                        await owner.send(
                            embed=discord.Embed(
                                description="> I have left your guild due to you not having **75 members**",
                                color=self.bot.color,
                            )
                        )
                    except Exception:
                        pass
                    return await guild.leave()
        await self.join_message(guild)
        await self.get_channel(self.owner_channel).send(
            f"Joined `{guild.name}` (ID: {guild.id}), owned by {guild.owner.mention} (ID: {guild.owner.id}), with `{guild.member_count}` members."
        )

    async def send_exception(self, ctx: Context, exception: Exception):
        code = tuuid.tuuid()
        await self.db.execute(
            """INSERT INTO traceback (command, error_code, error_message, guild_id, channel_id, user_id, content) VALUES($1, $2, $3, $4, $5, $6, $7)""",
            ctx.command.qualified_name,
            code,
            str(exception),
            ctx.guild.id,
            ctx.channel.id,
            ctx.author.id,
            ctx.message.content,
        )
        return await ctx.send(
            content=f"`{code}`",
            embed=discord.Embed(
                description=f"<:wockwarning:1234264951091105843> {ctx.author.mention}: Error occurred while performing command **{ctx.command.qualified_name}**. Use the given error code to report it to the developers in the [support server]({self.support_server})",
                color=0xFFA500,
            ),
        )

    async def on_xdcommand_error(self, ctx: Context, exception: Exception) -> None:
        bucket = self._cd.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if await self.glory_cache.ratelimited(
            f"rl:error_message:{ctx.author.id}", 1, 5
        ):
            return
        if retry_after:
            return

        error = getattr(exception, "original", exception)
        ignored = [
            commands.CommandNotFound,
        ]
        if type(exception) in ignored:
            return

        if isinstance(exception, commands.CommandOnCooldown):
            if await self.glory_cache.ratelimited(
                f"rl:cooldown_message{ctx.author.id}", 1, exception.retry_after
            ):
                return

            return await ctx.fail(
                f"Command is on a ``{exception.retry_after:.2f}s`` **cooldown**"
            )
        if isinstance(exception, commands.MissingPermissions):
            if ctx.author.id in self.owner_ids:
                return await ctx.reinvoke()
            return await ctx.fail(
                f"Must have **{', '.join(exception.missing_permissions)}** permissions"
            )
        if isinstance(exception, commands.MissingRequiredArgument):
            return await ctx.fail(f"Provide a **{exception.param.name}**")
        if isinstance(exception, commands.BadArgument):
            error = exception
            tb = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            logger.info(tb)
            exception = (
                str(exception)
                .replace("Member", "**Member**")
                .replace("User", "**User**")
            )
            return await ctx.warning(f"{exception}")
        if isinstance(exception, commands.BadUnionArgument):
            return await ctx.warning(f"{exception}")
        if isinstance(exception, commands.MemberNotFound):
            return await ctx.warning("That Member **not** found")
        if isinstance(exception, commands.UserNotFound):
            return await ctx.warning("That User **not** found")
        if isinstance(exception, commands.RoleNotFound):
            return await ctx.warning("That Role was **not** found")
        if isinstance(exception, commands.ChannelNotFound):
            return await ctx.warning("That Channel was **not** found")
        if isinstance(exception, commands.EmojiNotFound):
            return await ctx.warning("That **Emoji** was not found")
        if isinstance(exception, discord.ext.commands.errors.CommandError):
            return await ctx.warning(str(exception))
        if isinstance(exception, commands.CommandNotFound):
            await self.paginators.check(ctx)
            aliases = [
                CommandAlias(command=command_name, alias=alias)
                for command_name, alias in await self.db.fetch(
                    "SELECT command_name, alias FROM aliases WHERE guild_id = $1",
                    ctx.guild.id,
                )
            ]
            return await handle_aliases(ctx, aliases)
        if isinstance(exception, discord.ext.commands.errors.CheckFailure):
            return
        exc = "".join(
            traceback.format_exception(type(error), error, error.__traceback__)
        )
        if isinstance(exception, SnipeError):
            return await ctx.warning(str(exception))
        log.error(
            f'{type(error).__name__:25} > {ctx.guild} | {ctx.author} "{ctx.message.content}" \n {error} \n {exc}'
        )
        if isinstance(exception, RolePosition):
            return await ctx.warning(str(exception))
        if hasattr(exception, "message"):
            return await ctx.warning(exception.message.split(":")[-1])
        if "Missing Permissions" in str(exception):
            return await ctx.warning(
                "Due to hierarchy position I could not edit that object"
            )
        return await self.send_exception(
            ctx, exception
        )  # await ctx.warning(str(exception))

    async def hierarchy(
        self,
        ctx: Context,
        member: discord.Member,
        author: bool = False,
    ):
        if isinstance(member, discord.User):
            return True

        elif ctx.guild.me.top_role <= member.top_role:
            await ctx.warning(f"The role of {member.mention} is **higher than wocks**")
            return False
        elif ctx.author.id == member.id and not author:
            await ctx.warning("You **can not execute** that command on **yourself**")
            return False
        elif ctx.author.id == member.id and author:
            return True
        elif ctx.author.id == ctx.guild.owner_id:
            return True
        elif member.id == ctx.guild.owner_id:
            await ctx.warning(
                "**Can not execute** that command on the **server owner**"
            )
            return False
        elif ctx.author.top_role.is_default():
            await ctx.warning("You are **missing permissions to use this command**")
            return False
        elif ctx.author.top_role == member.top_role:
            await ctx.warning("You have the **same role** as that user")
            return False
        elif ctx.author.top_role < member.top_role:
            await ctx.warning("You **do not** have a role **higher** than that user")
            return False
        else:
            return True

    async def dump_command_page(self):
        def get_usage(command):
            if not command.clean_params:
                return "None"
            return ", ".join(m for m in [str(c) for c in command.clean_params.keys()])

        def get_aliases(command):
            if len(command.aliases) == 0:
                return ["None"]
            return command.aliases

        def get_category(command):
            if "settings" not in command.qualified_name:
                return command.cog_name
            else:
                return "settings"

        commands = list()
        excluded = ["owner", "errors", "webserver", "jishaku"]
        for command in self.walk_commands():
            if cog := command.cog_name:
                if cog.lower() in excluded:
                    continue
                if command.hidden or not command.brief:
                    continue
                if not command.permissions:
                    permissions = ["send_messages"]
                else:
                    permissions = command.permissions
                commands.append(
                    {
                        "name": command.qualified_name,
                        "help": command.brief or "",
                        "brief": (
                            [permissions.replace("_", " ").title()]
                            if not isinstance(permissions, list)
                            else [_.replace("_", " ").title() for _ in permissions]
                        ),
                        "usage": get_usage(command),
                        "description": "",
                        "aliases": get_aliases(command),
                        "category": get_category(command).title(),
                    }
                )
        with open(
            "/root/wock.web/src/app/(routes)/commands/commands.json", "wb"
        ) as file:
            file.write(orjson.dumps(commands))
        proc = await asyncio.create_subprocess_shell(
            "cd ~/wock.web ; npm run build ; pm2 restart website",
            stderr=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
