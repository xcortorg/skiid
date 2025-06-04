from typing import TYPE_CHECKING, Any

import config
from config import Emoji
from discord import ButtonStyle, Interaction
from discord.ui import Button, View, button
from discord.ui.item import Item
from pomice import LoopMode, QueueEmpty, Track
from tools.client.context import Context
from tools.utilities.text import shorten

if TYPE_CHECKING:
    from ..player import Player


class Panel(View):
    """
    Music Player Controller Panel
    """

    def __init__(self, ctx: Context, player: "Player"):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.player = player

        self.play.emoji = (
            self.player.is_paused and Emoji.Music.PAUSED or Emoji.Music.UNPAUSED
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user not in self.player.channel.members:
            await interaction.response.send_message(
                **self.ctx.create(
                    description=f"{config.Emoji.warn} {interaction.user}: You must be in {self.player.channel.mention} to use this **panel*."
                ),
                ephemeral=True,
            )
        return interaction.user in self.player.channel.members

    async def on_error(self, _: Interaction, __: Exception, ___: Item[Any]) -> None: ...

    @button(emoji=Emoji.Music.PREVIOUS, style=ButtonStyle.gray)
    async def previous(self, interaction: Interaction, _: Button) -> None:
        empty = self.ctx.create(
            description=f"{config.Emoji.warn} {interaction.user}: No previous track to play"
        )

        if not self.player.history or len(self.player.history) == 0:
            return await interaction.response.send_message(
                **empty,
                ephemeral=True,
            )

        try:
            track: Track = self.player.history.get()
        except QueueEmpty:
            return await interaction.response.send_message(
                **empty,
                ephemeral=True,
            )

        self.player.queue.put_at_front(track)
        await self.player.stop()
        return await interaction.followup.send(
            **self.ctx.create(description="Playing previous track"), ephemeral=True
        )

    @button(emoji=Emoji.Music.UNPAUSED, style=ButtonStyle.gray)
    async def play(self, interaction: Interaction, button: Button) -> None:
        await self.player.set_pause(not self.player.is_paused)
        button.emoji = (
            self.player.is_paused and Emoji.Music.PAUSED or Emoji.Music.UNPAUSED
        )
        return await interaction.response.edit_message(view=self)

    @button(emoji=Emoji.Music.SKIP, style=ButtonStyle.gray)
    async def skip(self, interaction: Interaction, _: Button) -> None:
        await self.player.stop()
        return await interaction.followup.send(
            **self.ctx.create(description="Skipping to the next track"), ephemeral=True
        )
