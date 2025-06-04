from __future__ import annotations

from discord.ext.commands import Cog, command, Context, check, hybrid_group, bot_has_permissions, has_permissions
from discord import (
    AuditLogAction,
    AuditLogEntry,
    Member,
    Guild,
    User,
    Object,
    Role,
    utils,
    Embed,
    Permissions,
    TextChannel,
    Webhook,
)
from asyncio import gather, Lock, sleep
from datetime import timedelta, datetime
from collections import defaultdict
from typing import Optional, Union, Dict, Set, List, Any
from contextlib import suppress
from loguru import logger


def trusted():
    async def predicate(ctx: Context):
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        check = await ctx.bot.db.fetchval(
            "SELECT COUNT(*) FROM antinuke_admin WHERE guild_id = $1 and user_id = $2",
            ctx.guild.id,
            ctx.author.id,
        )
        if check == 0 and not ctx.author.id == ctx.guild.owner_id:
            await ctx.fail("you aren't the guild owner or an antinuke admin")
            return False
        return True

    return check(predicate)


def get_action(e: Union[AuditLogAction, AuditLogEntry]) -> str:
    if isinstance(e, AuditLogAction):
        if "webhook" in str(e).lower():
            return "webhooks"
        return (
            str(e)
            .split(".")[-1]
            .replace("create", "update")
            .replace("delete", "update")
        )

    else:
        if "webhook" in str(e.action).lower():
            return "webhooks"
        return (
            str(e.action)
            .replace("create", "update")
            .replace("delete", "update")
            .split(".")[-1]
        )


class ActionBucket:
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.actions: List[datetime] = []
        
    def add_action(self) -> int:
        now = datetime.utcnow()
        self.actions = [t for t in self.actions if now - t < timedelta(seconds=self.window_seconds)]
        self.actions.append(now)
        return len(self.actions)
        
    def get_count(self) -> int:
        now = datetime.utcnow()
        self.actions = [t for t in self.actions if now - t < timedelta(seconds=self.window_seconds)]
        return len(self.actions)


class RateLimiter:
    def __init__(self):
        self.buckets: Dict[str, ActionBucket] = {}
        
    def check_rate(self, key: str, threshold: int, window: int = 60) -> bool:
        if key not in self.buckets:
            self.buckets[key] = ActionBucket(window)
        return self.buckets[key].add_action() > threshold


class AntiNuke(Cog):
    """A class that implements an anti-nuke system to protect a guild from malicious actions."""

    def __init__(self, bot):
        self.bot = bot
        self.locks = defaultdict(Lock)
        self.punishments = {}
        self.guilds = {}
        self.thresholds = {}
        self.rate_limiters: Dict[int, RateLimiter] = {}
        self.cleanup_queue: Dict[int, Set[str]] = defaultdict(set)
        self.modules = [
            "bot_add",
            "role_update",
            "channel_update",
            "guild_update",
            "kick",
            "ban",
            "member_prune",
            "webhooks",
        ]

    async def cog_load(self):
        await self.bot.db.execute(
            """CREATE TABLE IF NOT EXISTS antinuke_threshold (guild_id BIGINT PRIMARY KEY, bot_add BIGINT DEFAULT 0, role_update BIGINT DEFAULT 0, channel_update BIGINT DEFAULT 0, guild_update BIGINT DEFAULT 0, kick BIGINT DEFAULT 0, ban BIGINT DEFAULT 0, member_prune BIGINT DEFAULT 0, webhooks BIGINT DEFAULT 0)"""
        )
        await self.make_cache()

    def serialize(self, data: dict):
        data.pop("guild_id", None)  # Use None as default to avoid KeyError
        return data

    async def make_cache(self):
        try:
            # Get all guilds with antinuke enabled
            rows = await self.bot.db.fetch(
                """SELECT guild_id, bot_add, role_update, channel_update, kick, ban, guild_update, member_prune, webhooks FROM antinuke"""
            )
            
            # Create guilds cache with enabled features
            self.guilds = {}
            for r in rows:
                try:
                    guild_id = r.guild_id
                    guild_dict = self.serialize(dict(r))
                    self.guilds[guild_id] = guild_dict
                except Exception as e:
                    logger.error(f"Error processing antinuke config for guild ID {getattr(r, 'guild_id', 'unknown')}: {str(e)}")
                    continue
            
            # Get all existing threshold entries
            threshold_rows = await self.bot.db.fetch(
                """SELECT * FROM antinuke_threshold"""
            )
            
            # Create thresholds cache
            self.thresholds = {}
            for r in threshold_rows:
                try:
                    guild_id = r.guild_id
                    guild_dict = self.serialize(dict(r))
                    self.thresholds[guild_id] = guild_dict
                except Exception as e:
                    logger.error(f"Error processing threshold for guild ID {getattr(r, 'guild_id', 'unknown')}: {str(e)}")
                    continue
                    
            return True
        except Exception as e:
            logger.error(f"Error rebuilding antinuke cache: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def make_reason(self, reason: str) -> str:
        return f"[ {self.bot.user.name} antinuke ] {reason}"

    async def get_thresholds(
        self, guild: Guild, action: Union[AuditLogAction,str]
    ) -> Optional[int]:
        try:
            if guild.id in self.guilds:
                # Get the action string if needed
                action_str = get_action(action) if isinstance(action, AuditLogAction) else action
                
                # If guild has thresholds in cache, check there first
                if guild.id in self.thresholds:
                    # Return the threshold from cache or 0 if not found
                    return self.thresholds[guild.id].get(action_str, 0)
                
                # If not in threshold cache, try database but don't create new entries
                try:
                    threshold = await self.bot.db.fetchval(
                        f"""SELECT {action_str} FROM antinuke_threshold WHERE guild_id = $1""",
                        guild.id,
                    )
                    if threshold is not None:
                        return int(threshold)
                except Exception:
                    pass
                    
            # Default to 0 for any missing thresholds
            return 0
        except Exception as e:
            logger.error(f"Error getting threshold for guild {guild.id}: {str(e)}")
            return 0
            
    async def do_ban(self, guild: Guild, user: Union[User, Member], reason: str):
        try:
            if hasattr(user, "top_role"):
                if user.top_role >= guild.me.top_role:
                    logger.error(f"Cannot ban {user.name} in {guild.name} - user's role is higher than bot's role")
                    return False
                if user.id == guild.owner_id:
                    logger.error(f"Cannot ban {user.name} in {guild.name} - user is the guild owner")
                    return False
            
            if await self.bot.glory_cache.ratelimited(f"punishment-{guild.id}-{user.id}", 3, 15) != 0:
                logger.error(f"Punishment for {user.name} in {guild.name} is ratelimited")
                return False

            await guild.ban(Object(user.id), reason=reason)
            logger.warning(f"Banned {user.name} ({user.id}) in {guild.name} for antinuke violation")
            return True
        except Exception as e:
            logger.error(f"Failed to ban {user.name} in {guild.name}: {str(e)}")
            return False

    async def do_kick(self, guild: Guild, user: Union[User, Member], reason: str):
        try:
            if hasattr(user, "top_role"):
                if user.top_role.position >= guild.me.top_role.position:
                    logger.error(f"Cannot kick {user.name} in {guild.name} - user's role is higher than bot's role")
                    return False
                if user.id == guild.owner_id:
                    logger.error(f"Cannot kick {user.name} in {guild.name} - user is the guild owner")
                    return False
            
            if await self.bot.glory_cache.ratelimited(f"punishment-{guild.id}-{user.id}", 3, 15) != 0:
                logger.error(f"Punishment for {user.name} in {guild.name} is ratelimited")
                return False
                
            await user.kick(reason=reason)
            logger.warning(f"Kicked {user.name} ({user.id}) in {guild.name} for antinuke violation")
            return True
        except Exception as e:
            logger.error(f"Failed to kick {user.name} in {guild.name}: {str(e)}")
            return False

    async def do_strip(self, guild: Guild, user: Union[Member, User], reason: str):
        try:
            if isinstance(user, User):
                logger.error(f"Cannot strip roles from {user.name} in {guild.name} - user is not a member")
                return False
                
            if user.top_role >= guild.me.top_role:
                logger.error(f"Cannot strip roles from {user.name} in {guild.name} - user's role is higher than bot's role")
                return False
                
            if user.id == guild.owner_id:
                logger.error(f"Cannot strip roles from {user.name} in {guild.name} - user is the guild owner")
                return False
                
            if await self.bot.glory_cache.ratelimited(f"punishment-{guild.id}-{user.id}", 3, 15) != 0:
                logger.error(f"Punishment for {user.name} in {guild.name} is ratelimited")
                return False
                
            after_roles = [r for r in user.roles if not r.is_assignable()]
            await user.edit(roles=after_roles, reason=reason)
            logger.warning(f"Stripped roles from {user.name} ({user.id}) in {guild.name} for antinuke violation")
            return True
        except Exception as e:
            logger.error(f"Failed to strip roles from {user.name} in {guild.name}: {str(e)}")
            return False

    async def do_punishment(self, guild: Guild, user: Union[User, Member], reason: str):
        try:
            punishment = await self.bot.db.fetchval(
                """SELECT punishment FROM antinuke WHERE guild_id = $1""", guild.id
            )
            if punishment is None:
                punishment = "ban"
            
            logger.warning(f"Antinuke punishment triggered: {punishment} for {user.name} ({user.id}) in {guild.name}")
            
            result = False
            if user.bot:
                if not guild.me.guild_permissions.ban_members:
                    logger.error(f"Cannot ban bot {user.name} in guild {guild.name} - missing ban_members permission")
                    return
                result = await self.do_ban(guild, user, reason)
            elif punishment.lower() == "ban":
                if not guild.me.guild_permissions.ban_members:
                    logger.error(f"Cannot ban user {user.name} in guild {guild.name} - missing ban_members permission")
                    return
                result = await self.do_ban(guild, user, reason)
            elif punishment.lower() == "kick":
                if not guild.me.guild_permissions.kick_members:
                    logger.error(f"Cannot kick user {user.name} in guild {guild.name} - missing kick_members permission")
                    return
                result = await self.do_kick(guild, user, reason)
            else:
                if not guild.me.guild_permissions.manage_roles:
                    logger.error(f"Cannot strip roles from user {user.name} in guild {guild.name} - missing manage_roles permission")
                    return
                result = await self.do_strip(guild, user, reason)
                
            if result:
                logger.warning(f"Successfully applied {punishment} to {user.name} ({user.id}) in {guild.name}")
            else:
                logger.error(f"Failed to apply {punishment} to {user.name} ({user.id}) in {guild.name}")
                
            return result
        except Exception as e:
            logger.error(f"Error in do_punishment for {user.name} in {guild.name}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def get_rate_limiter(self, guild_id: int) -> RateLimiter:
        if guild_id not in self.rate_limiters:
            self.rate_limiters[guild_id] = RateLimiter()
        return self.rate_limiters[guild_id]

    async def check_rate_limit(self, guild: Guild, user_id: int, action: Union[AuditLogAction, str], threshold: int) -> bool:
        if isinstance(action, AuditLogAction):
            action_str = get_action(action)
        else:
            action_str = action
            
        rate_limiter = self.get_rate_limiter(guild.id)
        key = f"{user_id}:{action_str}"
        
        return rate_limiter.check_rate(key, threshold)

    async def queue_cleanup(self, guild_id: int, action_key: str):
        self.cleanup_queue[guild_id].add(action_key)
        
    async def process_cleanup_queue(self, guild: Guild):
        if not self.cleanup_queue[guild.id]:
            return
            
        async with self.locks[f"cleanup-{guild.id}"]:
            for action_key in list(self.cleanup_queue[guild.id]):
                try:
                    await self.attempt_cleanup(guild.id, action_key)
                    self.cleanup_queue[guild.id].remove(action_key)
                except Exception as e:
                    logger.error(f"Failed cleanup for {action_key} in {guild.id}: {e}")
                await sleep(1)

    async def check_entry(self, guild: Guild, entry: AuditLogEntry) -> bool:
        if entry.user is None:
            return True
            
        try:
            threshold = await self.get_thresholds(guild, entry.action)
            
            if await self.bot.db.fetchval(
                "SELECT user_id FROM antinuke_whitelist WHERE user_id = $1 AND guild_id = $2",
                entry.user.id,
                guild.id,
            ):
                return True
                
            if (
                entry.user.id == guild.owner_id
                or entry.user.id == self.bot.user.id
                or (hasattr(entry.user, "top_role") and entry.user.top_role >= guild.me.top_role)
            ):
                return True
                
            if await self.check_rate_limit(guild, entry.user.id, entry.action, threshold):
                logger.warning(
                    f"User {entry.user.name} exceeded threshold for {entry.action} in {guild.name}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error in check_entry: {e}")
            
        return True

    def check_guild(self, guild: Guild, action: Union[AuditLogAction, str]):
        if guild.id in self.guilds:
            if isinstance(action, AuditLogAction):
                action_str = get_action(action)
                result = action_str in self.guilds[guild.id]
                if result:
                    enabled_value = self.guilds[guild.id].get(action_str)
                    return enabled_value
            else:
                result = action in self.guilds[guild.id]
                if result:
                    enabled_value = self.guilds[guild.id].get(action)
                    return enabled_value
        return False

    async def get_audit(self, guild: Guild, action: AuditLogAction = None):
        try:
            if not guild.me.guild_permissions.view_audit_log:
                logger.error(f"Missing view_audit_log permission in guild {guild.name} ({guild.id})")
                return None
                
            # For webhook actions, increase the time window to improve detection
            time_window = 5 if action in [AuditLogAction.webhook_create, AuditLogAction.webhook_update] else 3
                
            try:
                if action is not None:
                    audits = [
                        a
                        async for a in guild.audit_logs(
                            limit=2,  # Increased limit for better detection
                            after=utils.utcnow() - timedelta(seconds=time_window),
                            action=action,
                        )
                    ]
                    if not audits:
                        return None
                    audit = audits[0]  # Get the most recent entry
                else:
                    audit = [
                        a
                        async for a in guild.audit_logs(
                            limit=1, after=utils.utcnow() - timedelta(seconds=time_window)
                        )
                    ][0]
                    
                # Handle bot actions with reason containing user ID
                if audit.user_id == self.bot.user.id and audit.reason and "|" in audit.reason:
                    try:
                        user_id = int(audit.reason.split(" | ")[-1].strip())
                        audit.user = self.bot.get_user(user_id)
                        if audit.guild.id == 1237821518940209212:
                            logger.info(f"user {str(audit.user)} invoked an event for {audit.action} on {str(audit.target)}")
                    except (ValueError, IndexError):
                        pass
                        
                # For webhook entries, additional logging to debug detection
                if action in [AuditLogAction.webhook_create, AuditLogAction.webhook_update]:
                    logger.debug(f"Found webhook audit entry: action={audit.action}, user={audit.user}, target={getattr(audit.target, 'name', 'unknown')}")
                    
                return audit
            except IndexError:
                logger.debug(f"No matching audit log entries found for action {action} in guild {guild.name}")
                return None
        except Exception as e:
            logger.error(f"Error getting audit logs in guild {guild.name}: {str(e)}")
            return None

    async def check_role(self, role: Role) -> bool:
        if (
            role.permissions.administrator
            or role.permissions.manage_guild
            or role.permissions.kick_members
            or role.permissions.ban_members
            or role.permissions.manage_roles
            or role.permissions.manage_channels
            or role.permissions.manage_webhooks
        ):
            return True
        return False

    async def get_channel_state(self, channel) -> dict:
        try:
            # Base attributes for all channel types
            state = {
                "name": getattr(channel, "name", "Unknown Channel"),
                "position": getattr(channel, "position", 0),
            }
            
            # Safely check and store attributes by type
            if hasattr(channel, "overwrites"):
                state["overwrites"] = channel.overwrites
                
            if hasattr(channel, "topic"):
                state["topic"] = channel.topic
                
            if hasattr(channel, "slowmode_delay"):
                state["slowmode_delay"] = channel.slowmode_delay
                
            if hasattr(channel, "nsfw"):
                state["nsfw"] = channel.nsfw
                
            if hasattr(channel, "bitrate"):
                state["bitrate"] = channel.bitrate
                
            if hasattr(channel, "user_limit"):
                state["user_limit"] = channel.user_limit
                
            if hasattr(channel, "rtc_region"):
                state["rtc_region"] = channel.rtc_region
                
            if hasattr(channel, "video_quality_mode"):
                state["video_quality_mode"] = channel.video_quality_mode
                
            # Store channel type information
            if hasattr(channel, "type"):
                state["type"] = str(channel.type.name)
                
            return state
        except Exception as e:
            logger.error(f"Error getting channel state for {getattr(channel, 'name', 'Unknown')}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"name": "Unknown Channel", "error": True}

    async def get_role_state(self, role: Role) -> dict:
        try:
            state = {
                "name": getattr(role, "name", "Unknown Role"),
                "permissions": Permissions(getattr(role, "permissions", Permissions.none()).value),
                "color": getattr(role, "color", 0),
                "hoist": getattr(role, "hoist", False),
                "mentionable": getattr(role, "mentionable", False)
            }
            return state
        except Exception as e:
            logger.error(f"Error getting role state for {getattr(role, 'name', 'Unknown')}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"name": "Unknown Role", "permissions": Permissions.none(), "error": True}

    async def get_guild_state(self, guild: Guild) -> dict:
        state = {
            "name": guild.name,
            "description": guild.description,
        }
        
        if guild.icon:
            try:
                state["icon_bytes"] = await guild.icon.read()
            except:
                pass
                
        if guild.banner:
            try:
                state["banner_bytes"] = await guild.banner.read()
            except:
                pass
                
        if guild.splash:
            try:
                state["splash_bytes"] = await guild.splash.read()
            except:
                pass
                
        return state

    async def attempt_cleanup(self, guild_id: int, action_key: str):
        """Helper method to attempt cleanup actions with retries"""
        for _ in range(5):  # Try up to 5 times
            if await self.bot.glory_cache.ratelimited(f"cleanup-{guild_id}", 1, 10) == 0:
                try:
                    return await self.attempt_cleanup_action(guild_id, action_key)
                except Exception:
                    pass
            await sleep(2)  # Wait 2 seconds before next attempt
        return None

    async def attempt_cleanup_action(self, guild_id: int, action_key: str):
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
            
        try:
            action_type, target_id = action_key.split(":")
            target_id = int(target_id)
            
            # Initialize storage if needed
            await self.initialize_guild_storage(guild)
            
            if action_type == "role_delete":
                # Try to recreate the deleted role
                deleted_roles = getattr(guild, "_deleted_roles", {})
                if target_id in deleted_roles:
                    role_data = deleted_roles[target_id]
                    try:
                        await guild.create_role(
                            name=role_data.get("name", "Restored Role"),
                            permissions=role_data.get("permissions", Permissions.none()),
                            color=role_data.get("color", 0),
                            hoist=role_data.get("hoist", False),
                            mentionable=role_data.get("mentionable", False),
                            reason=self.make_reason("Restoring deleted role")
                        )
                        logger.info(f"Restored deleted role {role_data.get('name')} in {guild.name}")
                    except Exception as e:
                        logger.error(f"Failed to restore role {target_id}: {e}")
                else:
                    logger.warning(f"No data found for deleted role {target_id} in guild {guild.id}")
                
            elif action_type == "role_update":
                # Restore role permissions and attributes
                role = guild.get_role(target_id)
                if role:
                    role_data = getattr(role, "_before_state", None)
                    if role_data:
                        try:
                            edit_kwargs = {k: v for k, v in role_data.items()}
                            await role.edit(**edit_kwargs, reason=self.make_reason("Restoring role settings"))
                            logger.info(f"Restored role settings for {role.name} in {guild.name}")
                        except Exception as e:
                            logger.error(f"Failed to restore role settings for {role.name}: {e}")
                    else:
                        logger.warning(f"No previous state found for role {role.name} in guild {guild.id}")
                else:
                    logger.warning(f"Role {target_id} not found in guild {guild.id}")
                    
            elif action_type == "channel_delete":
                # Try to recreate the deleted channel
                channel = guild.get_channel(target_id)
                if not channel:  # Channel was indeed deleted
                    deleted_channels = getattr(guild, "_deleted_channels", {})
                    if target_id in deleted_channels:
                        channel_data = deleted_channels[target_id]
                        try:
                            if channel_data.get("type") == "text":
                                await guild.create_text_channel(
                                    name=channel_data.get("name", "restored-channel"),
                                    topic=channel_data.get("topic"),
                                    position=channel_data.get("position"),
                                    overwrites=channel_data.get("overwrites", {}),
                                    reason=self.make_reason("Restoring deleted channel")
                                )
                            elif channel_data.get("type") == "voice":
                                await guild.create_voice_channel(
                                    name=channel_data.get("name", "Restored Channel"),
                                    position=channel_data.get("position"),
                                    overwrites=channel_data.get("overwrites", {}),
                                    reason=self.make_reason("Restoring deleted channel")
                                )
                            logger.info(f"Restored deleted channel {channel_data.get('name')} in {guild.name}")
                        except Exception as e:
                            logger.error(f"Failed to restore channel {target_id}: {e}")
                    else:
                        logger.warning(f"No data found for deleted channel {target_id} in guild {guild.id}")
                
            elif action_type == "channel_update":
                # Restore channel settings
                channel = guild.get_channel(target_id)
                if channel:
                    # Safely check if attribute exists
                    before_state = getattr(channel, "_before_state", None)
                    if before_state:
                        try:
                            update_kwargs = {k: v for k, v in before_state.items() if hasattr(channel, k)}
                            if update_kwargs:
                                await channel.edit(**update_kwargs, reason=self.make_reason("Restoring channel settings"))
                                logger.info(f"Restored channel settings for {channel.name} in {guild.name}")
                        except Exception as e:
                            logger.error(f"Failed to restore channel settings for {channel.name}: {e}")
                    else:
                        logger.warning(f"No previous state found for channel {channel.name} in guild {guild.id}")
                else:
                    logger.warning(f"Channel {target_id} not found in guild {guild.id}")
                
            elif action_type == "webhook_create":
                # Delete unauthorized webhooks
                channel = guild.get_channel(target_id)
                if channel:
                    try:
                        webhooks = await channel.webhooks()
                        deleted = 0
                        for webhook in webhooks:
                            try:
                                await webhook.delete(reason=self.make_reason("Removing unauthorized webhook"))
                                deleted += 1
                            except Exception:
                                pass
                        if deleted > 0:
                            logger.info(f"Deleted {deleted} unauthorized webhooks in channel {channel.name}")
                    except Exception as e:
                        logger.error(f"Error cleaning up webhooks in {channel.name}: {e}")
                else:
                    logger.warning(f"Channel {target_id} not found in guild {guild.id}")
                        
            elif action_type == "role_assignment":
                # Remove dangerous roles from a member
                member = guild.get_member(target_id)
                if member:
                    try:
                        # Safely access _dangerous_roles with getattr and fallback
                        dangerous_roles = getattr(member, "_dangerous_roles", [])
                        if dangerous_roles:
                            await member.remove_roles(*dangerous_roles, reason=self.make_reason("Removing unauthorized roles"))
                            logger.info(f"Removed dangerous roles from {member.name} in {guild.name}")
                        else:
                            logger.warning(f"No dangerous roles found for member {member.name} in guild {guild.id}")
                    except Exception as e:
                        logger.error(f"Failed to remove dangerous roles from {member.name}: {e}")
                else:
                    logger.warning(f"Member {target_id} not found in guild {guild.id}")
                        
            elif action_type == "ban":
                # Unban a member if they were banned incorrectly
                try:
                    await guild.unban(Object(target_id), reason=self.make_reason("Reversing unauthorized ban"))
                    logger.info(f"Unbanned user {target_id} in {guild.name}")
                except Exception as e:
                    logger.error(f"Failed to unban user {target_id}: {e}")
                    
            elif action_type == "guild_update":
                # Restore guild settings
                before_state = getattr(guild, "_before_state", None)
                if before_state:
                    try:
                        edit_kwargs = {}
                        if "name" in before_state:
                            edit_kwargs["name"] = before_state["name"]
                        if "description" in before_state:
                            edit_kwargs["description"] = before_state["description"]
                        if "icon_bytes" in before_state:
                            edit_kwargs["icon"] = before_state["icon_bytes"]
                        if "banner_bytes" in before_state:
                            edit_kwargs["banner"] = before_state["banner_bytes"]
                        if "splash_bytes" in before_state:
                            edit_kwargs["splash"] = before_state["splash_bytes"]
                            
                        if edit_kwargs:
                            await guild.edit(**edit_kwargs, reason=self.make_reason("Restoring guild settings"))
                            logger.info(f"Restored settings for guild {guild.name}")
                        else:
                            logger.warning(f"No settings to restore for guild {guild.name}")
                    except Exception as e:
                        logger.error(f"Failed to restore guild settings for {guild.name}: {e}")
                else:
                    logger.warning(f"No previous state found for guild {guild.id}")
                    
        except Exception as e:
            logger.error(f"Error during cleanup action {action_key} in guild {guild.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def handle_action(self, guild: Guild, entry: AuditLogEntry, cleanup_key: Optional[str] = None):
        if not await self.check_entry(guild, entry):
            if cleanup_key:
                await self.queue_cleanup(guild.id, cleanup_key)
                
            reason = self.make_reason(f"User caught performing {entry.action}")
            await self.do_punishment(guild, entry.user, reason)
            
            await self.process_cleanup_queue(guild)
            return False
        return True

    @Cog.listener("on_guild_role_update")
    async def role_update(self, before: Role, after: Role):
        try:
            if not before.guild.me.guild_permissions.view_audit_log:
                return
                
            # Only trigger for roles with dangerous permissions
            if await self.check_role(after) is not True:
                return
                
            if self.check_guild(after.guild, "role_update") is not True:
                return
                
            entry = await self.get_audit(after.guild, AuditLogAction.role_update)
            if entry is None:
                return
                
            # Initialize storage if needed
            storage_initialized = await self.initialize_guild_storage(after.guild)
            if not storage_initialized:
                logger.warning(f"Failed to initialize guild storage for role_update in {after.guild.id}")
            
            # Initialize attributes on the role object
            try:
                await self.initialize_object_attributes(after)
            except Exception as e:
                logger.error(f"Failed to initialize attributes for role {after.id}: {e}")
                import traceback
                logger.error(traceback.format_exc())

            # Store the previous state
            try:
                role_state = await self.get_role_state(before)
                attr_set = self.safe_set_attribute(after, "_before_state", role_state)
                if attr_set:
                    logger.info(f"Stored state for updated role {after.name} in {after.guild.name}")
                else:
                    logger.warning(f"Failed to store state for role {after.id} in guild {after.guild.id}")
            except Exception as e:
                logger.error(f"Failed to store role state: {e}")
                import traceback
                logger.error(traceback.format_exc())
            
            cleanup_key = f"role_update:{after.id}"
            await self.handle_action(after.guild, entry, cleanup_key)
        except Exception as e:
            logger.error(f"Error in role_update handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener("on_guild_role_delete") 
    async def role_delete(self, role: Role):
        try:
            guild = role.guild
            if self.check_guild(guild, "role_update") is not True:
                return
                
            # Safely initialize storage
            storage_initialized = await self.initialize_guild_storage(guild)
            if not storage_initialized:
                logger.warning(f"Failed to initialize guild storage for {guild.id}")
            
            # Store role state before it's fully deleted
            try:
                role_state = await self.get_role_state(role)
                
                # Get deleted_roles dictionary from our storage
                deleted_roles = self.safe_get_attribute(guild, "_deleted_roles", {})
                if isinstance(deleted_roles, dict):
                    # Add this role's state to the dictionary
                    deleted_roles[role.id] = role_state
                    
                    # Update the storage
                    self.safe_set_attribute(guild, "_deleted_roles", deleted_roles)
                    logger.info(f"Stored state for deleted role {role.name} in {guild.name}")
                else:
                    logger.warning(f"Deleted roles storage for guild {guild.id} is not a dictionary")
            except Exception as e:
                logger.error(f"Failed to store deleted role state: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            entry = await self.get_audit(guild, AuditLogAction.role_delete)
            if entry is None:
                return
                
            cleanup_key = f"role_delete:{role.id}"
            await self.handle_action(guild, entry, cleanup_key)
        except Exception as e:
            logger.error(f"Error in role_delete handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener("on_guild_channel_delete")
    async def channel_delete(self, channel):
        try:
            guild = channel.guild
            if self.check_guild(guild, "channel_update") is not True:
                return
                
            # Safely initialize storage
            storage_initialized = await self.initialize_guild_storage(guild)
            if not storage_initialized:
                logger.warning(f"Failed to initialize guild storage for {guild.id}")
                
            # Store channel state before it's fully deleted
            try:
                channel_state = await self.get_channel_state(channel)
                if hasattr(channel, "type"):
                    channel_state["type"] = channel.type.name
                
                # Get deleted_channels dictionary from our storage
                deleted_channels = self.safe_get_attribute(guild, "_deleted_channels", {})
                if isinstance(deleted_channels, dict):
                    # Add this channel's state to the dictionary
                    deleted_channels[channel.id] = channel_state
                    
                    # Update the storage
                    self.safe_set_attribute(guild, "_deleted_channels", deleted_channels)
                    logger.info(f"Stored state for deleted channel {channel.name} in {guild.name}")
                else:
                    logger.warning(f"Deleted channels storage for guild {guild.id} is not a dictionary")
                
            except Exception as e:
                logger.error(f"Failed to store deleted channel state: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            entry = await self.get_audit(guild, AuditLogAction.channel_delete)
            if entry is None:
                return
                
            cleanup_key = f"channel_delete:{channel.id}"
            await self.handle_action(guild, entry, cleanup_key)
        except Exception as e:
            logger.error(f"Error in channel_delete handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener("on_guild_channel_update")
    async def channel_update(self, before, after):
        try:
            guild = after.guild
            if self.check_guild(guild, "channel_update") is not True:
                return
                
            entry = await self.get_audit(guild, AuditLogAction.channel_update)
            if entry is None:
                return
                
            # Initialize storage if needed
            storage_initialized = await self.initialize_guild_storage(guild)
            if not storage_initialized:
                logger.warning(f"Failed to initialize guild storage for channel_update in {guild.id}")
            
            # Initialize attributes on the channel object - use a try/except block to catch any errors
            try:
                await self.initialize_object_attributes(after)
            except Exception as e:
                logger.error(f"Failed to initialize attributes for channel {after.id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            # Store the previous state based on channel type
            try:
                channel_state = await self.get_channel_state(before)
                # Use safer method to set attribute
                attr_set = self.safe_set_attribute(after, "_before_state", channel_state)
                if attr_set:
                    logger.info(f"Stored state for updated channel {after.name} in {guild.name}")
                else:
                    logger.warning(f"Failed to store state for channel {after.id} in guild {guild.id}")
            except Exception as e:
                logger.error(f"Failed to store channel state: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            cleanup_key = f"channel_update:{after.id}"
            await self.handle_action(guild, entry, cleanup_key)
        except Exception as e:
            logger.error(f"Error in channel_update handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener()
    async def on_webhooks_update(self, channel: TextChannel):
        try:
            guild: Guild = channel.guild
            
            webhook_protection = self.check_guild(guild, AuditLogAction.webhook_create)
            if webhook_protection is not True:
                return
                
            # Check for both webhook creation and update events
            entry: Optional[AuditLogEntry] = await self.get_audit(guild, AuditLogAction.webhook_create)
            if entry is None:
                entry = await self.get_audit(guild, AuditLogAction.webhook_update)
                if entry is None:
                    return
                    
            # Get the webhook target - entry.target is an Object with the webhook ID when action is webhook related
            webhook_id: int = entry.target.id if entry.target else 0
            if not webhook_id:
                logger.warning(f"No webhook ID found in audit log entry for guild {guild.name}")
                return
                
            # Store webhook state for potential cleanup
            try:
                # In webhook events, the target is an Object with limited attributes
                # The differences contain the actual webhook data
                webhook_state: Dict[str, Any] = {
                    "id": webhook_id,
                    "name": None,
                    "channel_id": None,
                    "type": 1,
                    "avatar": None,
                    "created_at": entry.created_at,
                    "created_by": entry.user.id if entry.user else None
                }
                
                # Extract webhook information from the audit log entry changes
                if entry.changes:
                    if hasattr(entry.changes, "name"):
                        webhook_state["name"] = entry.changes.name.new
                    if hasattr(entry.changes, "channel"):
                        webhook_state["channel_id"] = getattr(entry.changes.channel.new, "id", None)
                    if hasattr(entry.changes, "type"):
                        webhook_state["type"] = entry.changes.type.new
                    if hasattr(entry.changes, "avatar"):
                        webhook_state["avatar"] = entry.changes.avatar.new
                
                # If name is still None, use a fallback
                if webhook_state["name"] is None:
                    webhook_state["name"] = "Unknown Webhook"
                
                # If channel_id is still None but we have a channel, use it
                if webhook_state["channel_id"] is None and hasattr(entry.target, "channel_id"):
                    webhook_state["channel_id"] = entry.target.channel_id
                elif webhook_state["channel_id"] is None:
                    webhook_state["channel_id"] = channel.id
                
                # Initialize storage if needed
                storage_initialized: bool = await self.initialize_guild_storage(guild)
                if not storage_initialized:
                    logger.warning(f"Failed to initialize guild storage for webhook event in {guild.id}")
                
                # Store webhook state
                webhooks: Dict[int, Dict[str, Any]] = self.safe_get_attribute(guild, "_webhooks", {})
                webhooks[webhook_id] = webhook_state
                self.safe_set_attribute(guild, "_webhooks", webhooks)
                
                logger.info(f"Stored state for webhook {webhook_state['name']} in {guild.name}")
            except Exception as e:
                logger.error(f"Failed to store webhook state: {e}")
                import traceback
                logger.error(traceback.format_exc())
                    
            cleanup_key: str = f"webhook_create:{webhook_id}"
            await self.handle_action(guild, entry, cleanup_key)
            
        except Exception as e:
            logger.error(f"Error in webhook detection: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener()
    async def on_webhook_delete(self, webhook: Webhook):
        try:
            guild: Guild = webhook.guild
            
            webhook_protection = self.check_guild(guild, AuditLogAction.webhook_delete)
            if webhook_protection is not True:
                return
                
            entry: Optional[AuditLogEntry] = await self.get_audit(guild, AuditLogAction.webhook_delete)
            if entry is None:
                return
                
            # Get the webhook ID - for webhook_delete we have the actual webhook object
            webhook_id: int = webhook.id
                
            # Store deleted webhook state
            try:
                # We have the actual webhook object here, so use its attributes
                webhook_state: Dict[str, Any] = {
                    "id": webhook_id,
                    "name": webhook.name,
                    "channel_id": webhook.channel_id,
                    "type": 1,  # Standard webhook type
                    "avatar": webhook.avatar.url if webhook.avatar else None,
                    "deleted_at": entry.created_at if entry else datetime.utcnow(),
                    "deleted_by": entry.user.id if entry and entry.user else None
                }
                
                # Initialize storage if needed
                storage_initialized: bool = await self.initialize_guild_storage(guild)
                if not storage_initialized:
                    logger.warning(f"Failed to initialize guild storage for webhook deletion in {guild.id}")
                
                # Store deleted webhook state
                deleted_webhooks: Dict[int, Dict[str, Any]] = self.safe_get_attribute(guild, "_deleted_webhooks", {})
                deleted_webhooks[webhook_id] = webhook_state
                self.safe_set_attribute(guild, "_deleted_webhooks", deleted_webhooks)
                
                logger.info(f"Stored state for deleted webhook {webhook_state['name']} in {guild.name}")
            except Exception as e:
                logger.error(f"Failed to store deleted webhook state: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            if entry:
                cleanup_key: str = f"webhook_delete:{webhook_id}"
                await self.handle_action(guild, entry, cleanup_key)
            
        except Exception as e:
            logger.error(f"Error in webhook deletion detection: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener("on_audit_log_entry_create")
    async def on_member_action(self, entry: AuditLogEntry):
        if self.check_guild(entry.guild, entry.action) is False:
            return
            
        if entry.action in [AuditLogAction.kick, AuditLogAction.ban, AuditLogAction.member_prune]:
            if entry.user_id == self.bot.user.id and entry.reason and "|" in entry.reason:
                entry.user = self.bot.get_user(int(entry.reason.split(" | ")[-1].strip()))
                
            cleanup_key = None
            if entry.action == AuditLogAction.ban:
                cleanup_key = f"ban:{entry.target.id}"
                
            await self.handle_action(entry.guild, entry, cleanup_key)

    @Cog.listener("on_member_update")
    async def dangerous_role_assignment(self, before: Member, after: Member):
        try:
            if not before.guild.me.guild_permissions.view_audit_log:
                return
                
            if before.roles == after.roles:
                return
                
            if self.check_guild(after.guild, "role_update") is not True:
                return
                
            new_roles = [r for r in after.roles if r not in before.roles and r.is_assignable()]
            if not new_roles:
                return
                
            dangerous_roles = []
            for role in new_roles:
                if await self.check_role(role):
                    dangerous_roles.append(role)
                    
            if not dangerous_roles:
                return
                
            # Initialize guild storage
            await self.initialize_guild_storage(after.guild)
            
            # Initialize attributes on the member object
            await self.initialize_object_attributes(after, {"_dangerous_roles": dangerous_roles})
            
            logger.info(f"Found {len(dangerous_roles)} dangerous roles assigned to {after.name}")
                
            entry = await self.get_audit(after.guild, AuditLogAction.member_role_update)
            if not entry:
                return
                
            if after.guild.me.top_role.position <= after.top_role.position:
                return
                
            cleanup_key = f"role_assignment:{after.id}"
            await self.handle_action(after.guild, entry, cleanup_key)
        except Exception as e:
            logger.error(f"Error in dangerous_role_assignment handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener("on_guild_update")
    async def change_guild(self, before: Guild, after: Guild):
        try:
            if self.check_guild(after, "guild_update") is not True:
                return
                
            # Initialize storage if needed
            storage_initialized = await self.initialize_guild_storage(after)
            if not storage_initialized:
                logger.warning(f"Failed to initialize guild storage for guild_update in {after.id}")
            
            # Initialize attributes on the guild object
            try:
                await self.initialize_object_attributes(after)
            except Exception as e:
                logger.error(f"Failed to initialize attributes for guild {after.id}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            # Store the previous state
            try:
                guild_state = await self.get_guild_state(before)
                attr_set = self.safe_set_attribute(after, "_before_state", guild_state)
                if attr_set:
                    logger.info(f"Stored state for updated guild {after.name}")
                else:
                    logger.warning(f"Failed to store state for guild {after.id}")
            except Exception as e:
                logger.error(f"Failed to store guild state: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            entry = await self.get_audit(after, AuditLogAction.guild_update)
            if not entry:
                return
                
            cleanup_key = f"guild_update:{after.id}"
            await self.handle_action(after, entry, cleanup_key)
        except Exception as e:
            logger.error(f"Error in guild_update handler: {e}")
            import traceback
            logger.error(traceback.format_exc())

    @Cog.listener("on_member_join")
    async def antibot(self, member: Member):
        try:
            if not member.bot:
                return
                
            guild = member.guild
            if self.check_guild(guild, "bot_add") is not True:
                return
                
            entry = await self.get_audit(guild, AuditLogAction.bot_add)
            if not entry:
                return
                
            cleanup_key = f"bot_add:{member.id}"
            if not await self.handle_action(guild, entry, cleanup_key):
                try:
                    await member.ban(reason=self.make_reason("Cleanup"))
                except Exception as e:
                    logger.error(f"Failed to ban bot {member.id}: {e}")
        except Exception as e:
            logger.error(f"Error in antibot handler: {e}")

    @hybrid_group(
        name="antinuke",
        aliases=["an"],
        brief="protect your guild from nukers",
        with_app_command=True,
        example=",antinuke",
    )
    @bot_has_permissions(administrator=True)
    async def antinuke(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @antinuke.command(
        name="enable",
        aliases=["e", "setup", "on"],
        brief="Enable all antinuke settings with a default threshold of 0",
        example=",antinuke enable",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_enable(self, ctx: Context):
        await self.bot.db.execute(
            """INSERT INTO antinuke (guild_id, bot_add, guild_update, channel_update, role_update, kick, ban, webhooks, member_prune, threshold) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) ON CONFLICT (guild_id) DO UPDATE SET bot_add = excluded.bot_add, guild_update = excluded.guild_update, role_update = excluded.role_update, channel_update = excluded.channel_update, webhooks = excluded.webhooks, kick = excluded.kick, ban = excluded.ban, member_prune = excluded.member_prune, threshold = excluded.threshold""",
            ctx.guild.id,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            True,
            0,
        )
        self.guilds[ctx.guild.id] = {
            "bot_add": True,
            "guild_update": True,
            "channel_update": True,
            "role_update": True,
            "kick": True,
            "ban": True,
            "webhooks": True,
            "member_prune": True,
            "threshold": 0,
        }
        return await ctx.success("antinuke is now **enabled**")

    @antinuke.command(
        name="disable",
        aliases=["off", "d", "reset"],
        brief="Disable all antinuke settings",
        example=",antinuke disable",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_disable(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM antinuke WHERE guild_id = $1""", ctx.guild.id
        )
        try:
            self.guilds.pop(ctx.guild.id)
        except Exception:
            pass
        return await ctx.success("antinuke is now **disabled**")

    @antinuke.command(
        name="punishment",
        aliases=["punish"],
        brief="Set a punishment a user will recieve for breaking an antinuke rule",
        example=",antinuke punishment ban",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_punishment(self, ctx: Context, punishment: str):
        if punishment.lower() not in ["ban", "kick", "strip"]:
            return await ctx.fail(
                "punishment not **recognizied**, please use one of the following `ban`, `kick`, `strip`"
            )
        await self.bot.db.execute(
            """UPDATE antinuke SET punishment = $1 WHERE guild_id = $2""",
            punishment,
            ctx.guild.id,
        )
        return await ctx.success(f"antinuke **punishment** set to `{punishment}`")

    @antinuke.command(
        name="whitelist",
        aliases=["wl"],
        brief="Whitelist or unwhitelist a user from being punished by antinuke",
        example=",antinuke whitelist @sudosql",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_whitelist(self, ctx: Context, *, user: Union[User, Member]):
        if await self.bot.db.fetchval(
            """SELECT user_id FROM antinuke_whitelist WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            user.id,
        ):
            await self.bot.db.execute(
                """DELETE FROM antinuke_whitelist WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                user.id,
            )
            return await ctx.success(f"successfully **unwhitelisted** {user.mention}")
        else:
            await self.bot.db.execute(
                """INSERT INTO antinuke_whitelist (guild_id, user_id) VALUES($1,$2) ON CONFLICT(guild_id,user_id) DO NOTHING""",
                ctx.guild.id,
                user.id,
            )
            return await ctx.success(f"successfully **whitelisted** {user.mention}")

    @antinuke.command(
        name="trust",
        aliases=["admin"],
        brief="Permit a user to use antinuke commands as an antinuke admin",
        example=",antinuke trust @sudosql",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_trust(self, ctx: Context, *, user: Union[User, Member]):
        if await self.bot.db.fetchval(
            """SELECT user_id FROM antinuke_admin WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            user.id,
        ):
            await self.bot.db.execute(
                """DELETE FROM antinuke_admin WHERE guild_id = $1 AND user_id = $2""",
                ctx.guild.id,
                user.id,
            )
            return await ctx.success(f"successfully **untrusted** {user.mention}")
        else:
            await self.bot.db.execute(
                """INSERT INTO antinuke_admin (guild_id, user_id) VALUES($1,$2) ON CONFLICT(guild_id,user_id) DO NOTHING""",
                ctx.guild.id,
                user.id,
            )
            return await ctx.success(f"successfully **trusted** {user.mention}")

    @antinuke.command(
        name="whitelisted",
        aliases=["whitelists", "wld"],
        brief="List all users that cannot be effected by antinuke",
        example=",antinuke whitelisted",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_whitelisted(self, ctx: Context):
        if rows := await self.bot.db.fetch(
            """SELECT user_id FROM antinuke_whitelist WHERE guild_id = $1""",
            ctx.guild.id,
        ):
            i = 0
            users = []
            for row in rows:
                i += 1
                users.append(f"`{i}` <@!{row.user_id}>")
            embed = Embed(title="Whitelists", color=self.bot.color)
            if len(users) > 0:
                return await self.bot.dummy_paginator(ctx, embed, users)

    @antinuke.command(
        name="trusted",
        aliases=["admins"],
        brief="List all users who are antinuke admins",
        example=",antinuke trusted",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_trusted(self, ctx: Context):
        if rows := await self.bot.db.fetch(
            """SELECT user_id FROM antinuke_admin WHERE guild_id = $1""", ctx.guild.id
        ):
            i = 0
            users = []
            for row in rows:
                i += 1
                users.append(f"`{i}` <@!{row.user_id}>")
            embed = Embed(title="Admins", color=self.bot.color)
            if len(users) > 0:
                return await self.bot.dummy_paginator(ctx, embed, users)

    @antinuke.command(
        name="threshold",
        brief="Set the threshold until antinuke bans the user",
        example=",antinuke threshold",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_threshold(self, ctx: Context, action: str, threshold: int):
        if action not in self.modules:
            return await ctx.fail("invalid action provided")
        if await self.bot.db.fetch(
            """SELECT * FROM antinuke_threshold WHERE guild_id = $1""", ctx.guild.id
        ):
            await self.bot.db.execute(
                f"""UPDATE antinuke_threshold SET {action} = $1 WHERE guild_id = $2""",
                threshold,
                ctx.guild.id,
            )
        else:
            await self.bot.db.execute(
                f"""INSERT INTO antinuke_threshold (guild_id, {action}) VALUES($1, $2)""",
                ctx.guild.id,
                threshold,
            )

        #            return await ctx.fail(f"antinuke not **setup**")
        await self.make_cache()
        return await ctx.success(
            f"antinuke **threshold** set to `{threshold}` for **{action}**"
        )

    async def get_users(self, ctx: Context, whitelisted: Optional[bool] = False):
        if whitelisted is False:
            users = [
                r.user_id
                for r in await self.bot.db.fetch(
                    """SELECT user_id FROM antinuke_admin WHERE guild_id = $1""",
                    ctx.guild.id,
                )
            ]
        else:
            users = [
                r.user_id
                for r in await self.bot.db.fetch(
                    """SELECT user_id FROM antinuke_whitelist WHERE guild_id = $1""",
                    ctx.guild.id,
                )
            ]
        _ = []
        for m in users:
            if user := self.bot.get_user(m):
                _.append(user)
        _.append(ctx.guild.owner)
        return _

    async def find_thres(self, guild: Guild, action: str):
        d = await self.get_thresholds(guild, action)
        if not d:
            d = 0
        return (action, d)

    def format_module(self, module: str):
        module = module.replace("_", " ")
        return f"**anti [{module}]({self.bot.domain}):**"

    @antinuke.command(
        name="settings",
        aliases=["config"],
        brief="List your antinuke settings along with their thresholds",
        example=",antinuke settings",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_settings(self, ctx: Context):
        data = await self.bot.db.fetchrow(
            """SELECT * FROM antinuke WHERE guild_id = $1""", ctx.guild.id
        )
        if not data:
            return await ctx.fail("antinuke not **setup**")
        try:
            thresholds = await gather(
                *[self.find_thres(ctx.guild, a) for a in self.modules]
            )
            thresholds = {a[0]: a[1] for a in thresholds}
        except Exception:
            thresholds = {a: 0 for a in self.modules}
        #        thresholds = await self.get_threshold(ctx.guild.id, {m: 0 for m in self.modules})
        embed = Embed(title="Antinuke Settings", color=self.bot.color)
        d = dict(data)
        d.pop("guild_id")
        description = f"**Punishment:** `{d.get('punishment','ban')}`\n"
        try:
            d.pop("punishment")
        except Exception:
            pass
        for k, v in d.items():
            if isinstance(v, tuple) or isinstance(k, tuple):
                logger.info(f"{k} - {v}")
                continue
            if k == "threshold":
                continue
            if k in self.modules:
                threshold = thresholds.get(k)
                #                if threshold == 0: threshold+=1
                if threshold:
                    threshold_message = f"- limit: `{threshold}`"
                else:
                    threshold_message = ""
            else:
                threshold_message = ""
            if isinstance(v, int):
                if v == 0:
                    v = self.bot.cogs["Automod"].get_state(False)
                    threshold_message = ""
                else:
                    v = self.bot.cogs["Automod"].get_state(True)
                description += f"{self.format_module(k)} {v}{threshold_message}\n"
            else:
                if k != "punishment":
                    v = self.bot.cogs["Automod"].get_state(bool(v))
                    #                    embed.add_field(
                    #                       name=k.replace("_", " "),
                    #                      value=(
                    #                         f"`enabled`{threshold_message}"
                    #                        if bool(v) == True
                    #                       else f"`disabled`{threshold_message}"
                    #                  ),
                    #                 inline=False,
                    #            )
                    description += f"{self.format_module(k)} {v}{threshold_message}\n"
        embed.description = description
        whitelisted = [user for user in await self.get_users(ctx, True) if user is not None]
        admins = [user for user in await self.get_users(ctx, False) if user is not None]
        if len(whitelisted) > 0:
            embed.add_field(
                name="Whitelisted",
                value=", ".join(m.mention for m in whitelisted),
                inline=True,
            )
        if len(admins) > 0:
            embed.add_field(
                name="Admins", value=", ".join(m.mention for m in admins), inline=True
            )
        return await ctx.send(embed=embed)

    @antinuke.command(
        name="botadd",
        aliases=["bot", "ba", "bot_add"],
        brief="Toggle the anti bot add of antinuke",
        example=",antinuke bot_add true",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_bot_add(self, ctx: Context, state: bool):
        return await self.antinuke_toggle(ctx, "bot_add", state)

    @antinuke.command(
        name="role",
        brief="toggle the anti role update of antinuke",
        aliases=["roles", "role_update"],
        parameters={
            "threshold": {
                "type": int,
                "required": False,
                "brief": "set the threshold until antinuke bans the user",
            }
        },
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_role_update(self, ctx: Context, state: bool):
        return await self.antinuke_toggle(ctx, "role_update", state)

    @antinuke.command(
        name="channel",
        aliases=["channels", "channel_update"],
        brief="toggle the anti channel update of antinuke",
        example=",antinuke channel true",
        parameters={
            "threshold": {
                "type": int,
                "required": False,
                "brief": "set the threshold until antinuke bans the user",
            }
        },
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_channel_update(self, ctx: Context, state: bool):
        return await self.antinuke_toggle(ctx, "channel_update", state)

    @antinuke.command(
        name="webhooks",
        brief="toggle the anti webhooks of antinuke",
        example=",antinuke webhooks true",
        parameters={
            "threshold": {
                "type": int,
                "required": False,
                "brief": "set the threshold until antinuke bans the user",
            }
        },
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_webhooks(self, ctx: Context, state: bool):
        result = await self.antinuke_toggle(ctx, "webhooks", state)
        
        # Verify the setting was applied correctly
        entry_exists = await self.bot.db.fetchval(
            """SELECT COUNT(*) FROM antinuke WHERE guild_id = $1 AND webhooks = $2""", 
            ctx.guild.id, 
            state
        )
        
        if not entry_exists:
            logger.error(f"Failed to set webhook protection for guild {ctx.guild.id}")
        
        return result

    @antinuke.command(
        name="guild",
        brief="toggle the anti guild_update of antinuke",
        example=",antinuke guild true",
        parameters={
            "threshold": {
                "type": int,
                "required": False,
                "brief": "set the threshold until antinuke bans the user",
            }
        },
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_guild_update(self, ctx: Context, state: bool):
        return await self.antinuke_toggle(ctx, "guild_update", state)

    @antinuke.command(
        name="prune",
        brief="toggle the anti member_prune of antinuke",
        example=",antinuke member_prune true",
        aliases=["member_prune"],
        parameters={
            "threshold": {
                "type": int,
                "required": False,
                "brief": "set the threshold until antinuke bans the user",
            }
        },
    )
    @trusted()
    async def antinuke_member_prune(self, ctx: Context, state: bool):
        return await self.antinuke_toggle(ctx, "member_prune", state)

    @antinuke.command(
        name="kick",
        brief="toggle the anti kick of antinuke",
        example=",antinuke kick true",
        parameters={
            "threshold": {
                "type": int,
                "required": False,
                "brief": "set the threshold until antinuke bans the user",
            }
        },
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_kick(self, ctx: Context, state: bool):
        return await self.antinuke_toggle(ctx, "kick", state)

    @antinuke.command(
        name="ban",
        brief="toggle the anti ban of antinuke",
        example=",antinuke ban true",
        parameters={
            "threshold": {
                "type": int,
                "required": False,
                "brief": "set the threshold until antinuke bans the user",
            }
        },
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_ban(self, ctx: Context, state: bool):
        return await self.antinuke_toggle(ctx, "ban", state)

    async def antinuke_toggle(self, ctx: Context, module: str, state: bool):
        try:
            threshold = int(ctx.parameters.get("threshold", 0))
        except Exception:
            threshold = 0
            
        if module not in self.modules:
            for m in self.modules:
                if str(module).lower() in m.lower():
                    module = m
            if module not in self.modules:
                return await ctx.fail(
                    f"module not a valid feature, please do {ctx.prefix}antinuke modules to view valid modules"
                )
        if not await self.bot.db.fetchrow(
            """SELECT * FROM antinuke WHERE guild_id = $1""", ctx.guild.id
        ):
            return await ctx.fail("antinuke not **setup**")

        # Update the database
        await self.bot.db.execute(
            f"""UPDATE antinuke SET {module} = $1 WHERE guild_id = $2""",
            state,
            ctx.guild.id,
        )
        
        # Update the cache
        if ctx.guild.id in self.guilds:
            self.guilds[ctx.guild.id][module] = state
        else:
            self.guilds[ctx.guild.id] = {module: state}

        # Only update threshold if explicitly provided or changed
        if threshold > 0:
            # Check if threshold entry exists
            has_threshold_entry = await self.bot.db.fetchval(
                """SELECT COUNT(*) FROM antinuke_threshold WHERE guild_id = $1""", 
                ctx.guild.id
            )
            
            if has_threshold_entry:
                # Update existing threshold
                await self.bot.db.execute(
                    f"""UPDATE antinuke_threshold SET {module} = $1 WHERE guild_id = $2""",
                    threshold,
                    ctx.guild.id,
                )
            else:
                # Create new threshold entry only when needed
                await self.bot.db.execute(
                    f"""INSERT INTO antinuke_threshold (guild_id, {module}) VALUES($1, $2)""",
                    ctx.guild.id,
                    threshold,
                )
            
            # Update threshold cache
            if ctx.guild.id in self.thresholds:
                self.thresholds[ctx.guild.id][module] = threshold
            else:
                self.thresholds[ctx.guild.id] = {module: threshold}

        # Refresh cache when dealing with webhooks
        if module == "webhooks":
            await self.make_cache()

        if threshold == 0:
            thres = ""
        else:
            thres = f" with a threshold of `{threshold}`"
        
        if state is True:
            status = "enabled"
        else:
            status = "disabled"
            
        return await ctx.success(f"successfully **{status}** `{module}`{thres}")

    @antinuke.command(
        name="modules",
        aliases=["features", "events"],
        brief="show antinuke modules",
        example=",antinuke modules",
    )
    @bot_has_permissions(administrator=True)
    @trusted()
    async def antinuke_modules(self, ctx: Context):
        return await ctx.send(
            embed=Embed(
                title="antinuke modules",
                color=self.bot.color,
                description=", ".join(m for m in self.modules),
            )
        )

    @command(name="hardban", aliases=["hb"], brief="Hardban a user", example=",hardban @wurri")
    @trusted()
    @has_permissions(ban_members=True)
    async def hardban(self, ctx: Context, user: Union[User, Member]):
        res = await self.bot.db.fetchval(
            """SELECT user_id FROM hardban WHERE guild_id = $1 AND user_id = $2""",
            ctx.guild.id,
            user.id,
        )
        if res:
            confirm = await ctx.confirm("User is already hardbanned. Do you want to unhardban?")
            if confirm:
                await self.bot.db.execute(
                    """DELETE FROM hardban WHERE guild_id = $1 AND user_id = $2""",
                    ctx.guild.id,
                    user.id,
                )
                try:
                    await ctx.guild.unban(Object(id=user.id), reason="User unhardbanned by trusted admin or owner")
                except Exception:
                    pass
                return await ctx.success(f"Successfully **unhardbanned** {user.mention}")
        else:
            await self.bot.db.execute(
                """INSERT INTO hardban (guild_id, user_id) VALUES($1, $2)""",
                ctx.guild.id,
                user.id,
            )
            await ctx.guild.ban(Object(id=user.id), reason="User hardbanned by trusted admin or owner")
            return await ctx.success(f"Successfully **hardbanned** {user.mention}")
        
    
    @Cog.listener("on_member_join")
    async def hardban_listener(self, member: Member):
        res = await self.bot.db.fetchval(
            """SELECT user_id FROM hardban WHERE guild_id = $1 AND user_id = $2""",
            member.guild.id,
            member.id,
        )
        if res:
            with suppress(Exception):
                await member.ban(reason="User hardbanned by trusted admin or owner")

    # Add a method to safely initialize storage attributes on guild objects
    async def initialize_guild_storage(self, guild: Guild):
        try:
            # Create storage dictionary for the guild
            if not hasattr(self, "_object_attributes"):
                self._object_attributes = {}
                
            # Create unique key for the guild
            guild_id = guild.id
            storage_key = f"Guild:{guild_id}"
            
            # Initialize storage for this guild if needed
            if storage_key not in self._object_attributes:
                self._object_attributes[storage_key] = {}
                
            # Ensure deleted_channels storage exists
            if "_deleted_channels" not in self._object_attributes[storage_key]:
                self._object_attributes[storage_key]["_deleted_channels"] = {}
                
            # Ensure deleted_roles storage exists
            if "_deleted_roles" not in self._object_attributes[storage_key]:
                self._object_attributes[storage_key]["_deleted_roles"] = {}
                
            logger.info(f"Successfully initialized storage for guild {guild.name} ({guild.id})")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize guild storage for {guild.id}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # Add method to initialize attributes safely on any object
    def safe_set_attribute(self, obj, attr_name, value):
        try:
            # Check if the object already has a __dict__ attribute
            if not hasattr(obj, "__dict__"):
                # For Discord objects without __dict__, use a special storage dictionary
                if not hasattr(self, "_object_attributes"):
                    self._object_attributes = {}
                
                # Create unique key for the object based on its type and id
                obj_id = getattr(obj, "id", id(obj))
                obj_type = type(obj).__name__
                storage_key = f"{obj_type}:{obj_id}"
                
                # Initialize storage for this object if needed
                if storage_key not in self._object_attributes:
                    self._object_attributes[storage_key] = {}
                
                # Store the attribute in our custom storage
                self._object_attributes[storage_key][attr_name] = value
                return True
            
            # For objects with __dict__, use normal attribute setting
            # Check if attribute is already set
            if hasattr(obj, attr_name):
                # Update existing attribute
                existing_value = getattr(obj, attr_name)
                if isinstance(existing_value, dict) and isinstance(value, dict):
                    # Merge dictionaries if both values are dictionaries
                    existing_value.update(value)
                    return True
                    
            # Otherwise set the attribute directly
            setattr(obj, attr_name, value)
            return True
        except Exception as e:
            logger.error(f"Failed to set attribute {attr_name} on {type(obj).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # Initialize attributes on any discord object
    async def initialize_object_attributes(self, obj, attributes_dict=None):
        try:
            obj_type = type(obj).__name__
            obj_id = getattr(obj, "id", id(obj))
            
            # Default attributes for different object types
            if attributes_dict is None:
                attributes_dict = {}
                
            # For all objects, initialize _before_state if it doesn't exist
            if "_before_state" not in attributes_dict:
                existing_state = self.safe_get_attribute(obj, "_before_state")
                if existing_state is None:
                    attributes_dict["_before_state"] = None
                
            # For members, initialize dangerous roles tracking
            if obj_type == "Member" and not self.safe_get_attribute(obj, "_dangerous_roles"):
                attributes_dict["_dangerous_roles"] = []
                
            # Set all attributes from the dictionary
            success = True
            for attr_name, default_value in attributes_dict.items():
                if not self.safe_get_attribute(obj, attr_name):
                    result = self.safe_set_attribute(obj, attr_name, default_value)
                    if not result:
                        success = False
                        logger.warning(f"Failed to initialize attribute {attr_name} for {obj_type}:{obj_id}")
                    
            logger.debug(f"Initialized attributes for {obj_type}:{obj_id}")
            return success
        except Exception as e:
            logger.error(f"Failed to initialize attributes for {type(obj).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    # Get attributes safely from any object
    def safe_get_attribute(self, obj, attr_name, default=None):
        try:
            # Check if we're using the custom attribute storage
            if not hasattr(obj, "__dict__"):
                # Ensure we have our storage dictionary
                if hasattr(self, "_object_attributes"):
                    # Get the object's unique key
                    obj_id = getattr(obj, "id", id(obj))
                    obj_type = type(obj).__name__
                    storage_key = f"{obj_type}:{obj_id}"
                    
                    # Return from our custom storage if it exists
                    if storage_key in self._object_attributes:
                        return self._object_attributes[storage_key].get(attr_name, default)
                # If not found in custom storage, return default
                return default
            
            # For normal objects, use getattr with default
            return getattr(obj, attr_name, default)
        except Exception as e:
            logger.error(f"Failed to get attribute {attr_name} from {type(obj).__name__}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return default



async def setup(bot):
    return await bot.add_cog(AntiNuke(bot))