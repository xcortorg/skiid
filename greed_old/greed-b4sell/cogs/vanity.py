from discord.ext import commands, tasks
import discord
from typing import Optional, Union, List
from discord.ext.commands import Context
from tool.important.subclasses.command import TextChannel
from cogs.servers import EmbedConverter
from tool.greed import Greed
from loguru import logger
from tools import ratelimit
from contextlib import suppress
import asyncio
from collections import defaultdict


class Vanity(commands.Cog):
    def __init__(self, bot: Greed):
        self.bot = bot
        self.local_addr = "23.160.168.122"
        self.locks = defaultdict(asyncio.Lock)
        self.loop = asyncio.get_running_loop()
        self.notification_lock = asyncio.Lock()

    @commands.group(
        name="vanity",
        example=",vanity",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_roles=True)
    async def vanity(self, ctx: Context):
        await ctx.send_help(ctx.command.qualified_name)

    @vanity.command(
        name="set",
        brief="set the channel for checking vanities",
        example=",vanity set #vanity-updates",
    )
    async def vanity_set(self, ctx, channel: TextChannel):
        await self.bot.db.execute(
            """INSERT INTO vanity (guild_id, channel_id) VALUES($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = excluded.channel_id""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(f"**Vanity channel** set to {channel.mention}")

    @vanity.command(
        name="unset",
        brief="unset the channel for checking vanities",
        example=",vanity unset",
    )
    async def vanity_unset(self, ctx):
        result = await self.bot.db.execute(
            """DELETE FROM vanity WHERE guild_id = $1""",
            ctx.guild.id,
        )

        if result == "DELETE 0":
            return await ctx.error(
                "There is no **Vanity channel** set for this server."
            )

        return await ctx.success("**Vanity channel** has been unset.")

    @commands.Cog.listener("vanity_change")
    async def notify_vanity_channels(self, vanity: str):
        self.loop.create_task(self.notifyy(vanity))

    async def notifyy(vanity: str):
        if not (
            rows := await self.bot.db.fetch(
                """SELECT channel_id, message FROM vanity WHERE guild_id = ANY($1::BIGINT[])""",
                [g.id for g in self.bot.guilds],
            )
        ):
            return
        for row in rows:
            if not (channel := self.bot.get_channel(row.channel_id)):
                continue
            permissions = channel.permissions_for(channel.guild.me)
            if not permissions.send_messages or not permissions.embed_links:
                continue
            message = (row.message or f"Vanity **{vanity}** has been dropped").replace(
                "{vanity}", vanity
            )
            embed = discord.Embed(
                title="New Vanity", description=message, color=self.bot.color
            )
            try:
                await channel.send(embed=embed)
            except Exception:
                continue

    @commands.Cog.listener("on_guild_update")
    async def guild_update(self, before, after):
        self.loop.create_task(self.vanity_check(before, after))

    async def vanity_check(self, before: discord.Guild, after: discord.Guild):
        """
        Handles vanity URL updates in a guild and notifies servers with vanity monitoring enabled.
        """
        if before.vanity_url_code == after.vanity_url_code:
            return

        guilds = await self.bot.db.fetch(
            """SELECT guild_id, channel_id, message FROM vanity"""
        )

        channel_ids = [
            guild["channel_id"] for guild in guilds if guild.get("channel_id")
        ]
        if not channel_ids:
            return

        await self.notify(
            guilds,
            channel_ids,
            before.vanity_url_code,
        )

    async def notify(self, guilds: list, channel_ids: list, vanity: str):
        """
        Sends a notification about a dropped vanity URL to specified guild channels.
        """
        if not vanity or vanity.lower() == "none":
            return

        msg = None
        message = (msg or f"Vanity **{vanity}** has been dropped").replace(
            "{vanity}", vanity
        )
        embed = discord.Embed(
            title="New Vanity",
            description=message,
            color=self.bot.color,
        )

        for channel_id in channel_ids:
            try:
                await self.bot.send_raw(channel_id, embed=embed)
                await asyncio.sleep(0.1)
            except Exception:
                pass

        try:
            data = {"method": "vanity_change", "vanity": vanity}
            return await self.bot.connection.inform(
                data, destinations=self.bot.ipc.sources
            )
        except Exception as e:
            logger.error(f"Failed to send vanity notification: {e}")


async def setup(bot):
    await bot.add_cog(Vanity(bot))
