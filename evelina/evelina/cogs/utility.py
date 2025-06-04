import io
import re
import math
import json
import arrow
import tempfile
import uwuify
import asyncio
import discord
import datetime
import humanize
import tempfile
import humanfriendly
import dateutil.parser
import calendar
import os
import aiohttp
import urllib
import requests
import pytesseract
import lyricsgenius
from bs4 import BeautifulSoup

from discord import TextChannel, Embed, File, Member, Interaction, User, Thread, ForumChannel, Guild, ActivityType
from discord.ui import View, Button
from discord.ext.commands import Cog, has_guild_permissions, bot_has_guild_permissions, command, group, BucketType, CooldownMapping, Converter, Author, CurrentChannel, cooldown, CommandError, BadArgument

from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from aiofiles import open as aio_open
from typing import Union, Optional, Any
from shazamio import Shazam
from timezonefinder import TimezoneFinder
from deep_translator import GoogleTranslator

user_verification_data = {}

from modules import config
from modules.styles import emojis, colors, icons
from modules.evelinabot import Evelina
from modules.validators import ValidTime, ValidLanguage
from modules.handlers.lastfm import Handler
from modules.helpers import EvelinaContext
from modules.predicates import is_afk
from modules.persistent.feedback import FeedbackView
from modules.misc import utils
from modules.misc.utils import Timezone, TimezoneMember, TimezoneLocation, get_color

class Color(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        argument = str(argument)
        if argument.lower() in ("random", "rand", "r"):
            return discord.Color.random()
        elif argument.lower() in ("invisible", "invis"):
            return discord.Color.from_str("#2F3136")
        if color := get_color(argument):
            return color
        else:
            raise CommandError(f"Color **{argument}** not found")

class Utility(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.locks = {}
        self.tz = Timezone(bot)
        self.lastfmhandler = Handler(self.bot, config.API.LASTFM)
        self.week_days = {0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 4: "Friday", 5: "Saturday", 6: "Sunday"}
        self.months = {1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "August", 9: "September", 10: "October", 11: "November", 12: "December"}
    
    def human_format(self, number: int) -> str:
        if number > 999:
            return humanize.naturalsize(number, False, True)
        return number.__str__()
    
    async def cache_profile(self, member: discord.User) -> Any:
        if member.banner:
            banner = member.banner.url
        else:
            banner = None
        return await self.bot.cache.set(f"profile-{member.id}", {"banner": banner}, 3600)

    def get_joined_date(self, date) -> str:
        if date.month < 10:
            month = (self.tz.months.get(date.month))[:3]
        else:
            month = (self.tz.months.get(date.month))[:3]
        return f"Joined {month} {date.day} {str(date.year)}"

    @command(aliases=["uwu"], usage="uwuify Hello, how are you?")
    async def uwuify(self, ctx: EvelinaContext, *, message: str):
        """Convert a message to the uwu format"""
        flags = uwuify.YU | uwuify.STUTTER
        embed = discord.Embed(color=colors.NEUTRAL, description=uwuify.uwu(message, flags=flags))
        return await ctx.send(embed=embed)

    @command(aliases=["foryou", "foryoupage"])
    @cooldown(1,5, BucketType.user)
    async def fyp(self, ctx: EvelinaContext):
        """Repost a TikTok video from the FYP"""
        async with ctx.channel.typing():
            for attempt in range(3):
                x = await self.bot.session.get_json("https://api.evelina.bot/tiktok/fyp", params={"key": config.EVELINA})
                if 'video' in x and 'video' in x['video']:
                    video = x["video"]["video"]
                    file = File(fp=await self.bot.getbyte(video), filename="evelinatiktok.mp4")
                    caption = x["video"].get('caption', '')
                    description = f"[{caption}]({video})" if caption else ""
                    embed = Embed(color=colors.NEUTRAL, description=description).set_author(name=f"{x['author']['username']}", icon_url=f"{x['author']['avatar']}", url=f"https://tiktok.com/@{x['author']['username']}").set_footer(text=f"❤️ {x['video']['likes']:,}  💬 {x['video']['comments']:,}  🔗 {x['video']['shares']:,}  👀 {x['video']['views']:,} | {ctx.author}")
                    return await ctx.send(embed=embed, file=file)
                else:
                    await asyncio.sleep(1)
            await ctx.send_warning("Failed to fetch a TikTok video from the FYP")

    @command(name="safemode", aliases=["safesearch"], usage="safemode on")
    @has_guild_permissions(manage_guild=True)
    async def safemode(self, ctx: EvelinaContext, mode: str):
        """Toggle the safemode on or off"""
        if mode.lower() not in ("on", "off"):
            return await ctx.send_warning(f"Invalid mode, please use either **on** or **off**")
        row = await self.bot.db.fetchrow("SELECT * FROM safemode WHERE guild_id = $1", ctx.guild.id)
        if mode.lower() == "on":
            if row:
                await self.bot.db.execute("UPDATE safemode SET safemode = $1 WHERE guild_id = $2", True, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO safemode (guild_id, safemode) VALUES ($1, $2)", ctx.guild.id, True)
            return await ctx.send_success("Safe mode is now **on**")
        if mode.lower() == "off":
            if row:
                await self.bot.db.execute("UPDATE safemode SET safemode = $1 WHERE guild_id = $2", False, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO safemode (guild_id, safemode) VALUES ($1, $2)", ctx.guild.id, False)
            return await ctx.send_success("Safe mode is now **off**")
        
    @command(name="image", aliases=["img"], usage="image BMW M4")
    async def image(self, ctx: EvelinaContext, *, query: str):
        """Search for an image on Google"""
        safemode = await self.bot.db.fetchval("SELECT safemode FROM safemode WHERE guild_id = $1", ctx.guild.id)
        safemode = "off" if safemode is False else "on"
        async with ctx.channel.typing():
            url = "https://google-api31.p.rapidapi.com/imagesearch"
            payload = {
                "text": query,
                "safesearch": safemode,
                "region": "en-en",
                "color": "",
                "size": "",
                "type_image": "",
                "layout": "",
                "max_results": 100
            }
            headers = {
                "x-rapidapi-key": config.RAPIDAPI,
                "x-rapidapi-host": "google-api31.p.rapidapi.com",
                "Content-Type": "application/json"
            }
            try:
                data = await self.bot.session.post_json(url, headers=headers, params=payload)
                if not data:
                    return await ctx.send_warning(f"An error occurred while searching for **{query}**")
            except aiohttp.ClientError as e:
                return await ctx.send_warning(f"An error occurred: {e}")
            except asyncio.TimeoutError:
                return await ctx.send_warning("The request timed out. Please try again later.")
            results = data.get("result", [])
            embeds = []
            for i, result in enumerate(results):
                embed = Embed(
                    color=colors.NEUTRAL,
                    title=result["title"],
                    url=result["url"]
                )
                embed.set_image(url=result["image"])
                embed.set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                )
                embed.set_footer(
                    text=f"Page: {i + 1}/{len(results)} ({len(results)} entries) - Safe Mode: {safemode.capitalize()}",
                    icon_url=icons.GOOGLE
                )
                embeds.append(embed)
            if not embeds:
                return await ctx.send_warning(f"No results found for **{query}**")
            await ctx.paginator(embeds)

    @command(name="google", aliases=["search"], usage="google Evelina Bot")
    async def google(self, ctx: EvelinaContext, *, query: str):
        """Search Google for a query"""
        safemode = await self.bot.db.fetchval("SELECT safemode FROM safemode WHERE guild_id = $1", ctx.guild.id)
        safemode = "off" if safemode is False else "on"
        async with ctx.channel.typing():
            url = "https://google-api31.p.rapidapi.com/websearch"
            payload = {
                "text": query,
                "safesearch": safemode,
                "timelimit": "",
                "region": "en-en",
                "max_results": 20
            }
            headers = {
                "x-rapidapi-key": config.RAPIDAPI,
                "x-rapidapi-host": "google-api31.p.rapidapi.com",
                "Content-Type": "application/json"
            }
            try:
                data = await self.bot.session.post_json(url, headers=headers, params=payload)
                if not data:
                    return await ctx.send_warning(f"An error occurred while searching for **{query}**")
            except aiohttp.ClientError as e:
                return await ctx.send_warning(f"An error occurred: {e}")
            except asyncio.TimeoutError:
                return await ctx.send_warning("The request timed out. Please try again later.")
            results = data.get("result", [])
            embeds = []
            for i in range(0, len(results), 3):
                embed = Embed(color=colors.NEUTRAL, title=f"Search Results - `{query}`")
                embed.description = "\n".join(
                    f"**[{result['title']}]({result['href']})**\n{result['body']}\n"
                    for j, result in enumerate(results[i:i+3])
                )
                embed.set_author(
                    name=ctx.author.name,
                    icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url
                )
                embed.set_footer(
                    text=f"Page: {i // 3 + 1}/{len(results) // 3 + 1} ({len(results)} entries) - Safe Mode: {safemode.capitalize()}",
                    icon_url=icons.GOOGLE
                )
                embeds.append(embed)
            if not embeds:
                return await ctx.send_warning(f"No results found for **{query}**")
            await ctx.paginator(embeds)

    @group(name="avatarhistory", aliases=["avh"], invoke_without_command=True, case_insensitive=True)
    async def avatarhistory(self, ctx: EvelinaContext, *, user: User = Author):
        if user:
            await self.avatarhistory_view(ctx, user=user)
        else:
            return await ctx.create_pages()

    @avatarhistory.command(name="view", usage="avatarhistory view comminate")
    async def avatarhistory_view(self, ctx: EvelinaContext, *, user: User = Author):
        """Check a member's avatar history"""
        results = await self.bot.db.fetch("SELECT avatar FROM avatar_history WHERE user_id = $1", int(user.id))
        if not results:
            does = "don't" if user == ctx.author else "doesn't"
            return await ctx.send_warning(f"{'You' if user == ctx.author else user.mention} {does} have an **avatar history**")
        base_url = "https://cdn.evelina.bot/avatars/"
        avatar_urls = [f"{base_url}{record['avatar']}" for record in results]
        max_avatars = 20
        avatar_urls = avatar_urls[:max_avatars]
        image_bytes_list = []
        tasks = [self.bot.session.get_bytes(url) for url in avatar_urls]
        responses = await asyncio.gather(*tasks)
        for response in responses:
            if response:
                image_bytes_list.append(response)
        collage_image_bytes = await self.bot.misc.create_collage(image_bytes_list)
        file = discord.File(fp=collage_image_bytes, filename="avatar_collage.png")
        embed = discord.Embed(
            color=colors.NEUTRAL, 
            title=f"{user.name}'s Avatar History",
            description=f"Showing **{len(image_bytes_list)}** from **{len(results)}** pictures\n> Click [**here**](https://evelina.bot/avatars/{user.id}) to get the **full** list"
        )
        embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_image(url="attachment://avatar_collage.png")
        await ctx.reply(embed=embed, file=file)
    
    @avatarhistory.command(name="clear")
    async def avatarhistory_clear(self, ctx: EvelinaContext):
        """Clear your avatar history"""
        records = await self.bot.db.fetch("SELECT avatar FROM avatar_history WHERE user_id = $1", ctx.author.id)
        if not records:
            await ctx.send_warning(f"You have no avatar history to clear")
            return
        async def yes_callback(interaction: Interaction):
            successfully_deleted_files = []
            for record in records:
                file_name = record['avatar']
                delete_res = await self.bot.r2.delete_file("evelina", file_name, "avatars")
                if delete_res:
                    successfully_deleted_files.append(file_name)
            for avatar in successfully_deleted_files:
                await self.bot.db.execute("DELETE FROM avatar_history WHERE user_id = $1 AND avatar = $2", ctx.author.id, avatar)
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {ctx.author.mention}: Successfully deleted **{len(successfully_deleted_files)}** avatar history entries", color=colors.SUCCESS), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Avatar history clear got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to clear your avatar history?", yes_callback, no_callback)
    
    @avatarhistory.command(name="global")
    async def avatarhistory_global(self, ctx: EvelinaContext):
        """Returns a list of all avatar histories"""
        results = await self.bot.db.fetch("SELECT user_id, COUNT(*) as avatar_count FROM avatar_history GROUP BY user_id")
        res = sorted(results, key=lambda m: m["avatar_count"], reverse=True)
        total_avatars = sum(int(result['avatar_count']) for result in results)
        pages = [res[i:i + 10] for i in range(0, len(res), 10)]
        embeds = []
        for index, page in enumerate(pages):
            description = "\n".join([
                f"`{i + 1 + index * 10}.` **{self.bot.get_user(result['user_id'])}** - "
                f"[{int(result['avatar_count'])} Avatars](https://evelina.bot/avatars/{result['user_id']})"
                for i, result in enumerate(page)
            ])
            embed = discord.Embed(title="Global Avatar History", color=0x729BB0, description=description)
            embed.set_footer(text=f"Page: {index + 1}/{len(pages)} | Total Avatars: {total_avatars}")
            embeds.append(embed)
        if not embeds:
            return await ctx.send_warning("Error fetching information from the avatar history.")
        return await ctx.paginator(embeds=embeds)
    
    @avatarhistory.command(name="enable")
    async def avatarhistory_enable(self, ctx: EvelinaContext):
        """Enable avatar history tracking"""
        check = await self.bot.db.fetchval("SELECT status FROM avatar_privacy WHERE user_id = $1", ctx.author.id)
        if check is not None and check is True:
            return await ctx.send_warning("Avatar history tracking is already **enabled**")
        if check is None:
            await self.bot.db.execute("INSERT INTO avatar_privacy (user_id, status) VALUES ($1, $2)", ctx.author.id, True)
            return await ctx.send_success("Avatar history tracking has been **enabled**")
        else:
            await self.bot.db.execute("UPDATE avatar_privacy SET status = $1 WHERE user_id = $2", True, ctx.author.id)
            return await ctx.send_success("Avatar history tracking has been **enabled**")

    @avatarhistory.command(name="disable")
    async def avatarhistory_disable(self, ctx: EvelinaContext):
        """Disable avatar history tracking"""
        current_status = await self.bot.db.fetchval("SELECT status FROM avatar_privacy WHERE user_id = $1", ctx.author.id)
        if current_status is not None and current_status is False:
            return await ctx.send_warning("Avatar history tracking is already **disabled**")
        if current_status is None:
            await self.bot.db.execute("INSERT INTO avatar_privacy (user_id, status) VALUES ($1, $2)", ctx.author.id, False)
            return await ctx.send_success("Avatar history tracking has been **disabled**")
        else:
            await self.bot.db.execute("UPDATE avatar_privacy SET status = $1 WHERE user_id = $2", False, ctx.author.id)
            return await ctx.send_success("Avatar history tracking has been **disabled**")

    @command(aliases=["firstmsg"], usage="firstmessage #general comminate")
    async def firstmessage(self, ctx: EvelinaContext, channel: discord.TextChannel = CurrentChannel, user: discord.Member = None):
        """Get a link for the first message in a channel or by a user in a channel"""
        messages = [mes async for mes in channel.history(limit=1, oldest_first=True)]
        if messages:
            message = messages[0]
            await ctx.evelina_send(f"The first message sent in {channel.mention} - [**jump**]({message.jump_url})")
        else:
            await ctx.send_warning(f"No messages found in {channel.mention}")

    @command(aliases=["av"], usage="avatar comminate")
    async def avatar(self, ctx: EvelinaContext, *, member: Union[discord.Member, discord.User] = None,):
        """Get avatar of a member or yourself"""
        if member is None:
            member = ctx.author
        embed = discord.Embed(color=await self.bot.misc.dominant_color(member.avatar.url if member.avatar else member.default_avatar.url), title=f"{member.name}'s avatar", url=member.avatar.url if member.avatar else member.default_avatar.url)
        embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)

    @command(aliases=["sav", "savatar"], usage="serveravatar comminate")
    async def serveravatar(self, ctx: EvelinaContext, *, member: discord.Member = None):
        """Get the server avatar of a member or yourself"""
        if member is None:
            member = ctx.author
        if member.guild_avatar:
            embed = discord.Embed(color=await self.bot.misc.dominant_color(member.guild_avatar.url), title=f"{member.name}'s server avatar", url=member.guild_avatar.url)
            embed.set_image(url=member.guild_avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send_warning(f"{'You don' if member.id == ctx.author.id else f'{member.mention} doesn'}'t have a server avatar")

    @command(usage="banner comminate")
    async def banner(self, ctx: EvelinaContext, *, member: discord.User = None):
        """Get the banner of a member or yourself"""
        if member is None:
            member = ctx.author
        cache = await self.bot.cache.get(f"profile-{member.id}")
        if cache:
            banner = cache["banner"]
            if banner is None:
                return await ctx.send_warning(f"{'You don' if member.id == ctx.author.id else f'{member.mention} doesn'}'t have a banner")
        else:
            user = await self.bot.fetch_user(member.id)
            if not user.banner:
                await self.cache_profile(user)
                return await ctx.send_warning(f"{'You don' if member.id == ctx.author.id else f'{member.mention} doesn'}'t have a banner")
            banner = user.banner.url
        embed = discord.Embed(color=await self.bot.misc.dominant_color(banner), title=f"{member.name}'s banner", url=banner)
        embed.set_image(url=banner)
        return await ctx.send(embed=embed)
    
    @command(aliases=["sbanner"], usage="serverbanner comminate")
    async def serverbanner(self, ctx: EvelinaContext, *, member: discord.Member = None):
        if member is None:
            member = ctx.author
        if member.guild_banner:
            embed = discord.Embed(color=await self.bot.misc.dominant_color(member.guild_banner.url), title=f"{member.name}'s server banner", url=member.guild_banner.url)
            embed.set_image(url=member.guild_banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send_warning(f"{'You don' if member.id == ctx.author.id else f'{member.mention} doesn'}'t have a server banner")

    @group(name="stickymessage", aliases=["stickymsg", "sticky"], description="Set up a sticky message in one or multiple channels", invoke_without_command=True, case_insensitive=True)
    async def stickymessage(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @stickymessage.command(name="add", brief="manage guild", usage="stickymessage add #images No NSFW images", description="Add a sticky message to a channel")
    @has_guild_permissions(manage_guild=True)
    async def stickymessage_add(self, ctx: EvelinaContext, channel: TextChannel, *, code: str):
        not_delete = False
        if " --not_delete" in code:
            not_delete = True
            code = code.replace(" --not_delete", "")
        check = await self.bot.db.fetchrow("SELECT * FROM stickymessage WHERE channel_id = $1", channel.id)
        if check:
            args = ["UPDATE stickymessage SET message = $1, not_delete = $3 WHERE channel_id = $2", code, channel.id, not_delete]
        else:
            args = ["INSERT INTO stickymessage VALUES ($1,$2,$3,$4,$5)", ctx.guild.id, channel.id, code, None, not_delete]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Added sticky message to {channel.mention}\n```{code}```")

    @stickymessage.command(name="remove", brief="manage guild", usage="stickymessage remove #images", description="Remove a sticky message from a channel")
    @has_guild_permissions(manage_guild=True)
    async def stickymessage_remove(self, ctx: EvelinaContext, *, channel: TextChannel):
        check = await self.bot.db.fetchrow("SELECT * FROM stickymessage WHERE channel_id = $1", channel.id)
        if not check:
            return await ctx.send_warning("There is no sticky message configured in this channel")
        await self.bot.db.execute("DELETE FROM stickymessage WHERE channel_id = $1", channel.id)
        return await ctx.send_success(f"Deleted the sticky message from {channel.mention}")
    
    @stickymessage.command(name="list", brief="manage guild", usage="stickymessage list", description="List all channels with a sticky message")
    @has_guild_permissions(manage_guild=True)
    async def stickymessage_list(self, ctx: EvelinaContext):
        results = await self.bot.db.fetch("SELECT * FROM stickymessage WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are no sticky messages configured in this server")
        embeds = [
            discord.Embed(color=colors.NEUTRAL, title="Sticky Message Configuration")
            .set_footer(text=f"Page: {results.index(result) + 1}/{len(results)}")
            .add_field(name="Channel", value=f"{ctx.guild.get_channel(result['channel_id']).mention if ctx.guild.get_channel(result['channel_id']) else 'None'}", inline=True)
            .add_field(name="Message", value=f"```{result['message'][:1021] + '...' if len(result['message']) > 1024 else result['message']}```" if result['message'] else "No message set", inline=False)
            for result in results]
        await ctx.paginator(embeds)

    @command(name="names", aliases=["pastusernames", "usernames", "oldnames", "pastnames"], usage="names comminate")
    async def names(self, ctx: EvelinaContext, *, user: discord.User = Author):
        """View username and nickname history of a member or yourself"""
        username_results = await self.bot.db.fetch("SELECT * FROM usernames WHERE user_id = $1", user.id)
        nickname_results = await self.bot.db.fetch("SELECT * FROM nicknames WHERE user_id = $1", user.id)
        if len(username_results) == 0 and len(nickname_results) == 0:
            message = " You don't" if user == ctx.author else user.mention + " doesn't"
            return await ctx.send_warning(f"{message} have **past usernames or nicknames**")
        combined_results = [
            {"type": "U", "name": result['user_name'], "time": result['time']} for result in username_results
        ] + [
            {"type": "N", "name": result['nick_name'], "time": result['time']} for result in nickname_results
        ]
        combined_results = sorted(combined_results, key=lambda m: m["time"], reverse=True)
        formatted_results = [
            f"`{index + 1}{entry['type']}` **{entry['name']}** - {discord.utils.format_dt(datetime.datetime.fromtimestamp(entry['time']), style='R')}"
            for index, entry in enumerate(combined_results)
        ]
        return await ctx.namespaginate(formatted_results, f"Name changes", {"name": user.name, "icon_url": user.avatar.url if user.avatar else user.default_avatar.url})

    @command(name="clearnames", aliases=["cnames"])
    async def clearnames(self, ctx: EvelinaContext):
        """Reset your name history"""
        username_check = await self.bot.db.fetchrow("SELECT * FROM usernames WHERE user_id = $1", ctx.author.id)
        nickname_check = await self.bot.db.fetchrow("SELECT * FROM nicknames WHERE user_id = $1", ctx.author.id)
        if not username_check and not nickname_check:
            return await ctx.send_warning("There are no usernames or nicknames saved for you")
        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute("DELETE FROM usernames WHERE user_id = $1", interaction.user.id)
            await self.bot.db.execute("DELETE FROM nicknames WHERE user_id = $1", interaction.user.id)
            return await interaction.response.edit_message(embed=discord.Embed(
                color=colors.SUCCESS, 
                description=f"{emojis.APPROVE} {interaction.user.mention}: Cleared your username and nickname history"
            ), view=None)
        async def no_func(interaction: discord.Interaction):
            return await interaction.response.edit_message(embed=discord.Embed(
                color=colors.ERROR, 
                description=f"{emojis.DENY} {interaction.user.mention}: Username and nickname history deletion got canceled"
            ), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **clear** your username and nickname history?", yes_func, no_func)

    @command(name="guildnames", aliases=["gnames"], usage="guildnames 1228371886690537624")
    async def guildnames(self, ctx: EvelinaContext, *, guild: int = None):
        """View guildname history"""
        if not guild:
            guild = ctx.guild.id
        results = await self.bot.db.fetch("SELECT * FROM guildnames WHERE guild_id = $1 ORDER BY time DESC", guild)
        if not results:
            return await ctx.send_warning(f"There are no guildnames saved for {'this server' if ctx.guild.id == guild else guild}")
        formatted_results = [
            f"**{result['guild_name']}** - {discord.utils.format_dt(datetime.datetime.fromtimestamp(result['time']), style='R')}"
            for index, result in enumerate(results)
        ]
        return await ctx.paginate(formatted_results, f"Guild name changes", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @command(name="clearguildnames", aliases=["cleargnames"])
    async def clearguildnames(self, ctx: EvelinaContext):
        """Reset guild name history"""
        check = await self.bot.db.fetchrow("SELECT * FROM guildnames WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There are no guildnames saved for this server")
        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute("DELETE FROM guildnames WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=discord.Embed(
                color=colors.SUCCESS, 
                description=f"{emojis.APPROVE} {interaction.guild.name}: Cleared the guildname history"
            ), view=None)
        async def no_func(interaction: discord.Interaction):
            return await interaction.response.edit_message(embed=discord.Embed(
                color=colors.ERROR, 
                description=f"{emojis.DENY} {interaction.guild.name}: Guildname history deletion got canceled"
            ), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.guild.name}: Are you sure you want to **clear** the guildname history?", yes_func, no_func)

    @command(name="ownerhistory", aliases=["oh"])
    async def ownerhistory(self, ctx: EvelinaContext):
        """View the owner history of a guild"""
        results = await self.bot.db.fetch("SELECT * FROM owner_history WHERE guild_id = $1 ORDER BY timestamp DESC", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There is no owner history saved for this server")
        formatted_results = [f"<@{result['old_owner']}> > <@{result['new_owner']}> - <t:{result['timestamp']}:R>" for result in results]
        return await ctx.paginate(formatted_results, f"Owner history", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @command(name="clearownerhistory", aliases=["clearowner"])
    async def clearownerhistory(self, ctx: EvelinaContext):
        """Reset the owner history of a guild"""
        check = await self.bot.db.fetchrow("SELECT * FROM owner_history WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is no owner history saved for this server")
        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute("DELETE FROM owner_history WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=discord.Embed(
                color=colors.SUCCESS, 
                description=f"{emojis.APPROVE} {interaction.guild.name}: Cleared the owner history"
            ), view=None)
        async def no_func(interaction: discord.Interaction):
            return await interaction.response.edit_message(embed=discord.Embed(
                color=colors.ERROR, 
                description=f"{emojis.DENY} {interaction.guild.name}: Owner history deletion got canceled"
            ), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.guild.name}: Are you sure you want to **clear** the owner history?", yes_func, no_func)

    @command(aliases=["ri"], usage="roleinfo admin")
    async def roleinfo(self, ctx: EvelinaContext, *, role: Optional[discord.Role] = None):
        """View information about a role"""
        if role is None:
            role = ctx.author.top_role
        dangerous_permissions = {
            "Administrator": role.permissions.administrator,
            "Ban Members": role.permissions.ban_members,
            "Kick Members": role.permissions.kick_members,
            "Mention Everyone": role.permissions.mention_everyone,
            "Manage Channels": role.permissions.manage_channels,
            "Manage Events": role.permissions.manage_events,
            "Manage Expressions": role.permissions.manage_expressions,
            "Manage Guild": role.permissions.manage_guild,
            "Manage Roles": role.permissions.manage_roles,
            "Manage Messages": role.permissions.manage_messages,
            "Manage Webhooks": role.permissions.manage_webhooks,
            "Manage Permissions": role.permissions.manage_permissions,
            "Manage Threads": role.permissions.manage_threads,
            "Moderate Members": role.permissions.moderate_members,
            "Mute Members": role.permissions.mute_members,
            "Deafen Members": role.permissions.deafen_members,
            "Move Members": role.permissions.move_members
        }
        dangerous_perms_list = [name for name, has_perm in dangerous_permissions.items() if has_perm]
        dangerous_perms_str = ", ".join(dangerous_perms_list) if dangerous_perms_list else "None"
        embed = (
            discord.Embed(color=role.color if role.color.value != 0 else colors.NEUTRAL, title=role.name)
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
            .set_thumbnail(url=(role.display_icon if isinstance(role.display_icon, discord.Asset) else None))
            .add_field(name="Role ID", value=f"`{role.id}`")
            .add_field(name="Role color", value=(f"`#{hex(role.color.value)[2:]}`" if role.color.value != 0 else "No color"))
            .add_field(name="Created", value=f"{discord.utils.format_dt(role.created_at, style='f')} **{self.bot.misc.humanize_date(role.created_at.replace(tzinfo=None))}**", inline=False)
            .add_field(name=f"{len(role.members)} Member{'s' if len(role.members) != 1 else ''}", value=(", ".join([str(m) for m in role.members]) if len(role.members) < 7 else f"{', '.join([str(m) for m in role.members][:7])} + {len(role.members)-7} others"), inline=False)
        )
        if dangerous_perms_str != "None":
            embed.add_field(name=f"{emojis.WARNING} Dangerous Permissions", value=dangerous_perms_str, inline=False)
        await ctx.send(embed=embed)

    @command(name="permissions", aliases=["perms"], usage="permissions comminate")
    async def permissions(self, ctx: EvelinaContext, *, target: Union[Member, discord.Role] = Author):
        """View permissions of a member or role"""
        if isinstance(target, Member):
            permissions = target.guild_permissions
            title = f"{target.name}'s Permissions"
        elif isinstance(target, discord.Role):
            permissions = target.permissions
            title = f"{target.name} Role Permissions"
        permission_names = [
            'add_reactions', 'administrator', 'attach_files', 'ban_members', 'change_nickname', 'connect', 
            'create_instant_invite', 'create_private_threads', 'create_public_threads', 'deafen_members', 
            'embed_links', 'kick_members', 'manage_channels', 'manage_emojis_and_stickers', 'manage_events', 
            'manage_guild', 'manage_messages', 'manage_nicknames', 'manage_permissions', 'manage_roles', 
            'manage_threads', 'manage_webhooks', 'mention_everyone', 'moderate_members', 'move_members', 
            'mute_members', 'priority_speaker', 'read_message_history', 'request_to_speak', 'send_messages', 
            'send_messages_in_threads', 'send_tts_messages', 'speak', 'stream', 'use_application_commands', 
            'use_embedded_activities', 'use_external_emojis', 'use_external_stickers', 'use_voice_activation', 
            'view_audit_log', 'view_channel', 'view_guild_insights'
        ]
        dangerous_permissions = {
            "administrator", "ban_members", "kick_members", "mention_everyone", "manage_channels", 
            "manage_events", "manage_emojis_and_stickers", "manage_guild", "manage_roles", "manage_messages", 
            "manage_webhooks", "manage_permissions", "manage_threads", "moderate_members", "mute_members", 
            "deafen_members", "move_members"
        }
        perms = [
            (name, f"{emojis.WARNING if name in dangerous_permissions and getattr(permissions, name) else emojis.APPROVE if getattr(permissions, name) else emojis.DENY} {name.replace('_', ' ').title()}")
            for name in permission_names
        ]
        perms.sort(key=lambda x: x[0] in dangerous_permissions, reverse=True)
        perms_list = [perm[1] for perm in perms]
        await ctx.paginate(perms_list, title, {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(name="channelinfo", aliases=["ci"], usage="channelinfo #general")
    async def channelinfo(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread, ForumChannel] = None):
        """View information about a channel"""
        if channel is None:
            channel = ctx.channel
        else:
            if isinstance(channel, str):
                if channel.isdigit():
                    channel_id = int(channel)
                    for guild in self.bot.guilds:
                        channel = guild.get_channel(channel_id)
                        if channel:
                            break
                else:
                    for guild in self.bot.guilds:
                        channel = discord.utils.get(guild.channels, name=channel)
                        if channel:
                            break
        if not channel:
            await ctx.send_warning("An error occurred while fetching the channel")
            return
        embed = (
            discord.Embed(color=colors.NEUTRAL, title=channel.name)
            .set_author(name=ctx.author.name, icon_url=ctx.author.avatar)
            .add_field(name="Channel ID", value=f"`{channel.id}`", inline=True)
            .add_field(name="Type", value=str(channel.type).replace("_", " "), inline=True)
            .add_field(name="Guild", value=f"{channel.guild.name} (`{channel.guild.id}`)", inline=True)
        )
        if isinstance(channel, TextChannel):
            if channel.category:
                embed.add_field(name="Category", value=f"{channel.category.name} (`{channel.category.id}`)", inline=True)
            else:
                embed.add_field(name="Category", value="None", inline=True)
            embed.add_field(name="Topic", value=f"{channel.topic}" or "No topic", inline=False)
        elif isinstance(channel, Thread):
            if channel.category:
                embed.add_field(name="Category", value=f"{channel.category.name} (`{channel.category.id}`)", inline=True)
            else:
                embed.add_field(name="Category", value="None", inline=True)
            embed.add_field(name="Parent Channel", value=f"{channel.parent.name} (`{channel.parent.id}`)", inline=True)
        elif isinstance(channel, ForumChannel):
            if channel.category:
                embed.add_field(name="Category", value=f"{channel.category.name} (`{channel.category.id}`)", inline=True)
            else:
                embed.add_field(name="Category", value="None", inline=True)
            embed.add_field(name="Available Tags", value=", ".join(f"`{tag.name}`" for tag in channel.available_tags) or "None", inline=True)
            if channel.topic:
                embed.add_field(name="Post Guidelines", value=f"```{channel.topic}```", inline=False)
            else:
                embed.add_field(name="Post Guidelines", value="No guidelines", inline=False)
        embed.add_field(name="Created At", value=f"{discord.utils.format_dt(channel.created_at, style='F')} ({discord.utils.format_dt(channel.created_at, style='R')})", inline=False)
        await ctx.send(embed=embed)

    @command()
    async def donators(self, ctx: EvelinaContext):
        """Returns a list of all donators"""
        results = await self.bot.db.fetch("SELECT * FROM donor")
        res = sorted(results, key=lambda m: m["since"], reverse=True)
        return await ctx.paginate([f"<@!{result['user_id']}> - <t:{int(result['since'])}:R> {emojis.BOOSTER if result['status'] == 'boosted' else emojis.DONATOR}" for result in res], f"Evelina donators")

    #@command(aliases=["ss", "screenie"], usage="screenshot evelina.bot")
    #async def screenshot(self, ctx: EvelinaContext, url: str, delay: int = 1):
    #    """Get an image of a website"""
    #    if not url.startswith(("https://", "http://")):
    #        url = f"https://{url}"
    #    if not validators.url(url):
    #        return await ctx.send_warning("That is not a valid **URL**")
    #    api_url = f"https://api.apiflash.com/v1/urltoimage?access_key=745aca6c05664b488115b01c9c21d0c1&url={url}&width=1920&height=1080&fresh=true&delay={delay}&response_type=json&no_cookie_banners=true&no_ads=true&no_tracking=true&wait_until=page_loaded"
    #    data, status = await self.bot.session.get_json(api_url, return_status=True)
    #    if status == 200:
    #        image_url = data.get("url")
    #        if image_url:
    #            img_response, status = await self.bot.session.get_bytes(image_url, return_status=True)
    #            if status == 200:
    #                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
    #                    temp_file.write(img_response)
    #                    temp_file_path = temp_file.name
    #                with open(temp_file_path, 'rb') as f:
    #                    await ctx.send(file=discord.File(f, 'screenshot.png'))
    #                os.remove(temp_file_path)
    #            else:
    #                await ctx.send_warning("Failed to download the image")
    #        else:
    #            await ctx.send_warning("Failed to retrieve Image URL")
    #    else:
    #        await ctx.send_warning("Failed to fetch the screenshot from API")

    @command(aliases=["s"])
    async def snipe(self, ctx: EvelinaContext):
        """Snipe the latest message that was deleted"""
        try:
            snipes = await self.bot.db.fetch("""
                SELECT author_id, message_content, attachments, stickers, created_at, deleted_by
                FROM snipes 
                WHERE channel_id = $1 
                ORDER BY created_at DESC 
            """, ctx.channel.id)
            if not snipes:
                return await ctx.send_warning("No snipes found in this channel")
            embeds = []
            for i, result in enumerate(snipes, start=1):
                author = ctx.guild.get_member(result["author_id"])
                author_name = author.name if author else "Unknown User"
                author_avatar = author.avatar.url if author and author.avatar else None
                description = result["message_content"] if len(result["message_content"]) <= 4003 else result["message_content"][:4000] + '...'
                if result["deleted_by"]:
                    description += f"\n > **Deleted by:** <@{result['deleted_by']}>"
                embed = (
                    discord.Embed(color=colors.NEUTRAL, description=description, timestamp=datetime.datetime.fromtimestamp(result["created_at"]))
                    .set_author(name=author_name, icon_url=author_avatar)
                    .set_footer(text=f"Page: {i}/{len(snipes)} ({len(snipes)} entries)")
                )
                if result["stickers"]:
                    sticker_url = result["stickers"][0]
                    embed.set_image(url=sticker_url)
                if result["attachments"]:
                    attachment_fields = []
                    for index, url in enumerate(result["attachments"], start=1):
                        attachment_fields.append(f"[File #{index}]({url})")
                    if attachment_fields:
                        embed.add_field(name="Attachments", value=", ".join(attachment_fields), inline=False)
                    if result["attachments"] and not result["stickers"]:
                        embed.set_image(url=result["attachments"][0])
                embeds.append(embed)
            await ctx.paginator(embeds)
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while trying to snipe this message\n```{e}```")
        
    @command(aliases=["es"])
    async def editsnipe(self, ctx: EvelinaContext):
        """Snipe the latest message that was edited"""
        snipes = await self.bot.db.fetch("SELECT author_id, before_content, after_content, created_at FROM snipes_edit WHERE channel_id = $1 ORDER BY created_at DESC", ctx.channel.id)
        if not snipes:
            return await ctx.send_warning("No edit snipes found in this channel")
        embeds = []
        for i, result in enumerate(snipes, start=1):
            author = ctx.guild.get_member(result["author_id"])
            author_name = author.name if author else "Unknown User"
            author_avatar = author.avatar.url if author and author.avatar else None
            embed = (
                discord.Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.fromtimestamp(result["created_at"]))
                .set_author(name=author_name, icon_url=author_avatar)
            )
            before_value = result["before_content"] if len(result["before_content"]) <= 1024 else result["before_content"][:1021] + '...'
            after_value = result["after_content"] if len(result["after_content"]) <= 1024 else result["after_content"][:1021] + '...'
            embed.add_field(name="Before", value=before_value)
            embed.add_field(name="After", value=after_value)
            embed.set_footer(text=f"Page: {i}/{len(snipes)} ({len(snipes)} entries)")
            embeds.append(embed)
        await ctx.paginator(embeds)
    
    @command(aliases=["rs"])
    async def reactionsnipe(self, ctx: EvelinaContext):
        """Snipe the latest reaction that was removed"""
        snipes = await self.bot.db.fetch("SELECT * FROM snipes_reaction WHERE channel_id = $1 ORDER BY created_at DESC", ctx.channel.id)
        if not snipes:
            return await ctx.send_warning("No reaction snipes found in this channel")
        embeds = []
        for i, result in enumerate(snipes, start=1):
            embed = discord.Embed(color=colors.NEUTRAL, timestamp=datetime.datetime.fromtimestamp(result["created_at"]).replace(tzinfo=None))
            user = ctx.guild.get_member(result["user_id"])
            embed.description = (f"{user.mention if user else result['user_id']} reacted with {result['reaction']} <t:{int(result['created_at'])}:R> [**here**](https://discord.com/channels/{ctx.guild.id}/{ctx.channel.id}/{result['message_id']})")
            embed.set_footer(text=f"Page: {i}/{len(snipes)} ({len(snipes)} entries)")
            embeds.append(embed)
        await ctx.paginator(embeds)
            
    @command(aliases=["cs"], brief="Manage messages")
    @has_guild_permissions(manage_messages=True)
    async def clearsnipes(self, ctx: EvelinaContext):
        """Clear the snipes from the channel."""
        for table in ["snipes", "snipes_edit", "snipes_reaction"]:
            await self.bot.db.execute(f"DELETE FROM {table} WHERE channel_id = $1", ctx.channel.id)
        await ctx.send_success("Cleared all snipes from this channel")

    @command(aliases=["mc"], usage="membercount /evelina")
    async def membercount(self, ctx: EvelinaContext, invite: discord.Invite = None):
        """View server member count"""
        if invite:
            embed = discord.Embed(color=colors.NEUTRAL, description=f"> **members:** {invite.approximate_member_count:,}")
            embed.set_author(name=f"{invite.guild.name}'s statistics", icon_url=invite.guild.icon)
        else:
            
            embed = discord.Embed(color=colors.NEUTRAL, description=f">>> **humans** - {len(set(m for m in ctx.guild.members if not m.bot)):,}\n**bots** - {len(set(m for m in ctx.guild.members if m.bot)):,}\n**total** - {ctx.guild.member_count:,}")
            embed.set_author(icon_url=ctx.guild.icon, name=f"{ctx.guild.name}'s statistics (+{len([m for m in ctx.guild.members if (datetime.datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 3600*24])})")
        return await ctx.send(embed=embed)

    @command(aliases=["si"], usage="serverinfo /evelina")
    async def serverinfo(self, ctx: EvelinaContext, *, server: str = None):
        """View information about a server"""
        guild = None
        embed = None
        invite = None
        if server:
            try:
                if not re.match(r'^[a-zA-Z0-9-_]+$', server):
                    return await ctx.send_warning("The invite code contains invalid characters.")
                invite = await self.bot.fetch_invite(server)
                if invite:
                    guild = invite.guild
                    embed = discord.Embed(color=colors.NEUTRAL, title=f"Invite code: {invite.code}")
                    embed.add_field(name="Invite", value=f">>> **Channel:** {invite.channel.name} ({invite.channel.type})\n**ID:** `{invite.channel.id}`\n**Expires:** {f'yes ({self.bot.misc.humanize_date(invite.expires_at.replace(tzinfo=None))})' if invite.expires_at else 'no'}\n**Uses:** {invite.uses or 'unknown'}")
                    if invite.guild:
                        embed.description = invite.guild.description or ""
                        embed.set_thumbnail(url=invite.guild.icon.url if invite.guild.icon else None)
                        embed.add_field(name="Server", value=f">>> **Name:** {invite.guild.name}\n**ID:** `{invite.guild.id}`\n**Members:** {invite.approximate_member_count:,}\n**Created**: {discord.utils.format_dt(invite.created_at, style='R') if invite.created_at else 'N/A'}")
            except discord.NotFound:
                pass
            if not guild:
                try:
                    guild_id = int(server)
                    guild = self.bot.get_guild(guild_id)
                except ValueError:
                    pass
                if not guild:
                    return await ctx.send_warning("Bot is not in this **server** or the **invite** is invalid")
        if not guild:
            guild = ctx.guild
        if guild and not embed:
            servers = sorted(self.bot.guilds, key=lambda g: g.member_count or 0, reverse=True)
            owner = guild.owner
            owner_avatar_url = None
            if owner:
                owner_avatar_url = owner.avatar.url if owner.avatar else owner.default_avatar.url
            embed = (
                discord.Embed(
                    color=colors.NEUTRAL,
                    title=guild.name,
                    description=f"{guild.description or ''}\n\nCreated on {discord.utils.format_dt(guild.created_at, style='D')} {discord.utils.format_dt(guild.created_at, style='R')}\nJoined on {discord.utils.format_dt(guild.me.joined_at, style='D')} {discord.utils.format_dt(guild.me.joined_at, style='R')}"
                )
                .set_author(name=f"{owner} ({owner.id})" if owner else "Unknown Owner", icon_url=owner_avatar_url if owner_avatar_url else None)
                .set_thumbnail(url=guild.icon.url if guild.icon else None)
                .add_field(name="Counts", value=f">>> **Roles:** {len(guild.roles):,}\n**Emojis:** {len(guild.emojis):,}\n**Stickers:** {len(guild.stickers):,}")
                .add_field(name="Members", value=f">>> **Users:** {len(set(i for i in guild.members if not i.bot)):,}\n**Bots:** {len(set(i for i in guild.members if i.bot)):,}\n**Total:** {guild.member_count:,}")
                .add_field(name="Channels", value=f">>> **Text:** {len(guild.text_channels):,}\n**Voice:** {len(guild.voice_channels):,}\n**Categories:** {len(guild.categories):,}")
                .add_field(name="Info", value=f">>> **Vanity:** {guild.vanity_url_code or 'N/A'}\n**Popularity:** {servers.index(guild)+1}/{len(self.bot.guilds)}\n**Owner:** {owner.mention if owner else 'Unknown Owner'}")
                .add_field(name="Boost", value=f">>> **Boosts:** {guild.premium_subscription_count:,}\n**Level:** {guild.premium_tier}\n**Boosters:** {len(guild.premium_subscribers)}")
                .set_footer(text=f"Guild ID: {guild.id} • Shard: {guild.shard_id}/{len(self.bot.shards)}")
            )
        view = View()
        if guild.icon:
            view.add_item(Button(label="Icon", url=guild.icon.url))
        if guild.banner:
            view.add_item(Button(label="Banner", url=guild.banner.url))
        if guild.splash:
            view.add_item(Button(label="Splash", url=guild.splash.url))
        if guild.vanity_url_code:
            view.add_item(Button(label="Invite", url=f"https://discord.gg/{guild.vanity_url_code}"))
        elif invite:
            view.add_item(Button(label="Invite", url=invite.url))
        await ctx.send(embed=embed, view=view)

    @command(aliases=["user", "ui", "whois"], usage="userinfo comminate")
    async def userinfo(self, ctx: EvelinaContext, *, member: Union[discord.Member, discord.User] = Author):
        """View information about a member or yourself"""
        # async def lastfm(mem: discord.Member):
        #     lastfm = await self.bot.db.fetchval("SELECT username FROM lastfm WHERE user_id = $1", mem.id)
        #     if lastfm:
        #         a = await asyncio.wait_for(self.lastfmhandler.get_tracks_recent(lastfm, 1), timeout=15)
        #         if not a["recenttracks"]["track"]:
        #             return ""
        #         first_track = a["recenttracks"]["track"][0]
        #         track_name = first_track.get("name", "Unknown track")
        #         artist_name = first_track.get("artist", {}).get("#text", "Unknown artist")
        #         return f"{emojis.LASTFM} Listening to [**{track_name}**](https://last.fm/music/{track_name.replace(' ', '+')}) by **{artist_name}**\n"
        #     return ""
        badges = await self.bot.misc.get_badges(member)
        description = ""
        if badges:
            description += f"### {badges}\n"
        if isinstance(member, discord.Member):
            # lastfm_info = await lastfm(member)
            # description += lastfm_info if lastfm_info else ""
            activity_info = f"{member.activity.name} (`{getattr(member.activity, 'state', 'N/A')}`)" if member.activity else ""
            if activity_info:
                description += f"{emojis.INFO} {activity_info}\n"
        embed = (
            discord.Embed(color=await self.bot.misc.dominant_color(member.avatar.url if member.avatar else member.default_avatar.url), description=description)
            .set_author(name=f"{member.name} ({member.id})", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
            .set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
            .add_field(name="Created", value=f"{discord.utils.format_dt(member.created_at, style='D')}\n{discord.utils.format_dt(member.created_at, style='R')}")
        )
        if not isinstance(member, discord.ClientUser):
            embed.set_footer(text=f"{len(member.mutual_guilds):,} server(s)")
        if isinstance(member, discord.Member):
            members = sorted(ctx.guild.members, key=lambda m: m.joined_at)
            if not isinstance(member, discord.ClientUser):
                embed.set_footer(text=f"Join position: {members.index(member)+1:,} • {len(member.mutual_guilds):,} server(s)")
            embed.add_field(name="Joined", value=f"{discord.utils.format_dt(member.joined_at, style='D')}\n{discord.utils.format_dt(member.joined_at, style='R')}")
            if member.premium_since:
                embed.add_field(name="Boosted", value=f"{discord.utils.format_dt(member.premium_since, style='D')}\n{discord.utils.format_dt(member.premium_since, style='R')}")
            roles = member.roles[1:][::-1]
            if len(roles) > 0:
                embed.add_field(name=f"Roles [{len(roles)}]", value=(" ".join([r.mention for r in roles]) if len(roles) < 5 else " ".join([r.mention for r in roles[:4]]) + f" ... and {len(roles)-4} more"), inline=False)
        await ctx.send(embed=embed)

    @command(name="info", usage="info comminate")
    async def info(self, ctx: EvelinaContext, *, member: Member = Author):
        """View information about a user"""
        timezone = await self.bot.db.fetchval("SELECT zone FROM timezone WHERE user_id = $1", member.id)
        birthdayData = await self.bot.db.fetchrow("SELECT * FROM birthday WHERE user_id = $1", member.id)
        if birthdayData:
            birthday = f"{Timezone(ctx.bot).months.get(birthdayData['month'])} {ctx.bot.ordinal(birthdayData['day'])}"
        else:
            birthday = None
        languageData = await self.bot.db.fetchval("SELECT languages FROM language WHERE user_id = $1", member.id)
        language = json.loads(languageData) if languageData else []
        languages = ', '.join(language) if language else emojis.DENY
        d = str(member.desktop_status)
        m = str(member.mobile_status)
        w = str(member.web_status)
        if any([isinstance(a, discord.Streaming) for a in member.activities]):
            d = d if d == 'offline' else 'streaming'
            m = m if m == 'offline' else 'streaming'
            w = w if w == 'offline' else 'streaming'
        status = {
			'online': f'{emojis.DEVICE_ONLINE}',
			'idle': f'{emojis.DEVICE_IDLE}',
			'dnd': f'{emojis.DEVICE_DND}',
			'offline': f'{emojis.DEVICE_OFFLINE}',
			'streaming': f'{emojis.DEVICE_STREAMING}'
		}
        devices = f"{status[d]} Desktop {status[m]} Mobile {status[w]} Web"
        embed = (
            discord.Embed(color=colors.NEUTRAL)
            .add_field(name="Timezone", value=timezone if timezone else emojis.DENY, inline=True)
            .add_field(name="Birthday", value=birthday if birthdayData else emojis.DENY, inline=True)
            .add_field(name="Languages", value=languages, inline=True)
            .add_field(name="Devices", value=devices, inline=False)
            .set_author(name=f"{member.name} ({member.id})", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        )
        await ctx.send(embed=embed)

    @command(name="devices", usage="devices comminate")
    async def devices(self, ctx: EvelinaContext, *, member: Member = Author):
        """Send what device you or another person is using"""
        d = str(member.desktop_status)
        m = str(member.mobile_status)
        w = str(member.web_status)
        if any([isinstance(a, discord.Streaming) for a in member.activities]):
            d = d if d == 'offline' else 'streaming'
            m = m if m == 'offline' else 'streaming'
            w = w if w == 'offline' else 'streaming'
        status = {
			'online': f'{emojis.DEVICE_ONLINE}',
			'idle': f'{emojis.DEVICE_IDLE}',
			'dnd': f'{emojis.DEVICE_DND}',
			'offline': f'{emojis.DEVICE_OFFLINE}',
			'streaming': f'{emojis.DEVICE_STREAMING}'
		}
        embed = Embed(color=colors.NEUTRAL,
			description=(
				f'{status[d]} Desktop\n'
				f'{status[m]} Mobile\n'
				f'{status[w]} Web'),)
        embed.set_author(name=f"{member.name}'s devices", icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
        await ctx.send(embed=embed)

    @command(usage="weather vienna")
    async def weather(self, ctx: EvelinaContext, *, city: str):
        """Gets simple weather from OpenWeatherMap"""
        try:
            data = await self.bot.session.get_json(f"https://api.evelina.bot/weather?city={city}&key=X3pZmLq82VnHYTd6Cr9eAw")
            if 'message' in data:
                await ctx.send_warning(f"Couldn't get information about **{city}**")
                return
            embed = (
                discord.Embed(color=0x349BDB, title=f"{data['condition']} in {data['city']}, {data['country']}")
                .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                .set_thumbnail(url=f"https:{data['condition_image']}")
                .add_field(name="Temperature", value=f"{data['temp_c']} °C / {data['temp_f']} °F")
                .add_field(name="Wind", value=f"{data['wind_mph']} mph / {data['wind_kph']} kph")
                .add_field(name="Humidity", value=f"{data['humidity']}%")
            )
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send_warning(f"Couldn't get information about **{city}**")

    @group(name="guild", aliases=["server"], invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def guild(self, ctx: EvelinaContext):
        """View assets from your a given guild"""
        return await ctx.create_pages()

    @guild.command(name="splash", usage="guild splash /evelina")
    async def guild_splash(self, ctx: EvelinaContext, *, invite: Optional[discord.Invite] = None):
        """Returns server splash background"""
        if invite:
            guild = invite.guild
        else:
            guild = ctx.guild
        if not guild.splash:
            return await ctx.send_warning("This server has no splash background")
        embed = discord.Embed(color=await self.bot.misc.dominant_color(guild.splash.url), title=f"{guild.name}'s splash", url=guild.splash.url
        ).set_image(url=guild.splash.url)
        await ctx.send(embed=embed)

    @guild.command(name="banner", usage="guild banner /evelina")
    async def guild_banner(self, ctx: EvelinaContext, *, invite: Optional[discord.Invite] = None):
        """Returns server banner"""
        if invite:
            guild = invite.guild
        else:
            guild = ctx.guild
        if not guild.banner:
            return await ctx.send_warning("This server has no banner")
        embed = discord.Embed(color=await self.bot.misc.dominant_color(guild.banner.url), title=f"{guild.name}'s banner", url=guild.banner.url,
        ).set_image(url=guild.banner.url)
        await ctx.send(embed=embed)

    @guild.command(name="icon", usage="guild icon /evelina")
    async def guild_icon(self, ctx: EvelinaContext, *, invite: Optional[discord.Invite] = None):
        """Returns server icon"""
        if invite:
            guild = invite.guild
        else:
            guild = ctx.guild
        if not guild.icon:
            return await ctx.send_warning("This server has no icon")
        embed = discord.Embed(color=await self.bot.misc.dominant_color(guild.icon.url), title=f"{guild.name}'s icon", url=guild.icon.url,
        ).set_image(url=guild.icon.url)
        await ctx.send(embed=embed)

    @command(aliases=["define"], usage="urban cooking")
    async def urban(self, ctx: EvelinaContext, *, word: str):
        """Gets the definition of a word/slang from Urban Dictionary"""
        embeds = []
        data = await self.bot.session.get_json("http://api.urbandictionary.com/v0/define", params={"term": word})
        defs = data["list"]
        if len(defs) == 0:
            return await ctx.send_warning(f"No definition found for **{word}**")
        for defi in defs:
            def replace_with_url(match):
                word = match.group(1)
                url = f"https://www.urbandictionary.com/define.php?term={urllib.parse.quote_plus(word)}"
                return f"[{word}]({url})"
            definition = re.sub(r'\[(.*?)\]', replace_with_url, defi["definition"])
            example = re.sub(r'\[(.*?)\]', replace_with_url, defi["example"]) if "[" in defi["example"] and "]" in defi["example"] else defi["example"]
            e = (
                discord.Embed(color=colors.NEUTRAL, title=word, description=definition, url=defi["permalink"], timestamp=dateutil.parser.parse(defi["written_on"]))
                .set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
                .add_field(name="Example", value=example if example else "No example provided.", inline=False)
                .set_footer(text=f"{defi['thumbs_up']} 👍 | {defi['thumbs_down']} 👎", icon_url='https://www.urbandictionary.com/favicon.ico')
            )
            embeds.append(e)
        return await ctx.paginator(embeds)

    @command(aliases=["tr"], usage="translate de How are you?")
    async def translate(self, ctx: EvelinaContext, language: str, *, message: str = None):
        """Translate a message to a specific language"""
        if message is None:
            if ctx.message.reference is not None:
                try:
                    replied_message = await ctx.fetch_message(ctx.message.reference.message_id)
                    message = replied_message.content
                except discord.NotFound:
                    return await ctx.send_warning("The referenced message could not be found.")
                except discord.Forbidden:
                    return await ctx.send_warning("I do not have permission to access the referenced message.")
                except discord.HTTPException:
                    return await ctx.send_warning("An error occurred while fetching the referenced message.")
        if not message:
            return await ctx.send_warning("Please provide a message to translate or reply to a message.")
        try:
            translated = GoogleTranslator(source="auto", target=language).translate(message)
            embed = discord.Embed(color=colors.NEUTRAL, title=f"Translated to {language}", description=f"```{translated}```")
            await ctx.send(embed=embed)
        except Exception:
            return await ctx.send_warning("This language is **not** supported.\n> Use **language codes** like `en`, `de`, or `fr`.")

    @command(usage="seen comminate")
    async def seen(self, ctx: EvelinaContext, *, user: User = Author):
        """Check when a user was last seen"""
        time_guild = await self.bot.db.fetchval("SELECT time FROM seen WHERE user_id = $1 AND guild_id = $2", user.id, ctx.guild.id)
        time_global = await self.bot.db.fetchval("SELECT time FROM seen WHERE user_id = $1 ORDER BY time DESC LIMIT 1", user.id)
        if time_guild:
            time_guild = f"<t:{int(time_guild.timestamp())}:R>"
        else:
            time_guild = "**never**"
        if time_global:
            time_global = f"<t:{int(time_global.timestamp())}:R>"
        else:
            time_global = "**never**"
        return await ctx.evelina_send(f"**{user}** was last seen {time_guild} in this server and {time_global} globally")

    @command(usage="afk touching grass")
    @is_afk()
    async def afk(self, ctx: EvelinaContext, *, reason: str = "AFK"):
        """Set an AFK status for when you are mentioned"""
        if len(reason) > 100:
            return await ctx.send_warning("Reason for being AFK cannot exceed **100** characters")
        await self.bot.db.execute("INSERT INTO afk VALUES ($1, $2, $3)", ctx.author.id, reason, datetime.datetime.now())
        await ctx.evelina_send(f"You're now AFK with the status: **{reason}**", emoji="😴")

    @command(aliases=["hex"])
    async def dominant(self, ctx: EvelinaContext, *, input: str = None):
        """Grab the most dominant color from an image, emoji, or URL"""
        attachment = None
        if input:
            emoji_match = re.match(r'<a?:(\w+):(\d+)>', input)
            if emoji_match:
                emoji_id = emoji_match.group(2)
                attachment = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if input.startswith('<a') else 'png'}"
            elif re.match(r'https?://', input):
                attachment = input
            else:
                return await ctx.send_warning("Invalid input. Please provide a valid emoji or URL.")
        else:
            attachment = await ctx.get_attachment()
            if not attachment:
                if ctx.message.reference:
                    if ctx.message.reference.cached_message.attachments:
                        attachment = ctx.message.reference.cached_message.attachments[0]
                    else:
                        emojis = re.findall(r'<a?:(\w+):(\d+)>', ctx.message.reference.cached_message.content)
                        if emojis:
                            emoji_id = emojis[0][1]
                            attachment = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if ctx.message.reference.cached_message.content.startswith('<a') else 'png'}"
        attachment_url = attachment.url if hasattr(attachment, 'url') else attachment
        color = hex(await self.bot.misc.dominant_color(attachment_url))[2:]
        hex_info = await self.bot.session.get_json("https://www.thecolorapi.com/id", params={"hex": color})
        hex_image = f"https://singlecolorimage.com/get/{color}/200x200"
        embed = (
            discord.Embed(color=int(color, 16))
            .set_author(icon_url=hex_image, name=hex_info["name"]["value"])
            .set_thumbnail(url=hex_image)
            .add_field(name="RGB", value=hex_info["rgb"]["value"])
            .add_field(name="HEX", value=hex_info["hex"]["value"])
        )
        await ctx.send(embed=embed)

    @command()
    async def perks(self, ctx: EvelinaContext):
        """Check the perks that you get for donating $3 to us / boost our server"""
        commands = [f"**{c.qualified_name}** - {c.help}" for c in set(self.bot.walk_commands()) if "has_perks" in [check.__qualname__.split(".")[0] for check in c.checks]]
        embed = discord.Embed(color=colors.NEUTRAL, description="You can find all **Donator Perks** [here](https://evelina.bot/commands) when you click on `Donator` + you get 20% more daily income\n> Use `;donate` to check payment methods")
        await ctx.send(embed=embed)

    @command()
    async def youngest(self, ctx: EvelinaContext):
        """Get the youngest account in the server"""
        member = (sorted([m for m in ctx.guild.members if not m.bot], key=lambda m: m.created_at, reverse=True))[0]
        embed = (
            discord.Embed(color=colors.NEUTRAL, title=f"Youngest account in {ctx.guild.name}", url=f"https://discord.com/users/{member.id}")
            .add_field(name="user", value=member.mention)
            .add_field(name="created", value=self.bot.misc.humanize_date(member.created_at.replace(tzinfo=None)))
        )
        await ctx.send(embed=embed)

    @command()
    async def oldest(self, ctx: EvelinaContext):
        """Get the oldest account in the server"""
        member = (sorted([m for m in ctx.guild.members if not m.bot], key=lambda m: m.created_at))[0]
        embed = (
            discord.Embed(color=colors.NEUTRAL, title=f"Oldest account in {ctx.guild.name}", url=f"https://discord.com/users/{member.id}")
            .add_field(name="user", value=member.mention)
            .add_field(name="created", value=self.bot.misc.humanize_date(member.created_at.replace(tzinfo=None)))
        )
        await ctx.send(embed=embed)

    @command(brief="manage messages", aliases=["pic"], usage="picperms comminate")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def picperms(self, ctx: EvelinaContext, member: discord.Member, *, channel: discord.TextChannel = CurrentChannel):
        """Give a member permissions to post attachments in a channel"""
        overwrite = channel.overwrites_for(member)
        if (channel.permissions_for(member).attach_files and channel.permissions_for(member).embed_links):
            overwrite.attach_files = False
            overwrite.embed_links = False
            await channel.set_permissions(member, overwrite=overwrite, reason=f"Picture permissions removed by {ctx.author}")
            return await ctx.send_success(f"Removed pic perms from {member.mention} in {channel.mention}")
        else:
            overwrite.attach_files = True
            overwrite.embed_links = True
            await channel.set_permissions(member, overwrite=overwrite, reason=f"Picture permissions granted by {ctx.author}",
            )
            return await ctx.send_success(f"Added pic perms to {member.mention} in {channel.mention}")
        
    @command(brief="manage messages", usage="stickerperms comminate")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def stickerperms(self, ctx: EvelinaContext, member: discord.Member, *, channel: discord.TextChannel = CurrentChannel):
        """Give a member permissions to use stickers in a channel"""
        overwrite = channel.overwrites_for(member)
        if channel.permissions_for(member).use_external_stickers:
            overwrite.use_external_stickers = False
            await channel.set_permissions(member, overwrite=overwrite, reason=f"Sticker permissions removed by {ctx.author}")
            return await ctx.send_success(f"Removed sticker perms from {member.mention} in {channel.mention}")
        else:
            overwrite.use_external_stickers = True
            await channel.set_permissions(member, overwrite=overwrite, reason=f"Sticker permissions granted by {ctx.author}")
            return await ctx.send_success(f"Added sticker perms to {member.mention} in {channel.mention}")
        
    @command(brief="manage messages", usage="emojiperms comminate")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def emojiperms(self, ctx: EvelinaContext, member: discord.Member, *, channel: discord.TextChannel = CurrentChannel):
        """Give a member permissions to use emojis in a channel"""
        overwrite = channel.overwrites_for(member)
        if channel.permissions_for(member).use_external_emojis:
            overwrite.use_external_emojis = False
            await channel.set_permissions(member, overwrite=overwrite, reason=f"Emoji permissions removed by {ctx.author}")
            return await ctx.send_success(f"Removed emoji perms from {member.mention} in {channel.mention}")
        else:
            overwrite.use_external_emojis = True
            await channel.set_permissions(member, overwrite=overwrite, reason=f"Emoji permissions granted by {ctx.author}")
            return await ctx.send_success(f"Added emoji perms to {member.mention} in {channel.mention}")

    @command()
    async def roles(self, ctx: EvelinaContext):
        """View all roles in the server"""
        role_list = [f"{role.mention} - {len(role.members)} member{'s' if len(role.members) != 1 else ''}" for role in ctx.guild.roles[1:][::-1]]
        return await ctx.paginate(role_list, f"Roles in {ctx.guild.name}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command()
    async def muted(self, ctx: EvelinaContext):
        """Returns a list of muted members whose mute is still active"""
        members = [
            f"{member.mention} - {discord.utils.format_dt(member.timed_out_until, style='R')}"
            for member in ctx.guild.members
            if member.timed_out_until and member.timed_out_until > discord.utils.utcnow()
        ]
        if members:
            return await ctx.paginate(members, f"Muted in {ctx.guild.name}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        else:
            await ctx.send_warning("No muted members found")

    @command(name="joins", aliases=["joined"], invoke_without_command=True, case_insensitive=True)
    async def joins(self, ctx: EvelinaContext, timeframe: ValidTime = None):
        """View members who joined the server within a given timeframe"""
        query = "SELECT user_id, timestamp FROM activity_joined WHERE guild_id = $1"
        if timeframe:
            since_timestamp = datetime.datetime.now().timestamp() - timeframe
            query += " AND timestamp >= $2 ORDER BY timestamp DESC"
            rows = await self.bot.db.fetch(query, ctx.guild.id, since_timestamp)
        else:
            query += " ORDER BY timestamp DESC LIMIT 100"
            rows = await self.bot.db.fetch(query, ctx.guild.id)
        if not rows:
            return await ctx.send_warning("No members joined in this timeframe")
        members_data = []
        for row in rows:
            member = ctx.guild.get_member(row['user_id'])
            join_time = datetime.datetime.fromtimestamp(row['timestamp'])
            if member:
                members_data.append(f"{member} - {discord.utils.format_dt(join_time, style='R')}")
            else:
                members_data.append(f"<@{row['user_id']}> (left) - {discord.utils.format_dt(join_time, style='R')}")
        since_message = f"since {datetime.datetime.fromtimestamp(since_timestamp).strftime('%d/%m/%Y %H:%M')}" if timeframe else "recently"
        return await ctx.paginate(members_data, f"Members joined {since_message}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @command(name="leaves", aliases=["left"], invoke_without_command=True, case_insensitive=True)
    async def leaves(self, ctx: EvelinaContext, timeframe: ValidTime = None):
        """View members who left the server within a given timeframe"""
        query = "SELECT user_id, timestamp FROM activity_left WHERE guild_id = $1"
        if timeframe:
            since_timestamp = datetime.datetime.now().timestamp() - timeframe
            query += " AND timestamp >= $2 ORDER BY timestamp DESC"
            rows = await self.bot.db.fetch(query, ctx.guild.id, since_timestamp)
        else:
            query += " ORDER BY timestamp DESC LIMIT 100"
            rows = await self.bot.db.fetch(query, ctx.guild.id)
        if not rows:
            return await ctx.send_warning("No members left in this timeframe")
        members_data = []
        for row in rows:
            member = ctx.guild.get_member(row['user_id'])
            leave_time = datetime.datetime.fromtimestamp(row['timestamp'])
            if member:
                members_data.append(f"{member} - {discord.utils.format_dt(leave_time, style='R')}")
            else:
                members_data.append(f"<@{row['user_id']}> (joined) - {discord.utils.format_dt(leave_time, style='R')}")
        since_message = f"since {datetime.datetime.fromtimestamp(since_timestamp).strftime('%d/%m/%Y %H:%M')}" if timeframe else "recently"
        return await ctx.paginate(members_data, f"Members left {since_message}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command()
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def bans(self, ctx: EvelinaContext):
        """Returns a list of banned users"""
        banned = [ban async for ban in ctx.guild.bans(limit=100)]
        if not banned:
            return await ctx.send_warning("There are no **banned** users.")
        try:
            ban_list = [f"**{m.user}** (`{m.user.id}`) - {m.reason or 'no reason'}" for m in banned]
        except IndexError as e:
            return await ctx.send_warning(f"An error occurred: {e}")
        return await ctx.paginate(ban_list, f"Bans", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command()
    async def bots(self, ctx: EvelinaContext):
        """Returns a list of all bots in this server"""
        return await ctx.paginate([f"{m.mention} `{m.id}`" for m in ctx.guild.members if m.bot], f"Bots", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command()
    async def boosters(self, ctx: EvelinaContext):
        """View all recent server boosters"""
        if ctx.guild.premium_subscribers:
            members = sorted(ctx.guild.premium_subscribers, key=lambda m: m.premium_since, reverse=True)
            member_details = [
                f"<@{m.id}> - {discord.utils.format_dt(m.premium_since, style='R')}"
                for m in members
            ]
            return await ctx.paginate(member_details, "Boosters", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        else:
            return await ctx.send_warning("This server has no boosters")
        
    @command()
    async def boosterslost(self, ctx: EvelinaContext):
        """View all recent server boosters that unboosted"""
        check = await self.bot.db.fetch("SELECT * FROM booster_lost WHERE guild_id = $1 ORDER BY time", ctx.guild.id)
        if not check:
            return await ctx.send_warning("This server has no recent booster losses.")
        member_details = []
        for m in check:
            member_details.append(f"<@{m['user_id']}> - <t:{m['time']}:R>")
        if member_details:
            member_details.reverse()
            return await ctx.paginate(member_details, "Boosters Lost", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        else:
            return await ctx.send_warning("This server has no recent booster losses.")

    @command(usage="inrole admin")
    async def inrole(self, ctx: EvelinaContext, *, role: Union[discord.Role, str]):
        """View members in a role"""
        if isinstance(role, str):
            role = ctx.find_role(role)
            if not role:
                return await ctx.send_warning("Role not found")
        if len(role.members) > 500:
            return await ctx.send_warning("can't view roles with more than **500** members")
        if role.members:
            return await ctx.paginate([f"{m} (`{m.id}`)" for m in role.members], f"Members with {role.name}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        else:
            return await ctx.send_warning("No members found with this role")

    @command(invoke_without_command=False)
    async def shazam(self, ctx: EvelinaContext):
        """Find a song by providing video or audio"""
        attachment = await ctx.get_attachment()
        embed = discord.Embed(color=colors.LOADING, description=f"{emojis.LOADING} {ctx.author.mention}: Searching for track...")
        mes = await ctx.send(embed=embed)
        try:
            out = await Shazam().recognize(await attachment.read())
            track = out["track"]["share"]["text"]
            link = out["track"]["share"]["href"]
            embed = discord.Embed(color=colors.SHAZAM, description=f"{emojis.SHAZAM} {ctx.author.mention}: Found [**{track}**]({link})")
            await mes.edit(embed=embed)
        except:
            embed = discord.Embed(color=colors.ERROR, description=f"{emojis.DENY} {ctx.author.mention}: Unable to find this attachment's track name")
            await mes.edit(embed=embed)

    @group(aliases=["tz"], invoke_without_command=True, case_insensitive=True)
    async def timezone(self, ctx: EvelinaContext, *, member: TimezoneMember = None):
        """View your current time or somebody elses"""
        if member is None:
            member = await TimezoneMember().convert(ctx, str(ctx.author))
        embed = discord.Embed(color=colors.NEUTRAL, description=f"🕑 {ctx.author.mention}: **{'Your' if member == ctx.author else member[0].name + '’s'}** current date **{member[1]}**")
        await ctx.send(embed=embed)

    async def get_lat_long(self, location: str) -> Optional[dict]:
        params = {"q": location, "format": "json"}
        results = await self.bot.session.get_json("https://nominatim.openstreetmap.org/search", params=params)
        if len(results) == 0:
            return None
        return {"lat": float(results[0]["lat"]), "lng": float(results[0]["lon"])}

    @timezone.command(name="check", usage="timezone check Vienna")
    async def timezone_check(self, ctx: EvelinaContext, *, location: str):
        """Check the current time for a specific location"""
        try:
            obj = TimezoneFinder()
            kwargs = await self.get_lat_long(location)
            if not kwargs:
                raise BadArgument("Invalid location provided. Please try again with a valid city or region.")
            timezone = await asyncio.to_thread(obj.timezone_at, **kwargs)
            if not timezone:
                raise BadArgument("Could not find a timezone for the given location.")
            local_time = arrow.utcnow().to(timezone).naive
            hour = local_time.strftime("%I:%M %p")
            week_day = self.week_days.get(local_time.weekday())
            month = self.months.get(local_time.month)
            day = self.bot.ordinal(local_time.day)
            embed = discord.Embed(
                color=colors.NEUTRAL,
                title=f"Current Time in {location.title()}",
                description=f"🕑 {week_day}, {month} {day} - **{hour}**",
            )
            await ctx.send(embed=embed)
        except BadArgument as e:
            await ctx.send_warning(str(e))
        except Exception as e:
            await ctx.send_warning("An error occurred while fetching the timezone. Please try again later.")    

    @timezone.command(name="set", usage="timezone set Vienna/Austria")
    async def timezone_set(self, ctx: EvelinaContext, *, timezone: TimezoneLocation):
        """Set your timezone"""
        return await ctx.send_success(f"Saved your timezone as **{timezone.timezone}**\n> 🕑 Current date: **{timezone.date}**")

    @timezone.command(name="unset")
    async def timezone_unset(self, ctx: EvelinaContext):
        """Unset your timezone"""
        await self.bot.db.execute("DELETE FROM timezone WHERE user_id = $1", ctx.author.id)
        return await ctx.send_success(f"You succesfully deleted your timezone")

    @timezone.command(name="list")
    async def timezone_list(self, ctx: EvelinaContext):
        """View a list of every member's timezone"""
        ids = [member.id for member in ctx.guild.members]
        chunk_size = 1000
        results = []
        for i in range(0, len(ids), chunk_size):
            chunk = ids[i:i + chunk_size]
            placeholders = ', '.join(['$' + str(j + 1) for j in range(len(chunk))])
            query = f"SELECT user_id, zone FROM timezone WHERE user_id IN ({placeholders})"
            results += await self.bot.db.fetch(query, *chunk)
        if not results:
            await ctx.send_warning("No one has defined a timezone.")
            return
        await ctx.paginate([f"{ctx.guild.get_member(result['user_id'])} - **{result['zone']}**" for result in results], f"Timezones", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(aliases=["bday"], usage="birthday vault.oy", invoke_without_command=True, case_insensitive=True)
    async def birthday(self, ctx: EvelinaContext, *, user: User = Author):
        """View your birthday or somebody else's"""
        check = await self.bot.db.fetchrow("SELECT * FROM birthday WHERE user_id = $1", user.id)
        if not check:
            raise BadArgument(f"{'**You** don' if user == ctx.author else f'**{user.name}** doesn'}'t have a **birthday** configured")
        day = check["day"]
        month = check["month"]
        year = check["year"]
        now = datetime.datetime.now()
        next_birthday = datetime.datetime(year=now.year, month=month, day=day)
        if next_birthday < now:
            next_birthday = datetime.datetime(year=now.year + 1, month=month, day=day)
        formatted_date = f"{self.months[month]} {day}" + (f", {year}" if year else "")
        embed = discord.Embed(color=0xDEA5A4, description=f"🎂 {ctx.author.mention}: {'**Your**' if user == ctx.author else f'**{user.name}**'} birthday is **{formatted_date}**. That's **{self.bot.misc.humanize_date(next_birthday)}** and {'you' if user == ctx.author else f'he'} will be **{next_birthday.year - year}** years old." if year else f"🎂 {ctx.author.mention}: **{user.name}'s** birthday is **{formatted_date}**. That's **{self.bot.misc.humanize_date(next_birthday)}**.")
        return await ctx.send(embed=embed)

    @birthday.command(name="set", usage="birthday set March 20 2004")
    async def birthday_set(self, ctx: EvelinaContext, *, date: str):
        """Set your birthday"""
        parts = date.strip().split()
        if len(parts) not in [2, 3]:
            return await ctx.send_warning("Invalid date format.\n> Please use either `March 20` or `March 20 2004`")
        month, day = parts[:2]
        year = parts[2] if len(parts) == 3 else None
        month = month.capitalize().strip()
        day = day.strip()
        if month not in self.months.values():
            return await ctx.send_warning("Invalid month provided. Please try again with a valid month.")
        if not day.isdigit():
            return await ctx.send_warning("Invalid day format. Please provide a numeric day.")
        day = int(day)
        month_index = list(self.months.values()).index(month) + 1
        max_day = calendar.monthrange(2024, month_index)[1]
        if not 1 <= day <= max_day:
            return await ctx.send_warning(f"Invalid day for {month}. {month} has {max_day} days.")
        if year:
            if not year.isdigit():
                return await ctx.send_warning("Invalid year format. Please provide a numeric year.")
            year = int(year)
            if not 1900 <= year <= 2100:
                return await ctx.send_warning("Invalid year provided. Please enter a year between 1900 and 2100.")
        await self.bot.db.execute(
            "INSERT INTO birthday (user_id, day, month, year) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (user_id) DO UPDATE SET day = $2, month = $3, year = $4",
            ctx.author.id, day, month_index, year if year else None
        )
        embed = discord.Embed(color=0xDEA5A4, description=f"🎂 Your birthday is set to **{month} {day}{', ' + str(year) if year else ''}**." )
        return await ctx.send(embed=embed)

    @birthday.command(name="unset")
    async def birthday_unset(self, ctx: EvelinaContext):
        """Unset your birthday"""
        check = await self.bot.db.fetchrow("SELECT * FROM birthday WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send_warning("You haven't set a birthday yet")
        await self.bot.db.execute("DELETE FROM birthday WHERE user_id = $1", ctx.author.id)
        return await ctx.send_success("You succesfully deleted your birthday")

    @birthday.command(name="list")
    async def birthday_list(self, ctx: EvelinaContext):
        """View a list of every member's birthday in this server"""
        results = await self.bot.db.fetch("SELECT * FROM birthday")
        server_member_ids = {member.id for member in ctx.guild.members}
        bday_list = [{"user_id": result['user_id'], "date": datetime.datetime(year=result['year'] if result['year'] else 9999, month=result['month'], day=result['day'])} for result in results if result['user_id'] in server_member_ids]
        bday_list.sort(key=lambda x: (x["date"].month, x["date"].day))
        formatted_list = [f"<@{bday['user_id']}> - {self.months[bday['date'].month]} {bday['date'].day}, {bday['date'].year}".strip() for bday in bday_list if bday['date'].year != 9999]
        return await ctx.paginate(formatted_list, f"Birthdays in {ctx.guild.name}", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @birthday.command(name="globallist", aliases=["glist"])
    async def birthday_globallist(self, ctx: EvelinaContext):
        """View a list of every user's birthday"""
        results = await self.bot.db.fetch("SELECT * FROM birthday")
        bday_list = [{"user_id": result['user_id'], "date": datetime.datetime(year=result['year'] if result['year'] else 9999, month=result['month'], day=result['day'])} for result in results]
        bday_list.sort(key=lambda x: (x["date"].month, x["date"].day))
        formatted_list = [f"<@{bday['user_id']}> - {self.months[bday['date'].month]} {bday['date'].day}, {bday['date'].year}".strip() for bday in bday_list if bday['date'].year != 9999]
        return await ctx.paginate(formatted_list, "Global Birthdays", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @birthday.group(name="reward", invoke_without_command=True, case_insensitive=True)
    async def birthday_reward(self, ctx: EvelinaContext):
        """Set a reward for your birthday"""
        return await ctx.create_pages()
    
    @birthday_reward.command(name="set", usage="birthday reward set birthdayrole")
    async def birthday_reward_set(self, ctx: EvelinaContext, role: discord.Role):
        """Set a role as a reward for your birthday"""
        await self.bot.db.execute("INSERT INTO birthday_reward VALUES ($1, $2)", ctx.guild.id, role.id)
        return await ctx.send_success(f"Set **{role.name}** as your birthday reward")
    
    @birthday_reward.command(name="unset")
    async def birthday_reward_unset(self, ctx: EvelinaContext):
        """Unset your birthday reward"""
        await self.bot.db.execute("DELETE FROM birthday_reward WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success(f"You succesfully deleted your birthday reward")
    
    @birthday_reward.command(name="view")
    async def birthday_reward_view(self, ctx: EvelinaContext):
        """View your birthday reward"""
        role_id = await self.bot.db.fetchval("SELECT role_id FROM birthday_reward WHERE guild_id = $1", ctx.guild.id)
        if role_id:
            role = ctx.guild.get_role(role_id)
            return await ctx.send_success(f"Your birthday reward is **{role.mention}**")
        return await ctx.send_warning("You haven't set a birthday reward yet")

    @group(name="language", aliases=["lang"], usage="language comminate", invoke_without_command=True, case_insensitive=True)
    async def language(self, ctx: EvelinaContext, user: Optional[discord.User] = Author):
        """View your current languages or somebody else's"""
        result = await self.bot.db.fetchval("SELECT languages FROM language WHERE user_id = $1", user.id)
        if result:
            languages = json.loads(result)
            languages_str = ', '.join(languages)
            await ctx.send_success(f"{'**Your**' if user == ctx.author else f'**{user.name}’s**'} current languages are: **{languages_str}**")
        else:
            await ctx.send_warning(f"{'**You** don’t' if user == ctx.author else f'**{user.name}** doesn’t'} have a **language** configured")

    @language.command(name="add", usage="language add de")
    async def language_add(self, ctx: EvelinaContext, language: ValidLanguage):
        """Add a language"""
        existing_languages = await self.bot.db.fetchval("SELECT languages FROM language WHERE user_id = $1", ctx.author.id)
        if existing_languages:
            languages = json.loads(existing_languages)
            if language not in languages:
                languages.append(language)
        else:
            languages = [language]
        await self.bot.db.execute(
            "INSERT INTO language (user_id, languages) VALUES ($1, $2::jsonb) ON CONFLICT (user_id) DO UPDATE SET languages = $2::jsonb",
            ctx.author.id,
            json.dumps(languages)
        )
        return await ctx.send_success(f"Added **{language}** to your languages")

    @language.command(name="remove", usage="language remove de")
    async def language_remove(self, ctx: EvelinaContext, language: ValidLanguage):
        """Remove a specific language"""
        existing_languages = await self.bot.db.fetchval("SELECT languages FROM language WHERE user_id = $1", ctx.author.id)
        if existing_languages:
            languages = json.loads(existing_languages)
            if language in languages:
                languages.remove(language)
                if languages:
                    await self.bot.db.execute(
                        "UPDATE language SET languages = $2::jsonb WHERE user_id = $1",
                        ctx.author.id,
                        json.dumps(languages)
                    )
                else:
                    await self.bot.db.execute("DELETE FROM language WHERE user_id = $1", ctx.author.id)
                return await ctx.send_success(f"Removed **{language}** from your languages")
        return await ctx.send_warning(f"You haven't set **{language}** as one of your languages")

    @language.command(name="translate", usage="language translate de")
    async def language_translate(self, ctx: EvelinaContext, language: str, ephemeral: bool = True):
        """Translate a message to a specific language"""
        check = await self.bot.db.fetchval("SELECT lang FROM language_translate WHERE user_id = $1", ctx.author.id)
        if not check:
            await self.bot.db.execute("INSERT INTO language_translate VALUES ($1, $2, $3)", ctx.author.id, language, ephemeral)
        else:
            await self.bot.db.execute("UPDATE language_translate SET lang = $1, ephemeral = $2 WHERE user_id = $3", language, ephemeral, ctx.author.id)
        return await ctx.send_success(f"Set your translation language to **{language}** with {'ephemeral' if ephemeral else 'non-ephemeral'} messages")

    @language.command(name="list")
    async def language_list(self, ctx: EvelinaContext):
        """View a list of every member's languages"""
        results = await self.bot.db.fetch("SELECT * FROM language")
        if not results:
            return await ctx.send_warning("No one has defined any languages.")
        user_languages = []
        for result in results:
            languages = json.loads(result['languages'])
            languages_str = ', '.join(languages)
            user_languages.append(f"<@{result['user_id']}> - **{languages_str}**")
        await ctx.paginate(
            user_languages, 
            "Languages", 
            {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None}
        )

    @group(invoke_without_command=True, case_insensitive=True)
    async def reminder(self, ctx: EvelinaContext):
        """Get reminders for a duration set about whatever you choose"""
        return await ctx.create_pages()

    @reminder.command(name="add", usage="reminder add 1h Close the window")
    async def reminder_add(self, ctx: EvelinaContext, time: ValidTime, *, task: str):
        """Add a reminder"""
        if time < 60:
            return await ctx.send_warning("Reminder time can't be less than a minute")
        else:
            try:
                remind_time = int((datetime.datetime.now() + datetime.timedelta(seconds=time)).timestamp())
                await self.bot.db.execute("INSERT INTO reminder VALUES ($1,$2,$3,$4,$5)", ctx.author.id, ctx.channel.id, ctx.guild.id, remind_time, task)
                await ctx.send_reminder(f"I'm going to remind you **in {humanfriendly.format_timespan(time)}** about **{task}**")
            except Exception:
                return await ctx.send_warning("An error occurred while setting the reminder")

    @reminder.command(name="remove", aliases=["cancel"])
    async def reminder_remove(self, ctx: EvelinaContext, id: int):
        """Remove a reminder by its position in the list"""
        results = await self.bot.db.fetch("SELECT * FROM reminder WHERE user_id = $1 ORDER BY time ASC", ctx.author.id)
        if not results:
            return await ctx.send_warning("There are **no** reminders set")
        if id < 1 or id > len(results):
            return await ctx.send_warning(f"Reminder ID `{id}` is **invalid**")
        reminder_to_remove = results[id - 1]
        await self.bot.db.execute("DELETE FROM reminder WHERE guild_id = $1 AND user_id = $2 AND channel_id = $3 AND time = $4",
                                ctx.guild.id, ctx.author.id, reminder_to_remove['channel_id'], reminder_to_remove['time'])
        return await ctx.send_success(f"Deleted reminder `{id}` - **{reminder_to_remove['task']}**")

    @reminder.command(name="list")
    async def reminder_list(self, ctx: EvelinaContext):
        """View a list of every reminder"""
        results = await self.bot.db.fetch("SELECT * FROM reminder WHERE user_id = $1 ORDER BY time ASC", ctx.author.id)
        if not results:
            return await ctx.send_warning("There are **no** reminders set")
        reminder_list = [f"{result['task']} - <t:{int(result['time'])}:R>" for idx, result in enumerate(results)]
        await ctx.paginate(reminder_list, title=f"Reminders", author={"name": ctx.author.name, "icon_url": ctx.author.avatar or None})

    @command(aliases=["remindme"], usage="remind 1h Close the window")
    async def remind(self, ctx: EvelinaContext, time: ValidTime, *, task: str):
        """Add a reminder"""
        if time < 60:
            return await ctx.send_warning("Reminder time can't be less than a minute")
        else:
            try:
                remind_time = int((datetime.datetime.now() + datetime.timedelta(seconds=time)).timestamp())
                await self.bot.db.execute("INSERT INTO reminder VALUES ($1,$2,$3,$4,$5)", ctx.author.id, ctx.channel.id, ctx.guild.id, remind_time, task)
                await ctx.send_reminder(f"I'm going to remind you **in {humanfriendly.format_timespan(time)}** about **{task}**")
            except Exception:
                return await ctx.send_warning("An error occurred while setting the reminder")

    @group(name="tag", aliases=["tags"], invoke_without_command=True, case_insensitive=True)
    async def tag(self, ctx: EvelinaContext, *, tag: str):
        """View a tag"""
        check = await self.bot.db.fetchrow("SELECT * FROM tags WHERE guild_id = $1 AND name = $2", ctx.guild.id, tag)
        if not check:
            return await ctx.send_warning(f"No tag found for **{tag}**")
        if check["response"]:
            await ctx.reply(check["response"])
        else:
            await ctx.send_warning("The tag exists but has no content.")

    @tag.command(name="add", aliases=["create"], brief="manage guild", usage="tag add pic, Boost us for pic perms")
    @has_guild_permissions(manage_guild=True)
    async def tag_add(self, ctx: EvelinaContext, *, args: str):
        """Add a tag to guild"""
        args = args.split(",", maxsplit=1)
        if len(args) == 1:
            return await ctx.send_warning("No response found. Make sure to use a `,` to split the trigger from the response")
        name = args[0]
        response = args[1].strip()
        if await self.bot.db.fetchrow("SELECT * FROM tags WHERE guild_id = $1 AND name = $2", ctx.guild.id, name):
            return await ctx.send_warning(f"A tag for **{name}** already exists!")
        await self.bot.db.execute("INSERT INTO tags VALUES ($1, $2, $3, $4)", ctx.guild.id, ctx.author.id, name, response)
        await ctx.send_success(f"Added tag for **{name}**" + f"\n```{response}```")

    @tag.command(name="remove", aliases=["delete", "del"], brief="manage guild", usage="tag remove pic")
    @has_guild_permissions(manage_guild=True)
    async def tag_remove(self, ctx: EvelinaContext, *, tag: str):
        """Remove a tag from guild"""
        if not await self.bot.db.fetchrow("SELECT * FROM tags WHERE guild_id = $1 AND name = $2", ctx.guild.id, tag):
            return await ctx.send_warning(f"That is **not** an existing tag")
        await self.bot.db.execute("DELETE FROM tags WHERE guild_id = $1 AND name = $2", ctx.guild.id, tag)
        await ctx.send_success(f"Deleted the tag **{tag}**")

    @tag.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def tag_reset(self, ctx: EvelinaContext):
        """Reset every tag for this guild"""
        if not await self.bot.db.fetchrow("SELECT * FROM tags WHERE guild_id = $1", ctx.guild.id,):
            return await ctx.send_warning(f"There are **no** tags set")
        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute("DELETE FROM tags WHERE guild_id = $1", interaction.guild.id)
            await interaction.response.edit_message(embed=discord.Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Removed all **tags**", color=colors.SUCCESS), view=None)
        async def no_func(interaction: discord.Interaction):
            await interaction.response.edit_message(embed=discord.Embed(description=f"{emojis.DENY} {interaction.user.mention}: Tags deletion got canceled", color=colors.NEUTRAL), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **delete** all tags?", yes_func, no_func)

    @tag.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def tag_list(self, ctx: EvelinaContext):
        """View a list of every tag in guild"""
        results = await self.bot.db.fetch("SELECT * FROM tags WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"There are **no** tags set")
        await ctx.paginate([f"{result['name']} - {result['response']}" for result in results], title=f"Tags", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon or None})

    @tag.command(name="random")
    async def tag_random(self, ctx: EvelinaContext):
        """Return a random tag"""
        result = await self.bot.db.fetchrow("SELECT * FROM tags WHERE guild_id = $1 ORDER BY RANDOM() LIMIT 1", ctx.guild.id)
        if not result:
            return await ctx.send_warning(f"There are **no** tags set")
        x = await self.bot.embed_build.convert(ctx, result["response"])
        x["content"] = f"({result['name']}) {x['content'] or ''}"
        await ctx.send(**x)

    @tag.command(name="edit", brief="tag owner", usage="tag edit pic, Boost us for pic perms")
    async def tag_edit(self, ctx: EvelinaContext, *, args: str):
        """Edit the contents of your tag"""
        args = args.split(",", maxsplit=1)
        if len(args) == 1:
            return await ctx.send_warning("No response found. Make sure to use a `,` to split the trigger from the response")
        name = args[0]
        response = args[1].strip()
        check = await self.bot.db.fetchrow("SELECT * FROM tags WHERE guild_id = $1 AND name = $2", ctx.guild.id, name)
        if not check:
            return await ctx.send_warning(f"No tag found for **{name}**")
        if check["author_id"] != ctx.author.id:
            return await ctx.send_warning(f"You are not the **author** of this tag")
        await self.bot.db.execute("UPDATE tags SET response = $1 WHERE guild_id = $2 AND name = $3", response, ctx.guild.id, name)
        await ctx.send_success(f"Updated tag for **{name}**" + f"\n```{response}```")

    @tag.command(name="author", aliases=["creator"], usage="tag author pic")
    async def tag_author(self, ctx: EvelinaContext, *, tag: str):
        """View the author of a tag"""
        check = await self.bot.db.fetchrow("SELECT * FROM tags WHERE guild_id = $1 AND name = $2", ctx.guild.id, tag)
        if not check:
            return await ctx.send_warning(f"No tag found for **{tag}**")
        user = self.bot.get_user(check["author_id"])
        return await ctx.evelina_send(f"The author of this tag is **{user}**")

    @tag.command(name="search", usage="tag search pic")
    async def tag_search(self, ctx: EvelinaContext, *, query: str):
        """Search for tags containing a keyword"""
        results = await self.bot.db.fetch(f"SELECT * FROM tags WHERE guild_id = $1 AND name LIKE '%{query}%'", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"No **tags** found")
        await ctx.paginate([f"**{result['name']}**" for result in results], title=f"Tags like {query}")

    @command(name="color", aliases=["colour"], usage="color #ff00ff")
    async def color(self, ctx: EvelinaContext, *, color: Color):
        """Show a hex codes color in a embed"""
        embed = discord.Embed(color=color)
        embed.set_author(name=f"Showing hex code: {color}")
        embed.add_field(name="RGB Value", value=", ".join([str(x) for x in color.to_rgb()]), inline=True)
        embed.add_field(name="INT", value=color.value, inline=True)
        embed.set_thumbnail(url=("https://place-hold.it/250x219/" + str(color).replace("#", "") + "?text=%20"))
        return await ctx.send(embed=embed)

    @command(name="transparent", aliases=["tp"], usage="transparent https://evelina.bot/icon.png", cooldown=5)
    @cooldown(1, 5, BucketType.user)
    async def transparent(self, ctx: EvelinaContext, url: str = None):
        """Remove background from an image"""
        if not url:
            url = await ctx.get_attachment()
            if not url:
                return await ctx.send_help(ctx.command)
            url = url.url
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.send_warning("The image provided is not an url")
        async with ctx.channel.typing():
            image = await self.bot.session.get_bytes(url)
        with tempfile.TemporaryDirectory() as tdir:
            temp_file = os.path.join(tdir, "transparent.png")
            temp_file_output = os.path.join(tdir, "transparent_output.png")
            async with aio_open(temp_file, "wb") as f:
                await f.write(image)
            try:
                term = await asyncio.wait_for(
                    asyncio.create_subprocess_shell(
                        f"rembg i {temp_file} {temp_file_output}",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    ),
                    timeout=15,
                )
                stdout, stderr = await term.communicate()
                if stdout:
                    return await ctx.send_warning("Couldn't make the image **transparent**")
                if stderr:
                    return await ctx.send_warning("Couldn't make the image **transparent**")
            except asyncio.TimeoutError:
                return await ctx.send_warning("Couldn't make the image **transparent** due to a timeout")
            if not os.path.exists(temp_file_output):
                return await ctx.send_warning("Couldn't make the image **transparent**")
            await ctx.reply(file=discord.File(temp_file_output))

    @command(name="compress", aliases=["resize"], usage="compress 50 https://evelina.bot/icon.png", cooldown=5)
    @cooldown(1, 5, BucketType.user)
    async def compress(self, ctx: EvelinaContext, percentage: int, url: str = None):
        """Compress or resize an image or GIF based on percentage"""
        if percentage < 10 or percentage > 250:
            return await ctx.send_warning("Please provide a percentage between **10** and **250**")
        if not url:
            url = await ctx.get_attachment()
            if not url:
                return await ctx.send_help(ctx.command)
            url = url.url
        try:
            response = requests.get(url)
            image = Image.open(BytesIO(response.content))
            if image.format == "GIF" and getattr(image, "is_animated", False):
                frames = []
                for frame in range(image.n_frames):
                    image.seek(frame)
                    frame_image = image.copy()
                    width, height = frame_image.size
                    new_width = int(width * (percentage / 100))
                    new_height = int(height * (percentage / 100))
                    resized_frame = frame_image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    frames.append(resized_frame)
                img_byte_arr = BytesIO()
                frames[0].save(
                    img_byte_arr,
                    format="GIF",
                    save_all=True,
                    append_images=frames[1:],
                    duration=image.info.get("duration", 100),
                    loop=image.info.get("loop", 0),
                    optimize=True,
                )
                filename = "resized_animation.gif"
            else:
                width, height = image.size
                new_width = int(width * (percentage / 100))
                new_height = int(height * (percentage / 100))
                resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
                img_byte_arr = BytesIO()
                resized_image.save(img_byte_arr, format=image.format)
                filename = f"resized_image.{image.format.lower()}"
            img_byte_arr.seek(0)
            file = discord.File(fp=img_byte_arr, filename=filename)
            await ctx.send(file=file)
        except Exception as e:
            await ctx.send_warning(f"An error occurred while processing the image: {e}")

    @group(name="spotify_old", invoke_without_command=True, case_insensitive=True)
    async def spotify_old(self, ctx: EvelinaContext):
        """Get information about spotify"""
        return await ctx.create_pages()

    @spotify_old.command(name="track", aliases=["tr"], usage="spotify track yeat")
    async def spotify_old_track(self, ctx: EvelinaContext, *, query: str):
        """Search for a track on spotify"""
        data = await self.bot.session.get_json(f"https://api.evelina.bot/spotify/track?q={query}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            await ctx.send_warning(f"Couldn't get information about **{query}**")
            return
        track_name = data.get('track', {}).get('name', 'Unknown Track')
        track_url = data.get('track', {}).get('url', '#')
        artist_name = data.get('artist', {}).get('name', 'Unknown Artist')
        artist_url = data.get('artist', {}).get('url', '#')
        album_name = data.get('album', {}).get('name', 'Unknown Album')
        album_url = data.get('album', {}).get('url', '#')
        embed = (discord.Embed(color=0x1ED760, description=f"{emojis.SPOTIFY} [**{track_name}**]({track_url}) by [**{artist_name}**]({artist_url}) on [**{album_name}**]({album_url})"))
        await ctx.send(embed=embed)

    @command(name="crypto", aliases=["convert", "conv"], usage="crypto 125 eur ltc")
    async def crypto(self, ctx: EvelinaContext, amount: float, from_currency: str, to_currency: str):
        """Convert cryptocurrency to a specified currency"""
        try:
            data = await self.bot.session.get_json(f"https://api.evelina.bot/crypto?amount={amount}&from={from_currency}&to={to_currency}&key=X3pZmLq82VnHYTd6Cr9eAw")
            if data["status"] == "success":
                amount_from = data.get(from_currency.upper(), 'N/A')
                amount_to = data.get(to_currency.upper(), 'N/A')
                view = self.CryptoConversionView(amount_to)
                return await ctx.send(embed=Embed(color=colors.EXCHANGE, description=f"{emojis.EXCHANGE} {ctx.author.mention}: {amount_from} **{from_currency.upper()}** is {amount_to} **{to_currency.upper()}**"), view=view)
            else:
                return await ctx.send_warning("Failed to retrieve conversion data. Please check the currency codes.")
        except Exception:
            return await ctx.send_warning("An error occurred while retrieving conversion data.")

    class CryptoConversionView(View):
        def __init__(self, amount_to: str):
            super().__init__()
            self.amount_to = amount_to

        @discord.ui.button(label="Copy Amount", style=discord.ButtonStyle.primary)
        async def get_conversion_details(self, interaction: Interaction, button: Button):
            await interaction.response.send_message(self.amount_to, ephemeral=True)
        
    @command(aliases=["calc", "math"], usage="calculate 100 * 5")
    async def calculate(self, ctx: EvelinaContext, *, expression: str):
        """Calculate a mathematical expression including percentages"""
        try:
            original_expression = expression
            expression = re.sub(r'(\d+(\.\d+)?)(\s*[-+/*]\s*)(\d+(\.\d+)?)%', r'\1\3(\1 * \4 / 100)', expression)
            result = eval(expression, {"__builtins__": None}, {"sqrt": math.sqrt, "pow": math.pow, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi, "e": math.e})
            await ctx.evelina_send(f"Result of **{original_expression}** is **{result}**")
        except Exception as e:
            await ctx.send_warning(f"An error occurred while calculating the expression: {str(e)}")
        
    @command(name="ocr", usage="ocr image")
    async def ocr(self, ctx: EvelinaContext, image: str = None):
        """Perform OCR on an image or an attached image"""
        try:
            image_data = None
            if ctx.message.attachments:
                attachment = ctx.message.attachments[0]
                image_data = await attachment.read()
            elif image:
                image_data, status = await self.bot.session.get_bytes(image, return_status=True)
                if status != 200:
                    await ctx.send_warning("Failed to download the image.")
                    return
            if not image_data:
                await ctx.send_warning("Please provide either an image URL or attach an image.")
                return
            image = Image.open(io.BytesIO(image_data))
            text = pytesseract.image_to_string(image)
            await ctx.send(f"{text}")
        except Exception:
            pass
    
    @command(name="lyrics", usage="lyrics yeat, king tonka", description="Get the lyrics for a song")
    async def lyrics(self, ctx: EvelinaContext, *, song: str = None):
        try:
            if song is None:
                member = next(
                    (
                        g.get_member(ctx.author.id)
                        for g in self.bot.guilds
                        if g.get_member(ctx.author.id)
                        and g.get_member(ctx.author.id).activities
                    ),
                    None,
                )
                if member and member.activities:
                    for activity in member.activities:
                        if isinstance(activity, discord.Spotify):
                            song = f"{activity.title} {activity.artist if getattr(activity, 'artist', None) else ''}"
                            break
                        elif getattr(
                            activity, "type", None
                        ) == discord.ActivityType.listening and getattr(activity, "details", None):
                            song = activity.details
                            break
                if not song:
                    return await ctx.send_warning("Please provide a song name to search for")

            async with ctx.channel.typing():
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "https://genius.com/api/search/multi",
                        params={"q": song},
                    ) as response:
                        resp = await response.json()

                    track = next(
                        (
                            hit["result"]
                            for section in resp.get("response", {}).get("sections", [])
                            for hit in section.get("hits", [])
                            if hit["index"] == "song"
                        ),
                        None,
                    )
                    if not track:
                        return await ctx.send_warning("Couldn't find lyrics for this song")

                    async with session.get(track["url"]) as response:
                        html = await response.text()

                    soup = BeautifulSoup(html.replace("<br/>", "\n"), "html.parser")

                    divs = soup.find_all(
                        "div", class_=re.compile("^lyrics$|Lyrics__Container")
                    )
                    if not divs:
                        return await ctx.send_warning("Couldn't find lyrics for this song")

                    lyrics = ""
                    for div in divs:
                        header_containers = div.find_all(
                            "div", class_=re.compile("LyricsHeader__Container")
                        )
                        for header_container in header_containers:
                            header_container.decompose()

                        lyrics += div.get_text()

                    lyrics = lyrics.strip("\n")

                    section_pattern = re.compile(r"(\[.*?\])")
                    parts = section_pattern.split(lyrics)

                    organized_sections = []
                    current_section = ""
                    current_header = ""

                    for part in parts:
                        if section_pattern.match(part):
                            if current_section:
                                organized_sections.append(
                                    (current_header, current_section.strip())
                                )
                            current_header = part
                            current_section = ""
                        else:
                            current_section += part

                    if current_section:
                        organized_sections.append(
                            (current_header, current_section.strip())
                        )

                    if not organized_sections:
                        organized_sections = [("", lyrics)]

                    pages = []
                    for i, (header, content) in enumerate(organized_sections, 1):
                        section_text = f"{header}\n{content}" if header else content
                        embed = Embed(
                            title=track["title"],
                            description=f"```yaml\n{section_text}```",
                            url=track["url"],
                            color=await self.bot.misc.dominant_color(
                                track["song_art_image_url"]),
                        )
                        embed.set_author(
                            name=track["primary_artist"]["name"],
                            icon_url=track["primary_artist"]["image_url"],
                            url=track["primary_artist"]["url"],
                        )
                        embed.set_footer(
                            text=f"{i}/{len(organized_sections)} • {track.get('release_date_for_display', 'Unknown Release Date')}"
                        )
                        if track.get("song_art_image_url"):
                            embed.set_thumbnail(url=track["song_art_image_url"])
                        pages.append(embed)

                    await ctx.paginator(pages)
        except Exception as e:
            await ctx.send_warning(f"An error occurred while trying to fetch the lyrics for **{song}**: {e}")

    @command(name="movie", alias=["series", "show"], usage="movie The Matrix", description="Get information about a movie")
    async def movie(self, ctx: EvelinaContext, *, query: str):
        search_url = f"http://www.omdbapi.com/?s={query}&apikey={config.OMDB}"
        search_data = await self.bot.session.get_json(search_url)
        if search_data['Response'] == "False":
            return await ctx.send_warning(f"No results found for **{query}**")
        search_results = search_data['Search']
        detailed_results = []
        for result in search_results:
            movie_id = result['imdbID']
            detail_url = f"http://www.omdbapi.com/?i={movie_id}&apikey={config.OMDB}"
            detailed_data = await self.bot.session.get_json(detail_url)
            detailed_results.append(detailed_data)
        embeds = [
            Embed(
                title=f"{movie['Title']} ({movie['Year']})",
                color=colors.NEUTRAL
            )
            .add_field(name="Rating", value=movie['imdbRating'], inline=True)
            .add_field(name="Genre", value=movie['Genre'], inline=True)
            .add_field(name="Language", value=movie['Language'], inline=True)
            .add_field(name="Director", value=movie['Director'], inline=True)
            .add_field(name="Writer", value=movie['Writer'], inline=True)
            .add_field(name="Actors", value=movie['Actors'], inline=True)
            .add_field(name="Plot", value=movie['Plot'], inline=False)
            .set_thumbnail(url=movie['Poster'])
            .set_footer(text=f"Page: {index + 1}/{len(detailed_results)} ({len(detailed_results)} entries)")
            for index, movie in enumerate(detailed_results)
        ]
        await ctx.paginator(embeds)

    async def get_message_count(self, user_id, server_id, days):
        query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
        result = await self.bot.db.fetchval(
            "SELECT SUM(message_count) FROM activity_messages WHERE user_id = $1 AND server_id = $2 AND message_date >= $3",
            user_id, server_id, query_date)
        return result if result else 0
    
    async def get_channel_message_count(self, channel_id, server_id, days):
        query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
        result = await self.bot.db.fetchval(
            "SELECT SUM(message_count) FROM activity_messages WHERE channel_id = $1 AND server_id = $2 AND message_date >= $3",
            channel_id, server_id, query_date)
        return result if result else 0
    
    async def get_all_message_counts(self, server_id, days):
        query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
        result = await self.bot.db.fetchval(
            "SELECT SUM(message_count) FROM activity_messages WHERE server_id = $1 AND message_date >= $2",
            server_id, query_date)
        return result if result else 0

    async def get_voice_time(self, user_id, server_id, days):
        query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
        result = await self.bot.db.fetchval(
            "SELECT SUM(voice_time) FROM activity_voice WHERE user_id = $1 AND server_id = $2 AND voice_date >= $3",
            user_id, server_id, query_date)
        return result if result else 0

    async def get_all_voice_time(self, server_id, days):
        query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
        result = await self.bot.db.fetchval(
            "SELECT SUM(voice_time) FROM activity_voice WHERE server_id = $1 AND voice_date >= $2",
            server_id, query_date)
        return result if result else 0

    async def get_all_users_message_counts(self, server_id, days=None):
        if days is not None:
            query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
            query = """
                SELECT user_id, SUM(message_count) as total_count
                FROM activity_messages
                WHERE server_id = $1 AND message_date >= $2
                GROUP BY user_id
                ORDER BY total_count DESC
            """
            result = await self.bot.db.fetch(query, server_id, query_date)
        else:
            query = """
                SELECT user_id, SUM(message_count) as total_count
                FROM activity_messages
                WHERE server_id = $1
                GROUP BY user_id
                ORDER BY total_count DESC
            """
            result = await self.bot.db.fetch(query, server_id)
        return result
    
    async def get_all_global_message_counts(self, days=None):
        if days is not None:
            query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
            query = """
                SELECT user_id, SUM(message_count) as total_count
                FROM activity_messages
                WHERE message_date >= $1
                GROUP BY user_id
                ORDER BY total_count DESC
            """
            result = await self.bot.db.fetch(query, query_date)
        else:
            query = """
                SELECT user_id, SUM(message_count) as total_count
                FROM activity_messages
                GROUP BY user_id
                ORDER BY total_count DESC
            """
            result = await self.bot.db.fetch(query)
        return result
    
    async def get_all_guilds_message_counts(self, days=None):
        if days is not None:
            query_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days)).date()
            query = """
                SELECT server_id, SUM(message_count) as total_count
                FROM activity_messages
                WHERE message_date >= $1
                GROUP BY server_id
                ORDER BY total_count DESC
            """
            result = await self.bot.db.fetch(query, query_date)
        else:
            query = """
                SELECT server_id, SUM(message_count) as total_count
                FROM activity_messages
                GROUP BY server_id
                ORDER BY total_count DESC
            """
            result = await self.bot.db.fetch(query)
        return result
    
    async def get_joined_count(self, guild_id, days):
        return await self.bot.db.fetchval(f"SELECT COUNT(user_id) FROM activity_joined WHERE guild_id = $1 AND timestamp >= EXTRACT(EPOCH FROM (CURRENT_DATE - INTERVAL '{days} days'))", guild_id)
    
    async def get_left_count(self, guild_id, days):
        return await self.bot.db.fetchval(f"SELECT COUNT(user_id) FROM activity_left WHERE guild_id = $1 AND timestamp >= EXTRACT(EPOCH FROM (CURRENT_DATE - INTERVAL '{days} days'))", guild_id)
    
    async def send_message_counts(self, ctx: EvelinaContext, message_counts, period):
        if not message_counts:
            return await ctx.send_warning(f"No messages found for **{period}**")
        entries = []
        total_messages = 0
        for rank, row in enumerate(message_counts, 1):
            user = self.bot.get_user(row['user_id'])
            user_mention = f"<@{row['user_id']}>"
            entries.append(f"{user.mention if user else user_mention} - {row['total_count']:,.0f} messages")
            total_messages += row['total_count']
        await ctx.paginate(entries, title=f"{period.capitalize()} Messages ({total_messages:,.0f})", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    async def send_guild_message_counts(self, ctx: EvelinaContext, message_counts, period):
        if not message_counts:
            return await ctx.send_warning(f"No messages found for **{period}**")
        entries = []
        total_messages = 0
        for rank, row in enumerate(message_counts, 1):
            guild = self.bot.get_guild(row['server_id'])
            entries.append(f"**{guild.name if guild else row['server_id']}** - {row['total_count']:,.0f} messages")
            total_messages += row['total_count']
        await ctx.paginate(entries, title=f"Guild {period.capitalize()} Messages ({total_messages:,.0f})")

    @group(name="messages", aliases=["m", "msg"], invoke_without_command=True, case_insensitive=True)
    async def messages(self, ctx: EvelinaContext, user: User = None):
        """Shows messages statistics"""
        if user is None:
            user = ctx.author
        return await ctx.invoke(self.messages_user, user=user)

    @messages.command(name="user", usage="messages user comminate")
    async def messages_user(self, ctx: EvelinaContext, user: User = None) -> None:
        """Shows messages sent by a user"""
        if not user:
            user = ctx.author
        user_id = user.id
        server_id = ctx.guild.id
        today_count = await self.get_message_count(user_id, server_id, 0)
        last_7_days_count = await self.get_message_count(user_id, server_id, 7)
        last_30_days_count = await self.get_message_count(user_id, server_id, 30)
        total_count = await self.bot.db.fetchval("SELECT SUM(message_count) FROM activity_messages WHERE user_id = $1 AND server_id = $2", user_id, server_id)
        total_count = total_count if total_count else 0
        embed = Embed(color=colors.NEUTRAL, title=f"{user.name}'s Messages")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.description = f"**Today**: {today_count:,.0f}\n**Last 7 days**: {last_7_days_count:,.0f}\n**Last 30 days**: {last_30_days_count:,.0f}\n**Total**: {total_count:,.0f}"
        return await ctx.send(embed=embed)

    @messages.command(name="daily")
    async def messages_daily(self, ctx: EvelinaContext):
        """Shows messages sent in the past 24 hours"""
        server_id = ctx.guild.id
        message_counts = await self.get_all_users_message_counts(server_id, 0)
        await self.send_message_counts(ctx, message_counts, period="daily")

    @messages.command(name="weekly")
    async def messages_weekly(self, ctx: EvelinaContext):
        """Shows messages sent in the past 7 days"""
        server_id = ctx.guild.id
        message_counts = await self.get_all_users_message_counts(server_id, 7)
        await self.send_message_counts(ctx, message_counts, period="weekly")

    @messages.command(name="monthly")
    async def messages_monthly(self, ctx: EvelinaContext):
        """Shows messages sent in the past 30 days"""
        server_id = ctx.guild.id
        message_counts = await self.get_all_users_message_counts(server_id, 30)
        await self.send_message_counts(ctx, message_counts, period="monthly")

    @messages.command(name="total")
    async def messages_total(self, ctx: EvelinaContext):
        """Shows messages sent for the total of the server"""
        server_id = ctx.guild.id
        message_counts = await self.get_all_users_message_counts(server_id, None)
        await self.send_message_counts(ctx, message_counts, period="total")

    @messages.command(name="global")
    async def messages_global(self, ctx: EvelinaContext):
        """Shows total messages sent across all servers"""
        daily_count = await self.bot.db.fetchval("SELECT SUM(message_count) FROM activity_messages WHERE message_date = CURRENT_DATE")
        weekly_count = await self.bot.db.fetchval("SELECT SUM(message_count) FROM activity_messages WHERE message_date >= CURRENT_DATE - INTERVAL '7 days'")
        monthly_count = await self.bot.db.fetchval("SELECT SUM(message_count) FROM activity_messages WHERE message_date >= CURRENT_DATE - INTERVAL '30 days'")
        total_count = await self.bot.db.fetchval("SELECT SUM(message_count) FROM activity_messages")
        embed = Embed(color=colors.NEUTRAL, title="Total Messages")
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.description = f"**Today**: {daily_count:,.0f}\n**Last 7 days**: {weekly_count:,.0f}\n**Last 30 days**: {monthly_count:,.0f}\n**Total**: {total_count:,.0f}"
        await ctx.send(embed=embed)

    @command(name="feedback", brief="administrator", usage="feedback I love this bot")
    @has_guild_permissions(administrator=True)
    async def feedback(self, ctx: EvelinaContext, *, feedback: str):
        """Send feedback about the bot"""
        check = await self.bot.db.fetchrow("SELECT * FROM testimonials WHERE guild_id = $1", ctx.guild.id)
        if check:
            return await ctx.send_warning("You have already submitted feedback")
        if len(feedback) < 50:
            return await ctx.send_warning("Feedback must be at least 50 characters long")
        if len(feedback) > 500:
            return await ctx.send_warning("Feedback must be at most 500 characters long")
        channel = self.bot.get_guild(self.bot.logging_guild).get_channel_or_thread(self.bot.logging_feedback)
        embed = Embed(color=colors.NEUTRAL, title=f"Feedback from {ctx.author}", description=f"```{feedback}```")
        embed.add_field(name="Guild", value=ctx.guild.name, inline=True)
        embed.add_field(name="User", value=ctx.author.mention, inline=True)
        embed.add_field(name="Created", value=f"<t:{int(ctx.message.created_at.timestamp())}:R>", inline=True)
        embed.set_footer(text=f"User ID: {ctx.author.id}")
        view = FeedbackView(self.bot)
        message = await channel.send(embed=embed, view=view)
        await self.bot.db.execute("INSERT INTO testimonials VALUES ($1, $2, $3, $4, $5)", ctx.guild.id, ctx.author.id, feedback, False, message.id)
        return await ctx.send_success("Feedback has been submitted")

    @command(name="visible")
    async def visible(self, ctx: EvelinaContext):
        if not isinstance(ctx.channel, discord.TextChannel):
            return await ctx.send("This command can only be used in a text channel")
        channel = ctx.channel
        members = [member for member in channel.members if channel.permissions_for(member).read_messages]
        return await ctx.paginate([f"{member.mention} (`{member.id}`)" for member in members], title=f"Visible Members ({len(members)})", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(name="forward", aliases=["fw"], brief="manage messages", usage="forward #channel")
    @has_guild_permissions(manage_messages=True)
    async def forward(self, ctx: EvelinaContext, channel: TextChannel):
        """Forward a message to a channel"""
        message = ctx.message.reference
        if not message or not message.cached_message:
            return await ctx.send_warning("Please reply to a valid message to forward it")
        await ctx.send_success(f"Forwarded message to {channel.mention}")
        return await ctx.message.reference.cached_message.forward(channel)
    
    @command(name="sync", usage="sync comminate", cooldown=60)
    @cooldown(1, 60, BucketType.user)
    async def sync(self, ctx: EvelinaContext, *, user: Member = Author):
        """Sync all relevant roles for a user on Evelina's server"""
        message = await ctx.send_loading(f"Synchronizing roles for {user.mention}...")
        if not user.mutual_guilds:
            return await ctx.send_warning(f"User {user.mention} doesn't share any server with **{self.bot.user.name}**", obj=message)
        evelina_guild = self.bot.get_guild(self.bot.logging_guild)
        evelina_member = user
        if not evelina_member:
            return await ctx.send_warning(f"User {user.mention} is not a member of **{evelina_guild.name}**", obj=message)
        roles_to_sync = {
            "owner": 1242509393308946503,
            "donator": 1242474452353290291,
            "instance_owner": 1284159368262324285,
            "premium": 1242474452353290291,
            "bug_hunter_3": 1243745562197626982,
            "bug_hunter_5": 1300196517969137754,
        }
        added_roles = []
        is_owner = any(g.owner_id == user.id for g in user.mutual_guilds)
        if await self.update_role(evelina_member, roles_to_sync["owner"], is_owner, "Server Owner role synchronization"):
            added_roles.append(evelina_guild.get_role(roles_to_sync["owner"]))
        donator = await self.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", user.id)
        instance = await self.bot.db.fetchrow("SELECT * FROM instance WHERE owner_id = $1", user.id)
        premium = await self.bot.db.fetchrow("SELECT * FROM premium WHERE user_id = $1", user.id)
        bughunter_count = await self.bot.db.fetchval("SELECT COUNT(*) FROM bugreports WHERE user_id = $1", user.id)
        if await self.update_role(evelina_member, roles_to_sync["donator"], bool(donator) or bool(premium), "Donator role synchronization"):
            added_roles.append(evelina_guild.get_role(roles_to_sync["donator"]))
        if await self.update_role(evelina_member, roles_to_sync["instance_owner"], bool(instance), "Instance Owner role synchronization"):
            added_roles.append(evelina_guild.get_role(roles_to_sync["instance_owner"]))
        if await self.update_role(evelina_member, roles_to_sync["premium"], bool(premium) or bool(donator), "Premium role synchronization"):
            added_roles.append(evelina_guild.get_role(roles_to_sync["premium"]))
        if await self.update_role(evelina_member, roles_to_sync["bug_hunter_3"], bughunter_count >= 3, "Bug Hunter (3 reports) role synchronization"):
            added_roles.append(evelina_guild.get_role(roles_to_sync["bug_hunter_3"]))
        if await self.update_role(evelina_member, roles_to_sync["bug_hunter_5"], bughunter_count >= 5, "Bug Hunter (5 reports) role synchronization"):
            added_roles.append(evelina_guild.get_role(roles_to_sync["bug_hunter_5"]))
        if added_roles:
            roles_mentions = ", ".join(role.mention for role in added_roles if role)
            await ctx.send_success(f"Synchronized roles for {user.mention} successfully. Added roles: {roles_mentions}", obj=message)
        else:
            await ctx.send_success(f"No roles to synchronize for {user.mention}", obj=message)

    async def update_role(self, member, role_id, should_have, reason):
        role = member.guild.get_role(role_id)
        if role:
            if should_have and role not in member.roles:
                await member.add_roles(role, reason=reason)
                return True
            elif not should_have and role in member.roles:
                await member.remove_roles(role, reason=reason)
        return False
    
    @group(name="activity", aliases=["act"], invoke_without_command=True, case_insensitive=True)
    async def activity(self, ctx: EvelinaContext, user: Member = Author, range: Optional[str] = "lifetime"):
        """Shows activity statistics"""
        valid_ranges = {"1d": 1, "7d": 7, "14d": 14, "30d": 30, "lifetime": None}
        if range not in valid_ranges:
            return await ctx.send("Invalid time range! Please use one of the following: `1d`, `7d`, `14d`, `30d` or `lifetime`")
        return await ctx.invoke(self.activity_user, user=user, range=range)

    @activity.command(name="user", usage="activity user comminate 30d")
    async def activity_user(self, ctx: EvelinaContext, user: Member = Author, range: Optional[str] = "lifetime"):
        """Shows activity statistics for a user with an optional time range"""
        valid_ranges = {"1d": 1, "7d": 7, "14d": 14, "30d": 30, "lifetime": None}
        if range not in valid_ranges:
            return await ctx.send("Invalid time range! Please use one of the following: `1d`, `7d`, `14d`, `30d` or `lifetime`")
        message_date_cond = f"AND message_date >= (CURRENT_DATE - INTERVAL '{valid_ranges[range]} days')" if valid_ranges[range] else ""
        voice_date_cond = f"AND voice_date >= (CURRENT_DATE - INTERVAL '{valid_ranges[range]} days')" if valid_ranges[range] else ""
        
        async def fetch_message_rank(table, value_col, date_cond):
            result = await self.bot.db.fetch(f"""
            SELECT user_id, SUM({value_col}) as value FROM {table}
            WHERE server_id = $1 {date_cond}
            GROUP BY user_id ORDER BY value DESC
            """, ctx.guild.id)
            for rank, row in enumerate(result, 1):
                if row['user_id'] == user.id:
                    return rank
            return 0
        
        async def fetch_voice_rank(table, value_col, date_cond):
            result = await self.bot.db.fetch(f"""
            SELECT user_id, SUM({value_col}) as value FROM {table}
            WHERE server_id = $1 {date_cond}
            GROUP BY user_id ORDER BY value DESC
            """, ctx.guild.id)
            for rank, row in enumerate(result, 1):
                if row['user_id'] == user.id:
                    return rank
            return 0

        async def fetch_top_message_channels(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT channel_id, SUM({value_col}) as value FROM {table}
            WHERE user_id = $1 AND server_id = $2 {message_date_cond} AND channel_id != 0
            GROUP BY channel_id ORDER BY value DESC LIMIT 3
            """, user.id, ctx.guild.id)
        
        async def fetch_top_voice_channels(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT channel_id, SUM({value_col}) as value FROM {table}
            WHERE user_id = $1 AND server_id = $2 {voice_date_cond} AND channel_id != 0
            GROUP BY channel_id ORDER BY value DESC LIMIT 3
            """, user.id, ctx.guild.id)

        msg_rank, voice_rank = await fetch_message_rank('activity_messages', 'message_count', message_date_cond), await fetch_voice_rank('activity_voice', 'voice_time', voice_date_cond)
        text_ch, voice_ch = await fetch_top_message_channels('activity_messages', 'message_count'), await fetch_top_voice_channels('activity_voice', 'voice_time')

        day_msg, week_msg, month_msg = await self.get_message_count(user.id, ctx.guild.id, 0), await self.get_message_count(user.id, ctx.guild.id, 7), await self.get_message_count(user.id, ctx.guild.id, 30)
        total_msg = await self.bot.db.fetchval("SELECT SUM(message_count) FROM activity_messages WHERE user_id = $1 AND server_id = $2", user.id, ctx.guild.id) or 0

        day_voice, week_voice, month_voice = await self.get_voice_time(user.id, ctx.guild.id, 0), await self.get_voice_time(user.id, ctx.guild.id, 7), await self.get_voice_time(user.id, ctx.guild.id, 30)
        total_voice = await self.bot.db.fetchval("SELECT SUM(total_time) FROM voicetrack WHERE user_id = $1 AND guild_id = $2", user.id, ctx.guild.id) or 0

        # --- Drawing setup ---
        background = Image.open("data/images/activity/evelina_user_stats.png")
        draw = ImageDraw.Draw(background)
        font_30, font_40 = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 30), ImageFont.truetype("data/fonts/ChocolatesBold.otf", 40)

        # --- Draw Rank ---
        draw.text((275, 190), f"#{msg_rank:,.0f}", font=font_40, fill="#d0d3d6")
        draw.text((275, 262.5), f"#{voice_rank:,.0f}", font=font_40, fill="#d0d3d6")

        # --- Draw Messages ---
        for i, txt in enumerate([f"{day_msg:,} messages", f"{week_msg:,} messages", f"{month_msg:,} messages"]):
            draw.text((550, 182.5 + (47.5 * i)), txt, font=font_30, fill="#d0d3d6")

        # --- Draw Voice ---
        for i, time in enumerate([day_voice, week_voice, month_voice]):
            draw.text((970, 182.5 + (47.5 * i)), self.bot.misc.humanize_time(time, True, 'HH-MM-SS'), font=font_30, fill="#d0d3d6")

        # --- Draw Text Channels ---
        for i, ch in enumerate(text_ch):
            name, count = ctx.guild.get_channel(ch['channel_id']), f"{ch['value']:,.0f} messages"
            draw.text((45, 425 + (60 * i)), f"#{name.name if name else 'Unknown'}", font=font_30, fill="#d0d3d6")
            draw.text((305, 425 + (60 * i)), count, font=font_30, fill="#d0d3d6")

        # --- Draw Voice Channels ---
        for i, ch in enumerate(voice_ch):
            name, time = ctx.guild.get_channel(ch['channel_id']), self.bot.misc.humanize_time(ch['value'], True, 'HH-MM-SS')
            draw.text((675, 425 + (60 * i)), f"#{name.name if name else 'Unknown'}", font=font_30, fill="#d0d3d6")
            draw.text((930, 425 + (60 * i)), time, font=font_30, fill="#d0d3d6")

        # --- Profile Icon ---
        avatar_asset = user.avatar or user.default_avatar
        avatar_image = Image.open(BytesIO(await avatar_asset.read())).convert("RGBA").resize((75, 75))
        mask = Image.new("L", avatar_image.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0) + avatar_image.size, radius=15, fill=255)
        avatar_image.putalpha(mask)
        background.paste(avatar_image, (20, 20), avatar_image)

        # --- Username & Server ---
        draw.text((110, 18), user.name, font=font_30, fill="#d0d3d6")
        if ctx.guild.icon:
            icon_image = Image.open(BytesIO(await ctx.guild.icon.read())).convert("RGBA").resize((38, 38))
            mask = Image.new("L", icon_image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0) + icon_image.size, radius=15, fill=255)
            icon_image.putalpha(mask)
            background.paste(icon_image, (110, 55), icon_image)
        draw.text((155, 58), ctx.guild.name, font=font_30, fill="#d0d3d6")

        # --- Send File ---
        image_bytes = BytesIO()
        background.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        await ctx.send(file=discord.File(fp=image_bytes, filename="activity.png"))

    @activity.command(name="channel", usage="activity channel #general 30d")
    async def activity_channel(self, ctx: EvelinaContext, channel: TextChannel, range: Optional[str] = "lifetime"):
        """Shows activity statistics for a channel with an optional time range"""
        valid_ranges = {"1d": 1, "7d": 7, "14d": 14, "30d": 30, "lifetime": None}
        if range not in valid_ranges:
            return await ctx.send("Invalid time range! Please use one of the following: `1d`, `7d`, `14d`, `30d` or `lifetime`")
        date_cond = f"AND message_date >= (CURRENT_DATE - INTERVAL '{valid_ranges[range]} days')" if valid_ranges[range] else ""

        async def fetch_top_members(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT user_id, SUM({value_col}) as value FROM {table}
            WHERE channel_id = $1 AND server_id = $2 {date_cond}
            GROUP BY user_id ORDER BY value DESC LIMIT 3
            """, channel.id, ctx.guild.id)
        
        async def fetch_top_dates(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT message_date as date, SUM({value_col}) as value FROM {table}
            WHERE channel_id = $1 AND server_id = $2 {date_cond}
            GROUP BY message_date ORDER BY value DESC LIMIT 3
            """, channel.id, ctx.guild.id)
        
        day_msg, week_msg, month_msg = await self.get_channel_message_count(channel.id, ctx.guild.id, 0), await self.get_channel_message_count(channel.id, ctx.guild.id, 7), await self.get_channel_message_count(channel.id, ctx.guild.id, 30)
        top_members = await fetch_top_members('activity_messages', 'message_count')
        top_dates = await fetch_top_dates('activity_messages', 'message_count')
        total_msg = await self.bot.db.fetchval(f"SELECT SUM(message_count) FROM activity_messages WHERE channel_id = $1 AND server_id = $2 {date_cond}", channel.id, ctx.guild.id) or 0

        contributors_day = await self.bot.db.fetchval("SELECT COUNT(DISTINCT user_id) FROM activity_messages WHERE channel_id = $1 AND server_id = $2 AND message_date = CURRENT_DATE", channel.id, ctx.guild.id) or 0
        contributors_week = await self.bot.db.fetchval("SELECT COUNT(DISTINCT user_id) FROM activity_messages WHERE channel_id = $1 AND server_id = $2 AND message_date >= CURRENT_DATE - INTERVAL '7 days'", channel.id, ctx.guild.id) or 0
        contributors_month = await self.bot.db.fetchval("SELECT COUNT(DISTINCT user_id) FROM activity_messages WHERE channel_id = $1 AND server_id = $2 AND message_date >= CURRENT_DATE - INTERVAL '30 days'", channel.id, ctx.guild.id) or 0

        # --- Drawing setup ---
        background = Image.open("data/images/activity/evelina_channel_stats.png")
        draw = ImageDraw.Draw(background)
        font_30, font_40 = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 30), ImageFont.truetype("data/fonts/ChocolatesBold.otf", 40)
        box_left, box_top, box_right, box_bottom = 35, 140, 415, 335  # Shifted 20px down
        box_width = box_right - box_left
        box_height = box_bottom - box_top
        num_bbox = draw.textbbox((0, 0), f"{total_msg:,}", font=font_40)
        label_bbox = draw.textbbox((0, 0), "messages", font=font_30)
        num_width, num_height = num_bbox[2] - num_bbox[0], num_bbox[3] - num_bbox[1]
        label_width, label_height = label_bbox[2] - label_bbox[0], label_bbox[3] - label_bbox[1]
        spacing = 10
        total_text_height = num_height + spacing + label_height
        start_y = box_top + (box_height - total_text_height) / 2
        start_x_num = box_left + (box_width - num_width) / 2
        start_x_label = box_left + (box_width - label_width) / 2
        draw.text((start_x_num, start_y), f"{total_msg:,}", font=font_40, fill="#d0d3d6")
        draw.text((start_x_label, start_y + num_height + spacing), "messages", font=font_30, fill="#d0d3d6")

        # --- Draw Messages ---
        for i, txt in enumerate([f"{day_msg:,} messages", f"{week_msg:,} messages", f"{month_msg:,} messages"]):
            draw.text((550, 182.5 + (47.5 * i)), txt, font=font_30, fill="#d0d3d6")

        # --- Draw Contributors ---
        for i, count in enumerate([contributors_day, contributors_week, contributors_month]):
            draw.text((970, 182.5 + (47.5 * i)), f"{count:,.0f} members", font=font_30, fill="#d0d3d6")

        # --- Draw Top Members ---
        for i, member in enumerate(top_members):
            user = ctx.guild.get_member(member['user_id'])
            draw.text((45, 425 + (60 * i)), f"{user.name if user else 'Unknown'}", font=font_30, fill="#d0d3d6")
            draw.text((305, 425 + (60 * i)), f"{member['value']:,.0f} messages", font=font_30, fill="#d0d3d6")

        # --- Draw Top Dates ---
        for i, date in enumerate(top_dates):
            draw.text((675, 425 + (60 * i)), f"{date['date'].strftime('%d %b %Y')}", font=font_30, fill="#d0d3d6")
            draw.text((930, 425 + (60 * i)), f"{date['value']:,.0f} messages", font=font_30, fill="#d0d3d6")

        # --- Profile Icon ---
        avatar_image = Image.open("data/images/text.png").convert("RGBA").resize((75, 75))
        background.paste(avatar_image, (20, 20), avatar_image)

        # --- Username & Server ---
        draw.text((110, 18), f"#{channel.name}", font=font_30, fill="#d0d3d6")
        if ctx.guild.icon:
            icon_image = Image.open(BytesIO(await ctx.guild.icon.read())).convert("RGBA").resize((38, 38))
            mask = Image.new("L", icon_image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0) + icon_image.size, radius=15, fill=255)
            icon_image.putalpha(mask)
            background.paste(icon_image, (110, 55), icon_image)
        draw.text((155, 58), ctx.guild.name, font=font_30, fill="#d0d3d6")

        # --- Send File ---
        image_bytes = BytesIO()
        background.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        await ctx.send(file=discord.File(fp=image_bytes, filename="activity.png"))

    @activity.command(name="messages", usage="activity messages 30d")
    async def activity_messages(self, ctx: EvelinaContext, range: Optional[str] = "lifetime"):
        """Shows activity statistics for messages with an optional time range"""
        valid_ranges = {"1d": 1, "7d": 7, "14d": 14, "30d": 30, "lifetime": None}
        if range not in valid_ranges:
            return await ctx.send("Invalid time range! Please use one of the following: `1d`, `7d`, `14d`, `30d` or `lifetime`")
        date_cond = f"AND message_date >= (CURRENT_DATE - INTERVAL '{valid_ranges[range]} days')" if valid_ranges[range] else ""

        async def fetch_top_members(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT user_id, SUM({value_col}) as value FROM {table}
            WHERE server_id = $1 {date_cond}
            GROUP BY user_id ORDER BY value DESC LIMIT 3
            """, ctx.guild.id)
        
        async def fetch_top_channels(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT channel_id, SUM({value_col}) as value FROM {table}
            WHERE server_id = $1 {date_cond} AND channel_id != 0
            GROUP BY channel_id ORDER BY value DESC LIMIT 3
            """, ctx.guild.id)
        
        day_msg, week_msg, month_msg = await self.get_all_message_counts(ctx.guild.id, 0), await self.get_all_message_counts(ctx.guild.id, 7), await self.get_all_message_counts(ctx.guild.id, 30)
        top_members = await fetch_top_members('activity_messages', 'message_count')
        top_channels = await fetch_top_channels('activity_messages', 'message_count')
        total_msg = await self.bot.db.fetchval(f"SELECT SUM(message_count) FROM activity_messages WHERE server_id = $1 {date_cond}", ctx.guild.id) or 0        
        day_voice, week_voice, month_voice = await self.get_all_voice_time(ctx.guild.id, 0), await self.get_all_voice_time(ctx.guild.id, 7), await self.get_all_voice_time(ctx.guild.id, 30)

        # --- Drawing setup ---
        background = Image.open("data/images/activity/evelina_message_stats.png")
        draw = ImageDraw.Draw(background)
        font_30, font_40 = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 30), ImageFont.truetype("data/fonts/ChocolatesBold.otf", 40)
        box_left, box_top, box_right, box_bottom = 35, 140, 415, 335  # Shifted 20px down
        box_width = box_right - box_left
        box_height = box_bottom - box_top
        num_bbox = draw.textbbox((0, 0), f"{total_msg:,}", font=font_40)
        label_bbox = draw.textbbox((0, 0), "messages", font=font_30)
        num_width, num_height = num_bbox[2] - num_bbox[0], num_bbox[3] - num_bbox[1]
        label_width, label_height = label_bbox[2] - label_bbox[0], label_bbox[3] - label_bbox[1]
        spacing = 10
        total_text_height = num_height + spacing + label_height
        start_y = box_top + (box_height - total_text_height) / 2
        start_x_num = box_left + (box_width - num_width) / 2
        start_x_label = box_left + (box_width - label_width) / 2
        draw.text((start_x_num, start_y), f"{total_msg:,}", font=font_40, fill="#d0d3d6")
        draw.text((start_x_label, start_y + num_height + spacing), "messages", font=font_30, fill="#d0d3d6")

        # --- Draw Messages ---
        for i, txt in enumerate([f"{day_msg:,} messages", f"{week_msg:,} messages", f"{month_msg:,} messages"]):
            draw.text((550, 182.5 + (47.5 * i)), txt, font=font_30, fill="#d0d3d6")

        # --- Draw Voice ---
        for i, time in enumerate([day_voice, week_voice, month_voice]):
            draw.text((970, 182.5 + (47.5 * i)), self.bot.misc.humanize_time(time, True, 'HH-MM-SS'), font=font_30, fill="#d0d3d6")

        # --- Draw Top Members ---
        for i, member in enumerate(top_members):
            user = ctx.guild.get_member(member['user_id'])
            draw.text((45, 425 + (60 * i)), f"{user.name if user else 'Unknown'}", font=font_30, fill="#d0d3d6")
            draw.text((305, 425 + (60 * i)), f"{member['value']:,.0f} messages", font=font_30, fill="#d0d3d6")

        # --- Draw Top Channels ---
        for i, ch in enumerate(top_channels):
            name, count = ctx.guild.get_channel(ch['channel_id']), f"{ch['value']:,.0f} messages"
            draw.text((675, 425 + (60 * i)), f"#{name.name if name else 'Unknown'}", font=font_30, fill="#d0d3d6")
            draw.text((930, 425 + (60 * i)), count, font=font_30, fill="#d0d3d6")

        # --- Profile Icon ---
        avatar_image = Image.open("data/images/text.png").convert("RGBA").resize((75, 75))
        background.paste(avatar_image, (20, 20), avatar_image)

        # --- Username & Server ---
        draw.text((110, 18), "Messages", font=font_30, fill="#d0d3d6")
        if ctx.guild.icon:
            icon_image = Image.open(BytesIO(await ctx.guild.icon.read())).convert("RGBA").resize((38, 38))
            mask = Image.new("L", icon_image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0) + icon_image.size, radius=15, fill=255)
            icon_image.putalpha(mask)
            background.paste(icon_image, (110, 55), icon_image)
        draw.text((155, 58), ctx.guild.name, font=font_30, fill="#d0d3d6")

        # --- Send File ---
        image_bytes = BytesIO()
        background.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        await ctx.send(file=discord.File(fp=image_bytes, filename="activity.png"))

    @activity.command(name="voice", usage="activity voice 30d")
    async def activity_voice(self, ctx: EvelinaContext, range: Optional[str] = "lifetime"):
        """Shows activity statistics for voice with an optional time range"""
        valid_ranges = {"1d": 1, "7d": 7, "14d": 14, "30d": 30, "lifetime": None}
        if range not in valid_ranges:
            return await ctx.send("Invalid time range! Please use one of the following: `1d`, `7d`, `14d`, `30d` or `lifetime`")
        date_cond = f"AND voice_date >= (CURRENT_DATE - INTERVAL '{valid_ranges[range]} days')" if valid_ranges[range] else ""

        async def fetch_top_members(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT user_id, SUM({value_col}) as value FROM {table}
            WHERE server_id = $1 {date_cond}
            GROUP BY user_id ORDER BY value DESC LIMIT 3
            """, ctx.guild.id)
        
        async def fetch_top_channels(table, value_col):
            return await self.bot.db.fetch(f"""
            SELECT channel_id, SUM({value_col}) as value FROM {table}
            WHERE server_id = $1 {date_cond} AND channel_id != 0
            GROUP BY channel_id ORDER BY value DESC LIMIT 3
            """, ctx.guild.id)
        
        day_msg, week_msg, month_msg = await self.get_all_message_counts(ctx.guild.id, 0), await self.get_all_message_counts(ctx.guild.id, 7), await self.get_all_message_counts(ctx.guild.id, 30)
        top_members = await fetch_top_members('activity_voice', 'voice_time')
        top_channels = await fetch_top_channels('activity_voice', 'voice_time')
        total_voice = await self.bot.db.fetchval(f"SELECT SUM(voice_time) FROM activity_voice WHERE server_id = $1 {date_cond}", ctx.guild.id) or 0
        day_voice, week_voice, month_voice = await self.get_all_voice_time(ctx.guild.id, 0), await self.get_all_voice_time(ctx.guild.id, 7), await self.get_all_voice_time(ctx.guild.id, 30)

        formated_total_voice = total_voice / 60 / 60

        # --- Drawing setup ---
        background = Image.open("data/images/activity/evelina_message_stats.png")
        draw = ImageDraw.Draw(background)
        font_30, font_40 = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 30), ImageFont.truetype("data/fonts/ChocolatesBold.otf", 40)
        box_left, box_top, box_right, box_bottom = 35, 140, 415, 335  # Shifted 20px down
        box_width = box_right - box_left
        box_height = box_bottom - box_top
        num_bbox = draw.textbbox((0, 0), f"{formated_total_voice:.2f}", font=font_40)
        label_bbox = draw.textbbox((0, 0), "hours", font=font_30)
        num_width, num_height = num_bbox[2] - num_bbox[0], num_bbox[3] - num_bbox[1]
        label_width, label_height = label_bbox[2] - label_bbox[0], label_bbox[3] - label_bbox[1]
        spacing = 10
        total_text_height = num_height + spacing + label_height
        start_y = box_top + (box_height - total_text_height) / 2
        start_x_num = box_left + (box_width - num_width) / 2
        start_x_label = box_left + (box_width - label_width) / 2
        draw.text((start_x_num, start_y), f"{formated_total_voice:.2f}", font=font_40, fill="#d0d3d6")
        draw.text((start_x_label, start_y + num_height + spacing), "hours", font=font_30, fill="#d0d3d6")

        # --- Draw Messages ---
        for i, txt in enumerate([f"{day_msg:,} messages", f"{week_msg:,} messages", f"{month_msg:,} messages"]):
            draw.text((550, 182.5 + (47.5 * i)), txt, font=font_30, fill="#d0d3d6")

        # --- Draw Voice ---
        for i, time in enumerate([day_voice, week_voice, month_voice]):
            draw.text((970, 182.5 + (47.5 * i)), self.bot.misc.humanize_time(time, True, 'HH-MM-SS'), font=font_30, fill="#d0d3d6")

        # --- Draw Top Members ---
        for i, member in enumerate(top_members):
            user = ctx.guild.get_member(member['user_id'])
            draw.text((45, 425 + (60 * i)), f"{user.name if user else 'Unknown'}", font=font_30, fill="#d0d3d6")
            draw.text((305, 425 + (60 * i)), self.bot.misc.humanize_time(member['value'], True, 'HH-MM-SS'), font=font_30, fill="#d0d3d6")

        # --- Draw Top Channels ---
        for i, ch in enumerate(top_channels):
            name, count = ctx.guild.get_channel(ch['channel_id']), self.bot.misc.humanize_time(ch['value'], True, 'HH-MM-SS')
            draw.text((675, 425 + (60 * i)), f"#{name.name if name else 'Unknown'}", font=font_30, fill="#d0d3d6")
            draw.text((930, 425 + (60 * i)), count, font=font_30, fill="#d0d3d6")

        # --- Profile Icon ---
        avatar_image = Image.open("data/images/voice.png").convert("RGBA").resize((75, 75))
        background.paste(avatar_image, (20, 20), avatar_image)

        # --- Username & Server ---
        draw.text((110, 18), "Voice", font=font_30, fill="#d0d3d6")
        if ctx.guild.icon:
            icon_image = Image.open(BytesIO(await ctx.guild.icon.read())).convert("RGBA").resize((38, 38))
            mask = Image.new("L", icon_image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0) + icon_image.size, radius=15, fill=255)
            icon_image.putalpha(mask)
            background.paste(icon_image, (110, 55), icon_image)
        draw.text((155, 58), ctx.guild.name, font=font_30, fill="#d0d3d6")

        # --- Send File ---
        image_bytes = BytesIO()
        background.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        await ctx.send(file=discord.File(fp=image_bytes, filename="activity.png"))

    @activity.command(name="server", usage="activity server 30d")
    async def activity_server(self, ctx: EvelinaContext, range: Optional[str] = "lifetime"):
        """Shows activity statistics for the server with an optional time range"""
        valid_ranges = {"1d": 1, "7d": 7, "14d": 14, "30d": 30, "lifetime": None}
        if range not in valid_ranges:
            return await ctx.send("Invalid time range! Please use one of the following: `1d`, `7d`, `14d`, `30d` or `lifetime`")
        date_cond = f"AND timestamp >= EXTRACT(EPOCH FROM (CURRENT_DATE - INTERVAL '{valid_ranges[range]} days'))" if valid_ranges[range] else ""

        async def fetch_top_join_dates(table):
            return await self.bot.db.fetch(f"""
            SELECT to_timestamp(timestamp)::date as date, COUNT(user_id) as value FROM {table}
            WHERE guild_id = $1 {date_cond}
            GROUP BY date ORDER BY value DESC LIMIT 3
            """, ctx.guild.id)
        
        async def fetch_top_leave_dates(table):
            return await self.bot.db.fetch(f"""
            SELECT to_timestamp(timestamp)::date as date, COUNT(user_id) as value FROM {table}
            WHERE guild_id = $1 {date_cond}
            GROUP BY date ORDER BY value DESC LIMIT 3
            """, ctx.guild.id)
        
        day_joined, week_joined, month_joined = await self.get_joined_count(ctx.guild.id, 0), await self.get_joined_count(ctx.guild.id, 7), await self.get_joined_count(ctx.guild.id, 30)
        day_left, week_left, month_left = await self.get_left_count(ctx.guild.id, 0), await self.get_left_count(ctx.guild.id, 7), await self.get_left_count(ctx.guild.id, 30)

        top_joined_dates = await fetch_top_join_dates('activity_joined')
        top_left_dates = await fetch_top_leave_dates('activity_left')

        total_members = ctx.guild.member_count

        # --- Drawing setup ---
        background = Image.open("data/images/activity/evelina_server_stats.png")
        draw = ImageDraw.Draw(background)
        font_30, font_40 = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 30), ImageFont.truetype("data/fonts/ChocolatesBold.otf", 40)
        box_left, box_top, box_right, box_bottom = 35, 140, 415, 335  # Shifted 20px down
        box_width = box_right - box_left
        box_height = box_bottom - box_top
        num_bbox = draw.textbbox((0, 0), f"{total_members:,}", font=font_40)
        label_bbox = draw.textbbox((0, 0), "members", font=font_30)
        num_width, num_height = num_bbox[2] - num_bbox[0], num_bbox[3] - num_bbox[1]
        label_width, label_height = label_bbox[2] - label_bbox[0], label_bbox[3] - label_bbox[1]
        spacing = 10
        total_text_height = num_height + spacing + label_height
        start_y = box_top + (box_height - total_text_height) / 2
        start_x_num = box_left + (box_width - num_width) / 2
        start_x_label = box_left + (box_width - label_width) / 2
        draw.text((start_x_num, start_y), f"{total_members:,}", font=font_40, fill="#d0d3d6")
        draw.text((start_x_label, start_y + num_height + spacing), "members", font=font_30, fill="#d0d3d6")

        # --- Draw Joined ---
        for i, txt in enumerate([f"{day_joined:,} members", f"{week_joined:,} members", f"{month_joined:,} members"]):
            draw.text((550, 182.5 + (47.5 * i)), txt, font=font_30, fill="#d0d3d6")

        # --- Draw Left ---
        for i, txt in enumerate([f"{day_left:,} members", f"{week_left:,} members", f"{month_left:,} members"]):
            draw.text((970, 182.5 + (47.5 * i)), txt, font=font_30, fill="#d0d3d6")

        # --- Draw Top Joined Dates ---
        for i, date in enumerate(top_joined_dates):
            draw.text((45, 425 + (60 * i)), f"{date['date'].strftime('%d %b %Y')}", font=font_30, fill="#d0d3d6")
            draw.text((305, 425 + (60 * i)), f"{date['value']:,.0f} members", font=font_30, fill="#d0d3d6")

        # --- Draw Top Left Dates ---
        for i, date in enumerate(top_left_dates):
            draw.text((675, 425 + (60 * i)), f"{date['date'].strftime('%d %b %Y')}", font=font_30, fill="#d0d3d6")
            draw.text((930, 425 + (60 * i)), f"{date['value']:,.0f} members", font=font_30, fill="#d0d3d6")

        # --- Profile Icon ---
        avatar_image = Image.open("data/images/server.png").convert("RGBA").resize((75, 75))
        background.paste(avatar_image, (20, 20), avatar_image)

        # --- Username & Server ---
        draw.text((110, 18), ctx.guild.name, font=font_30, fill="#d0d3d6")
        if ctx.guild.icon:
            icon_image = Image.open(BytesIO(await ctx.guild.icon.read())).convert("RGBA").resize((38, 38))
            mask = Image.new("L", icon_image.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0) + icon_image.size, radius=15, fill=255)
            icon_image.putalpha(mask)
            background.paste(icon_image, (110, 55), icon_image)
        draw.text((155, 58), ctx.guild.name, font=font_30, fill="#d0d3d6")

        # --- Send File ---
        image_bytes = BytesIO()
        background.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        await ctx.send(file=discord.File(fp=image_bytes, filename="activity.png"))

    @activity.group(name="ignore", aliases=["ig"], invoke_without_command=True, case_insensitive=True)
    async def activity_ignore(self, ctx: EvelinaContext):
        """Manage ignored channels for activity tracking"""
        return await ctx.create_pages()
    
    @activity_ignore.command(name="add", aliases=["a"], brief="manage guild", usage="activity ignore add #general")
    @has_guild_permissions(manage_guild=True)
    async def activity_ignore_add(self, ctx: EvelinaContext, channel: TextChannel):
        """Add a channel to the ignored list for activity tracking"""
        check = await self.bot.db.fetchrow("SELECT * FROM activity_ignore WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if check:
            return await ctx.send_warning(f"Channel {channel.mention} is already ignored for activity tracking")
        await self.bot.db.execute("INSERT INTO activity_ignore (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Channel {channel.mention} has been added to the ignored list for activity tracking")
    
    @activity_ignore.command(name="remove", aliases=["r"], brief="manage guild", usage="activity ignore remove #general")
    @has_guild_permissions(manage_guild=True)
    async def activity_ignore_remove(self, ctx: EvelinaContext, channel: Union[TextChannel, int]):
        """Remove a channel from the ignored list for activity tracking"""
        channel_id = self.bot.misc.convert_channel(channel)
        check = await self.bot.db.fetchrow("SELECT * FROM activity_ignore WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        if not check:
            return await ctx.send_warning(f"Channel {self.bot.misc.humanize_channel(channel_id)} is not ignored for activity tracking")
        await self.bot.db.execute("DELETE FROM activity_ignore WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"Channel {self.bot.misc.humanize_channel(channel_id)} has been removed from the ignored list for activity tracking")
    
    @activity_ignore.command(name="list", aliases=["l"], brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def activity_ignore_list(self, ctx: EvelinaContext):
        """List all ignored channels for activity tracking"""
        result = await self.bot.db.fetch("SELECT * FROM activity_ignore WHERE guild_id = $1", ctx.guild.id)
        if not result:
            return await ctx.send("No channels are ignored for activity tracking")
        channels = [self.bot.misc.humanize_channel(row['channel_id']) for row in result]
        return await ctx.paginate(channels, title="Ignored for Activity Tracking", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @activity.group(name="leaderboard", aliases=["lb"], invoke_without_command=True, case_insensitive=True)
    async def activity_leaderboard(self, ctx: EvelinaContext):
        """Shows the activity leaderboard for the server"""
        return await ctx.create_pages()
    
    @activity_leaderboard.command(name="add", brief="manage guild", usage="activity leaderboard add #act-msg message 30d")
    @has_guild_permissions(manage_guild=True)
    async def activity_leaderboard_add(self, ctx: EvelinaContext, channel: TextChannel, table: str, range: Optional[str] = "lifetime"):
        """Add activity leaderboard for a channel"""
        valid_tables = {"message": "activity_messages", "voice": "activity_voice"}
        valid_ranges = {"1d": 1, "7d": 7, "30d": 30, "lifetime": None}
        if table not in valid_tables:
            return await ctx.send_warning("Invalid table! Use `message` or `voice`.")
        if range not in valid_ranges:
            return await ctx.send_warning("Invalid time range! Use `1d`, `7d`, `30d`, or `lifetime`.")
        date_condition = f"AND {table}_date >= (CURRENT_DATE - INTERVAL '{valid_ranges[range]} days')" if valid_ranges[range] else ""
        existing_leaderboard = await self.bot.db.fetchrow("SELECT * FROM activity_leaderboard WHERE guild_id = $1 AND type = $2 AND range = $3", ctx.guild.id, table, range)
        if existing_leaderboard:
            return await ctx.send_warning(f"Leaderboard for **{table}** is already set up.")
        column_name = "voice_time" if table == "voice" else "message_count"
        query = f"""
            SELECT user_id, SUM({column_name}) as value 
            FROM {valid_tables[table]}
            WHERE server_id = $1 {date_condition}
            GROUP BY user_id 
            ORDER BY value DESC 
            LIMIT 10
        """
        top_members = await self.bot.db.fetch(query, ctx.guild.id)
        if not top_members:
            if table == "voice":
                return await ctx.send_warning("No voice data found for the specified range.\n> Make sure you enabled voice tracking and someone has been in a voice channel.")
            elif table == "message":
                return await ctx.send_warning("No message data found for the specified range.\n> Make sure you have messages in the server.")
        formatted_range = range.capitalize() if range != "lifetime" else "Lifetime"
        embed = Embed(
            color=colors.NEUTRAL,
            title=f"{table.capitalize()} Leaderboard [{formatted_range}]",
            description="\n".join(
                f"{getattr(emojis, f'NUMBER_{i+1}', '')} <@{member['user_id']}>: "
                f"**{self.bot.misc.humanize_time(member['value'], True, 'HH-MM-SS') if table == 'voice' else '{:,} messages'.format(member['value'])}**"
                for i, member in enumerate(top_members)
            )
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.set_footer(text="Last updated", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        embed.timestamp = datetime.datetime.now()
        leaderboard_message = await channel.send(embed=embed)
        await self.bot.db.execute(
            "INSERT INTO activity_leaderboard (guild_id, type, range, message_id, channel_id) VALUES ($1, $2, $3, $4, $5)",
            ctx.guild.id, table, range, leaderboard_message.id, channel.id
        )
        return await ctx.send_success(f"Leaderboard for {table} set up in {channel.mention}.")

    @activity_leaderboard.command(name="remove", brief="manage guild", usage="activity leaderboard remove message 30d")
    @has_guild_permissions(manage_guild=True)
    async def activity_leaderboard_remove(self, ctx: EvelinaContext, table: str, range: Optional[str] = "lifetime"):
        """Remove the activity leaderboard for a channel"""
        valid_tables = {"message": "activity_messages", "voice": "activity_voice"}
        if table not in valid_tables:
            return await ctx.send_warning("Invalid table! Please use one of the following: `message` or `voice`")
        valid_ranges = {"1d": 1, "7d": 7, "30d": 30, "lifetime": None}
        if range not in valid_ranges:
            return await ctx.send_warning("Invalid time range! Please use one of the following: `1d`, `7d`, `30d` or `lifetime`")
        check = await self.bot.db.fetchrow(f"SELECT * FROM activity_leaderboard WHERE guild_id = $1 AND type = $2 AND range = $3", ctx.guild.id, table, range)
        if not check:
            return await ctx.send_warning(f"Leaderboard for {table} is not setup")
        await self.bot.db.execute(f"DELETE FROM activity_leaderboard WHERE guild_id = $1 AND type = $2 AND range = $3", ctx.guild.id, table, range)
        return await ctx.send_success(f"Leaderboard for {table} has been removed")

    @activity_leaderboard.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def activity_leaderboard_list(self, ctx: EvelinaContext):
        """List all activity leaderboards for the server"""
        result = await self.bot.db.fetch("SELECT * FROM activity_leaderboard WHERE guild_id = $1", ctx.guild.id)
        if not result:
            return await ctx.send_warning("No leaderboards are setup for this server")
        leaderboards = [f"{str(row['type']).capitalize()} - {row['range']} [`View`](https://discord.com/channels/{ctx.guild.id}/{row['channel_id']}/{row['message_id']})" for row in result]
        return await ctx.paginate(leaderboards, title="Leaderboards", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Utility(bot))