import datetime
from datetime import datetime, timedelta
from typing import Optional, Union

import asyncpg
import discord
from config import color, emoji
from discord.ext import commands
from system.base.context import Context


class AntiNuke(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.recent_actions = {}

    async def logs(self, guild_id: int, user_id: int, action_type: str, details: str):
        try:
            settings = await self.settings(guild_id)
            if not settings:
                return

            start_time = datetime.utcnow()

            await self.client.pool.execute(
                """
                INSERT INTO antinuke_logs (guild_id, user_id, action_type, timestamp, details)
                VALUES ($1, $2, $3, $4, $5)
            """,
                guild_id,
                user_id,
                action_type,
                datetime.utcnow(),
                details,
            )

            if settings.get("log_channel"):
                guild = self.client.get_guild(guild_id)
                if guild:
                    log_channel = guild.get_channel(settings["log_channel"])
                    if log_channel:
                        punishment = settings.get("punishment", "n/a").lower()
                        punished_user = await self.client.fetch_user(user_id)
                        user_pfp = (
                            punished_user.avatar.url
                            if punished_user.avatar
                            else punished_user.default_avatar.url
                        )
                        end_time = datetime.utcnow()
                        time_taken = (end_time - start_time).total_seconds()

                        embed = discord.Embed(
                            title="", color=color.default, timestamp=datetime.utcnow()
                        )
                        embed.set_author(
                            name=f"{punished_user.name} | antinuke", icon_url=user_pfp
                        )
                        embed.add_field(
                            name="<:29:1298731238655266847> Action",
                            value=f"> `{punishment}`",
                            inline=True,
                        )
                        embed.add_field(
                            name="<:18:1298392181169721468> User",
                            value=f"> <@{user_id}> ({user_id})",
                            inline=True,
                        )
                        embed.add_field(name="", value=f"‎ ‎ ", inline=True)
                        embed.add_field(
                            name="<:28:1298731241209729024> Details",
                            value=f"> {details}",
                            inline=True,
                        )
                        embed.add_field(
                            name="<:22:1298731253473874003> Time",
                            value=f"> `{time_taken:.2f}s`",
                            inline=True,
                        )
                        await log_channel.send(embed=embed)
        except Exception as e:
            print(f"Error logging action: {e}")

    async def settings(self, guild_id: int):
        settings = await self.client.pool.fetchrow(
            """
            SELECT 
                channeldelete,
                channelcreate,
                roledelete,
                rolecreate,
                roleupdate,
                webhookcreate,
                ban,
                kick,
                punishment,
                log
            FROM antinuke 
            WHERE guild_id = $1
        """,
            guild_id,
        )

        if not settings:
            await self.client.pool.execute(
                """
                INSERT INTO antinuke (
                    guild_id,
                    channeldelete,
                    channelcreate,
                    roledelete,
                    rolecreate,
                    roleupdate,
                    webhookcreate,
                    ban,
                    kick,
                    punishment,
                    log
                ) VALUES ($1, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL)
                ON CONFLICT (guild_id) DO NOTHING
            """,
                guild_id,
            )
            return None

        event_mapping = {
            "channel_delete": settings["channeldelete"],
            "channel_create": settings["channelcreate"],
            "role_delete": settings["roledelete"],
            "role_create": settings["rolecreate"],
            "role_update": settings["roleupdate"],
            "webhook_create": settings["webhookcreate"],
            "ban": settings["ban"],
            "kick": settings["kick"],
        }

        return {
            "events": event_mapping,
            "punishment": settings["punishment"],
            "log_channel": settings["log"],
        }

    async def threshold(self, guild_id: int, user_id: int, action_type: str) -> bool:
        settings = await self.settings(guild_id)
        if not settings or not settings["events"]:
            return False

        threshold = settings["events"].get(action_type)
        if not threshold:
            return False

        is_admin = await self.client.pool.fetchval(
            """
            SELECT EXISTS(
                SELECT 1 FROM antinuke_admins 
                WHERE guild_id = $1 AND user_id = $2
            )
        """,
            guild_id,
            user_id,
        )

        if is_admin:
            return False

        key = f"{guild_id}:{user_id}:{action_type}"
        current_time = datetime.utcnow()

        if key not in self.recent_actions:
            self.recent_actions[key] = []

        self.recent_actions[key] = [
            time
            for time in self.recent_actions[key]
            if (current_time - time).total_seconds() <= 10
        ]

        self.recent_actions[key].append(current_time)
        return len(self.recent_actions[key]) >= threshold

    async def take_action(
        self,
        guild: discord.Guild,
        user: Union[discord.Member, discord.User],
        action_type: str,
    ):
        try:
            settings = await self.settings(guild.id)
            if not settings or not settings["punishment"]:
                return

            punishment = settings["punishment"]
            member = guild.get_member(user.id)

            if not member:
                try:
                    member = await guild.fetch_member(user.id)
                except discord.NotFound:
                    return

            if member:
                if not guild.me.guild_permissions.ban_members and punishment == "ban":
                    await self.logs(
                        guild.id,
                        user.id,
                        action_type,
                        "**Failed** to kick user due to me having no ban permissions",
                    )
                    return

                if not guild.me.guild_permissions.kick_members and punishment == "kick":
                    await self.logs(
                        guild.id,
                        user.id,
                        action_type,
                        "**Failed** to kick user due to me having no kick permissions",
                    )
                    return

                if guild.me.top_role <= member.top_role:
                    await self.logs(
                        guild.id,
                        user.id,
                        action_type,
                        f"**Failed** to {punishment} user due to having a higher role",
                    )
                    return

                try:
                    reason = f"due to exceeding {action_type.replace('_', ' ').title()} threshold"
                    if punishment == "ban":
                        await member.ban(reason=reason)
                        action_detail = f"User **banned** for exceeding `{action_type.replace('_', ' ').title()}` threshold"
                    elif punishment == "kick":
                        await member.kick(reason=reason)
                        action_detail = f"User **kicked** for exceeding `{action_type.replace('_', ' ').title()}` threshold"

                    await self.logs(guild.id, user.id, action_type, action_detail)

                except discord.Forbidden:
                    await self.logs(
                        guild.id,
                        user.id,
                        action_type,
                        f"**Failed** to {punishment} user due to permissions",
                    )

        except Exception as e:
            await self.logs(guild.id, user.id, action_type, f"```{str(e)}```")

    async def is_admin(self, guild_id: int, user_id: int) -> bool:
        guild = self.client.get_guild(guild_id)
        if guild and guild.owner_id == user_id:
            return True
        result = await self.client.pool.fetchval(
            "SELECT 1 FROM antinuke_admins WHERE guild_id = $1 AND user_id = $2",
            guild_id,
            user_id,
        )
        return result is not None

    @commands.group(description="Protect your server agaisnt mad kids", aliases=["an"])
    @commands.has_permissions(administrator=True)
    async def antinuke(self, ctx: Context):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):  # type: ignore
            await ctx.deny("**You're** not an antinuke admin")
            return

        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)  # type: ignore

    @antinuke.command(
        name="channeldelete",
        description="Punish someone for deleting to many channels",
        aliases=["chnneldel"],
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_channeldelete(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET channeldelete = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(
                name=f"{ctx.author.name} | Enabled channel delete", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET channeldelete = NULL WHERE guild_id = $1",
                ctx.guild.id,
            )
            await ctx.agree("**Disabled** channel delete")

    @antinuke.command(
        name="channelcreate",
        description="Punish someone for creating to many channels",
        aliases=["chnnelcr"],
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_channelcreate(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET channelcreate = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(
                name=f"{ctx.author.name} | Enabled channel create", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET channelcreate = NULL WHERE guild_id = $1",
                ctx.guild.id,
            )
            await ctx.agree("**Disabled** channel create")

    @antinuke.command(
        name="roledelete",
        description="Punish someone for deleting to many roles",
        aliases=["roledel"],
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_roledelete(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET roledelete = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(
                name=f"{ctx.author.name} | Enabled role delete", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET roledelete = NULL WHERE guild_id = $1",
                ctx.guild.id,
            )
            await ctx.agree("**Disabled** role delete")

    @antinuke.command(
        name="rolecreate",
        description="Punish someone for creating to many roles",
        aliases=["rolecr"],
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_rolecreate(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET rolecreate = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(
                name=f"{ctx.author.name} | Enabled role create", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET rolecreate = NULL WHERE guild_id = $1",
                ctx.guild.id,
            )
            await ctx.agree("**Disabled** role create")

    @antinuke.command(
        name="roleupdate",
        description="Punish someone for updating to many roles",
        aliases=["roleupd"],
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_roleupdate(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET roleupdate = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(
                name=f"{ctx.author.name} | Enabled role update", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET roleupdate = NULL WHERE guild_id = $1",
                ctx.guild.id,
            )
            await ctx.agree("**Disabled** role update")

    @antinuke.command(
        name="webhookcreate",
        description="Punish someone for creating to many webhooks",
        aliases=["webcr", "webhookcr"],
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_webhookcreate(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET webhookcreate = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(
                name=f"{ctx.author.name} | Enabled webhook create", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET webhookcreate = NULL WHERE guild_id = $1",
                ctx.guild.id,
            )
            await ctx.agree("**Disabled** webhook create")

    @antinuke.command(
        name="ban", description="Punish someone for banning to many users"
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_ban(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET ban = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(name=f"{ctx.author.name} | Enabled ban", icon_url=user_pfp)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET ban = NULL WHERE guild_id = $1", ctx.guild.id
            )
            await ctx.agree("**Disabled** ban")

    @antinuke.command(
        name="kick", description="Punish someone for kicking to many users"
    )
    @commands.has_permissions(administrator=True)
    async def antinuke_kick(
        self,
        ctx,
        option: str,
        punishment: Optional[str] = None,
        threshold: Optional[int] = None,
    ):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        option = option.lower()
        if option not in ["on", "off"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        if option == "on":
            if not punishment or not threshold:
                await ctx.deny("You're **missing** punishment and threshold")
                return

            if punishment.lower() not in ["ban", "kick"]:
                await ctx.deny("**Invalid option,** use either ban or kick")
                return

            if threshold < 1:
                await ctx.deny("Threshold *needs* to be atleast `1`")
                return

            await self.client.pool.execute(
                "UPDATE antinuke SET kick = $1, punishment = $2 WHERE guild_id = $3",
                threshold,
                punishment.lower(),
                ctx.guild.id,
            )
            embed = discord.Embed(
                description=f"> <:28:1298731241209729024> **Option:** `enabled` \n> <:29:1298731238655266847> **Punishment:** `{punishment.lower()}` \n> <:22:1298731253473874003> **Threshold:** {threshold}",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(
                name=f"{ctx.author.name} | Enabled kick", icon_url=user_pfp
            )
            await ctx.send(embed=embed)
        else:
            await self.client.pool.execute(
                "UPDATE antinuke SET kick = NULL WHERE guild_id = $1", ctx.guild.id
            )
            await ctx.agree("**Disabled** kick")

    @antinuke.command(name="logs", description="Send logs into a channel")
    @commands.has_permissions(administrator=True)
    async def antinuke_logs(self, ctx, channel: discord.TextChannel):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        guild_id = ctx.guild.id
        channel_id = channel.id

        settings = await self.settings(guild_id)

        if settings:
            await self.client.pool.execute(
                "UPDATE antinuke SET log = $1 WHERE guild_id = $2", channel_id, guild_id
            )
        else:
            await self.client.pool.execute(
                "INSERT INTO antinuke (guild_id, log) VALUES ($1, $2)",
                guild_id,
                channel_id,
            )

        await ctx.agree(f"**Set** the log channel to: {channel.mention}")

    @antinuke.command(name="admin", description="Add/Remove antinuke admins")
    @commands.has_permissions(administrator=True)
    async def admin(self, ctx, option: str, user: discord.Member):
        if not await self.is_admin(ctx.guild.id, ctx.author.id):
            await ctx.deny("**You're** not an antinuke admin")
            return

        if option not in ["add", "remove"]:
            await ctx.deny("**Invalid option,** use either on or off")
            return

        guild_id = ctx.guild.id
        user_id = user.id

        if option == "add":
            await self.client.pool.execute(
                "INSERT INTO antinuke_admins (guild_id, user_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                guild_id,
                user_id,
            )
            await ctx.agree(f"**Added** {user.mention} as an antinuke admin")
        elif option == "remove":
            await self.client.pool.execute(
                "DELETE FROM antinuke_admins WHERE guild_id = $1 AND user_id = $2",
                guild_id,
                user_id,
            )
            await ctx.agree(f"**Removed** {user.mention} from an antinuke admin")

    @commands.Cog.listener()
    async def on_member_ban(
        self, guild: discord.Guild, user: Union[discord.Member, discord.User]
    ):
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
            if entry.user and not await self.is_admin(guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if await self.threshold(guild.id, entry.user.id, "ban"):
                    await self.take_action(guild, entry.user, "ban")

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        async for entry in member.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.kick
        ):
            if entry.user and not await self.is_admin(member.guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if await self.threshold(member.guild.id, entry.user.id, "kick"):
                    await self.take_action(member.guild, entry.user, "kick")

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel):
        async for entry in channel.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.channel_create
        ):
            if entry.user and not await self.is_admin(channel.guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if await self.threshold(
                    channel.guild.id, entry.user.id, "channel_create"
                ):
                    await self.take_action(channel.guild, entry.user, "channel_create")

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        async for entry in channel.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.channel_delete
        ):
            if entry.user and not await self.is_admin(channel.guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if await self.threshold(
                    channel.guild.id, entry.user.id, "channel_delete"
                ):
                    await self.take_action(channel.guild, entry.user, "channel_delete")

    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        async for entry in role.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.role_create
        ):
            if entry.user and not await self.is_admin(role.guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if await self.threshold(role.guild.id, entry.user.id, "role_create"):
                    await self.take_action(role.guild, entry.user, "role_create")

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        async for entry in role.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.role_delete
        ):
            if entry.user and not await self.is_admin(role.guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if await self.threshold(role.guild.id, entry.user.id, "role_delete"):
                    await self.take_action(role.guild, entry.user, "role_delete")

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        async for entry in before.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.role_update
        ):
            if entry.user and not await self.is_admin(before.guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if before.permissions != after.permissions:
                    if await self.threshold(
                        before.guild.id, entry.user.id, "role_update"
                    ):
                        await self.take_action(before.guild, entry.user, "role_update")

    @commands.Cog.listener()
    async def on_webhooks_update(self, channel: discord.TextChannel):
        async for entry in channel.guild.audit_logs(
            limit=1, action=discord.AuditLogAction.webhook_create
        ):
            if entry.user and not await self.is_admin(channel.guild.id, entry.user.id):
                if entry.user.id == self.client.user.id:
                    return

                if await self.threshold(
                    channel.guild.id, entry.user.id, "webhook_create"
                ):
                    await self.take_action(channel.guild, entry.user, "webhook_create")


async def setup(client):
    await client.add_cog(AntiNuke(client))
