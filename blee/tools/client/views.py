from typing import Optional, Union

import discord
from discord import ButtonStyle, Emoji, Interaction, PartialEmoji, ui
from discord.ext import commands
from discord.ui import Button, View


class ConfirmViewForUser(View):
    # Like ConfirmView, but it's for a specific member, not the author of the command
    def __init__(self, ctx: commands.Context, member: discord.Member):
        super().__init__()
        self.value = False
        self.ctx: commands.Context = ctx
        self.bot: commands.Bot = ctx.bot
        self.member = member

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, _: discord.Button):
        """Approve the action"""
        self.value = True
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, _: discord.Button):
        """Decline the action"""
        self.value = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.member.id:
            return True
        await interaction.warn(
            "You aren't the **author** of this embed",
        )
        return False


class ConfirmView(View):
    def __init__(self, ctx: commands.Context):
        super().__init__()
        self.value = False
        self.ctx: commands.Context = ctx
        self.bot: commands.Bot = ctx.bot

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, _: discord.Button):
        """Approve the action"""
        self.value = True
        self.stop()

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, _: discord.Button):
        """Decline the action"""
        self.value = False
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id == self.ctx.author.id:
            return True
        await interaction.warn(
            "You aren't the **author** of this embed",
        )
        return False


class EmojiButtons(ui.View):
    def __init__(self, emoji: Union[Emoji, PartialEmoji], ctx: commands.Context):
        super().__init__(timeout=30.0)
        self.emoji = emoji
        self.ctx = ctx

        # Disable Add button if emoji is a Unicode emoji
        if not hasattr(self.emoji, "id"):
            self.add_emoji.disabled = True

    async def on_timeout(self) -> None:
        """Disable all buttons when the view times out"""
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @ui.button(label="Add", style=ButtonStyle.green, emoji="➕")
    async def add_emoji(self, interaction: Interaction, button: ui.Button):
        if not interaction.user.guild_permissions.manage_emojis:
            return await interaction.response.send_message(
                "You need **Manage Emojis** permission to add emojis!", ephemeral=True
            )

        try:
            # Check if guild has space for new emoji
            if len(interaction.guild.emojis) >= interaction.guild.emoji_limit:
                return await interaction.response.send_message(
                    "This server has reached its emoji limit!", ephemeral=True
                )

            added_emoji = await interaction.guild.create_custom_emoji(
                name=self.emoji.name,
                image=await self.emoji.read(),
                reason=f"{interaction.user}: Added from emoji info",
            )
            await interaction.response.send_message(
                f"Successfully added emoji {added_emoji}!", ephemeral=True
            )

            # Disable the Add button after successful addition
            button.disabled = True
            await self.message.edit(view=self)

        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to add emojis!", ephemeral=True
            )
        except discord.HTTPException as e:
            await interaction.response.send_message(
                f"Failed to add emoji: {str(e)}", ephemeral=True
            )

    @ui.button(label="Close", style=ButtonStyle.red, emoji="✖️")
    async def close_menu(self, interaction: Interaction, button: ui.Button):
        if interaction.user.id != self.ctx.author.id:
            return await interaction.response.send_message(
                "You cannot close this menu!", ephemeral=True
            )
        await interaction.message.delete()
