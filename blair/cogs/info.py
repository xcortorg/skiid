import asyncio
import datetime
import os
import time
from datetime import datetime, timedelta, timezone
from platform import python_version
from typing import Union

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import (Bot, BucketType, cooldown, group,
                                  has_permissions, hybrid_command,
                                  hybrid_group)
from discord.ui import Button, View
from discord.utils import format_dt
from tools.config import color, emoji
from tools.context import Context
from tools.paginator import Simple


class Information(commands.Cog):
    def __init__(self, bot):
        self.client = bot
        self.start_time = datetime.now(timezone.utc)
        self.pool = bot.pool

    def count_code_lines(self, directory):
        """Count the number of lines in Python files in the specified directory."""
        total_lines = 0
        for dirpath, _, filenames in os.walk(directory):
            for filename in [f for f in filenames if f.endswith(".py")]:
                with open(
                    os.path.join(dirpath, filename), "r", encoding="utf-8"
                ) as file:
                    total_lines += sum(1 for line in file if line.strip())
        return total_lines

    @hybrid_command(aliases=["png"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ping(self, ctx: commands.Context):
        """Displays the bot's ping."""
        latency = round(self.client.latency * 1000)
        await ctx.send(
            embed=discord.Embed(
                description=f"> :stars: **Ping:** `{latency} ms`", color=color.default
            )
        )

    @hybrid_command(aliases=["up"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def uptime(self, ctx: commands.Context):
        """Displays the bot's uptime."""
        uptime_delta = datetime.now(timezone.utc) - self.start_time
        hours, minutes, seconds = (
            uptime_delta.seconds // 3600,
            (uptime_delta.seconds // 60) % 60,
            uptime_delta.seconds % 60,
        )
        uptime_str = f"{uptime_delta.days}d {hours}h {minutes}m {seconds}s"
        await ctx.send(
            embed=discord.Embed(
                description=f"> :candle: **Blare** has been up for: `{uptime_str}`",
                color=color.default,
            )
        )

    @hybrid_command(aliases=["shd"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def shards(self, ctx: commands.Context):
        """Displays shard information with minimal delay."""
        total_shards = self.client.shard_count
        shard_data = [{"guilds": 0, "members": 0} for _ in range(total_shards)]
        for guild in self.client.guilds:
            shard_info = shard_data[guild.shard_id]
            shard_info["guilds"] += 1
            shard_info["members"] += guild.member_count
        embed = discord.Embed(
            title="Shard Information",
            description=f"**Total Shards:** `{total_shards}`",
            color=color.default,
        )
        embed.add_field(
            name="Shard Stats",
            value="\n\n".join(
                f"**Shard {i}**\n> 🏠 Guilds: `{info['guilds']}`\n> 👥 Members: `{info['members']}`"
                for i, info in enumerate(shard_data)
            ),
            inline=False,
        )
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)

    @hybrid_command(aliases=["sup"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def support(self, ctx: commands.Context):
        """Get a link to the official Blare support."""
        embed = discord.Embed(
            title="official support",
            description="> Join the official Blare support server below if you need help ^_^",
            color=color.default,
        )
        view = View().add_item(
            Button(label="Join Support", url="https://discord.gg/blare")
        )
        await ctx.send(embed=embed, view=view, ephemeral=bool(ctx.interaction))

    @hybrid_command(aliases=["bi"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def botinfo(self, ctx):
        """view info of blare."""
        user_pfp = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )
        avatar_url = (
            self.client.user.avatar.url
            if self.client.user.avatar
            else self.client.user.default_avatar.url
        )

        members = sum(guild.member_count for guild in self.client.guilds)
        guilds = len(self.client.guilds)
        latency = round(self.client.latency * 1000)
        lines2 = self.count_code_lines("cogs")

        uptime_start = self.client.uptime()
        uptime = format_dt(uptime_start, style="R")

        total_commands = sum(
            1 + len(command.commands) if isinstance(command, commands.Group) else 1
            for command in self.client.commands
            if not command.hidden and command.cog_name != "Jishaku"
        )

        view = View()
        view.add_item(
            Button(
                style=discord.ButtonStyle.link,
                label="Support",
                url="https://discord.gg/blare",
            )
        )
        view.add_item(
            Button(
                style=discord.ButtonStyle.link,
                label="Invite me",
                url="https://discordapp.com/oauth2/authorize?client_id=1161529597012226099&scope=bot+applications.commands&permissions=8",
            )
        )

        embed = discord.Embed(
            title="Information",
            description=f"> **Loved** by `{members:,}` users & `{guilds:,}` guilds \n> **Worked** on by [lavalink](https://github.com/lavalink-dev) & [solix](https://github.com/SolixBloxYT)",
            color=color.default,
        )
        embed.add_field(
            name="Stats",
            value=f"> **Latency:** `{latency}ms` \n> **Lines:** `{lines2}` \n> **Commands:** `{total_commands}`",
            inline=True,
        )
        embed.add_field(
            name="System",
            value=f"> **Python:** `{python_version()}` \n> **Discord.py:** `{discord.__version__}` \n> **Started:** {uptime}",
            inline=True,
        )
        embed.set_author(name=ctx.author.name, icon_url=user_pfp)
        embed.set_thumbnail(url=avatar_url)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(aliases=["gicon"])
    async def guildicon(self, ctx: commands.Context, guild_id: int = None):
        """Displays the icon of the specified guild, or the current guild if none is provided."""
        guild = self.client.get_guild(guild_id) if guild_id else ctx.guild
        if not guild:
            return await ctx.deny("The guild could **not** be found")

        icon_url = getattr(guild.icon, "url", None)
        if icon_url:
            await ctx.send(
                embed=discord.Embed(title=f"{guild.name}'s Icon", color=color.default)
                .set_image(url=icon_url)
                .set_footer(
                    text=f"Requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url,
                )
            )
        else:
            await ctx.deny(f"{guild.name} has **no** icon")

    @commands.hybrid_command(aliases=["gbanner"])
    async def guildbanner(self, ctx: commands.Context, guild_id: int = None):
        """Shows the banner of the specified guild or current guild if none is provided."""
        guild = self.client.get_guild(guild_id) if guild_id else ctx.guild
        if not guild:
            return await ctx.deny("The guild could **not** be found")
        banner_url = getattr(guild.banner, "url", None)
        if banner_url:
            await ctx.send(
                embed=discord.Embed(title=f"{guild.name}'s Banner", color=color.default)
                .set_image(url=banner_url)
                .set_footer(
                    text=f"Requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url,
                )
            )
        else:
            await ctx.deny(f"{guild.name} has **no** banner")

    @commands.hybrid_command(aliases=["splashbg"])
    async def splash(self, ctx: commands.Context, guild_id: int = None):
        """Displays the splash background of the specified guild, or the current guild if none is provided."""
        guild = self.client.get_guild(guild_id) if guild_id else ctx.guild
        if not guild:
            return await ctx.deny("The guild could **not** be found")
        if guild.splash:
            await ctx.send(
                embed=discord.Embed(
                    title=f"{guild.name}'s Splash Background", color=color.default
                )
                .set_image(url=guild.splash.url)
                .set_footer(
                    text=f"Requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url,
                )
            )
        else:
            await ctx.deny(f"{guild.name} has **no** splash")

    @commands.command(aliases=["ii"])
    async def inviteinfo(self, ctx: commands.Context, invite_code: str):
        """Displays information about a specific server invite."""
        try:
            invite = await self.client.fetch_invite(invite_code, with_counts=True)
            embed = discord.Embed(
                title="Invite Information",
                color=color.default,
                timestamp=discord.utils.utcnow(),
            )
            if invite.guild.icon:
                embed.set_thumbnail(url=invite.guild.icon.url)
            embed.add_field(name="Invite Code", value=f"`{invite.code}`", inline=False)
            embed.add_field(name="Server Name", value=invite.guild.name, inline=False)
            embed.add_field(
                name="Inviter",
                value=invite.inviter.mention if invite.inviter else "Unknown",
                inline=False,
            )
            embed.add_field(name="Uses", value=f"`{invite.uses or 0}`", inline=True)
            embed.add_field(
                name="Max Uses",
                value=f"`{invite.max_uses or 'Unlimited'}`",
                inline=True,
            )
            embed.add_field(
                name="Expiration",
                value=(
                    invite.expires_at.strftime("%Y-%m-%d %H:%M:%S")
                    if invite.expires_at
                    else "Never"
                ),
                inline=False,
            )
            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )

            await ctx.send(embed=embed)

        except discord.NotFound:
            await ctx.deny("Invite not found or invalid code.", delete_after=5)
        except Exception as e:
            await ctx.deny(f"An error occurred: {e}", delete_after=5)

    @commands.command(name="oldest", aliases=["old"])
    async def oldest(self, ctx: Context):
        """View the member with the most recently created Discord account."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")

        try:
            youngest_member = min(
                (member for member in ctx.guild.members if member.created_at),
                key=lambda m: m.created_at,
                default=None,
            )

            if youngest_member:
                creation_date = youngest_member.created_at.strftime("%Y-%m-%d %H:%M:%S")
                await ctx.agree(
                    f"The oldest user in the server is {youngest_member.mention}, "
                    f"created on **{creation_date}**."
                )
            else:
                await ctx.deny(
                    "Could not retrieve the member with the most recent account creation date."
                )
        except Exception as e:
            await ctx.deny(f"An error occurred: {str(e)}")

    @commands.command(name="youngest", aliases=["young"])
    async def youngest(self, ctx: Context):
        """View the member with the oldest Discord account in the server."""
        if not ctx.guild:
            return await ctx.send("This command can only be used in a server.")

        try:
            oldest_member = max(
                (member for member in ctx.guild.members if member.created_at),
                key=lambda m: m.created_at,
                default=None,
            )

            if oldest_member:
                creation_date = oldest_member.created_at.strftime("%Y-%m-%d %H:%M:%S")
                await ctx.agree(
                    f"The youngest user in the server is {oldest_member.mention}, "
                    f"created on **{creation_date}**."
                )
            else:
                await ctx.deny(
                    "Could not retrieve the member with the oldest account creation date."
                )
        except Exception as e:
            await ctx.deny(f"An error occurred: {str(e)}")

    @commands.command(aliases=["inr"])
    async def inrole(self, ctx: commands.Context, role: discord.Role):
        """View members which have a specific role."""
        members_with_role = [
            member.mention for member in ctx.guild.members if role in member.roles
        ]

        if not members_with_role:
            await ctx.deny(f"No members found with the role: **{role.name}**.")
            return

        embed = discord.Embed(
            title=f"Members with Role: **{role.name}**",
            description="\n".join(members_with_role),
            color=color.default,
        ).set_footer(
            text=f"Total Members: {len(members_with_role)}", icon_url=ctx.guild.icon.url
        )
        await ctx.send(embed=embed)

    @hybrid_command(aliases=["av"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def avatar(self, ctx: commands.Context, member: discord.User = None):
        """Displays the avatar of the user."""
        member = member or ctx.author
        embed = (
            discord.Embed(title=f"{member.display_name}'s Avatar", color=color.default)
            .set_image(url=member.display_avatar.url)
            .set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url,
            )
        )
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="view avatar",
                url=member.display_avatar.url,
                style=discord.ButtonStyle.link,
            )
        )
        await ctx.send(embed=embed, view=view)

    @commands.command(aliases=["bstrs"])
    async def boosters(self, ctx: commands.Context):
        """View server boosters."""
        boosters = [
            member.mention for member in ctx.guild.members if member.premium_since
        ]

        embed = discord.Embed(title="Server Boosters", color=color.default)
        embed.description = (
            ", ".join(boosters)
            if boosters
            else "> There are no boosters in this server."
        )
        await ctx.send(embed=embed)

    @commands.command(aliases=["bstrsl"])
    async def boosters_lost(self, ctx: commands.Context):
        """View all lost boosters."""
        lost_boosters = [
            member.mention
            for member in ctx.guild.members
            if member.premium_since is None
            and hasattr(member, "premium")
            and member.premium
        ]
        response = (
            ", ".join(lost_boosters)
            if lost_boosters
            else "There are no lost boosters in this server."
        )
        await ctx.agree(f"{response}")

    @hybrid_command(aliases=["bnr"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def banner(
        self, ctx: Context, member: Union[discord.Member, discord.User] = None
    ):
        """Displays the banner of the specified user or the command caller if none is provided."""
        member = member or ctx.author

        if isinstance(member, discord.Member) and member.banner:
            user = await self.client.fetch_user(member.id)
        else:
            try:
                user = await self.client.fetch_user(member.id)
            except (discord.NotFound, discord.HTTPException):
                await ctx.deny("User not found or could not fetch user details.")
                return

        if user.banner:
            embed = (
                discord.Embed(
                    title=f"{user.display_name}'s Banner", color=color.default
                )
                .set_image(url=user.banner.url)
                .set_footer(
                    text=f"Requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url,
                )
            )

            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="view banner",
                    url=user.banner.url,
                    style=discord.ButtonStyle.link,
                )
            )
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.deny(f"{user.mention} **does not** have a banner.")

    @commands.command(aliases=["mc"])
    async def membercount(self, ctx: commands.Context):
        """View the member count of the server."""
        if not ctx.guild:
            return await ctx.deny("This command can only be used in a server.")

        total_members = ctx.guild.member_count
        human_members = sum(1 for member in ctx.guild.members if not member.bot)
        bot_members = total_members - human_members

        embed = discord.Embed(
            title=f"Member Count for {ctx.guild.name}", color=color.default
        )
        embed.add_field(name="Total", value=f"> {total_members}", inline=True)
        embed.add_field(name="Humans", value=f"> {human_members}", inline=True)
        embed.add_field(name="Bots", value=f"> {bot_members}", inline=True)
        embed.set_thumbnail(url=self.client.user.avatar.url)
        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url,
        )
        await ctx.send(embed=embed)

    @commands.command(description="Check all bots in the server")
    async def bots(self, ctx: commands.Context):
        """View all bots in the server."""
        bots = [member for member in ctx.guild.members if member.bot]
        bot_list = [f"> {bot.mention} (ID: {bot.id})" for bot in bots]

        pages = [
            discord.Embed(
                title="Bots in the Server",
                description="\n".join(bot_list[i : i + 10]),
                color=color.default,
            ).set_footer(
                text=f"Requested by {ctx.author}",
                icon_url=ctx.author.display_avatar.url,
            )
            for i in range(0, len(bot_list), 10)
        ]
        if len(pages) > 1:
            paginator = Simple()
            await paginator.start(ctx, pages)
        elif pages:
            await ctx.send(embed=pages[0])
        else:
            await ctx.deny("No bots found in this server.")

    @commands.command(aliases=["emotes"])
    async def emojis(self, ctx: commands.Context):
        """Display all emojis in the server with their IDs and links."""
        emojis = ctx.guild.emojis
        if not emojis:
            await ctx.deny("This server has no emojis.")
            return
        embed = discord.Embed(title="Server Emojis", color=color.default)
        for emoji in emojis:
            embed.add_field(
                name=emoji.name,
                value=f"ID: `{emoji.id}`\nLink: [View Emoji]({emoji.url})",
                inline=False,
            )
        await ctx.send(embed=embed)

    @commands.command(aliases=["firstmsg"])
    async def firstmessage(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ):
        """Fetch and display the first message from the specified channel with a link button."""
        channel = channel or ctx.channel
        try:
            async for msg in channel.history(limit=1, oldest_first=True):
                embed = discord.Embed(
                    title="First message in channel",
                    description=msg.content or "> This message has no content.",
                    color=color.default,
                ).set_footer(
                    text=f"Sent by {msg.author} on {msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
                )
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="go 2 first message",
                        url=f"https://discord.com/channels/{ctx.guild.id}/{channel.id}/{msg.id}",
                        style=discord.ButtonStyle.link,
                    )
                )
                await ctx.send(embed=embed, view=view)
                return
            await ctx.deny("No messages found in this channel.")
        except Exception as e:
            await ctx.deny(f"err occurred: {str(e)}")

    @commands.hybrid_command(aliases=["si"])
    async def serverinfo(self, ctx: commands.Context):
        guild = ctx.guild
        # info
        verif = str(guild.verification_level).replace("_", " ").title()
        created_at = format_dt(guild.created_at, "F")
        description = guild.description if guild.description else "n/a"

        # members
        humans = sum(not member.bot for member in guild.members)
        bots = sum(member.bot for member in guild.members)
        total = len(guild.members)

        embed = discord.Embed(
            title=f"Server Information - {guild.name}",
            description=description,
            color=color.default,
        )
        embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(
            name="Information",
            value=f"> **Owner:** {guild.owner.mention} \n> **Created:** {created_at} \n> **Verification:** {verif}",
            inline=False,
        )
        embed.add_field(
            name="Members",
            value=f"> **Total:** {total} \n> **Humans:** {humans} \n> **Bots:** {bots}",
            inline=True,
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

    @hybrid_command(aliases=["ui"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def userinfo(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author

        embed = discord.Embed(title=f"{member} ({member.id})", color=color.default)
        created_at = (
            format_dt(member.created_at, style="D")
            if hasattr(member, "created_at")
            else "n/a"
        )
        if isinstance(member, discord.Member):
            joined_at = (
                format_dt(member.joined_at, style="D") if member.joined_at else "n/a"
            )
            joined_time = f"> {joined_at} \n> {format_dt(member.joined_at, style='R') if member.joined_at else 'n/a'}"
        else:
            joined_time = "> N/A \n> N/A"
        embed.add_field(
            name="Created",
            value=f"> {created_at} \n> {format_dt(member.created_at, style='R') if hasattr(member, 'created_at') else 'n/a'}",
            inline=True,
        )
        embed.add_field(name="Joined", value=joined_time, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)


# unfinished


async def setup(client):
    await client.add_cog(Information(client))
