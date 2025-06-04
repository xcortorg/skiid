import json
import humanfriendly

from datetime import datetime

from discord import Member, User, TextChannel, Embed
from discord.ext.commands import Cog, group, has_guild_permissions

from modules.styles import colors, emojis
from modules.evelinabot import EvelinaContext, Evelina
from modules.validators import ValidTime
from modules.converters import Punishment
from modules.predicates import antiraid_configured

class Antiraid(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @Cog.listener("on_member_join")
    async def on_new_acc_join(self, member: Member):
        if not self.bot.ar.get_bot_perms(member.guild):
            return
        if not await self.bot.ar.is_module("age", member.guild):
            return
        if await self.bot.ar.is_whitelisted(member):
            return
        res = await self.bot.db.fetchval("SELECT threshold FROM antiraid_age WHERE guild_id = $1", member.guild.id)
        if (datetime.now() - datetime.fromtimestamp(member.created_at.timestamp())).total_seconds() >= res:
            return
        tasks = [self.bot.ar.decide_punishment("age", member, f"[Antiraid] Account younger than {humanfriendly.format_timespan(res)}")]
        action_time = datetime.now()
        check = await self.bot.db.fetchrow("SELECT logs FROM antiraid WHERE guild_id = $1", member.guild.id)
        logs = member.guild.get_channel(check["logs"]) if check["logs"] else None
        await self.bot.ar.take_action(f"Account younger than {humanfriendly.format_timespan(res)}", member, tasks, action_time, logs)

    @Cog.listener("on_member_join")
    async def on_default_avatar_join(self, member: Member):
        if not self.bot.ar.get_bot_perms(member.guild):
            return
        if not await self.bot.ar.is_module("avatar", member.guild):
            return
        if await self.bot.ar.is_whitelisted(member):
            return
        if member.avatar:
            return
        tasks = [self.bot.ar.decide_punishment("avatar", member, "[Antiraid] Default Avatar")]
        action_time = datetime.now()
        check = await self.bot.db.fetchrow("SELECT logs FROM antiraid WHERE guild_id = $1", member.guild.id)
        logs = member.guild.get_channel(check["logs"]) if check["logs"] else None
        await self.bot.ar.take_action("Default Avatar", member, tasks, action_time, logs)

    @group(name="antiraid", brief="administrator", invoke_without_command=True, case_insensitive=True)
    async def antiraid(self, ctx: EvelinaContext):
        """Configure protection against potential raids"""
        return await ctx.create_pages()
    
    @antiraid.command(name="setup", brief="administrator")
    @has_guild_permissions(administrator=True)
    async def antiraid_setup(self, ctx: EvelinaContext):
        """Setup antiraid in your server"""
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        if check:
            if check["configured"] == "true":
                return await ctx.send_warning("Antiraid is **already** configured")
        args = ["UPDATE antiraid SET configured = $1 WHERE guild_id = $2", "true", ctx.guild.id]
        if not check:
            args = ["INSERT INTO antiraid (guild_id, configured) VALUES ($1, $2)", ctx.guild.id, "true"]
        await self.bot.db.execute(*args)
        return await ctx.send_success("Antiraid has been **successfully** configured")
    
    @antiraid.command(name="reset", brief="administrator")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_reset(self, ctx: EvelinaContext):
        """Reset antiraid in your server"""
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Antiraid is **not** configured")
        await self.bot.db.execute("DELETE FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Antiraid has been **successfully** reset")
    
    @antiraid.command(name="logs", brief="administrator", usage="antiraid logs #logs")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_logs(self, ctx: EvelinaContext, channel: TextChannel):
        """Set logs channel for antiraid"""
        await self.bot.db.execute("UPDATE antiraid SET logs = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
        return await ctx.send_success(f"Logs channel has been set to {channel.mention}")
    
    @antiraid.command(name="config", brief="administrator")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_config(self, ctx: EvelinaContext):
        """View current antiraid configuration"""
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        embed = Embed(title="Antiraid Settings", color=colors.NEUTRAL)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        newaccounts = await self.bot.db.fetchrow("SELECT * FROM antiraid_age WHERE guild_id = $1", ctx.guild.id)
        defaultavatar = await self.bot.db.fetchrow("SELECT * FROM antiraid_avatar WHERE guild_id = $1", ctx.guild.id)
        massjoin = await self.bot.db.fetchrow("SELECT * FROM antiraid_massjoin WHERE guild_id = $1", ctx.guild.id)
        description = f"**Logs Channel:** {self.bot.misc.humanize_channel(check['logs'], True) if check['logs'] else emojis.DENY}"
        if description:
            embed.description = description
        if newaccounts:
            embed.add_field(name=f"New Accounts ({humanfriendly.format_timespan(newaccounts['threshold'])})", value=f"Punishment: **{newaccounts['punishment']}**")
        if defaultavatar:
            embed.add_field(name="Default Avatar", value=f"Punishment: **{defaultavatar['punishment']}**")
        if massjoin:
            embed.add_field(name=f"Mass Join ({massjoin['threshold']})", value=f"Punishment: **{massjoin['punishment']}**")
        if len(embed.fields) == 0:
            return await ctx.send_warning("Antiraid has no modules enabled")
        return await ctx.send(embed=embed)

    @antiraid.group(name="age", brief="administrator", invoke_without_command=True, case_insensitive=True)
    async def antiraid_age(self, ctx: EvelinaContext):
        """Punish new registered accounts"""
        return await ctx.create_pages()
        
    @antiraid_age.command(name="enable", brief="administrator", usage="antiraid age enable 3d kick")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_age_enable(self, ctx: EvelinaContext, time: ValidTime, punishment: Punishment):
        """Enable new accounts protection"""
        if punishment == "strip":
            return await ctx.send_warning("**Strip** can't be a punishment in this case")
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid_age WHERE guild_id = $1", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antiraid_age VALUES ($1, $2, $3)", ctx.guild.id, punishment, time]
        else:
            args = ["UPDATE antiraid_age SET punishment = $1, threshold = $2 WHERE guild_id = $3", punishment, time, ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **new accounts** protection\n> Punishment: **{punishment}** Applying to: Accounts newer than **{humanfriendly.format_timespan(time)}**")
    
    @antiraid_age.command(name="disable", brief="administrator")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_age_disable(self, ctx: EvelinaContext):
        """Disable new accounts protection"""
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid_age WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("New accounts protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antiraid_age WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Disabled **new accounts** protection")
    
    @antiraid_age.command(name="punishment", brief="administrator", usage="antiraid age punishment ban")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_age_punishment(self, ctx: EvelinaContext, punishment: Punishment):
        """Change punishment for new accounts protection"""
        if punishment == "strip":
            return await ctx.send_warning("**Strip** can't be a punishment in this case")
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid_age WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("New accounts protection is **not** enabled")
        await self.bot.db.execute("UPDATE antiraid_age SET punishment = $1 WHERE guild_id = $2", punishment, ctx.guild.id)
        return await ctx.send_success(f"Changed punishment to **{punishment}** for new accounts protection")
    
    @antiraid.group(name="avatar", invoke_without_command=True, case_insensitive=True)
    async def antiraid_avatar(self, ctx: EvelinaContext):
        """Punish members with default avatars"""
        return await ctx.create_pages()
    
    @antiraid_avatar.command(name="enable", brief="administrator", usage="antiraid avatar enable ban")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_avatar_enable(self, ctx: EvelinaContext, punishment: Punishment):
        """Enable default avatar protection"""
        if punishment == "strip":
            return await ctx.send_warning("**Strip** can't be a punishment in this case")
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid_avatar WHERE guild_id = $1", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antiraid_avatar VALUES ($1, $2)", ctx.guild.id, punishment]
        else:
            args = ["UPDATE antiraid_avatar SET punishment = $1 WHERE guild_id = $2", punishment, ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **default avatar** protection\n> Punishment: **{punishment}**")
    
    @antiraid_avatar.command(name="disable", brief="administrator")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_avatar_disable(self, ctx: EvelinaContext):
        """Disable default avatar protection"""
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid_avatar WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Default avatar protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antiraid_avatar WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Disabled **default avatar** protection")
    
    @antiraid_avatar.command(name="punishment", brief="administrator", usage="antiraid avatar punishment ban")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_avatar_punishment(self, ctx: EvelinaContext, punishment: Punishment):
        """Change punishment for default avatar protection"""
        if punishment == "strip":
            return await ctx.send_warning("**Strip** can't be a punishment in this case")
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid_avatar WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Default avatar protection is **not** enabled")
        await self.bot.db.execute("UPDATE antiraid_avatar SET punishment = $1 WHERE guild_id = $2", punishment, ctx.guild.id)
        return await ctx.send_success(f"Changed punishment to **{punishment}** for default avatar protection")

    @antiraid.group(name="massjoin", invoke_without_command=True, case_insensitive=True)
    async def antiraid_massjoin(self, ctx: EvelinaContext):
        """Prevent join raids on your server"""
        return await ctx.create_pages()

    @antiraid_massjoin.command(name="enable", brief="administrator", aliases=["e"], usage="antiraid massjoin enable ban 3")
    @has_guild_permissions(administrator=True)
    async def antiraid_massjoin_enable(self, ctx: EvelinaContext, punishment: Punishment, threshold: int):
        """Enable mass join protection"""
        if punishment == "strip":
            return await ctx.send_warning("**Strip** can't be a punishment in this case")
        if threshold < 1:
            return await ctx.send_warning("Rate can't be lower than **1**")
        if await self.bot.db.fetchrow("SELECT * FROM antiraid_massjoin WHERE guild_id = $1", ctx.guild.id):
            await self.bot.db.execute("UPDATE antiraid_massjoin SET punishment = $1, threshold = $2 WHERE guild_id = $3", punishment, threshold, ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO antiraid_massjoin VALUES ($1, $2, $3)", ctx.guild.id, punishment, threshold)
        return await ctx.send_success(f"Enabled **mass join** protection\n> Punishment: **{punishment}** Threshold: **{threshold}**")
    
    @antiraid_massjoin.command(name="disable", brief="administrator", aliases=["dis"])
    @has_guild_permissions(administrator=True)
    async def antiraid_massjoin_disable(self, ctx: EvelinaContext):
        """Disbale antiraid mass join protection"""
        check = await self.bot.db.fetchrow("SELECT * FROM antiraid_massjoin WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Mass join protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antiraid_massjoin WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Disabled **mass join** protection")

    @antiraid_massjoin.command(name="threshold", brief="administrator", usage="antiraid joins threshold 3")
    @has_guild_permissions(administrator=True)
    async def antiraid_massjoin_threshold(self, ctx: EvelinaContext, threshold: int):
        """Change threshold for mass join protection"""
        if threshold < 1:
            return await ctx.send_warning("Rate can't be lower than **1**")
        if await self.bot.db.fetchrow("SELECT * FROM antiraid_massjoin WHERE guild_id = $1", ctx.guild.id):
            await self.bot.db.execute("UPDATE antiraid_massjoin SET threshold = $1 WHERE guild_id = $2", threshold, ctx.guild.id)
        else:
            return await ctx.send_warning("Antiraid mass join protection is **not** enabled")
        return await ctx.send_success(f"Changed threshold to **{threshold}** for mass join protection")

    @antiraid_massjoin.command(name="punishment", brief="administrator", usage="antiraid joins punishment ban")
    @has_guild_permissions(administrator=True)
    async def antiraid_massjoin_punishment(self, ctx: EvelinaContext, punishment: Punishment):
        """Change punishment for anti mass join protection"""
        if punishment == "strip":
            return await ctx.send_warning("**Strip** can't be a punishment in this case")
        if await self.bot.db.fetchrow("SELECT * FROM antiraid_massjoin WHERE guild_id = $1", ctx.guild.id):
            await self.bot.db.execute("UPDATE antiraid_massjoin SET punishment = $1, WHERE guild_id = $2", punishment, ctx.guild.id)
        else:
            return await ctx.send_warning("Antiraid mass join protection is **not** enabled")
        return await ctx.send_success(f"Changed punishment to **{punishment}** for mass join protection")

    @antiraid.command(name="whitelist", aliases=["wl"], brief="administrator", usage="antiraid whitelist comminate")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_whitelist(self, ctx: EvelinaContext, *, user: User):
        """Create a one-time whitelist to allow a user to join"""
        whitelisted = await self.bot.db.fetchval("SELECT whitelisted FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        if not whitelisted:
            whitelisted = []
        else:
            whitelisted = json.loads(whitelisted)
        if user.id in whitelisted:
            return await ctx.send_warning("This member is **already** antiraid whitelisted")
        whitelisted.append(user.id)
        await self.bot.db.execute("UPDATE antiraid SET whitelisted = $1 WHERE guild_id = $2", json.dumps(whitelisted), ctx.guild.id)
        return await ctx.send_success(f"Whitelisted {user.mention} from Antiraid system")
    
    @antiraid.command(name="unwhitelist", aliases=["uwl"], brief="administrator", usage="antiraid unwhitelist comminate", description="Unwhitelist a user or role from Antiraid system")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_unwhitelist(self, ctx: EvelinaContext, *, user: User):
        whitelisted = await self.bot.db.fetchval("SELECT whitelisted FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        if not whitelisted:
            whitelisted = []
        else:
            whitelisted = json.loads(whitelisted)
        if user.id not in whitelisted:
            return await ctx.send_warning("This member isn't antiraid whitelisted")
        whitelisted.remove(user.id)
        await self.bot.db.execute("UPDATE antiraid SET whitelisted = $1 WHERE guild_id = $2", json.dumps(whitelisted), ctx.guild.id)
        return await ctx.send_success(f"Unwhitelisted {user.mention} from antiraid system")
    
    @antiraid.command(name="whitelisted", brief="administrator")
    @has_guild_permissions(administrator=True)
    @antiraid_configured()
    async def antiraid_whitelisted(self, ctx: EvelinaContext):
        """View all current antiraid whitelists"""
        whitelisted = await self.bot.db.fetchval("SELECT whitelisted FROM antiraid WHERE guild_id = $1", ctx.guild.id)
        if not whitelisted:
            return await ctx.send_warning("There are **no** whitelisted members or roles")
        whitelisted = json.loads(whitelisted) if whitelisted else []
        content = [f"<@{wl}> (`{wl}`)" for wl in whitelisted]
        if not content:
            return await ctx.send_warning("There are **no** whitelisted members or roles")
        return await ctx.paginate(content, f"Antiraid Whitelist", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Antiraid(bot))