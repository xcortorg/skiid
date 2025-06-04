import asyncio
import os
from typing import Literal

import discord
from discord.ext import commands
from tools.bot import Akari
from tools.helpers import AkariContext


class Autopfp(commands.Cog):
    def __init__(self, bot: Akari):
        self.bot = bot

    @commands.hybrid_group(invoke_without_command=True)
    async def autopfp(self, ctx: AkariContext):
        """
        Automatically send pfps to a channel in this server
        """

        return await ctx.create_pages()

    @autopfp.command(name="add", brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_webhooks=True)
    async def autopfp_add(
        self,
        ctx: AkariContext,
        channel: discord.TextChannel,
        category: Literal["random", "roadmen", "girl", "egirl", "anime"] = "random",
    ):
        """
        Add an autopfp channel
        """

        await self.bot.db.execute(
            """
            INSERT INTO autopfp VALUES ($1,$2,$3,$4)
            ON CONFLICT (guild_id, type, category) DO UPDATE
            SET channel_id = $4
            """,
            ctx.guild.id,
            "pfps",
            category,
            channel.id,
        )

        if not self.bot.pfps_send:
            self.bot.pfps_send = True
            asyncio.ensure_future(self.bot.autoposting("pfps"))

        return await ctx.success(f"Sending **{category}** pfps to {channel.mention}")

    @autopfp.command(name="remove", brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    async def autopfp_remove(
        self,
        ctx: AkariContext,
        category: Literal["random", "roadmen", "girl", "egirl", "anime"] = "random",
    ):
        """
        Remove an autopfp channel
        """

        await self.bot.db.execute(
            """
            DELETE FROM autopfp WHERE guild_id = $1 
            AND type = $2 AND category = $3
            """,
            ctx.guild.id,
            "pfps",
            category,
        )

        return await ctx.success(f"Stopped sending **{category}** pfps")

    @commands.hybrid_group()
    async def autobanner(self, ctx: AkariContext):
        """
        Automatically send banners to a channel
        """

        return await ctx.create_pages()

    @autobanner.command(name="add", brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    @commands.bot_has_guild_permissions(manage_webhooks=True)
    async def autobanner_add(
        self,
        ctx: AkariContext,
        channel: discord.TextChannel,
        category: Literal["random", "cute", "mix", "imsg"] = "random",
    ):
        """
        Add an autobanner channel
        """

        await self.bot.db.execute(
            """
            INSERT INTO autopfp VALUES ($1,$2,$3,$4)
            ON CONFLICT (guild_id, type, category) DO UPDATE
            SET channel_id = $4
            """,
            ctx.guild.id,
            "banners",
            category,
            channel.id,
        )

        if not self.bot.banners_send:
            self.bot.banners_send = True
            asyncio.ensure_future(self.bot.autoposting("banners"))

        return await ctx.success(f"Sending **{category}** banners to {channel.mention}")

    @autobanner.command(name="remove", brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    async def autobanner_remove(
        self,
        ctx: AkariContext,
        category: Literal["random", "cute", "mix", "imsg"] = "random",
    ):
        """
        Remove an autobanner channel
        """

        await self.bot.db.execute(
            """
            DELETE FROM autopfp WHERE guild_id = $1 
            AND type = $2 AND category = $3
            """,
            ctx.guild.id,
            "banners",
            category,
        )

        return await ctx.success(f"Stopped sending **{category}** banners")


async def setup(bot):
    await bot.add_cog(Autopfp(bot))
