import discord
from discord.ext import commands
from googleapiclient.discovery import build
import youtube_dl

YOUTUBE_API_KEY = "key"

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="join")
    async def join(self, ctx):
        """Join the user's voice channel."""
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel for me to join!")
            return

        voice_channel = ctx.author.voice.channel

        if ctx.voice_client:
            if ctx.voice_client.channel == voice_channel:
                await ctx.send("I'm already in your voice channel!")
                return
            else:
                await ctx.voice_client.disconnect()

        await voice_channel.connect()
        await ctx.send(f"👍")

    @commands.command(name="leave")
    async def leave(self, ctx):
        """Leave the current voice channel."""
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.voice_client.disconnect()
            await ctx.send("Disconnected from the voice channel.")
        else:
            await ctx.send("I'm not connected to any voice channel.")

    @commands.command(name="play")
    async def play(self, ctx, *, query: str):
        """Play music from a YouTube link or search."""
        if not ctx.author.voice:
            await ctx.send("You need to be in a voice channel for me to play music!")
            return

        if not ctx.voice_client:
            await ctx.invoke(self.join)

        if ctx.voice_client.is_playing():
            await ctx.send("I'm already playing music!")
            return

        if not query.startswith("http"):
            youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
            request = youtube.search().list(
                q=query, part="snippet", type="video", maxResults=1
            )
            response = request.execute()
            video = response["items"][0]
            video_title = video["snippet"]["title"]
            video_id = video["id"]["videoId"]
            url = f"https://www.youtube.com/watch?v={video_id}"
            await ctx.send(f"🔍 Found: **{video_title}**\n{url}")
        else:
            url = query

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        }

        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                audio_url = info["url"]
                title = info.get("title", "Unknown Title")

            source = discord.FFmpegPCMAudio(audio_url, executable="ffmpeg")
            ctx.voice_client.stop()
            ctx.voice_client.play(source)
            await ctx.send(f"Now playing: **{title}**")
        except Exception as e:
            await ctx.send(f"no")

    @commands.command(name="stop")
    async def stop(self, ctx):
        """Stop the current playback."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("⏹️ Stopped playback.")
        else:
            await ctx.send("no")

    @commands.command(name="search")
    async def search(self, ctx, *, query: str):
        """Search YouTube for a video and return the link."""
        youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
        request = youtube.search().list(
            q=query, part="snippet", type="video", maxResults=1
        )
        response = request.execute()

        video = response["items"][0]
        video_title = video["snippet"]["title"]
        video_id = video["id"]["videoId"]
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        await ctx.send(f"🔍 Found: **{video_title}**\n{video_url}")

    @commands.command(name="sdeafen", aliases= ["sd"])
    @commands.has_permissions(moderate_members=True)
    async def server_deafen(self, ctx, member: discord.Member = None):
        """Server deafens the mentioned member, or self if none mentioned."""
        target = member or ctx.author
        try:
            await target.edit(deafen=True)
            await ctx.send(f"👍")
        except discord.Forbidden:
            await ctx.send("I don't have permission to deafen members.")
        except Exception as e:
            await ctx.send(f"no, {e}")

    @commands.command(name="smute", aliases= ["sm"])
    @commands.has_permissions(moderate_members=True)
    async def server_mute(self, ctx, member: discord.Member = None):
        """Server mutes the mentioned member, or self if none mentioned."""
        target = member or ctx.author
        try:
            await target.edit(mute=True)
            await ctx.send(f"👍")
        except discord.Forbidden:
            await ctx.send("I don't have permission to mute members.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name="sundeafen", aliases= ["sund"])
    @commands.has_permissions(moderate_members=True)
    async def server_undeafen(self, ctx, member: discord.Member = None):
        """Server undeafens the mentioned member, or self if none mentioned."""
        target = member or ctx.author
        try:
            await target.edit(deafen=False)
            await ctx.send(f"👍")
        except discord.Forbidden:
            await ctx.send("I don't have permission to undeafen members.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.command(name="sunmute", aliases= ["sum"])
    @commands.has_permissions(moderate_members=True)
    async def server_unmute(self, ctx, member: discord.Member = None):
        """Server unmutes the mentioned member, or self if none mentioned."""
        target = member or ctx.author
        try:
            await target.edit(mute=False)
            await ctx.send(f"👍")
        except discord.Forbidden:
            await ctx.send("I don't have permission to unmute members.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

async def setup(bot):
    await bot.add_cog(Music(bot))
