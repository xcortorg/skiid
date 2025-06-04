import re
import unicodedata
import time
import math
import json
import hashlib
import hmac
import random
import base64
import dateparser
import urllib.parse
import os
import config
import discord
import io
import aiohttp
import decimal
import asyncio

from config import AUTHORIZATION
from main import Evict

from core.client import FlagConverter
from core.client.context import Context

from cogs.social.models import YouTubeVideo
from cogs.utility.handlers.embeds import EmbedScript, EmbedJson

from tools import dominant_color
from tools.conversion import PartialAttachment, Timezone
from tools.conversion.script import Script
from tools.formatter import codeblock, shorten

from managers.paginator import Paginator

from .extended import Extended
from .models.google import GoogleTranslate
from .handlers import EmbedBuilding

from dateutil.tz import gettz
from hashlib import sha1, sha224, sha256, sha384, sha512
from io import BytesIO
from urllib.parse import quote_plus
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
from PIL import Image
from io import BytesIO
from aiohttp import FormData
from secrets import token_urlsafe
# from nudenet import NudeDetector
from bs4 import BeautifulSoup
from shazamio import Serialize as ShazamSerialize, Shazam as ShazamClient
from collections import defaultdict
from xxhash import xxh32_hexdigest, xxh64_hexdigest, xxh128_hexdigest
from yarl import URL
from itertools import zip_longest
from dataclasses import dataclass
from humanize import ordinal
from logging import getLogger
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

from discord.ext import tasks
from discord.utils import format_dt, utcnow
from discord.ui import Button, View

from discord import (
    User,
    Guild,
    Embed,
    File,
    HTTPException,
    Member,
    Message,
    RawReactionActionEvent,
    TextChannel,
    Thread,
    Attachment,
    Interaction,
)

from discord.ext.commands import (
    BucketType,
    Cog,
    clean_content,
    command,
    cooldown,
    group,
    has_permissions,
    parameter,
    hybrid_group,
    hybrid_command,
    Range,
    flag,
    max_concurrency
)

from typing import (
    Annotated, 
    List, 
    Optional, 
    cast, 
    Literal, 
    Union
)

log = getLogger("evict/utility")

IMAGE_TYPES = (".png", ".jpg", ".jpeg", ".gif", ".webp")
STICKER_KB = 512
STICKER_DIM = 320
STICKER_EMOJI = "😶"
MISSING_EMOJIS = "cant find emojis or stickers in that message."
MISSING_REFERENCE = "reply to a message with this command to steal an emoji."
MESSAGE_FAIL = "i couldn't grab that message."
UPLOADED_BY = "uploaded by"
STICKER_DESC = "stolen sticker"
STICKER_FAIL = "failed to upload sticker"
STICKER_SUCCESS = "uploaded sticker"
EMOJI_SUCCESS = "uploaded emoji"
STICKER_SLOTS = "this server doesn't have any more space for stickers."
EMOJI_FAIL = "failed to upload"
EMOJI_SLOTS = "this server doesn't have any more space for emojis."
INVALID_EMOJI = "invalid emoji or emoji ID."
STICKER_TOO_BIG = f"stickers may only be up to {STICKER_KB} KB and {STICKER_DIM}x{STICKER_DIM} pixels."
STICKER_ATTACHMENT = ""

class ScreenshotFlags(FlagConverter):
    wait: Range[int, 0, 10] = flag(
        default=0,
        description="Seconds to wait before screenshot (max 10)",
    )
    full_page: bool = flag(
        default=False,
        description="Whether to capture the full page",
    )

@dataclass(init=True, order=True, frozen=True)
class StolenEmoji:
    animated: bool
    name: str
    id: int

    @property
    def url(self):
        return f"https://cdn.discordapp.com/emojis/{self.id}.{'gif' if self.animated else 'png'}"

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return isinstance(other, StolenEmoji) and self.id == other.id

class CryptoView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="Card Payment",
                url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR", 
                style=discord.ButtonStyle.url,
                emoji=config.EMOJIS.SOCIAL.WEBSITE
            )
        )

class CryptoButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            label="Crypto Addresses",
            style=discord.ButtonStyle.gray,
            emoji=f"{config.EMOJIS.MISC.CRYPTO}"
        )

    async def callback(self, interaction: Interaction):
        embed = Embed(
            title="Crypto Donation Addresses",
            description=(
                f"{config.EMOJIS.MISC.BITCOIN} **Bitcoin (BTC): **`3C3LrLwRGLkkwVMdSRhEAqKdHY9zNzDgNx`\n"
                f"{config.EMOJIS.MISC.ETHEREUM} **Ethereum (ETH): **`0xEc65518168b3d5A4032CfC244C5EE3c368700FBE`\n"
                f"{config.EMOJIS.MISC.XRP} **XRP (XRP): **`rw2ciyaNshpHe7bCHo4bRWq6pqqynnWKQg`\n"
                f"{config.EMOJIS.MISC.LITECOIN}**LTC (Litecoin): **`ltc1qfl5pg0ds68p9fm8h4tez8qm87xdhl64n3xrttv`\n"
                "\nWe also accept donations via the tip.cc Discord bot, please use `$tip @66adam <amount> <currency>`. Currency **must be** one of the listed above.\n"
                "\nAfter sending, please open a ticket in our [Discord server](https://discord.gg/evict) with your transaction hash. Payment via Crypto is not automated."
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text="Thank you for supporting Evict! ❤️")
        await interaction.response.edit_message(embed=embed, view=CryptoView())

class DonateView(discord.ui.View):
    def __init__(self, ctx: Context):
        super().__init__()
        self.ctx = ctx
        self.add_item(
            discord.ui.Button(
                label="Card & Cashapp Payment",
                url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                style=discord.ButtonStyle.url,
                emoji=config.EMOJIS.SOCIAL.WEBSITE
            )
        )
        self.add_item(CryptoButton())


class Utility(Extended, Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Utility commands to enhance functionality."
        self.locks = defaultdict(asyncio.Lock)
        self.shazamio = ShazamClient()
        # self.nude_detector = NudeDetector()
        self.auto_media.start()
        self._cache = {}
        self._cache_times = {}
        self._filter_cache = {}
        self._filter_ttl = 300  

    async def parse_time(self, time_str: str) -> int:
        """Convert time string to seconds"""
        total_seconds = 0
        current_num = ""
        
        for char in time_str.lower():
            if char.isdigit():
                current_num += char
            elif char in ['d', 'h', 'm', 's']:
                if not current_num:
                    raise ValueError("Invalid time format")
                num = int(current_num)
                if char == 'd':
                    total_seconds += num * 86400
                elif char == 'h':
                    total_seconds += num * 3600
                elif char == 'm':
                    total_seconds += num * 60
                elif char == 's':
                    total_seconds += num
                current_num = ""
            else:
                raise ValueError("Invalid time format")
        
        if current_num:
            raise ValueError("Invalid time format")
        
        return total_seconds

    async def reminder_check(self):
        """Background task to check and send reminders"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                current_time = utcnow()
                reminders = await self.bot.db.fetch(
                    "SELECT * FROM reminders WHERE remind_at <= $1",
                    current_time
                )

                for reminder in reminders:
                    user = self.bot.get_user(reminder['user_id'])
                    if user:
                        view = View()
                        if reminder['message_url']:
                            view.add_item(
                                Button(
                                    label="Jump to Message",
                                    url=reminder['message_url'],
                                    style=discord.ButtonStyle.url
                                )
                            )                       
                        try:
                            embed = Embed()
                            embed.description = f"⏰ **Reminder:** {reminder['reminder']}\n Set: {format_dt(reminder['invoked_at'], 'R')}"
                            
                            await user.send(embed=embed, view=view if reminder['message_url'] else None)
                        except:
                            pass 

                    await self.bot.db.execute(
                        "DELETE FROM reminders WHERE user_id = $1 AND remind_at = $2 AND reminder = $3",
                        reminder['user_id'],
                        reminder['remind_at'],
                        reminder['reminder']
                    )

            except Exception as e:
                print(f"Error in reminder check: {e}")

            await asyncio.sleep(60) 

    def _get_cache(self, key: str):
        """Get a value from cache if not expired"""
        if key in self._cache:
            if time.time() < self._cache_times[key]:
                return self._cache[key]
            else:
                del self._cache[key]
                del self._cache_times[key]
        return None

    def _set_cache(self, key: str, value, expire: int = 300):
        """Set a value in cache with expiration"""
        self._cache[key] = value
        self._cache_times[key] = time.time() + expire

    def cog_unload(self):
        self.auto_media.cancel()
        self.reminder_check_task.cancel()
    
    async def cog_load(self):
        self.reminder_check_task = self.bot.loop.create_task(self.reminder_check())

    @tasks.loop(seconds=60)
    async def auto_media(self):
        """
        Auto-post media to configured channels.
        """
        records = await self.bot.db.fetch(
            """
            SELECT guild_id, channel_id, type, category
            FROM auto.media
            """
        )

        for record in records:
            try:
                guild = self.bot.get_guild(record['guild_id'])
                if not guild:
                    continue

                channel = guild.get_channel(record['channel_id'])
                if not channel:
                    continue

                media_type = record['type']
                category = record['category']

                headers = {"X-API-Key": "125cfb43-af9b-4d1f-97d2-8223acab08a0"}
                base_url = f"http://cdn.evict.bot/files/autopfp/{media_type}/{category}"

                async with self.bot.session.get(base_url, headers=headers) as resp:
                    if resp.status != 200:
                        log.warning(f"Failed to get autopfp data: {resp.status} for {base_url}")
                        continue
                    
                    try:
                        data = await resp.json()
                        
                        required_fields = ["url", "filename", "format_type", "category"]
                        if not all(field in data for field in required_fields):
                            log.warning(f"Missing required fields in response: {data}")
                            continue
                        
                        image_url = data['url']

                        async with self.bot.session.get(image_url, headers=headers) as img_resp:
                            if img_resp.status != 200:
                                log.warning(f"Failed to get image: {img_resp.status} for {image_url}")
                                continue
                                
                            image_data = await img_resp.read()
                            
                            try:
                                color = await dominant_color(BytesIO(image_data))
                            except Exception as e:
                                log.warning(f"Failed to get dominant color: {e}")
                                color = 0x2F3136
                            
                            file_parts = data['url'].split('/')[-1].split('.')
                            file_hash = file_parts[0] if len(file_parts) > 0 else "unknown"
                            file_ext = data['format_type']
                            
                            file = File(
                                BytesIO(image_data), 
                                filename=f"{self.bot.user.name}-{file_hash}.{file_ext}"
                            )
                            
                            embed = Embed(color=color, title="Powered by Evict", url="https://discord.com/oauth2/authorize?client_id=1203514684326805524&permissions=8&scope=bot")
                            embed.set_image(url=f"attachment://{self.bot.user.name}-{file_hash}.{file_ext}")
                            
                            filename_without_ext = data['filename'].split('.')[0]
                            embed.set_footer(
                                text=f"{data['category']} • id: {filename_without_ext} • discord.gg/evict"
                            )
                            
                            await channel.send(embed=embed, file=file)
                    
                    except ValueError as e:
                        log.error(f"Failed to parse JSON response: {e}")
                        continue

            except Exception as e:
                log.error(f"Error in auto_media task: {e}")
                continue


    @auto_media.before_loop
    async def before_auto_media(self):
        await self.bot.wait_until_ready()

    @staticmethod
    def get_emojis(content: str) -> Optional[List[StolenEmoji]]:
        results = re.findall(r"<(a?):(\w+):(\d{10,20})>", content)
        return [StolenEmoji(*result) for result in results]

    @staticmethod
    def available_emoji_slots(guild: discord.Guild, animated: bool):
        current_emojis = len([em for em in guild.emojis if em.animated == animated])
        return guild.emoji_limit - current_emojis

    async def steal_ctx(
        self, ctx: Context
    ) -> Optional[List[Union[StolenEmoji, discord.StickerItem]]]:
        reference = ctx.message.reference
        if not reference:
            await ctx.warn(
                "Reply to a message with this command to steal an emoji, or run ``emoji add``."
            )
            return None
        message = await ctx.channel.fetch_message(reference.message_id)
        if not message:
            await ctx.warn("I couldn't fetch that message.")
            return None
        if message.stickers:
            return message.stickers
        if not (emojis := self.get_emojis(message.content)):
            await ctx.warn("Can't find emojis or stickers in that message.")
            return None
        return emojis

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

    # @Cog.listener("on_guild_update") 
    # async def vanity_tracker(self, before: Guild, after: Guild):
    #     """Listener for the vanity tracker."""
    #     if not before.vanity_url_code or before.vanity_url_code == after.vanity_url_code:
    #         return

    #     tracking_channels = await self.bot.db.fetch(
    #         "SELECT guild_id, vanity_channel_id FROM tracker WHERE vanity_channel_id IS NOT NULL"
    #     )

    #     embed = Embed(title="New Vanity Available", description=f"Vanity ``{before.vanity_url_code}`` is now available.")

    #     for record in tracking_channels:
    #         channel = self.bot.get_channel(record['vanity_channel_id'])
    #         if channel and after.vanity_url_code:
    #             try:
    #                 await channel.send(embed=embed)
    #             except:
    #                 pass

    #     tracking_data = await self.bot.db.fetchrow(
    #         """
    #         SELECT user_ids
    #         FROM track.vanity
    #         WHERE vanity = $1
    #         """,
    #         before.vanity_url_code.lower(),
    #     )

    #     if tracking_data and tracking_data["user_ids"]:
    #         user_embed = Embed(
    #             description=f"The vanity `{before.vanity_url_code}` you have set to track with **evict** is now available.\n> {config.EMOJIS.CONTEXT.WARN} You are receiving this message because you have setup vanity tracking with **evict**",
    #         )
    #         for user_id in tracking_data["user_ids"]:
    #             try:
    #                 if user := self.bot.get_user(user_id):
    #                     await user.send(embed=user_embed)
    #             except Exception as e:
    #                 log.error(f"Failed to send DM to user {user_id}: {e}")

    # @Cog.listener("on_user_update")
    # async def username_tracker(self, before: User, after: User):
    #     """Listener for the username tracker."""
    #     if before.name == after.name:
    #         return

    #     current_timestamp = int(time.time())
    #     future_timestamp = current_timestamp + (14 * 24 * 60 * 60)
    #     discord_timestamp = f"<t:{future_timestamp}:R>"

    #     tracking_channels = await self.bot.db.fetch(
    #         "SELECT guild_id, username_channel_id FROM tracker WHERE username_channel_id IS NOT NULL"
    #     )

    #     embed = Embed(title="New Username Available", description=f"Username ``{before.name}`` will be available {discord_timestamp}")

    #     for record in tracking_channels:
    #         if channel := self.bot.get_channel(record['username_channel_id']):
    #             try:
    #                 await channel.send(embed=embed)
    #             except:
    #                 pass
    #         else:
    #             await self.bot.db.execute(
    #                 "UPDATE tracker SET username_channel_id = NULL WHERE guild_id = $1",
    #                 record['guild_id']
    #             )

    #     tracking_data = await self.bot.db.fetchrow(
    #         "SELECT user_ids FROM track.username WHERE username = $1",
    #         before.name.lower(),
    #     )

    #     if tracking_data and tracking_data["user_ids"]:
    #         user_embed = Embed(
    #             description=f"The username `{before.name}` you have set to track with **evict** is now available.\n> {config.EMOJIS.CONTEXT.WARN} You are receiving this message because you have setup username tracking with **evict**",
    #         )
    #         for user_id in tracking_data["user_ids"]:
    #             try:
    #                 if user := self.bot.get_user(user_id):
    #                     await user.send(embed=user_embed)
    #             except Exception:
    #                 continue

    @Cog.listener("on_message_without_command")
    async def afk_listener(self, ctx: Context) -> Optional[Message]:
        if left_at := cast(
            Optional[datetime],
            await self.bot.db.fetchval(
                """
                DELETE FROM afk
                WHERE user_id = $1
                RETURNING left_at
                """,
                ctx.author.id,
            ),
        ):
            return await ctx.neutral(
                f"Welcome back, you left {format_dt(left_at, 'R')}",
                reference=ctx.message,
            )

        if len(ctx.message.mentions) == 1:
            user = ctx.message.mentions[0]
            
            rate_key = f"{ctx.channel.id}:{user.id}"
            
            if await self.bot.redis.ratelimited(rate_key, 6, 60):
                return

            if record := await self.bot.db.fetchrow(
                """
                SELECT status, left_at
                FROM afk
                WHERE user_id = $1
                """,
                user.id,
            ):
                return await ctx.neutral(
                    f"{user.mention} is currently AFK: **{record['status']}** - {format_dt(record['left_at'], 'R')}",
                    reference=ctx.message,
                )

    @hybrid_command(example="be back soon", aliases=["away"])
    async def afk(
        self,
        ctx: Context,
        *,
        status: str = "AFK",
    ) -> Optional[Message]:
        """
        Set an AFK status.
        """
        await self.bot.db.execute(
                """
                INSERT INTO afk (user_id, status)
                VALUES ($1, $2)
                ON CONFLICT (user_id) 
                DO UPDATE SET status = EXCLUDED.status
                """,
                ctx.author.id,
                status,
            )
            
        return await ctx.approve(f"You're now **AFK** with the status **{status}**")

    @hybrid_command(
        example="en te amo",
        name="translate",
        aliases=[
            "translation",
            "tr",
        ],
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def translate(
        self,
        ctx: Context,
        destination: Annotated[
            str,
            Optional[GoogleTranslate],
        ] = "en",
        *,
        text: Annotated[
            Optional[str],
            clean_content,
        ] = None,
    ) -> Message:
        """
        Translate text with Google Translate.
        This is an alias for the `google translate` command.
        """

        return await self.google_translate(
            ctx,
            destination=destination,
            text=text,
        )

    @command(
        aliases=[
            "rimg",
            "sauce",
        ]
    )
    async def reverse(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Reverse search an image on Google.
        This is an alias for the `google reverse` command.
        """

        return await self.google_reverse(ctx, attachment=attachment)

    @hybrid_group(
        aliases=["g", "ddg"],
        invoke_without_command=True,
        # fallback="search"
    )
    # @discord.app_commands.allowed_installs(guilds=True, users=True)
    # @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @cooldown(3, 60, BucketType.user)
    async def google(self, ctx: Context, *, query: str) -> Message:
        """
        Search a query on Google.
        """
        return await ctx.send_help(ctx.command)
        
        # if not isinstance(ctx.channel, discord.DMChannel):
        #     async with ctx.typing():
        #         data = await Google.search(self.bot.session, query)
        # else:
        #     data = await Google.search(self.bot.session, query)
            
        # if not data.results:
        #     return await ctx.warn(f"No results found for **{query}**!")

        # fields: List[dict] = []
        # embed = Embed(title=f"{data.header}{f' - {data.description}' if data.description else ''}" if data.header else f"Google Search - {query}")
        
        # if panel := data.panel:
        #     if panel.source:
        #         embed.url = panel.source.url
        #     embed.description = shorten(panel.description, 200)
        #     for item in panel.items:
        #         if not embed.description:
        #             embed.description = ""
        #         embed.description += f"\n> **{item.name}:** `{item.value}`"

        # for result in data.results:
        #     if any(result.title in field["name"] for field in fields):
        #         continue

        #     snippet = result.snippet or (".." if not result.tweets else "")
        #     for highlight in result.highlights:
        #         snippet = snippet.replace(highlight, f"**{highlight}**")

        #     fields.append({
        #         "name": f"**{result.title}**",
        #         "value": (
        #             f"**{result.url.split('?', 1)[0]}**\n{shorten(snippet, 200)}"
        #             + ("\n" if result.extended_links or result.tweets and snippet else "")
        #             + "\n".join([f"> [`{extended.title}`]({extended.url}): {textwrap.shorten(extended.snippet or '...', 46, placeholder='..')}" for extended in result.extended_links])
        #             + "\n".join([f"> [`{textwrap.shorten(tweet.text, 46, placeholder='..')}`]({tweet.url}) **{tweet.footer}**" for tweet in result.tweets[:3]])
        #         ),
        #         "inline": False
        #     })

        # paginator = Paginator(ctx, entries=fields, embed=embed, per_page=3)
        # return await paginator.start()

    @google.command(example="en te amo", name="translate", aliases=["translation", "tr"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def google_translate(self, ctx: Context, destination: Annotated[str, Optional[GoogleTranslate]] = "en", *, text: Annotated[Optional[str], clean_content] = None) -> Message:
        """Translate text with Google Translate."""
        if not text:
            reply = ctx.replied_message
            if reply and reply.content:
                text = reply.clean_content
            else:
                return await ctx.send_help(ctx.command)

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                result = await GoogleTranslate.translate(self.bot.session, text, target=destination)
        else:
            result = await GoogleTranslate.translate(self.bot.session, text, target=destination)

        embed = Embed(title="Google Translate")
        embed.add_field(name=f"**{result.source_language} to {result.target_language}**", value=result.translated, inline=False)
        return await ctx.send(embed=embed)

    @google.command(example="jake paul", name="youtube", aliases=["yt"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def google_youtube(self, ctx: Context, *, query: str) -> Message:
        """Search a query on YouTube."""
        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                results = await YouTubeVideo.search(self.bot.session, query)
        else:
            results = await YouTubeVideo.search(self.bot.session, query)
            
        if not results:
            return await ctx.warn(f"No videos found for **{query}**!")

        paginator = Paginator(ctx, entries=[result.url for result in results])
        return await paginator.start()

    @google.command(name="reverse", aliases=["rimg", "sauce"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @cooldown(1, 10, BucketType.user)
    async def google_reverse(
        self, 
        ctx: Context, 
        file: discord.Attachment = None
    ) -> Message:
        """
        Reverse search an image on Google.
        """
        if not file or not file.content_type or not file.content_type.startswith('image/'):
            return await ctx.warn("Please provide an image attachment!")

        is_nsfw = False if isinstance(ctx.channel, discord.DMChannel) else ctx.channel.is_nsfw()

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                response = await self.bot.session.get(
                    URL.build(
                        scheme="https",
                        host="www.google.com",
                        path="/searchbyimage",
                        query={"safe": "off" if is_nsfw else "on", "sbisrc": "tg", "image_url": file.url}
                    ),
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0"}
                )
                content = await response.text()
        else:
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="www.google.com",
                    path="/searchbyimage",
                    query={"safe": "off" if is_nsfw else "on", "sbisrc": "tg", "image_url": file.url}
                ),
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/111.0"}
            )
            content = await response.text()

        data = BeautifulSoup(content, "lxml")
        
        results = data.select("div.g")
        if not results:
            return await ctx.warn(f"No results were found for [`{file.filename}`]({file.url})!")

        embed = Embed(title="Reverse Image Search")
        embed.set_thumbnail(url=file.url)
        
        if best_guess := data.select_one("input[value^='Best guess']"):
            embed.description = f"*Best guess: `{best_guess.get('value').replace('Best guess for this image: ', '')}`*"

        if stats := data.select_one("div#result-stats"):
            embed.set_footer(text=stats.text)

        fields = []
        for result in results[:15]:  
            if title_elem := result.select_one("h3"):
                title = title_elem.text
                if link_elem := result.select_one("a"):
                    link = link_elem.get("href")
                    if desc_elem := result.select_one("div.VwiC3b"):
                        description = desc_elem.text
                        fields.append({
                            "name": title,
                            "value": f"[`{shorten(description, 65)}`]({link})",
                            "inline": False
                        })

        paginator = Paginator(
            ctx,
            entries=fields,
            embed=embed,
            per_page=3,
        )
        return await paginator.start()

    @hybrid_command(
        example="what time is it in new zealand", 
        aliases=["ai", "ask", "gemini"]
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def chatgpt(self, ctx: Context, *, question: str) -> Optional[Message]:
        """Ask AI a question."""
        
        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )
        
        if not is_donor:
            return await ctx.send("This command is only available to donators!")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                return await self._process_chatgpt(ctx, question)
        else:
            return await self._process_chatgpt(ctx, question)

    async def _process_chatgpt(self, ctx: Context, question: str):
        response = await self.bot.session.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": question}]
            }
        )

        if response.status != 200:
            return await ctx.warn("Failed to get a response from OpenAI API!")

        data = await response.json()
        if not data.get("choices"):
            return await ctx.warn("No response was found for that question!")

        response_content = data["choices"][0]["message"]["content"]
        
        embed = Embed()
        embed.description = response_content
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        
        if len(response_content) > 4096:
            temp_file = "temp_response.txt"
            try:
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(response_content)
                return await ctx.send(
                    embed=Embed(description="Response was too long, see attached file"),
                    file=discord.File(temp_file)
                )
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
        else:
            return await ctx.send(embed=embed)

    @hybrid_command(aliases=["w"], example="what is time")
    async def wolfram(
        self,
        ctx: Context,
        *,
        question: str,
    ) -> Message:
        """
        Solve a question with Wolfram Alpha.
        """
        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.wolframalpha.com",
                    path="/v1/result",
                    query={
                        "i": question,
                        "appid": AUTHORIZATION.WOLFRAM,
                    },
                ),
            )
            if not response.ok:
                return await ctx.warn("No solution was found for that question!")

            content = await response.read()

        return await ctx.send(content.decode("utf-8"))

    @hybrid_command(aliases=["char"], example="¤")
    async def charinfo(self, ctx: Context, *, characters: str) -> Message:
        """
        View unicode characters.
        """

        def to_string(char: str):
            digit = f"{ord(char):x}"
            name = unicodedata.name(char, "Unknown")

            return f"[`\\U{digit:>08}`](http://www.fileformat.info/info/unicode/char/{digit}): {name}"

        paginator = Paginator(
            ctx,
            entries=list(map(to_string, characters)),
            embed=Embed(
                title="Character Information",
            ),
            per_page=5,
            counter=False,
        )
        return await paginator.start()

    @hybrid_group(
        name="hash",
        invoke_without_command=True,
    )
    async def _hash(self, ctx: Context) -> Message:
        """
        Hash a string with a given algorithm.
        """

        return await ctx.send_help(ctx.command)

    @_hash.command(name="xxh32", example="hello world")
    async def _hash_xxh32(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the XXH32 algorithm.
        """

        hashed = xxh32_hexdigest(text)

        embed = Embed(
            title="XXH32 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="xxh64", example="hello world")
    async def _hash_xxh64(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the XXH64 algorithm.
        """

        hashed = xxh64_hexdigest(text)

        embed = Embed(
            title="XXH64 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="xxh128", example="hello world")
    async def _hash_xxh128(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the XXH128 algorithm.
        """

        hashed = xxh128_hexdigest(text)

        embed = Embed(
            title="XXH128 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha1", example="hello world")
    async def _hash_sha1(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA1 algorithm.
        """

        hashed = sha1(text.encode()).hexdigest()

        embed = Embed(
            title="SHA1 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha224", example="hello world")
    async def _hash_sha224(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA224 algorithm.
        """

        hashed = sha224(text.encode()).hexdigest()

        embed = Embed(
            title="SHA224 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha256", example="hello world")
    async def _hash_sha256(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA256 algorithm.
        """

        hashed = sha256(text.encode()).hexdigest()

        embed = Embed(
            title="SHA256 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha384", example="hello world")
    async def _hash_sha384(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA384 algorithm.
        """

        hashed = sha384(text.encode()).hexdigest()

        embed = Embed(
            title="SHA384 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @_hash.command(name="sha512", example="hello world")
    async def _hash_sha512(self, ctx: Context, *, text: str) -> Message:
        """
        Hash a string with the SHA512 algorithm.
        """

        hashed = sha512(text.encode()).hexdigest()

        embed = Embed(
            title="SHA512 Hash",
            description=(
                f"> **Original**"
                f"\n```{text}```"
                f"\n> **Hashed**"
                f"\n```{hashed}```"
            ),
        )
        return await ctx.send(embed=embed)

    @hybrid_group(
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

    @birthday.command(example="jan 13", name="set")
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

    @hybrid_group(
        aliases=["time", "tz"],
        invoke_without_command=True,
        example="@x",
        description="View your local time.",
        with_app_command=True,
        fallback="view"
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def timezone(
        self,
        ctx: Context,
        *,
        member: Union[Member, User, None] = parameter(
            default=lambda ctx: ctx.author,
            description="The member to check timezone for"
        ),
    ) -> Message:
        """View your local time."""
        target = member or ctx.author
        timezone = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT timezone
                FROM timezones
                WHERE user_id = $1
                """,
                target.id,
            ),
        )
        if not timezone:
            if target == ctx.author:
                return await ctx.warn(
                    "You haven't set your timezone yet!",
                    f"Use `{ctx.clean_prefix}timezone set <location>` to set it",
                )

            return await ctx.warn(f"**{target}** hasn't set their timezone yet!")

        timestamp = utcnow().astimezone(gettz(timezone))
        return await ctx.neutral(
            f"It's currently **{timestamp.strftime('%B %d, %I:%M %p')}** "
            + ("for you" if target == ctx.author else f"for {target.mention}")
        )

    @timezone.command(
        example="indianapolis", 
        name="set",
        with_app_command=True,
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
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

    @hybrid_group()
    async def variables(self, ctx: Context):
        await ctx.neutral("Variables are not currently up, see temporary variables: https://docs.greed.best/overview/variables")

    @command(aliases=["parse", "ce"], example="{embed}$v{description: @x}")
    @has_permissions(manage_messages=True)
    async def embed(self, ctx: Context, *, script: EmbedScript) -> Message:
        """
        Parse a script into an embed.
        """

        if script is None:
            if ctx.message.attachments:
                script = await EmbedJson.embed_json(
                    ctx.author, ctx.message.attachments[0]
                )
            else:
                return await ctx.send_help(ctx.command)

        await ctx.send(**script)

    @command(example="1287575466152300566", aliases=["embedcode", "ec"])
    async def copyembed(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Copy a script from a message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        script = Script.from_message(message)
        if not script:
            return await ctx.warn(
                f"That [`message`]({message.jump_url}) doesn't have any content!"
            )

        return await ctx.send(codeblock(script.template))

    @group(
        aliases=["quoter"],
        invoke_without_command=True,
    )
    async def quote(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Repost a message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        channel_id = await self.bot.db.fetchval(
            """SELECT channel_id 
            FROM quoter WHERE 
            guild_id = $1""",
            ctx.guild.id,
        )

        if not channel_id:
            return await ctx.warn("Quoting channel not set for this server.")

        channel = self.bot.get_channel(channel_id)
        if not channel:
            return await ctx.warn("The quoting channel does not exist.")

        if not channel.permissions_for(ctx.author).view_channel:
            return await ctx.warn("You don't have access to that channel!")

        if message.embeds and message.embeds[0].type != "image":
            embed = message.embeds[0]
        else:
            embed = Embed(color=message.author.color)

        embed.description = embed.description or ""
        embed.timestamp = message.created_at
        embed.set_author(
            name=str(message.author),
            icon_url=message.author.display_avatar.url,
            url=message.jump_url,
        )

        if message.content:
            embed.description += f"\n{message.content}"

        files: List[File] = []
        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith("image"):
                embed.set_image(url=attachment.proxy_url)
            elif (
                attachment.size <= ctx.guild.filesize_limit
                and attachment.filename.endswith(
                    ("mp4", "mp3", "mov", "wav", "ogg", "webm")
                )
            ):
                file = await attachment.to_file()
                files.append(file)

        embed.set_footer(
            text=f"#{message.channel.name}/{message.guild.name if message.guild else 'Unknown Guild'}",
            icon_url=message.guild.icon.url if message.guild else None,
        )

        await ctx.check()
        return await channel.send(
            embed=embed,
            files=files,
        )

    @quote.command(name="channel", example="#quotes")
    @has_permissions(manage_messages=True)
    async def quote_channel(self, ctx: Context, *, channel: TextChannel) -> Message:
        """
        Set the quote relay channel.
        """

        await self.bot.db.execute(
            """
            INSERT INTO quoter (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id,
        )
        return await ctx.approve(f"Now relaying quoted messages to {channel.mention}")

    @quote.command(name="emoji", aliases=["set"], example=":quote:")
    @has_permissions(manage_messages=True)
    async def quote_emoji(self, ctx: Context, emoji: str) -> Message:
        """
        Set the quote emoji to detect.
        """

        try:
            await ctx.message.add_reaction(emoji)
        except (HTTPException, TypeError):
            return await ctx.warn(
                f"I'm not able to use **{emoji}**",
                "Try using an emoji from this server",
            )

        await self.bot.db.execute(
            """
            INSERT INTO quoter (guild_id, emoji)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET emoji = EXCLUDED.emoji
            """,
            ctx.guild.id,
            emoji,
        )
        return await ctx.approve(f"Now watching for {emoji} on messages")

    @quote.command(name="embeds", aliases=["embed"])
    @has_permissions(manage_messages=True)
    async def quote_embeds(self, ctx: Context) -> Message:
        """
        Toggle if quoted messages will have an embed.
        """

        status = cast(
            bool,
            await self.bot.db.fetchval(
                """
                INSERT INTO quoter (guild_id)
                VALUES ($1)
                ON CONFLICT (guild_id)
                DO UPDATE SET embeds = NOT quoter.embeds
                RETURNING embeds
                """,
                ctx.guild.id,
            ),
        )

        return await ctx.approve(
            f"{'Now' if status else 'No longer'} displaying **embeds** for relayed messages"
        )

    @hybrid_command(
        example="divinity",
        aliases=[
            "dictionary",
            "define",
            "urban",
            "ud",
        ],
        with_app_command=True,
        brief="Define a word with Urban Dictionary.",
        fallback="define"
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def urbandictionary(
        self,
        ctx: Context,
        *,
        word: str,
    ) -> Message:
        """
        Define a word with Urban Dictionary.
        """

        if not isinstance(ctx.interaction, Interaction):
            async with ctx.typing():
                response = await self.bot.session.get(
                    URL.build(
                        scheme="https",
                        host="api.urbandictionary.com",
                        path="/v0/define",
                        query={
                            "term": word,
                        },
                    ),
                )
                data = await response.json()
        else:
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.urbandictionary.com",
                    path="/v0/define",
                    query={
                        "term": word,
                    },
                ),
            )
            data = await response.json()

        if not data["list"]:
            return await ctx.warn(f"No definitions found for **{word}**!")

        embeds: List[Embed] = []
        for result in data["list"]:
            embed = Embed(
                url=result["permalink"],
                title=result["word"],
                description=re.sub(
                    r"\[(.*?)\]",
                    lambda m: f"[{m[1]}](https://www.urbandictionary.com/define.php?term={quote_plus(m[1])})",
                    result["definition"],
                )[:4096],
            )

            embed.add_field(
                name="**Example**",
                value=re.sub(
                    r"\[(.*?)\]",
                    lambda m: f"[{m[1]}](https://www.urbandictionary.com/define.php?term={quote_plus(m[1])})",
                    result["example"],
                )[:1024],
            )
            embeds.append(embed)

        paginator = Paginator(
            ctx,
            entries=embeds,
        )
        return await paginator.start()

    @command(aliases=["dom", "hex"], example="https://example.com/image.png")
    async def dominant(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Extract the dominant color from an image.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        color = await dominant_color(attachment.buffer)
        image_url = f"https://place-hold.it/250x250/{str(color).strip('#')}?text=%20"
        return await ctx.neutral(
            f"The dominant color is [**{color}**]({image_url})",
            color=color,
        )

    @command()
    async def upload(
        self,
        ctx: Context,
        attachment: Attachment = parameter(
            default=lambda ctx: (
                ctx.message.attachments[0] if ctx.message.attachments else None
            ),
        ),
    ) -> Message:
        """
        Upload a file to Kraken Files.
        """

        if not attachment:
            return await ctx.warn("No attachment found!")

        async with ctx.typing():
            response = await self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="krakenfiles.com",
                    path="/api/server/available",
                ),
            )
            data = await response.json()

            if not data["data"]:
                return await ctx.warn(
                    "No available servers to upload file. Try again later!"
                )

            buffer = await attachment.read()

            server = data["data"]
            form = FormData(
                {
                    "file": buffer,
                    "filename": attachment.filename,
                    "serverAccessToken": server["serverAccessToken"],
                }
            )
            response = await self.bot.session.post(
                server["url"],
                data=form,
                headers={"X-AUTH-TOKEN": config.AUTHORIZATION.KRAKEN},
            )
            data = await response.json()
            if not data["data"]:
                return await ctx.warn(
                    "Please try again, the serverAccessToken has already been used!"
                )

            return await ctx.neutral(data["data"]["url"])

    # @hybrid_command(aliases=["ss"], example="https://evict.bot --delay 5")
    # @discord.app_commands.allowed_installs(guilds=True, users=True)
    # @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    # @cooldown(1, 5, BucketType.guild)
    # async def screenshot(
    #     self, 
    #     ctx: Context, 
    #     url: str, 
    #     delay: Optional[int] = 0,
    #     full_page: Optional[bool] = False
    # ) -> Message:
    #     """
    #     Capture a screenshot of a webpage and perform content moderation.
    #     """
    #     if isinstance(ctx.interaction, Interaction):
    #         await ctx.interaction.response.defer(ephemeral=False)

    #     if not url.startswith(("http://", "https://")):
    #         url = f"https://{url}"

    #     try:
    #         async with ctx.bot.browser.borrow_page() as page:
    #             await page.emulate_media(color_scheme="dark")
    #             await page.goto(
    #                 url, 
    #                 timeout=60000, 
    #                 wait_until="load",
    #             )
                
    #             if delay > 0:
    #                 await asyncio.sleep(delay)
    #             screenshot = await page.screenshot(full_page=full_page)
    #             await page.close()

    #         nparr = numpy.frombuffer(screenshot, numpy.uint8)
    #         img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    #         result = self.nude_detector.detect(img)
    #         time_taken = round(time.time() - ctx.message.created_at.timestamp(), 2)

    #         if result:
    #             if isinstance(ctx.interaction, Interaction):
    #                 return await ctx.interaction.followup.send(
    #                     "The screenshot contains potentially unsafe content and cannot be displayed."
    #                 )
    #             return await ctx.warn(
    #                 "The screenshot contains potentially unsafe content and cannot be displayed."
    #             )
            
    #         file = File(BytesIO(screenshot), filename="evict-screenshot.png")

    #         embed = Embed()
    #         embed.set_image(url="attachment://evict-screenshot.png")
    #         embed.set_footer(text=f"took {time_taken} seconds to screenshot.")

    #         if isinstance(ctx.interaction, Interaction):
    #             return await ctx.interaction.followup.send(embed=embed, file=file)
            
    #         return await ctx.send(embed=embed, file=file)
        
    #     except asyncio.TimeoutError:
    #         if isinstance(ctx.interaction, Interaction):
    #             return await ctx.interaction.followup.send(
    #                 "The request timed out. Please try again later."
    #             )
    #         return await ctx.warn("The request timed out. Please try again later.")
        
    #     except Exception as e:
    #         if "ERR_EMPTY_RESPONSE" in str(e):
    #             if isinstance(ctx.interaction, Interaction):
    #                 return await ctx.interaction.followup.send(
    #                     "The website did not respond or is invalid. Please check the URL and try again."
    #                 )
    #             return await ctx.warn("The website did not respond or is invalid. Please check the URL and try again.")
    #         raise e

    @command()
    @has_permissions(manage_messages=True)
    async def embedsetup(self, ctx: Context):
        """
        Create an embed using buttons and return an embed code.
        """
        embed = Embed(description="Create an embed")
        view = EmbedBuilding(ctx)
        return await ctx.send(embed=embed, view=view)

    @command()
    @has_permissions(manage_expressions=True)
    async def steal(self, ctx: Context, *names: str):
        """
        Reply with the emojis you want to steal.
        """
        if not (emojis := await self.steal_ctx(ctx)):
            return

        if isinstance(emojis[0], discord.StickerItem):
            if len(ctx.guild.stickers) >= ctx.guild.sticker_limit:
                return await ctx.warn("there are no more sticker slots.")

            sticker = emojis[0]
            fp = io.BytesIO()

            try:
                await sticker.save(fp)
                await ctx.guild.create_sticker(
                    name=sticker.name,
                    description=STICKER_DESC,
                    emoji=STICKER_EMOJI,
                    file=discord.File(fp),
                    reason=f"uploaded by {ctx.author}",
                )

            except Exception as error:
                return await ctx.warn(
                    f"{STICKER_FAIL}, {type(error).__name__}: {error}"
                )
            return await ctx.approve(f"{STICKER_SUCCESS}: {sticker.name}")

        names = ["".join(re.findall(r"\w+", name)) for name in names]
        names = [name if len(name) >= 2 else None for name in names]
        emojis = list(dict.fromkeys(emojis))

        async with aiohttp.ClientSession() as session:
            for emoji, name in zip_longest(emojis, names):
                if not self.available_emoji_slots(ctx.guild, emoji.animated):
                    return await ctx.warn(EMOJI_SLOTS)
                if not emoji:
                    break
                try:
                    async with session.get(emoji.url) as resp:
                        image = io.BytesIO(await resp.read()).read()
                    added = await ctx.guild.create_custom_emoji(
                        name=name or emoji.name,
                        image=image,
                        reason=f"uploaded by {ctx.author}",
                    )
                except Exception as error:
                    return await ctx.warn(
                        f"{EMOJI_FAIL} {emoji.name}, {type(error).__name__}: {error}"
                    )
                try:
                    await ctx.message.add_reaction(added)
                except:
                    pass

    # @group(invoke_without_command=True)
    # async def notify(self, ctx: Context):
    #     """Manage notifications for vanities and usernames."""
    #     await ctx.send_help(ctx.command)

    # @notify.command(name="add", example="vanity evict")
    # async def notify_add(
    #     self, ctx: Context, type: Literal["vanity", "username"], desired: str
    # ):
    #     """Add a notification for a vanity or username."""

    #     desired = desired.lower().strip()
    #     table = f"track.{type}"

    #     confirmation_message = (
    #         f"Are you sure you would like evict to notify you if the {type} `{desired}` is available?\n"
    #         f"> By agreeing, you allow evict to send you a direct message if the set {type} is available"
    #     )

    #     confirmed = await ctx.prompt(confirmation_message)

    #     if not confirmed:
    #         return await ctx.neutral("Notification setup cancelled.")

    #     await self.bot.db.execute(
    #         f"""
    #         INSERT INTO {table} ({type}, user_ids)
    #         VALUES ($1, ARRAY[$2]::BIGINT[])
    #         ON CONFLICT ({type}) 
    #         DO UPDATE SET user_ids = 
    #             CASE 
    #                 WHEN $2 = ANY({table}.user_ids) THEN {table}.user_ids
    #                 ELSE array_append({table}.user_ids, $2::BIGINT)
    #             END
    #         """,
    #         desired,
    #         ctx.author.id,
    #     )

    #     await ctx.approve(
    #         f"You will be notified if the {type} `{desired}` becomes available."
    #     )

    # @notify.command(name="list")
    # async def notify_list(self, ctx: Context):
    #     """List your active notifications."""

    #     vanities = await self.bot.db.fetch(
    #         """
    #         SELECT vanity
    #         FROM track.vanity
    #         WHERE $1 = ANY(user_ids)
    #         """,
    #         ctx.author.id,
    #     )

    #     usernames = await self.bot.db.fetch(
    #         """
    #         SELECT username
    #         FROM track.username
    #         WHERE $1 = ANY(user_ids)
    #         """,
    #         ctx.author.id,
    #     )

    #     if not vanities and not usernames:
    #         return await ctx.warn("You don't have any active notifications.")

    #     embed = Embed(title="Your Active Notifications")

    #     if vanities:
    #         vanity_list = ", ".join(f"`{v['vanity']}`" for v in vanities)
    #         embed.add_field(name="Vanities", value=vanity_list, inline=True)

    #     if usernames:
    #         username_list = ", ".join(f"`{u['username']}`" for u in usernames)
    #         embed.add_field(name="Usernames", value=username_list, inline=True)

    #     await ctx.send(embed=embed)

    # @notify.command(name="remove", example="vanity evict")
    # async def notify_remove(
    #     self, ctx: Context, type: Literal["vanity", "username"], desired: str
    # ):
    #     """Remove a notification for a vanity or username."""

    #     desired = desired.lower().strip()
    #     table = f"track.{type}"

    #     result = await self.bot.db.execute(
    #         f"""
    #         UPDATE {table}
    #         SET user_ids = array_remove(user_ids, $2::BIGINT)
    #         WHERE {type} = $1 AND $2 = ANY(user_ids)
    #         """,
    #         desired,
    #         ctx.author.id,
    #     )

    #     await self.bot.db.execute(
    #         f"""
    #         DELETE FROM {table} 
    #         WHERE array_length(user_ids, 1) IS NULL
    #         """
    #     )

    #     if result == "UPDATE 0":
    #         return await ctx.warn(f"You weren't tracking the {type} `{desired}`.")

    #     await ctx.approve(f"Removed notification for {type} `{desired}`.")

    # @group(name="tracker", invoke_without_command=True)
    # async def tracker(self, ctx: Context):
    #     await ctx.send_help(ctx.command)

    # @tracker.group(name="vanity", invoke_without_command=True)
    # async def tracker_vanity(self, ctx: Context):
    #     """Send available vanities to a specified channel."""
    #     await ctx.send_help(ctx.command)

    # @has_permissions(manage_channels=True)
    # @tracker_vanity.command(name="channel", example="#vanities")
    # async def tracker_vanity_channel(
    #     self, ctx: Context, channel: Optional[TextChannel]
    # ):
    #     """Send available vanities to a specified channel."""

    #     if channel is None:
    #         channel = ctx.channel

    #     await self.bot.db.execute(
    #         """
    #         INSERT INTO tracker (guild_id, vanity_channel_id)
    #         VALUES ($1, $2)
    #         ON CONFLICT (guild_id)
    #         DO UPDATE SET vanity_channel_id = EXCLUDED.vanity_channel_id
    #         """,
    #         ctx.guild.id,
    #         channel.id,
    #     )

    #     await ctx.approve(f"Now sending available vanities to {ctx.channel.mention}.")

    # @has_permissions(manage_channels=True)
    # @tracker_vanity.command(name="remove", example="#vanities")
    # async def tracker_vanity_remove(self, ctx: Context):
    #     """Remove the vanity tracking."""

    #     channel_id = await self.bot.db.fetchval(
    #         """
    #         SELECT vanity_channel_id 
    #         FROM tracker 
    #         WHERE guild_id = $1
    #         """,
    #         ctx.guild.id,
    #     )

    #     if channel_id is None:
    #         await ctx.warn("There is no vanity tracker set for this guild!")
    #         return

    #     await self.bot.db.execute(
    #         """
    #         UPDATE tracker
    #         SET vanity_channel_id = NULL 
    #         WHERE guild_id = $1
    #         """,
    #         ctx.guild.id,
    #     )

    #     await ctx.approve("Removed the vanity tracker!")

    # @tracker.group(name="usernames", aliases=["users"], invoke_without_command=True)
    # async def tracker_usernames(self, ctx: Context):
    #     """Send available usernames to a specified channel."""
    #     await ctx.send_help(ctx.command)

    # @has_permissions(manage_channels=True)
    # @tracker_usernames.command(name="channel", example="#usernames")
    # async def tracker_usernames_channel(
    #     self, ctx: Context, channel: Optional[TextChannel]
    # ):
    #     """Send available usernames to a specified channel."""

    #     if channel is None:
    #         channel = ctx.channel

    #     await self.bot.db.execute(
    #         """
    #         INSERT INTO tracker (guild_id, username_channel_id)
    #         VALUES ($1, $2)
    #         ON CONFLICT (guild_id)
    #         DO UPDATE SET username_channel_id = EXCLUDED.username_channel_id
    #         """,
    #         ctx.guild.id,
    #         channel.id,
    #     )

    #     await ctx.approve(f"Now sending available usernames to {ctx.channel.mention}.")

    # @has_permissions(manage_channels=True)
    # @tracker_usernames.command(name="remove", example="#usernames")
    # async def tracker_username_remove(self, ctx: Context):
    #     """Remove the username tracking."""

    #     channel_id = await self.bot.db.fetchval(
    #         """
    #         SELECT username_channel_id 
    #         FROM tracker 
    #         WHERE guild_id = $1
    #         """,
    #         ctx.guild.id,
    #     )

    #     if channel_id is None:
    #         await ctx.warn("There is no username tracker set for this guild!")
    #         return

    #     await self.bot.db.execute(
    #         """
    #         UPDATE tracker
    #         SET username_channel_id = NULL 
    #         WHERE guild_id = $1
    #         """,
    #         ctx.guild.id,
    #     )

    #     await ctx.approve("Removed the username tracker!")

    @group(invoke_without_command=True)
    async def profile(self, ctx: Context):
        """Profile media management commands."""
        return await ctx.send_help(ctx.command)

    @has_permissions(manage_guild=True)
    @profile.command(name="add", example="#general pfp anime")
    async def profile_add(self, ctx: Context, channel: TextChannel, media_type: str, category: str):
        """
        Set up automatic media for a channel.
        """
        media_type = media_type.lower()
        category = category.lower()

        if media_type in ("pfp", "pfps", "avatars", "avs"):
            media_type = "pfp"
            valid_categories = ["random", "anime", "cats", "egirls", "girls", "boys"]
        elif media_type in ("banner", "banners"):
            media_type = "banner"
            valid_categories = ["random", "anime", "cute", "imsg", "mix"]
            banner_case_map = {
                "anime": "Anime",
                "cute": "Cute",
                "imsg": "Imsg",
                "mix": "Mix",
                "random": "random"
            }
        else:
            return await ctx.warn("Invalid media type. Choose `banner` or `pfp`.")

        if category not in valid_categories:
            categories = ", ".join(f"`{c}`" for c in valid_categories)
            return await ctx.warn(f"Invalid category for {media_type}. Choose from: {categories}")

        if media_type == "banner":
            category = banner_case_map[category]

        await self.bot.db.execute(
            """
            INSERT INTO auto.media (guild_id, channel_id, type, category)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, channel_id, type)
            DO UPDATE SET category = EXCLUDED.category
            """,
            ctx.guild.id,
            channel.id,
            media_type,
            category
        )

        return await ctx.approve(f"Now sending automatic {media_type}s with category **{category}** to {channel.mention}")

    @profile.command(name="remove", example="#general pfp")
    async def profile_remove(self, ctx: Context, channel: TextChannel, media_type: str):
        """
        Remove automatic media from a channel.
        """
        media_type = media_type.lower()
        
        if media_type in ("pfp", "pfps", "avatars", "avs"):
            media_type = "pfp"
        elif media_type in ("banner", "banners"):
            media_type = "banner"
        else:
            return await ctx.warn("Invalid media type. Choose `banner` or `pfp`.")

        result = await self.bot.db.execute(
            """
            DELETE FROM auto.media
            WHERE guild_id = $1 AND channel_id = $2 AND type = $3
            """,
            ctx.guild.id,
            channel.id,
            media_type
        )

        if result == "DELETE 0":
            return await ctx.warn(f"No {media_type} automation found for {channel.mention}")

        return await ctx.approve(f"Removed {media_type} automation from {channel.mention}")

    @profile.command(name="list")
    async def profile_list(self, ctx: Context):
        """
        List all automatic media configurations.
        """
        data = await self.bot.db.fetch(
            """
            SELECT channel_id, type, category
            FROM auto.media
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if not data:
            return await ctx.warn("No automatic media configurations found.")

        entries = []
        for record in data:
            channel = ctx.guild.get_channel(record['channel_id'])
            if channel:
                entries.append(
                    f"{channel.mention}: **{record['type']}** ({record['category']})"
                )

        embed = Embed(
            title="Automatic Media Configurations",
            description="\n".join(entries) if entries else "No active configurations"
        )

        return await ctx.send(embed=embed)

    @hybrid_command()
    async def avreport(self, ctx: Context, image_id: str, category: str):
        """Report an inappropriate image."""
        report_channel = self.bot.get_channel(1309178072657821808)
        if not report_channel:
            return await ctx.warn("Report channel not found.")

        embed = Embed(
            title="Image Report",
            description=f"Image ID: `{image_id}`\nCategory: `{category}`",
            color=discord.Color.red()
        )
        
        embed.add_field(
            name="Reporter Information",
            value=f"User: {ctx.author} (`{ctx.author.id}`)\nGuild: {ctx.guild.name} (`{ctx.guild.id}`)"
        )
        
        embed.set_footer(text=f"Reported at {ctx.message.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        
        await report_channel.send(embed=embed)
        return await ctx.approve("Image has been reported to the staff team.")

    @group(aliases=["tra"], invoke_without_command=True)
    async def transcribe(self, ctx: Context) -> Message:
        """
        Transcribe audio from a file or message.
        """
        try:
            from pydub.utils import which

            if which("ffmpeg") is None or which("ffprobe") is None:
                return await ctx.warn(
                    "There was an ffmpeg error, please contact the developers."
                )

            attachment = None
            if ctx.message.attachments:
                attachment = ctx.message.attachments[0]
            elif ctx.replied_message and ctx.replied_message.attachments:
                attachment = ctx.replied_message.attachments[0]

            if not attachment:
                return await ctx.send_help(ctx.command)

            if not (
                attachment.filename.endswith((".mp3", ".wav", ".ogg", ".m4a"))
                or (
                    attachment.content_type
                    and "audio/ogg" in attachment.content_type
                    and attachment.filename.startswith("voice-message-")
                )
            ):
                return await ctx.warn("The file must be an audio file!")

            if attachment.size > 15_000_000:  # 15 mb cuh
                return await ctx.warn("The file must be under 15MB!")

            duration = await self.get_audio_duration(attachment.url)
            if duration > 90:  # 1:30
                return await ctx.warn(
                    "The audio must be under 1 minute and 30 seconds!"
                )

            async with ctx.typing():
                try:
                    transcript = await self.transcribe_audio(attachment.url)
                    return await ctx.approve(f"{transcript}")
                except Exception as e:
                    return await ctx.warn(f"Failed to transcribe audio: {e}")

        except Exception as e:
            return await ctx.warn(f"An error occurred: {e}")

    @transcribe.command(name="add", example="general")
    @has_permissions(manage_guild=True)
    async def transcribe_add(self, ctx: Context, channel: TextChannel) -> Message:
        """
        Add a channel for auto-transcription.
        """
        count = await self.bot.db.fetchval(
            """
            SELECT COUNT(*)
            FROM transcribe.channels
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if count >= 5:
            return await ctx.warn("You can only have 5 auto-transcribe channels!")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO transcribe.channels (guild_id, channel_id)
                VALUES ($1, $2)
                """,
                ctx.guild.id,
                channel.id,
            )
            return await ctx.approve(
                f"Added {channel.mention} to auto-transcribe channels!"
            )
        except Exception:
            return await ctx.warn(
                f"{channel.mention} is already an auto-transcribe channel!"
            )

    @transcribe.command(name="remove", example="general")
    @has_permissions(manage_guild=True)
    async def transcribe_remove(self, ctx: Context, channel: TextChannel) -> Message:
        """
        Remove a channel from auto-transcription.
        """
        deleted = await self.bot.db.execute(
            """
            DELETE FROM transcribe.channels
            WHERE guild_id = $1 AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )

        if not deleted:
            return await ctx.warn(
                f"{channel.mention} is not an auto-transcribe channel!"
            )

        return await ctx.approve(
            f"Removed {channel.mention} from auto-transcribe channels!"
        )

    @transcribe.command(name="list")
    async def transcribe_list(self, ctx: Context) -> Message:
        """
        List all auto-transcribe channels.
        """
        channels = await self.bot.db.fetch(
            """
            SELECT channel_id
            FROM transcribe.channels
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not channels:
            return await ctx.warn("No auto-transcribe channels set!")

        return await ctx.neutral(
            "Auto-transcribe channels:\n"
            + "\n".join(
                f"> {self.bot.get_channel(record['channel_id']).mention}"
                for record in channels
            )
        )

    @transcribe.command(name="clear")
    @has_permissions(manage_guild=True)
    async def transcribe_clear(self, ctx: Context) -> Message:
        """
        Clear all auto-transcribe channels.
        """
        if not await ctx.prompt(
            "Are you sure you want to clear all auto-transcribe channels?"
        ):
            return await ctx.warn("Action cancelled.")

        await self.bot.db.execute(
            """
            DELETE FROM transcribe.channels
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        return await ctx.approve("Cleared all auto-transcribe channels!")

    async def get_audio_duration(self, url: str) -> float:
        """Get duration of audio file in seconds and trim silence."""
        async with self.bot.session.get(url) as resp:
            if resp.status != 200:
                raise ValueError("Failed to download audio file")

            data = await resp.read()
            with io.BytesIO(data) as bio:
                audio = await asyncio.to_thread(AudioSegment.from_file, bio)

                chunks = await asyncio.to_thread(
                    lambda: detect_nonsilent(
                        audio,
                        min_silence_len=500,
                        silence_thresh=-40,
                    )
                )

                if not chunks:
                    return 0

                non_silent_audio = AudioSegment.empty()
                for start, end in chunks:
                    non_silent_audio += audio[start:end]

                return len(non_silent_audio) / 1000

    async def transcribe_audio(self, url: str) -> str:
        """Transcribe audio file using Whisper API."""
        async with self.bot.session.get(url) as resp:
            if resp.status != 200:
                raise ValueError("Failed to download audio file")

            data = await resp.read()
            with io.BytesIO(data) as bio:
                audio = await asyncio.to_thread(AudioSegment.from_file, bio)

                chunks = await asyncio.to_thread(
                    lambda: detect_nonsilent(
                        audio,
                        min_silence_len=500,
                        silence_thresh=-40,
                    )
                )

                if not chunks:
                    return "No speech detected in audio."

                non_silent_audio = AudioSegment.empty()
                for start, end in chunks:
                    non_silent_audio += audio[start:end]

                output = io.BytesIO()
                await asyncio.to_thread(
                    lambda: non_silent_audio.export(output, format="mp3")
                )
                output.seek(0)

                form = FormData()
                form.add_field(
                    "file", output, filename="audio.mp3", content_type="audio/mp3"
                )
                form.add_field("model", "whisper-1")

            async with self.bot.session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}"},
                data=form,
            ) as resp:
                if resp.status != 200:
                    raise ValueError("Failed to transcribe audio")

                result = await resp.json()
                return result["text"]

    @Cog.listener("on_message")
    async def auto_transcribe(self, message: Message):
        try:
            from pydub.utils import which

            if which("ffmpeg") is None or which("ffprobe") is None:
                return
        except Exception:
            return

        if not message.guild or not message.attachments:
            return

        channel_ids = await self.bot.db.fetch(
            """
            SELECT channel_id
            FROM transcribe.channels
            WHERE guild_id = $1
            """,
            message.guild.id,
        )

        if not channel_ids or message.channel.id not in [
            r["channel_id"] for r in channel_ids
        ]:
            return

        rate_limit = await self.bot.db.fetchrow(
            """
            SELECT last_used, uses 
            FROM transcribe.rate_limit
            WHERE guild_id = $1 AND channel_id = $2
            """,
            message.guild.id,
            message.channel.id,
        )

        now = datetime.now(timezone.utc)
        if rate_limit:
            if (now - rate_limit["last_used"]).total_seconds() < 60:
                if rate_limit["uses"] >= 3:
                    return
                await self.bot.db.execute(
                    """
                    UPDATE transcribe.rate_limit
                    SET uses = uses + 1
                    WHERE guild_id = $1 AND channel_id = $2
                    """,
                    message.guild.id,
                    message.channel.id,
                )
            else:
                await self.bot.db.execute(
                    """
                    UPDATE transcribe.rate_limit
                    SET last_used = $3, uses = 1
                    WHERE guild_id = $1 AND channel_id = $2
                    """,
                    message.guild.id,
                    message.channel.id,
                    now,
                )
        else:
            await self.bot.db.execute(
                """
                INSERT INTO transcribe.rate_limit (guild_id, channel_id)
                VALUES ($1, $2)
                """,
                message.guild.id,
                message.channel.id,
            )

        for attachment in message.attachments:
            if not (
                attachment.filename.endswith((".mp3", ".wav", ".ogg", ".m4a"))
                or (
                    attachment.content_type
                    and "audio/ogg" in attachment.content_type
                    and attachment.filename.startswith("voice-message-")
                )
            ):
                continue

            if attachment.size > 15_000_000:
                continue

            try:
                duration = await self.get_audio_duration(attachment.url)
                if duration > 90:
                    continue

                transcript = await self.transcribe_audio(attachment.url)
                await message.reply(f"{transcript}")
            except Exception:
                continue

    @group(name="wordstats", aliases=["ws"], invoke_without_command=True)
    async def wordstats(self, ctx: Context):
        """
        View word statistics for this server.
        """
        await ctx.send_help(ctx.command)

    @wordstats.command(name="topchatters", example="lol")
    async def wordstats_topchatters(
        self, 
        ctx: Context,
        word: Optional[str] = None
    ) -> Message:
        """
        Shows members who have sent the most messages.
        If a word is provided, shows who uses that word the most.
        """
        if word:
            data = await self.bot.db.fetch(
                """
                SELECT user_id, count
                FROM stats.word_usage
                WHERE guild_id = $1 AND word = $2
                ORDER BY count DESC
                LIMIT 25
                """,
                ctx.guild.id,
                word.lower()
            )
            
            if not data:
                return await ctx.warn(f"No one has used the word **{word}** yet!")
                
            embed = Embed(title=f"Top users of '{word}'")
            entries = []
            for record in data:
                member = ctx.guild.get_member(record['user_id'])
                user_text = member.mention if member else f"Unknown User ({record['user_id']})"
                entries.append(f"{user_text}: **{record['count']:,}** times")
            
        else:
            data = await self.bot.db.fetch(
                """
                SELECT user_id, SUM(count) as total
                FROM stats.word_usage
                WHERE guild_id = $1
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 25
                """,
                ctx.guild.id
            )
            
            if not data:
                return await ctx.warn("No word statistics available yet!")
                
            embed = Embed(title="Top Chatters")
            entries = []
            for record in data:
                member = ctx.guild.get_member(record['user_id'])
                user_text = member.mention if member else f"Unknown User ({record['user_id']})"
                entries.append(f"{user_text}: **{record['total']:,}** words")

        paginator = Paginator(
            ctx,
            entries=entries,
            embed=embed,
            per_page=10
        )
        return await paginator.start()

    @wordstats.command(name="topratio")
    async def wordstats_topratio(self, ctx: Context) -> Message:
        """
        Shows members with the highest ratio of unique words to total words.
        Only includes members with at least 1000 total words.
        """
        data = await self.bot.db.fetch(
            """
            WITH user_stats AS (
                SELECT 
                    user_id,
                    COUNT(DISTINCT word) as unique_words,
                    SUM(count) as total_words
                FROM stats.word_usage
                WHERE guild_id = $1
                GROUP BY user_id
                HAVING SUM(count) >= 1000
            )
            SELECT 
                user_id,
                unique_words,
                total_words,
                ROUND(CAST(unique_words AS DECIMAL) / total_words * 100, 2) as ratio
            FROM user_stats
            ORDER BY ratio DESC
            LIMIT 25
            """,
            ctx.guild.id
        )
        
        if not data:
            return await ctx.warn("No users have enough words to calculate ratios yet!")
            
        embed = Embed(title="Top Word Variety Ratios")
        entries = [
            f"{ctx.guild.get_member(record['user_id']).mention}: "
            f"**{record['ratio']}%** ({record['unique_words']:,} unique / {record['total_words']:,} total)"
            for record in data
        ]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=embed,
            per_page=10
        )
        return await paginator.start()

    @wordstats.command(name="common")
    async def wordstats_common(self, ctx: Context) -> Message:
        """
        Shows the most commonly used words in the server.
        Excludes ignored words and requires minimum word length from config.
        """
        config = await self.bot.db.fetchrow(
            """
            SELECT min_word_length
            FROM stats.config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        ) or {'min_word_length': 3}
        
        ignored = await self.bot.db.fetch(
            """
            SELECT word
            FROM stats.ignored_words
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        ignored_words = {r['word'] for r in ignored}
        
        data = await self.bot.db.fetch(
            """
            SELECT word, SUM(count) as total
            FROM stats.word_usage
            WHERE guild_id = $1
            AND LENGTH(word) >= $2
            GROUP BY word
            ORDER BY total DESC
            LIMIT 50
            """,
            ctx.guild.id,
            config['min_word_length']
        )
        
        filtered_data = [
            r for r in data 
            if r['word'].lower() not in ignored_words
        ]
        
        if not filtered_data:
            return await ctx.warn("No word statistics available yet!")
            
        total_words = sum(r['total'] for r in data)
        
        embed = Embed(title="Most Common Words")
        entries = [
            f"**{record['word']}**: {record['total']:,} times "
            f"({record['total']/total_words*100:.1f}%)"
            for record in filtered_data
        ]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=embed,
            per_page=10
        )
        embed.set_footer(text=f"Total words analyzed: {total_words:,}")
        
        return await paginator.start()

    @wordstats.group(name="ignore", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def wordstats_ignore(self, ctx: Context) -> Message:
        """
        Manage words to ignore in statistics.
        """
        return await ctx.send_help(ctx.command)

    @wordstats_ignore.command(name="add", example="hi")
    @has_permissions(manage_guild=True)
    async def wordstats_ignore_add(self, ctx: Context, word: str) -> Message:
        """Add a word to the ignore list"""
        word = word.lower()
        try:
            await self.bot.db.execute(
                """
                INSERT INTO stats.ignored_words (guild_id, word, added_by)
                VALUES ($1, $2, $3)
                """,
                ctx.guild.id,
                word,
                ctx.author.id
            )
            return await ctx.approve(f"Added **{word}** to ignored words!")
        except Exception:
            return await ctx.warn(f"**{word}** is already being ignored!")

    @wordstats_ignore.command(name="remove", example="hi")
    @has_permissions(manage_guild=True)
    async def wordstats_ignore_remove(self, ctx: Context, word: str) -> Message:
        """Remove a word from the ignore list"""
        word = word.lower()
        result = await self.bot.db.execute(
            """
            DELETE FROM stats.ignored_words
            WHERE guild_id = $1 AND word = $2
            """,
            ctx.guild.id,
            word
        )
        
        if result == "DELETE 0":
            return await ctx.warn(f"**{word}** was not being ignored!")
            
        return await ctx.approve(f"Removed **{word}** from ignored words!")

    @wordstats_ignore.command(name="list")
    @has_permissions(manage_guild=True)
    async def wordstats_ignore_list(self, ctx: Context) -> Message:
        """View all ignored words"""
        data = await self.bot.db.fetch(
            """
            SELECT word, added_by, added_at
            FROM stats.ignored_words
            WHERE guild_id = $1
            ORDER BY word
            """,
            ctx.guild.id
        )
        
        if not data:
            return await ctx.warn("No ignored words configured!")
            
        embed = Embed(title="Ignored Words")
        chunks = [data[i:i+10] for i in range(0, len(data), 10)]
        
        paginator = Paginator(
            ctx,
            entries=[
                "\n".join(
                    f"`{word['word']}` - Added by {ctx.guild.get_member(word['added_by']).mention} "
                    f"({format_dt(word['added_at'], 'R')})"
                    for word in chunk
                )
                for chunk in chunks
            ],
            embed=embed
        )
        return await paginator.start()

    @wordstats.command(name="config", example="minlength 3")
    @has_permissions(manage_guild=True)
    async def wordstats_config(
        self,
        ctx: Context,
        setting: str,
        value: str
    ) -> Message:
        """
        Configure wordstats settings.
        
        Settings:
        - minlength: Minimum word length to track (2-10)
        - countbots: Whether to count bot messages (true/false)
        - whitelist: Channel IDs to exclusively track (comma-separated)
        - blacklist: Channel IDs to ignore (comma-separated)
        """
        setting = setting.lower()
        if setting not in ("minlength", "countbots", "whitelist", "blacklist"):
            return await ctx.warn("Invalid setting! Use minlength, countbots, whitelist, or blacklist")

        if setting == "minlength":
            try:
                length = int(value)
                if not 2 <= length <= 10:
                    raise ValueError
            except ValueError:
                return await ctx.warn("Minimum length must be between 2 and 10!")
                
            await self.bot.db.execute(
                """
                INSERT INTO stats.config (guild_id, min_word_length)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET min_word_length = EXCLUDED.min_word_length
                """,
                ctx.guild.id,
                length
            )
            return await ctx.approve(f"Set minimum word length to **{length}**!")
            
        elif setting == "countbots":
            value = value.lower()
            if value not in ("true", "false"):
                return await ctx.warn("Value must be 'true' or 'false'!")
                
            count_bots = value == "true"
            await self.bot.db.execute(
                """
                INSERT INTO stats.config (guild_id, count_bots)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET count_bots = EXCLUDED.count_bots
                """,
                ctx.guild.id,
                count_bots
            )
            return await ctx.approve(f"{'Now' if count_bots else 'No longer'} counting bot messages!")
            
        elif setting in ("whitelist", "blacklist"):
            try:
                channels = [int(c.strip()) for c in value.split(",")]
                valid_channels = [
                    c for c in channels 
                    if ctx.guild.get_channel(c)
                ]
            except ValueError:
                return await ctx.warn("Please provide valid channel IDs separated by commas!")
                
            if not valid_channels:
                return await ctx.warn("No valid channels provided!")
                
            column = f"channel_{setting}"
            await self.bot.db.execute(
                f"""
                INSERT INTO stats.config (guild_id, {column})
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET {column} = EXCLUDED.{column}
                """,
                ctx.guild.id,
                valid_channels
            )
            
            channels_text = ", ".join(f"<#{c}>" for c in valid_channels)
            return await ctx.approve(f"Updated {setting} to: {channels_text}")

    @Cog.listener("on_message")
    async def word_tracker(self, message: Message):
        if not message.guild or message.author.bot:
            return
            
        cache_key = f'wordstats_config_{message.guild.id}'
        config = self._get_cache(cache_key)
        if config is None:
            config = await self.bot.db.fetchrow(
                """
                SELECT count_bots, channel_whitelist, channel_blacklist
                FROM stats.config
                WHERE guild_id = $1
                """,
                message.guild.id
            ) or {'count_bots': False, 'channel_whitelist': None, 'channel_blacklist': None}
            self._set_cache(cache_key, config, expire=300)
            
        if message.author.bot and not config['count_bots']:
            return
            
        if config['channel_whitelist'] and message.channel.id not in config['channel_whitelist']:
            return
            
        if config['channel_blacklist'] and message.channel.id in config['channel_blacklist']:
            return
            
        words = re.findall(r'\b\w+\b', message.content.lower())
        if not words:
            return

        word_counts = {}
        for word in words:
            word_counts[word] = word_counts.get(word, 0) + 1

        unique_words = list(word_counts.keys())
        counts = list(word_counts.values())

        await self.bot.db.execute(
            """
            INSERT INTO stats.word_usage (guild_id, user_id, word, count, last_used)
            SELECT $1, $2, word, count, CURRENT_TIMESTAMP
            FROM unnest($3::text[], $4::int[]) AS t(word, count)
            ON CONFLICT (guild_id, user_id, word)
            DO UPDATE SET 
                count = stats.word_usage.count + EXCLUDED.count,
                last_used = CURRENT_TIMESTAMP
            """,
            message.guild.id,
            message.author.id,
            unique_words,
            counts
        )

    @wordstats.group(name="command", aliases=["cmd"], invoke_without_command=True)
    async def wordstats_command(self, ctx: Context) -> Message:
        """
        Create custom commands to track specific words.
        """
        return await ctx.send_help(ctx.command)

    @wordstats_command.command(name="add", example="fword fuck")
    async def wordstats_command_add(self, ctx: Context, command: str, word: str) -> Message:
        """Create a custom command to track a word"""
        command = command.lower()
        word = word.lower()

        if self.bot.get_command(command):
            return await ctx.warn(f"Command `{command}` already exists!")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO stats.custom_commands (guild_id, command, word, created_by)
                VALUES ($1, $2, $3, $4)
                """,
                ctx.guild.id,
                command,
                word,
                ctx.author.id
            )
            return await ctx.approve(f"Created command `{command}` to track the word **{word}**!")
        except Exception:
            return await ctx.warn(f"Command `{command}` already exists for this server!")

    @wordstats_command.command(name="remove", example="fword")
    async def wordstats_command_remove(self, ctx: Context, command: str) -> Message:
        """Remove a custom word tracking command"""
        command = command.lower()
        result = await self.bot.db.execute(
            """
            DELETE FROM stats.custom_commands
            WHERE guild_id = $1 AND command = $2
            """,
            ctx.guild.id,
            command
        )
        
        if result == "DELETE 0":
            return await ctx.warn(f"Command `{command}` doesn't exist!")
            
        return await ctx.approve(f"Removed command `{command}`!")

    @wordstats_command.command(name="list")
    async def wordstats_command_list(self, ctx: Context) -> Message:
        """View all custom word tracking commands"""
        data = await self.bot.db.fetch(
            """
            SELECT command, word, created_by, created_at
            FROM stats.custom_commands
            WHERE guild_id = $1
            ORDER BY command
            """,
            ctx.guild.id
        )
        
        if not data:
            return await ctx.warn("No custom commands configured!")
            
        embed = Embed(title="Custom Word Commands")
        entries = [
            f"`;{cmd['command']}` tracks **{cmd['word']}** - Created by {ctx.guild.get_member(cmd['created_by']).mention} "
            f"({format_dt(cmd['created_at'], 'R')})"
            for cmd in data
        ]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=embed,
            per_page=10
        )
        return await paginator.start()

    async def process_custom_command(self, ctx: Context, command: str) -> Optional[Message]:
        """Process a custom word tracking command"""
        data = await self.bot.db.fetchrow(
            """
            SELECT word
            FROM stats.custom_commands
            WHERE guild_id = $1 AND command = $2
            """,
            ctx.guild.id,
            command
        )
        
        if not data:
            return None
            
        word = data['word']
        
        target_id = ctx.message.mentions[0].id if ctx.message.mentions else ctx.author.id
        
        stats = await self.bot.db.fetchval(
            """
            SELECT count
            FROM stats.word_usage
            WHERE guild_id = $1 AND word = $2 AND user_id = $3
            """,
            ctx.guild.id,
            word,
            target_id
        ) or 0
        
        user = ctx.guild.get_member(target_id)
        user_text = user.mention if user else f"Unknown User ({target_id})"
        
        embed = Embed(
            description=f"{user_text} has said **{word}** {stats:,} times",
            color=0xCCCCFF
        )
        return await ctx.send(embed=embed)

    @hybrid_command(aliases=["texttospeech", "speak"], example="hi how are you")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def tts(
        self,
        ctx: Context,
        voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "nova",
        *,
        text: str,
    ) -> Message:
        """
        Convert text to speech using OpenAI's TTS API.
        Premium users get 15 uses per hour and HD quality.
        
        Voices:
        - alloy: Versatile, balanced voice
        - echo: Warm, clear voice
        - fable: British accent, suitable for storytelling
        - onyx: Deep, authoritative voice
        - nova: Energetic female voice
        - shimmer: Gentle, welcoming voice
        """
        if len(text) > 1000:
            return await ctx.warn("Text cannot exceed 1000 characters!")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        key = f"tts:{ctx.author.id}"
        uses = await self.bot.redis.get(key)
        ttl = await self.bot.redis.ttl(key)
        
        max_uses = 15 if is_donor else 2
        
        if uses and int(uses) >= max_uses:
            embed = Embed(
                color=config.COLORS.WARN,
                description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in {int(ttl)} seconds.\n\nDonors get 15 uses per hour instead of 2! Consider becoming a donor for increased access."
            )
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="Become a Donor",
                    url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                    style=discord.ButtonStyle.url
                )
            )
            msg = await ctx.send(embed=embed)
            await msg.edit(view=view)
            return

        embed = Embed(
            title="Text to Speech",
            description=f"Voice: **{voice}**\nText: {text[:100]}{'...' if len(text) > 100 else ''}"
        )
        
        if is_donor:
            embed.set_footer(text="Premium User • HD Quality")
        else:
            embed.set_footer(text="Free User • Standard Quality")

        loading_msg = await ctx.send(
            f"Converting text to speech...", 
            embed=embed
        )

        try:
            if not isinstance(ctx.channel, discord.DMChannel):
                async with ctx.typing():
                    response = await self._generate_tts(ctx, text, voice, is_donor)
            else:
                response = await self._generate_tts(ctx, text, voice, is_donor)

            if not response:
                return await ctx.warn("Failed to generate speech!")

            audio_data = await response.read()
            file_size = len(audio_data)

            if isinstance(ctx.channel, discord.DMChannel):
                temp_file = "voice-message.mp3"
                try:
                    with open(temp_file, "wb") as f:
                        f.write(audio_data)
                    await ctx.send(
                        embed=embed,
                        file=discord.File(temp_file)
                    )
                finally:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            else:
                waveform = [random.randint(50, 200) for _ in range(256)]
                waveform_base64 = base64.b64encode(bytes(waveform)).decode('utf-8')

                upload_request = await self.bot.session.post(
                    f"https://discord.com/api/v10/channels/{ctx.channel.id}/attachments",
                    headers={
                        "Authorization": f"Bot {config.DISCORD.TOKEN}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "files": [{
                            "filename": "voice-message.ogg",
                            "file_size": file_size,
                            "id": "2"
                        }]
                    }
                )
                
                upload_data = await upload_request.json()
                upload_url = upload_data["attachments"][0]["upload_url"]
                uploaded_filename = upload_data["attachments"][0]["upload_filename"]

                await self.bot.session.put(
                    upload_url,
                    headers={
                        "Content-Type": "audio/ogg",
                        "Authorization": f"Bot {config.DISCORD.TOKEN}"
                    },
                    data=audio_data
                )

                await self.bot.session.post(
                    f"https://discord.com/api/v10/channels/{ctx.channel.id}/messages",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bot {config.DISCORD.TOKEN}"
                    },
                    json={
                        "flags": 8192,
                        "message_reference": {
                            "message_id": loading_msg.id,
                            "channel_id": ctx.channel.id,
                            "guild_id": ctx.guild.id
                        },
                        "attachments": [{
                            "id": "0",
                            "filename": "voice-message.ogg",
                            "uploaded_filename": uploaded_filename,
                            "duration_secs": 30,
                            "waveform": waveform_base64
                        }]
                    }
                )

            await loading_msg.edit(content=None)

            pipe = self.bot.redis.pipeline()
            pipe.incr(key)
            if not uses:
                pipe.expire(key, 3600)
            await pipe.execute()

        except Exception as e:
            await loading_msg.delete()
            return await ctx.warn(f"Failed to generate speech: {e}")

    async def _generate_tts(self, ctx: Context, text: str, voice: str, is_donor: bool):
        """Helper method to generate TTS response"""
        response = await self.bot.session.post(
            "https://api.openai.com/v1/audio/speech",
            headers={
                "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                "Content-Type": "application/json"
            },
            json={
                "model": "tts-1-hd" if is_donor else "tts-1",
                "input": text,
                "voice": voice,
                "response_format": "mp3" if isinstance(ctx.channel, discord.DMChannel) else "opus"
            }
        )
        
        if response.status != 200:
            return None
            
        return response

    @hybrid_command(name="imagine", example="standard 1024x1024 a hamburger")
    async def imagine(
        self,
        ctx: Context,
        quality: Literal["standard", "hd"] = "standard",
        size: Literal["1024x1024", "1024x1792", "1792x1024"] = "1024x1024",
        *,
        prompt: str,
    ) -> Message:
        """
        Generate images using DALL-E 3.
        Premium users get $15 worth of credits per 2 weeks.
        Free users get 2 generations per day.

        Quality:
        - standard: Basic quality ($0.040 per image)
        - hd: Higher quality ($0.080 per image)

        Size:
        - 1024x1024: Square image
        - 1024x1792: Portrait
        - 1792x1024: Landscape
        """
        if len(prompt) > 4000:
            return await ctx.warn("Prompt cannot exceed 4000 characters!")
        
        minute_key = f"imagine_minute:{ctx.author.id}"
        minute_uses = await self.bot.redis.get(minute_key)
        if minute_uses and int(minute_uses) >= 5:
            return await ctx.warn("You can only generate 5 images per minute. Please wait a moment.")

        daily_key = f"imagine_daily:{ctx.author.id}"
        daily_uses = await self.bot.redis.get(daily_key)
        if daily_uses and int(daily_uses) >= 1000:
            ttl = await self.bot.redis.ttl(daily_key)
            hours = int(ttl / 3600)
            minutes = int((ttl % 3600) / 60)
            return await ctx.warn(f"Daily limit reached (1000/1000). Resets in {hours}h {minutes}m")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        base_cost = decimal.Decimal('0.080') if quality == "hd" else decimal.Decimal('0.040')
        if size != "1024x1024":
            base_cost *= decimal.Decimal('2')

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None:
                await self.bot.db.execute(
                    """
                    INSERT INTO dalle_credits (user_id, credits, last_reset)
                    VALUES ($1, $2, NOW())
                    """,
                    ctx.author.id,
                    15.00 
                )
                credits = decimal.Decimal('15.00')

            last_reset = await self.bot.db.fetchval(
                """
                SELECT last_reset
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if (datetime.now() - last_reset).days >= 14:
                await self.bot.db.execute(
                    """
                    UPDATE dalle_credits
                    SET credits = $1, last_reset = NOW()
                    WHERE user_id = $2
                    """,
                    15.00,
                    ctx.author.id
                )
                credits = decimal.Decimal('15.00')

            if credits < base_cost:
                return await ctx.warn(
                    f"Insufficient credits! You have ${credits:.3f} remaining.\n"
                    f"This generation would cost ${base_cost:.3f}.\n"
                    "Credits reset every 2 weeks."
                )

        else:
            key = f"imagine:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            ttl = await self.bot.redis.ttl(key)
            
            if uses and int(uses) >= 2:
                embed = Embed(
                    color=config.COLORS.WARN,
                    description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in {int(ttl)} seconds.\n\nDonors get $15 worth of DALL-E credits every 2 weeks! Consider upgrading for increased access."
                )
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                msg = await ctx.send(embed=embed)
                await msg.edit(view=view)
                return

        global_minute_key = "dalle_global_minute"
        global_daily_key = "dalle_global_daily"
        
        global_minute_uses = await self.bot.redis.get(global_minute_key)
        if global_minute_uses and int(global_minute_uses) >= 5:
            return await ctx.warn("The image generation system is at capacity (5/minute). Please try again in a moment.")
    
        global_daily_uses = await self.bot.redis.get(global_daily_key)
        if global_daily_uses and int(global_daily_uses) >= 500:
            ttl = await self.bot.redis.ttl(global_daily_key)
            hours = int(ttl / 3600)
            minutes = int((ttl % 3600) / 60)
            return await ctx.warn(f"Daily global limit reached (500/500). Resets in {hours}h {minutes}m")

        async with ctx.typing():
            try:
                pipe = self.bot.redis.pipeline()
                pipe.incr(global_minute_key)
                pipe.expire(global_minute_key, 60)
                pipe.incr(global_daily_key)
                if not global_daily_uses:
                    pipe.expire(global_daily_key, 86400)
                await pipe.execute()

                response = await self.bot.session.post(
                    "https://api.openai.com/v1/images/generations",
                    headers={
                        "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "dall-e-3",
                        "prompt": prompt,
                        "n": 1,
                        "quality": quality,
                        "size": size
                    }
                )

                if response.status != 200:
                    error_data = await response.json()
                    log.error(
                        f"DALL-E generation failed: Status {response.status}\n"
                        f"Error: {error_data}\n"
                        f"User: {ctx.author} ({ctx.author.id})\n"
                        f"Prompt: {prompt}\n"
                        f"Quality: {quality}, Size: {size}"
                    )
                    return await ctx.warn(f"Failed to generate image: {error_data.get('error', {}).get('message', 'Unknown error')}")

                data = await response.json()
                image_url = data["data"][0]["url"]

                embed = Embed(
                    title="DALL-E Image Generation",
                    description=f"**Prompt:** {prompt}\n**Quality:** {quality}\n**Size:** {size}"
                )
                embed.set_image(url=image_url)

                if is_donor:
                    new_credits = credits - base_cost
                    await self.bot.db.execute(
                        """
                        UPDATE dalle_credits
                        SET credits = $1
                        WHERE user_id = $2
                        """,
                        new_credits,
                        ctx.author.id
                    )
                    embed.set_footer(text=f"Premium User • ${new_credits:.3f} credits remaining")
                else:
                    pipe = self.bot.redis.pipeline()
                    pipe.incr(key)
                    if not uses:
                        pipe.expire(key, 86400) 
                    await pipe.execute()
                    embed.set_footer(text="Free User • 2 uses per day")

                pipe = self.bot.redis.pipeline()
                pipe.incr(minute_key)
                pipe.expire(minute_key, 60) 
                pipe.incr(daily_key)
                if not daily_uses:
                    pipe.expire(daily_key, 86400)  
                await pipe.execute()

                return await ctx.send(embed=embed)

            except Exception as e:
                log.error(
                    f"DALL-E generation error:\n"
                    f"Error: {str(e)}\n"
                    f"User: {ctx.author} ({ctx.author.id})\n"
                    f"Prompt: {prompt}\n"
                    f"Quality: {quality}, Size: {size}",
                    exc_info=True
                )
                return await ctx.warn(f"Failed to generate image: {str(e)}")

    @hybrid_command(name="dalle_credits")
    async def dalle_credits(self, ctx: Context) -> Message:
        """
        Check your DALL-E credits.
        """
        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None:
                await self.bot.db.execute(
                    """
                    INSERT INTO dalle_credits (user_id, credits, last_reset)
                    VALUES ($1, $2, NOW())
                    """,
                    ctx.author.id,
                    15.00 
                )
                credits = 15.00

            last_reset = await self.bot.db.fetchval(
                """
                SELECT last_reset
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if (datetime.now() - last_reset).days >= 14:
                await self.bot.db.execute(
                    """
                    UPDATE dalle_credits
                    SET credits = $1, last_reset = NOW()
                    WHERE user_id = $2
                    """,
                    15.00,
                    ctx.author.id
                )
                credits = 15.00

            days_until_reset = 14 - (datetime.now() - last_reset).days
            embed = Embed(
                title="DALL-E Credits",
                description=f"You have ${credits:.3f} credits remaining.\n"
                f"Credits reset in {days_until_reset} days.\n\n"
                "**Pricing:**\n"
                "- Standard quality: $0.040 per image\n"
                "- HD quality: $0.080 per image\n"
                "- Portrait/Landscape: Double the cost\n"
                "- Premium users get $15 worth of credits every 2 weeks"
            )
            embed.set_footer(text="Contact support to request increased limits")

        else:
            key = f"imagine:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            ttl = await self.bot.redis.ttl(key)
            
            remaining_uses = 2 - int(uses) if uses else 2
            embed = Embed(
                title="DALL-E Credits",
                description=f"You have {remaining_uses} generations remaining.\n"
                f"Resets in {int(ttl)} seconds.\n\n"
                "**Pricing:**\n"
                "- Standard quality: $0.040 per image\n"
                "- HD quality: $0.080 per image\n"
                "- Portrait/Landscape: Double the cost\n"
                "- Premium users get $15 worth of credits every 2 weeks"
            )
            embed.set_footer(text="Become a donor for increased access")

            if remaining_uses <= 0:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                msg = await ctx.send(embed=embed)
                await msg.edit(view=view)
                return

        return await ctx.send(embed=embed)

    @hybrid_command(name="credits")
    async def dalle_credits(self, ctx: Context) -> Message:
        """Check your available DALL-E credits."""
        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None:
                await self.bot.db.execute(
                    """
                    INSERT INTO dalle_credits (user_id, credits, last_reset)
                    VALUES ($1, $2, NOW())
                    """,
                    ctx.author.id,
                    15.00
                )
                credits = 15.00

            last_reset = await self.bot.db.fetchval(
                """
                SELECT last_reset
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            days_until_reset = 14 - (datetime.now() - last_reset).days

            embed = Embed(
                title="DALL-E Credits",
                description=(
                    f"**Current Balance:** ${credits:.3f}\n"
                    f"**Days until reset:** {days_until_reset}\n\n"
                    "**Pricing:**\n"
                    "- Standard Quality: $0.040 per image\n"
                    "- HD Quality: $0.080 per image\n"
                    "- Non-square sizes cost 2x more"
                )
            )
            embed.set_footer(text="Premium User • Credits reset every 2 weeks")
            return await ctx.send(embed=embed)
        else:
            key = f"imagine:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            ttl = await self.bot.redis.ttl(key)
            remaining = 2 - (int(uses) if uses else 0)

            view = None
            if remaining <= 0:
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )

            embed = Embed(
                title="DALL-E Credits",
                description=(
                    f"**Remaining Uses:** {remaining}/2\n"
                    f"**Time until reset:** {int(ttl) if ttl > 0 else 0} seconds\n\n"
                    "**Premium Benefits:**\n"
                    "- $15 worth of credits every 2 weeks\n"
                    "- Higher quality options\n"
                    "- More size options"
                )
            )
            embed.set_footer(text="Free User • 2 uses per day")
            return await ctx.send(embed=embed, view=view)

    async def get_image_base64(self, url: str) -> str:
        async with self.bot.session.get(url) as response:
            if response.status != 200:
                raise ValueError("Failed to fetch image")
            image_data = await response.read()
            return f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}"

    @hybrid_command(name="describe")
    async def describe_image(
        self, 
        ctx: Context, 
        image: Optional[Attachment] = None
    ) -> Message:
        """Get an AI description of an image using GPT-4 Vision"""
        if not image:
            if not ctx.message.reference:
                return await ctx.warn("Please provide an image or reply to a message with an image!")
                
            try:
                reference = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                if reference.attachments:
                    image = reference.attachments[0]
                elif reference.embeds and reference.embeds[0].image:
                    image = SimpleNamespace(
                        url=reference.embeds[0].image.url,
                        content_type='image/unknown'
                    )
                else:
                    return await ctx.warn("The replied message doesn't contain any images!")
            except:
                return await ctx.warn("Couldn't fetch the replied message!")

        if not image.content_type.startswith('image/'):
            return await ctx.warn("Please provide a valid image!")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        cost = decimal.Decimal('0.05')

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None or credits < cost:
                return await ctx.warn(
                    f"Insufficient credits! You need ${cost:.3f} for this command.\n"
                    f"Current balance: ${credits:.3f if credits else 0:.3f}"
                )

        else:
            key = f"describe:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            if uses and int(uses) >= 2:
                embed = Embed(
                    color=config.COLORS.WARN,
                    description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in 24h.\n\nDonors get $15 worth of credits every 2 weeks!"
                )
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                return await ctx.send(embed=embed, view=view)
        
        async with ctx.typing():
            try:
                image_base64 = await self.get_image_base64(image.url)
                response = await self.bot.session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4-0125-preview",
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Describe this image in detail"},
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": image_base64
                                        }
                                    }
                                ]
                            }
                        ],
                        "max_tokens": 300
                    }
                )
                
                if response.status != 200:
                    error_data = await response.json()
                    log.error(
                        f"GPT-4 Vision failed: Status {response.status}\n"
                        f"Error: {error_data}\n"
                        f"User: {ctx.author} ({ctx.author.id})\n"
                        f"Image URL: {image.url}"
                    )
                    return await ctx.warn(f"Failed to analyze image: {error_data.get('error', {}).get('message', 'Unknown error')}")
                    
                data = await response.json()
                description = data['choices'][0]['message']['content']
                
                if is_donor:
                    await self.bot.db.execute(
                        """
                        UPDATE dalle_credits
                        SET credits = credits - $1
                        WHERE user_id = $2
                        """,
                        cost,
                        ctx.author.id
                    )
                else:
                    pipe = self.bot.redis.pipeline()
                    pipe.incr(key)
                    if not uses:
                        pipe.expire(key, 86400)
                    await pipe.execute()
                
                embed = Embed(description=description)
                embed.set_image(url=image.url)
                if is_donor:
                    new_balance = credits - cost
                    embed.set_footer(text=f"Premium User • ${new_balance:.3f} credits remaining")
                else:
                    embed.set_footer(text="Free User • 2 uses per day")
                return await ctx.send(embed=embed)
                
            except Exception as e:
                return await ctx.warn(f"Failed to analyze image: {e}")

    @hybrid_command(name="complete", example="the united states is...")
    async def complete_text(self, ctx: Context, *, prompt: str) -> Message:
        """Complete your text using GPT-3.5"""
        if len(prompt) > 1000:
            return await ctx.warn("Prompt cannot exceed 1000 characters!")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        cost = decimal.Decimal('0.02') 

        if is_donor:
            credits = await self.bot.db.fetchval(
                """
                SELECT credits
                FROM dalle_credits
                WHERE user_id = $1
                """,
                ctx.author.id
            )

            if credits is None or credits < cost:
                return await ctx.warn(
                    f"Insufficient credits! You need ${cost:.3f} for this command.\n"
                    f"Current balance: ${credits:.3f if credits else 0:.3f}"
                )

        else:
            key = f"complete:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            if uses and int(uses) >= 3:
                embed = Embed(
                    color=config.COLORS.WARN,
                    description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in 24h.\n\nDonors get $15 worth of credits every 2 weeks!"
                )
                view = discord.ui.View()
                view.add_item(
                    discord.ui.Button(
                        label="Become a Donor",
                        url="https://donate.stripe.com/cN26ra4tXgrg3T2cMR",
                        style=discord.ButtonStyle.url
                    )
                )
                return await ctx.send(embed=embed, view=view)

        async with ctx.typing():
            try:
                response = await self.bot.session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-3.5-turbo",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "max_tokens": 500,
                        "temperature": 0.7
                    }
                )
                
                if response.status != 200:
                    return await ctx.warn("Failed to generate completion!")
                    
                data = await response.json()
                completion = data['choices'][0]['message']['content']
                
                if is_donor:
                    await self.bot.db.execute(
                        """
                        UPDATE dalle_credits
                        SET credits = credits - $1
                        WHERE user_id = $2
                        """,
                        cost,
                        ctx.author.id
                    )
                else:
                    pipe = self.bot.redis.pipeline()
                    pipe.incr(key)
                    if not uses:
                        pipe.expire(key, 86400)
                    await pipe.execute()
                
                embed = Embed(title="Text Completion", description=completion)
                if is_donor:
                    new_balance = credits - cost
                    embed.set_footer(text=f"Premium User • ${new_balance:.3f} credits remaining")
                else:
                    embed.set_footer(text="Free User • 3 uses per day")
                return await ctx.send(embed=embed)
                
            except Exception as e:
                return await ctx.warn(f"Failed to generate completion: {e}")

    @command(name="donator", aliases=["donate", "donators"])
    async def donator(self, ctx: Context) -> Message:
        """View information about donator perks and benefits."""
        
        embed = Embed(
            title="<:donor1:1320054420616249396> Donator Benefits",
            description=(
                "Support Evict's development and get access to exclusive features!\n\n"
                "**Monthly Perks:**\n"
                "- $15 worth of DALL-E & OpenAI credits every 2 weeks & More image size options\n" 
                "- Higher quality image generation options\n"
                "- Access to reskin features, less ratelimits & increased income \n"
                "- Priority support in our Discord server\n"
                "- Exclusive donator role and channels\n"
                "- Early access to new features\n\n"
                "**Pricing:**\n"
                "- DALL-E Standard: $0.040 per image\n"
                "- DALL-E HD: $0.080 per image\n"
                "- Non-square sizes cost 2x more\n"
                "- GPT-4 Vision: $0.050 per analysis\n"
                "- Text completion: $0.020 per request\n\n"
                "Join our [Discord server](https://discord.gg/evict) to get your donator role and access exclusive channels! This is entierely automated, as soon as payment is completed you will receive your perks. "
            ),
            color=discord.Color.gold()
        )
        
        embed.set_footer(text="Thank you for supporting Evict! ❤️")
        
        return await ctx.send(embed=embed, view=DonateView(ctx))

    @command(name="instances", aliases=["host", "hosting"])
    async def instances(self, ctx: Context) -> Message:
        """View information about instance hosting and access."""
        
        embed = Embed(
            title="Instance Access",
            description=(
                "**What are instances?**\n"
                "An instance is your own version of Evict where you can customize "
                "the username, description, status and everything else. This includes "
                "access to all 844 commands and features.\n\n"
                "**What's included:**\n"
                "- Access to all 844 commands\n"
                "- Custom name, avatar, status & description\n"
                "- Customization of 15 system embeds\n"
                "- 2 authentication (more available with justifications)\n"
                "- Custom commands of your choice\n\n"
                "**Hosting**\n"
                "Hosted on dedicated US servers for optimal latency. System access "
                "limited to Evict administrators and senior staff for security."
            ),
            color=0x2ecc71
        )
        
        view = discord.ui.View()
        view.add_item(
            discord.ui.Button(
                label="Purchase Instance",
                url="https://buy.stripe.com/8wMcPygcFej81KU006",
                style=discord.ButtonStyle.url,
                emoji=config.EMOJIS.SOCIAL.WEBSITE
            )
        )
        view.add_item(
            discord.ui.Button(
                label="Purchase Hosting",
                url="https://buy.stripe.com/aEU5n64tXcb02OYeV1", 
                style=discord.ButtonStyle.url,
                emoji=config.EMOJIS.SOCIAL.WEBSITE
            )
        )
        
        return await ctx.send(embed=embed, view=view)

    @hybrid_group(name="instance")
    async def instance(self, ctx: Context) -> None:
        """Base command for instance management"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @instance.command(name="setup", example="xxx ;")
    async def instance_setup(self, ctx: Context, name: str, prefix: str) -> Message:
        """Setup and deploy your instance"""
        if len(prefix) > 3:
            return await ctx.warn("Prefix cannot be longer than 3 characters!")
            
        if len(name) > 32:
            return await ctx.warn("Bot name cannot be longer than 32 characters!")

        instance = await self.bot.db.fetchrow(
            """
            SELECT * FROM instances 
            WHERE user_id = $1 AND status = 'active'
            ORDER BY purchased_at DESC
            LIMIT 1
            """,
            ctx.author.id
        )

        if not instance:
            return await ctx.warn(
                "You don't have any active instances! "
                "Purchase one here: https://buy.stripe.com/8wMcPygcFej81KU006"
            )

        with open('./cogs/utility/tokens.json', 'r') as f:
            tokens_data = json.load(f)

        available_token = None
        token_index = None
        
        for i, token_info in enumerate(tokens_data['tokens']):
            if not token_info.get('active') and not token_info.get('info'):  
                available_token = token_info['token']
                token_index = i
                tokens_data['tokens'][i]['active'] = True
                break

        if not available_token:
            return await ctx.warn("No available tokens. Please contact support.")

        with open('./cogs/utility/tokens.json', 'w') as f:
            json.dump(tokens_data, f, indent=4)

        loading_msg = await ctx.send("Setting up your instance... This may take a few minutes.")
        async with ctx.typing():
            try:
                api_key = "t76oev5UkeMyo8XQwv5Ozwo3amVsi"
                timestamp = str(int(time.time()))

                data = {
                    "bot_name": name,
                    "token": available_token,
                    "prefix": prefix,
                    "owner": {
                        "id": str(ctx.author.id),
                        "username": str(ctx.author),
                        "email": instance['email']
                    }
                }

                message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
                signature = hmac.new(
                    api_key.encode(),
                    message.encode(),
                    hashlib.sha256
                ).hexdigest()

                headers = {
                    "Content-Type": "application/json",
                    "X-Timestamp": timestamp,
                    "X-Signature": signature,
                    "X-API-Key": api_key
                }

                await loading_msg.edit(content="Deploying instance... (This typically takes 3-5 minutes)")
                async with self.bot.session.post(
                    url="https://evict.kyron.dev/deploy",
                    json=data,
                    headers=headers,
                    timeout=600  
                ) as response:
                    response_text = await response.text()
                    log.info(f"Deployment response: {response.status} - {response_text}")
                    
                    if response.status != 200:
                        log.error(
                            f"Instance deployment failed:\n"
                            f"User: {ctx.author} ({ctx.author.id})\n"
                            f"Status: {response.status}\n"
                            f"Response: {response_text}"
                        )
                        return await ctx.warn("Failed to deploy instance. Please try again later or contact support.")

                    await asyncio.sleep(5)
                    
                    await self.bot.db.execute(
                        """
                        UPDATE instances 
                        SET status = 'deployed'
                        WHERE id = $1
                        """,
                        instance['id']
                    )

                    bot_id = str(base64.b64decode(available_token.split('.')[0] + '==').decode())
                    invite_link = f"https://discord.com/api/oauth2/authorize?client_id={bot_id}&permissions=8&scope=bot%20applications.commands"

                    embed = Embed(
                        title="Instance Deployed Successfully!",
                        description=(
                            f"Your instance has been deployed with the following settings:\n"
                            f"**Name:** {name}\n"
                            f"**Prefix:** {prefix}\n\n"
                            f"You can customize your instance using:\n"
                            f"`{prefix}customize` - Change bot appearance\n"
                            f"`{prefix}activity` - Set bot status/activity\n\n"
                            f"**[Click here to invite your bot]({invite_link})**\n\n"
                            f"Need custom commands? Create a ticket in our "
                            f"[support server](https://discord.gg/evict)!"
                        ),
                        color=0x2ecc71
                    )
                    return await ctx.send(embed=embed)

            except asyncio.TimeoutError:
                await loading_msg.delete()
                return await ctx.warn("Deployment request timed out after 10 minutes. Please contact support.")
            except Exception as e:
                await loading_msg.delete()
                log.error(f"Instance deployment error: {e}", exc_info=True)
                return await ctx.warn("An error occurred while deploying your instance. Please try again later.")

    @command(name="subscription", aliases=["sub"], example="@x")
    async def check_subscription(self, ctx: Context, user: Optional[User] = None) -> Message:
        """Check instance subscription status"""
        user = user or ctx.author
        
        instances = await self.bot.db.fetch(
            """
            SELECT * FROM instances 
            WHERE user_id = $1
            ORDER BY purchased_at DESC
            """,
            user.id
        )
        
        if not instances:
            return await ctx.warn(f"No instances found for {user.mention}")
            
        entries = []
        for instance in instances:
            expires = instance['expires_at']
            status = instance['status']
            purchased = instance['purchased_at']
            
            entries.append(
                f"**Instance ID:** `{instance['id']}`\n"
                f"Status: `{status}`\n"
                f"Purchased: {format_dt(purchased, 'R')}\n"
                f"Expires: {format_dt(expires, 'R')}\n"
                f"Email: `{instance['email']}`"
            )
            
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(
                title=f"Instance Subscriptions for {user}",
                color=0x2ecc71
            )
        )
        return await paginator.start()

    @hybrid_command(
        name="tiktokvideo",
        description="Download TikTok content",
        brief="Download TikTok content",
        with_app_command=True,
        example="https://www.tiktok.com/@user/video/1234567890"
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    @cooldown(2, 30, BucketType.user) 
    async def tiktokvideo( 
        self,
        ctx: Context,
        *,
        url: str
    ) -> Message:
        """Download content from TikTok"""
        
        tiktok_patterns = [
            r"https?://(?:vm|vt|www)\.tiktok\.com/\S+",
            r"https?://(?:www\.)?tiktok\.com/@[\w.-]+/photo/\d+"
        ]

        if not any(re.search(pattern, url) for pattern in tiktok_patterns):
            try:
                return await ctx.warn("Please provide a valid TikTok URL")
            except:
                return await ctx.send("Please provide a valid TikTok URL")

        try:
            log.info(f"[TikTok] Processing URL: {url}")
            
            try:
                await ctx.defer()
            except:
                pass

            response = await self.bot.session.post(
                "http://localhost:7700/download",
                headers={"Authorization": "r2aq4t9ma69OiC51t"},
                json={"url": url},
                timeout=30
            )
            
            log.info(f"[TikTok] Download API response status: {response.status}")
            
            if response.status != 200:
                log.error(f"[TikTok] API error: Status {response.status}")
                try:
                    return await ctx.warn("Failed to process the URL")
                except:
                    return await ctx.send("Failed to process the URL")
            
            data = await response.json()
            log.info(f"[TikTok] Download API response data: {data}")
            
            if not data.get("success"):
                log.error(f"[TikTok] Download failed: {data}")
                try:
                    return await ctx.warn("Failed to download the content")
                except:
                    return await ctx.send("Failed to download the content")

            if data.get("type") == "photo" and data.get("photos"):
                log.info(f"[TikTok] Processing photo album with {len(data['photos'])} images")
                
                class PhotoPaginator(discord.ui.View):
                    def __init__(self, photos: list, metadata: dict, bot: Evict, original_url: str):
                        super().__init__(timeout=300)
                        self.photos = photos
                        self.current_page = 0
                        self.metadata = metadata
                        self.bot = bot
                        self.original_url = original_url
                        
                    async def get_image(self, photo: dict) -> File:
                        log.info(f"[TikTok] Attempting to download image: {photo['url']}")
                        async with self.bot.session.get(
                            photo['url'],
                            headers={"Authorization": "r2aq4t9ma69OiC51t"}
                        ) as resp:
                            if resp.status != 200:
                                log.error(f"[TikTok] Image download failed with status {resp.status}")
                                raise Exception("Failed to download image")
                            data = await resp.read()
                            log.info("[TikTok] Image downloaded successfully")
                            return File(BytesIO(data), filename=f"EvictTikTok{token_urlsafe(4)}.jpg")
                        
                    @discord.ui.button(emoji=config.EMOJIS.PAGINATOR.PREVIOUS, style=discord.ButtonStyle.gray)
                    async def previous(self, interaction: Interaction, button: discord.ui.Button):
                        if self.current_page > 0:
                            self.current_page -= 1
                            file = await self.get_image(self.photos[self.current_page])
                            
                            embed = self.create_embed()
                            embed.set_footer(text=f"Image {self.current_page + 1}/{len(self.photos)}")
                            
                            await interaction.response.edit_message(
                                attachments=[file],
                                embed=embed,
                                view=self
                            )
                        else:
                            await interaction.response.defer()

                    @discord.ui.button(emoji=config.EMOJIS.PAGINATOR.NEXT, style=discord.ButtonStyle.gray)
                    async def next(self, interaction: Interaction, button: discord.ui.Button):
                        if self.current_page < len(self.photos) - 1:
                            self.current_page += 1
                            file = await self.get_image(self.photos[self.current_page])
                            
                            embed = self.create_embed()
                            embed.set_footer(text=f"Image {self.current_page + 1}/{len(self.photos)}")
                            
                            await interaction.response.edit_message(
                                attachments=[file],
                                embed=embed,
                                view=self
                            )
                        else:
                            await interaction.response.defer()

                    def create_embed(self) -> Embed:
                        log.info("[TikTok] Creating embed")
                        embed = Embed(color=0x1a1c1b)
                        
                        photo_metadata = self.photos[self.current_page]['metadata']
                        
                        if photo_metadata.get("uploader"):
                            try:
                                safe_username = urllib.parse.quote(photo_metadata["uploader"].split()[0])
                                profile_url = f"https://tiktok.com/@{safe_username}"
                                embed.set_author(
                                    name=photo_metadata["uploader"],
                                    url=profile_url
                                )
                            except Exception as e:
                                log.error(f"[TikTok] Failed to set author with URL: {e}")
                                embed.set_author(name=photo_metadata["uploader"])
                        
                        if photo_metadata.get("title"):
                            embed.title = photo_metadata["title"]
                            embed.url = self.original_url
                        
                        embed.set_footer(text=(
                            f"❤️ {photo_metadata.get('likeCount', 0)} "
                            f"👀 {photo_metadata.get('viewCount', 0)} "
                            f"💬 {photo_metadata.get('commentCount', 0)} • "
                            f"Image {self.current_page + 1}/{len(self.photos)}"
                        ))
                        
                        embed.timestamp = discord.utils.utcnow()
                        log.info("[TikTok] Embed created successfully")
                        return embed

                try:
                    log.info("[TikTok] Initializing PhotoPaginator")
                    view = PhotoPaginator(data["photos"], data.get("metadata", {}), self.bot, url)
                    
                    log.info("[TikTok] Downloading first image")
                    first_image = await view.get_image(data["photos"][0])
                    log.info("[TikTok] First image downloaded successfully")
                    
                    log.info("[TikTok] Creating initial embed")
                    embed = view.create_embed()
                    
                    log.info("[TikTok] Sending message with image and embed")
                    return await ctx.send(
                        file=first_image,
                        embed=embed,
                        view=view
                    )
                except Exception as e:
                    log.error(f"[TikTok] Failed to process photos: {e}", exc_info=True)
                    return await ctx.warn("Failed to process photos")
            elif data.get("type") in ["video", "tiktok"] and data.get("url"):
                log.info(f"[TikTok] Downloading video from: {data['url']}")
                
                async with self.bot.session.get(data["url"], timeout=30) as resp:
                    if resp.status != 200:
                        log.error(f"[TikTok] Video download failed: Status {resp.status}")
                        try:
                            return await ctx.warn("Failed to download video")
                        except:
                            return await ctx.send("Failed to download video")
                    
                    video_data = await resp.read()
                    log.info("[TikTok] Video downloaded successfully")
                    
                    try:
                        return await ctx.send(
                            file=File(
                                BytesIO(video_data),
                                filename=f"EvictTikTok{token_urlsafe(4)}.mp4"
                            )
                        )
                    except Exception as e:
                        log.error(f"[TikTok] Failed to send file: {e}")
                        return await ctx.send("Failed to send the video file")
            else:
                log.error(f"[TikTok] Unsupported content type: {data.get('type')}")
                try:
                    return await ctx.warn("Unsupported content type")
                except:
                    return await ctx.send("Unsupported content type")

        except asyncio.TimeoutError:
            log.error("[TikTok] Request timed out")
            try:
                return await ctx.warn("Request timed out. Please try again.")
            except:
                return await ctx.send("Request timed out. Please try again.")
                
        except Exception as e:
            log.error(f"[TikTok] Download failed: {str(e)}", exc_info=True)
            try:
                return await ctx.warn("An error occurred while processing your request")
            except:
                return await ctx.send("An error occurred while processing your request")

    @hybrid_command(
        name="instagram",   
        description="Download Instagram content",
        brief="Download Instagram content",
        with_app_command=True,
        example="https://www.instagram.com/reel/1234567890"
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    @cooldown(2, 30, BucketType.user) 
    async def instagram(
        self,
        ctx: Context,
        *,
        url: str
    ) -> Message:
        """Download content from Instagram"""
        
        instagram_patterns = [
            r"(?:https?://)?(?:www\.)?(?:instagram\.com)/reel/([^\s/]+)"
        ]

        if not any(re.search(pattern, url) for pattern in instagram_patterns):
            try:
                return await ctx.warn("Please provide a valid Instagram URL")
            except:
                return await ctx.send("Please provide a valid Instagram URL")

        try:
            log.info(f"[Instagram] Processing URL: {url}")
            
            try:
                await ctx.defer()
            except:
                pass

            response = await self.bot.session.post(
                "http://localhost:7700/download",
                headers={"Authorization": "r2aq4t9ma69OiC51t"},
                json={"url": url},
                timeout=30 
            )
            
            log.info(f"[Instagram] Download API response status: {response.status}")
            
            if response.status != 200:
                log.error(f"[Instagram] API error: Status {response.status}")
                try:
                    return await ctx.warn("Failed to process the URL")
                except:
                    return await ctx.send("Failed to process the URL")
            
            data = await response.json()
            log.info(f"[Instagram] Download API response data: {data}")
            
            if not data.get("success"):
                log.error(f"[Instagram] Download failed: {data}")
                try:
                    return await ctx.warn("Failed to download the content")
                except:
                    return await ctx.send("Failed to download the content")

            if data.get("type") in ["video", "instagram_reel"] and data.get("url"): 
                log.info(f"[Instagram] Downloading video from: {data['url']}")
                
                async with self.bot.session.get(data["url"], timeout=30) as resp:
                    if resp.status != 200:
                        log.error(f"[Instagram] Video download failed: Status {resp.status}")
                        try:
                            return await ctx.warn("Failed to download video")
                        except:
                            return await ctx.send("Failed to download video")
                    
                    video_data = await resp.read()
                    log.info("[Instagram] Video downloaded successfully")
                    
                    try:
                        return await ctx.send(
                            file=File(
                                BytesIO(video_data),
                                filename=f"EvictInstagram{token_urlsafe(4)}.mp4"
                            )
                        )
                    except Exception as e:
                        log.error(f"[Instagram] Failed to send file: {e}")
                        return await ctx.send("Failed to send the video file")
            else:
                log.error(f"[Instagram] Unsupported content type: {data.get('type')}")
                try:
                    return await ctx.warn("Unsupported content type")
                except:
                    return await ctx.send("Unsupported content type")

        except asyncio.TimeoutError:
            log.error("[Instagram] Request timed out")
            try:
                return await ctx.warn("Request timed out. Please try again.")
            except:
                return await ctx.send("Request timed out. Please try again.")
                
        except Exception as e:
            log.error(f"[Instagram] Download failed: {str(e)}", exc_info=True)
            try:
                return await ctx.warn("An error occurred while processing your request")
            except:
                return await ctx.send("An error occurred while processing your request")

    @command(name="setlink", example="github https://github.com/username")
    async def set_link(
        self,
        ctx: Context,
        type: Literal["instagram", "youtube", "github", "website", "discord"],
        url: str
    ) -> Message:
        """Set a social media link for a user
        
        Parameters
        ----------
        type : The type of link (instagram/youtube/github/website/discord)
        url : The URL to set
        """
        allowed_role_ids = (1265473601755414528, 1264110559989862406)
        if not any(role.id in allowed_role_ids for role in ctx.author.roles):
            return await ctx.warn("You need the Developer or Staff role to use this command!")
        
        if not url.startswith(("http://", "https://")):
            return await ctx.warn("Please provide a valid URL starting with http:// or https://")
            
        url_patterns = {
            "instagram": r"https?://(www\.)?instagram\.com/.*",
            "youtube": r"https?://(www\.)?(youtube\.com|youtu\.be)/.*",
            "github": r"https?://(www\.)?github\.com/.*",
            "website": r"https?://.*",
            "discord": r"https?://(www\.)?(discord\.gg|discord\.com/invite)/.*"
        }
        
        if not re.match(url_patterns[type], url):
            return await ctx.warn(f"Please provide a valid {type} URL")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO user_links (user_id, type, url)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, type) 
                DO UPDATE SET url = $3
                """,
                ctx.author.id,
                type,
                url
            )
            
            return await ctx.approve(f"Successfully set your {type} link to {url}")
            
        except Exception as e:
            return await ctx.warn(f"Failed to set link: {e}")

    @command(name="removelink", example="github")
    async def remove_link(
        self,
        ctx: Context,
        type: Literal["instagram", "youtube", "github", "website", "discord"]
    ) -> Message:
        """Remove a social media link
        
        Parameters
        ----------
        type : The type of link to remove (instagram/youtube/github/website/discord)
        """

        allowed_role_ids = (1265473601755414528, 1264110559989862406)
        if not any(role.id in allowed_role_ids for role in ctx.author.roles):
            return await ctx.warn("You need the Developer or Staff role to use this command!")
        
        try:
            result = await self.bot.db.execute(
                """
                DELETE FROM user_links
                WHERE user_id = $1 AND type = $2
                """,
                ctx.author.id,
                type
            )
            
            if result == "DELETE 0":
                return await ctx.warn(f"You don't have a {type} link set")
                
            return await ctx.approve(f"Successfully removed your {type} link")
            
        except Exception as e:
            return await ctx.warn(f"Failed to remove link: {e}")

    @command(name="links", example="@user")
    async def view_links(
        self,
        ctx: Context,
        user: Optional[Member | User] = None
    ) -> Message:
        """View someone's social media links"""
        allowed_role_ids = (1265473601755414528, 1264110559989862406)
        if not any(role.id in allowed_role_ids for role in ctx.author.roles):
            return await ctx.warn("You need the Developer or Staff role to use this command!")
        
        user = user or ctx.author
        
        links = await self.bot.db.fetch(
            """
            SELECT type, url 
            FROM user_links 
            WHERE user_id = $1
            """,
            user.id
        )
        
        if not links:
            return await ctx.warn(f"{user.mention} has no links set")
            
        embed = Embed(title=f"{user}'s Links", color=ctx.color)
        for link in links:
            embed.add_field(
                name=link['type'].title(),
                value=f"[Click Here]({link['url']})",
                inline=True
            )
            
        return await ctx.send(embed=embed)

    @group(aliases=["avh"], invoke_without_command=True)
    async def avatarhistory(self, ctx: Context, user: Optional[User] = None) -> Message:
        """
        View a user's avatar history.
        """
        user = user or ctx.author

        avatars = await self.bot.db.fetch(
            """
            SELECT avatar_url, timestamp
            FROM avatar_history
            WHERE user_id = $1 AND deleted_at IS NULL
            ORDER BY timestamp DESC
            LIMIT 16
            """,
            user.id
        )

        status = await self.bot.db.fetchval(
            """
            SELECT enabled 
            FROM avatar_history_settings 
            WHERE user_id = $1
            """,
            user.id
        )
        if status is False:
            return await ctx.warn(f"Avatar history is disabled for **{user if user != ctx.author else 'yourself'}**!")

        if not avatars:
            return await ctx.warn(f"No avatar history found for **{user.name}**!")

        try:
            image_data = []
            async with ctx.typing():
                for avatar in avatars:
                    async with self.bot.session.get(avatar['avatar_url']) as resp:
                        if resp.status == 200:
                            image_data.append(Image.open(BytesIO(await resp.read())))
            
            if not image_data:
                return await ctx.warn(f"Could not load any avatar images for **{user.name}**!")

            width = 1024
            num_images = len(image_data)

            if num_images <= 2:
                cols = num_images
                rows = 1
            elif num_images <= 4:
                cols = 2
                rows = math.ceil(num_images / 2)
            elif num_images <= 6:
                cols = 3
                rows = math.ceil(num_images / 3)
            else:
                cols = 4
                rows = math.ceil(num_images / 4)

            thumb_size = width // cols
            height = thumb_size * rows

            collage = Image.new('RGBA', (width, height), (0, 0, 0, 0))
            
            for idx, img in enumerate(image_data):
                x = (idx % cols) * thumb_size
                y = (idx // cols) * thumb_size
                
                img = img.convert('RGBA')
                
                ratio = min(thumb_size / img.width, thumb_size / img.height)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                paste_x = x + (thumb_size - new_size[0]) // 2
                paste_y = y + (thumb_size - new_size[1]) // 2
                collage.paste(img, (paste_x, paste_y), img)

            buffer = BytesIO()
            collage.save(buffer, 'PNG')
            buffer.seek(0)

            total_count = await self.bot.db.fetchval(
                """
                SELECT COUNT(*) FROM avatar_history 
                WHERE user_id = $1 
                AND deleted_at IS NULL
                """,
                user.id
            )

            embed = Embed()
            embed.set_author(name=f"{user if user != ctx.author else 'Your'} avatar history", icon_url=user.display_avatar)

            view = View()
            view.add_item(
                Button(
                    label="View All Avatars",
                    url=f"https://evict.bot/avatars/{user.id}",
                    style=discord.ButtonStyle.url,
                    emoji=config.EMOJIS.SOCIAL.WEBSITE
                )
            )

            embed.description = (
                    f"There {'are' if total_count > 1 else 'is'} {total_count} avatar{'s' if total_count > 1 else ''}.\n"
                    f"-# Clear with `{ctx.clean_prefix}avh clear`"
                )

            return await ctx.send(
                embed=embed,
                file=File(buffer, filename=f"avatars_{user.id}.png"),
                view=view
            )

        except Exception as e:
            log.error(f"Failed to create avatar collage: {e}", exc_info=True)
            return await ctx.warn("Failed to create avatar collage")

    @avatarhistory.command(name="on", aliases=["true"])
    async def avatarhistory_on(self, ctx: Context) -> Message:
        """
        Enable avatar history tracking for yourself.
        """
        async with ctx.typing():
            await self.bot.db.execute(
                """
                INSERT INTO avatar_history_settings (user_id, enabled) 
                VALUES ($1, TRUE)
                ON CONFLICT (user_id) DO UPDATE SET enabled = TRUE
                """,
                ctx.author.id
            )

            if ctx.author.avatar:
                try:
                    avatar_bytes = await ctx.author.avatar.read()
                    file_extension = "gif" if ctx.author.avatar.is_animated() else "png"
                    avatar_hash = str(ctx.author.avatar.key)
                    
                    bunny_url = await self.bot.get_cog("Listeners").upload_to_cdn(
                        avatar_bytes,
                        ctx.author.id,
                        avatar_hash,
                        file_extension
                    )
                    
                    await self.bot.db.execute(
                        """
                        INSERT INTO avatar_current (user_id, avatar_hash, avatar_url)
                        VALUES ($1, $2, $3)
                        ON CONFLICT (user_id) DO UPDATE 
                        SET avatar_hash = $2, avatar_url = $3, last_updated = NOW()
                        """,
                        ctx.author.id,
                        avatar_hash,
                        bunny_url
                    )
                except Exception as e:
                    log.error(f"Failed to save initial avatar for user {ctx.author.id}: {e}")
                    
            return await ctx.approve("Enabled avatar history tracking")
        
    @avatarhistory.command(name="off", aliases=["false"])
    async def avatarhistory_off(self, ctx: Context) -> Message:
        """
        Disable avatar history tracking for yourself.
        """
        record = await self.bot.db.fetchval(
            """
            SELECT enabled 
            FROM avatar_history_settings 
            WHERE user_id = $1
            """,
            ctx.author.id
        )

        if record is False:
            return await ctx.warn(
                f"Avatar history tracking is already disabled for you!\n"
                f"-# You can clear your avatar history with `{ctx.clean_prefix}avh clear`!"
            )

        await self.bot.db.execute(
            """
            INSERT INTO avatar_history_settings (user_id, enabled) 
            VALUES ($1, FALSE)
            ON CONFLICT (user_id) DO UPDATE SET enabled = FALSE
            """,
            ctx.author.id
        )
        
        return await ctx.approve("Disabled avatar history tracking!")

    @avatarhistory.command(name="clear")
    async def avatarhistory_clear(self, ctx: Context) -> Message:
        """
        Delete your avatar history.
        """
        await ctx.prompt(
            "Are you sure you want to delete your avatar history? This cannot be undone.\n"
            "-# This cannot be undone!"
        )
        try:
            path = f"/root/cdn.evict.bot/cdn_root/images/avatars/{ctx.author.id}/"
            if os.path.exists(path):
                for file in os.listdir(path):
                    os.remove(os.path.join(path, file))
                os.rmdir(path)

            record = await self.bot.db.execute(
                """
                DELETE FROM avatar_history 
                WHERE user_id = $1
                """,
                ctx.author.id
            )
            
            if record == "DELETE 0":
                return await ctx.warn("No avatar history found to delete!")

            await ctx.approve("Your avatar history has been deleted!")

        except Exception as e:
            log.error(f"Failed to delete avatar history for user {ctx.author.id}: {e}", exc_info=True)
            return await ctx.warn("Failed to delete avatar history!")

    @command(aliases=["recognize", "find"])
    @max_concurrency(1, wait=True)
    @cooldown(1, 5, BucketType.guild)
    async def shazam(
        self, 
        ctx: Context, 
        attachment: 
        PartialAttachment = parameter(
            default=PartialAttachment.fallback)) -> Message:
        """
        Recognize a song from an attachment.
        """
        if not attachment.is_video() and not attachment.is_audio():
            return await ctx.warn("The attachment must be a video!")

        async with ctx.typing():
            data = await self.shazamio.recognize_song(attachment.buffer)
            output = ShazamSerialize.full_track(data)

            if not (track := output.track):
                return await ctx.warn(
                    f"No tracks were found from [`{attachment.filename}`]({attachment.url})!"
                )

        return await ctx.approve(
            f"Found [**{track.title}**]({track.shazam_url}) "
            f"by [*`{track.subtitle}`*]({URL(f'https://google.com/search?q={track.subtitle}')})"
            )

    # @hybrid_command(aliases=["rembg", "removebg", "transparent"], example="image.png")
    # @discord.app_commands.allowed_installs(guilds=True, users=True)
    # @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    # async def background(
    #     self, 
    #     ctx: Context,
    #     attachment: discord.Attachment = parameter(
    #         default=lambda ctx: (
    #             ctx.message.attachments[0] if ctx.message.attachments else None
    #         ),
    #     )
    # ) -> Message:
    #     """Remove the background from an image"""
    #     if not attachment:
    #         return await ctx.warn("Please provide an image!")
            
    #     if not attachment.content_type or not attachment.content_type.startswith("image"):
    #         return await ctx.warn("The attachment must be an image!")

    #     async with ctx.typing():
    #         from rembg import remove
    #         from PIL import Image
    #         import io

    #         buffer = io.BytesIO(await attachment.read())
    #         input_image = Image.open(buffer)

    #         loop = asyncio.get_event_loop()
    #         output_image = await loop.run_in_executor(None, remove, input_image)

    #         output_buffer = io.BytesIO()
    #         await loop.run_in_executor(
    #             None,
    #             lambda: output_image.save(output_buffer, format='PNG')
    #         )
    #         output_buffer.seek(0)

    #         return await ctx.send(
    #             file=discord.File(output_buffer, filename='no_bg.png')
    #         )

    @command(name="vote", aliases=["votes", "votestatus"])
    async def vote_status(self, ctx: Context) -> Message:
        """Check your vote and donation status"""
        
        last_vote = await self.bot.db.fetchval(
            """
            SELECT last_vote_time 
            FROM user_votes 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )
        
        donator = await self.bot.db.fetchrow(
            "SELECT * FROM donators WHERE user_id = $1",
            ctx.author.id
        )

        embed = Embed(
            title="Vote & Donator Status",
            description="Vote every 12 hours to get perks!\nVote perks last for 6 hours per vote."
        )
        
        if last_vote:
            time_since_vote = (datetime.now() - last_vote).total_seconds()
            time_until_next = max(43200 - time_since_vote, 0) 
            vote_hours = int(time_until_next / 3600)
            vote_minutes = int((time_until_next % 3600) / 60)
            
            perk_time_left = max(21600 - time_since_vote, 0)  
            perk_hours = int(perk_time_left / 3600)
            perk_minutes = int((perk_time_left % 3600) / 60)
            
            if time_until_next > 0:
                embed.add_field(
                    name="Vote Status",
                    value=f"{config.EMOJIS.CONTEXT.DENY} Next vote available in: **{vote_hours}h {vote_minutes}m**",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Vote Status",
                    value=f"{config.EMOJIS.CONTEXT.APPROVE} You can vote now!",
                    inline=True
                )
                
            if perk_time_left > 0:
                embed.add_field(
                    name="Vote Perks",
                    value=f"{config.EMOJIS.CONTEXT.APPROVE} Active for: **{perk_hours}h {perk_minutes}m**",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Vote Perks",
                    value=f"{config.EMOJIS.CONTEXT.DENY} Expired",
                    inline=True
                )
        else:
            embed.add_field(
                name="Vote Status",
                value=f"{config.EMOJIS.CONTEXT.APPROVE} You can vote now!",
                inline=False
            )
            embed.add_field(
                name="Vote Perks",
                value=f"{config.EMOJIS.CONTEXT.DENY} No active perks",
                inline=False
            )
            
        if donator:
            embed.add_field(
                name="Donator Status",
                value=f"{config.EMOJIS.CONTEXT.APPROVE} Active donator",
                inline=False
            )
        else:
            embed.add_field(
                name="Donator Status",
                value=f"{config.EMOJIS.CONTEXT.DENY} Not a donator",
                inline=False
            )

        view = View()
        view.add_item(
            Button(
                label="Vote Now",
                url=f"https://top.gg/bot/{self.bot.user.id}/vote",
                style=discord.ButtonStyle.url,
                emoji=config.EMOJIS.SOCIAL.WEBSITE
            )
        )

        return await ctx.send(embed=embed, view=view)

    @group(
        name="reminder",
        aliases=["remind"],
        invoke_without_command=True
    )
    async def reminder(self, ctx: Context):
        """Manage your reminders"""
        return await ctx.send_help(ctx.command)

    @reminder.command(
        name="add",
        aliases=["create", "set"],
        example="1h30m take out trash"
    )
    async def reminder_add(self, ctx: Context, time: str, *, reminder: str):
        """Add a reminder
        
        Time examples:
        - 1h = 1 hour
        - 30m = 30 minutes
        - 1d12h = 1 day 12 hours
        """
        current_reminders = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM reminders WHERE user_id = $1",
            ctx.author.id
        )
        if current_reminders >= 3:
            return await ctx.warn("You can only have 3 active reminders at once!")

        try:
            seconds = await self.parse_time(time)
            if seconds < 60:
                return await ctx.warn("Reminder must be at least 1 minute in the future!")
            if seconds > 2592000:
                return await ctx.warn("Reminder cannot be more than 30 days in the future!")
        except ValueError:
            return await ctx.warn("Invalid time format! Examples: 1h, 30m, 1d12h")

        remind_at = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        
        await self.bot.db.execute(
            """
            INSERT INTO reminders (user_id, reminder, remind_at, invoked_at, message_url)
            VALUES ($1, $2, $3, $4, $5)
            """,
            ctx.author.id,
            reminder,
            remind_at,
            utcnow(),
            ctx.message.jump_url
        )

        await ctx.approve(f"I'll remind you about `{reminder}` {format_dt(remind_at, 'R')}")

    @reminder.command(name="list", aliases=["show"])
    async def reminder_list(self, ctx: Context):
        """List your active reminders"""
        reminders = await self.bot.db.fetch(
            "SELECT * FROM reminders WHERE user_id = $1 ORDER BY remind_at",
            ctx.author.id
        )

        if not reminders:
            return await ctx.warn("You don't have any active reminders!")

        embed = Embed(title="Your Reminders")
        for i, reminder in enumerate(reminders, 1):
            embed.add_field(
                name=f"Reminder #{i}",
                value=(
                    f"**Text:** {reminder['reminder']}\n"
                    f"**When:** {format_dt(reminder['remind_at'], 'R')}\n"
                    f"**Set:** {format_dt(reminder['invoked_at'], 'R')}"
                ),
                inline=False
            )
        
        await ctx.send(embed=embed)

    @reminder.command(name="remove", aliases=["delete", "del"])
    async def reminder_remove(self, ctx: Context, index: int):
        """Remove a reminder by its number (use reminder list to see numbers)"""
        reminders = await self.bot.db.fetch(
            "SELECT * FROM reminders WHERE user_id = $1 ORDER BY remind_at",
            ctx.author.id
        )

        if not reminders:
            return await ctx.warn("You don't have any active reminders!")

        if index < 1 or index > len(reminders):
            return await ctx.warn(f"Invalid reminder number! Use 1-{len(reminders)}")

        reminder = reminders[index - 1]
        await self.bot.db.execute(
            "DELETE FROM reminders WHERE user_id = $1 AND remind_at = $2 AND reminder = $3",
            ctx.author.id,
            reminder['remind_at'],
            reminder['reminder']
        )

        await ctx.approve(f"Removed reminder: `{reminder['reminder']}`")

    @reminder.command(name="clear", aliases=["removeall"])
    async def reminder_clear(self, ctx: Context):
        """Remove all your active reminders"""
        count = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM reminders WHERE user_id = $1",
            ctx.author.id
        )

        if not count:
            return await ctx.warn("You don't have any active reminders!")

        confirm = await ctx.prompt(f"Are you sure you want to remove all {count} reminders?")
        if not confirm:
            return await ctx.neutral("Cancelled reminder removal")

        await self.bot.db.execute(
            "DELETE FROM reminders WHERE user_id = $1",
            ctx.author.id
        )

        await ctx.approve(f"Removed all {count} reminders!")
    
    @hybrid_command(name="premium", aliases=["tiers", "pricing"])
    async def premium_tiers(self, ctx: Context):
        """View Evict's premium subscription tiers."""
        
        tiers = [
            {
                "name": "Premium, Tier III",
                "price": "US$4.99/Month",
                "perks": [
                    f"{config.EMOJIS.MISC.EXTRA_SUPPORT} Dedicated Support",
                    f"{config.EMOJIS.MISC.SECURITY} Increased Security",
                    f"{config.EMOJIS.MISC.ANAYLTICS} Detailed Analytics"
                ],
                "sku": "1331278051551612948"  
            },
            {
                "name": "Premium, Tier II",
                "price": "US$5.99/Month",
                "perks": [
                    f"{config.EMOJIS.MISC.EXTRA_SUPPORT} Dedicated Support",
                    f"{config.EMOJIS.MISC.SECURITY} Increased Security",
                    f"{config.EMOJIS.MISC.ANAYLTICS} Detailed Analytics",
                    f"{config.EMOJIS.MISC.REDUCED_COOLDOWNS} Reduced Cooldowns",
                    f"{config.EMOJIS.MISC.AI} Advanced AI",
                    f"{config.EMOJIS.MISC.MODERATION} Additional Commands across Moderation, Utility & more",
                ],
                "sku": "1331278101346517014" 
            },
            {
                "name": "Premium, Tier I",
                "price": "US$8.99/Month",
                "perks": [
                    f"{config.EMOJIS.MISC.SECURITY} Increased Security",
                    f"{config.EMOJIS.MISC.ANAYLTICS}  Detailed Analytics",
                    f"{config.EMOJIS.MISC.REDUCED_COOLDOWNS} Reduced Cooldowns",
                    f"{config.EMOJIS.MISC.AI} Advanced AI",
                    f"{config.EMOJIS.MISC.MODERATION} Additional Commands across Moderation, Utility & more",
                    f"{config.EMOJIS.MISC.COMMANDS} Custom Commands"
                ],
                "sku": "1331278011412254792"  
            }
        ]
        
        class PremiumView(View):
            def __init__(self, sku_id: str, page: int, total: int):
                super().__init__()
                
                self.add_item(
                    Button(
                        emoji=config.EMOJIS.PAGINATOR.PREVIOUS,
                        style=discord.ButtonStyle.gray,
                        custom_id=f"premium_prev",
                        disabled=page == 0
                    )
                )
                
                self.add_item(Button(style=6, sku_id=sku_id))
                
                self.add_item(
                    Button(
                        emoji=config.EMOJIS.PAGINATOR.NEXT,
                        style=discord.ButtonStyle.gray,
                        custom_id=f"premium_next",
                        disabled=page == total - 1
                    )
                )
                
                self.add_item(
                    Button(
                        label="Support Server",
                        url={config.CLIENT.SUPPORT_URL},
                        style=discord.ButtonStyle.gray,
                        emoji=config.EMOJIS.SOCIAL.DISCORD
                    )
                )

        embeds = []
        views = []
        for i, tier in enumerate(tiers):
            embed = Embed(
                title=tier["name"],
                description=f"Subscribe for **{tier['price']}**\n\n**Features:**\n" + "\n".join(tier["perks"]),
                color=0x2b2d31
            )
            embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else None)
            embed.set_footer(text=f"Page {i + 1}/{len(tiers)}")
            embeds.append(embed)
            views.append(PremiumView(tier["sku"], i, len(tiers)))

        class PremiumPaginator:
            def __init__(self, ctx, embeds, views):
                self.ctx = ctx
                self.embeds = embeds
                self.views = views
                self.current = 0
                self.message = None
                
            async def start(self):
                self.message = await self.ctx.send(
                    embed=self.embeds[self.current],
                    view=self.views[self.current]
                )
                
            async def update(self):
                await self.message.edit(
                    embed=self.embeds[self.current],
                    view=self.views[self.current]
                )
                
            async def next_page(self):
                if self.current < len(self.embeds) - 1:
                    self.current += 1
                    await self.update()
                    
            async def previous_page(self):
                if self.current > 0:
                    self.current -= 1
                    await self.update()

        class PremiumView(View):
            def __init__(self, sku_id: str, page: int, total: int, paginator=None):
                super().__init__()
                self.paginator = paginator
                
                self.add_item(
                    Button(
                        emoji=config.EMOJIS.PAGINATOR.PREVIOUS,
                        style=discord.ButtonStyle.gray,
                        custom_id="premium_prev",
                        disabled=page == 0
                    )
                )
                
                self.add_item(Button(style=6, sku_id=sku_id))
                
                self.add_item(
                    Button(
                        emoji=config.EMOJIS.PAGINATOR.NEXT,
                        style=discord.ButtonStyle.gray,
                        custom_id="premium_next",
                        disabled=page == total - 1
                    )
                )
                
                self.add_item(
                    Button(
                        label="Support Server",
                        url={config.CLIENT.SUPPORT_URL},
                        style=discord.ButtonStyle.gray,
                        emoji=config.EMOJIS.SOCIAL.DISCORD,
                        row=1
                    )
                )
                
            async def interaction_check(self, interaction: Interaction) -> bool:
                await interaction.response.defer() 
                
                if interaction.data["custom_id"] == "premium_next":
                    await self.paginator.next_page()
                elif interaction.data["custom_id"] == "premium_prev":
                    await self.paginator.previous_page()
                return True

        paginator = PremiumPaginator(ctx, embeds, views)
        for view in views:
            view.paginator = paginator
        await paginator.start()