from typing import Union

from discord import Embed, Interaction, TextChannel
from discord.ext.commands import Cog, has_guild_permissions, group

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidEmoji
from modules.predicates import clownboard_enabled, clownboard_disabled

class Clownboard(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Clownboard commands"

    @group(name="clownboard", description="Showcase the best messages in your server", invoke_without_command=True, case_insensitive=True)
    async def clownboard(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @clownboard.command(name="enable", brief="manage guild", aliases=["on"], description="Enable the suggestion module")
    @has_guild_permissions(manage_guild=True)
    @clownboard_disabled()
    async def clownboard_enable(self, ctx: EvelinaContext):
        await self.bot.db.execute("INSERT INTO modules (guild_id, clownboard) VALUES ($1, TRUE) ON CONFLICT (guild_id) DO UPDATE SET clownboard = TRUE", ctx.guild.id)
        return await ctx.send_success("Clownboard module has been **enabled** in this server")
    
    @clownboard.command(name="disable", brief="manage guild", aliases=["off"], description="Disable the suggestion module")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_disable(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction) -> None:
            await interaction.client.db.execute("INSERT INTO modules (guild_id, clownboard) VALUES ($1, FALSE) ON CONFLICT (guild_id) DO UPDATE SET clownboard = FALSE", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Clownboard module has been **disabled** in this server"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Clownboard deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** clownboard", yes_callback, no_callback)

    @clownboard.command(name="emoji", brief="manage guild", usage="clownboard emoji 🤡", description="Sets the emoji that triggers the clownboard messages")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_emoji(self, ctx: EvelinaContext, emoji: ValidEmoji):
        check = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", ctx.guild.id)
        emoji = str(emoji)
        if not check:
            await self.bot.db.execute("INSERT INTO clownboard VALUES ($1,$2,$3,$4)", ctx.guild.id, None, emoji, 1)
        else:
            await self.bot.db.execute("UPDATE clownboard SET emoji = $1 WHERE guild_id = $2", emoji, ctx.guild.id)
        return await ctx.send_success(f"Set clownboard emoji to {emoji}")
    
    @clownboard.command(name="count", brief="manage guild", usage="clownboard count 3", description="Sets the default amount stars needed to post")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_count(self, ctx: EvelinaContext, count: int):
        if count < 1:
            return await ctx.send_warning("Number can't be **lower** than **1**")
        check = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO clownboard VALUES ($1,$2,$3,$4)", ctx.guild.id, None, None, count)
        else:
            await self.bot.db.execute("UPDATE clownboard SET count = $1 WHERE guild_id = $2", count, ctx.guild.id)
        return await ctx.send_success(f"Set clownboard count to **{count}**")
    
    @clownboard.command(name="channel", brief="manage guild", usage="clownboard channel #clownboard", description="Sets the channel where clownboard messages will be sent to")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_channel(self, ctx: EvelinaContext, *, channel: TextChannel):
        check = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO clownboard VALUES ($1,$2,$3,$4)", ctx.guild.id, channel.id, None, 1)
        else:
            await self.bot.db.execute("UPDATE clownboard SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
        return await ctx.send_success(f"Set clownboard channel to **{channel.mention}**")
    
    @clownboard.command(name="config", brief="manage guild", description="View the settings for clownboard in guild")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_config(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Clownboard is **not** configured")
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name="clownboard settings", icon_url=ctx.guild.icon)
        embed.add_field(name="Count", value=check["count"])
        embed.add_field(name="Emoji", value=f"{check['emoji']}")
        embed.add_field(name="Channel", value=f"<#{check['channel_id']}>")
        await ctx.send(embed=embed)

    @clownboard.command(name="reset", brief="manage guild", description="Resets guild's configuration for clownboard")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_reset(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction) -> None:
            await interaction.client.db.execute("DELETE FROM clownboard WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Disabled clownboard"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Clownboard deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** clownboard", yes_callback, no_callback)

    @clownboard.group(name="ignore", brief="manage guild", description="Ignore channels from clownboard", invoke_without_command=True)
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_ignore(self, ctx: EvelinaContext):
        return await ctx.create_pages()
    
    @clownboard_ignore.command(name="add", brief="manage guild", usage="clownboard ignore add #playground", description="Add a channel to the ignore list")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_ignore_add(self, ctx: EvelinaContext, *, target: TextChannel):
        check = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("clownboard is **not** configured")
        ignored = await self.bot.db.fetch("SELECT * FROM clownboard_ignored WHERE guild_id = $1", ctx.guild.id)
        if target.id in ignored:
            return await ctx.send_warning("This channel is already ignored")
        await self.bot.db.execute("INSERT INTO clownboard_ignored VALUES ($1, $2)", ctx.guild.id, target.id)
        return await ctx.send_success(f"Added {target.mention} to the ignore list")
    
    @clownboard_ignore.command(name="remove", brief="manage guild", usage="clownboard ignore remove #playground", description="Remove a channel from the ignore list")
    @has_guild_permissions(manage_guild=True)
    @clownboard_enabled()
    async def clownboard_ignore_remove(self, ctx: EvelinaContext, *, target: Union[TextChannel, int]):
        channel_id = self.bot.misc.convert_channel(target)
        check = await self.bot.db.fetchrow("SELECT * FROM clownboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("clownboard is **not** configured")
        ignored = await self.bot.db.fetch("SELECT * FROM clownboard_ignored WHERE guild_id = $1", ctx.guild.id)
        if channel_id not in ignored:
            return await ctx.send_warning("This channel is not ignored")
        await self.bot.db.execute("DELETE FROM clownboard_ignored WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"Removed {self.bot.misc.humanize_channel(channel_id)} from the ignore list")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Clownboard(bot))