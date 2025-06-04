from typing import TYPE_CHECKING, Any
from discord import Interaction, ButtonStyle, Embed
from discord.ui import View, button, Button
from discord.ui.item import Item
from pomice import LoopMode, QueueEmpty, Track

from config import Emojis
from system.base import Context

if TYPE_CHECKING:
    from ..player import Player


class Panel(View):
    """Music Player Controller Panel"""

    def __init__(self, ctx: Context, player: "Player"):
        super().__init__(timeout=None)
        self.ctx = ctx
        self.player = player

        self.play.emoji = (
            self.player.is_paused and Emojis.Music.PAUSED or Emojis.Music.UNPAUSED
        )

        self.mode.emoji = (
            self.player.queue.loop_mode == LoopMode.QUEUE
            and Emojis.Music.LOOP_QUEUE
            or self.player.queue.loop_mode == LoopMode.TRACK
            and Emojis.Music.LOOP_TRACK
            or Emojis.Music.NO_LOOP
        )

        self.mode.style = (
            self.player.queue.loop_mode == LoopMode.QUEUE
            and ButtonStyle.primary
            or self.player.queue.loop_mode == LoopMode.TRACK
            and ButtonStyle.primary
            or ButtonStyle.secondary
        )

    async def interaction_check(self, interaction: Interaction) -> bool:
        if not self.player.channel:
            await interaction.warn("I'm not connected to a voice channel.")
            return False

        if not interaction.user:
            return False

        if interaction.user not in self.player.channel.members:
            await interaction.warn(
                f"You must be in {self.player.channel.mention} to use this panel."
            )
            return False

        return True

    async def on_error(
        self, interaction: Interaction, error: Exception, _: Item[Any]
    ) -> None:
        await interaction.warn(f"An error occurred: {str(error)}")

    @button(emoji=Emojis.Music.SHUFFLE, style=ButtonStyle.secondary)
    async def shuffle(self, interaction: Interaction, _: Button) -> None:
        if not self.player.queue:
            return await interaction.warn("No tracks in the queue to shuffle")

        self.player.queue.shuffle()
        return await interaction.approve("Queue has been shuffled")

    @button(emoji=Emojis.Music.PREVIOUS, style=ButtonStyle.secondary)
    async def previous(self, interaction: Interaction, _: Button) -> None:
        if not self.player.history or len(self.player.history) == 0:
            return await interaction.warn("No previous track to play")

        try:
            track: Track = self.player.history.get()
        except QueueEmpty:
            return await interaction.warn("No previous track to play")

        self.player.queue.put_at_front(track)
        await self.player.stop()
        return await interaction.approve("Playing previous track")

    @button(emoji=Emojis.Music.UNPAUSED, style=ButtonStyle.primary)
    async def play(self, interaction: Interaction, button: Button) -> None:
        await self.player.set_pause(not self.player.is_paused)
        button.emoji = (
            self.player.is_paused and Emojis.Music.PAUSED or Emojis.Music.UNPAUSED
        )
        embed = Embed(
            description=f"{interaction.user.mention} has {'paused' if self.player.is_paused else 'resumed'} the current track"
        )
        await interaction.response.send_message(embed=embed, delete_after=4)
        await interaction.message.edit(view=self)

    @button(emoji=Emojis.Music.SKIP, style=ButtonStyle.secondary)
    async def skip(self, interaction: Interaction, _: Button) -> None:
        await self.player.stop()
        return await interaction.approve("Skipping to the next track")

    @button(emoji=Emojis.Music.NO_LOOP, style=ButtonStyle.secondary)
    async def mode(self, interaction: Interaction, button: Button) -> None:
        queue = self.player.queue

        if queue.loop_mode == LoopMode.QUEUE:
            queue.set_loop_mode(LoopMode.TRACK)
            button.emoji = Emojis.Music.LOOP_TRACK
            button.style = ButtonStyle.primary
        elif queue.loop_mode == LoopMode.TRACK:
            queue.disable_loop()
            button.emoji = Emojis.Music.NO_LOOP
            button.style = ButtonStyle.secondary
        else:
            queue.set_loop_mode(LoopMode.QUEUE)
            button.emoji = Emojis.Music.LOOP_QUEUE
            button.style = ButtonStyle.primary

        return await interaction.response.edit_message(view=self)
