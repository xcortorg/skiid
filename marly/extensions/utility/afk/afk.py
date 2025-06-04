from typing import Optional

from discord import Message
from discord.ext.commands import Cog, command
from discord.utils import format_dt, utcnow

from system.tools.metaclass import CompositeMetaClass, MixinMeta
from system.tools import shorten
from system.base.context import Context


class afk(MixinMeta, metaclass=CompositeMetaClass):
    @Cog.listener("on_message")
    async def afk_listener(self, message: Message) -> Optional[Message]:
        if message.author.bot:
            return

        ctx = await self.bot.get_context(message)

        # Check if the message author was AFK
        left_at = await self.bot.db.fetchval(
            """
            SELECT left_at
            FROM afk
            WHERE user_id = $1
            """,
            message.author.id,
        )

        if left_at:
            await self.bot.db.execute(
                """
                DELETE FROM afk
                WHERE user_id = $1
                """,
                message.author.id,
            )
            await ctx.neutral(
                f"Welcome back You were away {format_dt(left_at, 'R')}",
                reference=message,
                emoji="👋",
            )
            return

        for mention in message.mentions:
            record = await self.bot.db.fetchrow(
                """
                SELECT status, left_at
                FROM afk
                WHERE user_id = $1
                """,
                mention.id,
            )
            if record:
                await ctx.neutral(
                    f"{mention.mention} is currently AFK: **{record['status']}** - {format_dt(record['left_at'], 'R')}",
                    reference=message,
                )

    @command(aliases=["away"])
    async def afk(
        self,
        ctx: Context,
        *,
        status: str = "AFK",
    ) -> Optional[Message]:
        """
        Set an AFK status.
        """

        status = shorten(status, 200)
        await self.bot.db.execute(
            """
            INSERT INTO afk (user_id, status, left_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id) DO UPDATE
            SET status = EXCLUDED.status, left_at = EXCLUDED.left_at
            """,
            ctx.author.id,
            status,
            utcnow(),
        )
        return await ctx.approve(f"You're now **AFK** with the status **`{status}`**")
