from typing import TYPE_CHECKING, List, Optional, Union

import config
from discord import Guild, Member, Message, Role, User
from discord.abc import GuildChannel

if TYPE_CHECKING:
    from core.Mono import Mono


class Settings:
    _cache = {}
    _self_prefix_cache = {}

    bot: "Mono"
    guild: Guild
    prefix: str
    reskin: bool
    prefixes: List[str]
    reposter_prefix: bool
    reposter_delete: bool
    reposter_embed: bool
    welcome_removal: bool
    booster_role_base_id: Optional[int]
    booster_role_include_ids: List[int]
    lock_role_id: Optional[int]
    lock_ignore_ids: List[int]
    log_ignore_ids: List[int]
    reassign_ignore_ids: List[int]
    reassign_roles: bool
    invoke_kick: Optional[str]
    invoke_ban: Optional[str]
    invoke_unban: Optional[str]
    invoke_timeout: Optional[str]
    invoke_untimeout: Optional[str]
    play_panel: bool
    play_deletion: bool
    safesearch_level: str  # Added safesearch_level

    def __init__(self, bot: "Mono", guild: Guild, record: dict):
        self.bot = bot
        self.guild = guild
        self.prefix = record.get("prefix", config.Mono.prefix)
        self.prefixes = record.get("prefixes", [config.Mono.prefix])
        self.reskin = record.get("reskin", False)
        self.reposter_prefix = record.get("reposter_prefix", True)
        self.reposter_delete = record.get("reposter_delete", False)
        self.reposter_embed = record.get("reposter_embed", True)
        self.welcome_removal = record.get("welcome_removal", False)
        self.booster_role_base_id = record.get("booster_role_base_id")
        self.booster_role_include_ids = record.get("booster_role_include_ids", [])
        self.lock_role_id = record.get("lock_role_id")
        self.lock_ignore_ids = record.get("lock_ignore_ids", [])
        self.log_ignore_ids = record.get("log_ignore_ids", [])
        self.reassign_ignore_ids = record.get("reassign_ignore_ids", [])
        self.reassign_roles = record.get("reassign_roles", False)
        self.invoke_kick = record.get("invoke_kick")
        self.invoke_ban = record.get("invoke_ban")
        self.invoke_unban = record.get("invoke_unban")
        self.invoke_timeout = record.get("invoke_timeout")
        self.invoke_untimeout = record.get("invoke_untimeout")
        self.play_panel = record.get("play_panel", True)
        self.play_deletion = record.get("play_deletion", False)
        self.safesearch_level = record.get(
            "safesearch_level", "strict"
        )  # Initialize safesearch_level

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

    @property
    def lock_role(self) -> Role:
        return self.guild.get_role(self.lock_role_id) or self.guild.default_role

    @property
    def lock_ignore(self) -> List[GuildChannel]:
        return [
            channel
            for channel_id in self.lock_ignore_ids
            if (channel := self.guild.get_channel(channel_id)) is not None
        ]

    @property
    def log_ignore(self) -> List[Union[GuildChannel, Member]]:
        return [
            target
            for target_id in self.log_ignore_ids
            if (target := self.guild.get_channel(target_id))
            or (target := self.guild.get_member(target_id))
        ]

    @property
    def reassign_ignore(self) -> List[Role]:
        return [
            role
            for role_id in self.reassign_ignore_ids
            if (role := self.guild.get_role(role_id)) is not None
        ]

    @classmethod
    async def get_self_prefix(cls, bot: "Mono", user: User) -> Optional[str]:
        if user.id in cls._self_prefix_cache:
            return cls._self_prefix_cache[user.id]

        self_prefix = await bot.db.fetchval(
            """
            SELECT prefix
            FROM selfprefix
            WHERE user_id = $1
            """,
            user.id,
        )

        cls._self_prefix_cache[user.id] = self_prefix
        return self_prefix

    @classmethod
    async def set_self_prefix(cls, bot: "Mono", user: User, prefix: str) -> None:
        await bot.db.execute(
            """
            INSERT INTO selfprefix (user_id, prefix)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET prefix = $2
            """,
            user.id,
            prefix,
        )
        cls._self_prefix_cache[user.id] = prefix

    @classmethod
    async def remove_self_prefix(cls, bot: "Mono", user: User) -> None:
        await bot.db.execute(
            """
            DELETE FROM selfprefix
            WHERE user_id = $1
            """,
            user.id,
        )
        cls._self_prefix_cache.pop(user.id, None)

    @classmethod
    def invalidate_self_prefix_cache(cls, user_id: int):
        cls._self_prefix_cache.pop(user_id, None)

    async def update(self, **kwargs):
        update_fields = {
            "prefix": kwargs.get("prefix", self.prefix),
            "reskin": kwargs.get("reskin", self.reskin),
            "reposter_prefix": kwargs.get("reposter_prefix", self.reposter_prefix),
            "reposter_delete": kwargs.get("reposter_delete", self.reposter_delete),
            "reposter_embed": kwargs.get("reposter_embed", self.reposter_embed),
            "welcome_removal": kwargs.get("welcome_removal", self.welcome_removal),
            "booster_role_base_id": kwargs.get(
                "booster_role_base_id", self.booster_role_base_id
            ),
            "booster_role_include_ids": kwargs.get(
                "booster_role_include_ids", self.booster_role_include_ids
            ),
            "lock_role_id": kwargs.get("lock_role_id", self.lock_role_id),
            "lock_ignore_ids": kwargs.get("lock_ignore_ids", self.lock_ignore_ids),
            "log_ignore_ids": kwargs.get("log_ignore_ids", self.log_ignore_ids),
            "reassign_ignore_ids": kwargs.get(
                "reassign_ignore_ids", self.reassign_ignore_ids
            ),
            "reassign_roles": kwargs.get("reassign_roles", self.reassign_roles),
            "invoke_kick": kwargs.get("invoke_kick", self.invoke_kick),
            "invoke_ban": kwargs.get("invoke_ban", self.invoke_ban),
            "invoke_unban": kwargs.get("invoke_unban", self.invoke_unban),
            "invoke_timeout": kwargs.get("invoke_timeout", self.invoke_timeout),
            "invoke_untimeout": kwargs.get("invoke_untimeout", self.invoke_untimeout),
            "play_panel": kwargs.get("play_panel", self.play_panel),
            "play_deletion": kwargs.get("play_deletion", self.play_deletion),
            "safesearch_level": kwargs.get(
                "safesearch_level", self.safesearch_level
            ),  # Added safesearch_level
        }

        await self.bot.db.execute(
            """
            UPDATE settings
            SET
                prefix = $2,
                reskin = $3,
                reposter_prefix = $4,
                reposter_delete = $5,
                reposter_embed = $6,
                welcome_removal = $7,
                booster_role_base_id = $8,
                booster_role_include_ids = $9,
                lock_role_id = $10,
                lock_ignore_ids = $11,
                log_ignore_ids = $12,
                reassign_ignore_ids = $13,
                reassign_roles = $14,
                invoke_kick = $15,
                invoke_ban = $16,
                invoke_unban = $17,
                invoke_timeout = $18,
                invoke_untimeout = $19,
                play_panel = $20,
                play_deletion = $21,
                safesearch_level = $22  -- Ensure safesearch_level is included here
            WHERE guild_id = $1
            """,
            self.guild.id,
            *update_fields.values(),
        )

        for key, value in update_fields.items():
            setattr(self, key, value)

        # Invalidate the cache for this guild
        Settings.invalidate_cache(self.guild.id)

    @classmethod
    def invalidate_cache(cls, guild_id: int):
        if guild_id in cls._cache:
            del cls._cache[guild_id]

    @classmethod
    async def fetch(cls, bot: "Mono", guild: Optional[Guild]) -> "Settings":
        if guild is None:
            raise ValueError("Guild cannot be None")

        if guild.id in cls._cache:
            return cls._cache[guild.id]

        record = await bot.db.fetchrow(
            """
            INSERT INTO settings (guild_id, prefix, safesearch_level)  -- Ensure safesearch_level is included here
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id)
            DO UPDATE
            SET guild_id = EXCLUDED.guild_id,
                prefix = EXCLUDED.prefix,
                safesearch_level = EXCLUDED.safesearch_level  -- Ensure safesearch_level is included here
            RETURNING *
            """,
            guild.id,
            config.Mono.prefix,
            "strict",  # Default value for safesearch_level
        )

        settings = cls(bot, guild, record)
        cls._cache[guild.id] = settings
        return settings

    @classmethod
    async def get_prefix(cls, bot: "Mono", message: Message) -> str:
        if message.guild:
            settings = await cls.fetch(bot, message.guild)
            guild_prefix = settings.prefix
        else:
            guild_prefix = None

        user_prefix = await cls.get_self_prefix(bot, message.author)

        return user_prefix or guild_prefix or config.Mono.prefix
