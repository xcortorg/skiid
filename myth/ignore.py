import platform
import time
from datetime import datetime, timedelta
from typing import Optional

import discord
import psutil
from config import color, emoji
from discord import ButtonStyle, Embed, Member, User
from discord.ext import commands
from discord.ext.commands.parameters import Author
from discord.ui import Button, View
from discord.utils import format_dt, get
from system.base.context import Context


class Information(commands.Cog):
    def __init__(self, client):
        self.client = client
<<<<<<< HEAD:ignore.py
=======

    @commands.command(
        description="Check the bot's latency",
        aliases=["p", "latency"]
    )
    async def ping(self, ctx):
        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        latency = round(self.client.latency * 1000)
        
        embed = discord.Embed(description=f"> :mag: Latency: **{latency}ms**", color=color.default)
        embed.set_author(name=ctx.author.name, icon_url=user_pfp)
        await ctx.send(embed=embed)

    @commands.command(
        description="Add me im cool :sunglasses:", 
        aliases=["invite", "links"]
    )
    async def inv(self, ctx):
        view = View()
        support = Button(style=discord.ButtonStyle.link, label="Support", url="https://discord.gg/uid", emoji=f"{emoji.link}")
        inv = Button(style=discord.ButtonStyle.link, label="Invite me", url="https://discordapp.com/oauth2/authorize?client_id=1284613721888526417&scope=bot+applications.commands&permissions=8", emoji=f"{emoji.link}")
        
        view.add_item(support)
        view.add_item(inv)
        await ctx.send(view=view)

    @commands.command(
        description="Check the bot's info", 
        aliases=["bi", "bot"]
    )
    async def botinfo(self, ctx):
        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        avatar_url = self.client.user.avatar.url if self.client.user.avatar else self.client.user.default_avatar.url

        members = sum(guild.member_count for guild in self.client.guilds)
        guilds = len(self.client.guilds)
        latency = round(self.client.latency * 1000)

        uptime_start = self.client.uptime()  
        uptime = format_dt(uptime_start, style='R')
        lines2 = self.client.lines() 
        
        total_commands = 0
        for command in self.client.commands:
            if not command.hidden and command.cog_name != "Jishaku":
                total_commands += 1 

                if isinstance(command, commands.Group):
                    for subcommand in command.commands:
                        if not subcommand.hidden and command.cog_name != "Jishaku":
                            total_commands += 1

        view = View()
        support = Button(style=discord.ButtonStyle.link, label="Support", url="https://discord.gg/uid", emoji=f"{emoji.link}")
        inv = Button(style=discord.ButtonStyle.link, label="Invite me", url="https://discordapp.com/oauth2/authorize?client_id=1284613721888526417&scope=bot+applications.commands&permissions=8", emoji=f"{emoji.link}")
        view.add_item(support)
        view.add_item(inv)

        embed = discord.Embed(title="", description=f"> **Myth** is the only **feature rich** bot that youre gonna need \n> Helping `{members:,}` users and `{guilds:,}` guilds \n> **Developed** by [lavalink](https://github.com/lavalink-dev) & [misimpression](https://github.com/misimpression)", color=color.default)
        embed.add_field(name="Stats", value=f"> Latency: `{latency}ms` \n> Lines: `{lines2}` \n> Commands: `{total_commands}` \n> Started: {uptime}", inline=True)
        embed.set_author(name=ctx.author.name, icon_url=user_pfp)
        embed.set_thumbnail(url=avatar_url)

        await ctx.send(embed=embed, view=view)
>>>>>>> 71080dd7efdc4274423477ec843378a8cdf70643:cogs/info.py
        
    @commands.command(
        description="Check a user's info", 
        aliases=["ui"]
    )
    async def userinfo(self, ctx: Context, member: discord.Member = None):
        if member is None:
            member = ctx.author

        user_data = await self.client.pool.fetchrow("""
            SELECT u.uid, i.name, i.footer, i.bio 
            FROM uids u 
            LEFT JOIN userinfo i ON u.user_id = i.user_id 
            WHERE u.user_id = $1
        """, member.id)

        uid = user_data['uid'] if user_data and user_data['uid'] is not None else "n/a"
        name = user_data['name'] if user_data and user_data['name'] else member.display_name
        footer = user_data['footer'] if user_data and user_data['footer'] else ""
        bio = user_data['bio'] if user_data and user_data['bio'] else ""

        user_pfp = member.avatar.url if member.avatar else member.default_avatar.url
        embed = discord.Embed(color=color.default)
        embed.set_author(name=f"{name} ({member.id})", icon_url=user_pfp)

        if bio:
            embed.description = f"> {bio}"

        if footer:
            embed.set_footer(text=footer)

        badges = []
        user = member

        if user.public_flags.hypesquad_balance:
            badges.append("<:balance:1291122370609676370>")
        if user.public_flags.hypesquad_bravery:
            badges.append("<:bravery:1291122449899061248>")
        if user.public_flags.hypesquad_brilliance:
            badges.append("<:brilliance:1291122354688102544>")
        if user.public_flags.early_supporter:
            badges.append("<:early:1291122492970111088>")
        if user.public_flags.active_developer:
            badges.append("<:activedev:1291122427094368348>")
        if user.id == 394152799799345152:
            badges.append("<:dev:1291123071498981436>")

        if member.premium_since:  
            badges.append("<:nitro:1291122409293742102>")
        if member.guild.premium_subscriber_role and member.guild.premium_subscriber_role in member.roles: 
            badges.append("<a:boost:1291122311944081531>")

        embed.add_field(name="Joined", value=f"> {format_dt(member.joined_at, style='D') if hasattr(member, 'joined_at') else 'n/a'} \n> {format_dt(member.joined_at, style='R') if member.joined_at else 'n/a'}", inline=True) # type: ignore
        embed.add_field(name="Created", value=f"> {format_dt(member.created_at, style='D') if hasattr(member, 'created_at') else 'n/a'} \n> {format_dt(member.created_at, style='R') if hasattr(member, 'created_at') else 'n/a'}", inline=True)
        embed.add_field(name="Extra", value=f"> **UID:** {uid} \n> **Badges:** {' '.join(badges) if badges else 'None'}", inline=True)
        
        if member:
            roles = [role.mention for role in member.roles[1:]]
            if len(roles) > 5:
                roles_display = ', '.join(roles[:5]) + f" + {len(roles) - 5} more"
            else:
                roles_display = ', '.join(roles) if roles else "n/a"

            embed.add_field(name="Roles", value=f"> {roles_display}", inline=False)

        await ctx.send(embed=embed)
        
    @commands.command(
        aliases=["serverinfo", "si"]
    )
    async def server(self, ctx: Context):
        guild = ctx.guild

        # boost
        boost = f"{guild.premium_subscription_count} (lvl {guild.premium_tier})" if guild.premium_subscription_count > 0 else "0" # type: ignore
        boosters = f"{guild.premium_subscription_count}" if guild.premium_subscription_count > 0 else "0" # type: ignore
        vanity = f".gg/{guild.vanity_url_code}" if guild.vanity_url_code else "None" # type: ignore

        # gen
        owner = guild.owner.mention # type: ignore 
        created_at = format_dt(guild.created_at, "F") # type: ignore
        guild_id = guild.id

        # misc
        emojis = len(guild.emojis) # type: ignore
        roles = len(guild.roles) # type: ignore
        stickers = len([sticker for sticker in guild.stickers if sticker.available]) # type: ignore
        max_emojis = guild.emoji_limit # type: ignore
        max_stickers = guild.sticker_limit # type: ignore

        # users
        humans = sum(not member.bot for member in guild.members) # type: ignore
        bots = sum(member.bot for member in guild.members) # type: ignore
        total_members = len(guild.members) # type: ignore

        # channel shit
        text_channels = len(guild.text_channels) # type: ignore
        voice_channels = len(guild.voice_channels) # type: ignore
        categories = len(guild.categories) # type: ignore

        # design
        banner = guild.banner.url if guild.banner else None # type: ignore
        pfp = guild.icon.url if guild.icon else None # type: ignore 
        splash = guild.splash.url if guild.splash else None # type: ignore

        # embed
        embed = discord.Embed(title=f"", color=color.default)
        icon_url = guild.icon.url if guild.icon else None # type: ignore
        embed.set_author(name=f"{guild.name} | serverinfo", icon_url=icon_url) # type: ignore
        
        embed.add_field(name=f"Boosts", value=f"> **Boosts:** `{boost}`\n> **Boosters:** `{boosters}`\n> **Vanity:** `{vanity}`", inline=True)
        embed.add_field(name="Misc", value=f"> **Emojis:** `{emojis}/{max_emojis}`\n> **Stickers:** `{stickers}/{max_stickers}`\n> **Roles:** `{roles}/250`", inline=True)
        embed.add_field(name="Members", value=f"> **Total:** `{total_members}`\n> **Humans:** `{humans}`\n> **Bots:** `{bots}`", inline=True)
        embed.add_field(name=f"Channels", value=f"> **Text:** `{text_channels}`\n> **Voice:** `{voice_channels}`\n> **Categories:** `{categories}`", inline=True)
        embed.add_field(name="General", value=f"> **Owner:** {owner}\n> **ID:** `{guild_id}`\n> **Created:** {created_at}", inline=True)
        embed.add_field(name=f"Design", value=f"> **Avatar:** {'[Here](' + pfp + ')' if pfp else 'n/a'}\n> **Banner:** {'[Here](' + banner + ')' if banner else 'n/a'}\n> **Splash:** {'[Here](' + splash + ')' if splash else 'n/a'}", inline=True)

        await ctx.send(embed=embed)

    @commands.command(
        description="Check a users avatar", 
        aliases=["av", "ava", "pfp"]
    )
    async def avatar(self, ctx: Context, user: User = None):
        if user is None:
            user = ctx.author
        elif isinstance(user, int):
            user = await self.client.fetch_user(user)

        avatar = user.avatar.url if user.avatar else 'https://none.none'
        embed = discord.Embed(color=color.default)
        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        embed.set_author(name=f"{ctx.author.name} | avatar", icon_url=user_pfp)
        embed.set_image(url=avatar)
        view = View()
        view.add_item(Button(label="Avatar", url=avatar, emoji=f"{emoji.link}"))
        if user.display_avatar:
            view.add_item(Button(label="Server Avatar", url=user.display_avatar.url, emoji=f"{emoji.link}"))
        await ctx.send(embed=embed, view=view)

    @commands.command(
        description="Check a users banner", 
        aliases=["bnner", "bnr", "bn"]
    )
    async def banner(self, ctx: Context, user: User = Author):
        try:
            user = await self.client.fetch_user(user.id) # type: ignore
            banner_url = user.banner.url if user.banner else None # type: ignore
        except discord.NotFound:
            banner_url = None

        embed = discord.Embed(color=color.default)
        if banner_url:
            embed.set_image(url=banner_url)
            user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
            embed.set_author(name=f"{ctx.author.name} | banner", icon_url=user_pfp)
            view = View()
            view.add_item(Button(label="Banner", url=banner_url, emoji=f"{emoji.link}"))
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.deny(f"{ctx.author.mention} **does not** have a banner")

    @commands.command(
        description="Check the server avatar", 
        aliases=["sa", "servericon"]
    )
    async def serveravatar(self, ctx: Context):
        if ctx.guild:
            if ctx.guild.icon:
                icon_url = ctx.guild.icon.url
                embed = discord.Embed(color=color.default)
                embed.set_image(url=icon_url)
                user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                embed.set_author(name=f"{ctx.author.name} | server avatar", icon_url=user_pfp)
                view = View()
                view.add_item(Button(style=discord.ButtonStyle.url, label="Server Avatar", url=icon_url, emoji=f"{emoji.link}"))
                await ctx.send(embed=embed, view=view)
            else:
                await ctx.deny(f"`{ctx.guild.name}` **does not** have an avatar")

    @commands.command(
        description="Check the server banner", 
        aliases=["sb"]
    )
    async def serverbanner(self, ctx: Context):
        if ctx.guild:
            if ctx.guild.banner:
                banner_url = ctx.guild.banner.url
                embed = discord.Embed(color=color.default)
                embed.set_image(url=banner_url)
                user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                embed.set_author(name=f"{ctx.author.name} | server banner", icon_url=user_pfp)
                view = View()
                view.add_item(Button(style=discord.ButtonStyle.url, label="Server Banner", url=banner_url, emoji=f"{emoji.link}"))
                await ctx.send(embed=embed, view=view)
            else:
                await ctx.deny(f"`{ctx.guild.name}` **does not** have a banner")

    @commands.command(
        description="Check banned users", 
        aliases=["banlist"]
    )
    @commands.has_permissions(ban_members=True)
    async def bans(self, ctx: Context):
        banned_users = [ban async for ban in ctx.guild.bans()] # type: ignore
        banned_list = [f"> {ban_entry.user.mention} - {ban_entry.reason or 'No reason'}" for ban_entry in banned_users] or ["> None"]

        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        pages = [
            discord.Embed(description='\n'.join(banned_list[i:i + 10]), color=color.default).set_author(name=f"{ctx.author.name} | Everyone banned", icon_url=user_pfp)
            for i in range(0, len(banned_list), 10)
        ]

        if len(pages) > 1:
            await ctx.paginate(pages)
        else:
            await ctx.send(embed=pages[0])

    @commands.command(
        description="Check users who boosted", 
        aliases=["boosts"]
    )
    async def boosters(self, ctx: Context):
        boosters = ctx.guild.premium_subscribers # type: ignore
        booster_list = [f"> {booster.mention}" for booster in boosters] or ["> None"]

        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        pages = [
            discord.Embed(description='\n'.join(booster_list[i:i + 10]), color=color.default).set_author(name=f"{ctx.author.name} | Everyone who boosted", icon_url=user_pfp)
            for i in range(0, len(booster_list), 10)
        ]

        if len(pages) > 1:
            await ctx.paginate(pages)
        else:
            await ctx.send(embed=pages[0])

    @commands.command(
        description="Check all bots in the server"
    )
    async def bots(self, ctx: Context):
        bots = [member for member in ctx.guild.members if member.bot] # type: ignore
        bot_list = [f"> {bot.mention}" for bot in bots] or ["> None"]

        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        pages = [
            discord.Embed(description='\n'.join(bot_list[i:i + 10]), color=color.default).set_author(name=f"{ctx.author.name} | Every bot", icon_url=user_pfp)
            for i in range(0, len(bot_list), 10)
        ]

        if len(pages) > 1:
            await ctx.paginate(pages)
        else:
            await ctx.send(embed=pages[0])
            
    @commands.command(
        description="Check all users in a role"
    )
    async def inrole(self, ctx: Context, role: discord.Role):
        members_with_role = [f"> {member.mention}" for member in ctx.guild.members if role in member.roles] # type: ignore
        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url

        if members_with_role:
            pages = []
            for i in range(0, len(members_with_role), 10):
                embed = discord.Embed(description='\n'.join(members_with_role[i:i + 10]), color=color.default)
                embed.set_author(name=f"{ctx.author.name} | People inrole: {role.name}", icon_url=user_pfp)
                pages.append(embed)

            if len(pages) > 1:
                await ctx.paginate(pages)
            else:
                await ctx.send(embed=pages[0])
        else:
            await ctx.deny(f"**None** is in role with the role: {role.mention}")

    @commands.command(
        description="Check all emojis in the server"
    )
    async def emojis(self, ctx: Context):
        emojis = ctx.guild.emojis # type: ignore
        emoji_list = [f"> {emoji} ({emoji.id})" for emoji in emojis] or ["> None"]

        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        pages = [
            discord.Embed(description='\n'.join(emoji_list[i:i + 10]), color=color.default)
            .set_author(name=f"{ctx.author.name} | Every emoji", icon_url=user_pfp)
            for i in range(0, len(emoji_list), 10)
        ]

        if len(pages) > 1:
            await ctx.paginate(pages)
        else:
            await ctx.send(embed=pages[0])

    @commands.command(
        description="Check all roles in the server"
    )
    async def roles(self, ctx: Context):
        roles = [role for role in ctx.guild.roles if role.name != "@everyone"] # type: ignore
        role_list = [f"> {role.mention}" for role in roles] or ["> None"]

        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        pages = [
            discord.Embed(description='\n'.join(role_list[i:i + 10]), color=color.default)
            .set_author(name=f"{ctx.author.name} | Every role", icon_url=user_pfp)
            for i in range(0, len(role_list), 10)
        ]

        if len(pages) > 1:
            await ctx.paginate(pages)
        else:
            await ctx.send(embed=pages[0])

    @commands.command(
        description="Check your join position", 
        aliases=["joinpos"]
    )
    async def joinposition(self, ctx: Context):
        join_position = (sorted(ctx.guild.members, key=lambda m: m.joined_at).index(ctx.author) + 1) # type: ignore
        await ctx.invisible(f"You joined **{join_position}** that's a really cool position :sunglasses:")

    @commands.command(
        description="Get info on a role", 
        aliases=["ri"]
    )
    async def roleinfo(self, ctx, *, role: discord.Role):
        guild = ctx.guild

        name = role.name
        id = role.id
        color = role.color
        created = format_dt(role.created_at, "F")
        position = role.position

        role_members = [member.mention for member in role.members]
        member_count = len(role_members)

        if member_count > 10:
            displayed = ", ".join(role_members[:10]) + ", + more"
        else:
            displayed = ", ".join(role_members) if role_members else "n/a"

        permissions = ", ".join(perm.replace('_', ' ').title() for perm, value in role.permissions if value)

        embed = discord.Embed(color=color)
        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        embed.set_author(name=f"{ctx.author.name} | roleinfo - {name}", icon_url=user_pfp)
        
        embed.add_field(name="General", value=f"> **ID:** `{id}` \n> **Color:** `{color}` \n> **Position:** `{position}/{len(guild.roles)}`", inline=True)
        embed.add_field(name="Created", value=f"> {created}", inline=False)
        embed.add_field(name="Members with the role", value=f"> {displayed}", inline=True)

        if permissions:
            embed.add_field(name="Permissions", value=f"> {permissions}", inline=True)
        else:
            embed.add_field(name="Permissions", value="> n/a", inline=True)

        await ctx.send(embed=embed)

    @commands.command(
        description="Get info on a channel", 
        aliases=["ci"]
    )
    async def channelinfo(self, ctx, channel: Optional[discord.TextChannel] = None):
        channel = channel or ctx.channel

        category = channel.category.name if channel.category else "None"
        name = channel.name
        id = channel.id
        created = format_dt(channel.created_at, 'R')
        nsfw = channel.is_nsfw()
        slowmode = channel.slowmode_delay
        
        embed = discord.Embed(color=color.default)
        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        embed.set_author(name=f"{ctx.author.name} | channelinfo - {name}", icon_url=user_pfp)
        
        embed.add_field(name="General", value=f"> **ID:** `{id}` \n> **Category:** `{category}` \n> **Slowmode:** `{slowmode}` \n> **NSFW:** `{nsfw}`", inline=False)
        embed.add_field(name="Created", value=f"> {created}", inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(
        description="Check for the yougest user in the server"
    )
    async def youngest(self, ctx):
        youngest = sorted(ctx.guild.members, key=lambda m: m.created_at, reverse=True)[0]
        account_age = format_dt(youngest.created_at, 'F')
        account_age2 = format_dt(youngest.created_at, 'R')
        await ctx.invisible(f"The youngest user in the server is {youngest.mention}, who created their account {account_age2} ({account_age})")

    @commands.command(
        description="Check for the oldest user in the server"
    )
    async def oldest(self, ctx):
        oldest = sorted(ctx.guild.members, key=lambda m: m.created_at)[0]
        account_age = format_dt(oldest.created_at, 'F')
        account_age2 = format_dt(oldest.created_at, 'R')
        await ctx.invisible(f"The oldest member in the server is {oldest.mention}, who created their account {account_age2} ({account_age})")

    @commands.command(
        description="Check how many invites you have in the server"
    )
    async def invites(self, ctx, user: Member = Author):
        user = user or ctx.author 
        invites = await ctx.guild.invites()
        allinvites = sum(invite.uses for invite in invites if invite.inviter == user)
        await ctx.invisible(f"You invited `{allinvites}` people")

    @commands.command(
        description="Check all shards of the bot"
    )
    async def shards(self, ctx):
        embed = discord.Embed(description=f"> Shard count: `{self.client.shard_count}`", color=color.default)
        user_pfp = ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
        embed.set_author(name=f"{ctx.author.name} | shards", icon_url=user_pfp)

        guilds = 0
        users = 0

        for shard_id in range(self.client.shard_count):
            shard = self.client.get_shard(shard_id)
            guilds_shard = sum(1 for g in self.client.guilds if g.shard_id == shard_id)
            users_shard = sum(g.member_count for g in self.client.guilds if g.shard_id == shard_id)

            guilds += guilds_shard
            users += users_shard

            embed.add_field(name=f"Shard: {shard_id}", value=f"> Guilds: `{guilds_shard}`\n> Users: `{users_shard:,}`", inline=True)

        await ctx.send(embed=embed)

    @commands.command(
        description="Check the total member count",
        aliases=["mc"]
    )
    async def membercount(self, ctx):
        if ctx.guild:
            all = ctx.guild.member_count
            humans = sum(1 for member in ctx.guild.members if not member.bot)
            bots = all - humans

            embed = discord.Embed(description=f"> **All:** `{str(all)}` \n> **Humans:** `{str(humans)}` \n> **Bots:** `{str(bots)}`", color=color.default)
            icon_url = ctx.guild.icon.url if ctx.guild.icon else None
            embed.set_author(name=f"{ctx.guild.name} | membercount", icon_url=icon_url)
            await ctx.send(embed=embed)
            
async def setup(client):
    await client.add_cog(Information(client))
