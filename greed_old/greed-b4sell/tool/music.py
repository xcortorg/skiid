from tool.greed import Greed  # type: ignore
from humanize import naturaldelta
from datetime import timedelta
from typing import Optional, Union, Literal  # type: ignore
from tool import expressions as regex
import discord
import pomice
import asyncio
import async_timeout
import random
import orjson
from discord.ext import tasks, commands
from discord.ext.commands.errors import CommandError
from discord.ext.commands import Context
from tuuid import tuuid
from contextlib import suppress

from loguru import logger

play_emoji = "<:greed_play:1207661064096063599>"
skip_emoji = "<:greed_skip:1207661069938589716>"
pause_emoji = "<:greed_pause:1207661063093620787>"
replay_emoji = "<:greed_replay:1207661068856598528>"
queue_emoji = "<:greed_queue:1207661066620764192>"

# async def auto_disconnect(bot: Greed, player: Player):
#   async def auto_destroy(bot: Greed, player: Player):
#      await asyncio.sleep(60)
#     if player.is_paused == True: return await player.destroy()
# asyncio.ensure_future(auto_destroy(bot, player))


def fmtseconds(seconds: Union[int, float], unit: str = "microseconds") -> str:
    return naturaldelta(timedelta(seconds=seconds), minimum_unit=unit)


async def play(bot: Greed, interaction: discord.Interaction):
    if player := bot.node.get_player(interaction.guild.id):
        await player.set_pause(False)
        embed = discord.Embed(description="> **Resumed** this track", color=0x2D2B31)
        return await interaction.response.send_message(embed=embed, ephemeral=True)


async def pause(bot: Greed, interaction: discord.Interaction):
    if player := bot.node.get_player(interaction.guild.id):
        await player.set_pause(True)
        embed = discord.Embed(description="> **Paused** this track", color=0x2D2B31)
        return await interaction.response.send_message(embed=embed, ephemeral=True)


async def skip(bot: Greed, interaction: discord.Interaction):
    if player := bot.node.get_player(interaction.guild.id):
        await player.skip()
        embed = discord.Embed(description="> **Skipped** this track", color=0x2D2B31)
        return await interaction.response.send_message(embed=embed, ephemeral=True)


async def replay(bot: Greed, interaction: discord.Interaction):
    if player := bot.node.get_player(interaction.guild.id):
        if player.loop:
            await player.set_loop(state=False)
            state = "**No longer looping** the queue"
            embed = discord.Embed(description=f"> {state}", color=0x2D2B31)
        else:
            state = "Now **looping** the queue"
            await player.set_loop(state=True)
            embed = discord.Embed(description=f"> {state}", color=0x2D2B31)
        return await interaction.response.send_message(embed=embed, ephemeral=True)


def chunk_list(data: list, amount: int) -> list:
    # makes lists of a big list of values every x amount of values
    chunks = zip(*[iter(data)] * amount)
    _chunks = [list(_) for _ in list(chunks)]
    return _chunks


class MusicInterface(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        style=discord.ButtonStyle.grey, emoji=replay_emoji, custom_id="music:replay"
    )
    async def replaay(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):  # type: ignore
        return await replay(self.bot, interaction)

    @discord.ui.button(
        style=discord.ButtonStyle.gray, emoji=pause_emoji, custom_id="music:pause"
    )
    async def paause(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore
        return await pause(self.bot, interaction)

    @discord.ui.button(
        style=discord.ButtonStyle.blurple, emoji=play_emoji, custom_id="music:play"
    )
    async def palay(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore
        return await play(self.bot, interaction)

    @discord.ui.button(
        style=discord.ButtonStyle.grey, emoji=skip_emoji, custom_id="music:skip"
    )
    async def skiap(self, interaction: discord.Interaction, button: discord.ui.Button):  # type: ignore
        return await skip(self.bot, interaction)

    @discord.ui.button(
        style=discord.ButtonStyle.grey, emoji=queue_emoji, custom_id="music:queue"
    )
    async def queueinfo(self, interaction, button):  # type: ignore
        if player := self.bot.node.get_player(interaction.guild.id):
            if len(player.queue._queue) > 0:
                queue = [f"[{t.title}]({t.uri})" for t in list(player.queue._queue)[:5]]
                description = "\n".join(q for q in queue)
            else:
                description = "no tracks found in queue"
        else:
            description = "no player found"
        return await interaction.response.send_message(
            embed=discord.Embed(description=description, color=self.bot.color),
            ephemeral=True,
        )


class plural:
    def __init__(self, value: int, bold: bool = False, code: bool = False):
        self.value: int = value
        self.bold: bool = bold
        self.code: bool = code

    def __format__(self, format_spec: str) -> str:
        v = self.value
        if isinstance(v, list):
            v = len(v)
        if self.bold:
            value = f"**{v:,}**"
        elif self.code:
            value = f"`{v:,}`"
        else:
            value = f"{v:,}"

        singular, sep, plural = format_spec.partition("|")  # type: ignore
        plural = plural or f"{singular}s"

        if abs(v) != 1:
            return f"{value} {plural}"

        return f"{value} {singular}"

    def do_plural(self, format_spec: str) -> str:
        v = self.value
        if isinstance(v, list):
            v = len(v)
        if self.bold:
            value = f"**{v:,}**"
        elif self.code:
            value = f"`{v:,}`"
        else:
            value = f"{v:,}"

        singular, sep, plural = format_spec.partition("|")  # type: ignore
        plural = plural or f"{singular}s"

        if abs(v) != 1:
            return f"{value} {plural}"

        return f"{value} {singular}"


def shorten(value: str, length: int = 20):
    if len(value) > length:
        value = value[: length - 2] + (".." if len(value) > length else "").strip()
    return value


def format_duration(duration: int, ms: bool = True):
    if ms:
        seconds = int((duration / 1000) % 60)
        minutes = int((duration / (1000 * 60)) % 60)
        hours = int((duration / (1000 * 60 * 60)) % 24)
    else:
        seconds = int(duration % 60)
        minutes = int((duration / 60) % 60)
        hours = int((duration / (60 * 60)) % 24)

    if any((hours, minutes, seconds)):
        result = ""
        if hours:
            result += f"{hours:02d}:"
        result += f"{minutes:02d}:"
        result += f"{seconds:02d}"
        return result
    else:
        return "00:00"


class Player(pomice.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bound_channel: Optional[discord.abc.MessageableChannel] = None
        self.message: Optional[discord.Message] = None
        self.track: Optional[pomice.Track] = None
        self.queue: asyncio.Queue = asyncio.Queue()
        self.waiting: bool = False
        self.loop: Union[str, bool] = False
        self.bot: Optional[Greed] = None

    @property
    def bound_channel(self) -> Optional[discord.TextChannel]:
        if not self._bound_channel and self.channel:
            if self.channel.category:
                for channel in self.channel.category.text_channels:
                    if channel.permissions_for(self.guild.me).send_messages:
                        self._bound_channel = channel
                        break
            if not self._bound_channel:
                for channel in self.guild.text_channels:
                    if channel.permissions_for(self.guild.me).send_messages:
                        self._bound_channel = channel
                        break
        return self._bound_channel

    @bound_channel.setter
    def bound_channel(self, channel: discord.TextChannel):
        self._bound_channel = channel

    def _format_socket_track(self, track: pomice.Track):
        return {
            "url": track.uri,
            "title": track.title,
            "author": track.author,
            "length": track.length,
            "image": track.thumbnail,
        }

    def _format_socket_channel(self):
        return {
            "voice": (
                {
                    "id": self.channel.id,
                    "name": self.channel.name,
                    "members": [
                        {
                            "id": member.id,
                            "name": str(member),
                            "avatar": (
                                member.display_avatar.url
                                if member.display_avatar
                                else None
                            ),
                        }
                        for member in self.channel.members
                        if not member.bot
                    ],
                }
                if self.channel
                else None
            ),
            "text": {"id": self.bound_channel.id, "name": self.bound_channel.name},
        }

    @property
    def get_percentage(self) -> int:
        if not self.current:
            return 0
        position = divmod(self.position, 60000)
        length = divmod(self.current.length, 60000)
        timeframe = f"{int(position[0])}:{round(position[1]/1000):02}/{int(length[0])}:{round(length[1]/1000):02}"
        pos, total = timeframe.split("/")
        pos_minutes = int(pos.split(":")[0])
        total_minutes = int(total.split(":")[0])
        pos_seconds = pos_minutes * 60
        total_seconds = total_minutes * 60
        pos_seconds += int(pos.split(":")[1])
        total_seconds += int(total.split(":")[1])
        return int((pos_seconds / total_seconds) * 100) if total_seconds > 0 else 0

    @property
    def progress(self):
        bar = "██"
        empty = "   "
        percentage = self.get_percentage
        actual = bar * (percentage // 10) + empty * (10 - (percentage // 10))
        return actual

    async def play(self, track: pomice.Track):
        #        if track not in self.queue._queue: self.queue._queue.insert(0, track)
        await super().play(track)

    async def insert(
        self, track: pomice.Track, filter: bool = True, bump: bool = False
    ):
        if filter and track.info.get("sourceName", "Spotify") == "youtube":
            response = await self.bot.session.get(
                "https://metadata-filter.vercel.app/api/youtube",
                params=dict(track=track.title),
            )
            data = await response.json()

            if data.get("status") == "success":
                track.title = data["data"].get("track")

        if bump:
            queue = self.queue._queue
            queue.insert(0, track)
        else:
            await self.queue.put(track)
        return True

    async def next_track(self, ignore_playing: bool = False) -> Optional[pomice.Track]:
        if not ignore_playing and (self.is_playing or self.waiting):
            return None

        self.waiting = True
        track = None
        try:
            if self.loop == "track" and self.track:
                track = self.track
            else:
                async with async_timeout.timeout(300):
                    track = await self.queue.get()
                    if self.loop == "queue":
                        await self.queue.put(track)

            if track:
                await self.play(track)
                self.track = track

                if self.bound_channel and self.loop != "track":
                    try:
                        if self.message:
                            async for message in self.bound_channel.history(limit=15):
                                if message.id == self.message.id:
                                    await message.delete()
                                    break
                        self.message = await track.ctx.neutral(
                            f"**Now playing** [**{track.title}**]({track.uri})",
                            emoji="<a:greed_playing:1207661065496825967>",
                        )
                    except Exception:
                        self.bound_channel = None
                        self.message = await track.ctx.neutral(
                            f"**Now playing** [**{track.title}**]({track.uri})",
                            emoji="<a:greed_playing:1207661065496825967>",
                        )

        except asyncio.TimeoutError:
            await self.teardown()
        finally:
            self.waiting = False

        return track

    async def skip(self):
        if self.is_paused:
            await self.set_pause(False)
        if self.loop is True:
            return await self.seek(self.current.length)
        return await self.stop()

    async def set_loop(self, state: str):
        self.loop = state
        self._queue = self.queue._queue

    async def teardown(self) -> None:
        try:
            self.queue._queue.clear()
            await self.reset_filters()
            await self.destroy()
        except Exception:
            pass

    def __repr__(self):
        return f"<greed.Player guild={self.guild.id} connected={self.is_connected} playing={self.is_playing}>"


class MusicError(CommandError):
    def __init__(self, message: str, **kwargs):
        super().__init__(message)
        self.kwargs = kwargs


async def auto_disconnect(bot: Greed, player: Player):
    async def auto_destroy(bot: Greed, player: Player):  # type: ignore
        await asyncio.sleep(60)
        logger.info("auto disconnecting now")
        if (
            player.is_paused is True
            or player.is_playing is False
            and len(player.queue._queue) == 0
            and not player.current
        ):
            return await player.teardown()

    await asyncio.ensure_future(auto_destroy(bot, player))


class Music(commands.Cog):
    def __init__(self, bot: Greed):
        self.bot = bot
        self.music_autodisconnect.start()

    #    async def cog_load(self):
    #       if not hasattr(self.bot, 'node'):
    #          return await self.check_node()

    async def check_node(self):
        logger.info("Initializing LavaLink Node Pool....")
        if not hasattr(self.bot, "node"):
            spotify = self.bot.config.get("spotify")
            if spotify is None:
                logger.info(
                    "No Spotify Credentials Found in Config so the bot will not be able to play spotify tracks"
                )
                self.bot.node = await pomice.NodePool().create_node(
                    bot=self.bot,
                    host="127.0.0.1",
                    port=2333,
                    password="youshallnotpass",
                    identifier=f"MAIN{tuuid()}",
                    spotify_client_id="d15ca7286e354306b231ca1fa918fc04",
                    spotify_client_secret="d5ec1357581b443c879f1e4d3d0e5608",
                    apple_music=True,
                )
            else:
                # try:
                self.bot.node = await pomice.NodePool().create_node(
                    bot=self.bot,
                    host="lavahatry4.techbyte.host",
                    port=3000,
                    password="NAIGLAVA-dash.techbyte.host",
                    identifier=f"CharlesNaig Node {tuuid()}",
                    spotify_client_id=spotify.get("d15ca7286e354306b231ca1fa918fc04"),
                    spotify_client_secret=spotify.get(
                        "d5ec1357581b443c879f1e4d3d0e5608"
                    ),
                    apple_music=True,
                )
                # except Exception as e:
                #   logger.info(f"Initialization of LavaLink Node Pool Errored with : {e}")
                # else:
                logger.info("Created LavaLink Node Pool Connection")

    @tasks.loop(minutes=1)
    async def music_autodisconnect(self):
        if not hasattr(self.bot, "node"):
            await self.check_node()
            return

        for player in list(self.bot.node.players.values()):
            if not player.is_playing and player.is_paused:
                await player.destroy()

    @commands.Cog.listener()
    async def on_pomice_track_end(
        self,
        player: pomice.Player,
        track: pomice.Track,
        reason: str,  # type: ignore
    ):
        #        logger.info('auto disconnecting')
        #       await auto_disconnect(self.bot, player)
        await player.next_track()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, reaction: discord.RawReactionActionEvent):
        if data := await self.bot.redis.get(f"lfnp:{reaction.message_id}"):
            data = orjson.loads(data)
            track = data["track"]
            artist = data["artist"]
            up_vote = data["up"]
            if str(reaction.emoji) == str(up_vote):
                await self.bot.db.execute(
                    """INSERT INTO lastfm_likes (user_id,track,artist) VALUES($1,$2,$3) ON CONFLICT (user_id,track,artist) DO NOTHING""",
                    reaction.user_id,
                    track,
                    artist,
                )

    @commands.Cog.listener("on_raw_reaction_remove")
    async def downvote_lastfm(self, reaction: discord.RawReactionActionEvent):
        if data := await self.bot.redis.get(f"lfnp:{reaction.message_id}"):
            data = orjson.loads(data)
            if str(reaction.emoji) == str(data["up"]):
                await self.bot.db.execute(
                    """DELETE FROM lastfm_likes WHERE user_id = $1 AND track = $2 AND artist = $3""",
                    reaction.user_id,
                    data["track"],
                    data["artist"],
                )

    @commands.Cog.listener()
    async def on_ready(self):
        if not hasattr(self.bot, "node"):
            await self.check_node()

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if not hasattr(self.bot, "node"):
            return

        if member.id == self.bot.user.id and not after.channel:
            if player := self.bot.node.get_player(member.guild.id):
                await player.destroy()
            return

        if before.channel and self.bot.user in before.channel.members:
            player = self.bot.node.get_player(member.guild.id)
            if player and len(before.channel.members) == 1:
                await player.teardown()

    async def get_player(
        self, ctx: Context, *, connect: bool = True, check_connected: bool = True
    ) -> Optional[Player]:
        """Get or create a player instance for a guild."""
        # Verify Lavalink node exists
        if not hasattr(self.bot, "node"):
            raise commands.CommandError("Lavalink node not initialized")

        if check_connected and not ctx.author.voice:
            if not check_connected:
                return None
            raise commands.CommandError("You must be in a voice channel")

        if (
            ctx.guild.me.voice
            and ctx.guild.me.voice.channel
            and ctx.author.voice
            and ctx.guild.me.voice.channel != ctx.author.voice.channel
        ):
            raise commands.CommandError("Already connected to different voice channel")

        player = self.bot.node.get_player(ctx.guild.id)

        if not player and connect and ctx.author.voice:
            try:
                player = await ctx.author.voice.channel.connect(
                    cls=Player, self_deaf=True
                )
                if isinstance(player, Player):
                    player.bound_channel = ctx.channel
                    player.bot = self.bot
                    await player.set_volume(65)
            except Exception as e:
                raise commands.CommandError(f"Failed to connect: {str(e)}")

        return player

    @commands.command(name="playing", aliases=["interface"])
    async def playing(self, ctx: Context):
        await self.get_player(ctx, connect=False)  # type: ignore
        return await ctx.send(
            embed=discord.Embed(
                description=f"{play_emoji} - `resume the queue`\n{pause_emoji} - `pause the queue`\n{skip_emoji} - `skip the current track`\n{replay_emoji} - `loop the queue`"
            ),
            view=MusicInterface(self.bot),
        )

    @commands.command(
        name="nowplaying", aliases=["current", "np"], brief="show current playing song"
    )
    async def nowplaying(
        self,
        ctx: Context,
        member: Optional[discord.Member] = Context.author,  # type: ignore
    ):
        player: Player = await self.get_player(
            ctx, connect=False, check_connected=False
        )
        if player is None:
            return await ctx.invoke(self.bot.get_command("lastfm nowplaying"))
        elif player.current:
            embed = discord.Embed(title="Song", color=0x2B2D31)
            embed.description = f"> **Playing: ** [**{shorten(player.current.title, 23)}**]({player.current.uri})\n > **Time: ** `{format_duration(player.position)}/{format_duration(player.current.length)}`\n > **Progess: ** ``{player.get_percentage} %``\n > ```{player.progress}```"
            if player.current.thumbnail:
                embed.set_thumbnail(url=player.current.thumbnail)

            return await ctx.send(embed=embed, view=MusicInterface(self.bot))
        else:
            return await ctx.fail(f"no current playing track : {player.current}")

    @commands.command(
        name="play",
        aliases=["queue", "p", "q"],
        parameters={
            "bump": {
                "require_value": False,
                "description": "Bump the track to the front of the queue",
                "aliases": ["b", "next"],
            },
            "shuffle": {
                "require_value": False,
                "description": "Shuffle the queue after adding the track",
                "aliases": ["s"],
            },
            "liked": {
                "require_value": False,
                "description": "Play the tracks you have liked from lastfm nowplaying embeds",
                "aliases": ["like", "love", "l", "loved"],
            },
        },
    )
    async def play(self, ctx: Context, *, query: str = None):
        """Queue a track"""

        if query is None:
            if ctx.invoked_with in ("play", "p"):
                return await ctx.send_help(ctx.command.qualified_name)
            else:
                if (player := self.bot.node.get_player(ctx.guild.id)) is None:
                    return await ctx.fail("Please **provide** a query")
                else:
                    queue = player.queue._queue.copy()
                    if not queue:
                        if not player.current:
                            return await ctx.fail("There isn't an active **track**")
                    embeds = []
                    embed = discord.Embed(
                        title=f"Queue for {player.channel.name}", color=0x2B2D31
                    )

                    if player.current:
                        embed.description = f"> **Duration: ** `{format_duration(player.position)}/{format_duration(player.current.length)}` \n > **Playing: ** [**{shorten(player.current.title, 23)}**]({player.current.uri})\n > **Requested by: ** {player.current.requester.mention}\n"
                        embeds.append(embed)
                    for track in queue:
                        embed = embed.copy()
                        embed.description = f"> **Duration: ** `00: 00/{format_duration(track.length)}`\n > [**{shorten(track.title, 23)}**]({track.uri}) - {track.requester.mention}"
                        embeds.append(embed)
                    return await ctx.paginate(embeds)
        player: Player = await self.get_player(ctx) or ctx.voice_client
        if query.lower() in ["-liked", "--liked", "liked"]:
            results = []
            errors = []
            for track, artist in await self.bot.db.fetch(
                """SELECT track,artist FROM lastfm_likes WHERE user_id = $1""",
                ctx.author.id,
            ):
                query = f"{track} by {artist}"
                try:
                    result = await player.node.get_tracks(
                        query=query, ctx=ctx, search_type=pomice.SearchType.scsearch
                    )
                    if len(result) > 0:
                        await player.insert(
                            result[0], filter=False, bump=ctx.parameters.get("bump")
                        )
                        results.append(f"[**{result[0].title}**]({result[0].uri})")
                    else:
                        errors.append(f"Failed to insert {query}")
                except Exception:  # type: ignore
                    return await ctx.fail("could not find that track")

            if len(results) > 0:
                await self.bot.paginate(
                    ctx,
                    discord.Embed(
                        title="Tracks Queued",
                        url=self.bot.domain,
                        color=self.bot.color,
                    ),
                    results,
                    10,
                )
        else:
            try:
                result = await ctx.voice_client.node.get_tracks(
                    query=query, ctx=ctx, search_type=pomice.SearchType.scsearch
                )
            except pomice.TrackLoadError:
                if match := regex.SOUNDCLOUD_TRACK_URL.match(
                    query
                ) or regex.SOUNDCLOUD_PLAYLIST_URL.match(query):
                    try:
                        result = await player.node.get_tracks(
                            query=f"ytsearch:{match.group('slug')}", ctx=ctx
                        )
                    except Exception:
                        return await ctx.fail("could not find that track")
                else:
                    result = None
            except TypeError:
                return await ctx.fail("could not find that track")
            except KeyError:
                return await ctx.fail("Music Node Is currently ratelimited...")

            if not result:
                return await ctx.fail("No **results** were found")
            elif isinstance(result, pomice.Playlist):
                for track in result.tracks:
                    await player.insert(
                        track, filter=False, bump=ctx.parameters.get("bump")
                    )
                await ctx.neutral(
                    f"Added ** {plural(result.track_count): track} ** from [**{result.name}**]({result.uri}) to the queue",
                    emoji="<a:greed_music:1207661059989831681>",
                )
            else:
                track = result[0]
                await player.insert(track, bump=ctx.parameters.get("bump"))
                if player.is_playing:
                    await ctx.neutral(
                        f"Added [**{track.title}**]({track.uri}) to the queue",
                        emoji="<a:greed_music:1207661059989831681>",
                    )

        if ctx.parameters.get("shuffle"):
            if queue := player.queue._queue:
                random.shuffle(queue)
                with suppress(discord.HTTPException):
                    await ctx.message.add_reaction("🔀")
        if not player.is_playing:
            await player.next_track()

        if bound_channel := player.bound_channel:
            if bound_channel != ctx.channel:
                with suppress(discord.HTTPException):
                    await ctx.message.add_reaction("✅")

    @commands.command(
        name="move",
        usage="(from) (to)",
        example="6 2",
        aliases=["mv"],
    )
    async def move(self, ctx: Context, track: int, to: int):
        """Move a track to a different position"""

        player: Player = await self.get_player(ctx, connect=False)
        queue = player.queue._queue

        if track == to:
            return await ctx.fail(f"Track position `{track}` is invalid")
        try:
            queue[track - 1]
            queue[to - 1]
        except IndexError:
            return await ctx.fail(
                f"Track position `{track}` is invalid (`1`/`{len(queue)}`)"
            )

        _track = queue[track - 1]
        del queue[track - 1]
        queue.insert(to - 1, _track)
        await ctx.success(
            f"Moved [**{_track.title}**]({_track.uri}) to position `{to}`"
        )

    @commands.command(
        name="remove",
        usage="(index)",
        example="3",
        aliases=["rmv"],
    )
    async def remove(self, ctx: Context, track: int):
        """Remove a track from the queue"""

        player: Player = await self.get_player(ctx, connect=False)
        queue = player.queue._queue

        if track < 1 or track > len(queue):
            return await ctx.fail(
                f"Track position `{track}` is invalid (`1`/`{len(queue)}`)"
            )

        _track = queue[track - 1]
        del queue[track - 1]
        await ctx.success(f"Removed [**{_track.title}**]({_track.uri}) from the queue")

    @commands.command(
        name="shuffle",
        aliases=["mix"],
    )
    async def shuffle(self, ctx: Context):
        """Shuffle the queue"""

        player: Player = await self.get_player(ctx, connect=False)

        if queue := player.queue._queue:
            random.shuffle(queue)
            await ctx.message.add_reaction("🔀")
        else:
            await ctx.fail("There aren't any **tracks** in the queue")

    @commands.command(name="skip", aliases=["next", "sk"])
    async def skip(self, ctx: Context):
        """Skip the current track"""

        player: Player = await self.get_player(ctx, connect=False)

        if player.is_playing:
            await ctx.success("**Skipped** this song")
            await player.skip()
        else:
            await ctx.fail("There isn't an active **track**")

    @commands.command(
        name="loop",
        usage="(track, queue, or off)",
        example="queue",
        aliases=["repeat", "lp"],
    )
    async def loop(self, ctx: Context, option: Literal["track", "queue", "off"]):
        """Toggle looping for the current track or queue"""

        player: Player = await self.get_player(ctx, connect=False)

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

    @commands.command(name="pause")
    async def pause(self, ctx: Context):
        """Pause the current track"""

        player: Player = await self.get_player(ctx, connect=False)

        if player.is_playing and not player.is_paused:
            await ctx.success("**Paused** this song")
            await player.set_pause(True)

        else:
            await ctx.fail(
                "There isn't an active **track**"
                if not player.is_playing
                else "The player is already paused"
            )

    @commands.command(name="resume", aliases=["rsm"])
    async def resume(self, ctx: Context):
        """Resume the current track"""

        player: Player = await self.get_player(ctx, connect=False)

        if player.is_playing and player.is_paused:
            await ctx.success("**Resumed** the song")
            await player.set_pause(False)

        else:
            await ctx.fail("There isn't an active **track**")

    @commands.command(
        name="volume",
        aliases=["vol", "v"],
    )
    async def volume(self, ctx: Context, percentage: int = 65):
        """Set the player volume"""
        if percentage >= 100:
            percentage = 100
        player: Player = await self.get_player(ctx, connect=False)
        if percentage is None:
            return await ctx.neutral(f"Current volume: `{player.volume}%`")
        await player.set_volume(percentage)
        await ctx.success(f"Set **volume** to `{percentage}%`")

    @commands.command(name="disconnect", aliases=["dc", "stop"])
    async def disconnect(self, ctx: Context):
        """Disconnect the music player"""
        player: Player = await self.get_player(ctx, connect=False)
        try:
            await player.teardown()
        except Exception:
            pass
        await ctx.success("**Disconnected** from the voice channel")

    @commands.group(
        name="presets",
        aliases=["eq", "equalizer", "preset"],
        invoke_without_command=True,
    )
    async def presets(self, ctx):
        await ctx.send_help(ctx.command.qualified_name)

    @presets.command(
        name="list",
        aliases=["ls"],
        brief="List available presets",
        example=",presets list",
    )
    async def presets_list(self, ctx: Context):
        player: Player = await self.get_player(ctx)
        presets = [
            "vaporwave",
            "nightcore",
            "boost",
            "metal",
            "flat",
            "piano",
        ]
        embed = discord.Embed(title="Available Presets", color=0x2B2D31)
        embed.description = "\n".join(presets)
        await ctx.send(embed=embed)

    @presets.command(
        name="vaporwave",
        brief="Apply the vaporwave preset",
        example=",presets vaporwave",
    )
    async def vaporwave(self, ctx: Context):
        player: Player = await self.get_player(ctx)
        try:
            vaporwave = pomice.Timescale.vaporwave()
            await player.add_filter(vaporwave, fast_apply=True)
            await ctx.success("Applied the **vaporwave** preset")
        except pomice.FilterTagAlreadyInUse as e:
            await ctx.warning(f"That filter is already in use")

    @presets.command(
        name="nightcore",
        brief="Apply the vaporwave preset",
        example=",presets vaporwave",
    )
    async def nightcore(self, ctx: Context):
        player: Player = await self.get_player(ctx)
        try:
            preset = pomice.Timescale.nightcore()
            await player.add_filter(preset, fast_apply=True)
            await ctx.success("Applied the **nightcore** preset")
        except pomice.FilterTagAlreadyInUse as e:
            await ctx.warning(f"That filter is already in use")

    @presets.command(
        name="boost", brief="Apply the boost preset", example=",presets boost"
    )
    async def boost(self, ctx: Context):
        player: Player = await self.get_player(ctx)
        try:
            boost = pomice.Equalizer.boost()
            await player.add_filter(boost, fast_apply=True)
            await ctx.success("Applied the **boost** preset")
        except pomice.FilterTagAlreadyInUse as e:
            await ctx.warning(f"That filter is already in use")

    @presets.command(
        name="metal", brief="Apply the metal preset", example=",presets metal"
    )
    async def metal(self, ctx: Context):
        player: Player = await self.get_player(ctx)
        try:
            metal = pomice.Equalizer.metal()
            await player.add_filter(metal, fast_apply=True)
            await ctx.success("Applied the **metal** preset")
        except pomice.FilterTagAlreadyInUse as e:
            await ctx.warning(f"That filter is already in use")

    @presets.command(
        name="flat", brief="Apply the flat preset", example=",presets flat"
    )
    async def flat(self, ctx: Context):
        player: Player = await self.get_player(ctx)
        try:
            flat = pomice.Equalizer.flat()
            await player.add_filter(flat, fast_apply=True)
            await ctx.success("Applied the **flat** preset")
        except pomice.FilterTagAlreadyInUse as e:
            await ctx.warning(f"That filter is already in use")

    @presets.command(
        name="piano", brief="Apply the piano preset", example=",presets piano"
    )
    async def piano(self, ctx: Context):
        player: Player = await self.get_player(ctx)
        try:
            piano = pomice.Equalizer.piano()
            await player.add_filter(piano, fast_apply=True)
            await ctx.success("Applied the **piano** preset")
        except pomice.FilterTagAlreadyInUse as e:
            await ctx.warning(f"That filter is already in use")

    @presets.command(
        name="indian", brief="Apply the indian preset", example=",presets indian"
    )
    async def indian(self, ctx: Context):
        player: Optional[Player] = await self.get_player(ctx)
        if not player:
            return await ctx.fail("No player found to apply the **indian** preset.")

        try:
            await ctx.invoke(self.boost)
            await ctx.invoke(self.vaporwave)

            if player.queue and player.queue._queue:
                player.queue._queue.clear()

            if player.is_playing:
                await player.skip()

            await ctx.invoke(self.play_command, query="light up sketchers")
            player.loop = "track"

            await ctx.success("Applied the **indian** preset successfully.")
        except Exception as e:
            await ctx.fail(f"Failed to apply the **indian** preset: {str(e)}")

    @presets.command(
        name="remove",
        aliases=["off"],
        brief="Remove a preset from the current player",
        example=",presets remove vaporwave",
    )
    async def remove_preset(self, ctx: Context, preset: str):
        player: Player = await self.get_player(ctx)
        presets = [
            "vaporwave",
            "nightcore",
            "boost",
            "metal",
            "flat",
            "piano",
        ]
        if preset not in presets:
            return await ctx.warning(f"`{preset}` is not a valid preset")
        try:
            await player.remove_filter(preset, fast_apply=True)
            await ctx.success(f"Removed the **{preset}** preset")
        except pomice.FilterTagNotInUse as e:
            await ctx.warning(f"That filter is not in use")


async def setup(bot):
    await bot.add_cog(Music(bot))
