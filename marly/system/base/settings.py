from typing import TYPE_CHECKING, Optional, Dict, List
from discord import Guild, Member, Role
from discord.abc import GuildChannel
import config
from discord.utils import cached_property

if TYPE_CHECKING:
    from system import Marly


class Settings:
    bot: "Marly"
    guild: Guild
    prefix: str
    mod_log: Optional[int]
    jail_role: Optional[int]
    jail_channel: Optional[int]
    nuke_view: Optional[str]
    ban_delete_days: Optional[int]
    booster_role_base_id: Optional[int]
    booster_role_include_ids: List[int]
    lock_role_id: Optional[int]
    lock_ignore_ids: List[int]
    log_ignore_ids: List[int]
    image_mute_role_id: List[int]
    mute_role: Optional[int]
    reaction_mute_role: Optional[int]
    welcome_removal: bool
    # Channel invoke messages
    invoke_kick_message: Optional[str]
    invoke_ban_message: Optional[str]
    invoke_unban_message: Optional[str]
    invoke_timeout_message: Optional[str]
    invoke_untimeout_message: Optional[str]
    invoke_mute_message: Optional[str]
    invoke_unmute_message: Optional[str]
    invoke_softban_message: Optional[str]
    invoke_warn_message: Optional[str]
    invoke_tempban_message: Optional[str]
    invoke_hardban_message: Optional[str]
    invoke_jail_message: Optional[str]
    invoke_unjail_message: Optional[str]
    invoke_imute_message: Optional[str]
    invoke_iunmute_message: Optional[str]
    invoke_rmute_message: Optional[str]
    invoke_runmute_message: Optional[str]
    # DM invoke messages
    invoke_kick_dm: Optional[str]
    invoke_ban_dm: Optional[str]
    invoke_unban_dm: Optional[str]
    invoke_timeout_dm: Optional[str]
    invoke_untimeout_dm: Optional[str]
    invoke_mute_dm: Optional[str]
    invoke_unmute_dm: Optional[str]
    invoke_softban_dm: Optional[str]
    invoke_warn_dm: Optional[str]
    invoke_tempban_dm: Optional[str]
    invoke_hardban_dm: Optional[str]
    invoke_jail_dm: Optional[str]
    invoke_unjail_dm: Optional[str]
    invoke_imute_dm: Optional[str]
    invoke_iunmute_dm: Optional[str]
    invoke_rmute_dm: Optional[str]
    invoke_runmute_dm: Optional[str]
    invoke: Dict[str, str]
    invoke_silent_mode: bool

    def __init__(self, bot: "Marly", guild: Guild, record: dict):
        self.bot = bot
        self.guild = guild
        self.prefix = record.get("prefix", config.Marly.PREFIX)
        self.mod_log = record.get("mod_log")
        self.jail_role = record.get("jail_role")
        self.jail_channel = record.get("jail_channel")
        self.nuke_view = record.get("nuke_view")
        self.ban_delete_days = record.get("ban_delete_days", 0)
        self.booster_role_base_id = record.get("booster_role_base_id")
        self.booster_role_include_ids = record.get("booster_role_include_ids", [])
        self.lock_role_id = record.get("lock_role_id")
        self.lock_ignore_ids = record.get("lock_ignore_ids", [])
        self.log_ignore_ids = record.get("log_ignore_ids", [])
        self.image_mute_role_id = record.get("image_mute_role_id", [])
        self.mute_role = record.get("mute_role")
        self.reaction_mute_role = record.get("reaction_mute_role")
        self.welcome_removal = record.get("welcome_removal", False)
        # Channel invoke messages
        self.invoke_kick_message = record.get("invoke_kick_message")
        self.invoke_ban_message = record.get("invoke_ban_message")
        self.invoke_unban_message = record.get("invoke_unban_message")
        self.invoke_timeout_message = record.get("invoke_timeout_message")
        self.invoke_untimeout_message = record.get("invoke_untimeout_message")
        self.invoke_mute_message = record.get("invoke_mute_message")
        self.invoke_unmute_message = record.get("invoke_unmute_message")
        self.invoke_softban_message = record.get("invoke_softban_message")
        self.invoke_warn_message = record.get("invoke_warn_message")
        self.invoke_tempban_message = record.get("invoke_tempban_message")
        self.invoke_hardban_message = record.get("invoke_hardban_message")
        self.invoke_jail_message = record.get("invoke_jail_message")
        self.invoke_unjail_message = record.get("invoke_unjail_message")
        self.invoke_imute_message = record.get("invoke_imute_message")
        self.invoke_iunmute_message = record.get("invoke_iunmute_message")
        self.invoke_rmute_message = record.get("invoke_rmute_message")
        self.invoke_runmute_message = record.get("invoke_runmute_message")
        # DM invoke messages
        self.invoke_kick_dm = record.get("invoke_kick_dm")
        self.invoke_ban_dm = record.get("invoke_ban_dm")
        self.invoke_unban_dm = record.get("invoke_unban_dm")
        self.invoke_timeout_dm = record.get("invoke_timeout_dm")
        self.invoke_untimeout_dm = record.get("invoke_untimeout_dm")
        self.invoke_mute_dm = record.get("invoke_mute_dm")
        self.invoke_unmute_dm = record.get("invoke_unmute_dm")
        self.invoke_softban_dm = record.get("invoke_softban_dm")
        self.invoke_warn_dm = record.get("invoke_warn_dm")
        self.invoke_tempban_dm = record.get("invoke_tempban_dm")
        self.invoke_hardban_dm = record.get("invoke_hardban_dm")
        self.invoke_jail_dm = record.get("invoke_jail_dm")
        self.invoke_unjail_dm = record.get("invoke_unjail_dm")
        self.invoke_imute_dm = record.get("invoke_imute_dm")
        self.invoke_iunmute_dm = record.get("invoke_iunmute_dm")
        self.invoke_rmute_dm = record.get("invoke_rmute_dm")
        self.invoke_runmute_dm = record.get("invoke_runmute_dm")
        self.invoke = record.get("invoke", {})
        self.invoke_silent_mode = record.get("invoke_silent_mode", False)

    def _to_dict(self) -> dict:
        """Convert settings to a dictionary for caching"""
        return {
            "prefix": self.prefix,
            "mod_log": self.mod_log,
            "jail_role": self.jail_role,
            "jail_channel": self.jail_channel,
            "nuke_view": self.nuke_view,
            "ban_delete_days": self.ban_delete_days,
            "booster_role_base_id": self.booster_role_base_id,
            "booster_role_include_ids": self.booster_role_include_ids,
            "lock_role_id": self.lock_role_id,
            "lock_ignore_ids": self.lock_ignore_ids,
            "log_ignore_ids": self.log_ignore_ids,
            "image_mute_role_id": self.image_mute_role_id,
            "mute_role": self.mute_role,
            "reaction_mute_role": self.reaction_mute_role,
            "welcome_removal": self.welcome_removal,
            "invoke_kick_message": self.invoke_kick_message,
            "invoke_ban_message": self.invoke_ban_message,
            "invoke_unban_message": self.invoke_unban_message,
            "invoke_timeout_message": self.invoke_timeout_message,
            "invoke_untimeout_message": self.invoke_untimeout_message,
            "invoke_mute_message": self.invoke_mute_message,
            "invoke_unmute_message": self.invoke_unmute_message,
            "invoke_softban_message": self.invoke_softban_message,
            "invoke_warn_message": self.invoke_warn_message,
            "invoke_tempban_message": self.invoke_tempban_message,
            "invoke_hardban_message": self.invoke_hardban_message,
            "invoke_jail_message": self.invoke_jail_message,
            "invoke_unjail_message": self.invoke_unjail_message,
            "invoke_imute_message": self.invoke_imute_message,
            "invoke_iunmute_message": self.invoke_iunmute_message,
            "invoke_rmute_message": self.invoke_rmute_message,
            "invoke_runmute_message": self.invoke_runmute_message,
            "invoke_kick_dm": self.invoke_kick_dm,
            "invoke_ban_dm": self.invoke_ban_dm,
            "invoke_unban_dm": self.invoke_unban_dm,
            "invoke_timeout_dm": self.invoke_timeout_dm,
            "invoke_untimeout_dm": self.invoke_untimeout_dm,
            "invoke_mute_dm": self.invoke_mute_dm,
            "invoke_unmute_dm": self.invoke_unmute_dm,
            "invoke_softban_dm": self.invoke_softban_dm,
            "invoke_warn_dm": self.invoke_warn_dm,
            "invoke_tempban_dm": self.invoke_tempban_dm,
            "invoke_hardban_dm": self.invoke_hardban_dm,
            "invoke_jail_dm": self.invoke_jail_dm,
            "invoke_unjail_dm": self.invoke_unjail_dm,
            "invoke_imute_dm": self.invoke_imute_dm,
            "invoke_iunmute_dm": self.invoke_iunmute_dm,
            "invoke_rmute_dm": self.invoke_rmute_dm,
            "invoke_runmute_dm": self.invoke_runmute_dm,
            "invoke": self.invoke,
            "invoke_silent_mode": self.invoke_silent_mode,
        }

    async def _cache_settings(self, ex: int = 300):
        """Cache the current settings in Redis"""
        cache_key = f"settings:{self.guild.id}"
        await self.bot.redis.set(cache_key, self._to_dict(), ex=ex)

    async def invalidate_cache(self):
        """Manually invalidate the settings cache for this guild"""
        cache_key = f"settings:{self.guild.id}"
        await self.bot.redis.delete(cache_key)

    async def update(self, **kwargs):
        # Build the SQL query dynamically using annotations
        fields = [f for f in self.__annotations__ if f not in ("bot", "guild")]
        placeholders = [f"{field} = ${i+2}" for i, field in enumerate(fields)]
        query = f"""
            UPDATE settings
            SET {', '.join(placeholders)}
            WHERE guild_id = $1
        """

        # Build values list in the same order as placeholders
        values = [self.guild.id]
        for field in fields:
            values.append(kwargs.get(field, getattr(self, field)))

        await self.bot.db.execute(query, *values)

        # Update instance attributes
        for key, value in kwargs.items():
            setattr(self, key, value)

        # Update cache
        await self._cache_settings()

    @classmethod
    async def fetch(cls, bot: "Marly", guild: Guild) -> "Settings":
        # Try to get from cache first
        cache_key = f"settings:{guild.id}"
        cached_data = await bot.redis.get(cache_key)

        if cached_data:
            return cls(bot, guild, cached_data)

        # If not in cache, fetch from database
        record = await bot.db.fetchrow(
            """
            INSERT INTO settings (guild_id)
            VALUES ($1)
            ON CONFLICT (guild_id)
            DO UPDATE
            SET guild_id = EXCLUDED.guild_id
            RETURNING *
            """,
            guild.id,
        )

        # Create instance and cache it
        instance = cls(bot, guild, record)
        await instance._cache_settings()
        return instance

    async def fetch_user_prefix(self, user_id: int) -> Optional[str]:
        cache_key = f"selfprefix:{user_id}"
        cached_prefix = await self.bot.redis.get(cache_key)

        if cached_prefix:
            return cached_prefix

        record = await self.bot.db.fetchrow(
            """
            SELECT prefix
            FROM selfprefix
            WHERE user_id = $1
            """,
            user_id,
        )

        if record:
            await self.bot.redis.set(cache_key, record["prefix"], ex=300)
            return record["prefix"]
        return None

    async def update_user_prefix(self, user_id: int, prefix: str):
        await self.bot.db.execute(
            """
            INSERT INTO selfprefix (user_id, prefix)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET prefix = EXCLUDED.prefix
            """,
            user_id,
            prefix,
        )

        # Update cache
        cache_key = f"selfprefix:{user_id}"
        await self.bot.redis.set(cache_key, prefix, ex=300)

    async def remove_self_prefix(self, user_id: int):
        await self.bot.db.execute(
            """
            DELETE FROM selfprefix
            WHERE user_id = $1
            """,
            user_id,
        )

        # Remove from cache
        cache_key = f"selfprefix:{user_id}"
        await self.bot.redis.delete(cache_key)

    @property
    def lock_role(self) -> Role:
        return self.guild.get_role(self.lock_role_id) or self.guild.default_role

    @property
    def image_mute_role(self) -> List[Role]:
        return [
            role
            for role_id in self.image_mute_role_id
            if (role := self.guild.get_role(role_id)) is not None
        ]

    @property
    def lock_ignore(self) -> List[GuildChannel]:
        return [
            channel
            for channel_id in self.lock_ignore_ids
            if (channel := self.guild.get_channel(channel_id)) is not None
        ]

    @property
    def booster_role_base(self) -> Optional[Role]:
        if not self.booster_role_base_id:
            return None
        return self.guild.get_role(self.booster_role_base_id)

    @property
    def booster_role_include(self) -> List[Role]:
        return [
            role
            for role_id in self.booster_role_include_ids
            if (role := self.guild.get_role(role_id)) is not None
        ]
