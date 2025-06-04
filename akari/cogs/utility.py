import asyncio
import datetime
import json
import os
import random

import aiohttp
import dateutil.parser
import discord
import humanfriendly
import humanize
import uwuify
import validators
from nudenet import NudeDetector

nude_detector = NudeDetector()

import re
from io import BytesIO
from typing import Any, Optional, Union

import rembg
from deep_translator import GoogleTranslator
from deep_translator.exceptions import LanguageNotSupportedException
from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import has_guild_permissions
from playwright.async_api import async_playwright
from shazamio import Shazam
from tools.bot import Akari
from tools.handlers.socials.cashapp import CashappUser
from tools.handlers.socials.github import GithubUser
from tools.handlers.socials.instagram import InstagramUser
from tools.handlers.socials.roblox import RobloxUser
from tools.handlers.socials.snapchat import SnapUser
from tools.handlers.socials.tiktok import TikTokUser
from tools.handlers.socials.weather import WeatherLocation
from tools.helpers import AkariContext
from tools.misc.utils import (BdayDate, BdayMember, Timezone, TimezoneLocation,
                              TimezoneMember, get_color)
from tools.misc.views import Donate
from tools.predicates import is_afk, is_there_a_reminder, reminder_exists
from tools.validators import ValidTime


class Color(commands.Converter):
    async def convert(self, ctx: AkariContext, argument: str):
        argument = str(argument)

        if argument.lower() in ("random", "rand", "r"):
            return discord.Color.random()
        elif argument.lower() in ("invisible", "invis"):
            return discord.Color.from_str("#2F3136")

        if color := get_color(argument):
            return color
        else:
            raise commands.CommandError(f"Color **{argument}** not found")


class Utility(commands.Cog):
    def __init__(self, bot: Akari):
        self.bot = bot
        self.tz = Timezone(bot)
        self.description = "Utility commands"
        self.afk_cd = commands.CooldownMapping.from_cooldown(
            3, 3, commands.BucketType.channel
        )

    def human_format(self, number: int) -> str:
        """
        Humanize a number, if the case
        """

        if number > 999:
            return humanize.naturalsize(number, False, True)

        return number.__str__()

    def afk_ratelimit(self, message: discord.Message) -> Optional[int]:
        """
        Cooldown for the afk message event
        """

        bucket = self.afk_cd.get_bucket(message)
        return bucket.update_rate_limit()

    async def cache_profile(self, member: discord.User) -> Any:
        """
        Cache someone's banner
        """

        if member.banner:
            banner = member.banner.url
        else:
            banner = None

        return await self.bot.cache.set(
            f"profile-{member.id}", {"banner": banner}, 3600
        )

    def get_joined_date(self, date) -> str:
        if date.month < 10:
            month = (self.tz.months.get(date.month))[:3]
        else:
            month = (self.tz.months.get(date.month))[:3]

        return f"Joined {month} {date.day} {str(date.year)}"

    @commands.Cog.listener("on_message")
    async def seen_listener(self, message: discord.Message):
        if message.author.bot:
            return

        check = await self.bot.db.fetchrow(
            """
      SELECT * FROM seen
      WHERE user_id = $1
      AND guild_id = $2
      """,
            message.author.id,
            message.guild.id,
        )
        args = [message.author.id, message.guild.id, datetime.datetime.now()]

        if not check:
            await self.bot.db.execute("INSERT INTO seen VALUES ($1,$2,$3)", *args)
        else:
            await self.bot.db.execute(
                "UPDATE seen SET time = $3 WHERE user_id = $1 AND guild_id = $2", *args
            )

    @commands.Cog.listener("on_message")
    async def stickymessage_listener(self, message: discord.Message):
        if message.author.bot:
            return

        check = await self.bot.db.fetchrow(
            """
      SELECT * FROM stickymessage
      WHERE channel_id = $1
      AND guild_id = $2
      """,
            message.channel.id,
            message.guild.id,
        )
        if check:
            lastmsg = self.bot.cache.get(
                f"sticky-{message.guild.id}-{message.channel.id}"
            )
            if lastmsg:
                lastmsg = await message.channel.fetch_message(str(lastmsg))
                await lastmsg.delete()
            newmsg = await message.channel.send(check["message"])
            await self.bot.cache.set(
                f"sticky-{message.guild.id}-{message.channel.id}", newmsg.id, 3600
            )

    @commands.Cog.listener("on_message")
    async def afk_listener(self, message: discord.Message):
        if message.is_system():
            return

        if not message.guild:
            return

        if not message.author:
            return

        if message.author.bot:
            return

        if check := await self.bot.db.fetchrow(
            "SELECT * FROM afk WHERE guild_id = $1 AND user_id = $2",
            message.guild.id,
            message.author.id,
        ):
            ctx = await self.bot.get_context(message)
            time = check["time"]
            await self.bot.db.execute(
                "DELETE FROM afk WHERE guild_id = $1 AND user_id = $2",
                message.guild.id,
                message.author.id,
            )
            embed = discord.Embed(
                color=self.bot.color,
                description=f"👋 {ctx.author.mention}: Welcome back! You were gone for **{humanize.precisedelta(datetime.datetime.fromtimestamp(time.timestamp()), format='%0.0f')}**",
            )
            return await ctx.reply(embed=embed)

        for mention in message.mentions:
            check = await self.bot.db.fetchrow(
                "SELECT * FROM afk WHERE guild_id = $1 AND user_id = $2",
                message.guild.id,
                mention.id,
            )
            if check:
                if self.afk_ratelimit(message):
                    continue

                ctx = await self.bot.get_context(message)
                time = check["time"]
                embed = discord.Embed(
                    color=self.bot.color,
                    description=f"👋 {ctx.author.mention}: **{mention.name}** is **AFK** for **{humanize.precisedelta(datetime.datetime.fromtimestamp(time.timestamp()), format='%0.0f')}** - {check['reason']}",
                )
                return await ctx.reply(embed=embed)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if (before.avatar != after.avatar) or (before.banner != after.banner):
            if before.avatar != after.avatar:
                imgtype = "gif" if before.display_avatar.is_animated() else "png"
                try:

                    async with aiohttp.ClientSession() as session:
                        async with session.request(
                            "POST",
                            "http://127.0.0.1:3030/upload",
                            json={
                                "url": before.display_avatar.url,
                                "type": imgtype,
                                "userid": str(after.id),
                                "name": after.name,
                            },
                            headers={
                                "Authorization": "hmfq0U9odsH3T7X0ICK6oWJN",
                                "Content-Type": "application/json",
                            },
                        ) as r:
                            if r.status != 200:
                                await session.close()
                                return
                            if r.status == 200:
                                await session.close()
                except Exception as e:
                    await session.close()
                    return

            cache = self.bot.cache.get(f"profile-{before.id}")
            if cache:
                await self.cache_profile(after)

    @commands.command(aliases=["uwu"])
    async def uwuify(self, ctx: AkariContext, *, message: str):
        """
        Convert a message to the uwu format
        """

        flags = uwuify.YU | uwuify.STUTTER
        embed = discord.Embed(
            color=self.bot.color, description=uwuify.uwu(message, flags=flags)
        )
        return await ctx.reply(embed=embed)

    @commands.command(aliases=["foryou", "foryoupage"])
    async def fyp(self, ctx: AkariContext):
        "Get a random TikTok video"

        async with ctx.typing():
            recommended = await self.bot.session.get_json(
                url="https://www.tiktok.com/api/recommend/item_list/?WebIdLastTime=1709562791&aid=1988&app_language=en&app_name=tiktok_web&browser_language=en-US&browser_name=Mozilla&browser_online=true&browser_platform=Win32&browser_version=5.0%20%28Windows%20NT%2010.0%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F124.0.0.0%20Safari%2F537.36&channel=tiktok_web&clientABVersions=70508271%2C72097972%2C72118536%2C72139452%2C72142433%2C72147654%2C72156694%2C72157773%2C72174908%2C72183344%2C72191581%2C72191933%2C72203590%2C72211002%2C70405643%2C71057832%2C71200802%2C71957976&cookie_enabled=true&count=9&coverFormat=2&device_id=7342516164603889184&device_platform=web_pc&device_type=web_h264&focus_state=true&from_page=fyp&history_len=3&isNonPersonalized=false&is_fullscreen=false&is_page_visible=true&language=en&odinId=7342800074206741537&os=windows&priority_region=&pullType=1&referer=&region=BA&screen_height=1440&screen_width=2560&showAboutThisAd=true&showAds=false&tz_name=Europe%2FLondon&watchLiveLastTime=1713523355360&webcast_language=en&msToken=W3zoVLSFi9M0BsPE6uC63GCdeoVC7hmjRNelZIe-7FP7x-1LRee6WYHYfpWXg3NYPoreJf_dMxfRWTZprVN8UU70_IaHnBMNirtZIRNp2QuR1nBivJgnetgiM-XTh7_KGbNswVs=&X-Bogus=DFSzswVOmtvANegtt2bDG-OckgSu&_signature=_02B4Z6wo00001BozSvQAAIDBhqj5OL8769AaM05AAGCne"
            )
            recommended = recommended["itemList"][0]
            embed = discord.Embed(color=self.bot.color)
            embed.description = f'[{recommended["desc"]}](https://tiktok.com/@{recommended["author"]["uniqueId"]}/video/{recommended["id"]})'

            embed.set_footer(
                text=f"❤️ {self.bot.session.human_format(recommended['stats']['diggCount'])} 💬 {self.bot.session.human_format(recommended['stats']['commentCount'])} 🔗 {self.bot.session.human_format(recommended['stats']['shareCount'])} ({self.bot.session.human_format(recommended['stats']['playCount'])} views)"
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
                    fp=await self.bot.session.getbyte(url=final["data"]["play"]),
                    filename="resenttiktok.mp4",
                ),
            )
            try:
                await ctx.message.delete()
            except:
                pass

    """@commands.command(aliases=["avh"])
    async def avatarhistory(
        self, ctx: AkariContext, *, member: discord.User = commands.Author
    ):

        results = await self.bot.db.fetchrow(
            "SELECT * FROM avatar_history WHERE user_id = $1", str(member.id)
        )
        length = len(json.loads(results["avatars"])) if results else 0
        if not results:
            does = "don't" if member == ctx.author else f"doesn't"
            return await ctx.error(
                f"{'You' if member == ctx.author else f'{member.mention}'} {does} have an **avatar history**"
            )

        embed = discord.Embed(
            color=self.bot.color,
            url=f"https://images.Akari.bot/avatarhistory/{member.id}",
            title=f"{member.name}'s avatar history ({length})",
        )
        return await ctx.reply(embed=embed)"""

    """@commands.command(aliases=["clearavs", "clearavh", "clearavatarhistory"])
    async def clearavatars(self, ctx: AkariContext):


        check = await self.bot.db.fetchrow(
            "SELECT * FROM avatar_history WHERE user_id = $1", str(ctx.author.id)
        )
        if not check:
            return await ctx.warning("There are no avatars saved for you")

        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute(
                "DELETE FROM avatar_history WHERE user_id = $1",
                str(interaction.user.id),
            )
            return await interaction.response.edit_message(
                embed=discord.Embed(
                    color=self.bot.yes_color,
                    description=f"{self.bot.yes} {interaction.user.mention}: Cleared your avatar history",
                ),
                view=None,
            )

        async def no_func(interaction: discord.Interaction):
            return await interaction.response.edit_message(
                embed=discord.Embed(
                    color=self.bot.color,
                    description=f"{interaction.user.mention}: Aborting action",
                ),
                view=None,
            )

        await ctx.confirmation_send(
            "Are you sure you want to **clear** your avatar history?", yes_func, no_func
        )"""

    @commands.command(aliases=["firstmsg"])
    async def firstmessage(
        self,
        ctx: AkariContext,
        *,
        channel: discord.TextChannel = commands.CurrentChannel,
    ):
        """
        Get the first message in a channel
        """

        message = [mes async for mes in channel.history(limit=1, oldest_first=True)][0]
        await ctx.akari_send(
            f"the first message sent in {channel.mention} - [**jump**]({message.jump_url})"
        )

    @commands.hybrid_command(aliases=["av"])
    async def avatar(
        self,
        ctx: AkariContext,
        *,
        member: Union[discord.Member, discord.User] = commands.Author,
    ):
        """
        Return someone's avatar
        """

        if member.avatar is None:
            return await ctx.warning(f"{member.mention} **doesn't** have a avatar set.")

        embed = discord.Embed(
            color=await self.bot.dominant_color(member.display_avatar.url),
            title=f"{member.name}'s avatar",
            url=member.display_avatar.url,
        )

        embed.set_image(url=member.display_avatar.url)
        return await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["sav"])
    async def serveravatar(
        self,
        ctx: AkariContext,
        *,
        member: discord.Member = commands.Author,
    ):
        """
        Return someone's avatar
        """

        if member.guild_avatar is None:
            return await ctx.warning(
                f"{member.mention} **doesn't** have a guild avatar set."
            )

        embed = discord.Embed(
            color=await self.bot.dominant_color(member.guild_avatar.url),
            title=f"{member.name}'s avatar",
            url=member.guild_avatar.url,
        )

        embed.set_image(url=member.guild_avatar.url)
        return await ctx.reply(embed=embed)

    @commands.group(
        name="stickymessage",
        aliases=["stickymsg", "sticky"],
        invoke_without_command=True,
    )
    async def stickymessage(self, ctx: AkariContext):
        return await ctx.create_pages()

    @stickymessage.command(name="add", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def stickymessage_add(
        self, ctx: AkariContext, channel: TextChannel, *, code: str
    ):
        """add a sticky message to the server"""
        check = await self.bot.db.fetchrow(
            "SELECT * FROM stickymessage WHERE channel_id = $1", channel.id
        )
        if check:
            args = [
                "UPDATE stickymessage SET message = $1 WHERE channel_id = $2",
                code,
                channel.id,
            ]
        else:
            args = [
                "INSERT INTO stickymessage VALUES ($1,$2,$3)",
                ctx.guild.id,
                channel.id,
                code,
            ]

        await self.bot.db.execute(*args)
        return await ctx.success(
            f"Added sticky message to {channel.mention}\n```{code}```"
        )

    @stickymessage.command(name="remove", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def stickymessage_remove(self, ctx: AkariContext, *, channel: TextChannel):
        """remove a sticky message from the server"""
        check = await self.bot.db.fetchrow(
            "SELECT * FROM stickymessage WHERE channel_id = $1", channel.id
        )
        if not check:
            return await ctx.warning(
                "There is no sticky message configured in this channel"
            )

        await self.bot.db.execute(
            "DELETE FROM stickymessage WHERE channel_id = $1", channel.id
        )
        return await ctx.success(f"Deleted the sticky message from {channel.mention}")

    @commands.command(aliases=["pastusernanes", "usernames", "oldnames", "pastnames"])
    async def names(self, ctx: AkariContext, *, user: discord.User = commands.Author):
        """
        Check a member's past usernames
        """

        results = await self.bot.db.fetch(
            "SELECT * FROM usernames WHERE user_id = $1", user.id
        )
        if len(results) == 0:
            return await ctx.error(
                f"{'You' if user == ctx.author else f'{user.mention}'} doesn't have **past usernames**"
            )

        users = sorted(results, key=lambda m: m["time"], reverse=True)

        return await ctx.paginate(
            [
                f"**{result['user_name']}** - {discord.utils.format_dt(datetime.datetime.fromtimestamp(result['time']), style='R')}"
                for result in users
            ],
            f"Username changes ({len(users)})",
            {"name": user.name, "icon_url": user.display_avatar.url},
        )

    @commands.command(aliases=["clearusernames", "deletenames", "deleteusernames"])
    async def clearnames(self, ctx: AkariContext):
        """clear your username history"""
        check = await self.bot.db.fetchrow(
            "SELECT * FROM usernames WHERE user_id = $1", ctx.author.id
        )
        if not check:
            return await ctx.warning("There are no usernames saved for you")

        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute(
                "DELETE FROM usernames WHERE user_id = $1", interaction.user.id
            )
            return await interaction.response.edit_message(
                embed=discord.Embed(
                    color=self.bot.yes_color,
                    description=f"{self.bot.yes} {interaction.user.mention}: Cleared your username history",
                ),
                view=None,
            )

        async def no_func(interaction: discord.Interaction):
            return await interaction.response.edit_message(
                embed=discord.Embed(
                    color=self.bot.color,
                    description=f"{interaction.user.mention}: Aborting action",
                ),
                view=None,
            )

        await ctx.confirmation_send(
            "Are you sure you want to **clear** your username history?",
            yes_func,
            no_func,
        )

    @commands.hybrid_command()
    async def banner(
        self, ctx: AkariContext, *, member: discord.User = commands.Author
    ):
        """
        Get someone's banner
        """

        cache = self.bot.cache.get(f"profile-{member.id}")

        if cache:
            banner = cache["banner"]

            if banner is None:
                return await ctx.warning(f"{member.mention} **doesn't** have a banner")

        else:
            user = await self.bot.fetch_user(member.id)

            if not user.banner:
                await self.cache_profile(user)
                return await ctx.warning(f"{member.mention} **doesn't** have a banner")

            banner = user.banner.url

        embed = discord.Embed(
            color=await self.bot.dominant_color(banner),
            title=f"{member.name}'s banner",
            url=banner,
        )
        embed.set_image(url=banner)
        return await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["ri"])
    async def roleinfo(self, ctx: AkariContext, *, role: Optional[discord.Role] = None):
        """
        Information about a role
        """

        if role is None:
            role = ctx.author.top_role

        embed = (
            discord.Embed(
                color=role.color if role.color.value != 0 else self.bot.color,
                title=role.name,
            )
            .set_author(
                name=ctx.author.name,
                icon_url=(
                    role.display_icon
                    if isinstance(role.display_icon, discord.Asset)
                    else None
                ),
            )
            .add_field(name="Role ID", value=f"`{role.id}`")
            .add_field(
                name="Role color",
                value=(
                    f"`#{hex(role.color.value)[2:]}`"
                    if role.color.value != 0
                    else "No color"
                ),
            )
            .add_field(
                name="Created",
                value=f"{discord.utils.format_dt(role.created_at, style='f')} **{self.bot.humanize_date(role.created_at.replace(tzinfo=None))}**",
                inline=False,
            )
            .add_field(
                name=f"{len(role.members)} Member{'s' if len(role.members) != 1 else ''}",
                value=(
                    ", ".join([str(m) for m in role.members])
                    if len(role.members) < 7
                    else f"{', '.join([str(m) for m in role.members][:7])} + {len(role.members)-7} others"
                ),
                inline=False,
            )
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(name="channelinfo", aliases=["ci"])
    async def channelinfo(
        self, ctx: AkariContext, *, channel: Optional[TextChannel] = None
    ):
        """
        view information about a channel
        """

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

        await ctx.reply(embed=embed)

    @commands.command()
    async def donators(self, ctx: AkariContext):
        """
        Returns a list of all donators
        """

        results = await self.bot.db.fetch("SELECT * FROM donor")
        res = sorted(results, key=lambda m: m["since"], reverse=True)
        return await ctx.paginate(
            [
                f"<@!{result['user_id']}> - <t:{int(result['since'])}:R> {'<a:boost:1105870150588182539>' if result['status'] == 'boosted' else '💸'}"
                for result in res
            ],
            f"Akari donators ({len(results)})",
        )

    @commands.hybrid_command()
    async def invites(
        self, ctx: AkariContext, *, member: discord.Member = commands.Author
    ):
        """
        returns the number of invites you have in the server
        """

        invites = await ctx.guild.invites()
        await ctx.akari_send(
            f"{f'{member.mention} has' if member.id != ctx.author.id else 'You have'} **{sum(invite.uses for invite in invites if invite.inviter == member)} invites**"
        )

    @commands.command(aliases=["cs"], brief="manage messages")
    @commands.has_guild_permissions(manage_messages=True)
    async def clearsnipes(self, ctx: AkariContext):
        """
        Clear the snipes from the channel
        """

        for i in ["snipe", "edit_snipe", "reaction_snipe"]:
            snipes = self.bot.cache.get(i)

            if snipes:
                for s in [m for m in snipes if m["channel"] == ctx.channel.id]:
                    snipes.remove(s)
                await self.bot.cache.set(i, snipes)

        await ctx.success("Cleared all snipes from this channel")

    @commands.command(aliases=["rs"])
    async def reactionsnipe(self, ctx: AkariContext, index: int = 1):
        """
        Get the most recent message with a reaction removed in this channel
        """

        if not self.bot.cache.get("reaction_snipe"):
            return await ctx.warning("No reaction snipes found in this channel")

        snipes = [
            s
            for s in self.bot.cache.get("reaction_snipe")
            if s["channel"] == ctx.channel.id
        ]

        if len(snipes) == 0:
            return await ctx.warning("No reaction snipes found in this channel")

        if index > len(snipes):
            return await ctx.warning(
                f"There are only **{len(snipes)}** reaction snipes in this channel"
            )

        result = snipes[::-1][index - 1]
        try:
            message = await ctx.channel.fetch_message(result["message"])
            return await ctx.akari_send(
                f"**{result['user']}** reacted with {result['reaction']} **{self.bot.humanize_date(datetime.datetime.fromtimestamp(int(result['created_at'])))}** [**here**]({message.jump_url})"
            )
        except:
            return await ctx.akari_send(
                f"**{result['user']}** reacted with {result['reaction']} **{self.bot.humanize_date(datetime.datetime.fromtimestamp(int(result['created_at'])))}**"
            )

    @commands.command(aliases=["ss", "screenie"])
    async def screenshot(self, ctx: AkariContext, url: str):
        # Check if the URL is valid
        if not url.startswith(("https://", "http://")):
            url = f"https://{url}"

        if not validators.url(url):
            return await ctx.warning("That is not a **URL**")

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            # Navigate to the specified URL
            await ctx.channel.typing()
            await page.goto(url)
            # Capture screenshot
            screenshot_file = f"{url.replace('https://', '').replace('/', '_')}.png"
            await page.screenshot(path=screenshot_file)

            # Define the keywords to detect
            keywords = ["pussy", "tits", "porn"]

            # Read the page content
            page_content = await page.content()

            # Check if any of the keywords are present in the page content
            if any(
                re.search(r"\b{}\b".format(keyword), page_content, re.IGNORECASE)
                for keyword in keywords
            ):
                await ctx.error(
                    "This website contains explicit content. I cannot send the screenshot."
                )
                return
            detections = nude_detector.detect(screenshot_file)
            for prediction in detections:

                if (
                    prediction["class"] == "FEMALE_BREAST_EXPOSED"
                    or prediction["class"] == "ANUS_EXPOSED"
                    or prediction["class"] == "FEMALE_GENITALIA_EXPOSED"
                    or prediction["class"] == "MALE_GENITALIA_EXPOSED"
                    or prediction["class"] == "BUTTOCKS_EXPOSED"
                ):

                    await ctx.error(
                        "This website contains explicit content. I cannot send the screenshot."
                    )
                    return
            # Send the screenshot back to Discord
            with open(screenshot_file, "rb") as file:
                screenshot = discord.File(file)
                await ctx.reply(file=screenshot)

            # Close Playwright browser
            await browser.close()

            # Remove the screenshot file
            os.remove(screenshot_file)

    @commands.command(aliases=["es"])
    async def editsnipe(self, ctx: AkariContext, index: int = 1):
        """
        Get the most recent edited message in the channel
        """

        if not self.bot.cache.get("edit_snipe"):
            return await ctx.warning("No edit snipes found in this channel")

        snipes = [
            s
            for s in self.bot.cache.get("edit_snipe")
            if s["channel"] == ctx.channel.id
        ]

        if len(snipes) == 0:
            return await ctx.warning("No edit snipes found in this channel")

        if index > len(snipes):
            return await ctx.warning(
                f"There are only **{len(snipes)}** edit snipes in this channel"
            )

        result = snipes[::-1][index - 1]
        embed = (
            discord.Embed(color=self.bot.color)
            .set_author(name=result["name"], icon_url=result["avatar"])
            .set_footer(text=f"{index}/{len(snipes)}")
        )

        for m in ["before", "after"]:
            embed.add_field(name=m, value=result[m])

        return await ctx.reply(embed=embed)

    @commands.command(aliases=["s"])
    async def snipe(self, ctx: AkariContext, index: int = 1):
        """
        Get the most recent deleted message in the channel
        """
        try:
            if not self.bot.cache.get("snipe"):
                return await ctx.warning("No snipes found in this channel")
            snipes = [
                s for s in self.bot.cache.get("snipe") if s["channel"] == ctx.channel.id
            ]
            if len(snipes) == 0:
                return await ctx.warning("No snipes found in this channel")
            if index > len(snipes):
                return await ctx.warning(
                    f"There are only **{len(snipes)}** snipes in this channel"
                )
            result = snipes[::-1][index - 1]
            embed = (
                discord.Embed(
                    color=self.bot.color,
                    description=result["message"],
                    timestamp=datetime.datetime.fromtimestamp(
                        result["created_at"]
                    ).replace(tzinfo=None),
                )
                .set_author(name=result["name"], icon_url=result["avatar"])
                .set_footer(text=f"{index}/{len(snipes)}")
            )

            if len(result["stickers"]) > 0:
                sticker: discord.StickerItem = result["stickers"][0]
                embed.set_image(url=sticker.url)
            else:
                if len(result["attachments"]) > 0:
                    attachment: discord.Attachment = result["attachments"][0]
                    if ".mp4" in attachment.filename or ".mov" in attachment.filename:
                        file = discord.File(
                            BytesIO(await attachment.read()),
                            filename=attachment.filename,
                        )
                        return await ctx.reply(embed=embed, file=file)
                    else:
                        embed.set_image(url=attachment.url)

            return await ctx.reply(embed=embed)
        except Exception as e:
            return await ctx.warning("There was an error getting snipes.")

    @commands.hybrid_command(aliases=["mc"])
    async def membercount(self, ctx: AkariContext, invite: discord.Invite = None):
        """
        Returns the number of members in your server or the server given
        """

        if invite:
            embed = discord.Embed(
                color=self.bot.color,
                description=f"> **members:** {invite.approximate_member_count:,}",
            ).set_author(
                name=f"{invite.guild.name}'s statistics", icon_url=invite.guild.icon
            )
        else:
            embed = discord.Embed(
                color=self.bot.color,
                description=f">>> **humans** - {len(set(m for m in ctx.guild.members if not m.bot)):,}\n**bots** - {len(set(m for m in ctx.guild.members if m.bot)):,}\n**total** - {ctx.guild.member_count:,}",
            ).set_author(
                icon_url=ctx.guild.icon,
                name=f"{ctx.guild.name}'s statistics (+{len([m for m in ctx.guild.members if (datetime.datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 3600*24])})",
            )

        return await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["si", "ii", "inviteinfo"])
    async def serverinfo(self, ctx: AkariContext, invite: discord.Invite = None):
        """
        Get the information about a server
        """

        if invite:
            embed = discord.Embed(
                color=self.bot.color, title=f"Invite code: {invite.code}"
            ).add_field(
                name="Invite",
                value=f"**channel:** {invite.channel.name} ({invite.channel.type})\n**id:** `{invite.channel.id}`\n**expires:** {f'yes ({self.bot.humanize_date(invite.expires_at.replace(tzinfo=None))})' if invite.expires_at else 'no'}\n**uses:** {invite.uses or 'unknown'}",
            )

            if invite.guild:
                embed.description = invite.guild.description or ""
                embed.set_thumbnail(url=invite.guild.icon).add_field(
                    name="Server",
                    value=f"**name:** {invite.guild.name}\n**id:** `{invite.guild.id}`\n**members:** {invite.approximate_member_count:,}\n**created**: {discord.utils.format_dt(invite.created_at, style='R') if invite.created_at else 'N/A'}",
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

        await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["user", "ui", "whois"])
    async def userinfo(
        self,
        ctx: AkariContext,
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
                    "<:deafened:1188943549870387332>"
                    if mem.voice.self_deaf or mem.voice.deaf
                    else "<:undeafened:1188943560897200199>"
                )
                mute = (
                    "<:muted:1188945885510500442>"
                    if mem.voice.self_mute or mem.voice.mute
                    else "<:unmuted:1188943586868346960>"
                )
                stream = (
                    "<:stream:1188943574264447037>" if mem.voice.self_stream else ""
                )
                video = "<:video:1188945875716812840>" if mem.voice.self_video else ""
                channelmembers = (
                    f"with {len(mem.voice.channel.members)-1} other member{'s' if len(mem.voice.channel.members) > 2 else ''}"
                    if len(mem.voice.channel.members) > 1
                    else ""
                )
                return f" {deaf} {mute} {stream} {video} **in voice channel** {channelname} {channelmembers}\n"
            return ""

        embed = (
            discord.Embed(
                color=await self.bot.dominant_color(member.display_avatar),
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

        await ctx.reply(embed=embed)

    @commands.hybrid_command()
    async def weather(self, ctx: AkariContext, *, location: WeatherLocation):
        """
        Returns the weather of a location
        """

        embed = (
            discord.Embed(
                color=self.bot.color,
                title=f"{location.condition} in {location.place}, {location.country}",
                timestamp=location.time,
            )
            .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            .set_thumbnail(url=location.condition_image)
            .add_field(
                name="Temperature",
                value=f"{location.temp_c} °C / {location.temp_f} °F",
                inline=False,
            )
            .add_field(name="Humidity", value=f"{location.humidity}%", inline=False)
            .add_field(
                name="Wind",
                value=f"{location.wind_mph} mph / {location.wind_kph} kph",
                inline=False,
            )
        )

        return await ctx.reply(embed=embed)

    @commands.hybrid_command()
    async def roblox(self, ctx: AkariContext, user: RobloxUser):
        """
        Get someone's roblox profile
        """

        embed = (
            discord.Embed(
                color=self.bot.color,
                title=f"{user.display_name} @{user.username}",
                url=user.url,
                description=user.bio,
            )
            .set_thumbnail(url=user.avatar_url)
            .add_field(name="Friends", value=user.friends)
            .add_field(name="Followers", value=user.followers)
            .add_field(name="Following", value=user.followings)
            .set_footer(text=self.get_joined_date(user.created_at), icon_url=user.icon)
        )

        if user.banned:
            embed.set_author(name="This user is banned")

        await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["snap"])
    async def snapchat(self, ctx: AkariContext, user: SnapUser):
        """
        Get someone's snapchat profile
        """

        embed = (
            discord.Embed(
                color=self.bot.color,
                title=user.display_name,
                url=user.url,
                description=user.bio,
            )
            .set_author(name=user.username)
            .set_thumbnail(url=user.avatar)
        )

        button = discord.ui.Button(
            label="snapcode", emoji="<:snap:1142555339133300917>"
        )

        async def button_callback(interaction: discord.Interaction):
            e = discord.Embed(color=0xFFFF00)
            e.set_image(url=user.snapcode)
            await interaction.response.send_message(embed=e, ephemeral=True)

        button.callback = button_callback
        view = discord.ui.View()
        view.add_item(button)

        await ctx.reply(embed=embed, view=view)

    @commands.hybrid_command(aliases=["ig"])
    async def instagram(self, ctx: AkariContext, *, user: InstagramUser):
        """
        Get someone's instagram profile
        """

        embed = (
            discord.Embed(
                color=self.bot.color,
                title=f"@{user.username}",
                description=user.bio,
                url=user.url,
            )
            .set_thumbnail(url=user.profile_pic)
            .add_field(name="Following", value=f"{user.following:,}")
            .add_field(name="Followers", value=f"{user.followers:,}")
            .add_field(name="Posts", value=f"{user.posts:,}")
        )

        if user.pronouns:
            embed.set_author(name=", ".join(user.pronouns))

        return await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["tt"])
    async def tiktok(self, ctx: AkariContext, *, user: TikTokUser):
        """
        Get someone's tiktok profile
        """

        embed = (
            discord.Embed(
                color=self.bot.color,
                url=user.url,
                title=(
                    f"{f'{user.nickname} ({user.username})' if user.nickname else f'{user.username}'} {''.join(user.badges)}"
                    if user.nickname != "⠀⠀"
                    else f"{user.username} {''.join(user.badges)}"
                ),
                description=user.bio,
            )
            .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            .set_thumbnail(url=user.avatar)
            .add_field(name="Following", value=f"{user.following:,}")
            .add_field(name="Followers", value=f"{user.followers:,}")
            .add_field(name="Hearts", value=f"{user.hearts:,}")
        )
        await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["git"])
    async def github(self, ctx: AkariContext, *, user: GithubUser):
        """
        Get someone's github profile
        """

        embed = (
            discord.Embed(
                color=self.bot.color,
                title=f"{user.username} {f'aka {user.display}' if user.display else ''}",
                description=user.bio,
                url=user.url,
                timestamp=user.created_at,
            )
            .set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            .set_thumbnail(url=user.avatar_url)
            .add_field(name="Followers", value=user.followers)
            .add_field(name="Following", value=user.following)
            .add_field(name="Repos", value=user.repos)
        )

        await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["fnshop"])
    async def fortniteshop(self, ctx: AkariContext):
        """
        Get the fortnite item shop for today
        """

        now = datetime.datetime.now()
        file = discord.File(
            await self.bot.getbyte(
                f"https://bot.fnbr.co/shop-image/fnbr-shop-{now.day}-{now.month}-{now.year}.png"
            ),
            filename="fortnite.png",
        )

        await ctx.reply(file=file)

    @commands.command(aliases=["splash"])
    async def serversplash(
        self, ctx: AkariContext, *, invite: Optional[discord.Invite] = None
    ):
        """
        Get a server's splash
        """

        if invite:
            guild = invite.guild
        else:
            guild = ctx.guild

        if not guild.splash:
            return await ctx.warning("This server has no splash image")

        embed = discord.Embed(
            color=await self.bot.dominant_color(guild.splash.url),
            title=f"{guild.name}'s splash",
            url=guild.splash.url,
        ).set_image(url=guild.splash.url)

        await ctx.reply(embed=embed)

    @commands.command(aliases=["sbanner"])
    async def serverbanner(
        self, ctx: AkariContext, *, invite: Optional[discord.Invite] = None
    ):
        """
        Get a server's banner
        """

        if invite:
            guild = invite.guild
        else:
            guild = ctx.guild

        if not guild.banner:
            return await ctx.warning("This server has no banner")

        embed = discord.Embed(
            color=await self.bot.dominant_color(guild.banner.url),
            title=f"{guild.name}'s banner",
            url=guild.banner.url,
        ).set_image(url=guild.banner.url)

        await ctx.reply(embed=embed)

    @commands.command(aliases=["sicon"])
    async def servericon(
        self, ctx: AkariContext, *, invite: Optional[discord.Invite] = None
    ):
        """
        Get a server's icon
        """

        if invite:
            guild = invite.guild
        else:
            guild = ctx.guild

        if not guild.icon:
            return await ctx.warning("This server has no icon")

        embed = discord.Embed(
            color=await self.bot.dominant_color(guild.icon.url),
            title=f"{guild.name}'s icon",
            url=guild.icon.url,
        ).set_image(url=guild.icon.url)

        await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["define"])
    async def urban(self, ctx: AkariContext, *, word: str):
        """
        find a definition of a word
        """

        embeds = []

        data = await self.bot.session.get_json(
            "http://api.urbandictionary.com/v0/define", params={"term": word}
        )

        defs = data["list"]
        if len(defs) == 0:
            return await ctx.error(f"No definition found for **{word}**")

        for defi in defs:
            e = (
                discord.Embed(
                    color=self.bot.color,
                    title=word,
                    description=defi["definition"],
                    url=defi["permalink"],
                    timestamp=dateutil.parser.parse(defi["written_on"]),
                )
                .set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                .add_field(name="example", value=defi["example"], inline=False)
                .set_footer(text=f"{defs.index(defi)+1}/{len(defs)}")
            )
            embeds.append(e)

        return await ctx.paginator(embeds)

    @commands.command(aliases=["tr"])
    async def translate(self, ctx: AkariContext, language: str, *, message: str):
        """
        Translate a message to a specific language
        """

        try:
            translator = GoogleTranslator(source="auto", target=language)
            translated = await self.bot.loop.run_in_executor(
                self.bot.executor, translator.translate, message
            )
            embed = discord.Embed(
                color=self.bot.color,
                title=f"translated to {language}",
                description=f"```{translated}```",
            )

            await ctx.reply(embed=embed)
        except LanguageNotSupportedException:
            return await ctx.error("This language is **not** supported")

    @commands.hybrid_command()
    async def seen(
        self, ctx: AkariContext, *, member: discord.Member = commands.Author
    ):
        """
        Check when a member was last seen
        """

        time = await self.bot.db.fetchval(
            """
      SELECT time FROM seen
      WHERE user_id = $1
      AND guild_id = $2
      """,
            member.id,
            ctx.guild.id,
        )

        if not time:
            return await ctx.error("This member doesn't have any last seen record")

        await ctx.akari_send(
            f"**{member}** was last seen **{self.bot.humanize_date(datetime.datetime.fromtimestamp(time.timestamp()))}**"
        )

    @commands.hybrid_command()
    @is_afk()
    async def afk(self, ctx: AkariContext, *, reason: str = "AFK"):
        """
        let the members know that you're away
        """

        await self.bot.db.execute(
            """
      INSERT INTO afk
      VALUES ($1,$2,$3,$4)
      """,
            ctx.guild.id,
            ctx.author.id,
            reason,
            datetime.datetime.now(),
        )

        embed = discord.Embed(
            color=self.bot.color,
            description=f"😴 {ctx.author.mention}: You are now AFK with the reason: **{reason}**",
        )
        await ctx.reply(embed=embed)

    @commands.command(aliases=["hex"])
    async def dominant(self, ctx: AkariContext):
        """
        Get the color of an image
        """

        attachment = await ctx.get_attachment()

        if not attachment:
            return await ctx.send_help("dominant")

        color = hex(await self.bot.dominant_color(attachment.url))[2:]
        hex_info = await self.bot.session.get_json(
            "https://www.thecolorapi.com/id", params={"hex": color}
        )
        hex_image = f"https://singlecolorimage.com/get/{color}/200x200"
        embed = (
            discord.Embed(color=int(color, 16))
            .set_author(icon_url=hex_image, name=hex_info["name"]["value"])
            .set_thumbnail(url=hex_image)
            .add_field(name="RGB", value=hex_info["rgb"]["value"])
            .add_field(name="HEX", value=hex_info["hex"]["value"])
        )

        await ctx.reply(embed=embed)

    @commands.command()
    async def youngest(self, ctx: AkariContext):
        """
        Get the youngest account in the server
        """

        member = (
            sorted(
                [m for m in ctx.guild.members if not m.bot],
                key=lambda m: m.created_at,
                reverse=True,
            )
        )[0]

        embed = (
            discord.Embed(
                color=self.bot.color,
                title=f"Youngest account in {ctx.guild.name}",
                url=f"https://discord.com/users/{member.id}",
            )
            .add_field(name="user", value=member.mention)
            .add_field(
                name="created",
                value=self.bot.humanize_date(member.created_at.replace(tzinfo=None)),
            )
        )
        await ctx.reply(embed=embed)

    @commands.command()
    async def oldest(self, ctx: AkariContext):
        """
        Get the oldest account in the server
        """

        member = (
            sorted(
                [m for m in ctx.guild.members if not m.bot], key=lambda m: m.created_at
            )
        )[0]
        embed = (
            discord.Embed(
                color=self.bot.color,
                title=f"Oldest account in {ctx.guild.name}",
                url=f"https://discord.com/users/{member.id}",
            )
            .add_field(name="user", value=member.mention)
            .add_field(
                name="created",
                value=self.bot.humanize_date(member.created_at.replace(tzinfo=None)),
            )
        )

        await ctx.reply(embed=embed)

    @commands.hybrid_command(brief="manage messages", aliases=["pic"])
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_guild_permissions(manage_channels=True)
    async def picperms(
        self,
        ctx: AkariContext,
        member: discord.Member,
        *,
        channel: discord.TextChannel = commands.CurrentChannel,
    ):
        """
        Give a member permissions to post attachments in a channel
        """

        overwrite = channel.overwrites_for(member)

        if (
            channel.permissions_for(member).attach_files
            and channel.permissions_for(member).embed_links
        ):
            overwrite.attach_files = False
            overwrite.embed_links = False
            await channel.set_permissions(
                member,
                overwrite=overwrite,
                reason=f"Picture permissions removed by {ctx.author}",
            )
            return await ctx.success(
                f"Removed pic perms from {member.mention} in {channel.mention}"
            )
        else:
            overwrite.attach_files = True
            overwrite.embed_links = True
            await channel.set_permissions(
                member,
                overwrite=overwrite,
                reason=f"Picture permissions granted by {ctx.author}",
            )
            return await ctx.success(
                f"Added pic perms to {member.mention} in {channel.mention}"
            )

    @commands.command()
    async def roles(self, ctx: AkariContext):
        """
        Returns a list of server's roles
        """

        role_list = [
            f"{role.mention} - {len(role.members)} member{'s' if len(role.members) != 1 else ''}"
            for role in ctx.guild.roles[1:][::-1]
        ]
        return await ctx.paginate(
            role_list,
            f"Roles in {ctx.guild.name} ({len(ctx.guild.roles[1:])})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.command()
    async def muted(self, ctx: AkariContext):
        """
        Returns a list of muted members
        """

        members = [
            f"{member.mention} - {discord.utils.format_dt(member.timed_out_until, style='R')}"
            for member in ctx.guild.members
            if member.timed_out_until
        ]

        return await ctx.paginate(
            members,
            f"Muted in {ctx.guild.name} ({len(members)})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.command()
    async def joins(self, ctx: AkariContext):
        """
        Returns a list of members that joined in the last 24 hours
        """

        members = sorted(
            [
                m
                for m in ctx.guild.members
                if (
                    datetime.datetime.now() - m.joined_at.replace(tzinfo=None)
                ).total_seconds()
                < 3600 * 24
            ],
            key=lambda m: m.joined_at,
            reverse=True,
        )

        return await ctx.paginate(
            [
                f"{m} - {discord.utils.format_dt(m.joined_at, style='R')}"
                for m in members
            ],
            f"Joined today ({len(members)})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.command()
    @commands.has_guild_permissions(ban_members=True)
    @commands.bot_has_guild_permissions(ban_members=True)
    async def bans(self, ctx: AkariContext):
        """
        Returns a list of banned users
        """

        banned = [ban async for ban in ctx.guild.bans(limit=100)]
        return await ctx.paginate(
            [f"{m.user} - {m.reason or 'no reason'}" for m in banned],
            f"Bans ({len(banned)})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.command()
    async def bots(self, ctx: AkariContext):
        """
        Returns a list of all bots in this server
        """

        return await ctx.paginate(
            [f"{m.mention} `{m.id}`" for m in ctx.guild.members if m.bot],
            f"Bots ({len([m for m in ctx.guild.members if m.bot])})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.command()
    async def boosters(self, ctx: AkariContext):
        """
        Returns a list of members that boosted the server
        """

        members = sorted(
            ctx.guild.premium_subscribers, key=lambda m: m.premium_since, reverse=True
        )

        if members is None:
            return await ctx.warning("This server has **no** boosters.")

        return await ctx.paginate(
            [
                f"{m} - {discord.utils.format_dt(m.premium_since, style='R')}"
                for m in members
            ],
            f"Boosters ({len(ctx.guild.premium_subscribers)})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.command()
    async def inrole(self, ctx: AkariContext, *, role: Union[discord.Role, str]):
        """
        Get the list of members that have a specific
        """

        if isinstance(role, str):
            role = ctx.find_role(role)
            if not role:
                return await ctx.error("Role not found")

        if len(role.members) > 200:
            return await ctx.warning("Cannot view roles with more than **200** members")

        return await ctx.paginate(
            [f"{m} (`{m.id}`)" for m in role.members],
            f"Members with {role.name} ({len(role.members)})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.command()
    async def shazam(self, ctx: AkariContext):
        """
        Get the name of a music in a file using shazam
        """

        attachment = await ctx.get_attachment()

        if not attachment:
            await ctx.send_help(ctx.command)

        embed = discord.Embed(
            color=0x09A1ED,
            description=f"<:shazam:1106874229451931689> {ctx.author.mention}: Searching for track...",
        )

        mes = await ctx.reply(embed=embed)
        try:
            out = await Shazam().recognize_song(await attachment.read())
            track = out["track"]["share"]["text"]
            link = out["track"]["share"]["href"]

            embed = discord.Embed(
                color=0x09A1ED,
                description=f"<:shazam:1106874229451931689> {ctx.author.mention}: Found [**{track}**]({link})",
            )

            await mes.edit(embed=embed)
        except:
            embed = discord.Embed(
                color=self.bot.no_color,
                description=f"{self.bot.no} {ctx.author.mention}: Unable to find this attachment's track name",
            )

            await mes.edit(embed=embed)

    @commands.command(aliases=["ca"])
    async def cashapp(self, ctx: AkariContext, user: CashappUser):
        """
        get someone's cashapp url and qr
        """

        await ctx.reply(user.url, file=discord.File(user.qr, filename="cashapp_qr.png"))

    @commands.group(aliases=["tz"], invoke_without_command=True)
    async def timezone(self, ctx: AkariContext, *, member: TimezoneMember = None):
        """
        Get the member's current date
        """

        if member is None:
            member = await TimezoneMember().convert(ctx, str(ctx.author))

        embed = discord.Embed(
            color=self.bot.color,
            description=f"🕑 {ctx.author.mention}: **{member[0].name}'s** current date is **{member[1]}**",
        )
        await ctx.reply(embed=embed)

    @timezone.command(name="set")
    async def timezone_set(self, ctx: AkariContext, *, timezone: TimezoneLocation):
        """
        Set your timezone
        """

        embed = discord.Embed(
            color=self.bot.color,
            description=f"Saved your timezone as **{timezone.timezone}**\n🕑 Current date: **{timezone.date}**",
        )
        await ctx.reply(embed=embed)

    @timezone.command(name="unset")
    async def timezone_unset(self, ctx: AkariContext):
        """
        Unset your timezone
        """

        await self.bot.db.execute(
            """
      DELETE FROM timezone
      WHERE user_id = $1
      """,
            ctx.author.id,
        )

        return await ctx.success(f"You succesfully deleted your timezone")

    @timezone.command(name="list")
    async def timezone_list(self, ctx: AkariContext):
        """
        Get the timezones of everyone in this server
        """

        ids = list(map(lambda m: str(m.id), ctx.guild.members))
        results = await self.bot.db.fetch(
            f"SELECT zone FROM timezone WHERE user_id IN ({', '.join(ids)})"
        )
        await ctx.paginate(
            [
                f"<@{result['user_id']}> - **{self.tz.get_timezone(ctx.guild.get_member(result['user_id']))}"
                for result in results
            ],
            f"Timezones ({len(results)})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.group(aliases=["bday"], invoke_without_command=True)
    async def birthday(self, ctx: AkariContext, *, member: Optional[BdayMember] = None):
        """
        Get the birthday of an user
        """

        if member is None:
            member = await BdayMember().convert(ctx, str(ctx.author))

        embed = discord.Embed(
            color=0xDEA5A4,
            description=f"🎂 {ctx.author.mention}: **{member.name}'s** birthday is **{member.date}**. That's **{member.birthday}**",
        )

        await ctx.reply(embed=embed)

    @birthday.command(name="set")
    async def bday_set(self, ctx: AkariContext, *, date: BdayDate):
        """
        Set your birthday
        """

        embed = discord.Embed(
            color=0xDEA5A4,
            description=f"🎂 Your birthday is **{date[0]}**. That's **{date[1]}**",
        )
        await ctx.reply(embed=embed)

    @birthday.command(name="unset")
    async def bday_unset(self, ctx: AkariContext):
        """
        Unset your birthday
        """

        await self.bot.db.execute(
            """
      DELETE FROM bday
      WHERE user_id = $1
      """,
            ctx.author.id,
        )

        return await ctx.success(f"You succesfully deleted your birthday")

    @birthday.command(name="list")
    async def bday_list(self, ctx: AkariContext):
        """
        Get the birthdays of everyone in this server
        """

        ids = list(map(lambda m: str(m.id), ctx.guild.members))
        results = await self.bot.db.fetch(
            f"SELECT * FROM bday WHERE user_id IN ({', '.join(ids)})"
        )
        await ctx.paginate(
            [
                f"""<@{result['user_id']}> - **{self.tz.months.get(result['month'])} {result['day']}**"""
                for result in results
            ],
            f"Birthdays ({len(results)})",
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon},
        )

    @commands.group(invoke_without_command=True)
    async def reminder(self, ctx):
        return await ctx.create_pages()

    @reminder.command(name="add")
    @reminder_exists()
    async def reminder_add(self, ctx: AkariContext, time: ValidTime, *, task: str):
        """
        Make the bot remind you about a task
        """

        if time < 60:
            return await ctx.warning("Reminder time can't be less than a minute")

        else:
            try:
                await self.bot.db.execute(
                    """
        INSERT INTO reminder
        VALUES ($1,$2,$3,$4,$5)
        """,
                    ctx.author.id,
                    ctx.channel.id,
                    ctx.guild.id,
                    (datetime.datetime.now() + datetime.timedelta(seconds=time)),
                    task,
                )

                await ctx.reply(
                    f"🕰️ {ctx.author.mention}: I'm going to remind you in {humanfriendly.format_timespan(time)} about **{task}**"
                )
            except:
                return await ctx.warning(
                    f"You already have a reminder set in this channel. Use `{ctx.clean_prefix}reminder stop` to cancel the reminder"
                )

    @reminder.command(name="stop", aliases=["cancel"])
    @is_there_a_reminder()
    async def reminder_stop(self, ctx: AkariContext):
        """
        Stop the bot from reminding you
        """

        await self.bot.db.execute(
            """
      DELETE FROM reminder
      WHERE guild_id = $1
      AND user_id = $2
      """,
            ctx.guild.id,
            ctx.author.id,
        )

        return await ctx.success("Deleted a reminder")

    @commands.command(aliases=["remindme"])
    @reminder_exists()
    async def remind(self, ctx: AkariContext, time: ValidTime, *, task: str):
        """
        Make the bot remind you about a task
        """

        if time < 60:
            return await ctx.warning("Reminder time can't be less than a minute")
        else:
            try:
                await self.bot.db.execute(
                    """
        INSERT INTO reminder
        VALUES ($1,$2,$3,$4,$5)
        """,
                    ctx.author.id,
                    ctx.channel.id,
                    ctx.guild.id,
                    (datetime.datetime.now() + datetime.timedelta(seconds=time)),
                    task,
                )
                await ctx.reply(
                    f"🕰️ {ctx.author.mention}: I'm going to remind you in {humanfriendly.format_timespan(time)} about **{task}**"
                )
            except:
                return await ctx.warning(
                    f"You already have a reminder set in this channel. Use `{ctx.clean_prefix}reminder stop` to cancel the reminder"
                )

    @commands.group(name="tag", aliases=["tags", "t"], invoke_without_command=True)
    async def tag(self, ctx: AkariContext, *, tag: str):
        """
        view a tag
        """

        check = await self.bot.db.fetchrow(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      AND name = $2
      """,
            ctx.guild.id,
            tag,
        )

        if not check:
            return await ctx.warning(f"No tag found for **{tag}**")

        x = await self.bot.embed_build.convert(ctx, check["response"])
        await ctx.reply(**x)

    @tag.command(name="create", aliases=["make"], brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    async def tag_create(self, ctx: AkariContext, *, args: str):
        """
        create a tag
        """

        args = args.split(",", maxsplit=1)

        if len(args) == 1:
            return await ctx.warning(
                "No response found. Make sure to use a `,` to split the trigger from the response"
            )

        name = args[0]
        response = args[1].strip()

        if await self.bot.db.fetchrow(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      AND name = $2
      """,
            ctx.guild.id,
            name,
        ):
            return await ctx.warning(f"A tag for **{name}** already exists!")

        await self.bot.db.execute(
            """
      INSERT INTO tags
      VALUES ($1, $2, $3, $4)
      """,
            ctx.guild.id,
            ctx.author.id,
            name,
            response,
        )
        await ctx.success(f"Added tag for **{name}**" + f"\n```{response}```")

    @tag.command(name="remove", aliases=["delete", "del"], brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    async def tag_remove(self, ctx: AkariContext, *, tag: str):
        """
        delete a tag
        """

        if not await self.bot.db.fetchrow(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      AND name = $2
      """,
            ctx.guild.id,
            tag,
        ):
            return await ctx.warning(f"That is **not** an existing tag")

        await self.bot.db.execute(
            """
      DELETE FROM tags
      WHERE guild_id = $1
      AND name = $2
      """,
            ctx.guild.id,
            tag,
        )
        await ctx.success(f"Deleted the tag **{tag}**")

    @tag.command(name="reset", brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    async def tag_reset(self, ctx: AkariContext):
        """
        delete all tags in the guild
        """

        if not await self.bot.db.fetchrow(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      """,
            ctx.guild.id,
        ):
            return await ctx.warning(f"There are **no** tags set")

        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute(
                """
        DELETE FROM tags
        WHERE guild_id = $1
        """,
                interaction.guild.id,
            )
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"{self.bot.yes} {interaction.user.mention}: Removed all **tags**",
                    color=self.bot.yes_color,
                ),
                view=None,
            )

        async def no_func(interaction: discord.Interaction):
            await interaction.response.edit_message(
                embed=discord.Embed(
                    description=f"{interaction.user.mention}: Cancelling action...",
                    color=self.bot.color,
                ),
                view=None,
            )

        await ctx.confirmation_send(
            f"Are you sure you want to **delete** all tags?", yes_func, no_func
        )

    @tag.command(name="list", brief="manage server")
    @commands.has_guild_permissions(manage_guild=True)
    async def tag_list(self, ctx: AkariContext):
        """
        returns a list of all tags
        """

        results = await self.bot.db.fetch(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      """,
            ctx.guild.id,
        )

        if not results:
            return await ctx.warning(f"There are **no** tags set")

        await ctx.paginate(
            [f"{result['name']} - {result['response']}" for result in results],
            title=f"Tags ({len(results)})",
            author={"name": ctx.guild.name, "icon_url": ctx.guild.icon or None},
        )

    @tag.command(name="random")
    async def tag_random(self, ctx: AkariContext):
        """
        returns a random tag from the guild
        """

        result = await self.bot.db.fetchrow(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      ORDER BY RANDOM()
      LIMIT 1
      """,
            ctx.guild.id,
        )

        if not result:
            return await ctx.warning(f"There are **no** tags set")

        x = await self.bot.embed_build.convert(ctx, result["response"])
        x["content"] = f"({result['name']}) {x['content'] or ''}"
        await ctx.reply(**x)

    @tag.command(name="edit", brief="tag owner")
    async def tag_edit(self, ctx: AkariContext, *, args: str):
        """
        edit a tag
        """

        args = args.split(",", maxsplit=1)

        if len(args) == 1:
            return await ctx.warning(
                "No response found. Make sure to use a `,` to split the trigger from the response"
            )

        name = args[0]
        response = args[1].strip()

        check = await self.bot.db.fetchrow(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      AND name = $2
      """,
            ctx.guild.id,
            name,
        )

        if not check:
            return await ctx.warning(f"No tag found for **{name}**")

        if check["author_id"] != ctx.author.id:
            return await ctx.warning(f"You are not the **author** of this tag")

        await self.bot.db.execute(
            """
      UPDATE tags
      SET response = $1
      WHERE guild_id = $2
      AND name = $3
      """,
            response,
            ctx.guild.id,
            name,
        )
        await ctx.success(f"Updated tag for **{name}**" + f"\n```{response}```")

    @tag.command(name="creator", aliases=["author"])
    async def tag_creator(self, ctx: AkariContext, *, tag: str):
        """
        view the creator of a tag
        """

        check = await self.bot.db.fetchrow(
            """
      SELECT * FROM tags
      WHERE guild_id = $1
      AND name = $2
      """,
            ctx.guild.id,
            tag,
        )

        if not check:
            return await ctx.warning(f"No tag found for **{tag}**")

        user = self.bot.get_user(check["author_id"])
        return await ctx.akari_send(f"The author of this tag is **{user}**")

    @tag.command(name="search")
    async def tag_search(self, ctx: AkariContext, *, query: str):
        """
        search for a tag
        """

        results = await self.bot.db.fetch(
            f"""
      SELECT * FROM tags
      WHERE guild_id = $1
      AND name LIKE '%{query}%'
      """,
            ctx.guild.id,
        )

        if not results:
            return await ctx.warning(f"No **tags** found")

        await ctx.paginate(
            [f"**{result['name']}**" for result in results], title=f"Tags like {query}"
        )

    @commands.command(name="color", aliases=["colour"])
    async def color(self, ctx: AkariContext, *, color: Color):
        """
        view info about a color
        """

        embed = discord.Embed(color=color)
        embed.set_author(name=f"Showing hex code: {color}")

        embed.add_field(
            name="RGB Value",
            value=", ".join([str(x) for x in color.to_rgb()]),
            inline=True,
        )
        embed.add_field(name="INT", value=color.value, inline=True)

        embed.set_thumbnail(
            url=(
                "https://place-hold.it/250x219/"
                + str(color).replace("#", "")
                + "?text=%20"
            )
        )

        return await ctx.reply(embed=embed)

    @commands.command(name="transparent", aliases=["tp"])
    @commands.max_concurrency(1, commands.BucketType.channel, wait=True)
    @commands.cooldown(1, 6, commands.BucketType.user)
    async def transparent(self, ctx: AkariContext, url: str = None):
        """
        make an image transparent
        """

        if not url:
            url = await ctx.get_attachment()
            if not url:
                return await ctx.send_help(ctx.command)

            url = url.url

        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.error("The image provided is not an url")

        try:
            async with ctx.channel.typing(), asyncio.timeout(15):
                return await ctx.reply(
                    file=discord.File(
                        BytesIO(
                            await self.bot.loop.run_in_executor(
                                self.bot.executor,
                                rembg.bg.remove,
                                await self.bot.session.get_bytes(url),
                            )
                        ),
                        "transparent.png",
                    )
                )

        except Exception:
            return await ctx.warning(f"Couldn't make the image **transparent**")

    @commands.command(name="image", aliases=["img", "im"])
    @commands.cooldown(1, 1, commands.BucketType.member)
    async def image(self, ctx: AkariContext, *, query: str):
        """
        search for an image
        """

        response = await self.bot.session.post_json(
            f"https://vile.bot/api/browser/images",
            data=query.replace(" ", "%20"),
            params=dict(colors="true"),
        )

        if not response:
            return await ctx.warning(f"No results found for **{query}**")

        entries = [
            discord.Embed(
                title=entry.get("title"),
                url=f"https://{entry.get('domain')}",
                color=entry.get("color"),
            )
            .set_image(url=entry.get("url"))
            .set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar
            )
            .set_footer(
                text="Brave Results",
                icon_url="https://upload.wikimedia.org/wikipedia/commons/5/51/Brave_icon_lionface.png",
            )
            for entry in response
        ]

        await ctx.paginator(entries)


async def setup(bot: Akari) -> None:
    return await bot.add_cog(Utility(bot))
