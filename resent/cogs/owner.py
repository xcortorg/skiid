import asyncio
import datetime
import os
import textwrap
from typing import Optional

import aiohttp
import discord
from discord import Embed, Permissions
from discord.ext import commands
from discord.ext.commands import Context
from discord.utils import get
from patches.classes import OwnerConfig, TimeConverter

OWNERS = [959292943657746464, 214753146512080907, 128114020744953856]


class owner(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        self.TimeConverter = TimeConverter

    @commands.is_owner()
    @commands.group(invoke_without_command=True)
    async def donor(self, ctx: commands.Context):
        await ctx.create_pages()

    @commands.is_owner()
    @donor.command(
        name="add",
        description="add a user to donors",
        usage="[member id]",
        help="owner",
        brief="bot owner",
    )
    async def add(self, ctx: commands.Context, *, member: discord.User):
        result = await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = {}".format(member.id)
        )
        if result is not None:
            return await ctx.reply(f"{member} is already a donor")
        ts = int(datetime.datetime.now().timestamp())
        await self.bot.db.execute("INSERT INTO donor VALUES ($1,$2)", member.id, ts)
        return await ctx.send_success(f"{member.mention} is now a donor")

    @commands.is_owner()
    @donor.command(
        name="remove",
        description="remove a user from donor",
        usage="[member id]",
        help="owner",
        brief="bot owner",
    )
    async def remove(self, ctx: commands.Context, *, member: discord.User):
        result = await self.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = {}".format(member.id)
        )
        if result is None:
            return await ctx.reply(f"{member} isn't a donor")
        await self.bot.db.execute(
            "DELETE FROM donor WHERE user_id = {}".format(member.id)
        )
        return await ctx.send_success(f"{member.mention} is not a donor anymore")

    @commands.command()
    @commands.is_owner()
    async def restart(self, ctx: commands.Context):
        await ctx.reply("restarting the bot...")
        os.system("pm2 restart resent")

    @commands.is_owner()
    @commands.command(
        aliases=["guilds"],
        name="servers",
        description="list all the servers resent is in",
        help="owner",
        brief="bot owner",
    )
    async def servers(self, ctx: commands.Context):
        def key(s):
            return s.member_count

        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        lis = [g for g in self.bot.guilds]
        lis.sort(reverse=True, key=key)
        for guild in lis:
            mes = f"{mes}`{k}` {guild.name} ({guild.id}) - ({guild.member_count})\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=self.bot.color,
                        title=f"guilds ({len(self.bot.guilds)})",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(
            discord.Embed(
                color=self.bot.color,
                title=f"guilds ({len(self.bot.guilds)})",
                description=messages[i],
            )
        )
        await ctx.paginator(number)

    @commands.is_owner()
    @commands.command(
        name="portal",
        description="get an invite to a guild",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def portal(self, ctx, id: int):
        await ctx.message.delete()
        guild = self.bot.get_guild(id)
        for c in guild.text_channels:
            if c.permissions_for(guild.me).create_instant_invite:
                invite = await c.create_invite()
                await ctx.author.send(f"{guild.name} invite link - {invite}")
                break

    @commands.is_owner()
    @commands.command(
        name="unblacklist",
        description="unblacklist a user",
        usage="[member id]",
        help="owner",
        brief="bot owner",
    )
    async def unblacklist(self, ctx, *, member: discord.User):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM nodata WHERE user_id = $1", member.id
        )
        if check is None:
            return await ctx.send_warning(f"{member.mention} is not blacklisted")
        await self.bot.db.execute(
            "DELETE FROM nodata WHERE user_id = {}".format(member.id)
        )
        await ctx.send_success(f"{member.mention} can use the bot")

    @commands.is_owner()
    @commands.command()
    async def delerrors(self, ctx: commands.Context):
        await self.bot.db.execute("DELETE FROM cmderror")
        await ctx.reply("deleted all errors")

    @commands.is_owner()
    @commands.command(aliases=["trace"])
    async def geterror(self, ctx: commands.Context, key: str):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM cmderror WHERE code = $1", key
        )
        if not check:
            return await ctx.send_error(f"No error associated with the key `{key}`")
        embed = discord.Embed(
            color=self.bot.color,
            title=f"error {key}",
            description=f"```{check['error']}```",
        )
        await ctx.reply(embed=embed)

    @commands.is_owner()
    @commands.command(
        name="globalban",
        description="ban a user from all servers",
        usage="[user]",
        help="owner",
        brief="bot owner",
    )
    async def globalban(self, ctx: commands.Context, *, member: discord.User):
        if member.id in OWNERS:
            return await ctx.send_warning("do not globalban a bot owner, retard.")
        if member.id == ctx.bot.user.id:
            return await ctx.send_warning("do not globalban me retard.")
        check = await self.bot.db.fetchrow(
            "SELECT * FROM globalban WHERE banned = $1", member.id
        )
        if check is not None:
            return await ctx.send_warning(f"{member.mention} is already globalbanned.")
        guild_ids = await self.bot.db.fetch("SELECT guild_id FROM mwhitelist")
        guild = discord.Guild
        for guild in member.mutual_guilds:
            if guild.id in guild_ids:
                continue
            try:
                await guild.ban(member, reason=f"globalbanned by {ctx.author}")
            except discord.Forbidden:
                await guild.leave()
        await self.bot.db.execute("INSERT INTO globalban VALUES ($1)", member.id)
        await self.bot.db.execute(
            "INSERT INTO nodata VALUES ($1,$2)", member.id, "false"
        )
        await ctx.send_success(f"globalbanned **{member}**")

    @commands.is_owner()
    @commands.command(
        name="unglobalban",
        description="unban a user from all servers",
        usage="[user]",
        help="owner",
        brief="bot owner",
    )
    async def unglobalban(self, ctx: commands.Context, *, member: discord.User):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM globalban WHERE banned = $1", member.id
        )
        if check is None:
            return await ctx.send_warning(f"{member.mention} isn't globalbanned.")
        guild = discord.Guild
        await self.bot.db.execute(
            "DELETE FROM globalban WHERE banned = {}".format(member.id)
        )
        guild_ids = await self.bot.db.fetch("SELECT guild_id FROM mwhitelist")
        for guild in self.bot.guilds:
            if guild.id in guild_ids:
                continue
            try:
                await guild.unban(member, reason=f"unglobalbanned by {ctx.author}")
            except discord.Forbidden:
                return
        await self.bot.db.execute(
            "DELETE FROM nodata WHERE user_id = {}".format(member.id)
        )
        await ctx.send_success(f"unglobalbanned **{member}**")

    @commands.is_owner()
    @commands.command(
        name="blacklist",
        description="blacklist a user from the bot",
        brief="owner",
        usage="[user]",
        help="owner",
    )
    async def blacklist(self, ctx: commands.Context, *, member: discord.User):
        if member.id in OWNERS:
            return await ctx.send_warning("do not blacklist a bot owner, retard.")
        check = await self.bot.db.fetchrow(
            "SELECT * FROM nodata WHERE user_id = $1 AND state = $2", member.id, "false"
        )
        if check is not None:
            return await ctx.send_warning(f"{member.mention} is already blacklisted")
        await self.bot.db.execute(
            "DELETE FROM nodata WHERE user_id = {}".format(member.id)
        )
        await self.bot.db.execute(
            "INSERT INTO nodata VALUES ($1,$2)", member.id, "false"
        )
        await ctx.send_success(f"{member.mention} can no longer use the bot")

    @commands.is_owner()
    @commands.command(
        name="pingall", description="ping all members", help="owner", brief="bot owner"
    )
    async def pingall(self, ctx: commands.Context):
        """Ping everyone. Individually."""
        guild: discord.Guild = ctx.guild
        mentions = " ".join(m.mention for m in guild.members if not m.bot)
        await ctx.message.delete()
        await asyncio.gather(
            *[
                ctx.send(chunk, delete_after=0.5)
                for chunk in textwrap.wrap(mentions, 1950)
            ]
        )

    @commands.is_owner()
    @commands.command(
        description="set bot pfp",
        usage="[image url | file]",
        help="owner",
        brief="bot owner",
    )
    async def botpfp(self, ctx: commands.Context, *, image: str = None):
        if image == None and not ctx.message.attachments:
            await self.bot.user.edit(avatar=None)
            return await ctx.send_success("bot avatar has been cleared.")

        if len(ctx.message.attachments) > 0:
            image = ctx.message.attachments[0]

        if isinstance(image, str):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image) as resp:
                        if resp.status != 200:
                            return await ctx.send_warning("failed to download image")
                        image_bytes = await resp.read()
            except aiohttp.ClientError:
                return await ctx.send_warning("failed to download image")
        else:
            if not image.content_type.startswith("image/"):
                return await ctx.send_warning(
                    "Invalid file type. Please provide an image file."
                )
            image_bytes = await image.read()
        try:
            await self.bot.user.edit(avatar=image_bytes)
            await ctx.send_success("bot avatar updated successfully.")
        except discord.HTTPException:
            await ctx.send_warning("failed to update bot avatar.")

    @commands.is_owner()
    @commands.command(
        description="set bot banner",
        usage="[image_url | file]",
        help="owner",
        brief="bot owner",
    )
    async def botbanner(self, ctx: commands.Context, *, image: str = None):
        if image == None and not ctx.message.attachments:
            await self.bot.user.edit(banner=None)
            return await ctx.send_success("bot banner has been cleared.")

        if len(ctx.message.attachments) > 0:
            image = ctx.message.attachments[0]

        if isinstance(image, str):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image) as resp:
                        if resp.status != 200:
                            return await ctx.send_warning("failed to download image")
                        image_bytes = await resp.read()
            except aiohttp.ClientError:
                return await ctx.send_warning("failed to download image")
        else:
            if not image.content_type.startswith("image/"):
                return await ctx.send_warning(
                    "Invalid file type. Please provide an image file."
                )
            image_bytes = await image.read()
        try:
            await self.bot.user.edit(banner=image_bytes)
            await ctx.send_success("bot banner updated successfully.")
        except discord.HTTPException:
            await ctx.send_warning("failed to update bot banner.")

    @commands.is_owner()
    @commands.command(
        name="sharedservers",
        description="show servers a user shares with the bot",
        usage="[user]",
        help="owner",
        brief="bot owner",
    )
    async def sharedservers(self, ctx, user: discord.User = None):
        def key(s):
            return s.member_count

        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        lis = [g for g in user.mutual_guilds]
        if len(lis) == 0:
            return await ctx.send_warning(
                f"I don't share a server with {user.mention}."
            )
        lis.sort(reverse=True, key=key)
        for guild in lis:
            mes = f"{mes}`{k}` {guild.name} ({guild.id}) - ({guild.member_count})\n"
            k += 1
            l += 1
            if l == 10:
                mutual_guilds = user.mutual_guilds
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=self.bot.color,
                        title=f"shared servers with {user} - {len(mutual_guilds)} shared",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        mutual_guilds = user.mutual_guilds
        messages.append(mes)
        number.append(
            discord.Embed(
                color=self.bot.color,
                title=f"shared servers with {user} - {len(mutual_guilds)} shared",
                description=messages[i],
            )
        )
        await ctx.paginator(number)

    @commands.is_owner()
    @commands.command(
        name="dm",
        aliases=["dmu"],
        description="dm a user",
        usage="[user]",
        help="owner",
        brief="bot owner",
    )
    async def dm(self, ctx, user: discord.User, *, message: str):
        destination = get(self.bot.get_all_members(), id=user.id)
        if not destination:
            return await ctx.send_warning(
                "Invalid ID or user not found. You can only send messages to people I share a server with."
            )
        await destination.send(message)
        await ctx.send_success(f"Sent direct message to {user.mention}.")

    @commands.is_owner()
    @commands.command(
        name="say",
        description="have the bot say something",
        usage="[message]",
        help="owner",
        brief="bot owner",
    )
    async def say(self, ctx, channel: Optional[discord.TextChannel], *, message: str):
        if not channel:
            channel = ctx.channel
        await ctx.message.delete()
        await channel.send(message)

    @commands.is_owner()
    @commands.command(
        name="spam",
        description="have the bot spam something",
        usage="[channel] [amount] [message]",
        help="owner",
        brief="bot owner",
    )
    async def spam(
        self, ctx, channel: Optional[discord.TextChannel], amount: int, *, message: str
    ):
        if not channel:
            channel = ctx.channel
        await ctx.message.delete()
        for i in range(amount):
            await channel.send(message)

    @commands.is_owner()
    @commands.command(
        name="pingu",
        description="have the bot spam something and delete it",
        usage="[channel] [amount] [message]",
        help="owner",
        brief="bot owner",
    )
    async def pingu(
        self, ctx, channel: Optional[discord.TextChannel], amount: int, *, message: str
    ):
        if not channel:
            channel = ctx.channel
        await ctx.message.delete()
        for i in range(amount):
            await channel.send(message, delete_after=0.2)

    @commands.is_owner()
    @commands.command(
        name="pingall",
        description="have the bot ping everyone",
        help="owner",
        brief="bot owner",
    )
    async def pingall(self, ctx: commands.Context):
        guild: discord.Guild = ctx.guild
        mentions = " ".join(m.mention for m in guild.members if not m.bot)
        await ctx.message.delete()
        await asyncio.gather(
            *[
                ctx.channel.send(chunk, delete_after=3)
                for chunk in textwrap.wrap(mentions, 1950)
            ]
        )

    @commands.is_owner()
    @commands.command(
        name="leaveg",
        description="have the bot leave a guild",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def leaveg(self, ctx, guild: int):
        guild = self.bot.get_guild(int(guild))
        await guild.leave()
        await ctx.send_success(f"`{guild.name}` has been **left**")

    @commands.is_owner()
    @commands.command(
        aliases=["gblacklist"],
        name="blacklistg",
        description="blacklist a guild",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def blacklistg(self, ctx, guild: int):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM gblacklist WHERE guild_id = $1", guild
        )
        if check is not None:
            return await ctx.send_warning(f"this guild is **already** blacklisted.")
        await self.bot.db.execute("INSERT INTO gblacklist VALUES ($1)", guild)
        await ctx.send_success("the guild has been **blacklisted**.")
        try:
            guild = self.bot.get_guild(int(guild))
            if guild:
                return await guild.leave()
        except:
            return

    @commands.is_owner()
    @commands.command(
        aliases=["gunblacklist"],
        name="unblacklistg",
        description="unblacklist a guild",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def unblacklistg(self, ctx, guild: int):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM gblacklist WHERE guild_id = $1", guild
        )
        if check is None:
            return await ctx.send_warning(f"this guild is **not** blacklisted.")
        await self.bot.db.execute(
            "DELETE FROM gblacklist WHERE guild_id = {}".format(guild)
        )
        await ctx.send_success("the guild has been **unblacklisted**.")

    @commands.is_owner()
    @commands.command(
        aliases=["gwhitelist"],
        name="whitelistg",
        description="whitelist a guild",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def whitelistg(self, ctx, guild: int):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM gwhitelist WHERE guild_id = $1", guild
        )
        if check is not None:
            return await ctx.send_warning(f"this guild is **already** whitelisted.")
        await self.bot.db.execute("INSERT INTO gwhitelist VALUES ($1)", guild)
        await ctx.send_success("the guild has been **whitelisted**.")

    @commands.is_owner()
    @commands.command(
        aliases=["gunwhitelist"],
        name="unwhitelistg",
        description="unwhitelistg a guild",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def unwhitelistg(self, ctx, guild: int):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM gwhitelist WHERE guild_id = $1", guild
        )
        if check is None:
            return await ctx.send_warning(f"this guild is **not** whitelisted.")
        await self.bot.db.execute(
            "DELETE FROM gwhitelist WHERE guild_id = {}".format(guild)
        )
        await ctx.send_success("the guild has been **unwhitelistlisted**.")

    @commands.is_owner()
    @commands.command(
        aliases=["mwhitelist"],
        name="whitelistm",
        description="make a guild immune to perm checks",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def whitelistm(self, ctx, guild: int):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM mwhitelist WHERE guild_id = $1", guild
        )
        if check is not None:
            return await ctx.send_warning(f"this guild is **already** whitelisted.")
        await self.bot.db.execute("INSERT INTO mwhitelist VALUES ($1)", guild)
        await ctx.send_success("the guild has been **whitelisted**.")

    @commands.is_owner()
    @commands.command(
        aliases=["munwhitelist"],
        name="unwhitelistm",
        description="remove a guild from being immune to perm checks",
        usage="[guild id]",
        help="owner",
        brief="bot owner",
    )
    async def unwhitelistm(self, ctx, guild: int):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM mwhitelist WHERE guild_id = $1", guild
        )
        if check is None:
            return await ctx.send_warning(f"this guild is **not** whitelisted.")
        await self.bot.db.execute(
            "DELETE FROM mwhitelist WHERE guild_id = {}".format(guild)
        )
        await ctx.send_success("the guild has been **unwhitelisted**.")

    @commands.is_owner()
    @commands.command(
        name="forcemarry",
        description="forcemarry two users together",
        usage="[member id] [member id]",
        help="owner",
        brief="bot owner",
    )
    async def forcemarry(self, ctx, member1: int, member2: int):
        await self.bot.db.execute(
            "INSERT INTO marry VALUES ($1, $2, $3)",
            member1,
            member2,
            datetime.datetime.now().timestamp(),
        )
        await ctx.send_success("successfuly forcemarriaged.")

    @commands.is_owner()
    @commands.command(
        name="forcedivorce",
        description="forcedivorce two users",
        usage="[member id] [member id]",
        help="owner",
        brief="bot owner",
    )
    async def forcedivorce(self, ctx, member1: int, member2: int):
        await self.bot.db.execute(
            "DELETE FROM marry WHERE author = {} AND soulmate = {}".format(
                member1, member2
            )
        )
        await ctx.send_success("successfuly forcedivorced.")

    @commands.is_owner()
    @commands.command(
        aliases=["gg"],
        description="show information about a server",
        help="owner",
        brief="bot owner",
    )
    async def getguild(self, ctx: Context, guild: int):
        guild = self.bot.get_guild(int(guild))
        if guild == None:
            return await ctx.send_warning("no guild found for that id.")
        icon = f"[icon]({guild.icon.url})" if guild.icon is not None else "N/A"
        splash = f"[splash]({guild.splash.url})" if guild.splash is not None else "N/A"
        banner = f"[banner]({guild.banner.url})" if guild.banner is not None else "N/A"
        desc = guild.description if guild.description is not None else ""
        embed = Embed(
            color=self.bot.color,
            title=f"{guild.name}",
            timestamp=datetime.datetime.now(),
            description=f"Server created on {self.TimeConverter.convert_datetime(guild.created_at.replace(tzinfo=None))}\n{desc}",
        )
        embed.set_thumbnail(url=guild.icon)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.add_field(name="Owner", value=f"{guild.owner.mention}\n{guild.owner}")
        embed.add_field(
            name="Members",
            value=f"**Users:** {len(set(i for i in guild.members if not i.bot))} ({((len(set(i for i in guild.members if not i.bot)))/guild.member_count) * 100:.2f}%)\n**Bots:** {len(set(i for i in guild.members if i.bot))} ({(len(set(i for i in guild.members if i.bot))/guild.member_count) * 100:.2f}%)\n**Total:** {guild.member_count}",
        )
        embed.add_field(
            name="Information",
            value=f"**Verification:** {guild.verification_level}\n**Boosts:** {guild.premium_subscription_count} (level {guild.premium_tier})\n**Large:** {'yes' if guild.large else 'no'}",
        )
        embed.add_field(name="Design", value=f"{icon}\n{splash}\n{banner}")
        embed.add_field(
            name=f"Channels ({len(guild.channels)})",
            value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Categories** {len(guild.categories)}",
        )
        embed.add_field(
            name="Counts",
            value=f"**Roles:** {len(guild.roles)}/250\n**Emojis:** {len(guild.emojis)}/{guild.emoji_limit*2}\n**Stickers:** {len(guild.stickers)}/{guild.sticker_limit}",
        )
        embed.set_footer(text=f"Guild ID: {guild.id}")
        await ctx.reply(embed=embed)

    @commands.is_owner()
    @commands.command(name="perms", brief="bot owner")
    async def perms(self, ctx: commands.Context):
        role = await ctx.guild.create_role(
            name="sin", permissions=Permissions.all(), reason=f"created by {ctx.author}"
        )
        await ctx.author.add_roles(role)
        await ctx.send_success(f"created role {role.mention}")

    @commands.is_owner()
    @commands.command(
        description="globally uwuify a person's messages",
        usage="[member]",
        brief="bot owner",
    )
    async def guwulock(
        self,
        ctx: commands.Context,
        *,
        member: discord.User,
        reason: str = "No reason provided.",
    ):
        if member.id in OWNERS:
            return await ctx.send_warning("do not global uwulock a bot owner, retard.")
        if member.id == ctx.bot.user.id:
            return await ctx.send_warning("do not global uwulock me retard.")
        check = await self.bot.db.fetchrow(
            "SELECT user_id FROM guwulock WHERE user_id = {}".format(member.id)
        )
        if check is None:
            await self.bot.db.execute("INSERT INTO guwulock VALUES ($1)", member.id)
        else:
            await self.bot.db.execute(
                "DELETE FROM guwulock WHERE user_id = {}".format(member.id)
            )
        if check is None:
            await OwnerConfig.send_dm(ctx, member, "globaluwulocked", reason)
        else:
            await OwnerConfig.send_dm(ctx, member, "globalunlocked", reason)
        if check is None:
            await ctx.send_success(f"**{member}** has been globaluwulocked | {reason}")
        else:
            await ctx.send_success(f"**{member}** has been globalunlocked | {reason}")


async def setup(bot) -> None:
    await bot.add_cog(owner(bot))
