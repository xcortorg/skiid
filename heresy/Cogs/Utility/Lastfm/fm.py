import discord
from discord.ext import commands
import aiohttp
import hashlib
import time
import json
from urllib.parse import urlencode


class LastFM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = "empty"
        self.api_secret = "emmpty"
        self.user_data = {}

    def save_user_data(self):
        """Save user data to a file."""
        with open("lastfm_users.json", "w") as f:
            json.dump(self.user_data, f, indent=4)

    def load_user_data(self):
        """Load user data from a file."""
        try:
            with open("lastfm_users.json", "r") as f:
                self.user_data = json.load(f)
        except FileNotFoundError:
            self.user_data = {}

    def generate_api_sig(self, method, params):
        """Generate the API signature for Last.fm calls."""
        sorted_params = sorted(params.items())

        base_string = f"api_key{self.api_key}"
        base_string += ''.join([f"{key}{value}" for key, value in sorted_params])
        base_string += f"{self.api_secret}"

        signature = hashlib.md5(base_string.encode('utf-8')).hexdigest()

        print(f"Generated API Signature: {signature}")
        return signature

    @commands.Cog.listener()
    async def on_ready(self):
        """Load user data when the bot starts."""
        self.load_user_data()

    @commands.command(name="login")
    async def lastfm_login(self, ctx):
        """Provide instructions to connect a Last.fm account."""
        token = await self.fetch_request_token()

        if not token:
            await ctx.send("There was an error fetching the token. Please try again later.")
            return

        auth_url = f"http://www.last.fm/api/auth/?api_key={self.api_key}&token={token}"

        embed = discord.Embed(
            title="Connect your Last.fm account",
            description=(
                f"Authorize Heresy to use your Last.fm account [here]({auth_url}).\n\n"
                "Once you have authorized the app, run `,auth <token>` to complete the process."
            ),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)

    async def fetch_request_token(self):
        """Fetch a request token from Last.fm."""
        params = {
            'method': 'auth.getToken',
            'api_key': self.api_key,
            'format': 'json'
        }
        params['api_sig'] = self.generate_api_sig('auth.getToken', params)

        async with aiohttp.ClientSession() as session:
            url = f"http://ws.audioscrobbler.com/2.0/?{urlencode(params)}"
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        print(f"HTTP Error: {resp.status}")
                        return None

                    data = await resp.json()
                    print("Last.fm API Response:", data)

                    if 'error' in data:
                        print(f"Error from Last.fm: {data.get('message')}")
                        return None

                    return data.get("token")
            except Exception as e:
                print(f"Error during token fetch: {e}")
                return None

    @commands.command(name="auth")
    async def auth_complete(self, ctx, token: str):
        """Complete the authorization process by obtaining a session key."""
        await ctx.send("Attempting to complete authorization...")

        params = {
            'method': 'auth.getSession',
            'api_key': self.api_key,
            'token': token,
            'format': 'json'
        }

        params['api_sig'] = self.generate_api_sig('auth.getSession', params)

        url = f"http://ws.audioscrobbler.com/2.0/?{urlencode(params)}"

        print(f"Auth URL: {url}")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await ctx.send(f"HTTP error: {resp.status}. Please try again.")
                        return

                    data = await resp.json()
                    print("Authorization Response:", data)

                    if 'error' in data:
                        await ctx.send(f"Authorization failed: {data.get('message', 'Unknown error')}")
                        return

            except Exception as e:
                await ctx.send("An error occurred while connecting to Last.fm. Please try again later.")
                print(f"Error fetching session key: {e}")
                return

        try:
            session_key = data["session"]["key"]
            username = data["session"]["name"]
            user_id = str(ctx.author.id)

            self.user_data[user_id] = {"username": username, "session_key": session_key}
            self.save_user_data()

            await ctx.send(f"Authorization complete! Your Last.fm account ({username}) is now linked.")
        except KeyError:
            await ctx.send("Failed to retrieve session information. Please try again.")

    @commands.command(name="logout")
    async def lastfm_logout(self, ctx):
        """Remove the user's Last.fm account."""
        user_id = str(ctx.author.id)
        if user_id in self.user_data:
            del self.user_data[user_id]
            self.save_user_data()
            await ctx.send("Your Last.fm account has been disconnected.")
        else:
            await ctx.send("You don't have an account connected.")

    @commands.command(name="fm", aliases= ["np"])
    async def now_playing(self, ctx):
        """Show the user's current track and scrobble stats."""
        user_id = str(ctx.author.id)
        if user_id not in self.user_data:
            await ctx.send("You need to connect your Last.fm account first using `,login`.")
            return

        username = self.user_data[user_id]["username"]

        async with aiohttp.ClientSession() as session:
            params = {
                'method': 'user.getrecenttracks',
                'user': username,
                'api_key': self.api_key,
                'format': 'json',
                'limit': 1
            }
            url = f"http://ws.audioscrobbler.com/2.0/?{urlencode(params)}"

            async with session.get(url) as resp:
                data = await resp.json()

        try:
            track = data["recenttracks"]["track"][0]
            artist = track["artist"]["#text"]
            album = track["album"]["#text"]
            track_name = track["name"]
            image_url = track["image"][-1]["#text"]

            embed = discord.Embed(
                title=f"Now Playing: {track_name}",
                description=f"Artist: **{artist}**\nAlbum: **{album}**",
                color=discord.Color.green(),
            )
            embed.set_thumbnail(url=image_url)
            await ctx.send(embed=embed)
        except (KeyError, IndexError):
            await ctx.send("Couldn't fetch your current track. Make sure scrobbling is enabled!")

    @commands.command(name="topartists", aliases= ["ta, top"])
    async def top_artists(self, ctx):
        """Show the user's top artists."""
        user_id = str(ctx.author.id)
        if user_id not in self.user_data:
            await ctx.send("You need to connect your Last.fm account first using `,login`.")
            return

        username = self.user_data[user_id]["username"]
        session_key = self.user_data[user_id]["session_key"]

        async with aiohttp.ClientSession() as session:
            params = {
                'api_key': self.api_key,
                'method': 'user.gettopartists',
                'user': username,
                'sk': session_key,
                'limit': '5'
            }
            params['api_sig'] = self.generate_api_sig('user.gettopartists', params)
            url = f"http://ws.audioscrobbler.com/2.0/?{urlencode(params)}"

            async with session.get(url) as resp:
                data = await resp.json()

        try:
            artists = data["topartists"]["artist"]
            description = "\n".join([f"{idx+1}. **{artist['name']}** ({artist['playcount']} plays)" for idx, artist in enumerate(artists)])
            embed = discord.Embed(
                title="Your Top Artists",
                description=description,
                color=discord.Color.purple(),
            )
            await ctx.send(embed=embed)
        except KeyError:
            await ctx.send("Couldn't fetch your top artists. Make sure your account has activity!")

async def setup(bot):
    await bot.add_cog(LastFM(bot))
