import random
from inspect import iscoroutinefunction as iscoro
from inspect import isfunction as isfunc
from typing import Iterable, Optional

import config
import discord
from discord.ext.commands import Context
from loguru import logger as log


class GotoModal(discord.ui.Modal, title="Pagination"):
    def __init__(self, button: discord.ui.Button):
        super().__init__()
        self.button = button
        self.page_num = discord.ui.TextInput(
            label="Page Menu",
            placeholder="Enter Page Number",
            style=discord.TextStyle.short,
            required=True,
        )
        self.add_item(self.page_num)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            view = self.button.view
            num = int(self.page_num.value) - 1
            assert 0 <= num < len(view.embeds), await interaction.warn(
                "Please provide a **valid** number."
            )
            view.page = num
            await view.edit_embed(interaction)
        except AssertionError:
            pass


class Paginator(discord.ui.View):
    def __init__(
        self,
        embeds: Iterable[discord.Embed],
        destination,
        /,
        *,
        invoker: Optional[discord.Member] = None,
        attachments: Optional[Iterable] = None,
    ) -> None:
        super().__init__(timeout=30)
        self.attachments = attachments
        self.embeds = list(embeds)
        self.page = 0
        self.destination = destination
        self.invoker = invoker
        self.author_id = (
            destination.author.id if isinstance(destination, Context) else None
        )
        self.cache = {}
        self.message = None  # Initialize the message attribute

        if len(self.embeds) > 1:
            self.previous_page_button = discord.ui.Button(
                style=discord.ButtonStyle.grey, emoji=config.Emoji.Paginator.previous
            )
            self.previous_page_button.callback = self.previous_page
            self.add_item(self.previous_page_button)

            self.next_page_button = discord.ui.Button(
                style=discord.ButtonStyle.grey, emoji=config.Emoji.Paginator.next
            )
            self.next_page_button.callback = self.next_page
            self.add_item(self.next_page_button)

            self.goto_page_button = discord.ui.Button(
                style=discord.ButtonStyle.blurple,
                emoji=config.Emoji.Paginator.navigate,
            )
            self.goto_page_button.callback = self.goto_page
            self.add_item(self.goto_page_button)

            self.close_button = discord.ui.Button(
                style=discord.ButtonStyle.red, emoji=config.Emoji.Paginator.trash
            )
            self.close_button.callback = self.close_paginator
            self.add_item(self.close_button)

    async def previous_page(self, interaction: discord.Interaction):
        await self.change_page(interaction, self.page - 1)

    async def next_page(self, interaction: discord.Interaction):
        await self.change_page(interaction, self.page + 1)

    async def goto_page(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GotoModal(self.goto_page_button))

    async def change_page(self, interaction: discord.Interaction, page: int):
        await interaction.response.defer()
        self.page = page % len(self.embeds)
        await self.edit_embed(interaction)

    async def edit_embed(self, interaction: discord.Interaction) -> None:
        if self.page not in self.cache:
            current = self.embeds[self.page]
            kwargs = {"view": self}
            if self.attachments:
                kwargs["attachments"] = [self.attachments[self.page]]
            if isinstance(current, str):
                kwargs.update({"content": current, "embed": None})
            elif isinstance(current, discord.Embed):
                kwargs.update({"content": None, "embed": current})
            elif isinstance(current, tuple):
                kwargs.update(
                    {
                        k: v
                        for item in current
                        for k, v in (
                            ("content", item)
                            if isinstance(item, str)
                            else ("embed", item)
                        )
                    }
                )
            self.cache[self.page] = kwargs

        try:
            await interaction.response.edit_message(**self.cache[self.page])
        except discord.errors.InteractionResponded:
            await interaction.followup.edit_message(
                interaction.message.id, **self.cache[self.page]
            )

    async def start(self) -> None:
        try:
            current = self.embeds[self.page]
            kwargs = {"view": self}
            if self.attachments:
                kwargs["file"] = self.attachments[self.page]
            if isinstance(current, str):
                kwargs.update({"content": current, "embed": None})
            elif isinstance(current, discord.Embed):
                kwargs.update({"content": None, "embed": current})
            elif isinstance(current, tuple):
                kwargs.update(
                    {
                        k: v
                        for item in current
                        for k, v in (
                            ("content", item)
                            if isinstance(item, str)
                            else ("embed", item)
                        )
                    }
                )
            self.message = await self.destination.send(
                **kwargs
            )  # Set the message attribute
        except discord.HTTPException:
            self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.warn("You are not the **author** of this embed")
            return False
        return True

    async def close_paginator(self, interaction: discord.Interaction):
        await interaction.response.defer()
        if self.message:  # Ensure message exists before trying to delete
            await self.message.delete()
        self.stop()

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass
            except Exception as e:
                log.error(f"An error occurred in Paginator.on_timeout: {e}")
