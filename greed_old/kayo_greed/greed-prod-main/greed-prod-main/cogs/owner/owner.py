import gc
from copy import copy
from importlib import import_module, reload
from io import StringIO
from itertools import chain
from logging import getLogger
from pathlib import Path
from traceback import format_exception
from typing import Annotated, Dict, List, Optional
from asyncio import gather

import stackprinter
from cashews import cache
from discord import (
    File,
    HTTPException,
    Member,
    Message,
    TextChannel,
    User,
    Embed
)
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
import json
import re

log = getLogger("greed/owner")

class ShardInfo(BaseModel):
    shard_id: int
    is_ready: bool
    server_count: int
    member_count: int
    uptime: str
    latency: float
    last_updated: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

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

        # self.check_cb = PeriodicCallback(self.check_whitelist)

    async def cog_check(self, ctx: Context) -> bool:
        return ctx.author.id in self.bot.owner_ids

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

    def cog_unload(self):
        self.update_shards_info.cancel()

    def parse_uptime(self, uptime_str):
        uptime_parts = uptime_str.split(', ')
        total_seconds = 0
        for part in uptime_parts:
            if 'days' in part:
                total_seconds += int(part.split()[0]) * 86400
            elif 'hours' in part:
                total_seconds += int(part.split()[0]) * 3600
            elif 'minutes' in part:
                total_seconds += int(part.split()[0]) * 60
            elif 'seconds' in part:
                total_seconds += int(part.split()[0])
        return total_seconds

    def format_uptime(self, total_seconds):
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"

    @tasks.loop(seconds=60)
    async def update_shards_info(self):
        if not config.CLIENT.UPDATE_SHARD_STATS:
            log.info("Shard updating is disabled via configuration.")
            return

        async def get_shard_info(shard_id, shard):
            last_updated = datetime.now(timezone.utc).isoformat()
            uptime_seconds = self.parse_uptime(self.bot.uptime)
            shard_info = {
                "shard_id": shard_id,
                "is_ready": not shard.is_closed(),
                "server_count": sum(1 for guild in self.bot.guilds if guild.shard_id == shard_id),
                "member_count": sum(guild.member_count for guild in self.bot.guilds if guild.shard_id == shard_id),
                "uptime": self.format_uptime(uptime_seconds),
                "latency": shard.latency,
                "last_updated": last_updated,
            }
            return shard_info

        shard_tasks = [get_shard_info(shard_id, shard) for shard_id, shard in self.bot.shards.items()]
        shards_info = await gather(*shard_tasks)

        data = {"shards": shards_info}

        headers = {
            "X-API-KEY": config.API.greed,
            "Content-Type": "application/json"
        }

        async with self.bot.session.post(
            "https://api.greed.best/shards/post",
            json=data, 
            headers=headers,
        ) as response:
            if response.status == 200:
                log.info("Shards info posted successfully!")
            else:
                log.exception(f"Error posting shards info: {response.status}")

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

        guild_prefix = self.bot.command_prefix(self.bot, ctx.message) if callable(self.bot.command_prefix) else self.bot.command_prefix
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
                return await ctx.warn(f"Failed to leave the guild.\n no longer allowing **{guild}** to use **{self.bot.user}**")

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

    @group(aliases=['donator', 'prem', 'donor'], invoke_without_command=True)
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
                """, member.id, datetime.now(timezone.utc))
        await ctx.approve(f"{member.mention} has been added to the premium list.")

    @premium.command()
    async def remove(self, ctx: Context, member: Member) -> Message:
        """Remove a member from the premium list"""
        result = await self.bot.db.execute("DELETE FROM donators WHERE user_id = $1", member.id)
        if result == "DELETE 1":
            await ctx.approve(f"{member.mention} has been removed from the premium list.")
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
            entries=[member.id for member in record['user_id']],
            embed=embed,
            per_page=10
        )
        await paginator.start()