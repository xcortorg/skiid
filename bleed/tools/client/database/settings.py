from typing import TYPE_CHECKING, Optional

import config
from discord import Guild, Message, User

if TYPE_CHECKING:
    from tools.bleed import Bleed


class Settings:
    _cache = {}
    _self_prefix_cache = {}

    bot: "Bleed"
    guild: Guild
    prefix: str

    def __init__(self, bot: "Bleed", guild: Guild, record: dict):
        self.bot = bot
        self.guild = guild
        self.prefix = record.get("prefix", config.Bleed.prefix)
        self.prefixes = record.get("prefixes", [config.Bleed.prefix])

    @classmethod
    async def get_self_prefix(cls, bot: "Bleed", user: User) -> Optional[str]:
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
    async def set_self_prefix(cls, bot: "Bleed", user: User, prefix: str) -> None:
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
    async def remove_self_prefix(cls, bot: "Bleed", user: User) -> None:
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
            # Additional fields can be added here in the future
        }

        # Invalidate cache before update
        Settings.invalidate_cache(self.guild.id)

        await self.bot.db.execute(
            """
            UPDATE settings
            SET prefix = $2
            WHERE guild_id = $1
            """,
            self.guild.id,
            update_fields["prefix"],
        )

        for key, value in update_fields.items():
            setattr(self, key, value)

    @classmethod
    def invalidate_cache(cls, guild_id: int):
        if guild_id in cls._cache:
            del cls._cache[guild_id]

    @classmethod
    async def fetch(cls, bot: "Bleed", guild: Optional[Guild]) -> "Settings":
        if guild is None:
            raise ValueError("Guild cannot be None")

        if guild.id in cls._cache:
            return cls._cache[guild.id]

        record = await bot.db.fetchrow(
            """
            INSERT INTO settings (guild_id, prefix)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) 
            DO UPDATE 
            SET prefix = EXCLUDED.prefix
            RETURNING *
            """,
            guild.id,
            config.Bleed.prefix,
        )

        settings = cls(bot, guild, record)
        cls._cache[guild.id] = settings
        return settings

    @classmethod
    async def get_prefix(cls, bot: "Bleed", message: Message) -> str:
        if message.guild:
            settings = await cls.fetch(bot, message.guild)
            guild_prefix = settings.prefix
        else:
            guild_prefix = None

        user_prefix = await cls.get_self_prefix(bot, message.author)

        return user_prefix or guild_prefix or config.Bleed.prefix

    @classmethod
    async def create_or_update(
        cls, bot: "Bleed", guild: Guild, prefix: str
    ) -> "Settings":
        """Create or update a guild's settings"""
        record = await bot.db.fetchrow(
            """
            INSERT INTO settings (guild_id, prefix)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE 
            SET prefix = $2
            RETURNING *
            """,
            guild.id,
            prefix,
        )

        cls.invalidate_cache(guild.id)
        settings = cls(bot, guild, record)
        cls._cache[guild.id] = settings
        return settings
