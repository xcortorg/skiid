from contextlib import suppress
from dataclasses import dataclass
from typing import List, Optional, cast

from discord import HTTPException, Member, Message
from pomice import Player as DefaultPlayer
from pomice import Queue, QueueEmpty, Track
from pydantic import BaseModel
from tools.client.context import Context
from tools.utilities import format_duration
from tools.utilities.text import shorten

from .panel import Panel


class Player(DefaultPlayer):
    """
    Extended Pomice Player Class For Added Functionality

    Created with documentation help from https://github.com/cloudwithax/pomice/blob/main/examples/advanced.py
    """

    queue: Queue = Queue()
    history: Queue = Queue()
    controller: Optional[Message] = None
    context: Optional[Context] = None
    dj: Optional[Member] = None
    pause_votes: Optional[List[Member]] = []
    skip_votes: Optional[List[Member]] = []
    resume_votes: Optional[List[Member]] = []
    shuffle_votes: Optional[List[Member]] = []
    stop_votes: Optional[List[Member]] = []

    async def send_panel(self, track: Track) -> Optional[Message]:
        """Send the player controller panel to the channel."""
        if not self.context:
            return

        return await self.context.embed(
            description=f"Now playing [`{shorten(track.title)}`]({track.uri}) by **{track.author}**",
            footer=track.requester
            and {
                "text": f"Queued by {track.requester.name} • {format_duration(track.length)} Remaining",
                "icon_url": getattr(track.requester.avatar, "url", None),
            },
            view=Panel(self.context, self),
        )

    async def do_next(self) -> None:
        """Play the next track in the queue."""
        self.pause_votes = []
        self.skip_votes = []
        self.resume_votes = []
        self.shuffle_votes = []
        self.stop_votes = []

        if self.controller:
            with suppress((HTTPException), (KeyError)):
                await self.controller.delete()

        try:
            track: Track = self.queue.get()
            self.history.put(track)
        except QueueEmpty:
            return await self.teardown()

        await self.play(track)
        self.controller = await self.send_panel(track)

        if self.channel:  # Add channel check
            await self.channel.edit(status=f"{track.title} by {track.author}")

    async def teardown(self):
        """Clear internal states, remove player controller and disconnect."""
        with suppress((HTTPException), (KeyError)):
            await self.destroy()
            if self.controller:
                await self.controller.delete()

    async def set_context(self, ctx: Context):
        """Set context for the player"""
        self.context = ctx
        self.dj = cast(Member, ctx.author)


__all__ = ("Player", "Panel")
