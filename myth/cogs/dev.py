import asyncio
import random
import string

import aiohttp
import discord
from config import color, emoji
from discord.ext import commands
from discord.utils import oauth_url
from system.base.context import Context
from system.base.paginator import Paginator


class Developer(commands.Cog):
    def __init__(self, client):
        self.client = client

    def gen_id(self):
        random_id = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"error-{random_id}"

    async def log_error(self, error_message: str):
        err_id = self.gen_id()
        await self.client.pool.execute(
            "INSERT INTO errors (error_id, error_message) VALUES ($1, $2)",
            err_id,
            error_message,
        )
        return err_id

    @commands.command(description="Get an error from an error id")
    @commands.is_owner()
    async def error(self, ctx: Context, error_id: str):
        error_data = await self.client.pool.fetchrow(
            "SELECT error_message, timestamp FROM errors WHERE error_id = $1", error_id
        )

        if error_data:
            error_message = error_data["error_message"]
            timestamp = error_data["timestamp"]
            embed = discord.Embed(
                description=f"> Error ID: `{error_id}` \n> Occurred at: `{timestamp}` \n```{error_message}```",
                color=color.default,
            )
            embed.set_author(name="Error Occurred", icon_url=ctx.author.avatar.url)
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
            await ctx.send(embed=embed)
        else:
            await ctx.message.add_reaction(emoji.warn)

    @commands.command(desription="Change the bots pfp")
    @commands.is_owner()
    async def botpfp(self, ctx, url):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        print(f"Failed failed: {resp.status}")
                        return await ctx.deny("coulnt fetch the img")

                    data = await resp.read()

                    await self.client.user.edit(avatar=data)
                    await ctx.message.add_reaction(f"{emoji.agree}")
        except Exception as e:
            await ctx.warn(f"```{e}```")

    @commands.command(desription="Change the bots banner")
    @commands.is_owner()
    async def botbanner(self, ctx, url: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        return await ctx.deny("coulnt fetch the img")

                    data = await resp.read()

                    await self.client.user.edit(banner=data)
                    await ctx.message.add_reaction(f"{emoji.agree}")
        except discord.HTTPException as e:
            await ctx.warn(f"```{e}```")
        except Exception as e:
            await ctx.warn(f"```{e}```")

    @commands.command(
        description="Check out the lastest guilds", aliases=["lastestgd", "lgd"]
    )
    @commands.is_owner()
    async def latestguilds(self, ctx):
        guilds = sorted(self.client.guilds, key=lambda g: g.me.joined_at, reverse=True)[
            :5
        ]

        if not guilds:
            await ctx.send("aint in any guilds")
            return

        description = []
        for guild in guilds:
            invite = None
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite = await channel.create_invite(max_age=0, max_uses=1)
                    break

            invite_link = invite.url if invite else "cant get inv"
            description.append(
                f"**{guild.name}** ({guild.member_count} members)\nInvite: {invite_link}"
            )

        await ctx.send("\n\n".join(description))

    @commands.command(description="Make the bot leave a guild")
    @commands.is_owner()
    async def botleave(self, ctx, guild_id: int = None):
        guild = None

        if guild_id:
            guild = self.client.get_guild(guild_id)
            if guild is None:
                await ctx.send(f"cant find the id: {guild_id}")
                return
        else:
            guild = ctx.guild

        await ctx.agree(f"left: {guild.name} ({guild.id})")
        await guild.leave()

    @commands.command()
    @commands.is_owner()
    async def test(self, ctx):
        embed1 = discord.Embed(
            title="Myth",
            description="> The bot that will change your discord server forever.",
            color=color.default,
        )
        embed1.add_field(
            name="Why Myth?",
            value="> 24/7 online \n> ‎ Active updates \n> ‎ ‎ Automoderation \n> ‎ ‎ ‎  Just simply cooler 😎",
            inline=False,
        )

        embed2 = discord.Embed(
            title="Roles",
            description="> <:29:1298731238655266847> - Downtimes or undergoing maintenances \n> ‎ <:28:1298731241209729024> - Updates, changelogs and devlogs",
            color=color.default,
        )
        embed2.add_field(
            name="Rules",
            value="> No selfbot \n> ‎ No promo (includes dm promo)",
            inline=False,
        )

        await ctx.send(embeds=[embed1, embed2])

    @commands.command(description="Leave servers under 10 humans")
    @commands.is_owner()
    async def massleave(self, ctx):
        left_guilds = []
        for guild in self.client.guilds:
            human_members = sum(1 for member in guild.members if not member.bot)
            if human_members < 10:
                await guild.leave()
                left_guilds.append(guild.name)

        if left_guilds:
            await ctx.agree(f"left: {', '.join(left_guilds)}")
        else:
            await ctx.deny("cant find shit")

    @commands.command(description="Blacklist horrible people", aliases=["bl"])
    @commands.is_owner()
    async def blacklist(
        self, ctx, user: discord.User, *, reason: str = "No reason provided"
    ):
        async with self.client.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM blacklist WHERE user_id = $1", str(user.id)
            )
            if result:
                await ctx.deny(f"{user.mention} is **already** blacklisted.")
                return

            await conn.execute(
                "INSERT INTO blacklist (user_id, reason) VALUES ($1, $2)",
                str(user.id),
                reason,
            )
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Unblacklist nice people", aliases=["unbl"])
    @commands.is_owner()
    async def unblacklist(self, ctx, user: discord.User):
        async with self.client.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT 1 FROM blacklist WHERE user_id = $1", str(user.id)
            )
            if not result:
                await ctx.deny(f"{user.mention} isn't **blacklisted**")
                return

            await conn.execute("DELETE FROM blacklist WHERE user_id = $1", str(user.id))
            await ctx.message.add_reaction(f"{emoji.agree}")

    @commands.command(description="Check for all the blacklisted users")
    async def blacklisted(self, ctx: commands.Context):
        rows = await self.client.pool.fetch("SELECT user_id, reason FROM blacklist")

        if not rows:
            embed = discord.Embed(description="Nones blacklisted", color=color.default)
            return await ctx.send(embed=embed)

        embeds = []
        for i in range(0, len(rows), 10):
            embed = discord.Embed(title="Blacklisted", color=color.default)
            description = ""
            for row in rows[i : i + 10]:
                user_id = row["user_id"]
                reason = row["reason"]
                user = await self.client.fetch_user(user_id)
                description += f"> {user.mention} ({user.id}) blacklisted for the reason: {reason}\n\n"

            embed.description = description
            embed.set_footer(text=f"Page {i // 10 + 1}/{(len(rows) - 1) // 10 + 1}")
            embeds.append(embed)

        paginator = Paginator(ctx, pages, current=0)
        message = await ctx.send(embed=pages[0], view=paginator)

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        invite_link = (
            f"https://discord.gg/{guild.vanity_url_code}"
            if guild.vanity_url_code
            else None
        )

        if not invite_link:
            for channel in guild.text_channels:
                if channel.permissions_for(guild.me).create_instant_invite:
                    invite = await channel.create_invite(max_age=0, max_uses=0)
                    invite_link = invite.url
                    break

        embed = discord.Embed(
            title=f"Joined: {guild.name}",
            description=f"> {invite_link}\n> **Members**: {guild.member_count}\n> **Owner**: {guild.owner}",
            color=color.default,
        )
        embed.set_footer(text=f"ID: {guild.id}")
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        channel = self.client.get_channel(1294659350819897384)
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild):
        embed = discord.Embed(
            title=f"Left: {guild.name}",
            description=f"> **Members**: {guild.member_count}\n> **Owner**: {guild.owner}",
            color=color.default,
        )
        embed.set_footer(text=f"ID: {guild.id}")
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)

        channel = self.client.get_channel(1294659367962148935)
        if channel:
            await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        whitelisted = [394152799799345152, 255841984470712330, 1168186952772747364]
        if member.guild.id != 1294657805843697664:
            return

        if member.id not in whitelisted:
            await member.kick(reason="not whitelisted")
            print(f"kicked {member.name} (ID: {member.id}) for not being whitelisted")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id == 1282563196120727663:
            channel = member.guild.get_channel(1298729337742430230)

            if channel:
                user_pfp = (
                    member.avatar.url if member.avatar else member.default_avatar.url
                )

                embed = discord.Embed(
                    title="Welcome <a:008:1298392198076694559>",
                    description=f"> https://discord.com/channels/1282563196120727663/1298391057570074705 \n> https://discord.com/channels/1282563196120727663/1292535994435768350",
                    color=color.default,
                )
                embed.set_thumbnail(url=user_pfp)
                embed.set_footer(
                    text=f"We're now at {member.guild.member_count} members"
                )

                await channel.send(f"{member.mention}", embed=embed)


async def setup(client):
    await client.add_cog(Developer(client))
