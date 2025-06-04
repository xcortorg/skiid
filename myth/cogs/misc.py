from datetime import datetime, timedelta

import asyncpg
import discord
import pytz
from config import color, emoji
from discord.ext import commands
from discord.utils import format_dt
from system.base.context import Context
from system.base.paginator import Paginator


class Miscellaneous(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.afk = {}
        self.deleted_messages = {}
        self.edited_messages = {}

    @commands.command(description="Set your custom prefix", aliases=["sp", "sx"])
    async def selfprefix(self, ctx: Context, prefix: str = None):
        if prefix is None:
            await ctx.send_help(ctx.command.qualified_name)
        else:
            if len(prefix) > 8:
                await ctx.deny("The prefix **cannot** be longer than 8 characters")
                return

            user_id = str(ctx.author.id)

            async with self.client.pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO prefixes (user_id, prefix) 
                    VALUES ($1, $2) 
                    ON CONFLICT (user_id) 
                    DO UPDATE SET prefix = EXCLUDED.prefix""",
                    user_id,
                    prefix,
                )

            await ctx.agree(f"**Set** your prefix to: `{prefix}`")

    @commands.command(
        description="Clear bot messages", aliases=["bc", "botpurge", "bp"]
    )
    @commands.has_permissions(manage_messages=True)
    async def botclear(self, ctx, amount: int = None):
        if amount is None:
            await ctx.send("You're **missing a number**")
            return

        if amount > 20:
            amount = 20
            await ctx.send("The **maximum** is 20")

        deleted = 0
        async for message in ctx.channel.history(limit=amount):
            if message.author.bot:
                await message.delete()
                deleted += 1

        await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Check for old and deleted messages", aliases=["s"])
    async def snipe(self, ctx):
        channel_id = ctx.channel.id
        sniped_messages = self.deleted_messages.get(channel_id, [])

        if sniped_messages:
            pages = []

            for index, deleted_message in enumerate(reversed(sniped_messages), start=1):
                deleting_user = ctx.guild.get_member(int(deleted_message.author.id))
                user_pfp = (
                    deleting_user.avatar.url
                    if deleting_user.avatar
                    else deleting_user.default_avatar.url
                )

                embed = discord.Embed(
                    description=f"> {deleted_message.content}", color=color.default
                )
                embed.set_author(name=deleting_user.display_name, icon_url=user_pfp)
                embed.set_footer(text=f"Page {index} of {len(sniped_messages)}")
                pages.append(embed)

            paginator = Paginator(ctx, pages, current=0)
            message = await ctx.send(embed=pages[0], view=paginator)
        else:
            await ctx.message.add_reaction(f"{emoji.deny}")

    @commands.command(description="Check for old and edited messages", aliases=["es"])
    async def editsnipe(self, ctx):
        channel_id = ctx.channel.id
        sniped_edits = self.edited_messages.get(channel_id, [])

        if sniped_edits:
            pages = []

            for index, (before, after) in enumerate(reversed(sniped_edits), start=1):
                editing_user = ctx.guild.get_member(int(before.author.id))
                user_pfp = (
                    editing_user.avatar.url
                    if editing_user.avatar
                    else editing_user.default_avatar.url
                )

                embed = discord.Embed(description=f"", color=color.default)
                embed.add_field(name="Before", value=f"{before.content}")
                embed.add_field(name="After", value=f"{after.content}")
                embed.set_author(name=editing_user.display_name, icon_url=user_pfp)
                embed.set_footer(text=f"Page {index} of {len(sniped_edits)}")
                pages.append(embed)

            paginator = Paginator(ctx, pages, current=0)
            message = await ctx.send(embed=pages[0], view=paginator)
        else:
            await ctx.message.add_reaction(f"{emoji.deny}")

    @commands.command(description="Clear all snipes", aliases=["cs"])
    @commands.has_permissions(manage_messages=True)
    async def clearsnipe(self, ctx):
        channel_id = ctx.channel.id
        cleared = False

        if channel_id in self.deleted_messages:
            del self.deleted_messages[channel_id]
            cleared = True

        if channel_id in self.edited_messages:
            del self.edited_messages[channel_id]
            cleared = True

        if cleared:
            await ctx.message.add_reaction(f"{emoji.agree}")
        else:
            await ctx.message.add_reaction(f"{emoji.deny}")

    @commands.command(description="Set your afk")
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
        embed.set_author(name=f"{ctx.author.name} | Is now afk", icon_url=user_pfp)
        await ctx.send(embed=embed)

    @commands.command(description="Clear your messages", aliases=["selfclear", "me"])
    async def selfpurge(self, ctx, amount: str = None):
        if amount is None:
            await ctx.deny("You're **missing a number**")
            return

        if amount.lower() == "all":
            amount = None
        else:
            try:
                amount = int(amount)
            except ValueError:
                await ctx.deny("You're **missing a number**")
                return

        if amount and amount > 250:
            await ctx.send("The **maximum** is 250")
            return

        to_delete = []

        async for m in ctx.channel.history(limit=(amount or 250)):
            if m.author.id == ctx.author.id and m.id != ctx.message.id:
                to_delete.append(m)

        if to_delete:
            await ctx.message.add_reaction(f"{emoji.agree}")
            await ctx.channel.delete_messages(to_delete)
        else:
            await ctx.message.add_reaction(f"{emoji.deny}")

    @commands.command(
        description="Allow people sending attachments", aliases=["pic", "picperms"]
    )
    @commands.has_permissions(manage_channels=True)
    async def picperm(self, ctx, user: discord.Member):
        channel = ctx.channel
        overwrite = channel.overwrites_for(user)

        if (overwrite.attach_files is None or overwrite.attach_files is False) and (
            overwrite.embed_links is None or overwrite.embed_links is False
        ):
            overwrite.attach_files = True
            overwrite.embed_links = True
            await channel.set_permissions(user, overwrite=overwrite)
            await ctx.agree(f"**Added** picperms to: {user.mention}")
        else:
            overwrite.attach_files = False
            overwrite.embed_links = False
            await channel.set_permissions(user, overwrite=overwrite)
            await ctx.agree(f"**Removed** picperms from: {user.mention}")

    @commands.group(
        description="Configure timezone", invoke_without_command=True, aliases=["tz"]
    )
    async def timezone(self, ctx, user: discord.User = None):
        user = user or ctx.author

        row = await self.client.pool.fetchrow(
            "SELECT timezone FROM timezone WHERE user_id = $1", user.id
        )
        user_tz = row["timezone"] if row else None

        if not user_tz:
            await ctx.deny(
                f"{user.mention} **has not** set their timezone, use `{ctx.prefix}timezone set [Europe/London]` to set your timezone"
            )
            return

        timezone1 = datetime.now(pytz.timezone(user_tz))
        timezone = timezone1.strftime("%Y-%m-%d %I:%M %p")

        embed = discord.Embed(
            description=f"> **It's currently:** `{timezone}`", color=color.default
        )
        embed.set_author(
            name=f"{user.name} | {user_tz}",
            icon_url=user.avatar.url or user.default_avatar.url,
        )
        await ctx.send(embed=embed)

    @timezone.command(
        name="set",
        description="Set your timezone, for example: America/Chicago",
    )
    async def timezone_set(self, ctx, timezone: str):
        if timezone not in pytz.all_timezones:
            await ctx.warn(
                "**Invalid timezone,** use a valid timezone like: `America/Chicago`"
            )
            return

        await self.client.pool.execute(
            """
            INSERT INTO timezone (user_id, timezone)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET timezone = $2;
        """,
            ctx.author.id,
            timezone,
        )
        await ctx.agree(f"**Set** your timezone to: `{timezone}`")

    @timezone.command(
        name="unset", description="Unset your timezone", aliases=["tzunset"]
    )
    async def timezone_unset(self, ctx):
        await self.client.pool.execute(
            "DELETE FROM timezone WHERE user_id = $1", ctx.author.id
        )
        await ctx.agree("**Removed** your timezone")

    # events and others

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id != self.client.user.id and not message.content.startswith(
            await self.client.command_prefix(message)
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

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and not message.author.bot:
            channel_id = message.channel.id
            if channel_id not in self.deleted_messages:
                self.deleted_messages[channel_id] = []
            self.deleted_messages[channel_id].append(message)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.guild and not before.author.bot:
            channel_id = before.channel.id
            if channel_id not in self.edited_messages:
                self.edited_messages[channel_id] = []
            self.edited_messages[channel_id].append((before, after))

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
    await client.add_cog(Miscellaneous(client))
