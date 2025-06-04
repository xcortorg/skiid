from contextlib import suppress
from dataclasses import dataclass
from pydantic import BaseModel
from typing import List, Optional, cast

from pomice import Player as DefaultPlayer, QueueEmpty, Track, LoopMode
from pomice import Queue

from discord import Member, Message, HTTPException
from system.tools.utils import shorten_lower
from .panel import Panel
from system.base.context import Context
from system.tools.utils import format_duration, shorten


def pretty_source(track: Track) -> tuple[str | None, str | None]:
    track_type = str(track.track_type).lower()

    if track_type == "spotify":
        return (
            "Spotify",
            "https://cdn.discordapp.com/emojis/1307549140858961981.webp",
        )
    elif track_type == "applemusic":
        return (
            "Apple Music",
            "https://cdn.discordapp.com/emojis/1307549141307490376.webp",
        )
    elif track_type == "soundcloud":
        return (
            "SoundCloud",
            "https://cdn.discordapp.com/emojis/1307549138988171348.webp",
        )
    elif track_type.startswith("youtube"):
        return (
            "YouTube",
            "https://cdn.discordapp.com/emojis/1307549137977217045.webp",
        )
    return None, None


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
    pause_votes: List[Member] = []
    skip_votes: List[Member] = []
    resume_votes: List[Member] = []
    shuffle_votes: List[Member] = []
    stop_votes: List[Member] = []

    async def send_panel(self, track: Track) -> Optional[Message]:
        """Send the player controller panel to the channel."""
        if not self.context:
            return

        source_name, source_icon = pretty_source(track)
        safe_title = shorten(track.title, 20).replace("[", "(").replace("]", ")")
        return await self.context.embed(
            description=f"Now playing [`{safe_title}`]({track.uri})\n> by **{track.author}**",
            footer=track.requester
            and {
                "text": f"Queued by {track.requester.name} • {format_duration(track.length)} Remaining • {source_name}",
                "icon_url": source_icon,
            },
            image=track.thumbnail if track.thumbnail else None,
            view=Panel(self.context, self),
        )

    @property
    def requester(self) -> Optional[Member]:
        track = self.current
        if not track:
            return

        return track.requester

    async def skip(self, force: bool = False) -> None:
        """Skip the currently playing track."""
        if not force and self.queue.loop_mode == LoopMode.TRACK:
            return

        await self.stop()

    async def do_next(self) -> None:
        """Play the next track in the queue."""
        self.pause_votes.clear()
        self.skip_votes.clear()
        self.resume_votes.clear()
        self.shuffle_votes.clear()
        self.stop_votes.clear()

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
