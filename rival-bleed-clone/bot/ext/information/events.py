from discord.ext.commands import (
    Cog,
    Context,
    command,
    group,
    CommandError,
    has_permissions,
)
from discord.ext import tasks
from discord import Client, Embed, File, Member, User, Guild
from typing import Callable, Any, List, Tuple
import datetime
import asyncio
from loguru import logger


async def daily_task(
    coroutines: List[Tuple[Callable[..., Any], Tuple[Any, ...], dict]]
) -> None:
    while True:
        now = datetime.datetime.now()
        # Calculate the time until midnight
        midnight = datetime.datetime.combine(
            now.date() + datetime.timedelta(days=1), datetime.time(0, 0)
        )
        wait_time = (midnight - now).total_seconds()

        # Wait until midnight
        await asyncio.sleep(wait_time)

        # Execute each provided coroutine with its arguments
        for coroutine, args, kwargs in coroutines:
            await coroutine(*args, **kwargs)
            logger.info(f"Executed daily task for {coroutine.__name__} at midnight.")


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self.task: asyncio.Task = None

    async def cog_load(self) -> None:
        self.task = self.bot.loop.create_task(
            daily_task(
                [
                    self.daily_task,
                    self.bot,
                ]
            )
        )

    async def cog_unload(self) -> None:
        if self.task:
            self.task.cancel()

    async def daily_task(self):
        await self.bot.db.execute("""DELETE FROM statistics.member_count""")

    @Cog.listener("on_member_remove")
    async def decrement_joins(self, member: Member):
        await self.bot.db.execute(
            """
                INSERT INTO statistics.member_count (guild_id, joins) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET joins = joins - 1
            """,
            member.guild.id,
            -1,
        )

    @Cog.listener("on_member_join")
    async def increment_joins(self, member: Member):
        await self.bot.db.execute(
            """
                INSERT INTO statistics.member_count (guild_id, joins) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET joins = member_activity.joins + 1;
            """,
            member.guild.id,
            1,
        )

    @Cog.listener("on_member_unboost")
    async def store_boost(self, member: Member) -> None:
        await self.bot.db.execute(
            """
            INSERT INTO boosters_lost (
                guild_id,
                user_id,
                started_at
            ) VALUES($1, $2, $3)
            ON CONFLICT (guild_id, user_id)
            DO UPDATE SET
                started_at = EXCLUDED.started_at,
                expired_at = NOW()
            """,
            member.guild.id,
            member.id,
            member.premium_since,
        )
