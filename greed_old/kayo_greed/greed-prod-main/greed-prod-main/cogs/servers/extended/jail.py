from discord import Embed, Member, Role, TextChannel, Message, PermissionOverwrite
from discord.ext.commands import Cog, command, Context, group, has_permissions
from discord.ext import tasks
from tools import MixinMeta, CompositeMetaClass
from humanfriendly import parse_timespan
from datetime import datetime, timedelta, timezone
from tools.paginator import Paginator
from tools.conversion import TouchableMember
from logging import getLogger

from main import greed

log = getLogger("greed/jail")
class Jail(MixinMeta, metaclass=CompositeMetaClass):
    """Jail cog for Greed"""
    
    async def cog_load(self) -> None:
        self.check_jail.start()
        member_check = await self.bot.db.fetch("SELECT user_id, guild_id, jailed_at FROM jailed.users")
        if member_check:
            for member in member_check:
                guild = self.bot.get_guild(member["guild_id"])
                if guild:
                    user = guild.get_member(member["user_id"])
                    if user:
                        jail_role_id = await self.bot.db.fetchval(
                            "SELECT role_id FROM jailed.config WHERE guild_id = $1",
                            guild.id
                        )
                        if jail_role_id:
                            jail_role = guild.get_role(jail_role_id)
                            if jail_role:
                                user_duration = member["jailed_at"].replace(tzinfo=timezone.utc)
                                if (datetime.utcnow().replace(tzinfo=timezone.utc) - user_duration).total_seconds() > 0:
                                    previous_roles = await self.bot.db.fetchval(
                                        "SELECT roles FROM jailed.users WHERE user_id = $1",
                                        member["user_id"]
                                    )
                                    if previous_roles:
                                        roles = [guild.get_role(role) for role in previous_roles if guild.get_role(role)]
                                        if roles:
                                            await user.add_roles(*roles, reason="Jail duration expired")
                                    await user.remove_roles(jail_role, reason="Jail duration expired")
                                    await self.bot.db.execute(
                                        "DELETE FROM jailed.users WHERE user_id = $1",
                                        member["user_id"]
                                    )
                                user_duration = member["jailed_at"].replace(tzinfo=timezone.utc)
                            elif (datetime.fromtimestamp(datetime.now(timezone.utc).timestamp()) - user_duration).total_seconds() < 0:
                                await user.remove_roles(*user.roles, reason="Jailed member re-joined")
                                await user.add_roles(jail_role, reason="Jailed member re-joined")
        return await super().cog_load()
    
    async def cog_unload(self) -> None:
        self.check_jail.cancel()
        return await super().cog_unload()

    @tasks.loop(seconds=30)
    async def check_jail(self) -> None:
        log.info("Checking jailed members")
        """Check jailed members"""
        jailed = await self.bot.db.fetch("SELECT user_id, guild_id, jailed_at FROM jailed.users")
        for user in jailed:
            guild = self.bot.get_guild(user["guild_id"])
            if guild:
                member = await guild.fetch_member(user["user_id"])
                if member:
                    role_id = await self.bot.db.fetchval(
                        "SELECT role_id FROM jailed.config WHERE guild_id = $1",
                        guild.id
                    )
                    if role_id:
                        role = guild.get_role(role_id)
                        if role:
                            user_duration = user["jailed_at"].replace(tzinfo=timezone.utc)
                            if (datetime.utcnow().replace(tzinfo=timezone.utc) - user_duration).total_seconds() > 0:
                                previous_roles = await self.bot.db.fetchval(
                                    "SELECT roles FROM jailed.users WHERE user_id = $1",
                                    member.id
                                )
                                if previous_roles:
                                    roles = [guild.get_role(role_id) for role_id in previous_roles if guild.get_role(role_id)]
                                    if roles:
                                        await member.add_roles(*roles, reason="Jail duration expired")
                                await member.remove_roles(role, reason="Jail duration expired")
                                await self.bot.db.execute(
                                    "DELETE FROM jailed.users WHERE user_id = $1",
                                    member.id
                                )
                                
    @command(name="setupjail")
    @has_permissions(manage_guild=True)
    async def setup_jail(self, ctx: Context) -> Message:
        """Setup jail role and channel"""
        check = await self.bot.db.fetchval(
            "SELECT role_id FROM jailed.config WHERE guild_id = $1",
            ctx.guild.id
        )
        if check:
            return await ctx.warn("Jail role and channel is already setup! please use `jail reset` to reset jail settings")
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
        return await ctx.approve("Jail channel and role has been setup successfully! please make sure the channel permissions are correct.")

    @Cog.listener("on_member_join")
    async def on_member_join(self, member: Member) -> None:
        """Check if member is jailed"""
        check = await self.bot.db.fetchval(
            "SELECT role_id FROM jailed.config WHERE guild_id = $1",
            member.guild.id
        )
        if check:
            jailed = await self.bot.db.fetchval(
                "SELECT user_id FROM jailed.users WHERE user_id = $1",
                member.id
            )
            if jailed:
                role = member.guild.get_role(jailed)
                if role:
                    member.remove_roles(*member.roles, reason="Jailed member joined")
                    await member.add_roles(role, reason="Jailed member joined")
    
    @Cog.listener("on_guild_channel_create")
    async def on_guild_channel_create(self, channel: TextChannel) -> None:
        """Check if a channel was created and a jail role exists"""
        check = await self.bot.db.fetchval(
            "SELECT channel_id FROM jailed.config WHERE guild_id = $1",
            channel.guild.id
        )
        if check:
            jail = await self.bot.db.fetchval(
                "SELECT channel_id FROM jailed.config WHERE channel_id = $1",
                channel.id
            )
            if jail:
                role = channel.guild.get_role(jail)
                if role:
                    await channel.set_permissions(role, send_messages=True, view_channel=True)
    
    @group(name="jail", invoke_without_command=True)
    @has_permissions(manage_roles=True, manage_channels=True, moderate_members=True)
    async def jail(self, ctx: Context, member: TouchableMember, duration: str = "7d", *, reason: str = "no reason provided") -> Message:
        """Jail a member"""
        check = await self.bot.db.fetchval(
            "SELECT role_id FROM jailed.config WHERE guild_id = $1",
            ctx.guild.id
        )
        if check:
            role = ctx.guild.get_role(check)
            if role:
                seconds = parse_timespan(duration)
                if seconds < 30:
                    return await ctx.warn("Duration cannot be under 30 seconds!")
                if seconds > 604800:
                    return await ctx.warn("Duration must not exceed 7 days!")
                now = datetime.now()
                now += timedelta(seconds=seconds)
                jailed = await self.bot.db.fetchval(
                    "SELECT user_id FROM jailed.users WHERE user_id = $1",
                    member.id
                )
                if jailed:
                    return await ctx.warn(f"{member.mention} is already jailed!")
                roles = [roled.id for roled in member.roles if roled != ctx.guild.default_role]
                roles_check = [ctx.guild.get_role(role_id) for role_id in roles]
                await member.remove_roles(*roles_check, reason=reason)
                await member.add_roles(role, reason=reason)
                await self.bot.db.execute(
                    "INSERT INTO jailed.users (user_id, guild_id, roles, jailed_at) VALUES ($1, $2, $3, $4)",
                    member.id, ctx.guild.id, roles, now
                )
                return await ctx.approve(f"{member.mention} has been jailed! for {seconds}")
            else:
                return await ctx.warn("Jail role not found! please setup jail role and channel")
        
    @jail.command(name="reset")
    @has_permissions(manage_guild=True)
    async def jail_reset(self, ctx: Context) -> Message:
        """Reset jail settings"""
        check = await self.bot.db.fetchval(
            "SELECT role_id FROM jailed.config WHERE guild_id = $1",
            ctx.guild.id
        )
        if check:
            role = ctx.guild.get_role(check)
            if role:
                await role.delete(reason="Jail role reset")
            channel = await self.bot.db.fetchval(
                "SELECT channel_id FROM jailed.config WHERE guild_id = $1",
                ctx.guild.id
            )
            if channel:
                channel = ctx.guild.get_channel(channel)
                if channel:
                    await channel.delete(reason="Jail channel reset")
            await self.bot.db.execute(
                "DELETE FROM jailed.config WHERE guild_id = $1",
                ctx.guild.id
            )
            await self.bot.db.execute(
                "DELETE FROM jailed.users WHERE guild_id = $1",
                ctx.guild.id
            )
            return await ctx.approve("Jail settings have been reset!")
        else:
            role_id = await self.bot.db.fetchval(
                "SELECT role_id FROM jailed.config WHERE guild_id = $1",
                ctx.guild.id
            )
            channel_id = await self.bot.db.fetchval(
                "SELECT channel_id FROM jailed.config WHERE guild_id = $1",
                ctx.guild.id
            )
            if role_id:
                role = ctx.guild.get_role(role_id)
                if role:
                    await role.delete(reason="Jail role reset")
            if channel_id:
                channel = ctx.guild.get_channel(channel_id)
                if channel:
                    await channel.delete(reason="Jail channel reset")
            await self.bot.db.execute(
                "DELETE FROM jailed.config WHERE guild_id = $1",
                ctx.guild.id
            )
            await self.bot.db.execute(
                "DELETE FROM jailed.users WHERE guild_id = $1",
                ctx.guild.id
            )
            return await ctx.approve("Jail settings have been reset!")
    
    @command(name="unjail")
    @has_permissions(manage_roles=True, manage_channels=True, moderate_members=True)
    async def unjail(self, ctx: Context, member: TouchableMember) -> Message:
        """Unjail a member"""
        check = await self.bot.db.fetchval(
            "SELECT role_id FROM jailed.config WHERE guild_id = $1",
            ctx.guild.id
        )
        if check:
            role = ctx.guild.get_role(check)
            if role:
                jailed = await self.bot.db.fetchval(
                    "SELECT user_id FROM jailed.users WHERE user_id = $1",
                    member.id
                )
                if jailed:
                    await member.remove_roles(role, reason="Unjailed by moderator")
                    previos_roles = await self.bot.db.fetchval(
                        "SELECT roles FROM jailed.users WHERE user_id = $1",
                        member.id
                    )
                    if previos_roles:
                        roles = [ctx.guild.get_role(role) for role in previos_roles]
                        await member.add_roles(*roles, reason="Unjailed by moderator")
                    await self.bot.db.execute(
                        "DELETE FROM jailed.users WHERE user_id = $1",
                        member.id
                    )
                    return await ctx.approve(f"{member.mention} has been unjailed!")
                return await ctx.warn(f"{member.mention} is not jailed!")
            else:
                return await ctx.warn("Jail role not found! please setup jail role and channel")
    
    @command(name="jailed")
    @has_permissions(manage_roles=True, manage_channels=True, moderate_members=True)
    async def jailed(self, ctx: Context) -> Message:
        """List jailed members"""
        check = await self.bot.db.fetchval(
            "SELECT role_id FROM jailed.config WHERE guild_id = $1",
            ctx.guild.id
        )
        if check:
            role = ctx.guild.get_role(check)
            if role:
                jailed = await self.bot.db.fetch("SELECT user_id FROM jailed.users WHERE guild_id = $1", ctx.guild.id)
                if jailed:
                    members = [member.mention for member in ctx.guild.members if role in member.roles]
                    if members:
                        paginator = Paginator(ctx, members, 10)
                        return await paginator.start()
                    return await ctx.warn("No jailed members found!")
        else:
            return await ctx.warn("Jail role not found! please setup jail role and channel")
    
    @command(name="jailconfig", aliases=["jailsettings", "jailview"])
    @has_permissions(manage_roles=True, manage_channels=True, moderate_members=True)
    async def jailconfig(self, ctx: Context) -> Message:
        """View jail settings"""
        check = await self.bot.db.fetchrow(
            "SELECT role_id, channel_id FROM jailed.config WHERE guild_id = $1",
            ctx.guild.id
        )
        if check:
            role = ctx.guild.get_role(check["role_id"])
            channel = ctx.guild.get_channel(check["channel_id"])
            if role and channel:
                embed = Embed(
                    title="Jail Settings",
                )
                embed.add_field(name="jail configuration", value=f"Role: {role.mention}\nChannel: {channel.mention}")
                return await ctx.send(embed=embed)
        else:
            return await ctx.warn("Jail role and channel not found! please setup jail role and channel")
        
