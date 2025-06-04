import io
import random
import time
import typing
from datetime import datetime
from discord import ui
import sympy as sp
import random
import requests
import aiohttp
import asyncio
import yt_dlp as youtube_dl
import os
from discord.ui import Modal, TextInput, Button
import arrow
import discord
from discord.ext import commands, tasks
from discord.ext.commands import Cog
from collections import defaultdict
from asyncio import Lock, sleep
from datetime import timedelta
from typing import Optional, Literal

# from tool.important.services import TTS
from tool.processing import FileProcessing
from tool.important import Context  # type: ignore
from typing import Union
from discord import PartialEmoji
import cairosvg
from datetime import datetime, timedelta
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import re
import urllib.parse
from googleapiclient.discovery import build
from google.oauth2 import service_account
import socket
import dns.resolver
from base64 import b64encode
import json
from loguru import logger
from cashews import cache


def generate(img: bytes) -> bytes:
    return cairosvg.svg2png(bytestring=img)


if typing.TYPE_CHECKING:
    from tool.greed import Greed  # type: ignore
from pydantic import BaseModel

DEBUG = True
cache.setup("mem://")
eros_key = "c9832179-59f7-477e-97ba-dca4a46d7f3f"


@cache(ttl=300, key="donator:{user_id}")
async def get_donator(ctx: Context, user_id: int) -> bool:
    """Check if a user is a donator through top.gg votes or server boosters.

    Args:
        ctx: Command context
        user_id: Discord user ID to check

    Returns:
        bool: True if user is a donator, False otherwise
    """
    try:
        if await ctx.bot.db.fetchval(
            "SELECT 1 FROM boosters WHERE user_id = $1", user_id
        ):
            return True

        async with ctx.bot.session.get(
            f"https://top.gg/api/bots/{ctx.bot.user.id}/check",
            params={"userId": user_id},
            headers={
                "Authorization": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IjExNDk1MzU4MzQ3NTY4NzQyNTAiLCJib3QiOnRydWUsImlhdCI6MTczODEzODM1MH0.HQRfKRPwsZ6RlPuXWyt7pK2tEwYGgZI22_YwulNdt8I"
            },
            timeout=3.0,
        ) as response:
            if response.status == 200:
                data = await response.json()
                if data.get("voted", 0) == 1:
                    return True

    except asyncio.TimeoutError:
        logger.warning(f"Timeout checking top.gg vote status for user {user_id}")
    except Exception as e:
        logger.error(f"Error checking donator status for user {user_id}: {e}")

    return False


class ValorantProfile(BaseModel):
    account_level: Optional[int] = None
    avatar_url: Optional[str] = None
    current_rating: Optional[str] = None
    damage_round_ratio: Optional[float] = None
    deaths: Optional[int] = None
    headshot_percent: Optional[float] = None
    kd_ratio: Optional[float] = None
    kills: Optional[int] = None
    last_update: Optional[int] = None
    lost: Optional[int] = None
    matches_played: Optional[int] = None
    name: Optional[str] = None
    peak_rating_act: Optional[str] = None
    peak_rating: Optional[str] = None
    puuid: Optional[str] = None
    region: Optional[str] = None
    tag: Optional[str] = None
    win_percent: Optional[float] = None
    wins: Optional[int] = None

    async def to_embed(self, ctx: Context) -> discord.Embed:
        embed = discord.Embed(
            color=ctx.bot.color,
            title=f"{self.name}#{self.tag}",
            url=f"https://eros.rest/valorant?user={self.name}&tag={self.tag}",
        )
        embed.add_field(
            name="MMR",
            value=f"""**Current Rank:** {self.current_rating}\n**Peak:** {self.peak_rating}\n**Peak Act:** {self.peak_rating_act}""",
            inline=True,
        )
        embed.add_field(
            name="Stats",
            value=f"""**KDR:** {str(self.kd_ratio)[2]}\n**WR:** {str(self.wr_ratio)[2]}\n**HSR:** {str(self.hs_ratio)[2]}\n""",
            inline=True,
        )
        embed.set_thumbnail(url=self.avatar_url)
        embed.set_footer(
            text=f"Region: {self.region} | Matches: {self.matches_played} | DPR: {int(self.damage_round_ratio)}"
        )
        return embed

    @classmethod
    async def from_snowflake(cls, user: str, tag: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://eros.rest/valorant",
                params={"user": user, "tag": tag},
                headers={"api-key": eros_key},
            ) as response:
                data = await response.read()
        return cls.parse_raw(data)  # type: ignore


# class ValorantUser(commands.Converter):
#     async def convert(self, ctx: Context, argument: str):  # type: ignore
#         if "#" not in argument:
#             raise commands.CommandError(
#                 "please include a `#` inbetween the user and tag"
#             )
#         return argument.split("#")


snipe_message_author = {}
snipe_message_content = {}
snipe_message_attachment = {}
snipe_message_author_avatar = {}
snipe_message_time = {}
snipe_message_sticker = {}
snipe_message_embed = {}


# from tool import valorant  # noqa: E402
class ReviveMessageView(ui.View):
    def __init__(self, message_content, guild_id, is_embed, cog):
        super().__init__()
        self.message_content = message_content
        self.guild_id = guild_id
        self.is_embed = is_embed
        self.cog = cog

    @ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: ui.Button):
        # Update the message in the database
        await self.cog.bot.db.execute(
            "INSERT INTO revive (guild_id, message, is_embed) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id) DO UPDATE SET message = $2, is_embed = $3",
            self.guild_id,
            self.message_content,
            self.is_embed,
        )

        # Update the interaction message
        await interaction.response.edit_message(
            content="✅ Revive message has been updated.", view=None
        )

    @ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: ui.Button):
        # Update the interaction message to indicate decline
        await interaction.response.edit_message(
            content="❌ You have declined this message.", view=None
        )



FONT_PATH = "fonts/NotoColorEmoji.ttf"  # Ensure you have this font file

class EmojiKitchen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def render_emoji(self, emoji):
        """Converts an emoji to a PNG image dynamically using Noto Emoji Font."""
        font_size = 128
        image_size = (font_size, font_size)

        # Create a blank image with transparency
        img = Image.new("RGBA", image_size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Load the emoji font
        if not os.path.exists(FONT_PATH):
            raise FileNotFoundError("NotoColorEmoji.ttf font file is missing!")

        font = ImageFont.truetype(FONT_PATH, font_size)

        # Center the emoji
        text_width, text_height = draw.textsize(emoji, font=font)
        position = ((image_size[0] - text_width) // 2, (image_size[1] - text_height) // 2)

        # Draw the emoji
        draw.text(position, emoji, font=font, fill=(255, 255, 255, 255))

        return img


class Miscellaneous(Cog):
    def __init__(self, bot: "Greed") -> None:
        self.bot = bot
        self.color = self.bot.color
        self.bot.afks = {}
        self.locks = {}
        self.revive_loops = {}  # Store tasks for each guild
        self.revive_tasks = {}  # Store task objects to manage looping tasks
        self.nsfw_domains = [
            "pornhub.com",
            "xvideos.com",
            "xhamster.com",
            "redtube.com",
            "tube8.com",
            "youporn.com",
            "spankwire.com",
            "tnaflix.com",
            "sex.com",
            "bangbros.com",
            # Add any other domains you'd like to block
        ]

        self.file_processor = FileProcessing(self.bot)
        self.queue = defaultdict(Lock)
        self.uwu_queue = defaultdict(list)  # New: Queue for uwu messages
        self.check_reminds.start()
        self.process_uwu_queue.start()  # New: Start the uwu queue processor

    async def cog_load(self):
        await self.bot.db.execute(
            """CREATE TABLE IF NOT EXISTS reminders (
            user_id BIGINT,
            guild_id BIGINT,
            channel_id BIGINT,
            reminder TEXT,
            time TIMESTAMP
            );"""
        )

    def cog_unload(self):
        self.check_reminds.cancel()
        self.process_uwu_queue.cancel()

    # @tasks.loop(minutes = 10)
    # async def auto_destroy(self):
    #     for client in self.bot.voice_clients:
    #         if client.channel and len(client.channel.members) < 2:
    #             try:
    #                 await client.destroy()
    #             except:
    #                 await client.disconnect()

    @tasks.loop(seconds=7200)
    async def revive_task(self):
        """Repeatedly call send_message for all guilds with enabled revive tasks."""
        for guild_id in self.revive_loops:
            guild = self.bot.get_guild(guild_id)
            if guild:
                await self.send_message(guild)

    async def notify_owner(self, ctx, command_name):
        """Notify the server owner that a command was used."""
        server_owner = ctx.guild.owner
        user = ctx.author

        if server_owner:
            try:
                embed = discord.Embed(
                    title="Command Used Notification",
                    description=f"An admin only command (`{command_name}`) was used.",
                    color=self.bot.color,
                )
                embed.add_field(
                    name="User",
                    value=f"{user.mention} ({user.name}#{user.discriminator})",
                )
                embed.add_field(name="User ID", value=user.id)
                embed.set_thumbnail(url=user.avatar.url)
                embed.add_field(name="Command", value=command_name)
                embed.set_footer(
                    text=f"Server: {ctx.guild.name} | Server ID: {ctx.guild.id}"
                )

                await server_owner.send(embed=embed)
            except Exception as e:
                await ctx.fail(
                    "Could not notify the server owner. Ensure their DMs are open."
                )

    @tasks.loop(seconds=10)
    async def check_reminds(self):
        try:
            BATCH_SIZE = 10
            total_processed = 0

            while True:
                reminds = await self.bot.db.fetch(
                    "SELECT * FROM reminders WHERE time < $1 LIMIT $2",
                    datetime.utcnow(),
                    BATCH_SIZE,
                )

                if not reminds:
                    break

                for i in range(0, len(reminds), 5):
                    chunk = reminds[i : i + 5]

                    for remind in chunk:
                        try:
                            user = await self.bot.fetch_user(remind["user_id"])
                            channel = self.bot.get_channel(remind["channel_id"])

                            if channel:
                                view = discord.ui.View()
                                view.add_item(
                                    discord.ui.Button(
                                        style=discord.ButtonStyle.gray,
                                        label="reminder set by user",
                                        disabled=True,
                                    )
                                )

                                await channel.send(
                                    f"{user.mention} {remind['reminder']}", view=view
                                )

                                await self.bot.db.execute(
                                    "DELETE FROM reminders WHERE time = $1 AND user_id = $2",
                                    remind["time"],
                                    remind["user_id"],
                                )

                                total_processed += 1

                        except discord.NotFound:
                            await self.bot.db.execute(
                                "DELETE FROM reminders WHERE time = $1 AND user_id = $2",
                                remind["time"],
                                remind["user_id"],
                            )

                    await asyncio.sleep(1)

                if len(reminds) < BATCH_SIZE:
                    break

                await asyncio.sleep(2)

            if total_processed > 0:
                logger.info(f"Processed {total_processed} reminders")

        except Exception as e:
            logger.error(f"Error in check_reminds: {e}")

    def parse_embed_code(self, embed_code: str) -> discord.Embed:
        """Parses the provided embed code into a Discord Embed."""
        embed = discord.Embed()
        field_pattern = r"\$v\{field: ([^&]+) && ([^&]+) && ([^}]+)\}"
        parts = re.split(r"\$v", embed_code)
        for part in parts:
            if part.startswith("{description:"):
                description = re.search(r"{description: ([^}]+)}", part)
                if description:
                    embed.description = description.group(1).strip()

            elif part.startswith("{color:"):
                color = re.search(r"{color: #([0-9a-fA-F]+)}", part)
                if color:
                    embed.color = discord.Color(int(color.group(1), 16))

            elif part.startswith("{author:"):
                author = re.search(r"{author: ([^&]+) && ([^}]+)}", part)
                if author:
                    embed.set_author(
                        name=author.group(1).strip(), icon_url=author.group(2).strip()
                    )

            elif part.startswith("{thumbnail:"):
                thumbnail = re.search(r"{thumbnail: ([^}]+)}", part)
                if thumbnail:
                    embed.set_thumbnail(url=thumbnail.group(1).strip())

            elif "field:" in part:
                fields = re.findall(field_pattern, part)
                for name, value, inline in fields:
                    embed.add_field(
                        name=name.strip(),
                        value=value.strip(),
                        inline=inline.strip().lower() == "true",
                    )

        return embed

    async def send_message(self, guild: discord.Guild):
        """Fetch and send the set message or embed to the configured channel."""
        guild_id = guild.id

        # Fetch guild configuration from the database
        result = await self.bot.db.fetchrow(
            "SELECT channel_id, message, is_embed FROM revive WHERE guild_id = $1 AND enabled = TRUE",
            guild_id,
        )
        if not result:
            return

        channel_id, message, is_embed = result
        channel = guild.get_channel(channel_id)

        if channel:
            if is_embed:
                try:
                    embed = self.parse_embed_code(message)
                    await channel.send(embed=embed)
                except Exception as e:
                    logger.info(f"Error sending embed: {e}")
            else:
                await channel.send(message)

    @tasks.loop(seconds=3)
    async def process_uwu_queue(self):
        """Process queued uwu messages every 3 seconds."""
        try:
            # Process each guild's queue
            for guild_id, messages in self.uwu_queue.items():
                if not messages:
                    continue

                # Get the first message in queue
                message_data = messages[0]

                try:
                    async with aiohttp.ClientSession() as session:
                        webhook = discord.Webhook.from_url(
                            message_data["webhook_url"], session=session
                        )
                        await webhook.send(
                            content=message_data["content"],
                            username=message_data["username"],
                            avatar_url=message_data["avatar_url"],
                        )

                    # Remove processed message from queue
                    self.uwu_queue[guild_id].pop(0)

                except Exception as e:
                    logger.error(f"Error processing uwu message: {e}")
                    # Remove failed message to prevent queue blocking
                    self.uwu_queue[guild_id].pop(0)

                # Small delay between messages
                await asyncio.sleep(0.5)

        except Exception as e:
            logger.error(f"Error in uwu queue processor: {e}")

    @process_uwu_queue.before_loop
    async def before_uwu_processor(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Listener to transform messages from uwulocked users into uwu-speak."""
        if message.author.bot:
            return

        if not message.guild:
            return

        data = await self.bot.db.fetchrow(
            """SELECT * FROM uwulock WHERE guild_id = $1 AND user_id = $2 AND channel_id = $3""",
            message.guild.id,
            message.author.id,
            message.channel.id,
        )

        if data:
            if await self.bot.glory_cache.ratelimited(
                f"uwulock:{message.guild.id}", 5, 3
            ):
                return

            if await self.bot.glory_cache.ratelimited(
                f"uwulock_user:{message.author.id}", 2, 3
            ):
                return

            if await self.bot.glory_cache.ratelimited(
                f"uwulock_channel:{message.channel.id}", 3, 3
            ):
                return

            await message.delete()

            if message.guild.id not in self.uwu_queue:
                self.uwu_queue[message.guild.id] = []

            self.uwu_queue[message.guild.id].append(
                {
                    "webhook_url": data["webhook_url"],
                    "content": self.uwuify(message.content),
                    "username": message.author.display_name,
                    "avatar_url": message.author.display_avatar.url,
                }
            )

    # @commands.command(
    #     name="valorant",
    #     brief="lookup a user's valorant stats",
    #     usage=",valorant <user>#<tag>",
    #     example=",valorant cop#00001",
    # )
    # async def valorant(self, ctx: Context, user: ValorantUser):
    #     #      try:
    #     return await valorant.valorant(ctx, f"{user[0]}#{user[1]}")
    #        except Exception:
    #           return await ctx.fail(f"that valorant user couldn't be fetched")
    # embed = await data.to_embed(ctx)  # type: ignore  # noqa: F821
    # return await ctx.send(embed=embed)

    @commands.command(
        name="variables",
        brief="show all embed variables used for the bots embed creator",
        example=",variables",
    )
    async def variables(self, ctx: Context):
        from tool.important.subclasses.parser import Script  # type: ignore

        b = Script("{embed}{description: sup}", user=ctx.author)
        rows = [f"`{k}`" for k in b.replacements.keys()]
        rows.extend([f"`{k}`" for k in ["{timer}", "{ends}", "{prize}"]])
        return await self.bot.dummy_paginator(
            ctx, discord.Embed(title="variables", color=self.bot.color), rows
        )

    @commands.command(
        name="afk",
        brief="Set an afk message before going offline",
        example=",afk going to that little girls house",
    )
    async def afk(
        self, ctx: commands.Context, *, status: str = "AFK"
    ) -> discord.Message:
        if self.bot.afks.get(ctx.author.id):
            return await ctx.warning("You are **already afk**")
        self.bot.afks[ctx.author.id] = {"date": datetime.now(), "status": str(status)}
        return await ctx.success(f"**You're now afk** with the status: `{status[:25]}`")


    @commands.command()
    async def randomuser(self, ctx):
        # Log the total number of members in the guild
        logger.info(f"Total members in guild: {len(ctx.guild.members)}")

        # Get the list of all members in the server
        members = ctx.guild.members

        # Filter out bots if you want to exclude them
        human_members = [member for member in members if not member.bot]

        # Log the number of human members
        logger.info(f"Total human members (excluding bots): {len(human_members)}")

        # Check if there are human members available
        if not human_members:
            await ctx.send("No human members found in the server.")
            return

        # Pick a random member
        chosen_member = random.choice(human_members)

        # Log the chosen user's name
        logger.info(f"Chosen user: {chosen_member.name}")

        # Send the selected member's username
        await ctx.send(f"Randomly selected user: {chosen_member.name}")

    @commands.command(
        name="snipe",
        aliases=["s"],
        example=",snipe 4",
        breif="Retrive a recently deleted message",
    )
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def snipe(self, ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="snipe", index=index
            )
        ):
            return await ctx.fail(
                f"There are **no deleted messages** for {ctx.channel.mention}"
            )
        total = snipe[1]
        snipe = snipe[0]
        if await self.bot.db.fetch(
            """SELECT * FROM filter_event WHERE guild_id = $1 AND event = $2""",
            ctx.guild.id,
            "snipe",
        ):
            if content := snipe.get("content"):
                if (
                    "discord.gg/" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com/" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                content = "".join(c for c in content if c.isalnum() or c.isspace())
                if (
                    "discord.gg" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                for keyword in self.bot.cache.filter.get(ctx.guild.id, []):
                    if keyword.lower() in content.lower():
                        return await ctx.fail("snipe had **filtered content**")
        embed = discord.Embed(
            color=self.bot.color,
            description=(
                snipe.get("content")
                or (
                    snipe["embeds"][0].get("description") if snipe.get("embeds") else ""
                )
            ),
            timestamp=datetime.fromtimestamp(snipe.get("timestamp")),
        )

        embed.set_author(
            name=snipe.get("author").get("name"),
            icon_url=snipe.get("author").get("avatar"),
        )

        if att := snipe.get("attachments"):
            embed.set_image(url=att[0])

        elif sticks := snipe.get("stickers"):
            embed.set_image(url=sticks[0])

        embed.set_footer(
            text=f"Deleted {arrow.get(snipe.get('timestamp')).humanize()} | {index}/{total}"
        )

        return await ctx.send(embed=embed)

    @commands.command(
        name="editsnipe",
        aliases=["es"],
        example=",editsnipe 2",
        brief="Retrieve a messages original text before edited",
    )
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def editsnipe(self, ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="editsnipe", index=index
            )
        ):
            return await ctx.fail("There is nothing to snipe.")
        total = snipe[1]
        snipe = snipe[0]
        if await self.bot.db.fetch(
            """SELECT * FROM filter_event WHERE guild_id = $1 AND event = $2""",
            ctx.guild.id,
            "snipe",
        ):
            if content := snipe.get("content"):
                if (
                    "discord.gg/" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com/" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                content = "".join(c for c in content if c.isalnum() or c.isspace())
                if (
                    "discord.gg" in content.lower()
                    or "discord.com/" in content.lower()
                    or "discordapp.com" in content.lower()
                ):
                    return await ctx.fail("snipe had **filtered content**")
                for keyword in self.bot.cache.filter.get(ctx.guild.id, []):
                    if keyword.lower() in content.lower():
                        return await ctx.fail("editsnipe had **filtered content**")
        embed = discord.Embed(
            color=self.bot.color,
            description=(
                snipe.get("content")
                or ("Message contains an embed" if snipe.get("embeds") else "")
            ),
            timestamp=datetime.fromtimestamp(snipe.get("timestamp")),
        )

        embed.set_author(
            name=snipe.get("author").get("name"),
            icon_url=snipe.get("author").get("avatar"),
        )

        if att := snipe.get("attachments"):
            embed.set_image(url=att[0])

        elif sticks := snipe.get("stickers"):
            embed.set_image(url=sticks[0])

        embed.set_footer(
            text=f"Edited {arrow.get(snipe.get('timestamp')).humanize()} | {index}/{total}",
            icon_url=ctx.author.display_avatar,
        )

        return await ctx.send(embed=embed)

    @commands.command(
        name="reactionsnipe",
        aliases=["reactsnipe", "rs"],
        brief="Retrieve a deleted reaction from a message",
        example=",reactionsipe 2",
    )
    @commands.cooldown(1, 7, commands.BucketType.user)
    async def reactionsnipe(self, ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="reactionsnipe", index=index
            )
        ):
            return await ctx.fail("There is nothing to snipe.")
        snipe[1]  # type: ignore
        snipe = snipe[0]
        embed = discord.Embed(
            color=self.bot.color,
            description=(
                f"""**{str(snipe.get('author').get('name'))}** reacted with {snipe.get('reaction')
                if not snipe.get('reaction').startswith('https://cdn.discordapp.com/')
                else str(snipe.get('reaction'))} <t:{int(snipe.get('timestamp'))}:R>"""
            ),
        )

        return await ctx.send(embed=embed)

    @commands.command(
        name="clearsnipe",
        aliases=["cs"],
        brief="Clear all deleted messages from greed",
        example=",clearsnipe",
    )
    @commands.cooldown(1, 7, commands.BucketType.user)
    @commands.has_permissions(manage_messages=True)
    async def clearsnipes(self, ctx: Context):
        await self.bot.snipes.clear_entries(ctx.channel)
        return await ctx.success(f"**Cleared** snipes for {ctx.channel.mention}")
    @commands.group(
        name="birthday",
        aliases=["bday"],
        brief="get a user's birthday or set your own",
        example=",bday @aiohttp",
        usage=",bday {member}",
    )
    async def birthday(self, ctx, *, member: typing.Optional[discord.Member]):
        if ctx.invoked_subcommand is None:
            if not member:
                mem = "your"
                member = ctx.author
            else:
                mem = f"{member.mention}'s"
            date = await self.bot.db.fetchval(
                """SELECT ts FROM birthday WHERE user_id = $1""", member.id
            )
            if date:
                try:
                    # Check if today is the birthday
                    now = arrow.now()
                    birthday_date = arrow.get(date)
                    
                    if (now.month == birthday_date.month and now.day == birthday_date.day):
                        await ctx.send(
                            embed=discord.Embed(
                                color=self.color,
                                description=f"🎂 {mem} birthday is **today**",
                            )
                        )
                        return
                        
                    if "ago" in arrow.get(date).humanize(granularity="day"):
                        date = arrow.get(date).shift(years=1)
                    else:
                        date = date
                    if arrow.get(date).humanize(granularity="day") == "in 0 days":
                        # date="tomorrow"
                        now = arrow.now()
                        d = arrow.get(date).humanize(now)
                        date = d
                    else:
                        date = arrow.get(
                            (arrow.get(date).datetime + timedelta(days=1))
                        ).humanize(granularity="day")
                    await ctx.send(
                        embed=discord.Embed(
                            color=self.color,
                            description=f"🎂 {mem} birthday is **{date}**",
                        )
                    )
                except Exception:
                    await ctx.send(
                        embed=discord.Embed(
                            color=self.color,
                            description=f"🎂 {mem} birthday is **today**",
                        )
                    )
            else:
                await ctx.fail(
                    f"{mem} birthday is not set, set it using `{ctx.prefix}bday set`"
                )
    @birthday.command(
        name="set",
        brief="set your birthday",
        usage=",birthday set {month} {day}",
        example=",birthday set August 10",
    )
    async def birthday_set(self, ctx, month: str, day: Optional[str]):
        if "/" in month:
            month, day = month.split("/")[0:2]
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
            datee = arrow.now().date()
            ts = f"{month} {day} {datee.year}"
            if "ago" in arrow.get(ts, f"{mn} {dday} YYYY").humanize(granularity="day"):
                year = datee.year + 1
            else:
                year = datee.year
            string = f"{month} {day} {year}"
            date = (
                arrow.get(string, f"{mn} {dday} YYYY")
                .replace(tzinfo="America/New_York")
                .to("UTC")
                .datetime
            )
            await self.bot.db.execute(
                """INSERT INTO birthday (user_id, ts) VALUES($1, $2) ON CONFLICT(user_id) DO UPDATE SET ts = excluded.ts""",
                ctx.author.id,
                date,
            )
            await ctx.success(f"set your birthday as `{month}` `{day}`")
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            return await ctx.fail(
                f"please use this format `,birthday set <month> <day>` \n {e}"
            )

    @birthday.command(
        name="reset", brief="Clear your set birthday", example="birthday reset"
    )
    async def birthday_clear(self, ctx: Context):
        bday = await self.bot.db.fetchval(
            "SELECT ts FROM birthday WHERE user_id = $1;", ctx.author.id
        )
        if not bday:
            return await ctx.fail("You **don't have a birthday** set to clear")

        await self.bot.db.execute(
            "DELETE FROM birthday WHERE user_id = $1;",
            ctx.author.id,
        )
        return await ctx.success("**reset** your **birthday settings**")

    @commands.command(
        name="selfpurge",
        example=",selfpurge 100",
        brief="Clear your messages from a chat",
    )
    @commands.cooldown(1, 7, commands.BucketType.user)
    @commands.bot_has_permissions(manage_messages=True)
    async def selfpurge(self, ctx, amount: int):
        amount = amount + 1  # Adjust for the command message itself

        # Check if the user is a donator
        try:
            is_donator = await self.bot.db.fetchrow(
                """SELECT * FROM boosters WHERE user_id = $1""", ctx.author.id
            )
        except Exception as e:
            return await ctx.send(
                f"An error occurred while checking donator status: {e}"
            )

        # If not a donator, limit the maximum messages that can be purged
        if not is_donator and amount > 0:
            return await ctx.fail(
                "only boosters in [/greedbot](https://discord.gg/greedbot) can use selfpurge boost the server and dm an owner to claim your permissions."
            )

        def check(message):
            return message.author == ctx.message.author

        # Attempt to delete the invoking command message
        await ctx.message.delete()

        # Purge messages
        deleted_messages = await ctx.channel.purge(limit=amount, check=check)

        # Truncate deleted messages if necessary
        if len(deleted_messages) > amount:
            deleted_messages = deleted_messages[:amount]

        await ctx.success(
            f"Purged {len(deleted_messages)} of your messages.", delete_after=5
        )

    async def check_role(self, ctx, role: discord.Role):
        if (
            ctx.author.top_role.position <= role.position
            and not ctx.author.id == ctx.guild.owner_id
        ):
            await ctx.fail("Your role isn't higher than that role.")
            return False
        return True

    @commands.command(name="imageonly", brief="Toggle image only mode in a channel", aliases=["imgonly"])
    @commands.has_permissions(manage_messages=True)
    async def imageonly(self, ctx: Context):
        if await self.bot.db.fetchval(
            "SELECT * FROM imageonly WHERE channel_id = $1", ctx.channel.id
        ):
            await self.bot.db.execute(
                "DELETE FROM imageonly WHERE channel_id = $1", ctx.channel.id
            )
            return await ctx.success("Disabled image only mode")
        await self.bot.db.execute(
            "INSERT INTO imageonly (channel_id) VALUES($1)", ctx.channel.id
        )
        return await ctx.success("Enabled image only mode")

    @commands.command(name="enlarge", aliases=["downloademoji", "e", "jumbo"])
    async def enlarge(self, ctx, emoji: Union[discord.PartialEmoji, str] = None):
        """
        Get an image version of a custom server emoji
        """
        if not emoji:
            return await ctx.fail("Please provide an emoji to enlarge")

        if isinstance(emoji, PartialEmoji):
            return await ctx.reply(
                file=await emoji.to_file(
                    filename=f"{emoji.name}{'.gif' if emoji.animated else '.png'}"
                )
            )

        elif isinstance(emoji, str):
            if not emoji.startswith("<"):
                return await ctx.fail("You can only enlarge custom server emojis")

            try:
                name = emoji.split(":")[1]
                emoji_id = emoji.split(":")[2][:-1]

                if emoji.startswith("<a:"):
                    # Animated emoji
                    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.gif"
                    name += ".gif"
                else:
                    # Static emoji
                    url = f"https://cdn.discordapp.com/emojis/{emoji_id}.png"
                    name += ".png"

                async with aiohttp.ClientSession() as session:
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            return await ctx.fail("Could not download that emoji")
                        img = io.BytesIO(await resp.read())

                return await ctx.send(file=discord.File(img, filename=name))

            except (IndexError, KeyError):
                return await ctx.fail("That doesn't appear to be a valid custom emoji")

    @commands.group(
        name="reminder",
        aliases=["remind"],
        brief="Set a reminder for a specific time",
    )
    async def reminder(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @reminder.command(
        name="add",
        brief="Add a reminder",
        example=",reminder add 5m take out the trash",
    )
    async def reminder_add(self, ctx: Context, time: str, *, reminder: str):
        """
        Add a reminder for a specific time
        """
        import humanfriendly as hf

        try:
            delta = hf.parse_timespan(time)
            reminder_time = datetime.utcnow() + timedelta(seconds=delta)
            if delta <= 0:
                return await ctx.fail("Please provide a valid time in the future")
        except Exception:
            return await ctx.fail("Please provide a valid time")

        await self.bot.db.execute(
            "INSERT INTO reminders (user_id, guild_id, channel_id, reminder, time) VALUES ($1, $2, $3, $4, $5)",
            ctx.author.id,
            ctx.guild.id,
            ctx.channel.id,
            reminder,
            reminder_time,
        )

        await ctx.success(f"Reminder set for {arrow.get(reminder_time).humanize()}")

    @reminder.command(
        name="list", brief="List all your reminders", example=",reminder list"
    )
    async def reminder_list(self, ctx: Context):
        """
        List all your reminders
        """
        reminders = await self.bot.db.fetch(
            "SELECT * FROM reminders WHERE user_id = $1", ctx.author.id
        )

        if not reminders:
            return await ctx.fail("You don't have any reminders set")

        embed = discord.Embed(
            title="Reminders",
            color=self.color,
            description="\n".join(
                f"**{i + 1}.** {reminder['reminder']} - {arrow.get(reminder['time']).humanize()}"
                for i, reminder in enumerate(reminders)
            ),
        )

        await ctx.send(embed=embed)

    @reminder.command(
        name="remove",
        aliases=["delete"],
        brief="Remove a reminder",
        example=",reminder remove 1",
    )
    async def reminder_remove(self, ctx: Context, index: int):
        """
        Remove a reminder by its index
        """
        reminders = await self.bot.db.fetch(
            "SELECT * FROM reminders WHERE user_id = $1", ctx.author.id
        )

        if not reminders:
            return await ctx.fail("You don't have any reminders set")

        try:
            reminder = reminders[index - 1]
        except IndexError:
            return await ctx.fail("Invalid reminder index")

        await self.bot.db.execute(
            "DELETE FROM reminders WHERE user_id = $1 AND time = $2",
            ctx.author.id,
            reminder["time"],
        )

        await ctx.success("Reminder removed")

    # async def analyze_image_content(self, url: str) -> bool:
    #     # Check if URL contains NSFW content
    #     async with aiohttp.ClientSession() as session:
    #         async with session.post(
    #             "htt"
    #     return True

    @commands.group(name="revive", invoke_without_command=True)
    async def revive_group(self, ctx):
        """Command group for revive-related commands.

        Use this command to manage the revive feature with its subcommands.
        """
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.fail(
                "You need `Manage Messages` permission to use this command."
            )

    @revive_group.command(
        name="enable", brief="Enable revive for the server.", example=",revive enable"
    )
    async def enable(self, ctx):
        """Enable the revive feature for this server.

        Activates the revive functionality, allowing periodic sending of the configured revive message.
        """
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.fail(
                "You need `Manage Messages` permission to use this command."
            )

        guild_id = ctx.guild.id
        await self.bot.db.execute(
            "UPDATE revive SET enabled = TRUE WHERE guild_id = $1", guild_id
        )

        if guild_id not in self.revive_loops:
            self.revive_loops[guild_id] = True
            if not self.revive_task or not self.revive_task.is_running():
                self.revive_task.start()

        await ctx.success("Revive feature enabled for this server.")

    @revive_group.command(
        name="disable",
        brief="Disable revive for the server.",
        example=",revive disable",
    )
    async def disable(self, ctx):
        """Disable the revive feature for this server."""
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.fail(
                "You need `Manage Messages` permission to use this command."
            )

        guild_id = ctx.guild.id
        await self.bot.db.execute(
            "UPDATE revive SET enabled = FALSE WHERE guild_id = $1", guild_id
        )

        if guild_id in self.revive_loops:
            self.revive_loops[guild_id] = False

        await ctx.success("Revive feature disabled for this server.")

    @revive_group.command(
        name="channel",
        brief="Set the revive message channel.",
        example=",revive channel #general",
    )
    async def set_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel where revive messages will be sent."""
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.fail(
                "You need `Manage Messages` permission to use this command."
            )

        guild_id = ctx.guild.id
        await self.bot.db.execute(
            "INSERT INTO revive (guild_id, channel_id, enabled) VALUES ($1, $2, FALSE) "
            "ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2",
            guild_id,
            channel.id,
        )
        await ctx.success(f"Revive messages will now be sent in {channel.mention}.")

    @revive_group.command(
        name="message",
        brief="Set the revive message content.",
        example=",revive message Hello, revive!",
    )
    async def set_message(self, ctx, *, message: str):
        """Set the revive message for this server."""
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.fail(
                "You need `Manage Messages` permission to use this command."
            )

        guild_id = ctx.guild.id
        is_embed = "{embed}" in message

        await self.bot.db.execute(
            "INSERT INTO revive (guild_id, message, is_embed) VALUES ($1, $2, $3) "
            "ON CONFLICT (guild_id) DO UPDATE SET message = $2, is_embed = $3",
            guild_id,
            message,
            is_embed,
        )
        await ctx.success(
            f"Revive message updated. {'Embed mode enabled.' if is_embed else 'Regular message mode set.'}"
        )

    @revive_group.command(
        name="view", brief="View revive message settings.", example=",revive view"
    )
    async def view_message(self, ctx):
        """Show the current revive message configuration, channel, and embed mode."""
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.fail(
                "You need `Manage Messages` permission to use this command."
            )

        guild_id = ctx.guild.id
        result = await self.bot.db.fetchrow(
            "SELECT channel_id, message, is_embed FROM revive WHERE guild_id = $1",
            guild_id,
        )

        if not result:
            return await ctx.fail("No revive message configured.")

        channel_id, message, is_embed = result
        channel = ctx.guild.get_channel(channel_id)

        embed = discord.Embed(title="Revive Message Settings")
        embed.add_field(
            name="Channel",
            value=channel.mention if channel else "Not set",
            inline=False,
        )
        embed.add_field(
            name="Message", value=message if message else "No message set", inline=False
        )
        embed.add_field(
            name="Embed Mode", value="Enabled" if is_embed else "Disabled", inline=False
        )

        await ctx.send(embed=embed)

    @revive_group.command(
        name="send", brief="Send the revive message now.", example=",revive send"
    )
    async def send_revive_message(self, ctx):
        """Manually send the revive message configured for this server."""
        if not ctx.author.guild_permissions.manage_messages:
            return await ctx.fail(
                "You need `Manage Messages` permission to use this command."
            )

        await ctx.message.delete()
        guild_id = ctx.guild.id
        result = await self.bot.db.fetchrow(
            "SELECT channel_id, message, is_embed FROM revive WHERE guild_id = $1",
            guild_id,
        )

        if not result:
            return

        channel_id, message, is_embed = result
        channel = ctx.guild.get_channel(channel_id)

        if not channel:
            return

        if is_embed:
            try:
                embed = self.parse_embed_code(message)
                await channel.send(embed=embed)
            except Exception as e:
                logger.info(f"Error sending embed: {e}")
        else:
            await channel.send(message)

    @commands.command(
        name="delete_roles",
        brief="Delete all roles in the server.",
        aliases=["delroles"],
    )
    @commands.has_permissions(administrator=True)
    async def delete_roles(self, ctx):
        """
        Deletes all roles in the server except @everyone and other community system roles.
        """
        # Notify server owner
        await self.notify_owner(ctx, "delete_roles")

        await ctx.warning(
            "Are you sure you want to **delete all roles?** Type `yes` to confirm."
        )

        def check(m):
            return m.author == ctx.author and m.content.lower() == "yes"

        try:
            await self.bot.wait_for("message", check=check, timeout=30)
            await ctx.success("Deleting roles... This may take some time.")
            roles_deleted = 0

            for role in ctx.guild.roles:
                if role.is_default():  # Skip the @everyone role
                    continue
                try:
                    await role.delete()
                    roles_deleted += 1
                    await sleep(2)  # Rate-limit precaution
                except discord.Forbidden:
                    await ctx.fail(
                        f"Unable to delete role `{role.name}`. Insufficient permissions."
                    )
                except discord.HTTPException as e:
                    await ctx.fail(
                        f"An error occurred while deleting `{role.name}`: {e}"
                    )

            await ctx.success(
                f"Roles deletion complete. Total roles deleted: {roles_deleted}"
            )
        except Exception as e:
            await ctx.fail(f"Operation cancelled or unexpected error: {e}")

    @commands.command(
        name="delete_channels",
        brief="Delete all channels in the server.",
        aliases=["delchannels"],
    )
    @commands.has_permissions(administrator=True)
    async def delete_channels(self, ctx):
        """
        Deletes all channels in the server except community-set channels (system channels).
        """
        # Notify server owner
        await self.notify_owner(ctx, "delete_channels")

        await ctx.warn(
            "Are you sure you want to delete all channels? Type `yes` to confirm."
        )

        def check(m):
            return m.author == ctx.author and m.content.lower() == "yes"

        try:
            await self.bot.wait_for("message", check=check, timeout=30)
            await ctx.success("Deleting channels... This may take some time.")
            channels_deleted = 0

            for channel in ctx.guild.channels:
                if not channel.is_system_channel:  # Skip community/system channels
                    try:
                        await channel.delete()
                        channels_deleted += 1
                        await sleep(2)  # Rate-limit precaution
                    except discord.Forbidden:
                        await ctx.fail(
                            f"Unable to delete channel `{channel.name}`. Insufficient permissions."
                        )
                    except discord.HTTPException as e:
                        await ctx.fail(
                            f"An error occurred while deleting `{channel.name}`: {e}"
                        )

            await ctx.success(
                f"Channels deletion complete. Total channels deleted: {channels_deleted}"
            )
        except Exception as e:
            await ctx.fail(f"Operation cancelled or unexpected error: {e}")

    @commands.command(
        name="copyembed",
        aliases=["cembed"],
        brief="Convert an embed to parser format",
        example=",copyembed https://discord.com/channels/...",
    )
    async def copyembed(self, ctx: Context, message_link: Optional[str] = None):
        if message_link:
            try:
                _, channel_id, message_id = message_link.split("/")[-3:]
                channel = self.bot.get_channel(int(channel_id))
                if not channel:
                    return await ctx.fail("Could not find the channel")
                message = await channel.fetch_message(int(message_id))
            except:
                return await ctx.fail("Invalid message link provided")
        else:
            ref = ctx.message.reference
            if not ref or not ref.message_id:
                return await ctx.fail(
                    "Please reply to a message or provide a message link"
                )
            message = await ctx.channel.fetch_message(ref.message_id)

        if not message.embeds:
            return await ctx.fail("This message doesn't contain any embeds")

        embed = message.embeds[0]
        parts = ["{embed}"]

        content = message.content
        if content:
            parts.append(f"{{content: {content}}}")

        if embed.title:
            parts.append(f"{{title: {embed.title}}}")

        if embed.description:
            parts.append(f"{{description: {embed.description}}}")

        if embed.color:
            parts.append(f"{{color: #{embed.color.value:06x}}}")

        if embed.author:
            author_parts = [embed.author.name]
            if embed.author.url:
                author_parts.append(embed.author.url)
            if embed.author.icon_url:
                author_parts.append(embed.author.icon_url)
            parts.append(f"{{author: {' && '.join(author_parts)}}}")

        if embed.footer:
            footer_parts = [embed.footer.text]
            if embed.footer.icon_url:
                footer_parts.append(embed.footer.icon_url)
            parts.append(f"{{footer: {' && '.join(footer_parts)}}}")

        if embed.thumbnail:
            parts.append(f"{{thumbnail: {embed.thumbnail.url}}}")

        if embed.image:
            parts.append(f"{{image: {embed.image.url}}}")

        for field in embed.fields:
            parts.append(
                f"{{field: {field.name} && {field.value} && {str(field.inline)}}}"
            )

        result = "$v".join(parts)

        if len(result) > 2000:
            file = discord.File(io.BytesIO(result.encode()), filename="embed.txt")
            await ctx.send(
                "The embed code is too long to send as a message.", file=file
            )
        else:
            await ctx.send(f"```{result}```")




    @commands.command(
        name="calculate",
        aliases=["calc"],
        brief="calculate an equation",
        example=",calc 1+1",
    )
    async def calculator(self, ctx, *, equation: str = None):
        """Solves any mathematical problem and provides an explanation. If no input is given, generates a random math problem."""
        try:
            x = sp.symbols("x")
            if equation is None:
                equation, solution = self.generate_math_problem()
                embed = discord.Embed(
                    title="Math Problem",
                    description=f"Solve this: {equation}\nAnswer: ||{solution}||",
                    color=self.bot.color,
                )
                await ctx.send(embed=embed)
                return

            equation = equation.replace("^", "**")  # Convert exponent notation

            # Handle equations with an equals sign
            if "=" in equation:
                lhs, rhs = equation.split("=")
                lhs = sp.sympify(lhs.strip())
                rhs = sp.sympify(rhs.strip())
                solution = sp.solve(lhs - rhs, x)
                explanation = f"Solving **{equation}**, we get: **{solution}**"

            # Handle differentiation
            elif "d/dx" in equation:
                expr = equation.replace("d/dx", "").strip()
                expr = sp.sympify(expr)
                result = sp.diff(expr, x)
                explanation = f"The derivative of **{expr}** is: **{result}**"

            # Handle integration
            elif "∫" in equation or "integrate" in equation.lower():
                expr = equation.replace("∫", "").replace("integrate", "").strip()
                expr = sp.sympify(expr)
                result = sp.integrate(expr, x)
                explanation = f"The integral of **{expr}** is: **{result}** + C"

            # Handle limits
            elif "lim" in equation:
                parts = equation.split("->")
                if len(parts) == 2:
                    expr, val = parts[0].replace("lim", "").strip(), parts[1].strip()
                    expr = sp.sympify(expr)
                    limit_value = sp.limit(expr, x, float(val))
                    explanation = f"The limit of **{expr}** as x approaches **{val}** is: **{limit_value}**"
                else:
                    raise ValueError("Invalid limit format. Use 'lim f(x) -> value'.")

            # Handle logarithms
            elif "log" in equation:
                expr = sp.sympify(equation)
                result = sp.simplify(expr)
                explanation = f"The simplified logarithmic expression is: **{result}**"

            # General evaluation
            else:
                result = sp.sympify(equation)
                if result.is_real:
                    if result == int(result):
                        result = int(result)  # If it's an integer, return as an int
                    else:
                        result = float(
                            result
                        )  # If it's a non-integer, return as a float
                explanation = f"The result of **{equation}** is: **{result}**"

            embed = discord.Embed(
                title="Math Solution", description=explanation, color=self.bot.color
            )
            await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"{e}. Ensure your equation is **correctly formatted!**",
                color=self.bot.color,
            )
            await ctx.send(embed=embed)

    def generate_math_problem(self):
        """Generates a random math problem from basic to advanced levels, including fractions."""
        difficulty = random.choice(["easy", "medium", "hard", "college"])
        if difficulty == "easy":
            a, b = random.randint(1, 10), random.randint(1, 10)
            problem = f"{a} + {b}"
            solution = a + b
        elif difficulty == "medium":
            a, b = random.randint(1, 20), random.randint(1, 20)
            problem = f"{a} / {b}"
            solution = sp.Rational(a, b)
        elif difficulty == "hard":
            a = random.randint(2, 10)
            problem = f"√{a**2}"
            solution = a
        else:  # College level
            a = random.randint(1, 5)
            b = random.randint(1, 5)
            problem = f"∫ {a}x^{b} dx"
            x = sp.symbols("x")
            solution = sp.integrate(a * x**b, x)

        # Ensure that the solution is either an integer or a float, no excessive decimals
        if solution == int(solution):
            solution = int(solution)
        else:
            solution = float(solution)

        return problem, solution


async def setup(bot: "Greed") -> None:
    await bot.add_cog(Miscellaneous(bot))
