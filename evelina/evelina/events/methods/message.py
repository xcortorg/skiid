import re
import os
import math
import json
import time
import uuid
import yt_dlp
import random
import string
import aiohttp
import asyncio
import humanize
import humanfriendly

from io import BytesIO
from typing import Optional, List, Union
from collections import defaultdict
from datetime import datetime, timedelta

from discord import Message, Embed, File, VoiceChannel, ButtonStyle, AllowedMentions, MessageType, InteractionType, Member, Webhook, DMChannel, User, Member, utils, NotFound, Forbidden, HTTPException, Thread, TextChannel
from discord.ui import Button, View
from discord.abc import GuildChannel
from discord.ext.commands import CooldownMapping, BucketType
from discord.errors import NotFound

from modules import config
from modules.styles import emojis, colors, icons
from modules.uwuipy import uwuipy
from modules.evelinabot import Evelina, LoggingMeasures
from modules.validators import ValidAutoreact

class MessageMethods:
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.log = LoggingMeasures(self.bot)
        self.spam_cache = {}
        self.repeat_cache = {}
        self.afk_cd = CooldownMapping.from_cooldown(3, 3, BucketType.channel)
        self.level_cd = CooldownMapping.from_cooldown(3, 3, BucketType.member)
        self.ratelimit_cd = CooldownMapping.from_cooldown(4, 6, BucketType.channel)
        self.autoreact_cd = CooldownMapping.from_cooldown(4, 6, BucketType.channel)
        self.locks = defaultdict(asyncio.Lock)
        self.reaction_locks = defaultdict(asyncio.Lock)
        self.message_author_map = {}
        self.last_triggered_autoresponder = {}

    def get_cooldown(self, message: Message) -> Optional[int]:
        bucket = self.level_cd.get_bucket(message)
        return bucket.update_rate_limit()
    
    def afk_ratelimit(self, message: Message) -> Optional[int]:
        bucket = self.afk_cd.get_bucket(message)
        return bucket.update_rate_limit()
    
    def autoresponder_replacement(self, member: Union[Member, User], params: str = None):
        if params is None:
            return None
        if "{member.id}" in params:
            params = params.replace("{member.id}", str(member.id))
        if "{member.name}" in params:
            params = params.replace("{member.name}", member.name)
        if "{member.nick}" in params:
            params = params.replace("{member.nick}", member.nick or member.display_name)
        if "{member.display}" in params:
            params = params.replace("{member.display}", member.display_name)
        if "{member.mention}" in params:
            params = params.replace("{member.mention}", member.mention)
        if "{member.discriminator}" in params:
            params = params.replace("{member.discriminator}", member.discriminator)
        if "{member.avatar}" in params:
            params = params.replace("{member.avatar}", member.avatar.url)
        return params
    
    async def get_blacklist(self, guild_id):
        res = await self.bot.db.fetchrow("SELECT users, channels, roles FROM antinuke_linksedit WHERE guild_id = $1", guild_id)
        if res is None:
            return [], [], []
        users = json.loads(res['users']) if res['users'] else []
        channels = json.loads(res['channels']) if res['channels'] else []
        roles = json.loads(res['roles']) if res['roles'] else []
        return users, channels, roles

    async def level_replace(self, member: Member, params: str):
        check = await self.bot.db.fetchrow("SELECT * FROM level_user WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id)
        if "{level}" in params:
            params = params.replace("{level}", str(check["level"]))
        if "{target_xp}" in params:
            params = params.replace("{target_xp}", str(check["target_xp"]))
        return params

    def antispam_threshold(self, message: Message):
        if not self.spam_cache.get(message.guild.id):
            self.spam_cache[message.guild.id] = {}
        if not self.spam_cache[message.guild.id].get(message.author.id):
            self.spam_cache[message.guild.id][message.author.id] = [(datetime.now(), message)]
        else:
            self.spam_cache[message.guild.id][message.author.id].append((datetime.now(), message))
        to_remove = [d for d in self.spam_cache[message.guild.id][message.author.id] if (datetime.now() - d[0]).total_seconds() > 10]
        for d in to_remove:
            self.spam_cache[message.guild.id][message.author.id].remove(d)
        return list(map(lambda m: m[1], self.spam_cache[message.guild.id][message.author.id]))
    
    async def whitelisted_antispam(self, message: Message):
        res = await self.bot.db.fetchrow("SELECT users, channels, roles FROM automod_spam WHERE guild_id = $1", message.guild.id)
        if res is None:
            return False
        if res["users"]:
            users = json.loads(res["users"])
            if message.author.id in users:
                return True
        if res["channels"]:
            channels = json.loads(res["channels"])
            if message.channel.id in channels:
                return True
        if res["roles"]:
            roles = json.loads(res["roles"])
            member_roles = [role.id for role in message.author.roles]
            if any(role in member_roles for role in roles):
                return True
        return False
    
    def antirepeat_threshold(self, message: Message):
        if not self.repeat_cache.get(message.guild.id):
            self.repeat_cache[message.guild.id] = {}
        if not self.repeat_cache[message.guild.id].get(message.author.id):
            self.repeat_cache[message.guild.id][message.author.id] = {
                "last_message": message.content,
                "count": 1,
                "timestamp": datetime.now(),
            }
        else:
            data = self.repeat_cache[message.guild.id][message.author.id]
            if data["last_message"] == message.content:
                data["count"] += 1
                data["timestamp"] = datetime.now()
            else:
                data["last_message"] = message.content
                data["count"] = 1
                data["timestamp"] = datetime.now()
            if (datetime.now() - data["timestamp"]).total_seconds() > 10:
                data["count"] = 1
        return self.repeat_cache[message.guild.id][message.author.id]["count"]
    
    async def whitelisted_antirepeat(self, message: Message):
        res = await self.bot.db.fetchrow("SELECT users, channels, roles FROM automod_repeat WHERE guild_id = $1", message.guild.id)
        if res is None:
            return False
        if res["users"]:
            users = json.loads(res["users"])
            if message.author.id in users:
                return True
        if res["channels"]:
            channels = json.loads(res["channels"])
            if message.channel.id in channels:
                return True
        if res["roles"]:
            roles = json.loads(res["roles"])
            member_roles = [role.id for role in message.author.roles]
            if any(role in member_roles for role in roles):
                return True
        return False

    async def get_autoreact_cd(self, message: Message) -> Optional[int]:
        bucket = self.autoreact_cd.get_bucket(message)
        return bucket.update_rate_limit()

    async def get_ratelimit(self, message: Message) -> Optional[int]:
        bucket = self.ratelimit_cd.get_bucket(message)
        return bucket.update_rate_limit()

    async def on_reposter_message(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        check = await self.bot.db.fetchrow("SELECT status, prefix FROM reposter WHERE guild_id = $1", message.guild.id)
        if check:
            if not check["status"]:
                return
            prefix = check["prefix"] or "evelina"
        else:
            prefix = "evelina"
        if message.content.startswith(prefix):
            content = message.content[len(prefix) + 1:].strip()
            if content:
                if re.search(r"\bhttps?:\/\/(?:m|www|vm|t)\.tiktok\.com\/\S*?\b(?:(?:(?:usr|v|embed|user|video|photo|t)\/|\?shareId=|\&item_id=)(\d+)|(?=\w{7})(\w*?[A-Z\d]\w*)(?=\s|\/$))\b", content):
                    return await self.repost_tiktok(message)
                elif re.search(r"((?:https?:\/\/)?(?:www\.)?instagram\.com\/(?:reel|reels|p)\/([^/?#&]+)).*", content):
                    return await self.repost_instagram(message)
                elif re.search(r"https:\/\/(?:www\.)?snapchat\.com\/(?:t\/\S+|spotlight\/\S+)", content):
                    return await self.repost_snapchat(message)
                elif re.search(r"https:\/\/x\.com\/(?:i\/web\/status\/\d+|[a-zA-Z0-9_]+)", content) or re.search(r"https:\/\/twitter\.com\/(?:i\/web\/status\/\d+|[a-zA-Z0-9_]+)", content):
                    return await self.repost_twitter(message)
                elif re.search(r"https:\/\/(?:www\.)?pinterest\.com\/pin\/\d+\/", content) or re.search(r"https:\/\/(?:[a-z]{2}\.)?pinterest\.com\/pin\/\d+\/", content):
                    return await self.repost_pinterest(message)
    
    async def repost_tiktok(self, message: Message):
        ctx = await self.bot.get_context(message)
        settings = await self.bot.db.fetchrow("SELECT delete, prefix, embed FROM reposter WHERE guild_id = $1", message.guild.id)
        if not settings:
            delete = True
            embed_enabled = True
        else:
            delete = settings["delete"]
            embed_enabled = settings["embed"]
        cooldown = await self.get_ratelimit(message)
        if not cooldown:
            async with self.locks[message.guild.id]:
                url = message.content.split()[1] if len(message.content.split()) > 1 else ""
                api_url = "https://api.evelina.bot/tiktok/media"
                if delete:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                async with message.channel.typing():
                    try:
                        x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
                    except Exception:
                        return await message.channel.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author.mention}: Failed to fetch TikTok URL\n> {url}"))
                    if not isinstance(x, dict):
                        return await message.channel.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author.mention}: Unexprected response format\n> {url}"))
                    author = x.get("author", {})
                    username = author.get("username", "unknown")
                    avatar_url = author.get("avatar", "")
                    if "images" in x and x["images"]:
                        try:
                            image_urls = x["images"]
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
                                .set_footer(text=f"Page: {index + 1}/{len(image_urls)} ・ ❤️ {likes:,}  💬 {comments:,}  🔗 {shares:,}  👀 {views:,} | {message.author}")
                                for index, image_url in enumerate(image_urls)
                            ]
                            if not embeds:
                                return await message.channel.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author.mention}: Error fetching Images from TikTok URL\n> {url}"))
                            return await ctx.paginator(embeds, author_only=False)
                        except Exception:
                            return await message.channel.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author.mention}: Failed to send TikTok Images\n> {url}"))
                    elif isinstance(x.get("video"), str):
                        try:
                            video = x["video"]
                            music = x.get("music", "")
                            file = File(fp=await self.bot.getbyte(video), filename="evelinatiktok.mp4")
                            caption = x.get('caption', 'no caption')
                            embed = Embed(color=colors.TIKTOK, description=f"[{caption}]({url})\n> **Music:** [Download]({music})",
                            ).set_author(name=f"{username}", icon_url=f"{avatar_url}", url=f"https://tiktok.com/@{username}",
                            ).set_footer(icon_url=icons.TIKTOK, text=f"❤️ {x['likes']:,}  💬 {x['comments']:,}  🔗 {x['shares']:,}  👀 {x['views']:,} | {message.author}")
                            if embed_enabled:
                                return await message.channel.send(embed=embed, file=file)
                            else:
                                return await message.channel.send(file=file)
                        except Exception:
                            return await message.channel.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author.mention}: Failed to send TikTok Video\n> {url}"))
                    else:
                        return await message.channel.send(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author.mention}: Couldn't retrieve information about the TikTok URL\n> {url}"))

    async def repost_instagram(self, message: Message):
        settings = await self.bot.db.fetchrow("SELECT delete, prefix, embed FROM reposter WHERE guild_id = $1", message.guild.id)
        if not settings:
            delete = True
            embed_enabled = True
        else:
            delete = settings["delete"]
            embed_enabled = settings["embed"]
        cooldown = await self.get_ratelimit(message)
        if not cooldown:
            async with self.locks[message.guild.id]:
                url = message.content.split()[1] if len(message.content.split()) > 1 else ""
                api_url = "https://api.evelina.bot/instagram/media"
                if delete:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                async with message.channel.typing():
                    x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
                    if x["video"].get("video"):
                        video = x["video"]["video"]
                        file = File(fp=await self.bot.getbyte(video), filename="evelinainstagram.mp4")
                        caption = x["video"].get('caption', '')
                        description = f"[{caption}]({url})" if caption else ""
                        icon_url = None if x['author']['avatar'] == "None" else x['author']['avatar']
                        name = None if x['author']['username'] == "None" else x['author']['username']
                        url = None if x['author']['username'] == "None" else f"https://instagram.com/{x['author']['username']}"
                        embed = Embed(color=colors.INSTAGRAM, description=description,
                        ).set_author(name=name, icon_url=icon_url, url=url,
                        ).set_footer(icon_url=icons.INSTAGRAM, text=f"❤️ {x['video']['likes']:,}  💬 {x['video']['comments']:,}  🔗 {x['video']['shares']:,}  👀 {x['video']['views']:,} | {message.author}")
                        if embed_enabled:
                            return await message.channel.send(embed=embed, file=file)
                        else:
                            return await message.channel.send(file=file)
                    else:
                        embed = Embed(color=colors.WARNING, description=f"Couldn't get information about {url}")
                        return await message.channel.send(embed=embed)

    async def repost_snapchat(self, message: Message):
        settings = await self.bot.db.fetchrow("SELECT delete, prefix, embed FROM reposter WHERE guild_id = $1", message.guild.id)
        if not settings:
            delete = True
            embed_enabled = True
        else:
            delete = settings["delete"]
            embed_enabled = settings["embed"]
        cooldown = await self.get_ratelimit(message)
        if not cooldown:
            async with self.locks[message.guild.id]:
                url = message.content.split()[1] if len(message.content.split()) > 1 else ""
                api_url = "https://api.evelina.bot/snapchat/media"
                if delete:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                async with message.channel.typing():
                    x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
                    if x["video"].get("video"):
                        video = x["video"]["video"]
                        file = File(fp=await self.bot.getbyte(video), filename="evelinasnapchat.mp4")
                        caption = x["video"].get('caption', '')
                        views = int(x["video"].get('views', 0))
                        description = f"[{caption}]({url})" if caption else ""
                        embed = Embed(color=colors.SNAPCHAT, description=description,
                        ).set_author(name=f"{x['author']['username']}", url=f"https://snapchat.com/add/{x['author']['username']}",
                        ).set_footer(icon_url=icons.SNAPCHAT, text=f"👀 {views:,} | {message.author}")
                        if embed_enabled:
                            return await message.channel.send(embed=embed, file=file)
                        else:
                            return await message.channel.send(file=file)
                    else:
                        embed = Embed(color=colors.WARNING, description=f"Couldn't get information about {url}")
                        return await message.channel.send(embed=embed)

    async def repost_twitter(self, message: Message):
        settings = await self.bot.db.fetchrow("SELECT delete, prefix, embed FROM reposter WHERE guild_id = $1", message.guild.id)
        if not settings:
            delete = True
            embed_enabled = True
        else:
            delete = settings["delete"]
            embed_enabled = settings["embed"]
        cooldown = await self.get_ratelimit(message)
        if not cooldown:
            async with self.locks[message.guild.id]:
                url = message.content.split()[1] if len(message.content.split()) > 1 else ""
                api_url = "https://api.evelina.bot/twitter/media"
                if delete:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                async with message.channel.typing():
                    x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
                    if x["video"].get("video"):
                        video = x["video"]["video"]
                        file = File(fp=await self.bot.getbyte(video), filename="evelinatwitter.mp4")
                        caption = x["video"].get('caption', '')
                        description = f"[{caption}]({url})" if caption else ""
                        embed = Embed(color=colors.TWITTER, description=description,
                        ).set_author(name=f"{x['author']['username']}", icon_url=f"{x['author']['avatar']}", url=f"https://twitter.com/{x['author']['username']}",
                        ).set_footer(icon_url=icons.TWITTER ,text=f"🔖 {x['video']['saves']:,} | {message.author}")
                        if embed_enabled:
                            return await message.channel.send(embed=embed, file=file)
                        else:
                            return await message.channel.send(file=file)
                    else:
                        embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author.mention}: Tweet not found, private, or contains adult content.\n> {url}")
                        return await message.channel.send(embed=embed)

    async def repost_pinterest(self, message: Message):
        settings = await self.bot.db.fetchrow("SELECT delete, prefix, embed FROM reposter WHERE guild_id = $1", message.guild.id)
        if not settings:
            delete = True
            embed_enabled = True
        else:
            delete = settings["delete"]
            embed_enabled = settings["embed"]
        cooldown = await self.get_ratelimit(message)
        if not cooldown:
            async with self.locks[message.guild.id]:
                url = message.content.split()[1] if len(message.content.split()) > 1 else ""
                api_url = "https://api.evelina.bot/pinterest/media"
                if delete:
                    try:
                        await message.delete()
                    except Exception:
                        pass
                async with message.channel.typing():
                    x = await self.bot.session.get_json(api_url, params={"url": url, "key": config.EVELINA})
                    if x['type'] == 'image':
                        file = File(fp=await self.bot.getbyte(x['data']['url']), filename="evelinapinterest.png")
                        description = f"[{x['data']['title']}]({url})" if x['data']['title'] else ""
                        embed = Embed(color=colors.PINTEREST, description=description,
                        ).set_footer(icon_url=icons.PINTEREST, text=f"{message.author}")
                        if embed_enabled:
                            return await message.channel.send(embed=embed, file=file)
                        else:
                            return await message.channel.send(file=file)
                    elif x['type'] == 'video':
                        file = File(fp=await self.bot.getbyte(x['data']['url']), filename="evelinapinterest.mp4")
                        description = f"[{x['data']['title']}]({url})" if x['data']['title'] else ""
                        embed = Embed(color=colors.PINTEREST, description=description,
                        ).set_footer(icon_url=icons.PINTEREST, text=f"{message.author}")
                        if embed_enabled:
                            return await message.channel.send(embed=embed, file=file)
                        else:
                            return await message.channel.send(file=file)
                    else:
                        embed = Embed(color=colors.WARNING, description=f"Couldn't get information about {url}")
                        return await message.channel.send(embed=embed)

    async def on_bump_message(self, message: Message):
        if message.type == MessageType.chat_input_command:
            interaction = message.interaction_metadata
            if interaction and interaction.type == InteractionType.application_command and message.author.id == 302050872383242240:
                check = None
                for embed in message.embeds:
                    if "bump" in (embed.description or "").lower() or "bump" in (embed.title or "").lower():
                        check = await self.bot.db.fetchrow("SELECT thankyou FROM bumpreminder WHERE guild_id = $1", message.guild.id)
                        break
                if check is not None:
                    member = message.guild.get_member(interaction.user.id)
                    if member:
                        x = await self.bot.embed_build.alt_convert(member, check[0])
                        x["allowed_mentions"] = AllowedMentions.all()
                        await message.channel.send(**x)
                        await self.bot.db.execute("UPDATE bumpreminder SET time = $1, channel_id = $2, user_id = $3 WHERE guild_id = $4", datetime.now() + timedelta(hours=2), message.channel.id, interaction.user.id, message.guild.id)
                        await self.bot.db.execute("INSERT INTO bumpreminder_leaderboard (guild_id, user_id, bumps) VALUES ($1, $2, 1) ON CONFLICT (guild_id, user_id) DO UPDATE SET bumps = bumpreminder_leaderboard.bumps + 1", message.guild.id, interaction.user.id)

    async def on_boost_message(self, message: Message):
        if message.guild:
            if "MessageType.premium_guild" in str(message.type):
                member = message.author
                results = await self.bot.db.fetch("SELECT * FROM boost WHERE guild_id = $1", message.guild.id)
                for result in results:
                    channel = self.bot.get_channel(result["channel_id"])
                    if channel:
                        perms = channel.permissions_for(member.guild.me)
                        if perms.send_messages and perms.embed_links:
                            try:
                                x = await self.bot.embed_build.alt_convert(member, result["message"])
                                await channel.send(**x)
                            except Exception as e:
                                embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {message.author}: Failed to send boost message:\n```{e}```")
                                await channel.send(embed=embed)

    async def on_autoresponder_event(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        now = time.time()
        channel_id = message.channel.id
        last_time = self.last_triggered_autoresponder.get(channel_id, 0)
        if now - last_time < 2.5:
            return
        self.last_triggered_autoresponder[channel_id] = now
        autoresponders = await self.bot.db.fetch("SELECT * FROM autoresponder WHERE guild_id = $1", message.guild.id)
        for row in autoresponders:
            trigger = str(row["trigger"]).lower()
            response = row["response"]
            ctx = await self.bot.get_context(message)
            permissions = await self.bot.db.fetch("SELECT state, data FROM autoresponder_permissions WHERE guild_id = $1 AND trigger = $2", message.guild.id, trigger)
            if not await self._check_permissions(permissions, message):
                continue
            if row["strict"]:
                if trigger == message.content.lower():
                    await self._send_autoresponse(ctx, message, response, row)
            else:
                if trigger in message.content.lower():
                    await self._send_autoresponse(ctx, message, response, row)

    async def _send_autoresponse(self, ctx, message, response, row):
        member = message.mentions[0] if message.mentions else message.author
        x = await self.bot.embed_build.convert(ctx, self.autoresponder_replacement(member, response))
        if row["reply"]:
            kwargs = {"reference": message.to_reference(), "mention_author": False}
            try:
                await ctx.send(**x, **kwargs)
            except Exception:
                await ctx.send(**x)
        else:
            await ctx.send(**x)
        if row["delete"]:
            try:
                await message.delete()
            except Exception:
                pass

    async def _check_permissions(self, permissions, message: Message) -> bool:
        user_id = message.author.id
        channel_id = message.channel.id
        member_roles = [role.id for role in message.author.roles]
        allow_present = False
        deny_present = False
        allow_matched = False
        deny_matched = False
        for permission in permissions:
            state = permission["state"]
            data = permission["data"]
            if isinstance(data, str):
                data = json.loads(data)
            matched = (
                user_id in data["users"] or
                channel_id in data["channels"] or
                any(role_id in data["roles"] for role_id in member_roles)
            )
            if state == "deny":
                deny_present = True
                if matched:
                    deny_matched = True
            elif state == "allow":
                allow_present = True
                if matched:
                    allow_matched = True
        if allow_present and not deny_present:
            return allow_matched
        if deny_matched:
            return False
        if allow_present:
            return allow_matched
        return True
                
    async def on_autoreact_event(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        if not message.guild.me or not message.guild.me.guild_permissions:
            return
        if not message.guild.me.guild_permissions.add_reactions:
            return
        channels_with_autoreact = await self.bot.db.fetch("SELECT * FROM autoreact_channel WHERE guild_id = $1", message.guild.id)
        autoreact_channel_ids = [channel['channel_id'] for channel in channels_with_autoreact]
        if message.channel.id in autoreact_channel_ids:
            if isinstance(message.channel, GuildChannel) and hasattr(message.channel, 'slowmode_delay'):
                channel = message.channel
            else:
                channel = await message.channel.fetch()
            if hasattr(channel, 'slowmode_delay') and not channel.slowmode_delay:
                return
            reactions_data = [json.loads(channel['reactions']) for channel in channels_with_autoreact if str(channel['channel_id']) == str(message.channel.id)]
            for reactions in reactions_data:
                for reaction in reactions:
                    try:
                        await message.add_reaction(reaction)
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
        results = await self.bot.db.fetch("SELECT * FROM autoreact WHERE guild_id = $1", message.guild.id)
        def is_sequence_in(words, sequence):
            for i in range(len(words) - len(sequence) + 1):
                if words[i:i + len(sequence)] == sequence:
                    return True
            return False
        for result in results:
            trigger = result["trigger"].lower()
            trigger_words = trigger.split()
            message_words = message.content.lower().split()
            if is_sequence_in(message_words, trigger_words):
                bucket = await self.get_autoreact_cd(message)
                if bucket:
                    return
                async with self.reaction_locks[message.channel.id]:
                    reactions = json.loads(result["reactions"])
                    ctx = await self.bot.get_context(message)
                    for reaction in reactions:
                        x = await ValidAutoreact().convert(ctx, reaction)
                        if x:
                            try:
                                await message.add_reaction(x)
                            except Exception:
                                pass
                            await asyncio.sleep(0.5)

    async def on_channeltype_check(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        if not message.guild.me or not message.guild.me.guild_permissions:
            return
        if not message.guild.me.guild_permissions.manage_messages:
            return
        guild_id = message.guild.id
        channel_id = message.channel.id
        imgonly_check = await self.bot.db.fetchrow("SELECT * FROM only_img WHERE guild_id = $1 AND channel_id = $2", guild_id, channel_id)
        botonly_check = await self.bot.db.fetchrow("SELECT * FROM only_bot WHERE guild_id = $1 AND channel_id = $2", guild_id, channel_id)
        linkonly_check = await self.bot.db.fetchrow("SELECT * FROM only_link WHERE guild_id = $1 AND channel_id = $2", guild_id, channel_id)
        auto_thread_check = await self.bot.db.fetchrow("SELECT * FROM autothread WHERE guild_id = $1 AND channel_id = $2", guild_id, channel_id)
        if isinstance(message.author, Member) and not message.author.guild_permissions.manage_messages:
            if imgonly_check and not message.attachments:
                try:
                    await message.delete()
                except Exception:
                    pass
                return
            if botonly_check and not message.author.bot:
                try:
                    await message.delete()
                except Exception:
                    pass
                return
            if linkonly_check and not any(word.startswith("http://") or word.startswith("https://") for word in message.content.split()):
                try:
                    await message.delete()
                except Exception:
                    pass
                return
        if auto_thread_check:
            if message.channel.default_auto_archive_duration:
                auto_archive_duration = message.channel.default_auto_archive_duration
            else:
                auto_archive_duration = 10080
            try:
                thread = await message.create_thread(name=f"{message.author.name}'s thread", auto_archive_duration=auto_archive_duration)
                msg = await thread.send(f".")
                await msg.delete()
            except Exception:
                pass

    async def on_directmessage_event(self, message: Message):
        if message.author.id == 335500798752456705 and not message.reference:
            return
        if isinstance(message.channel, DMChannel) and message.author != self.bot.user and not message.reference:
            channel = self.bot.get_channel(1278487990792093790)
            if channel:
                attachments = []
                for attachment in message.attachments:
                    file = await attachment.to_file()
                    attachments.append(file)
                stickers = []
                for sticker in message.stickers:
                    file = await sticker.to_file()
                    attachments.append(file)
                sent_message = await channel.send(f"**{message.author}** (`{message.author.id}`): {message.content}", files=attachments + stickers)
                self.message_author_map[sent_message.id] = message.author.id
            else:
                channel = self.bot.get_channel(1284182037825065096)
                if channel:
                    attachments = []
                    for attachment in message.attachments:
                        file = await attachment.to_file()
                        attachments.append(file)
                    stickers = []
                    for sticker in message.stickers:
                        file = await sticker.to_file()
                        attachments.append(file)
                    sent_message = await channel.send(f"**{message.author}** (`{message.author.id}`): {message.content}", files=attachments + stickers)
                    self.message_author_map[sent_message.id] = message.author.id
        elif message.author.id in self.bot.owner_ids and message.reference:
            original_message_id = message.reference.message_id
            original_author_id = self.message_author_map.get(original_message_id)
            if original_author_id:
                original_author = self.bot.get_user(original_author_id)
                if original_author:
                    await original_author.send(f"{message.content}")

    async def on_messagestats_event(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        user_id = message.author.id
        channel_id = message.channel.id
        server_id = message.guild.id
        server_name = message.guild.name
        message_date = datetime.utcnow().date()
        check = await self.bot.db.fetchrow("SELECT * FROM activity_ignore WHERE channel_id = $1 AND guild_id = $2", channel_id, server_id)
        if check:
            return
        await self.bot.db.execute("""
            INSERT INTO activity_messages (user_id, channel_id, server_id, message_date, message_count)
            VALUES ($1, $2, $3, $4, 1)
            ON CONFLICT (user_id, channel_id, server_id, message_date)
            DO UPDATE SET message_count = activity_messages.message_count + 1
        """, user_id, channel_id, server_id, message_date)
        await self.bot.db.execute("""
            INSERT INTO guild_names (guild_id, guild_name)
            VALUES ($1,$2)
            ON CONFLICT (guild_id)
            DO UPDATE SET guild_name = $2
        """, server_id, server_name)

    async def on_uwulock_message(self, message: Message):
        if message.is_system():
            return
        if not message.guild or not message.author or message.author.bot:
            return
        if isinstance(message.channel, Thread):
            return
        cache_key = f'uwuifyer_{message.guild.id}_{message.author.id}'
        uwuifyer_status = await self.bot.cache.get(cache_key)
        if uwuifyer_status:
            if message.attachments and not message.content.strip():
                attachment_urls = [attachment.url for attachment in message.attachments]
                content_with_attachments = "\n".join(attachment_urls)
            else:
                if message.content.strip():
                    uwuifier = uwuipy()
                    try:
                        uwuified = uwuifier.uwuify(message.content)
                    except Exception:
                        uwuified = message.content
                else:
                    uwuified = ""
                content_with_attachments = f"{uwuified[:2000]}"
                if message.attachments:
                    attachment_urls = [attachment.url for attachment in message.attachments]
                    content_with_attachments += "\n\n" + "\n".join(attachment_urls)
            async with aiohttp.ClientSession() as session:
                webhooks = await message.channel.webhooks()
                bot_webhook = None
                for webhook in webhooks:
                    if webhook.user.id == self.bot.user.id:
                        bot_webhook = webhook
                        break
                if bot_webhook is None:
                    try:
                        bot_webhook = await message.channel.create_webhook(name="Webhook")
                    except Exception:
                        return
                try:
                    webhook = Webhook.from_url(bot_webhook.url, session=session)
                    await webhook.send(
                        content=content_with_attachments,
                        username=message.author.display_name,
                        avatar_url=str(message.author.avatar.url if message.author.avatar else message.author.default_avatar.url),
                        allowed_mentions=AllowedMentions.none()
                    )
                except Exception:
                    return
                try:
                    await message.delete()
                except Exception:
                    return

    async def on_announce_message(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        result = await self.bot.db.fetchrow("SELECT channel_id FROM autopublish WHERE guild_id = $1 AND channel_id = $2", message.guild.id, message.channel.id)
        if result:
            try:
                await message.publish()
            except Exception:
                pass

    async def on_seen_event(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        args = [message.author.id, message.guild.id, datetime.now()]
        await self.bot.db.execute("INSERT INTO seen (user_id, guild_id, time) VALUES ($1, $2, $3) ON CONFLICT (user_id, guild_id) DO UPDATE SET time = EXCLUDED.time", *args)

    async def on_stickymessage_event(self, message: Message):
        if str(message.author.id) == str(self.bot.user.id):
            return
        if not message.guild or not message.author or message.author.bot:
            return
        if not message.content and not message.attachments and not message.embeds:
            return
        check = await self.bot.db.fetchrow("SELECT * FROM stickymessage WHERE channel_id = $1 AND guild_id = $2", message.channel.id, message.guild.id)
        if check:
            if check["not_delete"] == False:
                if check["last_message_id"]:
                    try:
                        last_msg = await message.channel.fetch_message(check["last_message_id"])
                        await last_msg.delete()
                    except Exception:
                        pass
            try:
                member = message.author
                x = await self.bot.embed_build.alt_convert(member, check["message"])
                new_msg = await message.channel.send(**x)
                await self.bot.db.execute("UPDATE stickymessage SET last_message_id = $1 WHERE channel_id = $2 AND guild_id = $3", new_msg.id, message.channel.id, message.guild.id)
            except Exception:
                pass

    async def on_afk_event(self, message: Message):
        if message.is_system():
            return
        if not message.guild or not message.author or message.author.bot:
            return
        if check := await self.bot.db.fetchrow("SELECT * FROM afk WHERE user_id = $1", message.author.id):
            last_afk_time = check["time"]
            if (datetime.now().timestamp() - last_afk_time.timestamp()) < 3:
                return
            ctx = await self.bot.get_context(message)
            await self.bot.db.execute("DELETE FROM afk WHERE user_id = $1", message.author.id)
            embed = Embed(color=colors.NEUTRAL, description=f"👋 {ctx.author.mention}: Welcome back! You were gone for **{humanize.precisedelta(datetime.fromtimestamp(last_afk_time.timestamp()), format='%0.0f')}**")
            try:
                return await ctx.send(embed=embed)
            except Exception:
                pass
        for mention in message.mentions:
            check = await self.bot.db.fetchrow("SELECT * FROM afk WHERE user_id = $1", mention.id)
            if check:
                if self.afk_ratelimit(message):
                    continue
                ctx = await self.bot.get_context(message)
                time = check["time"]
                embed = Embed(color=colors.NEUTRAL, description=f"👋 {ctx.author.mention}: **{mention.name}** is **AFK** for **{humanize.precisedelta(datetime.fromtimestamp(time.timestamp()), format='%0.0f')}** - {check['reason']}")
                try:
                    return await ctx.send(embed=embed)
                except Exception:
                    pass

    async def on_counting_message(self, message):
        if not message.guild or not message.author or message.author.bot:
            return
        counter_data = await self.bot.db.fetchrow("SELECT channel_id, last_counted, current_number, highest_count, safemode FROM number_counter WHERE guild_id = $1", message.guild.id)
        if not counter_data:
            return
        channel_id, last_counted, current_number, highest_count, safemode = counter_data
        if message.channel.id != channel_id:
            return
        if hasattr(message.channel, 'slowmode_delay') and not message.channel.slowmode_delay:
            try:
                await message.channel.edit(slowmode_delay=5)
            except Exception:
                return
        def evaluate_math(expression):
            try:
                expression = re.sub(r'(\d+(\.\d+)?)(\s*[-+/*]\s*)(\d+(\.\d+)?)%', r'\1\3(\1 * \4 / 100)', expression)
                result = eval(expression, {"__builtins__": None}, {"sqrt": math.sqrt, "pow": math.pow, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi, "e": math.e})
                return result
            except Exception:
                return None
        try:
            clean_content = message.content.replace(" ", "")
            number = evaluate_math(clean_content) if re.search(r"[+\-*/%]", clean_content) else int(clean_content)
            if number is None:
                number = int(clean_content)
        except (ValueError, TypeError):
            if not (message.author.guild_permissions.administrator or message.author.guild_permissions.manage_messages):
                try:
                    await message.delete()
                except Exception:
                    pass
            return
        if message.author.id == last_counted:
            try:
                await message.delete()
                return await message.channel.send(f"{message.author.mention}, you can't count twice in a row!", delete_after=5)
            except Exception:
                pass
        if number == current_number:
            await self.bot.db.execute("UPDATE number_counter SET current_number = $1, last_counted = $2 WHERE guild_id = $3", current_number + 1, message.author.id, message.guild.id)
            current_number += 1
            await asyncio.sleep(0.5)
            try:
                goal_number = current_number - 1
                if goal_number % 100 == 0:
                    await message.add_reaction("🎉")
                    await message.add_reaction("✅")
                else:
                    await message.add_reaction("✅")
            except Exception:
                pass
        else:
            if safemode:
                await asyncio.sleep(0.5)
                try:
                    await message.add_reaction("❌")
                    await message.channel.send(f"{message.author.mention}, incorrect number, but safemode is ON. Continue from **{current_number}**.", delete_after=5)
                except Exception:
                    pass
            else:
                await asyncio.sleep(0.5)
                try:
                    await message.add_reaction("❌")
                    await message.channel.send(f"{message.author.mention}, wrong number! Start again from **1**")
                except Exception:
                    pass
                await self.bot.db.execute("UPDATE number_counter SET current_number = 1, last_counted = NULL WHERE guild_id = $1", message.guild.id)
                current_number = 1
        if not safemode and current_number > highest_count:
            await self.bot.db.execute("UPDATE number_counter SET highest_count = $1 WHERE guild_id = $2", current_number, message.guild.id)

    async def on_antispam_event(self, message: Message):
        if message.guild:
            if not message.guild.chunked:
                await message.guild.chunk(cache=True)
            if not message.guild.me:
                return
            if isinstance(message.author, User):
                return
            if not message.author.guild_permissions.manage_guild:
                if message.guild.me.guild_permissions.moderate_members:
                    if message.guild.me.top_role and message.author.top_role:
                        if message.author.top_role >= message.guild.me.top_role:
                            return
                    elif not message.guild.me.top_role:
                        return
                    if check := await self.bot.db.fetchrow("SELECT * FROM automod_spam WHERE guild_id = $1", message.guild.id):
                        if not await self.whitelisted_antispam(message):
                            spam_count = self.antispam_threshold(message)
                            if len(spam_count) > check["rate"]:
                                res = await self.bot.cache.get(f"antispam-{message.author.id}")
                                if not res:
                                    messages = [msg for msg in self.bot.cached_messages if msg.author.id == message.author.id and msg.channel.id == message.channel.id]
                                    messages.sort(key=lambda m: m.created_at)
                                    if messages:
                                        for i in range(0, len(messages[1:]), 100):
                                            try:
                                                await message.channel.delete_messages(messages[i:i + 100])
                                            except Exception:
                                                pass
                                    try:
                                        if message.guild.id in self.spam_cache and message.author.id in self.spam_cache[message.guild.id]:
                                            del self.spam_cache[message.guild.id][message.author.id]
                                        if check['timeout'] != 0:
                                            timeout = utils.utcnow() + timedelta(seconds=check['timeout'])
                                            await message.author.timeout(timeout, reason="Flagged by the antispam")
                                            if check['message'] == True:
                                                res = await self.bot.cache.get(f"antispam-{message.author.id}")
                                                if not res:
                                                    await message.channel.send(embed=Embed(color=colors.WARNING, description=f"> {emojis.WARNING} {message.author.mention} has been muted for **{humanfriendly.format_timespan(check['timeout'])}** - ***spamming messages***"))
                                        else:
                                            if check['message'] == True:
                                                res = await self.bot.cache.get(f"antispam-{message.author.id}")
                                                if not res:
                                                    await message.channel.send(embed=Embed(color=colors.WARNING, description=f"> {emojis.WARNING} {message.author.mention} has been flagged for ***spamming messages***"))
                                        await self.bot.cache.set(f"antispam-{message.author.id}", True, expiration=30)
                                    except Exception:
                                        pass

    async def on_antirepeat_event(self, message: Message):
        if message.guild:
            if not message.guild.chunked:
                await message.guild.chunk(cache=True)
            if not message.guild.me:
                return
            if isinstance(message.author, User):
                return
            if not message.author.guild_permissions.manage_guild:
                if message.guild.me.guild_permissions.moderate_members:
                    if message.guild.me.top_role and message.author.top_role:
                        if message.author.top_role >= message.guild.me.top_role:
                            return
                    elif not message.guild.me.top_role:
                        return
                    if check := await self.bot.db.fetchrow("SELECT * FROM automod_repeat WHERE guild_id = $1", message.guild.id):
                        if not await self.whitelisted_antirepeat(message):
                            repeat_count = self.antirepeat_threshold(message)
                            if repeat_count > check["rate"]:
                                res = await self.bot.cache.get(f"antirepeat-{message.author.id}")
                                if not res:
                                    messages = [msg for msg in self.bot.cached_messages if msg.author.id == message.author.id and msg.channel.id == message.channel.id]
                                    messages.sort(key=lambda m: m.created_at)
                                    if messages:
                                        for i in range(0, len(messages[1:]), 100):
                                            try:
                                                await message.channel.delete_messages(messages[1:][i:i + 100])
                                            except Exception:
                                                pass
                                    try:
                                        if message.guild.id in self.repeat_cache and message.author.id in self.repeat_cache[message.guild.id]:
                                            del self.repeat_cache[message.guild.id][message.author.id]
                                        if check['timeout'] != 0:
                                            timeout = utils.utcnow() + timedelta(seconds=check['timeout'])
                                            await message.author.timeout(timeout, reason="Flagged by antirepeat")
                                            if check['message'] == True:
                                                res = await self.bot.cache.get(f"antirepeat-{message.author.id}")
                                                if not res:
                                                    await message.channel.send(embed=Embed(color=colors.WARNING, description=f"> {emojis.WARNING} {message.author.mention} has been muted for **{humanfriendly.format_timespan(check['timeout'])}** - ***repeating messages***"))
                                        else:
                                            if check['message'] == True:
                                                res = await self.bot.cache.get(f"antirepeat-{message.author.id}")
                                                if not res:
                                                    await message.channel.send(embed=Embed(color=colors.WARNING, description=f"> {emojis.WARNING} {message.author.mention} has been flagged for ***repeating messages***"))
                                        await self.bot.cache.set(f"antirepeat-{message.author.id}", True, expiration=30)
                                    except Exception:
                                        pass

    async def on_lastfm_message(self, message: Message):
        if message.guild:
            if not message.author.bot:
                if check := await self.bot.db.fetchrow("SELECT * FROM lastfm WHERE user_id = $1 AND customcmd = $2", message.author.id, message.content):
                    ctx = await self.bot.get_context(message)
                    guild_disabled = await self.bot.db.fetchrow("SELECT * FROM guild_disabled_commands WHERE guild_id = $1 AND cmd = $2", message.guild.id, "nowplaying")
                    if guild_disabled:
                        if not (ctx.author.guild_permissions.administrator or ctx.author.id in ctx.bot.owner_ids):
                            return
                    channel_disabled = await self.bot.db.fetchrow("SELECT * FROM channel_disabled_commands WHERE guild_id = $1 AND channel_id = $2 AND cmd = $3", message.guild.id, message.channel.id, "nowplaying")
                    if channel_disabled:
                        if not (ctx.author.guild_permissions.administrator or ctx.author.id in ctx.bot.owner_ids):
                            return
                    return await ctx.invoke(self.bot.get_command("nowplaying"), member=message.author)
                
    async def on_leveling_message(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        ignore_commands = await self.bot.db.fetchval("SELECT command FROM leveling WHERE guild_id = $1", message.guild.id)
        if ignore_commands:
            prefixes = set()
            user_prefix = self.bot.prefix_cache["users"].get(message.author.id)
            if user_prefix:
                prefixes.add(user_prefix)
            guild_prefix = self.bot.prefix_cache["guilds"].get(message.guild.id) if message.guild else None
            if guild_prefix:
                prefixes.add(guild_prefix)
            else:
                prefixes.add(";")
            if any(message.content.startswith(prefix) for prefix in prefixes):
                return
        if isinstance(message.channel, VoiceChannel):
            return
        member = message.guild.get_member(message.author.id)
        if not member:
            return
        blacklist_users, blacklist_channels, blacklist_roles = await self.bot.level.get_blacklist(message.guild.id)
        if (message.author.id in set(blacklist_users) or 
            message.channel.id in set(blacklist_channels) or 
            any(role.id in set(blacklist_roles) for role in member.roles)):
            return
        res = await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", message.guild.id)
        if not res:
            return
        if not self.get_cooldown(message):
            async with self.locks[message.author.id]:
                check = await self.bot.db.fetchrow("SELECT * FROM level_user WHERE guild_id = $1 AND user_id = $2", message.guild.id, message.author.id)
                global_multiplier = res['multiplier'] if res['multiplier'] else 1
                booster_multiplier = res['booster'] if message.author.premium_since else 1
                role_multipliers = await self.bot.db.fetch("SELECT multiplier FROM level_multiplier WHERE guild_id = $1 AND role_id = ANY($2::BIGINT[])", message.guild.id, [role.id for role in member.roles])
                max_role_multiplier = max((float(rm["multiplier"]) for rm in role_multipliers if rm["multiplier"] is not None), default=1)
                final_multiplier = max(
                    global_multiplier if global_multiplier is not None else 1,
                    booster_multiplier if booster_multiplier is not None else 1,
                    max_role_multiplier if max_role_multiplier is not None else 1
                )
                base_xp = 4
                xp_gain = base_xp * final_multiplier
                if not check:
                    await self.bot.db.execute("INSERT INTO level_user (guild_id, user_id, xp, level, target_xp) VALUES ($1, $2, $3, $4, $5)", message.guild.id, message.author.id, xp_gain, 0, int((100 * 1) ** 0.9))
                    target_xp = 100
                else:
                    new_xp = check["xp"] + xp_gain
                    target_xp = check["target_xp"]
                    await self.bot.db.execute("UPDATE level_user SET xp = $1 WHERE user_id = $2 AND guild_id = $3", new_xp, message.author.id, message.guild.id)
                    await self.bot.level.give_rewards(message.author, check["level"])
                    if new_xp >= target_xp:
                        new_level = check["level"] + 1
                        new_target_xp = int((100 * new_level + 1) ** 0.9)
                        await self.bot.db.execute("UPDATE level_user SET target_xp = $1, xp = $2, level = $3 WHERE user_id = $4 AND guild_id = $5", new_target_xp, 0, new_level, message.author.id, message.guild.id)
                        if res["channel_id"] == 0:
                            mes = res["message"]
                            if mes != "none":
                                x = await self.bot.embed_build.alt_convert(message.author, await self.level_replace(message.author, mes))
                                try:
                                    await message.author.send(**x)
                                except Exception:
                                    pass
                            await self.bot.level.give_rewards(message.author, new_level)
                        else:
                            channel = (message.guild.get_channel(res["channel_id"]) or message.channel)
                            mes = res["message"]
                            if mes != "none":
                                x = await self.bot.embed_build.alt_convert(message.author, await self.level_replace(message.author, mes))
                                try:
                                    await channel.send(**x)
                                except Exception:
                                    pass
                            await self.bot.level.give_rewards(message.author, new_level)

    async def on_ping_message(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        if not message.role_mentions:
            return
        if message.author.guild_permissions.administrator or message.author.guild_permissions.manage_guild:
            return
        for role in message.role_mentions:
            check = await self.bot.db.fetchrow("SELECT * FROM pingtimeout WHERE guild_id = $1 AND role_id = $2", message.guild.id, role.id)
            if check:
                await self.bot.db.execute("UPDATE pingtimeout SET last_ping = $1 WHERE guild_id = $2 AND role_id = $3", datetime.now().timestamp(), message.guild.id, role.id)
                await role.edit(mentionable=False)

    async def on_last_message(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        check = await self.bot.db.fetchrow("SELECT * FROM revive WHERE guild_id = $1 AND channel_id = $2", message.guild.id, message.channel.id)
        if check:
            await self.bot.db.execute("UPDATE revive SET last_message = $1 WHERE guild_id = $2 AND channel_id = $3", datetime.now().timestamp(), message.guild.id, message.channel.id)

    async def on_gtn_message(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        check = await self.bot.db.fetchrow("SELECT * FROM guessthenumber WHERE guild_id = $1 AND channel_id = $2", message.guild.id, message.channel.id)
        if check:
            if message.content.isdigit():
                number = int(message.content)
                if number == check["number"]:
                    await message.channel.send(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {message.author.mention} guessed the number! The number was **{check['number']}**"))
                    await self.bot.db.execute("DELETE FROM guessthenumber WHERE guild_id = $1 AND channel_id = $2", message.guild.id, message.channel.id)
                    settings = await self.bot.db.fetchrow("SELECT * FROM guessthenumber_settings WHERE guild_id = $1", message.guild.id)
                    if settings:
                        if settings['lock'] == True:
                            check_roles = await self.bot.db.fetch("SELECT * FROM lockdown_role WHERE guild_id = $1", message.guild.id)
                            if not check_roles:
                                pass
                            roles = [message.guild.get_role(role["role_id"]) for role in check_roles if message.guild.get_role(role["role_id"])]
                            if not roles:
                                pass
                            if isinstance(message.channel, TextChannel):
                                overwrites = {role: message.channel.overwrites_for(role) for role in roles}
                                if all(ow.send_messages is False for ow in overwrites.values()):
                                    pass
                                for role, overwrite in overwrites.items():
                                    overwrite.send_messages = False
                                    await message.channel.set_permissions(role, overwrite=overwrite, reason=f"Channel locked by {message.author}")
                else:
                    pass
            else:
                pass

    async def on_snipe_event(self, message: Message):
        if not message.guild or not message.author or message.author.bot:
            return
        attachment_urls = []
        for attachment in message.attachments:
            try:
                file_data = await attachment.read()
                file_extension = attachment.filename.split('.')[-1]
                file_name = f"{str(uuid.uuid4())[:8]}.{file_extension}"
                content_type = attachment.content_type
                upload_res = await self.bot.r2.upload_file("evelina-attachments", file_data, file_name, content_type)
                if upload_res:
                    attachment_urls.append(f"https://attachments.evil.bio/evelina-attachments/{file_name}")
            except NotFound:
                continue
        return await self.bot.db.execute("INSERT INTO snipes (channel_id, author_id, message_content, attachments, stickers, created_at) VALUES ($1, $2, $3, $4, $5, $6)", message.channel.id, message.author.id, message.content, attachment_urls, [sticker.url for sticker in message.stickers], int(datetime.now().timestamp()))

    async def on_counting_event(self, message):
        if not message.guild or not message.author or message.author.bot:
            return
        counter_data = await self.bot.db.fetchrow("SELECT channel_id, current_number, last_counted FROM number_counter WHERE guild_id = $1", message.guild.id)
        if not counter_data:
            return
        channel_id, current_number, last_counted = counter_data
        if message.channel.id != channel_id:
            return
        def evaluate_math(expression):
            try:
                expression = re.sub(r'(\d+(\.\d+)?)(\s*[-+/*]\s*)(\d+(\.\d+)?)%', r'\1\3(\1 * \4 / 100)', expression)
                result = eval(expression, {"__builtins__": None}, {"sqrt": math.sqrt, "pow": math.pow, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi, "e": math.e})
                return result
            except Exception:
                return None
        clean_content = message.content.replace(" ", "")
        try:
            number = evaluate_math(clean_content) if re.search(r"[+\-*/%]", clean_content) else int(clean_content)
            if number is None:
                number = int(clean_content)
        except (ValueError, TypeError):
            return
        if message.author.id == last_counted:
            previous_number = current_number - 1
            if number == previous_number:
                await message.channel.send(f"{message.author.mention} deleted **{previous_number}** their last count. The next number is **{current_number}**")

    async def on_bulk_message_delete_logging(self, messages: List[Message]):
        messages = messages[::-1]
        guild = messages[0].guild
        message_channel = messages[0].channel
        if await self.log.is_ignored(guild.id, "channels", message_channel.id):
            return
        record = await self.bot.db.fetchval("SELECT messages FROM logging WHERE guild_id = $1", guild.id)
        channel = await self.log.fetch_logging_channel(guild, record)
        if isinstance(channel, (TextChannel, Thread)):
            if not channel.permissions_for(channel.guild.me).send_messages:
                return
            if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                return
            async with self.locks[guild.id]:
                button = Button(label="Message", style=ButtonStyle.link, url=f"https://discord.com/channels/{guild.id}/{message_channel.id}/{messages[0].id}")
                view = View()
                view.add_item(button)
                text_file = BytesIO()
                text_file.write(
                    bytes("\n".join([f"[{idx}] {message.author}: {message.clean_content}" for idx, message in enumerate(messages, start=1)]), encoding="utf-8"))
                text_file.seek(0)
                embed = (Embed(color=colors.NEUTRAL, title="Bulk Message Delete", description=f"`{len(messages)}` messages got deleted", timestamp=datetime.now()))
                embed.add_field(name="Channel", value=f"<#{message_channel.id}> (`{message_channel.id}`)", inline=False)
                embed.set_footer(text=f"ID: {messages[0].id}")
                file = File(text_file, filename="messages.txt")
                await self.log.add_to_queue(channel, embed, view, file)

    async def on_message_delete_logging(self, message: Message):
        if not message.author.bot and message.guild is not None:
            if await self.log.is_ignored(message.guild.id, "users", message.author.id) or await self.log.is_ignored(message.guild.id, "channels", message.channel.id):
                return
            record = await self.bot.db.fetchval("SELECT messages FROM logging WHERE guild_id = $1", message.guild.id)
            channel = await self.log.fetch_logging_channel(message.guild, record)
            if isinstance(channel, (TextChannel, Thread)):
                if not channel.permissions_for(channel.guild.me).send_messages:
                    return
                if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                    return
                async with self.locks[message.guild.id]:
                    button = Button(label="Message", style=ButtonStyle.link,  url=f"https://discord.com/channels/{message.guild.id}/{message.channel.id}/{message.id}")
                    view = View()
                    view.add_item(button)
                    embed = Embed(color=colors.NEUTRAL, title="Message Deleted", description=(message.content if message.content != "" else "No Content"), timestamp=datetime.now())
                    embed.set_author(name=str(message.author), icon_url=message.author.avatar.url if message.author.avatar else None)
                    embed.add_field(name="Channel", value=f"<#{message.channel.id}> (`{message.channel.id}`)")
                    embed.set_footer(text=f"ID: {message.id}")
                    file = None
                    if attachment := next(iter(message.attachments), None):
                        try:
                            file_data = await attachment.read()
                            if file_data:
                                if attachment.filename.endswith(("jpg", "png", "gif", "jpeg")):
                                    file = File(BytesIO(file_data), filename=attachment.filename)
                                    embed.set_image(url=f"attachment://{attachment.filename}")
                                else:
                                    file = File(BytesIO(file_data), filename=attachment.filename)
                        except NotFound:
                            embed.add_field(name="Attachment", value="Attachment not found", inline=False)
                    if sticker := next(iter(message.stickers), None):
                        embed.set_image(url=sticker.url)
                        if embed.description != "No Content":
                            embed.description = sticker.name
                    await self.log.add_to_queue(channel, embed, view, file)

    async def on_editsnipe_event(self, before: Message, after: Message):
        if before.author.bot or before.content == after.content:
            return
        await self.bot.db.execute("INSERT INTO snipes_edit (channel_id, author_id, before_content, after_content, created_at) VALUES ($1, $2, $3, $4, $5)", before.channel.id, before.author.id, before.content, after.content, int(datetime.now().timestamp()))

    async def on_countingedit_event(self, before, after):
        if before.author.bot:
            return
        if not before.guild:
            return
        counter_data = await self.bot.db.fetchrow("SELECT channel_id, current_number, last_counted FROM number_counter WHERE guild_id = $1", before.guild.id)
        if not counter_data:
            return
        channel_id, current_number, last_counted = counter_data
        if before.channel.id != channel_id:
            return
        def evaluate_math(expression):
            try:
                original_expression = expression
                expression = re.sub(r'(\d+(\.\d+)?)(\s*[-+/*]\s*)(\d+(\.\d+)?)%', r'\1\3(\1 * \4 / 100)', expression)
                result = eval(expression, {"__builtins__": None}, {"sqrt": math.sqrt, "pow": math.pow, "sin": math.sin, "cos": math.cos, "tan": math.tan, "pi": math.pi, "e": math.e})
                return result
            except Exception:
                return None
        clean_content = after.content.replace(" ", "")
        try:
            number = evaluate_math(clean_content) if re.search(r"[+\-*/%]", clean_content) else int(clean_content)
            if number is None:
                number = int(clean_content)
        except (ValueError, TypeError):
            return
        if before.author.id == last_counted:
            previous_number = current_number - 1
            await after.channel.send(f"{before.author.mention} edited **{previous_number}** their last count. The next number is **{current_number}**")

    async def on_message_edit_logging(self, before: Message, after: Message):
        if not before.author.bot:
            if before.guild is None:
                return
            if before.content == after.content:
                return
            if await self.log.is_ignored(before.guild.id, "users", before.author.id) or await self.log.is_ignored(before.guild.id, "channels", before.channel.id):
                return
            record = await self.bot.db.fetchval("SELECT messages FROM logging WHERE guild_id = $1", before.guild.id)
            channel = await self.log.fetch_logging_channel(before.guild, record)
            if isinstance(channel, (TextChannel, Thread)):
                if not channel.permissions_for(channel.guild.me).send_messages:
                    return
                if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                    return
                async with self.locks[before.guild.id]:
                    button = Button(label="Message", style=ButtonStyle.link, url=f"https://discord.com/channels/{before.guild.id}/{before.channel.id}/{before.id}")
                    view = View()
                    view.add_item(button)
                    before_content = before.content[:1021] + '...' if len(before.content) > 1024 else before.content
                    after_content = after.content[:1021] + '...' if len(after.content) > 1024 else after.content
                    embed = (
                        Embed(color=colors.NEUTRAL, title="Message Edit", timestamp=datetime.now(), description=f"{before.author.mention} edited a message")
                        .set_author(name=str(after.author), icon_url=after.author.avatar.url if after.author.avatar else None)
                        .add_field(name="Before", value=before_content, inline=False)
                        .add_field(name="After", value=after_content, inline=False)
                        .add_field(name="Channel", value=f"<#{after.channel.id}> (`{after.channel.id}`)")
                        .set_footer(text=f"ID: {after.id}")
                    )
                    await self.log.add_to_queue(channel, embed, view)

    async def on_message_edit_link(self, before: Message, after: Message):
        if not before.author.bot and before.guild:
            if before.content != after.content:
                if "http://" in after.content or "https://" in after.content:
                    if not before.author:
                        return
                    blacklist_users, blacklist_channels, blacklist_roles = await self.get_blacklist(before.guild.id)
                    if (before.author.id in set(blacklist_users) or before.channel.id in set(blacklist_channels) or any(role.id in set(blacklist_roles) for role in before.author.roles)):
                        return
                    check = await self.bot.db.fetchrow("SELECT * FROM antinuke_linksedit WHERE guild_id = $1", before.guild.id)
                    if not check:
                        return
                    if not check['status']:
                        return
                    try:
                        await after.delete()
                    except Exception:
                        pass