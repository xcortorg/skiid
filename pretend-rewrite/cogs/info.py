import datetime
import os
from datetime import datetime, timedelta
from platform import python_version

import discord
import humanize
import psutil
from discord import Embed, Permissions, User, __version__, utils
from discord.ext import commands
from discord.ext.commands import Cog, command, hybrid_command
from discord.ui import Button, View
from get.pretend import Pretend, PretendContext
from get.quote import Quotes
from get.time import human_timedelta, humanize
from psutil._common import bytes2human as natural_size


class Info(commands.Cog):
    def __init__(self, bot: Pretend):
        self.bot = bot
        self.quoting = Quotes(self.bot)

    @hybrid_command(description="see bot information", aliases=["bi"])
    async def botinfo(self, ctx):
        avatar_url = self.bot.user.avatar.url if self.bot.user.avatar else None

        embed = (
            discord.Embed(color=self.bot.color, description="")
            .add_field(
                name="Analystics",
                value=f">>> Ping: **{round(self.bot.latency * 1000)}ms**\nCommands: **{len(self.bot.commands)}**\nShard(s): **{self.bot.shard_count}**",
                inline=True,
            )
            .add_field(
                name="Information",
                value=f">>> Servers: **{len(self.bot.guilds)}**\nUsers: **{sum(g.member_count for g in self.bot.guilds):,}**\nDiscord: **{discord.__version__}**",
                inline=True,
            )
        )

        await ctx.reply(embed=embed)

    @command(help="info", description="get bot invite", aliases=["inv", "link"])
    async def invite(self, ctx):
        """
        Send an invite link of the bot
        """
        embed = discord.Embed(
            color=self.bot.color,
            description="[press here](https://discordapp.com/oauth2/authorize?client_id=1263734958586073141&scope=bot+applications.commands&permissions=8)",
        )
        await ctx.reply(embed=embed)

    @command()
    async def ping(self, ctx):
        e = discord.Embed(
            color=self.bot.color,
            description=f"📡 **{round(self.bot.latency * 1000)}ms**",
        )
        await ctx.reply(embed=e, mention_author=False)

    @command(name="quote")
    async def quote(self, ctx: PretendContext, message: discord.Message = None):
        return await self.quoting.get_caption(ctx, message)


async def setup(bot: Pretend) -> None:
    return await bot.add_cog(Info(bot))
