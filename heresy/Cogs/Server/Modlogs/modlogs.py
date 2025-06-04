import discord
from discord.ext import commands
import json
import os

class ModLogs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_channels = {}
        self.load_log_channels()

    def load_log_channels(self):
        if os.path.isfile("mod_log_channels.json"):
            with open("mod_log_channels.json", "r") as file:
                self.log_channels = json.load(file)

    def save_log_channels(self):
        with open("mod_log_channels.json", "w") as file:
            json.dump(self.log_channels, file, indent=4)

    async def send_log(self, guild_id, embed):
        log_channel_id = self.log_channels.get(str(guild_id))
        if log_channel_id:
            log_channel = self.bot.get_channel(int(log_channel_id))
            if log_channel:
                await log_channel.send(embed=embed)

    @commands.command(name="modlogs")
    @commands.has_permissions(administrator=True)
    async def set_modlog_channel(self, ctx, channel: discord.TextChannel):
        self.log_channels[str(ctx.guild.id)] = channel.id
        self.save_log_channels()
        await ctx.send(f"Mod logs channel has been set to {channel.mention}")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        if before.nick != after.nick:
            embed = discord.Embed(title="**Member Update**", color=discord.Color.blue())
            embed.add_field(name="**Responsible:**", value=f"{after.guild.me.mention} ({after.guild.me.id})")
            embed.add_field(name="**Target:**", value=f"{after.mention} ({after.id})")
            embed.add_field(name="*Time:*", value="*{0}*".format(after.joined_at.strftime('%A, %b %d, %Y %I:%M %p')))
            embed.add_field(name="**Changes**", value=f"> **Nick:** \n> {before.nick or 'None'} --> {after.nick or 'None'}", inline=False)
            await self.send_log(after.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_role_update(self, member, before, after):
        added_roles = [role for role in after.roles if role not in before.roles]
        removed_roles = [role for role in before.roles if role not in after.roles]

        if added_roles or removed_roles:
            embed = discord.Embed(title="**Member Role Update**", color=discord.Color.green())
            embed.add_field(name="**Responsible:**", value=f"{member.guild.me.mention} ({member.guild.me.id})")
            embed.add_field(name="**Target:**", value=f"{member.mention} ({member.id})")
            embed.add_field(name="*Time:*", value="*{0}*".format(member.joined_at.strftime('%A, %b %d, %Y %I:%M %p')))
            changes = ""
            if added_roles:
                changes += "> **Additions:** \n> " + ", ".join([role.mention for role in added_roles])
            if removed_roles:
                changes += "\n> **Removals:** \n> " + ", ".join([role.mention for role in removed_roles])
            embed.add_field(name="**Changes**", value=changes, inline=False)
            await self.send_log(member.guild.id, embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return

        embed = discord.Embed(title="**Message Deleted**", color=discord.Color.red())
        embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
        embed.add_field(name="Message sent by", value=message.author.mention)
        embed.add_field(name="Deleted in", value=message.channel.mention)
        embed.add_field(
            name="Content", 
            value=f"```diff\n- {message.content}\n```" if message.content else "No content available", 
            inline=False
        )
        embed.add_field(name="Author ID", value=f"{message.author.id} | Message ID: {message.id}")
        await self.send_log(message.guild.id, embed)

    @commands.Cog.listener()
    async def on_bulk_message_delete(self, messages):
        if len(messages) == 0:
            return
        channel = messages[0].channel
        embed = discord.Embed(title="**Bulk Delete**", color=discord.Color.red())
        embed.add_field(name="Bulk Delete in", value=f"{channel.mention}, {len(messages)} messages deleted")
        embed.add_field(name="*Time:*", value="*{0}*".format(discord.utils.utcnow().strftime('%A, %b %d, %Y %I:%M %p')))
        await self.send_log(channel.guild.id, embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.content != after.content:
            embed = discord.Embed(title="**Message Edited**", color=discord.Color.orange())
            embed.set_author(name=before.author.display_name, icon_url=before.author.avatar.url)
            embed.add_field(name="Message Edited in", value=f"{before.channel.mention} [Jump to Message]({before.jump_url})")
            embed.add_field(name="**Before:**", value=f"*{before.content}*", inline=False)
            embed.add_field(name="**After:**", value=f"*{after.content}*", inline=False)
            embed.add_field(name="User ID", value=f"{before.author.id}")
            await self.send_log(before.guild.id, embed)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        embed = discord.Embed(title="**Member Ban Add**", color=discord.Color.red())
        embed.add_field(name="**Responsible:**", value=f"{guild.me.mention} ({guild.me.id})")
        embed.add_field(name="**Target:**", value=f"{user.mention} ({user.id})")
        embed.add_field(name="*Time:*", value="*{0}*".format(discord.utils.utcnow().strftime('%A, %b %d, %Y %I:%M %p')))
        await self.send_log(guild.id, embed)

async def setup(bot):
    await bot.add_cog(ModLogs(bot))
