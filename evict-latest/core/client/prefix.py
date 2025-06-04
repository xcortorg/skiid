from typing import List, Optional, Tuple, TYPE_CHECKING, Any
from discord import Message

import logging

if TYPE_CHECKING:
    from main import Evict

async def getprefix(bot: Any, message: Message) -> Tuple[str, str]:
    """
    Utility function to get the bot prefix.
    """
    if not message.guild:
        return ";", ";"

    guildprefix = ";"
    selfprefix = ";"

    async with bot.redis.pipeline() as pipe:
        await pipe.get(f"prefix:guild:{message.guild.id}")
        await pipe.get(f"prefix:user:{message.author.id}")
        guild_prefix, user_prefix = await pipe.execute()

    if guild_prefix is not None:
        guildprefix = guild_prefix.decode("utf-8") if isinstance(guild_prefix, bytes) else str(guild_prefix)
    
    if user_prefix is not None:
        selfprefix = user_prefix.decode("utf-8") if isinstance(user_prefix, bytes) else str(user_prefix)

    if guild_prefix is None or user_prefix is None:
        if guild_prefix is None:
            res = await bot.db.fetchrow("SELECT prefix FROM prefix WHERE guild_id = $1", message.guild.id)
            if res:
                    guildprefix = res["prefix"]
                    await bot.redis.set(f"prefix:guild:{message.guild.id}", guildprefix, ex=21600)
                
            if user_prefix is None:
                res = await bot.db.fetchrow("SELECT prefix FROM selfprefix WHERE user_id = $1", message.author.id)
                if res:
                    selfprefix = res["prefix"]
                    await bot.redis.set(f"prefix:user:{message.author.id}", selfprefix, ex=21600)

    if selfprefix == ";" and guildprefix != ";":
        selfprefix = guildprefix

    logging.debug(f"Guild Prefix: {guildprefix}, User Prefix: {selfprefix}")

    return guildprefix, selfprefix


async def update_guild_prefix(bot, guild_id: int, prefix: str) -> None:
    """
    Utility function to update a guild's prefix.
    """
    exists = await bot.db.fetchval(
        """
        SELECT EXISTS(
            SELECT 1 FROM prefix 
            WHERE guild_id = $1
        )
        """,
        guild_id,
    )

    if exists:
        await bot.db.execute(
            """
            UPDATE prefix 
            SET prefix = $1 
            WHERE guild_id = $2
            """,
            prefix,
            guild_id,
        )
    else:
        await bot.db.execute(
            """
            INSERT INTO prefix (guild_id, prefix)
            VALUES ($1, $2)
            """,
            guild_id,
            prefix,
        )

    if prefix:
        await bot.redis.set(f"prefix:guild:{guild_id}", str(prefix), ex=21600)
    else:
        await bot.redis.delete(f"prefix:guild:{guild_id}")


async def update_user_prefix(bot, user_id: int, prefix: Optional[str] = None) -> None:
    """
    Utility function to update a user's prefix.
    """
    if prefix is None:
        await bot.db.execute(
            "DELETE FROM selfprefix WHERE user_id = $1",
            user_id,
        )
        await bot.redis.delete(f"prefix:user:{user_id}")
    else:
        exists = await bot.db.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM selfprefix 
                WHERE user_id = $1
            )
            """,
            user_id,
        )

        if exists:
            await bot.db.execute(
                """
                UPDATE selfprefix 
                SET prefix = $1 
                WHERE user_id = $2
                """,
                prefix,
                user_id,
            )
        else:
            await bot.db.execute(
                """
                INSERT INTO selfprefix (user_id, prefix)
                VALUES ($1, $2)
                """,
                user_id,
                prefix,
            )

        await bot.redis.set(f"prefix:user:{user_id}", str(prefix), ex=21600)
