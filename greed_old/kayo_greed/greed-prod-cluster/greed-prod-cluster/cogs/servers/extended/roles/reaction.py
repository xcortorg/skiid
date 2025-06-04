from logging import getLogger
from typing import Annotated, Optional, cast
from collections import defaultdict

from asyncpg import UniqueViolationError
from discord import Embed, HTTPException, Forbidden, Message, RawReactionActionEvent, Role
from discord.ext.commands import Cog, group, has_permissions

from tools import CompositeMetaClass, MixinMeta
from tools.client import Context
from tools.conversion import StrictRole
from tools.paginator import Paginator

import asyncio
import time
log = getLogger("greed/roles")

BURST_LIMIT = 4
BURST_WINDOW = 2
DEBOUNCE_DELAY = 2

class ReactionRoles(MixinMeta, metaclass=CompositeMetaClass):
    """
    Allow members to assign roles to themselves.
    """

    @staticmethod
    def redis_key(guild_id: int) -> str:
        """
        Generate a Redis key for storing burst and debounce data for the guild.
        """
        return f"rrreaction_burst:{guild_id}"

    async def handle_burst_and_debounce(self, guild_id):
        """
        Handle burst reaction limits and debounce the guild using Redis.
        """
        redis_key = self.redis_key(guild_id)
        now = time.time()

        burst_count = await self.bot.redis.incr(redis_key)
        if burst_count == 1:
            await self.bot.redis.expire(redis_key, BURST_WINDOW)

        if burst_count > BURST_LIMIT:
            debounce_key = f"rrdebounce:{guild_id}"
            debounce_ttl = await self.bot.redis.ttl(debounce_key)
            
            if debounce_ttl > 0:
                return True
            else:
                await self.bot.redis.setex(debounce_key, DEBOUNCE_DELAY, "1")
                await self.bot.redis.set(redis_key, 0)
                return True

        return False



    @group(aliases=["rr"], invoke_without_command=True, description="manage roles")
    @has_permissions(manage_roles=True)
    async def reactionrole(self, ctx: Context) -> Message:
        """
        Allow members to assign roles to themselves.
        """

        return await ctx.send_help(ctx.command)

    @reactionrole.command(
        name="add",
        aliases=["create"],
        description="manage roles",
        usage="<message> <emoji> <role>",
        brief="https://discord.com/channels/1135484270740246578/1143553248284909568/1251941944385339436 :straight: @Straight",
    )
    @has_permissions(manage_roles=True)
    async def reactionrole_add(
        self,
        ctx: Context,
        message: Message,
        emoji: str,
        *,
        role: Annotated[
            Role,
            StrictRole(check_dangerous=True),
        ],
    ) -> Message:
        """
        Add a new reaction role to a message.
        """

        if message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server")

        try:
            await message.add_reaction(emoji)
        except (HTTPException, TypeError):
            return await ctx.warn(
                "I couldn't add the reaction to the message",
                "If you're using a custom emoji from another server,",
                "you can react with it first and then run this command",
            )

        try:
            await self.bot.db.execute(
                """
                INSERT INTO reaction_role (
                    guild_id,
                    channel_id,
                    message_id,
                    role_id,
                    emoji
                ) VALUES (
                    $1,
                    $2,
                    $3,
                    $4,
                    $5
                )
                """,
                ctx.guild.id,
                message.channel.id,
                message.id,
                role.id,
                emoji,
            )
        except UniqueViolationError:
            return await ctx.warn("That reaction role already exists")

        return await ctx.approve(
            f"Now assigning {role.mention} for **{emoji}** on [`{message.id}`]({message.jump_url})"
        )

    @reactionrole.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        description="manage roles",
        usage="<message> <emoji>",
        brief="https://discord.com/channels/1135484270740246578/1143553248284909568/1251941944385339436 :straight:",
    )
    @has_permissions(manage_roles=True)
    async def reactionrole_remove(
        self,
        ctx: Context,
        message: Message,
        emoji: str,
    ) -> Message:
        """
        Remove a reaction role from a message.
        """

        if message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server")

        result = await self.bot.db.execute(
            """
            DELETE FROM reaction_role
            WHERE guild_id = $1
            AND message_id = $2
            AND emoji = $3
            """,
            ctx.guild.id,
            message.id,
            emoji,
        )
        if result == "DELETE 0":
            return await ctx.warn("That reaction role doesn't exist")

        return await ctx.approve(
            f"No longer assigning a role for **{emoji}** on [`{message.id}`]({message.jump_url})"
        )

    @reactionrole.command(
        name="clear",
        aliases=["clean", "reset"],
        description="manage roles",
        usage="<message>",
        brief="https://discord.com/channels/1135484270740246578/1143553248284909568/1251941944385339436",
    )
    @has_permissions(manage_roles=True)
    async def reactionrole_clear(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Remove all reaction roles.
        """

        if message is None:
            await ctx.prompt(
                "Are you sure you want to remove all reaction roles?",
            )

            result = await self.bot.db.execute(
                """
                DELETE FROM reaction_role
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if result == "DELETE 0":
                return await ctx.warn("No reaction roles exist for this server")

            return await ctx.approve("Successfully removed all reaction roles")

        if message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server")

        result = await self.bot.db.execute(
            """
            DELETE FROM reaction_role
            WHERE guild_id = $1
            AND message_id = $2
            """,
            ctx.guild.id,
            message.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"No reaction roles exist for that [`message`]({message.jump_url})"
            )

        return await ctx.approve(
            f"Successfully removed all reaction roles from [`{message.id}`]({message.jump_url})"
        )

    @reactionrole.command(name="list", aliases=["ls"], description="manage roles")
    @has_permissions(manage_roles=True)
    async def reactionrole_list(self, ctx: Context) -> Message:
        """
        View all reaction roles.
        """

        messages = [
            (
                f"[`{message.id}`]({message.jump_url})"
                f" - {role.mention} for **{record['emoji']}**"
            )
            for record in await self.bot.db.fetch(
                """
                SELECT
                    channel_id,
                    message_id,
                    role_id,
                    emoji
                FROM reaction_role
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(record["channel_id"])) is not None
            and (message := channel.get_partial_message(record["message_id"]))  # type: ignore
            and (role := ctx.guild.get_role(record["role_id"])) is not None
        ]
        if not messages:
            return await ctx.warn("No reaction roles exist for this server")

        paginator = Paginator(
            ctx,
            entries=messages,
            embed=Embed(
                title="Reaction Roles",
            ),
        )
        return await paginator.start()

    @Cog.listener("on_raw_reaction_add")
    async def reactionrole_event(self, payload: RawReactionActionEvent) -> None:
        """
        Assign a role when a reaction is added.
        """
        guild = payload.guild_id and self.bot.get_guild(payload.guild_id)
        member = payload.member or (guild and guild.get_member(payload.user_id))
        if not guild or not member or member.bot:
            return

        role_id = cast(
            Optional[int],
            await self.bot.db.fetchval(
                """
                SELECT role_id
                FROM reaction_role
                WHERE guild_id = $1
                AND message_id = $2
                AND emoji = $3
                """,
                guild.id,
                payload.message_id,
                str(payload.emoji),
            ),
        )
        if (
            role_id is None
            or not guild.me.guild_permissions.manage_roles
            or (role := guild.get_role(role_id)) is None
            or role >= guild.me.top_role
            or role in member.roles
        ):
            return

        debounce_triggered = await self.handle_burst_and_debounce(guild.id)
        if debounce_triggered:
            return

        try:
            await member.add_roles(role, reason="Reaction role")
        except HTTPException:
            pass
        except Forbidden:
            pass

    @Cog.listener("on_raw_reaction_remove")
    async def reactionrole_remove_event(self, payload: RawReactionActionEvent) -> None:
        """
        Remove a role when a reaction is removed.
        """
        guild = payload.guild_id and self.bot.get_guild(payload.guild_id)
        member = guild and guild.get_member(payload.user_id)
        if not guild or not member or member.bot:
            return

        role_id = cast(
            Optional[int],
            await self.bot.db.fetchval(
                """
                SELECT role_id
                FROM reaction_role
                WHERE guild_id = $1
                AND message_id = $2
                AND emoji = $3
                """,
                guild.id,
                payload.message_id,
                str(payload.emoji),
            ),
        )
        if (
            role_id is None
            or not guild.me.guild_permissions.manage_roles
            or (role := guild.get_role(role_id)) is None
            or role >= guild.me.top_role
            or role not in member.roles
        ):
            return

        debounce_triggered = await self.handle_burst_and_debounce(guild.id)
        if debounce_triggered:
            return

        try:
            await member.remove_roles(role, reason="Reaction role")
        except HTTPException:
            pass
        except Forbidden:
            pass