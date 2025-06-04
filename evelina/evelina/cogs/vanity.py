import time
import json
import discord

from typing import Union

from discord import Role, Embed
from discord.ext.commands import Cog, group, has_guild_permissions

from modules.styles import emojis, colors
from modules.predicates import boosted_to
from modules.evelinabot import EvelinaContext, Evelina

class Vanity(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.guild_configs = {}
        self.member_cache = {}
        self.cooldown_cache = {}
        self.alert_cooldown = 30

    async def cog_load(self):
        await self.load_guild_configs()

    async def load_guild_configs(self):
        query = "SELECT * FROM vanity"
        rows = await self.bot.db.fetch(query)
        for row in rows:
            if isinstance(row['roles'], str):
                roles = json.loads(row['roles'])
            elif isinstance(row['roles'], list):
                roles = row['roles']
            else:
                roles = []
            vanity_trigger = row['trigger'].lower() if row['trigger'] else None
            self.guild_configs[row['guild_id']] = {
                'channel_id': row['channel_id'],
                'roles': roles,
                'message': row['message'],
                'vanity': vanity_trigger
            }

    @Cog.listener()
    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        if self.bot.is_ready() and before.guild and before.guild.id in self.guild_configs:
            guild_id = after.guild.id
            if guild_id not in self.guild_configs:
                return
            config = self.guild_configs[guild_id]
            vanity_link = config['vanity']
            channel_id = config['channel_id']
            role_ids = config['roles']
            roles = [discord.Object(id=role_id) for role_id in role_ids]
            if after.status in [discord.Status.offline, discord.Status.invisible]:
                member_role_ids = [role.id for role in after.roles]
                to_remove = [role for role in roles if role.id in member_role_ids]
                if to_remove:
                    try:
                        await after.remove_roles(*to_remove, reason="[Vanity] User went offline/invisible")
                    except Exception:
                        pass
                self.member_cache[after.id] = False
                return
            had_vanity = self.member_cache.get(after.id, False)
            has_vanity = self.check_vanity_status(after.activities, vanity_link) if vanity_link else False
            if had_vanity == has_vanity:
                return
            self.member_cache[after.id] = has_vanity 
            member_role_ids = [role.id for role in after.roles]
            if has_vanity and not had_vanity:
                to_add = [role for role in roles if role.id not in member_role_ids]
                if to_add:
                    try:
                        await after.add_roles(*to_add, reason="[Vanity] User has vanity link in status")
                    except Exception:
                        pass
                if self.check_cooldown(guild_id, after.id):
                    await self.send_alert_embed(after, channel_id)
            elif not has_vanity and had_vanity:
                to_remove = [role for role in roles if role.id in member_role_ids]
                if to_remove:
                    try:
                        await after.remove_roles(*to_remove, reason="[Vanity] User removed vanity link from status")
                    except Exception:
                        pass
                self.member_cache[after.id] = False

    def check_cooldown(self, guild_id: int, member_id: int) -> bool:
        now = time.time()
        if guild_id not in self.cooldown_cache:
            self.cooldown_cache[guild_id] = {}
        last_alert = self.cooldown_cache[guild_id].get(member_id, 0)
        if now - last_alert >= self.alert_cooldown:
            self.cooldown_cache[guild_id][member_id] = now
            return True
        return False

    def check_vanity_status(self, activities, vanity_link: str) -> bool:
        for activity in activities:
            if activity.type == discord.ActivityType.custom and activity.name:
                activity_name = activity.name.lower() if activity.name else ""
                if vanity_link in activity_name:
                    return True
        return False

    async def send_alert_embed(self, member: discord.Member, channel_id: int):
        config = self.guild_configs[member.guild.id]
        channel = member.guild.get_channel(channel_id)
        if channel:
            try:
                embed_message = await self.bot.embed_build.alt_convert(member, config["message"])
                await channel.send(**embed_message)
            except Exception:
                pass

    @group(name="vanity", aliases=["van"], invoke_without_command=True, case_insensitive=True)
    async def vanity(self, ctx: EvelinaContext):
        """Manage vanity settings"""
        return await ctx.create_pages()
    
    @vanity.command(name="set", brief="manage guild", usage="vanity set /evelina")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_set(self, ctx: EvelinaContext, vanity: str):
        """Set the vanity substring"""
        check = await self.bot.db.fetchrow("SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("UPDATE vanity SET trigger = $1 WHERE guild_id = $2", vanity, ctx.guild.id)
            await ctx.send_success(f"Updated **vanity substring** to `{vanity}`")
            return await self.load_guild_configs()
        else:
            await self.bot.db.execute("INSERT INTO vanity (guild_id, trigger) VALUES ($1, $2)", ctx.guild.id, vanity) 
            await ctx.send_success(f"Set **vanity substring** to `{vanity}`")
            return await self.load_guild_configs()

    @vanity.command(name="remove", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_remove(self, ctx: EvelinaContext):
        """Remove the vanity substring"""
        check = await self.bot.db.fetchrow("SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("DELETE FROM vanity WHERE guild_id = $1", ctx.guild.id)
            await ctx.send_success(f"Removed **vanity substring**")
            return await self.load_guild_configs()
        else:
            await ctx.send_error("No **vanity substring** set")
            return await self.load_guild_configs()
        
    @vanity.group(name="role", invoke_without_command=True, case_insensitive=True)
    async def vanity_role(self, ctx: EvelinaContext):
        """Manage vanity reward roles"""
        return await ctx.create_pages()

    @vanity_role.command(name="add", brief="manage guild", usage="vanity role add @vanity", description="Add a role as vanity reward role")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_role_add(self, ctx: EvelinaContext, *, role: Role):
        """Add a role as vanity reward role"""
        roles = await self.bot.db.fetchval("SELECT roles FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if roles:
            roles = json.loads(roles)
            if role.id in roles:
                return await ctx.send_warning("This role is **already** set as vanity reward role")
            roles.append(role.id)
        else:
            roles = [role.id]
        await self.bot.db.execute("UPDATE vanity SET roles = $1 WHERE guild_id = $2", json.dumps(roles), ctx.guild.id)
        await ctx.send_success(f"Added {role.mention} as **vanity reward role**")
        return await self.load_guild_configs()
        
    @vanity_role.command(name="remove", brief="manage guild", usage="vanity role remove @vanity", description="Remove a role from vanity reward roles")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_role_remove(self, ctx: EvelinaContext, role: Union[Role, int]):
        """Remove a role from vanity reward roles"""
        role_id = self.bot.misc.convert_role(role)
        roles = await self.bot.db.fetchval("SELECT roles FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if not roles:
            return await ctx.send_error("No **award roles** set")
        roles = json.loads(roles)
        if role_id not in roles:
            return await ctx.send_error(f"Role {self.bot.misc.humanize_role(ctx.guild, role_id)} is **not** an award role")
        roles.remove(role_id)
        await self.bot.db.execute("UPDATE vanity SET roles = $1 WHERE guild_id = $2", json.dumps(roles), ctx.guild.id)
        await ctx.send_success(f"Removed {self.bot.misc.humanize_role(ctx.guild, role_id)} as an **award role**")
        return await self.load_guild_configs()
        
    @vanity_role.command(name="list", brief="manage guild", description="List all vanity reward roles")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_role_list(self, ctx: EvelinaContext):
        """List all vanity reward roles"""
        roles = await self.bot.db.fetchval("SELECT roles FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if not roles:
            return await ctx.send_error("No **award roles** set")
        roles = json.loads(roles)
        if not roles:
            return await ctx.send_error("No **award roles** set")
        content = [f"{self.bot.misc.humanize_role(ctx.guild, role_id)}" for role_id in roles]
        await ctx.paginate(content, "Vanity Award Roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        return await self.load_guild_configs()
        
    @vanity.command(name="message", brief="manage guild", usage="vanity message thank you {user.mention}")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_message(self, ctx: EvelinaContext, *, message: str):
        """Set the vanity message"""
        check = await self.bot.db.fetchrow("SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("UPDATE vanity SET message = $1 WHERE guild_id = $2", message, ctx.guild.id)
            await ctx.send_success(f"Updated **vanity message** to:\n```{message}```")
            return await self.load_guild_configs()
        else:
            await self.bot.db.execute("INSERT INTO vanity (guild_id, message) VALUES ($1, $2)", ctx.guild.id, message)
            await ctx.send_success(f"Set **vanity message** to:\n```{message}```")
            return await self.load_guild_configs()

    @vanity.group(name="channel", invoke_without_command=True, case_insensitive=True)
    async def vanity_channel(self, ctx: EvelinaContext):
        """Manage vanity channel"""
        return await ctx.create_pages()

    @vanity_channel.command(name="set", brief="manage guild", usage="vanity channel set #channel")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_channel_set(self, ctx: EvelinaContext, channel: discord.TextChannel):
        """Set the vanity channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("UPDATE vanity SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
            await ctx.send_success(f"Set **vanity channel** to {channel.mention}")
            return await self.load_guild_configs()
        else:
            await self.bot.db.execute("INSERT INTO vanity (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
            await ctx.send_success(f"Set **vanity channel** to {channel.mention}")
            return await self.load_guild_configs()
        
    @vanity_channel.command(name="remove", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_channel_remove(self, ctx: EvelinaContext):
        """Remove the vanity channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("UPDATE vanity SET channel_id = $1 WHERE guild_id = $2", None, ctx.guild.id)
            await ctx.send_success("Removed **vanity channel**")
            return await self.load_guild_configs()
        else:
            await ctx.send_error("No **vanity channel** set")
            return await self.load_guild_configs()
        
    @vanity.command(name="config", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @boosted_to(3)
    async def vanity_config(self, ctx: EvelinaContext):
        """Show the vanity settings for the guild."""
        check = await self.bot.db.fetchrow("SELECT * FROM vanity WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_error("No **vanity settings** found for this server.")
        channel_id = check['channel_id']
        trigger = check['trigger'] or emojis.DENY
        message = check['message'] or "No message set"
        roles_raw = check['roles']
        filtered_roles = []
        if roles_raw:
            if isinstance(roles_raw, str):
                try:
                    roles_list = json.loads(roles_raw)
                except json.JSONDecodeError:
                    roles_list = []
            elif isinstance(roles_raw, list):
                roles_list = roles_raw
            else:
                roles_list = []
            filtered_roles = [int(role_id) for role_id in roles_list if str(role_id).isdigit()]
        role_mentions = [self.bot.misc.humanize_role(ctx.guild, role_id) for role_id in filtered_roles]
        role_field_value = ", ".join(role_mentions) if role_mentions else emojis.DENY
        channel_field_value = self.bot.misc.humanize_channel(channel_id) if channel_id else emojis.DENY
        embed = Embed(title="Vanity Settings", color=colors.NEUTRAL)
        embed.add_field(name="Channel", value=channel_field_value, inline=True)
        embed.add_field(name="Trigger", value=trigger, inline=True)
        embed.add_field(name="Roles", value=role_field_value, inline=True)
        embed.add_field(name="Message", value=f"```{message}```", inline=False)
        await ctx.send(embed=embed)
        await self.load_guild_configs()

async def setup(bot: Evelina):
    await bot.add_cog(Vanity(bot))