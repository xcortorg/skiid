# Standard library imports
import asyncio
import colorsys
import os
import textwrap
import traceback
from asyncio import sleep
from contextlib import suppress
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
from re import Pattern, compile
from time import perf_counter
from typing import Annotated, Dict, List, Literal, Optional, cast

# Third-party library imports
import aiohttp
# Local imports
import config
import dateparser
import lyricsgenius
import pytz
from bs4 import BeautifulSoup
from core.client.context import Context
from core.client.database.settings import Settings
from core.client.network.errors import CommandFailure
from core.managers.checks import require_dm
from core.managers.script import EmbedScript, EmbedScriptValidator
from core.Mono import Mono
from core.tools import CustomColorConverter, FlagConverter, ordinal, shorten
from core.tools.converters.basic import Domain as FilteredDomain
from core.tools.converters.basic import TimeConverter
from core.tools.converters.kayo import Timezone
from core.tools.logging import logger as log
from dateutil.tz import gettz
from discord import (Attachment, Color, Embed, File, HTTPException, Member,
                     Message, Permissions, RawReactionActionEvent, TextChannel,
                     Thread, app_commands, utils)
from discord.ext.commands import (BadArgument, BucketType, Cog, CommandError,
                                  Group, Range, command, cooldown, flag, group,
                                  has_permissions, hybrid_command,
                                  max_concurrency, parameter)
from discord.ext.tasks import loop
from discord.utils import find, format_dt, oauth_url, utcnow
from extensions.socials.models import YouTubeVideo
from extensions.utility.models.google.images import Google as GoogleImages
from extensions.utility.models.google.images import SafeSearchLevel
from humanize import naturalsize
from jishaku.math import mean_stddev
from lyricsgenius.song import Song as GeniusSong
from psutil import Process
from shazamio import Serialize as ShazamSerialize
from shazamio import Shazam as ShazamClient
from wand.image import Image as WandImage
from yarl import URL

# Module imports
from .extended import Extended
from .models.google import Google


class ScreenshotFlags(FlagConverter):
    delay: Optional[Range[int, 1, 10]] = flag(
        description="The amount of seconds to let the page render.",
        default=None,
    )

    full_page: Optional[bool] = flag(
        description="Whether or not to take a screenshot of the entire page.",
        default=None,
    )

    wait_until: Optional[str] = flag(
        description="When to consider navigation as complete.",
        default=None,
    )


class SafeSearchLevel(Enum):  # Update SafeSearchLevel to match the one in images.py
    OFF = "off"
    STRICT = "strict"


class Utility(Extended, Cog):
    def __init__(self, bot: Mono):
        self.bot: Mono = bot
        self.process = Process()
        self.genius = lyricsgenius.Genius(config.Api.Genious.client_id)
        self.genius.verbose = False
        self.shazamio = ShazamClient()
        self.hs = {
            "aries": {
                "name": "Aries",
                "emoji": ":aries:",
                "date_range": "Mar 21 - Apr 19",
                "id": 1,
            },
            "taurus": {
                "name": "Taurus",
                "emoji": ":taurus:",
                "date_range": "Apr 20 - May 20",
                "id": 2,
            },
            "gemini": {
                "name": "Gemini",
                "emoji": ":gemini:",
                "date_range": "May 21 - Jun 20",
                "id": 3,
            },
            "cancer": {
                "name": "Cancer",
                "emoji": ":cancer:",
                "date_range": "Jun 21 - Jul 22",
                "id": 4,
            },
            "leo": {
                "name": "Leo",
                "emoji": ":leo:",
                "date_range": "Jul 23 - Aug 22",
                "id": 5,
            },
            "virgo": {
                "name": "Virgo",
                "emoji": ":virgo:",
                "date_range": "Aug 23 - Sep 22",
                "id": 6,
            },
            "libra": {
                "name": "Libra",
                "emoji": ":libra:",
                "date_range": "Sep 23 - Oct 22",
                "id": 7,
            },
            "scorpio": {
                "name": "Scorpio",
                "emoji": ":scorpius:",
                "date_range": "Oct 23 - Nov 21",
                "id": 8,
            },
            "sagittarius": {
                "name": "Sagittarius",
                "emoji": ":sagittarius:",
                "date_range": "Nov 22 - Dec 21",
                "id": 9,
            },
            "capricorn": {
                "name": "Capricorn",
                "emoji": ":capricorn:",
                "date_range": "Dec 22 - Jan 19",
                "id": 10,
            },
            "aquarius": {
                "name": "Aquarius",
                "emoji": ":aquarius:",
                "date_range": "Jan 20 - Feb 18",
                "id": 11,
            },
            "pisces": {
                "name": "Pisces",
                "emoji": ":pisces:",
                "date_range": "Feb 19 - Mar 20",
                "id": 12,
            },
        }

    async def cog_load(self):
        self.reminder.start()

    async def cog_unload(self):
        self.reminder.stop()

    @loop(seconds=30)
    async def reminder(self):
        """Check for reminders"""
        for reminder in await self.bot.db.fetch("SELECT * FROM reminders"):
            if user := self.bot.get_user(reminder["user_id"]):
                if utcnow() >= reminder["timestamp"]:
                    with suppress(HTTPException):
                        await user.send(
                            embed=Embed(
                                title="Reminder",
                                description=reminder["text"],
                            )
                        )
                        await self.bot.db.execute(
                            "DELETE FROM reminders WHERE user_id = $1 AND text = $2",
                            reminder["user_id"],
                            reminder["text"],
                        )

    @Cog.listener("on_raw_reaction_add")
    async def quote_listener(
        self,
        payload: RawReactionActionEvent,
    ) -> Optional[Message]:
        record = await self.bot.db.fetchrow(
            """
            SELECT channel_id, embeds
            FROM quoter
            WHERE guild_id = $1
            AND emoji = $2
            """,
            payload.guild_id,
            str(payload.emoji),
        )
        if not record:
            return

        guild = payload.guild_id and self.bot.get_guild(payload.guild_id)
        if not guild or guild.me.is_timed_out():
            return

        payload_channel = guild.get_channel_or_thread(payload.channel_id)
        if not isinstance(payload_channel, (TextChannel, Thread)):
            return

        channel = cast(Optional[TextChannel], guild.get_channel(record["channel_id"]))
        if not channel:
            return

        message = self.bot.get_message(payload.message_id)
        if not message:
            try:
                message = await payload_channel.fetch_message(payload.message_id)
            except HTTPException:
                return

        if message.embeds and message.embeds[0].type != "image":
            embed = message.embeds[0]
        else:
            embed = Embed(color=message.author.color)

        embed.description = embed.description or ""
        embed.timestamp = message.created_at
        embed.set_author(
            name=message.author,
            icon_url=message.author.display_avatar,
            url=message.jump_url,
        )

        if message.content:
            embed.description += f"\n{message.content}"

        if message.attachments:
            attachment = message.attachments[0]
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.proxy_url)

        files: List[File] = []
        for attachment in message.attachments:
            if (
                not attachment.content_type
                or attachment.content_type.startswith("image")
                or attachment.size > guild.filesize_limit
                or not attachment.filename.endswith(
                    ("mp4", "mp3", "mov", "wav", "ogg", "webm")
                )
            ):
                continue

            file = await attachment.to_file()
            files.append(file)

        embed.set_footer(
            text=f"#{message.channel}/{message.guild or 'Unknown Guild'}",
            icon_url=message.guild.icon if message.guild else None,
        )

        if not record["embeds"] and files:
            return await channel.send(files=files)

        return await channel.send(
            embed=embed,
            files=files,
        )

    @Cog.listener("on_message")
    async def afk_listener(self, message: Message) -> Optional[Message]:
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        # Check if the message author was AFK
        left_at = await self.bot.db.fetchval(
            """
            SELECT left_at
            FROM afk
            WHERE user_id = $1
            """,
            message.author.id,
        )

        if left_at:
            await self.bot.db.execute(
                """
                DELETE FROM afk
                WHERE user_id = $1
                """,
                message.author.id,
            )
            await ctx.neutral(
                f"👋 Welcome back {message.author.mention} You were away {format_dt(left_at, 'R')}",
                reference=message,
            )
            return

        for mention in message.mentions:
            record = await self.bot.db.fetchrow(
                """
                SELECT status, left_at
                FROM afk
                WHERE user_id = $1
                """,
                mention.id,
            )
            if record:
                await ctx.neutral(
                    f"{mention.mention} is currently AFK: **{record['status']}** - {format_dt(record['left_at'], 'R')}",
                    reference=message,
                )

    @command(aliases=["away"])
    async def afk(
        self,
        ctx: Context,
        *,
        status: str = "AFK",
    ) -> Optional[Message]:
        """
        Set an AFK status.
        """

        status = shorten(status, 200)
        await self.bot.db.execute(
            """
            INSERT INTO afk (user_id, status, left_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
            SET status = EXCLUDED.status, left_at = EXCLUDED.left_at
            """,
            ctx.author.id,
            status,
            utcnow(),
        )
        return await ctx.approve(f"You're now **AFK** with the status **{status}**")

    @command()
    async def ping(self, ctx: Context) -> Message:
        """
        Check the bot's ping.
        """
        return await ctx.reply(f"`{round(self.bot.latency * 1000)}ms`")

    #    @command()
    #    async def ping(self, ctx: Context) -> Message:
    #        """
    #        Check the bot's ping using Jishaku's RTT command.
    #        """
    #        jsk_rtt = self.bot.get_command("jsk rtt")
    #        if jsk_rtt:
    #            return await ctx.invoke(jsk_rtt)

    #    @command(name="ping")
    #    @cooldown(1, 5, BucketType.channel)
    #    async def ping(self, ctx: Context) -> Optional[Message]:
    #        """
    #        View the round-trip latency to the Discord API.
    #        """
    #
    #        message: Optional[Message] = None
    #        embed = Embed(title="Round-Trip Latency")
    #
    #        api_readings: List[float] = []
    #        websocket_readings: List[float] = []
    #
    #        for _ in range(5):
    #            if api_readings:
    #                embed.description = (
    #                    ">>> ```bf\n"
    #                    + "\n".join(
    #                        f"Trip {index + 1}: {reading * 1000:.2f}ms"
    #                        for index, reading in enumerate(api_readings)
    #                    )
    #                    + "```"
    #                )
    #
    #            text = ""
    #
    #            if api_readings:
    #                average, stddev = mean_stddev(api_readings)
    #
    #                text += f"Average: `{average * 1000:.2f}ms` `\N{PLUS-MINUS SIGN}` `{stddev * 1000:.2f}ms`"
    #
    #            if websocket_readings:
    #                average = sum(websocket_readings) / len(websocket_readings)
    #
    #                text += f"\nWebsocket Latency: `{average * 1000:.2f}ms`"
    #            else:
    #                text += f"\nWebsocket latency: `{self.bot.latency * 1000:.2f}ms`"
    #
    #            if message:
    #                embed = message.embeds[0]
    #                embed.clear_fields()
    #                embed.add_field(
    #                    name="​",
    #                    value=text,
    #                )
    #
    #                before = perf_counter()
    #                await message.edit(embed=embed)
    #                after = perf_counter()
    #
    #                api_readings.append(after - before)
    #            else:
    #                embed.add_field(
    #                    name="​",
    #                    value=text,
    #                )
    #
    #                before = perf_counter()
    #                message = await ctx.send(embed=embed)
    #                after = perf_counter()
    #
    #                api_readings.append(after - before)
    #
    #            if self.bot.latency > 0.0:
    #                websocket_readings.append(self.bot.latency)
    #
    #        if message:
    #            return message

    @hybrid_command(example="example.com --delay 5", aliases=["ss"], hidden=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @cooldown(1, 5, BucketType.user)
    async def screenshot(
        self, ctx: Context, url: FilteredDomain, *, flags: ScreenshotFlags
    ) -> Message:
        """
        Capture a screenshot of a webpage.
        > full_page takes yes or no as an argument
        """

        async with ctx.typing():
            try:
                async with ctx.bot.browser.borrow_page() as page:
                    await page.emulate_media(color_scheme="dark")
                    await page.goto(
                        str(url), wait_until=flags.wait_until or "load", timeout=30000
                    )

                    if flags.delay:
                        await sleep(flags.delay)

                    screenshot_options = {
                        "full_page": flags.full_page,
                        "type": "jpeg",
                        "quality": 80,
                    }

                    screenshot = await page.screenshot(**screenshot_options)
            except Exception as e:
                return await ctx.warn(f"Failed to capture screenshot: {e}")

        return await ctx.send(file=File(BytesIO(screenshot), filename="screenshot.jpg"))

    @command(aliases=["bi"])
    async def botinfo(self, ctx: Context) -> Message:
        """
        View information about the bot.
        """

        def count_commands(commands):
            total = 0
            for command in commands:
                #                # Skip Jishaku commands
                #                if command.cog_name == "Jishaku":
                #                    continue
                total += 1
                if isinstance(command, Group):
                    total += count_commands(command.commands)
            return total

        # Count the number of commands
        command_count = count_commands(self.bot.commands)

        embed = Embed(
            description=(
                ""
                + (
                    f"\nServing `{len(self.bot.guilds):,}` **servers**"
                    f" with `{len(self.bot.users):,}` **users**."
                )
                + (
                    f"\nUtilizing `{command_count}` **commands** "
                    f" across `{len(self.bot.cogs):,}` **extensions**."
                )
            ),
        )
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.avatar,
            url=config.Mono.support
            or oauth_url(self.bot.user.id, permissions=Permissions(permissions=8)),
        )

        embed.add_field(
            name="Process",
            value="\n".join(
                [
                    f"**Latency:** `{round(self.bot.latency * 1000)}ms`",
                    f"**RAM:** `{naturalsize(self.process.memory_info().rss)}`",
                    f"**Launched:** {format_dt(self.bot.uptime, 'R')}",
                ]
            ),
            inline=True,
        )
        embed.add_field(
            name="Links",
            value="\n".join(
                [
                    f"[`Website`]({config.Mono.website})",
                    f"[`Support`]({config.Mono.support})",
                    f"[`Docs`]({config.Mono.docs})",
                ]
            ),
            inline=True,
        )
        embed.set_footer(
            text=f"{self.bot.user.name.upper()}/{self.bot.version}    CPU : {self.process.cpu_percent()}%   VM : {self.process.memory_info().vms / 1024 / 1024:.2f} MB"
        )
        return await ctx.reply(embed=embed)

    @command(
        name="selfprefix",
        aliases=["selfp"],
        example="$",
    )
    async def selfprefix(
        self,
        ctx: Context,
        *,
        prefix: Optional[str] = None,
    ) -> Message:
        """
        Set a custom prefix for yourself.
        > `selfprefix remove` to remove your custom prefix.
        > `selfprefix <prefix>` to set your custom prefix.
        """
        if prefix:
            if prefix.lower() == "remove":
                await ctx.prompt(
                    "Are you sure you want to **remove** your custom prefix?",
                    "This action will reset your prefix to the default.",
                )
                await Settings.remove_self_prefix(self.bot, ctx.author)
                return await ctx.approve("Your **custom prefix** has been removed.")
            else:
                if len(prefix) > 5:
                    return await ctx.warn(
                        "Your prefix cannot be longer than 5 characters."
                    )

                await ctx.prompt(
                    f"Are you sure you want to set your **custom prefix** to `{prefix}`?",
                    "This will change how you interact with the bot's commands.",
                )
                await Settings.set_self_prefix(self.bot, ctx.author, prefix)
                return await ctx.approve(
                    f"Your **custom prefix** has been set to: `{prefix}`"
                )
        else:
            current_prefix = await Settings.get_self_prefix(self.bot, ctx.author)
            if current_prefix:
                return await ctx.neutral(f"Your prefix is: `{current_prefix}`")
            else:
                return await ctx.send_help(ctx.command)

    @command(aliases=["ai", "ask", "chatgpt", "gpt"])
    async def gemini(self, ctx: Context, *, question: str) -> Optional[Message]:
        """
        Ask AI a question.
        """

        async with ctx.typing():
            response = await self.bot.session.post(
                URL.build(
                    scheme="https",
                    host="generativelanguage.googleapis.com",
                    path="/v1/models/gemini-pro:generateContent",
                    query={
                        "key": config.Api.GEMINI,
                    },
                ),
                json={"contents": [{"parts": [{"text": question}]}]},
            )

            if not (data := await response.json()):
                return await ctx.warn("No response was found for that question!")

            if not (content := data.get("candidates", [])[0].get("content")) or not (
                parts := content.get("parts")
            ):
                return await ctx.warn("No response was found for that question!")

            await ctx.reply(parts[0]["text"])

    @command(
        name="shazam",
        usage="<attachment>",
        aliases=[
            "recognize",
            "find",
        ],
    )
    @max_concurrency(1, wait=True)
    @cooldown(1, 5, BucketType.user)
    async def shazam(
        self,
        ctx: Context,
    ) -> Message:
        """
        Recognize a song from an attachment.
        """
        attachment = None

        if ctx.message.reference:
            ref_message = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
            if ref_message.attachments:
                attachment = ref_message.attachments[0]
            else:
                return await ctx.warn(
                    "The replied-to message does not contain a video or audio file."
                )
        elif ctx.message.attachments:
            attachment = ctx.message.attachments[0]

        if not attachment:
            return await ctx.warn(
                "Please provide a video or audio file or reply to a message with one."
            )

        if not (
            attachment.content_type.startswith("audio/")
            or attachment.content_type.startswith("video/")
        ):
            return await ctx.warn("The provided file is not an audio or video file.")

        async with ctx.typing():
            data = await self.shazamio.recognize(await attachment.read())
            output = ShazamSerialize.full_track(data)

        if not (track := output.track):
            return await ctx.warn(
                f"Couldn't recognize any tracks from [{attachment.filename}]({attachment.url})!"
            )

        track_url = data.get("track", {}).get("share", {}).get("href", "N/A")
        artist_url = URL(f"https://google.com/search?q={track.subtitle}")
        cover_art = data.get("track", {}).get("images", {}).get("coverart")

        return await ctx.shazam(
            f"**Track** \n> [`{shorten(track.title)}`]({track_url})\n"
            f"**Artist** \n> [`{track.subtitle}`]({artist_url}).",
            cover_art=cover_art,
            reference=ctx.message,
        )

    @command(
        name="quickpoll",
        example="im i ugly",
    )
    async def quickpoll(self, ctx: Context, *, question: str):
        """
        Create a quick poll
        """
        await ctx.message.add_reaction("⬆️")
        await ctx.message.add_reaction("⬇️")

    @command(
        name="poll",
        usage="[duration] <question>",
        example="15 Is this a good bot?",
    )
    @cooldown(1, 5, BucketType.user)
    async def poll(self, ctx: Context, duration: Optional[int] = 20, *, question: str):
        """
        Create a timed poll
        """
        embed = Embed(
            description=f"{ctx.author.mention} started a poll that will end after **{duration}** second(s)!\n**Question:** {question}",
            color=config.Color.base,
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        embed.set_footer(
            text=f"Guild: {ctx.guild.name} • Channel: {ctx.channel.name} • "
        )

        poll_message = await ctx.send(embed=embed)
        await poll_message.add_reaction("👍")
        await poll_message.add_reaction("👎")

        await sleep(duration)

        poll_message = await ctx.channel.fetch_message(poll_message.id)
        thumbs_up = utils.get(poll_message.reactions, emoji="👍")
        thumbs_down = utils.get(poll_message.reactions, emoji="👎")

        embed.add_field(
            name="Results",
            value=f"👍 `{thumbs_up.count - 1}` / 👎 `{thumbs_down.count - 1}`",
            inline=False,
        )
        embed.timestamp = datetime.now(timezone.utc)
        embed.set_footer(text=f"Poll ended • {ctx.guild.name} • {ctx.channel.name} •")

        await ctx.send(embed=embed)
        await poll_message.delete()

    @command(
        name="dominant",
        example="reply or attachment",
    )
    async def dominant(self, ctx: Context, image_url: str = None) -> Message:
        """Get the dominant color of an image from a URL, attachment, or replied message"""
        # Check for replied message with attachment
        if ctx.message.reference:
            replied_message = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
            if replied_message.attachments:
                image_url = replied_message.attachments[0].url
        # Check for attachment in the command message
        elif not image_url and ctx.message.attachments:
            image_url = ctx.message.attachments[0].url

        if not image_url:
            return await ctx.send_help(ctx.command)

        try:
            async with self.bot.session.get(image_url) as response:
                if response.status != 200:
                    return await ctx.warn("Failed to fetch the image.")
                image_data = await response.read()

            with WandImage(blob=image_data) as img:
                img.resize(100, 100)
                img.quantize(number_colors=5, colorspace_type="srgb")
                histogram = img.histogram
                dominant_color = max(histogram, key=histogram.get)
                hex_color = f"{dominant_color.red_int8:02x}{dominant_color.green_int8:02x}{dominant_color.blue_int8:02x}"

            async with self.bot.session.get(
                f"https://api.alexflipnote.dev/color/{hex_color}"
            ) as resp:
                if resp.status != 200:
                    return await ctx.warn("Failed to fetch color information.")
                data = await resp.json()

            embed = Embed(
                title=f"Dominant Color: {data['name']}",
                color=Color(int(hex_color, 16)),
                url=f"https://www.color-hex.com/color/{hex_color}",
            )
            embed.add_field(name="HEX", value=f"`#{hex_color.upper()}`", inline=True)
            embed.add_field(
                name="RGB",
                value=f"`{dominant_color.red_int8}, {dominant_color.green_int8}, {dominant_color.blue_int8}`",
                inline=True,
            )
            embed.add_field(
                name="HSL",
                value=f"`{data['hsl']['h']}, {data['hsl']['s']}, {data['hsl']['l']}`",
                inline=True,
            )
            embed.set_thumbnail(
                url=f"https://api.alexflipnote.dev/color/image/{hex_color}"
            )
            embed.set_image(
                url=f"https://api.alexflipnote.dev/color/image/gradient/{hex_color}"
            )

            return await ctx.reply(embed=embed)
        except Exception as e:
            return await ctx.warn(f"An error occurred: {str(e)}")

    @command(
        name="color",
        usage="(hex, random, member, role, or color name)",
        example="#c2e746",
        aliases=["colour"],
    )
    async def color(
        self, ctx: Context, *, color_input: CustomColorConverter = Color(0)
    ):
        """
        Show a hex code's color in an embed
        """
        try:
            hex_color = str(color_input).replace("#", "")
            color_url = f"https://www.color-hex.com/color/{hex_color}"

            embed = Embed(color=color_input, url=color_url)
            embed.set_author(name=f"Showing color: #{hex_color}", url=color_url)
            embed.set_thumbnail(
                url=f"https://api.alexflipnote.dev/color/image/{hex_color}"
            )
            embed.set_image(
                url=f"https://api.alexflipnote.dev/color/image/gradient/{hex_color}"
            )

            embed.add_field(
                name="HEX",
                value=f"[`#{hex_color.upper()}`]({color_url})",
                inline=True,
            )
            embed.add_field(
                name="RGB Value",
                value=f"`{color_input.r}, {color_input.g}, {color_input.b}`",
                inline=True,
            )
            embed.add_field(
                name="HSL Value",
                value="`"
                + ", ".join(
                    f"{int(value * (360 if index == 0 else 100))}%"
                    for index, value in enumerate(
                        colorsys.rgb_to_hls(*[x / 255.0 for x in color_input.to_rgb()])
                    )
                )
                + "`",
                inline=True,
            )

            return await ctx.reply(embed=embed)
        except BadArgument as e:
            return await ctx.warn(str(e))
        except Exception as e:
            error_code = await self.bot.log_error(ctx, e)

    @command(
        name="urban",
        usage="(word)",
        example="dog",
        aliases=["define"],
    )
    async def urban(self, ctx: Context, *, word: str):
        """
        find a definition of a word
        """

        embeds = []

        # Use the custom Network class to make the request
        response = await self.bot.session.request(
            url="http://api.urbandictionary.com/v0/define",
            method="GET",
            params={"term": word},
        )

        data = await response.json()

        defs = data["list"]
        if len(defs) == 0:
            return await ctx.warn(
                f"No definition found for **{word}**", reference=ctx.message
            )

        for defi in defs:
            e = (
                Embed(
                    color=config.Color.base,
                    title=defi["word"],
                    description=defi["definition"],
                    url=defi["permalink"],
                )
                .set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                .add_field(name="Example", value=defi["example"], inline=False)
                .add_field(
                    name="Votes",
                    value=f"👍 `{defi['thumbs_up']} / {defi['thumbs_down']}` 👎",
                    inline=False,
                )
                .set_footer(
                    text=f"Page {defs.index(defi) + 1}/{len(defs)} of Urban Dictionary Results",
                    icon_url=ctx.author.display_avatar.url,
                )
            )
            embeds.append(e)

        await ctx.paginate(embeds)

    @command(
        name="safesearch",
        aliases=["safetylevel", "googlesafetylevel"],
        example="moderate",
    )
    @has_permissions(manage_guild=True)
    async def safesearch(
        self, ctx: Context, level: Optional[SafeSearchLevel] = None
    ) -> Message:
        """
        Set or view the Google SafeSearch level for the server.
        > Levels: off - strict
        """
        if level is None:
            current_level = await self.bot.db.fetchval(
                """
                SELECT safesearch_level
                FROM settings
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            return await ctx.neutral(
                f"The current **SafeSearch** level for this server is: **`{current_level}`**"
            )

        await self.bot.db.execute(
            """
            UPDATE settings
            SET safesearch_level = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            level.value,
        )
        return await ctx.approve(
            f"The **SafeSearch** level for this **server** has been set to: **`{level.value}`**"
        )

    @command(
        name="reverse",
        aliases=["rimg", "sauce"],
    )
    async def reverse(
        self,
        ctx: Context,
        attachment: Attachment | None = None,
    ) -> Message:
        """
        Reverse search an image on Google.
        """

        if (
            not attachment
            or not attachment.content_type
            or not attachment.content_type.startswith("image/")
        ):
            return await ctx.warn("Please provide a valid image attachment!")

        async with ctx.typing():
            classes: Dict[str, str | Pattern[str]] = {
                "description": compile("VwiC3b yXK7lf"),
                "result": "srKDX cvP2Ce",
                "related": "fKDtNb",
            }
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="www.google.com",
                    path="/searchbyimage",
                    query={
                        "safe": "off" if ctx.channel.is_nsfw() else "on",
                        "sbisrc": "tg",
                        "image_url": attachment.url,
                    },
                ),
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) "
                        "Gecko/20100101 Firefox/111.0"
                    )
                },
            )
            content = await response.text()

            data = BeautifulSoup(content, "lxml")
            related = data.find("a", class_=classes["related"])
            results = data.findAll("div", class_=classes["result"])
            if not related or not results:
                return await ctx.warn(
                    f"No results were found for [`{attachment.filename}`]({attachment.url})!"
                )

        embed = Embed(
            title="Reverse Image Search",
            description=f"*`{related.text}`*",
        )
        embed.set_thumbnail(url=attachment.url)
        if stats := data.find("div", id="result-stats"):
            embed.set_footer(text=stats.text)

        for result in results[:3]:
            link = result.a.get("href")
            title = result.find("h3").text
            description = (
                result.find("div", class_=classes["description"])
                .findAll("span")[-1]
                .text
            )

            embed.add_field(
                name=title,
                value=f"[`{shorten(description, 65)}`]({link})",
                inline=False,
            )

        return await ctx.send(embed=embed)

    @command(
        aliases=["g", "ddg"],
        invoke_without_command=True,
    )
    @cooldown(3, 60, BucketType.user)
    async def google(self, ctx: Context, *, query: str) -> Message:
        """
        Search a query on Google.
        """
        safesearch_level = await self.bot.db.fetchval(
            """
            SELECT safesearch_level
            FROM settings
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        async with ctx.typing():
            data = await Google.search(
                self.bot.session, query, safe=safesearch_level
            )  # Pass the SafeSearch level
            if not data.results:
                return await ctx.warn(f"No results found for **{query}**!")

        embed = Embed(
            title=(
                f"{data.header}"
                + (f" - {data.description}" if data.description else "")
                if data.header
                else f"Google Search - {query}"
            ),
            color=config.Color.base,
        )

        # Add Knowledge Panel Items to the description
        if panel := data.panel:
            if panel.source:
                embed.url = panel.source.url

            embed.description = (
                shorten(panel.description, 200) if panel.description else ""
            )

            for item in panel.items:
                if embed.description:
                    embed.description += (
                        "\n"  # Add a newline if there's existing description
                    )
                embed.description += f"> **{item.name}:** `{item.value}`"

        description = []
        for result in data.results:
            snippet = result.snippet or (".." if not result.tweets else "")
            for highlight in result.highlights:
                snippet = snippet.replace(highlight, f"**{highlight}**")

            result_text = f"**[{result.title}]({result.url.split('?', 1)[0]})**\n{shorten(snippet, 200)}"

            if result.extended_links:
                result_text += "\n" + "\n".join(
                    f"> [`{extended.title}`]({extended.url}): {textwrap.shorten(extended.snippet or '...', 46, placeholder='..')}"
                    for extended in result.extended_links
                )

            if result.tweets:
                result_text += "\n" + "\n".join(
                    f"> [`{textwrap.shorten(tweet.text, 46, placeholder='..')}`]({tweet.url}) **{tweet.footer}**"
                    for tweet in result.tweets[:3]
                )

            description.append(result_text)

        # Add the knowledge items to the description
        if panel and panel.items:
            description.append("\n")
            for item in panel.items:
                description.append(f"> **{item.name}:** `{item.value}`")

        return await ctx.autopaginator(embed, description, split=5)

    @command(
        name="lyrics",
        aliases=["ly", "genius"],
        usage="<song name>",
        example="f*ck swag nettspend",
    )
    @cooldown(1, 5, BucketType.user)
    async def lyrics(self, ctx: Context, *, query: str) -> Message:
        """
        Search for song lyrics on Genius.
        """
        async with ctx.typing():
            try:
                song: GeniusSong = await self.bot.loop.run_in_executor(
                    None, self.genius.search_song, query
                )
                if not song:
                    return await ctx.warn(f"No lyrics found for **{query}**!")

                lyrics = song.lyrics.split("\n")

                artist_url = (
                    f"https://genius.com/artists/{song.artist.replace(' ', '-')}"
                )

                embed = Embed(
                    title=f"**{song.title}**", url=song.url, color=config.Color.base
                )
                embed.set_author(name=song.artist, url=artist_url)
                if song.song_art_image_url:
                    embed.set_thumbnail(url=song.song_art_image_url)

                pages = []
                current_page = ""

                for line in lyrics:
                    if line.strip() == "Embed" or "Contributors" in line:
                        continue

                    if "[Chorus]" in line or len(current_page) + len(line) + 1 > 1000:
                        if current_page:
                            pages.append(current_page.strip())
                        current_page = line + "\n"
                    else:
                        current_page += line + "\n"

                if current_page:
                    pages.append(current_page.strip())

                embeds = []
                for i, page in enumerate(pages):
                    embed_copy = embed.copy()
                    embed_copy.description = page
                    embed_copy.set_footer(text=f"Page {i+1} of {len(pages)}")
                    embeds.append(embed_copy)

                if len(embeds) > 1:
                    return await ctx.paginate(embeds)
                else:
                    return await ctx.reply(embed=embeds[0])

            except Exception as e:
                return await ctx.warn(
                    f"An error occurred while fetching lyrics: {str(e)}"
                )

    @command(
        name="createembed",
        usage="(embed script)",
        example="{title: hello!}",
        aliases=["embed", "ce"],
    )
    async def createembed(self, ctx: Context, *, script: EmbedScriptValidator):
        """
        Send an embed to the channel
        > variables **[`here`](https://docs.skunkk.xyz/)**

        """
        await script.send(
            ctx,
            bot=self.bot,
            guild=ctx.guild,
            channel=ctx.channel,
            user=ctx.author,
        )

    @command(
        name="copyembed",
        usage="(message)",
        example="dscord.com/chnls/999/..",
        aliases=["embedcode", "ec"],
    )
    async def copyembed(self, ctx: Context, message: Optional[Message] = None):
        """Copy embed code for a message. Reply to a message or provide a message link."""
        if message is None:
            if ctx.message.reference:
                message = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
            else:
                return await ctx.warn(
                    "Please reply to a message or provide a message link."
                )

        result = []
        if content := message.content:
            result.append(f"{{content: {content}}}")

        for embed in message.embeds:
            result.append("{embed}")
            if color := embed.color:
                result.append(f"{{color: {color}}}")

            if author := embed.author:
                _author = []
                if name := author.name:
                    _author.append(name)
                if icon_url := author.icon_url:
                    _author.append(icon_url)
                if url := author.url:
                    _author.append(url)

                result.append(f"{{author: {' && '.join(_author)}}}")

            if url := embed.url:
                result.append(f"{{url: {url}}}")

            if title := embed.title:
                result.append(f"{{title: {title}}}")

            if description := embed.description:
                result.append(f"{{description: {description}}}")

            result.extend(
                f"{{field: {field.name} && {field.value} && {str(field.inline).lower()}}}"
                for field in embed.fields
            )
            if thumbnail := embed.thumbnail:
                result.append(f"{{thumbnail: {thumbnail.url}}}")

            if image := embed.image:
                result.append(f"{{image: {image.url}}}")

            if footer := embed.footer:
                _footer = []
                if text := footer.text:
                    _footer.append(text)
                if icon_url := footer.icon_url:
                    _footer.append(icon_url)

                result.append(f"{{footer: {' && '.join(_footer)}}}")

            if timestamp := embed.timestamp:
                result.append(f"{{timestamp: {str(timestamp)}}}")

        if not result:
            return await ctx.warn(
                f"Message [`{message.id}`]({message.jump_url}) doesn't contain an embed"
            )

        result = "\n".join(result)
        return await ctx.approve(f"Copied the **embed code**\n```{result}```")

    @command(
        name="weather",
        example="New York",
    )
    @cooldown(1, 4, BucketType.user)
    async def weather(self, ctx: Context, *, location: str):
        """
        Get the weather for a location.
        """
        await ctx.typing()

        url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={config.Api.OPEN_WEATHER}&units=metric"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()

        if data.get("cod") != 200:
            await ctx.warn(
                f"{ctx.author.mention}: Could not find weather data for {location}."
            )
            return

        weather = data["weather"][0]
        main = data["main"]
        wind = data["wind"]
        sys = data["sys"]

        temp_celsius = main["temp"]
        temp_fahrenheit = (temp_celsius * 9 / 5) + 32

        local_tz = pytz.FixedOffset(data["timezone"] // 60)
        sunrise_time = (
            datetime.utcfromtimestamp(sys["sunrise"])
            .replace(tzinfo=pytz.utc)
            .astimezone(local_tz)
        )
        sunset_time = (
            datetime.utcfromtimestamp(sys["sunset"])
            .replace(tzinfo=pytz.utc)
            .astimezone(local_tz)
        )

        embed = Embed(
            title=f"{weather['description'].title()} in {data['name']}, {sys['country']}",
            color=config.Color.base,
            timestamp=datetime.utcnow(),
        )
        embed.set_thumbnail(
            url=f"http://openweathermap.org/img/wn/{weather['icon']}.png"
        )
        embed.add_field(
            name="Temperature",
            value=f"{temp_celsius:.2f} °C / {temp_fahrenheit:.2f} °F",
            inline=True,
        )
        embed.add_field(name="Wind", value=f"{wind['speed']} mph", inline=True)
        embed.add_field(name="Humidity", value=f"{main['humidity']}%", inline=True)
        embed.add_field(
            name="Sunrise", value=utils.format_dt(sunrise_time, style="T"), inline=True
        )
        embed.add_field(
            name="Sunset", value=utils.format_dt(sunset_time, style="T"), inline=True
        )
        embed.add_field(
            name="Visibility", value=f"{data['visibility'] / 1000:.1f} km", inline=True
        )
        embed.set_footer(
            text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)

    @group(
        aliases=["bday", "bd"],
        invoke_without_command=True,
    )
    async def birthday(
        self,
        ctx: Context,
        *,
        member: Member = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View your birthday.
        """

        birthday = cast(
            Optional[datetime],
            await self.bot.db.fetchval(
                """
                SELECT birthday
                FROM birthdays
                WHERE user_id = $1
                """,
                member.id,
            ),
        )
        if not birthday:
            if member == ctx.author:
                return await ctx.warn(
                    "You haven't set your birthday yet!",
                    f"Use `{ctx.clean_prefix}birthday set <date>` to set it",
                )

            return await ctx.warn(f"**{member}** hasn't set their birthday yet!")

        current = utcnow()
        next_birthday = current.replace(
            year=current.year + 1,
            month=birthday.month,
            day=birthday.day,
        )
        if next_birthday.day == current.day and next_birthday.month == current.month:
            phrase = "**today**, happy birthday! 🎊"
        elif (
            next_birthday.day + 1 == current.day
            and next_birthday.month == current.month
        ):
            phrase = "**tomorrow**, happy early birthday! 🎊"
        else:
            days_until_birthday = (next_birthday - current).days
            if days_until_birthday > 365:
                next_birthday = current.replace(
                    year=current.year,
                    month=birthday.month,
                    day=birthday.day,
                )
                days_until_birthday = (next_birthday - current).days

            phrase = f"**{next_birthday.strftime('%B')} {ordinal(next_birthday.day)}**, that's {format_dt(next_birthday, 'R')}"

        return await ctx.neutral(
            f"Your birthday is {phrase}"
            if member == ctx.author
            else f"**{member}**'s birthday is {phrase}"
        )

    @birthday.command(name="set")
    async def birthday_set(
        self,
        ctx: Context,
        *,
        date: str,
    ) -> Message:
        """
        Set your birthday
        """

        birthday = dateparser.parse(date)
        if not birthday:
            return await ctx.warn(f"Date not found for **{date}**")

        await self.bot.db.execute(
            """
            INSERT INTO birthdays (user_id, birthday)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET birthday = EXCLUDED.birthday
            """,
            ctx.author.id,
            birthday,
        )
        return await ctx.approve(
            f"Your birthday has been set to **{birthday:%B} {ordinal(birthday.strftime('%-d'))}**"
        )

    @group(
        aliases=["time", "tz"],
        invoke_without_command=True,
    )
    async def timezone(
        self,
        ctx: Context,
        *,
        member: Member = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View your local time.
        """

        timezone = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT timezone
                FROM timezones
                WHERE user_id = $1
                """,
                member.id,
            ),
        )
        if not timezone:
            if member == ctx.author:
                return await ctx.warn(
                    "You haven't set your timezone yet!",
                    f"Use `{ctx.clean_prefix}timezone set <location>` to set it",
                )

            return await ctx.warn(f"**{member}** hasn't set their timezone yet!")

        timestamp = utcnow().astimezone(gettz(timezone))
        return await ctx.neutral(
            f"It's currently **{timestamp.strftime('%B %d, %I:%M %p')}** "
            + ("for you" if member == ctx.author else f"for {member.mention}")
        )

    @timezone.command(name="set")
    async def timezone_set(
        self,
        ctx: Context,
        *,
        timezone: Annotated[
            str,
            Timezone,
        ],
    ) -> Message:
        """
        Set your local timezone.
        """

        await self.bot.db.execute(
            """
            INSERT INTO timezones (user_id, timezone)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
            SET timezone = EXCLUDED.timezone
            """,
            ctx.author.id,
            timezone,
        )
        return await ctx.approve(f"Your timezone has been set to `{timezone}`")

    @group(
        name="remind",
        usage="(duration) (text)",
        example="1h go to the gym",
        aliases=["reminder"],
        invoke_without_command=True,
    )
    @require_dm()
    async def remind(
        self,
        ctx: Context,
        duration: TimeConverter,
        *,
        text: str,
    ):
        """Set a reminder"""
        if duration.seconds < 60:
            return await ctx.warn("Duration must be at least **1 minute**")

        try:
            await self.bot.db.execute(
                "INSERT INTO reminders (user_id, text, jump_url, created_at, timestamp) VALUES ($1, $2, $3, $4, $5)",
                ctx.author.id,
                text,
                ctx.message.jump_url,
                ctx.message.created_at,
                ctx.message.created_at + duration.delta,
            )

        except Exception:
            return await ctx.warn(f"Already being reminded for **{text}**")

        await ctx.approve(
            f"I'll remind you {format_dt(ctx.message.created_at + duration.delta, style='R')}"
        )

    @remind.command(
        name="remove",
        usage="(text)",
        example="go to the gym",
        aliases=["delete", "del", "rm", "cancel"],
    )
    async def remove(self, ctx: Context, *, text: str):
        """Remove a reminder"""
        try:
            await self.bot.db.execute(
                "DELETE FROM reminders WHERE user_id = $1 AND lower(text) = $2",
                ctx.author.id,
                text.lower(),
            )
        except Exception:
            return await ctx.warn(f"Coudn't find a reminder for **{text}**")

        return await ctx.approve(f"Removed reminder for **{text}**")

    @remind.command(
        name="list",
        aliases=["show", "view"],
    )
    async def remind_list(self, ctx: Context):
        """
        Get a list of your reminders
        """

        reminders = await self.bot.db.fetch(
            "SELECT * FROM reminders WHERE user_id = $1", ctx.author.id
        )

        if not reminders:
            return await ctx.warn("You do not have any upcoming reminders")

        # Format reminders with an index starting at 01
        formatted_reminders = [
            f"`{index:02}` {r.reminder}** {utils.format_dt(r.remind_at, style='R')}"
            for index, r in enumerate(
                sorted(reminders, key=lambda re: re.remind_at), start=1
            )
        ]

        return await ctx.autopaginator(
            Embed(title="Your reminders").set_footer(
                text="To remove a reminder use remind remove [index] where index is the remind number shown on this embed"
            ),
            description=formatted_reminders,
        )

    @command(
        name="image",
        usage="<query>",
        example="cute cats",
        aliases=["img", "imgsearch"],
    )
    @cooldown(1, 5, BucketType.user)
    async def image(self, ctx: Context, *, query: str):
        """
        Search for images on Google
        """
        await ctx.typing()
        try:
            # Fetch the SafeSearch level from the database
            safesearch_level = await self.bot.db.fetchval(
                """
                SELECT safesearch_level
                FROM settings
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )

            # Ensure the fetched level is a valid SafeSearchLevel
            safesearch_enum = (
                SafeSearchLevel[safesearch_level.upper()]
                if safesearch_level
                else SafeSearchLevel.MODERATE
            )

            # Log the SafeSearch level being used
            log.info(f"Using SafeSearch level: {safesearch_enum.value}")

            # Initialize Google instance with the session and SafeSearch level
            google = GoogleImages(
                session=self.bot.session, safe_search=safesearch_enum, max_results=5
            )

            # Get the list of image URLs directly
            results = await google.images(
                query, safe_search=safesearch_enum
            )  # Pass the SafeSearch level here

            # Debugging: Log the number of results
            log.info(f"Number of results found: {len(results)}")
            if not results:
                return await ctx.warn(f"No images found for **{query}**")

            embeds = []
            for i, image_url in enumerate(results, 1):
                embed = Embed(
                    title=f"Image result {i} for: {query}",
                    color=config.Color.base,
                    url=image_url,
                )
                embed.set_image(url=image_url)  # Set the direct image URL
                embed.set_footer(text=f"Page {i} of {len(results)}")
                embeds.append(embed)

            await ctx.paginate(embeds)  # This should work with the existing paginator

        except CommandFailure as e:
            await ctx.warn(f"An error occurred while searching for images: {str(e)}")
            log.error(f"CommandFailure in image search: {str(e)}")
        except Exception as e:
            await ctx.warn(f"An unexpected error occurred while searching for images.")
            log.error(f"Unexpected error in image search: {str(e)}")
            log.error(traceback.format_exc())

    @command()
    async def credits(self, ctx: Context):
        """
        View the credits for the bot.
        """
        return await ctx.neutral(
            "Developed by <@1247076592556183598> [`Github`](https://github.com/hiddeout?tab=repositories) \n>  If i stole some of your code please contact me so i can block you"
        )

    @command(example="how to get a cat")
    async def wikihow(self, ctx: Context, *, question: str):
        """
        Get answers to your question from wikihow
        """

        html = await self.bot.session.get(
            "https://www.wikihow.com/wikiHowTo", params={"search": question}
        )
        html_content = await html.text()  # Get the text content of the response

        soup = BeautifulSoup(html_content, "html.parser")
        searchlist = soup.find("div", attrs={"id": "searchresults_list"})
        contents = searchlist.find_all("a", attrs={"class": "result_link"})

        for content in contents:
            url = content["href"]
            if not "Category:" in url:
                title = content.find("div", attrs={"class": "result_title"})
                x = await self.bot.session.get(url)
                s = BeautifulSoup(
                    await x.text(), "html.parser"
                )  # Get the text content of the response
                steps = s.find_all("b", attrs={"class": "whb"})
                embed = Embed(
                    title=title.text,
                    url=url,
                    description="\n".join(
                        [
                            f"`{i}.` {step.text}"
                            for i, step in enumerate(steps[:10], start=1)
                        ]
                    ),
                ).set_footer(text="wikihow.com")
                return await ctx.reply(embed=embed)

        return await ctx.warn("Unfortunately i found nothing")

    @group(aliases=["hs"], invoke_without_command=True)
    async def horoscope(self, ctx: Context):
        """Get your daily horoscope."""
        await self.send_hs(ctx, "daily-today")

    @horoscope.command(name="tomorrow")
    async def horoscope_tomorrow(self, ctx: Context):
        """Get tomorrow's horoscope."""
        await self.send_hs(ctx, "daily-tomorrow")

    @horoscope.command(name="yesterday")
    async def horoscope_yesterday(self, ctx: Context):
        """Get yesterday's horoscope."""
        await self.send_hs(ctx, "daily-yesterday")

    @horoscope.command(name="weekly", aliases=["week"])
    async def horoscope_weekly(self, ctx: Context):
        """Get this week's horoscope."""
        await self.send_hs(ctx, "weekly")

    @horoscope.command(name="monthly", aliases=["month"])
    async def horoscope_monthly(self, ctx: Context):
        """Get this month's horoscope."""
        await self.send_hs(ctx, "monthly")

    async def send_hs(
        self,
        ctx: Context,
        variant: Literal[
            "daily-yesterday", "daily-today", "daily-tomorrow", "weekly", "monthly"
        ],
    ):
        sunsign = await self.bot.db.fetchval(
            "SELECT sunsign FROM user_settings WHERE user_id = $1",
            ctx.author.id,
        )
        if not sunsign:
            return await ctx.warn(
                "Please save your zodiac sign using `horoscope set <sign>`.\n"
                "Use `horoscope list` if you don't know which one you are."
            )

        sign = self.hs.get(sunsign)
        if not sign:
            return await ctx.warn("Invalid zodiac sign stored. Please set it again.")

        async with self.bot.session.get(
            f"https://www.horoscope.com/us/horoscopes/general/horoscope-general-{variant}.aspx",
            params={"sign": sign["id"]},
        ) as response:
            response.raise_for_status()
            soup = BeautifulSoup(await response.text(), "lxml")
            paragraph = soup.select_one("p")

        if paragraph is None:
            return await ctx.warn("Something went wrong trying to get horoscope text.")

        date_node = paragraph.find("strong")
        date = date_node.text.strip() if date_node else "[ERROR]"
        if date_node:
            date_node.clear()

        for line_break in paragraph.findAll("br"):
            line_break.replaceWith("\n")
        hs_text = paragraph.get_text().strip("- ")

        embed = Embed(
            title=f"{sign['emoji']} {sign['name']} | {date}",
            description=hs_text,
        )

        if variant.startswith("daily"):
            async with self.bot.session.get(
                f"https://www.horoscope.com/star-ratings/{variant.split('-')[-1]}/{sunsign}"
            ) as response:
                second_soup = BeautifulSoup(await response.text(), "lxml")
                wrapper = second_soup.select_one(".module-skin")

            if wrapper:
                titles = wrapper.findAll("h3")
                texts = wrapper.findAll("p")
                for title, text in zip(titles, texts):
                    star_count = len(title.select(".highlight"))
                    stars = star_count * ":star:"
                    emptystars = (5 - star_count) * "⬛"
                    title_text = title.text.strip()
                    if title_text == "Sex":
                        title_text = "Romance"
                    embed.add_field(
                        name=f"{title_text} {stars}{emptystars}",
                        value=text.text,
                        inline=False,
                    )

        await ctx.send(embed=embed)

    @horoscope.command(name="set")
    async def horoscope_set(self, ctx: Context, sign: str):
        """Save your zodiac sign"""
        sign = sign.lower()
        if self.hs.get(sign) is None:
            raise CommandError(
                f"`{sign}` is not a valid zodiac! Use `horoscope list` for a list of zodiacs."
            )

        await ctx.bot.db.execute(
            """
            INSERT INTO user_settings (user_id, sunsign)
                VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE
                SET sunsign = EXCLUDED.sunsign
            """,
            ctx.author.id,
            sign,
        )
        await ctx.send(
            f"Zodiac saved as **{sign.capitalize()}** {self.hs[sign]['emoji']}"
        )

    @horoscope.command(name="list")
    async def horoscope_list(self, ctx: Context):
        """Get list of all zodiac signs"""
        content = Embed(
            title=":crystal_ball: Zodiac signs",
            description="\n".join(
                f"{sign['emoji']} **{sign['name']}**: {sign['date_range']}"
                for sign in self.hs.values()
            ),
        )
        return await ctx.send(embed=content)

    @hybrid_command(
        name="youtubesearch",
        aliases=["ytsearch"],
    )
    @cooldown(1, 5, BucketType.user)
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def google_youtube(self, ctx: Context, *, query: str) -> Message:
        """
        Search a query on YouTube.
        """

        async with ctx.typing():
            results = await YouTubeVideo.search(self.bot.session, query)
            if not results:
                return await ctx.warn(f"No videos found for **{query}**!")

            # Format the results similar to SoundCloud
            pages = [
                f"({i + 1}/{len(results)}) {result.url}"
                for i, result in enumerate(results)
            ]

            return await ctx.paginate(pages=pages)
