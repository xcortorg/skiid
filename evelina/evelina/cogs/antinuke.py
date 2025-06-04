import json
import asyncio
import humanfriendly
from typing import Union, List
from collections import defaultdict
from datetime import datetime

from discord import User, Member, Guild, Message, Embed, Role, TextChannel, Interaction, AuditLogAction
from discord.abc import GuildChannel
from discord.ext.commands import Cog, group
from discord.errors import Forbidden

from modules.styles import emojis, colors
from modules.helpers import EvelinaContext
from modules.evelinabot import Evelina
from modules.validators import ValidTime
from modules.converters import Punishment, NoStaff
from modules.predicates import antinuke_owner, admin_antinuke, antinuke_configured

class Antinuke(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Antinuke commands"
        self.locks = defaultdict(asyncio.Lock)
        self.thresholds = {}

        self.audit_log_cache = {}
        self.audit_log_queue = asyncio.Queue()
        self.rate_limit_status = defaultdict(int)
        self.worker_stop_event = asyncio.Event()
        self.queue_worker = None

        self.start_worker()

    def start_worker(self):
        if self.queue_worker:
            self.stop_worker()
        self.worker_stop_event.clear()
        self.queue_worker = asyncio.create_task(self.audit_log_worker())

    def stop_worker(self):
        if self.queue_worker:
            self.worker_stop_event.set()
            self.queue_worker.cancel()

    async def fetch_audit_log(self, guild: Guild, action: AuditLogAction, cache_duration=5):
        now = datetime.now()
        cache_key = (guild.id, action)
        if cache_key in self.audit_log_cache:
            entry, timestamp = self.audit_log_cache[cache_key]
            if (now - timestamp).total_seconds() < cache_duration:
                return entry
        try:
            async for entry in guild.audit_logs(limit=1, action=action):
                self.audit_log_cache[cache_key] = (entry, now)
                return entry
        except Exception:
            return None
    
    async def audit_log_worker(self):
        try:
            while not self.worker_stop_event.is_set():
                try:
                    guild, action, callback = await self.audit_log_queue.get()
                    if not guild or not action or not callback:
                        self.audit_log_queue.task_done()
                        continue
                    entry = await self.fetch_audit_log(guild, action)
                    if entry:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(entry)
                    self.audit_log_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception:
                    pass
        finally:
            pass

    async def queue_audit_log(self, guild: Guild, action: AuditLogAction, callback=None):
        if any(item[0] == guild and item[1] == action for item in self.audit_log_queue._queue):
            return
        await self.audit_log_queue.put((guild, action, callback))

    async def handle_ratelimit(self, guild: Guild):
        self.rate_limit_status[guild.id] += 1
        if self.rate_limit_status[guild.id] >= 10:
            await asyncio.sleep(10)
            self.rate_limit_status[guild.id] = 0
            return True
        return False
    
    async def stop_worker_async(self):
        """Stoppt den Worker sauber und wartet auf ausstehende Aufgaben."""
        if self.queue_worker:
            self.worker_stop_event.set()
            self.queue_worker.cancel()
            try:
                await self.queue_worker
            except asyncio.CancelledError:
                pass
        
        await self.audit_log_queue.join()

    async def cog_unload(self):
        """Wird aufgerufen, wenn das Cog entladen wird (z. B. beim Bot-Shutdown)."""
        await self.stop_worker_async()

    async def joined_whitelist(self, member: Member) -> bool:
        check = await self.bot.db.fetchval("SELECT whitelisted FROM antinuke WHERE guild_id = $1", member.guild.id)
        if check:
            whitelist = json.loads(check)
            return member.id in whitelist
        return False

    def big_role_mention(self, roles: List[Role]) -> bool:
        return any(len(role.members) / role.guild.member_count * 100 > 70 for role in roles)

    @Cog.listener("on_guild_role_update")
    async def on_role_edit(self, before: Role, after: Role):
        if not self.bot.an.get_bot_perms(before.guild):
            return
        if not await self.bot.an.is_module("edit role", before.guild):
            return
        if before.permissions == after.permissions:
            return
        if not self.bot.misc.is_dangerous(before) and not self.bot.misc.is_dangerous(after):
            return
        if self.bot.misc.is_dangerous(before) and not self.bot.misc.is_dangerous(after):
            return
        if await self.handle_ratelimit(before.guild):
            return
        async def process_entry(entry):
            if not self.bot.an.check_hieracy(entry.user, before.guild.me):
                return
            if await self.bot.an.is_whitelisted(entry.user):
                return
            tasks = []
            if not self.bot.misc.is_dangerous(before) and self.bot.misc.is_dangerous(after):
                tasks.append(after.edit(permissions=before.permissions))
            tasks.append(await self.bot.an.decide_punishment("edit role", entry.user, "[Antinuke] Maliciously editing roles"))
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", before.guild.id)
            logs = before.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Maliciously editing roles", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(before.guild, AuditLogAction.role_update, process_entry)

    @Cog.listener("on_guild_update")
    async def change_antinuke_owner(self, before: Guild, after: Guild):
        if before.owner_id == after.owner_id:
            return
        await self.bot.db.execute("INSERT INTO owner_history (guild_id, old_owner, new_owner, timestamp) VALUES ($1,$2,$3,$4)", before.id, before.owner_id, after.owner_id, datetime.now().timestamp())
        if not await self.bot.db.fetchrow("SELECT * FROM antinuke WHERE guild_id = $1 and owner_id = $2", before.id, before.owner_id):
            return
        await self.bot.db.execute("UPDATE antinuke SET owner_id = $1 WHERE guild_id = $2", after.owner_id, before.id)

    @Cog.listener("on_guild_update")
    async def vanity_change(self, before: Guild, after: Guild):
        if before.vanity_url_code != after.vanity_url_code:
            if before.vanity_url_code is None:
                return
            if not await self.bot.an.is_module("vanity change", after):
                return
            if await self.handle_ratelimit(after):
                return
            async def process_entry(entry):
                if await self.bot.an.is_whitelisted(entry.user):
                    return
                if not self.bot.an.check_hieracy(entry.user, after.me):
                    return
                tasks = [self.bot.an.decide_punishment("vanity change", entry.user, "[Antinuke] Unauthorized vanity URL change")]
                action_time = datetime.now()
                check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", after.id)
                logs = after.get_channel(check["logs"]) if check["logs"] else None
                await self.bot.an.take_action("Vanity URL change", entry.user, tasks, action_time, check["owner_id"], logs)
            await self.queue_audit_log(after, AuditLogAction.guild_update, process_entry)

    @Cog.listener("on_member_join")
    async def on_bot_join(self, member: Member):
        if not self.bot.an.get_bot_perms(member.guild):
            return
        if not member.bot:
            return
        if not await self.bot.an.is_module("bot add", member.guild):
            return
        if await self.handle_ratelimit(member.guild):
            return
        async def process_entry(entry):
            if await self.joined_whitelist(member):
                return
            if not self.bot.an.check_hieracy(entry.user, member.guild.me):
                return
            if await self.bot.an.is_whitelisted(entry.user):
                return
            tasks = [member.ban(reason="Unwhitelisted bot added"), self.bot.an.decide_punishment("bot add", entry.user, "[Antinuke] Adding unwhitelisted bots")]
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", member.guild.id)
            logs = member.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Adding unwhitelisted bot", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(member.guild, AuditLogAction.bot_add, process_entry)

    @Cog.listener("on_guild_channel_create")
    async def on_guild_channel_create(self, channel: GuildChannel):
        if not self.bot.an.get_bot_perms(channel.guild):
            return
        if not await self.bot.an.is_module("channel create", channel.guild):
            return
        if await self.handle_ratelimit(channel.guild):
            return
        async def process_entry(entry):
            if not entry or not self.bot.an.check_hieracy(entry.user, channel.guild.me):
                return
            if await self.bot.an.is_whitelisted(entry.user):
                return
            if not await self.bot.an.check_threshold("channel create", entry.user):
                return
            await channel.delete()
            cache_key = f"createchannel-{channel.guild.id}"
            if await self.bot.cache.get(cache_key):
                return
            await self.bot.cache.set(cache_key, True, 5)
            tasks = [self.bot.an.decide_punishment("channel create", entry.user, "[Antinuke] Creating channels")]
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", channel.guild.id)
            logs = channel.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Creating channels", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(channel.guild, AuditLogAction.channel_create, process_entry)

    @Cog.listener("on_guild_channel_delete")
    async def on_guild_channel_delete(self, channel: GuildChannel):
        if not self.bot.an.get_bot_perms(channel.guild):
            return
        if not await self.bot.an.is_module("channel delete", channel.guild):
            return
        if await self.handle_ratelimit(channel.guild):
            return
        async def process_entry(entry):
            if not self.bot.an.check_hieracy(entry.user, channel.guild.me):
                return
            if await self.bot.an.is_whitelisted(entry.user):
                return
            if not await self.bot.an.check_threshold("channel delete", entry.user):
                return
            if channel.category:
                await channel.clone()
            else:
                await channel.clone(parent=None)
            cache = await self.bot.cache.get(f"deletechannel-{channel.guild.id}")
            if cache:
                return
            await self.bot.cache.set(f"deletechannel-{channel.guild.id}", True, 5)
            tasks = [self.bot.an.decide_punishment("channel delete", entry.user, "[Antinuke] Deleting channels")]
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", channel.guild.id)
            logs = channel.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Deleting channels", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(channel.guild, AuditLogAction.channel_delete, process_entry)

    @Cog.listener("on_guild_role_create")
    async def on_role_creation(self, role: Role):
        if not self.bot.an.get_bot_perms(role.guild):
            return
        if not await self.bot.an.is_module("role create", role.guild):
            return
        if await self.handle_ratelimit(role.guild):
            return
        async def process_entry(entry):
            if not self.bot.an.check_hieracy(entry.user, role.guild.me):
                return
            if await self.bot.an.is_whitelisted(entry.user):
                return
            if not await self.bot.an.check_threshold("role create", entry.user):
                return
            guild = role.guild
            await role.delete()
            cache = await self.bot.cache.get(f"rolecreate-{guild.id}")
            if cache:
                return
            await self.bot.cache.set(f"rolecreate-{guild.id}", True, 5)
            tasks = [self.bot.an.decide_punishment("role create", entry.user, "[Antinuke] Creating roles")]
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", guild.id)
            logs = role.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Creating roles", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(role.guild, AuditLogAction.role_create, process_entry)

    @Cog.listener("on_guild_role_delete")
    async def on_role_deletion(self, role: Role):
        if not self.bot.an.get_bot_perms(role.guild):
            return
        if not await self.bot.an.is_module("role delete", role.guild):
            return
        if await self.handle_ratelimit(role.guild):
            return
        async def process_entry(entry):
            if not self.bot.an.check_hieracy(entry.user, role.guild.me):
                return
            if await self.bot.an.is_whitelisted(entry.user):
                return
            if not await self.bot.an.check_threshold("role delete", entry.user):
                return
            await role.guild.create_role(name=role.name, permissions=role.permissions, color=role.color, hoist=role.hoist, display_icon=role.display_icon, mentionable=role.mentionable,)
            cache = await self.bot.cache.get(f"roledelete-{role.guild.id}")
            if cache:
                return
            await self.bot.cache.set(f"roledelete-{role.guild.id}", True, 5)
            tasks = [self.bot.an.decide_punishment("role delete", entry.user, "[Antinuke] Deleting roles")]
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", role.guild.id)
            logs = role.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Deleting roles", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(role.guild, AuditLogAction.role_delete, process_entry)

    @Cog.listener("on_member_update")
    async def on_member_role_give(self, before: Member, after: Member):
        if len(before.roles) >= len(after.roles):
            return
        roles = [r for r in after.roles if r not in before.roles and r.is_assignable()]
        if not roles:
            return
        if not self.bot.an.get_bot_perms(before.guild):
            return
        role_lock_data = await self.bot.db.fetchrow("SELECT * FROM antinuke_roles WHERE guild_id = $1", before.guild.id)
        if role_lock_data and role_lock_data['status'] == True:
            locked_roles = json.loads(role_lock_data['roles']) if role_lock_data else []
            roles_to_revert = [role for role in roles if role.id in locked_roles]
            if roles_to_revert:
                await asyncio.sleep(1)
                async for entry in after.guild.audit_logs(limit=1, action=AuditLogAction.member_role_update):
                    if await self.bot.an.is_whitelisted(entry.user):
                        return
                    if not self.bot.an.check_hieracy(entry.user, before.guild.me):
                        return
                    await after.edit(roles=[r for r in after.roles if r not in roles_to_revert], reason="Locked roles being reverted")
                    action_time = datetime.now()
                    check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", before.guild.id)
                    logs = before.guild.get_channel(check["logs"]) if check["logs"] else None
                    return await self.bot.an.take_action("Locked role assigned", entry.user, [], action_time, check["owner_id"], logs)
            else:
                dangerous_roles = [role for role in roles if self.bot.misc.is_dangerous(role)]
                if not dangerous_roles:
                    return
                if not await self.bot.an.is_module("role giving", before.guild):
                    return
                await asyncio.sleep(1)
                async for entry in after.guild.audit_logs(limit=1, action=AuditLogAction.member_role_update):
                    if await self.bot.an.is_whitelisted(entry.user):
                        return
                    if not self.bot.an.check_hieracy(entry.user, before.guild.me):
                        return
                    if not await self.bot.cache.get(f"role-give-{before.guild.id}"):
                        await self.bot.cache.set(f"role-give-{before.guild.id}", True, 5)
                    added_roles = [role for role in after.roles if role not in before.roles and role.is_assignable()]
                    if not added_roles:
                        return
                    tasks = [
                        after.edit(roles=[role for role in after.roles if role not in added_roles], reason="Reverting added roles"),
                        self.bot.an.decide_punishment("role giving", entry.user, "Giving roles with dangerous permissions")
                    ]
                    action_time = datetime.now()
                    check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", before.guild.id)
                    logs = before.guild.get_channel(check["logs"]) if check["logs"] else None
                    return await self.bot.an.take_action("Giving roles with dangerous permissions", entry.user, tasks, action_time, check["owner_id"], logs)
        else:
            dangerous_roles = [role for role in roles if self.bot.misc.is_dangerous(role)]
            if not dangerous_roles:
                return
            if not await self.bot.an.is_module("role giving", before.guild):
                return
            await asyncio.sleep(1)
            async for entry in after.guild.audit_logs(limit=1, action=AuditLogAction.member_role_update):
                if await self.bot.an.is_whitelisted(entry.user):
                    return
                if not self.bot.an.check_hieracy(entry.user, before.guild.me):
                    return
                if not await self.bot.cache.get(f"role-give-{before.guild.id}"):
                    await self.bot.cache.set(f"role-give-{before.guild.id}", True, 5)
                added_roles = [role for role in after.roles if role not in before.roles and role.is_assignable()]
                if not added_roles:
                    return
                tasks = [
                    after.edit(roles=[role for role in after.roles if role not in added_roles], reason="Reverting added roles"),
                    self.bot.an.decide_punishment("role giving", entry.user, "Giving roles with dangerous permissions")
                ]
                action_time = datetime.now()
                check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", before.guild.id)
                logs = before.guild.get_channel(check["logs"]) if check["logs"] else None
                return await self.bot.an.take_action("Giving roles with dangerous permissions", entry.user, tasks, action_time, check["owner_id"], logs)

    @Cog.listener("on_member_remove")
    async def on_kick_action(self, member: Member):
        if not self.bot.an.get_bot_perms(member.guild):
            return
        if not await self.bot.an.is_module("kick", member.guild):
            return
        async def process_entry(entry):
            if await self.bot.an.is_whitelisted(entry.user):
                return
            executor = member.guild.get_member(entry.user.id)
            if not executor:
                return
            if not self.bot.an.check_hieracy(executor, member.guild.me):
                return
            if not await self.bot.an.check_threshold("kick", entry.user):
                return
            if await self.bot.cache.get(f"kick-{member.guild.id}"):
                return
            await self.bot.cache.set(f"kick-{member.guild.id}", True, 5)
            tasks = [self.bot.an.decide_punishment("kick", entry.user, "[Antinuke] Kicking members")]
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", member.guild.id)
            logs = member.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Kicking members", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(member.guild, AuditLogAction.kick, process_entry)

    @Cog.listener("on_member_ban")
    async def on_ban_action(self, guild: Guild, user: Union[User, Member]):
        if not self.bot.an.get_bot_perms(guild):
            return
        if not await self.bot.an.is_module("ban", guild):
            return
        async def process_entry(entry):
            if await self.bot.an.is_whitelisted(entry.user):
                return
            if isinstance(user, Member) and not self.bot.an.check_hieracy(entry.user, guild.me):
                return
            if not await self.bot.an.check_threshold("ban", entry.user):
                return
            cache = await self.bot.cache.get(f"ban-{guild.id}")
            if cache:
                return
            await self.bot.cache.set(f"ban-{guild.id}", True, 5)
            tasks = [self.bot.an.decide_punishment("ban", entry.user, "[Antinuke] Banning members")]
            action_time = datetime.now()
            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", guild.id)
            logs = user.guild.get_channel(check["logs"]) if check["logs"] else None
            await self.bot.an.take_action("Banning members", entry.user, tasks, action_time, check["owner_id"], logs)
        await self.queue_audit_log(guild, AuditLogAction.ban, process_entry)

    @group(name="antinuke", aliases=["an"], description="Antinuke & antiraid commands", invoke_without_command=True, case_insensitive=True)
    async def antinuke(self, ctx: EvelinaContext):
        await ctx.send_help(ctx.command)

    @antinuke.command(name="setup", brief="antinuke owner", description="Enable Antinuke system to protect your server")
    async def antinuke_setup(self, ctx: EvelinaContext):
        check = await ctx.bot.db.fetchrow("SELECT * FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if check:
            if check["configured"] == "true":
                return await ctx.send_warning("Antinuke is **already** configured\n> You can check [**here**](https://docs.evelina.bot/security/antinuke#antinuke-recommended-configuration) our recommend antinuke configuration")
            if check["owner_id"]:
                owner_id = check["owner_id"]
        else:
            owner_id = ctx.guild.owner_id
        if ctx.author.id != owner_id:
            return await ctx.send_warning(f"Only <@!{owner_id}> can use this command!\n> If the account can't be used, please join the [**support server**](https://discord.gg/evelina)")
        args = ["UPDATE antinuke SET configured = $1 WHERE guild_id = $2", "true", ctx.guild.id]
        if not check:
            args = ["INSERT INTO antinuke (guild_id, configured, owner_id) VALUES ($1,$2,$3)", ctx.guild.id, "true", ctx.guild.owner_id]
        await self.bot.db.execute(*args)
        await ctx.send_success("Antinuke is **enabled**\n> You can check [**here**](https://docs.evelina.bot/security/antinuke#antinuke-recommended-configuration) our recommend antinuke configuration")
        
    @antinuke.command(name="reset", aliases=["disable"], brief="antinuke owner", description="Disable Antinuke system on your server")
    @antinuke_owner()
    async def antinuke_reset(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM antinuke WHERE guild_id = $1", interaction.guild.id)
            await interaction.client.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1", interaction.guild.id)
            await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Disabled the antinuke"), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Antinuke deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** antinuke?", yes_func=yes_callback, no_func=no_callback)
        
    @antinuke.command(name="config", brief="antinuke admin", description="View Antinuke config on your server")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_config(self, ctx: EvelinaContext):
        results = await self.bot.db.fetch("SELECT module, punishment, threshold FROM antinuke_modules WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There is **no** module enabled")
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=f"{ctx.guild.name}'s Antinuke Config", icon_url=ctx.guild.icon)
        for result in results:
            module_name = result['module'].capitalize()
            punishment = result['punishment']
            threshold = result['threshold']
            if module_name == "New accounts":
                threshold = self.bot.misc.humanize_time(result['threshold'])
            description = f"Punishment: {punishment}\nThreshold: {threshold}"
            embed.add_field(name=f"> {module_name}", value=description, inline=True)
        await ctx.send(embed=embed)
        
    @antinuke.command(name="logs", brief="antinuke admin", usage="antinuke logs #an-logs", description="Add/Remove Antinuke logs channel")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_logs(self, ctx: EvelinaContext, *, channel: TextChannel = None):
        if not channel:
            await self.bot.db.execute("UPDATE antinuke SET logs = $1 WHERE guild_id = $2", None, ctx.guild.id)
            return await ctx.send_success("Removed the logs channel")
        await self.bot.db.execute("UPDATE antinuke SET logs = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
        await ctx.send_success(f"Set the antinuke logs channel to {channel.mention}")
        
    @antinuke.group(name="channeldelete", brief="antinuke admin", description="Prevent admins from deleting channels", invoke_without_command=True, case_insensitive=True)
    async def antinuke_channelremove(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_channelremove.command(name="enable", brief="antinuke admin", usage="antinuke channeldelete enable 1 strip", description="Enable protection against deleting channels")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_channelremove_enable(self, ctx: EvelinaContext, threshold: int, punishment: Punishment):
        if threshold < 0:
            return await ctx.send_warning("Threshold can't be lower than **0**")
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "channel delete", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "channel delete", punishment, threshold]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1, threshold = $2 WHERE module = $3 AND guild_id = $4", punishment, threshold, "channel delete", ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **channel delete** protection\n> Punishment: **{punishment}** Threshold: **{threshold}/60s**")
    
    @antinuke_channelremove.command(name="disable", brief="antinuke admin", description="Disable protection against deleting channels")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_channelremove_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "channel delete", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Channel delete protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "channel delete")
        return await ctx.send_success("Disabled **channel delete** protection")
    
    @antinuke.group(name="channelcreate", brief="antinuke admin", description="Prevent admins from creating channels", invoke_without_command=True, case_insensitive=True)
    async def antinuke_channelcreate(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_channelcreate.command(name="enable", brief="antinuke admin", usage="antinuke channelcreate enable 3 strip", description="Enable protection against creating channels")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_channelcreate_enable(self, ctx: EvelinaContext, threshold: int, punishment: Punishment):
        if threshold < 0:
            return await ctx.send_warning("Threshold can't be lower than **0**")
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "channel create", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "channel create", punishment, threshold]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1, threshold = $2 WHERE module = $3 AND guild_id = $4", punishment, threshold, "channel create", ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **channel create** protection\n> Punishment: **{punishment}** Threshold: **{threshold}/60s**")
    
    @antinuke_channelcreate.command(name="disable", brief="antinuke admin", description="Disable protection against creating channels")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_channelcreate_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "channel create", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Channel create protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "channel create")
        return await ctx.send_success("Disabled **channel create** protection")
    
    @antinuke.group(name="giverole", brief="antinuke admin", description="Prevent admins from giving dangerous roles", invoke_without_command=True, case_insensitive=True)
    async def antinuke_giverole(self, ctx: EvelinaContext):
        return await ctx.create_pages()
        
    @antinuke_giverole.command(name="enable", brief="antinuke admin", usage="antinuke giverole enable ban", description="Enable protection against giving dangerous roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_giverole_enable(self, ctx: EvelinaContext, punishment: Punishment):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "role giving", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "role giving", punishment, 0,]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1, threshold = $2 WHERE module = $3 AND guild_id = $4", punishment, 0, "role giving", ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **role giving** protection\n> Punishment: **{punishment}**")
    
    @antinuke_giverole.command(name="disable", brief="antinuke admin", description="Disable protection against giving dangerous roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_giverole_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "role giving", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Role giving protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "role giving")
        return await ctx.send_success("Disabled **role giving** protection")
    
    @antinuke.group(name="roledelete", brief="antinuke admin", description="Prevent admins from deleting roles", invoke_without_command=True, case_insensitive=True)
    async def antinuke_roledelete(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_roledelete.command(name="enable", brief="antinuke admin", usage="antinuke roledelete enable 1 strip", description="Enable protection against deleting roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_roledelete_enable(self, ctx: EvelinaContext, threshold: int, punishment: Punishment):
        if threshold < 0:
            return await ctx.send_warning("Threshold can't be lower than **0**")
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "role delete", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "role delete", punishment, threshold]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1, threshold = $2 WHERE module = $3 AND guild_id = $4", punishment, threshold, "role delete", ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **role delete** protection\n> Punishment: **{punishment}** Threshold: **{threshold}/60s**")
    
    @antinuke_roledelete.command(name="disable", brief="antinuke admin", description="Disable protection against deleting roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_roldelete_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "role delete", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Role delete protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "role delete")
        return await ctx.send_success("Disabled **role delete** protection")
    
    @antinuke.group(name="rolecreate", brief="antinuke admin", description="Prevent admins from creating roles", invoke_without_command=True, case_insensitive=True)
    async def antinuke_rolecreate(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_rolecreate.command(name="enable", brief="antinuke admin", usage="antinuke rolecreate enable 3 strip", description="Enable protection against creating roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_rolecreate_enable(self, ctx: EvelinaContext, threshold: int, punishment: Punishment):
        if threshold < 0:
            return await ctx.send_warning("Threshold can't be lower than **0**")
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "role create", ctx.guild.id,)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "role create", punishment, threshold]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1, threshold = $2 WHERE module = $3 AND guild_id = $4", punishment, threshold, "role create", ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **role create** protection\n> Punishment: **{punishment}** Threshold: **{threshold}/60s**")
    
    @antinuke_rolecreate.command(name="disable", brief="antinuke admin", description="Disable protection against creating roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_rolecreate_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "role create", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Role create protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "role create",)
        return await ctx.send_success("Disabled **role create** protection")
    
    @antinuke.group(name="rolelock", brief="antinuke admin", description="Manage role locks on your server", invoke_without_command=True, case_insensitive=True)
    async def antinuke_rolelock(self, ctx: EvelinaContext):
        await ctx.send_help(ctx.command)

    @antinuke_rolelock.command(name="enable", brief="antinuke admin", description="Enable all role locks on the server")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_rolelock_enable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO antinuke_roles (guild_id, roles, status) VALUES ($1, $2, $3)", ctx.guild.id, json.dumps([]), True)
        else:
            await self.bot.db.execute("UPDATE antinuke_roles SET status = $1 WHERE guild_id = $2", True, ctx.guild.id)
        await ctx.send_success("Role lock system has been **enabled**")

    @antinuke_rolelock.command(name="disable", brief="antinuke admin", description="Disable all role locks on the server")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_rolelock_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO antinuke_roles (guild_id, roles, status) VALUES ($1, $2, $3)", ctx.guild.id, json.dumps([]), False)
        else:
            await self.bot.db.execute("UPDATE antinuke_roles SET status = $1 WHERE guild_id = $2", False, ctx.guild.id)
        await ctx.send_success("Role lock system has been **disabled**")

    @antinuke_rolelock.command(name="add", brief="antinuke admin", usage="antinuke rolelock add @role", description="Add a role to the lock list")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_rolelock_add(self, ctx: EvelinaContext, *, role: Role):
        role_locks_status = await self.bot.db.fetchval("SELECT status FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        if role_locks_status is False or role_locks_status is None:
            return await ctx.send_warning(f"Role lock system is not enabled. Use `{ctx.clean_prefix}antinuke rolelock enable` first")
        role_locks = await self.bot.db.fetchval("SELECT roles FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        role_locks = json.loads(role_locks)
        if role.id in role_locks:
            return await ctx.send_warning(f"Role {role.mention} is **already** locked")
        role_locks.append(role.id)
        await self.bot.db.execute("UPDATE antinuke_roles SET roles = $1 WHERE guild_id = $2", json.dumps(role_locks), ctx.guild.id)
        await ctx.send_success(f"Role {role.mention} has been **locked**")

    @antinuke_rolelock.command(name="remove", brief="antinuke admin", usage="antinuke rolelock remove @role", description="Remove a role from the lock list")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_rolelock_remove(self, ctx: EvelinaContext, *, role: Union[Role, int]):
        role_id = self.bot.misc.convert_role(role)
        role_locks_status = await self.bot.db.fetchval("SELECT status FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        if role_locks_status is False or role_locks_status is None:
            return await ctx.send_warning(f"Role lock system is not enabled. Use `{ctx.clean_prefix}antinuke rolelock enable` first")
        role_locks = await self.bot.db.fetchval("SELECT roles FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        role_locks = json.loads(role_locks)
        if role_id not in role_locks:
            return await ctx.send_warning(f"Role {self.bot.misc.humanize_role(ctx.guild, role_id)} is **not** locked.")
        role_locks.remove(role_id)
        await self.bot.db.execute("UPDATE antinuke_roles SET roles = $1 WHERE guild_id = $2", json.dumps(role_locks), ctx.guild.id)
        await ctx.send_success(f"Role {self.bot.misc.humanize_role(ctx.guild, role_id)} has been **unlocked**")

    @antinuke_rolelock.command(name="list", brief="antinuke admin", description="List all locked roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_rolelock_list(self, ctx: EvelinaContext):
        role_locks = await self.bot.db.fetchval("SELECT roles FROM antinuke_roles WHERE guild_id = $1", ctx.guild.id)
        if not role_locks:
            return await ctx.send_warning("There are **no** locked roles")
        role_locks = json.loads(role_locks)
        roles = [ctx.guild.get_role(r) for r in role_locks if ctx.guild.get_role(r)]
        if not roles:
            return await ctx.send_warning("There are **no** locked roles")
        roles = [r.mention for r in roles]
        await ctx.paginate(roles, f"{ctx.guild.name}'s locked roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @antinuke.group(name="kick", brief="antinuke admin", description="Prevent admins from kicking members", invoke_without_command=True, case_insensitive=True)
    async def antinuke_kick(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_kick.command(name="enable", brief="antinuke admin", usage="antinuke kick enable 3 kick", description="Enable protection against kicking members")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_kick_enable(self, ctx: EvelinaContext, threshold: int, punishment: Punishment):
        if threshold < 0:
            return await ctx.send_warning("Threshold can't be lower than **0**")
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "kick", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "kick", punishment, threshold]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1, threshold = $2 WHERE module = $3 AND guild_id = $4", punishment, threshold, "kick", ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **kick** protection\n> Punishment: **{punishment}** Threshold: **{threshold}/60s**")
    
    @antinuke_kick.command(name="disable", brief="antinuke admin", description="Disable protection against kicking members")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_kick_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "kick", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Kick protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "kick")
        return await ctx.send_success("Disabled **kick** protection")
    
    @antinuke.group(name="ban", brief="antinuke admin", description="Prevent admins from banning members", invoke_without_command=True, case_insensitive=True)
    async def antinuke_ban(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_ban.command(name="enable", brief="antinuke admin", usage="antinuke ban enable 3 kick", description="Enable protection against banning members")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_ban_enable(self, ctx: EvelinaContext, threshold: int, punishment: Punishment):
        if threshold < 0:
            return await ctx.send_warning("Threshold can't be lower than **0**")
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "ban", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "ban", punishment, threshold]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1, threshold = $2 WHERE module = $3 AND guild_id = $4", punishment, threshold, "ban", ctx.guild.id]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **ban** protection\n> Punishment: **{punishment}** Threshold: **{threshold}/60s**")
    
    @antinuke_ban.command(name="disable", brief="antinuke admin", description="Disable protection against banning members")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_ban_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "ban", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Ban protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "ban")
        return await ctx.send_success("Disabled **ban** protection")
    
    @antinuke.group(name="editrole", brief="antinuke admin", description="Prevent admins from editing dangerous roles", invoke_without_command=True, case_insensitive=True)
    async def antinuke_editrole(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_editrole.command(name="enable", brief="antinuke admin", usage="antinuke editrole enable strip", description="Enable protection against editing dangerous attributes of a role")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_editrole_enable(self, ctx: EvelinaContext, punishment: Punishment):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "edit role", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "edit role", punishment, None]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1 WHERE guild_id = $2 AND module = $3", punishment, ctx.guild.id, "edit role"]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **edit role** protection\n> Punishment: **{punishment}**")
    
    @antinuke_editrole.command(name="disable", brief="antinuke admin", description="Disable protection against editing dangerous attributes of a role")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_editrole_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "edit role", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Edit role protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "edit role")
        return await ctx.send_success("Disabled **edit role** protection")
    
    @antinuke.group(name="vanity", brief="antinuke admin", description="Protect your server against vanity changes", invoke_without_command=True, case_insensitive=True)
    async def antinuke_vanity(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_vanity.command(name="enable", brief="antinuke admin", usage="antinuke vanity enable ban", description="Enable protaction against vanity change")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_vanity_enable(self, ctx: EvelinaContext, punishment: Punishment):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "vanity change", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "vanity change", punishment, None]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1 WHERE guild_id = $2 AND module = $3", punishment, ctx.guild.id, "vanity change"]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **vanity change** protection\n> Punishment: **{punishment}**\n-# Keep in mind that evelina only will punish the user, not changing the Vanity back.")
    
    @antinuke_vanity.command(name="disable", brief="antinuke admin", description="Disable protection against vanity change")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_vanity_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "vanity change", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Vanity change protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "vanity change")
        return await ctx.send_success("Disabled **vanity change** protection")
    
    @antinuke.group(name="botadd", brief="antinuke admin", description="Protect your server against new bot additions", invoke_without_command=True, case_insensitive=True)
    async def antinuke_botadd(self, ctx: EvelinaContext):
        await ctx.send_help(ctx.command)

    @antinuke_botadd.command(name="enable", brief="antinuke admin", usage="antinuke botadd enable ban", description="Enable protection against new bot additions")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_botadd_enable(self, ctx: EvelinaContext, *, punishment: Punishment):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "bot add", ctx.guild.id)
        if not check:
            args = ["INSERT INTO antinuke_modules VALUES ($1,$2,$3,$4)", ctx.guild.id, "bot add", punishment, None]
        else:
            args = ["UPDATE antinuke_modules SET punishment = $1 WHERE guild_id = $2 AND module = $3", punishment, ctx.guild.id, "bot add"]
        await self.bot.db.execute(*args)
        return await ctx.send_success(f"Enabled **bot add** protection\n> Punishment: **{punishment}**")
    
    @antinuke_botadd.command(name="disable", brief="antinuke admin", description="Disable protection against new bot additions")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_botadd_disable(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM antinuke_modules WHERE module = $1 AND guild_id = $2", "bot add", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Bot add protection is **not** enabled")
        await self.bot.db.execute("DELETE FROM antinuke_modules WHERE guild_id = $1 AND module = $2", ctx.guild.id, "bot add")
        return await ctx.send_success("Disabled **bot add** protection")

    @antinuke.command(name="whitelist", aliases=["wl"], brief="antinuke admin", usage="antinuke whitelist comminate", description="Whitelist a user or role from Antinuke system")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_whitelist(self, ctx: EvelinaContext, *, target: Union[User, Member, Role]):
        whitelisted = await self.bot.db.fetchval("SELECT whitelisted FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        whitelisted_roles = await self.bot.db.fetchval("SELECT whitelisted_roles FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if not whitelisted:
            whitelisted = []
        else:
            whitelisted = json.loads(whitelisted)
        if not whitelisted_roles:
            whitelisted_roles = []
        else:
            whitelisted_roles = json.loads(whitelisted_roles)
        if isinstance(target, Role):
            if target.id in whitelisted_roles:
                return await ctx.send_warning("This role is **already** antinuke whitelisted")
            whitelisted_roles.append(target.id)
            await self.bot.db.execute("UPDATE antinuke SET whitelisted_roles = $1 WHERE guild_id = $2", json.dumps(whitelisted_roles), ctx.guild.id)
            return await ctx.send_success(f"Whitelisted {target.mention} from Antinuke system")
        if target.id in whitelisted:
            return await ctx.send_warning("This member is **already** antinuke whitelisted")
        whitelisted.append(target.id)
        await self.bot.db.execute("UPDATE antinuke SET whitelisted = $1 WHERE guild_id = $2", json.dumps(whitelisted), ctx.guild.id)
        return await ctx.send_success(f"Whitelisted {target.mention} from Antinuke system")
    
    @antinuke.command(name="unwhitelist", aliases=["uwl"], brief="antinuke admin", usage="antinuke unwhitelist comminate", description="Unwhitelist a user or role from Antinuke system")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_unwhitelist(self, ctx: EvelinaContext, *, target: Union[User, Member, Role]):
        whitelisted = await self.bot.db.fetchval("SELECT whitelisted FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        whitelisted_roles = await self.bot.db.fetchval("SELECT whitelisted_roles FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if not whitelisted:
            whitelisted = []
        else:
            whitelisted = json.loads(whitelisted)
        if not whitelisted_roles:
            whitelisted_roles = []
        else:
            whitelisted_roles = json.loads(whitelisted_roles)
        if isinstance(target, Role):
            if target.id not in whitelisted_roles:
                return await ctx.send_warning("This role isn't antinuke whitelisted")
            whitelisted_roles.remove(target.id)
            await self.bot.db.execute("UPDATE antinuke SET whitelisted_roles = $1 WHERE guild_id = $2", json.dumps(whitelisted_roles), ctx.guild.id)
            return await ctx.send_success(f"Unwhitelisted {target.mention} from Antinuke system")
        if target.id not in whitelisted:
            return await ctx.send_warning("This member isn't antinuke whitelisted")
        whitelisted.remove(target.id)
        await self.bot.db.execute("UPDATE antinuke SET whitelisted = $1 WHERE guild_id = $2", json.dumps(whitelisted), ctx.guild.id)
        return await ctx.send_success(f"Unwhitelisted {target.mention} from Antinuke system")
    
    @antinuke.command(name="whitelisted", brief="antinuke admin", description="View AntiNuke whitelisted members & bots on your server")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_whitelisted(self, ctx: EvelinaContext):
        whitelisted = await self.bot.db.fetchval("SELECT whitelisted FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        whitelisted_roles = await self.bot.db.fetchval("SELECT whitelisted_roles FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if not whitelisted and not whitelisted_roles:
            return await ctx.send_warning("There are **no** whitelisted members or roles")
        whitelisted = json.loads(whitelisted) if whitelisted else []
        whitelisted_roles = json.loads(whitelisted_roles) if whitelisted_roles else []
        content = [f"<@!{wl}>" for wl in whitelisted]
        content.extend([f"<@&{wl}>" for wl in whitelisted_roles])
        if not content:
            return await ctx.send_warning("There are **no** whitelisted members or roles")
        return await ctx.paginate(content, f"{ctx.guild.name}'s Antinuke whitelisted members & roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @antinuke.group(name="admin", brief="antinuke owner", description="Manage the members that can change the Antinuke settings", invoke_without_command=True, case_insensitive=True)
    async def antinuke_admin(self, ctx: EvelinaContext):
        return await ctx.create_pages()
        
    @antinuke_admin.command(name="add", brief="antinuke owner", usage="antinuke admin add comminate", description="Give a user permissions to edit Antinuke settings")
    @antinuke_configured()
    @antinuke_owner()
    async def antinuke_admin_add(self, ctx: EvelinaContext, *, member: Member):
        if member == ctx.author:
            return await ctx.send("You are the antinuke owner yourself lol")
        if member.bot:
            return await ctx.send("Why would a bot be an antinuke admin? They can't manage the settings anyways -_-")
        admins = await self.bot.db.fetchval("SELECT admins FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if admins:
            admins = json.loads(admins)
            if member.id in admins:
                return await ctx.send_warning("This member is **already** an antinuke admin")
            admins.append(member.id)
        else:
            admins = [member.id]
        await self.bot.db.execute("UPDATE antinuke SET admins = $1 WHERE guild_id = $2", json.dumps(admins), ctx.guild.id)
        return await ctx.send_success(f"Added {member.mention} as an antinuke admin")
    
    @antinuke_admin.command(name="remove", brief="antinuke owner", usage="antinuke admin remove comminate", description="Remove a user permissions to edit Antinuke settings")
    @antinuke_configured()
    @antinuke_owner()
    async def antinuke_admin_remove(self, ctx: EvelinaContext, *, member: Member):
        admins = await self.bot.db.fetchval("SELECT admins FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if admins:
            admins = json.loads(admins)
            if not member.id in admins:
                return await ctx.send_warning("This member isn't an antinuke admin")
            admins.remove(member.id)
            await self.bot.db.execute("UPDATE antinuke SET admins = $1 WHERE guild_id = $2", json.dumps(admins), ctx.guild.id)
            return await ctx.send_success(f"Removed {member.mention} from the antinuke admins")
        return await ctx.send_warning("There is **no** antinuke admin")
    
    @antinuke_admin.command(name="list", brief="antinuke admin", description="View Antinuke admins on your server")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_admin_list(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT owner_id, admins FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        content = [f"<@!{check['owner_id']}> {emojis.CROWN}"]
        admins = json.loads(check["admins"]) if check["admins"] else []
        content.extend([f"<@!{wl}>" for wl in admins])
        await ctx.paginate(content, f"Antinuke admins", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @antinuke.group(name="staff", brief="antinuke owner", description="Manage the roles that are marked as staff", invoke_without_command=True, case_insensitive=True)
    async def antinuke_staff(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @antinuke_staff.command(name="add", brief="antinuke owner", usage="antinuke staff add Moderator", description="Add a role as staff role")
    @antinuke_configured()
    @antinuke_owner()
    async def antinuke_staff_add(self, ctx: EvelinaContext, *, role: Role):
        if role.managed:
            return await ctx.send("Managed roles cannot be set as staff role")
        staffs = await self.bot.db.fetchval("SELECT staffs FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if staffs:
            staffs = json.loads(staffs)
            if role.id in staffs:
                return await ctx.send_warning("This role is **already** set as staff role")
            staffs.append(role.id)
        else:
            staffs = [role.id]
        await self.bot.db.execute("UPDATE antinuke SET staffs = $1 WHERE guild_id = $2", json.dumps(staffs), ctx.guild.id)
        return await ctx.send_success(f"Added {role.mention} as staff role")

    @antinuke_staff.command(name="remove", brief="antinuke owner", usage="antinuke staff remove Moderator", description="Remove a role as staff role")
    @antinuke_configured()
    @antinuke_owner()
    async def antinuke_staff_remove(self, ctx: EvelinaContext, *, role: Union[Role, int]):
        role_id = self.bot.misc.convert_role(role)
        staffs = await self.bot.db.fetchval("SELECT staffs FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if staffs:
            staffs = json.loads(staffs)
            if role_id not in staffs:
                return await ctx.send_warning("This role isn't set as staff role")
            staffs.remove(role_id)
            await self.bot.db.execute("UPDATE antinuke SET staffs = $1 WHERE guild_id = $2", json.dumps(staffs), ctx.guild.id)
            return await ctx.send_success(f"Removed {self.bot.misc.humanize_role(ctx.guild, role_id)} as staff role")
        return await ctx.send_warning("There are **no** staff role")

    @antinuke_staff.command(name="list", brief="antinuke admin", description="View all staff roles")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_staff_list(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT staffs FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        content = []
        staffs = json.loads(check["staffs"]) if check["staffs"] else []
        content.extend([f"<@&{role_id}>" for role_id in staffs])
        if not content:
            return await ctx.send_warning("There are **no** staff roles")
        await ctx.paginate(content, f"Antinuke Staff roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        
    @antinuke.command(name="restore", brief="antinuke admin", description="Restore roles after an antinuke punishment")
    @antinuke_configured()
    @admin_antinuke()
    async def antinuke_restore(self, ctx: EvelinaContext, *, member: NoStaff):
        """Give a member their roles back after an antinuke punishment"""
        async with self.locks[ctx.guild.id]:
            check = await self.bot.db.fetchrow("SELECT roles FROM restore_antinuke WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
            if not check:
                return await ctx.send_warning("This member doesn't have any roles saved.")
        roles = [ctx.guild.get_role(r) for r in json.loads(check["roles"]) if ctx.guild.get_role(r)]
        assignable_roles = [role for role in roles if role.is_assignable() and role.position < ctx.author.top_role.position and role.position < ctx.guild.me.top_role.position]
        if not assignable_roles:
            return await ctx.send_warning("No assignable roles were found to restore. Make sure your role hierarchy allows this.")
        restored_roles = []
        for role in assignable_roles:
            try:
                await member.add_roles(role, reason=f"Dangerous roles restored by {ctx.author}")
                restored_roles.append(role.mention)
            except Forbidden:
                return await ctx.send_warning(f"I don't have permission to assign the role: {role.mention}")
        if restored_roles:
            await ctx.send_success(f"Successfully restored the following roles for {member.mention}: {', '.join(restored_roles)}.")
        else:
            await ctx.send_warning("No roles were restored due to permission issues or hierarchy conflicts")
        await self.bot.db.execute("DELETE FROM restore_antinuke WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Antinuke(bot))