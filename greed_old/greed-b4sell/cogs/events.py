from __future__ import annotations
from asyncio import ensure_future, sleep, gather
import json
from base64 import b64decode
from datetime import datetime, timedelta
from typing import Any, List, Union, Optional, Dict, Set
from discord.ext import tasks
from discord import Guild, Message, Member
import discord
import humanize
from contextlib import suppress
import orjson
import asyncio
import humanfriendly
from boltons.cacheutils import LRI
from discord.ext import commands
import contextlib
import unicodedata
from tools import ratelimit  # type: ignore
from tool import expressions
from collections import defaultdict
import aiohttp
import io
from contextlib import suppress
import re  # type: ignore
from loguru import logger
from cashews import cache
import time
from cogs.moderation import Moderation
from functools import lru_cache
from tenacity import retry, stop_after_attempt, wait_exponential
from dataclasses import dataclass
from contextlib import asynccontextmanager
from tool.greed import Greed

cache.setup("mem://")

# Cache configuration
CACHE_TTL = 300  # 5 minutes
BATCH_SIZE = 100
MAX_RETRIES = 3


@dataclass
class GuildConfig:
    """Cached guild configuration"""

    filter_events: Set[str]
    autoroles: List[int]
    settings: Dict[str, Any]
    last_updated: float


def get_humanized_time(seconds: Union[float, int]):
    return humanize.naturaldelta(int(seconds))


url_regex = re.compile(
    r"https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+",
    re.I,
)

SPECIAL_ = re.compile(r"[@_!#$%^&*()<>?/\|}{~:]")


def clean_content(m: Message):
    content = SPECIAL_.sub("", m.content)
    return content


EMOJI_REGEX = re.compile(
    r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
)
# from loguru import logger
LIST = []


def get_emoji(emoji: Any):
    emoji = b64decode(emoji).decode()
    logger.info(emoji)
    return emoji


def format_int(n: int) -> str:
    m = humanize.intword(n)
    m = (
        m.replace(" million", "m")
        .replace(" billion", "b")
        .replace(" trillion", "t")
        .replace(" thousand", "k")
        .replace(" hundred", "")
    )
    return m


def is_unicode(emoji: str) -> bool:
    with contextlib.suppress(Exception):
        unicodedata.name(emoji)
        return True

    return False


def find_emojis(text: str) -> List[str]:
    """
    Find emojis in the given text.

    Parameters:
        text (str): The text to search for emojis.

    Returns:
        List[str]: A list of emojis found in the text.
    """

    return expressions.custom_emoji.findall(text) + expressions.unicode_emoji.findall(
        text
    )


def find_invites(text: str) -> List[str]:
    """
    Finds all Discord invite links in the given text.

    Parameters:
        text (str): A string representing the text to search for invite links.

    Return:
        List[str]: A list of Discord invite links found in the text.
    """

    return expressions.discord_invite.findall(text)


TUPLE = ()
DICT = {}

PREV, NEXT, KEY, VALUE = range(4)  # names for the link fields
DEFAULT_MAX_SIZE = 128


def default_lock_cache(max_size: int = 5000) -> dict[Any, asyncio.Lock]:
    return LRI(max_size=max_size, on_miss=lambda x: asyncio.Lock())  # type: ignore


class Events(commands.Cog):
    def __init__(self, bot: Greed):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)
        self.no_snipe = []
        self.watched_users = []
        self.cooldowns = {}
        self.channel_id = 1334073848118771723
        self.last_active_voter = None
        self.cooldown_messages = {}
        self.bot.loop.create_task(self.create_countertables())
        self.maintenance = True
        self.bot.loop.create_task(self.setup_db())
        self.voicemaster_clear.start()
        self.sent_notifications = {}  # Store guild notification statuses
        self.guild_remove_time = {}  # Store timestamp of when the bot was removed
        self.system_sticker = None
        self.last_posted = None
        self.bot.audit_cache = {}
        self.guild_config_cache: Dict[int, GuildConfig] = {}
        self.connection_pool = None
        self.batch_queue = defaultdict(list)
        self.processing_locks = defaultdict(asyncio.Lock)
        self.DICT = {}
        self.notification_channel_id = 1330619140331016192
        self.min_member_threshold = 1000

        # Start background tasks
        self.batch_processor.start()
        self.cache_cleanup.start()

    async def setup_db(self):
        """Sets up the database tables if they don't exist."""
        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS labs (
                user_id BIGINT PRIMARY KEY,
                level INT DEFAULT 1,
                ampoules INT DEFAULT 1,
                earnings BIGINT DEFAULT 0,
                storage BIGINT DEFAULT 164571
            )
        """
        )

    @tasks.loop(minutes=5)
    async def cache_cleanup(self):
        """Clean expired cache entries"""
        current_time = time.time()
        expired = [
            guild_id
            for guild_id, config in self.guild_config_cache.items()
            if current_time - config.last_updated > CACHE_TTL
        ]
        for guild_id in expired:
            self.guild_config_cache.pop(guild_id, None)

    @tasks.loop(seconds=5)
    async def batch_processor(self):
        """Process batched operations"""
        for queue_name, queue in self.batch_queue.items():
            if len(queue) >= BATCH_SIZE:
                async with self.processing_locks[queue_name]:
                    batch = queue[:BATCH_SIZE]
                    self.batch_queue[queue_name] = queue[BATCH_SIZE:]
                    await self.process_batch(queue_name, batch)

    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential())
    async def process_batch(self, queue_name: str, batch: list):
        """Process a batch of operations with retry logic"""
        if queue_name == "messages":
            await self.process_message_batch(batch)
        elif queue_name == "members":
            await self.process_member_batch(batch)

    @asynccontextmanager
    async def get_guild_config(self, guild_id: int):
        """Get cached guild configuration with automatic updates"""
        config = self.guild_config_cache.get(guild_id)
        if not config or time.time() - config.last_updated > CACHE_TTL:
            async with self.processing_locks[f"guild_config:{guild_id}"]:
                config = await self.fetch_guild_config(guild_id)
                self.guild_config_cache[guild_id] = config
        yield config

    async def fetch_guild_config(self, guild_id: int) -> GuildConfig:
        """Fetch and cache guild configuration from database"""
        async with self.bot.pool.acquire() as conn:
            # Fetch all guild settings in parallel
            filter_events, autoroles, settings = await asyncio.gather(
                conn.fetch(
                    "SELECT event FROM filter_event WHERE guild_id = $1", guild_id
                ),
                conn.fetch(
                    "SELECT role_id FROM autorole WHERE guild_id = $1", guild_id
                ),
                conn.fetchrow(
                    "SELECT * FROM guild_settings WHERE guild_id = $1", guild_id
                ),
            )

        return GuildConfig(
            filter_events={event["event"] for event in filter_events},
            autoroles=[role["role_id"] for role in autoroles],
            settings=dict(settings) if settings else {},
            last_updated=time.time(),
        )

    def cog_unload(self):
        self.voicemaster_clear.cancel()
        self.bot.levels.remove_listener(self.on_level_up, "on_text_level_up")
        self.batch_processor.cancel()
        self.cache_cleanup.cancel()

    # async def do_command_storage(self):
    #    output = ""
    #     for name, cog in sorted(self.bot.cogs.items(), key=lambda cog: cog[0].lower()):
    #          if name.lower() in ("jishaku", "Develoepr"):
    #               continue
    #
    #        _commands = list()
    #         for command in cog.walk_commands():
    #              if command.hidden:
    #                   continue
    #
    #         usage = " " + command.usage if command.usage else ""
    #          aliases = (
    #               "(" + ", ".join(command.aliases) +
    #                ")" if command.aliases else ""
    #             )
    #              if isinstance(command, commands.Group) and not command.root_parent:
    #                   _commands.append(
    #                        f"| +-- {command.name}{aliases}: {
    #                            command.brief or 'No description'}"
    #                  )
    #             elif not isinstance(command, commands.Group) and command.root_parent:
    #                _commands.append(
    #                   f"| |   +-- {command.qualified_name}{aliases}{
    #                      usage}: {command.brief or 'No description'}"
    #             )
    #        elif isinstance(command, commands.Group) and command.root_parent:
    #           _commands.append(
    #              f"| |   +-- {command.qualified_name}{
    #                 aliases}: {command.brief or 'No description'}"
    #        )
    #   else:
    #      _commands.append(
    #         f"| +-- {command.qualified_name}{aliases}{
    #            usage}: {command.brief or 'No description'}"
    #   )

    #            if _commands:
    #               output += f"+-- {name}\n" + "\n".join(_commands) + "\n"
    #
    #       return await self.bot.redis.set("commands", orjson.dumps(output))

    async def add_entry(self, audit: discord.AuditLogEntry):
        from collections import deque

        if audit.guild.id not in self.bot.audit_cache:
            self.bot.audit_cache[audit.guild.id] = deque(maxlen=10)
        if len(self.bot.audit_cache[audit.guild.id]) == 10:
            self.bot.audit_cache[audit.guild.id].pop()
        self.bot.audit_cache[audit.guild.id].insert(0, audit)

    # def random_pfp(self, message: discord.Message):
    #     return random.choice(message.attachments)

    # def random_avatar(self):
    #     choice = random.choice(self.bot.users)
    #     return choice.display_avatar.url

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listener that checks for offensive words and updates the count.
        """
        if message.author.bot:  # Don't process messages from bots
            return

        # List of offensive words to check for (you can customize this list)
        offensive_words = [r"\bnigga\b", r"\bniggas\b"]  # Replace with your own list
        hard_r_word = r"\bnigger\b"

        # Check for any offensive word in the message
        if re.search(hard_r_word, message.content, re.IGNORECASE):
            await self.increment_offensive_word_count(message.author.id, "hard_r")

        for word in offensive_words:
            if re.search(word, message.content, re.IGNORECASE):
                await self.increment_offensive_word_count(message.author.id, "general")
                break

    @commands.Cog.listener("on_message")
    async def imageonly(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return

        if not message.channel.permissions_for(message.guild.me).manage_messages:
            return

        if await self.bot.db.fetchval(
            "SELECT * FROM imageonly WHERE channel_id = $1", message.channel.id
        ):
            if message.content and not message.attachments or message.embeds:
                with suppress(discord.Forbidden, discord.HTTPException):
                    await message.delete()

    @commands.Cog.listener("on_audit_log_entry_create")
    async def moderation_logs(self, entry: discord.AuditLogEntry):
        if not entry.guild.me.guild_permissions.view_audit_log:
            return
        return await self.bot.modlogs.do_log(entry)

    @commands.Cog.listener("on_text_level_up")
    async def on_level_up(self, guild: Guild, member: Member, level: int):
        async def do_roles():
            data = await self.bot.db.fetchval(
                """SELECT roles FROM text_level_settings WHERE guild_id = $1""",
                member.guild.id,
            )
            if not data:
                return
            data = json.loads(data)
            for entry in data:
                role_level, role_id = entry
                role = guild.get_role(role_id)
                if not role:
                    continue
                if level >= role_level:
                    if role not in member.roles:
                        await member.add_roles(role, reason="level roles")

        async def do_message():
            data = await self.bot.db.fetchval(
                """SELECT award_message FROM text_level_settings WHERE guild_id = $1""",
                guild.id,
            )

            if not data:
                return

            data = json.loads(data)
            channel_id = data.get("channel_id")
            message = data.get("message")

            if not channel_id:
                return
            channel = guild.get_channel(channel_id)
            if not channel:
                return

            if message is None:
                message = (
                    f"Congratulations {member.mention}, you have reached level {level}!"
                )

            message = message.replace("{level}", str(level))
            return await self.bot.send_embed(channel, message, user=member)

        await do_roles()
        await do_message()

    #    @commands.Cog.listener("on_command_completion")
    async def command_moderation_logs(self, ctx: commands.Context):
        try:
            return await self.bot.modlogs.do_log(ctx)
        except Exception:
            logger.info(
                f"The below exception was raised in {ctx.command.qualified_name}"
            )

    #            raise e

    # @asyncretry(max_tries = 5, pause = 1)
    async def get_pfps(self):
        ts = datetime.now() - timedelta(days=6)
        ts = int(ts.timestamp())
        data = await self.bot.db.fetch(
            "SELECT * FROM avatars WHERE time > $1 ORDER BY RANDOM() LIMIT 10", ts
        )
        pfps = [u["avatar"] for u in data]
        if pfps != self.last_posted:
            self.last_posted = pfps
        else:
            raise TypeError()
        return pfps

    async def get_image(self, url: str) -> discord.File:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.read()
        return discord.File(
            fp=io.BytesIO(data), filename=url.split("/")[-1].split("?")[0]
        )

    # @tasks.loop(minutes=4)
    # async def do_pfp_loop(self):
    #     pfps = await self.get_pfps()
    #     embeds = [Embed(title="new pfp", url=p).set_image(url=p) for p in pfps]
    #     logger.info("sending avatars now")
    #     for guild_id, channel_id in await self.bot.db.fetch(
    #         """SELECT guild_id,channel_id FROM pfps"""
    #     ):
    #         if guild := self.bot.get_guild(int(guild_id)):
    #             if channel := guild.get_channel(int(channel_id)):
    #                 try:
    #                     await channel.send(embeds=embeds)
    #                 except Exception as e:
    #                     logger.info(f"autopfp loop raised an exception: {e}")
    #                     pass

    @commands.Cog.listener("on_member_update")
    async def booster_lost(self, before, after):
        if (
            before.guild.premium_subscriber_role in before.roles
            and before.guild.premium_subscriber_role not in after.roles
        ):
            await self.bot.db.execute(
                """INSERT INTO boosters_lost (user_id,guild_id,ts) VALUES($1,$2,$3) ON CONFLICT(user_id,guild_id) DO UPDATE SET ts = excluded.ts""",
                before.id,
                before.guild.id,
                datetime.now(),
            )

    @commands.Cog.listener("on_user_update")
    async def namehistory_event(self, before, after):
        async with self.bot.redis.lock(f"namehistory:{before.id}"):
            if before.name != after.name and before.name is not None:
                name = before.name
                nt = "username"
            elif (
                before.global_name != after.global_name
                and before.global_name is not None
            ):
                name = before.global_name
                nt = "globalname"
            elif (
                before.display_name != after.display_name
                and before.display_name is not None
            ):
                name = before.display_name
                nt = "display"
            else:
                return

            cache_key = f"namehistory:{before.id}:{nt}:{name}"
            if await self.bot.redis.get(cache_key):
                return

            await self.bot.db.execute(
                """INSERT INTO names (user_id, type, username, ts) VALUES($1,$2,$3,$4) ON CONFLICT(user_id,username,ts) DO NOTHING""",
                before.id,
                nt,
                name,
                datetime.now(),
            )

            await self.bot.redis.set(cache_key, 1, 60)

    @commands.Cog.listener("on_audit_log_entry_create")
    async def audit_log_cache(self, entry: discord.AuditLogEntry):
        return await self.add_entry(entry)

    async def forcenick_check(
        self, guild: discord.Guild, member: discord.Member
    ) -> bool:
        if guild.me.guild_permissions.administrator is False:
            return False
        if self.bot.is_touchable(member) is False:
            return False
            #        if logs := self.bot.audit_cache.get(guild.id):
            #            if [
            #                l
            #                for l in logs  # noqa: E741
            #                if l.action == discord.AuditLogAction.member_update
            #                and (l.target.id == member.id or l.user.id == member.id)
            #                and l.user.bot is not True
            #                and l.user.id != self.bot.user.id
            #            ]:
            #                return True
            return False
        return True

    async def check_rolee(self, guild: discord.Guild, role: discord.Role):
        if role.position >= guild.me.top_role.position:
            return False
        return True

    @commands.Cog.listener("on_raw_reaction_add")
    async def reaction_role_add(self, reaction: discord.RawReactionActionEvent):
        emoji = str(reaction.emoji)
        if roles := await self.bot.db.fetch(
            """SELECT role_id FROM reactionrole WHERE guild_id = $1 AND message_id = $2 AND emoji = $3""",
            reaction.guild_id,
            reaction.message_id,
            emoji,
        ):
            guild = self.bot.get_guild(reaction.guild_id)
            if guild.me.guild_permissions.administrator is False:
                return
        else:
            return

        @ratelimit("rr:{reaction.guild_id}", 3, 5, True)
        async def do(
            reaction: discord.RawReactionActionEvent, roles: Any, guild: Guild
        ):
            for r in roles:
                if role := guild.get_role(r.role_id):
                    if await self.check_rolee(guild, role) is not True:
                        return logger.info("failed rr checks")
                    if member := guild.get_member(reaction.user_id):
                        if await self.bot.glory_cache.ratelimited("rr", 1, 4) != 0:
                            await asyncio.sleep(5)
                        if role in member.roles:
                            return
                        try:
                            await member.add_roles(role)
                        except Exception:
                            await member.add_roles(role)

        return await do(reaction, roles, guild)

    @commands.Cog.listener("on_raw_reaction_remove")
    async def reaction_role_remove(self, reaction: discord.RawReactionActionEvent):
        emoji = str(reaction.emoji)
        if roles := await self.bot.db.fetch(
            """SELECT role_id FROM reactionrole WHERE guild_id = $1 AND message_id = $2 AND emoji = $3""",
            reaction.guild_id,
            reaction.message_id,
            emoji,
        ):
            guild = self.bot.get_guild(reaction.guild_id)
            if guild.me.guild_permissions.administrator is False:
                return logger.info("failed rr perm checks")
        else:
            return

        @ratelimit("rr:{reaction.guild_id}", 3, 5, True)
        async def do(
            reaction: discord.RawReactionActionEvent, roles: Any, guild: Guild
        ):
            if member := guild.get_member(reaction.user_id):
                if len(member.roles) > 0:
                    member_roles = [r.id for r in member.roles]
                    for role in roles:
                        if r := guild.get_role(role.role_id):
                            if await self.check_rolee(guild, r) is not True:
                                return logger.info("failed rr checks")
                        else:
                            return logger.info("no role lol")
                        if role.role_id in member_roles:
                            if await self.bot.glory_cache.ratelimited("rr", 1, 4) != 0:
                                await asyncio.sleep(5)
                            try:
                                await member.remove_roles(guild.get_role(role.role_id))
                            except Exception:
                                await member.remove_roles(
                                    guild.get_role(role.role_id), reason="RR"
                                )

        return await do(reaction, roles, guild)

    @commands.Cog.listener("on_member_update")
    @ratelimit("fn:{before.guild.id}", 3, 5, True)
    async def forcenick_event(self, before: discord.Member, after: discord.Member):
        if before.nick == after.nick:
            return

        if not (data := self.bot.cache.forcenick.get(before.guild.id)):
            return

        if not data.get(before.id):
            return
        if after.guild.me.top_role < after.top_role:
            return

        if await self.forcenick_check(after.guild, after) is True:
            if has_data := self.bot.cache.forcenick.get(before.guild.id):
                if name := has_data.get(before.id):
                    try:
                        if after.nick != name:
                            await after.edit(nick=name[:32])
                    except discord.Forbidden:
                        self.bot.cache.forcenick[before.guild.id].pop(before.id, None)
        else:
            if before.nick and before.nick != after.nick and before.nick is not None:
                return await self.bot.db.execute(
                    """INSERT INTO names (user_id,type,username,ts) VALUES($1,$2,$3,$4) ON CONFLICT(user_id,username,ts) DO NOTHING""",
                    before.id,
                    "nickname",
                    before.nick,
                    datetime.now(),
                )

    async def get_event_types(self, message: discord.Message):
        p = []
        _types = ["spoilers", "images", "emojis", "stickers"]
        for t in _types:
            if yes := self.bot.cache.autoreacts[message.guild.id].get(t):  # type: ignore  # noqa: F841
                p.append(t)
        return p

    async def check_message(self, message: discord.Message):
        """Check message for autoresponses with improved efficiency"""
        if (
            await self.bot.glory_cache.ratelimited(
                f"check_msg:{message.guild.id}", 1, 1
            )
            != 0
        ):
            return

        try:
            data = self.bot.cache.autoresponders.get(message.guild.id)
            if not data:
                return

            # Add a per-channel rate limit to prevent excessive autoresponses in busy channels
            if (
                await self.bot.glory_cache.ratelimited(
                    f"autoresponse_channel:{message.channel.id}", 3, 5
                )
                != 0
            ):
                return

            # Add a per-user rate limit to prevent a single user from triggering too many autoresponses
            if (
                await self.bot.glory_cache.ratelimited(
                    f"autoresponse_user:{message.author.id}:{message.guild.id}", 2, 10
                )
                != 0
            ):
                return

            content = message.content.lower()
            for trigger, response_data in data.items():
                # Skip empty triggers
                if not trigger or not response_data:
                    continue

                # Handle both old format (string) and new format (dict with flags)
                response = response_data
                strict_mode = False
                reply_mode = False
                
                if isinstance(response_data, dict):
                    response = response_data.get("response", "")
                    strict_mode = response_data.get("strict", False)
                    reply_mode = response_data.get("reply", False)

                if not response:
                    continue

                trigger = trigger.lower()
                matched = False

                # Check for wildcard matches first
                if trigger.endswith("*"):
                    base = trigger.strip("*")
                    if base in content:
                        matched = True
                # For strict mode, only match exact trigger
                elif strict_mode:
                    if content == trigger or content.split() == [trigger]:
                        matched = True
                # Then check for exact/word boundary matches
                else:
                    trigger = trigger.strip()
                    # Check for word boundary matches or substring match
                    if (
                        content.startswith(f"{trigger} ")
                        or content == trigger
                        or f" {trigger} " in content
                        or content.endswith(f" {trigger}")
                        or trigger in content.split()
                        or trigger in content  # Allow substring match for non-strict mode
                    ):
                        matched = True

                if matched:
                    await self.do_autoresponse(trigger, message, reply_mode)
                    break  # Stop after first match

        except Exception as e:
            logger.error(f"Error in check_message: {e}")

    async def do_autoresponse(self, trigger: str, message: discord.Message, reply_mode: bool = False):
        """Handle autoresponse with improved error handling"""
        try:
            # Check channel-specific rate limit
            if (
                await self.bot.glory_cache.ratelimited(
                    f"ar:{message.channel.id}:{trigger}", 1, 1
                )
                != 0
            ):
                return

            # Check guild-wide rate limit
            if (
                await self.bot.glory_cache.ratelimited(
                    f"ar:{message.guild.id}:{trigger}", 2, 4
                )
                != 0
            ):
                return
                
            # Add a per-user rate limit for this specific trigger
            if (
                await self.bot.glory_cache.ratelimited(
                    f"ar_user:{message.author.id}:{trigger}", 1, 15
                )
                != 0
            ):
                return

            # Safely get response from cache
            response_data = None
            if message.guild.id in self.bot.cache.autoresponders:
                response_data = self.bot.cache.autoresponders[message.guild.id].get(trigger)

            # Handle both old format (string) and new format (dict with flags)
            response = None
            if isinstance(response_data, dict):
                response = response_data.get("response", "")
                # Override reply_mode if it's in the cache
                reply_mode = response_data.get("reply", reply_mode)
            else:
                response = response_data

            # If not in cache, try getting from database
            if not response:
                db_data = await self.bot.db.fetchrow(
                    """SELECT response, strict, reply FROM autoresponder WHERE guild_id = $1 AND trig = $2""",
                    message.guild.id,
                    trigger,
                )
                if db_data:
                    response = db_data["response"]
                    # Override reply_mode with database value
                    reply_mode = db_data["reply"]
                    
                    # Update cache with new format
                    if message.guild.id not in self.bot.cache.autoresponders:
                        self.bot.cache.autoresponders[message.guild.id] = {}
                    self.bot.cache.autoresponders[message.guild.id][trigger] = {
                        "response": response,
                        "strict": db_data["strict"],
                        "reply": reply_mode
                    }

            if not response:
                logger.debug(
                    f"No response found for trigger '{trigger}' in guild {message.guild.id}"
                )
                return

            if response.lower().startswith("{embed}"):
                if reply_mode:
                    await self.bot.send_embed(
                        message.channel, response, user=message.author, reference=message
                    )
                else:
                    await self.bot.send_embed(
                        message.channel, response, user=message.author
                    )
            else:
                if reply_mode:
                    await message.reply(
                        response,
                        allowed_mentions=discord.AllowedMentions(
                            users=True,
                        ),
                    )
                else:
                    await message.channel.send(
                        response,
                        allowed_mentions=discord.AllowedMentions(
                            users=True,
                        ),
                    )

        except Exception as e:
            logger.error(f"Error in do_autoresponse for trigger '{trigger}': {str(e)}")

    @commands.Cog.listener("on_message")
    async def autoresponder_event(self, message: discord.Message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        try:
            if message.channel.permissions_for(message.guild.me).send_messages is False:
                return
        except discord.errors.ClientException:
            pass

        # Add a global rate limit for autoresponder processing to prevent excessive CPU usage
        if (
            await self.bot.glory_cache.ratelimited(
                f"autoresponder_global:{message.guild.id}", 10, 3
            )
            != 0
        ):
            return

        # Handle both autoresponses and autoreacts
        await asyncio.gather(
            self.check_message(message),  # Autoresponses
            self.handle_autoreacts(message),  # Autoreacts
        )

    async def handle_autoreacts(self, message: discord.Message):
        """Handle automatic reactions to messages"""
        if not self.bot.cache.autoreacts.get(message.guild.id):
            return

        # Add a guild-wide rate limit to prevent excessive processing
        if await self.bot.glory_cache.ratelimited(
            f"autoreact_guild:{message.guild.id}", 5, 2
        ):
            return

        try:
            # Handle keyword-based reactions
            keywords_covered = []
            
            # Add a per-channel rate limit to prevent spam in busy channels
            if await self.bot.glory_cache.ratelimited(
                f"autoreact_channel:{message.channel.id}", 3, 5
            ):
                return
                
            # Add a per-user rate limit to prevent a single user from triggering too many reactions
            if await self.bot.glory_cache.ratelimited(
                f"autoreact_user:{message.author.id}", 2, 10
            ):
                return
                
            for keyword, reactions in self.bot.cache.autoreacts[
                message.guild.id
            ].items():
                if keyword not in ["spoilers", "images", "emojis", "stickers"]:
                    if keyword.lower() in message.content.lower():
                        if await self.bot.glory_cache.ratelimited(
                            f"autoreact:{message.guild.id}:{message.channel.id}:{keyword}", 1, 3
                        ):
                            continue
                        await self.add_reaction(message, reactions)
                        keywords_covered.append(keyword)

            # Handle event-based reactions
            event_types = await self.get_event_types(message)
            if not event_types:
                return

            tasks = []
            for event_type in event_types:
                if event_type == "images" and any(
                    attachment.content_type
                    and attachment.content_type.startswith(("image/", "video/"))
                    for attachment in message.attachments
                ):
                    tasks.append(self.add_event_reaction(message, "images"))

                elif event_type == "spoilers" and message.content.count("||") >= 2:
                    tasks.append(self.add_event_reaction(message, "spoilers"))

                elif event_type == "emojis" and find_emojis(message.content):
                    tasks.append(self.add_event_reaction(message, "emojis"))

                elif event_type == "stickers" and message.stickers:
                    tasks.append(self.add_event_reaction(message, "stickers"))

            if tasks:
                await asyncio.gather(*tasks)

        except Exception as e:
            logger.error(f"Error in handle_autoreacts: {e}")

    async def add_event_reaction(self, message: discord.Message, event_type: str):
        """Add reactions for specific event types with rate limiting"""
        if await self.bot.glory_cache.ratelimited(
            f"autoreact:{message.guild.id}:{message.channel.id}:{event_type}", 1, 3
        ):
            return

        reactions = self.bot.cache.autoreacts[message.guild.id].get(event_type)
        if reactions:
            await self.add_reaction(message, reactions)

    async def do_afk(
        self, message: discord.Message, context: commands.Context, afk_data: Any
    ):
        if (
            await self.bot.glory_cache.ratelimited(f"afk:{message.author.id}", 1, 1)
            == 0
        ):
            author_afk_since: datetime = afk_data["date"]
            welcome_message = (
                f":wave_tone3: {message.author.mention}: **Welcome back**, "
                f"you went away {discord.utils.format_dt(author_afk_since, style='R')}"
            )
            embed = discord.Embed(description=welcome_message, color=0x9EAFBF)
            await context.send(embed=embed)

            if message.author.id in self.bot.afks:
                self.bot.afks.pop(message.author.id)
            else:
                logger.error(f"{message.author.id} not found in AFK list.")

    async def revert_slowmode(self, channel: discord.TextChannel):
        await asyncio.sleep(300)
        await channel.edit(slowmode_delay=0, reason="Auto Mod Auto Slow Mode")
        return True

    async def reset_filter(self, guild: Guild):
        tables = [
            """DELETE FROM filter_event WHERE guild_id = $1""",
            """DELETE FROM filter_setup WHERE guild_id = $1""",
        ]
        return await asyncio.gather(
            *[self.bot.db.execute(table, guild.id) for table in tables]
        )

    #    @ratelimit("to:{message.guild.id}", 1, 5, True)
    async def do_timeout(
        self, message: discord.Message, reason: str, context: commands.Context
    ):
        if self.bot.check_bot_hierarchy(message.guild) is False:
            await self.reset_filter(message.guild)
            return False
        if await self.bot.glory_cache.ratelimited(f"timeout-attempt-{message.guild.id}", 1, 10) != 0:
            return
        if await self.bot.glory_cache.ratelimited(f"timeout-attempt-{message.author.id}-{message.guild.id}", 1, 10) != 0: 
            return
        async def check():
            if message.author.top_role >= message.guild.me.top_role:
                if self.maintenance is True:
                    if message.author.name == "aiohttp":
                        logger.info(
                            "top role issue lol, {message.author.top_role.position} - {message.guild.me.top_role.position}"
                        )
                return False
            whitelist = self.bot.cache.filter_whitelist.get(context.guild.id, LIST)
            return all(
                (
                    message.author.id
                    not in (message.guild.owner_id, message.guild.me.id),
                    not message.author.guild_permissions.administrator,
                    (
                        (
                            message.author.top_role.position
                            <= message.guild.me.top_role.position
                        )
                        if message.author.top_role
                        else True
                    ),
                    not any(
                        (
                            message.author.id in whitelist,
                            message.channel.id in whitelist,
                            any(role.id in whitelist for role in message.author.roles),
                        )
                    ),
                )
            )

        if message.guild.me.guild_permissions.moderate_members is True:
            async with self.locks[f"am-{message.author.id}-{message.guild.id}"]:
                if timeframe := await self.bot.db.fetchval(
                    """SELECT timeframe FROM automod_timeout WHERE guild_id = $1""",
                    message.guild.id,
                ):
                    try:
                        converted = humanfriendly.parse_timespan(timeframe)
                    except Exception:
                        converted = 20
                else:
                    converted = 20
                if await check():
                    if (
                        await self.bot.glory_cache.ratelimited(
                            f"amti-{message.author.id}", 1, converted
                        )
                        is not True
                    ):
                        #                     gather(
                        #                          *(
                        await message.delete()
                        if not message.author.is_timed_out():  #
                            await message.author.timeout(
                                datetime.now().astimezone()
                                + timedelta(seconds=converted),
                                reason=reason,
                            )
                        await context.normal(
                            f"has been **timed out** for `{get_humanized_time(converted)}`. **Reason:** {reason}",
                            delete_after=5,
                        )

                else:
                    if self.maintenance is True:
                        if message.author.name == "aiohttp":
                            logger.info("failed checks")
            return True
        return False

    async def add_reaction(
        self, message: discord.Message, reactions: list | str | bytes
    ):
        """Add reactions with validation and cleanup."""
        try:
            if isinstance(reactions, (str, bytes)):
                reactions = [reactions]

            # Global rate limit for adding reactions to prevent API abuse
            if await self.bot.glory_cache.ratelimited(
                f"reaction_global:{message.guild.id}", 5, 3
            ):
                return

            for reaction in reactions:
                try:
                    # Channel-specific rate limit to prevent spam in busy channels
                    if await self.bot.glory_cache.ratelimited(
                        f"reaction:{message.channel.id}", 2, 2
                    ):
                        await asyncio.sleep(1)
                        
                    # Message-specific rate limit to prevent too many reactions on a single message
                    if await self.bot.glory_cache.ratelimited(
                        f"reaction_msg:{message.id}", 3, 5
                    ):
                        return

                    if isinstance(reaction, str) and "<:" in reaction:
                        try:
                            emoji_id = int(reaction.split(":")[-1].rstrip(">"))
                            emoji = self.bot.get_emoji(emoji_id)
                            if not emoji:
                                await self.bot.db.execute(
                                    """DELETE FROM autoreact WHERE reaction = $1""",
                                    reaction,
                                )
                                await self.bot.db.execute(
                                    """DELETE FROM autoreact_event WHERE reaction = $1""",
                                    reaction,
                                )
                                logger.info(
                                    f"Removed invalid emoji {reaction} from database"
                                )
                                continue
                            reaction = emoji
                        except (ValueError, IndexError):
                            continue

                    await message.add_reaction(reaction)
                    await asyncio.sleep(0.5)

                except discord.NotFound:
                    break  # Message was deleted
                except discord.Forbidden:
                    break  # No permission
                except discord.HTTPException as e:
                    if e.code == 10014:  # Unknown Emoji error code
                        # Remove the invalid emoji from database
                        await self.bot.db.execute(
                            """DELETE FROM autoreact WHERE reaction = $1""",
                            str(reaction),
                        )
                        await self.bot.db.execute(
                            """DELETE FROM autoreact_event WHERE reaction = $1""",
                            str(reaction),
                        )
                        logger.info(f"Removed unknown emoji {reaction} from database")
                    else:
                        logger.error(f"Error adding reaction {reaction}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error in add_reaction: {e}")

    async def validate_reaction(self, reaction: str) -> bool:
        """Validate if a reaction emoji is valid and available."""
        try:
            # Handle custom emoji format
            if reaction.startswith("<") and reaction.endswith(">"):
                # Extract emoji ID
                emoji_id = int(reaction.split(":")[-1].rstrip(">"))
                try:
                    # Try to fetch the emoji
                    await self.bot.fetch_emoji(emoji_id)
                    return True
                except (discord.NotFound, discord.HTTPException):
                    return False

            # Handle unicode emoji
            if reaction.strip():  # Ensure not empty/whitespace
                try:
                    # Try to encode/decode to validate unicode emoji
                    reaction.encode("utf-8").decode("utf-8")
                    return True
                except UnicodeError:
                    return False

            return False
        except Exception:
            return False

    async def clean_invalid_reactions(self, guild_id: int) -> None:
        """Remove invalid reactions from the database."""
        try:
            # Get all autoreact data for the guild
            autoreacts = self.bot.cache.autoreacts.get(guild_id, {})
            if not autoreacts:
                return

            invalid_keywords = []
            updates = []

            for keyword, reactions in autoreacts.items():
                if not isinstance(reactions, (list, tuple)):
                    reactions = [reactions]

                valid_reactions = []
                for reaction in reactions:
                    # Handle string reactions that may be lists
                    if isinstance(reaction, list):
                        reaction = "".join(reaction)

                    if await self.validate_reaction(reaction):
                        valid_reactions.append(reaction)
                    else:
                        logger.info(
                            f"Removing invalid reaction {reaction} for keyword {keyword} in guild {guild_id}"
                        )

                if not valid_reactions and keyword not in [
                    "spoilers",
                    "images",
                    "emojis",
                    "stickers",
                ]:
                    invalid_keywords.append(keyword)
                elif valid_reactions != reactions:
                    # First delete existing reactions for this keyword
                    await self.bot.db.execute(
                        """
                        DELETE FROM autoreact 
                        WHERE guild_id = $1 AND keyword = $2
                        """,
                        guild_id,
                        keyword,
                    )

                    # Then add each valid reaction individually
                    for reaction in valid_reactions:
                        try:
                            await self.bot.db.execute(
                                """
                                INSERT INTO autoreact (guild_id, keyword, reaction)
                                VALUES ($1, $2, $3)
                                """,
                                guild_id,
                                keyword,
                                reaction,
                            )
                        except Exception as e:
                            logger.error(
                                f"Failed to insert reaction {reaction} for keyword {keyword}: {e}"
                            )
                            continue

                    # Update cache
                    self.bot.cache.autoreacts[guild_id][keyword] = valid_reactions

            # Remove entries with no valid reactions
            if invalid_keywords:
                await self.bot.db.execute(
                    """
                    DELETE FROM autoreact 
                    WHERE guild_id = $1 AND keyword = ANY($2)
                    """,
                    guild_id,
                    invalid_keywords,
                )

            # Update cache for removed keywords
            for keyword in invalid_keywords:
                self.bot.cache.autoreacts[guild_id].pop(keyword, None)

        except Exception as e:
            logger.error(f"Error cleaning invalid reactions for guild {guild_id}: {e}")

    # def uwu_catgirl_mode(self, text: str):
    #     # Define emotive faces and replacements
    #     emotive_faces = ["(・`ω´・)", ";;w;;", "owo", "UwU", ">w<", "^w^"]
    #     replacements = {
    #         "r": "w",
    #         "l": "w",
    #         "R": "W",
    #         "L": "W",
    #         "o": "owo",
    #         "O": "OwO",
    #         "no": "nu",
    #         "has": "haz",
    #         "you": "yu",
    #         "y": "yw",
    #         "the": "da",
    #     }

    #     # Replace characters and apply random emotive faces
    #     for key, value in replacements.items():
    #         text = text.replace(key, value)

    #     text += " " + random.choice(emotive_faces)
    #     return text

    @commands.Cog.listener("on_message")
    async def system_messages_event(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()

        if message.author.bot or not message.guild:
            return

        try:
            if isinstance(message.channel, discord.Thread):
                if not message.channel.parent:
                    return
                permissions = message.channel.parent.permissions_for(message.guild.me)
            else:
                permissions = message.channel.permissions_for(message.guild.me)

            if not all(
                [
                    permissions.send_messages,
                    permissions.moderate_members,
                    permissions.manage_messages,
                ]
            ):
                return
        except discord.ClientException:
            return

        if message.is_system and message.type == discord.MessageType.new_member:
            row = await self.bot.db.fetchrow(
                "SELECT * FROM system_messages WHERE guild_id = $1",
                message.guild.id,
            )

            if row:
                if self.system_sticker is None:
                    try:
                        self.system_sticker = await self.bot.fetch_sticker(
                            749054660769218631
                        )
                    except discord.NotFound:
                        return logger.error("System sticker not found.")

                await message.reply(stickers=[self.system_sticker])

    def debug(self, m: discord.Message, msg: str):
        if self.maintenance is True:
            if m.author.name == "aiohttp":
                logger.info(msg)
        return

    async def get_whitelist(self, message: discord.Message):
        """Get whitelist data for a message author"""
        try:
            checks = [message.author.id, message.channel.id]

            if isinstance(message.author, discord.Member):
                checks.extend(role.id for role in message.author.roles)

            data = await self.bot.db.fetch(
                """SELECT user_id, events FROM filter_whitelist 
                WHERE guild_id = $1 
                AND user_id = ANY($2)""",
                message.guild.id,
                checks,
            )
            return data or None

        except Exception as e:
            logger.error(f"Error in get_whitelist: {e}")
            return None

    async def check_event_whitelist(self, message: discord.Message, event: str) -> bool:
        if data := await self.get_whitelist(message):
            for d in data:
                # Handle potential whitespace in stored events
                events = [e.strip().lower() for e in d["events"].split(",")]
                if event.lower() in events or "all" in events:
                    logger.debug(
                        f"Whitelist triggered for {message.author} in {message.guild} - Event: {event}"
                    )
                    return True
        return False

    @commands.Cog.listener("on_guild_join")
    async def handle_guild_join(self, guild: discord.Guild) -> None:
        """
        Handle new guild joins and notify about larger servers joining the network.
        Includes rate limiting and validation checks.
        """
        try:
            if (
                await self.bot.db.fetchval(
                    """SELECT guild_id FROM guild_notifications WHERE guild_id = $1""",
                    guild.id,
                )
                or guild.member_count < self.min_member_threshold
            ):
                return

            invite = await self._get_guild_invite(guild)
            notification_data = {
                "method": "handle_guild_join_notification",
                "guild_id": guild.id,
                "guild_name": guild.name,
                "member_count": guild.member_count,
                "owner_id": guild.owner_id,
                "invite": str(invite) if invite else "No invite available",
                "timestamp": datetime.now().timestamp(),
            }

            await self.bot.db.execute(
                """INSERT INTO guild_notifications (guild_id) VALUES ($1)""", guild.id
            )

            try:
                await self.bot.connection.inform(notification_data, ["cluster2"])
            except Exception as e:
                logger.error(f"IPC error for guild {guild.id}: {e}")

        except Exception as e:
            logger.error(
                f"Error handling guild join for {guild.id}: {e}", exc_info=True
            )

    async def _get_guild_invite(self, guild: discord.Guild) -> Optional[discord.Invite]:
        """Helper method to get a guild invite if possible"""
        if not guild.me.guild_permissions.create_instant_invite:
            return None

        for channel in guild.text_channels:
            try:
                if channel.permissions_for(guild.me).create_instant_invite:
                    return await channel.create_invite(reason="greed network")
            except discord.Forbidden:
                continue
            except Exception as e:
                logger.error(f"Error creating invite in {channel.id}: {e}")
                continue

        return None

    async def handle_guild_join_notification(self, source: str, *, data: dict) -> bool:
        """
        Process guild join notifications received via IPC.
        Sends channel notifications and DMs server owner.
        """
        try:
            channel = self.bot.get_channel(self.notification_channel_id)
            if not channel:
                logger.error("Notification channel not found")
                return False

            try:
                await channel.send(
                    f"New network member - {data.get('guild_name', 'Unknown')} ({data.get('member_count', 0)} members)\n"
                    f"Join link: {data.get('invite', 'No invite available')}"
                )
            except Exception as e:
                logger.error(f"Failed to send channel notification: {e}")
                return False

            try:
                owner_id = data.get("owner_id")
                if owner_id:
                    owner = await self.bot.fetch_user(owner_id)
                    if owner:
                        embed = discord.Embed(
                            title="Network Integration",
                            description=(
                                f"Your server **{data.get('guild_name', 'Unknown')}** has been networked with "
                                f"[Greed](https://discord.gg/greedbot) due to having over {self.min_member_threshold} members "
                                f"({data.get('member_count', 0)})."
                            ),
                            color=self.bot.color,
                            timestamp=datetime.fromtimestamp(
                                data.get("timestamp", time.time())
                            ),
                        )
                        embed.set_footer(text="Greed Network")

                        await owner.send(embed=embed)
                        logger.info(f"Sent owner notification to {owner_id}")

            except discord.Forbidden:
                logger.warning(f"Could not DM owner {data.get('owner_id')}")
            except Exception as e:
                logger.error(f"Error in owner notification: {e}")

            return True

        except Exception as e:
            logger.error(f"Error handling notification: {e}", exc_info=True)
            return False

    @commands.Cog.listener("on_message_edit")
    async def filter_response_edit(
        self, before: discord.Message, after: discord.Message
    ):
        # Ignore edits from bots
        if before.author.bot:
            return
        # Ignore edits in DMs
        if before.guild is None:
            return
        # Check if the edited message is a valid command
        ctx = await self.bot.get_context(after)
        if ctx.valid:
            return
        # Process the edited message through the filter
        return await self.on_message_filter(after)

    @commands.Cog.listener("on_message")
    async def on_message_filter(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()

        if message.author.bot or not message.guild:
            return

        try:
            if isinstance(message.channel, discord.Thread):
                if not message.channel.parent:
                    return
                permissions = message.channel.parent.permissions_for(message.guild.me)
            else:
                permissions = message.channel.permissions_for(message.guild.me)

            if not all(
                [
                    permissions.send_messages,
                    permissions.moderate_members,
                    permissions.manage_messages,
                ]
            ):
                return self.debug(message, "Missing required permissions")

        except (discord.ClientException, AttributeError):
            return

        context = await self.bot.get_context(message)

        # Fetch filter events and AFK data concurrently
        db_fetch = self.bot.db.fetch(
            "SELECT event FROM filter_event WHERE guild_id = $1", context.guild.id
        )
        afk_fetch = asyncio.create_task(
            asyncio.to_thread(lambda: self.bot.afks.get(message.author.id))
        )

        filter_events, afk_data = await asyncio.gather(
            db_fetch, afk_fetch, return_exceptions=True
        )

        # Process filter events
        filter_events = (
            tuple(record.event for record in filter_events)
            if isinstance(filter_events, list)
            else ()
        )

        # Handle AFK logic
        if isinstance(afk_data, dict):
            if not context.valid or context.command.qualified_name.lower() != "afk":
                await self.do_afk(message, context, afk_data)

        # Handle AFK mentions with improved rate limiting
        if message.mentions:
            # Use a global rate limit for all AFK mentions in this guild
            if not await self.bot.glory_cache.ratelimited(
                f"afk_mentions:{message.guild.id}", 3, 10
            ):
                # Process mentions with individual rate limits
                mention_tasks = []
                processed_users = set()  # Track which users we've already processed

                for user in message.mentions:
                    # Skip duplicate mentions of the same user
                    if user.id in processed_users:
                        continue
                    processed_users.add(user.id)

                    if user_afk := self.bot.afks.get(user.id):
                        # Use a per-user rate limit to avoid spamming the same user's AFK status
                        if not await self.bot.glory_cache.ratelimited(
                            f"afk_user:{user.id}", 1, 30
                        ):
                            mention_tasks.append(
                                self.handle_afk_mention(
                                    context, message, user, user_afk
                                )
                            )

                            # Limit to max 3 AFK mentions per message to avoid spam
                            if len(mention_tasks) >= 3:
                                break

                if mention_tasks:
                    # Process mentions sequentially instead of all at once
                    for task in mention_tasks:
                        await task
                        await asyncio.sleep(0.5)  # Add a small delay between messages

        block_command_execution = False

        # Fetch automod timeout settings
        timeframe = await self.bot.db.fetchval(
            """SELECT timeframe FROM automod_timeout WHERE guild_id = $1""",
            message.guild.id,
        )
        converted = 5  # Default timeout duration
        if timeframe:
            try:
                converted = humanfriendly.parse_timespan(timeframe)
            except Exception:
                pass

        async def check():
            """Check if the user is subject to moderation."""
            return all(
                (
                    message.author.id
                    not in (message.guild.owner_id, message.guild.me.id),
                    not message.author.guild_permissions.administrator,
                    (
                        message.author.top_role.position
                        <= message.guild.me.top_role.position
                        if message.author.top_role
                        else True
                    ),
                )
            )

        async def apply_punishment(reason: str):
            """Apply the appropriate punishment based on guild settings."""
            try:
                await message.delete()
            except Exception as e:
                logger.error(f"Failed to delete message in filter: {e}")
                pass

            punishment = await self.bot.db.fetchval(
                "SELECT punishment FROM filter_setup WHERE guild_id = $1",
                message.guild.id,
            )
            
            logger.info(f"Applying filter punishment in {message.guild.id}: {punishment} for user {message.author.id}, reason: {reason}")

            if punishment == "timeout":
                await self.do_timeout(message, reason, context)
            elif punishment == "kick":
                if message.guild.me.guild_permissions.kick_members:
                    await message.author.kick(reason=reason)
                else:
                    self.debug(message, "Missing kick permissions")
            elif punishment == "ban":
                if message.guild.me.guild_permissions.ban_members:
                    await message.author.ban(reason=reason)
                else:
                    self.debug(message, "Missing ban permissions")
            elif punishment == "jail":
                try:
                    await Moderation.do_jail(message.author, reason=reason)
                except Exception as e:
                    self.debug(message, f"Failed to jail user: {e}")

        # Before processing any filters, check for whitelist first
        if await self.check_event_whitelist(message, "all"):
            return

        # Then in each filter section, check specific event whitelist:
        if (
            "keywords" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("keywords", self.DICT)
            .get("is_enabled", False)
            and not await self.check_event_whitelist(message, "keywords")
            and not block_command_execution
        ):
            logger.debug(f"Checking keywords filter for {message.guild.id} - Keywords: {self.bot.cache.filter.get(context.guild.id, [])}")
            for keyword in self.bot.cache.filter.get(context.guild.id, []):
                if keyword.lower().endswith("*"):
                    keyword_base = keyword.replace("*", "").lower()
                    if keyword_base in message.content.lower():
                        logger.info(f"Keyword filter triggered: '{keyword_base}' found in message from {message.author.id} in {message.guild.id}")
                        await apply_punishment("muted by the chat filter")
                        break
                else:
                    content_words = set(message.content.lower().split())
                    # Check both exact word matches and substring matches
                    if keyword.lower() in content_words or keyword.lower() in message.content.lower():
                        logger.info(f"Keyword filter triggered: '{keyword}' found in message from {message.author.id} in {message.guild.id}")
                        await apply_punishment("muted by the chat filter")
                        break

        # Spoiler filter
        if (
            "spoilers" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("spoilers", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if not await self.check_event_whitelist(message, "spoilers"):
                if message.content.count("||") >= (
                    self.bot.cache.filter_event[context.guild.id]["spoilers"][
                        "threshold"
                    ]
                    * 2
                ):
                    await apply_punishment("Muted by spoiler filter")
                    block_command_execution = True

        # Headers filter
        if (
            "headers" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("headers", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if not await self.check_event_whitelist(message, "headers"):
                for m in message.content.split("\n"):
                    if m.startswith("# "):
                        if (
                            len(m.split(" "))
                            >= self.bot.cache.filter_event[context.guild.id]["headers"][
                                "threshold"
                            ]
                        ):
                            await apply_punishment("Muted by the header filter")
                            block_command_execution = True

        # Images filter
        if (
            "images" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("images", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if not await self.check_event_whitelist(message, "images"):
                if len(message.attachments) > 0:
                    threshold = self.bot.cache.filter_event[context.guild.id]["images"][
                        "threshold"
                    ]
                    for attachment in message.attachments:
                        if await self.bot.glory_cache.ratelimited(
                            f"ai-{message.guild.id}-{message.author.id}", threshold, 10
                        ):
                            await apply_punishment("Muted by my image filter")
                            block_command_execution = True

        # Links filter
        if (
            "links" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("links", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if not await self.check_event_whitelist(message, "links"):
                matches = url_regex.findall(message.content)
                if len(matches) > 0:
                    for m in matches:
                        if "tenor.com" not in m:
                            reason = "muted by the link filter"
                            await apply_punishment(reason)
                            block_command_execution = True

        # Spam filter
        if (
            "spam" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("spam", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if await self.bot.glory_cache.ratelimited(
                f"amtis-{message.guild.id}", 20, 10
            ):
                if await check():
                    if not await self.check_event_whitelist(message, "spam"):
                        if (
                            await self.bot.glory_cache.ratelimited(
                                f"amasm-{message.channel.id}", 1, 300
                            )
                            == 0
                        ):
                            await message.channel.edit(
                                slowmode_delay=5, reason="Auto Mod Auto Slow Mode"
                            )
                            await message.channel.send(
                                embed=discord.Embed(
                                    description=f"Set the channel to **slow mode due to excessive spam**, it will be disabled in <t:{int(datetime.now().timestamp())+500}:R>"
                                )
                            )
                            ensure_future(self.revert_slowmode(message.channel))
            if (
                await self.bot.glory_cache.ratelimited(
                    f"rl:message_spam{message.author.id}-{message.guild.id}",
                    self.bot.cache.filter_event[context.guild.id]["spam"]["threshold"]
                    - 1,
                    5,
                )
                != 0
            ):
                if await self.bot.glory_cache.ratelimited(
                    f"spam:message{message.author.id}:{message.guild.id}", 1, 4
                ):
                    if await check():
                        if not await self.check_event_whitelist(message, "spam"):
                            if message.guild.me.guild_permissions.moderate_members:
                                await message.author.timeout(
                                    datetime.now().astimezone()
                                    + timedelta(seconds=converted)
                                )
                else:
                    if not await self.check_event_whitelist(message, "spam"):
                        if await check():
                            reason = "flooding chat"
                            await apply_punishment(reason)
                            block_command_execution = True
                if not await self.check_event_whitelist(message, "spam"):
                    if await check():
                        if message.guild.me.guild_permissions.manage_messages:
                            try:
                                await message.channel.purge(
                                    limit=10,
                                    check=lambda m: m.author.id == message.author.id,
                                    bulk=True,
                                    reason="Auto-moderation: Spam filter",
                                )
                            except (
                                discord.NotFound,
                                discord.Forbidden,
                                discord.HTTPException,
                            ) as e:
                                pass
                            finally:
                                block_command_execution = True

        # Emojis filter
        if (
            "emojis" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("emojis", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if (
                len(find_emojis(message.content))
                >= self.bot.cache.filter_event[context.guild.id]["emojis"]["threshold"]
            ):
                if not await self.check_event_whitelist(message, "emojis"):
                    reason = "muted by the emoji filter"
                    await apply_punishment(reason)
                    block_command_execution = True

        # Invites filter
        if (
            "invites" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("invites", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if not await self.check_event_whitelist(message, "invites"):
                if len(message.invites) > 0:
                    reason = "muted by the invite filter"
                    await apply_punishment(reason)
                    block_command_execution = True

        # Caps filter
        if (
            "caps" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("caps", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if not await self.check_event_whitelist(message, "caps"):
                if (
                    len(tuple(c for c in message.content if c.isupper()))
                    >= self.bot.cache.filter_event[context.guild.id]["caps"][
                        "threshold"
                    ]
                ):
                    reason = "muted by the cap filter"
                    await apply_punishment(reason)
                    block_command_execution = True

        # Mass mention filter
        if (
            "massmention" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, self.DICT)
            .get("massmention", self.DICT)
            .get("is_enabled", False)
            and not block_command_execution
        ):
            if not await self.check_event_whitelist(message, "massmention"):
                if (
                    len(message.mentions)
                    >= self.bot.cache.filter_event[context.guild.id]["massmention"][
                        "threshold"
                    ]
                ):
                    reason = "muted by the mention filter"
                    await apply_punishment(reason)
                    block_command_execution = True

        if block_command_execution:
            return

        # Autoreact logic
        if self.bot.cache.autoreacts.get(message.guild.id):

            async def do_autoreact():
                try:
                    keywords_covered = []
                    for keyword, reactions in self.bot.cache.autoreacts[
                        message.guild.id
                    ].items():
                        if keyword not in ["spoilers", "images", "emojis", "stickers"]:
                            if keyword in message.content:
                                if await self.bot.glory_cache.ratelimited(
                                    f"autoreact:{message.guild.id}:{keyword}", 1, 2
                                ):
                                    continue

                                await asyncio.gather(
                                    *[
                                        self.add_reaction(message, reaction)
                                        for reaction in reactions
                                    ]
                                )
                                keywords_covered.append(keyword)
                except Exception as e:
                    logger.error(f"Autoreact error: {e}")

            with suppress(discord.errors.HTTPException):
                asyncio.create_task(do_autoreact())

            tasks = []
            if await self.get_event_types(message):

                async def do_autoreact_event(_type: str):
                    _ = f"rl:autoreact:{message.guild.id}:{_type}"
                    if await self.bot.glory_cache.ratelimited(_, 5, 30):
                        return
                    reactions = self.bot.cache.autoreacts[message.guild.id].get(_type)
                    if reactions:
                        await self.add_reaction(message, reactions)

                events = await self.get_event_types(message)

                if "images" in events and any(
                    attachment.content_type.startswith(("image/", "video/"))
                    for attachment in message.attachments
                ):
                    await do_autoreact_event("images")

                for event_type in ["spoilers", "emojis", "stickers"]:
                    if event_type in events:
                        condition = False
                        if event_type == "spoilers" and message.content.count("||") > 2:
                            condition = True
                        elif event_type == "emojis" and find_emojis(message.content):
                            condition = True
                        elif event_type == "stickers" and message.stickers:
                            condition = True

                        if condition:
                            tasks.append(do_autoreact_event(event_type))

            try:
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
            except Exception:
                pass

        if not block_command_execution:
            return

    async def handle_afk_mention(self, ctx, message, user, user_afk):
        # No need for additional rate limiting here since we already did it above
        embed = discord.Embed(
            description=f"{message.author.mention}: {user.mention} is AFK: **{user_afk['status']} ** - {humanize.naturaltime(datetime.now() - user_afk['date'])}",
            color=0x9EAFBF,
        )
        await ctx.send(embed=embed)

    async def create_countertables(self):
        """Ensure the necessary tables exist in the database."""
        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS counter_channels (
                channel_id BIGINT PRIMARY KEY,
                current_count INTEGER NOT NULL
            )
            """
        )

    @commands.Cog.listener("on_member_join")
    async def on_member_join(self, member: discord.Member):
        if not member.guild.me.guild_permissions.manage_roles:
            return

        await asyncio.gather(
            self.autorole_give(member),
            self.jail_check(member),
            self.pingonjoin_listener(member),
            return_exceptions=True,
        )

    async def check_roles(self, member: discord.Member) -> bool:
        if len(member.roles) > 0:
            roles = [
                r
                for r in member.roles
                if r
                not in (member.guild.premium_subscriber_role, member.guild.default_role)
            ]
            if len(roles) > 0:
                return True
        return False

    def check_role(self, role: discord.Role) -> bool:
        if prem_role := role.guild.premium_subscriber_role:
            if role.id != prem_role.id:
                pass
            else:
                return False
        if default := role.guild.default_role:
            if role.id != default.id:
                pass
            else:
                return False
        return True

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        if member.bot:
            return
        if len(member.roles) > 0 and await self.check_roles(member) is not False:
            await self.bot.redis.set(
                f"r-{member.guild.id}-{member.id}",
                orjson.dumps(
                    [r.id for r in member.roles if self.check_role(r) is not False]
                ),
                ex=9000,
            )

    @commands.Cog.listener("on_member_update")
    async def booster_role_event(self, before: discord.Member, after: discord.Member):
        if after.bot:
            return

        if not after.guild.me.guild_permissions.manage_roles:
            return
            
        # Create a cache key for this member's boost status
        cache_key = f"booster_role:{after.guild.id}:{after.id}"
        
        # Check if we've recently processed this member's boost status
        if await self.bot.glory_cache.get(cache_key):
            return

        # Handle boosting role add
        if before.premium_since is None and after.premium_since is not None:
            # Set cache to prevent repeated processing
            await self.bot.glory_cache.set(cache_key, "1", 30)  # Cache for 30 seconds
            
            if data := await self.bot.db.fetchrow(
                "SELECT * FROM guild.boost WHERE guild_id = $1", before.guild.id
            ):
                channel = before.guild.get_channel(data.channel_id)
                if isinstance(channel, discord.TextChannel):
                    if channel.permissions_for(after.guild.me).send_messages:
                        await self.bot.send_embed(channel, data.message, user=after)

            if data := await self.bot.db.fetch(
                """SELECT role_id FROM premiumrole WHERE guild_id = $1""",
                after.guild.id,
            ):
                for role_id in data:
                    if role := after.guild.get_role(role_id):
                        if (
                            role not in after.roles
                            and role.position < after.guild.me.top_role.position
                        ):
                            with suppress(discord.Forbidden):
                                await after.add_roles(role, reason="Booster Role")

        # Handle boosting role remove
        elif before.premium_since is not None and after.premium_since is None:
            # Set cache to prevent repeated processing
            await self.bot.glory_cache.set(cache_key, "1", 30)  # Cache for 30 seconds
            
            if data := await self.bot.db.fetch(
                """SELECT role_id FROM premiumrole WHERE guild_id = $1""",
                after.guild.id,
            ):
                for role_id in data:
                    if role := after.guild.get_role(role_id):
                        if (
                            role in after.roles
                            and role.position < after.guild.me.top_role.position
                        ):
                            with suppress(discord.Forbidden):
                                await after.remove_roles(role, reason="Booster Role")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages in enabled counter channels."""
        if message.author.bot:
            return

        row = await self.bot.db.fetchrow(
            "SELECT current_count FROM counter_channels WHERE channel_id = $1",
            message.channel.id,
        )

        if not row:
            return

        current_count = row["current_count"]
        try:
            # Ensure the message content matches the expected count
            if int(message.content) == current_count + 1:
                new_count = current_count + 1

                # Update the database
                await self.bot.db.execute(
                    "UPDATE counter_channels SET current_count = $1 WHERE channel_id = $2",
                    new_count,
                    message.channel.id,
                )

                # React to the message with a green check mark
                await message.add_reaction("✅")

                # Send a milestone message for every hundredth count
                if new_count % 100 == 0:
                    embed = discord.Embed(
                        title="🎉 Milestone Reached!",
                        description=f"You've reached {new_count}! Say {new_count + 1} to continue.",
                        color=discord.Color.green(),
                    )
                    await message.channel.send(embed=embed)

                # Reset and purge messages when count reaches 1000
                if new_count == 1000:
                    await message.channel.send(
                        "Counter reset to 1. Deleting previous messages..."
                    )
                    await message.channel.purge()
                    await self.bot.db.execute(
                        "UPDATE counter_channels SET current_count = 1 WHERE channel_id = $1",
                        message.channel.id,
                    )
                    first_message = await message.channel.send("1")
                    await first_message.add_reaction("✅")
            else:
                # Delete messages with incorrect or out-of-sequence numbers
                await message.delete()
        except ValueError:
            # Delete non-numeric messages
            await message.delete()

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):  # type: ignore
        if after.bot:
            return

        if (
            after.top_role.position < after.guild.me.top_role.position
            and after.id != after.guild.owner_id
        ):
            if after.guild.id in self.bot.cache.filter:
                if (
                    "nicknames" in self.bot.cache.filter_event.get(after.guild.id, DICT)
                    and self.bot.cache.filter_event[after.guild.id].get(
                        "links", {"is_enabled": False}
                    )["is_enabled"]
                    is True
                ):
                    if after.nick in self.bot.cache.filter[after.guild.id]:
                        await after.edit(
                            nick=None,
                            reason=f"{self.bot.user.name.title()} Moderation: Nickname contains a filtered word",
                        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.id in (self.bot.user.id, 123):
            return

        if not message.guild:
            return

        if not message.channel.permissions_for(message.guild.me).view_channel:
            return

        await self.bot.snipes.add_entry("snipe", message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content == after.content or before.author.id == self.bot.user.id:
            return

        if not before.guild:
            return

        if not before.channel.permissions_for(before.guild.me).view_channel:
            return

        await self.bot.snipes.add_entry("editsnipe", before)

    @commands.Cog.listener()
    async def on_reaction_remove(
        self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]
    ):
        if not reaction.message.guild:
            return

        if not reaction.message.channel.permissions_for(
            reaction.message.guild.me
        ).view_channel:
            return

        await self.bot.snipes.add_entry("rs", (reaction, user))

    @commands.Cog.listener("on_member_join")
    async def autorole_give(self, member: discord.Member):
        # Create a member-specific cache key to prevent repeated processing for the same member
        member_cache_key = f"autorole:member:{member.guild.id}:{member.id}"
        
        # Check if we've recently processed this member
        if await self.bot.glory_cache.get(member_cache_key):
            return
            
        if (
            await self.bot.glory_cache.ratelimited(f"autorole:{member.guild.id}", 5, 10)
            == 0
        ):
            if not member.guild.me.guild_permissions.manage_roles:
                return

            if data := self.bot.cache.autorole.get(member.guild.id):
                roles = []
                for role_id in data:
                    if role := member.guild.get_role(role_id):
                        if role.position < member.guild.me.top_role.position:
                            roles.append(role)

                if (
                    roles
                    and await self.bot.glory_cache.ratelimited("ar", 4, 6) is not True
                ):
                    await self.bot.glory_cache.set(member_cache_key, 1, 30)  
                    
                    await asyncio.sleep(4)
                    with suppress(discord.Forbidden, discord.HTTPException):
                        await member.add_roles(*roles, reason="Auto Role")

    @tasks.loop(minutes=5)
    async def voicemaster_clear(self):
        """Clean up empty voice master channels periodically."""
        try:
            if await self.bot.glory_cache.ratelimited("voicemaster_clear", 1, 10):
                return

            rows = await self.bot.db.fetch(
                """SELECT guild_id, channel_id FROM voicemaster_data"""
            )

            # Process channels in smaller batches
            for batch in [rows[i : i + 10] for i in range(0, len(rows), 10)]:
                delete_tasks = []

                for row in batch:
                    if guild := self.bot.get_guild(row["guild_id"]):
                        if channel := guild.get_channel(row["channel_id"]):
                            active_members = [m for m in channel.members if not m.bot]
                            if not active_members:
                                delete_tasks.append(
                                    self._delete_channel(channel, row["channel_id"])
                                )

                if delete_tasks:
                    await asyncio.gather(*delete_tasks, return_exceptions=True)

                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"Error in voicemaster_clear: {str(e)}")

    async def _delete_channel(self, channel: discord.VoiceChannel, channel_id: int):
        with suppress(
            discord.NotFound, discord.Forbidden, commands.BotMissingPermissions
        ):
            await channel.delete(reason="Voice master cleanup - channel empty")

        await self.bot.db.execute(
            """DELETE FROM voicemaster_data WHERE channel_id = $1""", channel_id
        )

        logger.debug(f"Cleaned up empty voice channel {channel_id}")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        return await self.voicemaster_event(member, before, after)

    @ratelimit("voicemaster_guild:{member.guild.id}", 3, 5, False)
    async def create_and_move(
        self,
        member: discord.Member,
        after: discord.VoiceState,
        status: Optional[str] = None,
    ):
        guild_rl = await self.bot.glory_cache.ratelimited(
            f"voicemaster_guild:{member.guild.id}", 5, 10
        )
        user_rl = await self.bot.glory_cache.ratelimited(
            f"voicemaster_move:{member.id}", 5, 10
        )

        if guild_rl > 0:
            await asyncio.sleep(guild_rl)
            return None

        if user_rl > 0:
            await asyncio.sleep(user_rl)
            return None

        try:
            overwrites = {
                member: discord.PermissionOverwrite(connect=True, view_channel=True)
            }
            channel = await member.guild.create_voice_channel(
                name=f"{member.name}'s channel",
                user_limit=0,
                category=after.channel.category,
                overwrites=overwrites,
            )
            if status:
                await channel.edit(status=status)
            await asyncio.sleep(0.3)
            try:
                await member.move_to(channel)
            except Exception:
                with suppress(discord.errors.NotFound):
                    await channel.delete()
                return None
            return channel
        except Exception:
            return None

    async def voicemaster_event(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if (
            await self.bot.glory_cache.ratelimited(f"vm_event:{member.guild.id}", 20, 5)
            == 0
        ):
            if self.bot.is_ready() and not (
                before.channel
                and after.channel
                and before.channel.id == after.channel.id
            ):
                if data := await self.bot.db.fetchrow(
                    """
                    SELECT voicechannel_id, category_id
                    FROM voicemaster
                    WHERE guild_id = $1
                    """,
                    member.guild.id,
                ):
                    join_chanel = data["voicechannel_id"]
                    data["category_id"]  # type: ignore
                    if after.channel and after.channel.id == join_chanel:
                        if await self.bot.glory_cache.ratelimited(
                            f"rl:voicemaster_channel_create:{member.guild.id}", 15, 30
                        ):
                            if (
                                before.channel
                                and before.channel != join_chanel
                                and len(before.channel.members) == 0
                                and await self.bot.db.fetchrow(
                                    "SELECT * FROM voicemaster_data WHERE channel_id = $1",
                                    before.channel.id,
                                )
                            ):
                                await self.bot.db.execute(
                                    """
                                    DELETE FROM voicemaster_data
                                    WHERE channel_id = $1
                                    """,
                                    before.channel.id,
                                )
                                with suppress(discord.errors.NotFound):
                                    await before.channel.delete()

                        else:
                            status = None
                            if stat := await self.bot.db.fetchrow(
                                """SELECT status FROM vm_status WHERE user_id = $1""",
                                member.id,
                            ):
                                status = stat["status"]
                            channel = await self.create_and_move(member, after, status)
                            if channel is not None:
                                await self.bot.db.execute(
                                    """
                                    INSERT INTO voicemaster_data
                                    (channel_id, guild_id, owner_id)
                                    VALUES ($1, $2, $3)
                                    """,
                                    channel.id,
                                    channel.guild.id,
                                    member.id,
                                )

                            if (
                                before.channel
                                and before.channel != join_chanel
                                and len(before.channel.members) == 0
                                and await self.bot.db.fetchrow(
                                    "SELECT * FROM voicemaster_data WHERE channel_id = $1",
                                    before.channel.id,
                                )
                            ):
                                await self.bot.db.execute(
                                    """
                                    DELETE FROM voicemaster_data
                                    WHERE channel_id = $1
                                    """,
                                    before.channel.id,
                                )
                                with suppress(discord.errors.NotFound):
                                    await before.channel.delete()

                    elif before and before.channel:
                        voice = await self.bot.db.fetchval(
                            """
                            SELECT channel_id
                            FROM voicemaster_data
                            WHERE channel_id = $1
                            """,
                            before.channel.id,
                        )
                        if len(before.channel.members) == 0 and voice:
                            if before.channel.id == voice:
                                await self.bot.db.execute(
                                    """
                                    DELETE FROM voicemaster_data
                                    WHERE channel_id = $1
                                    """,
                                    before.channel.id,
                                )
                                with suppress(discord.errors.NotFound):
                                    await before.channel.delete()
                            elif before.channel.id == data:
                                await asyncio.sleep(5)
                                voice = await self.bot.db.fetchval(
                                    """
                                    SELECT channel_id
                                    FROM voicemaster_data
                                    WHERE owner_id = $1
                                    """,
                                    member.id,
                                )
                                if before.channel.id == voice:
                                    await self.bot.db.execute(
                                        """
                                        DELETE FROM voicemaster_data
                                        WHERE owner_id = $1
                                        """,
                                        member.id,
                                    )
                                    with suppress(discord.errors.NotFound):
                                        await before.channel.delete()

    @commands.Cog.listener("on_member_join")
    @ratelimit("pingonjoin:{guild.id}", 2, 3, False)
    async def pingonjoin_listener(self, member: discord.Member):
        """Groups multiple joins together and pings them in a single message."""
        if not member.guild.me.guild_permissions.send_messages:
            return

        if await self.bot.glory_cache.ratelimited(f"poj:{member.guild.id}", 1, 1) != 0:
            return

        try:
            async with self.locks[f"pingonjoin:{member.guild.id}"]:
                cache_key = f"pingonjoin:{member.guild.id}"
                config = await cache.get(cache_key)
                if not config:
                    config = await self.bot.db.fetchrow(
                        "SELECT channel_id, threshold, message FROM pingonjoin WHERE guild_id = $1",
                        member.guild.id,
                    )
                    if config:
                        config = dict(config)
                        await cache.set(cache_key, config)

                if not config:
                    return

                channel = member.guild.get_channel(config["channel_id"])
                if not channel:
                    return logger.error(
                        f"Channel {config['channel_id']} not found in guild {member.guild.id}"
                    )

                delay = min(max(config.get("threshold", 3) + 1, 2), 10)
                message_template = config.get("message") or "{user.mention}"
                members = [member]

                deadline = asyncio.get_event_loop().time() + delay
                remaining_time = delay

                while len(members) < 5 and remaining_time > 0:
                    try:
                        new_member = await asyncio.wait_for(
                            self.bot.wait_for(
                                "member_join",
                                check=lambda m: m.guild.id == member.guild.id,
                            ),
                            timeout=remaining_time,
                        )
                        members.append(new_member)
                        remaining_time = deadline - asyncio.get_event_loop().time()
                    except asyncio.TimeoutError:
                        break
                    except asyncio.TimeoutError:
                        break
                    await asyncio.sleep(0)  # Yield control periodically

                # Process mentions in chunks to avoid blocking
                mentions = []
                for i in range(0, len(members), 5):
                    chunk = members[i : i + 5]
                    mentions.extend(m.mention for m in chunk)
                    await asyncio.sleep(0)

                final_message = message_template.replace(
                    "{user.mention}", ", ".join(mentions)
                )

                with suppress(discord.Forbidden, discord.HTTPException):
                    msg = await channel.send(
                        final_message,
                        allowed_mentions=discord.AllowedMentions(users=True),
                    )
                    await msg.delete(delay=delay + 1)

        except Exception as e:
            logger.error(f"Error in pingonjoin_listener for {member.guild.id}: {e}")

    @commands.Cog.listener("on_member_join")
    async def jail_check(self, member: discord.Member):
        if (
            await self.bot.glory_cache.ratelimited(
                f"jail_check:{member.guild.id}", 1, 1
            )
            == 0
        ):
            """Check and apply jail role if member was previously jailed"""
            try:
                # Check if member was previously jailed
                jailed = await self.bot.db.fetchrow(
                    "SELECT * FROM jailed WHERE guild_id = $1 AND user_id = $2",
                    member.guild.id,
                    member.id,
                )

                if not jailed:
                    return

                jail_role = discord.utils.get(member.guild.roles, name="jailed")
                if not jail_role:
                    return

                removable_roles = [
                    role
                    for role in member.roles
                    if role != member.guild.default_role
                    and role.position < member.guild.me.top_role.position
                ]

                if removable_roles:
                    with suppress(discord.Forbidden, discord.HTTPException):
                        await member.remove_roles(
                            *removable_roles, reason="Member was previously jailed"
                        )

                with suppress(discord.Forbidden, discord.HTTPException):
                    await member.add_roles(
                        jail_role, reason="Member was previously jailed"
                    )

            except Exception as e:
                logger.error(f"Error in jail_check for {member}: {str(e)}")


async def setup(bot):
    await bot.add_cog(Events(bot))
