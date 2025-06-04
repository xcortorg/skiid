import re
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands, tasks
from get.checks import Perms as utils


class TempChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db
        self.check_expired_channels.start()

    def parse_duration(self, duration_str):
        """
        Parses a duration string into a timedelta object.
        Supports seconds (s), minutes (m), hours (h), days (d), and weeks (w).
        Example inputs: '30s', '10m', '2h', '1d', '1w'
        """
        units = {
            "s": "seconds",
            "m": "minutes",
            "h": "hours",
            "d": "days",
            "w": "weeks",
        }
        regex = re.compile(r"(\d+)([smhdw])")
        matches = regex.findall(duration_str)

        if not matches:
            raise ValueError(
                "Invalid duration format. Use numbers followed by s, m, h, d, or w (e.g., '30s', '1d')."
            )

        duration_kwargs = {}
        for value, unit in matches:
            if unit in units:
                duration_kwargs[units[unit]] = int(value)
            else:
                raise ValueError(f"Unknown duration unit: {unit}")

        return timedelta(**duration_kwargs)

    @commands.group(help="utility", invoke_without_command=True, aliases=["tc"])
    async def tempchannel(self, ctx: commands.Context):
        await ctx.create_pages()

    @tempchannel.command(
        help="utility",
        usage="[time, example: 1s,1m,1h,1d,1w] [channel name]",
        description="make a temp text channel in the server",
    )
    @utils.get_perms("manage_channels")
    async def create(self, ctx, duration: str, *, channel_name: str):
        """
        Command to create a temporary text channel.
        :param ctx: The context of the command.
        :param duration: Duration in seconds, minutes, hours, days, or weeks before the channel is deleted.
        :param channel_name: The name of the temporary channel.
        """
        try:
            delta = self.parse_duration(duration)
        except ValueError as e:
            await ctx.send(str(e))
            return

        # Create the temporary text channel
        temp_channel = await ctx.guild.create_text_channel(channel_name)
        expiration_time = datetime.now(timezone.utc) + delta

        # Store the channel information in the database
        await self.db.execute(
            """
            INSERT INTO temp_channels(channel_id, guild_id, expiration_time)
            VALUES($1, $2, $3)
        """,
            temp_channel.id,
            ctx.guild.id,
            expiration_time,
        )

        await ctx.send_success(
            f"Temporary channel {temp_channel.mention} created for {duration}."
        )

    @tasks.loop(minutes=1)
    async def check_expired_channels(self):
        current_time = datetime.now(timezone.utc)
        expired_channels = await self.db.fetch(
            """
            SELECT channel_id, guild_id FROM temp_channels
            WHERE expiration_time <= $1
        """,
            current_time,
        )

        for channel in expired_channels:
            guild = self.bot.get_guild(channel["guild_id"])
            if guild:
                temp_channel = guild.get_channel(channel["channel_id"])
                if temp_channel:
                    await temp_channel.delete()

        # Remove the expired channels from the database
        await self.db.execute(
            """
            DELETE FROM temp_channels WHERE expiration_time <= $1
        """,
            current_time,
        )

    @check_expired_channels.before_loop
    async def before_check_expired_channels(self):
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot):
    await bot.add_cog(TempChannel(bot))
