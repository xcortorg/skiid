import json
import time
import orjson
import asyncio
import aiohttp

from io import BytesIO
from time import time
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from discord import User, Member, Forbidden, HTTPException, VoiceState, Guild, Embed, AllowedMentions, Object, utils, Thread, TextChannel, Status
from discord.errors import NotFound

from modules.styles import emojis, colors, icons
from modules.evelinabot import Evelina, LoggingMeasures
from modules.misc.views import ServerView

class MemberMethods:
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.log = LoggingMeasures(self.bot)
        self.locks = defaultdict(asyncio.Lock)
        self.joins_cache = {}

        self.sent_messages = {}
        self.lock = asyncio.Lock()
        self.cache_duration = 5
        self.user_status_cache = {}
        self.user_cooldown = 10

        self.message_queues = {}
        self.queue_tasks = {}

    def get_joins(self, member: Member) -> int:
        if self.joins_cache.get(member.guild.id):
            self.joins_cache[member.guild.id].append((datetime.now(), member.id))
            to_remove = [m for m in self.joins_cache[member.guild.id] if (datetime.now() - m[0]).total_seconds() > 5]
            for r in to_remove:
                self.joins_cache[member.guild.id].remove(r)
        else:
            self.joins_cache[member.guild.id] = [(datetime.now(), member.id)]
        return len(self.joins_cache[member.guild.id])

    async def on_username_change(self, before: User, after: User):
        if before.name != after.name:
            await self.bot.db.execute("INSERT INTO usernames VALUES ($1,$2,$3)", after.id, str(before), int(datetime.now().timestamp()))

    async def on_username_tracking(self, before: User, after: User):
        if str(before) != str(after):
            results = await self.bot.db.fetch("SELECT * FROM webhook_username")
            headers = {"Content-Type": "application/json"}
            invalid_webhooks = []
            async with aiohttp.ClientSession(headers=headers) as session:
                for result in results:
                    if result["length"] is not None and len(after.name) > result["length"]:
                        continue
                    name = result['name'] if result['name'] else "Evelina - Usernames"
                    avatar = result['avatar'] if result['avatar'] else icons.EVELINA
                    json_data = {
                        "username": name,
                        "avatar_url": avatar,
                        "content": f"New username available: **{before}**"
                    }
                    try:
                        async with session.post(result["webhook_url"], json=json_data) as r:
                            if r.status == 429:
                                retry_after = int(r.headers.get("Retry-After", 1))
                                await asyncio.sleep(retry_after)
                            elif r.status not in [204, 429]:
                                invalid_webhooks.append(result["webhook_url"])
                    except Exception:
                        invalid_webhooks.append(result["webhook_url"])
            if invalid_webhooks:
                await self.bot.db.execute("DELETE FROM webhook_username WHERE webhook_url = ANY($1)", invalid_webhooks)

    async def on_avatar_change(self, before: User, after: User):
        if after.bot:
            return
        if before.avatar == after.avatar:
            return
        check = await self.bot.db.fetchrow("SELECT * FROM avatar_privacy WHERE user_id = $1", after.id)
        if not check:
            return
        if check["status"] == False:
            return
        response = await self.bot.session.get_bytes(after.display_avatar.url)
        if response:
            avatar_hash = after.display_avatar.url.split('/')[-1].split('.')[0].split('?')[0]
            if len(avatar_hash) < 5:
                return
            file_data = BytesIO(response) 
            file_extension = "gif" if avatar_hash.startswith("a_") else "png"
            file_name = f"{avatar_hash}.{file_extension}"
            content_type = 'image/gif' if file_extension == 'gif' else 'image/png'
            if await self.bot.db.fetchrow("SELECT 1 FROM avatar_history WHERE user_id = $1 AND avatar = $2", after.id, file_name):
                return
            if await self.bot.r2.file_exists("evelina", file_name, "avatars"):
                return
            await self.bot.r2.upload_file("evelina", file_data, file_name, content_type, "avatars")
            try:
                await self.bot.db.execute("INSERT INTO avatar_history (user_id, avatar, timestamp) VALUES($1, $2, $3)", after.id, file_name, int(time()))
            except Exception:
                pass

    async def on_nickname_change(self, before: Member, after: Member):
        if before.bot:
            return
        if before.nick is None:
            return
        if before.nick != after.nick:
            await self.bot.db.execute("INSERT INTO nicknames VALUES ($1, $2, $3)", after.id, str(before.nick), int(datetime.now().timestamp()))

    async def on_boost_event(self, before: Member, after: Member):
        if (not before.guild.premium_subscriber_role in before.roles and after.guild.premium_subscriber_role in after.roles):
            if before.guild.system_channel:
                return
            results = await self.bot.db.fetch("SELECT * FROM boost WHERE guild_id = $1", after.guild.id)
            for result in results:
                channel = self.bot.get_channel(result["channel_id"])
                if channel:
                    perms = channel.permissions_for(after.guild.me)
                    if perms.send_messages and perms.embed_links:
                        try:
                            x = await self.bot.embed_build.alt_convert(after, result["message"])
                            await channel.send(**x)
                            await asyncio.sleep(1)
                        except Exception:
                            pass

    async def on_boost_transfer(self, before: Member, after: Member):
        if before.guild.premium_subscriber_role in before.roles and not after.guild.premium_subscriber_role in after.roles:
            await self.bot.db.execute("INSERT INTO booster_lost VALUES ($1, $2, $3)", before.guild.id, before.id, int(datetime.now().timestamp()))
            check = await self.bot.db.fetchrow("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", before.guild.id, before.id)
            if check:
                role = before.guild.get_role(int(check["role_id"]))
                await self.bot.db.execute("DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2", before.guild.id, before.id)
                if role:
                    try:
                        await role.delete(reason="booster transferred all their boosts")
                    except Exception:
                        pass

    async def on_boostaward_event(self, before: Member, after: Member):
        if (not before.guild.premium_subscriber_role in before.roles and before.guild.premium_subscriber_role in after.roles):
            results = await self.bot.db.fetch("SELECT role_id FROM booster_award WHERE guild_id = $1", before.guild.id)
            roles = [after.guild.get_role(record['role_id']) for record in results if after.guild.get_role(record['role_id']).is_assignable()]
            try:
                await asyncio.gather(*[after.add_roles(role, reason="Booster role awarded given") for role in roles])
            except Exception:
                pass
        elif (before.guild.premium_subscriber_role in before.roles and not after.guild.premium_subscriber_role in after.roles):
            results = await self.bot.db.fetch("SELECT role_id FROM booster_award WHERE guild_id = $1", before.guild.id)
            roles = [after.guild.get_role(record['role_id']) for record in results if after.guild.get_role(record['role_id']).is_assignable() and after.guild.get_role(record['role_id']) in after.roles]
            try:
                await asyncio.gather(*[after.remove_roles(role, reason="Removing booster awards from this member") for role in roles])
            except Exception:
                pass

    async def on_forcenickname_event(self, before: Member, after: Member):
        if str(before.nick) != str(after.nick):
            if nickname := await self.bot.db.fetchval("SELECT nickname FROM force_nick WHERE guild_id = $1 AND user_id = $2", before.guild.id, before.id):
                if after.nick != nickname:
                    try:
                        await after.edit(nick=nickname, reason="Force nickname applied to this member")
                    except Exception:
                        pass

    async def process_queue(self, channel_id):
        while self.message_queues[channel_id]:
            channel, message, member = self.message_queues[channel_id].pop(0)
            try:
                sent_message = await channel.send(**message)
                await self.bot.db.execute(
                    "INSERT INTO welcome_messages (guild_id, user_id, channel_id, message_id, timestamp) VALUES ($1, $2, $3, $4, $5)",
                    member.guild.id, member.id, channel.id, sent_message.id, int(datetime.now().timestamp())
                )
            except Exception:
                pass
            await asyncio.sleep(1)
        del self.queue_tasks[channel_id]

    async def on_join_event(self, member: Member):
        guild_id = member.guild.id
        welc_results = await self.bot.db.fetch("SELECT * FROM welcome WHERE guild_id = $1", guild_id)
        for result in welc_results:
            channel = self.bot.get_channel(result["channel_id"])
            if channel:
                perms = channel.permissions_for(member.guild.me)
                if perms.send_messages and perms.embed_links:
                    try:
                        x = await self.bot.embed_build.alt_convert(member, result["message"])
                        x["allowed_mentions"] = AllowedMentions.all()
                        if channel.id not in self.message_queues:
                            self.message_queues[channel.id] = []
                        self.message_queues[channel.id].append((channel, x, member))
                        if channel.id not in self.queue_tasks:
                            self.queue_tasks[channel.id] = asyncio.create_task(self.process_queue(channel.id))
                    except Exception:
                        pass
        dm_result = await self.bot.db.fetchrow("SELECT * FROM joindm WHERE guild_id = $1", guild_id)
        if dm_result:
            try:
                x = await self.bot.embed_build.alt_convert(member, dm_result["message"])
                view = ServerView(guild_name=member.guild.name)
                await member.send(**x)
                await member.send(view=view)
            except Exception:
                pass

    async def on_autorole_event(self, member: Member):
        if await self.bot.db.fetchrow("SELECT * FROM jail_members WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id):
            return
        if not member.guild.me.guild_permissions.manage_roles:
            return
        if member.guild.id == self.bot.logging_guild:
            if any(guild.owner_id == member.id for guild in self.bot.guilds):
                role = member.guild.get_role(1242509393308946503)
                if role and role.is_assignable() and role not in member.roles:
                    await member.add_roles(role, reason="Join | Server Owner role synchronization")
            donator = await self.bot.db.fetchrow("SELECT * FROM donor WHERE user_id = $1", member.id)
            if donator:
                role = member.guild.get_role(1242474452353290291)
                if role and role.is_assignable() and role not in member.roles:
                    await member.add_roles(role, reason="Donator joined the server")
            instance = await self.bot.db.fetchrow("SELECT * FROM instance WHERE owner_id = $1", member.id)
            if instance:
                role = member.guild.get_role(1284159368262324285)
                if role and role.is_assignable() and role not in member.roles:
                    await member.add_roles(role, reason="Instance owner joined the server")
            premium = await self.bot.db.fetchrow("SELECT * FROM premium WHERE user_id = $1", member.id)
            if premium:
                role = member.guild.get_role(1242474452353290291)
                if role and role.is_assignable() and role not in member.roles:
                    await member.add_roles(role, reason="Premium user joined the server")
            bughunter = await self.bot.db.fetchval("SELECT COUNT(*) FROM bugreports WHERE user_id = $1", member.id)
            if bughunter >= 3:
                role = member.guild.get_role(1243745562197626982)
                if role and role.is_assignable() and role not in member.roles:
                    await member.add_roles(role, reason="Bug Hunter joined the server")
            if bughunter >= 5:
                role = member.guild.get_role(1300196517969137754)
                if role and role.is_assignable() and role not in member.roles:
                    await member.add_roles(role, reason="Bug Hunter joined the server")
        autoroles_all = await self.bot.db.fetch("SELECT role_id FROM autorole WHERE guild_id = $1", member.guild.id)
        await self.assign_roles(member, autoroles_all, "AutoRole for all members")
        if not member.bot:
            autoroles_humans = await self.bot.db.fetch("SELECT role_id FROM autorole_humans WHERE guild_id = $1", member.guild.id)
            await self.assign_roles(member, autoroles_humans, "AutoRole for humans")
        else:
            autoroles_bots = await self.bot.db.fetch("SELECT role_id FROM autorole_bots WHERE guild_id = $1", member.guild.id)
            await self.assign_roles(member, autoroles_bots, "AutoRole for bots")

    async def assign_roles(self, member, roles_data, reason):
        for result in roles_data:
            role = member.guild.get_role(result["role_id"])
            if role and role.is_assignable() and role not in member.roles:
                try:
                    await member.add_roles(role, reason=reason)
                    await asyncio.sleep(1)
                except Exception:
                    pass

    async def on_whitelist_check(self, member: Member):
        if await self.bot.db.fetchrow("SELECT * FROM whitelist_module WHERE guild_id = $1", member.guild.id):
            if not await self.bot.db.fetchrow("SELECT * FROM whitelist WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id):
                check = await self.bot.db.fetchrow("SELECT * FROM whitelist_module WHERE guild_id = $1", member.guild.id)
                if check:
                    try:
                        if check["embed"] == "default":
                            await member.send(f"You are not whitelisted to join **{member.guild.name}**")
                            if check["punishment"] == "ban":
                                return await member.guild.ban(member, reason="Not in the whitelist")
                            elif check["punishment"] == "kick":
                                return await member.guild.kick(member, reason="Not in the whitelist")
                        elif check["embed"] == "none":
                            if check["punishment"] == "ban":
                                return await member.guild.ban(member, reason="Not in the whitelist")
                            elif check["punishment"] == "kick":
                                return await member.guild.kick(member, reason="Not in the whitelist")
                        else:
                            x = await self.bot.embed_build.alt_convert(member, check["embed"])
                            await member.send(**x)
                            if check["punishment"] == "ban":
                                return await member.guild.ban(member, reason="Not in the whitelist")
                            elif check["punishment"] == "kick":
                                return await member.guild.kick(member, reason="Not in the whitelist")
                    except Exception:
                        pass

    async def on_invite_join(self, member: Member):
        guild = member.guild
        invites_settings = await self.bot.db.fetchrow("SELECT fake_threshold, message, logs, autoupdate FROM invites_settings WHERE guild_id = $1", guild.id)
        if not invites_settings:
            return
        try:
            invites_before_data = await self.bot.redis.getstr(f"invites_{guild.id}")
            if invites_before_data is None:
                invites = await self.safe_fetch_invites(guild)
                invites_data = [{"code": invite.code, "uses": invite.uses, "inviter_id": invite.inviter.id if invite.inviter else None} for invite in invites]
                await self.bot.redis.set(f"invites_{guild.id}", orjson.dumps(invites_data).decode("utf-8"))
                return
            invites_before = orjson.loads(invites_before_data)
        except Forbidden:
            return
        try:
            invites_after = await self.safe_fetch_invites(guild)
        except Exception:
            return
        invites_after_data = [{"code": invite.code, "uses": invite.uses, "inviter_id": invite.inviter.id if invite.inviter else None} for invite in invites_after]
        await self.bot.redis.set(f"invites_{guild.id}", orjson.dumps(invites_after_data).decode("utf-8"))
        fake_threshold = invites_settings['fake_threshold']
        message_template = invites_settings['message'] or "{embed}{description: {user.mention} has been invited by {inviter.mention}!}$v{color: {invisible}}"
        logs_channel_id = invites_settings['logs']
        autoupdate = invites_settings['autoupdate']
        account_age_days = (datetime.now(timezone.utc) - member.created_at).days
        for invite in invites_before:
            for new_invite in invites_after:
                if invite['code'] == new_invite.code and invite['uses'] is not None and new_invite.uses is not None and invite['uses'] < new_invite.uses:
                    inviter_id = new_invite.inviter.id
                    inviter = guild.get_member(inviter_id) or await self.bot.fetch_user(inviter_id)
                    if not isinstance(inviter, Member):
                        try:
                            inviter = guild.get_member(inviter_id)
                            if not inviter:
                                inviter = await guild.fetch_member(inviter_id)
                        except NotFound:
                            return
                    timestamp = datetime.now().timestamp()
                    await self.bot.db.execute("INSERT INTO invites_users (guild_id, user_id, inviter_id, invite_code, timestamp) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (guild_id, user_id) DO NOTHING", guild.id, member.id, inviter_id, invite['code'], timestamp)
                    invite_type = 'fake_count' if account_age_days < fake_threshold else 'regular_count'
                    await self.bot.db.execute(f"INSERT INTO invites (guild_id, user_id, {invite_type}) VALUES ($1, $2, 1) ON CONFLICT (guild_id, user_id) DO UPDATE SET {invite_type} = invites.{invite_type} + 1",guild.id, inviter_id)
                    invite_counts = await self.bot.db.fetchrow("SELECT regular_count, left_count, fake_count, bonus, (regular_count + left_count + fake_count + bonus) AS total_count FROM invites WHERE guild_id = $1 AND user_id = $2", guild.id, inviter_id)
                    if logs_channel_id:
                        logs_channel = guild.get_channel(logs_channel_id)
                        if logs_channel:
                            embed = message_template
                            embed = embed.replace("{inviter.name}", inviter.name)
                            embed = embed.replace("{inviter.display}", inviter.display_name)
                            embed = embed.replace("{inviter.mention}", inviter.mention)
                            embed = embed.replace("{inviter.id}", str(inviter.id))
                            embed = embed.replace("{inviter.avatar}", inviter.avatar.url if inviter.avatar else inviter.default_avatar.url)
                            embed = embed.replace("{inviter.regular_count}", str(invite_counts['regular_count'] or 0))
                            embed = embed.replace("{inviter.left_count}", str(invite_counts['left_count'] or 0))
                            embed = embed.replace("{inviter.fake_count}", str(invite_counts['fake_count'] or 0))
                            embed = embed.replace("{inviter.bonus_count}", str(invite_counts['bonus'] or 0))
                            embed = embed.replace("{inviter.total_count}", str(invite_counts['total_count'] or 0))
                            x = await self.bot.embed_build.alt_convert(member, embed)
                            await logs_channel.send(**x)
                    rewards = await self.bot.db.fetch("SELECT threshold, role_id FROM invites_rewards WHERE guild_id = $1", guild.id)
                    if autoupdate:
                        current_roles = {reward['role_id'] for reward in rewards if reward['role_id'] in [role.id for role in inviter.roles]}
                        for role_id in current_roles:
                            role = guild.get_role(role_id)
                            if role:
                                await inviter.remove_roles(role, reason="Invite reward updated")
                    for reward in rewards:
                        if invite_counts['regular_count'] + invite_counts['bonus'] >= reward['threshold']:
                            role = guild.get_role(reward['role_id'])
                            if role and role not in inviter.roles:
                                await inviter.add_roles(role, reason="Invite reward added")
                    return
                
    async def on_ticket_owner_rejoin(self, member: Member):
        res = await self.bot.db.fetch(
            "SELECT channel_id FROM ticket_opened WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id
        )
        if not res:
            return
        for row in res:
            channel = member.guild.get_channel(row['channel_id'])
            if channel:
                if not await self.bot.cache.get(f"OwnerRejoinAnnounce_{member.id}"):
                    await self.bot.cache.set(f"OwnerRejoinAnnounce_{member.id}", member.id, 14400)
                else:
                    return
                overwrite = channel.overwrites_for(member)
                overwrite.view_channel = True
                overwrite.send_messages = True
                await channel.set_permissions(member, overwrite=overwrite)

                await channel.send(content=member.mention,
                    embed=Embed(
                        description=f"### 👋 Welcome back, {member.mention}!"
                                    "\n> Your **access** to the ticket got **restored**",
                        color=colors.NEUTRAL
                        ),
                        allowed_mentions=AllowedMentions(users=True)
                    )
                
    async def on_activity_join_event(self, member: Member):
        if member.guild and member.guild.id:
            await self.bot.db.execute("INSERT INTO activity_joined VALUES ($1, $2, $3)", member.guild.id, member.id, int(datetime.now().timestamp()))
                
    async def safe_fetch_invites(self, guild: Guild):
        retry_after = 0
        while retry_after > 0:
            try:
                return await guild.invites()
            except HTTPException as e:
                if e.status == 429:
                    retry_after = float(e.response.headers.get("Retry-After", 1))
                    await asyncio.sleep(retry_after)
                else:
                    raise
        return await guild.invites()
                
    async def on_jail_check(self, member: Member):
        if await self.bot.db.fetchrow("SELECT * FROM jail_members WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id):
            await member.edit(roles=[])
            if re := await self.bot.db.fetchrow("SELECT role_id FROM jail WHERE guild_id = $1", member.guild.id):
                if role := member.guild.get_role(re[0]):
                    await member.add_roles(role, reason="member jailed")
                
    async def on_globalban_check(self, member: Member):
        reason = await self.bot.db.fetchval("SELECT reason FROM globalban WHERE user_id = $1", member.id)
        if reason:
            if member.guild.me.guild_permissions.ban_members:
                await member.ban(reason=reason)

    async def on_massjoin_event(self, member: Member):
        if member.guild.me.guild_permissions.administrator:
            if threshold := await self.bot.db.fetchval("SELECT threshold FROM antiraid_massjoin WHERE guild_id = $1", member.guild.id):
                joins = self.get_joins(member)
                if joins > threshold:
                    async with self.locks[member.guild.id]:
                        tasks = []
                        for m in self.joins_cache[member.guild.id]:
                            try:
                                punishment = await self.bot.db.fetchval("SELECT punishment FROM antiraid_massjoin WHERE guild_id = $1", member.guild.id)
                                if punishment == "ban":
                                    await member.guild.ban(user=Object(m[1]), reason="Flagged by mass join protection")
                                elif punishment == "kick":
                                    await member.guild.kick(user=Object(m[1]), reason="Flagged by mass join protection")
                            except Exception:
                                pass
                            else:
                                punishment = await self.bot.db.fetchval("SELECT punishment FROM antiraid_massjoin WHERE guild_id = $1", member.guild.id)
                                if punishment == "ban":
                                    tasks.append(member.guild.ban(user=Object(m[1]), reason="Flagged by mass join protection"))
                                elif punishment == "kick":
                                    tasks.append(member.guild.kick(user=Object(m[1]), reason="Flagged by mass join protection"))
                        await asyncio.gather(*tasks)
                        self.joins_cache[member.guild.id] = []
                        url = f"https://discord.com/api/v9/guilds/{member.guild.id}/incident-actions"
                        until = (utils.utcnow() + timedelta(minutes=30)).isoformat()
                        headers = {"Authorization": f"Bot {self.bot.http.token}", "Content-Type": "application/json"}
                        data = {"dms_disabled_until": until, "invites_disabled_until": until}
                        await self.bot.session.post_json(url, params=data, headers=headers)

    async def on_member_join_logging(self, member: Member):
        if not member.bot:
            if await self.log.is_ignored(member.guild.id, "users", member.id):
                return
            record = await self.bot.db.fetchval("SELECT members FROM logging WHERE guild_id = $1", member.guild.id)
            channel = await self.log.fetch_logging_channel(member.guild, record)
            if isinstance(channel, (TextChannel, Thread)):
                if not channel.permissions_for(channel.guild.me).send_messages:
                    return
                if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                    return
                async with self.locks[member.guild.id]:
                    if datetime.now(timezone.utc) - member.created_at < timedelta(days=7):
                        embed = (
                            Embed(color=colors.WARNING, title="Member Join", description=f"{member.mention} joined the server\n{emojis.WARNING} Account is younger than **7 days**", timestamp=member.joined_at)
                            .set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
                            .add_field(name="Created", value=f"{utils.format_dt(member.created_at)}\n{utils.format_dt(member.created_at, style='R')}", inline=False)
                            .add_field(name="Joined", value=f"{utils.format_dt(member.joined_at)}\n{utils.format_dt(member.joined_at, style='R')}", inline=False)
                            .set_footer(text=f"Members: {member.guild.member_count} | ID: {member.id}")
                        )
                    else:
                        embed = (
                            Embed(color=colors.SUCCESS, title="Member Join", description=f"{member.mention} joined the server", timestamp=member.joined_at)
                            .set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
                            .add_field(name="Created", value=f"{utils.format_dt(member.created_at)}\n{utils.format_dt(member.created_at, style='R')}", inline=False)
                            .add_field(name="Joined", value=f"{utils.format_dt(member.joined_at)}\n{utils.format_dt(member.joined_at, style='R')}", inline=False)
                            .set_footer(text=f"Members: {member.guild.member_count} | ID: {member.id}")
                        )
                    await self.log.add_to_queue(channel, embed, None)

    async def on_leave_event(self, member: Member):
        if not member or not member.guild:
            return
        results = await self.bot.db.fetch("SELECT * FROM leave WHERE guild_id = $1", member.guild.id)
        for result in results:
            channel = self.bot.get_channel(result["channel_id"])
            if channel:
                perms = channel.permissions_for(member.guild.me)
                if perms.send_messages and perms.embed_links:
                    try:
                        x = await self.bot.embed_build.alt_convert(member, result["message"])
                        await channel.send(**x)
                        await asyncio.sleep(2)
                    except Exception:
                        pass
        welcome_messages = await self.bot.db.fetch("SELECT * FROM welcome_messages WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id)
        for welcome_message in welcome_messages:
            check = await self.bot.db.fetchrow("SELECT * FROM welcome WHERE guild_id = $1 AND channel_id = $2", member.guild.id, welcome_message["channel_id"])
            if check and check['delete']:
                if int(welcome_message['timestamp'] + check['duration']) > int(datetime.now().timestamp()):
                    try:
                        channel = member.guild.get_channel(welcome_message["channel_id"])
                        if channel:
                            message = await channel.fetch_message(welcome_message["message_id"])
                            await message.delete()
                    except Exception:
                        pass

    async def on_boost_remove(self, before: Member):
        if before.guild.premium_subscriber_role in before.roles:
            await self.bot.db.execute("INSERT INTO booster_lost VALUES ($1, $2, $3)", before.guild.id, before.id, int(datetime.now().timestamp()))
            check = await self.bot.db.fetchrow("SELECT role_id FROM booster_roles WHERE guild_id = $1 AND user_id = $2", before.guild.id, before.id)
            if check:
                role = before.guild.get_role(int(check["role_id"]))
                await self.bot.db.execute("DELETE FROM booster_roles WHERE guild_id = $1 AND user_id = $2", before.guild.id, before.id)
                try:
                    await role.delete(reason="booster left the server")
                except Exception:
                    pass

    async def on_invite_leave(self, member: Member):
        guild = member.guild
        inv_rec = await self.bot.db.fetchrow("SELECT inviter_id FROM invites_users WHERE guild_id = $1 AND user_id = $2", guild.id, member.id)
        if not inv_rec:
            return
        inviter_id = inv_rec['inviter_id']
        invite_entry = await self.bot.db.fetchrow("SELECT regular_count FROM invites WHERE guild_id = $1 AND user_id = $2", guild.id, inviter_id)
        if invite_entry and invite_entry['regular_count'] > 0:
            await self.bot.db.execute("UPDATE invites SET regular_count = regular_count - 1, left_count = left_count + 1 WHERE guild_id = $1 AND user_id = $2", guild.id, inviter_id)
            rewards = await self.bot.db.fetch("SELECT threshold, role_id FROM invites_rewards WHERE guild_id = $1 ORDER BY threshold DESC", guild.id)
            invite_counts = await self.bot.db.fetchrow("SELECT regular_count FROM invites WHERE guild_id = $1 AND user_id = $2", guild.id, inviter_id)
            inviter = guild.get_member(inviter_id) or await self.bot.fetch_user(inviter_id)
            if isinstance(inviter, Member):
                for reward in rewards:
                    if invite_counts['regular_count'] < reward['threshold']:
                        role = guild.get_role(reward['role_id'])
                        if role and role in inviter.roles:
                            try:
                                await inviter.remove_roles(role, reason="Invite reward removed")
                            except Exception:
                                pass
        await self.bot.db.execute("DELETE FROM invites_users WHERE guild_id = $1 AND user_id = $2", guild.id, member.id)

    async def on_ticket_leave(self, member: Member):
        ticket_opened = await self.bot.db.fetchrow("SELECT topic FROM ticket_opened WHERE user_id = $1 AND guild_id = $2", member.id, member.guild.id)
        if ticket_opened:
            topic = ticket_opened['topic']
            tickets = await self.bot.db.fetch("SELECT channel_id FROM ticket_opened WHERE user_id = $1 AND guild_id = $2", member.id, member.guild.id)
            for ticket in tickets:
                channel = member.guild.get_channel(ticket['channel_id'])
                if channel:
                    cache_key = f"TicketLeave_{member.guild.id}_{member.id}_{ticket['channel_id']}"
                    if not await self.bot.cache.get(cache_key):
                        await self.bot.cache.set(cache_key, member.id, 14400)
                    else:
                        continue
                    roles = []
                    if topic == "default":
                        default_support_roles = await self.bot.db.fetchval("SELECT support_roles FROM ticket WHERE guild_id = $1", member.guild.id)
                        if default_support_roles:
                            roles = json.loads(default_support_roles)
                    else:
                        topic_support_roles = await self.bot.db.fetchrow("SELECT support_roles FROM ticket_topics WHERE guild_id = $1 AND name = $2", member.guild.id, topic)
                        if topic_support_roles and topic_support_roles['support_roles']:
                            roles = json.loads(topic_support_roles['support_roles'])
                    support_roles = ' '.join([f"<@&{role}>" for role in roles])
                    embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} Ticket owner {member.mention} (`{member.id}`) left the server")
                    await channel.send(content=support_roles, embed=embed, allowed_mentions=AllowedMentions(everyone=True, roles=True, users=True))
    
    async def on_restore_event(self, member: Member):
        try:
            await self.bot.db.execute("INSERT INTO restore VALUES ($1,$2,$3)", member.guild.id, member.id, json.dumps([r.id for r in member.roles]))
        except:
            await self.bot.db.execute("UPDATE restore SET roles = $1 WHERE guild_id = $2 AND user_id = $3", json.dumps([r.id for r in member.roles]), member.guild.id, member.id)

    async def on_member_remove_logging(self, member: Member):
        if not member.guild or await self.log.is_ignored(member.guild.id, "users", member.id):
            return
        record = await self.bot.db.fetchval("SELECT members FROM logging WHERE guild_id = $1", member.guild.id)
        channel = await self.log.fetch_logging_channel(member.guild, record)
        if not channel:
            return
        if not hasattr(channel, "guild") or channel.guild is None:
            return
        if isinstance(channel, (TextChannel, Thread)):
            if not channel.permissions_for(channel.guild.me).send_messages:
                return
            if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                return
            async with self.locks[member.guild.id]:
                embed = (
                    Embed(color=colors.ERROR, title="Member Left", description=f"{member.mention} left the server", timestamp=datetime.now())
                    .set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
                    .add_field(name="Created", value=f"{utils.format_dt(member.created_at)}\n{utils.format_dt(member.created_at, style='R')}", inline=False)
                    .add_field(name="Joined", value=f"{utils.format_dt(member.joined_at)}\n{utils.format_dt(member.joined_at, style='R')}", inline=False)
                    .set_footer(text=f"Members: {member.guild.member_count} | ID: {member.id}")
                )
                await self.log.add_to_queue(channel, embed, None)

    async def on_activity_leave_event(self, member: Member):
        if member.guild and member.guild.id:
            await self.bot.db.execute("INSERT INTO activity_left VALUES ($1, $2, $3)", member.guild.id, member.id, int(datetime.now().timestamp()))

    async def on_hardban_check(self, guild, user):
        check = await self.bot.db.fetchrow("SELECT * FROM hardban WHERE guild_id = $1 AND user_id = $2", guild.id, user.id)
        if check:
            member = self.bot.get_user(check["moderator_id"])
            reason = (f"Hardbanned by {member.name} ({member.id}): {check['reason']}" if member else f"Hardbanned: {check['reason']}")
            try:
                await guild.ban(user, reason=reason)
            except Exception:
                pass

    async def on_voicetrack_event(self, member: Member, before: VoiceState, after: VoiceState):
        if member.bot or before.channel == after.channel:
            return
        guild_id = member.guild.id
        user_id = member.id
        current_time = int(time())
        settings = await self.bot.db.fetchrow("SELECT state, mute_track, level_state FROM voicetrack_settings WHERE guild_id = $1", guild_id)
        if not settings:
            return
        time_spent = 0
        if after.channel and not before.channel:
            if (after.mute or after.self_mute) and settings["mute_track"]:
                return await self.bot.db.execute(
                    "INSERT INTO voicetrack (guild_id, user_id, joined_time, total_time, muted_time, mute_time) "
                    "VALUES ($1, $2, NULL, 0, $3, 0) "
                    "ON CONFLICT (guild_id, user_id) DO UPDATE SET muted_time = $3",
                    guild_id, user_id, current_time
                )
            else:
                return await self.bot.db.execute(
                    "INSERT INTO voicetrack (guild_id, user_id, joined_time, total_time, muted_time, mute_time) "
                    "VALUES ($1, $2, $3, 0, NULL, 0) "
                    "ON CONFLICT (guild_id, user_id) DO UPDATE SET joined_time = $3, muted_time = NULL",
                    guild_id, user_id, current_time
                )
        elif before.channel and not after.channel:
            res = await self.bot.db.fetchrow("SELECT joined_time, total_time, muted_time, mute_time FROM voicetrack WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
            if not res:
                return
            total_time = res["total_time"] or 0
            mute_time = res["mute_time"] or 0
            if res["joined_time"]:
                join_time = res["joined_time"]
                time_spent = current_time - join_time
                total_time += time_spent
            if res["muted_time"]:
                muted_time = res["muted_time"]
                mute_time += current_time - muted_time
            await self.bot.db.execute("UPDATE voicetrack SET total_time = $1, joined_time = NULL, mute_time = $2, muted_time = NULL WHERE guild_id = $3 AND user_id = $4", total_time, mute_time, guild_id, user_id)
            if time_spent > 0:
                voice_date = datetime.utcnow().date()
                channel_id = before.channel.id
                await self.bot.db.execute(
                    """
                    INSERT INTO activity_voice (user_id, channel_id, server_id, voice_date, voice_time)
                    VALUES ($1, $2, $3, $4, $5)
                    ON CONFLICT (user_id, channel_id, server_id, voice_date)
                    DO UPDATE SET voice_time = activity_voice.voice_time + $5
                    """,
                    user_id, channel_id, guild_id, voice_date, time_spent
                )
            if settings['level_state'] and time_spent:
                await self.bot.level.add_voice_xp(member, time_spent, guild_id)

    async def on_mutetrack_event(self, member: Member, before: VoiceState, after: VoiceState):
        if member.bot:
            return
        guild_id = member.guild.id
        user_id = member.id
        res = await self.bot.db.fetchrow("SELECT mute_track FROM voicetrack_settings WHERE guild_id = $1", guild_id)
        if not res or not res['mute_track']:
            return
        if not before.self_mute and after.self_mute or not before.mute and after.mute:
            res = await self.bot.db.fetchrow("SELECT joined_time, total_time FROM voicetrack WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
            if res and res['joined_time']:
                join_time = res['joined_time']
                total_time = res['total_time']
                time_spent = int(time()) - join_time
                total_time += time_spent
            else:
                total_time = 0
            await self.bot.db.execute("UPDATE voicetrack SET muted_time = $1, joined_time = NULL, total_time = $2 WHERE guild_id = $3 AND user_id = $4", int(time()), total_time, guild_id, user_id)
        elif before.self_mute and not after.self_mute or before.mute and not after.mute:
            res = await self.bot.db.fetchrow("SELECT muted_time, mute_time FROM voicetrack WHERE guild_id = $1 AND user_id = $2", guild_id, user_id)
            if res and res['muted_time']:
                muted_time = res['muted_time']
                mute_time = res['mute_time'] or 0
                time_spent = int(time()) - muted_time
                await self.bot.db.execute("UPDATE voicetrack SET mute_time = $1, muted_time = NULL, joined_time = $2 WHERE guild_id = $3 AND user_id = $4", mute_time + time_spent, int(time()), guild_id, user_id)

    async def on_voicerole_event(self, member, before, after):
        if not member or not member.guild:
            return
        if before.channel and (not after.channel or before.channel.id != after.channel.id):
            default = await self.bot.db.fetchrow("SELECT role_id FROM voicerole_default WHERE guild_id = $1", member.guild.id)
            if default:
                role = member.guild.get_role(default['role_id'])
                if role and role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Left voice channel")
                    except Exception:
                        pass
            if before.channel:
                check = await self.bot.db.fetchrow("SELECT roles FROM voicerole WHERE guild_id = $1 AND channel_id = $2", member.guild.id, before.channel.id)
                if check:
                    try:
                        role_ids = json.loads(check['roles'])
                        roles_to_remove = [member.guild.get_role(role_id) for role_id in role_ids if member.guild.get_role(role_id)]
                        if roles_to_remove:
                            try:
                                await member.remove_roles(*roles_to_remove, reason="Left voice channel")
                            except Exception:
                                pass
                    except json.JSONDecodeError:
                        pass
        if after.channel and (not before.channel or before.channel.id != after.channel.id):
            default = await self.bot.db.fetchrow("SELECT role_id FROM voicerole_default WHERE guild_id = $1", member.guild.id)
            if default:
                role = member.guild.get_role(default['role_id'])
                if role and role not in member.roles:
                    try:
                        await member.add_roles(role, reason="Joined voice channel")
                    except Exception:
                        pass
            if after.channel:
                check = await self.bot.db.fetchrow("SELECT roles FROM voicerole WHERE guild_id = $1 AND channel_id = $2", member.guild.id, after.channel.id)
                if check:
                    try:
                        role_ids = json.loads(check['roles'])
                        roles_to_add = [member.guild.get_role(role_id) for role_id in role_ids if member.guild.get_role(role_id)]
                        if roles_to_add:
                            try:
                                await member.add_roles(*roles_to_add, reason="Joined voice channel")
                            except Exception:
                                pass
                    except json.JSONDecodeError:
                        pass

    async def on_voice_state_update_logging(self, member: Member, before: VoiceState, after: VoiceState):
        if await self.log.is_ignored(member.guild.id, "users", member.id):
            return
        record = await self.bot.db.fetchval("SELECT voice FROM logging WHERE guild_id = $1", member.guild.id)
        channel = await self.log.fetch_logging_channel(member.guild, record)
        if isinstance(channel, (TextChannel, Thread)):
            if not channel.permissions_for(channel.guild.me).send_messages:
                return
            if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                return
            embed = Embed(color=colors.NEUTRAL, timestamp=datetime.now())
            description = None
            if before.channel is None and after.channel is not None:
                embed.title = "Voice Channel Join"
                description = f"{member.mention} joined voice channel"
                embed.add_field(name="Channel", value=after.channel.mention)
                embed.set_footer(text=f"ID: {after.channel.id}")
            elif before.channel is not None and after.channel is None:
                embed.title = "Voice Channel Leave"
                description = f"{member.mention} left voice channel"
                embed.add_field(name="Channel", value=before.channel.mention)
                embed.set_footer(text=f"ID: {before.channel.id}")
            elif before.channel != after.channel:
                embed.title = "Voice Channel Switch"
                description = f"{member.mention} switched voice channel"
                embed.add_field(name="Before", value=before.channel.mention, inline=True)
                embed.add_field(name="After", value=after.channel.mention, inline=True)
                embed.set_footer(text=f"ID: {after.channel.id}")
            embed.set_author(name=str(member), icon_url=member.avatar.url if member.avatar else member.default_avatar.url)
            if description is not None:
                embed.description = description
                await self.log.add_to_queue(channel, embed, None)
            else:
                pass

    async def on_voiceban_event(self, member: Member, before: VoiceState, after: VoiceState):
        if after.channel is None:
            return
        check = await self.bot.db.fetchrow("SELECT * FROM voiceban WHERE guild_id = $1 AND user_id = $2", member.guild.id, member.id)
        if check:
            try:
                await member.edit(voice_channel=None, reason=f"Voice ban by {member.guild.me}")
            except Exception:
                pass