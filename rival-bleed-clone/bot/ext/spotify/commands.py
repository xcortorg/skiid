from discord.ext.commands import Cog, CommandError, command, group, Boolean
from discord import Client, Member, Embed, File, User, Guild, Color
from tekore import AsyncSender, Credentials, Spotify
from .config import CLIENT_ID, CLIENT_SECRET, CLIENT_REDIRECT, get_token
from typing import Dict, Optional, Union, Any
from asyncio import Event, create_task, Task
from .models.user import SpotifyUser, Callback
from .views.Authenticate import AuthenticationView
from .views.Devices import DeviceView
from lib.patch.context import Context
import tekore


SCOPES = [
    "user-read-private",
    "user-top-read",
    "user-read-recently-played",
    "user-follow-read",
    "user-library-read",
    "user-read-currently-playing",
    "user-read-playback-state",
    "user-read-playback-position",
    "playlist-read-collaborative",
    "playlist-read-private",
    "user-follow-modify",
    "user-library-modify",
    "user-modify-playback-state",
    "playlist-modify-public",
    "playlist-modify-private",
    "ugc-image-upload",
]


class Commands(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.sender: AsyncSender = None
        self.spotify: Spotify = None
        self._credentials: Credentials = None
        self._tokens = (CLIENT_ID, CLIENT_SECRET, CLIENT_REDIRECT)
        self._token: str = None
        self._genres = None
        self.tasks: Dict[str, Task] = {}
        self._ready = Event()  # For delaying commands from working before its ready

    async def initialize(self) -> None:
        self.sender = AsyncSender()
        self._credentials = Credentials(*self._tokens, sender=self.sender)
        self._token = get_token()
        self.spotify = Spotify(self._token, sender=self.sender)
        self._ready.set()

    async def cog_load(self) -> None:
        await self.initialize()

    async def cog_unload(self) -> None:
        if self.sender:
            create_task(self.sender.aclose())

    async def cog_before_invoke(self, ctx: Context) -> None:
        await self._ready.wait()

    @group(
        name="spotify",
        aliases=["sp"],
        description="Control your music on Spotify through commands or search for a track. Get started with spotify login to connect your account.",
        example=",spotify yung purp",
        invoke_without_command=True,
    )
    async def spotify(self, ctx: Context, *, track: str):
        track = await self.spotify.search(query=track, types=("track",))
        return await ctx.send(track.items[0].url)

    @spotify.command(name="pause", description="Pause the current song")
    async def spotify_pause(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        await user.pause()
        return await ctx.message.add_reaction("⏸️")

    @spotify.command(name="resume", description="Resume the current song")
    async def spotify_resume(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        await user.resume()
        return await ctx.message.add_reaction("▶")

    @spotify.command(
        name="login",
        aliases=["connect"],
        description="Grant rival access to your Spotify account",
    )
    async def spotify_login(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, False)
        view = AuthenticationView(ctx, user)
        message = await ctx.spotify(
            f"Click [here]({user.auth_url}) to **grant** {self.bot.user.name.lower()} access to your **Spotify account**. Once you have received the code, please click the button below to **authenticate** yourself.",
            view=view,
        )
        view.message = message
        return await view.wait()

    @spotify.command(
        name="play",
        aliases=["p"],
        description="Immediately skip to the requested song",
        example=",spotify play montana of 300 goated up",
    )
    async def spotify_play(self, ctx: Context, *, track: str):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        tracks = await user.play(track)
        embeds = []
        total = len(tracks)
        for i, track in enumerate(tracks, start=1):
            embed = Embed(
                title=f"{track.name} by {'& '.join(f.name for f in track.artists)}",
                url=track.url,
            )
            embed.set_footer(text=f"Track {i} / {total}")
            embeds.append(embed)
        return await ctx.paginate(embeds)

    @spotify.command(
        name="next",
        aliases=["skip", "s", "sk", "n"],
        description="Immediately skip to the next song",
    )
    async def spotify_next(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        await user.next()
        return await ctx.message.add_reaction("⏭")

    @spotify.command(
        name="previous",
        aliases=["prev", "back", "b"],
        description="immediately go back one song",
    )
    async def spotify_previous(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        await user.previous()
        return await ctx.message.add_reaction("⏮")

    @spotify.command(
        name="repeat",
        description="Repeat the current song",
        example=",spotify repeat track",
    )
    async def spotify_repeat(self, ctx: Context, mode: str):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        if mode.lower() == "track":
            await user.repeat("track")
            emoji = ":repeat_one:"
        elif mode.lower() in ("queue", "all", "ctx", "context"):
            emoji = ":repeat:"
            await user.repeat("context")
        else:
            emoji = self.bot.config["emojis"]["fail"]
            await user.repeat("off")
        return await ctx.message.add_reaction(emoji)

    @spotify.command(name="shuffle", description="Toggle playback shuffle")
    async def spotify_shuffle(self, ctx: Context, option: Boolean):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        await user.shuffle(option)
        return await ctx.message.add_reaction(
            "🔀" if option else self.bot.config["emojis"]["fail"]
        )

    @spotify.command(
        name="logout",
        aliases=["reset"],
        description="Disconnect your Spotify from our servers",
    )
    async def spotify_logout(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM spotify WHERE user_id = $1""", ctx.author.id
        )
        return await ctx.success(
            f"successfully **DISCONNECTED** your spotify from our servers"
        )

    @spotify.command(
        name="queue",
        aliases=["q"],
        description="Queue a song",
        example=",spotify queue montana of 300 goated up",
    )
    async def spotify_queue(self, ctx: Context, *, track: str):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        tracks = await user.add(track)
        embeds = []
        total = len(tracks)
        for i, track in enumerate(tracks, start=1):
            embed = Embed(
                title=f"{track.name} by {'& '.join(f.name for f in track.artists)}",
                url=track.url,
            )
            embed.set_footer(text=f"Track {i} / {total}")
            embeds.append(embed)
        return await ctx.paginate(embeds)

    @spotify.command(
        name="seek",
        aliases=["ff", "rr", "rewind", "fastforward"],
        description="Seek to position in current song",
        example=",spotify seek +60",
    )
    async def spotify_seek(self, ctx: Context, position: str):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        try:
            current = await user.session.playback_currently_playing().position_ms
            if position.startswith("-"):
                position = int(position) * 1000
                new = int(current) - position
            else:
                position = int(position[1:]) * 1000
                new = int(current) + position
            await user.session.playback_seek(new)
            return await ctx.message.add_reaction("⏩")
        except Exception:
            return await ctx.message.add_reaction(self.bot.config["emojis"]["fail"])

    @spotify.command(
        name="volume",
        description="Adjust current player volume",
        aliases=["vol", "v"],
        example=",spotify volume 80",
    )
    async def spotify_volume(self, ctx: Context, volume: int):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        await user.set_volume(volume)
        return await ctx.message.add_reaction("🔊")

    @spotify.command(
        name="like", description="Like your current playing song on Spotify"
    )
    async def spotify_like(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        if not (current := await user.session.playback_current_playing()):
            raise CommandError("You are not currently listening to anything..")
        await user.session.saved_tracks_add(current.id)
        return await ctx.message.add_reaction("❤")

    @spotify.command(
        name="unlike",
        aliases=["dislike"],
        description="Unlike your current playing song on Spotify",
    )
    async def spotify_unlike(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        if not (current := await user.session.playback_current_playing()):
            raise CommandError("You are not currently listening to anything..")
        if await user.session.saved_tracks_contains(current.id):
            await user.session.saved_tracks_remove(current.id)
            return await ctx.success(
                f"successfully un-liked [**{current.name}** by {', '.join(f.name for f in current.artists)}]({current.preview_url})"
            )
        else:
            raise CommandError("you haven't liked the current track...")

    @spotify.group(
        name="device",
        description="Change the device that youre listening to Spotify with",
        invoke_without_command=True,
    )
    async def spotify_device(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        view = await DeviceView.initialize(ctx, user)
        return await ctx.spotify(f"select a device below", view=view)

    @spotify_device.command(
        name="list",
        description="List all current devices connected to your Spotify account",
    )
    async def spotify_device_list(self, ctx: Context):
        user = await SpotifyUser.get(self, ctx.author.id, True)
        devices = await user.session.devices()
        rows = [
            f"`{i}` **{device.device.name}(`{str(device.device.type)})"
            for i, device in enumerate(devices, start=1)
        ]
        embed = Embed(title=f"Connected Devices")
        return await ctx.paginate(embed, rows)
