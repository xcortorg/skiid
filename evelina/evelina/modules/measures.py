import time
import json
import asyncio
import discord
import asyncpg
import datetime
import humanize

from time import time
from typing import Optional, Union
from collections import defaultdict, deque

from discord import Embed
from discord import Embed, User, Member, TextChannel, Guild, Thread
from discord.ext.commands import AutoShardedBot as AB
from discord.errors import Forbidden, HTTPException, NotFound

from modules.styles import colors

class AuditLogHandler:
    def __init__(self, bot, cache_duration=60, delay_between_requests=2):
        self.bot = bot
        self.last_request_time = defaultdict(lambda: 0)
        self.audit_log_cache = defaultdict(lambda: None)
        self.cache_duration = cache_duration
        self.delay_between_requests = delay_between_requests

    async def get_audit_logs_throttled(self, guild):
        current_time = time()
        if (self.audit_log_cache[guild.id] and 
                (current_time - self.last_request_time[guild.id]) < self.cache_duration):
            return self.audit_log_cache[guild.id]
        if (current_time - self.last_request_time[guild.id]) < self.delay_between_requests:
            await asyncio.sleep(self.delay_between_requests - (current_time - self.last_request_time[guild.id]))
        try:
            logs = [entry async for entry in guild.audit_logs(limit=100)]
        except Exception:
            return None
        self.audit_log_cache[guild.id] = logs
        self.last_request_time[guild.id] = current_time
        return logs

class LoggingMeasures:
    def __init__(self, bot):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)
        self.queues = defaultdict(deque)
        self.audit_log_handler = AuditLogHandler(bot)
        self.task = asyncio.create_task(self.process_queues())

    async def process_queues(self):
        try:
            while True:
                for guild_id, queue in list(self.queues.items()):
                    if queue:
                        async with self.locks[guild_id]:
                            channel, embed, view, file = queue.popleft()
                            try:
                                if file:
                                    await channel.send(embed=embed, view=view, file=file)
                                else:
                                    await channel.send(embed=embed, view=view)
                            except Exception:
                                pass
                            await asyncio.sleep(2.5)
                await asyncio.sleep(0.5)
        except asyncio.CancelledError:
            pass

    async def add_to_queue(self, channel, embed, view=None, file=None):
        self.queues[channel.guild.id].append((channel, embed, view, file))

    async def fetch_logging_channel(self, guild: Guild, channel_id: Optional[int]) -> Optional[Union[TextChannel, Thread]]:
        if not channel_id:
            return None
        channel = guild.get_channel(channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(channel_id)
            except (NotFound, Forbidden):
                return None
            except HTTPException:
                return None
        if not channel.permissions_for(guild.me).send_messages:
            return None
        return channel
    
    async def stop(self):
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass
    
    async def insert_history(self, entry, action_type, duration, reason, timestamp):
        max_retries = 5
        attempts = 0
        while attempts < max_retries:
            try:
                record = await self.bot.db.fetchrow(
                    """
                    INSERT INTO history 
                    (id, guild_id, user_id, moderator_id, server_id, punishment, duration, reason, time) 
                    VALUES (
                        (SELECT COALESCE(MAX(id), 0) + 1 FROM history),
                        (SELECT COALESCE(MAX(guild_id), 0) + 1 FROM history WHERE server_id = $1), 
                        $2, $3, $4, $5, $6, $7, $8
                    ) RETURNING guild_id
                    """,
                    entry.guild.id, entry.target.id, entry.user.id, entry.guild.id, action_type, duration, reason or "No reason provided", timestamp
                )
                if record:
                    return str(record['guild_id'])
                return None
            except asyncpg.UniqueViolationError:
                attempts += 1
                await asyncio.sleep(0.1)
                continue
            except Exception:
                return None
        return None
    
    async def ctx_insert_history(self, ctx, member, action_type, duration, reason, timestamp):
        max_retries = 5
        attempts = 0
        while attempts < max_retries:
            try:
                record = await self.bot.db.fetchrow(
                    """
                    INSERT INTO history 
                    (id, guild_id, user_id, moderator_id, server_id, punishment, duration, reason, time) 
                    VALUES (
                        (SELECT COALESCE(MAX(id), 0) + 1 FROM history),
                        (SELECT COALESCE(MAX(guild_id), 0) + 1 FROM history WHERE server_id = $1), 
                        $2, $3, $4, $5, $6, $7, $8
                    ) RETURNING guild_id
                    """,
                    ctx.guild.id, member.id, ctx.author.id, ctx.guild.id, action_type, duration, reason, timestamp
                )
                if record:
                    return str(record['guild_id'])
                return None
            except asyncpg.UniqueViolationError:
                attempts += 1
                await asyncio.sleep(0.1)
                continue
            except Exception:
                return None
        return None

    async def is_ignored(self, guild_id: int, column: str, target_id: int) -> bool:
        if column == "users":
            column = "ignored_users"
        elif column == "channels":
            column = "ignored_channels"
        elif column == "roles":
            column = "ignored_roles"
        else:
            pass
        ignore_list = await self.bot.db.fetchval(f"SELECT {column} FROM logging WHERE guild_id = $1", guild_id)
        if not ignore_list:
            return False
        if isinstance(ignore_list, str):
            try:
                ignore_list = json.loads(ignore_list)
            except json.JSONDecodeError:
                return False
        if not isinstance(ignore_list, list):
            return False
        return str(target_id) in map(str, ignore_list)

class AntiraidMeasures:
    def __init__(self: "AntiraidMeasures", bot: AB):
        self.bot = bot

    def get_bot_perms(self, guild: Guild) -> bool:
        if guild.me is None:
            return False
        return all([guild.me.guild_permissions.ban_members, guild.me.guild_permissions.kick_members, guild.me.guild_permissions.manage_roles])
    
    async def is_module(self: "AntiraidMeasures", module: str, guild: Guild) -> bool:
        return (await self.bot.db.fetchrow(f"SELECT * FROM antiraid_{module} WHERE guild_id = $1", guild.id) is not None)
    
    async def is_whitelisted(self: "AntiraidMeasures", member: Member) -> bool:
        if isinstance(member, discord.User):
            return False
        if member.guild is None:
            return False
        check = await self.bot.db.fetchrow("SELECT whitelisted FROM antiraid WHERE guild_id = $1", member.guild.id)
        if check is None:
            return True
        if check["whitelisted"]:
            if member.id in json.loads(check["whitelisted"]):
                return True
        return False
    
    async def decide_punishment(self: "AntiraidMeasures", module: str, member: Member, reason: str):
        punishment = await self.bot.db.fetchval(f"SELECT punishment FROM antiraid_{module} WHERE guild_id = $1", member.guild.id)
        if punishment == "ban":
            try:
                return await member.ban(reason=reason)
            except Exception:
                pass
        elif punishment == "kick":
            try:
                return await member.kick(reason=reason)
            except Exception:
                pass

    async def take_action(self: "AntiraidMeasures", action: str, user: Member, tasks: list, action_time: datetime.datetime, channel: TextChannel = None):
        awaitable_tasks = [task for task in tasks if asyncio.iscoroutine(task) or isinstance(task, asyncio.Future)]
        if awaitable_tasks:
            await asyncio.gather(*awaitable_tasks)
        time = humanize.precisedelta(action_time)
        embed = Embed(color=colors.NEUTRAL, title="User punished", description=f"**{self.bot.user.name}** took **{time}** to take action")
        if isinstance(user, Member):
            embed.set_author(name=user.guild.name, icon_url=user.guild.icon)
            embed.add_field(name="Server", value=user.guild.name, inline=True)
        embed.add_field(name="User", value=str(user), inline=True)
        embed.add_field(name="Reason", value=action, inline=False)
        if channel:
            return await channel.send(embed=embed)

class AntinukeMeasures:
    def __init__(self: "AntinukeMeasures", bot: AB):
        self.bot = bot
        self.thresholds = {}

    def get_bot_perms(self, guild: Guild) -> bool:
        if guild.me is None:
            return False
        return all([guild.me.guild_permissions.ban_members, guild.me.guild_permissions.kick_members, guild.me.guild_permissions.manage_roles])

    def check_hieracy(self: "AntinukeMeasures", member: Member, bot: Member) -> bool:
        if not isinstance(member, Member) or not isinstance(bot, Member):
            return False
        if member.top_role:
            if bot.top_role:
                return member.top_role < bot.top_role
            return False
        return bot.top_role is not None

    async def is_module(self: "AntinukeMeasures", module: str, guild: Guild) -> bool:
        return (await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", module, guild.id) is not None)

    async def is_whitelisted(self: "AntinukeMeasures", member: Member) -> bool:
        if isinstance(member, discord.User):
            return False
        if member.guild is None:
            return False
        check = await self.bot.db.fetchrow("SELECT owner_id, admins, whitelisted, whitelisted_roles FROM antinuke WHERE guild_id = $1", member.guild.id)
        if check is None:
            return True
        if member.id == check["owner_id"]:
            return True
        if check["whitelisted"]:
            if member.id in json.loads(check["whitelisted"]):
                return True
        if check["admins"]:
            if member.id in json.loads(check["admins"]):
                return True
        if check["whitelisted_roles"]:
            whitelisted_roles = json.loads(check["whitelisted_roles"])
            if any(role.id in whitelisted_roles for role in member.roles):
                return True
        return False
    
    def is_dangerous(self, role: discord.Role) -> bool:
        return any(
            [
                role.permissions.ban_members,
                role.permissions.kick_members,
                role.permissions.mention_everyone,
                role.permissions.manage_channels,
                role.permissions.manage_events,
                role.permissions.manage_expressions,
                role.permissions.manage_guild,
                role.permissions.manage_roles,
                role.permissions.manage_messages,
                role.permissions.manage_webhooks,
                role.permissions.manage_permissions,
                role.permissions.manage_threads,
                role.permissions.moderate_members,
                role.permissions.mute_members,
                role.permissions.deafen_members,
                role.permissions.move_members,
                role.permissions.administrator,
            ]
        )

    async def decide_punishment(self: "AntinukeMeasures", module: str, member: Member, reason: str):
        if member.bot:
            try:
                return await member.kick(reason=reason)
            except Exception:
                pass
        punishment = await self.bot.db.fetchval("SELECT punishment FROM antinuke_modules WHERE guild_id = $1 AND module = $2", member.guild.id, module)
        if punishment == "ban":
            try:
                return await member.ban(reason=reason)
            except Exception:
                pass
        elif punishment == "kick":
            try:
                return await member.kick(reason=reason)
            except Exception:
                pass
        elif punishment == "strip":
            bot_highest_role = member.guild.me.top_role
            roles_to_remove = []
            staff_roles = await self.bot.db.fetchval("SELECT staffs FROM antinuke WHERE guild_id = $1", member.guild.id,)
            if staff_roles:
                staff_roles_list = json.loads(staff_roles)
                if isinstance(staff_roles_list, list) and staff_roles_list:
                    roles_to_remove = [role for role in member.roles if role.id in staff_roles_list and not role.managed and role.position < bot_highest_role.position]
                else:
                    pass
            else:
                pass
            if not roles_to_remove:
                roles_to_remove = [role for role in member.roles if role.is_assignable() and self.is_dangerous(role) and not role.managed and role.position < bot_highest_role.position]
            if not roles_to_remove:
                return False
            await self.bot.db.execute("""INSERT INTO restore_antinuke (guild_id, user_id, roles) VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id) DO UPDATE SET roles = EXCLUDED.roles""", member.guild.id, member.id, json.dumps([r.id for r in roles_to_remove]),)
            try:
                for role in roles_to_remove:
                    await member.remove_roles(role, reason=reason)
                return True
            except Exception:
                return False
        else:
            return

    async def check_threshold(self: "AntinukeMeasures", module: str, member: Member) -> bool:
        if isinstance(member, discord.User):
            return
        check = await self.bot.db.fetchval("SELECT threshold FROM antinuke_modules WHERE module = $1 AND guild_id = $2", module, member.guild.id)
        if check == 0:
            return True
        payload = self.thresholds
        if payload:
            if not payload.get(module):
                payload[module] = {}
            if not payload[module].get(member.guild.id):
                payload[module][member.guild.id] = {}
            if not payload[module][member.guild.id].get(member.id):
                payload[module][member.guild.id][member.id] = [datetime.datetime.now()]
            else:
                payload[module][member.guild.id][member.id].append(datetime.datetime.now())
        else:
            payload = {module: {member.guild.id: {member.id: [datetime.datetime.now()]}}}
        to_remove = [d for d in payload[module][member.guild.id][member.id] if (datetime.datetime.now() - d).total_seconds() > 60]
        for r in to_remove:
            payload[module][member.guild.id][member.id].remove(r)
        self.thresholds = payload
        if check < len(payload[module][member.guild.id][member.id]):
            return True
        return False

    async def take_action(self: "AntinukeMeasures", action: str, user: Member, tasks: list, action_time: datetime.datetime, owner_id: int, channel: TextChannel = None):
        awaitable_tasks = [task for task in tasks if asyncio.iscoroutine(task) or isinstance(task, asyncio.Future)]
        if awaitable_tasks:
            await asyncio.gather(*awaitable_tasks)
        time = humanize.precisedelta(action_time)
        embed = Embed(color=colors.NEUTRAL, title="User punished", description=f"**{self.bot.user.name}** took **{time}** to take action")
        if isinstance(user, Member):
            embed.set_author(name=user.guild.name, icon_url=user.guild.icon)
            embed.add_field(name="Server", value=user.guild.name, inline=True)
        embed.add_field(name="User", value=str(user), inline=True)
        embed.add_field(name="Reason", value=action, inline=False)
        if channel:
            return await channel.send(embed=embed)
        owner = self.bot.get_user(owner_id)
        try:
            await owner.send(embed=embed)
        except:
            pass

class LevelingMeasures:
    def __init__(self: "LevelingMeasures", bot: AB):
        self.bot = bot

    async def add_voice_xp(self, member: Member, total_time: int, guild_id: int):
        blacklist_users, blacklist_channels, blacklist_roles = await self.get_blacklist(member.guild.id)
        if (member.id in set(blacklist_users) or 
            any(role.id in set(blacklist_roles) for role in member.roles)):
            return
        base_xp_per_minute = 8
        res = await self.bot.db.fetchrow("SELECT * FROM leveling WHERE guild_id = $1", guild_id)
        if not res:
            return
        global_voice_multiplier = res["voice_multiplier"] if res["voice_multiplier"] else 1
        voice_booster_multiplier = res["voice_booster"] if member.premium_since else 1
        role_multipliers = await self.bot.db.fetch("SELECT multiplier FROM level_multiplier_voice WHERE guild_id = $1 AND role_id = ANY($2::BIGINT[])", guild_id, [role.id for role in member.roles])
        max_role_multiplier = max((float(rm["multiplier"]) for rm in role_multipliers if rm["multiplier"] is not None), default=1)
        final_multiplier = max(
            global_voice_multiplier if global_voice_multiplier is not None else 1,
            voice_booster_multiplier if voice_booster_multiplier is not None else 1,
            max_role_multiplier if max_role_multiplier is not None else 1
        )
        xp_gain = int((total_time // 60) * base_xp_per_minute * final_multiplier)
        if xp_gain > 0:
            check = await self.bot.db.fetchrow("SELECT * FROM level_user WHERE guild_id = $1 AND user_id = $2", guild_id, member.id)
            if not check:
                await self.bot.db.execute("INSERT INTO level_user (guild_id, user_id, xp, level, target_xp) VALUES ($1, $2, $3, $4, $5)", guild_id, member.id, xp_gain, 0, int((100 * 1) ** 0.9))
            else:
                new_xp = check["xp"] + xp_gain
                target_xp = check["target_xp"]
                await self.bot.db.execute("UPDATE level_user SET xp = $1 WHERE user_id = $2 AND guild_id = $3", new_xp, member.id, guild_id)
                if new_xp >= target_xp:
                    new_level = check["level"] + 1
                    new_target_xp = int((100 * new_level + 1) ** 0.9)
                    await self.bot.db.execute("UPDATE level_user SET target_xp = $1, xp = $2, level = $3 WHERE user_id = $4 AND guild_id = $5", new_target_xp, 0, new_level, member.id, guild_id)
                    await self.give_rewards(member, new_level)

    async def get_blacklist(self, guild_id):
        res = await self.bot.db.fetchrow("SELECT users, channels, roles FROM leveling WHERE guild_id = $1", guild_id)
        if not res:
            return [], [], []
        users = json.loads(res['users']) if res['users'] else []
        channels = json.loads(res['channels']) if res['channels'] else []
        roles = json.loads(res['roles']) if res['roles'] else []
        return users, channels, roles

    async def give_rewards(self, member: Member, level: int):
        stack_status = await self.bot.db.fetchval("SELECT stack FROM leveling WHERE guild_id = $1", member.guild.id)
        level_rewards = await self.bot.db.fetch("SELECT level, role_id FROM level_rewards WHERE guild_id = $1", member.guild.id)
        if not level_rewards:
            return
        level_rewards_dict = {reward["level"]: reward["role_id"] for reward in level_rewards}
        min_level_reward = min(level_rewards_dict.keys(), default=None)
        if min_level_reward is None or level < min_level_reward:
            roles_to_remove = [member.guild.get_role(role_id) for role_id in level_rewards_dict.values() if member.guild.get_role(role_id) in member.roles]
            if roles_to_remove:
                try:
                    await member.remove_roles(*roles_to_remove, reason="Removing level rewards for low-level user")
                except Exception:
                    pass
            return
        if stack_status:
            roles_to_add = [role for lvl in range(min_level_reward, level + 1) if (role := member.guild.get_role(level_rewards_dict.get(lvl))) and role not in member.roles]
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Leveled up")
                except Exception:
                    pass
        else:
            highest_level = max((lvl for lvl in level_rewards_dict if lvl <= level), default=None)
            if highest_level is not None:
                highest_role = member.guild.get_role(level_rewards_dict.get(highest_level))
                roles_to_remove = [role for role in member.roles if role.id in level_rewards_dict.values() and role != highest_role]
                if roles_to_remove:
                    try:
                        await member.remove_roles(*roles_to_remove, reason="Leveled up")
                    except Exception:
                        pass
                if highest_role and highest_role not in member.roles:
                    try:
                        await member.add_roles(highest_role, reason="Leveled up")
                    except Exception:
                        pass

class ManageMeasures:
    def __init__(self: "ManageMeasures", bot: AB):
        self.bot = bot

    async def logging(self, author: User, description: str, action: str):
        guild = self.bot.get_guild(self.bot.logging_guild) or await self.bot.fetch_guild(self.bot.logging_guild)
        embed = (Embed(color=colors.NEUTRAL, description=f"{author.mention}: {description}"))
        if action == "money":
            channel = guild.get_channel_or_thread(self.bot.logging_money)
        elif action == "blacklist":
            channel = guild.get_channel_or_thread(self.bot.logging_blacklist)
        elif action == "system":
            channel = guild.get_channel_or_thread(self.bot.logging_system)
        if channel:
            return await channel.send(embed=embed)
        
    async def add_role(self, member: User, role_id: int):
        guild = self.bot.get_guild(self.bot.logging_guild) or await self.bot.fetch_guild(self.bot.logging_guild)
        if not guild:
            return
        
        user = guild.get_member(member.id)
        if user:
            role = guild.get_role(role_id)
            if role:
                await user.add_roles(role)

    async def remove_role(self, member: User, role_id: int):
        guild = self.bot.get_guild(self.bot.logging_guild) or await self.bot.fetch_guild(self.bot.logging_guild)
        user = guild.get_member(member.id)
        if user:
            role = guild.get_role(role_id)
            if role:
                await user.remove_roles(role)

    async def guild_name(self, guild_id: int, formatted: bool = False):
        guild = self.bot.get_guild(self.bot.logging_guild) or await self.bot.fetch_guild(self.bot.logging_guild)
        if guild:
            if formatted:
                return f"**{guild.name}** (`{guild.id}`)"
            else:
                return guild.name
        else:
            guild_name = await self.bot.db.fetchval("SELECT guild_name FROM guild_names WHERE guild_id = $1", guild_id)
            if guild_name:
                if formatted:
                    return f"**{guild_name}** (`{guild_id}`)"
                else:
                    return guild_name
            else:
                if formatted:
                    return f"**{guild_id}**"
                else:
                    return str(guild_id)
                
    async def get_rank(self, user_id: int):
        rank = await self.bot.db.fetchval("SELECT rank FROM team_members WHERE user_id = $1", user_id)
        if rank == "Developer":
            return 4
        elif rank == "Manager":
            return 3
        elif rank == "Moderator":
            return 2
        elif rank == "Supporter":
            return 1
        else:
            return 0