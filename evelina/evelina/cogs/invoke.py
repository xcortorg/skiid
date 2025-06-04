from typing import Union

from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext

from discord import Member, User
from discord.ext.commands import Cog, group, has_guild_permissions

class Invoke(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Invoke commands"

    def invoke_replacement(self, member: Union[Member, User], params: str = None):
        if params is None:
            return None
        if "{member.id}" in params:
            params = params.replace("{member.id}", str(member.id))
        if "{member.name}" in params:
            params = params.replace("{member.name}", member.name)
        if "{member.nick}" in params:
            params = params.replace("{member.nick}", member.nick or member.display_name)
        if "{member.display}" in params:
            params = params.replace("{member.display}", member.display_name)
        if "{member.mention}" in params:
            params = params.replace("{member.mention}", member.mention)
        if "{member.discriminator}" in params:
            params = params.replace("{member.discriminator}", member.discriminator)
        if "{member.avatar}" in params:
            params = params.replace("{member.avatar}", member.avatar.url)
        return params

    @group(name="invoke", invoke_without_command=True, case_insensitive=True)
    async def invoke(self, ctx: EvelinaContext):
        """Change punishment messages for DM or command response"""
        return await ctx.create_pages()

    @invoke.group(name="message", invoke_without_command=True, case_insensitive=True)
    async def invoke_message(self, ctx: EvelinaContext):
        """Change punishment messages for command response"""
        return await ctx.create_pages()

    @invoke_message.group(name="ban", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_ban(self, ctx: EvelinaContext):
        """Change ban message for command response"""
        return await ctx.create_pages()

    @invoke_message_ban.command(name="add", brief="manage guild", usage="invoke message ban add Banned, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_ban_add(self, ctx: EvelinaContext, *, code: str):
        """Add ban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "ban")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "ban", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        
    @invoke_message_ban.command(name="remove", brief="manage guild", usage="invoke message ban remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_ban_remove(self, ctx: EvelinaContext):
        """Remove ban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_ban.command(name="view", brief="manage guild", usage="invoke message ban view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_ban_view(self, ctx: EvelinaContext):
        """View ban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_ban.command(name="test", brief="manage guild", usage="invoke message ban test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_ban_test(self, ctx: EvelinaContext):
        """Test ban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            member = ctx.author
            reason = "test"
            time = "1 hour"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason).replace("{duration}", time).replace("{time}", time)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message.group(name="unban", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unban(self, ctx: EvelinaContext):
        """Change unban message for command response"""
        return await ctx.create_pages()

    @invoke_message_unban.command(name="add", brief="manage guild", usage="invoke message unban add Unbanned, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unban_add(self, ctx: EvelinaContext, *, code: str):
        """Add unban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "unban")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "unban", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
    
    @invoke_message_unban.command(name="remove", brief="manage guild", usage="invoke message unban remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unban_remove(self, ctx: EvelinaContext):
        """Remove unban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_unban.command(name="view", brief="manage guild", usage="invoke message unban view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unban_view(self, ctx: EvelinaContext):
        """View unban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_unban.command(name="test", brief="manage guild", usage="invoke message unban test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unban_test(self, ctx: EvelinaContext):
        """Test unban message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message.group(name="kick", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_kick(self, ctx: EvelinaContext):
        """Change kick message for command response"""
        return await ctx.create_pages()

    @invoke_message_kick.command(name="add", brief="manage guild", usage="invoke message kick add Kicked, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_kick_add(self, ctx: EvelinaContext, *, code: str):
        """Add kick message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "kick")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "kick", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        
    @invoke_message_kick.command(name="remove", brief="manage guild", usage="invoke message kick remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_kick_remove(self, ctx: EvelinaContext):
        """Remove kick message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_kick.command(name="view", brief="manage guild", usage="invoke message kick view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_kick_view(self, ctx: EvelinaContext):
        """View kick message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_kick.command(name="test", brief="manage guild", usage="invoke message kick test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_kick_test(self, ctx: EvelinaContext):
        """Test kick message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message.group(name="mute", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_mute(self, ctx: EvelinaContext):
        """Change mute message for command response"""
        return await ctx.create_pages()

    @invoke_message_mute.command(name="add", brief="manage guild", usage="invoke message mute add Muted, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_mute_add(self, ctx: EvelinaContext, *, code: str):
        """Add mute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "mute")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "mute", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        
    @invoke_message_mute.command(name="remove", brief="manage guild", usage="invoke message mute remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_mute_remove(self, ctx: EvelinaContext):
        """Remove mute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
    
    @invoke_message_mute.command(name="view", brief="manage guild", usage="invoke message mute view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_mute_view(self, ctx: EvelinaContext):
        """View mute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
    
    @invoke_message_mute.command(name="test", brief="manage guild", usage="invoke message mute test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_mute_test(self, ctx: EvelinaContext):
        """Test mute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            member = ctx.author
            reason = "test"
            time = "1 hour"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason).replace("{duration}", time).replace("{time}", time)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message.group(name="unmute", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unmute(self, ctx: EvelinaContext):
        """Change unmute message for command response"""
        return await ctx.create_pages()

    @invoke_message_unmute.command(name="add", brief="manage guild", usage="invoke message unmute add Unmuted, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unmute_add(self, ctx: EvelinaContext, *, code: str):
        """Add unmute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "unmute")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "unmute", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        
    @invoke_message_unmute.command(name="remove", brief="manage guild", usage="invoke message unmute remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unmute_remove(self, ctx: EvelinaContext):
        """Remove unmute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_unmute.command(name="view", brief="manage guild", usage="invoke message unmute view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unmute_view(self, ctx: EvelinaContext):
        """View unmute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_unmute.command(name="test", brief="manage guild", usage="invoke message unmute test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unmute_test(self, ctx: EvelinaContext):
        """Test unmute message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
    
    @invoke_message.group(name="jail", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jail(self, ctx: EvelinaContext):
        """Change jail message for command response"""
        return await ctx.create_pages()

    @invoke_message_jail.command(name="add", brief="manage guild", usage="invoke message jail add Jailed, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jail_add(self, ctx: EvelinaContext, *, code: str):
        """Add jail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "jail")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "jail", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
    
    @invoke_message_jail.command(name="remove", brief="manage guild", usage="invoke message jail remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jail_remove(self, ctx: EvelinaContext):
        """Remove jail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_jail.command(name="view", brief="manage guild", usage="invoke message jail view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jail_view(self, ctx: EvelinaContext):
        """View jail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_jail.command(name="test", brief="manage guild", usage="invoke message jail test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jail_test(self, ctx: EvelinaContext):
        """Test jail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            member = ctx.author
            reason = "test"
            time = "1 hour"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason).replace("{duration}", time).replace("{time}", time)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message.group(name="jailchannel", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jailchannel(self, ctx: EvelinaContext):
        """Change jail channel message for command response"""
        return await ctx.create_pages()
    
    @invoke_message_jailchannel.command(name="add", brief="manage guild", usage="invoke message jailchannel add Jailed, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jailchannel_add(self, ctx: EvelinaContext, *, code: str):
        """Add jail channel message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jailchannel")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "jailchannel")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "jailchannel", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        
    @invoke_message_jailchannel.command(name="remove", brief="manage guild", usage="invoke message jailchannel remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jailchannel_remove(self, ctx: EvelinaContext):
        """Remove jail channel message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jailchannel")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jailchannel")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_jailchannel.command(name="view", brief="manage guild", usage="invoke message jailchannel view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jailchannel_view(self, ctx: EvelinaContext):
        """View jail channel message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jailchannel")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_jailchannel.command(name="test", brief="manage guild", usage="invoke message jailchannel test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_jailchannel_test(self, ctx: EvelinaContext):
        """Test jail channel message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jailchannel")
        if check:
            member = ctx.author
            reason = "test"
            time = "1 hour"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason).replace("{duration}", time).replace("{time}", time)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")

    @invoke_message.group(name="unjail", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unjail(self, ctx: EvelinaContext):
        """Change unjail message for command response"""
        return await ctx.create_pages()
    
    @invoke_message_unjail.command(name="add", brief="manage guild", usage="invoke message unjail add Unjailed, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unjail_add(self, ctx: EvelinaContext, *, code: str):
        """Add unjail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "unjail")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "unjail", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        
    @invoke_message_unjail.command(name="remove", brief="manage guild", usage="invoke message unjail remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unjail_remove(self, ctx: EvelinaContext):
        """Remove unjail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_unjail.command(name="view", brief="manage guild", usage="invoke message unjail view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unjail_view(self, ctx: EvelinaContext):
        """View unjail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_unjail.command(name="test", brief="manage guild", usage="invoke message unjail test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_unjail_test(self, ctx: EvelinaContext):
        """Test unjail message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message.group(name="warn", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_warn(self, ctx: EvelinaContext):
        """Change warn message for command response"""
        return await ctx.create_pages()

    @invoke_message_warn.command(name="add", brief="manage guild", usage="invoke message warn add Warned, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_warn_add(self, ctx: EvelinaContext, *, code: str):
        """Add warn message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_message SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "warn")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_message (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "warn", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** message as\n```{code}```")
        
    @invoke_message_warn.command(name="remove", brief="manage guild", usage="invoke message warn remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_warn_remove(self, ctx: EvelinaContext):
        """Remove warn message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_warn.command(name="view", brief="manage guild", usage="invoke message warn view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_warn_view(self, ctx: EvelinaContext):
        """View warn message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")
        
    @invoke_message_warn.command(name="test", brief="manage guild", usage="invoke message warn test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_message_warn_test(self, ctx: EvelinaContext):
        """Test warn message for command response"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_message WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.reply(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** message")

    @invoke.group(name="dm", invoke_without_command=True, case_insensitive=True)
    async def invoke_dm(self, ctx: EvelinaContext):
        """Change punishment messages for DM"""
        return await ctx.create_pages()

    @invoke_dm.group(name="ban", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_ban(self, ctx: EvelinaContext):
        """Change ban message for DM"""
        return await ctx.create_pages()

    @invoke_dm_ban.command(name="add", brief="manage guild", usage="invoke dm ban add Banned, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_ban_add(self, ctx: EvelinaContext, *, code: str):
        """Add ban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "ban")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "ban", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_ban.command(name="remove", brief="manage guild", usage="invoke dm ban remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_ban_remove(self, ctx: EvelinaContext):
        """Remove ban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_ban.command(name="view", brief="manage guild", usage="invoke dm ban view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_ban_view(self, ctx: EvelinaContext):
        """View ban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_ban.command(name="test", brief="manage guild", usage="invoke dm ban test")
    @has_guild_permissions(manage_guild=True)	
    async def invoke_dm_ban_test(self, ctx: EvelinaContext):
        """Test ban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "ban")
        if check:
            member = ctx.author
            reason = "test"
            time = "1 hour"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason).replace("{duration}", time).replace("{time}", time)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm.group(name="unban", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unban(self, ctx: EvelinaContext):
        """Change unban message for DM"""
        return await ctx.create_pages()

    @invoke_dm_unban.command(name="add", brief="manage guild", usage="invoke dm unban add Unbanned, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unban_add(self, ctx: EvelinaContext, *, code: str):
        """Add unban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "unban")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "unban", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_unban.command(name="remove", brief="manage guild", usage="invoke dm unban remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unban_remove(self, ctx: EvelinaContext):
        """Remove unban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_unban.command(name="view", brief="manage guild", usage="invoke dm unban view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unban_view(self, ctx: EvelinaContext):
        """View unban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_unban.command(name="test", brief="manage guild", usage="invoke dm unban test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unban_test(self, ctx: EvelinaContext):
        """Test unban message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unban")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm.group(name="kick", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_kick(self, ctx: EvelinaContext):
        """Change kick message for DM"""
        return await ctx.create_pages()

    @invoke_dm_kick.command(name="add", brief="manage guild", usage="invoke dm kick add Kicked, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_kick_add(self, ctx: EvelinaContext, *, code: str):
        """Add kick message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "kick")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "kick", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_kick.command(name="remove", brief="manage guild", usage="invoke dm kick remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_kick_remove(self, ctx: EvelinaContext):
        """Remove kick message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_kick.command(name="view", brief="manage guild", usage="invoke dm kick view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_kick_view(self, ctx: EvelinaContext):
        """View kick message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_kick.command(name="test", brief="manage guild", usage="invoke dm kick test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_kick_test(self, ctx: EvelinaContext):
        """Test kick message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "kick")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm.group(name="mute", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_mute(self, ctx: EvelinaContext):
        """Change mute message for DM"""
        return await ctx.create_pages()

    @invoke_dm_mute.command(name="add", brief="manage guild", usage="invoke dm mute add Muted, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_mute_add(self, ctx: EvelinaContext, *, code: str):
        """Add mute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "mute")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "mute", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_mute.command(name="remove", brief="manage guild", usage="invoke dm mute remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_mute_remove(self, ctx: EvelinaContext):
        """Remove mute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_mute.command(name="view", brief="manage guild", usage="invoke dm mute view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_mute_view(self, ctx: EvelinaContext):
        """View mute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_mute.command(name="test", brief="manage guild", usage="invoke dm mute test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_mute_test(self, ctx: EvelinaContext):
        """Test mute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "mute")
        if check:
            member = ctx.author
            reason = "test"
            time = "1 hour"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason).replace("{duration}", time).replace("{time}", time)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm.group(name="unmute", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unmute(self, ctx: EvelinaContext):
        """Change unmute message for DM"""
        return await ctx.create_pages()

    @invoke_dm_unmute.command(name="add", brief="manage guild", usage="invoke dm unmute add Unmuted, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unmute_add(self, ctx: EvelinaContext, *, code: str):
        """Add unmute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "unmute")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "unmute", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_unmute.command(name="remove", brief="manage guild", usage="invoke dm unmute remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unmute_remove(self, ctx: EvelinaContext):
        """Remove unmute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_unmute.command(name="view", brief="manage guild", usage="invoke dm unmute view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unmute_view(self, ctx: EvelinaContext):
        """View unmute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_unmute.command(name="test", brief="manage guild", usage="invoke dm unmute test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unmute_test(self, ctx: EvelinaContext):
        """Test unmute message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unmute")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm.group(name="jail", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_jail(self, ctx: EvelinaContext):
        """Change jail message for DM"""
        return await ctx.create_pages()

    @invoke_dm_jail.command(name="add", brief="manage guild", usage="invoke dm jail add Jailed, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_jail_add(self, ctx: EvelinaContext, *, code: str):
        """Add jail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "jail")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "jail", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_jail.command(name="remove", brief="manage guild", usage="invoke dm jail remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_jail_remove(self, ctx: EvelinaContext):
        """Remove jail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_jail.command(name="view", brief="manage guild", usage="invoke dm jail view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_jail_view(self, ctx: EvelinaContext):
        """View jail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_jail.command(name="test", brief="manage guild", usage="invoke dm jail test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_jail_test(self, ctx: EvelinaContext):
        """Test jail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "jail")
        if check:
            member = ctx.author
            reason = "test"
            time = "1 hour"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason).replace("{duration}", time).replace("{time}", time)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm.group(name="unjail", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unjail(self, ctx: EvelinaContext):
        """Change unjail message for DM"""
        return await ctx.create_pages()

    @invoke_dm_unjail.command(name="add", brief="manage guild", usage="invoke dm unjail add Unjailed, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unjail_add(self, ctx: EvelinaContext, *, code: str):
        """Add unjail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "unjail")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "unjail", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_unjail.command(name="remove", brief="manage guild", usage="invoke dm unjail remove")#
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unjail_remove(self, ctx: EvelinaContext):
        """Remove unjail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_unjail.command(name="view", brief="manage guild", usage="invoke dm unjail view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unjail_view(self, ctx: EvelinaContext):
        """View unjail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_unjail.command(name="test", brief="manage guild", usage="invoke dm unjail test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_unjail_test(self, ctx: EvelinaContext):
        """Test unjail message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "unjail")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")

    @invoke_dm.group(name="warn", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_warn(self, ctx: EvelinaContext):
        """Change warn message for DM"""
        return await ctx.create_pages()

    @invoke_dm_warn.command(name="add", brief="manage guild", usage="invoke dm warn add Warned, {member.mention}")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_warn_add(self, ctx: EvelinaContext, *, code: str):
        """Add warn message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            if code == check:
                return await ctx.send_warning(f"You already have this custom **{ctx.command.qualified_name.split()[2]}** direct message set up")
            else:
                await self.bot.db.execute("UPDATE invoke_dm SET embed = $1 WHERE guild_id = $2 AND command = $3", code, ctx.guild.id, "warn")
                return await ctx.send_success(f"Updated your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        else:
            await self.bot.db.execute("INSERT INTO invoke_dm (guild_id, command, embed) VALUES ($1, $2, $3)", ctx.guild.id, "warn", code)
            return await ctx.send_success(f"Added your custom **{ctx.command.qualified_name.split()[2]}** direct message as\n```{code}```")
        
    @invoke_dm_warn.command(name="remove", brief="manage guild", usage="invoke dm warn remove")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_warn_remove(self, ctx: EvelinaContext):
        """Remove warn message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            await self.bot.db.execute("DELETE FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
            return await ctx.send_success(f"Removed your custom **{ctx.command.qualified_name.split()[2]}** direct message")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_warn.command(name="view", brief="manage guild", usage="invoke dm warn view")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_warn_view(self, ctx: EvelinaContext):
        """View warn message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            return await ctx.evelina_send(f"Your custom **{ctx.command.qualified_name.split()[2]}** direct message is:\n```{check}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")
        
    @invoke_dm_warn.command(name="test", brief="manage guild", usage="invoke dm warn test")
    @has_guild_permissions(manage_guild=True)
    async def invoke_dm_warn_test(self, ctx: EvelinaContext):
        """Test warn message for DM"""
        check = await self.bot.db.fetchval("SELECT embed FROM invoke_dm WHERE guild_id = $1 AND command = $2", ctx.guild.id, "warn")
        if check:
            member = ctx.author
            reason = "test"
            try:
                x = await self.bot.embed_build.convert(ctx, self.invoke_replacement(member, check.replace("{reason}", reason)))
                return await ctx.author.send(**x)
            except Exception as e:
                return await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        else:
            return await ctx.send_warning(f"You don't have a custom **{ctx.command.qualified_name.split()[2]}** direct message")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Invoke(bot))