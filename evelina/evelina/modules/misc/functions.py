import time
import json
import asyncio
import random
import datetime
import logging
import discord

from time import time
from datetime import timedelta
from epic_games_free import EpicGames

from discord import Embed, AllowedMentions, utils, Forbidden
from discord.ui import View, Button
from discord.ext.commands import AutoShardedBot as AB

from data.pfps import PFPS

from modules.styles import emojis, colors, icons
from modules.persistent.giveaway import GiveawayEndedView

from cogs.moderation import Moderation

logger = logging.getLogger(__name__)
nuke_lock = asyncio.Lock()

async def ensure_guild_chunked(guild):
    if not guild.chunked:
        await guild.chunk(cache=True)

async def reminder(bot: AB):
    current_time = int(datetime.datetime.now().timestamp())
    results = await bot.db.fetch("SELECT * FROM reminder WHERE time <= $1", current_time)
    for result in results:
        channel = bot.get_channel(int(result["channel_id"]))
        if channel:
            await ensure_guild_chunked(channel.guild)
            perms = channel.permissions_for(channel.guild.me)
            if perms.send_messages and perms.embed_links:
                await channel.send(f"🕐 <@{result['user_id']}> - {result['task']}")
            await bot.db.execute("DELETE FROM reminder WHERE guild_id = $1 AND user_id = $2 AND channel_id = $3 AND time = $4", channel.guild.id, result["user_id"], channel.id, result["time"])

async def bump(bot):
    current_time = datetime.datetime.now()
    results = await bot.db.fetch("SELECT channel_id, reminder, user_id FROM bumpreminder WHERE time <= $1", current_time,)
    for channel_id, reminder_text, user_id in results:
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        await ensure_guild_chunked(channel.guild)
        member = channel.guild.get_member(user_id) or channel.guild.owner
        try:
            embed_data = await bot.embed_build.alt_convert(member, reminder_text)
            embed_data["allowed_mentions"] = AllowedMentions.all()
            await channel.send(**embed_data)
        except Exception:
            continue
        await bot.db.execute("UPDATE bumpreminder SET time = NULL, channel_id = NULL, user_id = NULL WHERE channel_id = $1", channel_id,)

async def vote(bot: AB):
    current_timestamp = datetime.datetime.now().timestamp()
    results = await bot.db.fetch("SELECT user_id FROM votes WHERE vote_until < $1 AND vote_reminder = TRUE", current_timestamp,)
    embed = Embed(color=0xFF819F, description=f"{emojis.HEART} Don't forget to vote for Evelina on top.gg!")
    view = View()
    view.add_item(Button(label="Vote on Top.gg", url="https://top.gg/bot/1242930981967757452"))
    updated_users = []
    for record in results:
        user = bot.get_user(record["user_id"])
        if user:
            try:
                await user.send(embed=embed, view=view)
                updated_users.append(record["user_id"])
            except Forbidden:
                continue
    if updated_users:
        await bot.db.execute("UPDATE votes SET vote_until = NULL WHERE user_id = ANY($1::bigint[])", updated_users,)

async def giveaway(bot: AB):
    results = await bot.db.fetch("SELECT * FROM giveaway WHERE finish <= $1", datetime.datetime.now())
    for result in results:
        await giveaway_end(bot, result)

async def giveaway_end(bot: AB, result):
    guild = bot.get_guild(result["guild_id"])
    if not guild: return
    try:
        channel = guild.get_channel(result["channel_id"]) or await guild.fetch_channel(result["channel_id"])
        message = await channel.fetch_message(result["message_id"])
    except (discord.NotFound, discord.Forbidden): return
    members, winners = json.loads(result["members"]), result["winners"]
    timestamp = int(datetime.datetime.now().timestamp())
    if len(members) <= winners:
        desc = f"**Ended:** <t:{timestamp}> (<t:{timestamp}:R>)\n**Hosted by:** <@!{result['host']}>\n**Winners:** {winners}\n\n> Not enough entries to determine the winners!"
        wins = []
    else:
        wins = random.sample(members, winners)
        desc = f"**Ended:** <t:{timestamp}> (<t:{timestamp}:R>)\n**Hosted by:** <@!{result['host']}>\n**Winners:** {', '.join([f'<@{w}>' for w in wins])}"
    embed = Embed(color=colors.NEUTRAL, title=message.embeds[0].title, description=desc)
    embed.add_field(name="Entries", value=len(members), inline=True)
    for key, label in [("required_bonus", "Bonus"), ("required_role", "Role"), ("required_messages", "Messages"), ("required_level", "Level"), ("required_invites", "Invites")]:
        if result[key]: embed.add_field(name=label, value=f"<@&{result[key]}>" if "role" in key or "bonus" in key else result[key])
    await message.edit(embed=embed, view=GiveawayEndedView(bot))
    if wins:
        try:
            await message.reply(f"**{result['title']}** winners:\n" + "\n".join([f"<@{w}> (`{w}`)" for w in wins]))
        except Forbidden: pass
    await bot.db.execute("INSERT INTO giveaway_ended VALUES ($1,$2,$3)", result["channel_id"], result["message_id"], json.dumps(members))
    await bot.db.execute("DELETE FROM giveaway WHERE channel_id = $1 AND message_id = $2", result["channel_id"], result["message_id"])

async def nuke(bot: AB):
    scheduled_nukes = await bot.db.fetch("SELECT * FROM nuke_scheduler")
    if not scheduled_nukes: return
    async with nuke_lock:
        for nuke in scheduled_nukes:
            if int(datetime.datetime.now().timestamp()) < nuke['last_nuke'] + nuke['schedule']:
                continue
            guild = bot.get_guild(nuke['guild_id'])
            if not guild:
                continue
            channel = guild.get_channel(nuke['channel_id'])
            if not channel:
                continue
            try:
                await bot.db.execute("UPDATE nuke_scheduler SET last_nuke = $1 WHERE guild_id = $2 AND channel_id = $3", int(datetime.datetime.now().timestamp()), guild.id, channel.id)
                new_channel = await channel.clone(reason="Nuke Schedule: channel nuked")
                await new_channel.edit(position=channel.position)
                setups_restored = []
                for table in ("welcome", "leave", "boost", "nuke_scheduler", "stickymessage", "channel_disabled_commands", "channel_disabled_module"):
                    exists = await bot.db.fetchrow(f"SELECT 1 FROM {table} WHERE guild_id = $1 AND channel_id = $2", guild.id, channel.id)
                    if exists:
                        await bot.db.execute(f"UPDATE {table} SET channel_id = $1 WHERE guild_id = $2 AND channel_id = $3", new_channel.id, guild.id, channel.id)
                        setups_restored.append(f"- restored {table.replace('_', ' ')} setup")
                await channel.delete(reason="Nuke Schedule: channel nuked")
                em = Embed(description="### 💣 Channel nuked by schedule", color=colors.NEUTRAL)
                if setups_restored:
                    em.add_field(name="Restored Setups", value='\n'.join(setups_restored))
                await new_channel.send(embed=em)
                await bot.db.execute("UPDATE nuke_scheduler SET channel_id = $1 WHERE guild_id = $2 AND channel_id = $3", new_channel.id, guild.id, channel.id)
            except Exception:
                continue

# async def twitch(bot: AB):
#     results = await bot.db.fetch("SELECT channel_id, streamer, message FROM autopost_twitch")
#     for row in results:
#         channel_id, streamer, message = row
#         stream_data = await bot.twitch.fetch_stream_data(streamer)
#         if stream_data["is_live"]:
#             check = await bot.db.fetchrow("SELECT * FROM autopost_twitch_announced WHERE stream_id = $1 AND channel_id = $2", stream_data['stream_id'], channel_id)
#             if not check or check is None:
#                 channel = bot.get_channel(channel_id)
#                 if channel:
#                     view = discord.ui.View()
#                     view.add_item(discord.ui.Button(label="Watch", url=f"https://twitch.tv/{streamer}", emoji=emojis.TWITCH))
#                     try:
#                         embed=Embed(
#                             title=f"{streamer} is now live! 🎥",
#                             description=stream_data['title'],
#                             url=f"https://twitch.tv/{streamer}",
#                             timestamp=datetime.datetime.now(),
#                             color=colors.TWITCH
#                         )
#                         embed.add_field(name="👀 Viewers", value=stream_data["viewers"], inline=True)
#                         embed.add_field(name="🎮 Game", value=stream_data["game"], inline=True)
#                         embed.set_image(url=stream_data["thumbnail_url"].format(width=640, height=360))
#                         embed.set_footer(text="Twitch")
#                         await channel.send(content=message if message else "", embed=embed, view=view, allowed_mentions=discord.AllowedMentions.all())
#                         return await bot.db.execute("INSERT INTO autopost_twitch_announced VALUES ($1, $2)", channel_id, stream_data['stream_id'])
#                     except Exception:
#                         continue

async def pingtimeout(bot: AB):
    now = datetime.datetime.now().timestamp()
    results = await bot.db.fetch("SELECT guild_id, role_id FROM pingtimeout WHERE last_ping + timeout <= $1", now)
    for guild_id, role_id in results:
        guild = bot.get_guild(guild_id)
        role = guild and guild.get_role(role_id)
        if role and not role.mentionable:
            await role.edit(mentionable=True)

async def revive(bot: AB):
    now = datetime.datetime.now().timestamp()
    results = await bot.db.fetch("SELECT guild_id, channel_id, message, last_revive FROM revive WHERE last_message + timeout <= $1", now)
    for guild_id, channel_id, message, last_revive in results:
        guild = bot.get_guild(guild_id)
        if not guild:
            continue
        channel = guild.get_channel(channel_id)
        if not channel:
            continue
        if channel.last_message_id == last_revive:
            continue
        try:
            owner = channel.guild.owner
            x = await bot.embed_build.alt_convert(owner, message)
            x["allowed_mentions"] = AllowedMentions.all()
            msg = await channel.send(**x)
            await bot.db.execute("UPDATE revive SET last_message = $1, last_revive = $2 WHERE guild_id = $3 AND channel_id = $4", datetime.datetime.now().timestamp(), msg.id, guild_id, channel_id)
        except Exception:
            continue

async def blacklist(bot: AB):
    now = datetime.datetime.now().timestamp()
    tables = [
        ("blacklist_user", "user_id"),
        ("blacklist_server", "guild_id"),
        ("blacklist_cog", "user_id"),
        ("blacklist_cog_server", "guild_id"),
        ("blacklist_command", "user_id"),
        ("blacklist_command_server", "guild_id"),
    ]
    for table, id_col in tables:
        expired = await bot.db.fetch(f"SELECT {id_col} FROM {table} WHERE duration IS NOT NULL AND (timestamp + duration) <= $1", now)
        if expired:
            await bot.db.execute(f"DELETE FROM {table} WHERE {id_col} = ANY($1::BIGINT[])", [row[id_col] for row in expired])

async def twitter(bot: AB):
    results = await bot.db.fetch("SELECT channel_id, username, message FROM autopost_twitter")
    for row in results:
        channel_id, username, message = row
        tweet = await bot.social.fetch_twitter_post(username)
        if tweet:
            check = await bot.db.fetchrow("SELECT * FROM autopost_twitter_announced WHERE tweet_id = $1 AND channel_id = $2", tweet['tweet_id'], channel_id)
            if not check or check is None:
                channel = bot.get_channel(channel_id)
                if channel:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="View Tweet", url=f"https://x.com/{username}/status/{tweet['tweet_id']}", emoji=emojis.TWITTER))
                    try:
                        embed = Embed(
                            title=f"{username} tweeted! 🐦",
                            description=tweet['text'],
                            url=f"https://x.com/{username}/status/{tweet['tweet_id']}",
                            timestamp=datetime.datetime.now(),
                            color=colors.TWITTER
                        )
                        embed.set_image(url=tweet['media']['photo'][0]['media_url_https'] if tweet['media'] and 'photo' in tweet['media'] else None)
                        embed.set_footer(text="Twitter", icon_url=icons.TWITTER)
                        file_url = tweet['media']['video'][0]['variants'][4]['url'] if tweet['media'] and 'video' in tweet['media'] else None
                        if file_url:
                            file = discord.File(fp=await bot.getbyte(file_url), filename="evelinatweet.mp4")
                            await channel.send(content=message if message else "", embed=embed, view=view, file=file, allowed_mentions=discord.AllowedMentions.all())
                        else:
                            await channel.send(content=message if message else "", embed=embed, view=view, allowed_mentions=discord.AllowedMentions.all())
                        return await bot.db.execute("INSERT INTO autopost_twitter_announced VALUES ($1, $2)", channel_id, tweet['tweet_id'])
                    except Exception:
                        continue

async def youtube(bot: AB):
    results = await bot.db.fetch("SELECT channel_id, username, message FROM autopost_youtube")
    for row in results:
        channel_id, username, message = row
        youtube_channel_id = await bot.social.fetch_youtube_channel(username)
        if not youtube_channel_id:
            continue
        video = await bot.social.fetch_youtube_video(youtube_channel_id)
        if video:
            check = await bot.db.fetchrow("SELECT * FROM autopost_youtube_announced WHERE video_id = $1 AND channel_id = $2", video['video_id'], channel_id)
            if not check or check is None:
                channel = bot.get_channel(channel_id)
                if channel:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Watch Video", url=f"https://youtube.com/watch?v={video['video_id']}", emoji=emojis.YOUTUBE))
                    try:
                        embed = Embed(
                            title=f"{username} uploaded a new video! 🎥",
                            description=video['title'],
                            url=f"https://youtube.com/watch?v={video['video_id']}",
                            timestamp=datetime.datetime.now(),
                            color=colors.YOUTUBE
                        )
                        embed.set_image(url=video['thumbnails'][3]['url'].format(width=640, height=360) if video['thumbnails'] else None)
                        embed.set_footer(text="YouTube", icon_url=icons.YOUTUBE)
                        await channel.send(content=message if message else "", embed=embed, view=view, allowed_mentions=discord.AllowedMentions.all())
                        return await bot.db.execute("INSERT INTO autopost_youtube_announced VALUES ($1, $2)", channel_id, video['video_id'])
                    except Exception:
                        continue

async def tiktok(bot: AB):
    results = await bot.db.fetch("SELECT channel_id, username, message FROM autopost_tiktok")
    for row in results:
        channel_id, username, message = row
        video = await bot.social.fetch_tiktok_video(username)
        if video:
            check = await bot.db.fetchrow("SELECT * FROM autopost_tiktok_announced WHERE video_id = $1 AND channel_id = $2", video['aweme_id'], channel_id)
            if not check or check is None:
                channel = bot.get_channel(channel_id)
                if channel:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="Watch Video", url=video['share_url'], emoji=emojis.TIKTOK))
                    try:
                        embed = Embed(
                            title=f"{username} uploaded a new video! 🎥",
                            description=video['desc'],
                            url=video['share_url'],
                            timestamp=datetime.datetime.now(),
                            color=colors.TIKTOK
                        )
                        embed.set_footer(text="TikTok", icon_url=icons.TIKTOK)
                        file_url = video['video']['play_addr']['url_list'][0] if video['video'] and 'play_addr' in video['video'] else None
                        if file_url:
                            file = discord.File(fp=await bot.getbyte(file_url), filename="evelinatiktok.mp4")
                            await channel.send(content=message if message else "", embed=embed, file=file, view=view, allowed_mentions=discord.AllowedMentions.all())
                            return await bot.db.execute("INSERT INTO autopost_tiktok_announced VALUES ($1, $2)", channel_id, video['aweme_id'])
                    except Exception:
                        continue

async def instagram(bot: AB):
    results = await bot.db.fetch("SELECT channel_id, username, message FROM autopost_instagram")
    for row in results:
        channel_id, username, message = row
        post = await bot.social.fetch_instagram_post(username)
        if post:
            check = await bot.db.fetchrow("SELECT * FROM autopost_instagram_announced WHERE post_id = $1 AND channel_id = $2", post['code'], channel_id)
            if not check or check is None:
                channel = bot.get_channel(channel_id)
                if channel:
                    view = discord.ui.View()
                    view.add_item(discord.ui.Button(label="View Post", url=f"https://instagram.com/p/{post['code']}", emoji=emojis.INSTAGRAM))
                    try:
                        embed = Embed(
                            title=f"{username} posted! 📸",
                            description=post['caption']['text'] if 'caption' in post else None,
                            url=f"https://instagram.com/p/{post['code']}",
                            timestamp=datetime.datetime.now(),
                            color=colors.INSTAGRAM
                        )
                        embed.set_footer(text="Instagram", icon_url=icons.INSTAGRAM)
                        files = []
                        post_details = await bot.social.fetch_instagram_post_details(post['code'])
                        if post_details:
                            if post_details['is_video']:
                                file_url = post_details['video_url'] if 'video_url' in post_details else None
                                if file_url:
                                    file = discord.File(fp=await bot.getbyte(file_url), filename="evelinainstagram.mp4")
                                    files.append(file)
                            else:
                                file_url = post_details['image_versions']['items'][0]['url'] if 'image_versions' in post_details else None
                                if file_url:
                                    file = discord.File(fp=await bot.getbyte(file_url), filename="evelinainstagram.png")
                                    files.append(file)
                        if files:
                            await channel.send(content=message if message else "", embed=embed, files=files, view=view, allowed_mentions=discord.AllowedMentions.all())
                            return await bot.db.execute("INSERT INTO autopost_instagram_announced VALUES ($1, $2)", channel_id, post['code'])
                        else:
                            await channel.send(content=message if message else "", embed=embed, view=view, allowed_mentions=discord.AllowedMentions.all())
                            return await bot.db.execute("INSERT INTO autopost_instagram_announced VALUES ($1, $2)", channel_id, post['code'])
                    except Exception:
                        continue

async def leaderboard(bot: AB):
    results = await bot.db.fetch("SELECT * FROM activity_leaderboard")
    valid_tables = {"message": "activity_messages", "voice": "activity_voice"}
    valid_ranges = {"1d": 1, "7d": 7, "30d": 30, "lifetime": None}
    cooldowns = {}
    for row in results:
        guild = bot.get_guild(row["guild_id"])
        if not guild:
            continue
        channel = guild.get_channel(row["channel_id"])
        if not channel:
            continue
        if channel.id in cooldowns and cooldowns[channel.id] > datetime.datetime.now():
            await asyncio.sleep(5)
        try:
            message = await channel.fetch_message(row["message_id"])
        except discord.NotFound:
            continue
        time_range = valid_ranges.get(row["range"])
        time_condition = f"AND {row['type']}_date >= (CURRENT_DATE - INTERVAL '{time_range} days')" if time_range else ""
        column_name = "voice_time" if row['type'] == "voice" else "message_count"
        query = f"""
            SELECT user_id, SUM({column_name}) as value 
            FROM {valid_tables[row['type']]}
            WHERE server_id = $1 {time_condition}
            GROUP BY user_id 
            ORDER BY value DESC 
            LIMIT 10
        """
        top_members = await bot.db.fetch(query, guild.id)
        if not top_members:
            continue
        formatted_range = {
            "1d": "Daily",
            "7d": "Weekly",
            "30d": "Monthly",
            "lifetime": "Lifetime"
        }.get(row["range"], "Unknown")
        embed = Embed(
            color=colors.NEUTRAL,
            title=f"{row['type'].capitalize()} Leaderboard [{formatted_range}]",
            timestamp=datetime.datetime.now()
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
        embed.set_footer(text="Last updated", icon_url=guild.icon.url if guild.icon else None)
        description = []
        for index, member in enumerate(top_members, start=1):
            value = (
                f"{member['value']:,} message"
                if row["type"] == "message"
                else bot.misc.humanize_time(member["value"], True, "HH-MM-SS")
            )
            description.append(f"{getattr(emojis, f'NUMBER_{index}', '')} <@{member['user_id']}>: **{value}**")
        embed.description = "\n".join(description)
        await message.edit(embed=embed)
        cooldowns[channel.id] = datetime.datetime.now() + datetime.timedelta(seconds=5)
        await asyncio.sleep(1)

async def jail(bot: AB):
    now = datetime.datetime.utcnow()
    results = await bot.db.fetch("SELECT guild_id, user_id, roles FROM jail_members WHERE jailed_until <= $1", now)
    for guild_id, user_id, stored_roles in results:
        guild = bot.get_guild(guild_id)
        if not guild: continue
        member = guild.get_member(user_id)
        jail_info = await bot.db.fetchrow("SELECT role_id FROM jail WHERE guild_id = $1", guild_id)
        if not member or not jail_info: continue
        jail_role = guild.get_role(jail_info["role_id"])
        if not jail_role: continue
        try:
            roles = [guild.get_role(r) for r in json.loads(stored_roles) if guild.get_role(r)]
            roles = [r for r in roles if r.position < guild.me.top_role.position]
            if guild.premium_subscriber_role in member.roles:
                roles.append(guild.premium_subscriber_role)
            await member.edit(roles=roles, reason="Jail time expired")
            embed = Embed(description=f"You have been automatically unjailed on **{guild.name}** as your jail time expired.", color=colors.SUCCESS)
            try:
                await member.send(embed=embed)
            except Exception:
                pass
            await bot.db.execute("DELETE FROM jail_members WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
            current_timestamp = utils.utcnow().timestamp()
            history_id = await bot.db.fetchval(
                """INSERT INTO history (id, guild_id, user_id, moderator_id, server_id, punishment, duration, reason, time)
                   VALUES ((SELECT COALESCE(MAX(id),0)+1 FROM history),
                           (SELECT COALESCE(MAX(guild_id),0)+1 FROM history WHERE server_id = $1),
                           $2, $3, $4, 'Unjail', 'None', 'Automatic unjail (time expired)', $5)
                   RETURNING guild_id""",
                guild_id, user_id, bot.user.id, guild_id, current_timestamp
            )
            await Moderation(bot).logging(guild, member, bot.user, "Automatic unjail (time expired)", "unjailed", "Unjail", history_id)
        except Exception:
            continue

async def timer(bot: AB):
    now = datetime.datetime.now().timestamp()
    results = await bot.db.fetch('SELECT channel_id, code FROM timer WHERE time + "interval" <= $1', now)
    for channel_id, code in results:
        channel = bot.get_channel(channel_id)
        if not channel:
            continue
        await ensure_guild_chunked(channel.guild)
        owner = channel.guild.owner
        embed_data = await bot.embed_build.alt_convert(owner, code)
        embed_data["allowed_mentions"] = AllowedMentions.all()
        await channel.send(**embed_data)
        await bot.db.execute("UPDATE timer SET time = $1 WHERE channel_id = $2", now, channel_id)

async def autoposting_pfps(bot):
    if bot.pfps_send:
        await autoposting(bot, "pfps")

async def autoposting_banners(bot):
    if bot.banners_send:
        await autoposting(bot, "banners")

async def autoposting(bot, kind: str):
    if getattr(bot, f"{kind}_send"):
        results = await bot.db.fetch("SELECT * FROM autopost WHERE type = $1", kind)
        for result in results:
            if channel := bot.get_channel(result['channel_id']):
                try:
                    if result['category'] == "random":
                        category = random.choice(["females", "males", "animes"])
                    else:
                        category = result['category']
                    categories = getattr(PFPS, category, [])
                    if not categories:
                        continue
                    selected_image = random.choice(categories)
                    image_id = categories.index(selected_image)
                    guild: discord.Guild = bot.get_guild(result['guild_id'])
                    embed = (
                        discord.Embed(color=colors.NEUTRAL)
                        .set_image(url=selected_image)
                        .set_footer(text=f"{kind} module: {category.lower()} • id {image_id} • /{guild.vanity_url_code}")
                    )
                    webhooks = await channel.webhooks()
                    webhook = discord.utils.get(webhooks, name="Autopost Webhook")
                    if webhook is None:
                        webhook = await channel.create_webhook(name="Autopost Webhook")
                    if result['webhook_name']:
                        webhook_name = result['webhook_name']
                    else:
                        webhook_name = bot.user.name
                    if result['webhook_avatar']:
                        webhook_avatar = result['webhook_avatar']
                    else:
                        webhook_avatar = bot.user.avatar.url if bot.user.avatar else None
                    try:
                        await webhook.send(embed=embed, username=webhook_name, avatar_url=webhook_avatar)
                    except discord.errors.NotFound:
                        await bot.db.execute("DELETE FROM autopost WHERE channel_id = $1", result['channel_id'])
                    except discord.errors.HTTPException as e:
                        if 'username' in str(e):
                            await bot.db.execute("UPDATE autopost SET webhook_name = NULL WHERE channel_id = $1", result['channel_id'])
                        if 'avatar_url' in str(e):
                            await bot.db.execute("UPDATE autopost SET webhook_avatar = NULL WHERE channel_id = $1", result['channel_id'])
                except discord.errors.Forbidden:
                    await bot.db.execute("DELETE FROM autopost WHERE channel_id = $1", result['channel_id'])
                except Exception as e:
                    guild_id = getattr(channel.guild, 'id', '[ERROR]')
                    await bot.get_channel(bot.logging_report).send(f"{kind} posting error - {e} in `{guild_id}`")

async def voicetrack(bot: AB):
    current_time = int(time())
    results = await bot.db.fetch("SELECT * FROM voicetrack WHERE joined_time IS NOT NULL OR muted_time IS NOT NULL")
    for result in results:
        guild = bot.get_guild(result['guild_id'])
        if not guild: continue
        member = guild.get_member(result['user_id'])
        total_time, mute_time = result['total_time'], result['mute_time'] or 0
        joined_time, muted_time = result['joined_time'], result['muted_time']
        if not member or not member.voice:
            await bot.db.execute("UPDATE voicetrack SET joined_time = NULL, muted_time = NULL WHERE guild_id = $1 AND user_id = $2", guild.id, result['user_id'])
            continue
        time_spent = current_time - joined_time if joined_time else 0
        mute_duration = current_time - muted_time if muted_time else 0
        total_time += time_spent
        mute_time += mute_duration if muted_time else 0
        muted_now = member.voice.mute or member.voice.self_mute
        new_muted_time = current_time if muted_now else None
        await bot.db.execute(
            """UPDATE voicetrack SET
                total_time = $1, joined_time = $2,
                mute_time = $3, muted_time = $4
               WHERE guild_id = $5 AND user_id = $6""",
            total_time, current_time if joined_time else None,
            mute_time, new_muted_time, guild.id, member.id
        )
        voice_date = datetime.datetime.utcnow().date()
        channel_id = member.voice.channel.id
        if time_spent > 0:
            await bot.db.execute(
                """
                INSERT INTO activity_voice (user_id, channel_id, server_id, voice_date, voice_time)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id, channel_id, server_id, voice_date)
                DO UPDATE SET voice_time = activity_voice.voice_time + $5
                """,
                member.id,
                channel_id,
                guild.id,
                voice_date,
                time_spent
            )
        settings = await bot.db.fetchrow("SELECT level_state FROM voicetrack_settings WHERE guild_id = $1", guild.id)
        if settings and settings['level_state'] and joined_time and time_spent:
            await bot.level.add_voice_xp(member, time_spent, guild.id)

async def counter(bot: AB):
    results = await bot.db.fetch("SELECT * FROM counters")
    for result in results:
        channel = bot.get_channel(int(result["channel_id"]))
        if channel:
            guild = channel.guild
            await ensure_guild_chunked(guild)
            if not guild.me.guild_permissions.manage_channels:
                continue
            module = result["module"]
            match module:
                case "members":
                    target = str(guild.member_count)
                case "humans":
                    target = str(len([m for m in guild.members if not m.bot]))
                case "bots":
                    target = str(len([m for m in guild.members if m.bot]))
                case "boosters":
                    target = str(len(guild.premium_subscribers))
                case "voice":
                    target = str(sum(len(c.members) for c in guild.voice_channels))
                case "role":
                    role = channel.guild.get_role(int(result["role_id"]))
                    if role:
                        target = str(len(role.members))
                    else:
                        continue
                case "boosts":
                    target = str(guild.premium_subscription_count)
            name = result["channel_name"].replace("{target}", target)
            await channel.edit(name=name, reason="updating counter")

async def snipe(bot: AB):
    now = datetime.datetime.now()
    six_hours_ago = now - timedelta(hours=6)
    for table in ["snipes", "snipes_edit", "snipes_reaction"]:
        await bot.db.execute(f"DELETE FROM {table} WHERE created_at < $1", int(six_hours_ago.timestamp()))

async def birthday(bot: AB):
    results = await bot.db.fetch("SELECT * FROM birthday_reward")
    for result in results:
        guild = bot.get_guild(result["guild_id"])
        if not guild:
            continue
        birthdays = {row["user_id"]: row for row in await bot.db.fetch("SELECT * FROM birthday WHERE user_id = ANY($1)", [m.id for m in guild.members if not m.bot])}
        today = datetime.datetime.now()
        role = guild.get_role(result["role_id"])
        if not role:
            continue
        for member in guild.members:
            if member.bot:
                continue
            birthday = birthdays.get(member.id)
            if not birthday:
                continue
            if birthday["day"] == today.day and birthday["month"] == today.month:
                await member.add_roles(role, reason="Birthday Role")
            else:
                await member.remove_roles(role, reason="Birthday Role")

async def freegames(bot: AB):
    results = await bot.db.fetch("SELECT * FROM freegames")
    for result in results:
        with EpicGames() as epic_games:
            free_games = epic_games.get_info_all_games()
        already_posted = json.loads(result['already_posted'])
        for game in free_games:
            if game["discountPrice"] == "0" and game['gameSlug'] not in already_posted:
                embed = Embed(title=game["title"], color=colors.NEUTRAL, description=game["description"])
                embed.add_field(name="Original Price", value=game["originalPrice"], inline=True)
                embed.add_field(name="Discount Price", value="$0.00", inline=True)
                embed.add_field(name="Epicgames Launcher", value=f"[Get Game](https://evelina.bot/epicgames/{game['gameSlug']})", inline=True)
                embed.set_image(url=game["gameImgUrl"])
                guild = bot.get_guild(result["guild_id"])
                if guild:
                    channel = guild.get_channel_or_thread(result["channel_id"])
                    if channel:
                        await channel.send(embed=embed)
                        already_posted.append(game['gameSlug'])
        await bot.db.execute("UPDATE freegames SET already_posted = $1 WHERE channel_id = $2", json.dumps(already_posted), result["channel_id"])