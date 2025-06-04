from pydantic import BaseModel
from tekore import RefreshingCredentials, UserAuth, Token, Spotify
from tekore._model import Device
from typing import Optional, Tuple, Any, List, Dict, Union
from discord import Embed, Color
from discord.ext.commands import CommandError, Cog
from loguru import logger
from tekore._auth.scope import Scope
from .callback import Callback
from lib.classes.builtins import get_error
from lib.patch.context import Context
from ..config import CLIENT_ID, CLIENT_SECRET, CLIENT_REDIRECT, get_token
from datetime import timedelta, datetime, timezone
from lib.classes.color import get_dominant_color
from regex import Pattern

import re
import tekore

SPOTIFY_RE: Pattern[str] = re.compile(
    r"(https?:\/\/open\.spotify\.com\/|spotify:?)(track|playlist|album|artist|episode|show)\/?:?([^?\(\)\s]+)"
)  # CREDIT TRUSTY COGS


def format_time(time: str) -> list:
    time = time.split(".")[0].split(":")
    if time[0] == "0":
        return ":".join(time[1:])
    else:
        time[0] = "0" + time[0]  # add leading 0 to hour value
        return ":".join(time)
    return


class PlaybackDevice(BaseModel):
    device: Device


class SpotifyUser:
    def __init__(
        self,
        cog: Cog,
        user_id: int,
        user_token: Optional[Union[tekore.Token, RefreshingCredentials]] = None,
    ):
        self.cog = cog
        self.user_id = user_id
        self.user_token = user_token
        self.scopes = Scope(
            tekore.scope.user_read_currently_playing,
            tekore.scope.user_modify_playback_state,
            tekore.scope.user_read_playback_state,
        )
        self.default_device_id = None
        self.cred = get_token()
        self.auth: Optional[UserAuth] = UserAuth(self.cred, scope=self.scopes)
        self.session = Spotify(
            token=self.user_token or self.cred,
            sender=self.cog.sender,
            asynchronous=True,
        )
        self._volume: int = 100

    @property
    def auth_url(self) -> str:
        return self.auth.url

    @property
    def kwargs(self) -> Dict[str, Any]:
        if self.default_device_id:
            return {"device_id": self.default_device_id}
        else:
            return {}

    async def authorize(self, callback: Callback) -> Tuple[bool, Any]:
        try:
            _token = await self.auth.request_token(
                code=callback.code, state=callback.state
            )
            self.user_token = _token
            self.session = Spotify(
                token=_token, sender=self.cog.sender, asynchronous=True
            )
            await self.update()
        except Exception as error:
            return (False, get_error(error))
        return (True, None)

    async def refresh(self) -> bool:
        try:
            self.user_token = await self.cred.refresh_token(
                self.user_token.refresh_token
            )
            await self.update()
            return True
        except Exception as error:
            logger.error(f"Refreshing user token raised {get_error(error)}")
            return False

    async def update(self):
        return await self.cog.bot.db.execute(
            """INSERT INTO spotify (user_id, access_token, refresh_token, expiration, default_device_id) VALUES($1, $2, $3, $4, $5) ON CONFLICT(user_id) DO UPDATE SET access_token = excluded.access_token, refresh_token = excluded.refresh_token, expiration = excluded.expiration, default_device_id = excluded.default_device_id""",
            self.user_id,
            self.user_token.access_token,
            self.user_token.refresh_token,
            datetime.fromtimestamp(self.user_token.expires_at),
            self.default_device_id,
        )

    @classmethod
    async def get(cls, cog: Cog, user_id: int, check: Optional[bool] = False):
        if data := await cog.bot.db.fetchrow(
            """SELECT * FROM spotify WHERE user_id = $1""", user_id
        ):
            token = Token(
                {
                    "token_type": "Bearer",
                    "access_token": data.access_token,
                    "refresh_token": data.refresh_token,
                    "expires_in": int(data.expiration.timestamp()),
                },
                uses_pkce=False,
            )
            _ = cls(cog, user_id, token)
            _.session = Spotify(token=token, sender=_.cog.sender, asynchronous=True)
            return _
        else:
            if check:
                raise CommandError(
                    "you have not linked your spotify account using `spotify login`"
                )
            return cls(cog, user_id)

    async def devices(self) -> List[PlaybackDevice]:
        devices = await self.session.devices()
        _ = []
        for device in devices:
            _.append(
                PlaybackDevice(device=device, default=True)
                if device.id == self.default_device_id
                else PlaybackDevice(device=device)
            )
        return _

    async def set_device(self, device: PlaybackDevice):
        self.default_device_id = device.id
        await self.session.playback_transfer(self.default_device_id)
        await self.update()

    def get_progress(self, progress: int, duration: int) -> str:
        _prog = progress * 10 // duration
        bot = self.cog.bot
        bar = [
            bot.config["emojis"]["white_left"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_regular"],
            bot.config["emojis"]["white_right"],
        ]
        if _prog < 1:
            return "".join(b for b in bar)
        bright = bot.config["emojis"]["pink_right"]
        bleft = bot.config["emojis"]["pink_left"]
        blue = bot.config["emojis"]["pink_regular"]
        if _prog > 2:
            bar[0] = bleft
        string = str(_prog)
        total = string[0]
        total = int(total)
        if _prog > 10:
            if _prog != 100:
                for i in range(total):
                    if i == 9:
                        bar[i] = bright
                    elif i == 0:
                        bar[i] = bleft
                    else:
                        bar[i] = blue
            else:
                bar[0] = bleft
                for i in range(total):
                    if i == 0:
                        bar[i] = bleft
                    elif i == 9:
                        bar[i] = bright
                    else:
                        bar[i] = blue
        return "".join(b for b in bar)

    async def nowplaying(self, ctx: Context) -> Embed:
        item = await self.session.playback()
        track = item.item
        if not (track := item.item):
            raise CommandError("Nothing is currently playing..")
        is_local_track = isinstance(track, tekore.model.LocalTrack)
        if track.type == "track":
            artists = ", ".join([artist.name for artist in track.artists]).strip(", ")
            album_art = track.album.images[0].url if not is_local_track else None
            show_artist_url = f"https://open.spotify.com/artist/{track.artists[0].id}"
            album_name = track.album.name
        elif track.type == "episode":
            artists = track.show.name
            album_art = track.images[0].url
            show_artist_url = f"https://open.spotify.com/show/{track.show.id}"
            album_name = None
        embed = Embed(
            title="Now Playing", color=Color.from_str(await get_dominant_color())
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        progress_bar = self.get_progress(item.progress_ms, track.duration_ms)
        track_url = f"https://open.spotify.com/{track.type}/{track.id}"
        embed.add_field(
            name="Track",
            value=(
                f"[{track.name}]({track_url})\n[**{artists}**]({show_artist_url})"
                + (f" | *{album_name}*" if album_name else "")
                if not is_local_track
                else f"{track.name}\n**{artists}**"
            ),
        )
        progress = format_time(timedelta(milliseconds=item.progress_ms).__str__())
        duration = format_time(timedelta(milliseconds=track.duration_ms).__str__())
        embed.add_field(name="Progress", value=f"{progress_bar}")
        embed.set_footer(text=f"{progress}/{duration}")
        embed.set_thumbnail(url=album_art)
        embed.url = track_url
        return embed

    async def previous(self):
        return await self.session.playback_previous(**self.kwargs)

    async def next(self):
        return await self.session.playback_next(**self.kwargs)

    async def pause(self):
        return await self.session.playback_pause(**self.kwargs)

    async def resume(self):
        return await self.session.playback_resume(**self.kwargs)

    async def queue(self):
        return await self.session.playback_queue(**self.kwargs)

    async def search(self, query: str):
        song_data = SPOTIFY_RE.finditer(query)
        tracks = []
        albums = []
        playlists = []
        if song_data:
            new_uri = ""
            for match in song_data:
                new_uri = f"spotify:{match.group(2)}:{match.group(3)}"
                if match.group(2) == "track":
                    tracks.append(match.group(3))
                if match.group(2) == "album":
                    albums.append(match.group(3))
                if match.group(2) == "playlist":
                    playlists.append(match.group(3))

        if tracks:
            return await self.session.track(tracks[0])
        elif albums:
            return self.session.album_tracks(albums[0])
        elif playlists:
            return await self.session.playlist_items(playlists[0])
        else:
            types = ("album", "track")
            d = await self.session.search(query, types=types)
            if hasattr(d, "items"):
                return d.items
            else:
                if hasattr(d[0], "items"):
                    return d[0].items
                return d

    async def add(self, query: str):
        tracks = await self.search(query)
        _ = [t.id for t in tracks]
        await self.session.playback_start_tracks(_, **self.kwargs)
        return tracks

    async def play(self, query: str):
        try:
            tracks = await self.search(query)
            await self.session.playback_start_tracks(
                [t.id for t in tracks], **self.kwargs
            )
            return tracks
        except Exception as e:
            if "premium" in str(e).lower():
                raise CommandError("You don't have spotify premium which is required!")
            else:
                raise e

    async def set_volume(self, value: int):
        self._volume = value
        return await self.session.playback_volume(value, **self.kwargs)

    async def repeat(self, mode: str):
        return await self.session.playback_repeat(mode, **self.kwargs)

    async def shuffle(self, state: bool):
        return await self.session.playback_shuffle(state, **self.kwargs)

    @property
    def volume(self) -> int:
        return self._volume
