import asyncio
from contextlib import suppress
from logging import getLogger
from typing import Annotated, List, Literal, Optional, cast
from colorama import Fore, Style
import discord 
import io
import re
from urllib.parse import urlencode
import psutil
import hashlib
import time
import config

from .core.panel import Panel
import aiohttp
import validators
from aiohttp import ClientSession
from discord import Embed, HTTPException, Member, Message, SelectOption
from discord.ext.commands import (
    Cog,
    CommandError,
    command,
    group,
    has_permissions,
    parameter,
)
from discord.utils import as_chunks
from humanfriendly import format_timespan
from humanize import ordinal
from pomice import LoopMode, Playlist, SearchType, Track, Player
from pomice.enums import URLRegex as regex

from cogs.audio import Client, Percentage, Position
from main import Evict
from core.client import Context as DefaultContext
from tools.formatter import duration, plural, shorten
from managers.paginator import Paginator
from processors.audio import process_track_data, process_playlist_data

import wavelink
from discord.ui import Select, Button, View

BASE_URL = "http://ws.audioscrobbler.com"

log = getLogger("evict/audio")

SOURCE_PATTERNS = (
    regex.SPOTIFY_URL,
    regex.YOUTUBE_URL,
    regex.YOUTUBE_PLAYLIST_URL,
    regex.AM_URL,
    regex.AM_SINGLE_IN_ALBUM_REGEX,
    regex.SOUNDCLOUD_URL,
    regex.SOUNDCLOUD_PLAYLIST_URL,
    regex.SOUNDCLOUD_TRACK_IN_SET_URL,
)

class Context(DefaultContext):
    voice: Client

class SongSelect(Select):
    def __init__(self, tracks: List[Track]):
        options = [
            SelectOption(
                label=shorten(track.title, 100),
                description=f"By {shorten(track.author, 100)}",
                value=str(i)
            ) for i, track in enumerate(tracks[:25]) 
        ]
        super().__init__(
            placeholder="Select a song to play...",
            options=options,
            row=0
        )
        self.tracks = tracks

    async def callback(self, interaction: discord.Interaction):
        if not interaction.guild.voice_client:
            return await interaction.response.send_message("Not connected to a voice channel!", ephemeral=True)
            
        client = interaction.guild.voice_client
        selected_track = self.tracks[int(self.values[0])]
        
        if not await check_dj(interaction):
            return await interaction.response.send_message("You need DJ permissions to do this!", ephemeral=True)
            
        await client.play(selected_track)
        await interaction.response.send_message(f"Now playing **{selected_track.title}**", ephemeral=True)

class ControlPanel(View):
    def __init__(self, client: Client, tracks: List[Track]):
        super().__init__(timeout=None)
        self.client = client
        if len(tracks) > 1:
            self.add_item(SongSelect(tracks))
        
    @discord.ui.button(label="Play/Pause", style=discord.ButtonStyle.primary, row=1)
    async def play_pause(self, interaction: discord.Interaction, button: Button):
        if not await check_dj(interaction):
            return await interaction.response.send_message("You need DJ permissions to do this!", ephemeral=True)
            
        if self.client.is_paused:
            await self.client.set_pause(False)
            await interaction.response.send_message("Resumed playback", ephemeral=True)
        else:
            await self.client.set_pause(True)
            await interaction.response.send_message("Paused playback", ephemeral=True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.primary, row=1)
    async def skip(self, interaction: discord.Interaction, button: Button):
        if not await check_dj(interaction):
            return await interaction.response.send_message("You need DJ permissions to do this!", ephemeral=True)
            
        await self.client.stop()
        await interaction.response.send_message("Skipped track", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, row=1)
    async def stop(self, interaction: discord.Interaction, button: Button):
        if not await check_dj(interaction):
            return await interaction.response.send_message("You need DJ permissions to do this!", ephemeral=True)
            
        await self.client.destroy()
        await interaction.response.send_message("Stopped playback", ephemeral=True)

async def check_dj(interaction: discord.Interaction) -> bool:
    """Check if user has DJ permissions"""
    if interaction.user.guild_permissions.administrator:
        return True
        
    dj_role = await get_dj_role(interaction.guild.id)
    if dj_role and dj_role in interaction.user.roles:
        return True
        
    return False

async def get_dj_role(guild_id: int) -> Optional[discord.Role]:
    """Get the configured DJ role for a guild"""
    role_id = await Cog.bot.db.fetchval("""
        SELECT dj_role_id 
        FROM audio.settings
        WHERE guild_id = $1
    """, guild_id)
    
    if role_id:
        guild = Cog.bot.get_guild(guild_id)
        return guild.get_role(role_id)
    return None

class Audio(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "Audio commands for playing music in voice channels."
        self.track_info = {}
        self._last_track_time = {} 
        self._track_spam_count = {} 
        # Increase cooldown period to prevent rapid re-triggering
        self.TRACK_COOLDOWN = 2.0  # Increased from 1.0
        # Lower threshold to detect spamming sooner
        self.SPAM_THRESHOLD = 3    # Reduced from 5
        # Use a smaller window to detect rapid triggers
        self.SPAM_WINDOW = 3.0     # Reduced from 5.0
        self.panels = {}
        self.lyrics_cache = {}  
        self.current_lyrics_task = None
        
        # Don't set up automatic cleanup task to avoid potential issues
        # self._cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def _periodic_cleanup(self):
        """Periodically clean up stale data in caches"""
        try:
            while True:
                await asyncio.sleep(300)  # Run every 5 minutes
                current_time = time.time()
                
                # Clean up track timing data
                self._last_track_time = {
                    k: v for k, v in self._last_track_time.items() 
                    if current_time - v <= 600  # 10 minutes
                }
                
                # Clean up spam count data
                self._track_spam_count = {
                    k: v for k, v in self._track_spam_count.items()
                    if current_time - v["first_time"] <= 600  # 10 minutes
                }
                
                # Clean up lyrics cache (keep only recent entries)
                if len(self.lyrics_cache) > 100:
                    # If cache gets too large, keep only 50 most recent entries
                    self.lyrics_cache = {}
                    
                log.info(f"{Fore.CYAN}Performed periodic cleanup of audio resources")
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"{Fore.RED}Error in periodic cleanup task: {e}", exc_info=True)

    async def cog_before_invoke(self, ctx: Context) -> None:
        ctx.voice = await self.get_player(ctx)

    async def cog_unload(self) -> None:
        """Clean up resources when cog is unloaded"""
        log.info(f"{Fore.YELLOW}Audio cog is being unloaded, cleaning up resources")
        
        # Cancel any lyrics task
        if hasattr(self, 'current_lyrics_task') and self.current_lyrics_task:
            self.current_lyrics_task.cancel()
            
        # Clear caches
        self._last_track_time.clear()
        self._track_spam_count.clear()
        self.track_info.clear()
        self.lyrics_cache.clear()
        
        # Clean up voice clients
        for guild in self.bot.guilds:
            if guild.voice_client:
                client = guild.voice_client
                # Cancel any auto queue tasks
                existing_task = getattr(client, '_auto_queue_task', None)
                if existing_task:
                    existing_task.cancel()
                # Cancel any leave timers
                leave_timer = getattr(client, '_leave_timer', None)
                if leave_timer:
                    leave_timer.cancel()
                # Close the connection
                self.bot.loop.create_task(client.disconnect(force=True))
                
        log.info(f"{Fore.GREEN}Audio cog resources cleaned up successfully")

    async def get_player(self, ctx: Context) -> Client:
        log.info(f"{Fore.CYAN}Getting player for {ctx.author} in {ctx.guild}")
        
        client = ctx.voice_client
        log.info(f"{Fore.CYAN}Current voice client: {client}")
        
        author = cast(Member, ctx.author)
        log.info(f"{Fore.CYAN}Author voice state: {author.voice}")

        if not author.voice or not author.voice.channel:
            raise CommandError("You're not in a voice channel!")

        elif client and client.channel != author.voice.channel:
            raise CommandError("You're not in my voice channel!")

        elif not client or (client and not client.is_connected):
            log.info(f"{Fore.CYAN}No client found or not connected, attempting to connect")
            if ctx.command != self.play_group and ctx.command != self.play:
                raise CommandError("I'm not in a voice channel!")

            elif not author.voice.channel.permissions_for(ctx.guild.me).connect:
                raise CommandError(
                    "I don't have permission to connect to your voice channel!"
                )

            # Force cleanup any existing connections to ensure we can reconnect
            try:
                # Check for any voice clients in this guild and clean them up
                if ctx.guild.voice_client:
                    log.info(f"{Fore.YELLOW}Found lingering voice client, cleaning up")
                    try:
                        # Try to properly disconnect the client
                        await ctx.guild.voice_client.disconnect(force=True)
                    except Exception as e:
                        log.error(f"{Fore.RED}Error disconnecting voice client: {e}")
                
                # If we have a disconnected client, try to clean it up properly
                if client:
                    log.info(f"{Fore.YELLOW}Cleaning up disconnected client")
                    try:
                        # Use destroy if available (pomice-specific)
                        if hasattr(client, 'destroy'):
                            await client.destroy()
                        # Fallback to standard disconnect
                        elif hasattr(client, 'disconnect'):
                            await client.disconnect(force=True)
                    except Exception as e:
                        log.error(f"{Fore.RED}Error cleaning up client: {e}")
            except Exception as e:
                log.error(f"{Fore.RED}Error cleaning up existing voice connections: {e}")

            try:
                # Use a short delay to ensure Discord has time to process the disconnection
                await asyncio.sleep(1.0)
                log.info(f"{Fore.CYAN}Connecting to voice channel: {author.voice.channel}")
                client = await author.voice.channel.connect(cls=Client, self_deaf=True)
                log.info(f"{Fore.CYAN}Connected, client: {client}")
            except Exception as e:
                log.error(f"{Fore.RED}Connection error: {e}")
                # If we still get "Already connected" error, try one more approach
                if "Already connected" in str(e):
                    log.info(f"{Fore.YELLOW}Using alternative connection method")
                    # Force the bot to disconnect from voice channel by finding active voice clients
                    try:
                        for vc in ctx.bot.voice_clients:
                            if vc.guild.id == ctx.guild.id:
                                log.info(f"{Fore.YELLOW}Disconnecting from existing voice client: {vc}")
                                await vc.disconnect(force=True)
                    except Exception as disconnect_err:
                        log.error(f"{Fore.RED}Error in alternative disconnect: {disconnect_err}")
                    
                    # Try a longer delay
                    await asyncio.sleep(2)
                    # Try connecting again
                    client = await author.voice.channel.connect(cls=Client, self_deaf=True)
                else:
                    raise  # Re-raise if it's not the "Already connected" error
            
            volume = (
                cast(
                    Optional[int],
                    await self.bot.db.fetchval(
                        """
                        SELECT volume
                        FROM audio.config
                        WHERE guild_id = $1
                        """,
                        ctx.guild.id,
                    ),
                )
                or 60
            )
            await client.set_volume(volume)
            await client.set_context(ctx)  # type: ignore
            log.info(f"{Fore.CYAN}Client setup complete")

        return cast(Client, client)

    async def _handle_track_start(self, guild_id: int, track_title: str) -> bool:
        """
        Handle track start event with spam protection.
        Returns True if event should be processed, False if it should be ignored.
        """
        current_time = time.time()
        track_key = f"{guild_id}:{track_title}"
        
        if track_key in self._last_track_time:
            time_diff = current_time - self._last_track_time[track_key]
            
            if time_diff < self.TRACK_COOLDOWN:
                if track_key not in self._track_spam_count:
                    self._track_spam_count[track_key] = {"count": 1, "first_time": current_time}
                else:
                    spam_data = self._track_spam_count[track_key]
                    if current_time - spam_data["first_time"] <= self.SPAM_WINDOW:
                        spam_data["count"] += 1
                        if spam_data["count"] >= self.SPAM_THRESHOLD:
                            log.warning(f"{Fore.RED}Track spam detected for {track_title} in guild {guild_id}")
                            self._track_spam_count.pop(track_key, None)
                            self._last_track_time.pop(track_key, None)
                            return False
                    else:
                        self._track_spam_count[track_key] = {"count": 1, "first_time": current_time}
                
                return False  
        
        self._last_track_time[track_key] = current_time
        return True

    async def fetch_and_cache_lyrics(self, track: Track) -> list:
        """Fetch and cache lyrics for a track"""
        if track.uri in self.lyrics_cache:
            return self.lyrics_cache[track.uri]
            
        clean_title, clean_artist = await self.clean_title_for_search(track.title, track.author)
        
        async with aiohttp.ClientSession() as session:
            params = {
                'title': clean_title,
                'artist': clean_artist,
                'key': 'evictiscool'
            }
            async with session.get('https://listen.squareweb.app/lyrics', params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get('results') and data['results'][0].get('lyrics'):
                        self.lyrics_cache[track.uri] = data['results'][0]['lyrics']
                        return self.lyrics_cache[track.uri]
        return []

    async def format_lyrics_description(self, lyrics: list, current_ms: int) -> str:
        """Format lyrics for embed description based on current position"""
        if not lyrics:
            return "No lyrics available"

        current_idx = 0
        for i, line in enumerate(lyrics):
            if line.get('milliseconds', 0) > current_ms:
                current_idx = i
                break

        description_parts = []
        
        if current_idx < 3:
            for i in range(min(3, len(lyrics))):
                if lyrics[i].get('line'):
                    description_parts.append(f"**{lyrics[i]['line']}**")
            for i in range(3, min(7, len(lyrics))):
                if lyrics[i].get('line'):
                    description_parts.append(f"ᵐ{lyrics[i]['line']}")
        else:
            for i in range(max(0, current_idx-3), current_idx):
                if lyrics[i].get('line'):
                    description_parts.append(f"ᵐ{lyrics[i]['line']}")
            for i in range(current_idx, min(current_idx+3, len(lyrics))):
                if lyrics[i].get('line'):
                    description_parts.append(f"**{lyrics[i]['line']}**")
            for i in range(current_idx+3, min(current_idx+6, len(lyrics))):
                if lyrics[i].get('line'):
                    description_parts.append(f"ᵐ{lyrics[i]['line']}")

        return "\n".join(description_parts)

    @Cog.listener()
    async def on_pomice_track_start(self, client: Client, track: Track):
        """Handle track start event"""
        try:
            log.info(f"{Fore.CYAN}Track start event triggered for: {track.title}")
            
            # Use more unique identifier for track (including URI if available)
            track_identifier = f"{track.title}:{track.uri}" if hasattr(track, 'uri') and track.uri else track.title
            
            if not await self._handle_track_start(client.guild.id, track_identifier):
                log.info(f"{Fore.YELLOW}Track start handling skipped due to spam detection")
                return
                
            if hasattr(self, 'current_lyrics_task') and self.current_lyrics_task:
                log.info(f"{Fore.CYAN}Cancelling existing lyrics task")
                self.current_lyrics_task.cancel()
                
            log.info(f"{Fore.CYAN}Starting new lyrics update task")
            # self.current_lyrics_task = asyncio.create_task(self.lyrics_update_loop(client))
            
            log.info(f"{Fore.GREEN}Successfully started lyrics update task for: {track.title}")
            
            # Clean up old tracking data more aggressively
            current_time = time.time()
            self._last_track_time = {
                k: v for k, v in self._last_track_time.items() 
                if current_time - v <= self.TRACK_COOLDOWN * 2
            }
            self._track_spam_count = {
                k: v for k, v in self._track_spam_count.items()
                if current_time - v["first_time"] <= self.SPAM_WINDOW * 2
            }

            for member in client.channel.members:
                if not member.bot:
                    lastfm_config = await self.bot.db.fetchrow(
                        """
                        SELECT access_token, user_id 
                        FROM lastfm.config 
                        WHERE user_id = $1 AND web_authentication = true
                        """,
                        member.id
                    )

                    if lastfm_config and lastfm_config['access_token']:
                        await self.scrobble_track(client, track, lastfm_config)

            if track.requester:
                try:
                    track_info = self.track_info.get(track.uri, {})
                    
                    await self.bot.db.execute("""
                        INSERT INTO audio.recently_played 
                        (guild_id, user_id, track_title, track_uri, track_author, artwork_url, playlist_name, playlist_url)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    """,
                        client.guild.id,
                        track.requester.id, 
                        track.title,
                        track.uri,
                        track.author,
                        track.artwork_url or None,
                        getattr(track, 'playlist_name', track_info.get('playlist_name')),
                        getattr(track, 'playlist_url', track_info.get('playlist_url'))
                    )
                    
                    self.track_info.pop(track.uri, None)
                    
                    existing_task = getattr(client, '_auto_queue_task', None)
                    if existing_task:
                        log.info(f"{Fore.CYAN}Cancelling existing autoplay task")
                        existing_task.cancel()
                        client._auto_queue_task = None
                    
                    log.info(f"{Fore.CYAN}Checking autoplay conditions - Queue empty: {not client.queue}")
                    
                    if not client.queue:
                        remaining_duration = track.length - client.position
                        log.info(f"{Fore.CYAN}Track length: {track.length}, Position: {client.position}, Remaining: {remaining_duration}")
                        
                        if remaining_duration > 15000:
                            log.info(f"{Fore.CYAN}Scheduling autoplay task to run in {(remaining_duration - 15000)/1000} seconds")
                            try:
                                client._auto_queue_task = asyncio.create_task(
                                    self.schedule_autoplay(client, track, remaining_duration - 15000)
                                )
                                log.info(f"{Fore.GREEN}Successfully created autoplay task")
                            except Exception as e:
                                log.error(f"{Fore.RED}Failed to create autoplay task: {e}", exc_info=True)
                        else:
                            log.info(f"{Fore.YELLOW}Not enough remaining duration for autoplay")
                    
                except Exception as e:
                    log.error(f"{Fore.RED}Failed to save recently played: {e}")

            if track.uri not in self.track_info:  
                clean_title, clean_artist = await self.clean_title_for_search(track.title, track.author)
                artwork_url = ""
                
                async with aiohttp.ClientSession() as session:
                    search_query = f"{clean_title} {clean_artist}"
                    deezer_search = f"https://api.deezer.com/search?{urlencode({'q': search_query})}"
                    
                    try:
                        async with session.get(deezer_search) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data.get('data') and len(data['data']) > 0:
                                    artwork_url = data['data'][0].get('album', {}).get('cover_xl', '')
                    except Exception:
                        pass

                self.track_info[track.uri] = {
                    'artwork_url': artwork_url or "https://cdn.discordapp.com/attachments/1173913793446527016/1175145799481962506/music.png"
                }

            try:
                title = track.title
                artist = track.author

                if " - " in title:
                    parts = title.split(" - ", 1)
                    if len(parts) == 2:
                        artist, title = parts
                
                elif "," in title:
                    parts = title.split(",", 1)[0] 
                    if " - " in parts:
                        artist, title = parts.split(" - ", 1)

                artist = artist.strip()
                title = title.strip()
                
                log.info(f"{Fore.LIGHTBLUE_EX}Initial track data: Artist='{artist}', Title='{title}'")
                
                async with AsyncClient(base_url=BASE_URL) as session:
                    search_params = {
                        "method": "track.search",
                        "track": title,
                        "artist": artist,
                        "api_key": "bc84a74e4b3cf9eb040fbeaab4071df5",
                        "format": "json"
                    }
                        
            except Exception as e:
                log.error(f"{Fore.RED}Failed to process track with Last.fm: {e}", exc_info=True)

        except Exception as e:
            log.error(f"{Fore.RED}Error in track start event: {e}", exc_info=True)

    @Cog.listener()
    async def on_pomice_track_end(self, client: Client, track: Track, _):
        """Handle track end event"""
        if not client.queue and hasattr(client, '_panel_message'):
            try:
                await client._panel_message.edit(
                    embed=discord.Embed(
                        title="Now Playing",
                        description="Nothing is currently playing",
                        color=discord.Color.dark_embed()
                    ),
                    view=Panel(client.context)
                )
            except:
                pass
                
        # Clean up track-specific resources
        if hasattr(track, 'uri'):
            # Remove from track info cache
            self.track_info.pop(track.uri, None)
            # Remove from lyrics cache
            self.lyrics_cache.pop(track.uri, None)
            
        # Clear any track-specific tasks
        if hasattr(self, 'current_lyrics_task') and self.current_lyrics_task:
            self.current_lyrics_task.cancel()
            self.current_lyrics_task = None
            
        # Clear auto queue task if it exists
        existing_task = getattr(client, '_auto_queue_task', None)
        if existing_task:
            log.info(f"{Fore.CYAN}Cancelling existing autoplay task on track end")
            existing_task.cancel()
            client._auto_queue_task = None
            
        await client.do_next()

    @Cog.listener()
    async def on_pomice_track_stuck(self, client: Client, track: Track, _):
        await client.do_next()

    @Cog.listener()
    async def on_pomice_track_exception(self, client: Client, track: Track, _):
        await client.do_next()

    @Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Handle voice state updates"""
        if not member.guild.voice_client or not isinstance(member.guild.voice_client, Player):
            return

        voice_client = member.guild.voice_client
        channel = voice_client.channel

        if member == self.bot.user:
            # Bot disconnected, clean up all resources
            if before.channel and not after.channel:
                log.info(f"{Fore.YELLOW}Bot disconnected from voice, cleaning up resources")
                # Clean all guild-related tracks from caches
                guild_id = member.guild.id
                self._last_track_time = {
                    k: v for k, v in self._last_track_time.items() 
                    if not k.startswith(f"{guild_id}:")
                }
                self._track_spam_count = {
                    k: v for k, v in self._track_spam_count.items()
                    if not k.startswith(f"{guild_id}:")
                }
                
                # Clear any panel message
                if hasattr(voice_client, '_panel_message'):
                    try:
                        await voice_client._panel_message.delete()
                    except:
                        pass
                    voice_client._panel_message = None
                    
                # Don't try to clean up here - we're already in the disconnect flow
                # and pomice will handle it
            return

        if before.channel != channel and after.channel != channel:
            return

        humans = sum(1 for m in channel.members if not m.bot)

        if humans == 0:
            log.info(f"{Fore.YELLOW}No users left in voice channel, starting leave timer")
            
            # Safely cancel existing timer if present
            if hasattr(voice_client, '_leave_timer') and voice_client._leave_timer is not None:
                try:
                    voice_client._leave_timer.cancel()
                except Exception as e:
                    log.error(f"{Fore.RED}Error cancelling leave timer: {e}")
            
            # Set leave timer attribute if not already present
            if not hasattr(voice_client, '_leave_timer'):
                voice_client._leave_timer = None
            
            voice_client._leave_timer = asyncio.create_task(self._leave_timeout(voice_client))

        else:
            # Safely cancel timer if present
            if hasattr(voice_client, '_leave_timer') and voice_client._leave_timer is not None:
                log.info(f"{Fore.GREEN}Users present in voice channel, cancelling leave timer")
                try:
                    voice_client._leave_timer.cancel()
                except Exception as e:
                    log.error(f"{Fore.RED}Error cancelling leave timer: {e}")
                voice_client._leave_timer = None

    async def _leave_timeout(self, voice_client: Player):
        """Handle the leave timeout"""
        try:
            await asyncio.sleep(120)  
            if voice_client and voice_client.is_connected:
                log.info(f"{Fore.YELLOW}Leave timeout reached, disconnecting from voice")
                if hasattr(voice_client, '_panel_message'):
                    try:
                        await voice_client._panel_message.edit(
                            embed=discord.Embed(
                                title="Music Player",
                                description="Session ended due to inactivity",
                                color=discord.Color.dark_embed()
                            ),
                            view=None
                        )
                    except:
                        try:
                            await voice_client._panel_message.delete()
                        except:
                            pass
                    voice_client._panel_message = None
                # Use destroy() instead of disconnect() to avoid cleanup() call
                await voice_client.destroy()
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log.error(f"{Fore.RED}Error in leave timeout: {e}")

    # @Cog.listener()
    # async def on_wavelink_track_start(
    #     self,
    #     payload: TrackStartEventPayload,
    # ) -> Optional[Message]:
    #     """
    #     Notify the channel what track is now playing.
    #     """

    #     if not payload.player:
    #         return

    #     channel = payload.player.channel
    #     track = payload.original or payload.track
    #     title = await self.sanitize(track)

    #     with suppress(HTTPException, AttributeError):
    #         topic = f"♫ {title}" + (
    #             f" - {track.author}"
    #             if track.author not in track.title and " - " not in track.title
    #             else ""
    #         )
    #         if not topic:
    #             return

    #         elif isinstance(channel, StageChannel) and channel.instance:
    #             await channel.instance.edit(topic=topic)

    #         elif isinstance(channel, VoiceChannel):
    #             await channel.edit(status=topic)

    async def sanitize(self, track: Track) -> str:
        """
        Sanitize the track title.
        """

        title = track.title

        with suppress(Exception):
            async with ClientSession() as session:
                async with session.get(
                    "https://metadata-filter.vercel.app/api/youtube",
                    params={"track": track.title},
                ) as resp:
                    title = (await resp.json())["data"]["track"]

        return title

    @group(
        aliases=["q"],
        invoke_without_command=True,
    )
    async def queue(self, ctx: Context) -> Optional[Message]:
        """
        View the tracks in the queue.
        """

        if not ctx.voice.current and not ctx.voice.queue:
            return await ctx.warn("The queue is empty!")

        embed = Embed(
            title=f"Queue for {ctx.guild}",
            description=(
                f"Listening to [**{shorten(track.title)}**]({track.uri}) [`{duration(ctx.voice.position)}/{duration(track.length)}`]\n"
                + (f"Requested by {track.requester.mention}" if track.requester else "")
                if (track := ctx.voice.current)
                else "Nothing is currently playing"
            ),
        )
        fields: List[dict] = []

        if ctx.voice.queue or ctx.voice.auto_queue:
            offset = 0
            for index, chunk in enumerate(
                as_chunks(list(ctx.voice.queue or ctx.voice.auto_queue), 5)
            ):
                is_left = index % 2 == 0

                fields.append(
                    dict(
                        name="**Next up**" if is_left else "​",
                        value="\n".join(
                            f"{'' if is_left else ''}`{position + 1 + offset}` [**{shorten(track.title)}**]({track.uri})"
                            for position, track in enumerate(chunk)
                        )[:1024],
                        inline=True,
                    )
                )
                offset += len(chunk)

            embed.set_footer(
                text=" • ".join(
                    [
                        f"{plural(len(ctx.voice.queue or ctx.voice.auto_queue)):track}",
                        format_timespan(
                            sum(
                                track.length / 1e3
                                for track in (ctx.voice.queue or ctx.voice.auto_queue)
                            )
                        ),
                    ]
                ),
            )

        paginator = Paginator(
            ctx,
            entries=fields,
            embed=embed,
            per_page=2,
        )
        return await paginator.start()

    async def clean_title_for_search(self, title: str, artist: str) -> tuple[str, str]:
            """Clean up title and artist for better search results"""
            
            patterns = [
                r'\[.*?\]',          
                r'\(from .*?\)',      
                r'\(Official.*?\)',  
                r'\(feat\..*?\)',    
                r'\(ft\..*?\)',      
                r'\(Explicit\)',     
                r'\(Official Video\)', 
                r'\(Audio\)',         
                r'\(Lyrics\)',   
                r'\(Official Visualizer\)',
                r'\(Official Music Video\)',
                r'\(Official Audio\)',
                r'\(Visualizer\)',
            ]
            
            clean_title = title
            for pattern in patterns:
                clean_title = re.sub(pattern, '', clean_title, flags=re.IGNORECASE)
            
            if " - " in clean_title:
                parts = clean_title.split(" - ", 1)
                if len(parts) == 2:
                    artist, clean_title = parts
            
            clean_title = clean_title.strip()
            artist = artist.strip()
            
            log.info(f"{Fore.CYAN}Cleaned search query: '{clean_title}' by '{artist}'")
            return clean_title, artist

    @queue.group(
        name="nowplaying",
        aliases=["np"],
        invoke_without_command=True,
    )
    async def queue_nowplaying(self, ctx: Context) -> Optional[Message]:
        """
        Show what's currently playing with a fancy image.
        """
        if not ctx.voice.current:
            return await ctx.warn("Nothing is playing!")

        await ctx.typing()

        track = ctx.voice.current
        
        position = ctx.voice.position
        length = track.length
        
        formatted_position = duration(position)
        formatted_length = duration(length)
        percentage = int((position / length) * 100) if length > 0 else 0

        clean_title, clean_artist = await self.clean_title_for_search(track.title, track.author)

        async with aiohttp.ClientSession() as session:
            search_query = f"{clean_title} {clean_artist}"
            deezer_search = f"https://api.deezer.com/search?{urlencode({'q': search_query})}"
            
            log.info(f"{Fore.CYAN}Searching Deezer with URL: {deezer_search}")
            artwork_url = ""
            
            try:
                async with session.get(deezer_search) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        log.info(f"{Fore.CYAN}Deezer response: {data}")
                        if data.get('data') and len(data['data']) > 0:
                            artwork_url = data['data'][0].get('album', {}).get('cover_xl', '')
                            log.info(f"{Fore.CYAN}Found artwork URL: {artwork_url}")
            except Exception as e:
                log.error(f"{Fore.RED}Failed to fetch Deezer artwork: {e}")

            if not artwork_url:
                artwork_url = track.artwork_url if hasattr(track, 'artwork_url') else ""
                log.info(f"{Fore.YELLOW}Using fallback artwork URL: {artwork_url}")

            lyrics_params = {
                "title": track.title,
                "artist": track.author,
                "key": "evictiscool",
                "duration": str(track.length),
            }
            
            lyrics_url = f"https://listen.squareweb.app/lyrics?{urlencode(lyrics_params)}"
            log.info(f"{Fore.CYAN}Fetching lyrics with URL: {lyrics_url}")
            
            async with session.get(lyrics_url) as response:
                lyrics_data = await response.json()

            lyrics_lines = []
            if lyrics_data and "results" in lyrics_data:
                result = lyrics_data["results"][0]
                if "lyrics" in result:
                    sorted_lyrics = sorted(
                        result["lyrics"], 
                        key=lambda x: float(x.get("milliseconds", 0)) if x.get("milliseconds") is not None else 0
                    )
                    lyrics_lines = [item["line"] for item in sorted_lyrics if item.get("line")]
                elif "richSync" in result and result["richSync"]:
                    sorted_lyrics = sorted(
                        result["richSync"],
                        key=lambda x: x.get("startTime", 0)
                    )
                    lyrics_lines = [item["text"] for item in sorted_lyrics if item.get("text")]

            log.info(f"{Fore.CYAN}ISRC: {getattr(track, 'isrc', '')}")
            
            nowplaying_params = {
                "title": track.title,
                "artist": track.author,
                "artwork": artwork_url,
                "key": "evictiscool",
                "duration": str(track.length),
                "per": str(percentage),
                "length": formatted_length,
                "position": formatted_position,
                "volume": str(ctx.voice.volume),
                "isrc": getattr(track, 'isrc', ''),  
            }

            if not lyrics_lines:
                nowplaying_params["lyrics"] = "No lyrics available"
            else:
                current_position_ms = position
                current_index = 0
                for i, line in enumerate(lyrics_lines):
                    if i < len(lyrics_lines) - 1:
                        next_ms = float(sorted_lyrics[i + 1].get("milliseconds", 0) if "milliseconds" in sorted_lyrics[i + 1] else sorted_lyrics[i + 1].get("startTime", 0))
                        if next_ms > current_position_ms:
                            current_index = i
                            break

                start_index = max(0, current_index - 4)
                selected_lyrics = lyrics_lines[start_index:start_index + 8]
                nowplaying_params["lyrics"] = "§".join(selected_lyrics)

            nowplaying_url = f"https://images.listenbot.site/nowplaying?{urlencode(nowplaying_params)}"
            log.info(f"{Fore.CYAN}Generating nowplaying image with URL: {nowplaying_url}")
            async with session.get(nowplaying_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return await ctx.send(file=discord.File(fp=io.BytesIO(image_data), filename="nowplaying.png"))
                else:
                    return await ctx.warn("Failed to generate nowplaying image!")

    @queue_nowplaying.group(
        name="vertical",
        aliases=["v"],
    )
    async def queue_nowplaying_vertical(self, ctx: Context) -> Optional[Message]:
        """
        Show what's currently playing with a fancy image.
        """
        if not ctx.voice.current:
            return await ctx.warn("Nothing is playing!")

        await ctx.typing()

        track = ctx.voice.current
        
        position = ctx.voice.position
        length = track.length
        
        formatted_position = duration(position)
        formatted_length = duration(length)
        percentage = int((position / length) * 100) if length > 0 else 0

        clean_title, clean_artist = await self.clean_title_for_search(track.title, track.author)

        async with aiohttp.ClientSession() as session:
            search_query = f"{clean_title} {clean_artist}"
            deezer_search = f"https://api.deezer.com/search?{urlencode({'q': search_query})}"
            
            log.info(f"{Fore.CYAN}Searching Deezer with URL: {deezer_search}")
            artwork_url = ""
            
            try:
                async with session.get(deezer_search) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        log.info(f"{Fore.CYAN}Deezer response: {data}")
                        if data.get('data') and len(data['data']) > 0:
                            artwork_url = data['data'][0].get('album', {}).get('cover_xl', '')
                            log.info(f"{Fore.CYAN}Found artwork URL: {artwork_url}")
            except Exception as e:
                log.error(f"{Fore.RED}Failed to fetch Deezer artwork: {e}")

            if not artwork_url:
                artwork_url = track.artwork_url if hasattr(track, 'artwork_url') else ""
                log.info(f"{Fore.YELLOW}Using fallback artwork URL: {artwork_url}")

            lyrics_params = {
                "title": track.title,
                "artist": track.author,
                "key": "evictiscool",
                "duration": str(track.length),
            }
            
            lyrics_url = f"https://listen.squareweb.app/lyrics?{urlencode(lyrics_params)}"
            log.info(f"{Fore.CYAN}Fetching lyrics with URL: {lyrics_url}")
            
            async with session.get(lyrics_url) as response:
                lyrics_data = await response.json()

            lyrics_lines = []
            if lyrics_data and "results" in lyrics_data:
                result = lyrics_data["results"][0]
                if "lyrics" in result:
                    sorted_lyrics = sorted(
                        result["lyrics"], 
                        key=lambda x: float(x.get("milliseconds", 0)) if x.get("milliseconds") is not None else 0
                    )
                    lyrics_lines = [item["line"] for item in sorted_lyrics if item.get("line")]
                elif "richSync" in result and result["richSync"]:
                    sorted_lyrics = sorted(
                        result["richSync"],
                        key=lambda x: x.get("startTime", 0)
                    )
                    lyrics_lines = [item["text"] for item in sorted_lyrics if item.get("text")]

            log.info(f"{Fore.CYAN}ISRC: {getattr(track, 'isrc', '')}")
            
            nowplaying_params = {
                "title": track.title,
                "artist": track.author,
                "artwork": artwork_url,
                "key": "evictiscool",
                "duration": str(track.length),
                "per": str(percentage),
                "length": formatted_length,
                "position": formatted_position,
                "volume": str(ctx.voice.volume),
                "isrc": getattr(track, 'isrc', ''),  
                "vertical": 1
            }

            if not lyrics_lines:
                nowplaying_params["lyrics"] = "No lyrics available"
            else:
                current_position_ms = position
                current_index = 0
                for i, line in enumerate(lyrics_lines):
                    if i < len(lyrics_lines) - 1:
                        next_ms = float(sorted_lyrics[i + 1].get("milliseconds", 0) if "milliseconds" in sorted_lyrics[i + 1] else sorted_lyrics[i + 1].get("startTime", 0))
                        if next_ms > current_position_ms:
                            current_index = i
                            break

                start_index = max(0, current_index - 4)
                selected_lyrics = lyrics_lines[start_index:start_index + 8]
                nowplaying_params["lyrics"] = "§".join(selected_lyrics)

            nowplaying_url = f"https://images.listenbot.site/nowplaying?{urlencode(nowplaying_params)}"
            log.info(f"{Fore.CYAN}Generating nowplaying image with URL: {nowplaying_url}")
            async with session.get(nowplaying_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    return await ctx.send(file=discord.File(fp=io.BytesIO(image_data), filename="nowplaying.png"))
                else:
                    return await ctx.warn("Failed to generate nowplaying image!")

    @queue.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    async def queue_clear(self, ctx: Context) -> Optional[Message]:
        """
        Remove all tracks from the queue.
        """

        queue = ctx.voice.queue or ctx.voice.auto_queue
        if not queue:
            return await ctx.warn("The queue is empty!")

        queue.clear()
        return await ctx.message.add_reaction("✅")

    @queue.command(
        name="shuffle",
        aliases=["mix"],
    )
    async def queue_shuffle(self, ctx: Context) -> Optional[Message]:
        """
        Shuffle the queue.
        """

        queue = ctx.voice.queue or ctx.voice.auto_queue
        if not queue:
            return await ctx.warn("The queue is empty!")

        queue.shuffle()
        return await ctx.message.add_reaction("✅")

    @queue.command(
        name="remove",
        aliases=["del", "rm"],
        example="2"
    )
    async def queue_remove(self, ctx: Context, position: int) -> Optional[Message]:
        """
        Remove a track from the queue.
        """

        queue = ctx.voice.queue or ctx.voice.auto_queue
        if not queue:
            return await ctx.warn("The queue is empty!")

        elif not 0 < position <= len(queue):
            return await ctx.warn(
                f"Invalid position - must be between `1` and `{len(queue)}`!"
            )

        track = queue[position - 1]
        queue.remove(track)

        return await ctx.approve(
            f"Removed [**{shorten(track.title)}**]({track.uri}) from the queue"
        )

    @queue.command(
        name="move",
        aliases=["mv"],
        example="2 1"
    )
    async def queue_move(
        self,
        ctx: Context,
        position: int,
        new_position: int,
    ) -> Optional[Message]:
        """
        Move a track in the queue.
        """

        queue = ctx.voice.queue or ctx.voice.auto_queue
        if not queue:
            return await ctx.warn("The queue is empty!")

        elif not 0 < position <= len(queue):
            return await ctx.warn(
                f"Invalid position - must be between `1` and `{len(queue)}`!"
            )

        elif not 0 < new_position <= len(queue):
            return await ctx.warn(
                f"Invalid new position - must be between `1` and `{len(queue)}`!"
            )

        track = queue[position - 1]
        queue.remove(track)
        queue._queue.insert(new_position - 1, track)

        return await ctx.approve(
            f"Moved [**{shorten(track.title)}**]({track.uri}) to `{ordinal(new_position)}` in the queue"
        )

    @group(name="play", aliases=["p"], invoke_without_command=True)
    async def play_group(self, ctx: Context, *, query: Optional[str] = None):
        """Play a track or playlist in the voice channel."""
        
        if not ctx.author.voice:
            return await ctx.warn("You must be in a voice channel to use this command!")
            
        if not query:
            if not ctx.message.attachments:
                return await ctx.send_help(ctx.command)

            attachment = ctx.message.attachments[0]
            query = attachment.url

        try:
            client = await self.get_player(ctx)
            
            if not client:
                return await ctx.warn("Failed to connect to voice channel")
                
            if regex.SPOTIFY_URL.match(query):
                log.info(f"{Fore.CYAN}Processing Spotify URL: {query}")
                try:
                    log.info(f"{Fore.CYAN}Attempting to get tracks from Spotify URL")
                    spotify_tracks = await client.get_tracks(query)
                    
                    if not spotify_tracks:
                        log.error(f"{Fore.RED}No tracks returned from Spotify URL")
                        return await ctx.warn("Failed to get track info from Spotify!")
                    
                    log.info(f"{Fore.CYAN}Successfully got tracks from Spotify. Type: {type(spotify_tracks)}")
                    
                    if isinstance(spotify_tracks, Playlist):
                        playlist_name = spotify_tracks.name
                        all_tracks = []
                        
                        log.info(f"{Fore.CYAN}Processing Spotify playlist: {playlist_name} with {len(spotify_tracks.tracks)} tracks")
                        
                        for spotify_track in spotify_tracks.tracks:
                            search_query = f"ytmsearch:{spotify_track.author} - {spotify_track.title}"
                            log.info(f"{Fore.CYAN}Searching SoundCloud for: {search_query}")
                            
                            results = await client.get_tracks(search_query)
                            if results:
                                track = results[0]
                                track.requester = ctx.author
                                all_tracks.append(track)
                                self.track_info[track.uri] = {
                                    'playlist_name': playlist_name,
                                    'playlist_url': query
                                }
                                log.info(f"{Fore.GREEN}Found SoundCloud match: {track.title}")
                            else:
                                log.warning(f"{Fore.YELLOW}No SoundCloud match found for: {search_query}")
                        
                        if not all_tracks:
                            return await ctx.warn("Couldn't find any matching tracks on SoundCloud!")
                        
                        if not ctx.voice.is_playing:
                            await ctx.voice.play(all_tracks[0])
                            for track in all_tracks[1:]:
                                ctx.voice.queue.put(track)
                            response = await ctx.approve(
                                f"Now playing [{shorten(all_tracks[0].title)}]({all_tracks[0].uri})\n"
                                f"Added {plural(len(all_tracks)-1):track} from Spotify playlist **{playlist_name}** to the queue"
                            )
                            # await self.update_panel_queue(ctx)
                        else:
                            for track in all_tracks:
                                ctx.voice.queue.put(track)
                            response = await ctx.approve(
                                f"Added {plural(len(all_tracks)):track} from Spotify playlist **{playlist_name}** to the queue"
                            )
                            # await self.update_panel_queue(ctx)
                    else:
                        spotify_track = spotify_tracks[0]
                        search_query = f"ytmsearch:{spotify_track.author} - {spotify_track.title}"
                        log.info(f"{Fore.CYAN}Searching Youtube for single track: {search_query}")
                        
                        results = await client.get_tracks(search_query)
                        if not results:
                            return await ctx.warn("Couldn't find a matching track on SoundCloud!")
                        
                        track = results[0]
                        track.requester = ctx.author
                        
                        if not ctx.voice.is_playing:
                            await ctx.voice.play(track)
                            response = await ctx.approve(
                                f"Now playing [**{shorten(track.title)}**]({track.uri})"
                            )
                            # await self.update_panel_queue(ctx)
                        else:
                            ctx.voice.queue.put(track)
                            response = await ctx.approve(
                                f"Added [**{shorten(track.title)}**]({track.uri}) to the queue"
                            )
                            # await self.update_panel_queue(ctx)
                        return response
                    
                    return response
                    
                except Exception as e:
                    log.error(f"{Fore.RED}Error processing Spotify URL: {e}", exc_info=True)
                    return await ctx.warn(f"Failed to process Spotify URL: {str(e)}")
            
            if not any(regex.match(query) for regex in SOURCE_PATTERNS):
                log.info(f"{Fore.YELLOW}Searching for track: {query}")
                try:
                    log.info(f"{Fore.CYAN}Trying Youtube Music search")
                    results = await client.get_tracks(f"ytmsearch:{query}")
                    
                    if not results:
                        log.info(f"{Fore.CYAN}Trying Deezer search")
                        results = await client.get_tracks(f"dzsearch:{query}")
                        
                    if not results:
                        log.info(f"{Fore.CYAN}Trying SoundCloud search")
                        results = await client.get_tracks(f"scsearch:{query}")
                    
                    if not results:
                        return await ctx.warn("No results found!")
                    
                    track = results[0]
                    track.requester = ctx.author
                    
                    log.info(f"{Fore.CYAN}Found track: {track.title} ({track.uri})")
                    
                    if not ctx.voice.is_playing:
                        await ctx.voice.play(track)
                        response = await ctx.approve(
                            f"Now playing [**{shorten(track.title)}**]({track.uri})"
                        )
                        # await self.update_panel_queue(ctx)
                    else:
                        ctx.voice.queue.put(track)
                        response = await ctx.approve(
                            f"Added [**{shorten(track.title)}**]({track.uri}) to the queue"
                        )
                        # await self.update_panel_queue(ctx)

                    # activity_prompt = await ctx.prompt(
                    #     "Would you like to connect to Discord's music activity to display your status?",
                    # )
                    # if activity_prompt:
                    #     try:
                    #         invite = await ctx.author.voice.channel.create_invite(
                    #             target_type=discord.InviteTarget.embedded_application,
                    #             target_application_id=1323720110787268768
                    #         )
                    #         embed = Embed(
                    #             title="Discord Activity",
                    #             description="Click the button below to show your currently playing track on Discord",
                    #             color=0x0d0d0d
                    #         )
                            
                    #         view = discord.ui.View()
                    #         view.add_item(
                    #             discord.ui.Button(
                    #                 label="Using Activities",
                    #                 url="https://docs.evict.bot/activity/setup",
                    #                 style=discord.ButtonStyle.link,
                    #                 emoji=config.EMOJIS.SOCIAL.WEBSITE
                    #             )
                    #         )
                            
                    #         await ctx.send(
                    #             content=f"{invite.url}",
                    #             embed=embed,
                    #             view=view
                    #         )
                    #     except Exception as e:
                    #         log.error(f"{Fore.RED}Failed to set activity: {e}", exc_info=True)
                    #         await ctx.warn("Failed to connect to Discord's music activity")
                    
                    return response

                except Exception as e:
                    log.error(f"{Fore.RED}Error in play command: {e}")
                    return await ctx.warn(f"An error occurred: {e}")
            else:
                log.info(f"{Fore.CYAN}Loading from URL: {query}")
                results = await client.get_tracks(query)
                if not results:
                    return await ctx.warn("No results found!")

                if isinstance(results, Playlist):
                    tracks = results.tracks
                    playlist_name = results.name
                    
                    first_track = tracks[0]
                    first_track.requester = ctx.author
                    
                    self.track_info[first_track.uri] = {
                        'playlist_name': playlist_name,
                        'playlist_url': query
                    }
                    
                    for track in tracks[1:]:
                        track.requester = ctx.author
                        self.track_info[track.uri] = {
                            'playlist_name': playlist_name, 
                            'playlist_url': query
                        }
                    
                    asyncio.create_task(self.process_playlist_data(
                        ctx.guild.id,
                        ctx.author.id,
                        playlist_name,
                        query,
                        tracks
                    ))
                    
                    if not ctx.voice.is_playing:
                        await ctx.voice.play(first_track)  
                        for track in tracks[1:]:
                            ctx.voice.queue.put(track)
                        
                        response = await ctx.approve(
                            f"Now playing [{shorten(first_track.title)}]({first_track.uri})\n"
                            f"Added {plural(len(tracks)-1):track} from playlist **{playlist_name}** to the queue"
                        )
                        # await self.update_panel_queue(ctx)
                        return response
                    else:
                        for track in tracks:
                            ctx.voice.queue.put(track)
                        response = await ctx.approve(
                            f"Added {plural(len(tracks)):track} from playlist **{playlist_name}** to the queue"
                        )
                        # await self.update_panel_queue(ctx)
                        return response
                else:
                    track = results[0]
                    track.requester = ctx.author
                    self.track_info[track.uri] = {
                        'playlist_name': None,
                        'playlist_url': None
                    }
                    tracks = [track]
                    
                    if not ctx.voice.is_playing:
                        await ctx.voice.play(track)
                        response = await ctx.approve(
                            f"Now playing [**{shorten(track.title)}**]({track.uri})"
                        )
                        # await self.update_panel_queue(ctx)
                    else:
                        ctx.voice.queue.put(track)
                        response = await ctx.approve(
                            f"Added [**{shorten(track.title)}**]({track.uri}) to the queue"
                        )
                        # await self.update_panel_queue(ctx)

                    activity_prompt = await ctx.prompt(
                        "Would you like to connect to Discord's music activity to display your status?",
                    )
                    if activity_prompt:
                        try:
                            invite = await ctx.author.voice.channel.create_invite(
                                target_type=discord.InviteTarget.embedded_application,
                                target_application_id=1323720110787268768
                            )
                            embed = Embed(
                                title="Discord Activity",
                                description="Click below to show your currently playing track on Discord",
                                color=0x0d0d0d
                            )

                            view = discord.ui.View()
                            view.add_item(
                                discord.ui.Button(
                                    label="Using Activities",
                                    url="https://docs.evict.bot/activity/setup",
                                    style=discord.ButtonStyle.link,
                                    emoji=config.EMOJIS.SOCIAL.WEBSITE
                                )
                            )
                            
                            await ctx.send(
                                content=f"{invite.url}",
                                embed=embed,
                                view=view
                            )
                        except Exception as e:
                            log.error(f"{Fore.RED}Failed to create activity invite: {e}", exc_info=True)
                    
                    return response

        except Exception as e:
            log.error(f"{Fore.RED}Error in play command: {e}", exc_info=True)
            return await ctx.warn(f"An error occurred: {e}")

    @play_group.command(name="bump")
    async def play_bump(self, ctx: Context, *, query: str):
        """
        Add a track to the front of the queue.
        """

        response = await self.play(ctx, query=f"{query} bump")
        
        try:
                    invite = await ctx.author.voice.channel.create_invite(
                        target_type=discord.InviteTarget.embedded_application,
                        target_application_id=1323720110787268768
                    )
                    embed = Embed(
                        title="Discord Activity",
                        description="Click below to show your currently playing track on Discord",
                        color=0x0d0d0d
                    )

                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="Using Activities",
                            url="https://docs.evict.bot/activity/setup",
                            style=discord.ButtonStyle.link,
                            emoji=config.EMOJIS.SOCIAL.WEBSITE
                        )
                    )
                    
                    await ctx.send(
                        content=f"{invite.url}",
                        embed=embed,
                        view=view
                    )
        except Exception as e:
            log.error(f"{Fore.RED}Failed to create activity invite: {e}", exc_info=True)
        
        return response

    @play_group.command(name="panel")
    @has_permissions(manage_messages=True)
    async def play_panel(self, ctx: Context):
        """
        Toggle the now playing button panel.
        """

        await ctx.settings.update(play_panel=not ctx.settings.play_panel)
        return await ctx.approve(
            f"{'Now' if ctx.settings.play_panel else 'No longer'} displaying the button panel"
        )

    @play_group.command(name="deletion")
    @has_permissions(manage_messages=True)
    async def play_deletion(self, ctx: Context):
        """
        Toggle added to queue message deletion.
        """

        await ctx.settings.update(play_deletion=not ctx.settings.play_deletion)
        return await ctx.approve(
            f"{'Now' if ctx.settings.play_deletion else 'No longer'} deleting added to queue messages"
        )

    @command(
        aliases=[
            "fastforward",
            "rewind",
            "ff",
            "rw",
        ],
        example="2:30"
    )
    async def seek(
        self,
        ctx: Context,
        position: Annotated[
            int,
            Position,
        ],
    ) -> Message:
        """
        Seek to a specific position.
        """

        if not ctx.voice.is_playing or not ctx.voice.current:  # type: ignore
            return await ctx.warn("I'm not playing anything!")

        existing_task = getattr(ctx.voice, '_auto_queue_task', None)
        if existing_task:
            log.info(f"{Fore.CYAN}Cancelling existing autoplay task due to seek")
            existing_task.cancel()
            ctx.voice._auto_queue_task = None

        await ctx.voice.seek(position)
        
        if not ctx.voice.queue:
            remaining_duration = ctx.voice.current.length - position
            log.info(f"{Fore.CYAN}After seek - Remaining duration: {remaining_duration}")
            
            if remaining_duration > 15000:
                log.info(f"{Fore.CYAN}Scheduling new autoplay task after seek")
                try:
                    ctx.voice._auto_queue_task = asyncio.create_task(
                        self.schedule_autoplay(ctx.voice, ctx.voice.current, remaining_duration - 15000)
                    )
                    log.info(f"{Fore.GREEN}Successfully created new autoplay task after seek")
                except Exception as e:
                    log.error(f"{Fore.RED}Failed to create autoplay task after seek: {e}", exc_info=True)

        return await ctx.approve(
            f"Seeked to `{duration(position)}` in [{ctx.voice.current}]({ctx.voice.current.uri})"
        )

    @command(aliases=["ap", "auto"], example="5")
    async def autoplay(self, ctx: Context, amount: int = 5):
        """Add autoplay recommendations to the queue"""
        if amount < 1 or amount > 10:
            return await ctx.warn("Please specify a number between 1 and 10")
            
        if not ctx.voice or not ctx.voice.is_playing:
            return await ctx.warn("Nothing is currently playing!")
            
        current_track = ctx.voice.current
        clean_title, clean_artist = await self.clean_title_for_search(current_track.title, current_track.author)

        params = {
            'title': clean_title,
            'author': clean_artist,
            'algorithm': 'DYNAMIC',
            'key': 'evictiscool'
        }
        
        async with ctx.typing():
            async with aiohttp.ClientSession() as session:
                url = f"https://listen.squareweb.app/autoplay?{urlencode(params)}"
                log.info(f"{Fore.CYAN}Fetching recommendations from: {url}")
                
                async with session.get(url) as resp:
                    if resp.status != 200:
                        log.error(f"{Fore.RED}Failed to fetch recommendations: {resp.status}")
                        return await ctx.warn("Failed to fetch recommendations")
                        
                    recommendations = await resp.json()
                    if not recommendations:
                        return await ctx.warn("No recommendations found")
                        
                    log.info(f"{Fore.CYAN}Received {len(recommendations)} recommendations")
                    added = 0
                    
                    for track_data in recommendations:
                        if added >= amount:
                            break
                            
                        try:
                            results = None
                            source_name = track_data.get('sourceName', '')
                            search_query = f"{track_data['title']} {track_data['author']}"
                            
                            log.info(f"{Fore.CYAN}Trying YouTube Music search for: {search_query}")
                            results = await ctx.voice.get_tracks(f"ytmsearch:{search_query}")
                            
                            if not results:
                                if source_name == 'deezer':
                                    log.info(f"{Fore.CYAN}Trying Deezer track: {track_data['uri']}")
                                    results = await ctx.voice.get_tracks(track_data['uri'])
                                if not results:
                                    log.info(f"{Fore.CYAN}Trying Deezer search for: {search_query}")
                                    results = await ctx.voice.get_tracks(f"dzsearch:{search_query}")
                            
                            if not results:
                                log.info(f"{Fore.CYAN}Trying SoundCloud search for: {search_query}")
                                results = await ctx.voice.get_tracks(f"scsearch:{search_query}")
                            
                            if results:
                                track = results[0]
                                track.requester = None
                                track.author = track.author.replace(" - Topic", "")
                                ctx.voice.queue.put(track)
                                added += 1
                                log.info(f"{Fore.GREEN}Added track: {track.title}")
                                
                        except Exception as e:
                            log.error(f"{Fore.RED}Failed to process recommendation: {e}")
                            continue
                                
        if added == 0:
            return await ctx.warn("Failed to add any recommendations")

        return await ctx.approve(f"Added {plural(added):recommendation} to the queue based on **{clean_title}**")

    @command(aliases=["vol"], example="50")
    async def volume(
        self,
        ctx: Context,
        volume: Annotated[int, Percentage],
    ) -> Message:
        """
        Change the volume.
        """

        await self.bot.db.execute(
            """
            INSERT INTO audio.config (guild_id, volume)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE SET volume = EXCLUDED.volume
            """,
            ctx.guild.id,
            volume,
        )
        await ctx.voice.set_volume(volume)
        return await ctx.approve(f"Set the volume to `{volume}%`")

    @command()
    async def pause(self, ctx: Context) -> Optional[Message]:
        """
        Pause the current track.
        """

        if not ctx.voice.is_playing:  # type: ignore
            return await ctx.warn("I'm not playing anything!")

        elif ctx.voice.is_paused:  # type: ignore
            return await ctx.warn("The track is already paused!")

        await ctx.voice.set_pause(True)  # type: ignore
        return await ctx.message.add_reaction("✅")

    @command()
    async def resume(self, ctx: Context) -> Optional[Message]:
        """
        Resume the current track.
        """

        if not ctx.voice.current:
            return await ctx.warn("I'm not playing anything!")

        elif not ctx.voice.is_paused:  # type: ignore
            return await ctx.warn("The track is not paused!")

        await ctx.voice.set_pause(False)  # type: ignore
        
        try:
                    invite = await ctx.author.voice.channel.create_invite(
                        target_type=discord.InviteTarget.embedded_application,
                        target_application_id=1323720110787268768
                    )
                    embed = Embed(
                        title="Discord Activity",
                        description="Click below to show your currently playing track on Discord",
                        color=0x0d0d0d
                    )

                    view = discord.ui.View()
                    view.add_item(
                        discord.ui.Button(
                            label="Using Activities",
                            url="https://docs.evict.bot/activity/setup",
                            style=discord.ButtonStyle.link,
                            emoji=config.EMOJIS.SOCIAL.WEBSITE
                        )
                    )
                    
                    await ctx.send(
                        content=f"{invite.url}",
                        embed=embed,
                        view=view
                    )
        except Exception as e:
            log.error(f"{Fore.RED}Failed to create activity invite: {e}", exc_info=True)
        
        return await ctx.message.add_reaction("✅")

    @command(aliases=["next", "sk"])
    async def skip(self, ctx: Context) -> None:
        """
        Skip the current track.
        """

        await ctx.voice.stop()
        return await ctx.message.add_reaction("✅")

    @command(aliases=["mix"])
    async def shuffle(self, ctx: Context) -> Optional[Message]:
        """
        Shuffle the queue.
        """

        return await self.queue_shuffle(ctx)

    @command(aliases=["loop"], example="track")
    async def repeat(
        self,
        ctx: Context,
        option: Literal["track", "queue", "off"],
    ) -> None:
        """
        Set the repeat mode.
        """

        if option == "track":
            ctx.voice.queue.set_loop_mode(LoopMode.TRACK)  # type: ignore
            await ctx.voice.refresh_panel()  # type: ignore
            return await ctx.message.add_reaction("🔂")

        elif option == "queue":
            ctx.voice.queue.set_loop_mode(LoopMode.QUEUE)  # type: ignore
            await ctx.voice.refresh_panel()  # type: ignore
            return await ctx.message.add_reaction("🔁")

        ctx.voice.queue.disable_loop()
        await ctx.voice.refresh_panel()  # type: ignore
        return await ctx.message.add_reaction("✅")

    @command(aliases=["stop"])
    async def disconnect(self, ctx: Context) -> None:
        """
        Disconnect from the voice channel.
        """
        try:
            # Clean up panel message if it exists
            if hasattr(ctx.voice, '_panel_message') and ctx.voice._panel_message is not None:
                try:
                    await ctx.voice._panel_message.edit(
                        embed=discord.Embed(
                            title="Music Player",
                            description="Session ended",
                            color=discord.Color.dark_embed()
                        ),
                        view=None
                    )
                except Exception:
                    try:
                        await ctx.voice._panel_message.delete()
                    except Exception:
                        pass
                ctx.voice._panel_message = None
            
            # Cancel leave timer if it exists
            if hasattr(ctx.voice, '_leave_timer') and ctx.voice._leave_timer is not None:
                try:
                    ctx.voice._leave_timer.cancel()
                    ctx.voice._leave_timer = None
                except Exception as e:
                    log.error(f"{Fore.RED}Error cancelling leave timer: {e}")
            
            # Try multiple methods for disconnection in order of preference
            disconnected = False
            
            # Method 1: Use destroy if available (preferred for Pomice Player)
            if hasattr(ctx.voice, 'destroy'):
                try:
                    log.info(f"{Fore.CYAN}Destroying voice client with proper cleanup")
                    await ctx.voice.destroy()
                    disconnected = True
                except Exception as e:
                    log.error(f"{Fore.RED}Error using destroy: {e}")
            
            # Method 2: Try manual disconnection with force flag
            if not disconnected and hasattr(ctx.voice, 'disconnect'):
                try:
                    log.info(f"{Fore.YELLOW}Using disconnect method with force=True")
                    await ctx.voice.disconnect(force=True)
                    disconnected = True
                except Exception as e:
                    log.error(f"{Fore.RED}Error using disconnect: {e}")
            
            # Method 3: Try alternative approach for stubborn connections
            if not disconnected:
                for vc in ctx.bot.voice_clients:
                    if vc.guild.id == ctx.guild.id:
                        try:
                            log.info(f"{Fore.YELLOW}Using alternative disconnect method via bot.voice_clients")
                            await vc.disconnect(force=True)
                            disconnected = True
                            break
                        except Exception as e:
                            log.error(f"{Fore.RED}Failed alternative disconnect method: {e}")
            
            # Send success reaction regardless, as we've tried our best
            return await ctx.message.add_reaction("✅")
        except Exception as e:
            log.error(f"{Fore.RED}Error disconnecting: {e}")
            return await ctx.warn("Failed to disconnect")

    async def generate_api_signature(self, params: dict) -> str:
        """Generate Last.fm API call signature"""
        import hashlib
        
        API_SECRET = "87ee1fd771e030357630388312d28c12"
        
        sorted_keys = sorted(params.keys())
        
        signature_string = ''
        for key in sorted_keys:
            signature_string += key + str(params[key])
        
        signature_string += API_SECRET
        
        log.info(f"{Fore.CYAN}Signature string (first 50 chars): {signature_string[:50]}...")
        
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()

    async def process_playlist_data(self, guild_id: int, user_id: int, playlist_name: str, playlist_url: str, tracks: List[Track]):
        """Process and save playlist data in the background."""
        try:
            await self.bot.db.execute("""
                INSERT INTO audio.playlists 
                (guild_id, user_id, playlist_name, playlist_url, track_count)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (guild_id, user_id, playlist_url) 
                DO UPDATE SET 
                    track_count = EXCLUDED.track_count,
                    added_at = CURRENT_TIMESTAMP
            """,
                guild_id,
                user_id,
                playlist_name,
                playlist_url,
                len(tracks)
            )

            async with aiohttp.ClientSession() as session:
                for track in tracks:
                    clean_title, clean_artist = await self.clean_title_for_search(track.title, track.author)
                    artwork_url = ""
                    album_name = None
                    
                    search_query = f"{clean_title} {clean_artist}"
                    deezer_search = f"https://api.deezer.com/search?{urlencode({'q': search_query})}"
                    
                    try:
                        async with session.get(deezer_search) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                if data.get('data') and len(data['data']) > 0:
                                    first_result = data['data'][0]
                                    artwork_url = first_result.get('album', {}).get('cover_xl', '')
                                    album_name = first_result.get('album', {}).get('title')
                    except Exception:
                        pass

                    await self.bot.db.execute("""
                        INSERT INTO audio.playlist_tracks 
                        (guild_id, user_id, playlist_url, track_title, track_uri, track_author, album_name, artwork_url)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (guild_id, user_id, playlist_url, track_uri) 
                        DO UPDATE SET 
                            album_name = EXCLUDED.album_name,
                            artwork_url = EXCLUDED.artwork_url,
                            added_at = CURRENT_TIMESTAMP
                    """,
                        guild_id,
                        user_id,
                        playlist_url,
                        track.title,
                        track.uri,
                        track.author,
                        album_name,
                        artwork_url or None
                    )
                    
                    await asyncio.sleep(0.1)
                    
        except Exception as e:
            log.error(f"{Fore.RED}Failed to process playlist data: {e}")

    @group(name="music", aliases=["filters", "fx"], invoke_without_command=True)
    async def music_group(self, ctx: Context) -> Optional[Message]:
        """
        Audio filter commands.
        """
        return await ctx.send_help(ctx.command)

    @music_group.group(name="filter", aliases=["filters", "fx"], invoke_without_command=True)
    async def filter_group(self, ctx: Context) -> Optional[Message]:
        """
        Audio filter commands.
        """
        return await ctx.send_help(ctx.command)

    @filter_group.command(aliases=["bass"], example="50")
    async def bassboost(self, ctx: Context, percentage: Annotated[int, Percentage] = 100) -> Message:
        """
        Adjust the bass boost level.
        """
        async with aiohttp.ClientSession() as session:
            if percentage == 0:
                async with session.patch(
                    f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                    headers={"Authorization": "youshallnotpass"},
                    json={"filters": {}}
                ) as response:
                    await response.read()
                return await ctx.approve("Reset audio filters")

            gain = (percentage / 100) * 0.25
            bands = [{"band": i, "gain": gain} for i in range(2)]
            
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {"equalizer": bands}}
            ) as response:
                await response.read()
            return await ctx.approve(f"Set bass boost to `{percentage}%`")

    @filter_group.command(aliases=["nc"], example="50")
    async def nightcore(
        self,
        ctx: Context,
        percentage: Annotated[int, Percentage] = 100,
    ) -> Message:
        """
        Adjust the nightcore effect level.
        """
        async with aiohttp.ClientSession() as session:
            if percentage == 0:
                async with session.patch(
                    f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                    headers={"Authorization": "youshallnotpass"},
                    json={"filters": {}}
                ) as response:
                    await response.read()
                return await ctx.approve("Reset nightcore filter")

            speed = 1 + (percentage / 100) * 0.5
            pitch = 1 + (percentage / 100) * 0.5
            
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {"timescale": {"speed": speed, "pitch": pitch}}}
            ) as response:
                await response.read()
            return await ctx.approve(f"Set nightcore to `{percentage}%`")

    @filter_group.command(aliases=["rv"], example="50")
    async def reverb(
        self,
        ctx: Context,
        percentage: Annotated[int, Percentage] = 100,
    ) -> Message:
        """
        Adjust the reverb effect level.
        """
        async with aiohttp.ClientSession() as session:
            if percentage == 0:
                async with session.patch(
                    f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                    headers={"Authorization": "youshallnotpass"},
                    json={"filters": {}}
                ) as response:
                    await response.read()
                return await ctx.approve("Reset reverb filter")

            level = percentage / 100
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {
                    "equalizer": [
                        {"band": 0, "gain": level * 0.6},
                        {"band": 1, "gain": level * 0.8}
                    ]
                }}
            ) as response:
                await response.read()
            return await ctx.approve(f"Set reverb to `{percentage}%`")

    @filter_group.command(name="reset")
    async def filter_reset(self, ctx: Context) -> Message:
        """
        Reset all audio filters.
        """
        async with aiohttp.ClientSession() as session:
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {}}
            ) as response:
                await response.read()
        return await ctx.approve("Reset all audio filters")

    @filter_group.command(aliases=["vib"], example="50")
    async def vibrato(
        self,
        ctx: Context,
        percentage: Annotated[int, Percentage] = 100,
    ) -> Message:
        """Adjust the vibrato effect level."""
        async with aiohttp.ClientSession() as session:
            if percentage == 0:
                async with session.patch(
                    f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                    headers={"Authorization": "youshallnotpass"},
                    json={"filters": {}}
                ) as response:
                    await response.read()
                return await ctx.approve("Reset vibrato filter")

            frequency = 2 + (percentage / 100) * 12  
            depth = 0.2 + (percentage / 100) * 0.5   
            
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {"vibrato": {"frequency": frequency, "depth": depth}}}
            ) as response:
                await response.read()
            return await ctx.approve(f"Set vibrato to `{percentage}%`")

    @filter_group.command(aliases=["trem"], example="50")
    async def tremolo(
        self,
        ctx: Context,
        percentage: Annotated[int, Percentage] = 100,
    ) -> Message:
        """Adjust the tremolo effect level."""
        async with aiohttp.ClientSession() as session:
            if percentage == 0:
                async with session.patch(
                    f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                    headers={"Authorization": "youshallnotpass"},
                    json={"filters": {}}
                ) as response:
                    await response.read()
                return await ctx.approve("Reset tremolo filter")

            frequency = 2 + (percentage / 100) * 12
            depth = 0.2 + (percentage / 100) * 0.5
            
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {"tremolo": {"frequency": frequency, "depth": depth}}}
            ) as response:
                await response.read()
            return await ctx.approve(f"Set tremolo to `{percentage}%`")

    @filter_group.command(aliases=["dist"], example="50")
    async def distortion(
        self,
        ctx: Context,
        percentage: Annotated[int, Percentage] = 100,
    ) -> Message:
        """Adjust the distortion effect level."""
        async with aiohttp.ClientSession() as session:
            if percentage == 0:
                async with session.patch(
                    f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                    headers={"Authorization": "youshallnotpass"},
                    json={"filters": {}}
                ) as response:
                    await response.read()
                return await ctx.approve("Reset distortion filter")

            scale = percentage / 100
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {"distortion": {
                    "sinOffset": scale * 0.5,
                    "sinScale": scale * 0.5,
                    "cosOffset": scale * 0.5,
                    "cosScale": scale * 0.5,
                    "tanOffset": scale * 0.5,
                    "tanScale": scale * 0.5,
                    "offset": scale * 0.5,
                    "scale": scale * 0.5
                }}}
            ) as response:
                await response.read()
            return await ctx.approve(f"Set distortion to `{percentage}%`")

    @filter_group.command(aliases=["rot"], example="50")
    async def rotation(
        self,
        ctx: Context,
        percentage: Annotated[int, Percentage] = 100,
    ) -> Message:
        """Adjust the rotation effect level."""
        async with aiohttp.ClientSession() as session:
            if percentage == 0:
                async with session.patch(
                    f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                    headers={"Authorization": "youshallnotpass"},
                    json={"filters": {}}
                ) as response:
                    await response.read()
                return await ctx.approve("Reset rotation filter")

            speed = (percentage / 100) * 0.5 
            async with session.patch(
                f"http://localhost:2333/v4/sessions/pomice/players/{ctx.guild.id}",
                headers={"Authorization": "youshallnotpass"},
                json={"filters": {"rotation": {"rotationHz": speed}}}
            ) as response:
                await response.read()
            return await ctx.approve(f"Set rotation to `{percentage}%`")

    async def schedule_autoplay(self, client: Client, current_track: Track, delay_ms: int):
        """Schedule fetching and queueing of autoplay recommendations"""
        try:
            log.info(f"{Fore.CYAN}Autoplay task started - waiting {delay_ms/1000} seconds")
            await asyncio.sleep(delay_ms / 1000)
            
            if not client.is_playing:
                log.info(f"{Fore.YELLOW}Autoplay cancelled - client no longer playing")
                return
                
            clean_title, clean_artist = await self.clean_title_for_search(current_track.title, current_track.author)
            params = {
                'title': clean_title,
                'author': clean_artist,
                'algorithm': 'DYNAMIC',
                'key': 'evictiscool'
            }
            
            log.info(f"{Fore.CYAN}Fetching autoplay recommendations for: {clean_title}")
            
            async with aiohttp.ClientSession() as session:
                url = f"https://listen.squareweb.app/autoplay?{urlencode(params)}"
                log.info(f"{Fore.CYAN}Autoplay API URL: {url}")
                
                async with session.get(url) as resp:
                    log.info(f"{Fore.CYAN}Autoplay API response status: {resp.status}")
                    if resp.status == 200:
                        recommendations = await resp.json()
                        log.info(f"{Fore.CYAN}Received {len(recommendations)} recommendations")
                        
                        for track_data in recommendations:
                            if not client.is_playing:
                                log.info(f"{Fore.YELLOW}Stopping recommendations - client no longer playing")
                                break
                                
                            try:
                                results = None
                                search_query = f"{track_data['title']} {track_data['author']}"
                                source_name = track_data.get('sourceName', '')
                                
                                log.info(f"{Fore.CYAN}Trying YouTube Music search for: {search_query}")
                                results = await client.get_tracks(f"ytmsearch:{search_query}")
                                
                                if not results:
                                    if source_name == 'deezer':
                                        log.info(f"{Fore.CYAN}Trying Deezer track: {track_data['uri']}")
                                        results = await client.get_tracks(track_data['uri'])
                                    if not results:
                                        log.info(f"{Fore.CYAN}Trying Deezer search for: {search_query}")
                                        results = await client.get_tracks(f"dzsearch:{search_query}")
                                
                                if not results:
                                    log.info(f"{Fore.CYAN}Trying SoundCloud search for: {search_query}")
                                    results = await client.get_tracks(f"scsearch:{search_query}")
                                
                                if results:
                                    track = results[0]
                                    track.requester = None
                                    track.author = track.author.replace(" - Topic", "")
                                    client.queue.put(track)
                                    log.info(f"{Fore.GREEN}Added recommendation to queue: {track.title}")
                            except Exception as e:
                                log.error(f"{Fore.RED}Failed to process recommendation: {e}")
                                continue
                                
        except Exception as e:
            log.error(f"{Fore.RED}Error in autoplay scheduling: {e}", exc_info=True)
        finally:
            if hasattr(client, '_auto_queue_task'):
                del client._auto_queue_task
            log.info(f"{Fore.CYAN}Autoplay task completed")

    async def scrobble_track(self, client: Client, track: Track, lastfm_config):
        """Scrobble a track to Last.fm"""
        clean_title, clean_artist = await self.clean_title_for_search(track.title, track.author)
        timestamp = int(time.time())

        lastfm_key = "e4a7307f64e8b843427b3f13f9737f4e"
        lastfm_secret = "0542656e3abde410d3284c8dca8cda8c"
        
        method = "track.scrobble"
        api_sig = hashlib.md5(
            f"api_key{lastfm_key}artist[0]{clean_artist}method{method}sk{lastfm_config['access_token']}timestamp[0]{timestamp}track[0]{clean_title}{lastfm_secret}".encode('utf-8')
        ).hexdigest()

        params = {
            "method": method,
            "api_key": lastfm_key,
            "api_sig": api_sig,
            "sk": lastfm_config['access_token'],
            "artist[0]": clean_artist,
            "track[0]": clean_title,
            "timestamp[0]": timestamp,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("http://ws.audioscrobbler.com/2.0/", data=params) as response:
                    if response.status == 200:
                        member = client.guild.get_member(int(lastfm_config['user_id']))
                        log.info(f"{Fore.GREEN}Successfully scrobbled track for {member}")
                        
                        if not hasattr(client, '_scrobble_users'):
                            client._scrobble_users = set()
                        
                        if member:
                            client._scrobble_users.add(member.display_name)
                            
                            if not hasattr(client, '_scrobble_notified'):
                                await client.channel.send(
                                    f"{', '.join(client._scrobble_users)} your music is being scrobbled to Last.fm",
                                    delete_after=10
                                )
                                client._scrobble_notified = True
                    else:
                        log.error(f"{Fore.RED}Failed to scrobble track: {await response.text()}")
        except Exception as e:
            log.error(f"{Fore.RED}Error scrobbling track: {e}")

    @group(name="dj")
    @has_permissions(manage_guild=True)
    async def dj_group(self, ctx: Context):
        """Manage DJ settings"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @dj_group.command(name="channel")
    async def dj_channel(self, ctx: Context, channel: discord.TextChannel = None):
        """Set the music control panel channel"""
        if channel:
            await self.bot.db.execute("""
                INSERT INTO audio.settings (guild_id, panel_channel_id)
                VALUES ($1, $2)
                ON CONFLICT (guild_id) 
                DO UPDATE SET panel_channel_id = $2
            """, ctx.guild.id, channel.id)
            await ctx.approve(f"Set control panel channel to {channel.mention}")
        else:
            await self.bot.db.execute("""
                UPDATE audio.settings 
                SET panel_channel_id = NULL
                WHERE guild_id = $1
            """, ctx.guild.id)
            await ctx.approve("Removed control panel channel")

    async def _periodic_cleanup(self):
        """Periodically clean up stale data"""
        while True:
            try:
                log.info(f"{Fore.CYAN}Running periodic cleanup task")
                
                # Clean up old playlist data
                await self.bot.db.execute("""
                    DELETE FROM audio.playlists
                    WHERE added_at < NOW() - INTERVAL '7 days'
                """)
                
                # Clean up old playlist track data
                await self.bot.db.execute("""
                    DELETE FROM audio.playlist_tracks
                    WHERE added_at < NOW() - INTERVAL '7 days'
                """)
                
                # Clean up old queue data
                await self.bot.db.execute("""
                    DELETE FROM audio.queue
                    WHERE added_at < NOW() - INTERVAL '1 day'
                """)
                
                # Clean up old config data
                await self.bot.db.execute("""
                    DELETE FROM audio.config
                    WHERE updated_at < NOW() - INTERVAL '30 days'
                """)
                
                # Clean up old settings data
                await self.bot.db.execute("""
                    DELETE FROM audio.settings
                    WHERE updated_at < NOW() - INTERVAL '30 days'
                """)
                
                log.info(f"{Fore.GREEN}Periodic cleanup task completed successfully")
            except Exception as e:
                log.error(f"{Fore.RED}Error in periodic cleanup task: {e}", exc_info=True)
            finally:
                await asyncio.sleep(300)  # Wait for 5 minutes before running again

    #         if current_group > 0:
    #             start_idx = (current_group - 1) * 3
    #             for i in range(start_idx, min(start_idx + 3, len(lyrics))):
    #                 line = lyrics[i].get('line', '').strip()
    #                 if line:
    #                     description += f"-# {line}\n"
    #                 elif lyrics[i].get('milliseconds'):  
    #                     description += f"-# ♫\n"

    #         start_idx = current_group * 3
    #         for i in range(start_idx, min(start_idx + 3, len(lyrics))):
    #             line = lyrics[i].get('line', '').strip()
    #             if line:
    #                 description += f"**{line}**\n"
    #             elif lyrics[i].get('milliseconds'): 
    #                 description += f"**♫**\n"

    #         if current_group * 3 + 3 < len(lyrics):
    #             start_idx = (current_group + 1) * 3
    #             for i in range(start_idx, min(start_idx + 3, len(lyrics))):
    #                 line = lyrics[i].get('line', '').strip()
    #                 if line:
    #                     description += f"-# {line}\n"
    #                 elif lyrics[i].get('milliseconds'):  
    #                     description += f"-# ♫\n"

    #         if hasattr(ctx, '_lyric_update') and ctx._lyric_update:
    #             duration = ctx.voice.current.length
    #             current = ctx.voice.position
    #             bar_length = 8  
    #             filled = int((current / duration) * bar_length) if duration > 0 else 0
                
    #             if filled == 0:
    #                 progress_bar = (
    #                     f"{config.EMOJIS.SPOTIFY.LEFT}" + 
    #                     f"{config.EMOJIS.SPOTIFY.BLACK}" * (bar_length - 2) + 
    #                     f"{config.EMOJIS.SPOTIFY.BLACK_RIGHT}"
    #                 )
    #             elif filled == bar_length:
    #                 progress_bar = f"{config.EMOJIS.SPOTIFY.BLACK_RIGHT}" * filled
    #             else:
    #                 progress_bar = (
    #                     f"{config.EMOJIS.SPOTIFY.LEFT}" + 
    #                     f"{config.EMOJIS.SPOTIFY.WHITE}" * (filled - 1) + 
    #                     f"{config.EMOJIS.SPOTIFY.RIGHT}" + 
    #                     f"{config.EMOJIS.SPOTIFY.BLACK}" * (bar_length - filled - 2) + 
    #                     f"{config.EMOJIS.SPOTIFY.BLACK_RIGHT}"
    #                 )

    #             current_time = f"{int(current/1000//60):02d}:{int((current/1000)%60):02d}"
    #             total_time = f"{int(duration/1000//60):02d}:{int((duration/1000)%60):02d}"
                
    #             description += f"\n`{current_time}` {progress_bar} `{total_time}`"
            
    #         description += f"\n\nLyrics Provided by <:listen:1340319592559542283> [Listen](https://discord.gg/c22uktKn) in partnership with Evict"

    #     embed = discord.Embed(
    #         title="Now Playing",
    #         description=description,
    #         color=discord.Color.dark_embed()
    #     )
    #     if artwork_url:
    #         embed.set_thumbnail(url=artwork_url)
            
    #     if ctx.voice.queue:
    #         queue_text = "\n".join(
    #             f"`{i+1}.` [{shorten(t.title)}]({t.uri})"
    #             for i, t in enumerate(list(ctx.voice.queue)[:5])
    #         )
    #         embed.add_field(name="Queue", value=queue_text, inline=False)

    #     view = Panel(ctx)
        
    #     if not hasattr(ctx.voice, '_panel_message'):
    #         log.info(f"{Fore.CYAN}[PANEL] No existing message, creating new one")
    #         ctx.voice._panel_message = await channel.send(embed=embed, view=view)
    #     else:
    #         try:
    #             if ctx.voice._panel_message.channel.id != channel.id:
    #                 log.info(f"{Fore.CYAN}[PANEL] Message in wrong channel, creating new one")
    #                 await ctx.voice._panel_message.delete()
    #                 ctx.voice._panel_message = await channel.send(embed=embed, view=view)
    #             else:
    #                 await ctx.voice._panel_message.edit(embed=embed, view=view)
    #         except discord.NotFound:
    #             log.warning(f"{Fore.YELLOW}[PANEL] Message not found, creating new one")
    #             ctx.voice._panel_message = await channel.send(embed=embed, view=view)
    #         except Exception as e:
    #             log.error(f"{Fore.RED}[PANEL] Error updating message: {str(e)}")
    #             ctx.voice._panel_message = None
                
    async def play(self, ctx: Context, *, query: Optional[str] = None):
        response = await super().play(ctx, query=query)
        # await self.update_panel_queue(ctx) 
        return response

    # async def lyrics_update_loop(self, client: Client):
    #     """Update panel based on lyrics timestamps"""
    #     log.info(f"{Fore.CYAN}Starting lyrics update loop for track: {client.current.title if client.current else 'None'}")
        
    #     if not hasattr(client, '_lyrics_task'):
    #         client._lyrics_task = None
            
    #     if client._lyrics_task and not client._lyrics_task.done():
    #         log.info(f"{Fore.YELLOW}Cancelling existing lyrics task")
    #         client._lyrics_task.cancel()
    #         try:
    #             await client._lyrics_task
    #         except asyncio.CancelledError:
    #             pass
                
    #     try:
    #         if not client.is_playing or not client.current:
    #             log.warning(f"{Fore.YELLOW}Client not playing or no current track")
    #             return
                
    #         channel_id = getattr(client.context.channel, 'id', None)
    #         if not channel_id:
    #             log.error(f"{Fore.RED}No channel ID found for client")
    #             return
                
    #         lyrics = self.lyrics_cache.get(client.current.uri, [])
    #         log.info(f"{Fore.CYAN}Found cached lyrics for {client.current.title}: {bool(lyrics)}")
            
    #         if not lyrics:
    #             clean_title, clean_artist = await self.clean_title_for_search(
    #                 client.current.title, 
    #                 client.current.author
    #             )
    #             log.info(f"{Fore.CYAN}Fetching lyrics for: {clean_title} - {clean_artist}")
                
    #             async with aiohttp.ClientSession() as session:
    #                 params = {
    #                     'title': clean_title,
    #                     'artist': clean_artist,
    #                     'key': 'evictiscool'
    #                 }
    #                 try:
    #                     async with session.get('https://listen.squareweb.app/lyrics', params=params) as resp:
    #                         if resp.status == 200:
    #                             data = await resp.json()
    #                             if data.get('results') and data['results'][0].get('lyrics'):
    #                                 lyrics = data['results'][0]['lyrics']
    #                                 self.lyrics_cache[client.current.uri] = lyrics
    #                                 log.info(f"{Fore.GREEN}Successfully fetched lyrics with {len(lyrics)} lines")
    #                             else:
    #                                 log.warning(f"{Fore.YELLOW}No lyrics found in API response")
    #                         else:
    #                             log.warning(f"{Fore.YELLOW}Lyrics API returned status {resp.status}")
    #                 except Exception as e:
    #                     log.error(f"{Fore.RED}Failed to fetch lyrics: {e}")
            
    #         if not lyrics:
    #             log.warning(f"{Fore.YELLOW}No lyrics available for {client.current.title}, exiting loop")
    #             return
                
    #         async def _update_loop():
    #             last_line = -1
    #             while client.is_playing and client.current:
    #                 try:
    #                     current_ms = client.position
    #                     current_line = None
    #                     next_timestamp = None
                        
    #                     for i, line in enumerate(lyrics):
    #                         timestamp = line.get('milliseconds', 0)
    #                         if timestamp <= current_ms + 50:
    #                             current_line = i
    #                         elif timestamp > current_ms + 50:
    #                             next_timestamp = timestamp
    #                             break
                                
    #                     if current_line is not None and current_line != last_line:
    #                         last_line = current_line
    #                         ctx = client.context
    #                         if ctx:
    #                             ctx._lyric_update = True
    #                             await self.update_panel_queue(ctx)
    #                         else:
    #                             log.error(f"{Fore.RED}No context found in client")
                                
    #                     if not next_timestamp:
    #                         log.info(f"{Fore.YELLOW}No more timestamps, breaking loop")
    #                         break
                            
    #                     wait_time = max((next_timestamp - current_ms) / 1000 - 0.1, 0)
    #                     if wait_time > 0:
    #                         log.debug(f"{Fore.CYAN}Waiting {wait_time:.2f}s for next lyric")
    #                         await asyncio.sleep(wait_time)
                            
    #                     await asyncio.sleep(0.05)
                        
    #                 except asyncio.CancelledError:
    #                     log.info(f"{Fore.YELLOW}Update loop cancelled")
    #                     raise
    #                 except Exception as e:
    #                     log.error(f"{Fore.RED}Error in update loop: {e}", exc_info=True)
    #                     await asyncio.sleep(1)
                
    #             log.info(f"{Fore.GREEN}Update loop completed")
                        
    #         client._lyrics_task = asyncio.create_task(_update_loop())
    #         await client._lyrics_task
            
    #     except asyncio.CancelledError:
    #         log.info(f"{Fore.YELLOW}Lyrics update loop cancelled")
    #         raise
    #     except Exception as e:
    #         log.error(f"{Fore.RED}Error in lyrics_update_loop: {e}", exc_info=True)
    #     finally:
    #         if hasattr(client, '_lyrics_task'):
    #             client._lyrics_task = None
    #         log.info(f"{Fore.CYAN}Lyrics update loop finished")

    # async def update_panel_queue(self, ctx: Context):
    #     """Queue panel updates to prevent race conditions"""
    #     if not hasattr(self, '_panel_queue'):
    #         log.info(f"{Fore.CYAN}Initializing panel update queue")
    #         self._panel_queue = asyncio.Queue()
    #         self._panel_task = None

    #     ctx._lyric_update = True
        
    #     try:
    #         if self._panel_task and not self._panel_task.done():
    #             try:
    #                 self._panel_task.cancel()
    #                 await self._panel_task
    #             except Exception:
    #                 pass
    #             self._panel_task = None
            
    #         await self._panel_queue.put(ctx)
            
    #         if not self._panel_task:
    #             self._panel_task = asyncio.create_task(self._process_panel_queue())
                
    #     except Exception as e:
    #         log.error(f"{Fore.RED}Error queueing panel update: {e}")

    # async def _process_panel_queue(self):
    #     """Process queued panel updates"""
    #     update_count = 0
    #     start_time = time.time()
        
    #     try:
    #         while True:
    #             ctx = None
    #             try:
    #                 ctx = await self._panel_queue.get()
    #                 if not ctx:
    #                     self._panel_queue.task_done()
    #                     break
                        
    #                 try:
    #                     await self.update_panel(ctx)
    #                     update_count += 1
    #                 except Exception as e:
    #                     log.error(f"{Fore.RED}Error processing panel update: {e}")
                    
    #                 self._panel_queue.task_done()
                    
    #             except asyncio.CancelledError:
    #                 if ctx:
    #                     self._panel_queue.task_done()
    #                 break
                    
    #             except Exception as e:
    #                 log.error(f"{Fore.RED}Error in panel queue loop: {e}")
                    
    #             await asyncio.sleep(0.1)
                
    #     except Exception as e:
    #         log.error(f"{Fore.RED}Fatal error in panel queue processor: {e}")
    #     finally:
    #         duration = time.time() - start_time
    #         log.info(f"{Fore.CYAN}Panel queue processor finished after {duration:.2f}s with {update_count} updates")
            
    #         if hasattr(self, '_panel_task'):
    #             self._panel_task = None

    # async def make_request_with_retries(self, session: aiohttp.ClientSession, url: str, 
    #                                   params: Optional[dict] = None, 
    #                                   max_retries: int = 3, 
    #                                   timeout: int = 5) -> Optional[dict]:
    #     """Make HTTP request with retries and timeout"""
    #     for attempt in range(max_retries):
    #         try:
    #             async with session.get(url, params=params, timeout=timeout) as resp:
    #                 if resp.status == 200:
    #                     return await resp.json()
    #                 elif resp.status == 429:  
    #                     retry_after = int(resp.headers.get('Retry-After', 1))
    #                     await asyncio.sleep(retry_after)
    #                     continue
    #                 else:
    #                     log.error(f"{Fore.RED}Request failed with status {resp.status}")
    #                     return None
    #         except asyncio.TimeoutError:
    #             log.warning(f"{Fore.YELLOW}Request timed out, attempt {attempt + 1}/{max_retries}")
    #         except Exception as e:
    #             log.error(f"{Fore.RED}Request error: {e}")
    #             if attempt == max_retries - 1:
    #                 return None
    #         await asyncio.sleep(1)  
    #     return None

    async def cog_unload(self) -> None:
        """Clean up resources when cog is unloaded"""
        log.info(f"{Fore.YELLOW}Audio cog is being unloaded, cleaning up resources")
        
        # Cancel any lyrics task
        if hasattr(self, 'current_lyrics_task') and self.current_lyrics_task:
            self.current_lyrics_task.cancel()
            
        # Clear caches
        self._last_track_time.clear()
        self._track_spam_count.clear()
        self.track_info.clear()
        self.lyrics_cache.clear()
        
        # Clean up voice clients
        for guild in self.bot.guilds:
            if guild.voice_client:
                client = guild.voice_client
                # Cancel any auto queue tasks
                existing_task = getattr(client, '_auto_queue_task', None)
                if existing_task:
                    existing_task.cancel()
                # Cancel any leave timers
                leave_timer = getattr(client, '_leave_timer', None)
                if leave_timer:
                    leave_timer.cancel()
                # Close the connection
                self.bot.loop.create_task(client.disconnect(force=True))
                
        log.info(f"{Fore.GREEN}Audio cog resources cleaned up successfully")

    # Create a separate dc command to make sure aliases work correctly
    @command()
    async def dc(self, ctx: Context) -> None:
        """
        Disconnect from the voice channel.
        """
        log.info(f"{Fore.CYAN}DC command called directly by {ctx.author} in {ctx.guild}")
        
        # First try to use the main disconnect method
        try:
            await self.disconnect(ctx)
            return
        except Exception as e:
            log.error(f"{Fore.RED}Error using normal disconnect method in dc: {e}")
        
        # If that fails, try direct methods
        try:
            voice_client = ctx.guild.voice_client
            if voice_client:
                log.info(f"{Fore.CYAN}Found voice client directly via guild in dc command")
                
                # Try to clean up panel if it exists
                if hasattr(voice_client, '_panel_message') and voice_client._panel_message is not None:
                    try:
                        await voice_client._panel_message.delete()
                    except Exception:
                        pass
                    voice_client._panel_message = None
                
                # Try to cancel leave timer if it exists
                if hasattr(voice_client, '_leave_timer') and voice_client._leave_timer is not None:
                    try:
                        voice_client._leave_timer.cancel()
                        voice_client._leave_timer = None
                    except Exception as e:
                        log.error(f"{Fore.RED}Error cancelling leave timer: {e}")
                
                # Try to stop playback first
                try:
                    if hasattr(voice_client, 'stop'):
                        await voice_client.stop()
                except Exception as e:
                    log.error(f"{Fore.RED}Error stopping playback in dc: {e}")
                
                # Try multiple disconnect methods in order
                disconnected = False
                
                # Method 1: destroy()
                if not disconnected and hasattr(voice_client, 'destroy'):
                    try:
                        log.info(f"{Fore.CYAN}Destroying voice client in dc command")
                        await voice_client.destroy()
                        disconnected = True
                    except Exception as e:
                        log.error(f"{Fore.RED}Error destroying voice client: {e}")
                
                # Method 2: disconnect()
                if not disconnected and hasattr(voice_client, 'disconnect'):
                    try:
                        log.info(f"{Fore.CYAN}Disconnecting voice client in dc command")
                        await voice_client.disconnect(force=True)
                        disconnected = True
                    except Exception as e:
                        log.error(f"{Fore.RED}Error disconnecting voice client: {e}")
                        
                if disconnected:
                    await ctx.message.add_reaction("✅")
                    return
                
            # Last resort: try to find and disconnect any voice clients in this guild
            for vc in ctx.bot.voice_clients:
                if vc.guild.id == ctx.guild.id:
                    try:
                        log.info(f"{Fore.YELLOW}Found voice client via bot's voice_clients")
                        await vc.disconnect(force=True)
                        await ctx.message.add_reaction("✅")
                        return
                    except Exception as e:
                        log.error(f"{Fore.RED}Error disconnecting alternative client: {e}")
            
            # If we got here, all methods failed
            await ctx.warn("Failed to disconnect from voice channel after trying all methods")
        except Exception as e:
            log.error(f"{Fore.RED}Critical error in dc command: {e}")
            await ctx.warn(f"Failed to disconnect: {str(e)}")

class AsyncClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(base_url=self.base_url)
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()