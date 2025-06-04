from __future__ import annotations

import asyncio
import contextlib
import io
import json
import random
import re  # type: ignore
import unicodedata
from asyncio import ensure_future, gather, sleep
from base64 import b64decode
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timedelta
from typing import Any, List, Optional, Union

import aiohttp
import discord
import humanfriendly
import humanize
import orjson
from boltons.cacheutils import LRI
from discord import Embed, Guild, Message
from discord.ext import commands, tasks
from loguru import logger
from rival_tools import ratelimit, timeit  # type: ignore
from tools import expressions

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
    def __init__(self, bot):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)
        self.no_snipe = []
        self.maintenance = True
        self.voicemaster_clear.start()
        self.system_sticker = None
        self.last_posted = None
        self.bot.audit_cache = {}

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

    def random_pfp(self, message: discord.Message):
        return random.choice(message.attachments)

    def random_avatar(self):
        choice = random.choice(self.bot.users)
        return choice.display_avatar.url

    @commands.Cog.listener("on_audit_log_entry_create")
    async def moderation_logs(self, entry: discord.AuditLogEntry):
        return await self.bot.modlogs.do_log(entry)

    #    @commands.Cog.listener("on_socket_raw_receive")
    async def test_interactions(self, payload: str):
        if "1203455800236965958" not in payload:
            return
        payload = json.loads(payload)
        logger.info(payload)
        return
        if guild_id := payload.get("guild_id"):
            if int(guild_id) == 1203455800236965958:
                logger.info(payload)

    @commands.Cog.listener("on_command_completion")
    async def command_moderation_logs(self, ctx: commands.Context):
        try:
            return await self.bot.modlogs.do_log(ctx)
        except Exception as e:
            logger.info(
                f"The below exception was raised in {ctx.command.qualified_name}"
            )
            raise e

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

    @tasks.loop(minutes=4)
    async def do_pfp_loop(self):
        pfps = await self.get_pfps()
        embeds = [Embed(title="new pfp", url=p).set_image(url=p) for p in pfps]
        logger.info("sending avatars now")
        for guild_id, channel_id in await self.bot.db.fetch(
            """SELECT guild_id,channel_id FROM pfps"""
        ):
            if guild := self.bot.get_guild(int(guild_id)):
                if channel := guild.get_channel(int(channel_id)):
                    try:
                        await channel.send(embeds=embeds)
                    except Exception as e:
                        logger.info(f"autopfp loop raised an exception: {e}")
                        pass

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

    async def namehistory_event(self, before, after):
        if before.id == 352190010998390796:
            logger.info("User Change Detected")
            logger.info(f"{before.banner} - {after.banner}")
        if before.name != after.name:
            name = before.name
            nt = "username"
        elif before.global_name != after.global_name:
            name = before.global_name
            nt = "globalname"
        elif before.display_name != after.display_name:
            name = before.display_name
            nt = "display"
        else:
            return
        if name is None:
            return
        await self.bot.db.execute(
            """INSERT INTO names (user_id, type, username, ts) VALUES($1,$2,$3,$4) ON CONFLICT(user_id,username,ts) DO NOTHING""",
            before.id,
            nt,
            name,
            datetime.now(),
        )

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
        if logs := self.bot.audit_cache.get(guild.id):
            if [
                l
                for l in logs  # noqa: E741
                if l.action == discord.AuditLogAction.member_update
                and (l.target.id == member.id or l.user.id == member.id)
                and l.user.bot is not True
                and l.user.id != self.bot.user.id
            ]:
                return True
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
    async def forcenick_event(self, before: discord.Member, after: discord.Member):
        if not (data := self.bot.cache.forcenick.get(before.guild.id)):
            return

        if not data.get(before.id):
            return
        if after.guild.me.guild_permissions.administrator is not True:
            return
        if after.guild.me.top_role < after.top_role:
            return
        if rl_check := await self.bot.glory_cache.ratelimited(
            f"forcenick{after.guild.id}", 4, 20
        ):
            await asyncio.sleep(rl_check)

        if await self.forcenick_check(after.guild, after) is True:
            if has_data := self.bot.cache.forcenick.get(before.guild.id):
                if name := has_data.get(before.id):
                    if after.nick != name:
                        await after.edit(nick=name[:32])
        else:
            if before.display_name != after.display_name:
                return await self.bot.db.execute(
                    """INSERT INTO names (user_id,type,username,ts) VALUES($1,$2,$3,$4) ON CONFLICT(user_id,username,ts) DO NOTHING""",
                    before.id,
                    "nickname",
                    before.display_name,
                    datetime.now(),
                )

    async def get_event_types(self, message: discord.Message):
        p = []
        _types = ["spoilers", "images", "emojis", "stickers"]
        for t in _types:
            if yes := self.bot.cache.autoreacts[message.guild.id].get(t):  # type: ignore  # noqa: F841
                p.append(t)
        return p

    async def do_autoresponse(self, trigger: str, message: discord.Message):
        if (
            await self.bot.glory_cache.ratelimited(
                f"ar:{message.guild.id}:{trigger}", 3, 5
            )
            != 0
        ):
            return
        response = self.bot.cache.autoresponders[message.guild.id][trigger]
        if response.lower().startswith(
            "{embed}"
        ):  # if any(var in response.lower() for var in variables):
            # Do something if any of the variables are found in the message content
            return await self.bot.send_embed(
                message.channel, response, user=message.author, guild=message.guild
            )
        else:
            return await message.channel.send(response)

    async def check_message(self, message: discord.Message):
        if data := self.bot.cache.autoresponders.get(message.guild.id):
            for trigger, response in data.items():  # type: ignore
                if trigger.endswith("*"):
                    if trigger.strip("*").lower() in message.content.lower():
                        await self.do_autoresponse(trigger, message)
                else:
                    trigger.rstrip().lstrip()
                    content = message.content  # )
                    if (
                        content.lower().startswith(f"{trigger.lower()} ")
                        or content.lower() == trigger.lower()
                    ):
                        return await self.do_autoresponse(trigger, message)
                    if (
                        f"{trigger.lower()} " in content.lower()
                        or f" {trigger.lower()}" in content.lower()
                    ):
                        return await self.do_autoresponse(trigger, message)
                    if (
                        trigger.lower() in content.lower().split()
                        or f"{trigger.lower()} " in content.lower()
                        or content.lower().startswith(f"{trigger.lower()} ")
                        or content.lower().endswith(f" {trigger.lower()}")
                    ):
                        await self.do_autoresponse(trigger, message)

    @commands.Cog.listener("on_message")
    async def autoresponder_event(self, message: discord.Message):
        if message.guild is None:
            return
        if message.author.bot:
            return
        if message.channel.permissions_for(message.guild.me).send_messages is False:
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        await self.check_message(message)

    @commands.Cog.listener("on_message")
    async def booster_event(self, message: discord.Message):
        if message.guild is None:
            return
        if message.channel.permissions_for(message.guild.me).send_messages is False:
            return
        if data := await self.bot.db.fetchrow(
            "SELECT * FROM guild.boost WHERE guild_id = $1", message.guild.id
        ):
            if message.type == discord.MessageType.premium_guild_subscription:
                channel = message.guild.get_channel(data.channel_id)
                # embed = await EmbedBuilder(message.author).build_embed(data.message)
                if channel and isinstance(channel, discord.TextChannel):
                    return await self.bot.send_embed(
                        channel, data.message, user=message.author
                    )

    async def do_afk(
        self, message: discord.Message, context: commands.Context, afk_data: Any
    ):
        author_afk_since: datetime = afk_data["date"]
        # afk_since = datetime.now() - author_afk_since
        # ago = str(humanize.naturaltime(afk_since)).strip(' ago').replace('now','1 second') # OLD TIME SINCE AFK
        welcome_message = f":wave: {message.author.mention}: Welcome back, you went away {discord.utils.format_dt(author_afk_since, style='R')}"
        embed = discord.Embed(description=welcome_message, color=0x2B2D31)
        await context.send(embed=embed)
        self.bot.afks.pop(message.author.id)

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
                        await message.author.timeout(
                            datetime.now().astimezone() + timedelta(seconds=converted)
                        )
                        await context.normal(
                            f"has been **timed out** for `{converted} seconds`. **Reason:** {reason}",
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
        if message.author.name == "aiohttp":
            logger.info(reactions)
            # else:
        # if isinstance(reactions, list):
        # reactions = [(b64decode(reaction.encode()).decode() if len(tuple(reaction)) > 1 else reaction) for reaction in reaction]
        if isinstance(reactions, list):
            pass
        else:
            reactions = [reactions]
            # reactions = [(b64decode(reaction.encode()).decode() if len(tuple(reaction)) > 1 else reaction) for reaction in reactions]
        for reaction in reactions:
            try:
                await message.add_reaction(reaction)
            except Exception:
                pass
        return

    @commands.Cog.listener("on_message")
    async def system_messages_event(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if message.author.bot or not message.guild:
            return
        if message.channel.permissions_for(message.guild.me).send_messages is False:
            return
        if message.channel.permissions_for(message.guild.me).moderate_members is False:
            return
        if message.channel.permissions_for(message.guild.me).manage_messages is False:
            return
        if message.is_system:
            if message.type == discord.MessageType.new_member:
                if await self.bot.db.fetchrow(
                    """SELECT * FROM system_messages WHERE guild_id = $1""",
                    message.guild.id,
                ):
                    if self.system_sticker is None:
                        self.system_sticker = await self.bot.fetch_sticker(
                            749054660769218631
                        )
                    await message.reply(stickers=[self.system_sticker])

    def debug(self, m: discord.Message, msg: str):
        if self.maintenance is True:
            if m.author.name == "aiohttp":
                logger.info(msg)
        return

    @commands.Cog.listener("on_message")
    async def time_response(self, message: discord.Message) -> None:
        if message.author.bot or message.author is self.bot.user.bot:
            return
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return
        async with timeit() as timer:
            await self.on_message_filter(message)
        self.response_time = timer.elapsed

    @commands.Cog.listener("on_message_edit")
    async def filter_response_edit(
        self, before: discord.Message, after: discord.Message
    ):  # type: ignore
        if before.author.bot or before.author is self.bot.user.bot:
            return
        ctx = await self.bot.get_context(after)
        if ctx.valid:
            return
        return await self.on_message_filter(after)

    async def on_message_filter(self, message: discord.Message) -> None:
        await self.bot.wait_until_ready()
        if message.author.bot or not message.guild:
            return
        if message.channel.permissions_for(message.guild.me).send_messages is False:
            return self.debug(message, "no send_messages perms")
        if message.guild.me.guild_permissions.moderate_members is False:
            return self.debug(message, "no moderate_members perms")
        if message.guild.me.guild_permissions.manage_messages is False:
            return self.debug(message, "no manage_members perms")
        block_command_execution = False
        context = await self.bot.get_context(message)
        filter_events = tuple(
            record.event
            for record in await self.bot.db.fetch(
                "SELECT event FROM filter_event WHERE guild_id = $1", context.guild.id
            )
        )
        if afk_data := self.bot.afks.get(message.author.id):
            if context.valid:
                if context.command.qualified_name.lower() == "afk":
                    pass
                else:
                    await self.do_afk(message, context, afk_data)
            else:
                await self.do_afk(message, context, afk_data)

        if message.mentions:
            for user in message.mentions:
                if user_afk := self.bot.afks.get(user.id):
                    if not await self.bot.glory_cache.ratelimited(
                        f"rl:afk_mention_message:{message.channel.id}", 2, 5
                    ):
                        embed = discord.Embed(
                            description=f"{message.author.mention}: {user.mention} is AFK: **{user_afk['status']} ** - {humanize.naturaltime(datetime.now() - user_afk['date'])}",
                            color=0x2B2D31,
                        )
                        await context.send(embed=embed)
        if timeframe := await self.bot.db.fetchval(
            """SELECT timeframe FROM automod_timeout WHERE guild_id = $1""",
            message.guild.id,
        ):
            try:
                converted = humanfriendly.parse_timespan(timeframe)
            except Exception:
                converted = 5
        else:
            converted = 5

        async def check():
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

        if (
            self.bot.cache.filter.get(context.guild.id)
            and block_command_execution is False
        ):
            if await check():

                async def do_filter():
                    for keyword in self.bot.cache.filter.get(context.guild.id, []):
                        if keyword.lower().endswith("*"):
                            await self.do_timeout(
                                message, "muted by the chat filter", context
                            )
                            break
                        else:
                            if keyword.lower() in message.content.lower().split(" "):
                                await self.do_timeout(
                                    message, "muted by the chat filter", context
                                )
                                break

                        await sleep(0.001)

                ensure_future(do_filter())

        if (
            "spoilers" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("spoilers", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            if message.content.count("||") >= (
                self.bot.cache.filter_event[context.guild.id]["spoilers"]["threshold"]
                * 2
            ):
                #    if await check():
                reason = "Muted by spoiler filter"
                await self.do_timeout(message, reason, context)
                block_command_execution = True
        if (
            "headers" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("headers", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            for m in message.content.split("\n"):
                if m.startswith("# "):
                    if (
                        len(m.split(" "))
                        >= self.bot.cache.filter_event[context.guild.id]["headers"][
                            "threshold"
                        ]
                    ):
                        await self.do_timeout(
                            message, "Muted by the header filter", context
                        )
                        block_command_execution = True
        if (
            "images" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("images", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            if len(message.attachments) > 0:
                threshold = self.bot.cache.filter_event[context.guild.id]["images"][
                    "threshold"
                ]
                for attachment in message.attachments:  # type: ignore
                    if await self.bot.glory_cache.ratelimited(
                        f"ai-{message.guild.id}-{message.author.id}", threshold, 10
                    ):
                        await self.do_timeout(
                            message, "Muted by my image filter", context
                        )
                        block_command_execution = True
        if (
            "links" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("links", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            # if await check():
            if "http" in message.content or "www" in message.content:
                reason = "muted by the link filter"
                await self.do_timeout(message, reason, context)
                block_command_execution = True

        if (
            "spam" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("spam", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            # if await check():
            if await self.bot.glory_cache.ratelimited(
                f"amtis-{message.guild.id}", 20, 10
            ):
                if await check():
                    #
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
                        if message.guild.me.guild_permissions.moderate_members is True:
                            await message.author.timeout(
                                datetime.now().astimezone()
                                + timedelta(seconds=converted)
                            )
                else:
                    reason = "flooding chat"
                    await self.do_timeout(message, reason, context)
                    block_command_execution = True

                if message.guild.me.guild_permissions.manage_messages is True:
                    await message.channel.purge(
                        limit=10, check=lambda m: m.author.id == message.author.id
                    )
                    block_command_execution = True

        if (
            "emojis" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("emojis", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            if len(find_emojis(message.content)) >= (
                self.bot.cache.filter_event[context.guild.id]["emojis"]["threshold"]
            ):
                # if await check():
                reason = "muted by the emoji filter"
                await self.do_timeout(message, reason, context)

                block_command_execution = True

        if (
            "invites" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("invites", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            if len(message.invites) > 0:
                reason = "muted by the invite filter"
                await self.do_timeout(message, reason, context)

                block_command_execution = True

        if (
            "caps" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("caps", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            if len(tuple(c for c in message.content if c.isupper())) >= (
                self.bot.cache.filter_event[context.guild.id]["caps"]["threshold"]
            ):
                reason = "muted by the cap filter"
                await self.do_timeout(message, reason, context)

                block_command_execution = True

        if (
            "massmention" in filter_events
            and self.bot.cache.filter_event.get(context.guild.id, DICT)
            .get("massmention", DICT)
            .get("is_enabled", False)
            is True
            and block_command_execution is False
        ):
            if len(message.mentions) >= (
                self.bot.cache.filter_event[context.guild.id]["massmention"][
                    "threshold"
                ]
            ):
                reason = "muted by the mention filter"
                await self.do_timeout(message, reason, context)

                block_command_execution = True

        if block_command_execution is True:
            return

        if self.bot.cache.autoreacts.get(message.guild.id):

            async def do_autoreact():
                try:

                    def check_emoji(react: Any):  # type: ignore
                        if not isinstance(react, str):
                            return True
                        if match := EMOJI_REGEX.match(react):
                            emoji = match.groupdict()
                            if re := message.guild.get_emoji(int(emoji["id"])):  # type: ignore  # noqa: F841
                                return True
                            else:
                                return False
                        return True

                    keywords_covered = []
                    for keyword, reaction in self.bot.cache.autoreacts[  # type: ignore
                        message.guild.id
                    ].items():
                        if keyword not in ["spoilers", "images", "emojis", "stickers"]:
                            if keyword in message.content:
                                reactions = self.bot.cache.autoreacts[message.guild.id][
                                    keyword
                                ]
                                reactions = [reaction for reaction in reactions]
                                reactions = [r for r in reactions]

                                async def do_reaction(
                                    message: discord.Message, reaction: str
                                ):
                                    try:
                                        name = unicodedata.name(reaction)
                                        if "variation" in name.lower():
                                            #                                           logger.info(f"not adding {reaction} due to the name being {name}")
                                            return
                                    #                                        logger.info(f"emoji name: {name}")
                                    except Exception:
                                        pass
                                    try:
                                        #                  if message.author.name == "aiohttp": logger.info(reaction)
                                        await message.add_reaction(reaction)
                                    except Exception as e:
                                        self.bot.eee = reaction
                                        #                                      logger.info(f"An Autoreaction error occurred : {e} : for emoji {reaction} with type {type(reaction)}")
                                        return await message.channel.send(
                                            embed=discord.Embed(
                                                color=self.bot.color,
                                                description=f"i cannot react to messages due to an error, please report this: {e}",
                                            )
                                        )
                                        pass  # type: ignore

                                gather(
                                    *(
                                        do_reaction(message, reaction)
                                        for reaction in reactions
                                    )
                                )

                                keywords_covered.append(keyword)
                                continue
                except Exception:
                    pass

            with suppress(discord.errors.HTTPException):
                await do_autoreact()

            if await self.get_event_types(message):

                async def do_autoreact_event(_type: str):
                    #   if await self.bot.glory_cache.ratelimited(
                    #      f"rl:autoreact{message.guild.id}", 5, 30
                    #    ):
                    #    return
                    if reactions := self.bot.cache.autoreacts[message.guild.id].get(
                        _type
                    ):
                        await self.add_reaction(message, reactions)

                #                        await gather(
                #                           *(
                # #                             message.add_reaction(
                #                              get_emoji(reaction)
                # #                                if len(tuple(reaction)) < 1
                #                             else reaction
                #                        )
                #                       for reaction in reactions
                #                  )
                #                       )
                #
                events = await self.get_event_types(message)
                #                if message.author.name == "aiohttp": logger.info(f"{events}")
                if "images" in events and any(
                    tuple(
                        attachment.content_type.startswith(("image/", "video/"))
                        for attachment in message.attachments
                    )
                ):
                    #                   if message.author.name == "aiohttp": logger.info(f"doing autoreact for images")
                    await do_autoreact_event("images")
                #              else:
                #                 if message.author.name == "aiohttp": logger.info(f"not an image")

                if "spoilers" in events and (message.content.count("||") > 2):
                    ensure_future(do_autoreact_event("spoilers"))

                if "emojis" in events and find_emojis(message.content):
                    ensure_future(do_autoreact_event("emojis"))

                if "stickers" in events and message.stickers:
                    ensure_future(do_autoreact_event("stickers"))

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
        if before.premium_since is None and after.premium_since is not None:
            if data := await self.bot.db.fetch(
                """SELECT role_id FROM premiumrole WHERE guild_id = $1""",
                after.guild.id,
            ):
                for role_id in data:
                    if role := after.guild.get_role(role_id):
                        if role not in after.roles:
                            await after.add_roles(role, reason="Booster Role")
        elif before.premium_since is not None and after.premium_since is None:
            if data := await self.bot.db.fetch(
                """SELECT role_id FROM premiumrole WHERE guild_id = $1""",
                after.guild.id,
            ):
                for role_id in data:
                    if role := after.guild.get_role(role_id):
                        if role in after.roles:
                            await after.remove_roles(role, reason="Booster Role")

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
                    and self.bot.cache.filter_event[after.guild.id]["links"][
                        "is_enabled"
                    ]
                    is True
                ):
                    if after.nick in self.bot.cache.filter[after.guild.id]:
                        await after.edit(
                            nick=None,
                            reason=f"{self.bot.user.name.title()} Moderation: Nickname contains a filtered word",
                        )

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.id == self.bot.user.id or message.author.id == 123:
            return
        return await self.bot.snipes.add_entry("snipe", message)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.content != after.content and before.author.id != self.bot.user.id:
            return await self.bot.snipes.add_entry("editsnipe", before)

    @commands.Cog.listener()
    async def on_reaction_remove(
        self, reaction: discord.Reaction, user: Union[discord.Member, discord.User]
    ):
        return await self.bot.snipes.add_entry("rs", (reaction, user))

    @commands.Cog.listener("on_member_join")
    async def autorole_give(self, member: discord.Member):
        if data := self.bot.cache.autorole.get(member.guild.id):
            roles = [
                member.guild.get_role(i)
                for i in data
                if member.guild.get_role(i) is not None
            ]
            if await self.bot.glory_cache.ratelimited("ar", 4, 6) is not True:
                await asyncio.sleep(4)
            await member.add_roles(*roles, atomic=False)

    @tasks.loop(minutes=1)
    async def voicemaster_clear(self):
        async for row in self.bot.db.fetchiter(
            """SELECT guild_id, channel_id FROM voicemaster_data"""
        ):
            if guild := self.bot.get_guild(row.guild_id):
                if channel := guild.get_channel(row.channel_id):
                    members = [c for c in channel.members if c != self.bot.user]
                    if len(members) == 0:
                        await channel.delete(reason="voicemaster cleanup")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        return await self.voicemaster_event(member, before, after)

    @ratelimit("voicemaster:{member.id}", 2, 5, False)
    async def create_and_move(
        self,
        member: discord.Member,
        after: discord.Voicestate,
        status: Optional[str] = None,
    ):
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
        await member.move_to(channel)
        return channel

    async def voicemaster_event(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if not (
            not self.bot.is_ready()
            or (
                before.channel
                and after.channel
                and before.channel.id == after.channel.id
            )
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
                        f"rl: voicemaster_channel_create: {member.guild.id}", 5, 30
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
                            await before.channel.delete()

                    else:
                        if stat := await self.bot.db.fetchrow(
                            """SELECT status FROM vm_status WHERE user_id = $1""",
                            member.id,
                        ):
                            status = stat["status"]
                        else:
                            status = None
                        {
                            member: discord.PermissionOverwrite(
                                connect=True, view_channel=True
                            )
                        }  # type: ignore
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
                                await before.channel.delete()


async def setup(bot):
    await bot.add_cog(Events(bot))
