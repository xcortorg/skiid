from discord.ext.commands import (
    Cog,
    command,
    group,
    CommandError,
    Position,
    Percentage,
    Boolean,
)
from discord import Client, Embed, Message, Attachment
from lib.patch.context import Context
import random
from tuuid import tuuid
from pomice import NodePool, NoNodesAvailable, Playlist, Track
from typing import Literal, Optional, Union, List
from loguru import logger
from lib.classes.processing import shorten, human_timedelta, format_duration
from datetime import datetime, timedelta
from lib.classes.music import Filters, BleedPlayer


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    async def check_node(self):
        logger.info("Lavalink is starting.")
        if not hasattr(self.bot, "node"):
            spotify = self.bot.config.get("spotify")
            if spotify is None:
                self.bot.node = await NodePool().create_node(
                    bot=self.bot,
                    host="127.0.0.1",
                    port=2333,
                    password="youshallnotpass",
                    identifier=f"MAIN{tuuid()}",
                    spotify_client_id="",
                    spotify_client_secret="",
                    apple_music=True,
                )
            else:
                self.bot.node = await NodePool().create_node(
                    bot=self.bot,
                    host="127.0.0.1",
                    port=2333,
                    password="youshallnotpass",
                    identifier=f"MAIN{tuuid()}",
                    spotify_client_id="",
                    spotify_client_secret="",
                    apple_music=True,
                )
                logger.info("Lavalink has connected successfully")

    async def cog_load(self):
        await self.check_node()

    async def get_player(self, ctx: Context, *, connect: bool = False) -> BleedPlayer:
        if not hasattr(self.bot, "node"):
            raise CommandError(
                "The **connection** to the **node** hasn't been established!"
            )

        if not (voice := ctx.author.voice):
            raise CommandError("You're not connected to a **voice channel**!")

        elif (bot_voice := ctx.guild.me.voice) and (
            voice.channel.id != bot_voice.channel.id
        ):
            raise CommandError("You're not connected to my **voice channel**!")

        if not ctx.guild.me.voice or not (
            player := self.bot.node.get_player(ctx.guild.id)
        ):
            if not connect:
                raise CommandError("I'm not connected to a **voice channel**!")
            else:
                try:
                    await ctx.author.voice.channel.connect(
                        cls=BleedPlayer, self_deaf=True
                    )
                except NoNodesAvailable:
                    raise CommandError(
                        "The **connection** to the **node** hasn't been established!"
                    )

                player = self.bot.node.get_player(ctx.guild.id)
                player.invoke_id = ctx.channel.id
                await player.set_volume(65)

        return player

    @command(name="current")
    async def current(self, ctx: Context) -> Message:
        """
        View the current track
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not player.current:
            return await ctx.fail("Nothing is **currently** playing!")

        return await ctx.channel.normal(
            f"Currently playing [**{player.current.title}**]({player.current.uri}) in {player.channel.mention} [{player.current.requester.mention}]",
        )

    @command(
        name="repeat",
        example=",repeat queue",
        aliases=["loop", "lp"],
        description="Change the current loop mode",
    )
    async def repeat(self, ctx: Context, option: Literal["track", "queue", "off"]):

        player: BleedPlayer = await self.get_player(ctx)

        if option == "off":
            if not player.loop:
                return await ctx.fail("There isn't an active **loop**")
        elif option == "track":
            if not player.is_playing:
                return await ctx.fail("There isn't an active **track**")
        elif option == "queue":
            if not player.queue._queue:
                return await ctx.fail("There aren't any **tracks** in the queue")

        await ctx.message.add_reaction(
            "✅" if option == "off" else "🔂" if option == "track" else "🔁"
        )
        await player.set_loop(option if option != "off" else False)

    async def handle_attachment(self, ctx: Context) -> Optional[str]:
        if len(ctx.message.attachments) == 0:
            return
        for attachment in ctx.message.attachments:
            if attachment.filename.endswith(".mp3"):
                return attachment.proxy_url
            else:
                return await ctx.fail("Only **MP3's** can be played")

    @command(
        name="play",
        usage="(query)",
        example=",play Yeat Out thë way",
        aliases=[
            "p",
        ],
    )
    async def play(self, ctx: Context, *, query: Union[str, Attachment] = None) -> None:
        """
        Queue a track
        """

        player: BleedPlayer = await self.get_player(ctx, connect=True)

        if not query:
            query = await self.handle_attachment(ctx)
            if not query:
                return await ctx.send_help(ctx.command.qualified_name)

        elif not isinstance(query, str):
            query = query.url
        if "open.spotify.com" in query:
            query = await player.scrape_spotify(query)
        try:
            result: Union[List[Track], Playlist] = await player.get_tracks(
                query=query, ctx=ctx
            )
        except Exception:
            return await ctx.fail("No **results** were found")

        if not result:
            return await ctx.fail("No **results** were found")

        if isinstance(result, Playlist):
            for track in result.tracks:
                await player.insert(track)

            await ctx.channel.normal(
                f"Enqueued **{result.track_count} tracks** from [**{result.name}**]({result.uri}) [{track.requester.mention}]",
            )

        else:
            track = result[0]
            await player.insert(track)
            if player.is_playing:
                await ctx.channel.normal(
                    f"Enqueued [**{track.title}**]({track.uri}) [{track.requester.mention}]",
                )

        if not player.is_playing:
            await player.next()

    @command(
        name="fastforward",
        usage="(position)",
        example=",fastforward 30s",
        aliases=[
            "ff",
        ],
    )
    async def fastforward(self, ctx: Context, position: str) -> None:
        """
        fast forward to a specific position
        """

        player: BleedPlayer = await self.get_player(ctx)
        position = f"+{position}"
        position = await Position().convert(ctx, position)
        if not player.current:
            return await ctx.fail("Nothing is **currently** playing!")

        await player.seek(max(0, min(position, player.current.length)))
        await ctx.message.add_reaction("✅")

    @command(
        name="rewind",
        usage="(position)",
        example=",rewind 30s",
        aliases=[
            "rw",
        ],
    )
    async def rewind(self, ctx: Context, position: str) -> None:
        """
        rewind to a specific position
        """

        player: BleedPlayer = await self.get_player(ctx)
        position = f"-{position}"
        position = await Position().convert(ctx, position)
        if not player.current:
            return await ctx.fail("Nothing is **currently** playing!")

        await player.seek(max(0, min(position, player.current.length)))
        await ctx.message.add_reaction("✅")

    @command(
        name="skip",
        aliases=["sk"],
    )
    async def skip(self, ctx: Context) -> None:
        """
        Skip the current track
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not player.queue._queue:
            return await ctx.fail("The **queue** is empty!")

        await player.skip()
        await ctx.message.add_reaction("⏩")

    @command(name="pause", aliases=["stop"])
    async def pause(self, ctx: Context) -> None:
        """
        Pause the track
        """

        player: BleedPlayer = await self.get_player(ctx)

        if player.is_paused:
            return await ctx.fail("There isn't a **track** playing")

        await player.set_pause(True)
        await ctx.message.add_reaction("⏸️")

    @command(
        name="resume",
        aliases=["unpause"],
    )
    async def resume(self, ctx: Context) -> None:
        """
        Resume the track
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not player.is_paused:
            return await ctx.fail("The **track** isn't paused")

        await player.set_pause(False)
        await ctx.message.add_reaction("⏯️")

    @group(
        name="queue", description="View all tracks queued", invoke_without_command=True
    )
    async def queue(self, ctx: Context) -> None:
        player: BleedPlayer = await self.get_player(ctx)
        if not (queue := player.queue._queue) and not (track := player.current):
            return await ctx.send_help()
        if not queue:
            queue = []
        tracks = list()
        if track := player.current:
            tracks.append(
                f"Listening to: [**{shorten(track.title, 23)}**]({track.uri}) "
                + (
                    f"by **{track.author}** "
                    if track.track_type.value == "spotify"
                    else ""
                )
                + f"[{track.requester.mention}]\n"
                + (
                    (
                        "**"
                        + human_timedelta(
                            datetime.now()
                            - timedelta(
                                seconds=(
                                    int(track.length / 1000)
                                    - int(player.position / 1000)
                                )
                            ),
                            suffix=False,
                        )
                        + f"** left of this track `{format_duration(player.position)}`/`{format_duration(track.length)}`\n"
                    )
                    if not track.is_stream
                    else ""
                )
            )

        for track in queue:
            tracks.append(
                f"`{len(tracks)}` [**{shorten(track.title, 23)}**]({track.uri}) - {track.requester.mention}"
            )

        return await ctx.paginate(
            Embed(
                title=f"Queue in {player.channel.name}",
            ),
            tracks,
            10,
            "track",
        )

    @queue.command(
        name="shuffle",
        aliases=["mix"],
    )
    async def shuffle(self, ctx: Context) -> None:
        """
        Shuffle the music queue
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not (queue := player.queue._queue):
            return await ctx.fail("The **queue** is empty!")

        random.shuffle(queue)
        await ctx.message.add_reaction("🔀")

    @queue.command(
        name="move",
        usage="(track index) (new index)",
        example=",queue move 2 1",
    )
    async def move(self, ctx: Context, index: int, new_index: int) -> Message:
        """
        Move a track in the queue
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not (queue := player.queue._queue):
            return await ctx.fail("The **queue** is empty!")

        if index < 1 or index > len(queue):
            return await ctx.fail(
                f"The **index** must be between `1` and `{len(queue)}`"
            )

        if new_index < 1 or new_index > len(queue):
            return await ctx.fail(
                f"The **new index** must be between `1` and `{len(queue)}`"
            )

        track = queue[index - 1]
        del queue[index - 1]
        queue.insert(new_index - 1, track)

        return await ctx.success(
            f"Moved [**{track.title}**]({track.uri}) to index `{new_index}`"
        )

    @queue.command(
        name="remove",
        usage="(track index)",
        example=",queue remove 2",
    )
    async def remove(self, ctx: Context, index: int) -> Message:
        """
        Remove a track from the queue
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not (queue := player.queue._queue):
            return await ctx.fail("The **queue** is empty!")

        if index < 1 or index > len(queue):
            return await ctx.fail(
                f"The **index** must be between `1` and `{len(queue)}`"
            )

        track = queue[index - 1]
        del queue[index - 1]

        return await ctx.success(
            f"Removed [**{track.title}**]({track.uri}) from the queue"
        )

    @command(
        name="volume",
        usage="<percentage>",
        example=",volume 45%",
        aliases=[
            "vol",
            "v",
        ],
    )
    async def volume(self, ctx: Context, volume: Percentage = None) -> Message:
        """
        Adjust the track volume
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not player.is_playing:
            return await ctx.fail("There isn't a **track** playing")

        elif not volume:
            return await ctx.normal(f"Volume: `{player.volume}%`")

        await player.set_volume(volume)
        await ctx.success(f"Set the **volume** to `{volume}%`")

    @command(name="clear")
    async def clear(self, ctx: Context) -> None:
        """
        Clear the queue
        """

        player: BleedPlayer = await self.get_player(ctx)

        if not (queue := player.queue._queue):
            return await ctx.fail("The **queue** is empty!")

        queue.clear()
        await ctx.message.add_reaction("🧹")

    @command(name="disconnect", aliases=["dc"])
    async def disconnect(self, ctx: Context) -> None:
        """
        Disconnect the player
        """

        player: BleedPlayer = await self.get_player(ctx)

        await player.destroy()
        await ctx.message.add_reaction("👋")

    async def clear_filters(self, ctx: Context, player: BleedPlayer):
        try:
            return player.filters.reset_filters()
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            pass

    @group(
        name="preset", description="Use a preset for Music", invoke_without_command=True
    )
    async def preset(self, ctx: Context):
        return await ctx.send_help()

    @preset.command(
        name="vibrato",
        description="Introduces a wavering pitch effect for dynamic tone",
        example=",preset vibrato True",
    )
    async def vibrato(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.vibrato)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="metal",
        description="Amplifies midrange for a fuller, concert-like sound, ideal for metal track",
        example=",preset metal True",
    )
    async def metal(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.metal)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="flat",
        description="Represents a normal EQ setting with default levels across the board",
        example=",preset flat True",
    )
    async def flat(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.flat)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="vaporwave",
        description="Slows track playback for nostalgic and vintage half-speed effect",
        example=",preset vaporwave True",
    )
    async def vaporwave(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.vaporwave)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="nightcore",
        description="Accelerates track playback for nightcore-style music",
        example=",preset nightcore True",
    )
    async def nightcore(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.nightcore)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="soft",
        description="Cuts high and mid frequencies, allowing only low frequencies",
        example=",preset soft True",
    )
    async def soft(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.soft)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="boost",
        description="Enhances track with heightened bass and highs for a lively, energetic feel",
        example=",preset boost True",
    )
    async def boost(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.boost)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="8d",
        aliases=["eightd"],
        description="Creates a stereo-like panning effect, rotating audio for immersive sound",
        example=",preset 8d True",
    )
    async def eightd(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.eightd)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="chipmunk",
        description="Accelerates track playback to produce a high-pitched, chipmunk-like sound",
        example=",preset chipmunk True",
    )
    async def chipmunk(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.chipmunk)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="piano",
        description="Enhances mid and high tones for standout piano-based tracks",
        example=",preset piano True",
    )
    async def piano(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.piano)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="karaoke",
        description="Filters out vocals from the track, leaving only the instrumental",
        example=",preset karaoke True",
    )
    async def karaoke(self, ctx: Context, setting: Boolean):
        player: BleedPlayer = await self.get_player(ctx)
        await self.clear_filters(ctx, player)
        if setting:
            await player.add_filter(Filters.karaoke)
        await ctx.message.add_reaction("✅")

    @preset.command(
        name="active",
        aliases=["list", "l", "show", "view"],
        description="List all currently applied filters",
    )
    async def active(self, ctx: Context):
        player: BleedPlayer = await self.get_player(ctx)
        filters = await player.get_filters()
        if not filters:
            raise CommandError("You have not set any filters")
        await ctx.normal(f"Your current filter is set to {filters}")
