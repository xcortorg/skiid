from functools import wraps
from typing import Optional

from core.client.context import Context
from core.tools import CompositeMetaClass, Duration, MixinMeta
from core.tools.logging import logger as log
from discord import Embed, Member
from discord.abc import GuildChannel
from discord.ext import tasks
from discord.ext.commands import (CheckFailure, Cog, command, group,
                                  has_permissions)
from discord.utils import get, utcnow
from humanize import naturaldelta


class Jail(MixinMeta, metaclass=CompositeMetaClass):
    """
    Jail members for a specified duration.
    """

    def mod_setup_check():
        def decorator(func):
            @wraps(func)
            async def wrapper(self, ctx: Context, *args, **kwargs):
                try:
                    await self.jail_check(ctx)
                except CheckFailure as e:
                    return await ctx.warn(str(e))
                return await func(self, ctx, *args, **kwargs)

            return wrapper

        return decorator

    async def cog_load(self) -> None:
        await super().cog_load()
        self.check_jail_expirations.start()

    @tasks.loop(minutes=1)
    async def check_jail_expirations(self):
        current_time = utcnow()
        expired_jails = await self.bot.db.fetch(
            """
            SELECT user_id, guild_id
            FROM jail
            WHERE is_active = TRUE AND end_time <= $1
            """,
            current_time,
        )

        for record in expired_jails:
            await self.unjail_member(record["guild_id"], record["user_id"])

    async def jail_check(self, ctx: Context):
        """Check if the moderation setup has been completed."""
        setup = await self.bot.db.fetchrow(
            """
            SELECT jail_channel_id, mod_log_channel_id, jail_role_id
            FROM settings 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if not setup or not (
            setup["jail_channel_id"]
            and setup["mod_log_channel_id"]
            and setup["jail_role_id"]
        ):
            raise CheckFailure(
                "**Moderation** setup is **missing.** Please run the `setup` command again."
            )

        # Additional checks to ensure channels and roles still exist
        guild = ctx.guild
        jail_channel = guild.get_channel(setup["jail_channel_id"])
        mod_log_channel = guild.get_channel(setup["mod_log_channel_id"])
        jail_role = guild.get_role(setup["jail_role_id"])

        if not jail_channel or not mod_log_channel or not jail_role:
            raise CheckFailure(
                "**Moderation** setup is incomplete. Please run the `setup` command again."
            )

        return True

    @command(name="jail")
    @has_permissions(manage_channels=True)
    async def jail(
        self,
        ctx: Context,
        member: Optional[Member] = None,
        duration: Optional[Duration] = None,
        *,
        reason: str = "No reason provided",
    ):
        from extensions.mod.moderation import \
            Action  # Import here to avoid circular import

        """
        Jail a member for a specified duration.
        """
        try:
            await self.jail_check(ctx)
        except CheckFailure:
            return await ctx.warn(
                "**Jail** isn't **set up** in this server. Run `setup` command to set it up."
            )

        if member is None:
            return await ctx.send_help(ctx.command)

        if member.top_role >= ctx.author.top_role:
            return await ctx.warn("You cannot jail this member due to role hierarchy.")

        end_time = utcnow() + duration if duration else None

        current_roles = [
            role.id for role in member.roles if role != ctx.guild.default_role
        ]

        await self.bot.db.execute(
            """
            INSERT INTO jail (user_id, guild_id, moderator_id, reason, end_time, previous_roles)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (user_id, guild_id) DO UPDATE
            SET moderator_id = $3, reason = $4, end_time = $5, is_active = TRUE, previous_roles = $6
            """,
            member.id,
            ctx.guild.id,
            ctx.author.id,
            reason,
            end_time,
            current_roles,
        )

        # Remove all roles and assign the jail role
        jail_role = get(ctx.guild.roles, name="Jailed")
        if not jail_role:
            jail_role = await ctx.guild.create_role(
                name="Jailed", reason="Jail role for moderation"
            )

        await member.remove_roles(*member.roles[1:], reason="Member jailed")
        await member.add_roles(jail_role, reason="Member jailed")

        # Retrieve the jail channel and send a message
        setup = await self.bot.db.fetchrow(
            """
            SELECT jail_channel_id FROM settings WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if setup and setup["jail_channel_id"]:
            jail_channel = ctx.guild.get_channel(setup["jail_channel_id"])
            if jail_channel:
                await jail_channel.send(
                    f"{member.mention}, you have been jailed! Wait for a staff member to unjail you and check direct messages if you have received one!"
                )

        # Create a case entry
        case = await self.bot.get_cog("Moderation").insert_case(
            ctx=ctx,
            target=member,
            reason=reason,
            action=Action.JAIL,
            action_expiration=end_time,
        )

        duration_str = f" for {naturaldelta(duration)}" if duration else ""
        await ctx.approve(
            f"{member.mention} has been jailed{duration_str}. Reason: {reason}. Case ID: #{case.id}"
        )

    @command(name="jailed")
    @has_permissions(manage_channels=True)
    @mod_setup_check()
    async def jail_list(self, ctx: Context):
        """
        List all currently jailed members.
        """
        jailed_members = await self.bot.db.fetch(
            "SELECT user_id, reason, start_time, end_time FROM jail WHERE guild_id = $1 AND is_active = TRUE",
            ctx.guild.id,
        )

        if not jailed_members:
            return await ctx.send("There are no jailed members.")

        entries = []
        for record in jailed_members:
            member = ctx.guild.get_member(record["user_id"])
            if member:
                duration = (
                    f"until {record['end_time']}"
                    if record["end_time"]
                    else "indefinitely"
                )
                entries.append(
                    f"{member.mention}: {record['reason']} (Jailed {duration})"
                )

        embed = Embed(title="Jailed Members")
        await ctx.autopaginator(embed=embed, description=entries, split=10)

    @command(name="unjail", aliases=["freehim"])
    @has_permissions(manage_channels=True)
    @mod_setup_check()
    async def unjail(self, ctx: Context, member: Member):
        """
        Remove a member from jail.
        """
        from extensions.mod.moderation import \
            Action  # Import here to avoid circular import

        success = await self.unjail_member(ctx.guild.id, member.id)
        if success:
            # Create a case entry
            case = await self.bot.get_cog("Moderation").insert_case(
                ctx=ctx, target=member, reason="Unjailed", action=Action.UNJAIL
            )
            await ctx.approve(
                f"{member.mention} has been removed from jail. Case ID: #{case.id}"
            )
        else:
            await ctx.warn(f"{member.mention} is not currently jailed.")

    async def unjail_member(self, guild_id: int, user_id: int) -> bool:
        jail_data = await self.bot.db.fetchrow(
            """
            UPDATE jail
            SET is_active = FALSE
            WHERE guild_id = $1 AND user_id = $2 AND is_active = TRUE
            RETURNING previous_roles
            """,
            guild_id,
            user_id,
        )

        if jail_data:
            guild = self.bot.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    # Remove jail role
                    jail_role_id = await self.bot.db.fetchval(
                        "SELECT jail_role_id FROM settings WHERE guild_id = $1",
                        guild_id,
                    )
                    jail_role = guild.get_role(jail_role_id)
                    if jail_role:
                        await member.remove_roles(jail_role, reason="Unjailed")

                    # Restore previous roles
                    previous_roles = [
                        guild.get_role(role_id)
                        for role_id in jail_data["previous_roles"]
                        if guild.get_role(role_id)
                    ]
                    await member.add_roles(*previous_roles, reason="Unjailed")

            return True
        return False

    @Cog.listener()
    async def on_member_update(self, before: Member, after: Member):
        if before.roles != after.roles:
            is_jailed = await self.bot.db.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM jail WHERE user_id = $1 AND guild_id = $2 AND is_active = TRUE)
                """,
                after.id,
                after.guild.id,
            )
            if is_jailed:
                jail_role = get(after.guild.roles, name="Jailed")
                if jail_role and jail_role not in after.roles:
                    await after.add_roles(jail_role, reason="Restoring jail role")
                    non_jail_roles = [
                        role
                        for role in after.roles
                        if role != jail_role and role != after.guild.default_role
                    ]
                    if non_jail_roles:
                        await after.remove_roles(
                            *non_jail_roles, reason="Removing non-jail roles"
                        )

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GuildChannel):
        if check := await self.bot.db.fetchrow(
            "SELECT * FROM jail WHERE guild_id = $1", channel.guild.id
        ):
            if role := channel.guild.get_role(int(check["role_id"])):
                await channel.set_permissions(
                    role,
                    view_channel=False,
                    reason="Overwriting permissions for jail role",
                )

    @Cog.listener()
    async def on_member_join(self, member: Member):
        if await self.bot.db.fetchrow(
            "SELECT * FROM jail WHERE guild_id = $1 AND user_id = $2",
            member.guild.id,
            member.id,
        ):
            if re := await self.bot.db.fetchrow(
                "SELECT jail_role_id FROM settings WHERE guild_id = $1", member.guild.id
            ):
                if role := member.guild.get_role(re[0]):
                    await member.add_roles(role, reason="Member jailed")
