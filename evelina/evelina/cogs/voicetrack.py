import discord

from discord.ext.commands import group, Cog, Author, has_guild_permissions

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext

class Voicetrack(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Voicetracking commands"

    @group(name="voicetrack", aliases=["vct", "vt"], invoke_without_command=True, case_insensitive=True)
    async def voicetrack(self, ctx: EvelinaContext, member: discord.Member = Author):
        """Shows how long a users' been in a voice channel"""
        res = await self.bot.db.fetchrow("SELECT total_time, mute_time FROM voicetrack WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        settings = await self.bot.db.fetchrow("SELECT mute_track FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        if res and res['total_time'] > 0:
            total_seconds = res['total_time']
            mute_time = res['mute_time']
            if member.id == ctx.author.id:
                message = f"You have spent **{self.bot.misc.humanize_time(total_seconds, True, 'HH-MM-SS')}** in voice channels on **{ctx.guild.name}**"
                if settings and settings['mute_track'] and mute_time:
                    message += f" with a mute time of **{self.bot.misc.humanize_time(mute_time, True, 'HH-MM-SS')}**"
                await ctx.evelina_send(message, emoji="🎙️")
            else:
                message = f"**{member.display_name}** has spent **{self.bot.misc.humanize_time(total_seconds, True, 'HH-MM-SS')}** in voice channels on **{ctx.guild.name}**"
                if settings and settings['mute_track'] and mute_time:
                    message += f" with a mute time of **{self.bot.misc.humanize_time(mute_time, True, 'HH-MM-SS')}**"
                await ctx.evelina_send(message, emoji="🎙️")
        else:
            if member.id == ctx.author.id:
                await ctx.send_warning("No voice records found on this server.")
            else:
                await ctx.send_warning(f"No voice records found for **{member.display_name}** on this server.")

    @voicetrack.command(name="enable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicetrack_enable(self, ctx: EvelinaContext):
        """Enable the voice track feature for your guild"""
        res = await self.bot.db.fetchrow("SELECT state FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        if res is None or res['state'] is False:
            await self.bot.db.execute("INSERT INTO voicetrack_settings (guild_id, state) VALUES ($1, True) ON CONFLICT (guild_id) DO UPDATE SET state = True", ctx.guild.id)
            await ctx.send_success("Voice tracking has been **enabled**")
        else:
            await ctx.send_warning("Voice tracking is **already** enabled for this server")

    @voicetrack.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicetrack_disable(self, ctx: EvelinaContext):
        """Disable the voice track feature for your guild"""
        res = await self.bot.db.fetchrow("SELECT state FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        if res and res['state'] is True:
            await self.bot.db.execute(
                "UPDATE voicetrack_settings SET state = False WHERE guild_id = $1", ctx.guild.id)
            await ctx.send_success("Voice tracking has been **disabled**")
        else:
            await ctx.send_warning("Voice tracking is **not** enabled")

    @voicetrack.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicetrack_reset(self, ctx: EvelinaContext):
        """Reset the voicetracking system in your server"""
        res = await self.bot.db.fetchrow("SELECT * FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        if not res:
            return await ctx.send_warning("Voice tracking is **not** enabled")
        async def yes_callback(interaction: discord.Interaction):
            await self.bot.db.execute("DELETE FROM voicetrack WHERE guild_id = $1", interaction.guild.id)
            await self.bot.db.execute("DELETE FROM voicetrack_settings WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(
                embed=discord.Embed(color=colors.SUCCESS, description=f"{emojis.DENY} {interaction.user.mention}: Cleared all voice trackings in your server"), view=None)
        async def no_callback(interaction: discord.Interaction):
            return await interaction.response.edit_message(
                embed=discord.Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Voicetracking reset got canceled"), view=None)
        await ctx.confirmation_send("Are you sure you want to **reset** the voice tracking feature?\n**THIS WILL DELETE ALL TRACKING DATA FROM USERS**", yes_callback, no_callback)

    @voicetrack.command(name="clear", aliases=["c"], brief="manage guild", usage="voicetrack clear comminate")
    async def voicetrack_clear(self, ctx: EvelinaContext, member: discord.Member = Author):
        """Clear your voice tracking data for the current guild"""
        res = await self.bot.db.fetchrow("SELECT * FROM voicetrack WHERE user_id = $1 AND guild_id = $2", member.id, ctx.guild.id)
        if not res:
            return await ctx.send_warning("There is **no data** saved for this user")
        async def yes_func(interaction: discord.Interaction):
            await self.bot.db.execute("DELETE FROM voicetrack WHERE user_id = $1 AND guild_id = $2", member.id, interaction.guild.id)
            return await interaction.response.edit_message(embed=discord.Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Cleared {member.mention} voice tracking data"), view=None)
        async def no_func(interaction: discord.Interaction):
            return await interaction.response.edit_message(embed=discord.Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Voicetracking data clear got canceled"), view=None)
        await ctx.confirmation_send(f"Are you sure you want to **clear** {member.mention}'s voice tracking data?", yes_func, no_func)

    @voicetrack.command(name="enablemute", usage="voicetrack enablemute", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicetrack_enablemute(self, ctx: EvelinaContext):
        """Enable the mute time tracking"""
        res = await self.bot.db.fetchrow("SELECT mute_track FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id,)
        if not res or res["mute_track"] is False:
            await self.bot.db.execute("UPDATE voicetrack_settings SET mute_track = True WHERE guild_id = $1", ctx.guild.id)
            await ctx.send_success("Mute time tracking has been **enabled**")
        else:
            await ctx.send_warning("Mute time tracking is **already** enabled for this server")

    @voicetrack.command(name="disablemute", usage="voicetrack disablemute", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicetrack_disablemute(self, ctx: EvelinaContext):
        """Disable the mute time tracking"""
        res = await self.bot.db.fetchrow("SELECT mute_track FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id,)
        if res and res['mute_track'] is True:
            await self.bot.db.execute("UPDATE voicetrack_settings SET mute_track = False WHERE guild_id = $1", ctx.guild.id,)
            await ctx.send_success("Mute time tracking has been **disabled**")
        else:
            await ctx.send_warning("Mute time tracking is **not** enabled for this server")

    @voicetrack.command(name="leaderboard", aliases=["lb"], usage="voicetrack leaderboard")
    async def voicetrack_lb(self, ctx: EvelinaContext):
        """List the members with the most voice time"""
        res = await self.bot.db.fetchrow("SELECT state, mute_track FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        if not res or res['state'] is False:
            return await ctx.send_warning("Voice tracking is not enabled for this server.")
        results = await self.bot.db.fetch("SELECT user_id, total_time, mute_time FROM voicetrack WHERE guild_id = $1 ORDER BY total_time DESC", ctx.guild.id)
        if not results:
            return await ctx.send_warning("No voice records found on this server.")
        leaderboard = []
        for record in results[:50]:
            total_seconds = record['total_time']
            mute_time = record['mute_time']
            user = self.bot.get_user(record['user_id'])
            if user:
                if res['mute_track'] and mute_time:
                    leaderboard.append(f"**{user.name}** - {self.bot.misc.humanize_time(total_seconds, True, 'HH-MM-SS')} (🔇 {self.bot.misc.humanize_time(mute_time, True, 'HH-MM-SS')})")
                else:
                    leaderboard.append(f"**{user.name}** - {self.bot.misc.humanize_time(total_seconds, True, 'HH-MM-SS')}")
        await ctx.paginate(leaderboard, "Voice Time Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else self.bot.user.display_avatar.url})

    @voicetrack.command(name="globalleaderboard", aliases=["glb"])
    async def voicetrack_glb(self, ctx: EvelinaContext):
        """List the members with the most voice time over all servers"""
        results = await self.bot.db.fetch("SELECT user_id, SUM(total_time) AS total_time FROM voicetrack GROUP BY user_id ORDER BY total_time DESC")
        leaderboard = []
        for record in results[:50]:
            total_seconds = record['total_time']
            user = self.bot.get_user(record['user_id']) or await self.bot.fetch_user(record['user_id'])
            if user:
                leaderboard.append(f"**{user.name}** - {self.bot.misc.humanize_time(total_seconds, True, 'HH-MM-SS')}")
        if not leaderboard:
            return await ctx.send_warning("No voice records found")
        await ctx.paginate(leaderboard, "Global Voice Time Leaderboard", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url},)

    @voicetrack.group(name="leveling", aliases=["level"])
    async def voicetrack_leveling(self, ctx: EvelinaContext):
        """Manage voice leveling"""
        return await ctx.create_pages()

    @voicetrack_leveling.command(name="enable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicetrack_leveling_enable(self, ctx: EvelinaContext):
        """Enable the voice leveling feature for your guild"""
        res = await self.bot.db.fetchrow("SELECT level_state FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        if res is None or res['level_state'] is False:
            await self.bot.db.execute("INSERT INTO voicetrack_settings (guild_id, level_state) VALUES ($1, True) ON CONFLICT (guild_id) DO UPDATE SET level_state = True", ctx.guild.id)
            await ctx.send_success("Voice leveling has been **enabled**")
        else:
            await ctx.send_warning("Voice leveling is **already** enabled for this server")

    @voicetrack_leveling.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def voicetrack_leveling_disable(self, ctx: EvelinaContext):
        """Disable the voice leveling feature for your guild"""
        res = await self.bot.db.fetchrow("SELECT level_state FROM voicetrack_settings WHERE guild_id = $1", ctx.guild.id)
        if res and res['level_state'] is True:
            await self.bot.db.execute(
                "UPDATE voicetrack_settings SET level_state = False WHERE guild_id = $1", ctx.guild.id)
            await ctx.send_success("Voice leveling has been **disabled**")
        else:
            await ctx.send_warning("Voice leveling is **not** enabled")

async def setup(bot: Evelina):
    await bot.add_cog(Voicetrack(bot))