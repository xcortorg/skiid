import sqlite3

import discord
from discord.ext import commands
from get.checks import Perms as utils


class Vanity(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_file = "db/vanity.db"
        self.create_tables()

    def create_tables(self):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            """CREATE TABLE IF NOT EXISTS vanity_channels (
                            guild_id INTEGER,
                            channel_id INTEGER,
                            PRIMARY KEY (guild_id, channel_id)
                          )"""
        )
        conn.commit()
        conn.close()

    def save_vanity_channel(self, guild_id, channel_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT OR IGNORE INTO vanity_channels (guild_id, channel_id) VALUES (?, ?)""",
            (guild_id, channel_id),
        )
        conn.commit()
        conn.close()

    def remove_vanity_channel(self, guild_id, channel_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            """DELETE FROM vanity_channels WHERE guild_id = ? AND channel_id = ?""",
            (guild_id, channel_id),
        )
        conn.commit()
        conn.close()

    def get_vanity_channels(self, guild_id):
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute(
            """SELECT channel_id FROM vanity_channels WHERE guild_id = ?""", (guild_id,)
        )
        result = cursor.fetchall()
        conn.close()
        return [row[0] for row in result]

    @commands.Cog.listener()
    async def on_ready(self):
        await self.check_vanity_channels()

    async def check_vanity_channels(self):
        for guild in self.bot.guilds:
            vanity_channels = self.get_vanity_channels(guild.id)
            for channel_id in vanity_channels:
                vanity_channel = guild.get_channel(channel_id)
                if vanity_channel:
                    await self.save_vanity_channel(guild.id, channel_id)

    @commands.Cog.listener()
    async def on_guild_update(self, before, after):
        if before.vanity_url_code != after.vanity_url_code:
            for guild in self.bot.guilds:
                vanity_channels = self.get_vanity_channels(guild.id)
                for channel_id in vanity_channels:
                    vanity_channel = guild.get_channel(channel_id)
                    if vanity_channel:
                        embed = discord.Embed(
                            description=f"Vanity /{before.vanity_url_code} has been dropped",
                            color=self.bot.color,
                        )
                        await vanity_channel.send(embed=embed)

    @commands.command(
        help="config",
        description="snipe vanity`s on a channel",
        brief="manage_channels",
        usage="[channel]",
    )
    @utils.get_perms("manage_channels")
    async def vanityset(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if channel.guild.id != guild_id:
            await ctx.send_warning("Please mention a channel within this server.")
            return
        vanity_channels = self.get_vanity_channels(guild_id)
        if channel.id in vanity_channels:
            await ctx.send_warning(
                "Vanity logging is already enabled for this channel."
            )
        else:
            self.save_vanity_channel(guild_id, channel.id)
            await ctx.send_success(f"Vanity logging enabled for #{channel.name}.")

    @commands.command(
        help="config",
        description="remove vanity snipe from a channel",
        brief="manage_channels",
        usage="[channel]",
    )
    @utils.get_perms("manage_channels")
    async def vanityunset(self, ctx, channel: discord.TextChannel):
        guild_id = ctx.guild.id
        if channel.guild.id != guild_id:
            await ctx.send_error("Please mention a channel within this server.")
            return
        vanity_channels = self.get_vanity_channels(guild_id)
        if channel.id not in vanity_channels:
            await ctx.send_error("Vanity logging is not enabled for this channel.")
        else:
            self.remove_vanity_channel(guild_id, channel.id)
            await ctx.send_success(f"Vanity logging disabled for #{channel.name}.")


async def setup(bot):
    await bot.add_cog(Vanity(bot))
