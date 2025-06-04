import math
from typing import Literal, Optional, Union, cast

from discord import Member, Message, VoiceChannel
from discord.ext.commands import Cog, check, command, group
from discord.utils import format_dt
from humanize import ordinal
from pomice import LoopMode, NodePool, Playlist, Timescale
from tools.client.context import Context
from tools.managers.paginator import Paginator
from tools.utilities import format_duration, pluralize
from tools.utilities.text import shorten

from .player import Panel, Player


def player():
    async def predicate(ctx: Context) -> bool:
        if not ctx.voice_client:
            await ctx.warn(f" I need to be in a **voice channel**!")
        return True if ctx.voice_client else False

    return check(predicate)  # type: ignore


class Music(Cog):
    """
    Play a selection of songs in a voice channel with felony
    """

    pomice: NodePool = NodePool()

    async def cog_check(self, ctx: Context) -> bool:  # type: ignore
        if not self.pomice.nodes:
            await ctx.warn(
                "No **Nodes** has been created. Please wait for a **full** startup."
            )
        return True if self.pomice.nodes else False

    def required(self, ctx: Context):
        """Method which returns required votes based on amount of members in a channel."""
        # Remove the incorrect condition that was preventing the method from working
        if not ctx.voice_client:
            return 0

        player = cast(Player, ctx.voice_client)
        channel = self.bot.get_channel(int(player.channel.id))

        if not isinstance(channel, VoiceChannel):
            return 0

        required = math.ceil((len(channel.members) - 1) / 2.5)

        if ctx.command and ctx.command.name == "stop":
            if len(channel.members) == 3:
                required = 2

        return required

    def is_privileged(self, ctx: Context):
        """Check whether the user is an Admin or DJ."""
        player = cast(Player, ctx.voice_client)

        if not isinstance(ctx.author, Member):
            return

        return player.dj == ctx.author or ctx.author.guild_permissions.kick_members

    @Cog.listener()
    async def on_pomice_track_end(self, player: Player, track, _):
        await player.do_next()

    @Cog.listener()
    async def on_pomice_track_stuck(self, player: Player, track, _):
        await player.teardown()

    @Cog.listener()
    async def on_pomice_track_exception(self, player: Player, track, _):
        await player.teardown()

    @command(aliases=("p",), example="Star Boy - XTC")
    async def play(
        self, ctx: Context, next: Optional[Literal["next"]] = None, *, query: str = None
    ) -> Optional[Message]:
        """
        Queue a track
        Parameters
        ----------
        next: Optional[str]
            If "next" is specified, the track will be added to the front of the queue
        query: str
            The song to search for
        """

        assert isinstance(ctx.author, Member), "Author must be a member."

        # Handle attachments from current message or referenced message
        if not query and next:
            query = next
            next = None
        if not query:
            if ctx.message.attachments:
                query = ctx.message.attachments[0].url
            elif (
                hasattr(ctx.message.reference, "resolved")
                and ctx.message.reference.resolved
            ):
                referenced_msg = ctx.message.reference.resolved
                if (
                    hasattr(referenced_msg, "attachments")
                    and referenced_msg.attachments
                ):
                    query = referenced_msg.attachments[0].url

        if not (player := cast(Player, ctx.voice_client)):
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.warn("You are not **connected** to a voice channel.")
            await ctx.author.voice.channel.connect(cls=Player)  # type: ignore
            player = cast(Player, ctx.voice_client)
            await player.set_context(ctx)

        if not query:
            return await ctx.send_help(ctx.command)

        if player.channel != getattr(ctx.author.voice, "channel", None):
            return await ctx.warn(
                "You must be in the same voice channel as the bot to **play** a song."
            )

        node = self.pomice.get_node()
        if not (results := await node.get_tracks(query, ctx=ctx)):
            return await ctx.warn(f"Couldn't find any results for **{query}**.")

        tracks = results.tracks if isinstance(results, Playlist) else [results[0]]

        # Add tracks to queue based on 'next' parameter
        for track in tracks:
            if next:
                player.queue.put_at_front(track)
            else:
                player.queue.put(track)

        # Update response message
        if isinstance(results, Playlist):
            position = "start of" if next else "end of"
            await ctx.neutral(f"Added `{results.name}` to the {position} queue")
        else:
            position = 1 if next else len(player.queue)
            await ctx.neutral(
                f"Added [`{shorten(results[0].title)}`]({results[0].uri}) to `{ordinal(position)}` in the queue"
            )

        if not player.is_playing:
            await player.do_next()

    @command()
    @player()
    async def stop(self, ctx: Context) -> Message:
        """
        Stop the player and clear the queue.
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to stop the player.")

        await player.teardown()
        return await ctx.add_check()

    @command()
    @player()
    async def skip(self, ctx: Context) -> Message:
        """
        Skip the current track.
        """

        player = cast(Player, ctx.voice_client)

        if self.is_privileged(ctx) or len(player.skip_votes) >= self.required(ctx):  # type: ignore
            await player.stop()
            return await ctx.add_check()

        if ctx.author in player.skip_votes:  # type: ignore
            return await ctx.warn("You have already voted to skip this track.")

        player.skip_votes.append(ctx.author)  # type: ignore

        return await ctx.approve(
            f"Voted to skip the current track. **{len(player.skip_votes)}** {pluralize('vote', len(player.skip_votes))} received, **{self.required(ctx)}** required."  # type: ignore
        )

    @command(aliases=("vol", "v"))
    @player()
    async def volume(self, ctx: Context, volume: int) -> Message:
        """
        Set the volume of the player.
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to change the volume.")

        if not 0 <= volume <= 100:
            return await ctx.warn("Volume must be between 0 and 100.")

        await player.set_volume(volume)
        return await ctx.add_check()

    @command()
    @player()
    async def pause(self, ctx: Context) -> Message:
        """
        Pause the current track.
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to pause the player.")

        await player.set_pause(True)
        return await ctx.approve("Paused the player.")

    @command()
    @player()
    async def resume(self, ctx: Context) -> Message:
        """
        Resume the current track.
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to resume the player.")

        await player.set_pause(False)
        return await ctx.approve("Resumed the player.")

    @command()
    @player()
    async def shuffle(self, ctx: Context) -> Message:
        """
        Shuffle the queue.
        """

        assert isinstance(ctx.author, Member), "Author must be a member."
        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn(
                "You do not have **permission** to shuffle the queue."
            )

        if not player.queue:
            return await ctx.warn("No **tracks** are in the queue.")

        player.queue.shuffle()
        return await ctx.add_check()

    @command()
    @player()
    async def repeat(self, ctx: Context, option: str = "off") -> Message:
        """
        Set the loop mode of the player.
        Options: off, queue, current
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to change the loop mode.")

        # Convert input to lowercase and validate
        option = option.lower()
        valid_options = ["off", "queue", "current"]
        if option not in valid_options:
            return await ctx.warn(
                f"**option** must be one of: {', '.join(f'`{opt}`' for opt in valid_options)}"
            )

        # Map user input to LoopMode
        mode_map = {"off": None, "queue": LoopMode.QUEUE, "current": LoopMode.TRACK}

        mode = mode_map[option]
        if mode is None:
            if player.queue.loop_mode is None:
                return await ctx.warn("The **queue loop** is already disabled.")
            player.queue.disable_loop()
        else:
            player.queue.set_loop_mode(mode)

        await player.controller.edit(view=Panel(player.context, player))  # type: ignore
        return await ctx.approve(f"Set loop mode to **{option}**.")

    @group(aliases=("q",), invoke_without_command=True)
    async def queue(self, ctx: Context) -> Union[Message, Paginator]:
        """View all songs in the queue."""

        if not ctx.voice_client:
            return await ctx.warn("There are no tracks in the queue.")

        player = cast(Player, ctx.voice_client)
        queue = player.queue

        if not player.current and not queue:
            return await ctx.warn("No tracks are in the queue")

        # Create track list for pagination
        tracks = [
            f"`{idx + 1}` [`{shorten(track.title)}`]({track.uri}) by **{track.author}** {track.requester and f'[{track.requester.mention}]' or ''}"
            for idx, track in enumerate(queue)
        ]

        embeds = []
        base_description = ""
        if current_track := player.current:
            base_description = (
                f"**Listening** to [`{shorten(current_track.title)}`]({current_track.uri}) "
                f"[`{format_duration(player.position)}/{format_duration(current_track.length)}`]\n"
            )
            total_duration = sum(track.length for track in queue) + (
                current_track.length - player.position
            )
            footer_text = (
                f"{format_duration(total_duration)} remaining • {len(queue)} tracks"
            )
        else:
            footer_text = f"{len(queue)} tracks"

        for i in range(0, len(tracks), 10):
            page_tracks = tracks[i : i + 10]
            embed = ctx.create(
                title=f"**Queue**",
                description=base_description + "\n".join(page_tracks),
            )["embed"]
            embed.set_footer(text=footer_text)
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )
            embeds.append(embed)

        if not embeds:
            embed = ctx.create(title=f"**Queue**", description=base_description)[
                "embed"
            ]
            embed.set_footer(text=footer_text)
            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )
            embeds.append(embed)

        paginator = Paginator(embeds, ctx)
        await paginator.start()
        return paginator

    @queue.command(name="clear", aliases=("empty",))
    @player()
    async def queue_clear(self, ctx: Context) -> Message:
        """
        Clear the queue.
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to clear the queue.")

        player.queue.clear()
        return await ctx.approve("Cleared the queue.")

    @queue.command(name="remove")
    @player()
    async def queue_remove(self, ctx: Context, index: int) -> Message:
        """
        Remove a track from the queue.
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn(
                "You do not have permission to remove tracks from the queue."
            )

        if not (track := player.queue[index]):
            return await ctx.warn(f"Track at index **{index}** doesn't exist.")

        player.queue.remove(track)
        return await ctx.approve(f"Removed **{track.title}** from the queue.")

    @queue.command(name="move")
    @player()
    async def queue_move(self, ctx: Context, index: int, new_index: int) -> Message:
        """
        Move a track in the queue.
        """

        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn(
                "You do not have permission to move tracks in the queue."
            )

        if not (track := player.queue[index]):
            return await ctx.warn(f"Track at index **{index}** doesn't exist.")

        player.queue.put_at_index(new_index, track)
        return await ctx.approve(f"Moved **{track.title}** to index **{new_index}**.")

    @queue.command(name="shuffle")
    @player()
    async def queue_shuffle(self, ctx: Context) -> Message:
        """
        Shuffle all tracks in the queue.
        """
        player = cast(Player, ctx.voice_client)

        if not self.is_privileged(ctx):
            return await ctx.warn("You do not have permission to shuffle the queue.")

        if not player.queue:
            return await ctx.warn("There are no **tracks** in the queue to shuffle.")

        player.queue.shuffle()
        return await ctx.approve("Shuffled all **tracks** in the queue.")

    @group(
        usage="(subcommand) (args)",
        examples="nightcore on",
        invoke_without_command=True,
    )
    @player()
    async def preset(self, ctx: Context) -> Optional[Message]:
        """
        Use a preset for Music
        """
        return await ctx.send_help(ctx.command)

    @preset.command(name="vaporwave")
    @player()  # Add the player decorator
    async def preset_vaporwave(self, ctx: Context) -> Message:
        """
        Timescale preset which speeds up the currently playing track,
        which matches up to nightcore, a genre of sped-up music
        """
        player = cast(Player, ctx.voice_client)
        await player.reset_filters()
        await player.add_filter(Timescale.vaporwave())
        return await ctx.approve("Set preset to **Vaporwave**.")

    @preset.command(name="nightcore")
    @player()  # Add the player decorator
    async def preset_nightcore(self, ctx: Context) -> Message:
        """
        Timescale preset which speeds up the currently playing track,
        which matches up to nightcore, a genre of sped-up music
        """
        player = cast(Player, ctx.voice_client)
        await player.reset_filters()
        await player.add_filter(Timescale.nightcore())
        return await ctx.approve("Set preset to **Nightcore**.")

    @preset.command(name="remove")
    @player()  # Add the player decorator
    async def preset_remove(self, ctx: Context) -> Message:
        """
        Remove all filters from the player.
        """
        player = cast(Player, ctx.voice_client)
        await player.reset_filters()
        return await ctx.approve("Removed all filters from the player.")
