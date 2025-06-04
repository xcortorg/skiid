import aiohttp
import discord
from config import color, emoji
from discord.ext import commands
from system.base import Context


class LastFm(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.api_key = "4d2d1157ada4114d6cacd34fc0e58532"
        self.session = aiohttp.ClientSession()

    async def fetch_now_playing(self, username):
        url = f"http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user={username}&api_key={self.api_key}&format=json&limit=1"
        async with self.session.get(url) as response:
            data = await response.json()
            track = data.get("recenttracks", {}).get("track")
            if track:
                now_playing = track[0]
                artist = now_playing["artist"]["#text"]
                track_name = now_playing["name"]
                album = now_playing.get("album", {}).get("#text", "Unknown Album")
                track_url = now_playing.get("url", "No URL")
                image_url = now_playing.get("image", [])[-1].get("#text", "")
                return artist, track_name, album, track_url, image_url
            return None, None, None, None, None

    async def fetch_top_week(self, username):
        url = f"http://ws.audioscrobbler.com/2.0/?method=user.gettoptracks&user={username}&api_key={self.api_key}&format=json&period=7day&limit=10"
        async with self.session.get(url) as response:
            data = await response.json()
            top_tracks = data.get("toptracks", {}).get("track", [])
            return [
                {
                    "artist": track["artist"]["name"],
                    "name": track["name"],
                    "playcount": track["playcount"],
                }
                for track in top_tracks
            ]

    @commands.command(
        name="nowplaying",
        aliases=["np"],
        description="Shows the current playing track.",
    )
    async def nowplaying(self, ctx):
        await self.lastfm_nowplaying(ctx)

    @commands.group(description="Interact with Last.fm", aliases=["lf", "fm"])
    async def lastfm(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command.qualified_name)

    @lastfm.command(
        name="nowplaying", description="Check what's currently playing", aliases=["np"]
    )
    async def lastfm_nowplaying(self, ctx):
        username = await self.client.pool.fetchval(
            "SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id
        )
        if not username:
            await ctx.warn(
                f"**You** didn't set a username, use `{ctx.prefix}lastfm set [username]` to set one"
            )
            return

        artist, track_name, album, track_url, image_url = await self.fetch_now_playing(
            username
        )
        if artist and track_name:
            embed = discord.Embed(
                description=f"> **You** are listening to `{track_name}`",
                color=color.default,
            )
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(name=f"{ctx.author.name} | now playing", icon_url=user_pfp)
            embed.add_field(name="Artist", value=f"> {artist}", inline=True)
            embed.add_field(name="Album", value=f"> {album}", inline=True)
            embed.set_thumbnail(url=image_url)
            view = discord.ui.View()
            view.add_item(
                discord.ui.Button(
                    label="Listen", url=track_url, style=discord.ButtonStyle.link
                )
            )
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.deny("**No** currently playing track found")

    @lastfm.command(
        name="topweek",
        description="Check the top tracks played this week",
        aliases=["tw"],
    )
    async def lastfm_topweek(self, ctx):
        username = await self.client.pool.fetchval(
            "SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id
        )
        if not username:
            await ctx.warn(
                f"**You** didn't set a username, use `{ctx.prefix}lastfm set [username]` to set one"
            )
            return

        top_tracks = await self.fetch_top_week(username)
        if top_tracks:
            embed = discord.Embed(title="", color=color.default)
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            embed.set_author(name=f"{ctx.author.name} | top week", icon_url=user_pfp)
            for track in top_tracks:
                embed.add_field(
                    name=f"",
                    value=f"> **{track['artist']} - {track['name']}** Plays: `{track['playcount']}`",
                    inline=False,
                )
            await ctx.send(embed=embed)
        else:
            await ctx.deny("**No** top tracks found for the past week")

    @lastfm.command(name="set", description="Set your LastFm username", aliases=["add"])
    async def lastfm_set(self, ctx, username: str):
        await self.client.pool.execute(
            """
            INSERT INTO lastfm (user_id, username)
            VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET username = $2
            """,
            ctx.author.id,
            username,
        )
        await ctx.agree(f"**Set** your LastFm user to: `{username}`")

    @lastfm.command(
        name="remove", description="Remove your LastFm username", aliases=["delete"]
    )
    async def lastfm_remove(self, ctx):
        await self.client.pool.execute(
            "UPDATE lastfm SET username = NULL WHERE user_id = $1", ctx.author.id
        )
        await ctx.agree("**Removed** your LastFm username")


async def setup(client):
    await client.add_cog(LastFm(client))
