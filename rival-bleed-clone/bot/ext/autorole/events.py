from discord.ext.commands import (
    Cog,
)
from discord import (
    Client,
    RawReactionActionEvent,
    Member,
)
from collections import defaultdict
from asyncio import sleep, Lock


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self.locks = defaultdict(Lock)

    @Cog.listener("on_member_agree")
    async def on_autorole(self, member: Member) -> None:
        if (
            await self.bot.object_cache.ratelimited(
                f"member_joins:{member.guild.id}", 1, 5
            )
            != 0
        ):
            await sleep(5)
        if member.bot:
            return
        async with self.locks[f"member_joins:{member.guild.id}"]:
            if not (
                roles := await self.bot.db.fetch(
                    """SELECT role_id FROM auto_role WHERE guild_id = $1""",
                    member.guild.id,
                )
            ):
                return
            to_delete = []
            role_ids = [r.role_id for r in roles]
            valid_roles = member.roles
            for role_id in role_ids:
                if not (role := member.guild.get_role(role_id)):
                    to_delete.append(role_id)
                    continue
                if role.is_dangerous:
                    continue
                valid_roles.append(role)
            await member.edit(roles=valid_roles, reason="Auto Role")
            await self.bot.db.execute(
                """DELETE FROM auto_role WHERE guild_id = $1 AND role_id = ANY($2::BIGINT[])""",
                member.guild.id,
                to_delete,
            )

    @Cog.listener("on_raw_reaction_add")
    async def on_reaction_role_assign(self, payload: RawReactionActionEvent):
        if not (guild := self.bot.get_guild(payload.guild_id)):
            return
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM reaction_role WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4""",
                guild.id,
                payload.channel_id,
                payload.message_id,
                str(payload.emoji),
            )
        ):
            return
        if not (role := guild.get_role(role_id)):
            return
        if not (member := guild.get_member(payload.user_id)):
            return
        if member.bot:
            return
        if (
            await self.bot.object_cache.ratelimited(
                f"reaction_roles:{member.guild.id}", 1, 5
            )
            != 0
        ):
            await sleep(5)
        async with self.locks[f"reaction_roles:{member.guild.id}"]:
            await member.add_roles(role, reason="Reaction Role")

    @Cog.listener("on_raw_reaction_remove")
    async def on_reaction_role_remove(self, payload: RawReactionActionEvent):
        if not (guild := self.bot.get_guild(payload.guild_id)):
            return
        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT role_id FROM reaction_role WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4""",
                guild.id,
                payload.channel_id,
                payload.message_id,
                str(payload.emoji),
            )
        ):
            return
        if not (role := guild.get_role(role_id)):
            return
        if not (member := guild.get_member(payload.user_id)):
            return
        if member.bot:
            return
        if (
            await self.bot.object_cache.ratelimited(
                f"reaction_roles:{member.guild.id}", 1, 5
            )
            != 0
        ):
            await sleep(5)
        async with self.locks[f"reaction_roles:{member.guild.id}"]:
            await member.remove_roles(role, reason="Reaction Role")
