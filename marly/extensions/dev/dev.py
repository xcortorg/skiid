from datetime import datetime
from traceback import format_exception
from typing import Optional

from discord import Embed, Guild, Member, Message, TextChannel, User, Forbidden
from discord.ext.commands import (
    Cog,
    Command,
    ExtensionAlreadyLoaded,
    ExtensionFailed,
    ExtensionNotFound,
    ExtensionNotLoaded,
    CommandOnCooldown,
    UserNotFound,
    is_owner,
    CommandError,
    CommandInvokeError,
    BucketType,
    MissingPermissions,
    command,
    group,
    param,
)
import aiohttp
from discord.errors import HTTPException
import os
from discord.utils import format_dt
from discord.ext.commands import command, Group
import secrets
import json
from discord import File

from system import Marly
from config import Emojis, Color, Marly
from system.base.context import Context


class CustomError(Exception):
    pass


class Developer(Cog):
    def __init__(self, bot: Marly):
        self.bot: Marly = bot

    async def cog_check(self: "Developer", ctx: Context) -> bool:
        return await self.bot.is_owner(ctx.author)

    @command(name="sync")
    async def sync(self, ctx: Context):
        """
        Sync application commands globally.
        """
        await ctx.bot.tree.sync()
        await ctx.send("Commands synced globally.")

    @command(name="leaveserver")
    async def leaveguild(self, ctx: Context, guild_id: int):
        g = self.bot.get_guild(guild_id)
        await g.leave()
        return await ctx.approve(f"Left {g.name}")

    @command()
    async def dm(self, ctx: Context, user: User, *, message: str):
        """DM the user of your choice"""
        try:
            await user.send(message)
            await ctx.thumbsup()
        except Forbidden:
            await ctx.warn("Cant send DMs to this user")

    @command(aliases=["topcmds"])
    async def topcommands(self, ctx: Context):
        """View the most used commands across all servers."""

        query = """
        SELECT command_name, SUM(uses) as total_uses 
        FROM command_usage 
        GROUP BY command_name 
        ORDER BY total_uses DESC 
        LIMIT 40
        """

        records = await self.bot.db.fetch(query)

        if not records:
            return await ctx.warn("No command usage data found!")

        embed = Embed(
            title="Most Used Commands",
        )

        description = []
        for idx, record in enumerate(records, 1):
            cmd_name = record["command_name"]
            uses = record["total_uses"]

            description.append(f"`{idx:02d}` **{cmd_name}** `{uses:,}` uses")

        await ctx.autopaginator(embed=embed, description=description, split=20)
