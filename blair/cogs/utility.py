from datetime import datetime, timedelta

import aiohttp
import discord
import pytz
from discord.ext import commands
from discord.ext.commands import (Bot, BucketType, cooldown, group,
                                  has_permissions, hybrid_command,
                                  hybrid_group)
from discord.utils import format_dt
from tools.config import color, emoji
from tools.context import Context
from tools.paginator import Simple


class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.afk = {}

    async def set_user_timezone(self, user_id: int, timezone: str):
        async with self.client.pool.acquire() as conn:
            await conn.execute(
                """
            INSERT INTO user_timezones (user_id, timezone)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET timezone = $2;
            """,
                user_id,
                timezone,
            )

    async def unset_user_timezone(self, user_id: int):
        async with self.client.pool.acquire() as conn:
            await conn.execute("DELETE FROM user_timezones WHERE user_id = $1", user_id)

    async def get_user_timezone(self, user_id: int):
        async with self.client.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT timezone FROM user_timezones WHERE user_id = $1", user_id
            )
            return row["timezone"] if row else None

    @commands.command(description="Set your AFK")
    @commands.cooldown(1, 2, commands.BucketType.user)
    async def afk(self, ctx, *, message: str = "AFK"):
        timestamp = discord.utils.utcnow()
        self.afk[ctx.author.id] = (message, timestamp)

        user_pfp = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )

        embed = discord.Embed(
            description=f"> With the message: **{message}**", color=color.default
        )
        embed.set_author(name=f"{ctx.author.name} | Is now AFK", icon_url=user_pfp)
        await ctx.send(embed=embed)

    @commands.command(
        description="Show your love by sending feedback", aliases=["vouch"]
    )
    async def feedback(self, ctx, *, feedback: str):
        if feedback.endswith("/5"):
            try:
                *feedback_text, rating = feedback.rsplit(" ", 1)
                feedback_text = " ".join(feedback_text)

                stars = int(rating.split("/")[0])
                if not 1 <= stars <= 5:
                    raise ValueError
            except ValueError:
                await ctx.warn("You're **missing** a valid rating, use 1/5")
                return
        else:
            await ctx.warn("You're **missing** rating, use 1/5")
            return

        feedback_channel = self.client.get_channel(1299760035328557117)
        if not feedback_channel:
            await ctx.deny("Couldn't find the feedback channel")
            return

        stars_display = "⭐" * stars + "☆" * (5 - stars)

        embed = discord.Embed(
            description=f"> {feedback_text}\n\n**Rating:** {stars_display} ({stars}/5)",
            color=color.default,
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)

        await feedback_channel.send(embed=embed)
        await ctx.agree("**Sent** the feedback, thanks for your time!")

    @commands.command(description="Nuke a channel", aliases=["nk"])
    @commands.has_permissions(manage_channels=True)
    async def nuke(self, ctx: commands.Context, channel: discord.TextChannel = None):
        channel = channel or ctx.channel
        new_channel = await channel.clone(reason="Nuked")
        await channel.delete(reason="Nuked")
        await new_channel.send("first")
        await new_channel.edit(position=channel.position)

    @hybrid_command(aliases=["tz"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def timezone_view(self, ctx, user: discord.User = None):
        user = user or ctx.author
        user_timezone = await self.get_user_timezone(user.id)

        if not user_timezone:
            await ctx.warn(
                f"{user.display_name} hasn't set their timezone yet. Use `-tzset <timezone>` to set it."
            )
            return
        current_time = datetime.now(pytz.timezone(user_timezone)).strftime(
            "%d %B %Y, %I:%M %p"
        )

        embed = discord.Embed(
            title=f"",
            description=f"> **Current time:** {current_time}",
            color=color.default,
        )
        embed.set_footer(text=f"Timezone: {user_timezone}")
        embed.set_author(
            name=user.display_name, icon_url=user.avatar.url or user.default_avatar.url
        )
        await ctx.send(embed=embed)

    @hybrid_command(aliases=["tzl"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def timezone_list(self, ctx):
        async with self.client.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT timezone, COUNT(*) AS count FROM user_timezones GROUP BY timezone ORDER BY count DESC"
            )

        if not rows:
            await ctx.warn("No timezones have been set by users in this server.")
            return

        embeds = []
        timezone_list_str = ""

        for row in rows:
            timezone, count = row["timezone"], row["count"]
            timezone_list_str += f"**{timezone}**: {count} users\n"

            if len(timezone_list_str.splitlines()) >= 10:
                embed = discord.Embed(
                    description=timezone_list_str, color=color.default
                )
                embed.set_author(
                    name="Server Timezones",
                    icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
                )
                embeds.append(embed)
                timezone_list_str = ""

        if timezone_list_str:
            embed = discord.Embed(description=timezone_list_str, color=color.default)
            embed.set_author(
                name="Server Timezones",
                icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
            )
            embeds.append(embed)

        await Simple(embeds).start(ctx)

    @hybrid_command(aliases=["tzs"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def timezone_set(self, ctx, timezone: str):
        if timezone not in pytz.all_timezones:
            await ctx.warn(
                "Invalid timezone. Please use a valid timezone name, e.g., `America/New_York`."
            )
            return

        await self.set_user_timezone(ctx.author.id, timezone)
        embed = discord.Embed(
            description=f"> **Your timezone has been set to:** {timezone}",
            color=color.default,
        )
        embed.set_author(
            name=f"{ctx.author.name} | Timezone Set",
            icon_url=(
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            ),
        )
        await ctx.send(embed=embed)

    @hybrid_command(aliases=["tzrm"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def timezone_remove(self, ctx):
        user_id = ctx.author.id
        await self.unset_user_timezone(user_id)
        await ctx.agree("Your timezone has been unset.")

    # events

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.client.user.id and not message.content.startswith(
            "-"
        ):
            for user in message.mentions:
                if user.id in self.afk:
                    message_text, timestamp = self.afk[user.id]
                    now = discord.utils.utcnow()
                    afk_duration = now - timestamp
                    afk_duration_str = self.format_duration(afk_duration)

                    user_pfp = (
                        user.avatar.url if user.avatar else user.default_avatar.url
                    )

                    embed = discord.Embed(
                        description=f"> With the message: **{message_text}** \n > For: **{afk_duration_str}**",
                        color=color.default,
                    )
                    embed.set_author(name=f"{user.name} | Is afk", icon_url=user_pfp)
                    await message.channel.send(embed=embed)

            if message.author.id in self.afk:
                message_text, timestamp = self.afk[message.author.id]
                now = discord.utils.utcnow()
                afk_duration = now - timestamp
                afk_duration_str = self.format_duration(afk_duration)

                user_pfp = (
                    message.author.avatar.url
                    if message.author.avatar
                    else message.author.default_avatar.url
                )

                embed = discord.Embed(
                    description=f"> You were afk for: **{afk_duration_str}**",
                    color=color.default,
                )
                embed.set_author(
                    name=f"{message.author.name} | Welcome back!", icon_url=user_pfp
                )
                await message.channel.send(embed=embed)
                del self.afk[message.author.id]

    def format_duration(self, duration):
        total_seconds = int(duration.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        duration_str = ""
        if days > 0:
            duration_str += f"{days}d "
        if hours > 0 or days > 0:
            duration_str += f"{hours}h "
        if minutes > 0 or hours > 0 or days > 0:
            duration_str += f"{minutes}m "
        duration_str += f"{seconds}s"

        return duration_str


async def setup(client):
    await client.add_cog(Utility(client))
