from typing import Union

from discord import Embed, Interaction, TextChannel
from discord.ext.commands import Cog, has_guild_permissions, group

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidEmoji
from modules.predicates import starboard_enabled, starboard_disabled

class Starboard(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Starboard commands"

    @group(name="starboard", description="Showcase the best messages in your server", invoke_without_command=True, case_insensitive=True)
    async def starboard(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @starboard.command(name="enable", brief="manage guild", aliases=["on"], description="Enable the suggestion module")
    @has_guild_permissions(manage_guild=True)
    @starboard_disabled()
    async def starboard_enable(self, ctx: EvelinaContext):
        await self.bot.db.execute("INSERT INTO modules (guild_id, starboard) VALUES ($1, TRUE) ON CONFLICT (guild_id) DO UPDATE SET starboard = TRUE", ctx.guild.id)
        return await ctx.send_success("Starboard module has been **enabled** in this server")
    
    @starboard.command(name="disable", brief="manage guild", aliases=["off"], description="Disable the suggestion module")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_disable(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction) -> None:
            await interaction.client.db.execute("INSERT INTO modules (guild_id, starboard) VALUES ($1, FALSE) ON CONFLICT (guild_id) DO UPDATE SET starboard = FALSE", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Starboard module has been **disabled** in this server"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Starboard deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** starboard", yes_callback, no_callback)

    @starboard.command(name="emoji", brief="manage guild", usage="starboard emoji ⭐", description="Sets the emoji that triggers the starboard messages")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_emoji(self, ctx: EvelinaContext, emoji: ValidEmoji):
        check = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id)
        emoji = str(emoji)
        if not check:
            await self.bot.db.execute("INSERT INTO starboard VALUES ($1,$2,$3,$4)", ctx.guild.id, None, emoji, 1)
        else:
            await self.bot.db.execute("UPDATE starboard SET emoji = $1 WHERE guild_id = $2", emoji, ctx.guild.id)
        return await ctx.send_success(f"Set starboard emoji to {emoji}")
    
    @starboard.command(name="count", brief="manage guild", usage="starboard count 3", description="Sets the default amount stars needed to post")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_count(self, ctx: EvelinaContext, count: int):
        if count < 1:
            return await ctx.send_warning("Number can't be **lower** than **1**")
        check = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO starboard VALUES ($1,$2,$3,$4)", ctx.guild.id, None, None, count)
        else:
            await self.bot.db.execute("UPDATE starboard SET count = $1 WHERE guild_id = $2", count, ctx.guild.id)
        return await ctx.send_success(f"Set starboard count to **{count}**")
    
    @starboard.command(name="channel", brief="manage guild", usage="starboard channel #starboard", description="Sets the channel where starboard messages will be sent to")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_channel(self, ctx: EvelinaContext, *, channel: TextChannel):
        check = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            await self.bot.db.execute("INSERT INTO starboard VALUES ($1,$2,$3,$4)", ctx.guild.id, channel.id, None, 1)
        else:
            await self.bot.db.execute("UPDATE starboard SET channel_id = $1 WHERE guild_id = $2", channel.id, ctx.guild.id)
        return await ctx.send_success(f"Set starboard channel to **{channel.mention}**")
    
    @starboard.command(name="config", brief="manage guild", description="View the settings for starboard in guild")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_config(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Starboard is **not** configured")
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name="starboard settings", icon_url=ctx.guild.icon)
        embed.add_field(name="Count", value=check["count"])
        embed.add_field(name="Emoji", value=f"{check['emoji']}")
        embed.add_field(name="Channel", value=f"<#{check['channel_id']}>")
        await ctx.send(embed=embed)

    @starboard.command(name="reset", brief="manage guild", description="Resets guild's configuration for starboard")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_reset(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction) -> None:
            await interaction.client.db.execute("DELETE FROM starboard WHERE guild_id = $1", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Disabled starboard"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Starboard deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** starboard", yes_callback, no_callback)

    @starboard.group(name="ignore", brief="manage guild", description="Ignore channels or users from starboard", invoke_without_command=True)
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_ignore(self, ctx: EvelinaContext):
        return await ctx.create_pages()
    
    @starboard_ignore.command(name="add", brief="manage guild", usage="starboard ignore add #playground", description="Add a channel or user to the ignore list")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_ignore_add(self, ctx: EvelinaContext, *, target: TextChannel):
        check = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Starboard is **not** configured")
        ignored = await self.bot.db.fetch("SELECT * FROM starboard_ignored WHERE guild_id = $1", ctx.guild.id)
        if target.id in ignored:
            return await ctx.send_warning("This channel is already ignored")
        await self.bot.db.execute("INSERT INTO starboard_ignored VALUES ($1, $2)", ctx.guild.id, target.id)
        return await ctx.send_success(f"Added {target.mention} to the ignore list")
    
    @starboard_ignore.command(name="remove", brief="manage guild", usage="starboard ignore remove #playground", description="Remove a channel or user from the ignore list")
    @has_guild_permissions(manage_guild=True)
    @starboard_enabled()
    async def starboard_ignore_remove(self, ctx: EvelinaContext, *, target: Union[TextChannel, int]):
        channel_id = self.bot.misc.convert_channel(target)
        check = await self.bot.db.fetchrow("SELECT * FROM starboard WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Starboard is **not** configured")
        ignored = await self.bot.db.fetch("SELECT * FROM starboard_ignored WHERE guild_id = $1", ctx.guild.id)
        if channel_id not in ignored:
            return await ctx.send_warning("This channel is not ignored")
        await self.bot.db.execute("DELETE FROM starboard_ignored WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"Removed {self.bot.misc.humanize_channel(channel_id)} from the ignore list")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Starboard(bot))