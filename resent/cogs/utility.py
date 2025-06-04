import asyncio
import datetime
import os
from io import BytesIO
from typing import Union

import arrow
import discord
import humanfriendly
import uwuipy
from aiogtts import aiogTTS
from deep_translator import GoogleTranslator
from discord import Embed, File, Member, Role, TextChannel, User
from discord.ext import commands
from discord.ext.commands import AutoShardedBot as Bot
from discord.ext.commands import Cog, Context
from events.tasks import bday_task, is_there_a_reminder, reminder_task
from patches.classes import LastFMHandler as Handler
from patches.classes import TimeConverter, Timezone
from utils.permissions import Permissions

DISCORD_API_LINK = "https://discord.com/api/invite/"


class utility(commands.Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.tz = Timezone(self.bot)
        self.lastfmhandler = Handler("43693facbb24d1ac893a7d33846b15cc")
        self.cake = "🎂"
        self.weather_key = "64581e6f1d7d49ae834142709230804"
        self.a = TimeConverter

    async def bday_send(self, ctx: Context, message: str) -> discord.Message:
        return await ctx.reply(
            embed=discord.Embed(
                color=self.bot.color,
                description=f"{self.cake} {ctx.author.mention}: {message}",
            )
        )

    async def do_again(self, url: str):
        re = await self.make_request(url)
        if re["status"] == "converting":
            return await self.do_again(url)
        elif re["status"] == "failed":
            return None
        else:
            return tuple([re["url"], re["filename"]])

    async def make_request(self, url: str, action: str = "get", params: dict = None):
        r = await self.bot.session.get(url, params=params)
        if action == "get":
            return await r.json()
        if action == "read":
            return await r.read()

    @Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        bday_task.start(self.bot)
        reminder_task.start(self.bot)

    def convert_datetime(self, date: datetime.datetime = None):
        if date is None:
            return None
        month = f"0{date.month}" if date.month < 10 else date.month
        day = f"0{date.day}" if date.day < 10 else date.day
        year = date.year
        minute = f"0{date.minute}" if date.minute < 10 else date.minute
        if date.hour < 10:
            hour = f"0{date.hour}"
            meridian = "AM"
        elif date.hour > 12:
            hour = f"0{date.hour - 12}" if date.hour - 12 < 10 else f"{date.hour - 12}"
            meridian = "PM"
        else:
            hour = date.hour
            meridian = "PM"
        return f"{month}/{day}/{year} at {hour}:{minute} {meridian} ({discord.utils.format_dt(date, style='R')})"

    @commands.command(
        description="show user information",
        help="utility",
        usage="<user>",
        aliases=["whois", "ui", "user"],
    )
    async def userinfo(self, ctx: Context, *, member: Union[Member, User] = None):
        await ctx.typing()
        if member is None:
            member = ctx.author
        user = await self.bot.fetch_user(member.id)
        badges = []
        if user.id in self.bot.owner_ids:
            badges.append("<a:developer:1208257462549880913>")
        if user.public_flags.active_developer:
            badges.append("<:activedev:1208463590336503880>")
        if user.public_flags.early_supporter:
            badges.append("<:early:1208465674318647306>")
        if user.public_flags.verified_bot_developer:
            badges.append("<:developer:1208463282814455959>")
        if user.public_flags.staff:
            badges.append("<:tl_staff:1208466222791000094>")
        if user.public_flags.bug_hunter:
            badges.append("<:bughunter:1208466356274470997>")
        if user.public_flags.bug_hunter_level_2:
            badges.append("<:bughunter1:1192460270753284136>")
        if user.public_flags.partner:
            badges.append("<:partner:1208463582925426791>")

        # CUSTOM BADGES
        if user.id == 987183275560820806:
            badges.append("<a:odecy:1220454736906682468>")  # - odecy
        if user.id == 926419256785109013:
            badges.append("<:fwHuggies:1224620621217140797>")  # - angie
        if user.id == 1219003112874967250:
            badges.append("<:Apandi:1224620924167393330>")  # - rofl

        for guild in self.bot.guilds:
            mem = guild.get_member(user.id)
            if mem is not None:
                if mem.premium_since is not None:
                    badges.append("<:boosts:1208463280918765688>")
                    break

        async def tz_find(mem: discord.Member):
            if await self.tz.timezone_request(mem):
                return f"{self.tz.clock} Current time: {await self.tz.timezone_request(mem)}"
            return ""

        async def lf(mem: Union[Member, User]):
            check = await self.bot.db.fetchrow(
                "SELECT username FROM lastfm WHERE user_id = {}".format(mem.id)
            )
            if check is not None:
                u = str(check["username"])
                if u != "error":
                    a = await self.lastfmhandler.get_tracks_recent(u, 1)
                    return f"<:lastfm:1208398661961130064> Listening to [{a['recenttracks']['track'][0]['name']}]({a['recenttracks']['track'][0]['url']}) by **{a['recenttracks']['track'][0]['artist']['#text']}** on LastFM."

            return ""

        def vc(mem: Member):
            if mem.voice:
                channelname = mem.voice.channel.name
                deaf = (
                    "<:deafened:1208464929028575284>"
                    if mem.voice.self_deaf or mem.voice.deaf
                    else "<:undeafened:1208464410725715998>"
                )
                mute = (
                    "<:muted:1208464412571344900>"
                    if mem.voice.self_mute or mem.voice.mute
                    else "<:unmuted:1208464547002847242>"
                )
                stream = (
                    "<:stream:1208463585018249228>" if mem.voice.self_stream else ""
                )
                video = "<:video:1208234115682533416>" if mem.voice.self_video else ""
                channelmembers = (
                    f"with {len(mem.voice.channel.members)-1} other member{'s' if len(mem.voice.channel.members) > 2 else ''}"
                    if len(mem.voice.channel.members) > 1
                    else ""
                )
                return f"{deaf} {mute} {stream} {video} **in Voice** {channelname} {channelmembers}"
            return ""

        e = Embed(
            color=self.bot.color, title=str(user) + " " + "".join(map(str, badges))
        )
        if isinstance(member, Member):
            e.description = f"{vc(member)}\n{await tz_find(member)}\n{await lf(member)}"
            members = sorted(ctx.guild.members, key=lambda m: m.joined_at)
            ordinal = self.bot.ext.ordinal(int(members.index(member) + 1))
            e.set_author(
                name=f"{member} • {ordinal} Member", icon_url=member.display_avatar.url
            )
            e.add_field(
                name="Dates",
                value=f"**Joined:** {self.convert_datetime(member.joined_at)}\n**Created:** {self.convert_datetime(member.created_at)}\n{f'**Boosted:** {self.convert_datetime(member.premium_since)}' if self.convert_datetime(member.premium_since) else ''}",
                inline=False,
            )
            roles = member.roles[1:][::-1]
            if len(roles) > 0:
                e.add_field(
                    name=f"Roles ({len(roles)})",
                    value=(
                        " ".join([r.mention for r in roles])
                        if len(roles) < 5
                        else " ".join([r.mention for r in roles[:4]])
                        + f" ... and {len(roles)-4} more"
                    ),
                )
        elif isinstance(member, User):
            e.add_field(
                name="Dates",
                value=f"**Created:** {self.convert_datetime(member.created_at)}",
                inline=False,
            )
        e.set_thumbnail(url=member.display_avatar.url)
        if user.banner is not None:
            e.set_image(url=user.banner.url)
        try:
            e.set_footer(
                text="ID: "
                + str(member.id)
                + f" | {len(member.mutual_guilds)} Mutual(s)"
            )
        except:
            e.set_footer(text="ID: " + str(member.id))
        await ctx.reply(embed=e)

    @commands.command(
        description="clear your usernames",
        help="utility",
        aliases=["clearusernames", "clearusers"],
    )
    async def clearnames(self, ctx):
        embed = discord.Embed(
            color=self.bot.color,
            description=f"{ctx.author.mention} are you sure you want to clear your usernames. This decision is **irreversible**",
        )
        button1 = discord.ui.Button(emoji=self.bot.yes)
        button2 = discord.ui.Button(emoji=self.bot.no)

        async def button1_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                return await self.bot.ext.send_warning(
                    interaction, "You are not the author of this embed", ephemeral=True
                )
            await self.bot.db.execute(
                "DELETE FROM oldusernames WHERE user_id = $1", ctx.author.id
            )
            return await interaction.response.edit_message(
                view=None,
                embed=discord.Embed(
                    color=self.bot.color,
                    description=f"> {self.bot.yes} {interaction.user.mention}: Name history cleared",
                ),
            )

        async def button2_callback(interaction: discord.Interaction):
            if interaction.user.id != ctx.author.id:
                return await self.bot.ext.send_warning(
                    interaction, "You are not the author of this embed", ephemeral=True
                )
            return await interaction.response.edit_message(
                view=None,
                embed=discord.Embed(
                    color=self.bot.color, description=f"Aborting action..."
                ),
            )

        button1.callback = button1_callback
        button2.callback = button2_callback
        view = discord.ui.View()
        view.add_item(button1)
        view.add_item(button2)
        return await ctx.reply(embed=embed, view=view)

    @commands.command(
        description="clear all snipe data",
        help="utility",
        brief="manage messages",
        aliases=["cs"],
    )
    @Permissions.has_permission(manage_messages=True)
    async def clearsnipes(self, ctx: Context):
        lis = ["snipe", "reactionsnipe", "editsnipe"]
        for l in lis:
            await self.bot.db.execute(
                f"DELETE FROM {l} WHERE guild_id = $1", ctx.guild.id
            )
        return await ctx.send_success("Cleared all snipes from this server")

    @commands.command(
        aliases=["names", "usernames"],
        help="utility",
        usage="<user>",
        description="check an user's past usernames",
    )
    async def pastusernames(self, ctx, member: User = None):
        if not member:
            member = ctx.author
        data = await self.bot.db.fetch(
            "SELECT * FROM oldusernames WHERE user_id = $1", member.id
        )
        i = 0
        k = 1
        l = 0
        number = []
        messages = []
        num = 0
        auto = ""
        if data:
            for table in data[::-1]:
                username = table["username"]
                num += 1
                auto += f"\n`{num}` {username}: <t:{int(table['time'])}:R> "
                k += 1
                l += 1
                if l == 10:
                    messages.append(auto)
                    number.append(
                        Embed(color=self.bot.color, description=auto).set_author(
                            name=f"{member}'s past usernames",
                            icon_url=member.display_avatar,
                        )
                    )
                    i += 1
                    auto = ""
                    l = 0
            messages.append(auto)
            embed = Embed(description=auto, color=self.bot.color)
            embed.set_author(
                name=f"{member}'s past usernames", icon_url=member.display_avatar
            )
            number.append(embed)
            return await ctx.paginator(number)
        else:
            return await ctx.send_warning(
                f"no logged usernames for **{member}**".capitalize()
            )

    @commands.command(
        help="utility",
        usage="[message]",
        description="uwify a message",
        aliases=["uwu"],
    )
    async def uwuify(self, ctx: Context, *, text: str):
        uwu = uwuipy.uwuipy()
        uwu_message = uwu.uwuify(text)
        await ctx.send(uwu_message)

    @commands.command(
        help="utility",
        description="give someone permission to post pictures in a channel",
        usage="[member] <channel>",
        brief="manage roles",
    )
    @Permissions.has_permission(manage_roles=True)
    async def picperms(
        self, ctx: Context, member: Member, *, channel: TextChannel = None
    ):
        if channel is None:
            channel = ctx.channel
        if (
            channel.permissions_for(member).attach_files
            and channel.permissions_for(member).embed_links
        ):
            await channel.set_permissions(member, attach_files=False, embed_links=False)
            return await ctx.send_success(
                f"Removed pic perms from {member.mention} in {channel.mention}"
            )
        await channel.set_permissions(member, attach_files=True, embed_links=True)
        return await ctx.send_success(
            f"Added pic perms to {member.mention} in {channel.mention}"
        )

    @commands.command(
        description="see when a user was last seen", help="utility", usage="[member]"
    )
    async def seen(self, ctx, *, member: Member):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM seen WHERE guild_id = {} AND user_id = {}".format(
                ctx.guild.id, member.id
            )
        )
        if check is None:
            return await ctx.send_warning(f"I didn't see **{member}**")
        ts = check["time"]
        await ctx.reply(
            embed=Embed(
                color=self.bot.color,
                description="{}: **{}** was last seen <t:{}:R>".format(
                    ctx.author.mention, member, ts
                ),
            )
        )

    @commands.command(
        help="utility", description="let everyone know you are away", usage="<reason>"
    )
    async def afk(self, ctx: Context, *, reason="AFK"):
        ts = int(datetime.datetime.now().timestamp())
        result = await self.bot.db.fetchrow(
            "SELECT * FROM afk WHERE guild_id = {} AND user_id = {}".format(
                ctx.guild.id, ctx.author.id
            )
        )
        if result is None:
            await self.bot.db.execute(
                "INSERT INTO afk VALUES ($1,$2,$3,$4)",
                ctx.guild.id,
                ctx.author.id,
                reason,
                ts,
            )
            await ctx.send_success(f"You're now AFK with the status: **{reason}**")

    @commands.command(
        aliases=["es"],
        description="get the most recent edited messages from the channel",
        help="utility",
        usage="<number>",
    )
    async def editsnipe(self, ctx: Context, number: int = 1):
        results = await self.bot.db.fetch(
            "SELECT * FROM editsnipe WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            ctx.channel.id,
        )
        if len(results) == 0:
            return await ctx.send_warning(
                "There are no edited messages in this channel"
            )
        if number > len(results):
            return await ctx.send_warning(
                f"The maximum amount of snipes is **{len(results)}**"
            )
        sniped = results[::-1][number - 1]
        embed = Embed(color=self.bot.color)
        embed.set_author(name=sniped["author_name"], icon_url=sniped["author_avatar"])
        embed.add_field(name="before", value=sniped["before_content"])
        embed.add_field(name="after", value=sniped["after_content"])
        embed.set_footer(text=f"{number}/{len(results)}")
        await ctx.reply(embed=embed)

    @commands.command(
        aliases=["rs"],
        description="get the most recent messages that got one of their reactions removed",
        help="utility",
        usage="number",
    )
    async def reactionsnipe(self, ctx: Context, number: int = 1):
        results = await self.bot.db.fetch(
            "SELECT * FROM reactionsnipe WHERE guild_id = $1 AND channel_id = $2",
            ctx.guild.id,
            ctx.channel.id,
        )
        if len(results) == 0:
            return await ctx.send_warning(
                "There are no reaction removed in this channel"
            )
        if number > len(results):
            return await ctx.send_warning(
                f"The maximum amount of snipes is **{len(results)}**"
            )
        sniped = results[::-1][number - 1]
        message = await ctx.channel.fetch_message(sniped["message_id"])
        embed = Embed(
            color=self.bot.color,
            description=f"[{sniped['emoji_name']}]({sniped['emoji_url']})\n[message link]({message.jump_url if message else 'https://none.none'})",
        )
        embed.set_author(name=sniped["author_name"], icon_url=sniped["author_avatar"])
        embed.set_image(url=sniped["emoji_url"])
        embed.set_footer(text=f"{number}/{len(results)}")
        await ctx.reply(embed=embed)

    @commands.command(
        aliases=["s"],
        description="check the latest deleted message from a channel",
        usage="<number>",
        help="utility",
    )
    async def snipe(self, ctx: Context, *, number: int = 1):
        check = await self.bot.db.fetch(
            "SELECT * FROM snipe WHERE guild_id = {} AND channel_id = {}".format(
                ctx.guild.id, ctx.channel.id
            )
        )
        if len(check) == 0:
            return await ctx.send_warning(
                "There are no deleted messages in this channel"
            )
        if number > len(check):
            return await ctx.send_warning(
                f"current snipe limit is **{len(check)}**".capitalize()
            )
        sniped = check[::-1][number - 1]
        em = Embed(
            color=self.bot.color,
            description=sniped["content"],
            timestamp=sniped["time"],
        )
        em.set_author(name=sniped["author"], icon_url=sniped["avatar"])
        em.set_footer(text="{}/{}".format(number, len(check)))
        if sniped["attachment"] != "none":
            if ".mp4" in sniped["attachment"] or ".mov" in sniped["attachment"]:
                url = sniped["attachment"]
                r = await self.bot.session.read(url)
                bytes_io = BytesIO(r)
                file = File(fp=bytes_io, filename="video.mp4")
                return await ctx.reply(embed=em, file=file)
            else:
                try:
                    em.set_image(url=sniped["attachment"])
                except:
                    pass
        return await ctx.reply(embed=em)

    @commands.command(
        aliases=["mc"],
        description="check how many members does your server have",
        help="utility",
    )
    async def membercount(self, ctx: Context):
        b = len(set(b for b in ctx.guild.members if b.bot))
        h = len(set(b for b in ctx.guild.members if not b.bot))
        embed = Embed(color=self.bot.color)
        embed.set_author(
            name=f"{ctx.guild.name}'s member count", icon_url=ctx.guild.icon
        )
        embed.add_field(
            name=f"members (+{len([m for m in ctx.guild.members if (datetime.datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 3600*24 and not m.bot])})",
            value=h,
        )
        embed.add_field(name="total", value=ctx.guild.member_count)
        embed.add_field(name="bots", value=b)
        await ctx.reply(embed=embed)

    @commands.command(
        description="get role information",
        usage="[role]",
        help="utility",
        aliases=["ri"],
    )
    async def roleinfo(self, ctx: Context, *, role: Union[Role, str]):
        if isinstance(role, str):
            role = ctx.find_role(role)
            if role is None:
                return await ctx.send_warning("This is not a valid role")

        perms = (
            ", ".join([str(p[0]) for p in role.permissions if bool(p[1]) is True])
            if role.permissions
            else "none"
        )
        embed = Embed(
            color=role.color,
            title=f"@{role.name}",
            description="`{}`".format(role.id),
            timestamp=role.created_at,
        )
        embed.set_thumbnail(
            url=role.display_icon if not isinstance(role.display_icon, str) else None
        )
        embed.add_field(name="members", value=str(len(role.members)))
        embed.add_field(name="mentionable", value=str(role.mentionable).lower())
        embed.add_field(name="hoist", value=str(role.hoist).lower())
        embed.add_field(name="permissions", value=f"```{perms}```", inline=False)
        await ctx.reply(embed=embed)

    @commands.command(
        description="see all members in a role", help="utility", usage="[role]"
    )
    async def inrole(self, ctx: Context, *, role: Union[Role, str]):
        if isinstance(role, str):
            role = ctx.find_role(role)
            if role is None:
                return await ctx.send_warning("This isn't a valid role")

        if len(role.members) == 0:
            return await ctx.send_error("Nobody (even u) has this role")
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for member in role.members:
            mes = f"{mes}`{k}` {member} - ({member.id})\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"members in {role.name} [{len(role.members)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"members in {role.name} [{len(role.members)}]",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @commands.command(
        description="see all members joined within 24 hours", help="utility"
    )
    async def joins(self, ctx: Context):
        members = [
            m
            for m in ctx.guild.members
            if (
                datetime.datetime.now() - m.joined_at.replace(tzinfo=None)
            ).total_seconds()
            < 3600 * 24
        ]
        if len(members) == 0:
            return await ctx.send_error("No members joined in the last **24** hours")
        members = sorted(members, key=lambda m: m.joined_at)
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for member in members[::-1]:
            mes = f"{mes}`{k}` {member} - {discord.utils.format_dt(member.joined_at, style='R')}\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"joined today [{len(members)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"joined today [{len(members)}]",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @commands.command(description="see all muted members", help="utility")
    async def muted(self, ctx: Context):
        members = [m for m in ctx.guild.members if m.is_timed_out()]
        if len(members) == 0:
            return await ctx.send_error("There are no muted members")
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for member in members:
            mes = f"{mes}`{k}` {member} - <t:{int(member.timed_out_until.timestamp())}:R> \n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"{ctx.guild.name} muted members [{len(members)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"{ctx.guild.name} muted members [{len(members)}]",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @Permissions.has_permission(ban_members=True)
    @commands.command(description="see all banned members", help="utility")
    async def bans(self, ctx: Context):
        banned = [m async for m in ctx.guild.bans()]
        if len(banned) == 0:
            return await ctx.send_warning("There are no banned people in this server")
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for m in banned:
            mes = f"{mes}`{k}` **{m.user}** - `{m.reason or 'No reason provided'}` \n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"banned ({len(banned)})",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"banned ({len(banned)})",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @commands.group(invoke_without_command=True)
    async def boosters(self, ctx: commands.Context):
        await ctx.create_pages()

    @boosters.command(
        invoke_without_command=True,
        description="see all server boosters",
        help="utility",
    )
    async def list(self, ctx: Context):
        if (
            not ctx.guild.premium_subscriber_role
            or len(ctx.guild.premium_subscriber_role.members) == 0
        ):
            return await ctx.send_warning(
                "this server doesn't have any boosters".capitalize()
            )
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for member in ctx.guild.premium_subscriber_role.members:
            mes = f"{mes}`{k}` {member} - <t:{int(member.premium_since.timestamp())}:R> \n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"boosters [{len(ctx.guild.premium_subscriber_role.members)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"boosters [{len(ctx.guild.premium_subscriber_role.members)}]",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @boosters.command(name="lost", description="display lost boosters", help="utility")
    async def lost(self, ctx: Context):
        results = await self.bot.db.fetch(
            "SELECT * FROM boosterslost WHERE guild_id = $1", ctx.guild.id
        )
        if len(results) == 0:
            return await ctx.send_warning("There are no lost boosters")
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for result in results[::-1]:
            mes = f"{mes}`{k}` <@!{int(result['user_id'])}> - <t:{result['time']}:R> \n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"lost boosters [{len(results)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"lost boosters [{len(results)}]",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @Permissions.has_permission(manage_roles=True)
    @commands.command(description="see all server roles", help="utility")
    async def roles(self, ctx: Context):
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for role in ctx.guild.roles:
            mes = f"{mes}`{k}` {role.mention} - <t:{int(role.created_at.timestamp())}:R> ({len(role.members)} members)\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"roles [{len(ctx.guild.roles)}]",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"roles [{len(ctx.guild.roles)}]",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @Permissions.has_permission(moderate_members=True)
    @commands.command(description="see all server's bots", help="utility")
    async def bots(self, ctx: Context):
        i = 0
        k = 1
        l = 0
        b = len(set(b for b in ctx.guild.members if b.bot))
        mes = ""
        number = []
        messages = []
        for member in ctx.guild.members:
            if member.bot:
                mes = f"{mes}`{k}` {member} - ({member.id})\n"
                k += 1
                l += 1
                if l == 10:
                    messages.append(mes)
                    number.append(
                        Embed(
                            color=self.bot.color,
                            title=f"bots [{b}]",
                            description=messages[i],
                        )
                    )
                    i += 1
                    mes = ""
                    l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title=f"{ctx.guild.name} bots [{b}]",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)

    @commands.command(
        help="utility",
        description="check the weather from a location",
        usage="[country]",
    )
    async def weather(self, ctx: Context, *, location: str):
        url = "http://api.weatherapi.com/v1/current.json"
        params = {"key": self.weather_key, "q": location}
        data = await self.bot.session.json(url, params=params)
        place = data["location"]["name"]
        country = data["location"]["country"]
        temp_c = data["current"]["temp_c"]
        temp_f = data["current"]["temp_f"]
        wind_mph = data["current"]["wind_mph"]
        wind_kph = data["current"]["wind_kph"]
        humidity = data["current"]["humidity"]
        condition_text = data["current"]["condition"]["text"]
        condition_image = "http:" + data["current"]["condition"]["icon"]
        time = datetime.datetime.fromtimestamp(
            int(data["current"]["last_updated_epoch"])
        )
        embed = discord.Embed(
            color=self.bot.color,
            title=f"{condition_text} in {place}, {country}",
            timestamp=time,
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=condition_image)
        embed.add_field(name="Temperature", value=f"{temp_c} °C / {temp_f} °F")
        embed.add_field(name="Humidity", value=f"{humidity}%")
        embed.add_field(name="Wind", value=f"{wind_mph} mph / {wind_kph} kph")
        return await ctx.reply(embed=embed)

    @commands.command(
        description="shows the number of invites an user has",
        usage="<user>",
        help="utility",
    )
    async def invites(self, ctx: Context, *, member: Member = None):
        if member is None:
            member = ctx.author
        invites = await ctx.guild.invites()
        await ctx.reply(
            f"{member} has **{sum(invite.uses for invite in invites if invite.inviter.id == member.id)}** invites"
        )

    @commands.command(
        description="see the list of donators", help="utility", aliases=["donors"]
    )
    async def donators(self, ctx):
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        results = await self.bot.db.fetch("SELECT * FROM donor")
        if len(results) == 0:
            return await ctx.send_error("There are no donators")
        for result in results:
            mes = f"{mes}`{k}` <@!{result['user_id']}> ({result['user_id']}) - (<t:{int(result['time'])}:R>)\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"donators ({len(results)})",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(
            Embed(
                color=self.bot.color,
                title=f"donators ({len(results)})",
                description=messages[i],
            )
        )
        await ctx.paginator(number)

    @commands.command(
        aliases=["tts", "speech"],
        description="convert your message to mp3",
        help="utility",
        usage="[message]",
    )
    async def texttospeech(self, ctx: Context, *, txt: str):
        i = BytesIO()
        aiogtts = aiogTTS()
        await aiogtts.save(txt, "tts.mp3", lang="en")
        await aiogtts.write_to_fp(txt, i, slow=False, lang="en")
        await ctx.reply(file=discord.File(fp="tts.mp3", filename="tts.mp3"))
        return os.remove("tts.mp3")

    @commands.command(
        description="gets the invite link with administrator permission of a bot",
        help="utility",
        usage="[bot id]",
    )
    async def getbotinvite(self, ctx, id: User):
        if not id.bot:
            return await ctx.send_error("This isn't a bot")
        embed = Embed(
            color=self.bot.color,
            description=f"**[invite the bot](https://discord.com/api/oauth2/authorize?client_id={id.id}&permissions=8&scope=bot%20applications.commands)**",
        )
        await ctx.reply(embed=embed)

    @commands.command(
        aliases=["tr"],
        description="translate a message",
        help="utility",
        usage="[language] [message]",
    )
    async def translate(self, ctx: Context, lang: str, *, mes: str):
        translated = GoogleTranslator(source="auto", target=lang).translate(mes)
        embed = Embed(
            color=self.bot.color,
            description="```{}```".format(translated),
            title="translated to {}".format(lang),
        )
        await ctx.reply(embed=embed)

    @commands.group(
        invoke_without_command=True,
        help="utility",
        description="check member's birthday",
        aliases=["bday"],
    )
    async def birthday(self, ctx: Context, *, member: Member = None):
        if member is None:
            member = ctx.author
        lol = "'s"
        date = await self.bot.db.fetchrow(
            "SELECT bday FROM birthday WHERE user_id = $1", member.id
        )
        if not date:
            return await ctx.send_warning(
                f"**{'Your' if member == ctx.author else str(member) + lol}** birthday is not set"
            )
        date = date["bday"]
        if "ago" in arrow.get(date).humanize(granularity="day"):
            date = date.replace(year=date.year + 1)
        else:
            date = date
        if arrow.get(date).humanize(granularity="day") == "in 0 days":
            date = "tomorrow"
        elif (
            arrow.get(date).day == arrow.utcnow().day
            and arrow.get(date).month == arrow.utcnow().month
        ):
            date = "today"
        else:
            date = arrow.get(date + datetime.timedelta(days=1)).humanize(
                granularity="day"
            )
        await self.bday_send(
            ctx,
            f"{'Your' if member == ctx.author else '**' + member.name + lol + '**'} birthday is **{date}**",
        )

    @birthday.command(
        name="set",
        help="utility",
        description="set your birthday",
        usage="[month] [day]\nexample: birthday set January 19",
    )
    async def bday_set(self, ctx: Context, month: str, day: str):
        try:
            if len(month) == 1:
                mn = "M"
            elif len(month) == 2:
                mn = "MM"
            elif len(month) == 3:
                mn = "MMM"
            else:
                mn = "MMMM"
            if "th" in day:
                day = day.replace("th", "")
            if "st" in day:
                day = day.replace("st", "")
            if len(day) == 1:
                dday = "D"
            else:
                dday = "DD"
            ts = f"{month} {day} {datetime.date.today().year}"
            if "ago" in arrow.get(ts, f"{mn} {dday} YYYY").humanize(granularity="day"):
                year = datetime.date.today().year + 1
            else:
                year = datetime.date.today().year
            string = f"{month} {day} {year}"
            date = arrow.get(string, f"{mn} {dday} YYYY")
            check = await self.bot.db.fetchrow(
                "SELECT * FROM birthday WHERE user_id = $1", ctx.author.id
            )
            if not check:
                await self.bot.db.execute(
                    "INSERT INTO birthday VALUES ($1,$2,$3)",
                    ctx.author.id,
                    date.datetime,
                    "false",
                )
            else:
                await self.bot.db.execute(
                    "UPDATE birthday SET bday = $1 WHERE user_id = $2",
                    date.datetime,
                    ctx.author.id,
                )
            await self.bday_send(ctx, f"Configured your birthday as **{month} {day}**")
        except:
            return await ctx.send_error(
                f"usage: `{ctx.clean_prefix}birthday set [month] [day]`"
            )

    @birthday.command(name="unset", help="utility", description="unset your birthday")
    async def bday_unset(self, ctx: Context):
        check = await self.bot.db.fetchrow(
            "SELECT bday FROM birthday WHERE user_id = $1", ctx.author.id
        )
        if not check:
            return await ctx.send_warning("Your birthday is not set")
        await self.bot.db.execute(
            "DELETE FROM birthday WHERE user_id = $1", ctx.author.id
        )
        await ctx.send_warning("Unset your birthday")

    @commands.group(
        invoke_without_command=True,
        help="utility",
        description="check member's timezones",
        aliases=["tz"],
    )
    async def timezone(self, ctx: Context, *, member: discord.Member = None):
        if member is None:
            member = ctx.author
        return await self.tz.get_user_timezone(ctx, member)

    @timezone.command(
        name="set",
        help="utility",
        description="set the timezone",
        usage="[location]\nexample: ;tz set russia",
    )
    async def tz_set(self, ctx: Context, *, location: str):
        return await self.tz.tz_set_cmd(ctx, location)

    @timezone.command(
        name="list",
        help="utility",
        description="return a list of server member's timezones",
    )
    async def tz_list(self, ctx: Context):
        ids = [str(m.id) for m in ctx.guild.members]
        results = await self.bot.db.fetch(
            f"SELECT * FROM timezone WHERE user_id IN ({','.join(ids)})"
        )
        if len(results) == 0:
            await self.tz.timezone_send(ctx, "Nobody (even you) has their timezone set")
        await ctx.typing()
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for result in results:
            mes = f"{mes}`{k}` <@{int(result['user_id'])}> - {await self.tz.timezone_request(ctx.guild.get_member(int(result['user_id'])))}\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    Embed(
                        color=self.bot.color,
                        title=f"timezone list",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color, title=f"timezone list", description=messages[i]
        )
        number.append(embed)
        await ctx.paginator(number)

    @timezone.command(name="unset", help="utility", description="unset the timezone")
    async def tz_unset(self, ctx: Context):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM timezone WHERE user_id = $1", ctx.author.id
        )
        if not check:
            return await ctx.send_warning("You don't have a **timezone** set")
        await self.bot.db.execute(
            "DELETE * FROM timezone WHERE user_id = $1", ctx.author.id
        )
        return await ctx.send_success("Removed the timezone")

    @commands.group(invoke_without_command=True)
    async def reminder(self, ctx: Context):
        return await ctx.create_pages()

    @reminder.command(
        name="add",
        help="utility",
        description="make the bot remind you about a task",
        usage="[time] [reminder]",
    )
    async def reminder_add(self, ctx: Context, time: str, *, task: str):
        return await ctx.invoke(self.bot.get_command("remind"), time=time, task=task)

    @reminder.command(
        name="stop",
        aliases=["cancel"],
        description="cancel a reminder from this server",
        help="utility",
    )
    @is_there_a_reminder()
    async def reminder_stop(self, ctx: Context):
        await self.bot.db.execute(
            "DELETE FROM reminder WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        return await ctx.send_success("Deleted a reminder")

    @commands.command(
        aliases=["remindme"],
        help="utility",
        description="make the bot remind you about a task",
        usage="[time] [reminder]",
    )
    async def remind(self, ctx: Context, time: str, *, task: str):
        try:
            seconds = humanfriendly.parse_timespan(time)
        except humanfriendly.InvalidTimespan:
            return await ctx.send_warning(f"**{time}** is not a correct time format")
        await ctx.reply(
            f"🕰️ {ctx.author.mention}: I'm going to remind you in {humanfriendly.format_timespan(seconds)} about **{task}**"
        )
        if seconds < 5:
            await asyncio.sleep(seconds)
            return await ctx.channel.send(f"🕰️ {ctx.author.mention}: {task}")
        else:
            try:
                await self.bot.db.execute(
                    "INSERT INTO reminder VALUES ($1,$2,$3,$4,$5)",
                    ctx.author.id,
                    ctx.channel.id,
                    ctx.guild.id,
                    (datetime.datetime.now() + datetime.timedelta(seconds=seconds)),
                    task,
                )
            except:
                return await ctx.send_warning(
                    "You already have a reminder set in this channel. Use `{ctx.clean_prefix}reminder stop` to cancel the reminder"
                )

    @commands.command(
        name="members",
        description="get an embed of all the members in a server by join date",
        help="utility",
    )
    async def members(self, ctx: commands.Context):
        members1 = [m for m in ctx.guild.members if not m.bot]
        members = sorted(members1, key=lambda m: m.joined_at)
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for member in members[::-1]:
            mes = f"{mes}`{k}` **{member}** joined <t:{int(member.joined_at.timestamp())}:f> (<t:{int(member.joined_at.timestamp())}:R>)\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=self.bot.color,
                        title="total members",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color, title="total members", description=messages[i]
        )
        number.append(embed)
        await ctx.paginator(number)

    @commands.command(
        name="oldestaccounts",
        description="get an embed of the oldest accounts in the server",
        help="utility",
    )
    async def oldestaccounts(self, ctx: commands.Context):
        members1 = [m for m in ctx.guild.members if not m.bot]
        members = sorted(members1, key=lambda m: m.created_at, reverse=True)
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for member in members[::-1]:
            mes = f"{mes}`{k}` **{member}** created <t:{int(member.created_at.timestamp())}:f> (<t:{int(member.created_at.timestamp())}:R>)\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=self.bot.color,
                        title="oldest account by creation date",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        embed = Embed(
            color=self.bot.color,
            title="oldest account by creation date",
            description=messages[i],
        )
        number.append(embed)
        await ctx.paginator(number)


async def setup(bot):
    await bot.add_cog(utility(bot))
