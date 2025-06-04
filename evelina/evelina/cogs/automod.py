import json

from typing import Union
from datetime import timedelta

from discord import AutoModTrigger, AutoModRuleTriggerType, AutoModRuleAction, AutoModRuleEventType, TextChannel, Interaction, Embed, User, Role, CategoryChannel
from discord.ext.commands import Cog, group, has_guild_permissions

from modules.styles import emojis, colors
from modules.helpers import EvelinaContext
from modules.evelinabot import Evelina
from modules.converters import RoleConverter
from modules.validators import ValidTime
from modules.predicates import antispam_enabled, antirepeat_enabled

class Automod(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="automod", brief="manage guild", case_insensitive=True, invoke_without_command=True)
    @has_guild_permissions(manage_guild=True)
    async def automod(self, ctx: EvelinaContext):
        """Manage automod settings for your server"""
        return await ctx.create_pages()
        
    @automod.group(name="invites", aliases=["invite"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def automod_invites(self, ctx: EvelinaContext):
        """Prevent members from sending invite links"""
        return await ctx.create_pages()
    
    @automod_invites.command(name="enable", aliases=["on"], brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_enable(self, ctx: EvelinaContext):
        """Enable protection against invite links"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if check:
            return await ctx.send_warning("Automod **invites** is already enabled.")
        existing_rules = await ctx.guild.fetch_automod_rules()
        keyword_rules = [rule for rule in existing_rules if rule.trigger.type.value == 1]
        if len(keyword_rules) >= 6:
            return await ctx.send_warning(
                "Discord only allows a maximum of 6 keyword filter rules per server. You've reached this limit.\n"
                "You need to delete an existing rule before adding a new one using `automod delete <rule_id>`."
            )
        trigger = AutoModTrigger(type=AutoModRuleTriggerType.keyword, regex_patterns=[r"(https?://)?(www.)?(discord.(gg|io|me|li)|discordapp.com/invite|discord.com/invite)/.+[a-z]"])
        try:
            mod = await ctx.guild.create_automod_rule(name=f"{self.bot.user.name}-antiinvite", event_type=AutoModRuleEventType.message_send, trigger=trigger, enabled=True, actions=[AutoModRuleAction(custom_message=f"Message blocked by {self.bot.user.name} for containing an invite link")], reason=f"Automod invites filter rule created by {ctx.author}")
            await self.bot.db.execute("INSERT INTO automod_rules (guild_id, rule_id, mode) VALUES ($1, $2, $3)", ctx.guild.id, mod.id, "invites")
            return await ctx.send_success("Automod **invites** has been enabled.")
        except Exception as e:
            return await ctx.send_warning(f"Failed to create automod rule:\n```{e}```")
    
    @automod_invites.command(name="disable", aliases=["off"], brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_disable(self, ctx: EvelinaContext):
        """Disable the invites filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if not check:
            return await ctx.send_warning("Automod **invites** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        try:
            await mod.delete(reason=f"Automod invites filter rule deleted by {ctx.author}")
        except Exception:
            pass
        await self.bot.db.execute("DELETE FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        return await ctx.send_success("Automod **invites** has been disabled.")
    
    @automod_invites.command(name="timeout", brief="manage guild", usage="automod invites timeout 1d")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_timeout(self, ctx: EvelinaContext, time: ValidTime):
        """Change timeout duration for members who send invite links"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if not check:
            return await ctx.send_warning("Automod **invites** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if time == 0:
            timeout_duration = None
        else:
            timeout_duration = timedelta(seconds=time)
        try:
            await mod.edit(actions=[AutoModRuleAction(duration=timeout_duration)], reason=f"Invites filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success(f"Invites filter timeout has been set to {self.bot.misc.humanize_time(time)}.")

    @automod_invites.command(name="message", aliases=["msg"], brief="manage guild", usage="automod invites message You are not allowed to send invite links here.")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_message(self, ctx: EvelinaContext, *, message: str):
        """Set a custom message for invites filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if not check:
            return await ctx.send_warning("Automod **invites** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        try:
            await mod.edit(actions=[AutoModRuleAction(custom_message=message)], reason=f"Invites filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success("Invites filter message has been updated.")
    
    @automod_invites.command(name="logs", brief="manage guild", usage="automod invites logs #logs")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_logs(self, ctx: EvelinaContext, channel: TextChannel):
        """Set the channel where logs will be sent for invites filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if not check:
            return await ctx.send_warning("Automod **invites** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        try:
            await mod.edit(actions=[AutoModRuleAction(channel_id=channel.id)], reason=f"Invites filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success(f"Invites filter logs channel has been set to {channel.mention}.")

    @automod_invites.group(name="ignore", aliases=["exempt"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_ignore(self, ctx: EvelinaContext):
        """Manage ignored channels and roles for invites filter"""
        return await ctx.create_pages()
    
    @automod_invites_ignore.command(name="add", brief="manage guild", usage="automod invites ignore add #channel")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_ignore_add(self, ctx: EvelinaContext, target: Union[TextChannel, CategoryChannel, Role]):
        """Add a user, role or channel to the antispam whitelist"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if not check:
            return await ctx.send_warning("Automod **invites** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if isinstance(target, Role):
            if target.id in mod.exempt_role_ids:
                return await ctx.send_warning(f"{target.mention} is **already** ignored.")
            roles = mod.exempt_roles
            roles.append(target)
            try:
                await mod.edit(exempt_roles=roles, reason=f"Invites filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is now ignored.")
        elif isinstance(target, (TextChannel, CategoryChannel)):
            if target.id in mod.exempt_channel_ids:
                return await ctx.send_warning(f"{target.mention} is **already** ignored.")
            channels = mod.exempt_channels
            channels.append(target)
            try:
                await mod.edit(exempt_channels=channels, reason=f"Invites filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is now ignored.")
        
    @automod_invites_ignore.command(name="remove", brief="manage guild", usage="automod invites ignore remove #channel")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_ignore_remove(self, ctx: EvelinaContext, target: Union[TextChannel, CategoryChannel, Role]):
        """Remove ignored users, channels and roles for invites filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if not check:
            return await ctx.send_warning("Automod **invites** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if isinstance(target, Role):
            if target.id not in mod.exempt_role_ids:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            roles = mod.exempt_roles
            roles.remove(target)
            try:
                await mod.edit(exempt_roles=roles, reason=f"Invites filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        elif isinstance(target, (TextChannel, CategoryChannel)):
            if target.id not in mod.exempt_channel_ids:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            channels = mod.exempt_channels
            channels.remove(target)
            try:
                await mod.edit(exempt_channels=channels, reason=f"Invites filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        
    @automod_invites_ignore.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_invites_ignore_list(self, ctx: EvelinaContext):
        """List ignored users, channels and roles for invites filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "invites")
        if not check:
            return await ctx.send_warning("Automod **invites** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        channels = [f"{channel.mention} (`{channel.id}`) - [Text Channel]" for channel in mod.exempt_channels] if mod.exempt_channels else []
        roles = [f"{role.mention} (`{role.id}`) - [Role]" for role in mod.exempt_roles] if mod.exempt_roles else []
        if not channels and not roles:
            return await ctx.send_warning("No ignored channels or roles found.")
        content = channels + roles
        return await ctx.paginate(content, f"{ctx.guild.name}'s Ignored Invites", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @automod.group(name="words", aliases=["word"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def automod_words(self, ctx: EvelinaContext):
        """Prevent members from using blacklisted words"""
        return await ctx.create_pages()
    
    @automod_words.command(name="enable", aliases=["on"], brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_enable(self, ctx: EvelinaContext):
        """Enable protection against blacklisted words"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if check:
            return await ctx.send_warning("Automod **words** is already enabled.")
        existing_rules = await ctx.guild.fetch_automod_rules()
        keyword_rules = [rule for rule in existing_rules if rule.trigger.type.value == 1]  # 1 = keyword filter
        if len(keyword_rules) >= 6:
            return await ctx.send_warning(
                "Discord only allows a maximum of 6 keyword filter rules per server. You've reached this limit.\n"
                "You need to delete an existing rule before adding a new one using `automod delete <rule_id>`."
            )
        trigger = AutoModTrigger(type=AutoModRuleTriggerType.keyword)
        try:
            mod = await ctx.guild.create_automod_rule(name=f"{self.bot.user.name}-antiwords", event_type=AutoModRuleEventType.message_send, trigger=trigger, enabled=True, actions=[AutoModRuleAction(custom_message=f"Message blocked by {self.bot.user.name} for containing a blacklisted word")], reason=f"Automod words filter rule created by {ctx.author}")
            await self.bot.db.execute("INSERT INTO automod_rules (guild_id, rule_id, mode) VALUES ($1, $2, $3)", ctx.guild.id, mod.id, "words")
            return await ctx.send_success("Automod **words** has been enabled.")
        except Exception as e:
            return await ctx.send_warning(f"Failed to create automod rule:\n```{e}```")
    
    @automod_words.command(name="disable", aliases=["off"], brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_disable(self, ctx: EvelinaContext):
        """Disable the words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        try:
            await mod.delete(reason=f"Automod words filter rule deleted by {ctx.author}")
        except Exception:
            pass
        await self.bot.db.execute("DELETE FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        return await ctx.send_success("Automod **words** has been disabled.")
    
    @automod_words.command(name="timeout", brief="manage guild", usage="automod words timeout 1d")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_timeout(self, ctx: EvelinaContext, time: ValidTime):
        """Change timeout duration for members who spam messages"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if time == 0:
            timeout_duration = None
        else:
            timeout_duration = timedelta(seconds=time)
        try:
            await mod.edit(actions=[AutoModRuleAction(duration=timeout_duration)], reason=f"Words filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success(f"Words filter timeout has been set to {self.bot.misc.humanize_time(time)}.")
    
    @automod_words.command(name="message", aliases=["msg"], brief="manage guild", usage="automod words message You are not allowed to use blacklisted words here.")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_message(self, ctx: EvelinaContext, *, message: str):
        """Set a custom message for words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        try:
            await mod.edit(actions=[AutoModRuleAction(custom_message=message)], reason=f"Words filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success("Words filter message has been updated.")
    
    @automod_words.command(name="logs", brief="manage guild", usage="automod words logs #logs")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_logs(self, ctx: EvelinaContext, channel: TextChannel):
        """Set the channel where logs will be sent for words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        try:
            await mod.edit(actions=[AutoModRuleAction(channel_id=channel.id)], reason=f"Words filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success(f"Words filter logs channel has been set to {channel.mention}.")
    
    @automod_words.command(name="add", brief="manage guild", usage="automod words add word")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_add(self, ctx: EvelinaContext, *, word: str):
        """Add a blacklisted word to the words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if len(word) > 60:
            return await ctx.send_warning("Word must be less than 60 characters.")
        filters = mod.trigger.keyword_filter
        if "*" + word + "*" in filters:
            return await ctx.send_warning(f"Word `{word}` is already blacklisted.")
        filters.append("*" + word + "*")
        try:
            await mod.edit(trigger=AutoModTrigger(type=AutoModRuleTriggerType.keyword, keyword_filter=filters), reason=f"Words filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success(f"Word `{word}` has been blacklisted.")
    
    @automod_words.command(name="remove", brief="manage guild", usage="automod words remove word")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_remove(self, ctx: EvelinaContext, *, word: str):
        """Remove a blacklisted word from the words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        filters = mod.trigger.keyword_filter
        if "*" + word + "*" not in filters:
            return await ctx.send_warning(f"Word `{word}` is not blacklisted.")
        filters.remove("*" + word + "*")
        try:
            await mod.edit(trigger=AutoModTrigger(type=AutoModRuleTriggerType.keyword, keyword_filter=filters), reason=f"Words filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success(f"Word `{word}` has been removed from blacklist.")

    @automod_words.command(name="clear", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_clear(self, ctx: EvelinaContext):
        """Clear all blacklisted words for words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        filters = mod.trigger.keyword_filter
        if not filters:
            return await ctx.send_warning("No blacklisted words found.")
        try:
            await mod.edit(trigger=AutoModTrigger(type=AutoModRuleTriggerType.keyword), reason=f"Words filter rule edited by {ctx.author}")
        except Exception:
            return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
        return await ctx.send_success("All blacklisted words have been cleared.")

    @automod_words.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_list(self, ctx: EvelinaContext):
        """List blacklisted words for words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if not mod.trigger.keyword_filter:
            return await ctx.send_warning("No blacklisted words found.")
        return await ctx.paginate(mod.trigger.keyword_filter, f"{ctx.guild.name}'s Blacklisted Words", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @automod_words.group(name="ignore", aliases=["exempt"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def automod_words_ignore(self, ctx: EvelinaContext):
        """Manage ignored channels and roles for words filter"""
        return await ctx.create_pages()

    @automod_words_ignore.command(name="add", brief="manage guild", usage="automod ignore add #channel")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_ignore_add(self, ctx: EvelinaContext, target: Union[TextChannel, CategoryChannel, Role]):
        """Add a user, role or channel to the antispam whitelist"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if isinstance(target, Role):
            if target.id in mod.exempt_role_ids:
                return await ctx.send_warning(f"{target.mention} is **already** ignored.")
            roles = mod.exempt_roles
            roles.append(target)
            try:
                await mod.edit(exempt_roles=roles, reason=f"Words filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is now ignored.")
        elif isinstance(target, (TextChannel, CategoryChannel)):
            if target.id in mod.exempt_channel_ids:
                return await ctx.send_warning(f"{target.mention} is **already** ignored.")
            channels = mod.exempt_channels
            channels.append(target)
            try:
                await mod.edit(exempt_channels=channels, reason=f"Words filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is now ignored.")
        
    @automod_words_ignore.command(name="remove", brief="manage guild", usage="automod ignore remove #channel")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_ignore_remove(self, ctx: EvelinaContext, target: Union[TextChannel, CategoryChannel, Role]):
        """Remove ignored users, channels and roles for antispam"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        if isinstance(target, Role):
            if target.id not in mod.exempt_role_ids:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            roles = mod.exempt_roles
            roles.remove(target)
            try:
                await mod.edit(exempt_roles=roles, reason=f"Words filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        elif isinstance(target, (TextChannel, CategoryChannel)):
            if target.id not in mod.exempt_channel_ids:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            channels = mod.exempt_channels
            channels.remove(target)
            try:
                await mod.edit(exempt_channels=channels, reason=f"Words filter rule edited by {ctx.author}")
            except Exception:
                return await ctx.send_warning("Unable to edit automod rule, please resetup the automod.")
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        
    @automod_words_ignore.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_words_ignore_list(self, ctx: EvelinaContext):
        """List ignored users, channels and roles for words filter"""
        check = await self.bot.db.fetchrow("SELECT rule_id FROM automod_rules WHERE guild_id = $1 AND mode = $2", ctx.guild.id, "words")
        if not check:
            return await ctx.send_warning("Automod **words** is not enabled.")
        try:
            mod = await ctx.guild.fetch_automod_rule(check["rule_id"])
        except Exception:
            return await ctx.send_warning("Unable to fetch automod rule, please resetup the automod.")
        channels = [f"{channel.mention} (`{channel.id}`) - [Text Channel]" for channel in mod.exempt_channels] if mod.exempt_channels else []
        roles = [f"{role.mention} (`{role.id}`) - [Role]" for role in mod.exempt_roles] if mod.exempt_roles else []
        if not channels and not roles:
            return await ctx.send_warning("No ignored channels or roles found.")
        content = channels + roles
        return await ctx.paginate(content, f"{ctx.guild.name}'s Ignored Words", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @automod.group(name="spam", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    async def automod_spam(self, ctx: EvelinaContext):
        """Prevent members from spamming messages"""
        return await ctx.create_pages()

    @automod_spam.command(name="enable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_spam_enable(self, ctx: EvelinaContext):
        """Enable protection against message spamming"""
        if not await self.bot.db.fetchrow("SELECT * FROM automod_spam WHERE guild_id = $1", ctx.guild.id):
            await self.bot.db.execute("INSERT INTO automod_spam (guild_id, rate, timeout) VALUES ($1,$2,$3)", ctx.guild.id, 8, 120)
            return await ctx.send_success("Antispam is **now** enabled\n> Rate: **8** messages in **10 seconds** Punishment: **2 minutes** timeout")
        return await ctx.send_warning("Antispam is **already** enabled")
        
    @automod_spam.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_disable(self, ctx: EvelinaContext):
        """Disable protection against message spamming"""
        async def yes_func(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Disabled the Antispam system"), view=None)
        async def no_func(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Antispam deactivation got canceled"), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** the Antispam?", yes_func, no_func)
    
    @automod_spam.command(name="rate", brief="manage guild", usage="automod spam rate 5")
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_rate(self, ctx: EvelinaContext, rate: int):
        """Change rate at which members can sending messages in 10 seconds before triggering anti-spam protection"""
        if rate < 2:
            return await ctx.send_warning("The rate can't be lower than **2**")
        await self.bot.db.execute("UPDATE automod_spam SET rate = $1 WHERE guild_id = $2", rate, ctx.guild.id)
        return await ctx.send_success(f"Changed spam rate to **{rate}** messages per **10** seconds")

    @automod_spam.command(name='timeout', brief="manage guild", usage="automod spam timeout 1h")
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_timeout(self, ctx: EvelinaContext, time: ValidTime):
        """Change timeout duration for members who spam messages"""
        await self.bot.db.execute("UPDATE automod_spam SET timeout = $1 WHERE guild_id = $2", time, ctx.guild.id)
        return await ctx.send_success(f"Changed timeout punishment to **{self.bot.misc.humanize_time(time)}**")
    
    @automod_spam.command(name="message", brief="manage guild", usage="automod spam message on")
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_message(self, ctx: EvelinaContext, option: str):
        """Enable or disable the antispam punishment message"""
        if option.lower() == "on":
            await self.bot.db.execute("UPDATE automod_spam SET message = $1 WHERE guild_id = $2", True, ctx.guild.id)
            return await ctx.send_success(f"Enabled punishment message for antispam system")
        elif option.lower() == "off":
            await self.bot.db.execute("UPDATE automod_spam SET message = $1 WHERE guild_id = $2", False, ctx.guild.id)
            return await ctx.send_success(f"Disabled punishment message for antispam system")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
        
    @automod_spam.group(name="ignore", aliases=["exempt"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_ignore(self, ctx: EvelinaContext):
        """Manage ignored channels and roles for antispam"""
        return await ctx.create_pages()
    
    @automod_spam_ignore.command(name="add", brief="manage guild", usage="automod spam ignore add #channel")
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_ignore_add(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Add a user, role or channel to the antispam whitelist"""
        if isinstance(target, User):
            check = await self.bot.db.fetchval("SELECT users FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **already** ignored.")
                check.append(target.id)
            else:
                check = [target.id]
            await self.bot.db.execute("UPDATE automod_spam SET users = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is now ignored.")
        elif isinstance(target, TextChannel):
            check = await self.bot.db.fetchval("SELECT channels FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **already** ignored.")
                check.append(target.id)
            else:
                check = [target.id]
            await self.bot.db.execute("UPDATE automod_spam SET channels = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is now ignored.")
        elif isinstance(target, Role):
            check = await self.bot.db.fetchval("SELECT roles FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if target.id in check:
                    return await ctx.send_warning(f"This role is **already** Antispam whitelisted")
                check.append(target.id)
            else:
                check = [target.id]
            await self.bot.db.execute("UPDATE automod_spam SET roles = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is now ignored.")
        else:
            return await ctx.send_warning("Invalid target. Valid targets are: `User`, `Role` & `TextChannel`")
        
    @automod_spam_ignore.command(name="remove", brief="manage guild", usage="automod spam ignore remove #channel")
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_ignore_remove(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Remove ignored users, channels and roles for antispam"""
        if isinstance(target, User):
            check = await self.bot.db.fetchval("SELECT users FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if not target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **not** ignored.")
                check.remove(target.id)
            else:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            await self.bot.db.execute("UPDATE automod_spam SET users = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        elif isinstance(target, TextChannel):
            check = await self.bot.db.fetchval("SELECT channels FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if not target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **not** ignored.")
                check.remove(target.id)
            else:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            await self.bot.db.execute("UPDATE automod_spam SET channels = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        elif isinstance(target, Role):
            check = await self.bot.db.fetchval("SELECT roles FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if not target.id in check:
                    return await ctx.send_warning(f"This role is **not** Antispam whitelisted")
                check.remove(target.id)
            else:
                return await ctx.send_warning(f"This role is **not** Antispam whitelisted")
            await self.bot.db.execute("UPDATE automod_spam SET roles = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        else:
            return await ctx.send_warning("Invalid target. Valid targets are: `User`, `Role` & `TextChannel`")
        
    @automod_spam_ignore.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @antispam_enabled()
    async def automod_spam_ignore_list(self, ctx: EvelinaContext):
        """List ignored users, channels and roles for antispam"""
        users = await self.bot.db.fetchval("SELECT users FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
        channels = await self.bot.db.fetchval("SELECT channels FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
        roles = await self.bot.db.fetchval("SELECT roles FROM automod_spam WHERE guild_id = $1", ctx.guild.id)
        users = json.loads(users) if users else []
        channels = json.loads(channels) if channels else []
        roles = json.loads(roles) if roles else []
        content = [f"<@{user}> (`{user}`) - [User]" for user in users] + [f"<#{channel}> (`{channel}`) - [Text Channel]" for channel in channels] + [f"<@&{role}> (`{role}`) - [Role]" for role in roles]
        if not content:
            return await ctx.send_warning("No ignored users, channels or roles found.")
        return await ctx.paginate(content, f"{ctx.guild.name}'s Ignored Antispam", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @automod.group(name="repeat", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def automod_repeat(self, ctx: EvelinaContext):
        """Prevent members from repeating messages"""
        return await ctx.create_pages()
    
    @automod_repeat.command(name="enable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def automod_repeat_enable(self, ctx: EvelinaContext):
        """Enable protection against message repeating"""
        if not await self.bot.db.fetchrow("SELECT * FROM automod_repeat WHERE guild_id = $1", ctx.guild.id):
            await self.bot.db.execute("INSERT INTO automod_repeat (guild_id, rate, timeout) VALUES ($1,$2,$3)", ctx.guild.id, 5, 120)
            return await ctx.send_success("Antirepeat is **now** enabled\n> Rate: **5** messages in **10 seconds** Punishment: **2 minutes** timeout")
        return await ctx.send_warning("Antirepeat is **already** enabled")
    
    @automod_repeat.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()
    async def automod_repeat_disable(self, ctx: EvelinaContext):
        """Disable protection against message repeating"""
        async def yes_func(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Disabled the Antirepeat system"), view=None)
        async def no_func(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Antirepeat deactivation got canceled"), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** the Antirepeat?", yes_func, no_func)
    
    @automod_repeat.command(name="rate", brief="manage guild", usage="automod repeat rate 5")
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()   
    async def automod_repeat_rate(self, ctx: EvelinaContext, rate: int):
        """Change rate at which members can sending messages in 10 seconds before triggering anti-repeat protection"""
        if rate < 2:
            return await ctx.send_warning("The rate can't be lower than **2**")
        await self.bot.db.execute("UPDATE automod_repeat SET rate = $1 WHERE guild_id = $2", rate, ctx.guild.id)
        return await ctx.send_success(f"Changed repeat rate to **{rate}** messages per **10** seconds")
    
    @automod_repeat.command(name='timeout', brief="manage guild", usage="automod repeat timeout 1h")
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()
    async def automod_repeat_timeout(self, ctx: EvelinaContext, time: ValidTime):
        """Change timeout duration for members who repeat messages"""
        await self.bot.db.execute("UPDATE automod_repeat SET timeout = $1 WHERE guild_id = $2", time, ctx.guild.id)
        return await ctx.send_success(f"Changed timeout punishment to **{self.bot.misc.humanize_time(time)}**")
    
    @automod_repeat.command(name="message", brief="manage guild", usage="automod repeat message on")
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()
    async def automod_repeat_message(self, ctx: EvelinaContext, option: str):
        """Enable or disable the antirepeat punishment message"""
        if option.lower() == "on":
            await self.bot.db.execute("UPDATE automod_repeat SET message = $1 WHERE guild_id = $2", True, ctx.guild.id)
            return await ctx.send_success(f"Enabled punishment message for antirepeat system")
        elif option.lower() == "off":
            await self.bot.db.execute("UPDATE automod_repeat SET message = $1 WHERE guild_id = $2", False, ctx.guild.id)
            return await ctx.send_success(f"Disabled punishment message for antirepeat system")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
        
    @automod_repeat.group(name="ignore", aliases=["exempt"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()
    async def automod_repeat_ignore(self, ctx: EvelinaContext):
        """Manage ignored channels and roles for antirepeat"""
        return await ctx.create_pages()
    
    @automod_repeat_ignore.command(name="add", brief="manage guild", usage="automod repeat ignore add #channel")
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()
    async def automod_repeat_ignore_add(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Add a user, role or channel to the antirepeat whitelist"""
        if isinstance(target, User):
            check = await self.bot.db.fetchval("SELECT users FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **already** ignored.")
                check.append(target.id)
            else:
                check = [target.id]
            await self.bot.db.execute("UPDATE automod_repeat SET users = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is now ignored.")
        elif isinstance(target, TextChannel):
            check = await self.bot.db.fetchval("SELECT channels FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **already** ignored.")
                check.append(target.id)
            else:
                check = [target.id]
            await self.bot.db.execute("UPDATE automod_repeat SET channels = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is now ignored.")
        elif isinstance(target, Role):
            check = await self.bot.db.fetchval("SELECT roles FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if target.id in check:
                    return await ctx.send_warning(f"This role is **already** Antirepeat whitelisted")
                check.append(target.id)
            else:
                check = [target.id]
            await self.bot.db.execute("UPDATE automod_repeat SET roles = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is now ignored.")
        else:
            return await ctx.send_warning("Invalid target. Valid targets are: `User`, `Role` & `TextChannel`")
        
    @automod_repeat_ignore.command(name="remove", brief="manage guild", usage="automod repeat ignore remove #channel")
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()
    async def automod_repeat_ignore_remove(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Remove a user, role or channel from the antirepeat whitelist"""
        if isinstance(target, User):
            check = await self.bot.db.fetchval("SELECT users FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if not target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **not** ignored.")
                check.remove(target.id)
            else:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            await self.bot.db.execute("UPDATE automod_repeat SET users = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        elif isinstance(target, TextChannel):
            check = await self.bot.db.fetchval("SELECT channels FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if not target.id in check:
                    return await ctx.send_warning(f"{target.mention} is **not** ignored.")
                check.remove(target.id)
            else:
                return await ctx.send_warning(f"{target.mention} is **not** ignored.")
            await self.bot.db.execute("UPDATE automod_repeat SET channels = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        elif isinstance(target, Role):
            check = await self.bot.db.fetchval("SELECT roles FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
            if check:
                check = json.loads(check)
                if not target.id in check:
                    return await ctx.send_warning(f"This role is **not** Antirepeat whitelisted")
                check.remove(target.id)
            else:
                return await ctx.send_warning(f"This role is **not** Antirepeat whitelisted")
            await self.bot.db.execute("UPDATE automod_repeat SET roles = $1 WHERE guild_id = $2", json.dumps(check), ctx.guild.id)
            return await ctx.send_success(f"{target.mention} is no longer ignored.")
        else:
            return await ctx.send_warning("Invalid target. Valid targets are: `User`, `Role` & `TextChannel`")
        
    @automod_repeat_ignore.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @antirepeat_enabled()
    async def automod_repeat_ignore_list(self, ctx: EvelinaContext):
        """List all ignored users, channels and roles for antirepeat"""
        users = await self.bot.db.fetchval("SELECT users FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
        channels = await self.bot.db.fetchval("SELECT channels FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
        roles = await self.bot.db.fetchval("SELECT roles FROM automod_repeat WHERE guild_id = $1", ctx.guild.id)
        users = json.loads(users) if users else []
        channels = json.loads(channels) if channels else []
        roles = json.loads(roles) if roles else []
        content = [f"<@{user}> (`{user}`) - [User]" for user in users] + [f"<#{channel}> (`{channel}`) - [Text Channel]" for channel in channels] + [f"<@&{role}> (`{role}`) - [Role]" for role in roles]
        if not content:
            return await ctx.send_warning("No ignored users, channels or roles found.")
        return await ctx.paginate(content, f"{ctx.guild.name}'s Ignored Antirepeat", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Automod(bot))