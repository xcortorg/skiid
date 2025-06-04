import asyncio
import discord
import requests

from discord import SelectOption, Embed
from discord.ext.commands import Cog, group, Author

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext

class Spotify(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    async def get_spotify_tokens(self, discord_id):
        query = "SELECT access_token, refresh_token FROM spotify_tokens WHERE discord_id = $1"
        result = await self.bot.db.fetchrow(query, discord_id)
        return result

    async def update_access_token(self, discord_id, new_access_token):
        query = "UPDATE spotify_tokens SET access_token = $1 WHERE discord_id = $2"
        await self.bot.db.execute(query, new_access_token, discord_id)

    async def refresh_access_token(self, refresh_token):
        client_id = 'e3c57e9a39a2472e9e4606caed8af133'
        client_secret = '4f3a64f1082e400491cf1e2f0cbdffd0'
        token_url = 'https://accounts.spotify.com/api/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            response_data = response.json()
            new_access_token = response_data.get('access_token')
            return new_access_token
        return None

    async def ensure_access_token(self, discord_id):
        tokens = await self.get_spotify_tokens(discord_id)
        if tokens is None:
            return None, None
        access_token, refresh_token = tokens['access_token'], tokens['refresh_token']
        test_url = 'https://api.spotify.com/v1/me'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(test_url, headers=headers)
        if response.status_code == 401:
            new_access_token = await self.refresh_access_token(refresh_token)
            if new_access_token:
                await self.update_access_token(discord_id, new_access_token)
                access_token = new_access_token
            else:
                return None, None
        elif response.status_code != 200:
            return None, None
        return access_token, refresh_token

    async def get_current_track(self, access_token):
        current_track_url = 'https://api.spotify.com/v1/me/player/currently-playing'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(current_track_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data and data.get('is_playing', False):
                track = data['item']
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                track_url = track['external_urls']['spotify']
                return track_name, artist_name, track_url
        return None, None, None

    async def save_selected_device(self, discord_id, device_id):
        query = "INSERT INTO spotify_devices (discord_id, device_id) VALUES ($1, $2) ON CONFLICT (discord_id) DO UPDATE SET device_id = $2"
        await self.bot.db.execute(query, discord_id, device_id)

    async def get_selected_device_from_db(self, discord_id):
        query = "SELECT device_id FROM spotify_devices WHERE discord_id = $1"
        result = await self.bot.db.fetchval(query, discord_id)
        return result

    async def activate_device(self, access_token, device_id):
        player_url = 'https://api.spotify.com/v1/me/player'
        headers = {'Authorization': f'Bearer {access_token}'}
        data = {
            'device_ids': [device_id],
            'play': False
        }
        response = requests.put(player_url, headers=headers, json=data)
        return response.status_code == 204
    
    async def get_playlists(self, access_token):
        playlists_url = 'https://api.spotify.com/v1/me/playlists'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(playlists_url, headers=headers)

        if response.status_code == 200:
            playlists_data = response.json()
            playlists = [
                {"name": playlist["name"], "id": playlist["id"], "url": playlist["external_urls"]["spotify"]}
                for playlist in playlists_data["items"]
            ]
            return playlists
        return None

    async def play_playlist(self, access_token, device_id, playlist_uri):
        play_url = 'https://api.spotify.com/v1/me/player/play'
        headers = {'Authorization': f'Bearer {access_token}'}
        json_data = {
            'context_uri': playlist_uri,
            'device_id': device_id
        }
        response = requests.put(play_url, headers=headers, json=json_data)
        return response.status_code == 204

    @group(name="spotify", aliases=["sp"], invoke_without_command=True, case_insensitive=True)
    async def spotify(self, ctx: EvelinaContext):
        """Spotify Integration Commands"""
        return await ctx.create_pages()

    @spotify.command(name="login")
    async def spotify_login(self, ctx: EvelinaContext):
        """Login to your Spotify account"""
        discord_id = ctx.author.id
        tokens = await self.get_spotify_tokens(discord_id)
        if tokens is not None:
            access_token = tokens['access_token']
            user_profile_url = 'https://api.spotify.com/v1/me'
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(user_profile_url, headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                spotify_username = user_data.get('display_name', 'Unknown User')  # Fallback if no name available
                await ctx.send_warning(f"You are already logged in as **{spotify_username}**\n> Use `{ctx.clean_prefix}spotify logout` to logout")
            else:
                await ctx.send_warning(f"You are already logged in\n> Use `{ctx.clean_prefix}spotify logout` to logout")
            return
        await ctx.spotify_send(f"Click [**here**](https://evelina.bot/spotify) to **grant** Evelina access to your **Spotify account**. Once you've passed the **authorization**, you can use the Spotify commands")

    @spotify.command(name="logout")
    async def spotify_logout(self, ctx: EvelinaContext):
        """Logout from Spotify your account"""
        discord_id = ctx.author.id
        tokens = await self.get_spotify_tokens(discord_id)
        if tokens is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return
        query = "DELETE FROM spotify_tokens WHERE discord_id = $1"
        await self.bot.db.execute(query, discord_id)
        await ctx.spotify_send("Logged out successfully")

    @spotify.command(name="play", usage="spotify play ufo361, allein")
    async def spotify_play(self, ctx: EvelinaContext, *, track: str):
        """Start playing a track on Spotify"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        selected_device_id = await self.get_selected_device_from_db(discord_id)
        if not selected_device_id:
            await ctx.send_warning(f"You haven't selected a device\n> Use `{ctx.clean_prefix}spotify device` to choose a device")
            return

        device_activated = await self.activate_device(access_token, selected_device_id)
        if not device_activated:
            await ctx.send_warning("Failed to activate the selected device, try again later")
            return
        
        search_url = 'https://api.spotify.com/v1/search'
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'q': track, 'type': 'track', 'limit': 1}
        
        response = requests.get(search_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['tracks']['items']:
                track = data['tracks']['items'][0]
                track_uri = track['uri']
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                track_url = track['external_urls']['spotify']
                
                play_url = 'https://api.spotify.com/v1/me/player/play'
                json_data = {
                    'uris': [track_uri],
                    'device_id': selected_device_id
                }
                response = requests.put(play_url, headers=headers, json=json_data)
                if response.status_code == 204:
                    await ctx.spotify_send(f"Playing: [**{track_name}**]({track_url}) by **{artist_name}**")
                else:
                    await ctx.send_warning(f"An error occurred while playing the track")
            else:
                await ctx.send_warning(f"Track **{track}** not found on Spotify")

    @spotify.command(name="pause")
    async def spotify_pause(self, ctx: EvelinaContext):
        """Pause the current playback on Spotify if it is not already paused"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        selected_device_id = await self.get_selected_device_from_db(discord_id)
        if not selected_device_id:
            await ctx.send_warning("You haven't selected a device\n> Use `spotify device` to choose a device")
            return

        pause_url = 'https://api.spotify.com/v1/me/player/pause'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.put(pause_url, headers=headers, json={'device_id': selected_device_id})
        if response.status_code == 200:
            await ctx.spotify_send("Playback paused successfully")
        else:
            await ctx.send_warning(f"An error occurred while pausing the playback")

    @spotify.command(name="resume")
    async def spotify_resume(self, ctx: EvelinaContext):
        """Resume playback on Spotify if it is currently paused"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        selected_device_id = await self.get_selected_device_from_db(discord_id)
        if not selected_device_id:
            await ctx.send_warning("You haven't selected a device\n> Use `spotify device` to choose a device")
            return

        resume_url = 'https://api.spotify.com/v1/me/player/play'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.put(resume_url, headers=headers, json={'device_id': selected_device_id})
        if response.status_code == 200:
            await ctx.spotify_send("Track resumed successfully")
        else:
            await ctx.send_warning(f"An error occurred while resuming the playback")

    @spotify.command(name="devices", aliases=["device"])
    async def spotify_devices(self, ctx: EvelinaContext):
        """Shows available devices for Spotify playback with a dropdown menu"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        devices_url = 'https://api.spotify.com/v1/me/player/devices'
        headers = {'Authorization': f'Bearer ' + access_token}
        response = requests.get(devices_url, headers=headers)
        if response.status_code == 200:
            devices = response.json()['devices']
            if devices:
                device_type_emojis = {
                    'Computer': '💻',
                    'Smartphone': '📱',
                    'Speaker': '🔊',
                    'TV': '📺',
                    'AVR': '🎛️',
                    'STB': '📦',
                    'AudioDongle': '🎧',
                    'CastVideo': '📡',
                    'CastAudio': '🔈',
                    'Automobile': '🚗',
                    'GameConsole': '🎮',
                    'Unknown': '❓'
                }
                options = [
                    SelectOption(
                        label=device['name'], 
                        emoji=device_type_emojis.get(device['type'], '❓'),
                        value=device['id']
                    )
                    for device in devices
                ]

                class DeviceSelect(discord.ui.Select):
                    def __init__(self, parent_view):
                        super().__init__(placeholder="Choose a Spotify device", options=options, min_values=1, max_values=1)
                        self.parent_view = parent_view

                    async def callback(self, interaction: discord.Interaction):
                        selected_device_id = self.values[0]
                        selected_device = next((device for device in devices if device['id'] == selected_device_id), None)
                        if selected_device:
                            await self.parent_view.save_device_and_activate(ctx, discord_id, access_token, selected_device, interaction)
                        else:
                            await interaction.response.send_message("An error occurred white selecting devices", ephemeral=True)

                class DeviceView(discord.ui.View):
                    def __init__(self, parent):
                        super().__init__()
                        self.parent = parent
                        self.add_item(DeviceSelect(self))

                    async def save_device_and_activate(self, ctx, discord_id, access_token, selected_device, interaction):
                        await self.parent.save_selected_device(discord_id, selected_device['id'])
                        await self.parent.activate_device(access_token, selected_device['id'])
                        for child in self.children:
                            child.disabled = True
                        embed = Embed(color=colors.SPOTIFY, description=f"{emojis.SPOTIFY} {interaction.user.mention}: Selected device: **{selected_device['name']}**")
                        await interaction.message.edit(embed=embed, view=None)

                view = DeviceView(self)
                embed = Embed(color=colors.SPOTIFY, description=f"{emojis.SPOTIFY} {ctx.author.mention}: Please choose a device from the dropdown:")
                await ctx.send(embed=embed, view=view)
            else:
                await ctx.send_warning("No devices found, open Spotify on a device to see it here")
        else:
            await ctx.send_warning("An error occurred while fetching devices")

    @spotify.command(name="current")
    async def spotify_current(self, ctx: EvelinaContext):
        """Displays the currently playing track on Spotify"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        track_name, artist_name, track_url = await self.get_current_track(access_token)
        if track_name is None:
            await ctx.send_warning("No track is currently playing")
            return

        await ctx.spotify_send(f"Currently playing: [**{track_name}**]({track_url}) by **{artist_name}**")

    @spotify.command(name="volume", aliases=["vol"], usage="spotify volume 75")
    async def spotify_volume(self, ctx: EvelinaContext, volume: int = None):
        """Check or set the volume on the selected Spotify device"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        selected_device_id = await self.get_selected_device_from_db(discord_id)
        if not selected_device_id:
            await ctx.send_warning(f"You haven't selected a device\n> Use `{ctx.clean_prefix}spotify device` to choose a device")
            return

        if volume is None:
            playback_status_url = 'https://api.spotify.com/v1/me/player'
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(playback_status_url, headers=headers)

            if response.status_code == 200:
                data = response.json()
                if data and data.get('device', {}).get('volume_percent') is not None:
                    current_volume = data['device']['volume_percent']
                    await ctx.spotify_send(f"Current volume: **{current_volume}%**")
                else:
                    await ctx.send_warning("Failed to retrieve the current volume.")
            else:
                await ctx.send_warning("Failed to retrieve the playback status.")
        else:
            if volume < 0 or volume > 100:
                await ctx.send_warning("Volume must be between 0 and 100.")
                return

            volume_url = f'https://api.spotify.com/v1/me/player/volume?volume_percent={volume}&device_id={selected_device_id}'
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.put(volume_url, headers=headers)

            if response.status_code == 204:
                await ctx.spotify_send(f"Volume set to **{volume}%**")
            else:
                await ctx.send_warning("Failed to set the volume. Make sure a device is active and try again.")

    @spotify.command(name="info", usage="spotify info comminate")
    async def spotify_info(self, ctx: EvelinaContext, user: discord.Member = Author):
        """Displays information about the connected Spotify account and active device."""
        discord_id = user.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            if user.id != ctx.author.id:
                await ctx.send_warning(f"**{user.name}** hasn't linked their Spotify account yet")
                return
            else:
                await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
                return

        user_profile_url = 'https://api.spotify.com/v1/me'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(user_profile_url, headers=headers)

        if response.status_code != 200:
            await ctx.send_warning("Failed to retrieve Spotify user information.")
            return

        user_data = response.json()
        spotify_username = user_data.get('display_name', 'Unknown User')
        spotify_images = user_data.get('images', [])
        spotify_avatar = spotify_images[0].get('url', None) if spotify_images else None
        spotify_user_id = user_data.get('id', 'Unknown ID')
        product = user_data.get('product', 'Free')

        playback_status_url = 'https://api.spotify.com/v1/me/player'
        response = requests.get(playback_status_url, headers=headers)
        
        device_info = "No active device found."
        if response.status_code == 200:
            playback_data = response.json()
            device_data = playback_data.get('device')
            if device_data:
                device_name = device_data.get('name', 'Unknown Device')
                device_id = device_data.get('id', 'Unknown ID')
                device_volume = device_data.get('volume_percent', 'Unknown Volume')
                device_info = f"**{device_name}**\n> `{device_id}`"

        embed = discord.Embed(title="Spotify Account Information", color=colors.SPOTIFY)
        embed.set_author(name=spotify_username, icon_url=spotify_avatar)
        embed.add_field(name="Account ID", value=f"`{spotify_user_id}`", inline=True)
        embed.add_field(name="Subscription", value=f"{str(product).capitalize()}", inline=True)
        if device_info is not None:
            embed.add_field(name="Active Device", value=device_info, inline=False)

        await ctx.send(embed=embed)

    @spotify.command(name="skip")
    async def spotify_skip(self, ctx: EvelinaContext):
        """Skip to the next track"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        selected_device_id = await self.get_selected_device_from_db(discord_id)
        if not selected_device_id:
            await ctx.send_warning(f"You haven't selected a device\n> Use `{ctx.clean_prefix}spotify device` to choose a device")
            return

        skip_url = 'https://api.spotify.com/v1/me/player/next'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.post(skip_url, headers=headers, json={'device_id': selected_device_id})

        if response.status_code == 200:
            await asyncio.sleep(1)
            track_name, artist_name, track_url = await self.get_current_track(access_token)
            if track_name:
                await ctx.spotify_send(f"Skipped to: [**{track_name}**]({track_url}) by **{artist_name}**")
            else:
                await ctx.spotify_send("Skipped to the next track, but unable to retrieve track information.")
        else:
            await ctx.send_warning("Failed to skip to the next track. Please try again later.")

    @spotify.command(name="back")
    async def spotify_back(self, ctx: EvelinaContext):
        """Go back to the previous track"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        selected_device_id = await self.get_selected_device_from_db(discord_id)
        if not selected_device_id:
            await ctx.send_warning(f"You haven't selected a device\n> Use `{ctx.clean_prefix}spotify device` to choose a device")
            return

        back_url = 'https://api.spotify.com/v1/me/player/previous'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.post(back_url, headers=headers, json={'device_id': selected_device_id})

        if response.status_code == 200:
            await asyncio.sleep(1)
            track_name, artist_name, track_url = await self.get_current_track(access_token)
            if track_name:
                await ctx.spotify_send(f"Back to: [**{track_name}**]({track_url}) by **{artist_name}**")
            else:
                await ctx.spotify_send("Went back to the previous track, but unable to retrieve track information.")
        else:
            await ctx.send_warning("Failed to go back to the previous track. Please try again later.")

    @spotify.command(name="playlists")
    async def spotify_playlists(self, ctx: EvelinaContext):
        """Displays all Spotify playlists of the user"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return
        playlists = await self.get_playlists(access_token)
        if playlists is None or len(playlists) == 0:
            await ctx.send_warning("No playlists found.")
            return
        playlist_names = [f"**{playlist['name']}**" for idx, playlist in enumerate(playlists)]
        await ctx.paginate(playlist_names, "Your Spotify Playlists")

    @spotify.command(name="playlist", usage="spotify playlist Chill")
    async def spotify_playlist(self, ctx: EvelinaContext, *, name: str):
        """Plays a specific Spotify playlist by name"""
        discord_id = ctx.author.id
        access_token, refresh_token = await self.ensure_access_token(discord_id)
        if access_token is None:
            await ctx.send_warning(f"You haven't linked your Spotify account yet\n> Use `{ctx.clean_prefix}spotify login` to link your account")
            return

        selected_device_id = await self.get_selected_device_from_db(discord_id)
        if not selected_device_id:
            await ctx.send_warning(f"You haven't selected a device\n> Use `{ctx.clean_prefix}spotify device` to choose a device")
            return

        playlists = await self.get_playlists(access_token)
        if playlists is None or len(playlists) == 0:
            await ctx.send_warning("No playlists found.")
            return

        matching_playlist = next((playlist for playlist in playlists if name.lower() in playlist['name'].lower()), None)
        if not matching_playlist:
            await ctx.send_warning(f"No playlist found with the name **{name}**.")
            return

        playlist_uri = f"spotify:playlist:{matching_playlist['id']}"
        success = await self.play_playlist(access_token, selected_device_id, playlist_uri)

        if success:
            await ctx.spotify_send(f"Playing playlist: [**{matching_playlist['name']}**]({matching_playlist['url']})")
        else:
            await ctx.send_warning("Failed to play the selected playlist. Please try again.")

async def setup(bot: Evelina):
    return await bot.add_cog(Spotify(bot))