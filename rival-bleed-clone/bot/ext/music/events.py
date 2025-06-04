from discord.ext.commands import (
    Cog,
)
from discord import (
    Client,
    VoiceState,
    Member,
)
from lib.classes import BleedPlayer
from pomice import Track, TrackType
from asyncio import sleep
from loguru import logger


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot

    @Cog.listener()
    async def on_pomice_track_end(
        self,
        player: BleedPlayer,
        track: Track,
        reason: str,
    ) -> None:
        logger.info(f"track ended due to {reason}")
        await player.next()

    async def check_future(self, player: BleedPlayer):
        await sleep(300)
        if not player.is_playing:
            await player.destroy()

    @Cog.listener()
    async def on_pomice_track_exception(self, player: BleedPlayer, track: Track):
        logger.info("track exception")
        if track.type == TrackType.SPOTIFY:
            results = await player.get_tracks(f"{track.title}")
            if results:
                try:
                    await player.play(results[0])
                except Exception:
                    await player.next()
            else:
                await player.next()

    @Cog.listener()
    async def on_pomice_track_stuck(self, player: BleedPlayer, track: Track):
        logger.info("track stuck")
        if track.type == TrackType.SPOTIFY:
            results = await player.get_tracks(f"{track.title}")
            if results:
                try:
                    await player.play(results[0])
                except Exception:
                    await player.next()
            else:
                await player.next()

    @Cog.listener()
    async def on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ) -> None:

        if not member.id == self.bot.user.id:
            return

        if not hasattr(self.bot, "node") or not (
            player := self.bot.node.get_player(member.guild.id)
        ):
            return

        if not after.channel:
            await player.destroy()
