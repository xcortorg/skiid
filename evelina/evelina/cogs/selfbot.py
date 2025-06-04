import io
import re
import uuid
import time
import math
import aiohttp
import random
import yt_dlp
import asyncio
import requests
import datetime
import discord
import openai

from io import BytesIO
from time import time
from urllib.parse import unquote
from PIL import Image, ImageDraw, ImageSequence, UnidentifiedImageError, ImageFont
from typing import Optional, Union, Any
from collections import defaultdict
from datetime import datetime
from deep_translator import GoogleTranslator

from discord import app_commands, Interaction, Embed, File, Message, User, Member, ClientUser, utils, Object, ButtonStyle
from discord.ui import Button, View
from discord.app_commands import AppInstallationType, AppCommandContext
from discord.ext.commands import Cog

from modules import config
from modules.styles import emojis, colors, icons
from modules.evelinabot import Evelina
from modules.misc.views import GunsInfoView
from modules.handlers.lastfm import Handler

class Selfbot(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)
        self.ratelimits = {}
        self.order_messages = {}

    async def get_ratelimit(self, message: Union[Message, Interaction]) -> Optional[int]:
        user_id = message.user.id if isinstance(message, Interaction) else message.author.id
        now = time()
        if user_id in self.ratelimits:
            if now < self.ratelimits[user_id]:
                return self.ratelimits[user_id] - now
        self.ratelimits[user_id] = now + 10
        return None
    
    async def extract_info(self, url, ydl_opts):
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    async def retry_with_backoff(self, func, *args, retries=3, backoff_in_seconds=2):
        for attempt in range(retries):
            try:
                return await func(*args)
            except yt_dlp.utils.ExtractorError as e:
                if attempt < retries - 1:
                    await asyncio.sleep(backoff_in_seconds)
                    backoff_in_seconds *= 2
                else:
                    raise e
                
    async def cache_profile(self, member: User) -> Any:
        if member.banner:
            banner = member.banner.url
        else:
            banner = None
        return await self.bot.cache.set(f"profile-{member.id}", {"banner": banner}, 3600)
    
    async def has_perks(self, interaction: Interaction):
        bot = interaction.client
        user = interaction.user
        if interaction.guild:
            check_premium = await bot.db.fetchrow("SELECT * FROM premium WHERE guild_id = $1", interaction.guild.id)
            if check_premium:
                return True
        check_donor = await bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", user.id)
        check_vote = await bot.db.fetchrow("SELECT * FROM votes WHERE user_id = $1", user.id)
        if check_vote and check_vote["vote_until"] and check_vote["vote_until"] > datetime.now().timestamp():
            return True
        if check_donor:
            return True
        guild = bot.get_guild(self.bot.logging_guild)
        if guild:
            member = guild.get_member(user.id)
            if member:
                role = guild.get_role(1228378828704055366)
                if role and role in member.roles:
                    return True
        await interaction.warn("You need [**donator**](https://evelina.bot/premium) perks or to have [**vote**](https://top.gg/bot/1242930981967757452/vote) to use this command.", ephemeral=True)
        return False
    
    tiktok_group = app_commands.Group(name="tiktok", description="TikTok related commands", allowed_contexts=AppCommandContext(guild=True, dm_channel=True, private_channel=True), allowed_installs=AppInstallationType(guild=True, user=True))

    @tiktok_group.command(name="video", description="Repost a TikTok video")
    @app_commands.describe(url="URL to set:")
    async def tiktok_video(self, interaction: Interaction, url: str):
        """Repost a TikTok video"""
        ctx = await self.bot.get_context(interaction)
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        cooldown = await self.get_ratelimit(interaction)
        if cooldown:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are on cooldown. Please try again later"), ephemeral=True)
        try:
            x = await self.bot.session.get_json("https://api.evelina.bot/tiktok/media", params={"url": url, "key": config.EVELINA})
        except Exception:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Failed to fetch TikTok URL\n> {url}"), ephemeral=True)
        if not isinstance(x, dict):
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Unexpected response format\n> {url}"), ephemeral=True)
        author = x.get("author", {})
        username = author.get("username", "unknown")
        avatar_url = author.get("avatar", "")
        if "images" in x and x["images"]:
            try:
                image_urls = x["images"]
                if not image_urls:
                    return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: No images found in TikTok URL\n> {url}"), ephemeral=True)
                music = x.get("music", "")
                caption = x.get("caption", "no caption")
                likes = x.get("likes", 0)
                comments = x.get("comments", 0)
                shares = x.get("shares", 0)
                views = x.get("views", 0)
                embeds = [
                    Embed(color=colors.TIKTOK, description=f"[{caption}]({url})\n> **Music:** [Download]({music})")
                    .set_author(name=f"{username}", icon_url=f"{avatar_url}", url=f"https://tiktok.com/@{username}")
                    .set_image(url=image_url)
                    .set_footer(text=f"Page: {index + 1}/{len(image_urls)} ・ ❤️ {likes:,}  💬 {comments:,}  🔗 {shares:,}  👀 {views:,} | {interaction.user}")
                    for index, image_url in enumerate(image_urls)
                ]
                if not embeds:
                    return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Error creating embeds from TikTok URL\n> {url}"), ephemeral=True)
                return await ctx.paginator(embeds, author_only=False, interaction=interaction)
            except Exception:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Failed to process TikTok images\n> {url}"), ephemeral=True)
        elif isinstance(x.get("video"), str):
            try:
                video = x["video"]
                music = x.get("music", "")
                file = File(fp=await self.bot.getbyte(video), filename="evelinatiktok.mp4")
                caption = x.get('caption', 'no caption')
                embed = Embed(color=colors.TIKTOK, description=f"[{caption}]({url})\n> **Music:** [Download]({music})"
                ).set_author(name=f"{username}", icon_url=f"{avatar_url}", url=f"https://tiktok.com/@{username}"
                ).set_footer(icon_url=icons.TIKTOK, text=f"❤️ {x['likes']:,}  💬 {x['comments']:,}  🔗 {x['shares']:,}  👀 {x['views']:,} | {interaction.user}")
                return await interaction.followup.send(embed=embed, file=file)
            except Exception:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Failed to send TikTok video\n> {url}"), ephemeral=True)
        else:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't retrieve information about the TikTok URL\n> {url}"), ephemeral=True)

    @tiktok_group.command(name="user", description="Get information about a TikTok user")
    @app_commands.describe(username="Username to set:")
    async def tiktok_user(self, interaction: Interaction, username: str):
        """Gets profile information on the given TikTok user"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        data = await self.bot.session.get_json(f"https://api.tempt.lol/socials/tiktok/{username}", headers={"X-API-KEY": "3BduE1OR97a55xU8Vg-IwfzXI4RoEaRXEHZxJ0Y_2fI"})
        if not data:
            return await interaction.send_warning(f"Couldn't get information about **{username}**")
        else:
            embed = (
                Embed(color=colors.TIKTOK, title=f"{data['nickname']} (@{data['unique_id']})", url=f"https://tiktok.com/@{data['unique_id']}/")
                .set_thumbnail(url=data['avatar_thumb'])
                .add_field(name="Hearts", value=f"{self.humanize_number(data['stats']['heart_count'])}")
                .add_field(name="Following", value=f"{self.humanize_number(data['stats']['following_count'])}")
                .add_field(name="Followers", value=f"{self.humanize_number(data['stats']['follower_count'])}")
                .set_footer(text="TikTok", icon_url=icons.TIKTOK)
            )
            return await interaction.send(embed=embed)

    instagram_group = app_commands.Group(name="instagram", description="Instagram related commands", allowed_contexts=AppCommandContext(guild=True, dm_channel=True, private_channel=True), allowed_installs=AppInstallationType(guild=True, user=True))

    @instagram_group.command(name="video", description="Repost an Instagram video")
    @app_commands.describe(url="URL to set:")
    async def instagram_video(self, interaction: Interaction, url: str):
        """Repost an Instagram video"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        cooldown = await self.get_ratelimit(interaction)
        if cooldown:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are on cooldown. Please try again later"), ephemeral=True)
        await self.process_instagram(interaction, url)
    async def process_instagram(self, interaction: Interaction, url: str):
        api_url = "https://api.evelina.bot/instagram/media"
        x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
        if "video" in x and x["video"].get("video"):
            video = x["video"]["video"]
            file = File(fp=await self.bot.getbyte(video), filename="evelinainstagram.mp4")
            caption = x["video"].get('caption', '')
            description = f"[{caption}]({url})" if caption else ""
            icon_url = None if x['author']['avatar'] == "None" else x['author']['avatar']
            name = None if x['author']['username'] == "None" else x['author']['username']
            url = None if x['author']['username'] == "None" else f"https://instagram.com/{x['author']['username']}"
            embed = Embed(color=colors.INSTAGRAM, description=description
            ).set_author(name=name, icon_url=icon_url, url=url
            ).set_footer(icon_url=icons.INSTAGRAM, text=f"❤️ {x['video']['likes']:,}  💬 {x['video']['comments']:,}  🔗 {x['video']['shares']:,}  👀 {x['video']['views']:,} | {interaction.user}")
            return await interaction.followup.send(embed=embed, file=file)
        else:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't retrieve information about the Instagram URL\n> {url}"), ephemeral=True)

    @instagram_group.command(name="post", description="Repost an Instagram post")
    @app_commands.describe(url="URL to set:")
    async def instagram_post(self, interaction: Interaction, url: str):
        """Repost an Instagram post"""
        ctx = await self.bot.get_context(interaction)
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            data = await self.bot.session.get_json("https://api.evelina.bot/instagram/post", params={"url": url, "key": config.EVELINA})
            author = data.get("author", {})
            username = author.get("username", "unknown")
            display_name = author.get("display", "unknown")
            image_urls = data.get("media", {}).get("urls", [])
            caption = data.get("media", {}).get("caption", "")
            likes = data.get("media", {}).get("likes", 0)
            comments = data.get("media", {}).get("comments", 0)
            post_time = data.get("media", {}).get("time", 0)
            if not image_urls:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while fetching the post from **{url}**"))
            semaphore = asyncio.Semaphore(5)
            tasks = [self.process_instagram_post(image_url, post_time, username, index, len(image_urls), semaphore) for index, image_url in enumerate(image_urls)]
            uploaded_urls = await asyncio.gather(*tasks)
            uploaded_urls = [msg for msg in uploaded_urls if msg]
            if uploaded_urls:
                return await ctx.paginator_content(uploaded_urls, author_only=False, interaction=interaction)
            else:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: No valid posts found for **{url}**"))
        except Exception:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred while fetching the post from **{url}**"))
        
    @instagram_group.command(name="posts", description="Fetch Instagram post from a username")
    @app_commands.describe(username="Username to set:")
    async def instagram_posts(self, interaction: Interaction, username: str):
        """Fetch Instagram post from a username"""
        ctx = await self.bot.get_context(interaction)
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            data = await self.bot.session.get_json("https://api.evelina.bot/instagram/posts", params={"username": username, "key": config.EVELINA})
            items = data.get("items", [])
            if not items:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get posts from **{username}**"))
            embeds = []
            total_posts = len(items)
            for index, item in enumerate(items):
                author = item.get("author", {})
                username = author.get("username", "unknown")
                display_name = author.get("display", "unknown")
                avatar_url = author.get("avatar", "")
                caption = item.get("caption", "")
                code = item.get("code", "")
                likes = item.get("likes", 0)
                comments = item.get("comments", 0)
                media = item.get("media", [])
                if not media:
                    continue
                total_slides = len(media)
                for media_index, media_item in enumerate(media):
                    if media_item.get("type") == "image":
                        image_url = media_item.get("url")
                        embed = Embed(color=colors.INSTAGRAM, description=f"[{caption}](https://instagram.com/p/{code})")
                        embed.set_author(name=f"{username}", icon_url=f"{avatar_url}", url=f"https://instagram.com/{username}")
                        embed.set_image(url=image_url)
                        embed.set_footer(text=f"Post {index + 1}/{total_posts} ・ Slide {media_index + 1}/{total_slides} ・ ❤️ {likes:,}  💬 {comments:,} | {interaction.user.name}")
                        embeds.append(embed)
            if not embeds:
                return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Error fetching information from the Instagram URL."))
            return await ctx.paginator(embeds, author_only=False, interaction=interaction)
        except Exception:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get images from **{username}**"))

    @instagram_group.command(name="story", description="Gets all current stories for the given Instagram user")
    @app_commands.describe(username="Username to set:")
    async def instagram_story(self, interaction: Interaction, username: str):
        """Gets all current stories for the given Instagram user"""
        ctx = await self.bot.get_context(interaction)
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            data = await self.bot.session.get_json("https://api.evelina.bot/instagram/story", params={"username": username.lower(), "key": config.EVELINA})
            story_urls = data.get("stories", {}).get("urls", [])
            story_times = data.get("stories", {}).get("times", [])
            author = data.get("author", {}).get("username", "unknown")
            if not story_urls or not story_times:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get stories from **{username}** - no stories found.")
                return await interaction.followup.send(embed=embed)
            if len(story_urls) != len(story_times):
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Mismatch between story URLs and times.")
                return await interaction.followup.send(embed=embed)
            semaphore = asyncio.Semaphore(5)
            tasks = [self.process_story(url, timestamp_str, author, index, len(story_urls), semaphore) for index, (url, timestamp_str) in enumerate(zip(story_urls, story_times))]
            uploaded_urls = await asyncio.gather(*tasks)
            uploaded_urls = [msg for msg in uploaded_urls if msg]
            if uploaded_urls:
                return await ctx.paginator_content(uploaded_urls, author_only=False, interaction=interaction)
            else:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: No valid stories found for **{username}**")
                return await interaction.followup.send(embed=embed)
        except Exception:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get stories from **{username}**"))

    async def process_story(self, session: aiohttp.ClientSession, url: str, timestamp_str: str, author: str, index: int, total_stories: int, semaphore: asyncio.Semaphore) -> str:
        async with semaphore:
            try:
                timestamp = int(timestamp_str)
                r2_url = await self.upload_to_r2(url, session, author)
                if not r2_url:
                    return None
                message_content = f"**@{author}** — Posted <t:{timestamp}:R>\n({index + 1}/{total_stories}) {r2_url}"
                return message_content
            except Exception:
                return None
            
    async def process_instagram_post(self, session: aiohttp.ClientSession, image_url: str, post_time: int, username: str, index: int, total_images: int, semaphore: asyncio.Semaphore) -> str:
        async with semaphore:
            try:
                r2_url = await self.upload_to_r2(image_url, session, username)
                if not r2_url:
                    return None
                message_content = (
                    f"**@{username}** — Posted <t:{int(post_time)}:R>\n"
                    f"({index + 1}/{total_images}) {r2_url}\n"
                )
                return message_content
            except Exception as e:
                return None

    @instagram_group.command(name="user", description="Get information about an Instagram user")
    @app_commands.describe(username="Username to set:")
    async def instagram_user(self, interaction: Interaction, username: str):
        """Gets profile information on the given Instagram user"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        data = await self.bot.session.get_json(f"https://api.evelina.bot/instagram/user?username={username.lower()}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get information about **{username}**"), ephemeral=True)
        embed = (
            discord.Embed(color=colors.INSTAGRAM, title=f"{data['full_name']} (@{data['username']}){' ' + emojis.CHECKMARK if data['is_verified'] else ''}", url=f"https://instagram.com/{data['username']}/", description=data['bio'])
            .set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            .set_thumbnail(url=data['profile_pic'])
            .add_field(name="Posts", value=f"{data['posts']:,}")
            .add_field(name="Following", value=f"{data['following']:,}")
            .add_field(name="Followers", value=f"{data['followers']:,}")
            .set_footer(text="Instagram", icon_url=icons.INSTAGRAM)
        )
        return await interaction.followup.send(embed=embed)

    snapchat_group = app_commands.Group(name="snapchat", description="Snapchat related commands", allowed_contexts=AppCommandContext(guild=True, dm_channel=True, private_channel=True), allowed_installs=AppInstallationType(guild=True, user=True))

    @snapchat_group.command(name="video", description="Repost a Snapchat video")
    @app_commands.describe(url="URL to set:")
    async def snapchat_video(self, interaction: Interaction, url: str):
        """Repost a Snapchat video"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        cooldown = await self.get_ratelimit(interaction)
        if cooldown:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are on cooldown. Please try again later"), ephemeral=True)
        await self.process_snapchat(interaction, url)
    async def process_snapchat(self, interaction: Interaction, url: str):
        api_url = "https://api.evelina.bot/snapchat/media"
        x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
        if "video" in x and x["video"].get("video"):
            video = x["video"]["video"]
            file = File(fp=await self.bot.getbyte(video), filename="evelinasnapchat.mp4")
            caption = x["video"].get('caption', '')
            views = int(x["video"].get('views', 0))
            description = f"[{caption}]({url})" if caption else ""
            embed = Embed(color=colors.SNAPCHAT, description=description
            ).set_author(name=f"{x['author']['username']}", url=f"https://snapchat.com/add/{x['author']['username']}"
            ).set_footer(icon_url=icons.SNAPCHAT, text=f"👀 {views:,} | {interaction.user}")
            return await interaction.followup.send(embed=embed, file=file)
        else:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't retrieve information about the Snapchat URL\n> {url}"), ephemeral=True)

    @snapchat_group.command(name="user", description="Get information about a Snapchat user")
    @app_commands.describe(username="Username to set:")
    async def snapchat_user(self, interaction: Interaction, username: str):
        """Get bitmoji and QR scan code for user"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        data = await self.bot.session.get_json("https://api.evelina.bot/snapchat/user", params={"username": username, "key": "8F6qVxN55aoODT0FRh16pydP"})
        if 'message' in data:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get information about **{username}**"), ephemeral=True)
        embed = (
            discord.Embed(color=colors.SNAPCHAT, title=f"{data['display_name']} (@{data['username']})", url=data['url'], description=data.get('bio', 'No bio available'))
            .set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            .set_thumbnail(url=data['avatar'])
            .set_footer(text="Snapchat", icon_url=icons.SNAPCHAT)
        )
        button = discord.ui.Button(label="Snapcode")
        async def button_callback(interaction: discord.Interaction):
            e = discord.Embed(color=0xFFFF00)
            e.set_image(url=data['snapcode'])
            return await interaction.response.send_message(embed=e, ephemeral=True)
        button.callback = button_callback
        view = discord.ui.View()
        view.add_item(button)
        return await interaction.followup.send(embed=embed, view=view)

    twitter_group = app_commands.Group(name="twitter", description="Twitter related commands", allowed_contexts=AppCommandContext(guild=True, dm_channel=True, private_channel=True), allowed_installs=AppInstallationType(guild=True, user=True))

    @twitter_group.command(name="video", description="Repost a Twitter video")
    @app_commands.describe(url="URL to set:")
    async def twitter_video(self, interaction: Interaction, url: str):
        """Repost a Twitter video"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        cooldown = await self.get_ratelimit(interaction)
        if cooldown:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are on cooldown. Please try again later"), ephemeral=True)
        await self.process_twitter(interaction, url)
    async def process_twitter(self, interaction: Interaction, url: str):
        api_url = "https://api.evelina.bot/twitter/media"
        x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
        if "video" in x and x["video"].get("video"):
            video = x["video"]["video"]
            file = File(fp=await self.bot.getbyte(video), filename="evelinatwitter.mp4")
            caption = x["video"].get('caption', '')
            description = f"[{caption}]({url})" if caption else ""
            embed = Embed(color=colors.TWITTER, description=description,
            ).set_author(name=f"{x['author']['username']}", icon_url=f"{x['author']['avatar']}", url=f"https://twitter.com/{x['author']['username']}"
            ).set_footer(icon_url=icons.TWITTER, text=f"🔖 {x['video']['saves']:,} | {interaction.user}")
            return await interaction.followup.send(embed=embed, file=file)
        else:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't retrieve information about the Twitter URL\n> {url}"), ephemeral=True)

    @twitter_group.command(name="user", description="Get information about a Twitter user")
    @app_commands.describe(username="Username to set:")
    async def twitter_user(self, interaction: Interaction, username: str):
        """Gets profile information on the given Twitter user"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)  
        data = await self.bot.session.get_json(f"https://api.evelina.bot/twitter/user?username={username.lower()}&key=X3pZmLq82VnHYTd6Cr9eAw")
        if 'message' in data:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get information about **{username}**"), ephemeral=True)
        if data['username'] is None:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Account **{username}** is suspended or doesn't exist"), ephemeral=True)
        original_date_str = data.get('created_at')
        if original_date_str:
            date_obj = datetime.strptime(original_date_str, '%a %b %d %H:%M:%S %z %Y')
            formatted_date_str = date_obj.strftime('%d %b. %Y %H:%M')
        else:
            formatted_date_str = "N/A"
        embed = (
            discord.Embed(color=colors.TWITTER, title=f"{data['full_name']} (@{data['username']}){' ' + emojis.CHECKMARK if data['is_verified'] else ''}", url=f"https://twitter.com/{data['username']}/", description=data['bio'])
            .set_author(name=interaction.user.name, icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
            .set_thumbnail(url=data['profile_pic'])
            .add_field(name="Tweets", value=f"{data['posts']:,}")
            .add_field(name="Following", value=f"{data['following']:,}")
            .add_field(name="Followers", value=f"{data['followers']:,}")
            .set_footer(text=f"{formatted_date_str}", icon_url=icons.TWITTER)
        )
        try:
            return await interaction.response.send_message(embed=embed)
        except Exception:
            pass

    pinterest_group = app_commands.Group(name="pinterest", description="Pinterest related commands", allowed_contexts=AppCommandContext(guild=True, dm_channel=True, private_channel=True), allowed_installs=AppInstallationType(guild=True, user=True))

    @pinterest_group.command(name="video", description="Repost a Pinterest video")
    @app_commands.describe(url="URL to set:")
    async def pinterest_video(self, interaction: Interaction, url: str):
        """Repost a Pinterest video"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        cooldown = await self.get_ratelimit(interaction)
        if cooldown:
            return await interaction.followup.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are on cooldown. Please try again later"), ephemeral=True)
        try:
            x = await self.bot.session.get_json("https://api.evelina.bot/pinterest/media", params={"url": url, "key": config.EVELINA})
            if x['type'] == 'image':
                file = File(fp=await self.bot.getbyte(x['data']['url']), filename="evelinapinterest.png")
                description = f"[{x['data']['title']}]({url})" if x['data']['title'] else ""
                embed = Embed(color=colors.PINTEREST, description=description,
                ).set_footer(icon_url=icons.PINTEREST, text=f"{interaction.user}")
                return await interaction.followup.send(embed=embed, file=file)
            elif x['type'] == 'video':
                file = File(fp=await self.bot.getbyte(x['data']['url']), filename="evelinapinterest.mp4")
                description = f"[{x['data']['title']}]({url})" if x['data']['title'] else ""
                embed = Embed(color=colors.PINTEREST, description=description,
                ).set_footer(icon_url=icons.PINTEREST, text=f"{interaction.user}")
                return await interaction.followup.send(embed=embed, file=file)
            else:
                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't get information about {url}")
                return await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Failed to fetch Pinterest URL\n> {url}")
            return await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command()
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(user="User to set:")
    async def avatar(self, interaction: Interaction, user: User = None) -> None:
        """Get avatar of a user or yourself"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if user is None:
            user = interaction.user
        embed = Embed(color=await self.bot.misc.dominant_color(user.avatar.url if user.avatar else user.default_avatar.url), title=f"{user.name}'s avatar", url=user.avatar.url if user.avatar else user.default_avatar.url)
        embed.set_image(url=user.avatar.url if user.avatar else user.default_avatar.url)
        try:
            return await interaction.response.send_message(embed=embed)
        except Exception:
            pass

    @app_commands.command()
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(user="User to set:")
    async def banner(self, interaction: Interaction, user: User = None) -> None:
        """Get the banner of a user or yourself"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if user is None:
            user = interaction.user
        cache = await self.bot.cache.get(f"profile-{user.id}")
        if cache:
            banner = cache["banner"]
            if banner is None:
                return await interaction.warn(f"{'You don' if user.id == user.id else f'{user.mention} doesn'}'t have a banner")
        else:
            user = await self.bot.fetch_user(user.id)
            if not user.banner:
                await self.cache_profile(user)
                return await interaction.warn(f"{'You don' if user.id == user.id else f'{user.mention} doesn'}'t have a banner")
            banner = user.banner.url
        embed = Embed(color=await self.bot.misc.dominant_color(banner), title=f"{user.name}'s banner", url=banner)
        embed.set_image(url=banner)
        try:
            return await interaction.response.send_message(embed=embed)
        except Exception:
            pass

    @app_commands.command()
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(user="User to set:")
    async def userinfo(self, interaction: Interaction, user: User = None):
        """View information about a user or yourself"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if user is None:
            user = interaction.user
        badges = await self.bot.misc.get_badges(user)
        description = ""
        if badges:
            description += f" {badges}"
        embed = (
            Embed(color=await self.bot.misc.dominant_color(user.avatar.url if user.avatar else user.default_avatar.url), description=description)
            .set_author(name=f"{user.name} ({user.id})", icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
            .set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            .add_field(name="Created", value=f"{utils.format_dt(user.created_at, style='D')}\n{utils.format_dt(user.created_at, style='R')}")
        )
        if isinstance(user, Member):
            if interaction.guild.chunked:
                members = sorted(interaction.guild.members, key=lambda m: m.joined_at)
                if user in members:
                    join_position = members.index(user) + 1
                else:
                    join_position = "N/A"
            else:
                join_position = "N/A"
            if not isinstance(user, ClientUser):
                join_position_text = f"{join_position}" if isinstance(join_position, int) else join_position
                embed.set_footer(text=f"Join position: {join_position_text} • {len(user.mutual_guilds):,} server(s)")
            embed.add_field(name="Joined", value=f"{utils.format_dt(user.joined_at, style='D')}\n{utils.format_dt(user.joined_at, style='R')}")
            if user.premium_since:
                embed.add_field(name="Boosted", value=f"{utils.format_dt(user.premium_since, style='D')}\n{utils.format_dt(user.premium_since, style='R')}")
            roles = user.roles[1:][::-1]
            if len(roles) > 0:
                embed.add_field(name=f"Roles", value=(" ".join([r.mention for r in roles]) if len(roles) < 5 else " ".join([r.mention for r in roles[:4]]) + f" ... and {len(roles)-4} more"), inline=False)
        try:
            return await interaction.response.send_message(embed=embed)
        except Exception:
            pass

    @app_commands.command()
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(amount="Amount to set:", from_currency="Currency to set:", to_currency="Currency to set:")
    async def crypto(self, interaction: Interaction, amount: float, from_currency: str, to_currency: str) -> None:
        """Convert cryptocurrency to a specified currency"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            data = await self.bot.session.get_json(f"https://api.evelina.bot/crypto?amount={amount}&from={from_currency}&to={to_currency}&key=X3pZmLq82VnHYTd6Cr9eAw")
            if data["status"] == "success":
                amount_from = data.get(from_currency.upper(), 'N/A')
                amount_to = data.get(to_currency.upper(), 'N/A')
                view = self.CryptoConversionView(amount_to)
                return await interaction.response.send_message(embed=Embed(color=colors.EXCHANGE, description=f"{emojis.EXCHANGE} {interaction.user.mention} {amount_from} **{from_currency.upper()}** is {amount_to} **{to_currency.upper()}**"), view=view)
            else:
                return await interaction.warn("Failed to retrieve conversion data. Please check the currency codes.")
        except Exception:
            return await interaction.warn("An error occurred while retrieving conversion data.")
        
    class CryptoConversionView(View):
        def __init__(self, amount_to: str):
            super().__init__()
            self.amount_to = amount_to

        @discord.ui.button(label="Copy Amount", style=discord.ButtonStyle.primary)
        async def get_conversion_details(self, interaction: Interaction, button: Button):
            await interaction.response.send_message(self.amount_to, ephemeral=True)

    @app_commands.command()
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(language="Language to set:", message="Message to set:")
    async def translate(self, interaction: Interaction, language: str, message: str):
        """Translate a message to a specific language"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if message is None:
            if interaction.message.reference is not None:
                replied_message = await interaction.channel.fetch_message(interaction.message.reference.message_id)
                message = replied_message.content
        if message is None:
            await interaction.response.send_message("You need to provide a message or reply to a message to translate.", ephemeral=True)
            return
        try:
            translator = GoogleTranslator(source="auto", target=language)
            translated = await asyncio.to_thread(translator.translate, message)
            embed = Embed(color=colors.NEUTRAL, title=f"Translated to {language}", description=f"```{translated}```")
            try:
                return await interaction.response.send_message(embed=embed)
            except Exception:
                pass
        except Exception:
            return await interaction.warn(f"This language is **not** supported.\n> Use **language codes** like `en`, `de` or `fr`")
        
    @app_commands.command()
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(user="User to set:")
    async def avatarhistory(self, interaction: Interaction, *, user: User = None) -> None:
        """Check a member's avatar history"""
        await interaction.response.defer()
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if user is None:
            user = interaction.user
        results = await self.bot.db.fetch("SELECT avatar FROM avatar_history WHERE user_id = $1", int(user.id))
        if not results:
            does = "don't" if user == interaction.user else "doesn't"
            return await interaction.warn(f"{'You' if user == interaction.user else user.mention} {does} have an **avatar history**")
        base_url = "https://cdn.evelina.bot/avatars/"
        avatar_urls = [f"{base_url}{record['avatar']}" for record in results]
        max_avatars = 20
        avatar_urls = avatar_urls[:max_avatars]
        image_bytes_list = []
        for url in avatar_urls:
            image_bytes = await self.bot.session.get_bytes(url)
            image_bytes_list.append(image_bytes)
        collage_image_bytes = await self.bot.misc.create_collage(image_bytes_list)
        file = discord.File(fp=collage_image_bytes, filename="avatar_collage.png")
        embed = discord.Embed(
            color=colors.NEUTRAL,
            title=f"{user.name}'s Avatar History",
            description=f"Showing **{len(image_bytes_list)}** from **{len(results)}** pictures\n> Click [**here**](https://evelina.bot/avatars/{user.id}) to get the **full** list"
        )
        embed.set_author(name=f"{interaction.user.name}", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.set_image(url="attachment://avatar_collage.png")
        return await interaction.followup.send(embed=embed, file=file)

    @app_commands.command(name="calculate", description="Calculate a mathematical expression")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(expression="Expression to set:")
    async def calculate(self, interaction: Interaction, *, expression: str):
        """Calculate a mathematical expression"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            original_expression = expression
            expression = re.sub(r'(\d+(\.\d+)?)(\s*[-+/*]\s*)(\d+(\.\d+)?)%', r'\1\3(\1 * \4 / 100)', expression)
            result = eval(expression, {"__builtins__": None}, {"sqrt": math.sqrt, "pow": math.pow, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi, "e": math.e})
            embed = Embed(color=colors.NEUTRAL, description=f"{interaction.user.mention}: Result of **{original_expression}** is **{result}**")
            try:
                return await interaction.response.send_message(embed=embed)
            except Exception:
                pass
        except Exception:
            return await interaction.warn(f"An error occurred while calculating the expression")

    guns_group = app_commands.Group(name="guns", description="Guns related commands", allowed_contexts=AppCommandContext(guild=True, dm_channel=True, private_channel=True), allowed_installs=AppInstallationType(guild=True, user=True))

    @guns_group.command(name="user", description="Get profile information on the given Guns.lol user")
    @app_commands.describe(username="Username to set:")
    async def guns_user(self, interaction: Interaction, *, username: str):
        """Gets profile information on the given Guns.lol user"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        data = await self.bot.session.get_json("https://api.evelina.bot/guns/user", params={"username": username, "key": config.EVELINA})
        if 'message' in data:
            return await interaction.warn(f"Couldn't get information about Guns user **{username}**")
        display_name = data["config"].get("display_name", "Unknown")
        username = data.get("username", "Unknown")
        description = data["config"].get("description", "No description provided")
        discord_id = f"> Owned by <@{data['discord']['id']}>" if "discord" in data else ''
        page_views = data["config"].get("page_views", "Unknown")
        uid_value = data.get("uid", "Unknown")
        account_created = data.get("account_created", "Unknown")
        alias = data.get("alias", None)
        avatar_url = data["config"].get("avatar", None)
        if avatar_url == "":
            discord_avatars = data["discord"]['avatar'] if "discord" in data else []
            if len(discord_avatars) > 0:
                avatar_url = discord_avatars[0]
            else:
                avatar_url = None
        background_url = data["config"].get("url", None)
        audio_url = data["config"].get("audio", None)
        custom_cursor = data["config"].get("custom_cursor", None)
        user_badges = data["config"].get("user_badges", [])
        badge_emojis = {
            "bughunter": emojis.GUNS_BUGHUNTER,
            "donor": emojis.GUNS_DONOR,
            "imagehost_access": emojis.GUNS_IMAGEHOST_ACCESS,
            "og": emojis.GUNS_OG,
            "premium": emojis.GUNS_PREMIUM,
            "server_booster": emojis.GUNS_SERVER_BOOSTER,
            "staff": emojis.GUNS_STAFF,
            "verified": emojis.GUNS_VERIFIED,
            "christmas_2024": emojis.GUNS_CHRISTMAS_2024,
            "winner": emojis.GUNS_WINNER,
            "second": emojis.GUNS_SECOND,
            "third": emojis.GUNS_THIRD
        }
        if user_badges:
            if isinstance(user_badges[0], dict):
                enabled_badges = [badge['name'] for badge in user_badges if badge.get('enabled', False)]
            elif isinstance(user_badges[0], str):
                enabled_badges = user_badges
            else:
                enabled_badges = []
            badges = ' '.join([badge_emojis.get(badge, '') for badge in enabled_badges if isinstance(badge, str) and badge in badge_emojis])
        else:
            badges = None
        embed = (
            discord.Embed(
                color=colors.NEUTRAL,
                title=f"{display_name} (@{username})",
                description=f"{f'{badges}' if badges else ''}\n{description}\n{discord_id}",
                url=f"https://guns.lol/{username}"
            )
            .add_field(name="Account Creation", value=f"<t:{account_created}:R>")
            .set_footer(text=f"Views: {page_views:,} ● UID {uid_value:,}", icon_url=icons.GUNS)
        )
        if alias:
            embed.add_field(name="Alias", value=alias)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
            embed.add_field(name="Avatar", value=f"[Click here]({avatar_url})")
        if background_url:
            embed.set_image(url=background_url)
            embed.add_field(name="Background", value=f"[Click here]({background_url})")
        if custom_cursor:
            embed.add_field(name="Cursor", value=f"[Click here]({custom_cursor})")
        if audio_url:
            if isinstance(audio_url, str):
                embed.add_field(name="Audio", value=f"[Click here]({audio_url})")
            elif isinstance(audio_url, list):
                selected_audios = [audio for audio in audio_url]
                if selected_audios:
                    audio_field_value = ", ".join([f"[{audio['title']}]({audio['url']})" for i, audio in enumerate(selected_audios)])
                    embed.add_field(name="Audio", value=audio_field_value, inline=False)
        view = GunsInfoView(self.bot, data)
        await interaction.response.send_message(embed=embed, view=view)

    @guns_group.command(name="uid", description="Get profile information on the given Guns.lol UID")
    @app_commands.describe(uid="UID to set:")
    async def guns_uid(self, interaction: Interaction, *, uid: str):
        """Gets profile information on the given Guns.lol UID"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        data = await self.bot.session.get_json("https://api.evelina.bot/guns/uid", params={"id": uid, "key": config.EVELINA})
        if 'message' in data:
            return await interaction.warn(f"Couldn't get information about Guns UID **{uid}**")
        display_name = data["config"].get("display_name", "Unknown")
        username = data.get("username", "Unknown")
        description = data["config"].get("description", "No description provided")
        discord_id = f"> Owned by <@{data['discord']['id']}>" if "discord" in data else ''
        page_views = data["config"].get("page_views", "Unknown")
        uid_value = data.get("uid", "Unknown")
        account_created = data.get("account_created", "Unknown")
        alias = data.get("alias", None)
        avatar_url = data["config"].get("avatar", None)
        if avatar_url == "":
            discord_avatars = data["discord"]['avatar'] if "discord" in data else []
            if len(discord_avatars) > 0:
                avatar_url = discord_avatars[0]
            else:
                avatar_url = None
        background_url = data["config"].get("url", None)
        audio_url = data["config"].get("audio", None)
        custom_cursor = data["config"].get("custom_cursor", None)
        user_badges = data["config"].get("user_badges", [])
        badge_emojis = {
            "bughunter": emojis.GUNS_BUGHUNTER,
            "donor": emojis.GUNS_DONOR,
            "imagehost_access": emojis.GUNS_IMAGEHOST_ACCESS,
            "og": emojis.GUNS_OG,
            "premium": emojis.GUNS_PREMIUM,
            "server_booster": emojis.GUNS_SERVER_BOOSTER,
            "staff": emojis.GUNS_STAFF,
            "verified": emojis.GUNS_VERIFIED,
            "christmas_2024": emojis.GUNS_CHRISTMAS_2024,
            "winner": emojis.GUNS_WINNER,
            "second": emojis.GUNS_SECOND,
            "third": emojis.GUNS_THIRD
        }
        if user_badges:
            if isinstance(user_badges[0], dict):
                enabled_badges = [badge['name'] for badge in user_badges if badge.get('enabled', False)]
            elif isinstance(user_badges[0], str):
                enabled_badges = user_badges
            else:
                enabled_badges = []
            badges = ' '.join([badge_emojis.get(badge, '') for badge in enabled_badges if isinstance(badge, str) and badge in badge_emojis])
        else:
            badges = None
        embed = (
            discord.Embed(
                color=colors.NEUTRAL,
                title=f"{display_name} (@{username})",
                description=f"{f'{badges}' if badges else ''}\n{description}\n{discord_id}",
                url=f"https://guns.lol/{username}"
            )
            .add_field(name="Account Creation", value=f"<t:{account_created}:R>")
            .set_footer(text=f"Views: {page_views:,} ● UID {uid_value:,}", icon_url=icons.GUNS)
        )
        if alias:
            embed.add_field(name="Alias", value=alias)
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)
            embed.add_field(name="Avatar", value=f"[Click here]({avatar_url})")
        if background_url:
            embed.set_image(url=background_url)
            embed.add_field(name="Background", value=f"[Click here]({background_url})")
        if custom_cursor:
            embed.add_field(name="Cursor", value=f"[Click here]({custom_cursor})")
        if audio_url:
            if isinstance(audio_url, str):
                embed.add_field(name="Audio", value=f"[Click here]({audio_url})")
            elif isinstance(audio_url, list):
                selected_audios = [audio for audio in audio_url]
                if selected_audios:
                    audio_field_value = ", ".join([f"[{audio['title']}]({audio['url']})" for i, audio in enumerate(selected_audios)])
                    embed.add_field(name="Audio", value=audio_field_value, inline=False)
        view = GunsInfoView(self.bot, data)
        await interaction.response.send_message(embed=embed, view=view)

    tags_group = app_commands.Group(name="tags", description="Tag related commands", allowed_contexts=AppCommandContext(guild=True, dm_channel=True, private_channel=True), allowed_installs=AppInstallationType(guild=True, user=True))

    @tags_group.command(name="create", description="Create a new tag")
    @app_commands.describe(name="Name to set:")
    @app_commands.describe(response="Content to set:")
    async def tag_create(self, interaction: Interaction, name: str, response: str):
        """Create a new tag"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if len(name.lower()) > 10:
            return await interaction.warn("Tag name must be less than 10 characters")
        if len(response) > 2000:
            return await interaction.warn("Tag response must be less than 2000 characters")
        check = await self.bot.db.fetch("SELECT * FROM tags_user WHERE name = $1 AND user_id = $2", name.lower(), interaction.user.id)
        if check:
            return await interaction.warn(f"Tag **{name.lower()}** already exists")
        await self.bot.db.execute("INSERT INTO tags_user (user_id, name, response) VALUES ($1, $2, $3)", interaction.user.id, name.lower(), response)
        await interaction.approve(f"Tag **{name.lower()}** created successfully\n```{response}```")

    @tags_group.command(name="delete", description="Delete a tag")
    @app_commands.describe(name="Name to set:")
    async def tag_delete(self, interaction: Interaction, name: str):
        """Delete a tag"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        check = await self.bot.db.fetch("SELECT * FROM tags_user WHERE name = $1 AND user_id = $2", name.lower(), interaction.user.id)
        if not check:
            return await interaction.warn(f"Tag **{name.lower()}** doesn't exist")
        await self.bot.db.execute("DELETE FROM tags_user WHERE name = $1 AND user_id = $2", name.lower(), interaction.user.id)
        await interaction.approve(f"Tag **{name.lower()}** deleted successfully")

    @tag_delete.autocomplete("name")
    async def tag_delete_autocomplete(self, interaction: Interaction, current: str):
        entries = await interaction.client.db.fetch("SELECT name FROM tags_user WHERE user_id = $1", interaction.user.id)
        if not entries:
            return [app_commands.Choice(name="No tag found", value="none")]
        current_lower = current.lower()
        choices = [
            app_commands.Choice(name=entry["name"], value=entry["name"])
            for entry in entries
            if current_lower in entry["name"].lower()
        ]
        return choices[:25]

    @tags_group.command(name="edit", description="Edit a tag")
    @app_commands.describe(name="Name to set:")
    @app_commands.describe(response="Content to set:")
    async def tag_edit(self, interaction: Interaction, name: str, response: str):
        """Edit a tag"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        check = await self.bot.db.fetch("SELECT * FROM tags_user WHERE name = $1 AND user_id = $2", name.lower(), interaction.user.id)
        if not check:
            return await interaction.warn(f"Tag **{name.lower()}** doesn't exist")
        await self.bot.db.execute("UPDATE tags_user SET response = $1 WHERE name = $2 AND user_id = $3", response, name.lower(), interaction.user.id)
        await interaction.approve(f"Tag **{name.lower()}** edited successfully\n```{response}```")

    @tag_edit.autocomplete("name")
    async def tag_edit_autocomplete(self, interaction: Interaction, current: str):
        entries = await interaction.client.db.fetch("SELECT name FROM tags_user WHERE user_id = $1", interaction.user.id)
        if not entries:
            return [app_commands.Choice(name="No tag found", value="none")]
        current_lower = current.lower()
        choices = [
            app_commands.Choice(name=entry["name"], value=entry["name"])
            for entry in entries
            if current_lower in entry["name"].lower()
        ]
        return choices[:25]

    @app_commands.command(name="tag", description="View a tag")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(name="Name to set:")
    async def tag(self, interaction: Interaction, name: str):
        """View a tag"""
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        tag = await self.bot.db.fetchrow("SELECT * FROM tags_user WHERE name = $1 AND user_id = $2", name.lower(), interaction.user.id)
        if not tag:
            return await interaction.response.send_message(f"Tag **{name.lower()}** doesn't exist", ephemeral=True)
        x = await self.bot.embed_build.alt_convert(interaction.user, tag["response"])
        await interaction.response.send_message(**x)

    @tag.autocomplete("name")
    async def tag_autocomplete(self, interaction: Interaction, current: str):
        entries = await interaction.client.db.fetch("SELECT name FROM tags_user WHERE user_id = $1", interaction.user.id)
        if not entries:
            return [app_commands.Choice(name="No tag found", value="none")]
        current_lower = current.lower()
        choices = [
            app_commands.Choice(name=entry["name"], value=entry["name"])
            for entry in entries
            if current_lower in entry["name"].lower()
        ]
        return choices[:25]
    
    async def upload_to_r2(self, url: str, session: aiohttp.ClientSession, author: str) -> str:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    content_type = resp.headers.get('Content-Type')
                    if 'image' in content_type:
                        file_extension = 'png'
                    elif 'video' in content_type:
                        file_extension = 'mp4'
                    else:
                        return None
                    file_data = await resp.read()
                    file_name = f"{str(uuid.uuid4())[:8]}.{file_extension}"
                    upload_res = await self.bot.r2.upload_file("evelina-media", file_data, file_name, content_type)
                    file_url = f"https://m.evelina.bot/{file_name}"
                    return file_url
                else:
                    return None
        except Exception:
            return None
        
    @app_commands.command(name="ship", description="Check the ship rate between you and a member")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(member="Member to set:", partner="Partner to set:")
    async def ship(self, interaction: Interaction, member: User, partner: User = None):
        if await interaction.client.db.fetchrow("SELECT reason FROM blacklist_user WHERE user_id = $1", interaction.user.id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are blacklisted from using **{interaction.client.user.mention}**")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if partner and (partner == member):
            return await interaction.warn("You can't ship the same person twice")
        if (member == interaction.user and partner == interaction.user):
            return await interaction.warn("You can't ship yourself with yourself")
        if not partner:
            if member == interaction.user:
                return await interaction.warn("You can't ship yourself")
            else:
                partner = interaction.user
        ship_percentage = random.randrange(101)
        progress_bar = self.create_progress_bar(ship_percentage)
        image_path = self.create_ship_image(member.avatar.url if member.avatar else member.default_avatar.url, partner.avatar.url if partner.avatar else partner.default_avatar.url, ship_percentage)
        with open(image_path, "rb") as image_file:
            file = File(image_file, filename="ship.png")
            embed = Embed(color=0xFF819F, description=f"**{member.name}** 💞 **{partner.name}**\n**{ship_percentage}%** {progress_bar}")
            embed.set_image(url=f"attachment://ship.png")
            return await interaction.response.send_message(embed=embed, file=file)

    def create_progress_bar(self, percentage):
        filled_blocks = percentage // 8
        half_block = 1 if percentage % 8 >= 4 and filled_blocks > 0 else 0
        empty_blocks = 12 - filled_blocks - half_block
        if filled_blocks > 0:
            progress_bar = f"{emojis.FULLLEFT}"
        else:
            progress_bar = f"{emojis.EMPTYLEFT}"
        progress_bar += f"{emojis.FULL}" * filled_blocks  
        if half_block:
            progress_bar += f"{emojis.HALF}"
        progress_bar += f"{emojis.EMPTY}" * empty_blocks  
        progress_bar += f"{emojis.FULLRIGHT}" if filled_blocks + half_block == 13 else f"{emojis.EMPTYRIGHT}"
        return progress_bar

    def create_ship_image(self, member_avatar, partner_avatar, ship_percentage):
        avatar1 = Image.open(BytesIO(requests.get(str(member_avatar)).content)).convert("RGBA")
        avatar2 = Image.open(BytesIO(requests.get(str(partner_avatar)).content)).convert("RGBA")
        avatar_size = (125, 125)
        avatar1 = avatar1.resize(avatar_size, Image.LANCZOS)
        avatar2 = avatar2.resize(avatar_size, Image.LANCZOS)
        mask = Image.new("L", avatar_size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, avatar_size[0], avatar_size[1]), fill=255)
        avatar1.putalpha(mask)
        avatar2.putalpha(mask)
        file_brokenheart = "data/images/brokenheart.png"
        file_heart = "data/images/heart.png"
        heart_path = file_brokenheart if ship_percentage < 50 else file_heart
        heart = Image.open(heart_path).convert("RGBA")
        heart = heart.resize((75, 75), Image.LANCZOS)
        background = Image.new("RGBA", (280, 125), (255, 255, 255, 0))
        background.paste(avatar1, (0, 0), avatar1)
        background.paste(avatar2, (156, 0), avatar2)
        heart_x = (background.width - heart.width) // 2
        heart_y = (background.height - heart.height) // 2
        background.paste(heart, (heart_x, heart_y), heart)
        output_path = "data/images/tmp/ship.png"
        background.save(output_path, format="PNG")
        return output_path
    
    @app_commands.command(name="deeplookup", description="Deep lookup a user")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(user="User to set:")
    async def deeplookup(self, interaction: Interaction, user: User = None):
        """Deep lookup a member"""
        ctx = await self.bot.get_context(interaction)
        if not await self.has_perks(interaction):
            return
        if user is None:
            user = interaction.user
        if user.id in self.bot.owner_ids:
            if interaction.user.id not in self.bot.owner_ids:
                return await interaction.warn("You can't deep lookup the owner of the bot")
        message_data = await interaction.client.db.fetch(
            "SELECT server_id, SUM(message_count) as total_messages FROM activity_messages WHERE user_id = $1 GROUP BY server_id ORDER BY total_messages DESC",
            user.id
        )
        if not message_data:
            return await interaction.warn(f"No data found for {user.mention}")
        content = []
        for entry in message_data:
            guild = self.bot.get_guild(entry["server_id"])
            if guild:
                content.append(f"**{guild.name}** - `{entry['total_messages']:,.0f}` messages")
            else:
                guild_name = await interaction.client.db.fetchval(
                    "SELECT guild_name FROM guild_names WHERE guild_id = $1",
                    entry["server_id"]
                )
                if guild_name:
                    content.append(f"**{guild_name}** - `{entry['total_messages']:,.0f}` messages")
                else:
                    content.append(f"**{entry['server_id']}** - `{entry['total_messages']:,.0f}` messages")
        if not content:
            return await interaction.warn(f"{user.mention} has no message records across any servers")
        await ctx.paginate(content, f"Deep lookup for {user.name}", {"name": user.name, "icon_url": user.avatar.url if user.avatar else user.default_avatar.url}, author_only=False, interaction=interaction)

    @app_commands.command(name="support", description="Get AI Support")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(prompt="Prompt:")
    async def support(self, interaction: Interaction, prompt: str):
        """Get AI Support"""
        await interaction.response.defer()
        try:
            client = openai.OpenAI(api_key=config.OPENAI)
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model="ft:gpt-4o-mini-2024-07-18:evelina::B1zGGhDC",
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.choices[0].message.content
        except Exception as e:
            answer = f"Error: {e}"
        if len(answer) > 2000:
            return await interaction.warn("The response is too long to send")
        await interaction.followup.send(answer)

    @app_commands.command(name="caption", description="Add a caption to an image or GIF")
    @app_commands.user_install()
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.describe(file="Image or GIF to set:", text="Caption to set:")
    async def caption(self, interaction: discord.Interaction, text: str, file: discord.Attachment):
        """Caption Command for Slash."""
        await interaction.response.defer()
        if not file.content_type.startswith("image/"):
            return await interaction.warn("Please upload a valid image or GIF.", ephemeral=True)
        img_bytes = await file.read()
        output_buffer = BytesIO()
        try:
            is_gif = file.filename.lower().endswith(".gif")
            if is_gif:
                with Image.open(BytesIO(img_bytes)) as img:
                    frames = []
                    durations = []
                    transparencies = []
                    disposal = []
                    tasks = []
                    for frame in ImageSequence.Iterator(img):
                        frame = frame.convert("RGBA")
                        tasks.append(self.process_frame(frame.copy(), text))
                        durations.append(frame.info.get('duration', 100))
                        transparencies.append(frame.info.get('transparency', None))
                        disposal.append(frame.info.get('disposal', 2))
                    processed_frames = await asyncio.gather(*tasks)
                    final_frames = []
                    for frame in processed_frames:
                        frame = frame.convert("P", palette=Image.ADAPTIVE, dither=Image.NONE)
                        final_frames.append(frame)
                    final_frames[0].save(
                        output_buffer,
                        format="GIF",
                        save_all=True,
                        append_images=final_frames[1:],
                        duration=durations,
                        loop=0,
                        optimize=True,
                        disposal=disposal[0],
                        transparency=transparencies[0] if any(transparencies) else None
                    )
            else:
                with Image.open(BytesIO(img_bytes)) as img:
                    result_img = await self.process_frame(img, text)
                    result_img.save(output_buffer, format="GIF")
            output_buffer.seek(0)
            file = discord.File(fp=output_buffer, filename="caption.gif")
            return await interaction.followup.send(file=file)
        except UnidentifiedImageError:
            return await interaction.warn("The provided file could not be processed.", ephemeral=True)

    def parse_text_for_emojis(self, text: str):
        emoji_regex = r"<:(\w+):(\d+)>"
        parts = []
        last_pos = 0
        for match in re.finditer(emoji_regex, text):
            start, end = match.span()
            if start > last_pos:
                parts.append(('text', text[last_pos:start]))
            emoji_id = match.group(2)
            parts.append(('emoji', emoji_id))
            last_pos = end
        if last_pos < len(text):
            parts.append(('text', text[last_pos:]))
        return parts

    async def render_text_with_emojis_centered(self, draw, font, base_img, text, y, emoji_size, image_width):
        parts = self.parse_text_for_emojis(text)
        total_width = 0
        async with aiohttp.ClientSession() as session:
            for part_type, content in parts:
                if part_type == 'text':
                    bbox = draw.textbbox((0, 0), content, font=font)
                    total_width += (bbox[2] - bbox[0]) + 5
                elif part_type == 'emoji':
                    total_width += emoji_size + 5
        total_width -= 5
        start_x = (image_width - total_width) // 2
        x = start_x
        async with aiohttp.ClientSession() as session:
            for part_type, content in parts:
                if part_type == 'text':
                    draw.text((x, y), content, font=font, fill='black')
                    bbox = draw.textbbox((x, y), content, font=font)
                    x = bbox[2] + 5
                elif part_type == 'emoji':
                    emoji_url = f"https://cdn.discordapp.com/emojis/{content}.png"
                    async with session.get(emoji_url) as resp:
                        if resp.status == 200:
                            emoji_bytes = await resp.read()
                            emoji_img = Image.open(io.BytesIO(emoji_bytes)).convert("RGBA")
                            emoji_img = emoji_img.resize((emoji_size, emoji_size), Image.LANCZOS)
                            base_img.paste(emoji_img, (x, y), emoji_img)
                            x += emoji_size + 5

    async def process_frame(self, img: Image.Image, text: str) -> Image.Image:
        img = img.convert("RGBA")
        try:
            font_size = max(int(img.height * 0.07), 30)
            font = ImageFont.truetype("data/fonts/ChocolatesBold.otf", size=font_size)
        except:
            font = ImageFont.load_default()
        dummy_draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
        max_width = img.width - 40
        words = text.split()
        lines = []
        current_line = ""
        for word in words:
            test_line = f"{current_line} {word}".strip()
            bbox = dummy_draw.textbbox((0, 0), test_line, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        line_height = dummy_draw.textbbox((0, 0), "Ag", font=font)[3]
        min_bar_height = int(img.height * 0.15)
        bar_height = max(min_bar_height, line_height * len(lines) + 20)
        total_height = img.height + bar_height
        new_img = Image.new("RGBA", (img.width, total_height), (255, 255, 255, 255))
        new_img.paste(img, (0, bar_height), img)
        draw = ImageDraw.Draw(new_img)
        emoji_size = max(int(line_height * 1.1), 30)
        tasks = []
        for idx, line in enumerate(lines):
            y_text = (bar_height - (len(lines) * line_height)) // 2 + idx * line_height
            tasks.append(self.render_text_with_emojis_centered(draw, font, new_img, line, y_text, emoji_size, img.width))
        await asyncio.gather(*tasks)
        return new_img
    
async def setup(bot: Evelina) -> None:
    await bot.add_cog(Selfbot(bot))