import math
import os
import re
import typing
from datetime import datetime, timedelta
from difflib import get_close_matches
from io import BytesIO
from typing import Annotated, List, Optional, Union  # type: ignore

import aiohttp
import discord
import pytz
from aiohttp import ContentTypeError
from discord import Embed, Interaction, app_commands  # type: ignore
from discord.app_commands import Choice
from discord.ext import commands
from discord.ext.commands import CommandError, param
from discord.utils import chunk_list  # noqa: F401
from GeoPython import Client
from munch import DefaultMunch, Munch
from tools.important import Context  # type: ignore
from tools.important.subclasses.color import (color_info,  # type: ignore
                                              get_dominant_color)
from tools.important.subclasses.command import Message  # noqa: F401
from tools.important.subclasses.command import (Member,  # type: ignore
                                                NonAssignedRole, User)
from tools.shazam import Recognizer  # type: ignore
from tools.wock import Wock  # type: ignore
from typing_extensions import NotRequired, Type
from weather import WeatherClient  # type: ignore
from weather.weathertypes import Kind  # type: ignore

if typing.TYPE_CHECKING:
    pass
from aiohttp import ClientSession as Session
from bs4 import BeautifulSoup
from cashews import cache
from cogs.lastfm import shorten
from humanize import intword
from loguru import logger
from munch import DefaultMunch
from pydantic import BaseModel


class plural:
    def __init__(
        self: "plural",
        value: int | str | typing.List[typing.Any],
        number: bool = True,
        md: str = "",
    ):
        self.value: int = (
            len(value)
            if isinstance(value, list)
            else (
                (
                    int(value.split(" ", 1)[-1])
                    if value.startswith(("CREATE", "DELETE"))
                    else int(value)
                )
                if isinstance(value, str)
                else value
            )
        )
        self.number: bool = number
        self.md: str = md

    def __format__(self: "plural", format_spec: str) -> str:
        v = self.value
        singular, sep, plural = format_spec.partition("|")
        plural = plural or f"{singular}s"
        result = f"{self.md}{v:,}{self.md} " if self.number else ""

        result += plural if abs(v) != 1 else singular
        return result


DISCORD_FILE_PATTERN = r"(https://|http://)?(cdn\.|media\.)discord(app)?\.(com|net)/(attachments|avatars|icons|banners|splashes)/[0-9]{17,22}/([0-9]{17,22}/(?P<filename>.{1,256})|(?P<hash>.{32}))\.(?P<mime>[0-9a-zA-Z]{2,4})?"


def format_int(n: int) -> str:
    i = intword(n)
    i = (
        i.replace(" million", "m")
        .replace(" billion", "b")
        .replace(" trillion", "t")
        .replace(" thousand", "k")
        .replace(".0", "")
    )
    return i


cache.setup("mem://")


class Image:
    def __init__(self: "Image", fp: bytes, url: str, filename: str):
        self.fp = fp
        self.url = url
        self.filename = filename

    @property
    def buffer(self: "Image") -> BytesIO:
        buffer = BytesIO(self.fp)
        buffer.name = self.filename

        return buffer

    @classmethod
    async def fallback(cls: Type["Image"], ctx: Context) -> "Image":
        if ref := ctx.message.reference:
            message = await ctx.channel.fetch_message(ref.message_id)
        else:
            message = ctx.message
        if not message.attachments:
            raise CommandError("You must provide an image!")

        attachment = message.attachments[0]
        if not attachment.content_type:
            raise CommandError(
                f"The [attachment]({attachment.url}) provided is invalid!"
            )

        elif not attachment.content_type.startswith("image"):
            raise CommandError(
                f"The [attachment]({attachment.url}) provided must be an image file."
            )

        buffer = await attachment.read()
        return cls(
            fp=buffer,
            url=attachment.url,
            filename=attachment.filename,
        )

    @classmethod
    async def convert(cls: Type["Image"], ctx: Context, argument: str) -> "Image":
        if not (match := re.match(DISCORD_FILE_PATTERN, argument)):
            raise CommandError("The URL provided doesn't match the **Discord** regex!")

        response = await ctx.bot.session.get(match.group())
        if not response.content_type.startswith("image"):
            raise CommandError(f"The [URL]({argument}) provided must be an image file.")

        buffer = await response.read()
        return cls(
            fp=buffer,
            url=match.group(),
            filename=match.group("filename") or match.group("hash"),
        )


class InstagramUser(BaseModel):
    bio: Optional[str] = None
    followers: Optional[int] = None
    following: Optional[int] = None
    username: Optional[str] = None
    posts: Optional[int] = 0
    profile_pic: Optional[str] = None
    url: Optional[str] = None
    fullname: Optional[str] = None


class UrbanDefinition(BaseModel):
    definition: str
    permalink: str
    thumbs_up: int
    author: str
    word: str
    defid: int
    current_vote: str
    written_on: str
    example: str
    thumbs_down: int


@cache(ttl=1200, key="ig:{username}")
async def get_instagram_user(username: str) -> Optional[InstagramUser]:
    async with Session() as session:
        async with session.get(
            f"https://dumpoir.com/v/{username}",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0"
            },
        ) as response:
            data = await response.read()
    try:
        soup = BeautifulSoup(data, "html.parser")
        bio_element = soup.select_one(
            "#user-page > div.user > div > div.col-md-5.my-3 > div"
        )
        bio = bio_element.get_text(strip=True) if bio_element else ""
        result = {
            "bio": bio,  # soup.select_one('#user-page > div.user > div > div.col-md-5.my-3 > div').get_text(strip=True) if bio,
            "followers": soup.select_one(
                "#user-page > div.user > div > div.col-md-4.col-8.my-3 > ul > li:nth-child(2)"
            )
            .get_text(strip=True)
            .replace(" Followers", ""),
            "following": soup.select_one(
                "#user-page > div.user > div > div.col-md-4.col-8.my-3 > ul > li:nth-child(3)"
            )
            .get_text(strip=True)
            .replace(" Following", ""),
            "fullname": soup.select_one(
                "#user-page > div.user > div > div.col-md-4.col-8.my-3 > div > a > h1"
            ).get_text(strip=True),
            "posts": soup.select_one(
                "#user-page > div.user > div > div.col-md-4.col-8.my-3 > ul > li:nth-child(1)"
            )
            .get_text(strip=True)
            .replace(" Posts", ""),
            "profile_pic": soup.select_one(
                "#user-page > div.user > div.row > div > div.user__img"
            )["style"]
            .replace("background-image: url('", "")
            .replace("');", ""),
            "url": f"https://www.instagram.com/{username.replace('@', '')}",
            "username": username,
        }
        try:
            result["followers"] = int(result["followers"].replace(" ", ""))
        except Exception:
            result["followers"] = 0
        try:
            result["posts"] = int(result["posts"].replace(" ", ""))
        except Exception:
            result["posts"] = 0
        try:
            result["following"] = int(result["following"].replace(" ", ""))
        except Exception:
            result["following"] = 0
        return InstagramUser(**result)
    except Exception as e:
        if hasattr(e, "response") and e.response.status_code == 404:
            raise Exception("Error: Akun tidak ditemukan")
        elif hasattr(e, "response") and e.response.status_code == 403:
            raise Exception("Error: Akunnya Di Private")
        else:
            raise Exception("Error: Failed to fetch Instagram profile")


class Object:
    def __init__(self, data: dict):
        self.data = data

    def from_data(self):
        return DefaultMunch(object(), self.data)


class AuditLogParser:
    def __init__(self, bot: Wock, logs: List[discord.AuditLogEntry]):
        self.bot = bot
        self.logs = logs

    def do_parse(self):
        embeds = []
        embed = discord.Embed(
            title="Audit Logs", color=self.bot.color, url=self.bot.domain
        )

        i = 0
        for log in self.logs:
            if log.target is not None:
                if "Object" in str(log.target):
                    t = f"**Target:** {str(log.target.id)}\n"
                else:
                    t = f"{str(log.target)} ({log.target.id})"
                target = f"**Target:** {t}\n"
            else:
                target = ""
            embed.add_field(
                name=f"{log.user} ({log.user.id})",
                value=f"** Action: ** {str(log.action).split('.')[1].replace('_', ' ')}\n**Reason: ** {log.reason}\n{target}**Created: ** < t: {round(log.created_at.timestamp())}: R >",
                inline=False,
            )
            i += 1
            if i == 5:
                embeds.append(embed)
                embed = discord.Embed(
                    title="Audit Logs", color=self.bot.color, url=self.bot.domain
                )
                i = 0
        return embeds


def get_lines():
    lines = 0
    for directory in [x[0] for x in os.walk("./") if ".git" not in x[0]]:
        for file in os.listdir(directory):
            if file.endswith(".py"):
                lines += len(open(f"{directory}/{file}", "r").read().splitlines())
    return lines


# time humanizer
def humanize_timedelta(dt):
    timedelta_str = []
    if dt.days:
        days = dt.days
        timedelta_str.append(f'{days} day{"s" if days > 1 else ""}')
        dt -= timedelta(days=days)
    seconds = dt.seconds
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60

    if hours:
        timedelta_str.append(f'{hours} hour{"s" if hours > 1 else ""}')
    if minutes:
        timedelta_str.append(f'{minutes} minute{"s" if minutes > 1 else ""}')
    if seconds:
        timedelta_str.append(f'{seconds} second{"s" if seconds > 1 else ""}')
    return ", ".join(timedelta_str)


TREYTEN_API_CACHE = {}


class Tempature(BaseModel):
    celsius: Union[int, float]
    fahrenheit: Union[int, float]


class WeatherResponse(BaseModel):
    cloud_pct: Union[int, float]
    temp: Tempature
    feels_like: Tempature
    humidity: Union[int, float]
    min_temp: Tempature
    max_temp: Tempature
    wind_speed: Union[int, float]
    wind_degrees: Union[int, float]
    sunrise: Union[int, float]
    sunset: Union[int, float]


class MinecraftUser(commands.Converter):
    async def convert(
        self: "MinecraftUser", ctx: "Context", argument: str
    ) -> Optional[str]:
        if len(argument.split()) > 1:
            raise CommandError("Please provide a **valid** minecraft user.")

        data = await (
            await ctx.bot.session.get(
                f"https://playerdb.co/api/player/minecraft/{argument}"
            )
        ).json()
        if not data["data"]:
            raise CommandError("I couldn't find that minecraft user.")
        player = data["data"]["player"]
        player["body"] = f"https://crafthead.net/armor/body/{player['id']}"
        del player["meta"]
        return Munch(player)


class CategoryTransformer(app_commands.Transformer):
    async def autocomplete(
        self, interaction: Interaction, value: str
    ) -> list[Choice[str]]:
        bot: commands.Bot = interaction.client  # type: ignore
        return [
            Choice(name=cog.qualified_name, value=name)
            for name, cog in bot.cogs.items()
            if cog.qualified_name.casefold().startswith(value.casefold())
        ][:25]

    async def transform(self, interaction: Interaction, value: str) -> commands.Cog:
        cog: commands.Cog | None = interaction.client.get_cog(value)  # type: ignore
        if cog is None:
            raise ValueError(f"Category {value} not found.")
        else:
            return cog


class CommandTransformer(app_commands.Transformer):
    async def autocomplete(
        self, interaction: Interaction, value: str
    ) -> list[Choice[str]]:
        bot: commands.Bot = interaction.client  # type: ignore
        return [
            Choice(name=command.qualified_name, value=command.qualified_name)
            for command in bot.walk_commands()
            if command.qualified_name.casefold().startswith(value.casefold())
        ][:25]

    async def transform(self, interaction: Interaction, value: str) -> commands.Command:
        command: commands.Command | None = interaction.client.get_command(value)  # type: ignore
        if command is None:
            raise ValueError(f"Command {value} not found.")
        else:
            return command


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recognizer = Recognizer()
        self.client = Client()
        self.weather_client = WeatherClient()
        self.command_count = len(
            [
                cmd
                for cmd in list(self.walk_commands())
                if cmd.cog_name not in ("Jishaku", "events", "Owner")
            ]
        )

    @app_commands.command()
    async def help_(
        self,
        interaction: Interaction,
        category: Annotated[commands.Cog, CategoryTransformer] | None = None,
        command: Annotated[commands.Command, CommandTransformer] | None = None,
    ):
        if category is not None:
            pass  # type: ignore
        elif command is not None:
            pass  # type: ignore
        else:
            pass  # type: ignore

        ctx = await self.bot.get_context(interaction)
        return await ctx.send_help()

        self.client = Client()  # type: ignore

    async def find_timezone(self, city: str, country: Optional[str] = None):  # type: ignore
        if data := await self.client.lookup(city=city):
            return data.timezone
        else:
            if pytz.timezone(city):  # type: ignore
                return city
            else:
                return None

    async def get_time(self, timezone: str):
        return int(datetime.now(tz=pytz.timezone(timezone)).timestamp())  # type: ignore

    @commands.command(
        name="reverse",
        aliases=["reversesearch"],
        brief="Reverse search an image",
        usage=",reverse {image}",
    )
    async def reverse(
        self,
        ctx: Context,
        *,
        image: Image = param(
            default=Image.fallback,
            description="The image to search.",
        ),
    ):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    "POST",
                    "https://tineye.com/api/v1/result_json/",
                    params={
                        "sort": "score",
                        "order": "desc",
                    },
                    data={
                        "image": image.fp,
                    },
                ) as response:
                    data = DefaultMunch.fromDict(await response.json())
                    if not data.matches:
                        return await ctx.fail(
                            f"Couldn't find any matches for [`{data.query.hash}`]({image.url})!"
                        )
        except ContentTypeError:
            return await ctx.fail(
                f"Couldn't find any matches for [`this image`]({image.url})!"
            )

        embed = Embed(
            title="Reverse Image Lookup",
            description=(
                f"Found {plural(data.num_matches, md='`'):match|matches} for [`{image.filename}`]({image.url})."
            ),
            color=self.bot.color,
        )

        embed.set_thumbnail(url=image.url)

        for match in data.matches[:4]:
            backlink = match.backlinks[0]

            embed.add_field(
                name=match.domain,
                value=f"[`{shorten(backlink.backlink.replace('https://', '').replace('http://', ''))}`]({backlink.url})",
                inline=False,
            )

        return await ctx.send(embed=embed)

    @commands.group(
        name="timezone",
        aliases=["tz", "time"],
        invoke_without_command=True,
        brief="get the local time of a user if set",
        example=",timezone @o_5v",
    )
    async def timezone(
        self, ctx: Context, member: discord.Member | discord.User = commands.Author
    ):
        if data := await self.bot.db.fetchval(
            """SELECT tz FROM timezone WHERE user_id = $1""", member.id
        ):
            return await ctx.success(
                f"{member.mention}'s current time is <t:{await self.get_time(data)}:F>"
            )
        else:
            return await ctx.fail(
                f"{member.mention} does not have their time set with `timezone set`"
            )

    @timezone.command(
        name="set",
        brief="set a timezone via location or timezone",
        example=",timezone set New York/et",
    )
    async def timezone_set(self, ctx: Context, *, timezone: str):
        data = await self.find_timezone(city=timezone)
        if data:
            await self.bot.db.execute(
                """INSERT INTO timezone (user_id, tz) VALUES($1, $2) ON CONFLICT(user_id) DO UPDATE SET tz = excluded.tz""",
                ctx.author.id,
                data,
            )
            return await ctx.success(
                f"set your current time to <t:{await self.get_time(data)}:F>"
            )
        else:
            return await ctx.fail(f"could not find a timezone for `{timezone}`")

    @commands.command(
        brief="Check the bot's latency",
        description="Shows the current latency of the bot.",
        example=",ping",
    )
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"*...**{latency}**ms*")

    @commands.command(
        name="weather",
        brief="Show the current weather of a certain city",
        example=",weather columbia",
    )
    async def weather(self, ctx: Context, *, city: str):
        try:
            weather_dat = await self.weather_client.get(city)
            weather_data = weather_dat.current_condition[0]
            embed = discord.Embed(
                title=f"{Kind(int(weather_data.weatherCode)).emoji} weather in {city}",
                description=f"** Temp: ** {weather_data.temp_F}\n**Feels Like: ** {weather_data.FeelsLikeF}\n**Humidity: ** {weather_data.humidity} %",
                color=self.bot.color,
            )

            return await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(e)
            return await ctx.fail(f"**Could not find** the weather for `{city}`")

    @commands.command(
        name="bans", brief="Show banned users in the guild", example=",bans"
    )
    @commands.has_permissions(moderate_members=True)
    async def bans(self, ctx: Context):
        try:
            bans = [ban async for ban in ctx.guild.bans(limit=500)]
            rows = [
                f"`{i}` {self.try_escape(ban)}" for i, ban in enumerate(bans, start=1)
            ]
            if len(rows) == 0:
                return await ctx.fail("**no bans found in guild**")
            content = discord.Embed(
                title=f"{ctx.guild.name}'s bans", color=self.bot.color
            )
            return await self.bot.dummy_paginator(ctx, content, rows)
        except Exception:  # type: ignore
            return await ctx.fail("**no bans found in guild**")

    @commands.command(
        name="color",
        aliases=["clr", "hex"],
        brief="get information about a color",
        example=",color red",
    )
    async def color(
        self, ctx: Context, *, query: Optional[Union[str, User, Member]] = None
    ):
        try:
            if isinstance(query, User):
                _ = await get_dominant_color(query)
                logger.info(_)
            elif isinstance(query, Member):
                _ = await get_dominant_color(query)
                logger.info(_)
            else:
                if query is None:
                    if len(ctx.message.attachments) > 0:
                        _ = await get_dominant_color(ctx.message.attachments[0].url)
                    else:
                        d = await self.bot.get_image(ctx, query)
                        if d is None:
                            return await ctx.send_help()
                        _ = await get_dominant_color(d)
                else:
                    if query.startswith("http"):
                        _ = await get_dominant_color(query)
                    else:
                        _ = query
            return await color_info(ctx, _)
        except Exception:
            return await ctx.send_help()

    @commands.command(
        name="botinfo",
        aliases=["bi", "system", "sys"],
        brief="View wock bots information on its growth",
        example=",botinfo",
    )
    async def botinfo(self, ctx: Context):
        get_lines()  # type: ignore
        stat = await self.bot.get_statistics()
        embed = discord.Embed(
            color=self.bot.color,
            title="invite",
            url="https://discord.com/api/oauth2/authorize?client_id=1203419316230422548&permissions=8&scope=bot",
        )

        embed.add_field(
            name="**__Client__**",
            value=f""">>> **Latency:** {round(self.bot.latency * 1000, 2)} \n**CPU:** {
                self.bot.process.cpu_percent()}% \n**Guilds:** {await self.bot.guild_count()}""",
        )
        embed.add_field(
            name="__**Statistics**__",
            value=f""">>> **Users:** {await self.bot.user_count():,}
**Channels:** {await self.bot.channel_count():,}
**Roles:** {await self.bot.role_count():,}""",
            inline=False,
        )
        embed.add_field(
            name="__**Code**__",
            value=f""">>> **Lines**: {stat.lines}
**Classes**: {stat.classes}
**Files**: {stat.files}""",
            inline=False,
        )
        embed.description = f"<:uptime:1223394718067462175> {stat.uptime}"
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar)
        embed.set_footer(text="Created by: @icy.com | 1188282998534193152")
        embed.set_thumbnail(url=self.bot.user.avatar)
        await ctx.send(embed=embed)

    @commands.command(
        name="members",
        description="Show server statistics",
        example=",members",
        aliases=[
            "membercount",
            "serverstats",
        ],
    )
    async def server_stats(self, ctx):
        guild = ctx.guild
        total_users = len(guild.members)
        total_members = len([member for member in guild.members if not member.bot])
        total_bots = total_users - total_members
        e = discord.Embed(
            color=self.bot.color,
            title=f"**__{guild.name}__**",
        )
        e.set_thumbnail(url=guild.icon)  # Set server icon as thumbnail
        # Author information (user who used the command)
        e.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)
        e.add_field(name="Users", value=f"`{total_users}`", inline=True)
        e.add_field(name="Members", value=f"`{total_members}`", inline=True)
        e.add_field(name="Bots", value=f"`{total_bots}`", inline=True)
        await ctx.send(embed=e)

    @commands.command(
        name="serverinfo",
        aliases=["guildinfo", "sinfo", "ginfo", "si", "gi"],
        brief="view information on the server",
        example=",serverinfo",
    )
    async def serverinfo(self, ctx: Context, *, guild: discord.Guild = None):
        guild = ctx.guild if guild is None else guild
        invite = "None"
        if guild.vanity_url is not None:
            invite = f"[{guild.vanity_url_code}]({guild.vanity_url})"
        # Additional information
        e = discord.Embed(
            color=self.bot.color,
            title=f"{guild.name}",
            description=f'** __Created: __ ** \n{discord.utils.format_dt(guild.created_at, style="F")}',
        )
        # Stats Category
        e.add_field(
            name="**__Server__**",
            value=f""">>> **Members:** {guild.member_count}
**Level:** {guild.premium_tier}/3
**Vanity:** {invite}""",
            inline=False,
        )
        e.add_field(
            name="**__Channels__**",
            value=f""">>> **Text:** {len(guild.text_channels)}
**Voice:** {len(guild.voice_channels)}
**Categories:** {len(guild.categories)}""",
            inline=False,
        )
        e.add_field(
            name="**__Utility__**",
            value=f""">>> **Roles:** {len(guild.roles)}
**Emotes:** {len(guild.emojis)}
**Boosts:** {guild.premium_subscription_count}""",
            inline=False,
        )
        e.add_field(
            name="**__Design__**",
            value=f""">>> **Icon:** {f"[Here]({guild.icon.url})" if guild.icon else 'None'}
**Splash:** {f"[Here]({guild.splash.url})" if guild.splash else 'None'}
**Banner:** {f"[Here]({guild.banner.url})" if guild.banner else 'None'}""",
        )
        e.set_footer(text=f"Owner: @{guild.owner} | Guild id: {guild.id}")
        if guild.icon:
            e.set_thumbnail(url=guild.icon)
        e.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar)
        await ctx.send(embed=e)

    @commands.command(
        name="created",
        description="View when the server was created.",
        aliases=["servercreated", "sc"],
    )
    async def created(self, ctx, *, guild: discord.Guild = None):  # type: ignore
        e = discord.Embed(
            color=self.bot.color,
            description=f'> **Server Created ** {discord.utils.format_dt(ctx.guild.created_at, style="F")}',
        )

        e.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar)

        await ctx.send(embed=e)

    @commands.command(
        name="invite", description="Invite the bot to your server", example="invite"
    )
    async def invite(self, ctx):
        invite = self.bot.invite_url
        embed = discord.Embed(
            color=self.bot.color,
            description=f"click **[here]({invite})** to invite the bot.",
        )
        await ctx.send(embed=embed)

    @commands.command(
        aliases=["ui", "user", "userinfo"],
        example=",userinfo @o_5v",
        brief="View information on a users account",
    )
    async def whois(self, ctx, user: Member = None):
        """View some information on a user"""

        user = user or ctx.author

        mutual_guilds = tuple(g for g in self.bot.guilds if g.get_member(user.id))

        if not user:
            return await ctx.fail("Member not found")

        position = sorted(ctx.guild.members, key=lambda m: m.joined_at).index(user) + 1

        badges = []

        flags = user.public_flags

        emojis = {
            "nitro": "<:vile_nitro:1022941557541847101>",
            "hypesquad_brilliance": "<:vile_hsbrilliance:1022941561392209991>",
            "hypesquad_bravery": "<:vile_hsbravery:1022941564349194240>",
            "hypesquad_balance": "<:vile_hsbalance:1022941567318765619>",
            "bug_hunter": "<:vile_bhunter:991776532227969085>",
            "bug_hunter_level_2": "<:vile_bhunterplus:991776477278388386>",
            "discord_certified_moderator": "<:vile_cmoderator:1022943277340692521>",
            "early_supporter": "<:vile_esupporter:1022943630945685514>",
            "verified_bot_developer": "<:vile_dev:1042082778629537832>",
            "partner": "<:vile_partner:1022944710895075389>",
            "staff": "<:vile_dstaff:1022944972858720327>",
            "verified_bot": "<:vile_vbot:1022945560094834728>",
            "server_boost": "<:vile_sboost:1022950372576342146>",
            "active_developer": "<:vile_activedev:1043160384124751962>",
            "pomelo": "<:pomelo:1122143950719954964>",
            "web_idle": "<:status_web_idle:1212056346606702603>",
            "web_dnd": "<:status_web_dnd:1212056400298254367>",
            "web_online": "<:status_web_online:1212056442224382053>",
            "desktop_dnd": "<:status_desktop_dnd:1212056925475180595>",
            "desktop_idle": "<:status_desktop_idle:1212056962418610266>",
            "desktop_online": "<:status_desktop_online:1212056991170568223>",
            "mobile_dnd": "<:status_mobile_dnd:1212058839969701980>",
            "mobile_idle": "<:status_mobile_idle:1212058872521424946>",
            "mobile_online": "<:status_mobile_online:1212059013307437108>",
            "web_offline": "",
            "mobile_offline": "",
        }

        for flag in (
            "bug_hunter",
            "bug_hunter_level_2",
            "discord_certified_moderator",
            "hypesquad_balance",
            "hypesquad_bravery",
            "hypesquad_brilliance",
            "active_developer",
            "early_supporter",
            "partner",
            "staff",
            "verified_bot",
            "verified_bot_developer",
        ):
            if getattr(flags, flag, False) is True:
                badges.append(emojis[flag])

        def is_boosting(u):
            for g in mutual_guilds:
                if g.get_member(u.id).premium_since is not None:
                    return True

            return False

        if is_boosting(user) is True:
            badges.extend((emojis.get("nitro"), emojis.get("server_boost")))

        if user.discriminator == "0":
            badges.append(emojis.get("pomelo"))

        devices = (
            ", ".join(
                tuple(
                    k
                    for k, v in {
                        "desktop": user.desktop_status,
                        "web": user.web_status,
                        "mobile": user.mobile_status,
                    }.items()
                    if v.name != "offline"
                )
            )
            or "none"
        )

        badges = " ".join(badges)

        status_emoji = " "

        if split_devices := devices.split(","):
            device = split_devices[0].strip()

            if device == "none":
                device = "web"

            status_emoji = (
                f" {emojis[f'{device.lstrip().rstrip()}_{user.status.name.lower()}']} "
            )

        status = "none"

        if user.activity:
            start = user.activity.type.name.capitalize()

            if start == "Custom":
                start = ""

            if start == "Listening":
                start = "Listening to"

            status = f"{start} {user.activity.name}"

        embed = discord.Embed(
            color=self.bot.color,
            title=f"Status:\n{status_emoji}{status}",
        )

        embed.add_field(
            name="**__Account created__**",
            value=f"""> <t:{round(user.created_at.timestamp())}:D>
> <t:{round(user.created_at.timestamp())}:R>""",
            inline=False,
        )

        embed.add_field(
            name="**__Joined server__**",
            value=f"""> <t:{round(user.joined_at.timestamp())}:D>
> <t:{round(user.joined_at.timestamp())}:R>""",
            inline=False,
        )

        if user.premium_since:
            embed.add_field(
                name="**__Boosted server__**",
                value=f"""> <t:{round(user.joined_at.timestamp())}:D>
> <t:{round(user.joined_at.timestamp())}:R>""",
            )

        if user.roles:
            if len(user.roles) > 5:
                roles = (
                    ", ".join(
                        [role.mention for role in list(reversed(user.roles[1:]))[:5]]
                    )
                    + f" + {len(user.roles) - 5} more"
                )

            else:
                roles = ", ".join(
                    [role.mention for role in list(reversed(user.roles[1:]))[:5]]
                    + ["@everyone"]
                )

            embed.add_field(name="**__Roles__**", value=f"{roles}", inline=False)

        embed.set_author(name=f"{user.name} ({user.id})", icon_url=user.display_avatar)

        embed.set_thumbnail(url=user.display_avatar)

        embed.set_footer(
            text=f"{len(mutual_guilds)} mutuals, Join position: {position}"
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="serveravatar",
        description="View the avatar of a user for a server",
        example=",serveravatar @o_5v",
        aliases=["sav"],
    )
    async def serveravatar(self, ctx, *, user: Member = None):
        user = ctx.author if user is None else user

        avatar_url = user.guild_avatar if user.guild_avatar else user.display_avatar

        e = discord.Embed(
            title=f"{user.name}'s server avatar", url=avatar_url, color=self.bot.color
        )
        e.set_image(url=avatar_url)
        e.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.avatar)
        await ctx.send(embed=e)

    @commands.command(
        name="avatar",
        brief="View the avatar of a user",
        example=",avatar @o_5v",
        aliases=["av"],
    )
    async def avatar(self, ctx, *, user: User = None):
        user = user or ctx.author
        if user is None:
            user = await self.bot.fetch_user(user)
        avatar: str = user.avatar.url if user.avatar else user.display_avatar.url
        e = discord.Embed(
            title=f"{user.name}'s user avatar",
            url=user.default_avatar,
            color=self.bot.color,
        )
        e.set_image(url=avatar)
        e.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar
        )
        await ctx.send(embed=e)

    @commands.command(
        name="banner",
        brief="View the banner of a user",
        example=",banner @o_5v",
        aliases=["userbanner", "ub"],
    )
    async def banner(self, ctx, *, user: Member = None):
        member = user or ctx.author
        user = await self.bot.fetch_user(member.id)
        if user.banner:
            e = discord.Embed(
                title=f"{user.name}'s banner", url=user.banner, color=self.bot.color
            )
            e.set_author(
                name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar
            )
            e.set_image(url=user.banner)
            await ctx.send(embed=e)
        elif user.accent_color:
            await ctx.fail("User has no banner set.")
        else:
            await ctx.fail(" No banner image or color set.")

    @commands.command(
        name="guildicon",
        brief="View the icon of a server",
        example=",guildicon",
        aliases=["icon", "servericon", "sicon", "gicon"],
    )
    async def servericon(self, ctx, *, guild: discord.Guild = None):
        guild = guild or ctx.guild
        e = discord.Embed(
            title=f"{guild.name}'s icon", url=guild.icon, color=self.bot.color
        )
        e.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar
        )
        e.set_image(url=guild.icon)
        await ctx.send(embed=e)

    @commands.command(
        name="guildbanner",
        brief="View the banner of a server",
        example=",guildbanner",
        aliases=["sb", "serverbanner"],
    )
    async def serverbanner(self, ctx, *, guild: discord.Guild = None):
        guild = ctx.guild if guild is None else guild
        e = discord.Embed(
            title=f"{guild.name}'s banner", url=guild.banner, color=self.bot.color
        )
        e.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar
        )
        e.set_image(url=guild.banner)
        await ctx.send(embed=e)

    @commands.command(
        name="guildsplash",
        brief="View the splash of a server",
        example="guildsplash",
        aliases=["splash", "serversplash"],
    )
    async def serversplash(self, ctx, *, guild: discord.Guild = None):
        guild = guild or ctx.guild
        e = discord.Embed(
            color=self.bot.color, title=f"{guild.name}'s splash", url=guild.splash
        )
        e.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar
        )
        e.set_image(url=guild.splash)
        await ctx.send(embed=e)

    @commands.command(
        name="roles",
        description="View the server roles",
        example=",roles",
        aliases=["rolelist"],
    )
    async def roles(self, ctx):
        await ctx.typing()
        embeds = []
        ret = []
        num = 0
        pagenum = 0
        if ctx.guild.roles is None:
            return
        for role in ctx.guild.roles[::-1]:
            if role.name != "@everyone":
                num += 1
                ret.append(f"``{num}.`` {role.mention}")
                pages = [p for p in discord.utils.as_chunks(ret, 10)]
        for page in pages:
            pagenum += 1
            embeds.append(
                discord.Embed(
                    title="List of Roles",
                    color=self.bot.color,
                    description="\n".join(page),
                )
                .set_author(
                    name=ctx.author.display_name, icon_url=ctx.author.display_avatar
                )
                .set_footer(text=f"Page {pagenum}/{len(pages)}")
            )
        if len(embeds) == 1:
            return await ctx.send(embed=embeds[0])
        else:
            await ctx.paginate(embeds)

    @commands.command(
        name="names",
        aliases=["namehistory", "nh", "namehist"],
        brief="show a user's name history",
        example=",names @o_5v",
    )
    async def names(self, ctx, *, user: discord.User = None):
        if user is None:
            user = ctx.author
        if data := await self.bot.db.fetch(
            "SELECT username, ts, type FROM names WHERE user_id = $1 ORDER BY ts DESC",
            user.id,
        ):
            embed = discord.Embed(
                title=f"{str(user)}'s names", color=self.bot.color, url=self.bot.domain
            )
            rows = []
            for i, name in enumerate(data, start=1):
                name_type = str(name.type)[0].upper()
                rows.append(
                    f"`{i}{name_type}.` **{name.username}** - {discord.utils.format_dt(name.ts, style='R')}"
                )
            return await self.bot.dummy_paginator(ctx, embed, rows)
        return await ctx.fail(f"No **name history** found for **{str(user)}**")

    @commands.command(
        name="inrole",
        brief="list all users that has a role",
        aliases=["irole"],
        example=",inrole admin",
    )
    async def inrole(self, ctx, *, role: NonAssignedRole):
        """View the users in a role"""

        role = role[0]

        ret = []

        content = discord.Embed(
            color=self.bot.color,
            title=f"Members with {role.name}",
        ).set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar)

        for i, m in enumerate(role.members, start=1):
            ret.append(f"`{i}` {m.mention} (``{m.id}``)")

        if not ret:
            return await ctx.fail(f"no role found named `{role}`")

        return await self.bot.dummy_paginator(ctx, content, ret)

    @commands.command(
        name="roleinfo",
        description="Shows information on a role",
        example=",roleinfo admin",
        usage="<role>",
    )
    async def roleinfo(self, ctx, *, role: Union[discord.Role, str]):
        """View some information on a role"""

        if isinstance(role, str):
            matches = get_close_matches(
                role, [r.name for r in ctx.guild.roles], cutoff=0.3
            )

            role = discord.utils.get(ctx.guild.roles, name=matches[0])

        timestamp = round(role.created_at.timestamp())

        members = len(role.members)

        percentage = len(role.members) / len(ctx.guild.members) * 100

        role.guild.get_member(role.guild.owner_id)  # type: ignore

        embed = discord.Embed(color=role.color, title=role.name)

        embed.add_field(
            name="**__Overview__**",
            value=f""">>> **Created:** \n<t:{timestamp}:D> (<t:{timestamp}:R>)
**Members:** {members} ({percentage:.2f}%)
**Position:** {role.position}""",
        )

        embed.add_field(
            name="**__Misc__**",
            value=f""">>> **Hoist:** {role.hoist}
**Color:** {role.color}
**Managed:** {role.managed}""",
        )

        embed.set_author(
            name=role.name, icon_url=role.display_icon or ctx.author.display_avatar
        )

        embed.set_thumbnail(url=role.display_icon or ctx.author.display_avatar)

        await ctx.send(embed=embed)

    @commands.group(
        invoke_without_command=True,
        example=",boosters",
        brief="List all the current users boosting the guild",
    )
    async def boosters(self, ctx):
        rows = []

        if len(ctx.guild.premium_subscribers) == 0:
            rows.append("Guild Has No Boosters")

        else:
            premium_subscribers = sorted(
                ctx.guild.premium_subscribers,
                key=lambda m: m.premium_since,
                reverse=True,
            )

            for i, booster in enumerate(premium_subscribers, start=1):
                rows.append(
                    f"``{i}.``**{booster.name} ** - {discord.utils.format_dt(booster.premium_since, style='R')} "
                )

        embeds = []

        page = []

        for i, row in enumerate(rows):
            if i % 10 == 0 and i > 0:
                embeds.append(
                    discord.Embed(
                        color=self.bot.color,
                        title=f"{ctx.guild.name}'s boosters",
                        url=self.bot.domain,
                        description="\n".join(page),
                    )
                    .set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar
                    )
                    .set_footer(text=f"Page {len(embeds) + 1}/{(len(rows) + 4) // 10}")
                )

                page = []

            page.append(row)

        if page:
            embeds.append(
                discord.Embed(
                    color=self.bot.color,
                    title=f"{ctx.guild.name}'s boosters\n",
                    url=self.bot.domain,
                    description="\n".join(page),
                )
                .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
                .set_footer(text=f"Page {len(embeds) + 1}/{(len(rows) + 4) // 10}")
            )

        if not embeds:
            embeds.append(
                discord.Embed(
                    color=self.bot.color, description="**Guild Has No Boosters**"
                ).set_author(name=ctx.author.name, icon_url=ctx.author.display_avatarl)
            )

        await ctx.alternative_paginate(embeds)

    async def get_or_fetch(self, user_id: int) -> str:
        if user := self.bot.get_user(user_id):
            return user.global_name or user.name

        else:
            user = await self.bot.fetch_user(user_id)

            return user.global_name or user.name

    @boosters.command(
        name="lost",
        brief="List all users who has recently stopped boosting the server",
        example=",boosters lost",
    )
    async def boosters_lost(self, ctx: Context):
        embed = discord.Embed(
            title="boosters lost", url=self.bot.domain, color=self.bot.color
        )

        if rows := await self.bot.db.fetch(
            "SELECT user_id, ts FROM boosters_lost WHERE guild_id = $1 ORDER BY ts DESC",
            ctx.guild.id,
        ):
            lines = []

            for i, row in enumerate(rows, start=1):
                user = await self.get_or_fetch(row["user_id"])

                lines.append(
                    f"`{i}.` **{user}** - {discord.utils.format_dt(row['ts'], style='R')}"
                )
            return await self.bot.dummy_paginator(ctx, embed, lines)

        else:
            return await ctx.fail("no **boosters lost** in guild")

    @commands.command(
        name="emojis", brief="List all emojis in the server", example=",emojis"
    )
    async def emojis(self, ctx):
        emojis = ctx.guild.emojis

        if len(emojis) == 0:
            embed = discord.Embed(
                color=0x2B2D31, description="**Guild Has No Emojis**"
            ).set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)

            await ctx.send(embed=embed)

            return

        rows = []

        for i, emoji in enumerate(emojis, start=1):
            emoji_text = f"`{i}.`{str(emoji)}[{emoji.name}](https://cdn.discordapp.com/emojis/{emoji.id}.png)"

            rows.append(emoji_text)

        embeds = []

        page = []

        pagenum = 0

        # Calculate the total number of pages

        total_pages = (len(rows) + 9) // 10

        for i, row in enumerate(rows, start=1):
            if i % 10 == 0 and i > 0:
                pagenum += 1

                embeds.append(
                    discord.Embed(
                        color=0x2B2D31,
                        title=f"{ctx.guild.name}'s Emojis",
                        description="\n".join(page),
                    )
                    .set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar
                    )
                    .set_footer(text=f"Page {pagenum}/{total_pages}")
                )

                page = []

            page.append(row)

        if page:
            pagenum += 1

            embeds.append(
                discord.Embed(
                    color=0x2B2D31,
                    title=f"{ctx.guild.name}'s Emojis",
                    description="\n".join(page),
                )
                .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
                .set_footer(text=f"Page {pagenum}/{total_pages}")
            )

        if not embeds:
            embeds.append(
                discord.Embed(
                    color=0x2B2D31, description="**Guild Has No Emojis**"
                ).set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
            )

        await ctx.paginate(embeds)

    @commands.command(name="bots", brief="List all bots in the server", example=",bots")
    async def bots(self, ctx):
        bots = [member for member in ctx.guild.members if member.bot]

        if not bots:
            embed = discord.Embed(
                color=self.bot.color, description="**No bots found in this server**"
            ).set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)

            await ctx.send(embed=embed)

            return

        rows = []

        for i, bot in enumerate(bots, start=1):
            bot_text = f"`{i}.` {bot.mention}"

            rows.append(bot_text)

        embeds = []

        page = []

        for i, row in enumerate(rows, start=1):
            if i % 10 == 0 and i > 0:
                embeds.append(
                    discord.Embed(
                        color=self.bot.color,
                        title=f"Bots in {ctx.guild.name}",
                        description="\n".join(page),
                    )
                    .set_author(
                        name=ctx.author.name, icon_url=ctx.author.display_avatar
                    )
                    .set_footer(text=f"Page {len(embeds) + 1}/{(len(rows) + 9) // 10}")
                )

                page = []

            page.append(row)

        if page:
            embeds.append(
                discord.Embed(
                    color=self.bot.color,
                    title=f"Bots in {ctx.guild.name}",
                    description="\n".join(page),
                )
                .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
                .set_footer(text=f"Page {len(embeds) + 1}/{(len(rows) + 9) // 10}")
            )

        if not embeds:
            embeds.append(
                discord.Embed(
                    color=self.bot.color,
                    description="**No bots found in this server**",
                ).set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
            )

        await ctx.paginate(embeds)

    @commands.command(
        name="channelinfo",
        brief="View information on a channel",
        example=",channelinfo #txt",
    )
    async def channelinfo(self, ctx, channel: discord.TextChannel):
        category = channel.category.name if channel.category else "No category"

        topic = channel.topic if channel.topic else "No topic for this channel"

        creation_date = channel.created_at.strftime("%m-%d-%Y")

        embed = discord.Embed(
            title=f"#{channel.name}",
            color=self.bot.color,
            description=f"**Channel ID:** \n``{channel.id}``"
            f"\n**Guild ID:** \n``{channel.guild.id}``"
            f"\n**Category:** ``{category}``"
            f"\n**Type:** ``{channel.type}``\n"
            f"\n**Topic:** __{topic}__\n",
        )

        embed.set_footer(text=f"Creation date: {creation_date}")

        embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar)

        await ctx.send(embed=embed)

    async def urban_definition(self, term: str):
        async with self.bot.session.get(
            "https://api.urbandictionary.com/v0/define", params={"term": term}
        ) as response:
            data = await response.json()
            assert data.get("message") != "Internal server error"
            return tuple(UrbanDefinition(**record) for record in data["list"])

    @commands.command(
        name="urbandictionary",
        aliases=("urban", "ud"),
        example=",urbandictionary black",
        brief="Lookup a words meaning using the urban dictionary",
    )
    async def urbandictionary(self, ctx, term: str):
        """
        Get the urban definition of a term.
        """

        if not (data := await self.urban_definition(term)):
            return await ctx.fail("I couldn't find a definition for that word.")

        embeds = []

        for index, record in enumerate(
            sorted(data[:3], key=lambda record: record.thumbs_up, reverse=True), start=1
        ):
            embeds.append(
                discord.Embed(color=self.bot.color)
                .set_author(name=ctx.author, icon_url=ctx.author.display_avatar)
                .add_field(
                    name=f"Urban Definition for '{term}'",
                    value=f"{(record.definition[:650] + ('...' if len(record.definition) > 650 else '')).replace('[', '').replace(']', '')}",
                )
                .add_field(
                    name="Example",
                    value=f"{(record.example[:650] + ('...' if len(record.example) > 650 else '')).replace('[', '').replace(']', '')}",
                    inline=False,
                )
                .set_footer(
                    text=f"Page {index} / {len(data[:3])} | 👍 {record.thumbs_up} 👎 {record.thumbs_down}"
                )
            )

        return await ctx.paginate(embeds)


async def setup(bot):
    await bot.add_cog(Information(bot))
