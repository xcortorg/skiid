import asyncio

from discord import Interaction, Embed, Role
from discord.ext.commands import Cog, group, has_guild_permissions
from discord.errors import Forbidden

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.converters import HexColor
from modules.predicates import cr_is_configured

class Colorrole(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Colorrole commands"

    @group(invoke_without_command=True, aliases=["cr"], case_insensitive=True)
    async def colorrole(self, ctx: EvelinaContext):
        """Colorrole commands"""
        return await ctx.create_pages()

    @colorrole.command(name="setup", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def cr_setup(self, ctx: EvelinaContext):
        """Enable Colorrole system in your server"""
        if await self.bot.db.fetchrow("SELECT * FROM color_module WHERE guild_id = $1", ctx.guild.id):
            return await ctx.send_warning("Color role is **already** configured")
        await self.bot.db.execute("INSERT INTO color_module (guild_id) VALUES ($1)", ctx.guild.id)
        return await ctx.send_success("Configured color role module")
    
    @colorrole.command(name="reset", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @cr_is_configured()
    async def cr_reset(self, ctx: EvelinaContext):
        """Disable Colorrole system in your server"""
        async def yes_callback(interaction: Interaction):
            await self.bot.db.execute("DELETE FROM color_module WHERE guild_id = $1", ctx.guild.id)
            await self.bot.db.execute("DELETE FROM color_roles WHERE guild_id = $1", ctx.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: Color role module cleared"), view=None)
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {ctx.author.mention}: Color role deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to unset the colorrole module? This action is **IRREVERSIBLE**", yes_callback, no_callback)
    
    @colorrole.command(name="base", brief="manage guild", usage="colorrole base ---------")
    @has_guild_permissions(manage_guild=True)
    @cr_is_configured()
    async def cr_base(self, ctx: EvelinaContext, *, role: Role = None):
        """Set the base role for where boost roles will go under"""
        check = await self.bot.db.fetchrow("SELECT base FROM color_module WHERE guild_id = $1", ctx.guild.id)
        if role is None:
            if check is None:
                return await ctx.send_warning("Color role module **base role** isn't set")
            await self.bot.db.execute("UPDATE color_module SET base = $1 WHERE guild_id = $2", None, ctx.guild.id)
            return await ctx.send_success("Removed base role")
        await self.bot.db.execute("UPDATE color_module SET base = $1 WHERE guild_id = $2", role.id, ctx.guild.id)
        return await ctx.send_success(f"Set {role.mention} as base role")

    @colorrole.command(name="set", usage="colorrole set hex")
    @cr_is_configured()
    async def cr_set(self, ctx: EvelinaContext, *, color: HexColor):
        """Set or change your color role"""
        che = await self.bot.db.fetchval("SELECT base FROM color_module WHERE guild_id = $1", ctx.guild.id)
        color_value = color.value
        hex_color = f'#{color_value:06X}'
        existing_role = await self.bot.db.fetchrow("SELECT role_id FROM color_roles WHERE guild_id = $1 AND color = $2", ctx.guild.id, hex_color)
        try:
            await self.remove_old_color_role(ctx)
        except Forbidden:
            return await ctx.send_warning("I don't have permission to remove roles")
        if existing_role:
            role = ctx.guild.get_role(existing_role['role_id'])
            if role:
                try:
                    await ctx.author.add_roles(role)
                except Forbidden:
                    return await ctx.send_warning("I don't have permission to assign roles")
                await ctx.send_success("Color role assigned")
            else:
                await self.bot.db.execute("DELETE FROM color_roles WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, existing_role['role_id'])
                try:
                    await self.create_new_color_role(ctx, color_value, hex_color, che)
                except Forbidden:
                    await ctx.send_warning("I don't have permission to create roles")
        else:
            if len(ctx.guild.roles) >= 250:
                return await ctx.send_warning("I can't create more roles, please delete some roles first")
            try:
                await self.create_new_color_role(ctx, color_value, hex_color, che)
            except Forbidden:
                await ctx.send_warning("I don't have permission to create roles")
    
    async def remove_old_color_role(self, ctx: EvelinaContext):
        removed = False
        for role in ctx.author.roles:
            if role.name.startswith('#') and len(role.name) == 7:
                await ctx.author.remove_roles(role)
                if len(role.members) == 0:
                    await role.delete(reason="Unused color role removed")
                    await self.bot.db.execute("DELETE FROM color_roles WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
                removed = True
        return removed
    
    async def create_new_color_role(self, ctx, color_value, hex_color, che):
        name = hex_color
        ro = ctx.guild.get_role(che)
        role = await ctx.guild.create_role(name=name, color=color_value)
        await asyncio.sleep(1)
        if ro is not None:
            await role.edit(position=ro.position)
        else:
            await role.edit(position=1)
        await ctx.author.add_roles(role)
        await self.bot.db.execute("INSERT INTO color_roles (guild_id, role_id, color) VALUES ($1, $2, $3)", ctx.guild.id, role.id, hex_color)
        await ctx.send_success(f"Color role `{hex_color}` got created")

    @colorrole.command(name="remove", usage="colorrole remove")
    @cr_is_configured()
    async def cr_remove(self, ctx: EvelinaContext):
        """Remove your current color role"""
        removed = await self.remove_old_color_role(ctx)
        if removed:
            await ctx.send_success("Color role got removed")
        else:
            await ctx.send_warning("You don't have a color role to remove")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Colorrole(bot))