import discord
from discord.ext import commands
from discord import app_commands

class channel_cmds(app_commands.Group):

    @app_commands.command(name="attachments", description="Toggle the attachment permission for a channel")
    async def channel_attachments(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Toggles the attachment permission for a specified channel."""
        overwrites = channel.overwrites
        current_permission = channel.permissions_for(interaction.guild.default_role).attach_files
        await channel.set_permissions(interaction.guild.default_role, attach_files=not current_permission)
        new_status = "enabled" if not current_permission else "disabled"
        await interaction.response.send_message(f"Attachment permissions for '{channel.name}' have been {new_status}.", ephemeral=True)

    @app_commands.command(name="create", description="Create a new text channel")
    async def channel_create(self, interaction: discord.Interaction, channel_name: str):
        """Creates a new text channel."""
        guild = interaction.guild
        await guild.create_text_channel(channel_name)
        await interaction.response.send_message(f"Channel '{channel_name}' created.", ephemeral=True)

    @app_commands.command(name="delete", description="Delete a text channel")
    async def channel_delete(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Deletes a specified text channel."""
        await channel.delete()
        await interaction.response.send_message(f"Channel '{channel.name}' deleted.", ephemeral=True)

    @app_commands.command(name="show", description="Show a channel to all members")
    async def channel_show(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Shows a specified channel to all members."""
        await channel.set_permissions(interaction.guild.default_role, read_messages=True)
        await interaction.response.send_message(f"Channel '{channel.name}' is now visible to all members.", ephemeral=True)

    @app_commands.command(name="hide", description="Hide a channel from all members")
    async def channel_hide(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Hides a specified channel from all members without admin."""
        await channel.set_permissions(interaction.guild.default_role, read_messages=False)
        await interaction.response.send_message(f"Channel '{channel.name}' is now hidden from all members.", ephemeral=True)

    @app_commands.command(name="rename", description="Rename a text channel")
    async def channel_rename(self, interaction: discord.Interaction, channel: discord.TextChannel, new_name: str):
        """Renames a specified text channel."""
        await channel.edit(name=new_name)
        await interaction.response.send_message(f"Channel '{channel.name}' renamed to '{new_name}'.", ephemeral=True)

    @app_commands.command(name="revoke", description="Revoke a member's permission to view a channel")
    async def channel_revoke(self, interaction: discord.Interaction, channel: discord.TextChannel, member: discord.Member):
        """Revokes a member's permission to view a specified channel."""
        await channel.set_permissions(member, read_messages=False)
        await interaction.response.send_message(f"{member.display_name}'s access to '{channel.name}' has been revoked.", ephemeral=True)

    @app_commands.command(name="lock", description="Lock a channel from all members without admin")
    async def channel_lock(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Locks a specified channel from all members without admin."""
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f"Channel '{channel.name}' is now locked from all members.", ephemeral=True)

    @app_commands.command(name="unlock", description="Unlock a channel for all members")
    async def channel_unlock(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Unlocks a specified channel for all members."""
        await channel.set_permissions(interaction.guild.default_role, send_messages=True)
        await interaction.response.send_message(f"Channel '{channel.name}' is now unlocked for all members.", ephemeral=True)

async def setup(thebot):
    global bot
    bot = thebot
    bot.tree.add_command(channel_cmds(name='channel', description='Channel things'))