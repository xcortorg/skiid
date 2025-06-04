import discord

from typing import List

from discord import Interaction
from discord.ext import commands

from modules.styles import emojis, colors

class Paginator(discord.ui.View):
    def __init__(self, ctx: commands.Context, embeds: List[discord.Embed], invoker: int = None, author_only: bool = True):
        super().__init__()
        self.embeds = embeds
        self.ctx = ctx
        self.invoker = invoker
        self.author_only = author_only
        self.actions = ["next", "previous", "prev", "first", "last", "delete", "goto"]
        self.page = 0

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if self.author_only and interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are not the **author** of this embed"), ephemeral=True)
            return False
        return True

    async def update_view(self, interaction: discord.Interaction):
        try:
            if not interaction.response.is_done():
                await interaction.response.defer()
            await interaction.followup.edit_message(interaction.message.id, embed=self.embeds[self.page], view=self)
        except discord.NotFound:
            embed = discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: The message no longer exists.")
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.NotFound:
                pass
        except discord.HTTPException as e:
            embed = discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: An error occurred: {e.text}")
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except discord.NotFound:
                pass

    def add_button(self, action: str, /, *, label: str = "", emoji=None, style: str = discord.ButtonStyle.gray):
        action = action.strip().lower()
        if not action in self.actions:
            return
        if action == "first":
            self.add_item(first_page(label, emoji, style))
        elif action == "last":
            self.add_item(last_page(label, emoji, style))
        elif action == "next":
            self.add_item(next_page(label, emoji, style))
        elif action in ["prev", "previous"]:
            self.add_item(prev_page(label, emoji, style))
        elif action == "delete":
            self.add_item(delete_page(label, emoji, style))
        elif action == "goto":
            self.add_item(goto_page(label, emoji, style))

    async def start(self, interaction: Interaction = None, ephemeral: bool = False):
        try:
            if interaction:
                try:
                    await interaction.response.send_message(embed=self.embeds[0], view=self, ephemeral=ephemeral)
                    self.message = await interaction.original_response()
                except discord.InteractionResponded:
                    self.message = await interaction.followup.send(embed=self.embeds[0], view=self, ephemeral=ephemeral)
            else:
                self.message = await self.ctx.send(embed=self.embeds[0], view=self)
        except discord.HTTPException:
            self.stop()

class goto_modal(discord.ui.Modal, title="Go to"):
    page = discord.ui.TextInput(label="page", placeholder="page number", required=True, style=discord.TextStyle.short)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            view = self.view
            num = int(self.page.value) - 1
            if num in range(len(view.embeds)):
                view.page = num
                await view.update_view(interaction)
            else:
                return await interaction.response.send_message(ephemeral=True, embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Invalid Page"))
        except ValueError:
            return await interaction.response.send_message(ephemeral=True, embed=discord.Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: This is not a number"))

class prev_page(discord.ui.Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.page == 0:
            view.page = len(view.embeds) - 1
        else:
            view.page -= 1
        await view.update_view(interaction)

class next_page(discord.ui.Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.page == len(view.embeds) - 1:
            view.page = 0
        else:
            view.page += 1
        await view.update_view(interaction)

class first_page(discord.ui.Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style)

    async def callback(self, interaction: discord.Interaction):
        self.view.page = 0
        await self.view.update_view(interaction)

class last_page(discord.ui.Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style)

    async def callback(self, interaction: discord.Interaction):
        self.view.page = len(self.view.embeds) - 1
        await self.view.update_view(interaction)

class delete_page(discord.ui.Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style)

    async def callback(self, interaction: discord.Interaction):
        try:
            return await interaction.message.delete()
        except Exception:
            pass

class goto_page(discord.ui.Button):
    def __init__(self, label, emoji, style):
        super().__init__(label=label, emoji=emoji, style=style)

    async def callback(self, interaction: discord.Interaction):
        modal = goto_modal()
        modal.view = self.view
        return await interaction.response.send_modal(modal)