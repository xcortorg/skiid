import re
import discord
from discord import Embed, Member, TextChannel, PermissionOverwrite, Guild, Role
from discord.ext.commands import Cog, command, group, has_permissions
from discord.ext import tasks
from tools.client import Context
from tools import MixinMeta, CompositeMetaClass
from datetime import datetime, timedelta, timezone
from contextlib import suppress
from tools.paginator import Paginator
from logging import getLogger

log = getLogger("greed/jail")

def parse_timespan_jail(duration: str) -> int:
    pattern = r"(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?"
    match = re.fullmatch(pattern, duration)

    if not match:
        raise ValueError("Invalid time format")

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: int) -> str:
    delta = timedelta(seconds=seconds)
    days, remainder = divmod(delta.total_seconds(), 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts = [f"{int(days)}d" if days else "",
             f"{int(hours)}h" if hours else "",
             f"{int(minutes)}m" if minutes else "",
             f"{int(seconds)}s" if seconds else ""]
    return " ".join(part for part in parts if part)


class Jail(MixinMeta, metaclass=CompositeMetaClass):
    async def cog_load(self) -> None:
        self.check_jail.start()
        await self.restore_jailed_members()
        await super().cog_load()

    async def cog_unload(self) -> None:
        self.check_jail.cancel()
        await super().cog_unload()

    async def restore_jailed_members(self) -> None:
        members = await self.bot.db.fetch("SELECT user_id, guild_id, jailed_at FROM jailed.users")
        for member in members:
            await self.process_jailed_member(member)

    async def process_jailed_member(self, member: dict) -> None:
        guild: Guild | None = self.bot.get_guild(member["guild_id"])
        if not guild:
            return

        user: Member | None = guild.get_member(member["user_id"])
        if not user:
            return

        jail_role_id = await self.get_jail_role_id(guild)
        if not jail_role_id:
            return

        jail_role = guild.get_role(jail_role_id)
        if not jail_role:
            return

        user_duration = member["jailed_at"].replace(tzinfo=timezone.utc)
        current_time = datetime.utcnow().replace(tzinfo=timezone.utc)
        if (current_time - user_duration).total_seconds() > 0:
            await self.unjail_member(user, guild, jail_role, member["user_id"])
        else:
            await self.rejail_member(user, jail_role)

    async def get_jail_role_id(self, guild: Guild) -> int | None:
        return await self.bot.db.fetchval("SELECT role_id FROM jailed.config WHERE guild_id = $1", guild.id)

    async def unjail_member(self, user: Member, guild: Guild, jail_role: Role, user_id: int) -> None:
        previous_roles = await self.bot.db.fetchval("SELECT roles FROM jailed.users WHERE user_id = $1", user_id)
        if previous_roles:
            valid_roles = [guild.get_role(role) for role in previous_roles if guild.get_role(role)]
            if valid_roles:
                await user.add_roles(*valid_roles, reason="Jail duration expired")
        await user.remove_roles(jail_role, reason="Jail duration expired")
        await self.bot.db.execute("DELETE FROM jailed.users WHERE user_id = $1", user_id)

    async def rejail_member(self, user: Member, jail_role: Role) -> None:
        roles_to_remove = [role for role in user.roles if role in user.guild.roles]
        with suppress(discord.errors.NotFound):
            if roles_to_remove:
                await user.remove_roles(*roles_to_remove, reason="Jailed member re-joined")
        await user.add_roles(jail_role, reason="Jailed member re-joined")

    async def cleanup_database_roles(self) -> None:
        roles_data = await self.bot.db.fetch("SELECT guild_id, role_id FROM jailed.config")
        for role_data in roles_data:
            guild = self.bot.get_guild(role_data["guild_id"])
            if not guild:
                continue

            role = guild.get_role(role_data["role_id"])
            if role is None:
                await self.bot.db.execute(
                    "DELETE FROM jailed.config WHERE guild_id = $1 AND role_id = $2",
                    role_data["guild_id"], role_data["role_id"]
                )
                log.info(f"Removed non-existent role {role_data['role_id']} from guild {role_data['guild_id']}.")

    @Cog.listener("on_guild_channel_create")
    async def on_guild_channel_create(self, channel: TextChannel) -> None:
        """Check if a channel was created and a jail role exists."""
        jail_channel_id: int | None = await self.bot.db.fetchval(
            "SELECT channel_id FROM jailed.config WHERE guild_id = $1", channel.guild.id
        )
        if jail_channel_id and jail_channel_id == channel.id:
            jail_role_id: int | None = await self.bot.db.fetchval(
                "SELECT role_id FROM jailed.config WHERE guild_id = $1",
                channel.guild.id,
            )
            if jail_role_id:
                jail_role: Role | None = channel.guild.get_role(jail_role_id)
                if jail_role:
                    await channel.set_permissions(
                        jail_role, send_messages=True, view_channel=True
                    )

    @tasks.loop(seconds=30)
    async def check_jail(self) -> None:
        log.info("Checking jailed members")
        await self.cleanup_database_roles()

        jailed_members = await self.bot.db.fetch("SELECT user_id, guild_id, jailed_at FROM jailed.users")
        for member in jailed_members:
            await self.process_jailed_member(member)

    @command(name="setupjail", aliases=["setme"], description="manage guild")
    @has_permissions(manage_guild=True)
    async def setup_jail(self, ctx: Context) -> None:
        """Setup jail role and channel."""
        jail_role_id = await self.get_jail_role_id(ctx.guild)
        if jail_role_id:
            await ctx.warn("Jail role and channel are already set up. Use `jail reset` to reset.")
            return

        role = await ctx.guild.create_role(name="Jailed", reason="Jail role for Greed", mentionable=False, hoist=True)
        channel = await ctx.guild.create_text_channel(name="jail", reason="Jail channel for Greed")

        overwrite = {
            ctx.guild.default_role: PermissionOverwrite(read_messages=False, view_channel=False),
            role: PermissionOverwrite(read_messages=True, view_channel=True)
        }
        await channel.edit(overwrites=overwrite)

        await self.bot.db.execute(
            "INSERT INTO jailed.config (guild_id, role_id, channel_id) VALUES ($1, $2, $3)",
            ctx.guild.id, role.id, channel.id
        )

        await ctx.approve("Jail channel and role have been set up successfully.")

    @group(name="jail", invoke_without_command=True, description="manage roles")
    @has_permissions(manage_roles=True, manage_channels=True, moderate_members=True)
    async def jail(self, ctx: Context, member: Member, duration: str = "7d", *, reason: str = "no reason provided") -> None:
        """Jail a member."""
        jail_role_id = await self.get_jail_role_id(ctx.guild)
        if not jail_role_id:
            await ctx.warn("Jail role not found. Please set up a jail role and channel.")
            return

        role = ctx.guild.get_role(jail_role_id)
        if not role:
            await ctx.warn("Jail role not found. Please set up a jail role and channel.")
            return

        seconds = parse_timespan_jail(duration)
        if not (30 <= seconds <= 604800):
            await ctx.warn("Duration must be between 30 seconds and 7 days.")
            return

        is_jailed = await self.bot.db.fetchval("SELECT user_id FROM jailed.users WHERE user_id = $1", member.id)
        if is_jailed:
            await ctx.warn(f"{member.mention} is already jailed.")
            return

        roles_to_remove = [role for role in member.roles if role != ctx.guild.default_role]
        await member.remove_roles(*roles_to_remove, reason=reason)
        await member.add_roles(role, reason=reason)

        await self.bot.db.execute(
            "INSERT INTO jailed.users (user_id, guild_id, roles, jailed_at) VALUES ($1, $2, $3, $4)",
            member.id, ctx.guild.id, [role.id for role in roles_to_remove], datetime.utcnow() + timedelta(seconds=seconds)
        )

        readable_duration = format_duration(seconds)
        await ctx.approve(f"{member.mention} has been jailed for {readable_duration}.")

    @command(name="unjail", description="manage roles", brief="@66adam", usage="<member>")
    @has_permissions(manage_roles=True, manage_channels=True, moderate_members=True)
    async def unjail(self, ctx: Context, member: Member) -> None:
        """Unjail a member."""
        jail_role_id = await self.get_jail_role_id(ctx.guild)
        if not jail_role_id:
            await ctx.warn("Jail role not found. Please set up a jail role and channel.")
            return

        jail_role = ctx.guild.get_role(jail_role_id)
        if not jail_role:
            await ctx.warn("Jail role not found. Please set up a jail role and channel.")
            return

        is_jailed = await self.bot.db.fetchval("SELECT user_id FROM jailed.users WHERE user_id = $1", member.id)
        if not is_jailed:
            await ctx.warn(f"{member.mention} is not jailed.")
            return

        await member.remove_roles(jail_role, reason="Unjailed by moderator")

        previous_roles = await self.bot.db.fetchval("SELECT roles FROM jailed.users WHERE user_id = $1", member.id)
        if previous_roles:
            roles_to_add = [role for role in (ctx.guild.get_role(role_id) for role_id in previous_roles) if role]
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Unjailed by moderator")

        await self.bot.db.execute("DELETE FROM jailed.users WHERE user_id = $1", member.id)
        await ctx.approve(f"{member.mention} has been unjailed.")

    @command(name="jailed", description="manage roles")
    @has_permissions(manage_roles=True, manage_channels=True, moderate_members=True)
    async def jailed(self, ctx: Context) -> None:
        """List jailed members."""
        jail_role_id = await self.get_jail_role_id(ctx.guild)
        if not jail_role_id:
            await ctx.warn("Jail role not found. Please set up a jail role and channel.")
            return

        role = ctx.guild.get_role(jail_role_id)
        if not role:
            await ctx.warn("Jail role not found. Please set up a jail role and channel.")
            return

        jailed_members = [member.mention for member in ctx.guild.members if role in member.roles]

        if jailed_members:
            paginator = Paginator(ctx, entries=jailed_members, per_page=10)
            await paginator.start()
        else:
            await ctx.send("No jailed members found.")
