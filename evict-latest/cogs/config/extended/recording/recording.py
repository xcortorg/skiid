from discord.ext.commands import group, has_permissions
from core.client.context import Context
from tools import CompositeMetaClass, MixinMeta
import discord
import asyncio
import uuid
import os
from datetime import datetime, timezone
import aiohttp
from logging import getLogger
import wave
import io
import time
from discord import Embed

log = getLogger("evict/recording")

class WaveSink:
    def __init__(self):
        self.file = io.BytesIO()
        self.cleanup = lambda: None

class RecordingVoiceClient(discord.VoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        super().__init__(client, channel)
        self.recording = False
        self.recording_sink = None
        log.info("Initialized RecordingVoiceClient")

    async def start_recording(self, sink, callback, *args):
        self.recording = True
        self.recording_sink = sink
        self.recording_sink.callback = lambda *args_inner: callback(sink, *args)
        log.info("Started recording")

    def stop_recording(self):
        log.info("Stopping recording")
        self.recording = False
        if self.recording_sink:
            try:
                self.recording_sink.callback() 
                log.info("Called recording callback")
            except Exception as e:
                log.error(f"Error in callback: {e}")
            self.recording_sink.cleanup()
            self.recording_sink = None

    def cleanup(self):
        super().cleanup()
        self.stop_recording()

    def receive_audio(self, data, user, packet):
        """This is called when we receive audio data from Discord"""
        if self.recording and self.recording_sink:
            if user:  # Don't record the bot itself
                self.recording_sink.file.write(data)
                if not hasattr(self, '_last_log') or time.time() - self._last_log > 5:
                    log.info(f"Received audio data from user {user.name}, size: {len(data)} bytes")
                    self._last_log = time.time()

class Recording(MixinMeta, metaclass=CompositeMetaClass):
    """Voice recording functionality"""
    
    active_recordings = {}

    def __init__(self, bot):
        try:
            super().__init__(bot)
            self.bot = bot
            self.name = "Voice Recording"
            self.bunny_api_key = "30a5d679-42c5-4c5c-ba408eb1719c-a367-489a"
            self.bunny_storage_zone = "evict-voice"
            self.active_recordings = {}
        except Exception as e:
            log.error(f"Failed to initialize Recording cog: {e}")
            return

    async def cog_load(self) -> None:
        """Initialize when cog loads"""
        try:
            await super().cog_load()
        except Exception as e:
            log.error(f"Failed to load Recording cog: {e}")
            return

    async def cog_unload(self) -> None:
        """Cleanup when cog unloads"""
        try:
            for recording in self.active_recordings.values():
                await self.stop_recording(recording['channel'])
        except Exception as e:
            log.error(f"Failed to unload Recording cog: {e}")
            return
        
        try:
            await super().cog_unload()
        except Exception as e:
            log.error(f"Failed to unload Recording parent: {e}")
            return

    async def upload_to_bunny(self, file_path: str, recording_id: str) -> str:
        """Upload a file to BunnyCDN"""
        try:
            headers = {
                "AccessKey": "30a5d679-42c5-4c5c-ba408eb1719c-a367-489a"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    f"https://storage.bunnycdn.com/evict-voice/recordings/{recording_id}.mp3",
                    headers=headers,
                    data=open(file_path, 'rb')
                ) as resp:
                    if resp.status != 201:
                        raise Exception(f"Failed to upload: Status {resp.status}")
                    
                    return f"https://evict-voice.b-cdn.net/recordings/{recording_id}.mp3"
                
        except Exception as e:
            log.error(f"Failed to upload to BunnyCDN: {e}")
            raise

    @group(invoke_without_command=True)
    async def recording(self, ctx: Context):
        """Voice recording management commands"""
        return await ctx.send_help(ctx.command)

    @recording.command(name="start")
    @has_permissions(manage_guild=True)
    async def recording_start(self, ctx: Context, channel: discord.VoiceChannel):
        """Start recording a voice channel"""
        if channel.id in Recording.active_recordings:
            return await ctx.warn("This channel is already being recorded!")

        try:
            voice_client = channel.guild.voice_client
            if voice_client and voice_client.channel.id != channel.id:
                return await ctx.warn("I'm already in another voice channel!")
            
            try:
                if not voice_client:
                    voice_client = await channel.connect(cls=RecordingVoiceClient, timeout=20.0, self_deaf=True)
                elif not isinstance(voice_client, RecordingVoiceClient):
                    await voice_client.disconnect(force=True)
                    await asyncio.sleep(2)  
                    voice_client = await channel.connect(cls=RecordingVoiceClient, timeout=20.0, self_deaf=True)
                
                tries = 0
                while not voice_client.is_connected() and tries < 5:
                    await asyncio.sleep(1)
                    tries += 1
                    
                if not voice_client.is_connected():
                    raise Exception("Failed to establish voice connection")
                    
            except Exception as e:
                log.error(f"Failed to connect to voice channel: {e}")
                if voice_client:
                    try:
                        await voice_client.disconnect(force=True)
                    except:
                        pass
                return await ctx.warn(f"Failed to connect to voice channel: {e}")
            
            recording_id = str(uuid.uuid4())
            
            try:
                await voice_client.start_recording(
                    WaveSink(),
                    self.finished_callback,
                    recording_id
                )
            except Exception as e:
                log.error(f"Failed to start recording process: {e}")
                return await ctx.warn(f"Failed to start recording process: {e}")
            
            Recording.active_recordings[channel.id] = {
                'id': recording_id,
                'channel': channel,
                'started_at': datetime.now(timezone.utc),
                'initiator': ctx.author,
                'voice_client': voice_client,
                'participants': set(member.id for member in channel.members)
            }

            await channel.send(
                embed=Embed(
                    title="🔴 Recording Started",
                    description="This voice channel is now being recorded.",
                    color=discord.Color.red()
                )
            )

            await self.bot.db.execute(
                """
                INSERT INTO recordings (
                    id, guild_id, channel_id, initiator_id, started_at, status
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                recording_id, ctx.guild.id, channel.id, 
                ctx.author.id, datetime.now(timezone.utc), "recording"
            )

            return await ctx.approve(f"Started recording in {channel.mention}")

        except Exception as e:
            log.error(f"Failed to start recording: {e}")
            return await ctx.warn(f"Failed to start recording: {e}")

    @recording.command(name="stop")
    @has_permissions(manage_guild=True)
    async def recording_stop(self, ctx: Context, channel: discord.VoiceChannel = None):
        """Stop recording a voice channel"""
        if not channel:
            channel = ctx.author.voice.channel if ctx.author.voice else None
            if not channel:
                return await ctx.warn("Please specify a channel or join one!")

        if channel.id not in Recording.active_recordings:
            return await ctx.warn("This channel is not being recorded!")

        try:
            recording = Recording.active_recordings[channel.id]
            voice_client = recording['voice_client']
            
            log.info(f"Stopping recording for {recording['id']}")
            voice_client.stop_recording()
            
            await asyncio.sleep(2)
            
            file_path = f"/tmp/recording_{recording['id']}.wav"
            log.info(f"Checking for file at {file_path}")
            
            if not os.path.exists(file_path):
                log.error(f"Recording file not found at {file_path}")
                return await ctx.warn("Failed to save recording!")
                
            log.info(f"File exists, size: {os.path.getsize(file_path)} bytes")
            
            file_url = await self.upload_to_bunny(file_path, recording['id'])
            log.info(f"Uploaded to BunnyCDN: {file_url}")

            await self.bot.db.execute(
                """
                UPDATE recordings 
                SET ended_at = $1, status = $2, file_path = $3
                WHERE id = $4
                """,
                datetime.now(timezone.utc), "completed", file_url, recording['id']
            )

            duration = datetime.now(timezone.utc) - recording['started_at']
            embed = Embed(
                title="⏹️ Recording Stopped",
                description=f"Recording duration: {str(duration).split('.')[0]}",
                color=discord.Color.green()
            )
            embed.add_field(
                name="Download",
                value=f"[Click here to download]({file_url})"
            )
            await channel.send(embed=embed)

            if not hasattr(voice_client, 'is_playing') or not voice_client.is_playing:
                await voice_client.disconnect()

            del Recording.active_recordings[channel.id]
            os.remove(file_path)

            return await ctx.approve(f"Stopped recording in {channel.mention}")

        except Exception as e:
            log.error(f"Failed to stop recording: {e}", exc_info=True)
            return await ctx.warn(f"Failed to stop recording: {e}")

    @recording.command(name="list")
    @has_permissions(manage_guild=True)
    async def recording_list(self, ctx: Context):
        """List all recordings for this server"""
        recordings = await self.bot.db.fetch(
            """
            SELECT id, channel_id, initiator_id, started_at, ended_at, file_path
            FROM recordings
            WHERE guild_id = $1
            ORDER BY started_at DESC
            LIMIT 10
            """,
            ctx.guild.id
        )

        if not recordings:
            return await ctx.warn("No recordings found for this server!")

        embed = Embed(
            title="Voice Recordings",
            color=ctx.color
        )

        for rec in recordings:
            channel = ctx.guild.get_channel(rec['channel_id'])
            initiator = ctx.guild.get_member(rec['initiator_id'])
            
            duration = "In progress..."
            if rec['ended_at']:
                duration = str(rec['ended_at'] - rec['started_at']).split('.')[0]

            embed.add_field(
                name=f"Recording {rec['id'][:8]}",
                value=(
                    f"Channel: {channel.mention if channel else 'Deleted channel'}\n"
                    f"Started by: {initiator.mention if initiator else 'Unknown'}\n"
                    f"Duration: {duration}\n"
                    f"[Download]({rec['file_path']})" if rec['file_path'] else "Processing..."
                ),
                inline=False
            )

        return await ctx.send(embed=embed)

    @recording.command(name="delete")
    @has_permissions(manage_guild=True)
    async def recording_delete(self, ctx: Context, recording_id: str):
        """Delete a recording"""
        try:
            headers = {"AccessKey": "30a5d679-42c5-4c5c-ba408eb1719c-a367-489a"}
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    f"https://storage.bunnycdn.com/evict-voice/recordings/{recording_id}.mp3",
                    headers=headers
                ) as resp:
                    if resp.status not in (200, 404):
                        return await ctx.warn("Failed to delete recording file!")

            result = await self.bot.db.execute(
                """
                DELETE FROM recordings
                WHERE id = $1 AND guild_id = $2
                """,
                recording_id, ctx.guild.id
            )

            if result == "DELETE 0":
                return await ctx.warn("Recording not found!")

            return await ctx.approve("Recording deleted successfully!")

        except Exception as e:
            log.error(f"Failed to delete recording: {e}")
            return await ctx.warn(f"Failed to delete recording: {e}")

    async def finished_callback(self, sink, *args):
        """Callback for when recording finishes"""
        try:
            recording_id = args[0]
            file_path = f"/tmp/recording_{recording_id}.wav"
            log.info(f"Recording callback started for {recording_id}")
            
            log.info(f"Sink file size: {len(sink.file.getvalue())} bytes")
            
            with wave.open(file_path, 'wb') as wav_file:
                wav_file.setnchannels(2) 
                wav_file.setsampwidth(2)  
                wav_file.setframerate(48000) 
                wav_file.writeframes(sink.file.getvalue())
            
            log.info(f"Successfully saved recording to {file_path}")
            
        except Exception as e:
            log.error(f"Error in recording callback: {e}", exc_info=True) 