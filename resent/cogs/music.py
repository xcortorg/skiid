import pomice
from discord import Embed, Message, utils
from discord.ext import commands
from discord.ext.commands import BadArgument
from patches.classes import Player

from resent import NeoContext as ResentContext


class music(commands.Cog):
    def __init__(self, bot: commands.AutoShardedBot):
        self.bot = bot
        self.pomice = pomice.NodePool()
        self.player = Player

    async def music_send(self, ctx: ResentContext, message: str) -> Message:

        embed = Embed(
            color=self.bot.color, description=f"🎵 {ctx.author.mention}: {message}"
        )
        await ctx.send(embed=embed)

    async def start_nodes(self) -> pomice.Node:
        await self.pomice.create_node(
            bot=self.bot,
            host="127.0.0.1",
            port=2333,
            password="suckdick1337",
            spotify_client_id="f567fb50e0b94b4e8224d2960a00e3ce",
            spotify_client_secret="f4294b7b837940f996b3a4dcf5230628",
            secure=False,
            identifier="MAIN",
        )

    print("music node is ready")

    async def disconnect_nodes(self) -> None:
        return await self.pomice.disconnect()

    @commands.command(description="play a song", usage="[song]")
    async def play(self, ctx: commands.Context, *, query: str):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")

        if not ctx.voice_client:
            player = await ctx.author.voice.channel.connect(cls=Player, self_deaf=True)
        else:
            player: Player = ctx.voice_client

        player.set_context(ctx)
        player.awaiting = True

        try:
            results = await player.get_tracks(query=query, ctx=ctx)
        except Exception as e:
            return await ctx.send_warning("There was an issue fetching that track.")
        if not results:
            await ctx.send_warning("No song found")

        if isinstance(results, pomice.Playlist):
            for track in results.tracks:
                player.queue.put(track)
            track = None
            await self.music_send(
                ctx, f"Added **{len(results.tracks)}** songs to the queue"
            )
        else:
            track = results[0]
            if player.is_playing:
                player.queue.put(track)
            await self.music_send(
                ctx, f"Added [**{track.title}**]({track.uri}) to the queue"
            )

            if not player.is_playing:
                player.current_track = track
            await player.do_next(track)

    @commands.command(description="shuffle the queue")
    async def shuffle(self, ctx: ResentContext):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")

        player: Player = ctx.voice_client
        player.shuffle()
        if not player.is_playing:
            return await ctx.send_error("No track is playing right now")
        else:
            await ctx.send_success("Shuffling the whole queue")

    @commands.command(description="resume the song")
    async def resume(self, ctx: ResentContext):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")

        player: Player = ctx.voice_client
        await player.set_pause(False)
        if not player.set_pause:
            return await ctx.send_error("No track is in the queue")
        else:
            await ctx.send_success("Resumed the song")

    @commands.command(description="pause the song")
    async def pause(self, ctx: ResentContext):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")

        player: Player = ctx.voice_client
        await player.set_pause(True)
        return await ctx.send_success("Paused the song")

    @commands.command(description="skip the song", aliases=["next"])
    async def skip(self, ctx: ResentContext):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")

        player: Player = ctx.voice_client
        player.loop = False
        player.awaiting = True
        if not player.is_playing:
            return await ctx.send_error("No track is playing right now")
        else:
            await player.do_next()

    @commands.command(description="stop the player")
    async def stop(self, ctx: ResentContext):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")
        player: Player = ctx.voice_client
        if not player.is_playing:
            return await ctx.send_error("No track is playing right now")
        else:
            await ctx.voice_client.kill()
            return await ctx.send_success("The track has been stopped.")

    @commands.command(description="change the volume", usage="1-500", aliases=["vol"])
    async def volume(self, ctx: ResentContext, volume: int):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")

        if volume < 0 or volume > 500:
            raise BadArgument("Volume has to be between **0** and **500**")

        player: Player = ctx.voice_client
        await player.set_volume(volume=volume)
        if not player.is_playing:
            return await ctx.send_error("No track is playing right now")
        else:
            await self.music_send(ctx, f"Volume set to **{volume}**")

    @commands.command(description="loop the queue")
    async def loop(self, ctx: ResentContext):

        check = ctx.author.voice
        if check is None:
            return await ctx.send_warning("You are not in a voice channel.")

        player: Player = ctx.voice_client

        if not player.is_playing:
            return await ctx.send_error("No track is playing right now")

        if not player.loop:
            player.loop = True
            return await self.music_send(
                ctx,
                f"Looping [**{player.current_track.title}**]({player.current_track.uri})",
            )
        else:
            player.loop = False
            return await self.music_send(
                ctx,
                f"Removed the loop for [**{player.current_track.title}**]({player.current_track.uri})",
            )

    @commands.command(descirption="check the queue", aliases=["q"])
    async def queue(self, ctx: ResentContext):

        player: Player = ctx.voice_client
        playing = f"{'Looping' if player.loop else 'Playing'} [***{player.current.title}***]({player.current.uri}) by **{player.current.author}**"

        if player.queue.get_queue():
            tracks = [
                f"[**{track.title}**]({track.uri})"
                for track in player.queue.get_queue()
            ]
            embeds = []
            queue_length = len(player.queue.get_queue())

        for m in utils.as_chunks(tracks, 10):
            embed = Embed(color=self.bot.color, description=playing).add_field(
                name=f"Tracks ({queue_length})", value="\n".join([l for l in m])
            )
            embeds.append(embed)

            await ctx.paginator(embeds)
        else:
            embed = Embed(color=self.bot.color, description=playing)
            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(music(bot))
