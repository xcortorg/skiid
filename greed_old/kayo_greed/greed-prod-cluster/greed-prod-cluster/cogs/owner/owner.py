import asyncio, gc
from copy import copy
from importlib import import_module, reload
from io import StringIO
from itertools import chain
from logging import getLogger
from pathlib import Path
from traceback import format_exception
from typing import Annotated, Dict, List, Optional
from asyncio import gather, sleep
from aiohttp import ClientSession, TCPConnector, ClientError
from dataclasses import asdict
import json

import stackprinter
from cashews import cache
from discord import File, HTTPException, Member, Message, TextChannel, User, Embed
from discord.ext.commands import Cog, command, group, parameter
from discord.ext import tasks
from jishaku.modules import ExtensionConverter

from pydantic import BaseModel
from main import greed
from tools.client import Context
from tools.paginator import Paginator
from tools.conversion import PartialAttachment, StrictMember
from tools.formatter import codeblock
import config
from datetime import datetime, timezone

log = getLogger("greed/owner")

BUNNY_STORAGE_ZONE_NAME = "greed-zone-01"
BUNNY_API_KEY = "a04b6fbf-12ff-4723-8fed51e1a279-669b-42e2"
BUNNY_BASE_URL = f"https://ny.storage.bunnycdn.com/{BUNNY_STORAGE_ZONE_NAME}/avh"


class ShardInfo(BaseModel):
    shard_id: int
    is_ready: bool
    server_count: int
    member_count: int
    uptime: str
    latency: float
    last_updated: str
    cluster: int

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

class ShardsInfo(BaseModel):
    shards: List[ShardInfo]


# class PaymentFlags(FlagConverter):
#     method: str = flag(
#         default="CashApp",
#         aliases=["platform"],
#         description="The payment method used.",
#     )
#     amount: int = flag(
#         default=8,
#         aliases=["price"],
#         description="The amount paid.",
#     )


# class PaymentRecord(TypedDict):
#     guild_id: int
#     customer_id: int
#     method: str
#     amount: int
#     transfers: int
#     paid_at: datetime


class Owner(
    Cog,
    command_attrs=dict(hidden=True),
):
    def __init__(self, bot: greed):
        self.bot = bot
        self.update_shards_info.start()
        self.avatar_stats: dict[int, dict[str, int]] = {}
        self.avatar_stats = {}
        self.debounce_time = 2
        self.cleanup_interval = 3600
        # self.loop = bot.loop.create_task(self.clear_old_stats())
        # self.check_cb = PeriodicCallback(self.check_whitelist)

    # async def upload_avatar_size(
    #     self, url: str, avatar_hash: str, file_extension: str
    # ) -> Optional[int]:
    #     """Fetch avatar and upload it to BunnyCDN. Returns the avatar size if successful."""
    #     avatar_bytes = await self._retry_fetch(url)
    #     if avatar_bytes:
    #         await self.upload_to_bunny(avatar_bytes, avatar_hash, file_extension)
    #         return len(avatar_bytes)
    #     return None

    # async def _retry_fetch(self, url: str) -> Optional[bytes]:
    #     """Attempt to fetch the avatar from a URL with retry logic."""
    #     for attempt in range(self.retry_attempts):
    #         try:
    #             async with self.bot.session.get(url) as response:
    #                 if response.status == 200:
    #                     return await response.read()
    #                 else:
    #                     log.warning(
    #                         f"Attempt {attempt + 1}: Failed to fetch avatar from {url}, Status: {response.status}"
    #                     )
    #         except ClientError as e:
    #             log.error(
    #                 f"Attempt {attempt + 1}: Error fetching avatar from {url}: {e}"
    #             )
    #         await asyncio.sleep(2**attempt)
    #     log.error(
    #         f"All {self.retry_attempts} attempts failed to fetch avatar from {url}"
    #     )
    #     return None

    # async def upload_to_bunny(
    #     self, file_data: bytes, avatar_hash: str, file_extension: str
    # ) -> None:
    #     """Upload avatar data to BunnyCDN."""
    #     upload_url = f"{BUNNY_BASE_URL}/{avatar_hash}.{file_extension}"
    #     headers = {
    #         "AccessKey": BUNNY_API_KEY,
    #         "Content-Type": "application/octet-stream",
    #     }
    #     try:
    #         async with self.bot.session.put(
    #             upload_url, data=file_data, headers=headers
    #         ) as upload_response:
    #             if upload_response.status == 201:
    #                 log.info(
    #                     f"Successfully uploaded avatar to BunnyCDN: {avatar_hash}.{file_extension}"
    #                 )
    #             else:
    #                 log.error(
    #                     f"Failed to upload avatar to BunnyCDN, Status: {upload_response.status}"
    #                 )
    #     except ClientError as e:
    #         log.error(f"Error uploading avatar to BunnyCDN: {e}")

    # async def store_avatar_hash(self, user_id: int, avatar_hash: str) -> None:
    #     """Store avatar hash for the user in the database."""
    #     file_extension = "gif" if avatar_hash.startswith("a_") else "png"
    #     full_avatar_hash = f"{avatar_hash}.{file_extension}"

    #     try:
    #         row = await self.bot.db.fetchrow(
    #             "SELECT avatar_hashes, opt_out FROM avatar_hashes WHERE user_id = $1",
    #             user_id,
    #         )
    #         if row and row["opt_out"]:
    #             log.info(f"User {user_id} has opted out of avatar tracking.")
    #             return

    #         existing_hashes: List[str] = row["avatar_hashes"] if row else []
    #         if full_avatar_hash not in existing_hashes:
    #             log.debug(
    #                 f"Adding new avatar hash {full_avatar_hash} for user {user_id}."
    #             )
    #             existing_hashes.append(full_avatar_hash)
    #             if row:
    #                 await self.bot.db.execute(
    #                     "UPDATE avatar_hashes SET avatar_hashes = $1 WHERE user_id = $2",
    #                     existing_hashes,
    #                     user_id,
    #                 )
    #             else:
    #                 await self.bot.db.execute(
    #                     "INSERT INTO avatar_hashes (user_id, avatar_hashes) VALUES ($1, $2)",
    #                     user_id,
    #                     [full_avatar_hash],
    #                 )
    #         else:
    #             log.debug(
    #                 f"Avatar hash {full_avatar_hash} already exists for user {user_id}."
    #             )
    #     except Exception as e:
    #         log.error(f"Failed to store avatar hash for user {user_id}: {e}")

    # @Cog.listener()
    # async def on_user_update(self, before: User, after: User) -> None:
    #     """Event listener for user avatar updates."""
    #     if (
    #         before.avatar == after.avatar
    #         or before.avatar is None
    #         or after.default_avatar == after.avatar
    #     ):
    #         return

    #     user_id = after.id
    #     await asyncio.sleep(self.debounce_time)

    #     if await self.user_opted_out(user_id):
    #         return

    #     if user_id not in self.avatar_stats:
    #         self.avatar_stats[user_id] = {"changes": 0, "total_size": 0}

    #     self.avatar_stats[user_id]["changes"] += 1
    #     old_avatar_url = before.avatar.url
    #     old_avatar_hash = old_avatar_url.split("/")[-1].split(".")[0]
    #     file_extension = old_avatar_url.split(".")[-1]

    #     avatar_size = await self.upload_avatar_size(
    #         old_avatar_url, old_avatar_hash, file_extension
    #     )
    #     if avatar_size:
    #         self.avatar_stats[user_id]["total_size"] += avatar_size
    #         await self.store_avatar_hash(user_id, old_avatar_hash)

    # async def user_opted_out(self, user_id: int) -> bool:
    #     """Check if a user has opted out of avatar tracking."""
    #     opt_out = await self.bot.db.fetchval(
    #         "SELECT opt_out FROM avatar_hashes WHERE user_id = $1", user_id
    #     )
    #     if opt_out:
    #         log.info(f"User {user_id} has opted out of avatar tracking.")
    #     return bool(opt_out)

    # async def clear_old_stats(self) -> None:
    #     """Periodically clear avatar stats to prevent memory bloat."""
    #     while True:
    #         await asyncio.sleep(self.cleanup_interval)
    #         self.avatar_stats.clear()
    #         log.info("Cleared avatar stats to free up memory.")

    async def cog_unload(self) -> None:
        self.update_shards_info.cancel()

    # async def cog_load(self) -> None:
    #     self.check_cb.start(34, delay=2)

    # async def cog_unload(self) -> None:
    #     self.check_cb.stop()

    # async def check_whitelist(self) -> None:
    #     await self.bot.wait_until_ready()
    #     records = await self.bot.db.fetch(
    #         """
    #         SELECT guild_id
    #         FROM payment
    #         """
    #     )
    #     if len(records) < len(self.bot.guilds) * 0.5:
    #         return log.critical(
    #             f"We only have {len(records)} whitelisted servers out of {len(self.bot.guilds)}!"
    #         )

    #     for guild in self.bot.guilds:
    #         reason: Optional[str] = None
    #         if guild.id not in (record["guild_id"] for record in records):
    #             reason = "missing payment"

    #         elif not guild.me:
    #             log.warning(
    #                 f"Guild {Fore.LIGHTYELLOW_EX}{guild}{Fore.RESET} ({Fore.RED}{guild.id}{Fore.RESET}) was not chunked!"
    #             )
    #             continue

    #         if reason:
    #             await asyncio.sleep(uniform(0.5, 1.0))
    #             log.warning(
    #                 f"Leaving {Fore.LIGHTYELLOW_EX}{guild}{Fore.RESET} ({Fore.RED}{guild.id}{Fore.RESET}) {Fore.LIGHTWHITE_EX}{Style.DIM}{reason}{Fore.RESET}{Style.NORMAL}."
    #             )
    #             with suppress(HTTPException):

    #                 await guild.leave()

    async def cog_check(self, ctx: Context) -> bool:
        return ctx.author.id in self.bot.owner_ids

    def parse_uptime(self, uptime_str):
        uptime_parts = uptime_str.split(", ")
        total_seconds = 0
        for part in uptime_parts:
            if "days" in part:
                total_seconds += int(part.split()[0]) * 86400
            elif "hours" in part:
                total_seconds += int(part.split()[0]) * 3600
            elif "minutes" in part:
                total_seconds += int(part.split()[0]) * 60
            elif "seconds" in part:
                total_seconds += int(part.split()[0])
        return total_seconds

    def format_uptime(self, total_seconds):
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

    @tasks.loop(seconds=30)
    async def update_shards_info(self):
        if not config.CLIENT.UPDATE_SHARD_STATS:
            return log.info("Shard updating is disabled via configuration.")

        async def get_shard_info(shard_id, shard):
            last_updated = datetime.now(timezone.utc).isoformat()
            uptime_seconds = self.parse_uptime(self.bot.uptime)
            shard_info = ShardInfo(
                shard_id=shard_id,
                is_ready=not shard.is_closed(),
                server_count=sum(1 for guild in self.bot.guilds if guild.shard_id == shard_id),
                member_count=sum(guild.member_count for guild in self.bot.guilds if guild.shard_id == shard_id),
                uptime=self.format_uptime(uptime_seconds),
                latency=shard.latency,
                last_updated=last_updated,
                cluster=self.bot.cluster_id
            )
            return shard_info

        shard_tasks = [
            get_shard_info(shard_id, shard)
            for shard_id, shard in self.bot.shards.items()
        ]
        
        shards_info = await gather(*shard_tasks)
        shards_data = ShardsInfo(shards=shards_info)
        
        data = shards_data.dict()
        await self.bot.redis.set(f"cluster:{self.bot.cluster_id}:shards_info", data)

        all_clusters_info = []
        for cluster_id in range(1, 4):
            cluster_data = await self.bot.redis.get(f"cluster:{cluster_id}:shards_info")
            
            if cluster_data:
                if isinstance(cluster_data, str):
                    all_clusters_info.append(json.loads(cluster_data))
                else:
                    all_clusters_info.append(cluster_data)

        combined_data = {
            "shards": [shard for cluster in all_clusters_info for shard in cluster.get("shards", [])]
        }

        if self.bot.cluster_id == 1:
            headers = {"X-API-KEY": config.API.greed, "Content-Type": "application/json"}
            async with self.bot.session.post(
                "https://api.greed.best/shards/post",
                json=combined_data,
                headers=headers,
            ) as response:
                if response.status == 200:
                    log.info("Shards info posted successfully!")
                else:
                    log.exception(f"Error posting shards info: {response.status}")
        else:
            log.info(f"Cluster {self.bot.cluster_id} updated shard info in Redis, no API post.")

    @command()
    async def shutdown(self, ctx: Context) -> None:
        """
        Shutdown the bot.
        """

        await ctx.add_check()
        await self.bot.close()

    @command(aliases=["trace"])
    async def traceback(self, ctx: Context, error_code: Optional[str]) -> Message:
        if error_code is None:
            if not self.bot.traceback:
                return await ctx.warn("No traceback has been raised!")

            error_code = list(self.bot.traceback.keys())[-1]

        exc = self.bot.traceback.get(error_code)
        if not exc:
            return await ctx.warn("No traceback has been raised with that error code!")

        await ctx.add_check()
        fmt = stackprinter.format(exc)

        if len(fmt) > 1900:
            return await ctx.author.send(
                file=File(
                    StringIO(fmt),  # type: ignore
                    filename="error.py",
                ),
            )

        return await ctx.author.send(f"```py\n{fmt}\n```")

    @group(invoke_without_command=True)
    async def sudo(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        target: Optional[Member],
        *,
        command: str,
    ) -> None:
        """
        Run a command as another user.
        """

        guild_prefix = (
            self.bot.command_prefix(self.bot, ctx.message)
            if callable(self.bot.command_prefix)
            else self.bot.command_prefix
        )
        if isinstance(guild_prefix, list):
            guild_prefix = guild_prefix[0]

        message = copy(ctx.message)
        message.channel = channel or ctx.channel
        message.author = target or ctx.guild.owner or ctx.author
        message.content = f"{ctx.prefix or guild_prefix}{command}"

        new_ctx = await self.bot.get_context(message, cls=type(ctx))
        return await self.bot.invoke(new_ctx)

    @sudo.command(name="send", aliases=["dm"])
    async def sudo_send(
        self,
        ctx: Context,
        target: (
            Annotated[
                Member,
                StrictMember,
            ]
            | User
        ),
        *,
        content: str,
    ) -> Optional[Message]:
        """
        Send a message to a user.
        """

        try:
            await target.send(content, delete_after=15)
        except HTTPException as exc:
            return await ctx.warn("Failed to send the message!", codeblock(exc.text))

        return await ctx.add_check()

    @sudo.command(name="collect")
    async def sudo_collect(self, ctx: Context) -> None:
        """
        Flush the cache.
        """

        gc.collect()
        cached_keys = [key[0] async for key in cache.get_match("*")]
        for key in cached_keys:
            await cache.delete(key)

        return await ctx.add_check()

    @sudo.command(name="avatar", aliases=["pfp"])
    async def sudo_avatar(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Update the bot's avatar.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await self.bot.user.edit(avatar=attachment.buffer)
        return await ctx.reply("done")

    @sudo.command(name="reload")
    async def sudo_reload(self, ctx: Context, *, module: str) -> Optional[Message]:
        """
        Reload a dependency.
        """

        try:
            reload(import_module(module))
        except ModuleNotFoundError:
            return await ctx.warn("That module does not exist!")

        return await ctx.add_check()

    @sudo.command(name="emojis", aliases=["emotes"])
    async def sudo_emojis(self, ctx: Context) -> Message:
        """
        Load all necessary emojis.
        """

        path = Path("assets")
        result: Dict[str, List[str]] = {}
        for category in ("badges", "paginator", "audio"):
            result[category] = []
            for file in path.glob(f"{category}/*.jpg"):
                emoji = await ctx.guild.create_custom_emoji(
                    name=file.stem, image=file.read_bytes()
                )
                result[category].append(f'{file.stem.upper()}: str = "{emoji}"')

        return await ctx.reply(
            codeblock(
                "\n".join(
                    f"class {category.upper()}:\n"
                    + "\n".join(f"    {name}" for name in names)
                    for category, names in result.items()
                )
            )
        )

    @sudo.command(name="leave")
    async def sudo_leave(self, ctx: Context, guild_id: int) -> Message:
        """
        Leave a guild.
        """

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.warn("Guild not found!")

        await guild.leave()
        return await ctx.add_check()

    @group(aliases=["bl"], invoke_without_command=True)
    async def blacklist(
        self,
        ctx: Context,
        user: Member | User,
        *,
        information: Optional[str],
    ) -> Message:
        """
        Blacklist a user from using the bot.
        """

        blacklisted = await self.bot.db.execute(
            """
            DELETE FROM blacklist
            WHERE user_id = $1
            """,
            user.id,
        )
        if blacklisted == "DELETE 0":
            await self.bot.db.execute(
                """
                INSERT INTO blacklist (user_id, information)
                VALUES ($1, $2)
                """,
                user.id,
                information,
            )
            for guild in user.mutual_guilds:
                if guild.owner_id == user.id:
                    await guild.leave()

            return await ctx.approve(
                f"No longer allowing **{user}** to use **{self.bot.user}**"
            )

        return await ctx.approve(
            f"Allowing **{user}** to use **{self.bot.user}** again"
        )

    @blacklist.command(name="guild", aliases=["server", "g"])
    async def blacklist_guild(
        self,
        ctx: Context,
        guild_id: int,
        *,
        information: Optional[str] = "No reason provided.",
    ) -> Message:
        """
        Blacklist a guild from using the bot.
        """

        guild = self.bot.get_guild(guild_id)
        if not guild:
            return await ctx.warn("Guild not found!")

        blacklisted = await self.bot.db.execute(
            """
            DELETE FROM blacklist
            WHERE guild_id = $1
            """,
            guild.id,
        )
        if blacklisted == "DELETE 0":
            await self.bot.db.execute(
                """
                INSERT INTO guild_blacklist (guild_id, information)
                VALUES ($1, $2)
                """,
                guild.id,
                information,
            )
            try:
                await guild.leave(reason=information)
                return await ctx.approve(
                    f"No longer allowing **{guild}** to use **{self.bot.user}**"
                )
            except HTTPException:
                return await ctx.warn(
                    f"Failed to leave the guild.\n no longer allowing **{guild}** to use **{self.bot.user}**"
                )

        return await ctx.approve(
            f"Allowing **{guild}** to use **{self.bot.user}** again"
        )

    @command(aliases=["rl"])
    async def reload(
        self,
        ctx: Context,
        *extensions: Annotated[str, ExtensionConverter],
    ) -> Message:
        result: List[str] = []

        for extension in chain(*extensions):
            extension = "cogs." + extension.replace("cogs.", "")
            method, icon = (
                (
                    self.bot.reload_extension,
                    "\N{CLOCKWISE RIGHTWARDS AND LEFTWARDS OPEN CIRCLE ARROWS}",
                )
                if extension in self.bot.extensions
                else (self.bot.load_extension, "\N{INBOX TRAY}")
            )

            try:
                await method(extension)
            except Exception as exc:
                traceback_data = "".join(
                    format_exception(type(exc), exc, exc.__traceback__, 1)
                )

                result.append(
                    f"{icon}\N{WARNING SIGN} `{extension}`\n```py\n{traceback_data}\n```"
                )
            else:
                result.append(f"{icon} `{extension}`")

        return await ctx.reply("\n".join(result))

    @command(aliases=["debug"])
    async def logger(self, ctx: Context, module: str, level: str = "DEBUG") -> None:
        getLogger(f"greed/{module}").setLevel(level.upper())
        return await ctx.add_check()

    @group(aliases=["donator", "prem", "donor"], invoke_without_command=True)
    async def premium(self, ctx: Context) -> Message:
        """Premium command group"""
        await ctx.send_help(ctx.command)

    @premium.command()
    async def add(self, ctx: Context, member: Member) -> Message:
        """Add a member to the premium list"""
        await self.bot.db.execute(
            """
                INSERT INTO donators (user_id, created_at)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO NOTHING
                """,
            member.id,
            datetime.now(timezone.utc),
        )
        await ctx.approve(f"{member.mention} has been added to the premium list.")

    @premium.command()
    async def remove(self, ctx: Context, member: Member) -> Message:
        """Remove a member from the premium list"""
        result = await self.bot.db.execute(
            "DELETE FROM donators WHERE user_id = $1", member.id
        )
        if result == "DELETE 1":
            await ctx.approve(
                f"{member.mention} has been removed from the premium list."
            )
        else:
            await ctx.warn(f"{member.mention} was not found in the premium list.")

    @premium.command()
    async def list(self, ctx: Context) -> Message:
        """List all premium members"""
        records = await self.bot.db.fetch("SELECT user_id FROM donators")
        for record in records:
            if not records:
                return await ctx.warn("No premium members found.")

        embed = Embed(title="Premium Members")
        paginator = Paginator(
            entries=[member.id for member in record["user_id"]],
            embed=embed,
            per_page=10,
        )
        await paginator.start()
