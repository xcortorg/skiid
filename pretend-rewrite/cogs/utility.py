import asyncio
import datetime
import io
import os
from io import BytesIO
from typing import Any, Optional, Union

import arrow
import colorgram
import discord
import humanfriendly
import humanize
import instaloader
import timezonefinder
import uwuipy
from discord import Embed, File, Member, Role, Spotify, TextChannel, User
from discord.ext import commands
from discord.ext.commands import Author
from discord.ext.commands import AutoShardedBot as Bot
from discord.ext.commands import Cog, Context, command, group, hybrid_command
from discord.ui import Button, View
from geopy.geocoders import Nominatim
from get.checks import Perms
from get.pretend import Pretend, PretendContext
from PIL import Image
from shazamio import Serialize, Shazam
from timezonefinder import TimezoneFinder

DISCORD_API_LINK = "https://discord.com/api/invite/"


class Timezone(object):
    def __init__(self, bot: Bot):
        """
        Get timezones of people
        """
        self.bot = bot
        self.clock = ":alarm_clock:"
        self.months = {
            "01": "January",
            "02": "February",
            "03": "March",
            "04": "April",
            "05": "May",
            "06": "June",
            "07": "July",
            "08": "August",
            "09": "September",
            "10": "October",
            "11": "November",
            "12": "December",
        }

    async def timezone_send(self, ctx: Context, message: str):
        return await ctx.reply(
            embed=discord.Embed(
                color=self.bot.color, description=f"> {ctx.author.mention}: {message}"
            )
        )

    async def timezone_request(self, member: discord.Member):
        coord = await self.get_user_lat_long(member)
        if coord is None:
            return None
        utc = arrow.utcnow()
        local = utc.to(coord)
        timestring = local.format("YYYY-MM-DD HH:mm").split(" ")
        date = timestring[0][5:].split("-")
        try:
            hours, minutes = [int(x) for x in timestring[1].split(":")[:2]]
        except IndexError:
            return "N/A"

        if hours >= 12:
            suffix = "PM"
            hours -= 12
        else:
            suffix = "AM"
        if hours == 0:
            hours = 12
        return f"{self.months.get(date[0])} {self.bot.ordinal(date[1])} {hours}:{minutes:02d} {suffix}"

    async def get_user_lat_long(self, member: discord.Member):
        check = await self.bot.db.fetchrow(
            "SELECT * FROM timezone WHERE user_id = $1", member.id
        )
        if check is None:
            return None
        return check["zone"]

    async def tz_set_cmd(self, ctx: Context, location: str):
        await ctx.typing()
        geolocator = Nominatim(
            user_agent="Mozilla/5.0 (Linux; Android 8.0.0; SM-G955U Build/R16NW) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Mobile Safari/537.36"
        )
        lad = location
        location = geolocator.geocode(lad)
        if location is None:
            return await ctx.send_warning(
                "Couldn't find a **timezone** for that location"
            )
        check = await self.bot.db.fetchrow(
            "SELECT * FROM timezone WHERE user_id = $1", ctx.author.id
        )
        obj = TimezoneFinder()
        result = obj.timezone_at(lng=location.longitude, lat=location.latitude)
        if not check:
            await self.bot.db.execute(
                "INSERT INTO timezone VALUES ($1,$2)", ctx.author.id, result
            )
        else:
            await self.bot.db.execute(
                "DELETE FROM timezone WHERE user_id = $1", ctx.author.id
            )
            await self.bot.db.execute(
                "INSERT INTO timezone VALUES ($1,$2)", ctx.author.id, result
            )
        embed = Embed(
            color=self.bot.color,
            description=f"Saved your timezone as **{result}**\n{self.clock} Current time: **{await self.timezone_request(ctx.author)}**",
        )
        await ctx.reply(embed=embed)

    async def get_user_timezone(self, ctx: Context, member: discord.Member):
        if await self.timezone_request(member) is None:
            if member.id == ctx.author.id:
                return await ctx.send_warning(f"Use `{ctx.clean_prefix}tz set` first.")
            else:
                return await ctx.send_warning(
                    f"**{member.name}** doesn't have their **timezone** set"
                )
        if member.id == ctx.author.id:
            return await self.timezone_send(
                ctx, f"Current time: **{await self.timezone_request(member)}**"
            )
        else:
            return await self.timezone_send(
                ctx,
                f"Current time for **{member.name}** is **{await self.timezone_request(member)}**",
            )


def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60

    return "%d:%02d:%02d" % (hour, minutes, seconds)


def human_format(number):
    if number > 999:
        return humanize.naturalsize(number, False, True)
    return number


class utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cake = "🎂"
        self.weather_key = "64581e6f1d7d49ae834142709230804"
        self.tz = Timezone(self.bot)

    async def bday_send(self, ctx: commands.Context, message: str) -> discord.Message:
        return await ctx.reply(
            embed=discord.Embed(
                color=self.bot.color,
                description=f"> {self.cake} {ctx.author.mention}: {message}",
            )
        )

    @hybrid_command(
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

    @command(description="see the list of donators", help="utility", aliases=["donors"])
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

    @group(
        invoke_without_command=True,
        description="see all server boosters",
        help="utility",
    )
    async def boosters(self, ctx: Context):
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
    async def boosters_lost(self, ctx: Context):
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

    @command(description="see all server roles", help="utility")
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

    @command(description="see all server's bots", help="utility")
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

    @command(description="see all members joined within 24 hours", help="utility")
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

    @command(description="see all muted mebmers", help="utility")
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

    @commands.hybrid_command(
        description="see someone's banner", help="utility", usage="<user>"
    )
    async def banner(
        self, ctx: commands.Context, *, member: discord.User = commands.Author
    ):
        user = await self.bot.fetch_user(member.id)
        if not user.banner:
            return await ctx.send_warning(f"**{user}** Doesn't have a banner")
        embed = discord.Embed(
            color=self.bot.color, title=f"{user.name}'s banner", url=user.banner.url
        )
        embed.set_image(url=user.banner.url)
        return await ctx.reply(embed=embed)

    @hybrid_command(
        aliases=["firstmsg"],
        description="get the first message",
        help="utility",
        usage="<channel>",
    )
    async def firstmessage(self, ctx: Context, *, channel: TextChannel = None):
        channel = channel or ctx.channel
        messages = [mes async for mes in channel.history(oldest_first=True, limit=1)]
        message = messages[0]
        embed = Embed(
            color=self.bot.color,
            title="first message in #{}".format(channel.name),
            description=f"> {message.content}",
            timestamp=message.created_at,
        )
        embed.set_author(name=message.author, icon_url=message.author.display_avatar)
        view = View()
        view.add_item(Button(label="JUMP TO MESSAGE", url=message.jump_url))
        await ctx.reply(embed=embed, view=view)

    @group(
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
                f"`{ctx.clean_prefix}birthday set [month] [day]`"
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

    @hybrid_command(
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
        embed.add_field(name="Temperature", value=f"> {temp_c} °C / {temp_f} °F")
        embed.add_field(name="Humidity", value=f"> {humidity}%")
        embed.add_field(name="Wind", value=f"> {wind_mph} mph / {wind_kph} kph")
        return await ctx.reply(embed=embed)

    @command(help="config", description="shows variables for the embed")
    async def variables(self, ctx: Context):
        embed1 = Embed(color=self.bot.color, title="user related variables")
        embed1.description = """
    >>> {user} - returns user full name
{user.name} - returns user's username
{user.mention} - mentions user
{user.avatar} - return user's avatar
{user.joined_at} returns the relative date the user joined the server
{user.created_at} returns the relative time the user created the account
{user.discriminator} - returns the user's discriminator
    """

        embed2 = Embed(color=self.bot.color, title="guild related variables")
        embed2.description = """
    >>> {guild.name} - returns the server's name
 {guild.count} - returns the server's member count
 {guild.count.format} - returns the server's member count in ordinal format
 {guild.icon} - returns the server's icon
 {guild.id} - returns the server's id
 {guild.vanity} - returns the server's vanity, if any 
 {guild.created_at} - returns the relative time the server was created
 {guild.boost_count} - returns the number of server's boosts
 {guild.booster_count} - returns the number of boosters
 {guild.boost_count.format} - returns the number of boosts in ordinal format
 {guild.booster_count.format} - returns the number of boosters in ordinal format
 {guild.boost_tier} - returns the server's boost level
   """

        embed3 = Embed(color=self.bot.color, title="invoke command only variables")
        embed3.description = """
    >>> {member} - returns member's name and discriminator
    {member.name} - returns member's name
    {member.mention} - returns member mention
    {member.discriminator} - returns member's discriminator
    {member.id} - return member's id
    {member.avatar} - returns member's avatar
    {reason} - returns action reason, if any
    """

        embed4 = Embed(color=self.bot.color, title="last.fm variables")
        embed4.description = """
    >>> {scrobbles} - returns all song play count
    {trackplays} - returns the track total plays
    {artistplays} - returns the artist total plays
    {albumplays} - returns the album total plays
    {track} - returns the track name
    {trackurl} - returns the track url
    {trackimage} - returns the track image
    {artist} - returns the artist name
    {artisturl} - returns the artist profile url
    {album} - returns the album name 
    {albumurl} - returns the album url
    {username} - returns your username
    {useravatar} - returns user's profile picture"""

        embed6 = Embed(color=self.bot.color, title="vanity variables")
        embed6.description = """
     >>> {vanityrole.name} - returns the vanity role name\n{vanityrole.mention} - returns the mention of the vanity role\n{vanityrole.id} - returns the id of the vanity role\n{vanityrole.members} - returns the number of members who have the vanity role\n{vanityrole.members.format} - returns the number of members who have the vanity role in ordinal"""

        embed5 = Embed(color=self.bot.color, title="other variables")
        embed5.description = """
    >>> {invisible} - returns the invisible embed color
    {delete} - delete the trigger (for autoresponder)"""

        await ctx.paginator([embed1, embed2, embed3, embed4, embed6, embed5])

    @command(
        description="get a user info", help="utility", aliases=["user", "ui", "whois"]
    )
    async def userinfo(
        self,
        ctx,
        *,
        member: Union[discord.Member, discord.User] = commands.Author,
    ):
        """
        Returns information about an user
        """

        def vc(mem: discord.Member):
            if mem.voice:
                channelname = mem.voice.channel.name
                deaf = (
                    "<:undeafened:1258833442758594622>"
                    if mem.voice.self_deaf or mem.voice.deaf
                    else "<:undeafened:1258833442758594622> "
                )
                mute = (
                    "<:unmuted:1258832911981875330>"
                    if mem.voice.self_mute or mem.voice.mute
                    else "<:unmuted:1258832911981875330>"
                )
                stream = (
                    "<:stream:1258832920345579621>" if mem.voice.self_stream else ""
                )
                video = "<:rename:1258832924737015958>" if mem.voice.self_video else ""
                channelmembers = (
                    f"with {len(mem.voice.channel.members)-1} other member{'s' if len(mem.voice.channel.members) > 2 else ''}"
                    if len(mem.voice.channel.members) > 1
                    else ""
                )
                return f" {deaf} {mute} {stream} {video} **in voice channel** {channelname} {channelmembers}\n"
            return ""

        embed = (
            discord.Embed(
                color=self.bot.color,
                description=f"**{member}**",
            )
            .set_author(
                name=f"{member.name} ({member.id})", icon_url=member.display_avatar.url
            )
            .set_thumbnail(url=member.display_avatar.url)
            .add_field(
                name="Created",
                value=f"{discord.utils.format_dt(member.created_at, style='D')}\n{discord.utils.format_dt(member.created_at, style='R')}",
            )
        )

        if not isinstance(member, discord.ClientUser):
            embed.set_footer(text=f"{len(member.mutual_guilds):,} server(s)")

        if isinstance(member, discord.Member):
            members = sorted(ctx.guild.members, key=lambda m: m.joined_at)
            embed.description += vc(member)

            if not isinstance(member, discord.ClientUser):
                embed.set_footer(
                    text=f"Join position: {members.index(member)+1:,}, {len(member.mutual_guilds):,} server(s)"
                )

            embed.add_field(
                name="Joined",
                value=f"{discord.utils.format_dt(member.joined_at, style='D')}\n{discord.utils.format_dt(member.joined_at, style='R')}",
            )

            if member.premium_since:
                embed.add_field(
                    name="Boosted",
                    value=f"{discord.utils.format_dt(member.premium_since, style='D')}\n{discord.utils.format_dt(member.premium_since, style='R')}",
                )

            roles = member.roles[1:][::-1]

            if len(roles) > 0:
                embed.add_field(
                    name=f"Roles ({len(roles)})",
                    value=(
                        " ".join([r.mention for r in roles])
                        if len(roles) < 5
                        else " ".join([r.mention for r in roles[:4]])
                        + f" ... and {len(roles)-4} more"
                    ),
                    inline=False,
                )

        await ctx.send(embed=embed)

    @command(
        description="gets the banner from a server based by invite code",
        help="utility",
        usage="[invite code]",
    )
    async def sbanner(self, ctx, *, link: str):
        invite_code = link
        data = await self.bot.session.json(
            DISCORD_API_LINK + invite_code, proxy=self.bot.proxy_url, ssl=False
        )
        format = ".gif" if "a_" in data["guild"]["banner"] else ".png"
        embed = Embed(color=self.bot.color, title=data["guild"]["name"] + "'s banner")
        embed.set_image(
            url="https://cdn.discordapp.com/banners/"
            + data["guild"]["id"]
            + "/"
            + data["guild"]["banner"]
            + f"{format}?size=1024"
        )
        await ctx.reply(embed=embed)

    @command(
        description="gets the splash from a server based by invite code",
        help="utility",
        usage="[invite code]",
    )
    async def splash(self, ctx, *, link: str):
        invite_code = link
        data = await self.bot.session.json(
            DISCORD_API_LINK + invite_code, proxy=self.bot.proxy_url, ssl=False
        )
        embed = Embed(color=self.bot.color, title=data["guild"]["name"] + "'s splash")
        embed.set_image(
            url="https://cdn.discordapp.com/splashes/"
            + data["guild"]["id"]
            + "/"
            + data["guild"]["splash"]
            + ".png?size=1024"
        )
        await ctx.reply(embed=embed)

    @command(
        description="gets the icon from a server based by invite code",
        help="utility",
        usage="[invite code]",
    )
    async def sicon(self, ctx, *, link: str):
        invite_code = link
        data = await self.bot.session.json(
            DISCORD_API_LINK + invite_code, proxy=self.bot.proxy_url, ssl=False
        )
        format = ".gif" if "a_" in data["guild"]["icon"] else ".png"
        embed = Embed(color=self.bot.color, title=data["guild"]["name"] + "'s icon")
        embed.set_image(
            url="https://cdn.discordapp.com/icons/"
            + data["guild"]["id"]
            + "/"
            + data["guild"]["icon"]
            + f"{format}?size=1024"
        )
        await ctx.reply(embed=embed)

    @command(
        help="utility",
        description="get a server info(you can put a invite code after)",
        aliases=["si", "server"],
    )
    async def serverinfo(self, ctx, invite: discord.Invite = None):
        if invite:
            embed = discord.Embed(
                color=self.bot.color, title=f"{invite.code}"
            ).add_field(
                name="Invite",
                value=f">>> **Channel:** {invite.channel.name} ({invite.channel.type})\n**Id:** {invite.channel.id}\n**Expires:** {f'yes ({self.bot.humanize_date(invite.expires_at.replace(tzinfo=None))})' if invite.expires_at else 'no'}\n**Uses:** {invite.uses or 'unknown'}",
            )

            if invite.guild:
                embed.description = invite.guild.description or ""
                embed.set_thumbnail(url=invite.guild.icon).add_field(
                    name="Server",
                    value=f">>> **Name:** {invite.guild.name}\n**Id:** {invite.guild.id}\n**Members:** {invite.approximate_member_count:,}\n**Created**: {discord.utils.format_dt(invite.created_at, style='R') if invite.created_at else 'N/A'}",
                )

        else:
            servers = sorted(
                self.bot.guilds, key=lambda g: g.member_count, reverse=True
            )
            embed = (
                discord.Embed(
                    color=self.bot.color,
                    title=ctx.guild.name,
                    description=f"{ctx.guild.description or ''}\n\nCreated on {discord.utils.format_dt(ctx.guild.created_at, style='D')} {discord.utils.format_dt(ctx.guild.created_at, style='R')}\nJoined on {discord.utils.format_dt(ctx.guild.me.joined_at, style='D')} {discord.utils.format_dt(ctx.guild.me.joined_at, style='R')}",
                )
                .set_author(
                    name=f"{ctx.guild.owner} ({ctx.guild.owner_id})",
                    icon_url=ctx.guild.owner.display_avatar.url,
                )
                .set_thumbnail(url=ctx.guild.icon)
                .add_field(
                    name="Counts",
                    value=f">>> **Roles:** {len(ctx.guild.roles):,}\n**Emojis:** {len(ctx.guild.emojis):,}\n**Stickers:** {len(ctx.guild.stickers):,}",
                )
                .add_field(
                    name="Members",
                    value=f">>> **Users:** {len(set(i for i in ctx.guild.members if not i.bot)):,}\n**Bots:** {len(set(i for i in ctx.guild.members if i.bot)):,}\n**Total:** {ctx.guild.member_count:,}",
                )
                .add_field(
                    name="Channels",
                    value=f">>> **Text:** {len(ctx.guild.text_channels):,}\n**Voice:** {len(ctx.guild.voice_channels):,}\n**Categories:** {len(ctx.guild.categories):,}",
                )
                .add_field(
                    name="Info",
                    value=f">>> **Vanity:** {ctx.guild.vanity_url_code or 'N/A'}\n**Popularity:** {servers.index(ctx.guild)+1}/{len(self.bot.guilds)}",
                )
            )
            embed.add_field(
                name="Boost",
                value=f">>> **Boosts:** {ctx.guild.premium_subscription_count:,}\n**Level:** {ctx.guild.premium_tier}\n**Boosters:** {len(ctx.guild.premium_subscribers)}",
            ).add_field(
                name="Design",
                value=f">>> **Icon:** {f'[**here**]({ctx.guild.icon})' if ctx.guild.icon else 'N/A'}\n**Banner:**  {f'[**here**]({ctx.guild.banner})' if ctx.guild.banner else 'N/A'}\n**Splash:**  {f'[**here**]({ctx.guild.splash})' if ctx.guild.splash else 'N/A'}",
            ).set_footer(
                text=f"Guild ID: {ctx.guild.id} • Shard: {ctx.guild.shard_id}/{len(self.bot.shards)}"
            )

        await ctx.send(embed=embed)

    @command(
        help="utility",
        description="get a channel information",
        name="channelinfo",
        aliases=["ci"],
    )
    async def channelinfo(self, ctx, *, channel: Optional[TextChannel] = None):
        channel = channel or ctx.channel

        embed = (
            discord.Embed(color=self.bot.color, title=channel.name)
            .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
            .add_field(name="Channel ID", value=f"`{channel.id}`", inline=True)
            .add_field(name="Type", value=str(channel.type), inline=True)
            .add_field(
                name="Guild",
                value=f"{channel.guild.name} (`{channel.guild.id}`)",
                inline=True,
            )
            .add_field(
                name="Category",
                value=f"{channel.category.name} (`{channel.category.id}`)",
                inline=False,
            )
            .add_field(name="Topic", value=channel.topic or "N/A", inline=True)
            .add_field(
                name="Created At",
                value=f"{discord.utils.format_dt(channel.created_at, style='F')} ({discord.utils.format_dt(channel.created_at, style='R')})",
                inline=False,
            )
        )

        await ctx.send(embed=embed)

    @command(help="utility", description="pin a message with a reply")
    @Perms.get_perms("manage_messages")
    async def pin(self, ctx):
        if ctx.message.reference:
            referenced_message = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
            try:
                await referenced_message.pin()
                await ctx.send_success("The message is now **pinned**")
            except:
                await ctx.send("")
        else:
            return await ctx.send_error(
                f"Please reply to a **message** and type `{ctx.clean_prefix}pin`"
            )

    @hybrid_command(
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
            await ctx.send_success(f"You're now AFK - **{reason}**")

    @hybrid_command(
        help="utility",
        description="give someone permission to post pictures in a channel",
        usage="[member] <channel>",
        brief="manage roles",
    )
    @Perms.get_perms("manage_roles")
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
                f"{member.mention} can no longer send images in {channel.mention}"
            )
        await channel.set_permissions(member, attach_files=True, embed_links=True)
        return await ctx.send_success(
            f"{member.mention} can send now images in {channel.mention}"
        )

    @group(
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
        name="set", help="utility", description="set the timezone", usage="[location]"
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
            "DELETE FROM timezone WHERE user_id = $1", ctx.author.id
        )
        return await ctx.send_success("Removed the timezone")

    @hybrid_command(
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

    @hybrid_command(
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

    @command(
        help="utility",
        usage="[message]",
        description="uwify a message",
        aliases=["uwu"],
    )
    async def uwuify(self, ctx: Context, *, text: str):
        uwu = uwuipy.uwuipy()
        uwu_message = uwu.uwuify(text)
        await ctx.send(uwu_message)

    @command(
        description="Get the dominant color from an image",
        usage="[image url]",
        help="utility",
    )
    async def dominant(self, ctx):
        if not ctx.message.attachments:
            return await ctx.send("Please provide an image")

        img = Image.open(io.BytesIO(await ctx.message.attachments[0].read()))
        img.thumbnail((32, 32))
        colors = colorgram.extract(img, 3)
        rgb = colors[0].rgb
        hexx = discord.Color.from_rgb(r=rgb.r, g=rgb.g, b=rgb.b)
        hex_color = hex(hexx.value)

        embed = discord.Embed(color=hexx)
        embed.add_field(name="RGB", value=f"rgb({rgb.r}, {rgb.g}, {rgb.b})")
        embed.add_field(name="HEX", value=f"{hex_color}")

        await ctx.reply(embed=embed)

    @command(help="utility", aliases=["fnshop"])
    async def fortniteshop(self, ctx):
        now = datetime.datetime.now()
        url = f"https://bot.fnbr.co/shop-image/fnbr-shop-{now.day}-{now.month}-{now.year}.png"
        embed = discord.Embed(color=self.bot.color, title="", description="")
        embed.set_image(url=url)
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        await ctx.send(embed=embed)

    @command(help="utility", descriprion="get a track name from sound")
    async def shazam(self, ctx):
        if not ctx.message.attachments:
            return await ctx.send_warning("Please provide a video")
        song = await Shazam().recognize_song(await ctx.message.attachments[0].read())
        embed = discord.Embed(
            color=self.bot.color,
            title="Found",
            description=f"> **[{song['track']['share']['text']}]({song['track']['share']['href']})**",
        )
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        await ctx.reply(embed=embed)

    @hybrid_command(description="view a user avatar", aliases=["av"], help="utility")
    async def avatar(self, ctx, *, user: Union[User, Member] = Author):
        embed = discord.Embed(description=f"{user.name}'s avatar")
        embed.set_image(url=user.display_avatar)
        await ctx.send(embed=embed)

    @command(
        description="gets the invite link with administrator permission of a bot",
        usage="[bot id]",
        help="utility",
    )
    async def getbotinvite(self, ctx, id: User):
        if not id.bot:
            return await ctx.send_error("This is not a bot")
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label=f"invite {id.name}",
                url=f"https://discord.com/api/oauth2/authorize?client_id={id.id}&permissions=8&scope=bot%20applications.commands",
            )
        )
        await ctx.reply(view=view)

    @command(
        description="get the first message from a channel",
        usage="<channel>",
        aliases=["firstmsg"],
        help="utility",
    )
    async def firstmessage(self, ctx: Context, *, channel: TextChannel = None):
        channel = channel or ctx.channel
        messages = [mes async for mes in channel.history(oldest_first=True, limit=1)]
        message = messages[0]
        embed = Embed(
            color=self.bot.color,
            title="first message in {}".format(channel),
            description=message.content,
            timestamp=message.created_at,
        )
        embed.set_author(
            name=message.author.name, icon_url=message.author.display_avatar.url
        )
        view = View()
        view.add_item(Button(label="message", url=message.jump_url))
        await ctx.reply(embed=embed, view=view)

    @command(
        description="get role informations",
        help="utility",
        usage="[role]",
        aliases=["ri"],
    )
    async def roleinfo(self, ctx: Context, *, role: Union[Role, str]):
        if isinstance(role, str):
            role = ctx.find_role(role)
            if not role:
                return await ctx.send_warning(f"**{role.name}** is not a valid role")

        embed = Embed(
            color=role.color,
            title="@{} - `{}`".format(role.name, role.id),
            timestamp=role.created_at,
        )
        embed.set_thumbnail(
            url=role.display_icon if not isinstance(role.display_icon, str) else None
        )
        embed.add_field(
            name="stats",
            value=f"**hoist:** {str(role.hoist).lower()}\n**mentionable:** {str(role.mentionable).lower()}\n**members:** {str(len(role.members))}",
        )
        await ctx.reply(embed=embed)

    @command(
        aliases=["s"],
        description="check the latest deleted message from a channel",
        help="utility",
    )
    async def snipe(self, ctx: Context, *, number: int = 1):
        check = await self.bot.db.fetch(
            "SELECT * FROM snipe WHERE guild_id = {} AND channel_id = {}".format(
                ctx.guild.id, ctx.channel.id
            )
        )
        if len(check) == 0:
            return await ctx.send_error("🔎 No deleted messages found in this channel")
        if number > len(check):
            return await ctx.send_warning(
                f"snipe limit is **{len(check)}**".capitalize()
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

    @hybrid_command(
        description="check how many members does your guild has",
        aliases=["mc"],
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
            name=f"members +{len([m for m in ctx.guild.members if (datetime.datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 3600*24 and not m.bot])}",
            value=h,
        )
        embed.add_field(name="total", value=ctx.guild.member_count)
        embed.add_field(name="bots", value=b)
        await ctx.reply(embed=embed)

    @command(description="see all banned members", help="utility")
    async def bans(self, ctx: Context):
        banned = [m async for m in ctx.guild.bans()]
        if len(banned) == 0:
            return await ctx.send_warning("There are no banned people here")
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
        number.append(
            Embed(
                color=self.bot.color,
                title=f"banned ({len(banned)})",
                description=messages[i],
            )
        )
        await ctx.paginator(number)

    @hybrid_command(
        description="clear the guilds snipes", help="utility", aliases=["cs"]
    )
    @Perms.get_perms("manage_messages")
    async def clearsnipes(self, ctx: Context):
        lis = ["snipe"]
        for l in lis:
            await self.bot.db.execute(f"DELETE FROM {l}")
        return await ctx.send_success("Cleared the guild snipes")

    @commands.hybrid_command(aliases=["foryou", "foryoupage"])
    async def fyp(self, ctx: PretendContext):
        """
        Get a random tiktok video
        """

        async with ctx.typing():
            recommended = await self.bot.session.get_json(
                url="https://www.tiktok.com/api/recommend/item_list/?WebIdLastTime=1709562791&aid=1988&app_language=en&app_name=tiktok_web&browser_language=en-US&browser_name=Mozilla&browser_online=true&browser_platform=Win32&browser_version=5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F124.0.0.0%20Safari%2F537.36&channel=tiktok_web&clientABVersions=70508271%2C72097972%2C72118536%2C72139452%2C72142433%2C72147654%2C72156694%2C72157773%2C72174908%2C72183344%2C72191581%2C72191933%2C72203590%2C72211002%2C70405643%2C71057832%2C71200802%2C71957976&cookie_enabled=true&count=9&coverFormat=2&device_id=7342516164603889184&device_platform=web_pc&device_type=web_h264&focus_state=true&from_page=fyp&history_len=3&isNonPersonalized=false&is_fullscreen=false&is_page_visible=true&language=en&odinId=7342800074206741537&os=windows&priority_region=&pullType=1&referer=&region=BA&screen_height=1440&screen_width=2560&showAboutThisAd=true&showAds=false&tz_name=Europe%2FLondon&watchLiveLastTime=1713523355360&webcast_language=en&msToken=W3zoVLSFi9M0BsPE6uC63GCdeoVC7hmjRNelZIe-7FP7x-1LRee6WYHYfpWXg3NYPoreJf_dMxfRWTZprVN8UU70_IaHnBMNirtZIRNp2QuR1nBivJgnetgiM-XTh7_KGbNswVs=&X-Bogus=DFSzswVOmtvANegtt2bDG-OckgSu&_signature=_02B4Z6wo00001BozSvQAAIDBhqj5OL8769AaM05AAGCne"
            )
            recommended = recommended["itemList"][0]
            embed = discord.Embed(color=self.bot.color)
            embed.description = f'[{recommended["desc"]}](https://tiktok.com/@{recommended["author"]["uniqueId"]}/video/{recommended["id"]})'

            embed.set_author(
                name="@" + recommended["author"]["uniqueId"],
                icon_url=recommended["author"]["avatarLarger"],
            )
            embed.set_footer(
                text=f"❤️ {self.human_format(recommended['stats']['diggCount'])} 💬 {self.human_format(recommended['stats']['commentCount'])} 🔗 {self.human_format(recommended['stats']['shareCount'])} ({self.human_format(recommended['stats']['playCount'])} views)"
            )

            final = await self.bot.session.get_json(
                "https://tikwm.com/api/",
                params={
                    "url": f'https://tiktok.com/@{recommended["author"]["uniqueId"]}/video/{recommended["id"]}'
                },
            )
            await ctx.reply(
                embed=embed,
                file=discord.File(
                    fp=await self.bot.getbyte(url=final["data"]["play"]),
                    filename="pretendtiktok.mp4",
                ),
            )


async def setup(bot):
    await bot.add_cog(utility(bot))
