import asyncio
import discord
import config
import random
import os
import json
import time
import re
import mimetypes
import math
import dns.resolver
import io
import string
import aiohttp
import decimal

from uwuipy import uwuipy
from io import BytesIO
from random import choice, randint
from typing import Any, Dict, List, Optional, cast, Literal
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from datetime import datetime, timezone
from pydantic import BaseModel
from typing_extensions import Self
from xxhash import xxh64_hexdigest
from yarl import URL
from unidecode import unidecode

from PIL import (
    Image,
    ImageDraw,
    ImageChops,
    ImageStat,
    ImageSequence,
    ImageFont,
)

from discord import (
    Embed, 
    Member, 
    Message, 
    NotFound, 
    Reaction, 
    File, 
    TextChannel, 
    User, 
    ButtonStyle, 
    Embed, 
    Interaction
)

from discord.ui import Button, View, button
from discord.ext import tasks
from discord.utils import format_dt

from discord.ext.commands import (
    BucketType,
    Cog,
    command,
    max_concurrency,
    Range,
    has_permissions,
    hybrid_command,
    hybrid_group,
    cooldown,
    flag,
    group,
    parameter
)

from core.client import FlagConverter
from managers.paginator import Paginator
from main import Evict

from core.client.context import Context
from core.client.redis import Redis

from tools.formatter import plural
from tools.conversion import TouchableMember
from tools.handlers.vape import valid_flavors

from .jeyy import JeyyAPI
from .jeyy import CommandOnCooldown

from .alexflipnote import alexflipnote_api
from .alexflipnote import CommandOnCooldown

from .popcat import popcat_api
from .popcat import CommandOnCooldown

from .views import RPS, TicTacToe

from logging import getLogger
log = getLogger("evict/fun")
# EXAMPLES STOP AT LINE 1993
# - SIN

class MemeFlags(FlagConverter):
    top: str = flag(
        default=None,
        description="The text to display at the top of the meme",
    )
    bottom: str = flag(
        default=None,
        description="The text to display at the bottom of the meme",
    )
class TruthDareView(discord.ui.View):
    def __init__(self, bot, rating):
        super().__init__()
        self.bot = bot
        self.rating = rating

class DidYouMeanFlags(FlagConverter):
    first: str = flag(description="The first text to display")
    second: str = flag(description="The second text to display")

class PoohFlags(FlagConverter):
    first: str = flag(description="The regular text for normal Pooh")
    second: str = flag(description="The fancy text for fancy Pooh") 

class DrakeFlags(FlagConverter):
    first: str = flag(description="The text Drake is rejecting")
    second: str = flag(description="The text Drake is approving")

    @button(label="Truth", style=ButtonStyle.blurple)
    async def truth(self, interaction: Interaction, button: Button):

        if self.rating == "r" and not (isinstance(interaction.channel, discord.TextChannel) and interaction.channel.is_nsfw()):
            return await interaction.response.send_message("This channel is no longer NSFW", ephemeral=True)
            
        async with self.bot.session.get(f"https://api.truthordarebot.xyz/v1/truth?rating={self.rating}") as resp:
            if not resp.ok:
                return await interaction.response.send_message("Failed to fetch a question! Try again later.", ephemeral=True)
            
            data = await resp.json()
            
            cache_file = f"data/cache/truth_{self.rating}.json"
            try:
                if not os.path.exists("data/cache"):
                    os.makedirs("data/cache")
                    
                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        questions = json.load(f)
                else:
                    questions = []
                    
                if data["question"] not in questions:
                    questions.append(data["question"])
                    with open(cache_file, 'w') as f:
                        json.dump(questions, f, indent=4)
            except Exception:
                pass
            
            embed = discord.Embed(
                title="Truth",
                description=data["question"],
            )
            embed.set_footer(text=f"Rating: {data['rating'].upper()} • evict.bot")
            await interaction.response.send_message(embed=embed, view=TruthDareView(self.bot, self.rating))

    @button(label="Dare", style=ButtonStyle.red)
    async def dare(self, interaction: Interaction, button: Button):

        if self.rating == "r" and not (isinstance(interaction.channel, discord.TextChannel) and interaction.channel.is_nsfw()):
            return await interaction.response.send_message("This channel is no longer NSFW", ephemeral=True)
            
        async with self.bot.session.get(f"https://api.truthordarebot.xyz/v1/dare?rating={self.rating}") as resp:
            if not resp.ok:
                return await interaction.response.send_message("Failed to fetch a dare. Try again later.", ephemeral=True)
            
            data = await resp.json()
            
            cache_file = f"data/cache/dare_{self.rating}.json"
            try:
                if not os.path.exists("data/cache"):
                    os.makedirs("data/cache")
                    
                if os.path.exists(cache_file):
                    with open(cache_file, 'r') as f:
                        questions = json.load(f)
                else:
                    questions = []
                    
                if data["question"] not in questions:
                    questions.append(data["question"])
                    with open(cache_file, 'w') as f:
                        json.dump(questions, f, indent=4)
            except Exception:
                pass
            
            embed = discord.Embed(
                title="Dare",
                description=data["question"],
            )
            embed.set_footer(text=f"Rating: {data['rating'].upper()} • evict.bot")
            await interaction.response.send_message(embed=embed, view=TruthDareView(self.bot, self.rating))

class Blacktea(BaseModel):
    message_id: int
    channel_id: int
    waiting: bool = True
    players: Dict[int, int] = {}
    used_words: List[str] = []

    @staticmethod
    def key(channel_id: int) -> str:
        return f"blacktea:{channel_id}"

    @classmethod
    async def get(cls, redis: Redis, channel_id: int) -> Optional[Self]:
        key = cls.key(channel_id)
        data = cast(Optional[Dict[str, Any]], await redis.get(key))
        if not data:
            return

        return cls(**data)

    async def save(self, redis: Redis, **kwargs) -> None:
        key = self.key(self.channel_id)
        await redis.set(key, self.dict(), **kwargs)

    async def delete(self, redis: Redis) -> None:
        key = self.key(self.channel_id)
        await redis.delete(key)

class Flags(BaseModel):
    message_id: int
    channel_id: int
    waiting: bool = True
    players: Dict[int, int] = {}
    current_difficulty: str = "easy"
    used_flags: List[str] = []

    @staticmethod
    def key(channel_id: int) -> str:
        return f"flags:{channel_id}"

    @classmethod
    async def get(cls, redis: Redis, channel_id: int) -> Optional[Self]:
        key = cls.key(channel_id)
        data = cast(Optional[Dict[str, Any]], await redis.get(key))
        if not data:
            return
        return cls(**data)

    async def save(self, redis: Redis, **kwargs) -> None:
        key = self.key(self.channel_id)
        await redis.set(key, self.dict(), **kwargs)

    async def delete(self, redis: Redis) -> None:
        key = self.key(self.channel_id)
        await redis.delete(key)


class Fun(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Interact with games with other members."
        self.words: List[str] = []
        self.valid_flavors: List[str] = valid_flavors
        self.send_random_wyr.start()
        self.proposal_cache = {}
        
        self.flag_difficulties = {
            "easy": [
                "us", "gb", "ca", "fr", "de", "it", "es", "jp", "br", "au", 
                "cn", "in", "ru", "kr", "mx", "za", "tr", "ar", "se", "no",
                "dk", "fi", "pt", "gr", "ie", "ch", "be", "nl"
            ],
            "medium": [
                "eg", "sa", "ae", "pl", "ua", "ro", "at", "hu", "cz", "il",
                "th", "vn", "ph", "my", "id", "sg", "nz", "cl", "co", "ve",
                "ma", "ng", "dz", "ke", "pk", "ir", "iq", "kz", "af", "is"
            ],
            "hard": [
                "al", "am", "az", "ba", "bg", "by", "cy", "ee", "ge", "hr",
                "lt", "lv", "md", "me", "mk", "mt", "rs", "si", "sk", "tn",
                "lb", "jo", "kw", "qa", "om", "uz", "tm", "kg", "tj", "mn",
                "np", "bd", "lk", "mm", "kh", "la", "bn", "pg", "uy", "py",
                "bo", "ec", "pe", "cr", "pa", "do", "ht", "tt", "bs", "bb",
                "bh", "ye", "sy", "sd", "er", "et", "ug", "tz", "mz", "zm",
                "na", "bw", "zw", "gh", "ci", "cm", "ga", "cg", "ao"
            ]
        }

    async def cog_load(self) -> None:
        async with self.bot.session.get(
            "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
        ) as resp:
            buffer = await resp.text()
            self.words = buffer.splitlines()

    async def webhook(self, channel) -> Optional[discord.Webhook]:
        if not channel.permissions_for(channel.guild.me).manage_webhooks:
            return None

        try:
            for webhook in await channel.webhooks():
                if webhook.user == self.bot.user:
                    return webhook

            return await channel.create_webhook(name="evict")
        except discord.Forbidden:
            return None
        except Exception as e:
            return None

    async def cog_unload(self) -> None:
        self.words = []

    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, member: Member) -> None:
        if member.bot or reaction.emoji != "✅":
            return

        session = await Blacktea.get(self.bot.redis, reaction.message.channel.id)
        if (
            not session
            or not session.waiting
            or session.message_id != reaction.message.id
        ):
            return

        if member.id in session.players:
            return

        session.players[member.id] = 2
        await session.save(self.bot.redis)

        embed = Embed(description=f"**{member}** joined the game")
        await reaction.message.reply(embed=embed, delete_after=3)

    async def get_user_badges(self, user: Member | User) -> list:
        badges = []
        staff_eligible = False
        
        support_guild = self.bot.get_guild(892675627373699072)
        if support_guild:
            support_member = support_guild.get_member(user.id)
            if support_member:
                role_badges = {
                    1265473601755414528: ["developer", "owner"],
                    1264110559989862406: ["support"],
                    1323255508609663098: ["trial"],
                    1325007612797784144: ["mod"],
                    1318054098666389534: ["donor1"],
                    1320428924215496704: ["donor4"]
                }

                for role_id, badge_types in role_badges.items():
                    if any(role.id == role_id for role in support_member.roles):
                        badges.extend(badge_types)
                        if role_id not in [1318054098666389534, 1320428924215496704]:
                            staff_eligible = True

                if staff_eligible:
                    badges.append("staff")
                    
        return badges

    async def generate_profile_image(self, user: Member | User, force_update: bool = False) -> str:
        cached = await self.bot.db.fetchrow(
            "SELECT profile_image, last_avatar, last_background FROM socials WHERE user_id = $1",
            user.id
        )

        current_avatar = str(user.display_avatar.url)
        current_badges = await self.get_user_badges(user)
        current_background = await self.bot.db.fetchval(
            "SELECT background_url FROM socials WHERE user_id = $1",
            user.id
        )

        if not force_update and cached and cached['profile_image'] and \
           cached['last_avatar'] == current_avatar and \
           cached['last_background'] == current_background:
            return cached['profile_image']

        width, height = 1200, 630
        image = Image.new('RGBA', (width, height))
        draw = ImageDraw.Draw(image)

        if current_background:
            async with aiohttp.ClientSession() as session:
                async with session.get(current_background) as resp:
                    if resp.status == 200:
                        bg_data = await resp.read()
                        background = Image.open(BytesIO(bg_data)).convert('RGBA')
                        bg_ratio = width / height
                        img_ratio = background.width / background.height
                        
                        if img_ratio > bg_ratio:
                            new_width = int(height * img_ratio)
                            background = background.resize((new_width, height))
                            left = (new_width - width) // 2
                            background = background.crop((left, 0, left + width, height))
                        else:
                            new_height = int(width / img_ratio)
                            background = background.resize((width, new_height))
                            top = (new_height - height) // 2
                            background = background.crop((0, top, width, top + height))
                        image.paste(background, (0, 0))
        else:
            image.paste((24, 24, 27), (0, 0, width, height))

        overlay = Image.new('RGBA', (width, height), (0, 0, 0, 80))
        image.paste(overlay, (0, 0), overlay)

        avatar_size = 160
        async with aiohttp.ClientSession() as session:
            async with session.get(current_avatar) as resp:
                if resp.status == 200:
                    avatar_data = await resp.read()
                    avatar = Image.open(BytesIO(avatar_data))
                    avatar = avatar.resize((avatar_size, avatar_size))
                    
                    mask = Image.new('L', (avatar_size, avatar_size), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                    
                    output = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
                    output.paste(avatar, (0, 0))
                    output.putalpha(mask)
                    
                    avatar_x = (width - avatar_size) // 2
                    avatar_y = height // 4 - avatar_size // 4
                    image.paste(output, (avatar_x, avatar_y), output)

        username_font = ImageFont.truetype("assets/fonts/Montserrat-SemiBold.ttf", 75)
        link_font = ImageFont.truetype("assets/fonts/Montserrat-Regular.ttf", 32)
        
        username = user.name
        if len(username) > 15:
            username_font = ImageFont.truetype("assets/fonts/Montserrat-SemiBold.ttf", 60)
        
        bbox = draw.textbbox((0, 0), username, font=username_font)
        text_width = bbox[2] - bbox[0]
        username_x = (width - text_width) // 2
        username_y = avatar_y + avatar_size + 20
        draw.text((username_x, username_y), username, font=username_font, fill=(255, 255, 255))

        if current_badges:
            badge_size = 28
            badge_bg_size = 36
            total_width = len(current_badges) * badge_bg_size
            badge_start_x = (width - total_width) // 2
            badge_y = username_y + 100

            container = Image.new('RGBA', (total_width, badge_bg_size), (24, 24, 27))
            container_mask = Image.new('L', (total_width, badge_bg_size))
            container_draw = ImageDraw.Draw(container_mask)
            container_draw.rounded_rectangle((0, 0, total_width, badge_bg_size), radius=8, fill=255)
            
            image.paste(container, (badge_start_x, badge_y), container_mask)

            for i, badge in enumerate(current_badges):
                try:
                    badge_path = f"assets/badges/slugs/{badge}.png"
                    badge_img = Image.open(badge_path).convert('RGBA')
                    badge_img = badge_img.resize((badge_size, badge_size))
                    
                    x = badge_start_x + i * badge_bg_size
                    icon_x = x + (badge_bg_size - badge_size) // 2
                    icon_y = badge_y + (badge_bg_size - badge_size) // 2
                    image.paste(badge_img, (icon_x, icon_y), badge_img)
                except Exception as e:
                    continue

        profile_link = f"evict.bot/@{user.name}"
        bbox = draw.textbbox((0, 0), profile_link, font=link_font)
        link_width = bbox[2] - bbox[0]
        link_x = (width - link_width) // 2
        link_y = badge_y + 60 if current_badges else username_y + 80
        draw.text((link_x, link_y), profile_link, font=link_font, fill=(160, 160, 180))

        buffer = BytesIO()
        image.save(buffer, 'PNG')
        buffer.seek(0)

        filename = f"profile_{user.id}_{int(time.time())}.png"
        headers = {"AccessKey": "10e0eb5f-79de-4ae9-a35a9b9f71e0-8c99-4a58"}
        
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"https://storage.bunnycdn.com/evict/socials/{filename}",
                headers=headers,
                data=buffer.read()
            ) as upload:
                if upload.status != 201:
                    raise Exception("Failed to upload to CDN")

                new_url = f"https://bunny.evict.bot/socials/{filename}"

                if cached and cached['profile_image']:
                    old_filename = cached['profile_image'].split('/')[-1]
                    await session.delete(
                        f"https://storage.bunnycdn.com/evict/socials/{old_filename}",
                        headers=headers
                    )

                await self.bot.db.execute(
                    "INSERT INTO socials (user_id, profile_image, last_avatar, last_background) VALUES ($1, $2, $3, $4) ON CONFLICT (user_id) DO UPDATE SET profile_image = $2, last_avatar = $3, last_background = $4",
                    user.id, new_url, current_avatar, current_background
                )
                
                return new_url

    @command()  
    async def blacktea(self, ctx: Context) -> Optional[Message]:
        """
        Start a game of Blacktea.
        """

        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
        if session:
            return await ctx.warn("There is already a game in progress.")

        embed = Embed(
            title="Blacktea",
            description="\n> ".join(
                [
                    "React with `✅` to join the game. The game will start in **30 seconds**",
                    "You'll have **10 seconds** type a word containing the given letters",
                    "The word must be at least **3 letters long** and **not used before**",
                ]
            ),
        )
        message = await ctx.channel.send(embed=embed)

        session = Blacktea(message_id=message.id, channel_id=ctx.channel.id)
        await session.save(self.bot.redis)
        await message.add_reaction("✅")

        await asyncio.sleep(30)
        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
        if not session or len(session.players) < 2:
            await self.bot.redis.delete(Blacktea.key(ctx.channel.id))
            return await ctx.warn("Not enough players to start the game!")

        session.waiting = False
        await session.save(self.bot.redis, ex=600)

        while True:
            session = await Blacktea.get(self.bot.redis, ctx.channel.id)
            if not session:
                return await ctx.warn("Game has been stopped!")

            for member_id, lives in list(session.players.items()):
                session = await Blacktea.get(self.bot.redis, ctx.channel.id)
                if not session:
                    return
                    
                member = ctx.guild.get_member(member_id)
                if not member:
                    if len(session.players) == 1:
                        await session.delete(self.bot.redis)
                        return await ctx.warn("The winner left the server!")

                    continue

                if len(session.players) == 1:
                    await session.delete(self.bot.redis)
                    return await ctx.approve(f"**{member}** has won the game!")

                letters = choice(
                    [
                        word[i:i+3].upper()
                        for word in self.words
                        for i in range(len(word)-2)
                        if len(word[i:i+3]) == 3
                    ]
                )
                embed = Embed(description=f"Type a **word** containing `{letters}`")
                prompt = await ctx.channel.send(content=member.mention, embed=embed)

                for index in range(4):
                    try:
                        message: Message = await self.bot.wait_for(
                            "message",
                            check=lambda m: (
                                m.content
                                and m.channel == ctx.channel
                                and m.author == member
                                and m.content.lower() in self.words
                                and letters.lower() in m.content.lower()
                                and m.content.lower() not in session.used_words
                            ),
                            timeout=(7 if index == 0 else 1),
                        )
                    except asyncio.TimeoutError:
                        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
                        if not session:
                            return
                            
                        if index == 3:
                            lives = session.players[member_id] - 1
                            if not lives:
                                del session.players[member_id]
                                embed = Embed(
                                    description=f"**{member}** has been **eliminated**!"
                                )
                                await ctx.channel.send(embed=embed)
                                await session.save(self.bot.redis)
                                
                                if len(session.players) == 1:
                                    last_player_id = next(iter(session.players))
                                    last_player = ctx.guild.get_member(last_player_id)
                                    await session.delete(self.bot.redis)
                                    return await ctx.approve(f"**{last_player}** has won the game!")
                                break

                            else:
                                session.players[member_id] = lives
                                embed = Embed(
                                    description="\n> ".join(
                                        [
                                            f"You ran out of time, **{member}**!",
                                            f"You have {plural(lives, md='**'):life|lives} remaining",
                                        ]
                                    )
                                )
                                await ctx.channel.send(embed=embed)
                                await session.save(self.bot.redis)
                                break

                        elif index != 0:
                            reactions = {
                                0: "4️⃣",  
                                1: "3️⃣",
                                2: "2️⃣",
                                3: "1️⃣",
                            }
                            try:
                                await prompt.add_reaction(reactions[index])
                            except NotFound:
                                ...

                        continue
                    else:
                        await message.add_reaction("✅")
                        session.used_words.append(message.content.lower())

                        break

    @command(aliases=["endblacktea", "stopblacktea", "btstop"])
    @has_permissions(manage_messages=True)
    async def blackteastop(self, ctx: Context) -> Optional[Message]:
        """
        Stop an ongoing game of Blacktea.
        """
        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
        if not session:
            return await ctx.warn("There is no game in progress!")

        await session.delete(self.bot.redis)
        return await ctx.approve("Successfully ended the Blacktea game!")

    @command(aliases=["btleave"])
    async def blacktealeave(self, ctx: Context) -> Optional[Message]:
        """Leave the current Blacktea game."""
        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
        if not session:
            return await ctx.warn("There is no game in progress!")

        if ctx.author.id not in session.players:
            return await ctx.warn("You are not in the game!")

        del session.players[ctx.author.id]
        
        if len(session.players) <= 1:
            await session.delete(self.bot.redis)
            return await ctx.warn("Game ended due to insufficient players!")
            
        await session.save(self.bot.redis)
        return await ctx.approve("Successfully left the game!")

    @command(aliases=["btplayers"])
    async def blackteaplayers(self, ctx: Context) -> Optional[Message]:
        """View the current players in the Blacktea game."""
        session = await Blacktea.get(self.bot.redis, ctx.channel.id)
        if not session:
            return await ctx.warn("There is no game in progress!")

        if not session.players:
            return await ctx.warn("There are no players in the game!")

        players_list = []
        for member_id, lives in session.players.items():
            member = ctx.guild.get_member(member_id)
            if member:
                players_list.append(f"{member.mention}: {plural(lives, md='**'):life|lives}")

        embed = Embed(
            title="Blacktea Players",
            description="\n".join(players_list) if players_list else "No active players!"
        )
        return await ctx.send(embed=embed)

    @command(aliases=["ttt"], example="@x")
    @max_concurrency(1, BucketType.member)
    async def tictactoe(self, ctx: Context, opponent: Member) -> Message:
        """
        Play Tic Tac Toe with another member.
        """
        if opponent == ctx.author:
            return await ctx.warn("You can't play against **yourself**")

        elif opponent.bot:
            return await ctx.warn("You can't play against **bots**")

        return await TicTacToe(ctx, opponent).start()

    @command(aliases=["rps"], example="@x")
    @max_concurrency(1, BucketType.member)
    async def rockpaperscissors(self, ctx: Context, opponent: Member) -> Message:
        """
        Play Rock Paper Scissors with another member.
        """

        if opponent == ctx.author:
            return await ctx.warn("You can't play against **yourself**")

        elif opponent.bot:
            return await ctx.warn("You can't play against **bots**")

        return await RPS(ctx, opponent).start()

    @command(aliases=["scrap"], example="hi")
    async def scrapbook(
        self, ctx: Context, *, text: Range[str, 1, 20]
    ) -> Optional[Message]:
        """
        Create scrapbook letters.
        """
        async with ctx.typing():
            async with self.bot.session.get(
                URL.build(
                    scheme="https",
                    host="api.jeyy.xyz",
                    path="/v2/image/scrapbook",
                ),
                headers={"Authorization": f"Bearer {config.AUTHORIZATION.JEYY_API}"},
                params={"text": text},
            ) as response:
                if not response.ok:
                    return await ctx.warn("Failed to generate the image")

                buffer = await response.read()
                image = BytesIO(buffer)

                await ctx.send(
                    file=File(image, filename="scrapbook.gif"),
                )

    @has_permissions(manage_webhooks=True)
    @command(aliases=["mock"], example="@x hi")
    async def impersonate(self, ctx: Context, member: Member, *, content):
        """
        Make a user say something.
        """
        if member.id == ctx.bot.user.id:
            return await ctx.warn("You cannot **impersonate** me.")

        if isinstance(member, Member):
            await TouchableMember().check(ctx, member)

        try:
            webhook = await ctx.channel.create_webhook(
                name=member.display_name,
                reason=f"{ctx.author} used impersonate command",
            )

            await ctx.message.delete()
            await webhook.send(
                str(content),
                username=member.display_name,
                avatar_url=member.display_avatar.url,
            )

            await webhook.delete(reason=f"{ctx.author} used impersonate command")

        except discord.HTTPException as e:
            await ctx.warn(f"An error occurred:\n {e}")

    @group(name="uwulock", example="@x", invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def uwulock(self, ctx: Context, *, member: Member):
        """
        Uwuify a person's messages.
        Re-running this command will remove the uwulock.
        """
        if isinstance(member, Member):
            await TouchableMember().check(ctx, member)

        record = await self.bot.db.fetchrow(
            """
            SELECT * 
            FROM uwulock 
            WHERE user_id = $1
            AND guild_id = $2
            """,
            member.id, 
            ctx.guild.id
        )

        if record is None:
            await self.bot.db.execute(
                """
                INSERT INTO uwulock 
                VALUES ($1,$2)
                """, 
                ctx.guild.id, 
                member.id
            )

            return await ctx.approve(f"Added **{member}** to uwulock!")
        
        if record is not None:
            await ctx.prompt(f"Would you like to remove **{member}** from uwulock?")
            await self.bot.db.execute(
                """
                DELETE FROM uwulock 
                WHERE user_id = $1
                AND guild_id = $2
                """,
                member.id, 
                ctx.guild.id
            )
            
            return await ctx.approve(f"Removed **{member}** from uwulock!")
    
    @uwulock.command(name="reset")
    @has_permissions(manage_guild=True)
    async def uwulock_reset(self, ctx: Context):
        """
        Remove everyone from uwulock.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM uwulock 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if record is None:
            return await ctx.warn("There is no one in uwulock!")

        await ctx.prompt("Would you like to remove everyone from uwulock?")
        await self.bot.db.execute(
            """
            DELETE FROM uwulock 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        return await ctx.approve("Removed everyone from uwulock!")

    @group(name="shutup", example="@x", invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def shutup(self, ctx: Context, *, member: Member):
        """
        Automatically delete a person's messages.
        Re-running this command will remove the shutup.
        """
        if isinstance(member, Member):
            await TouchableMember().check(ctx, member)

        record = await self.bot.db.fetchrow(
            """
            SELECT * 
            FROM shutup 
            WHERE user_id = $1
            AND guild_id = $2
            """,
            member.id, 
            ctx.guild.id
        )

        if record is None:
            await self.bot.db.execute(
                """
                INSERT INTO shutup 
                VALUES ($1,$2)
                """, 
                ctx.guild.id, 
                member.id
            )

            return await ctx.approve(f"Added **{member}** to shutup!")
        
        if record is not None:
            await ctx.prompt(f"Would you like to remove **{member}** from shutup?")
            await self.bot.db.execute(
                """
                DELETE FROM shutup 
                WHERE user_id = $1
                AND guild_id = $2
                """,
                member.id, 
                ctx.guild.id
            )
            
            return await ctx.approve(f"Removed **{member}** from shutup!")

    @shutup.command(name="reset")
    @has_permissions(manage_guild=True)
    async def shutup_reset(self, ctx: Context):
        """
        Remove everyone from shutup.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM shutup 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if record is None:
            return await ctx.warn("There is no one in shutup!")

        await ctx.prompt("Would you like to remove everyone from shutup?")
        await self.bot.db.execute(
            """
            DELETE FROM shutup 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        return await ctx.approve("Removed everyone from shutup!")

    @command(aliases=["howdumb"], example="@x")
    async def howretarded(self, ctx: Context, member: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ):
        """
        Check how retarded a member is.
        """
        member = member or ctx.author
        embed = Embed(description=f"> {config.EMOJIS.FUN.DUMBASS} {member.mention} is ``{random.randint(1,100)}%`` retarded.")
        return await ctx.send(embed=embed)

    @hybrid_command(aliases=["lesbian"], example="@x", with_app_command=True, brief="Check how lesbian someone is.")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def howlesbian(
        self,
        ctx: Context,
        *,
        member: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ):
        """
        Check how much of a lesbian a member is.
        """
        embed = Embed(description=f"> {config.EMOJIS.FUN.LESBIAN} {member.mention} is ``{random.randint(1,100)}%`` lesbian.")
        return await ctx.send(embed=embed)

    @hybrid_command(aliases=["gay"], example="@x", with_app_command=True, brief="Check how gay someone is.")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def howgay(
        self,
        ctx: Context,
        *,
        member: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ):
        """
        Check how gay a member is.
        """
        member = member or ctx.author
        embed = Embed(description=f"> {config.EMOJIS.FUN.GAY} {member.mention} is ``{random.randint(1,100)}%`` gay.")
        return await ctx.send(embed=embed)

    @command(example="@x")
    async def penis(self, ctx: Context, *, member: Optional[Member] = None):
        """
        Check how big a member's penis is.
        """
        member = member or ctx.author
        penis = "===================="
        embed = discord.Embed(description=f"{member.mention}'s penis\n\n8{penis[random.randint(1, 20):]}D")
        return await ctx.send(embed=embed)

    @command(example="hi")
    async def uwuify(self, ctx: Context, *, msg: str):
        """
        Uwuify a message.
        """
        uwu = uwuipy()
        uwu_msg = uwu.uwuify(msg)
        return await ctx.send(uwu_msg)
    
    @cooldown(1, 5, BucketType.member)
    @group(name="vape", aliases=["juul"], invoke_without_command=True)
    async def vape(self, ctx: Context):
        """
        Check what vape flavor you have enabled.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM vape 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )

        if record is None:
            return await ctx.warn(
                f"You don't have a vape! Use `{ctx.clean_prefix}vape flavor <flavor>` to get a vape."
            )

        flavor = record["flavor"]
        return await ctx.vape(f"You have a **{flavor}** vape.")

    @cooldown(1, 5, BucketType.member)
    @vape.command(name="flavors", aliases=["flavours"], example="blueberry")
    async def vape_flavors(self, ctx: Context):
        """
        See a list of vape flavors.
        """
        flavors_list = "\n> ".join(valid_flavors)
        embed = Embed(
            title="Available Vape Flavors",
            description=f"> {flavors_list}",
        )

        return await ctx.send(embed=embed)

    @cooldown(1, 5, BucketType.member)
    @vape.command(name="hit", aliases=["smoke"])
    async def vape_hit(self, ctx: Context):
        """
        Hit your vape.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM vape 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )

        if record is None:
            return await ctx.warn(
                f"You don't have a **vape**. Use `{ctx.clean_prefix}vape flavor <flavor>` to get a vape."
            )

        hits = record.get("hits", 0) + 1
        flavor = record.get("flavor", "Unknown")

        try:
            await self.bot.db.execute(
                """
                UPDATE vape
                SET hits = $2
                WHERE user_id = $1
                """,
                ctx.author.id,
                hits,
            )

        except Exception:
            return await ctx.warn("An error occurred while updating your vape data.")

        vape = await ctx.vape("Hitting your vape..")
        await asyncio.sleep(1)
        return await ctx.vape(f"Hit your **{flavor}** vape. You now have **{hits}** hits.", patch=vape)

    @cooldown(1, 5, BucketType.member)
    @vape.command(name="flavor", aliases=["flavour", "set"], example="blueberry")
    async def vape_flavor(self, ctx: Context, *, flavor: str = None):
        """
        Set your vape flavor.
        """
        flavor = flavor.title()
        if flavor not in valid_flavors:
            flavors_list = ", ".join(valid_flavors)
            return await ctx.warn(f"Invalid flavor. Valid flavors are: {flavors_list}")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO vape (user_id, flavor, hits)
                VALUES ($1, $2, 0)
                ON CONFLICT (user_id)
                DO UPDATE SET flavor = $2
                """,
                ctx.author.id,
                flavor,
            )

        except Exception:
            return await ctx.warn("An error occurred while setting your vape flavor.")

        return await ctx.approve(f"Your vape flavor has been set to **{flavor}**.")

    @group(name="blunt", aliases=["joint"], invoke_without_command=True)
    async def blunt(self, ctx: Context):
        """
        Smoke a blunt.
        """
        await ctx.send_help(ctx.command)
    
    @cooldown(1, 5, BucketType.member)
    @blunt.command(name="light", aliases=["broll"])
    async def blunt_light(self, ctx: Context):
        """
        Light the blunt.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM blunt 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if record:
            user = ctx.guild.get_member(record.get("user_id"))
            return await ctx.warn(
                f"A blunt is already held by **{user or record.get('user_id')}**\n> It has been hit"
                f" {plural(record.get('hits')):time} by {plural(record.get('members')):member}",
            )

        await self.bot.db.execute(
            """
            INSERT INTO blunt (guild_id, user_id) 
            VALUES($1, $2)
            """,
            ctx.guild.id,
            ctx.author.id,
        )

        blunt = await ctx.blunt("Rolling up a **blunt**...")
        await asyncio.sleep(2)
        return await ctx.blunt(f"Lit up a blunt.\n> Use `{ctx.prefix}blunt hit` to smoke it.", patch=blunt)

    @cooldown(1, 5, BucketType.member)
    @blunt.command(name="pass", example="@x", aliases=["give"])
    async def blunt_pass(self, ctx: Context, *, member: Member):
        """
        Pass the blunt to another member.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM blunt 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not record:
            return await ctx.warn(
                f"There is no **blunt** to pass\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        
        if record.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(record.get("user_id"))
            return await ctx.warn(
                f"You don't have the blunt!\n> Steal it from **{member or blunt.get('user_id')}** first!"
            )
        
        if member == ctx.author:
            return await ctx.warn("You can't pass the blunt to **yourself!")

        await self.bot.db.execute(
            """
            UPDATE blunt SET user_id = $2, passes = passes + 1 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            member.id,
        )

        return await ctx.blunt(
            f"The **blunt** has been passed to **{member}**!\n> It has been passed around"
            f"**{plural(record.get('passes') + 1):time}**"
        )

    @cooldown(1, 5, BucketType.member)
    @blunt.command(name="steal", aliases=["take"])
    async def blunt_steal(self, ctx: Context):
        """
        Steal the blunt from another member.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM blunt 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if not record:
            return await ctx.warn(
                f"There is no **blunt** to steal!\n> Use `{ctx.prefix}blunt light` to roll one up!"
        )
        
        if record.get("user_id") == ctx.author.id:
            return await ctx.warn(
                f"You already have the blunt!\n> Use `{ctx.prefix}blunt pass` to pass it to someone else!"
        )

        member = ctx.guild.get_member(record.get("user_id"))

        if random.randint(1, 100) <= 50:
            return await ctx.warn(
                f"**{member or record.get('user_id')}** is hogging the blunt!"
            )

        await self.bot.db.execute(
            """
            UPDATE blunt SET user_id = $2 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            ctx.author.id,
        )

        return await ctx.approve(
            f"You just stole the **blunt** from **{member or record.get('user_id')}**!",
        )

    @cooldown(1, 5, BucketType.member)
    @blunt.command(name="hit", aliases=["smoke", "chief"])
    async def blunt_hit(self, ctx: Context):
        """
        Hit the blunt.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT * FROM blunt 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        
        if not record:
            return await ctx.warn(
                f"There is no **blunt** to hit\n> Use `{ctx.prefix}blunt light` to roll one up"
            )
        
        if record.get("user_id") != ctx.author.id:
            member = ctx.guild.get_member(record.get("user_id"))
            return await ctx.warn(
                f"You don't have the **blunt**!\n> Steal it from **{member or record.get('user_id')}** first!"
            )

        members = record.get("members", [])
        if ctx.author.id not in members:
            members.append(ctx.author.id)

        blunt = await ctx.blunt("Hitting the **blunt**..")
        
        async with ctx.typing():
            await asyncio.sleep(randint(1, 2))

            if record["hits"] + 1 >= 10 and randint(1, 100) <= 25:
                await self.bot.db.execute(
                    """
                    DELETE FROM blunt 
                    WHERE guild_id = $1
                    """,
                    ctx.guild.id,
                )

                await ctx.vape(
                    f"The **blunt** burned out after {plural(record.get('hits') + 1):hit} by"
                    f" **{plural(len(members)):member}**",
                    patch=blunt
                )

            await self.bot.db.execute(
                """
                UPDATE blunt SET hits = hits + 1, members = $2 
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                members,
            )
        
        return await ctx.blunt(
            f"You just hit the blunt! \n> It has been hit **{plural(record.get('hits') + 1):time}** by"
            f" **{plural(len(members)):member}**!",
            patch=blunt
        )

    @command(example="@x")
    async def pack(self, ctx: Context, *, user: Member):
        """
        Insult another user.
        """
        packs = "./cogs/fun/packs.txt"
        with open(packs, "r") as f:
            lines = f.readlines()
            randomPack = random.choice(lines).strip()
            return await ctx.send(f"{user.mention} " + randomPack)

    @command(example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def speechbubble(self, ctx: Context, image_url: str = None):
        """
        Add a speech bubble to an image/gif.
        """
        if not image_url:
            if not ctx.message.attachments:
                if not ctx.message.reference:
                    return await ctx.warn(
                        "Please provide an image URL, attachment, or reply to a message with an image"
                    )

                referenced = await ctx.channel.fetch_message(
                    ctx.message.reference.message_id
                )
                if referenced.attachments:
                    attachment = referenced.attachments[0]
                    if attachment.size > 10 * 1024 * 1024:
                        return await ctx.warn("File too large (max 10MB)")
                    image_url = attachment.url
                elif referenced.embeds:
                    embed = referenced.embeds[0]
                    if embed.thumbnail:
                        image_url = embed.thumbnail.url
                    elif embed.image:
                        image_url = embed.image.url
                    else:
                        return await ctx.warn(
                            "No image found in the referenced message"
                        )
                else:
                    return await ctx.warn("No image found in the referenced message")
            else:
                image_url = ctx.message.attachments[0].url

        async with ctx.typing():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as response:
                        if not response.ok:
                            return await ctx.warn("Failed to download the image")

                        content_type = response.headers.get("Content-Type", "")
                        if "image" not in content_type.lower():
                            if "/external/" in image_url:
                                original_url = image_url.split("/external/")[1].split(
                                    "/", 1
                                )[1]
                                if original_url.endswith(".mp4"):
                                    original_url = original_url.replace(".mp4", ".gif")
                                async with session.get(original_url) as orig_response:
                                    if orig_response.ok:
                                        image_data = await orig_response.read()
                                    else:
                                        return await ctx.warn(
                                            "Could not process this media type"
                                        )
                            else:
                                return await ctx.warn(
                                    "Could not process this media type"
                                )
                        else:
                            image_data = await response.read()
            except Exception as e:
                return await ctx.warn(f"An error occurred: {str(e)}")

            original = Image.open(BytesIO(image_data))

            is_animated = getattr(original, "is_animated", False)
            speech_bubble = Image.open("assets/manipulation/speech_bubble.png")

            def is_dark_image(img):
                if img.mode != "RGB":
                    img = img.convert("RGB")

                stat = ImageStat.Stat(img)
                brightness = sum(stat.mean) / 3

                return brightness < 128

            frames = []
            durations = []
            for frame in ImageSequence.Iterator(original):
                frame = frame.convert("RGBA")
                min_height = 200
                if frame.height < min_height:
                    new_height = min_height
                    new_width = int(frame.width * (min_height / frame.height))
                    frame = frame.resize((new_width, new_height))

                resized_bubble = speech_bubble.resize(frame.size)

                if is_dark_image(frame):
                    result = ImageChops.add(frame, resized_bubble)
                else:
                    result = ImageChops.subtract_modulo(frame, resized_bubble)

                frames.append(result)
                durations.append(original.info.get("duration", 100))

            output = BytesIO()
            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=durations,
                loop=0,
                disposal=2,
                optimize=False,
            )
            output.seek(0)

            await ctx.send(file=File(output, filename="evict-speechbubble.gif"))

    @hybrid_group(name="media", invoke_without_command=True)
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def media(self, ctx: Context):
        """Media manipulation commands"""
        await ctx.send_help(ctx.command)

    @media.command(name="scramble", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def media_scramble(self, ctx: Context, file: discord.Attachment):
        """Randomize frames within the given media"""
        if not file.content_type or not (
            file.content_type == "image/gif" or file.content_type.startswith("video/")
        ):
            return await ctx.warn("Please provide a GIF or video")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the media")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'scramble')
                await ctx.send(file=File(BytesIO(processed_bytes), "scrambled.gif"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the media")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'scramble')
            await ctx.send(file=File(BytesIO(processed_bytes), "scrambled.gif"))

    @media.command(name="reverse", example="https://example.com/image.jpg")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_reverse(self, ctx: Context, file: discord.Attachment):
        """Reverse the playback of a video or GIF"""
        if not file.content_type or not (
            file.content_type == "image/gif" or file.content_type.startswith("video/")
        ):
            return await ctx.warn("Please provide a GIF or video")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the media")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'reverse')
                await ctx.send(file=File(BytesIO(processed_bytes), "reversed.gif"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the media")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'reverse')
            await ctx.send(file=File(BytesIO(processed_bytes), "reversed.gif"))

    @media.command(name="speed", example="2.0 https://example.com/image.gif")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_speed(self, ctx: Context, file: discord.Attachment, speed: float = 2.0):
        """Change the speed of a GIF (0.5 = slower, 2.0 = faster)"""
        if not 0.1 <= speed <= 5.0:
            return await ctx.warn("Speed must be between 0.1 and 5.0")

        if not file.content_type or not file.content_type == "image/gif":
            return await ctx.warn("Please provide a GIF")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the GIF")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'speed', speed=speed)
                await ctx.send(file=File(BytesIO(processed_bytes), "speed.gif"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the GIF")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'speed', speed=speed)
            await ctx.send(file=File(BytesIO(processed_bytes), "speed.gif"))

    @media.command(name="zoom", example="https://example.com/image.jpg")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_zoom(self, ctx: Context, file: discord.Attachment):
        """Create a zooming gif using your photo"""
        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'zoom')
                await ctx.send(file=File(BytesIO(processed_bytes), "zoom.gif"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'zoom')
            await ctx.send(file=File(BytesIO(processed_bytes), "zoom.gif"))

    @media.command(name="zoomblur", example="https://example.com/image.jpg")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_zoomblur(self, ctx: Context, file: discord.Attachment):
        """Apply a zoom blur effect to an image"""
        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'zoomblur')
                await ctx.send(file=File(BytesIO(processed_bytes), "zoomblur.gif"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'zoomblur')
            await ctx.send(file=File(BytesIO(processed_bytes), "zoomblur.gif"))

    @media.command(name="rainbow", example="https://example.com/image.jpg")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_rainbow(self, ctx: Context, file: discord.Attachment):
        """Apply an animated rainbow color effect to your photo"""
        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'rainbow')
                await ctx.send(file=File(BytesIO(processed_bytes), "rainbow.gif"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'rainbow')
            await ctx.send(file=File(BytesIO(processed_bytes), "rainbow.gif"))

    @media.command(name="blur", example="5 https://example.com/image.jpg")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_blur(self, ctx: Context, file: discord.Attachment, radius: int = 5):
        """Blur an image with specified radius (1-20)"""
        if not 1 <= radius <= 20:
            return await ctx.warn("Blur radius must be between 1 and 20")

        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'blur', radius=radius)
                await ctx.send(file=File(BytesIO(processed_bytes), "blurred.png"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'blur', radius=radius)
            await ctx.send(file=File(BytesIO(processed_bytes), "blurred.png"))

    @media.command(name="caption", example="Hello, world!")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_caption(self, ctx: Context, file: discord.Attachment, *, caption: str):
        """Create your own caption meme using an image"""
        if len(caption) > 100:
            return await ctx.warn("Caption must be 100 characters or less")
        if len(caption) < 2:
            return await ctx.warn("Caption must be at least 2 characters")

        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'caption', caption=caption)
                await ctx.send(file=File(BytesIO(processed_bytes), "caption.png"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'caption', caption=caption)
            await ctx.send(file=File(BytesIO(processed_bytes), "caption.png"))

    @media.command(name="meme")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_meme(self, ctx: Context, file: discord.Attachment, *, flags: MemeFlags):
        """Create a top and bottom text meme"""
        if not flags.top and not flags.bottom:
            return await ctx.warn("Please provide at least one line of text (--top or --bottom)")

        if (flags.top and len(flags.top) > 100) or (flags.bottom and len(flags.bottom) > 100):
            return await ctx.warn("Text must be 100 characters or less")

        if (flags.top and len(flags.top) < 2) or (flags.bottom and len(flags.bottom) < 2):
            return await ctx.warn("Text must be at least 2 characters")

        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'meme', top_text=flags.top, bottom_text=flags.bottom)
                await ctx.send(file=File(BytesIO(processed_bytes), "meme.png"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'meme', top_text=flags.top, bottom_text=flags.bottom)
            await ctx.send(file=File(BytesIO(processed_bytes), "meme.png"))

    @media.command(name="flag", example="https://example.com/image.jpg")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_flag(self, ctx: Context, file: discord.Attachment):
        """Put a selected image onto a flag GIF"""
        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'flag')
                await ctx.send(file=File(BytesIO(processed_bytes), "flag.gif"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'flag')
            await ctx.send(file=File(BytesIO(processed_bytes), "flag.gif"))

    @media.command(name="deepfry", example="https://example.com/image.jpg")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @max_concurrency(1, BucketType.member)
    async def media_deepfry(self, ctx: Context, file: discord.Attachment):
        """Apply a deepfried filter to a photo"""
        if not file.content_type or not file.content_type.startswith("image/"):
            return await ctx.warn("Please provide an image")

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                async with self.bot.session.get(file.url) as resp:
                    if not resp.ok:
                        return await ctx.warn("Failed to download the image")
                    buffer = await resp.read()

                processed_bytes = await self.bot.process_image(buffer, 'deepfry')
                await ctx.send(file=File(BytesIO(processed_bytes), "deepfried.png"))
        else:
            async with self.bot.session.get(file.url) as resp:
                if not resp.ok:
                    return await ctx.warn("Failed to download the image")
                buffer = await resp.read()

            processed_bytes = await self.bot.process_image(buffer, 'deepfry')
            await ctx.send(file=File(BytesIO(processed_bytes), "deepfried.png"))

    @hybrid_group(name="filter")
    async def filter(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @filter.command(name="bayer", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_bayer(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a Bayer matrix dithering effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.bayer(url)
                await ctx.send(file=File(BytesIO(buffer), "bayer.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="emojify", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_emojify(self, ctx: Context, attachment: Optional[str] = None):
        """
        Convert image into emoji pixels
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.emojify(url)
                await ctx.send(file=File(BytesIO(buffer), "emojify.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="gameboy", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_gameboy(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a Gameboy-style effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.gameboy(url)
                await ctx.send(file=File(BytesIO(buffer), "gameboy.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="half_invert", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_half_invert(self, ctx: Context, attachment: Optional[str] = None):
        """
        Invert half of the image
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.half_invert(url)
                await ctx.send(file=File(BytesIO(buffer), "half_invert.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="letters", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_letters(self, ctx: Context, attachment: Optional[str] = None):
        """
        Convert image into ASCII letters
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.letters(url)
                await ctx.send(file=File(BytesIO(buffer), "letters.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="lines", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_lines(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a lined pattern effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.lines(url)
                await ctx.send(file=File(BytesIO(buffer), "lines.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="lsd", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_lsd(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a psychedelic color effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.lsd(url)
                await ctx.send(file=File(BytesIO(buffer), "lsd.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="matrix", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_matrix(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a Matrix-style effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.matrix(url)
                await ctx.send(file=File(BytesIO(buffer), "matrix.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="minecraft", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_minecraft(self, ctx: Context, attachment: Optional[str] = None):
        """
        Convert image into Minecraft blocks
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.minecraft(url)
                await ctx.send(file=File(BytesIO(buffer), "minecraft.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="neon", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_neon(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add neon glow effects
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.neon(url)
                await ctx.send(file=File(BytesIO(buffer), "neon.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="optics", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_optics(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply an optical distortion effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.optics(url)
                await ctx.send(file=File(BytesIO(buffer), "optics.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="pattern", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_pattern(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a repeating pattern from the image
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.pattern(url)
                await ctx.send(file=File(BytesIO(buffer), "pattern.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="sensitive", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_sensitive(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a sensitive content warning overlay
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.sensitive(url)
                await ctx.send(file=File(BytesIO(buffer), "sensitive.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @filter.command(name="stereo", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def filter_stereo(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a stereoscopic 3D effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.stereo(url)
                await ctx.send(file=File(BytesIO(buffer), "stereo.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @hybrid_group(name="animate")
    async def animate(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @animate.command(name="shine", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_shine(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a shining animation effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.shine(url)
                await ctx.send(file=File(BytesIO(buffer), "shine.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="shock", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_shock(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add an electric shock effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.shock(url)
                await ctx.send(file=File(BytesIO(buffer), "shock.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="shoot", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_shoot(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add shooting star effects
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.shoot(url)
                await ctx.send(file=File(BytesIO(buffer), "shoot.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="ripple", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_ripple(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a ripple animation effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.ripple(url)
                await ctx.send(file=File(BytesIO(buffer), "ripple.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="roll", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_roll(self, ctx: Context, attachment: Optional[str] = None):
        """
        Make the image roll like a barrel
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.roll(url)
                await ctx.send(file=File(BytesIO(buffer), "roll.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="fan", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_fan(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a fan blade spinning effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.fan(url)
                await ctx.send(file=File(BytesIO(buffer), "fan.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="fire", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_fire(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add animated fire effects
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.fire(url)
                await ctx.send(file=File(BytesIO(buffer), "fire.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="hearts", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_hearts(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add floating heart animations
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.hearts(url)
                await ctx.send(file=File(BytesIO(buffer), "hearts.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="boil", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_boil(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a boiling/bubbling effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.boil(url)
                await ctx.send(file=File(BytesIO(buffer), "boil.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="bomb", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_bomb(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add an explosion animation
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.bomb(url)
                await ctx.send(file=File(BytesIO(buffer), "bomb.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="3d", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_3d(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a 3D depth animation
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.three_d(url)
                await ctx.send(file=File(BytesIO(buffer), "3d.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="earthquake", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_earthquake(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a shaking earthquake effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.earthquake(url)
                await ctx.send(file=File(BytesIO(buffer), "earthquake.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="glitch", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_glitch(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add glitch/corruption effects
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.glitch(url)
                await ctx.send(file=File(BytesIO(buffer), "glitch.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="heart", example="https://example.com/image.jpg https://example.com/image2.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_heart(self, ctx: Context, url1: Optional[str] = None, url2: Optional[str] = None):
        """
        Create a heart locket animation with two images
        """
        async with ctx.typing():
            image1 = url1 or await self._get_media_url(ctx, None, accept_image=True) or ctx.author.display_avatar.url
            image2 = url2 or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.heart_locket(image1, image2)
                await ctx.send(file=File(BytesIO(buffer), "heart.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="magik", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_magik(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a liquid distortion animation
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.liquefy(url)
                await ctx.send(file=File(BytesIO(buffer), "magik.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="patpat", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_patpat(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a headpat animation
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.patpat(url)
                await ctx.send(file=File(BytesIO(buffer), "patpat.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="rain", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_rain(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add falling rain effects
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.rain(url)
                await ctx.send(file=File(BytesIO(buffer), "rain.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="triggered", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_triggered(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a triggered meme effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.earthquake(url)
                await ctx.send(file=File(BytesIO(buffer), "triggered.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="wasted", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_wasted(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a GTA wasted screen effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.explicit(url)
                await ctx.send(file=File(BytesIO(buffer), "wasted.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="spin", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_spin(self, ctx: Context, attachment: Optional[str] = None):
        """
        Make the image spin in circles
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.spin(url)
                await ctx.send(file=File(BytesIO(buffer), "spin.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="wave", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_wave(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a waving animation effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.wave(url)
                await ctx.send(file=File(BytesIO(buffer), "wave.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @animate.command(name="wiggle", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def animate_wiggle(self, ctx: Context, attachment: Optional[str] = None):
        """
        Make the image wiggle back and forth
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.wiggle(url)
                await ctx.send(file=File(BytesIO(buffer), "wiggle.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @hybrid_group(name="distort")
    async def distort(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @distort.command(name="burn", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def distort_burn(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a burning distortion effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.burn(url)
                await ctx.send(file=File(BytesIO(buffer), "burn.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="dizzy", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def distort_dizzy(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a dizzying spiral distortion effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.dizzy(url)
                await ctx.send(file=File(BytesIO(buffer), "dizzy.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="endless", example="https://example.com/image.jpg")
    @max_concurrency(1, BucketType.member)
    async def distort_endless(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create an endless looping distortion
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.endless(url)
                await ctx.send(file=File(BytesIO(buffer), "endless.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="infinity")
    @max_concurrency(1, BucketType.member)
    async def distort_infinity(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply an infinity mirror effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.infinity(url)
                await ctx.send(file=File(BytesIO(buffer), "infinity.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="melt")
    @max_concurrency(1, BucketType.member)
    async def distort_melt(self, ctx: Context, attachment: Optional[str] = None):
        """
        Make the image appear to melt
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.melt(url)
                await ctx.send(file=File(BytesIO(buffer), "melt.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="phase")
    @max_concurrency(1, BucketType.member)
    async def distort_phase(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a phasing distortion effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.phase(url)
                await ctx.send(file=File(BytesIO(buffer), "phase.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="poly")
    @max_concurrency(1, BucketType.member)
    async def distort_poly(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a polygonal distortion pattern
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.poly(url)
                await ctx.send(file=File(BytesIO(buffer), "poly.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="pyramid")
    @max_concurrency(1, BucketType.member)
    async def distort_pyramid(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a pyramid-like distortion effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.pyramid(url)
                await ctx.send(file=File(BytesIO(buffer), "pyramid.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="shear")
    @max_concurrency(1, BucketType.member)
    async def distort_shear(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a shearing distortion effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.shear(url)
                await ctx.send(file=File(BytesIO(buffer), "shear.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="shred")
    @max_concurrency(1, BucketType.member)
    async def distort_shred(self, ctx: Context, attachment: Optional[str] = None):
        """
        Shred the image into strips
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.shred(url)
                await ctx.send(file=File(BytesIO(buffer), "shred.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="slice")
    @max_concurrency(1, BucketType.member)
    async def distort_slice(self, ctx: Context, attachment: Optional[str] = None):
        """
        Slice the image into segments
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.slice(url)
                await ctx.send(file=File(BytesIO(buffer), "slice.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @distort.command(name="stretch")
    @max_concurrency(1, BucketType.member)
    async def distort_stretch(self, ctx: Context, attachment: Optional[str] = None):
        """
        Apply a stretching distortion effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.stretch(url)
                await ctx.send(file=File(BytesIO(buffer), "stretch.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @group(name="transform")
    async def transform(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @transform.command(name="ads")
    @max_concurrency(1, BucketType.member)
    async def transform_ads(self, ctx: Context, attachment: Optional[str] = None):
        """
        Transform image into an advertisement style
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.ads(url)
                await ctx.send(file=File(BytesIO(buffer), "ads.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="bevel")
    @max_concurrency(1, BucketType.member)
    async def transform_bevel(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a beveled edge effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.bevel(url)
                await ctx.send(file=File(BytesIO(buffer), "bevel.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="billboard")
    @max_concurrency(1, BucketType.member)
    async def transform_billboard(self, ctx: Context, attachment: Optional[str] = None):
        """
        Display image on a billboard
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.billboard(url)
                await ctx.send(file=File(BytesIO(buffer), "billboard.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="cube")
    @max_concurrency(1, BucketType.member)
    async def transform_cube(self, ctx: Context, attachment: Optional[str] = None):
        """
        Wrap image around a 3D cube
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.cube(url)
                await ctx.send(file=File(BytesIO(buffer), "cube.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="flag2")
    @max_concurrency(1, BucketType.member)
    async def transform_flag2(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create a waving flag effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.flag(url)
                await ctx.send(file=File(BytesIO(buffer), "flag.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="soap")
    @max_concurrency(1, BucketType.member)
    async def transform_soap(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a soap bubble effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.soap(url)
                await ctx.send(file=File(BytesIO(buffer), "soap.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="tiles")
    @max_concurrency(1, BucketType.member)
    async def transform_tiles(self, ctx: Context, attachment: Optional[str] = None):
        """
        Split image into rotating tiles
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.tiles(url)
                await ctx.send(file=File(BytesIO(buffer), "tiles.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="tv")
    @max_concurrency(1, BucketType.member)
    async def transform_tv(self, ctx: Context, attachment: Optional[str] = None):
        """
        Display image on a TV screen
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.tv(url)
                await ctx.send(file=File(BytesIO(buffer), "tv.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @transform.command(name="wall")
    @max_concurrency(1, BucketType.member)
    async def transform_wall(self, ctx: Context, attachment: Optional[str] = None):
        """
        Project image onto a wall
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.wall(url)
                await ctx.send(file=File(BytesIO(buffer), "wall.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @hybrid_group(name="scene")
    async def scene(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @scene.command(name="ace")
    @max_concurrency(1, BucketType.member)
    async def scene_ace(
        self, 
        ctx: Context,
        side: str,
        *, 
        text: str
    ):
        """
        Create an Ace Attorney text bubble.
        """
        
        side = side.lower()
        if side not in ["attorney", "prosecutor"]:
            return await ctx.warn("Side must be either `attorney` or `prosecutor`")

        async with ctx.typing():
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.ace(ctx.author.name, side, text)
                await ctx.send(file=File(BytesIO(buffer), "ace.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @scene.command(name="scrapbook")
    @max_concurrency(1, BucketType.member)
    async def scene_scrapbook(self, ctx: Context, *, text: str):
        async with ctx.typing():
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.scrapbook(text)
                await ctx.send(file=File(BytesIO(buffer), "scrapbook.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @group(name="render")
    async def render(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @render.command(name="cartoon")
    @max_concurrency(1, BucketType.member)
    async def render_cartoon(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a cartoon style effect.
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.cartoon(url)
                await ctx.send(file=File(BytesIO(buffer), "cartoon.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="cinema")
    @max_concurrency(1, BucketType.member)
    async def render_cinema(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a cinema style effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.cinema(url)
                await ctx.send(file=File(BytesIO(buffer), "cinema.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="console")
    @max_concurrency(1, BucketType.member)
    async def render_console(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a console style effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.console(url)
                await ctx.send(file=File(BytesIO(buffer), "console.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="contour")
    @max_concurrency(1, BucketType.member)
    async def render_contour(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a contour effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.contour(url)
                await ctx.send(file=File(BytesIO(buffer), "contour.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="dither")
    @max_concurrency(1, BucketType.member)
    async def render_dither(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a dither effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.dither(url)
                await ctx.send(file=File(BytesIO(buffer), "dither.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="emojify")
    @max_concurrency(1, BucketType.member)
    async def render_emojify(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add an emojify effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.emojify(url)
                await ctx.send(file=File(BytesIO(buffer), "emojify.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="gameboy")
    @max_concurrency(1, BucketType.member)
    async def render_gameboy(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a Gameboy style effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.gameboy(url)
                await ctx.send(file=File(BytesIO(buffer), "gameboy.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="halfinvert")
    @max_concurrency(1, BucketType.member)
    async def render_halfinvert(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a half invert effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.half_invert(url)
                await ctx.send(file=File(BytesIO(buffer), "halfinvert.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="knit")
    @max_concurrency(1, BucketType.member)
    async def render_knit(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a knit effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.knit(url)
                await ctx.send(file=File(BytesIO(buffer), "knit.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="letters")
    @max_concurrency(1, BucketType.member)
    async def render_letters(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a letters effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.letters(url)
                await ctx.send(file=File(BytesIO(buffer), "letters.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="lines")
    @max_concurrency(1, BucketType.member)
    async def render_lines(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a lines effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.lines(url)
                await ctx.send(file=File(BytesIO(buffer), "lines.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="lsd")
    @max_concurrency(1, BucketType.member)
    async def render_lsd(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a LSD effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.lsd(url)
                await ctx.send(file=File(BytesIO(buffer), "lsd.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="matrix")
    @max_concurrency(1, BucketType.member)
    async def render_matrix(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a matrix effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.matrix(url)
                await ctx.send(file=File(BytesIO(buffer), "matrix.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="minecraft")
    @max_concurrency(1, BucketType.member)
    async def render_minecraft(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a Minecraft style effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.minecraft(url)
                await ctx.send(file=File(BytesIO(buffer), "minecraft.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="neon")
    @max_concurrency(1, BucketType.member)
    async def render_neon(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a neon effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.neon(url)
                await ctx.send(file=File(BytesIO(buffer), "neon.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="optics")
    @max_concurrency(1, BucketType.member)
    async def render_optics(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add an optics effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.optics(url)
                await ctx.send(file=File(BytesIO(buffer), "optics.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="painting")
    @max_concurrency(1, BucketType.member)
    async def render_painting(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a painting effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.painting(url)
                await ctx.send(file=File(BytesIO(buffer), "painting.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="pattern")
    @max_concurrency(1, BucketType.member)
    async def render_pattern(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a pattern effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.pattern(url)
                await ctx.send(file=File(BytesIO(buffer), "pattern.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @render.command(name="poly")
    @max_concurrency(1, BucketType.member)
    async def render_poly(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add a poly effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.poly(url)
                await ctx.send(file=File(BytesIO(buffer), "poly.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @hybrid_group(name="overlay")
    async def overlay(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @overlay.command(name="blocks")
    @max_concurrency(1, BucketType.member)
    async def overlay_blocks(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add floating blocks overlay
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.blocks(url)
                await ctx.send(file=File(BytesIO(buffer), "blocks.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="cow")
    @max_concurrency(1, BucketType.member)
    async def overlay_cow(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add cow pattern overlay
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.cow(url)
                await ctx.send(file=File(BytesIO(buffer), "cow.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="equations")
    @max_concurrency(1, BucketType.member)
    async def overlay_equations(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add mathematical equations overlay
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.equations(url)
                await ctx.send(file=File(BytesIO(buffer), "equations.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="flush")
    @max_concurrency(1, BucketType.member)
    async def overlay_flush(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add toilet flush effect overlay
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.flush(url)
                await ctx.send(file=File(BytesIO(buffer), "flush.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="gallery")
    @max_concurrency(1, BucketType.member)
    async def overlay_gallery(self, ctx: Context, attachment: Optional[str] = None):
        """
        Display image in an art gallery setting
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.gallery(url)
                await ctx.send(file=File(BytesIO(buffer), "gallery.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="globe")
    @max_concurrency(1, BucketType.member)
    async def overlay_globe(self, ctx: Context, attachment: Optional[str] = None):
        """
        Place image on a rotating globe
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.globe(url)
                await ctx.send(file=File(BytesIO(buffer), "globe.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="ipcam")
    @max_concurrency(1, BucketType.member)
    async def overlay_ipcam(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add security camera overlay effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.ipcam(url)
                await ctx.send(file=File(BytesIO(buffer), "ipcam.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="kanye")
    @max_concurrency(1, BucketType.member)
    async def overlay_kanye(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add Kanye West album cover style
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.kanye(url)
                await ctx.send(file=File(BytesIO(buffer), "kanye.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="lamp")
    @max_concurrency(1, BucketType.member)
    async def overlay_lamp(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add glowing lamp lighting effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.lamp(url)
                await ctx.send(file=File(BytesIO(buffer), "lamp.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="laundry")
    @max_concurrency(1, BucketType.member)
    async def overlay_laundry(self, ctx: Context, attachment: Optional[str] = None):
        """
        Place image in washing machine animation
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.laundry(url)
                await ctx.send(file=File(BytesIO(buffer), "laundry.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="layers")
    @max_concurrency(1, BucketType.member)
    async def overlay_layers(self, ctx: Context, attachment: Optional[str] = None):
        """
        Create layered depth effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.layers(url)
                await ctx.send(file=File(BytesIO(buffer), "layers.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="logoff")
    @max_concurrency(1, BucketType.member)
    async def overlay_logoff(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add Windows logoff screen effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.logoff(url)
                await ctx.send(file=File(BytesIO(buffer), "logoff.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="magnify")
    @max_concurrency(1, BucketType.member)
    async def overlay_magnify(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add magnifying glass effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.magnify(url)
                await ctx.send(file=File(BytesIO(buffer), "magnify.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="paparazzi")
    @max_concurrency(1, BucketType.member)
    async def overlay_paparazzi(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add paparazzi camera effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.paparazzi(url)
                await ctx.send(file=File(BytesIO(buffer), "paparazzi.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="phase")
    @max_concurrency(1, BucketType.member)
    async def overlay_phase(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add phase effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.phase(url)
                await ctx.send(file=File(BytesIO(buffer), "phase.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="phone")
    @max_concurrency(1, BucketType.member)
    async def overlay_phone(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add phone camera effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.phone(url)
                await ctx.send(file=File(BytesIO(buffer), "phone.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="plank")
    @max_concurrency(1, BucketType.member)
    async def overlay_plank(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add plank effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.plank(url)
                await ctx.send(file=File(BytesIO(buffer), "plank.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="plates")
    @max_concurrency(1, BucketType.member)
    async def overlay_plates(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add plates effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.plates(url)
                await ctx.send(file=File(BytesIO(buffer), "plates.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="pyramid")
    @max_concurrency(1, BucketType.member)
    async def overlay_pyramid(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add pyramid effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.pyramid(url)
                await ctx.send(file=File(BytesIO(buffer), "pyramid.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="radiate")
    @max_concurrency(1, BucketType.member)
    async def overlay_radiate(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add radiate effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.radiate(url)
                await ctx.send(file=File(BytesIO(buffer), "radiate.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="reflection")
    @max_concurrency(1, BucketType.member)
    async def overlay_reflection(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add reflection effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.reflection(url)
                await ctx.send(file=File(BytesIO(buffer), "reflection.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="ripped")
    @max_concurrency(1, BucketType.member)
    async def overlay_ripped(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add ripped effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.ripped(url)
                await ctx.send(file=File(BytesIO(buffer), "ripped.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @overlay.command(name="shear")
    @max_concurrency(1, BucketType.member)
    async def overlay_shear(self, ctx: Context, attachment: Optional[str] = None):
        """
        Add shear effect
        """
        async with ctx.typing():
            url = await self._get_media_url(ctx, attachment, accept_image=True) or ctx.author.display_avatar.url
            try:
                jeyy_api = JeyyAPI()
                buffer = await jeyy_api.shear(url)
                await ctx.send(file=File(BytesIO(buffer), "shear.gif"))
            except CommandOnCooldown as e:
                await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")
            except Exception as e:
                await ctx.warn(f"An error occurred: {str(e)}")

    @group(name="wyr", aliases=["wouldyourather"], invoke_without_command=True)
    async def wyr(self, ctx: Context, rating: str = "pg13"):
        """Get a random would you rather question
        
        Rating can be pg13 or r (NSFW channels only)"""
        rating = rating.lower()
        
        if rating not in ["pg13", "r"]:
            return await ctx.warn("Rating must be either pg13 or r")
        
        if rating == "r" and not (isinstance(ctx.channel, discord.TextChannel) and ctx.channel.is_nsfw()):
            return await ctx.warn("R-rated questions can only be used in NSFW channels!")
        
        async with self.bot.session.get(f"https://api.truthordarebot.xyz/v1/wyr?rating={rating}") as resp:
            if not resp.ok:
                return await ctx.warn("Failed to fetch a question! Try again later.")
            
            data = await resp.json()
            await self._save_to_cache("wyr", rating, data["question"])
            
            embed = discord.Embed(
                title="Would You Rather...",
                description=data["question"],
                color=ctx.color
            )
            embed.set_footer(text=f"Rating: {data['rating'].upper()} • evict.bot")
            return await ctx.send(embed=embed)

    @wyr.command(name="add")
    @has_permissions(manage_channels=True)
    async def wyr_add(self, ctx: Context, channel: Optional[TextChannel] = None, rating: str = "pg13"):
        """Set a channel for automatic WYR questions (max 10 channels)
        
        Rating can be pg13 or r (NSFW channels only)"""

        channel = channel or ctx.channel
        rating = rating.lower()
        
        if rating not in ["pg13", "r"]:
            return await ctx.warn("Rating must be either pg13 or r")
        
        if rating == "r" and not channel.is_nsfw():
            return await ctx.warn("R-rated questions can only be sent to NSFW channels!")
        
        channel_count = await self.bot.db.fetchval(
            """
            SELECT COUNT(*) FROM fun.wyr_channels
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if channel_count >= 10:
            return await ctx.warn("Maximum of 10 channels reached! Remove some channels first.")
        
        await self.bot.db.execute(
            """
            INSERT INTO fun.wyr_channels (guild_id, channel_id, rating)
            VALUES ($1, $2, $3)
            """,
            ctx.guild.id, channel.id, rating
        )
        await ctx.approve(f"Now sending automatic {rating.upper()} WYR questions in {channel.mention}")

    @wyr.command(name="remove")
    @has_permissions(manage_channels=True)
    async def wyr_remove(self, ctx: Context, channel: Optional[TextChannel] = None):
        """Remove a channel from automatic WYR questions"""
        channel = channel or ctx.channel
        
        result = await self.bot.db.execute(
            """
            DELETE FROM fun.wyr_channels
            WHERE guild_id = $1 AND channel_id = $2
            """,
            ctx.guild.id, channel.id
        )
        
        if result == "DELETE 0":
            return await ctx.warn(f"No WYR configuration found for {channel.mention}")
            
        await ctx.approve(f"Removed {channel.mention} from automatic WYR questions")


    @tasks.loop(seconds=120)
    async def send_random_wyr(self):
        """Send random would you rather questions to configured channels"""
        
        channels = await self.bot.db.fetch(
            """
            SELECT channel_id, rating FROM fun.wyr_channels
            """
        )
        
        for i in range(0, len(channels), 5):
            chunk = channels[i:i+5]
            
            for record in chunk:
                channel = self.bot.get_channel(record['channel_id'])
                if not channel:
                    continue
                
                async with self.bot.session.get(f"https://api.truthordarebot.xyz/v1/wyr?rating={record['rating']}") as resp:
                    if not resp.ok:
                        continue
                    
                    data = await resp.json()
                    
                    cache_file = f"data/cache/wyr_{record['rating']}.json"
                    try:
                        if not os.path.exists("data/cache"):
                            os.makedirs("data/cache")
                        
                        if os.path.exists(cache_file):
                            with open(cache_file, 'r') as f:
                                questions = json.load(f)
                        else:
                            questions = []
                        
                        if data["question"] not in questions:
                            questions.append(data["question"])
                            with open(cache_file, 'w') as f:
                                json.dump(questions, f, indent=4)
                    except Exception:
                        pass
                    
                    embed = discord.Embed(
                        title="Would You Rather...",
                        description=data["question"]
                    )
                    embed.set_footer(text=f"Rating: {data['rating'].upper()} • evict.bot")
                    await channel.send(embed=embed)
            
            if i + 5 < len(channels):
                await asyncio.sleep(5)

    @command(name="truth")
    async def truth(self, ctx: Context, rating: str = "pg13"):
        """Get a random truth question
        
        Rating can be pg13 or r (NSFW channels only)"""

        rating = rating.lower()
        
        if rating not in ["pg13", "r"]:
            return await ctx.warn("Rating must be either pg13 or r")
        
        if rating == "r" and not (isinstance(ctx.channel, discord.TextChannel) and ctx.channel.is_nsfw()):
            return await ctx.warn("R-rated questions can only be used in NSFW channels!")
        
        async with self.bot.session.get(f"https://api.truthordarebot.xyz/v1/truth?rating={rating}") as resp:
            if not resp.ok:
                return await ctx.warn("Failed to fetch a question! Try again later.")
            
            data = await resp.json()
            await self._save_to_cache("truth", rating, data["question"])
            
            embed = discord.Embed(title="Truth", description=data["question"], color=ctx.color)
            embed.set_footer(text=f"Rating: {data['rating'].upper()} • evict.bot")
            return await ctx.send(embed=embed, view=TruthDareView(self.bot, rating))

    @command(name="dare")
    async def dare(self, ctx: Context, rating: str = "pg13"):
        """Get a random dare
        
        Rating can be pg13 or r (NSFW channels only)"""

        rating = rating.lower()
        
        if rating not in ["pg13", "r"]:
            return await ctx.warn("Rating must be either pg13 or r")
        
        if rating == "r" and not (isinstance(ctx.channel, discord.TextChannel) and ctx.channel.is_nsfw()):
            return await ctx.warn("R-rated dares can only be used in NSFW channels!")
        
        async with self.bot.session.get(f"https://api.truthordarebot.xyz/v1/dare?rating={rating}") as resp:
            if not resp.ok:
                return await ctx.warn("Failed to fetch a dare! Try again later.")
            
            data = await resp.json()
            await self._save_to_cache("dare", rating, data["question"])
            
            embed = discord.Embed(title="Dare", description=data["question"], color=ctx.color)
            embed.set_footer(text=f"Rating: {data['rating'].upper()} • evict.bot")
            return await ctx.send(embed=embed, view=TruthDareView(self.bot, rating))

    async def _save_to_cache(self, question_type: str, rating: str, question: str):
        """Save a question to the appropriate cache file"""
        cache_file = f"data/cache/{question_type}_{rating}.json"
        
        try:
            if not os.path.exists("data/cache"):
                os.makedirs("data/cache")
                
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    questions = json.load(f)
            else:
                questions = []
                
            if question not in questions:
                questions.append(question)
                with open(cache_file, 'w') as f:
                    json.dump(questions, f, indent=4)
        except Exception:
            pass

    @group(name="streak", invoke_without_command=True)
    async def streak(self, ctx: Context):
        """View your current streak information"""
        
        await self._check_booster_status(ctx.guild.id, ctx.author.id)
        
        data = await self.bot.db.fetchrow(
            """
            SELECT current_streak, highest_streak, last_streak_time, restores_available, total_images_sent
            FROM streaks.users
            WHERE guild_id = $1 AND user_id = $2
            """,
            ctx.guild.id,
            ctx.author.id
        )
        
        if not data:
            return await ctx.warn("You haven't started a streak yet!")
            
        embed = Embed(title="Streak Statistics")
        embed.add_field(name="Current Streak", value=f"{data['current_streak']:,} days", inline=True)
        embed.add_field(name="Highest Streak", value=f"{data['highest_streak']:,} days", inline=True)
        embed.add_field(name="Restore Tokens", value=f"{data['restores_available']:,}", inline=True)
        embed.add_field(name="Total Images", value=f"{data['total_images_sent']:,}", inline=True)
        
        if data['last_streak_time']:
            embed.add_field(
                name="Last Image",
                value=f"{format_dt(data['last_streak_time'])} ({format_dt(data['last_streak_time'], 'R')})",
                inline=False
            )
            
        return await ctx.send(embed=embed)

    @streak.command(name="setup", example="#streaks")
    @has_permissions(manage_guild=True)
    async def streak_setup(self, ctx: Context, channel: TextChannel):
        """Setup the streak channel for your server"""
        
        await self.bot.db.execute(
            """
            INSERT INTO streaks.config (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) 
            DO UPDATE SET channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id
        )
        
        return await ctx.approve(f"Streak channel set to {channel.mention}")

    @streak.command(name="restore")
    async def streak_restore(self, ctx: Context):
        """Restore your streak using a restore token"""
        
        await self._check_booster_status(ctx.guild.id, ctx.author.id)
        
        data = await self.bot.db.fetchrow(
            """
            SELECT restores_available, current_streak
            FROM streaks.users
            WHERE guild_id = $1 AND user_id = $2
            """,
            ctx.guild.id,
            ctx.author.id
        )
        
        if not data or data['restores_available'] <= 0:
            return await ctx.warn("You don't have any restore tokens!")
            
        if data['current_streak'] > 0:
            return await ctx.warn("Your streak isn't broken!")
            
        await self.bot.db.execute(
            """
            UPDATE streaks.users 
            SET 
                current_streak = 1,
                last_streak_time = CURRENT_TIMESTAMP,
                restores_available = restores_available - 1
            WHERE guild_id = $1 AND user_id = $2
            """,
            ctx.guild.id,
            ctx.author.id
        )
        
        await self.bot.db.execute(
            """
            INSERT INTO streaks.restore_log (guild_id, user_id, restored_by, previous_streak)
            VALUES ($1, $2, $3, $4)
            """,
            ctx.guild.id,
            ctx.author.id,
            "restore",
            0
        )
        
        return await ctx.approve("Successfully restored your streak!")

    @streak.command(name="emoji")
    @has_permissions(manage_guild=True)
    async def streak_emoji(self, ctx: Context, emoji: str):
        """Set the streak reaction emoji"""
        
        if len(emoji) > 2 and not emoji.startswith("<"):
            return await ctx.warn("Please provide a valid emoji!")
            
        await self.bot.db.execute(
            """
            UPDATE streaks.config 
            SET streak_emoji = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            emoji
        )
        
        return await ctx.approve(f"Streak emoji set to {emoji}")

    @streak.command(name="leaderboard", aliases=["lb"])
    async def streak_leaderboard(self, ctx: Context, type: str = "server"):
        """View the streak leaderboard
        
        Example: streak lb global"""
        
        if type.lower() not in ("server", "global"):
            return await ctx.warn("Type must be either server or global!")
            
        query = """
            SELECT 
                user_id,
                current_streak,
                highest_streak,
                total_images_sent
            FROM streaks.users
            """
            
        if type.lower() == "server":
            query += " WHERE guild_id = $1"
            args = [ctx.guild.id]
        else:
            args = []
            
        query += " ORDER BY current_streak DESC, highest_streak DESC LIMIT 100"
        
        data = await self.bot.db.fetch(query, *args)
        
        if not data:
            return await ctx.warn(f"No streak data found for {type}!")
            
        entries = []
        for index, record in enumerate(data, 1):
            user = self.bot.get_user(record['user_id'])
            if not user:
                continue
                
            entries.append(
                f"`{index}` **{user}** - {record['current_streak']:,} days "
                f"(Highest: {record['highest_streak']:,}, Total: {record['total_images_sent']:,})"
            )
            
        paginator = Paginator(
            ctx,
            entries=entries,
            per_page=10,
            embed=Embed(title=f"Streak Leaderboard ({type.title()})")
        )
        
        return await paginator.start()

    @streak.command(name="logs")
    @has_permissions(manage_guild=True)
    async def streak_logs(self, ctx: Context, channel: TextChannel):
        """Set the channel for streak notifications
        
        Example: streak logs #streak-logs"""
        
        await self.bot.db.execute(
            """
            UPDATE streaks.config 
            SET notification_channel_id = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            channel.id
        )
        
        return await ctx.approve(f"Streak notifications will be sent to {channel.mention}")

    @streak.command(name="imageonly", example="on")
    @has_permissions(manage_guild=True)
    async def streak_imageonly(self, ctx: Context, enabled: bool):
        """Toggle image-only mode for streak channel
        
        Example: streak imageonly true"""
        
        await self.bot.db.execute(
            """
            INSERT INTO streaks.config (guild_id, image_only)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) 
            DO UPDATE SET image_only = EXCLUDED.image_only
            """,
            ctx.guild.id,
            enabled
        )
        
        status = "enabled" if enabled else "disabled"
        return await ctx.approve(f"Image-only mode {status} for streak channel")

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        """Update restore tokens when boost count changes"""
        if before.premium_since == after.premium_since:
            return
            
        old_boost_count = sum(1 for m in before.guild.premium_subscribers if m.id == before.id)
        new_boost_count = sum(1 for m in after.guild.premium_subscribers if m.id == after.id)
        
        if new_boost_count > old_boost_count:
            boost_difference = new_boost_count - old_boost_count
            
            await self.bot.db.execute(
                """
                INSERT INTO streaks.users (guild_id, user_id, restores_available)
                VALUES ($1, $2, $3)
                ON CONFLICT (guild_id, user_id) DO UPDATE SET
                    restores_available = streaks.users.restores_available + $3
                """,
                after.guild.id,
                after.id,
                boost_difference
            )

    async def _check_booster_status(self, guild_id: int, user_id: int):
        """Check and update restore tokens for a user if they're a booster"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
            
        member = guild.get_member(user_id)
        if not member or not member.premium_since:
            return
            
        await self.bot.db.execute(
            """
            INSERT INTO streaks.users (guild_id, user_id, restores_available)
            VALUES ($1, $2, 1)
            ON CONFLICT (guild_id, user_id) DO UPDATE SET
                restores_available = 1
            WHERE streaks.users.restores_available = 0
            """,
            guild_id,
            user_id
        )

    @group(name="counting", invoke_without_command=True)
    async def counting(self, ctx: Context):
        """View current counting configuration"""
        
        config = await self.bot.db.fetchrow(
            """
            SELECT channel_id, current_count, high_score, safe_mode, allow_fails,
                   success_emoji, fail_emoji
            FROM counting.config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not config:
            return await ctx.warn("Counting is not set up in this server!")
            
        channel = ctx.guild.get_channel(config['channel_id'])
        if not channel:
            return await ctx.warn("Counting channel has been deleted!")
            
        embed = Embed(title="Counting Configuration")
        embed.add_field(name="Channel", value=channel.mention)
        embed.add_field(name="Current Count", value=str(config['current_count']))
        embed.add_field(name="High Score", value=str(config['high_score']))
        embed.add_field(name="Safe Mode", value="Enabled" if config['safe_mode'] else "Disabled")
        embed.add_field(name="Allow Fails", value="Enabled" if config['allow_fails'] else "Disabled")
        embed.add_field(name="Success Emoji", value=config['success_emoji'])
        embed.add_field(name="Fail Emoji", value=config['fail_emoji'])
        
        return await ctx.send(embed=embed)

    @counting.command(name="setup", example="#counting")
    @has_permissions(manage_guild=True)
    async def counting_setup(self, ctx: Context, channel: TextChannel):
        """Set up the counting channel
        
        Example: counting setup #counting"""
        
        await self.bot.db.execute(
            """
            INSERT INTO counting.config (guild_id, channel_id)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) 
            DO UPDATE SET channel_id = $2
            """,
            ctx.guild.id,
            channel.id
        )
        
        return await ctx.approve(f"Set {channel.mention} as the counting channel")

    @counting.command(name="remove")
    @has_permissions(manage_guild=True)
    async def counting_remove(self, ctx: Context):
        """Remove the counting channel"""
        
        deleted = await self.bot.db.execute(
            """
            DELETE FROM counting.config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if deleted == "DELETE 0":
            return await ctx.warn("Counting is not set up in this server!")
            
        return await ctx.approve("Removed counting configuration")

    @counting.command(name="reset")
    @has_permissions(manage_guild=True)
    async def counting_reset(self, ctx: Context):
        """Reset the count to 0"""
        
        updated = await self.bot.db.execute(
            """
            UPDATE counting.config
            SET current_count = 0, last_user_id = NULL
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if updated == "UPDATE 0":
            return await ctx.warn("Counting is not set up in this server!")
            
        return await ctx.approve("Reset count to 0")

    @counting.command(name="safemode", example="false")
    @has_permissions(manage_guild=True)
    async def counting_safemode(self, ctx: Context, enabled: bool):
        """Toggle safe mode (only allows pure numbers)
        
        Example: counting safemode true"""
        
        await self.bot.db.execute(
            """
            UPDATE counting.config
            SET safe_mode = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            enabled
        )
        
        status = "enabled" if enabled else "disabled"
        return await ctx.approve(f"Safe mode {status}")

    @counting.command(name="allowfails", example="true")
    @has_permissions(manage_guild=True)
    async def counting_allowfails(self, ctx: Context, enabled: bool):
        """Toggle whether counting can continue after wrong numbers
        
        Example: counting allowfails true"""
        
        await self.bot.db.execute(
            """
            UPDATE counting.config
            SET allow_fails = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            enabled
        )
        
        status = "enabled" if enabled else "disabled"
        return await ctx.approve(f"Allow fails {status}")

    @counting.command(name="highscore")
    async def counting_highscore(self, ctx: Context):
        """View the server's highest count"""
        
        score = await self.bot.db.fetchval(
            """
            SELECT high_score
            FROM counting.config
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )
        
        if not score:
            return await ctx.warn("No high score recorded yet!")
            
        return await ctx.neutral(f"Server high score: {score:,}")

    @counting.command(name="setemoji", example="success 🎯")
    @has_permissions(manage_guild=True)
    async def counting_setemoji(self, ctx: Context, type: str, emoji: str):
        """Set custom reaction emojis for correct/wrong numbers
        
        Example: counting setemoji success 🎯"""
        
        type = type.lower()
        if type not in ("success", "fail"):
            return await ctx.warn("Type must be either success or fail!")
            
        if len(emoji) > 2 and not emoji.startswith("<"):
            return await ctx.warn("Please provide a valid emoji!")
            
        column = "success_emoji" if type == "success" else "fail_emoji"
        
        await self.bot.db.execute(
            f"""
            UPDATE counting.config
            SET {column} = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            emoji
        )
        
        return await ctx.approve(f"Set {type} emoji to {emoji}")

    @command(name="marry")
    async def marry(self, ctx: Context, member: Member):
        """Propose marriage to another member"""
        if member.id == ctx.author.id:
            return await ctx.warn("You cannot marry yourself!")

        existing = await self.bot.db.fetchrow(
            """SELECT * FROM family.marriages 
            WHERE (user_id = $1 OR partner_id = $1) AND active = true""",
            ctx.author.id
        )
        if existing:
            return await ctx.warn("You are already married!")

        partner_married = await self.bot.db.fetchrow(
            """SELECT * FROM family.marriages 
            WHERE (user_id = $1 OR partner_id = $1) AND active = true""",
            member.id
        )
        if partner_married:
            return await ctx.warn(f"{member.name} is already married!")

        related = await self.bot.db.fetchrow(
            """SELECT * FROM family.members 
            WHERE user_id = $1 AND related_id = $2""",
            ctx.author.id, member.id
        )
        if related:
            return await ctx.warn("You cannot marry a family member!")

        self.proposal_cache[member.id] = ctx.author.id

        view = discord.ui.View(timeout=60)  
        accept = discord.ui.Button(label="Accept", style=discord.ButtonStyle.green)
        decline = discord.ui.Button(label="Decline", style=discord.ButtonStyle.red)

        async def accept_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                return await interaction.response.send_message("This isn't your proposal!", ephemeral=True)

            await self.bot.db.execute(
                """INSERT INTO family.marriages (user_id, partner_id)
                VALUES ($1, $2), ($2, $1)""",
                ctx.author.id, member.id
            )
            
            await interaction.message.edit(
                content=f"💝 {ctx.author.mention} and {member.mention} are now married!", 
                view=None
            )
            del self.proposal_cache[member.id]

        async def decline_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                return await interaction.response.send_message("This isn't your proposal!", ephemeral=True)

            await interaction.message.edit(
                content=f"💔 {member.mention} declined the proposal", 
                view=None
            )
            del self.proposal_cache[member.id]

        async def timeout_callback():
            if member.id in self.proposal_cache:
                del self.proposal_cache[member.id]
                await ctx.message.edit(
                    content=f"💤 Marriage proposal to {member.mention} has expired",
                    view=None
                )

        accept.callback = accept_callback
        decline.callback = decline_callback
        view.on_timeout = timeout_callback

        view.add_item(accept)
        view.add_item(decline)

        await ctx.send(
            f"💍 {ctx.author.mention} has proposed to {member.mention}! Do you accept?",
            view=view
        )

    @command(name="divorce")
    async def divorce(self, ctx: Context, member: Member):
        """Divorce your spouse"""
        marriage = await self.bot.db.fetchrow(
            """SELECT * FROM family.marriages 
            WHERE user_id = $1 AND partner_id = $2 AND active = true""",
            ctx.author.id, member.id
        )

        if not marriage:
            return await ctx.warn("You are not married to this person!")

        await self.bot.db.execute(
            """UPDATE family.marriages 
            SET active = false 
            WHERE (user_id = $1 AND partner_id = $2) 
            OR (user_id = $2 AND partner_id = $1)""",
            ctx.author.id, member.id
        )

        await ctx.send(f"💔 {ctx.author.mention} has divorced {member.mention}")

    @command(name="marriage")
    async def marriage(self, ctx: Context, member: Member = None):
        """View marriage status"""
        member = member or ctx.author

        marriages = await self.bot.db.fetch(
            """SELECT * FROM family.marriages 
            WHERE (user_id = $1 OR partner_id = $1) 
            AND active = true""",
            member.id
        )

        if not marriages:
            return await ctx.send(f"{member.name} is not married")

        embed = Embed(title=f"{member.name}'s Marriage Status")
        
        for marriage in marriages:
            partner_id = marriage['partner_id'] if marriage['user_id'] == member.id else marriage['user_id']
            partner = ctx.guild.get_member(partner_id)
            if partner:
                date = marriage['marriage_date'].strftime("%Y-%m-%d")
                embed.add_field(
                    name=f"Married to {partner.name}",
                    value=f"Since: {date}",
                    inline=False
                )

        await ctx.send(embed=embed)

    @command(name="spouses")
    async def spouses(self, ctx: Context, member: Member = None):
        """List all current spouses"""
        member = member or ctx.author

        spouses = await self.bot.db.fetch(
            """SELECT partner_id, marriage_date FROM family.marriages 
            WHERE user_id = $1 AND active = true""",
            member.id
        )

        if not spouses:
            return await ctx.warn(f"{member.name} is not married to anyone")

        embed = Embed(title=f"{member.name}'s Spouses")
        for record in spouses:
            spouse = ctx.guild.get_member(record['partner_id'])
            if spouse:
                date = record['marriage_date'].strftime("%Y-%m-%d")
                embed.add_field(
                    name=spouse.name,
                    value=f"Married since: {date}",
                    inline=False
                )

        await ctx.send(embed=embed)

    @command(name="adopt")
    async def adopt(self, ctx: Context, member: Member):
        """Adopt another member"""
        existing = await self.bot.db.fetchrow(
            """SELECT * FROM family.members 
            WHERE (user_id = $1 AND related_id = $2) 
            OR (user_id = $2 AND related_id = $1)""",
            ctx.author.id, member.id
        )
        if existing:
            return await ctx.warn("You are already family!")

        if await self.bot.db.fetchrow(
            """SELECT * FROM family.marriages 
            WHERE (user_id = $1 AND partner_id = $2) 
            OR (user_id = $2 AND partner_id = $1) AND active = true""",
            ctx.author.id, member.id
        ):
            return await ctx.warn("You cannot adopt your spouse!")

        view = discord.ui.View()
        accept = discord.ui.Button(label="Accept", style=discord.ButtonStyle.green)
        decline = discord.ui.Button(label="Decline", style=discord.ButtonStyle.red)

        async def accept_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                return await interaction.response.send_message(
                    "This isn't your adoption request!", 
                    ephemeral=True
                )

            await self.bot.db.execute(
                """INSERT INTO family.members (user_id, related_id, relationship)
                VALUES ($1, $2, 'parent'), ($2, $1, 'child')""",
                ctx.author.id, member.id
            )
            
            await interaction.message.edit(
                content=f"👨‍👦 {ctx.author.mention} has adopted {member.mention}!", 
                view=None
            )

        async def decline_callback(interaction: discord.Interaction):
            if interaction.user.id != member.id:
                return await interaction.response.send_message(
                    "This isn't your adoption request!", 
                    ephemeral=True
                )

            await interaction.message.edit(
                content=f"😢 {member.mention} declined the adoption", 
                view=None
            )

        accept.callback = accept_callback
        decline.callback = decline_callback
        view.add_item(accept)
        view.add_item(decline)

        await ctx.send(
            f"👶 {ctx.author.mention} wants to adopt {member.mention}! Do you accept?",
            view=view
        )

    @command(name="disown")
    async def disown(self, ctx: Context, member: Member):
        """Disown an adopted member"""
        relationship = await self.bot.db.fetchrow(
            """SELECT relationship FROM family.members 
            WHERE user_id = $1 AND related_id = $2""",
            ctx.author.id, member.id
        )

        if not relationship or relationship['relationship'] != 'parent':
            return await ctx.warn("This person is not your child!")

        await self.bot.db.execute(
            """DELETE FROM family.members 
            WHERE (user_id = $1 AND related_id = $2) 
            OR (user_id = $2 AND related_id = $1)""",
            ctx.author.id, member.id
        )

        await ctx.send(f"😢 {ctx.author.mention} has disowned {member.mention}")

    @group(name="family", invoke_without_command=True)
    async def family(self, ctx: Context, member: Member = None):
        """View family information"""
        member = member or ctx.author

        family = await self.bot.db.fetch(
            """SELECT related_id, relationship FROM family.members 
            WHERE user_id = $1""",
            member.id
        )

        if not family:
            return await ctx.send(f"{member.name} has no family")

        embed = Embed(title=f"{member.name}'s Family")
        
        for relation in ('parent', 'child', 'sibling'):
            members = [
                ctx.guild.get_member(r['related_id']) 
                for r in family 
                if r['relationship'] == relation
            ]
            if members:
                embed.add_field(
                    name=f"{relation.title()}s",
                    value="\n".join(m.mention for m in members if m),
                    inline=False
                )

        await ctx.send(embed=embed)

    @family.command(name="leave")
    async def family_leave(self, ctx: Context):
        """Leave your family"""
        family = await self.bot.db.fetch(
            """SELECT related_id, relationship FROM family.members 
            WHERE user_id = $1""",
            ctx.author.id
        )

        if not family:
            return await ctx.warn("You don't have a family to leave!")

        await self.bot.db.execute(
            """DELETE FROM family.members 
            WHERE user_id = $1 OR related_id = $1""",
            ctx.author.id
        )

        await ctx.send(f"👋 {ctx.author.mention} has left their family")

    @family.command(name="bank")
    async def family_bank(self, ctx: Context):
        """View shared family bank balance"""
        balance = await self.bot.db.fetchval(
            """
            SELECT COALESCE(SUM(amount), 0) FROM economy.transactions 
            WHERE user_id IN (
                SELECT related_id FROM family.members 
                WHERE user_id = $1
                UNION
                SELECT partner_id FROM family.marriages 
                WHERE user_id = $1 AND active = true
            )
            """,
            ctx.author.id
        )

        embed = Embed(title="Family Bank", color=ctx.color)
        embed.add_field(
            name="Combined Balance",
            value=f"${balance:,}"
        )
        await ctx.send(embed=embed)

    @family.command(name="profile")
    async def family_profile(self, ctx: Context, *, bio: str = None):
        """Set or view family profile"""
        if bio:
            await self.bot.db.execute(
                """
                INSERT INTO family.profiles (user_id, bio)
                VALUES ($1, $2)
                ON CONFLICT (user_id) DO UPDATE
                SET bio = $2
                """,
                ctx.author.id, bio
            )
            return await ctx.approve("Updated family profile!")

        profile = await self.bot.db.fetchrow(
            """
            SELECT bio FROM family.profiles
            WHERE user_id = $1
            """,
            ctx.author.id
        )

        family = await self.bot.db.fetch(
            """
            SELECT related_id, relationship FROM family.members 
            WHERE user_id = $1
            UNION
            SELECT partner_id, 'spouse' FROM family.marriages 
            WHERE user_id = $1 AND active = true
            """,
            ctx.author.id
        )

        embed = Embed(title=f"{ctx.author.name}'s Family Profile", color=ctx.color)
        if profile and profile['bio']:
            embed.description = profile['bio']

        for relation in ('spouse', 'parent', 'child', 'sibling'):
            members = [
                ctx.guild.get_member(r['related_id'])
                for r in family
                if r['relationship'] == relation
            ]
            if members:
                embed.add_field(
                    name=f"{relation.title()}s",
                    value="\n".join(m.mention for m in members if m),
                    inline=False
                )

        await ctx.send(embed=embed)

    @family.command(name="tree")
    async def family_tree(self, ctx: Context, member: Member = None):
        """View family tree"""
        member = member or ctx.author

        BACKGROUND = (9, 9, 11)    
        CARD = (24, 24, 27)         
        MUTED = (39, 39, 42)       
        PRIMARY = (244, 244, 245)   
        ACCENT = (124, 58, 237)     

        width = 1200  
        height = 800 
        img = Image.new('RGB', (width, height), BACKGROUND)
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("/assets/fonts/Monsterrat-Bold.ttf", 20)
        except:
            font = ImageFont.load_default()

        def draw_card(x, y, member_obj, title=None):
            card_width = 200
            card_height = 120
            
            draw.rounded_rectangle(
                [x-card_width//2, y-card_height//2, 
                 x+card_width//2, y+card_height//2],
                radius=12,
                fill=CARD,
                outline=ACCENT,
                width=2
            )

            draw.ellipse(
                [x-30, y-30, x+30, y+30], 
                fill=ACCENT
            )

            draw.text(
                (x, y+45), 
                member_obj.name,
                font=font,
                fill=PRIMARY,
                anchor="mt"
            )

            if title:
                draw.text(
                    (x, y-60),
                    title,
                    font=font,
                    fill=PRIMARY,
                    anchor="mt"
                )

        def draw_connection(start_x, start_y, end_x, end_y):
            spacing = 10
            distance = ((end_x - start_x) ** 2 + (end_y - start_y) ** 2) ** 0.5
            dots = int(distance / spacing)
            
            for i in range(dots):
                progress = i / dots
                x = start_x + (end_x - start_x) * progress
                y = start_y + (end_y - start_y) * progress
                draw.ellipse([x-1, y-1, x+1, y+1], fill=ACCENT)

        center_x = width // 2
        center_y = height // 2
        draw_card(center_x, center_y, member)

        family = await self.bot.db.fetch(
            """
            SELECT related_id, relationship FROM family.members 
            WHERE user_id = $1
            UNION
            SELECT partner_id, 'spouse' FROM family.marriages 
            WHERE user_id = $1 AND active = true
            """,
            member.id
        )

        if family:
            spouse_count = sum(1 for r in family if r['relationship'] == 'spouse')
            if spouse_count:
                spacing = 300
                start_x = center_x + spacing
                for relation in family:
                    if relation['relationship'] == 'spouse':
                        member_id = relation['partner_id']
                        if member_obj := ctx.guild.get_member(member_id):
                            draw_connection(center_x, center_y, start_x, center_y)
                            draw_card(start_x, center_y, member_obj, "Spouse")
                            start_x += spacing

        buffer = BytesIO()
        img.save(buffer, 'PNG')
        buffer.seek(0)
        
        file = discord.File(buffer, filename='family_tree.png')
        await ctx.send(file=file)

    @Cog.listener('on_message')
    async def streaks_counting(self, message: Message):
        if message.author.bot or not message.guild:
            return

        streaks_config = await self.bot.db.fetchrow(
            """
            SELECT channel_id, notification_channel_id, streak_emoji, image_only
            FROM streaks.config
            WHERE guild_id = $1
            """,
            message.guild.id
        )

        if streaks_config and message.channel.id == streaks_config['channel_id']:
            has_image = any(
                att.filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp'))
                for att in message.attachments
            )

            if streaks_config.get('image_only') and not has_image:
                try:
                    await message.delete()
                    return
                except:
                    pass

            if has_image:
                user_data = await self.bot.db.fetchrow(
                    """
                    SELECT current_streak, last_streak_time
                    FROM streaks.users
                    WHERE guild_id = $1 AND user_id = $2
                    """,
                    message.guild.id,
                    message.author.id
                )

                now = datetime.now(timezone.utc)

                if user_data and user_data['last_streak_time']:
                    time_diff = now - user_data['last_streak_time']
                    if time_diff.total_seconds() < 86400:
                        await message.add_reaction(streaks_config['streak_emoji'])
                        return

                    if time_diff.total_seconds() > 172800:
                        if streaks_config['notification_channel_id']:
                            channel = message.guild.get_channel(streaks_config['notification_channel_id'])
                            if channel:
                                await channel.send(
                                    f"{message.author.mention} Your streak of **{user_data['current_streak']}** days has been broken! "
                                    f"Use `streak restore` if you have any restore tokens."
                                )

                await self.bot.db.execute(
                    """
                    INSERT INTO streaks.users (
                        guild_id, user_id, current_streak, highest_streak, 
                        last_streak_time, total_images_sent
                    )
                    VALUES ($1, $2, 1, 1, $3, 1)
                    ON CONFLICT (guild_id, user_id) DO UPDATE SET
                        current_streak = CASE 
                            WHEN streaks.users.last_streak_time IS NULL OR 
                                 $3 - streaks.users.last_streak_time > INTERVAL '48 hours'
                            THEN 1
                            WHEN $3 - streaks.users.last_streak_time > INTERVAL '24 hours'
                            THEN streaks.users.current_streak + 1
                            ELSE streaks.users.current_streak
                        END,
                        highest_streak = GREATEST(
                            streaks.users.highest_streak,
                            CASE 
                                WHEN $3 - streaks.users.last_streak_time > INTERVAL '24 hours'
                                THEN streaks.users.current_streak + 1
                                ELSE streaks.users.current_streak
                            END
                        ),
                        last_streak_time = $3,
                        total_images_sent = streaks.users.total_images_sent + 1
                    """,
                    message.guild.id,
                    message.author.id,
                    now
                )

                await message.add_reaction(streaks_config['streak_emoji'])

        counting_config = await self.bot.db.fetchrow(
            """
            SELECT channel_id, current_count, high_score, safe_mode, allow_fails,
                   last_user_id, success_emoji, fail_emoji
            FROM counting.config
            WHERE guild_id = $1
            """,
            message.guild.id
        )

        if counting_config and message.channel.id == counting_config['channel_id']:
            try:
                if counting_config['safe_mode']:
                    if not message.content.isdigit():
                        await message.delete()
                        return
                    number = int(message.content)
                else:
                    number = int(eval(message.content))
            except:
                await message.delete()
                return

            expected_number = counting_config['current_count'] + 1
            is_correct = number == expected_number

            if message.author.id == counting_config['last_user_id']:
                await message.add_reaction(counting_config['fail_emoji'])
                if not counting_config['allow_fails']:
                    await self.bot.db.execute(
                        """
                        UPDATE counting.config
                        SET current_count = 0, last_user_id = NULL
                        WHERE guild_id = $1
                        """,
                        message.guild.id
                    )
                    await message.reply("You can't count twice in a row! Count reset to 0.")
                return

            if is_correct:
                await message.add_reaction(counting_config['success_emoji'])

                if number % 50 == 0:
                    await message.add_reaction('💯')

                new_count = counting_config['current_count'] + 1
                new_high_score = max(new_count, counting_config['high_score'])

                await self.bot.db.execute(
                    """
                    UPDATE counting.config
                    SET current_count = $2,
                        high_score = $3,
                        last_user_id = $4
                    WHERE guild_id = $1
                    """,
                    message.guild.id,
                    new_count,
                    new_high_score,
                    message.author.id
                )

                if new_count > counting_config['high_score']:
                    await message.reply(f"🎉 New high score: {new_count:,}!")

            else:
                await message.add_reaction(counting_config['fail_emoji'])
                if not counting_config['allow_fails']:
                    await self.bot.db.execute(
                        """
                        UPDATE counting.config
                        SET current_count = 0, last_user_id = NULL
                        WHERE guild_id = $1
                        """,
                        message.guild.id
                    )
                    
                    await message.reply(f"Wrong number! The next number should have been {expected_number}. Count reset to 0.")


    @Cog.listener("on_message")
    async def uwulock_shutup(self, message: Message):
        if not message.guild:
            return

        checks = await self.bot.db.fetch(
            """
            SELECT 'uwulock' as type FROM uwulock WHERE user_id = $1 AND guild_id = $2
            UNION ALL
            SELECT 'shutup' as type FROM shutup WHERE user_id = $1 AND guild_id = $2
            """,
            message.author.id,
            message.guild.id,
        )

        if not checks:
            return

        for check in checks:
            if check['type'] == 'uwulock':
                uwu = uwuipy()
                uwu_message = uwu.uwuify(message.content)
                hook = await self.webhook(message.channel)

                uwulock_key = f"uwulock:{message.author.id}{message.channel.id}"
                if await self.bot.redis.ratelimited(uwulock_key, 3, 2):
                    await asyncio.sleep(2)

                if hook and uwu_message.strip():
                    try:
                        await hook.send(
                            content=uwu_message,
                            username=message.author.display_name,
                            avatar_url=message.author.display_avatar,
                            thread=(
                                message.channel
                                if isinstance(message.channel, discord.Thread)
                                else discord.utils.MISSING
                            ),
                        )
                        await message.delete()
                    except (discord.Forbidden, discord.HTTPException):
                        pass

            elif check['type'] == 'shutup':
                shutup_key = f"stfu:{message.author.id}{message.channel.id}"
                if await self.bot.redis.ratelimited(shutup_key, 3, 2):
                    await asyncio.sleep(2)
                
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass

    async def _get_media_url(
        self,
        ctx: Context,
        attachment: Optional[str],
        accept_image: bool = False,
        accept_gif: bool = False,
        accept_video: bool = False,
    ) -> Optional[str]:
        """Helper method to get media URL from various sources"""
        if attachment:
            return attachment

        if ctx.message.attachments:
            file = ctx.message.attachments[0]
            if accept_image and file.content_type.startswith("image/"):
                return file.url
            if accept_gif and file.filename.endswith(".gif"):
                return file.url
            if accept_video and file.content_type.startswith("video/"):
                return file.url
            return None

        if ctx.message.reference:
            referenced = await ctx.channel.fetch_message(
                ctx.message.reference.message_id
            )
            if referenced.attachments:
                file = referenced.attachments[0]
                if accept_image and file.content_type.startswith("image/"):
                    return file.url
                if accept_gif and file.filename.endswith(".gif"):
                    return file.url
                if accept_video and file.content_type.startswith("video/"):
                    return file.url
            elif referenced.embeds:
                embed = referenced.embeds[0]
                if embed.image:
                    return embed.image.url
                elif embed.thumbnail:
                    return embed.thumbnail.url

        return None

    @command(name="8ball", aliases=["8b"])
    async def eight_ball(self, ctx: Context, *, question: str):
        """Ask the magic 8ball a question"""
        responses = [
            "It is certain.", "Without a doubt.", "Yes definitely.",
            "You may rely on it.", "As I see it, yes.", "Most likely.", 
            "Outlook good.", "Signs point to yes.", "Reply hazy, try again.",
            "Ask again later.", "Better not tell you now.", "Cannot predict now.",
            "Don't count on it.", "My reply is no.", "My sources say no.",
            "Outlook not so good.", "Very doubtful."
        ]
        embed = Embed(color=ctx.color)
        embed.add_field(name="Question", value=question)
        embed.add_field(name="Answer", value=f"🎱 {random.choice(responses)}")
        await ctx.send(embed=embed)

    @command(name="choose")
    async def choose(self, ctx: Context, *, options: str):
        """Choose between multiple options (separate with commas)"""
        choices = [choice.strip() for choice in options.split(",")]
        if len(choices) < 2:
            return await ctx.warn("Please provide at least 2 options separated by commas")
        
        embed = Embed(color=ctx.color)
        embed.add_field(name="Options", value="\n".join(f"• {c}" for c in choices))
        embed.add_field(name="Choice", value=f"**{random.choice(choices)}**")
        await ctx.send(embed=embed)

    @command(name="dadjoke")
    async def dadjoke(self, ctx: Context):
        """Get a random dad joke"""
        async with self.bot.session.get(
            "https://icanhazdadjoke.com/",
            headers={"Accept": "application/json"}
        ) as resp:
            if resp.ok:
                data = await resp.json()
                embed = Embed(description=data['joke'], color=ctx.color)
                embed.set_author(name="Dad Joke")
                await ctx.send(embed=embed)
            else:
                await ctx.warn("Failed to fetch a dad joke")

    @command(name="fact")
    async def fact(self, ctx: Context):
        """Get a random fun fact"""
        async with self.bot.session.get(
            "https://uselessfacts.jsph.pl/api/v2/facts/random",
            params={"language": "en"}
        ) as resp:
            if resp.ok:
                data = await resp.json()
                embed = Embed(description=data['text'], color=ctx.color)
                embed.set_author(name="Random Fact")
                await ctx.send(embed=embed)
            else:
                await ctx.warn("Failed to fetch a fact")

    @command(name="emojify")
    async def emojify(self, ctx: Context, *, text: str):
        """Convert text to regional indicator emojis"""
        if len(text) > 100:
            return await ctx.warn("Text must be 100 characters or less")
            
        mapping = {
            'a': '🇦', 'b': '🇧', 'c': '🇨', 'd': '🇩', 'e': '🇪',
            'f': '🇫', 'g': '🇬', 'h': '🇭', 'i': '🇮', 'j': '🇯',
            'k': '🇰', 'l': '🇱', 'm': '🇲', 'n': '🇳', 'o': '🇴',
            'p': '🇵', 'q': '🇶', 'r': '🇷', 's': '🇸', 't': '🇹',
            'u': '🇺', 'v': '🇻', 'w': '🇼', 'x': '🇽', 'y': '🇾',
            'z': '🇿'
        }
        
        result = ' '.join(mapping.get(c.lower(), c) for c in text)
        embed = Embed(description=result, color=ctx.color)
        embed.set_author(name="Emojified Text")
        await ctx.send(embed=embed)

    @command(name="reversetext")
    async def reversetext(self, ctx: Context, *, text: str):
        """Reverse any text"""
        if len(text) > 1000:
            return await ctx.warn("Text must be 1000 characters or less")
            
        embed = Embed(color=ctx.color)
        embed.add_field(name="Original", value=text)
        embed.add_field(name="Reversed", value=text[::-1])
        await ctx.send(embed=embed)

    @command(name="coinflip", aliases=['flip'])
    async def coinflip(self, ctx: Context, times: int = 1):
        """Flip a coin one or more times"""
        if not 1 <= times <= 100:
            return await ctx.warn("Can only flip between 1 and 100 coins")
            
        results = [random.choice(["Heads", "Tails"]) for _ in range(times)]
        counts = {"Heads": results.count("Heads"), "Tails": results.count("Tails")}
        
        embed = Embed(color=ctx.color)
        embed.set_author(name="Coin Flip")
        if times == 1:
            embed.description = f"🪙 The coin landed on **{results[0]}**!"
        else:
            embed.description = f"🪙 Flipped {times} coins"
            embed.add_field(name="Results", value=f"Heads: {counts['Heads']}\nTails: {counts['Tails']}")
        await ctx.send(embed=embed)

    @command(name="password")
    async def password(self, ctx: Context, length: Optional[int] = 16):
        """Generate a random secure password"""
        try:
            length = int(length)
        except (ValueError, TypeError):
            length = 16
            
        if not 8 <= length <= 100:
            return await ctx.warn("Password length must be between 8 and 100")
            
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        password = ''.join(random.choice(chars) for _ in range(length))
        
        embed = Embed(color=ctx.color)
        embed.set_author(name="Password Generator")
        embed.description = f"||`{password}`||"
        embed.set_footer(text="Click to reveal password")
        await ctx.send(embed=embed)

    @command()
    async def achievement(self, ctx: Context, *, text: str):
        """Generate a Minecraft achievement with custom text"""
        if len(text) > 50:
            return await ctx.warn("Text must be 50 characters or less")

        try:
            buffer = await alexflipnote_api.achievement(text)
            await ctx.send(file=File(BytesIO(buffer), "achievement.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def calling(self, ctx: Context, *, text: str):
        """Generate a 'mom come pick me up im scared' meme"""
        if len(text) > 50:
            return await ctx.warn("Text must be 50 characters or less")

        try:
            buffer = await alexflipnote_api.calling(text)
            await ctx.send(file=File(BytesIO(buffer), "calling.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def captcha(self, ctx: Context, *, text: str):
        """Generate a custom captcha image"""
        if len(text) > 50:
            return await ctx.warn("Text must be 50 characters or less")

        try:
            buffer = await alexflipnote_api.captcha(text)
            await ctx.send(file=File(BytesIO(buffer), "captcha.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def didyoumean(self, ctx: Context, *, flags: DidYouMeanFlags):
        """Generate a Google 'did you mean' image
        
        Flags:
        --text: The searched text
        --text2: The 'did you mean' suggestion"""
        try:
            buffer = await alexflipnote_api.didyoumean(flags.text, flags.text2)
            await ctx.send(file=File(BytesIO(buffer), "didyoumean.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def supreme(self, ctx: Context, *, text: str):
        """Generate a supreme logo with custom text"""
        if len(text) > 50:
            return await ctx.warn("Text must be 50 characters or less")

        try:
            buffer = await alexflipnote_api.supreme(text)
            await ctx.send(file=File(BytesIO(buffer), "supreme.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def facts(self, ctx: Context, *, text: str):
        """Generate a 'facts book' meme"""
        if len(text) > 100:
            return await ctx.warn("Text must be 100 characters or less")

        try:
            buffer = await alexflipnote_api.facts(text)
            await ctx.send(file=File(BytesIO(buffer), "facts.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    # Popcat API Commands
    @command()
    async def drip(self, ctx: Context, member: Member = None):
        """Give someone the drip"""
        member = member or ctx.author
        try:
            buffer = await popcat_api.drip(member.display_avatar.url)
            await ctx.send(file=File(BytesIO(buffer), "drip.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def gun(self, ctx: Context, member: Member = None):
        """Point a gun at someone"""
        member = member or ctx.author
        try:
            buffer = await popcat_api.gun(member.display_avatar.url)
            await ctx.send(file=File(BytesIO(buffer), "gun.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def wanted(self, ctx: Context, member: Member = None):
        """Generate a wanted poster"""
        member = member or ctx.author
        try:
            buffer = await popcat_api.wanted(member.display_avatar.url)
            await ctx.send(file=File(BytesIO(buffer), "wanted.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def alert(self, ctx: Context, *, text: str):
        """Generate an iPhone alert"""
        if len(text) > 100:
            return await ctx.warn("Text must be 100 characters or less")

        try:
            buffer = await popcat_api.alert(text)
            await ctx.send(file=File(BytesIO(buffer), "alert.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def pooh(self, ctx: Context, *, flags: PoohFlags):
        """Generate a Tuxedo Pooh meme"""
        try:
            buffer = await popcat_api.pooh(flags.first, flags.second)
            await ctx.send(file=File(BytesIO(buffer), "pooh.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def drake(self, ctx: Context, *, flags: DrakeFlags):
        """Generate a Drake meme"""
        try:
            buffer = await popcat_api.drake(flags.first, flags.second)
            await ctx.send(file=File(BytesIO(buffer), "drake.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def oogway(self, ctx: Context, *, text: str):
        """Generate an Oogway quote meme"""
        if len(text) > 100:
            return await ctx.warn("Text must be 100 characters or less")

        try:
            buffer = await popcat_api.oogway(text)
            await ctx.send(file=File(BytesIO(buffer), "oogway.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command()
    async def sadcat(self, ctx: Context, *, text: str):
        """Generate a sad cat meme"""
        if len(text) > 100:
            return await ctx.warn("Text must be 100 characters or less")

        try:
            buffer = await popcat_api.sadcat(text)
            await ctx.send(file=File(BytesIO(buffer), "sadcat.png"))
        except CommandOnCooldown as e:
            await ctx.warn(f"This command is on cooldown. Try again in {e.retry_after:.1f}s")

    @command(aliases=["guessflag", "flagguess"])
    @cooldown(1, 5, BucketType.user)
    async def flag(self, ctx: Context, difficulty: str = "medium") -> Message:
        """
        Play a flag guessing game.
        Difficulty options: easy, medium, hard
        """
        difficulty = difficulty.lower()
        if difficulty not in self.flag_difficulties:
            return await ctx.warn("Invalid difficulty! Choose: `easy`, `medium`, or `hard`")

        country_code = random.choice(self.flag_difficulties[difficulty])
        flag_path = f"assets/flags/{country_code}.png"

        country_names = {
            "ad": "Andorra", "ae": "United Arab Emirates", "af": "Afghanistan",
            "ag": "Antigua and Barbuda", "ai": "Anguilla", "al": "Albania",
            "am": "Armenia", "ao": "Angola", "aq": "Antarctica",
            "ar": "Argentina", "as": "American Samoa", "at": "Austria",
            "au": "Australia", "aw": "Aruba", "ax": "Åland Islands",
            "az": "Azerbaijan",
            "ba": "Bosnia and Herzegovina", "bb": "Barbados",
            "bd": "Bangladesh", "be": "Belgium", "bf": "Burkina Faso",
            "bg": "Bulgaria", "bh": "Bahrain", "bi": "Burundi",
            "bj": "Benin", "bl": "Saint Barthélemy", "bm": "Bermuda",
            "bn": "Brunei", "bo": "Bolivia", "bq": "Caribbean Netherlands",
            "br": "Brazil", "bs": "Bahamas", "bt": "Bhutan",
            "bw": "Botswana", "by": "Belarus", "bz": "Belize",
            "ca": "Canada", "cc": "Cocos Islands", "cd": "DR Congo",
            "cf": "Central African Republic", "cg": "Republic of the Congo",
            "ch": "Switzerland", "ci": "Ivory Coast", "ck": "Cook Islands",
            "cl": "Chile", "cm": "Cameroon", "cn": "China",
            "co": "Colombia", "cr": "Costa Rica", "cu": "Cuba",
            "cv": "Cape Verde", "cw": "Curaçao", "cx": "Christmas Island",
            "cy": "Cyprus", "cz": "Czech Republic",
            "de": "Germany", "dj": "Djibouti", "dk": "Denmark",
            "dm": "Dominica", "do": "Dominican Republic", "dz": "Algeria",
            "ec": "Ecuador", "ee": "Estonia", "eg": "Egypt",
            "eh": "Western Sahara", "er": "Eritrea", "es": "Spain",
            "et": "Ethiopia",
            "fi": "Finland", "fj": "Fiji", "fk": "Falkland Islands",
            "fm": "Micronesia", "fo": "Faroe Islands", "fr": "France",
            "ga": "Gabon", "gb": "United Kingdom", "gd": "Grenada",
            "ge": "Georgia", "gf": "French Guiana", "gg": "Guernsey",
            "gh": "Ghana", "gi": "Gibraltar", "gl": "Greenland",
            "gm": "Gambia", "gn": "Guinea", "gp": "Guadeloupe",
            "gq": "Equatorial Guinea", "gr": "Greece",
            "gs": "South Georgia", "gt": "Guatemala", "gu": "Guam",
            "gw": "Guinea-Bissau", "gy": "Guyana",
            "hk": "Hong Kong", "hm": "Heard Island",
            "hn": "Honduras", "hr": "Croatia", "ht": "Haiti",
            "hu": "Hungary",
            "id": "Indonesia", "ie": "Ireland", "il": "Israel",
            "im": "Isle of Man", "in": "India", "io": "British Indian Ocean Territory",
            "iq": "Iraq", "ir": "Iran", "is": "Iceland", "it": "Italy",
            "je": "Jersey", "jm": "Jamaica", "jo": "Jordan", "jp": "Japan",
            "ke": "Kenya", "kg": "Kyrgyzstan", "kh": "Cambodia",
            "ki": "Kiribati", "km": "Comoros", "kn": "Saint Kitts and Nevis",
            "kp": "North Korea", "kr": "South Korea", "kw": "Kuwait",
            "ky": "Cayman Islands", "kz": "Kazakhstan",
            "la": "Laos", "lb": "Lebanon", "lc": "Saint Lucia",
            "li": "Liechtenstein", "lk": "Sri Lanka", "lr": "Liberia",
            "ls": "Lesotho", "lt": "Lithuania", "lu": "Luxembourg",
            "lv": "Latvia", "ly": "Libya",
            "ma": "Morocco", "mc": "Monaco", "md": "Moldova",
            "me": "Montenegro", "mf": "Saint Martin", "mg": "Madagascar",
            "mh": "Marshall Islands", "mk": "North Macedonia",
            "ml": "Mali", "mm": "Myanmar", "mn": "Mongolia",
            "mo": "Macau", "mp": "Northern Mariana Islands",
            "mq": "Martinique", "mr": "Mauritania", "ms": "Montserrat",
            "mt": "Malta", "mu": "Mauritius", "mv": "Maldives",
            "mw": "Malawi", "mx": "Mexico", "my": "Malaysia",
            "mz": "Mozambique",
            "na": "Namibia", "nc": "New Caledonia", "ne": "Niger",
            "nf": "Norfolk Island", "ng": "Nigeria", "ni": "Nicaragua",
            "nl": "Netherlands", "no": "Norway", "np": "Nepal",
            "nr": "Nauru", "nu": "Niue", "nz": "New Zealand",
            "om": "Oman",
            "pa": "Panama", "pe": "Peru", "pf": "French Polynesia",
            "pg": "Papua New Guinea", "ph": "Philippines", "pk": "Pakistan",
            "pl": "Poland", "pm": "Saint Pierre and Miquelon",
            "pn": "Pitcairn Islands", "pr": "Puerto Rico",
            "ps": "Palestine", "pt": "Portugal", "pw": "Palau",
            "py": "Paraguay",
            "qa": "Qatar",
            "re": "Réunion", "ro": "Romania", "rs": "Serbia",
            "ru": "Russia", "rw": "Rwanda",
            "sa": "Saudi Arabia", "sb": "Solomon Islands",
            "sc": "Seychelles", "sd": "Sudan", "se": "Sweden",
            "sg": "Singapore", "sh": "Saint Helena",
            "si": "Slovenia", "sj": "Svalbard and Jan Mayen",
            "sk": "Slovakia", "sl": "Sierra Leone",
            "sm": "San Marino", "sn": "Senegal", "so": "Somalia",
            "sr": "Suriname", "ss": "South Sudan",
            "st": "São Tomé and Príncipe", "sv": "El Salvador",
            "sx": "Sint Maarten", "sy": "Syria", "sz": "Eswatini",
            "tc": "Turks and Caicos Islands", "td": "Chad",
            "tf": "French Southern Territories", "tg": "Togo",
            "th": "Thailand", "tj": "Tajikistan", "tk": "Tokelau",
            "tl": "East Timor", "tm": "Turkmenistan", "tn": "Tunisia",
            "to": "Tonga", "tr": "Turkey", "tt": "Trinidad and Tobago",
            "tv": "Tuvalu", "tw": "Taiwan", "tz": "Tanzania",
            "ua": "Ukraine", "ug": "Uganda", "um": "U.S. Minor Outlying Islands",
            "us": "United States", "uy": "Uruguay", "uz": "Uzbekistan",
            "va": "Vatican City", "vc": "Saint Vincent and the Grenadines",
            "ve": "Venezuela", "vg": "British Virgin Islands",
            "vi": "U.S. Virgin Islands", "vn": "Vietnam", "vu": "Vanuatu",
            "wf": "Wallis and Futuna", "ws": "Samoa",
            "xk": "Kosovo",
            "ye": "Yemen", "yt": "Mayotte",
            "za": "South Africa", "zm": "Zambia", "zw": "Zimbabwe"
        }

        embed = Embed(
            title="Guess the Flag!",
            description=(
                f"**Difficulty**: {difficulty.title()}\n"
                "You have 30 seconds to guess the country.\n"
                "*Type your answer in the chat.*"
            ),
            color=ctx.color
        )
        
        file = File(flag_path, filename="flag.png")
        embed.set_thumbnail(url="attachment://flag.png")
        
        message = await ctx.send(file=file, embed=embed)

        try:
            _ = await self.bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda m: (
                    m.author == ctx.author
                    and m.channel == ctx.channel
                    and (
                        unidecode(m.content.lower().strip()) in [
                            unidecode(country_names[country_code].lower()),
                            country_code.lower()
                        ]
                    )
                )
            )
        except asyncio.TimeoutError:
            embed.description = f"Time's up! The answer was **{country_names[country_code]}**"
            embed.color = discord.Color.red()
            await message.edit(embed=embed)
        else:
            embed.description = f"Correct! The answer was **{country_names[country_code]}**"
            embed.color = discord.Color.green()
            await message.edit(embed=embed)

    @command(aliases=['flaggame'])
    async def flags(self, ctx: Context) -> Optional[Message]:
        """Start a game of Flags."""

        country_names = {
            "ad": "Andorra", "ae": "United Arab Emirates", "af": "Afghanistan",
            "ag": "Antigua and Barbuda", "ai": "Anguilla", "al": "Albania",
            "am": "Armenia", "ao": "Angola", "aq": "Antarctica",
            "ar": "Argentina", "as": "American Samoa", "at": "Austria",
            "au": "Australia", "aw": "Aruba", "ax": "Åland Islands",
            "az": "Azerbaijan",
            "ba": "Bosnia and Herzegovina", "bb": "Barbados",
            "bd": "Bangladesh", "be": "Belgium", "bf": "Burkina Faso",
            "bg": "Bulgaria", "bh": "Bahrain", "bi": "Burundi",
            "bj": "Benin", "bl": "Saint Barthélemy", "bm": "Bermuda",
            "bn": "Brunei", "bo": "Bolivia", "bq": "Caribbean Netherlands",
            "br": "Brazil", "bs": "Bahamas", "bt": "Bhutan",
            "bw": "Botswana", "by": "Belarus", "bz": "Belize",
            "ca": "Canada", "cc": "Cocos Islands", "cd": "DR Congo",
            "cf": "Central African Republic", "cg": "Republic of the Congo",
            "ch": "Switzerland", "ci": "Ivory Coast", "ck": "Cook Islands",
            "cl": "Chile", "cm": "Cameroon", "cn": "China",
            "co": "Colombia", "cr": "Costa Rica", "cu": "Cuba",
            "cv": "Cape Verde", "cw": "Curaçao", "cx": "Christmas Island",
            "cy": "Cyprus", "cz": "Czech Republic",
            "de": "Germany", "dj": "Djibouti", "dk": "Denmark",
            "dm": "Dominica", "do": "Dominican Republic", "dz": "Algeria",
            "ec": "Ecuador", "ee": "Estonia", "eg": "Egypt",
            "eh": "Western Sahara", "er": "Eritrea", "es": "Spain",
            "et": "Ethiopia",
            "fi": "Finland", "fj": "Fiji", "fk": "Falkland Islands",
            "fm": "Micronesia", "fo": "Faroe Islands", "fr": "France",
            "ga": "Gabon", "gb": "United Kingdom", "gd": "Grenada",
            "ge": "Georgia", "gf": "French Guiana", "gg": "Guernsey",
            "gh": "Ghana", "gi": "Gibraltar", "gl": "Greenland",
            "gm": "Gambia", "gn": "Guinea", "gp": "Guadeloupe",
            "gq": "Equatorial Guinea", "gr": "Greece",
            "gs": "South Georgia", "gt": "Guatemala", "gu": "Guam",
            "gw": "Guinea-Bissau", "gy": "Guyana",
            "hk": "Hong Kong", "hm": "Heard Island",
            "hn": "Honduras", "hr": "Croatia", "ht": "Haiti",
            "hu": "Hungary",
            "id": "Indonesia", "ie": "Ireland", "il": "Israel",
            "im": "Isle of Man", "in": "India", "io": "British Indian Ocean Territory",
            "iq": "Iraq", "ir": "Iran", "is": "Iceland", "it": "Italy",
            "je": "Jersey", "jm": "Jamaica", "jo": "Jordan", "jp": "Japan",
            "ke": "Kenya", "kg": "Kyrgyzstan", "kh": "Cambodia",
            "ki": "Kiribati", "km": "Comoros", "kn": "Saint Kitts and Nevis",
            "kp": "North Korea", "kr": "South Korea", "kw": "Kuwait",
            "ky": "Cayman Islands", "kz": "Kazakhstan",
            "la": "Laos", "lb": "Lebanon", "lc": "Saint Lucia",
            "li": "Liechtenstein", "lk": "Sri Lanka", "lr": "Liberia",
            "ls": "Lesotho", "lt": "Lithuania", "lu": "Luxembourg",
            "lv": "Latvia", "ly": "Libya",
            "ma": "Morocco", "mc": "Monaco", "md": "Moldova",
            "me": "Montenegro", "mf": "Saint Martin", "mg": "Madagascar",
            "mh": "Marshall Islands", "mk": "North Macedonia",
            "ml": "Mali", "mm": "Myanmar", "mn": "Mongolia",
            "mo": "Macau", "mp": "Northern Mariana Islands",
            "mq": "Martinique", "mr": "Mauritania", "ms": "Montserrat",
            "mt": "Malta", "mu": "Mauritius", "mv": "Maldives",
            "mw": "Malawi", "mx": "Mexico", "my": "Malaysia",
            "mz": "Mozambique",
            "na": "Namibia", "nc": "New Caledonia", "ne": "Niger",
            "nf": "Norfolk Island", "ng": "Nigeria", "ni": "Nicaragua",
            "nl": "Netherlands", "no": "Norway", "np": "Nepal",
            "nr": "Nauru", "nu": "Niue", "nz": "New Zealand",
            "om": "Oman",
            "pa": "Panama", "pe": "Peru", "pf": "French Polynesia",
            "pg": "Papua New Guinea", "ph": "Philippines", "pk": "Pakistan",
            "pl": "Poland", "pm": "Saint Pierre and Miquelon",
            "pn": "Pitcairn Islands", "pr": "Puerto Rico",
            "ps": "Palestine", "pt": "Portugal", "pw": "Palau",
            "py": "Paraguay",
            "qa": "Qatar",
            "re": "Réunion", "ro": "Romania", "rs": "Serbia",
            "ru": "Russia", "rw": "Rwanda",
            "sa": "Saudi Arabia", "sb": "Solomon Islands",
            "sc": "Seychelles", "sd": "Sudan", "se": "Sweden",
            "sg": "Singapore", "sh": "Saint Helena",
            "si": "Slovenia", "sj": "Svalbard and Jan Mayen",
            "sk": "Slovakia", "sl": "Sierra Leone",
            "sm": "San Marino", "sn": "Senegal", "so": "Somalia",
            "sr": "Suriname", "ss": "South Sudan",
            "st": "São Tomé and Príncipe", "sv": "El Salvador",
            "sx": "Sint Maarten", "sy": "Syria", "sz": "Eswatini",
            "tc": "Turks and Caicos Islands", "td": "Chad",
            "tf": "French Southern Territories", "tg": "Togo",
            "th": "Thailand", "tj": "Tajikistan", "tk": "Tokelau",
            "tl": "East Timor", "tm": "Turkmenistan", "tn": "Tunisia",
            "to": "Tonga", "tr": "Turkey", "tt": "Trinidad and Tobago",
            "tv": "Tuvalu", "tw": "Taiwan", "tz": "Tanzania",
            "ua": "Ukraine", "ug": "Uganda", "um": "U.S. Minor Outlying Islands",
            "us": "United States", "uy": "Uruguay", "uz": "Uzbekistan",
            "va": "Vatican City", "vc": "Saint Vincent and the Grenadines",
            "ve": "Venezuela", "vg": "British Virgin Islands",
            "vi": "U.S. Virgin Islands", "vn": "Vietnam", "vu": "Vanuatu",
            "wf": "Wallis and Futuna", "ws": "Samoa",
            "xk": "Kosovo",
            "ye": "Yemen", "yt": "Mayotte",
            "za": "South Africa", "zm": "Zambia", "zw": "Zimbabwe"
        }
        
        session = await Flags.get(self.bot.redis, ctx.channel.id)
        if session:
            return await ctx.warn("There is already a game in progress.")

        embed = Embed(
            title="Flags Game",
            description="\n> ".join(
                [
                    "React with `✅` to join the game. The game will start in **30 seconds**",
                    "You'll have **15 seconds** to guess each flag",
                    "Game starts with **easy** flags and gets progressively harder",
                    "Each player has **3 lives**"
                ]
            ),
        )
        message = await ctx.channel.send(embed=embed)

        session = Flags(message_id=message.id, channel_id=ctx.channel.id)
        await session.save(self.bot.redis)
        await message.add_reaction("✅")

        def check(reaction, user):
            return (
                reaction.message.id == message.id 
                and str(reaction.emoji) == "✅"
                and not user.bot
            )

        try:
            while True:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=30.0, check=check)
                session = await Flags.get(self.bot.redis, ctx.channel.id)
                if session:
                    session.players[user.id] = 3 
                    await session.save(self.bot.redis)
        except asyncio.TimeoutError:
            pass

        session = await Flags.get(self.bot.redis, ctx.channel.id)
        if not session or len(session.players) < 2:
            await self.bot.redis.delete(Flags.key(ctx.channel.id))
            return await ctx.warn("Not enough players to start the game!")

        session.waiting = False
        await session.save(self.bot.redis, ex=1800)

        while True:
            for member_id, lives in list(session.players.items()):
                member = ctx.guild.get_member(member_id)
                if not member:
                    if len(session.players) == 1:
                        await session.delete(self.bot.redis)
                        return await ctx.warn("The winner left the server!")
                    continue

                if len(session.players) == 1:
                    await session.delete(self.bot.redis)
                    return await ctx.approve(f"**{member}** has won the game!")

                available_flags = [
                    flag for flag in self.flag_difficulties[session.current_difficulty]
                    if flag not in session.used_flags
                ]
                
                if not available_flags:
                    if session.current_difficulty == "easy":
                        session.current_difficulty = "medium"
                    elif session.current_difficulty == "medium":
                        session.current_difficulty = "hard"
                    else:
                        session.used_flags = []  
                    available_flags = self.flag_difficulties[session.current_difficulty]
                
                country_code = choice(available_flags)
                session.used_flags.append(country_code)
                
                if session.current_difficulty == "easy":
                    timeout = 10.0
                elif session.current_difficulty == "medium":
                    timeout = 8.0
                else:
                    timeout = 7.0

                file = File(f"assets/flags/{country_code}.png", filename="flag.png")
                embed = Embed(
                    title=f"Guess the Flag ({session.current_difficulty.title()})",
                    description=f"You have **{int(timeout)} seconds** to guess this flag"
                )
                embed.set_thumbnail(url="attachment://flag.png")
                message = await ctx.send(content=member.mention, file=file, embed=embed)

                start_time = time.time()
                
                while True:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        await message.add_reaction("❌")
                        lives = session.players[member_id] - 1
                        if not lives:
                            del session.players[member_id]
                            embed = Embed(description=f"**{member}** has been **eliminated**!\nThe flag was **{country_names[country_code]}**")
                        else:
                            session.players[member_id] = lives
                            embed = Embed(
                                description="\n> ".join([
                                    f"Time's up! The flag was **{country_names[country_code]}**",
                                    f"You have {plural(lives, md='**'):life|lives} remaining"
                                ])
                            )
                        await ctx.send(embed=embed)
                        break

                    try:
                        message_response = await self.bot.wait_for(
                            "message",
                            timeout=remaining_time,
                            check=lambda m: (
                                m.author == member
                                and m.channel == ctx.channel
                            )
                        )
                        
                        if unidecode(message_response.content.lower().strip()) in [
                            unidecode(country_names[country_code].lower()),
                            country_code.lower()
                        ]:
                            await message_response.add_reaction("✅")
                            await session.save(self.bot.redis)
                            break  
                        else:
                            await message_response.add_reaction("❌")
                            continue

                    except asyncio.TimeoutError:
                        continue

                await session.save(self.bot.redis)

    @command(aliases=["niko"])
    async def dog(self, ctx):
        """
        Sends qilla's dog to chat.
        """
        urls = [
            "https://r2.evict.bot/reskins/930383131863842816_1735300560.png",
            "https://r2.evict.bot/reskins/930383131863842816_1736194975.png"
        ]
        url = random.choice(urls)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    file = discord.File(io.BytesIO(image_data), filename="dog.png")
                    await ctx.send(file=file)
                else:
                    await ctx.send("Failed to fetch the dog image")

    @group(name="socials", invoke_without_command=True)
    async def socials(self, ctx: Context, user: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View your or another user's profile.
        """
        if not isinstance(user, User):
            user = await self.bot.fetch_user(user.id)

        socials = await self.bot.db.fetchrow(
            """
            SELECT * 
            FROM socials
            WHERE user_id = $1
            """,
            user.id
        )

        friends = await self.bot.db.fetch(
            """
            SELECT friends 
            FROM socials_details 
            WHERE user_id = $1
            """,
            user.id
        )

        links = await self.bot.db.fetch(
            """
            SELECT * 
            FROM social_links 
            WHERE user_id = $1
            """,
            user.id
        )

        embed = Embed(
            title=f"{user.name}",
            url=f"https://discord.com/users/{user.id}",
        )

        if isinstance(user, Member):
            support_guild = self.bot.get_guild(892675627373699072)  
            support_member = support_guild.get_member(user.id) if support_guild else None
            
            badges = []
            staff_eligible = False
            
            if support_member:  
                if any(role.id == 1265473601755414528 for role in support_member.roles):
                    badges.extend([f"{config.EMOJIS.STAFF.DEVELOPER}", f"{config.EMOJIS.STAFF.OWNER}"])
                    staff_eligible = True
                    
                if any(role.id == 1264110559989862406 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.SUPPORT}")
                    staff_eligible = True
                    
                if any(role.id == 1323255508609663098 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.TRIAL}")
                    staff_eligible = True

                if any(role.id == 1325007612797784144 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.MODERATOR}")
                    staff_eligible = True

                if any(role.id == 1318054098666389534 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.DONOR}")
                    
                if any(role.id == 1320428924215496704 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.INSTANCE}")
                
            if badges:
                if staff_eligible:
                    badges.append(f"{config.EMOJIS.STAFF.SUPPORT}")
                embed.description = f"{' '.join(badges)}"
            else:
                embed.description = "> No badges available."

        if socials and socials.get('bio'):
            embed.add_field(name="Bio", value=socials['bio'], inline=False)
        else:
            embed.add_field(name="Bio", value="> No bio added.", inline=False)

        if friends:
            friends_list = []
            for row in friends:
                try:
                    friend_user = await self.bot.fetch_user(row['friends'])
                    friends_list.append(f"> {friend_user.name}")
                except Exception:
                    friends_list.append(f"> Unknown User ({row['friends']})")

            embed.add_field(name="Friends", value="\n".join(friends_list), inline=False)
        else:
            embed.add_field(name="Friends", value="> No friends added.", inline=False)

        embed.add_field(
            name="Creation",
            value=f"> {format_dt(user.created_at, 'R')}",
            inline=False
        )

        if user.banner:
            embed.set_image(url=user.banner.url)

        view = View()
        for link in links:
            view.add_item(Button(label=link['type'], url=link['url'], style=ButtonStyle.link))

        return await ctx.send(embed=embed, view=view)


    @socials.command(name="bio")
    async def socials_bio(self, ctx: Context, *, bio: str = None):
        """
        Set your bio for the social embed. If no bio is specified and a bio exists, it will be removed.
        """
        check = await self.bot.db.fetchrow(
            """
            SELECT * FROM socials 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )

        if bio:
            if len(bio) > 200:
                return await ctx.warn("Bio must be 200 characters or less.")

            if check:
                await self.bot.db.execute(
                    """
                    UPDATE socials SET bio = $1 
                    WHERE user_id = $2
                    """, 
                    bio, 
                    ctx.author.id
                )
            else:
                await self.bot.db.execute(
                    """
                    INSERT INTO socials 
                    (user_id, bio) 
                    VALUES ($1, $2)
                    """, 
                    ctx.author.id, 
                    bio
                )
            await ctx.approve(f"Bio successfully set to **{bio}**.")
        else:
            if check and check['bio'] is not None:
                await ctx.prompt("Are you sure you want to remove your bio?")
                await self.bot.db.execute(
                    """
                    UPDATE socials SET bio = NULL 
                    WHERE user_id = $1
                    """, 
                    ctx.author.id
                )
                await ctx.approve("Bio successfully removed.")
            else:
                await ctx.warn("You don't have a bio to remove or set.")

    @socials.command(name="friends")
    async def socials_friends(self, ctx: Context, *, friends: Member):
        """
        Add or remove a friend for the social embed. If the friend already exists, remove the entry.
        """
        await self.bot.db.execute(
            """
            INSERT INTO socials (user_id) 
            VALUES ($1)
            ON CONFLICT (user_id) 
            DO NOTHING
            """,
            ctx.author.id
        )

        await self.bot.db.execute(
            """
            INSERT INTO socials (user_id) 
            VALUES ($1)
            ON CONFLICT (user_id) 
            DO NOTHING
            """,
            friends.id
        )

        check = await self.bot.db.fetchrow(
            """
            SELECT * FROM socials_details 
            WHERE user_id = $1 
            AND friends = $2
            """,
            ctx.author.id,
            friends.id
        )

        if check:
            await ctx.prompt(f"Are you sure you want to remove {friends.mention} from your friends list?")
            await self.bot.db.execute(
                """
                DELETE FROM socials_details 
                WHERE user_id = $1 
                AND friends = $2
                """,
                ctx.author.id,
                friends.id
            )
            await self.bot.db.execute(
                """
                DELETE FROM socials_details 
                WHERE user_id = $1 
                AND friends = $2
                """,
                friends.id,
                ctx.author.id
            )
            await ctx.approve(f"Friend **{friends}** has been removed.")
        else:
            await ctx.confirm(f"{friends.mention} would you like to be friends with {ctx.author.mention}?", user=friends)

            await self.bot.db.execute(
                """
                INSERT INTO socials_details 
                (user_id, friends) 
                VALUES ($1, $2)
                """,
                ctx.author.id,
                friends.id
            )
            await self.bot.db.execute(
                """
                INSERT INTO socials_details 
                (user_id, friends) 
                VALUES ($1, $2)
                """,
                friends.id,
                ctx.author.id
            )
            await ctx.approve(f"Friend **{friends}** has been added successfully.")
            await self.generate_profile_image(ctx.author, force_update=True)

    @socials.command(name="links")
    async def socials_links(
        self, 
        ctx: Context, 
        type: Literal["instagram", "youtube", "github", "discord", "twitter", "twitch", "reddit", "pinterest", "snapchat", "tiktok"],
        url: Optional[str] = None
    ):
        """
        Add or remove a link to your social embed.
        """
        url_patterns = {
            "instagram": r"https?://(www\.)?instagram\.com/.*",
            "youtube": r"https?://(www\.)?(youtube\.com|youtu\.be)/.*",
            "github": r"https?://(www\.)?github\.com/.*",
            "discord": r"https?://(www\.)?(discord\.gg|discord\.com/invite)/.*",
            "twitter": r"https?://(www\.)?twitter\.com/.*",
            "twitch": r"https?://(www\.)?twitch\.tv/.*",
            "reddit": r"https?://(www\.)?reddit\.com/.*",
            "pinterest": r"https?://(www\.)?pinterest\.com/.*",
            "snapchat": r"https?://(www\.)?snapchat\.com/.*",
            "tiktok": r"https?://(www\.)?tiktok\.com/.*",
        }

        if url:
            if not url.startswith(("http://", "https://")):
                return await ctx.warn("Please provide a valid URL starting with http:// or https://")

            if not re.match(url_patterns[type], url):
                return await ctx.warn(f"Please provide a valid {type} URL") 
            
            try:
                await self.bot.db.execute(
                    """
                    INSERT INTO social_links (user_id, type, url)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id, type) 
                    DO UPDATE SET url = $3
                    """,
                    ctx.author.id,
                    type,
                    url
                )
                await ctx.approve(f"Successfully set your {type} link to {url}")
                await self.generate_profile_image(ctx.author, force_update=True)


            except Exception as e:
                return await ctx.warn(f"Failed to set link: {e}")
        else:
            try:
                await ctx.prompt(f"Are you sure you want to remove your {type} link?")
                await self.generate_profile_image(ctx.author, force_update=True)
                result = await self.bot.db.execute(
                    """
                    DELETE FROM social_links 
                    WHERE user_id = $1 AND type = $2
                    """,
                    ctx.author.id,
                    type
                )
                if result == "DELETE 1":
                    return await ctx.approve(f"Successfully removed your {type} link.")
                else:
                    return await ctx.warn(f"No {type} link found to remove.")
            
            except Exception as e:
                return await ctx.warn(f"Failed to remove link: {e}")

    @socials.command(name="background")
    async def socials_background(self, ctx: Context, *, url: str = None):
        """Set your profile background. Send a URL or attach a file (images, GIFs, or videos under 30s)."""
        if not url and not ctx.message.attachments:
            await ctx.prompt("Are you sure you want to remove your background?")
            await self.bot.db.execute(
                """
                UPDATE socials 
                SET background_url = NULL 
                WHERE user_id = $1
                """,
                ctx.author.id
            )
            return await ctx.approve("Background successfully removed!")
        
        media_url = url or ctx.message.attachments[0].url
        if not media_url.startswith(('http://', 'https://')):
            return await ctx.warn("Please provide a valid URL or attachment")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url) as resp:
                    if resp.status != 200:
                        return await ctx.warn("Failed to fetch media")
                    
                    content_type = resp.headers.get('content-type', '')
                    
                    allowed_types = {
                        'image/jpeg', 'image/png', 'image/gif',
                        'video/mp4', 'video/webm', 'video/quicktime'
                    }
                    if content_type not in allowed_types:
                        return await ctx.warn("Invalid file type. Only jpg, png, gif, mp4, webm, and mov files are allowed.")
                    
                    media_data = await resp.read()
                    magic_bytes = media_data[:8]
                    
                    valid_signatures = {
                        b'\xFF\xD8\xFF': 'jpg', 
                        b'\x89PNG\r\n\x1A\n': 'png',
                        b'GIF87a': 'gif',  
                        b'GIF89a': 'gif', 
                        b'\x00\x00\x00': 'mp4', 
                        b'\x1A\x45\xDF\xA3': 'webm'  
                    }
                    
                    is_valid = False
                    for signature in valid_signatures:
                        if magic_bytes.startswith(signature):
                            is_valid = True
                            break
                            
                    if not is_valid:
                        return await ctx.warn("Invalid file format detected.")
                    
                    content_length = len(media_data)
                    if content_length > 8 * 1024 * 1024: 
                        return await ctx.warn("File must be under 8MB")

                    if content_type.startswith('video/'):
                        video_buffer = io.BytesIO(media_data)
                        
                        probe = await asyncio.create_subprocess_exec(
                            'ffprobe',
                            '-v', 'error',
                            '-show_entries', 'format=duration',
                            '-of', 'default=noprint_wrappers=1:nokey=1',
                            'pipe:0',
                            stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await probe.communicate(input=media_data)
                        
                        if probe.returncode != 0:
                            return await ctx.warn("Invalid video file")
                            
                        try:
                            duration = float(stdout.decode().strip())
                            if duration > 30:
                                return await ctx.warn("Video must be under 30 seconds")
                        except:
                            return await ctx.warn("Failed to process video")
                    
                    ext = mimetypes.guess_extension(content_type) or '.mp4'
                    filename = f"{ctx.author.id}_{int(time.time())}{ext}"
                    
                    headers = {"AccessKey": "10e0eb5f-79de-4ae9-a35a9b9f71e0-8c99-4a58"}
                    async with session.put(
                        f"https://storage.bunnycdn.com/evict/socials/{filename}",
                        headers=headers,
                        data=media_data
                    ) as upload:
                        if upload.status != 201:
                            return await ctx.warn("Failed to upload media")
                        
                        cdn_url = f"https://bunny.evict.bot/socials/{filename}"
                        await self.bot.db.execute(
                            """
                            UPDATE socials 
                            SET background_url = $1 
                            WHERE user_id = $2
                            """,
                            cdn_url,
                            ctx.author.id
                        )
                        await ctx.approve("Background successfully set!")
                        await self.generate_profile_image(ctx.author, force_update=True)
        except Exception as e:
            return await ctx.warn(f"Failed to set background: {e}")

    @socials.command(name="audio")
    async def socials_audio(self, ctx: Context, *, url: str = None):
        """Set your profile audio. Send a URL, attachment, or Discord message link containing audio."""
        if not url and not ctx.message.attachments:
            await ctx.prompt("Are you sure you want to remove your audio?")
            await self.bot.db.execute(
                """
                UPDATE socials 
                SET audio_url = NULL, 
                    audio_title = NULL 
                WHERE user_id = $1
                """,
                ctx.author.id
            )
            return await ctx.approve("Audio successfully removed!")

        if ctx.message.attachments:
            media_url = ctx.message.attachments[0].url
            original_filename = ctx.message.attachments[0].filename
        elif url and "discord.com/channels/" in url:
            try:
                _, _, _, guild_id, channel_id, message_id = url.split('/')
                channel = self.bot.get_channel(int(channel_id))
                message = await channel.fetch_message(int(message_id))
                
                audio_attachment = next(
                    (a for a in message.attachments if a.filename.endswith(('.mp3', '.wav', '.ogg', '.m4a'))), 
                    None
                )
                if not audio_attachment:
                    return await ctx.warn("No valid audio file found in the linked message")
                
                media_url = audio_attachment.url
                original_filename = audio_attachment.filename
            except Exception:
                return await ctx.warn("Invalid Discord message link or missing permissions")
        else:
            if not url:
                return await ctx.warn("Please provide a valid URL or attachment")
            media_url = url
            original_filename = url.split('/')[-1]
            
        if not media_url.startswith(('http://', 'https://')):
            return await ctx.warn("Please provide a valid URL or attachment")

        try:
            await ctx.typing()
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url) as resp:
                    if resp.status != 200:
                        return await ctx.warn("Failed to fetch audio")
                    
                    content_type = resp.headers.get('content-type', '')
                    
                    allowed_types = {
                        'audio/mpeg', 'audio/mp3', 'audio/wav', 
                        'audio/ogg', 'audio/mp4', 'audio/x-m4a'
                    }
                    if content_type not in allowed_types:
                        return await ctx.warn("Invalid file type. Only mp3, wav, ogg, and m4a files are allowed.")
                    
                    media_data = await resp.read()
                    magic_bytes = media_data[:8]
                    
                    valid_signatures = {
                        b'ID3': 'mp3',
                        b'\xFF\xFB': 'mp3', 
                        b'\xFF\xF3': 'mp3',
                        b'\xFF\xF2': 'mp3',  
                        b'RIFF': 'wav',
                        b'OggS': 'ogg',
                        b'ftyp': 'm4a',
                        b'\x00\x00\x00': 'm4a' 
                    }
                    
                    is_valid = False
                    detected_format = None
                    for signature, format_type in valid_signatures.items():
                        if magic_bytes.startswith(signature):
                            is_valid = True
                            detected_format = format_type
                            break
                            
                    if not is_valid:
                        return await ctx.warn("Invalid audio format detected.")
                    
                    content_length = len(media_data)
                    if content_length > 7 * 1024 * 1024:
                        return await ctx.warn("Audio file must be under 7MB")
                    elif content_length < 1024:  
                        return await ctx.warn("File is too small to be a valid audio file")

                    header_check = media_data[:1024].lower()
                    suspicious_patterns = [
                        b'<script', b'<?php', b'<%', b'#!/',  
                        b'ELF',
                        b'MZ',   
                        b'PK',   
                        b'#!',   
                        b'eval(', b'exec(', b'system(', 
                        b'.exe', b'.dll', b'.sh', b'.bat'  
                    ]
                    
                    for pattern in suspicious_patterns:
                        if pattern in header_check:
                            return await ctx.warn("Potentially malicious file detected")

                    def calculate_entropy(data):
                        if not data:
                            return 0
                        entropy = 0
                        for x in range(256):
                            p_x = data.count(x)/len(data)
                            if p_x > 0:
                                entropy += - p_x*math.log2(p_x)
                        return entropy

                    entropy = calculate_entropy(header_check)
                    if entropy > 7.5: 
                        return await ctx.warn("Suspicious file structure detected")

                    original_filename = original_filename.split('?')[0]
                    
                    old_audio = await self.bot.db.fetchval(
                        """
                        SELECT audio_url FROM socials 
                        WHERE user_id = $1
                        """, 
                        ctx.author.id
                    )

                    try:
                        process = await asyncio.create_subprocess_shell(
                            f'ffprobe -i pipe:0 -v error',
                            stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        stdout, stderr = await asyncio.wait_for(
                            process.communicate(input=media_data),
                            timeout=10.0
                        )
                            
                        if process.returncode != 0:
                            return await ctx.warn("Invalid audio file")
                            
                        ext = mimetypes.guess_extension(content_type) or f'.{detected_format}'
                    
                    except Exception as e:
                        return await ctx.warn(f"Failed to process audio: {e}")
                    
                    if not ext.lower() in ['.mp3', '.wav', '.ogg', '.m4a']:
                        ext = f'.{detected_format}'
                        
                    filename = f"audio_{ctx.author.id}_{int(time.time())}{ext}"
                    
                    headers = {"AccessKey": "10e0eb5f-79de-4ae9-a35a9b9f71e0-8c99-4a58"}
                    async with session.put(
                        f"https://storage.bunnycdn.com/evict/socials/{filename}",
                        headers=headers,
                        data=media_data
                    ) as upload:
                        if upload.status != 201:
                            return await ctx.warn("Failed to upload audio")
                        
                        cdn_url = f"https://bunny.evict.bot/socials/{filename}"
                        await self.bot.db.execute(
                            """
                            UPDATE socials 
                            SET audio_url = $1,
                                audio_title = $2
                            WHERE user_id = $3
                            """,
                            cdn_url,
                            original_filename,
                            ctx.author.id
                        )
                        await ctx.approve(f"Audio successfully set! Title: {original_filename}")

                        if old_audio:
                            old_filename = old_audio.split('/')[-1]
                            try:
                                async with session.delete(
                                    f"https://storage.bunnycdn.com/evict/socials/{old_filename}",
                                    headers=headers
                                ) as delete:
                                    print(f"Deleted old audio: {delete.status}")
                            except Exception as e:
                                print(f"Failed to delete old audio: {e}")

                        await self.generate_profile_image(ctx.author, force_update=True)
        except Exception as e:
            return await ctx.warn(f"Failed to set audio: {e}")

    @socials.command(name="togglefriends")
    async def socials_togglefriends(self, ctx: Context):
        """Toggle the visibility of your friends list."""
        current = await self.bot.db.fetchval(
            """
            SELECT show_friends 
            FROM socials 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        new_value = not current if current is not None else False
        await self.bot.db.execute(
            """
            UPDATE socials 
            SET show_friends = $1 
            WHERE user_id = $2
            """,
            new_value,
            ctx.author.id
        )
        await ctx.approve(f"Friends list visibility {'enabled' if new_value else 'disabled'}!")
        await self.generate_profile_image(ctx.author, force_update=True)

    @socials.command(name="toggleactivity")
    async def socials_toggleactivity(self, ctx: Context):
        """Toggle the visibility of your activity status."""
        support_guild = self.bot.get_guild(892675627373699072)
        if not support_guild or not support_guild.get_member(ctx.author.id):
            return await ctx.warn("You must be in the support server to use this feature!")

        current = await self.bot.db.fetchval(
            """
            SELECT show_activity 
            FROM socials 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        new_value = not current if current is not None else False
        await self.bot.db.execute(
            """
            UPDATE socials 
            SET show_activity = $1 
            WHERE user_id = $2
            """,
            new_value,
            ctx.author.id
        )
        await ctx.approve(f"Activity status visibility {'enabled' if new_value else 'disabled'}!")
        await self.generate_profile_image(ctx.author, force_update=True)

    @socials.group(name="colors", invoke_without_command=True)
    async def socials_colors(self, ctx: Context):
        """View your saved color sets."""
        linear_colors = await self.bot.db.fetch(
            """
            SELECT name, color 
            FROM socials_saved_colors 
            WHERE user_id = $1 AND type = 'linear'
            """, 
            ctx.author.id
        )
        
        gradient_sets = await self.bot.db.fetch(
            """
            SELECT DISTINCT name 
            FROM socials_saved_gradients 
            WHERE user_id = $1
            """,
            ctx.author.id
        )

        embed = discord.Embed(title="Your Saved Colors")
        
        if linear_colors:
            linear_text = "\n".join(f"• **{row['name']}**: {row['color']}" for row in linear_colors)
            embed.add_field(name="Linear Colors", value=linear_text, inline=False)
            
        if gradient_sets:
            gradient_text = "\n".join(f"• **{row['name']}**" for row in gradient_sets)
            embed.add_field(name="Gradient Sets", value=gradient_text, inline=False)
            
        if not linear_colors and not gradient_sets:
            embed.description = "No saved colors! Use `colors save` to save some."
            
        await ctx.send(embed=embed)

    @socials_colors.command(name="save")
    async def colors_save(self, ctx: Context, type: Literal["linear", "gradient"], name: str):
        """Save your current color setup with a name."""
        if len(name) > 32:
            return await ctx.warn("Name must be 32 characters or less!")

        if type == "linear":
            current = await self.bot.db.fetchval(
                """
                SELECT linear_color FROM socials 
                WHERE user_id = $1
                """, 
                ctx.author.id
            )
            if not current:
                return await ctx.warn("No linear color set to save!")
                
            await self.bot.db.execute(
                """
                INSERT INTO socials_saved_colors (user_id, name, color, type)
                VALUES ($1, $2, $3, 'linear')
                ON CONFLICT (user_id, name) 
                DO UPDATE SET color = $3
                """,
                ctx.author.id, name, current
            )
        else:
            colors = await self.bot.db.fetch(
                """
                SELECT color, position 
                FROM socials_gradients 
                WHERE user_id = $1 
                ORDER BY position
                """,
                ctx.author.id
            )
            if not colors:
                return await ctx.warn("No gradient colors set to save!")
                
            await self.bot.db.execute(
                """
                DELETE FROM socials_saved_gradients 
                WHERE user_id = $1 AND name = $2
                """,
                ctx.author.id, name
            )
            
            for color in colors:
                await self.bot.db.execute(
                    """
                    INSERT INTO socials_saved_gradients 
                    (user_id, name, color, position)
                    VALUES ($1, $2, $3, $4)
                    """,
                    ctx.author.id, name, color['color'], color['position']
                )
                
        await ctx.approve(f"Saved {type} colors as **{name}**!")

    @socials.command(name="apply")
    async def socials_apply(self, ctx: Context, element: Literal["text_underline", "bold_text", "status", "bio", "social_icons"], *, name: str):
        """Apply a saved color set to a profile element."""
        linear = await self.bot.db.fetchrow(
            """
            SELECT color FROM socials_saved_colors 
            WHERE user_id = $1 AND name = $2 AND type = 'linear'
            """,
            ctx.author.id, name
        )
        
        gradient = await self.bot.db.fetch(
            """
            SELECT color, position FROM socials_saved_gradients 
            WHERE user_id = $1 AND name = $2 
            ORDER BY position
            """,
            ctx.author.id, name
        )
        
        if not linear and not gradient:
            return await ctx.warn(f"No saved colors found with name **{name}**!")

        await self.bot.db.execute(
            """
            UPDATE socials 
            SET {}_color_type = $1,
                {}_linear_color = $2,
                {}_gradient_name = $3
            WHERE user_id = $4
            """.format(element, element, element),
            'linear' if linear else 'gradient',
            linear['color'] if linear else None,
            name if gradient else None,
            ctx.author.id
        )
        
        await ctx.approve(f"Applied **{name}** to {element.replace('_', ' ')}!")
        await self.generate_profile_image(ctx.author, force_update=True)

    @socials.command(name="remove")
    async def socials_remove(self, ctx: Context, element: Literal["text_underline", "bold_text", "status", "bio", "social_icons"]):
        """Remove colors from a profile element, resetting it to default."""
        await self.bot.db.execute(
            """
            UPDATE socials 
            SET {}_color_type = 'linear',
                {}_linear_color = '#ffffff',
                {}_gradient_name = NULL
            WHERE user_id = $1
            """.format(element, element, element),
            ctx.author.id
        )
        
        await ctx.approve(f"Removed colors from {element.replace('_', ' ')}!")
        await self.generate_profile_image(ctx.author, force_update=True)

    @socials_colors.group(name="gradient", invoke_without_command=True)
    async def colors_gradient(self, ctx: Context, name: str = None):
        """View a specific gradient set or list all your gradients."""
        if name:
            colors = await self.bot.db.fetch(
                """
                SELECT color, position 
                FROM socials_saved_gradients 
                WHERE user_id = $1 AND name = $2 
                ORDER BY position
                """,
                ctx.author.id, name
            )
            if not colors:
                return await ctx.warn(f"No gradient set found named **{name}**")
                
            embed = discord.Embed(title=f"Gradient Set: {name}")
            for color in colors:
                embed.add_field(
                    name=f"Position: {color['position']}%",
                    value=f"Color: {color['color']}",
                    inline=True
                )
        else:
            sets = await self.bot.db.fetch(
                """
                SELECT DISTINCT name 
                FROM socials_saved_gradients 
                WHERE user_id = $1
                """,
                ctx.author.id
            )
            if not sets:
                return await ctx.warn("No gradient sets saved! Use `colors gradient create` to make one.")
                
            embed = discord.Embed(title="Your Gradient Sets")
            embed.description = "\n".join(f"• **{row['name']}**" for row in sets)
            
        await ctx.send(embed=embed)

    @colors_gradient.command(name="create")
    async def gradient_create(self, ctx: Context, name: str):
        """Create a new gradient set."""
        if len(name) > 32:
            return await ctx.warn("Name must be 32 characters or less!")
            
        exists = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM socials_saved_gradients 
                WHERE user_id = $1 AND name = $2
            )
            """,
            ctx.author.id, name
        )
        if exists:
            return await ctx.warn(f"A gradient set named **{name}** already exists!")
            
        await ctx.approve(f"Created gradient set **{name}**! Add colors with `colors gradient add {name} #color position%`")

    @colors_gradient.command(name="add")
    async def gradient_add(self, ctx: Context, name: str, color: str, position: str):
        """Add a color to a gradient set. Color must be hex (#RRGGBB) and position must be 0-100%."""
        if not re.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$', color):
            return await ctx.warn("Invalid hex color! Must be in format #RRGGBB")
            
        try:
            position = int(position.strip('%'))
            if not 0 <= position <= 100:
                raise ValueError
        except ValueError:
            return await ctx.warn("Position must be between 0% and 100%")
            
        count = await self.bot.db.fetchval(
            """
            SELECT COUNT(*) FROM socials_saved_gradients 
            WHERE user_id = $1 AND name = $2
            """,
            ctx.author.id, name
        )
        
        if count >= 8:
            return await ctx.warn("You can only have up to 8 colors in a gradient!")
            
        await self.bot.db.execute(
            """
            INSERT INTO socials_saved_gradients 
            (user_id, name, color, position)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (user_id, name, position) 
            DO UPDATE SET color = $3
            """,
            ctx.author.id, name, color.lower(), position
        )
        await ctx.approve(f"Added {color} at position {position}% to gradient **{name}**")

    @colors_gradient.command(name="remove")
    async def gradient_remove(self, ctx: Context, name: str, position: str):
        """Remove a color from a gradient set by its position."""
        try:
            position = int(position.strip('%'))
        except ValueError:
            return await ctx.warn("Position must be a number between 0-100%")
            
        result = await self.bot.db.execute(
            """
            DELETE FROM socials_saved_gradients 
            WHERE user_id = $1 AND name = $2 AND position = $3
            """,
            ctx.author.id, name, position
        )
        
        if result == "DELETE 0":
            return await ctx.warn(f"No color found at position {position}% in gradient **{name}**")
            
        await ctx.approve(f"Removed color at position {position}% from gradient **{name}**")

    @colors_gradient.command(name="delete")
    async def gradient_delete(self, ctx: Context, name: str):
        """Delete an entire gradient set."""
        await ctx.prompt(f"Are you sure you want to delete gradient set **{name}**?")
        
        result = await self.bot.db.execute(
            """
            DELETE FROM socials_saved_gradients 
            WHERE user_id = $1 AND name = $2
            """,
            ctx.author.id, name
        )
        
        if result == "DELETE 0":
            return await ctx.warn(f"No gradient set found named **{name}**")
            
        await ctx.approve(f"Deleted gradient set **{name}**")

    @socials.group(name="click", invoke_without_command=True)
    async def socials_click(self, ctx: Context):
        """Toggle the click-to-enter feature for your profile."""
        current = await self.bot.db.fetchval(
            """
            SELECT click_enabled 
            FROM socials 
            WHERE user_id = $1
            """,
            ctx.author.id
        )
        
        new_value = not current if current is not None else True
        await self.bot.db.execute(
            """
            UPDATE socials 
            SET click_enabled = $1 
            WHERE user_id = $2
            """,
            new_value,
            ctx.author.id
        )
        await ctx.approve(f"Click to enter {'enabled' if new_value else 'disabled'}!")
        await self.generate_profile_image(ctx.author, force_update=True)

    @socials_click.command(name="text")
    async def socials_click_text(self, ctx: Context, *, text: str = None):
        """Set the text shown on the click-to-enter screen."""
        if not text:
            await ctx.prompt("Are you sure you want to reset your click text?")
            await self.bot.db.execute(
                """
                UPDATE socials 
                SET click_text = 'Click to enter...' 
                WHERE user_id = $1
                """,
                ctx.author.id
            )
            return await ctx.approve("Click text reset to default")

        if len(text) > 40:
            return await ctx.warn("Text must be 40 characters or less.")

        await self.bot.db.execute(
            """
            UPDATE socials 
            SET click_text = $1 
            WHERE user_id = $2
            """,
            text,
            ctx.author.id
        )
        await ctx.approve(f"Click text set to: {text}")
        await self.generate_profile_image(ctx.author, force_update=True)

    @socials.command(name="setguild")
    async def socials_setguild(self, ctx: Context, *, invite: str = None):
        """Set your featured Discord guild. Send without an invite to remove it."""
        if invite:
            try:
                invite = await self.bot.fetch_invite(invite)
                perm_invite = await invite.channel.create_invite(max_age=0, max_uses=0)
                
                await self.bot.db.execute(
                    """
                    UPDATE socials 
                    SET discord_guild = $1 
                    WHERE user_id = $2
                    """,
                    str(perm_invite.url),
                    ctx.author.id
                )
                await ctx.approve(f"Featured guild set to {invite.guild.name}!")
                asyncio.create_task(self.generate_profile_image(ctx.author, force_update=True))
            except:
                return await ctx.warn("Invalid invite link or missing permissions!")
        else:
            await ctx.prompt("Are you sure you want to remove your featured guild?")
            await self.bot.db.execute(
                """
                UPDATE socials 
                SET discord_guild = NULL 
                WHERE user_id = $1
                """,
                ctx.author.id
            )
            await ctx.approve("Featured guild removed!")
            await self.generate_profile_image(ctx.author, force_update=True)

    @socials.group(name="domain", invoke_without_command=True)
    async def socials_domain(self, ctx: Context):
        """Manage your custom domains"""
        return await ctx.send_help(ctx.command)

    @socials_domain.command(name="setup")
    async def domain_setup(self, ctx: Context, domain: str):
        """Setup a custom domain for your profile"""
        
        if not re.match(r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$', domain):
            return await ctx.warn("Please provide a valid domain name")

        domains = await self.bot.db.fetchval(
            """
            SELECT domains FROM socials WHERE user_id = $1
            """,
            ctx.author.id
        ) or []
        
        verified_domains = await self.bot.db.fetchval(
            """
            SELECT verified_domains FROM socials WHERE user_id = $1
            """,
            ctx.author.id
        ) or []

        if isinstance(domains, str):
            domains = json.loads(domains)
        if isinstance(verified_domains, str):
            verified_domains = json.loads(verified_domains)

        if domain in domains:
            return await ctx.warn("This domain is already in setup process!")
        
        if domain in verified_domains:
            return await ctx.warn("This domain is already verified!")
            
        if len(verified_domains) >= 2:
            return await ctx.warn("You can only have 2 verified domains at once!")

        await self.bot.db.execute(
            """
            UPDATE socials 
            SET domains = $1::jsonb
            WHERE user_id = $2
            """,
            json.dumps([domain]),
            ctx.author.id
        )

        embed = Embed(
            description=(
                "Please add the following records to your domain:\n\n"
                "**CNAME Record:** (Proxy Status: **OFF**)\n"
                f"`{domain}` → `cname.evict.bot`\n\n"
                "**TXT Record for Verification:**\n"
                f"`_evict-verify.{domain}` → `\"evict-verify={ctx.author.name}\"`\n\n"
                "**Important Notes:**\n"
                "> - Make sure the CNAME record is **NOT** proxied through Cloudflare\n"
                "> - DNS changes can take up to 24 hours to propagate\n"
                "> - Once records are added, use `domain verify` to verify ownership"
            )
        )
        
        await ctx.send(embed=embed)

    @socials_domain.command(name="verify")
    async def domain_verify(self, ctx: Context, domain: str):
        """Verify ownership of your domain"""
        
        domains = await self.bot.db.fetchval(
            """
            SELECT domains FROM socials WHERE user_id = $1
            """,
            ctx.author.id
        ) or []
        
        if isinstance(domains, str):
            domains = json.loads(domains)
            
        if domain not in domains:
            return await ctx.warn("This domain isn't in setup process! Use `domain setup` first")

        try:
            cname_records = await self.bot.loop.run_in_executor(
                None, 
                lambda: dns.resolver.resolve(domain, 'CNAME')
            )
            cname_valid = any(str(record.target).rstrip('.') == 'cname.evict.bot' for record in cname_records)
            
            if not cname_valid:
                return await ctx.warn("CNAME record is not properly configured")
                
            txt_records = await self.bot.loop.run_in_executor(
                None, 
                lambda: dns.resolver.resolve(f'_evict-verify.{domain}', 'TXT')
            )
            txt_valid = any(f"evict-verify={ctx.author.name}" in str(record) for record in txt_records)
            
            if not txt_valid:
                return await ctx.warn("TXT record is not properly configured")
                
            new_domains = [d for d in domains if d != domain]
            await self.bot.db.execute(
                """
                UPDATE socials 
                SET domains = $1::jsonb,
                    verified_domains = verified_domains || $2::jsonb
                WHERE user_id = $3
                """,
                json.dumps(new_domains),
                json.dumps([domain]),
                ctx.author.id
            )
            
            await ctx.approve(f"Domain `{domain}` has been verified successfully!")
                
        except dns.resolver.NXDOMAIN:
            return await ctx.warn("Could not find DNS records for this domain")
        except Exception as e:
            return await ctx.warn(f"Verification failed: {str(e)}")

    @socials_domain.command(name="list")
    async def domain_list(self, ctx: Context):
        """List your domains"""
        
        domains = await self.bot.db.fetchval(
            """
            SELECT domains FROM socials WHERE user_id = $1
            """,
            ctx.author.id
        ) or []
        
        verified_domains = await self.bot.db.fetchval(
            """
            SELECT verified_domains FROM socials WHERE user_id = $1
            """,
            ctx.author.id
        ) or []
        
        embed = Embed(title="Your Domains")
        
        if verified_domains:
            embed.add_field(
                name="Verified Domains",
                value="\n".join(f"• `{domain}`" for domain in verified_domains),
                inline=False
            )
        
        if domains:
            embed.add_field(
                name="Pending Verification",
                value="\n".join(f"• `{domain}`" for domain in domains),
                inline=False
            )
            
        if not domains and not verified_domains:
            embed.description = "You don't have any domains set up!"
            
        await ctx.send(embed=embed)

    @socials_domain.command(name="remove")
    async def domain_remove(self, ctx: Context, domain: str):
        """Remove a domain from your profile"""
        
        verified_domains = await self.bot.db.fetchval(
            """
            SELECT verified_domains FROM socials WHERE user_id = $1
            """,
            ctx.author.id
        ) or []
        
        if domain not in verified_domains:
            return await ctx.warn("This domain isn't verified!")
            
        await ctx.prompt(f"Are you sure you want to remove `{domain}`?")
        
        await self.bot.db.execute(
            """
            UPDATE socials 
            SET verified_domains = verified_domains - $1::text
            WHERE user_id = $2
            """,
            domain,
            ctx.author.id
        )
        
        await ctx.approve(f"Domain `{domain}` has been removed!")

    @hybrid_command(name="blend", description="Mix two emojis together", aliases=["emix", "emojimix", "mixemoji"], brief="Mix two emojis together", fallback="emojis")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    @cooldown(1, 5, BucketType.user)
    async def jumboo(self, ctx: Context, emoji1: str, emoji2: str) -> Message:
        """Mix two emojis together and create a jumbo version."""
        
        if not all(c in emoji1 + emoji2 for c in ('️', '⃣', '️')):
            if not all(ord(c) > 127 for c in emoji1 + emoji2):
                return await ctx.warn("Please provide valid Unicode emojis!")

        try:
            not_found = Image.open("assets/notfound.png")
            not_found_bytes = io.BytesIO()
            not_found.save(not_found_bytes, format='PNG')
            not_found_bytes = not_found_bytes.getvalue()
            
            url = f"https://emojik.vercel.app/s/{emoji1}_{emoji2}?size=256"
            
            async with self.bot.session.get(url) as response:
                if response.status != 200:
                    url = f"https://emojik.vercel.app/s/{emoji2}_{emoji1}?size=256"
                    async with self.bot.session.get(url) as response2:
                        if response2.status != 200:
                            return await ctx.warn("Those emojis can't be mixed!")
                        response_bytes = await response2.read()
                else:
                    response_bytes = await response.read()
            
            if response_bytes == not_found_bytes:
                return await ctx.warn("Those emojis can't be mixed!")
                
            buffer = io.BytesIO(response_bytes)
            return await ctx.send(file=discord.File(buffer, "jumbo.png"))
            
        except Exception as e:
            return await ctx.warn("Failed to create jumbo emoji!")

    @command(name="mini", description="Get AI responses using O3-mini", example="explain quantum computing")
    async def mini(self, ctx: Context, *, prompt: str) -> Message:
        """
        Get responses using OpenAI's O1-mini model.
        Premium users get $15 worth of credits per 2 weeks.
        Free users get 10 uses per day.
        
        Cost: $0.01 per response
        """
        if len(prompt) > 4000:
            return await ctx.warn("Prompt cannot exceed 4000 characters!")
            
        minute_key = f"mini_minute:{ctx.author.id}"
        minute_uses = await self.bot.redis.get(minute_key)
        if minute_uses and int(minute_uses) >= 10:
            return await ctx.warn("You can only use this command 10 times per minute. Please wait a moment.")

        is_donor = await self.bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM donators 
                WHERE user_id = $1
            )
            """,
            ctx.author.id
        )

        base_cost = decimal.Decimal('0.01')  

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

            if credits < base_cost:
                return await ctx.warn(
                    f"Insufficient credits! You have ${credits:.3f} remaining.\n"
                    f"This response would cost ${base_cost:.3f}.\n"
                    "Credits reset every 2 weeks."
                )
        else:
            key = f"mini:{ctx.author.id}"
            uses = await self.bot.redis.get(key)
            ttl = await self.bot.redis.ttl(key)
            
            if uses and int(uses) >= 10:  
                embed = discord.Embed(
                    color=config.COLORS.WARN,
                    description=f"> {config.EMOJIS.CONTEXT.WARN} {ctx.author.mention}: Rate limit exceeded! Try again in {int(ttl)} seconds.\n\nDonors get $15 worth of credits every 2 weeks! Consider upgrading for increased access."
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

        if not isinstance(ctx.channel, discord.DMChannel):
            async with ctx.typing():
                try:
                    response = await self.bot.session.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {config.AUTHORIZATION.OPENAI}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "o1-mini",
                            "messages": [{"role": "user", "content": prompt}],
                            "max_completion_tokens": 1500,
                        }
                    )

                    if response.status != 200:
                        error_data = await response.json()
                        log.error(
                            f"O1-mini generation failed: Status {response.status}\n"
                            f"Error: {error_data}\n"
                            f"User: {ctx.author} ({ctx.author.id})\n"
                            f"Prompt: {prompt}"
                        )
                        return await ctx.warn(f"Failed to generate response: {error_data.get('error', {}).get('message', 'Unknown error')}")

                    data = await response.json()
                    log.info(f"Full API response: {data}")
                    
                    response_text = data["choices"][0]["message"]["content"]
                    if len(response_text) > 2000:
                        entries = [response_text[i:i+2000] for i in range(0, len(response_text), 2000)]
                        paginator = Paginator(
                            ctx,
                            entries=entries,
                            per_page=1,
                            embed=discord.Embed(title="O1-mini Response")
                        )
                        return await paginator.start()
                    else:
                        embed = discord.Embed(
                            title="O1-mini Response",
                            description=response_text
                        )

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
                        embed.set_footer(text="Free User • 10 uses per day")

                    pipe = self.bot.redis.pipeline()
                    pipe.incr(minute_key)
                    pipe.expire(minute_key, 60)
                    await pipe.execute()

                    return await ctx.send(embed=embed)

                except Exception as e:
                    log.error(
                        f"O3-mini generation error:\n"
                        f"Error: {str(e)}\n"
                        f"User: {ctx.author} ({ctx.author.id})\n"
                        f"Prompt: {prompt}",
                        exc_info=True
                    )
                    return await ctx.warn(f"Failed to generate response: {str(e)}")


    # async def get_user_badges(self, user: Member | User) -> list:
    #     badges = []
    #     staff_eligible = False
        
    #     support_guild = self.bot.get_guild(892675627373699072)
    #     if support_guild:
    #         support_member = support_guild.get_member(user.id)
    #         if support_member:
    #             role_badges = {
    #                 1265473601755414528: ["developer", "owner"],
    #                 1264110559989862406: ["support"],
    #                 1323255508609663098: ["trial"],
    #                 1325007612797784144: ["mod"],
    #                 1318054098666389534: ["donor1"],
    #                 1320428924215496704: ["donor4"]
    #             }

    #             for role_id, badge_types in role_badges.items():
    #                 if any(role.id == role_id for role in support_member.roles):
    #                     badges.extend(badge_types)
    #                     if role_id not in [1318054098666389534, 1320428924215496704]:
    #                         staff_eligible = True

    #             if staff_eligible:
    #                 badges.append("staff")
                    
    #     return badges

#     @socials.command(name="ogimage")
#     async def socials_ogimage(self, ctx: Context, user: Member | User = None):
#         if not user:
#             user = ctx.author

#         socials, badges = await asyncio.gather(
#             self.bot.db.fetchrow(
#                 "SELECT background_url FROM socials WHERE user_id = $1",
#                 user.id
#             ),
#             self.get_user_badges(user)
#         )

#         width, height = 1200, 630
#         image = Image.new('RGBA', (width, height))
#         draw = ImageDraw.Draw(image)

#         try:
#             if socials and socials['background_url']:
#                 async with aiohttp.ClientSession() as session:
#                     async with session.get(socials['background_url']) as resp:
#                         if resp.status == 200:
#                             bg_data = await resp.read()
#                             background = Image.open(BytesIO(bg_data)).convert('RGBA')
#                             bg_ratio = width / height
#                             img_ratio = background.width / background.height
                            
#                             if img_ratio > bg_ratio:
#                                 new_width = int(height * img_ratio)
#                                 background = background.resize((new_width, height))
#                                 left = (new_width - width) // 2
#                                 background = background.crop((left, 0, left + width, height))
#                             else:
#                                 new_height = int(width / img_ratio)
#                                 background = background.resize((width, new_height))
#                                 top = (new_height - height) // 2
#                                 background = background.crop((0, top, width, top + height))
#                             image.paste(background, (0, 0))
#             else:
#                 image.paste((24, 24, 27), (0, 0, width, height))

#             overlay = Image.new('RGBA', (width, height), (0, 0, 0, 80))
#             image.paste(overlay, (0, 0), overlay)

#             avatar_size = 160
#             avatar_url = user.display_avatar.url
#             async with aiohttp.ClientSession() as session:
#                 async with session.get(str(avatar_url)) as resp:
#                     if resp.status == 200:
#                         avatar_data = await resp.read()
#                         avatar = Image.open(BytesIO(avatar_data))
#                         avatar = avatar.resize((avatar_size, avatar_size))
                        
#                         mask = Image.new('L', (avatar_size, avatar_size), 0)
#                         draw_mask = ImageDraw.Draw(mask)
#                         draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                        
#                         output = Image.new('RGBA', (avatar_size, avatar_size), (0, 0, 0, 0))
#                         output.paste(avatar, (0, 0))
#                         output.putalpha(mask)
                        
#                         avatar_x = (width - avatar_size) // 2
#                         avatar_y = height // 4 - avatar_size // 4
#                         image.paste(output, (avatar_x, avatar_y), output)

#             username_font = ImageFont.truetype("assets/fonts/Montserrat-SemiBold.ttf", 75)
#             link_font = ImageFont.truetype("assets/fonts/Montserrat-Regular.ttf", 32)
            
#             username = user.name
#             if len(username) > 15:
#                 username_font = ImageFont.truetype("assets/fonts/Montserrat-SemiBold.ttf", 70)
            
#             bbox = draw.textbbox((0, 0), username, font=username_font)
#             text_width = bbox[2] - bbox[0]
#             username_x = (width - text_width) // 2
#             username_y = avatar_y + avatar_size + 20
#             draw.text((username_x, username_y), username, font=username_font, fill=(255, 255, 255))

#             if badges:
#                 badge_size = 28
#                 badge_bg_size = 36
#                 badge_spacing = 0
#                 total_width = len(badges) * badge_bg_size
#                 badge_start_x = (width - total_width) // 2
#                 badge_y = username_y + 100

#                 container_width = total_width
#                 container_height = badge_bg_size
#                 container = Image.new('RGBA', (container_width, container_height), (24, 24, 27))
#                 container_mask = Image.new('L', (container_width, container_height))
#                 container_draw = ImageDraw.Draw(container_mask)
#                 container_draw.rounded_rectangle((0, 0, container_width, container_height), radius=8, fill=255)
                
#                 image.paste(container, (badge_start_x, badge_y), container_mask)

#                 for i, badge in enumerate(badges):
#                     try:
#                         badge_path = f"assets/badges/slugs/{badge}.png"
#                         badge_img = Image.open(badge_path).convert('RGBA')
#                         badge_img = badge_img.resize((badge_size, badge_size))
                        
#                         x = badge_start_x + i * badge_bg_size
#                         icon_x = x + (badge_bg_size - badge_size) // 2
#                         icon_y = badge_y + (badge_bg_size - badge_size) // 2
#                         image.paste(badge_img, (icon_x, icon_y), badge_img)
#                     except Exception as e:
#                         continue

#             profile_link = f"evict.bot/@{user.name}"
#             bbox = draw.textbbox((0, 0), profile_link, font=link_font)
#             link_width = bbox[2] - bbox[0]
#             link_x = (width - link_width) // 2
#             link_y = badge_y + 60 if badges else username_y + 80
#             draw.text((link_x, link_y), profile_link, font=link_font, fill=(160, 160, 180))

#         except Exception as e:
#             return await ctx.warn(f"Failed to generate image: {e}")

#         buffer = BytesIO()
#         image.save(buffer, 'PNG')
#         buffer.seek(0)
        
#         await ctx.send(file=discord.File(buffer, 'profile.png'))

# def generate_gradient(width, height, color1, color2):
#     """Generate a diagonal gradient (bottom-right)."""
#     base = Image.new('RGBA', (width, height), color1)
#     top = Image.new('RGBA', (width, height), color2)
#     mask = Image.new('L', (width, height))
#     mask_data = []
    
#     for y in range(height):
#         for x in range(width):
#             # Calculate gradient value based on position
#             # This creates a diagonal gradient
#             value = int(255 * ((x / width + y / height) / 2))
#             mask_data.append(value)
            
#     mask.putdata(mask_data)
#     base.paste(top, (0, 0), mask)
#     return base