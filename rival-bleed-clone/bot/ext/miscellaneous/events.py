from discord.ext.commands import (
    Cog,
    Context,
    command,
    group,
    CommandError,
    has_permissions,
)
from datetime import datetime
from discord import Client, Embed, File, Member, User, Guild, Message
from loguru import logger as logger_
from logging import getLogger
from typing import Union
from lib.classes.processing import human_timedelta
from lib.classes.checks import event_checks
import traceback

logger = getLogger(__name__) and logger_


def get_tbb(error: Exception) -> str:
    return "".join(traceback.format_exception(type(error), error, error.__traceback__))


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot

    async def namehistory_event(
        self: "Events", before: Union[Member, User], after: Union[Member, User]
    ):
        if before.name != after.name:
            name = before.name
            nt = "username"
        elif before.global_name != after.global_name:
            name = before.global_name
            nt = "globalname"
        elif before.display_name != after.display_name:
            name = before.display_name
            nt = "display"
        else:
            if not isinstance(before, Member):
                return
            else:
                try:
                    b_n = str(before.nick) or ""
                except Exception:
                    b_n = ""
                try:
                    a_n = str(after.nick) or ""
                except Exception:
                    a_n = ""
                if b_n != a_n:
                    if b_n == "":
                        return
                    name = b_n
                    nt = "nickname"
                else:
                    return
        if name is None:
            return
        await self.bot.db.execute(
            """INSERT INTO names (user_id, type, username, ts) VALUES($1, $2, $3, $4) ON CONFLICT(user_id, username, type, ts) DO NOTHING""",
            before.id,
            nt,
            name,
            datetime.now(),
        )

    @Cog.listener("on_user_update")
    async def on_username_change(self: "Events", before: User, after: User):
        if before.bot:
            return
        try:
            return await self.namehistory_event(before, after)
        except Exception as e:
            logger.info(get_tbb(e))

    @Cog.listener("on_member_update")
    async def on_member_nickname_change(self: "Events", before: Member, after: Member):
        if after.bot:
            return
        try:
            return await self.namehistory_event(before, after)
        except Exception as e:
            logger.info(get_tbb(e))

    @Cog.listener()
    async def on_guild_update(self: "Events", before: Guild, after: Guild):
        if before.name == after.name:
            return
        await self.bot.db.execute(
            """INSERT INTO guild_names (guild_id, name, ts) VALUES($1, $2, $3) ON CONFLICT(guild_id, name, ts) DO NOTHING""",
            before.id,
            before.name,
            datetime.now(),
        )

    @event_checks
    @Cog.listener("on_afk_check")
    async def on_afk_check(self, ctx: Context) -> None:
        try:
            return await self.do_afk_check(ctx)
        except Exception as e:
            return await self.bot.errors.handle_exceptions(ctx, e)

    async def do_afk_check(self, ctx: Context):
        message = ctx.message
        if ctx.command:
            return
        elif author_afk_since := await self.bot.db.fetchval(
            """
            DELETE FROM afk
            WHERE user_id = $1
            RETURNING date
            """,
            message.author.id,
            cached=False,
        ):
            await ctx.normal(
                f"Welcome back, you were away for **{human_timedelta(author_afk_since, suffix=False)}**",
                emoji="👋",
                reference=message,
            )

        elif len(message.mentions) == 1 and (user := message.mentions[0]):
            if user_afk := await self.bot.db.fetchrow(
                """
                SELECT status, date FROM afk
                WHERE user_id = $1
                """,
                user.id,
                cached=False,
            ):
                await ctx.normal(
                    f"{user.mention} is AFK: **{user_afk['status']}** - {human_timedelta(user_afk['date'], suffix=False)}",
                    emoji="💤",
                    reference=message,
                )
