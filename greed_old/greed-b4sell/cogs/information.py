from asyncio import tasks
import json
import os
import typing
import math
import time
from color_processing import ColorInfo
import discord
import pytz
import aiohttp
import asyncio
import psutil
from difflib import get_close_matches
from tool.important import Context  # type: ignore
from discord.ui import Button, View
from io import BytesIO
from discord.ext.commands import CommandError, param
from discord.ext import commands
from datetime import timedelta, datetime
from tool.important.subclasses.command import (  # type: ignore
    Member,
    User,
    NonAssignedRole,
)
from tool.worker import offloaded  # type: ignore
from aiohttp import ContentTypeError
from discord import Interaction, app_commands, Color  # type: ignore
from discord.app_commands import Choice
from typing import Union, Optional, List, Annotated  # type: ignore
from tool.greed import Greed  # type: ignore
from tool.emotes import EMOJIS  # type: ignore

# from tool.shazam import Recognizer  # type: ignore
# from weather import WeatherClient  # type: ignore
# from weather.weathertypes import Kind  # type: ignore
# ` 1from geopy import geocoders
from typing_extensions import Type
import re
from discord import Embed
from cogs.lastfm import LastFMHTTPRequester

if typing.TYPE_CHECKING:
    pass
from munch import DefaultMunch
from pydantic import BaseModel
from loguru import logger
from aiohttp import ClientSession as Session
from cashews import cache
from bs4 import BeautifulSoup
from humanize import intword
from cogs.lastfm import shorten
from tool.down_detector import DiscordStatus
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

GUILD_ID = 1301617147964821524


@offloaded
def get_timezone(location: str) -> str:
    geolocator = Nominatim(user_agent="Greed-Bot")
    location = geolocator.geocode(location)
    if location is None:
        raise ValueError("Location not found")

    tf = TimezoneFinder()
    timezone = tf.timezone_at(lng=location.longitude, lat=location.latitude)
    if timezone is None:
        raise ValueError("Timezone not found for the given location")
    logger.info(timezone)
    return timezone


class plural:
    def __init__(
        self: "plural",
        value: typing.Union[int, str, typing.List[typing.Any]],
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


# @cache(ttl=1200, key="ig:{username}")
# async def get_instagram_user(username: str) -> Optional[InstagramUser]:
#     async with Session() as session:
#         async with session.get(
#             f"https://dumpoir.com/v/{username}",
#             headers={
#                 "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/112.0"
#             },
#         ) as response:
#             data = await response.read()
#     try:
#         soup = BeautifulSoup(data, "html.parser")
#         bio_element = soup.select_one(
#             "#user-page > div.user > div > div.col-md-5.my-3 > div"
#         )
#         bio = bio_element.get_text(strip=True) if bio_element else ""
#         result = {
#             "bio": bio,  # soup.select_one('#user-page > div.user > div > div.col-md-5.my-3 > div').get_text(strip=True) if bio,
#             "followers": soup.select_one(
#                 "#user-page > div.user > div > div.col-md-4.col-8.my-3 > ul > li:nth-child(2)"
#             )
#             .get_text(strip=True)
#             .replace(" Followers", ""),
#             "following": soup.select_one(
#                 "#user-page > div.user > div > div.col-md-4.col-8.my-3 > ul > li:nth-child(3)"
#             )
#             .get_text(strip=True)
#             .replace(" Following", ""),
#             "fullname": soup.select_one(
#                 "#user-page > div.user > div > div.col-md-4.col-8.my-3 > div > a > h1"
#             ).get_text(strip=True),
#             "posts": soup.select_one(
#                 "#user-page > div.user > div > div.col-md-4.col-8.my-3 > ul > li:nth-child(1)"
#             )
#             .get_text(strip=True)
#             .replace(" Posts", ""),
#             "profile_pic": soup.select_one(
#                 "#user-page > div.user > div.row > div > div.user__img"
#             )["style"]
#             .replace("background-image: url('", "")
#             .replace("');", ""),
#             "url": f"https://www.instagram.com/{username.replace('@', '')}",
#             "username": username,
#         }
#         try:
#             result["followers"] = int(result["followers"].replace(" ", ""))
#         except Exception:
#             result["followers"] = 0
#         try:
#             result["posts"] = int(result["posts"].replace(" ", ""))
#         except Exception:
#             result["posts"] = 0
#         try:
#             result["following"] = int(result["following"].replace(" ", ""))
#         except Exception:
#             result["following"] = 0
#         return InstagramUser(**result)
#     except Exception as e:
#         if hasattr(e, "response") and e.response.status_code == 404:
#             raise Exception("Error: Akun tidak ditemukan")
#         elif hasattr(e, "response") and e.response.status_code == 403:
#             raise Exception("Error: Akunnya Di Private")
#         else:
#             raise Exception("Error: Failed to fetch Instagram profile")


class Object:
    def __init__(self, data: dict):
        self.data = data

    def from_data(self):
        return DefaultMunch(object(), self.data)


class AuditLogParser:
    def __init__(self, bot: Greed, logs: List[discord.AuditLogEntry]):
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
        cog: Optional[commands.Cog] = interaction.client.get_cog(value)  # type: ignore
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
        command: Optional[commands.Command] = interaction.client.get_command(value)  # type: ignore
        if command is None:
            raise ValueError(f"Command {value} not found.")
        else:
            return command


class Information(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.requester = LastFMHTTPRequester(api_key="260c08af4a7f26f90743f66637572031")
        self.bot.loop.create_task(self.setup_db())
        #       self.recognizer = Recognizer()
        self.command_count = len(
            [
                cmd
                for cmd in list(self.walk_commands())
                if cmd.cog_name not in ("Jishaku", "events", "Owner")
            ]
        )

    async def setup_db(self):
        """Sets up the database tables if they don't exist."""
        await self.bot.db.execute(
            """ 
            CREATE TABLE IF NOT EXISTS guilds_stats ( 
                guild_id BIGINT PRIMARY KEY, 
                joins INT DEFAULT 0, 
                leaves INT DEFAULT 0 
            )
        """
        )

    async def update_server_stats(self, guild_id: int, column: str):
        """Update join/leave count for a guild."""
        await self.bot.db.execute(
            f"""
            INSERT INTO guilds_stats (guild_id, {column})
            VALUES ($1, 1)
            ON CONFLICT (guild_id)
            DO UPDATE SET {column} = guilds_stats.{column} + 1
            """,
            guild_id,
        )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Listener for user joins."""
        await self.update_server_stats(member.guild.id, "joins")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        """Listener for user leaves."""
        await self.update_server_stats(member.guild.id, "leaves")

    async def lf(self, mem: Union[Member, discord.User]):
        """Fetches the last played song on LastFM for a user using the nowplaying method"""
        if not (
            conf := await self.bot.db.fetchrow(
                "SELECT * FROM lastfm.conf WHERE user_id = $1", mem.id
            )
        ):
            return None

        try:
            # Fetch recent tracks and user info
            data = await self.requester.get(
                method="user.getrecenttracks", user=conf["username"]
            )
            if "error" in data:
                return None

            track_data = data.get("recenttracks", {}).get("track", [])
            if track_data:
                track_name = track_data[0]["name"]
                track_url = track_data[0]["url"]
                artist_name = track_data[0]["artist"]["#text"]
                return f"<a:lfm:1333750101067305002> Listening to **{track_name}**"
        except Exception as e:
            print(f"Error fetching LastFM data: {e}")

        return None  # If no track is found, return None

    @commands.command(
        aliases=["guildstats", "mc", "membercount"],
        brief="View the member count of the server",
        example=",membercount",
    )
    async def guilds_stats(self, ctx):
        """Displays the number of joins, leaves, and total members for the server."""
        guild = ctx.guild
        total_users = len(guild.members)
        total_members = len([member for member in guild.members if not member.bot])
        total_bots = total_users - total_members

        # Fetch stats from the database
        stats = await self.bot.db.fetchrow(
            "SELECT joins, leaves FROM guilds_stats WHERE guild_id = $1", guild.id
        )
        joins = stats["joins"] if stats else 0
        leaves = stats["leaves"] if stats else 0

        embed = discord.Embed(
            title=f"**{ctx.guild.name}**",
            color=self.bot.color,
        )
        embed.add_field(
            name="> Total",
            value=f"<:line:1336409552786161724> **`{total_users}`** <:iconsPerson:1342771680879317095>",
            inline=False,
        )
        embed.add_field(
            name="> Joins",
            value=f"<:line:1336409552786161724> **`{joins}`** <:190:1337552566002647171>",
            inline=False,
        )
        embed.add_field(
            name="> Leaves",
            value=f"<:line:1336409552786161724> **`{leaves}`** <:190:1337552564404748308>",
            inline=False,
        )
        embed.add_field(
            name="> Bots",
            value=f"<:line:1336409552786161724> **`{total_bots}`** <:spyiconsbots:1342773947560886316>",
            inline=True,
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="level",
        brief="see your level in the server",
        aliases=["lvl", "rank", "rnk", "activity"],
        usage=",level <member>",
        example=",level @aiohttp",
    )
    async def level(self, ctx: Context, *, member: Optional[Member] = commands.Author):
        # Check if leveling is enabled for this guild
        enabled = bool(
            await self.bot.db.fetchrow(
                """SELECT 1 FROM text_level_settings WHERE guild_id = $1""", ctx.guild.id
            )
        )
        if not enabled:
            return await ctx.fail(
                f"levelling has not been enabled thru `{ctx.prefix}levels enable`"
            )
        
        # Get user's XP data directly from the database
        data = await self.bot.db.fetchrow(
            """SELECT xp, msgs FROM text_levels WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            member.id,
        )
        
        if not data:
            return await ctx.fail("No data found yet")
        
        xp = int(data['xp'])
        messages = int(data['msgs'])
        
        # Calculate level and progress
        current_level = math.floor(0.05 * (1 + math.sqrt(5)) * math.sqrt(xp)) + 1
        needed_xp = math.ceil(math.pow((current_level) / (0.05 * (1 + math.sqrt(5))), 2))
        
        percentage = min(100, int((xp / needed_xp) * 100))
        
        # Create progress bar directly
        async with ctx.typing():
            # Import matplotlib here to avoid import issues
            import matplotlib.pyplot as plt
            from matplotlib.patches import PathPatch, Path
            import matplotlib
            
            matplotlib.use("Agg")
            
            bar_width = 10
            height = 1
            corner_radius = 0.2
            
            fig, ax = plt.subplots(figsize=(bar_width, height))
            
            width_1 = (percentage / 100) * bar_width
            width_2 = ((100 - percentage) / 100) * bar_width
            
            # Create the filled part of the bar
            if width_1 > 0:
                path_data = [
                    (Path.MOVETO, [corner_radius, 0]),
                    (Path.LINETO, [width_1, 0]),
                    (Path.LINETO, [width_1, height]),
                    (Path.LINETO, [corner_radius, height]),
                    (Path.CURVE3, [0, height]),
                    (Path.CURVE3, [0, height - corner_radius]),
                    (Path.LINETO, [0, corner_radius]),
                    (Path.CURVE3, [0, 0]),
                    (Path.CURVE3, [corner_radius, 0]),
                ]
                codes, verts = zip(*path_data)
                path = Path(verts, codes)
                patch = PathPatch(path, facecolor="#2f4672", edgecolor="none")
                ax.add_patch(patch)
            
            # Create the empty part of the bar
            if width_2 > 0:
                path_data = [
                    (Path.MOVETO, [width_1, 0]),
                    (Path.LINETO, [bar_width - corner_radius, 0]),
                    (Path.CURVE3, [bar_width, 0]),
                    (Path.CURVE3, [bar_width, corner_radius]),
                    (Path.LINETO, [bar_width, height - corner_radius]),
                    (Path.CURVE3, [bar_width, height]),
                    (Path.CURVE3, [bar_width - corner_radius, height]),
                    (Path.LINETO, [width_1, height]),
                    (Path.LINETO, [width_1, 0]),
                ]
                codes, verts = zip(*path_data)
                path = Path(verts, codes)
                patch = PathPatch(path, facecolor="black", edgecolor="none")
                ax.add_patch(patch)
            
            ax.set_xlim(0, bar_width)
            ax.set_ylim(0, height)
            ax.axis("off")
            
            # Save the figure to a BytesIO object
            bar_img = BytesIO()
            plt.savefig(bar_img, format="png", bbox_inches="tight", pad_inches=0, transparent=True)
            plt.close(fig)
            bar_img.seek(0)
            
            bar = discord.File(fp=bar_img, filename="bar.png")
            
            # Create and send the embed
            embed = (
                Embed(
                    title=f"{member}'s text Level",
                    url="https://greed.rocks/",
                    color=0x2F4672,
                )
                .add_field(name="Messages", value=messages, inline=False)
                .add_field(name="Level", value=current_level, inline=False)
                .add_field(name="XP", value=f"{xp} / {needed_xp}", inline=False)
                .set_image(url=f"attachment://{bar.filename}")
            )
            
            await ctx.send(embed=embed, file=bar)

    @app_commands.command()
    async def help_(
        self,
        interaction: Interaction,
        category: Optional[Annotated[commands.Cog, CategoryTransformer]] = None,
        command: Optional[Annotated[commands.Command, CommandTransformer]] = None,
    ):
        if category is not None:
            pass  # type: ignore
        elif command is not None:
            pass  # type: ignore
        else:
            pass  # type: ignore

        ctx = await self.bot.get_context(interaction)
        return await ctx.send_help()

    #    self.client = Client()  # type: ignore

    async def find_timezone(self, city: str, country: Optional[str] = None): ...  # type: ignore

    # if data := await self.client.lookup(city=city):
    #     return data.timezone
    # else:
    #     if pytz.timezone(city):  # type: ignore
    #         return city
    #     else:
    #         return None

    def try_escape(self, ban: discord.BanEntry):
        try:
            if ban.user.discriminator == "0":
                return f"**{discord.utils.escape_markdown(ban.user.name)}**"
            return f"**{discord.utils.escape_markdown(ban.user.name)}#{ban.user.discriminator}**"
        except Exception:
            if ban.user.discriminator == "0":
                return f"**{ban.user.name}**"
            return f"**{ban.user.name}#{ban.user.discriminator}**"

    async def get_time(self, timezone: str):
        try:
            tz = pytz.timezone(timezone)
            logger.info(tz)
            return datetime.now(tz=tz).strftime("%-I:%M%p").lower()
        except pytz.UnknownTimeZoneError:
            raise ValueError(f"Unknown timezone: {timezone}")

    @commands.command(name="status", brief="check on discord's status")
    async def status(self, ctx: Context):
        data = await DiscordStatus.from_response()
        embed = data.to_embed(self.bot, False)
        return await ctx.send(embed=embed)

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
                    logger.info(data)
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
        example=",timezone @lim",
    )
    async def timezone(
        self,
        ctx: Context,
        member: Optional[Union[discord.Member, discord.User]] = commands.Author,
    ):
        if data := await self.bot.db.fetchval(
            """SELECT tz FROM timezone WHERE user_id = $1""", member.id
        ):
            return await ctx.success(
                f"{member.mention}'s **current time** is ``{await self.get_time(data)}``"
            )
        else:
            return await ctx.fail(
                f"{member.mention} **does not have their time set** with `timezone set`"
            )

    @timezone.command(
        name="set",
        brief="set a timezone via location or timezone",
        example=",timezone set New York",
    )
    async def timezone_set(self, ctx: Context, *, timezone: str):
        try:
            # Attempt to get the timezone using the provided location
            data = await get_timezone(timezone)  # Await the offloaded function
        except ValueError as e:
            # Handle cases where the location or timezone is invalid
            return await ctx.fail(f"Error: {str(e)}. Please provide a valid location.")
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Unexpected error in timezone_set: {e}")
            return await ctx.fail("An unexpected error occurred while setting your timezone.")
    
        # If a valid timezone is found, update the database
        await self.bot.db.execute(
            """INSERT INTO timezone (user_id, tz) VALUES($1, $2) 
               ON CONFLICT(user_id) DO UPDATE SET tz = excluded.tz""",
            ctx.author.id,
            data,
        )
        current_time = await self.get_time(data)
        return await ctx.success(f"Your timezone has been set to ``{current_time}``.")

    @commands.command(
        brief="Check the bot's latency",
        description="Shows the current latency of the bot.",
        example=",ping",
    )
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"*...**{latency}**ms*")

    #    @commands.command(
    #        name="weather",
    #        brief="Show the current weather of a certain city",
    #        example=",weather columbia",
    #    )
    #    async def weather(self, ctx: Context, *, city: str):
    #        try:
    #            weather_dat = await self.weather_client.get(city)
    #            weather_data = weather_dat.current_condition[0]
    #            embed = discord.Embed(
    #                title=f"{Kind(int(weather_data.weatherCode)).emoji} weather in {city}",
    #                description=f"**Temp:** {weather_data.temp_F}\n**Feels Like:** {weather_data.FeelsLikeF}\n**Humidity:** {weather_data.humidity}%",
    #                color=self.bot.color,
    #            )
    #
    #            return await ctx.send(embed=embed)
    #        except Exception as e:
    #            if ctx.author.name == "aiohttp":
    #                raise e
    #            return await ctx.fail(f"**Could not find** the weather for `{city}`")

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
        self, ctx: Context, *, query: Optional[Union[str, User, Member, Color]] = None
    ):
        if query is None:
            if len(ctx.message.attachments) > 0:
                query = ctx.message.attachments[0].url
            else:
                raise CommandError("you must provide a query or attachment")
        return await ColorInfo().convert(ctx, query)
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
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            return await ctx.send_help()

    @commands.command(name="botinfo", aliases=["bot", "info"])
    async def botinfo(self, ctx):
        """
        Shows information about the bot
        """
        try:
            logger.info("Starting botinfo command execution")
            cluster_id = getattr(self.bot, "cluster_id", 0)
            total_clusters = getattr(self.bot, "shard_count", 4)
            
            logger.info("Getting uptime")
            uptime = str(timedelta(seconds=int(round(time.time() - self.bot.startup_time.timestamp()))))
            total_commands = len(self.bot.commands)
            latency = round(self.bot.latency * 1000)
            memory = psutil.Process().memory_info().rss / 1024 / 1024
            
            logger.info("Fetching counts via IPC")
            guilds = await self.bot.guild_count()
            users = await self.bot.user_count()
            roles = await self.bot.role_count()
            channels = await self.bot.channel_count()
            
            logger.info(f"Got counts - Guilds: {guilds}, Users: {users}, Roles: {roles}, Channels: {channels}")
            
            embed = discord.Embed(
                title="Bot Information",
                color=discord.Color.blue()
            )
            
            embed.add_field(name="Bot Name", value=self.bot.user.name, inline=True)
            embed.add_field(name="Bot ID", value=self.bot.user.id, inline=True)
            embed.add_field(name="Created By", value=self.bot.get_user(self.bot.owner_id).mention, inline=True)
            embed.add_field(name="Uptime", value=uptime, inline=True)
            embed.add_field(name="Total Commands", value=total_commands, inline=True)
            embed.add_field(name="Latency", value=f"{latency}ms", inline=True)
            embed.add_field(name="Memory Usage", value=f"{memory:.2f} MB", inline=True)
            embed.add_field(name="Guilds", value=guilds, inline=True)
            embed.add_field(name="Users", value=users, inline=True)
            embed.add_field(name="Roles", value=roles, inline=True)
            embed.add_field(name="Channels", value=channels, inline=True)
            embed.add_field(name="Cluster", value=f"{cluster_id + 1}/{total_clusters}", inline=True)
            
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
            
            logger.info("Sending botinfo embed")
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in botinfo command: {e}", exc_info=True)
            await ctx.send("An error occurred while fetching bot information. Please try again later.")

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
        e = discord.Embed(
            color=self.bot.color,
            title=f"{guild.name}",
            description=f'** __Created: __ ** \n{discord.utils.format_dt(guild.created_at, style="F")}',
        )
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
        example=",userinfo @lim",
        brief="View information on a user's account",
    )
    async def whois(self, ctx, user: Union[User, Member] = None):
        """View some information on a user"""
        user = user or ctx.author

        if isinstance(user, discord.User):
            # Handle User that is not in the server - show minimal info
            embed = discord.Embed(
                color=self.bot.color,
                title=f"{user.name}",
            )
            embed.add_field(
                name="**Created**",
                value=f"**{discord.utils.format_dt(user.created_at, style='D')}**",
                inline=True,
            )
            embed.set_thumbnail(url=user.display_avatar)

            return await ctx.send(embed=embed)

        # Handle Member with full server info
        mutual_guilds = tuple(g for g in self.bot.guilds if g.get_member(user.id))
        position = sorted(ctx.guild.members, key=lambda m: m.joined_at).index(user) + 1

        badges = []
        staff = []
        flags = user.public_flags

        emojis = {
            "staff2": EMOJIS["badgediscordstaff"],
            "nitro": EMOJIS["Nitro_badge"],
            "hypesquad_brilliance": EMOJIS["Icon_Hypesquad_Brilliance"],
            "hypesquad_bravery": EMOJIS["hmubravery"],
            "hypesquad_balance": EMOJIS["HypeSquad_Balance"],
            "bug_hunter": EMOJIS["bug_hunter"],
            "bug_hunter_level_2": EMOJIS["bug_hunter_level_2"],
            "discord_certified_moderator": EMOJIS["certified_moderator"],
            "early_supporter": EMOJIS["EarlySupport"],
            "verified_bot_developer": EMOJIS["discord_developer"],
            "partner": EMOJIS["Partner_server_owner"],
            "staff": EMOJIS["Verified_badge_1_staff"],
            "verified_bot": EMOJIS["6_bot"],
            "server_boost": EMOJIS["boost_badge"],
            "active_developer": EMOJIS["ActiveDeveloper"],
            "pomelo": EMOJIS["pomelo"],
            "web_idle": EMOJIS["IconStatusWebIdle"],
            "web_dnd": EMOJIS["IconStatusWebDND"],
            "web_online": EMOJIS["IconStatusWebOnline"],
            "desktop_dnd": EMOJIS["hmudnd"],
            "desktop_idle": EMOJIS["hmuIdle"],
            "desktop_online": EMOJIS["online2"],
            "mobile_dnd": EMOJIS["dndphone"],
            "mobile_idle": EMOJIS["idlephone"],
            "mobile_online": EMOJIS["onlinephone"],
            "web_offline": "",
            "mobile_offline": "",
            "desktop_offline": "",
        }

        _staff = {
            "staff1": EMOJIS["Verified_badge_1_staff"],
            "lim": EMOJIS["bot_owner"],
            "dev": EMOJIS["buildbadge"],
        }

        for flag in (
            "staff1",
            "nitro",
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

        for staff_flag in (
            "dev",
            "staff1",
            "lim",
        ):
            if getattr(flags, staff_flag, False) is True:
                staff.append(_staff[staff_flag])

        def founder(u):
            return u.id in self.bot.lim

        def is_bot_staff(u):
            return u.id in self.bot.owner_ids

        def is_dev(u):
            return u.id in self.bot.dev

        staff_badges = set()

        if founder(user):
            staff_badges.add(_staff.get("lim"))
            staff_badges.add(_staff.get("staff1"))

        if is_bot_staff(user):
            staff_badges.add(_staff.get("staff1"))

        if is_dev(user):
            staff_badges.add(_staff.get("dev"))
            staff_badges.add(_staff.get("staff1"))

        staff.extend(badge for badge in staff_badges if badge is not None)

        def is_boosting(u):
            return any(g.get_member(u.id).premium_since for g in mutual_guilds)

        if is_boosting(user):
            badges.extend((emojis.get("nitro"), emojis.get("server_boost")))

        devices = (
            ", ".join(
                k
                for k, v in {
                    "desktop": user.desktop_status,
                    "web": user.web_status,
                    "mobile": user.mobile_status,
                }.items()
                if v != discord.Status.offline
            )
            or "none"
        )

        badges = " ".join(badges)
        staff = " ".join(staff)

        status_emoji = ""

        if devices != "none":
            status_emoji = " ".join(
                emojis.get(f"{device}_{user.status.name.lower()}", "")
                for device in devices.split(", ")
            )

        status = ""

        if user.activity:
            start = user.activity.type.name.capitalize()

            if start == "Custom":
                start = ""

            if start == "Listening":
                start = "Listening to"

            status = f"{start} {user.activity.name}"

        if status == "":
            status = "N/A"

        # Fetch the current LastFM track for this user
        lastfm_status = await self.lf(user)

        if lastfm_status:
            lastfm_status = f"{lastfm_status}"
        else:
            lastfm_status = ""

        embed = discord.Embed(
            color=self.bot.color,
            title=f"{staff}\n{user.name} {badges}",
            description=f"{status_emoji} {status}\n{lastfm_status}",
        )

        embed.add_field(
            name="**Created**",
            value=f"**{discord.utils.format_dt(user.created_at, style='D')}**",
            inline=True,
        )

        embed.add_field(
            name="**Joined**",
            value=f"**{discord.utils.format_dt(user.joined_at, style='D')}**",
            inline=True,
        )

        if user.premium_since:
            embed.add_field(
                name="**Boosted server**",
                value=f"**{discord.utils.format_dt(user.premium_since, style='D')}**",
            )

        if user.roles:
            roles = ", ".join(
                [role.mention for role in list(reversed(user.roles[1:]))[:5]]
            ) + (f" + {len(user.roles) - 5} more" if len(user.roles) > 5 else "")

            embed.add_field(name="**__Roles__**", value=f"{roles}", inline=False)

        embed.set_thumbnail(url=user.display_avatar)

        embed.set_footer(
            text=f"{len(mutual_guilds)} mutuals, Join position: {position}"
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="serveravatar",
        description="View the avatar of a user for a server",
        example=",serveravatar @lim",
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
        name="banner",
        brief="View the banner of a user",
        example=",banner @lim",
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
            await ctx.warning("User has **no banner set**")
        else:
            await ctx.warning("User has **no banner set**")

    @commands.command(
        name="serverbanner",
        brief="View the server banner of a user",
        example=",serverbanner @lim",
        aliases=["sb"],
    )
    async def serverbanner(self, ctx, *, user: Member = None):
        user = user or ctx.author
        banner_url = user.guild_banner
        if banner_url is None:
            return await ctx.fail(f"{user.mention} **has no server banner**")
        e = discord.Embed(
            title=f"{user.name}'s server banner", url=banner_url, color=self.bot.color
        )
        e.set_author(
            name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar
        )
        e.set_image(url=banner_url)
        await ctx.send(embed=e)

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
        brief="View the banner of a server using its ID or vanity URL.",
        usage=",guildbanner [server_id | vanity_url]",
        aliases=["gb"],
    )
    async def guildbanner(self, ctx, *, input_value: str = None):
        guild = None

        if input_value is None:
            guild = ctx.guild  # Default to the current server if no input is given
        else:
            # Check if the input is a numeric Guild ID
            if input_value.isdigit():
                guild = self.bot.get_guild(int(input_value))

            # If not a guild ID, assume it's a vanity URL and try fetching via invite
            if guild is None:
                try:
                    invite = await self.bot.fetch_invite(input_value)
                    guild = invite.guild
                except discord.NotFound:
                    return await ctx.fail("Invalid server ID or vanity URL.")
                except discord.Forbidden:
                    return await ctx.fail(
                        "I do not have permission to fetch this invite."
                    )
                except discord.HTTPException:
                    return await ctx.fail(
                        "An error occurred while fetching the invite."
                    )

        if guild is None:
            return await ctx.fail("Unable to find the server.")

        if not guild.banner:
            return await ctx.fail("This server does not have a banner.")

        total_guilds = len(self.bot.guilds)  # Get bot's total guild count

        embed = discord.Embed(
            title=f"{guild.name}'s Banner", url=guild.banner.url, color=self.bot.color
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar
        )
        embed.set_image(url=guild.banner.url)

        await ctx.send(embed=embed)

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
        brief="View the server roles",
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

        if not ret:
            return await ctx.fail("No roles found in this server.")

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
        name="clearnames",
        aliases=["clearnamehistory", "clnh", "clearnh"],
        brief="clear a user's name history",
        example=",clearnames @lim",
    )
    async def clearnames(self, ctx, *, user: discord.User = None):
        if user is None:
            user = ctx.author

        # Clear name history for the user
        await self.bot.db.execute("DELETE FROM names WHERE user_id = $1", user.id)

        await ctx.success(f"Successfully cleared the name history for **{str(user)}**.")

    @commands.command(
        name="names",
        aliases=["namehistory", "nh", "namehist"],
        brief="show a user's name history",
        example=",names @lim",
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
        brief="Shows information on a role",
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

    @commands.command(
        name="firstmessage",
        brief="Get a link for the first message in a channel",
    )
    async def firstmessage(self, ctx: Context, channel: discord.TextChannel = None):
        if channel is None:
            channel = ctx.channel

        try:
            async for message in channel.history(limit=1, oldest_first=True):
                if message:
                    link = message.jump_url
                    embed = discord.Embed(
                        description=f"> [First message]({link}) in {channel.mention}\n\n**Message content**:\n{message.content}",
                        color=self.bot.color,
                    )
                    await ctx.send(embed=embed)
                    return

            await ctx.fail("No messages found in this channel.")
        except Exception:
            await ctx.fail("No messages have been found in this channel.")

    @commands.command(
        name="inviteinfo",
        aliases=["ii"],
        brief="View information on an invite",
    )
    async def inviteinfo(self, ctx, invite: str):
        """View information on an invite"""

        if not invite.startswith("https://discord.gg/"):
            invite = f"https://discord.gg/{invite}"

        try:
            invite = await self.bot.fetch_invite(invite)
        except discord.NotFound:
            return await ctx.fail("Invalid invite URL or code.")

        embed = discord.Embed(
            color=self.bot.color,
        )

        invite_info = [
            f"**Code:** {invite.code}",
            f"**URL:** [Invite]({invite.url})",
            f"**Channel:** {invite.channel.name} (ID: {invite.channel.id})",
            f"**Channel Created:** {discord.utils.format_dt(invite.channel.created_at, style='F')}",
            f"**Invite Expiration:** {discord.utils.format_dt(invite.expires_at, style='F') if invite.expires_at else 'Never'}",
            f"**Inviter:** {invite.inviter.mention if invite.inviter else 'N/A'}",
            f"**Temporary:** {'Yes' if invite.temporary else 'No'}",
            f"**In Use:** {'Yes' if invite.uses else 'No'}",
        ]

        guild_info = [
            f"**Name:** {invite.guild.name}",
            f"**ID:** {invite.guild.id}",
            f"**Created:** {discord.utils.format_dt(invite.guild.created_at, style='F')}",
            f"**Members:** {invite.approximate_member_count if hasattr(invite, 'approximate_member_count') else 'N/A'}",
            f"**Verification Level:** {invite.guild.verification_level}",
        ]

        embed.add_field(
            name="**__Invite & Channel__**",
            value="\n".join([info for info in invite_info if "N/A" not in info]),
            inline=True,
        )

        embed.add_field(
            name="**__Guild__**",
            value="\n".join([info for info in guild_info if "N/A" not in info]),
            inline=True,
        )

        if invite.guild.icon:
            embed.set_thumbnail(url=invite.guild.icon.url)

        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="invites",
        brief="View all invites in the server",
    )
    async def invites(self, ctx):
        invites = await ctx.guild.invites()
        if not invites:
            return await ctx.fail("No invites found in this server.")

        invites = sorted(invites, key=lambda invite: invite.created_at, reverse=True)

        rows = []
        for i, invite in enumerate(invites, start=1):
            inviter = invite.inviter.mention if invite.inviter else "Unknown"
            created_at = discord.utils.format_dt(invite.created_at, style="R")
            rows.append(f"`{i}.` **{invite.code}** - {inviter} - {created_at}")

        embeds = []
        page = []
        for i, row in enumerate(rows, start=1):
            if i % 10 == 0 and i > 0:
                embeds.append(
                    discord.Embed(
                        color=self.bot.color,
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
                    title=f"Invites in {ctx.guild.name}",
                    description="\n".join(page),
                )
                .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
                .set_footer(text=f"Page {len(embeds) + 1}/{(len(rows) + 9) // 10}")
            )

        if not embeds:
            embeds.append(
                discord.Embed(
                    color=self.bot.color,
                    description="**No invites found in this server**",
                ).set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
            )

        await ctx.paginate(embeds)

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
                    color=self.bot.color, description="**This guild has no boosters**"
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
                color=self.bot.color, description="**Guild Has No Emojis**"
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
                        color=self.bot.color,
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
                    color=self.bot.color,
                    title=f"{ctx.guild.name}'s Emojis",
                    description="\n".join(page),
                )
                .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
                .set_footer(text=f"Page {pagenum}/{total_pages}")
            )

        if not embeds:
            embeds.append(
                discord.Embed(
                    color=self.bot.color, description="**Guild Has No Emojis**"
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

    @commands.command(
        name="boomer",
        help="Show the oldest member in the guild by account creation date.",
        aliases=["boomers", "oldest"],
    )
    async def boomer(self, ctx):
        oldest_member = min(ctx.guild.members, key=lambda m: m.created_at)

        embed = discord.Embed(title="Oldest Member", color=self.bot.color)

        embed.add_field(name="Username", value=oldest_member.name, inline=False)
        embed.add_field(
            name="Account Creation Date",
            value=oldest_member.created_at.strftime("%Y-%m-%d"),
            inline=False,
        )

        await ctx.send(embed=embed)

    @commands.command(
        name="avatar",
        aliases=["av", "useravatar"],
        description="get the mentioned user's avatar",
        brief="avatar [user]",
        help="avatar @lim",
    )
    async def avatar(
        self,
        ctx: Context,
        user: Optional[Union[discord.Member, discord.User]] = commands.Author,
    ):

        embed = discord.Embed(color=self.bot.color, title=f"{user.name}'s avatar")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar)
        embed.url = user.display_avatar.url
        embed.set_image(url=user.display_avatar)

        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="WEBP",
                url=str(user.display_avatar.replace(size=4096, format="webp")),
            )
        )
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="PNG",
                url=str(user.display_avatar.replace(size=4096, format="png")),
            )
        )
        view.add_item(
            discord.ui.Button(
                style=discord.ButtonStyle.link,
                label="JPG",
                url=str(user.display_avatar.replace(size=4096, format="jpg")),
            )
        )

        return await ctx.reply(embed=embed, view=view)

    @commands.command(name="vote")
    async def vote(self, ctx):
        """Command to send an embed with a button to vote for Greed bot on top.gg."""
        bot_id = str(self.bot.user.id)  # Use the bot's ID dynamically
        embed = Embed(
            title="Vote for Greed Bot!",
            color=self.bot.color,
            description=f"Vote for **{self.bot.user.name}** and get voter perks and econonmy rewards!",
        )
        embed.set_footer(text="You can vote once every 12 hours!")

        # Create a button that opens the vote link on top.gg
        button = discord.ui.Button(
            label="Vote Here",
            style=discord.ButtonStyle.link,
            url=f"https://top.gg/bot/{bot_id}/vote",
        )

        # Create a view to add the button
        view = discord.ui.View()
        view.add_item(button)

        await ctx.send(embed=embed, view=view)

    @commands.command()
    async def buy(self, ctx):
        """Send an embed with purchase options and buttons."""

        # Create the embed
        embed = discord.Embed(
            title="Greed Premium / Instances",
            description=(
                "Purchase Greed Premium **$3.50** monthly, **$7** one time, and **$12.50** for Instances\n\n"
                "**please open a ticket below after you have purchased one of these plans.**\n\n"
                "Prices and the available payment methods are listed here.\n\n"
                "Please do not ask to pay with Discord Nitro, or to negotiate the price. "
                "You will be either banned or just ignored.\n\n"
                "-# This is not for wrath or any other bot, this is only for **Greed**"
            ),
            color=self.bot.color,
        )

        monthly_button = Button(
            label="Monthly - $3.50",
            style=discord.ButtonStyle.green,
            url="https://buy.stripe.com/aEU5odegE3uf3egfZD",
        )
        lifetime_button = Button(
            label="Lifetime - $7",
            style=discord.ButtonStyle.blurple,
            url="https://buy.stripe.com/cN2aIxb4sd4P7uw6p4",
        )
        transfer_button = Button(
            label="Instances - $12.50",
            style=discord.ButtonStyle.blurple,
            url="https://buy.stripe.com/fZeaIxa0oe8T2accNt",
        )

        view = View()
        view.add_item(monthly_button)
        view.add_item(lifetime_button)
        view.add_item(transfer_button)

        await ctx.send(embed=embed, view=view)

    @commands.command(name="bible", brief="Get a random bible verse", example=",bible")
    async def bible(self, ctx):
        """Get a random Bible verse with reference."""
        try:
            async with self.bot.session.get(
                "https://beta.ourmanna.com/api/v1/get/?format=json"
            ) as response:
                if response.status != 200:
                    return await ctx.fail(
                        "Failed to fetch verse. Please try again later."
                    )

                data = await response.json()
                if not data.get("verse") or not data["verse"].get("details"):
                    return await ctx.fail("Invalid API response received.")

                verse = data["verse"]["details"]["text"]
                verse_reference = data["verse"]["details"]["reference"]

                # Create embed
                embed = discord.Embed(
                    title="Bible Verse", color=self.bot.color, description=f"*{verse}*"
                )
                embed.set_footer(text=verse_reference)
                embed.set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar
                )

                await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in bible command: {str(e)}")
            await ctx.fail(
                "An error occurred while fetching the verse. Please try again later."
            )

    @commands.command(
        name="quran",
        brief="Get a random quran verse with translation",
        example=",quran",
    )
    async def quran(self, ctx):
        """Get a random Quran verse with English translation."""
        try:
            # Get random verse with translation
            async with self.bot.session.get(
                "https://api.alquran.cloud/v1/ayah/random/editions/quran-simple-enhanced,en.asad"
            ) as response:
                if response.status != 200:
                    return await ctx.fail(
                        "Failed to fetch verse. Please try again later."
                    )

                data = await response.json()
                if not data.get("data") or len(data["data"]) < 2:
                    return await ctx.fail("Invalid API response received.")

                # Extract Arabic verse and English translation
                arabic = data["data"][0]
                english = data["data"][1]

                # Create embed
                embed = discord.Embed(
                    title=f"Surah {arabic['surah']['englishName']} ({arabic['surah']['name']})",
                    color=self.bot.color,
                )

                embed.description = f"{arabic['text']}\n\n*{english['text']}*"
                embed.set_footer(
                    text=f"Verse {arabic['numberInSurah']} • Juz {arabic['juz']}"
                )
                embed.set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar
                )

                await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in quran command: {str(e)}")
            await ctx.fail(
                "An error occurred while fetching the verse. Please try again later."
            )


async def setup(bot):
    await bot.add_cog(Information(bot))
