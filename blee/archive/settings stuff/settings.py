from typing import TYPE_CHECKING, Any, Dict, List, Optional

import config
from discord import Guild, Message, TextChannel, Thread, User

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

    # Welcome Messages Methods
    async def get_welcome_messages(self) -> List[Dict[str, Any]]:
        """Get all welcome messages for the guild"""
        return await self.bot.db.fetch(
            """
            SELECT channel_id, message, self_destruct 
            FROM join_messages
            WHERE guild_id = $1
            """,
            self.guild.id,
        )

    async def get_welcome_message(
        self, channel: TextChannel | Thread
    ) -> Optional[Dict[str, Any]]:
        """Get welcome message for a specific channel"""
        return await self.bot.db.fetchrow(
            """
            SELECT message, self_destruct
            FROM join_messages
            WHERE guild_id = $1 AND channel_id = $2
            """,
            self.guild.id,
            channel.id,
        )

    async def add_welcome_message(
        self, channel: TextChannel | Thread, message: str, self_destruct: int = None
    ) -> None:
        """Add a welcome message for a channel"""
        await self.bot.db.execute(
            """
            INSERT INTO join_messages (guild_id, channel_id, message, self_destruct)
            VALUES ($1, $2, $3, $4)
            """,
            self.guild.id,
            channel.id,
            message,
            self_destruct,
        )

    async def remove_welcome_message(self, channel: TextChannel | Thread) -> bool:
        """Remove a welcome message for a channel. Returns True if message was removed."""
        result = await self.bot.db.execute(
            """
            DELETE FROM join_messages 
            WHERE guild_id = $1 AND channel_id = $2
            """,
            self.guild.id,
            channel.id,
        )
        return result != "DELETE 0"

    async def reset_welcome_messages(self) -> None:
        """Remove all welcome messages for the guild"""
        await self.bot.db.execute(
            """
            DELETE FROM join_messages
            WHERE guild_id = $1
            """,
            self.guild.id,
        )

    # Sticky Messages Methods
    async def get_sticky_messages(self) -> List[Dict[str, Any]]:
        """Get all sticky messages for the guild"""
        return await self.bot.db.fetch(
            """
            SELECT channel_id, message_id, message, schedule
            FROM sticky_messages
            WHERE guild_id = $1
            """,
            self.guild.id,
        )

    async def get_sticky_message(
        self, channel: TextChannel | Thread
    ) -> Optional[Dict[str, Any]]:
        """Get sticky message for a specific channel"""
        return await self.bot.db.fetchrow(
            """
            SELECT message_id, message, schedule
            FROM sticky_messages
            WHERE guild_id = $1 AND channel_id = $2
            """,
            self.guild.id,
            channel.id,
        )

    async def add_sticky_message(
        self,
        channel: TextChannel | Thread,
        message: str,
        message_id: int,
        schedule: int = None,
    ) -> None:
        """Add a sticky message for a channel"""
        await self.bot.db.execute(
            """
            INSERT INTO sticky_messages (guild_id, channel_id, message_id, message, schedule)
            VALUES ($1, $2, $3, $4, $5)
            """,
            self.guild.id,
            channel.id,
            message_id,
            message,
            schedule,
        )

    async def update_sticky_message_id(
        self, channel: TextChannel | Thread, new_message_id: int
    ) -> None:
        """Update the message ID for a sticky message"""
        await self.bot.db.execute(
            """
            UPDATE sticky_messages
            SET message_id = $3
            WHERE guild_id = $1 AND channel_id = $2
            """,
            self.guild.id,
            channel.id,
            new_message_id,
        )

    async def remove_sticky_message(self, channel: TextChannel | Thread) -> bool:
        """Remove a sticky message for a channel. Returns True if message was removed."""
        result = await self.bot.db.execute(
            """
            DELETE FROM sticky_messages
            WHERE guild_id = $1 AND channel_id = $2
            """,
            self.guild.id,
            channel.id,
        )
        return result != "DELETE 0"

    async def reset_sticky_messages(self) -> None:
        """Remove all sticky messages for the guild"""
        await self.bot.db.execute(
            """
            DELETE FROM sticky_messages
            WHERE guild_id = $1
            """,
            self.guild.id,
        )
