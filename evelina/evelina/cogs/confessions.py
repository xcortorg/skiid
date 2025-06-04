from discord import TextChannel
from discord import app_commands, Interaction
from discord.ext.commands import Cog, group, has_guild_permissions

from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.persistent.confessions import confessModal

class Confessions(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Confessions Commands"

    @app_commands.command(name="confess", description="Confess your thoughts")
    async def confess(self, interaction: Interaction):
        """Anonymously confess your thoughts"""
        if interaction.guild is None:
            return await interaction.warn("You can't use this command in DMs", ephemeral=True)
        muted = await self.bot.db.fetchrow("SELECT * FROM confess_mute WHERE guild_id = $1 AND user_id = $2", interaction.guild.id, interaction.user.id)
        if muted:
            return await interaction.warn("You are **muted** from sending confessions in this server", ephemeral=True)
        check = await self.bot.db.fetchrow("SELECT channel_id FROM confess WHERE guild_id = $1", interaction.guild.id)
        if not check:
            return await interaction.warn("Confessions aren't enabled in this server", ephemeral=True)
        await interaction.response.send_modal(confessModal())

    @group(name="confessions", aliases=["conf"], invoke_without_command=True, case_insensitive=True)
    async def confessions(self, ctx: EvelinaContext):
        """Setup the confessions module"""
        return await ctx.create_pages()

    @confessions.command(name="enable", brief="manage_guild")
    @has_guild_permissions(manage_guild=True)
    async def confessions_enable(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Enable the confessions module"""
        check = await self.bot.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", ctx.guild.id)
        if check is not None:
            await self.bot.db.execute("UPDATE confess SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id,)
        elif check is None:
            await self.bot.db.execute("INSERT INTO confess VALUES ($1,$2,$3)", ctx.guild.id, channel.id, 0)
        return await ctx.send_success(f"Confession channel set to {channel.mention}")

    @confessions.command(name="disable", brief="manage_guild")
    @has_guild_permissions(manage_guild=True)
    async def confessions_disable(self, ctx: EvelinaContext):
        """Disable the confessions module"""
        check = await self.bot.db.fetchrow("SELECT channel_id FROM confess WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.send_warning("Confessions aren't **enabled** in this server")
        await self.bot.db.execute("DELETE FROM confess WHERE guild_id = $1", ctx.guild.id)
        await self.bot.db.execute("DELETE FROM confess_members WHERE guild_id = $1", ctx.guild.id)
        await self.bot.db.execute("DELETE FROM confess_mute WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Confessions disabled")
    
    @confessions.command(name="channel", brief="manage_guild", usage="confessions channel #conf")
    @has_guild_permissions(manage_guild=True)
    async def confessions_channel(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Set the confession channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.send_warning("Confessions aren't **enabled** in this server")
        await self.bot.db.execute("UPDATE confess SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
        return await ctx.send_success(f"Confession channel set to {channel.mention}")
    
    @confessions.command(name="mute", brief="manage_guild", usage="confessions mute 14")
    @has_guild_permissions(manage_guild=True)
    async def confessions_mute(self, ctx: EvelinaContext, id: int):
        """Mute a user from sending confessions"""
        check = await self.bot.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.send_warning("Confessions aren't **enabled** in this server")
        confession = await self.bot.db.fetchrow("SELECT * FROM confess_members WHERE guild_id = $1 AND confession = $2", ctx.guild.id, id)
        if not confession:
            return await ctx.send_warning(f"Confession **{id}** doesn't exist")
        confession_mute = await self.bot.db.fetchrow("SELECT * FROM confess_mute WHERE guild_id = $1 AND confession = $2", ctx.guild.id, id)
        if confession_mute:
            return await ctx.send_warning(f"Confession author **#{id}** is already **muted**")
        await self.bot.db.execute("INSERT INTO confess_mute VALUES ($1,$2,$3)", ctx.guild.id, confession["user_id"], id)
        return await ctx.send_success(f"Author of confession **#{id}** has been **muted**")

    @confessions.command(name="unmute", brief="manage_guild", usage="confessions unmute 14")
    @has_guild_permissions(manage_guild=True)
    async def confessions_unmute(self, ctx: EvelinaContext, id: int):
        """Unmute a user from sending confessions"""
        check = await self.bot.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.send_warning("Confessions aren't **enabled** in this server")
        confession = await self.bot.db.fetchrow("SELECT * FROM confess_members WHERE guild_id = $1 AND confession = $2", ctx.guild.id, id)
        if not confession:
            return await ctx.send_warning(f"Confession **{id}** doesn't exist")
        confession_mute = await self.bot.db.fetchrow("SELECT * FROM confess_mute WHERE guild_id = $1 AND confession = $2", ctx.guild.id, id)
        if not confession_mute:
            return await ctx.send_warning(f"Confession author **#{id}** isn't **muted**")
        await self.bot.db.execute("DELETE FROM confess_mute WHERE guild_id = $1 AND user_id = $2 AND confession = $3", ctx.guild.id, confession["user_id"], id)
        return await ctx.send_success(f"Author of confession **#{id}** has been **unmuted**")
    
    @confessions.command(name="muted", brief="manage_guild")
    @has_guild_permissions(manage_guild=True)
    async def confessions_muted(self, ctx: EvelinaContext):
        """List all confessions muted users"""
        check = await self.bot.db.fetchrow("SELECT * FROM confess WHERE guild_id = $1", ctx.guild.id)
        if check is None:
            return await ctx.send_warning("Confessions aren't **enabled** in this server")
        muted = await self.bot.db.fetch("SELECT * FROM confess_mute WHERE guild_id = $1", ctx.guild.id)
        if not muted:
            return await ctx.send_warning("There are no **confessions muted** users")
        members = [f"{user['confession']}" for user in muted]
        if members:
            return await ctx.paginate(members, f"Confessions Muted", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        else:
            await ctx.send_warning("There are no **confessions muted** users")
    
async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Confessions(bot))