from __future__ import annotations

import datetime
from typing import Any, Dict, Optional

import discord

from grief.core import Config as RedDB
from grief.core import commands
from grief.core.bot import Grief
from grief.core.commands import Cog as RedCog
from grief.core.utils.chat_formatting import humanize_timedelta

DEFAULT_USER: Dict[str, Any] = {
    "afk": False,
    "reason": None,
    "timestamp": None,
}


class AwayFromKeyboard(RedCog):
    """Let your friends know when you are afk, grief will add an autoresponder."""

    def __init__(self, bot: Grief):
        self.bot: Grief = bot
        self.db: RedDB = RedDB.get_conf(
            self, identifier=126875360, force_registration=True
        )
        self.db.register_user(**DEFAULT_USER)

    @commands.command(aliases=["away"])
    @commands.guild_only()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def afk(self, ctx: commands.Context, *, reason: Optional[str] = None) -> None:
        """Set your status to AFK."""
        async with self.db.user(ctx.author).all() as data:
            data["afk"] = True
            data["reason"] = reason if reason else "No reason provided."
            data["timestamp"] = int(
                datetime.datetime.now(datetime.timezone.utc).timestamp()
            )
        embed = discord.Embed()
        embed.color = 0x2F3136
        embed.description = "> You are now AFK."
        await ctx.reply(mention_author=False, embed=embed)

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        adata = await self.db.user(message.author).all()
        if adata["afk"]:
            async with self.db.user(message.author).all() as new_data:
                new_data["afk"] = False
                new_data["reason"] = None
                new_data["timestamp"] = None
            embed = discord.Embed(color=0x2F3136)
            description = "{}: welcome back, you were away for **{}**".format(
                message.author.mention,
                humanize_timedelta(
                    timedelta=(
                        datetime.datetime.now(datetime.timezone.utc)
                        - datetime.datetime.utcfromtimestamp(
                            adata["timestamp"]
                        ).replace(tzinfo=datetime.timezone.utc)
                    )
                ),
            )
            embed.description = description
            await message.channel.send(
                embed=embed,
                reference=message.to_reference(fail_if_not_exists=False),
                delete_after=15,
                mention_author=False,
            )
        if not message.mentions:
            return
        for mention in message.mentions:
            data = await self.db.user(mention).all()
            if not data["afk"]:
                continue
            embed = discord.Embed(color=0x2F3136)
            embed.description = "{} is AFK: **{}** - <t:{}:R>".format(
                mention.mention,
                data["reason"] or "No reason provided.",
                data["timestamp"],
            )
            await message.channel.send(
                embed=embed,
                reference=message.to_reference(fail_if_not_exists=False),
                delete_after=15,
                mention_author=False,
            )


async def setup(bot: Grief):
    cog = AwayFromKeyboard(bot)
    await discord.utils.maybe_coroutine(bot.add_cog, cog)
