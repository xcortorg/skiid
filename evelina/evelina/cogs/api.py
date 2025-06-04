import os
import re
import json
import asyncio
import aiohttp
from aiohttp import web
from datetime import datetime, timedelta
import threading

from discord import Embed, Spotify
from discord.ext import commands
from discord.ext.commands import Cog, command, is_owner

from modules.styles import colors
from modules.evelinabot import EvelinaContext, Evelina

def get_command_info(command):
    return {
        "name": command.qualified_name, 
        "description": command.description or command.help or "N/A",
        "permissions": command.brief or "N/A",
        "aliases": command.aliases or [],
        "category": command.cog_name.lower() if command.cog_name else "",
        "arguments": ', '.join(command.clean_params.keys()) if command.clean_params else 'N/A',
    }

def get_commands_info(commands_list):
    commands_info = []
    excluded_cogs = []
    def add_subcommands(subcommands):
        for subcommand in subcommands:
            commands_info.append(get_command_info(subcommand))
            if isinstance(subcommand, commands.Group):
                add_subcommands(subcommand.commands)
    for command in commands_list:
        if command.cog_name and command.cog_name.lower() in excluded_cogs:
            continue
        commands_info.append(get_command_info(command))
        if isinstance(command, commands.Group):
            add_subcommands(command.commands)
    return commands_info

class Api(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.last_save = datetime.min
        self.banners = {}
        self.decorations = {}
        
        self.api_app = web.Application()
        self.api_app.router.add_get('/shards', self.get_shards)
        self.api_app.router.add_get('/commands', self.get_commands_endpoint)
        self.api_app.router.add_get('/team', self.get_team)
        self.api_app.router.add_get('/templates', self.get_templates)
        self.api_app.router.add_get('/feedback', self.get_feedback)
        self.api_app.router.add_get('/avatars', self.get_avatars)
        self.api_app.router.add_get('/avatars/{user_id}', self.get_user_avatars)
        self.api_app.router.add_get('/history', self.get_history)
        self.api_app.router.add_get('/user/{user_id}', self.get_user)
        self.api_runner = None
        
        self.static_app = web.Application()
        self.static_app.router.add_get('/{hash}', self.serve_static_file)
        self.static_app.router.add_get('/{hash}/', self.serve_static_file)
        self.static_app.router.add_get('/{hash}/index.html', self.serve_static_file)
        self.static_runner = None
        
        asyncio.create_task(self.start_webservers())

    async def serve_static_file(self, request):
        hash_value = request.match_info['hash']
        file_path = os.path.join('/var/www/html', hash_value)
        
        if os.path.isdir(file_path):
            file_path = os.path.join(file_path, 'index.html')
        
        if not os.path.abspath(file_path).startswith('/var/www/html/'):
            raise web.HTTPForbidden()
            
        if not os.path.exists(file_path):
            raise web.HTTPNotFound()
            
        return web.FileResponse(file_path)

    async def start_webservers(self):
        await self.bot.wait_until_ready()
        
        self.api_runner = web.AppRunner(self.api_app)
        await self.api_runner.setup()
        api_site = web.TCPSite(self.api_runner, '0.0.0.0', 3002)
        await api_site.start()
        print(f"API server running on port 3002")
        
        self.static_runner = web.AppRunner(self.static_app)
        await self.static_runner.setup()
        static_site = web.TCPSite(self.static_runner, '0.0.0.0', 3003)
        await static_site.start()
        print(f"Static file server running on port 3003")

    async def get_team(self, request):
        try:
            team = await self.bot.db.fetch("SELECT * FROM team_members")
            team_info = []
            for member in team:
                team_info.append({
                    'user_id': str(member['user_id']),
                    'rank': member['rank'],
                    'socials': member['socials']
                })
            return web.json_response(team_info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def get_templates(self, request):
        try:
            templates = await self.bot.db.fetch("SELECT * FROM embeds_templates ORDER BY id DESC")
            templates_info = []
            for template in templates:
                templates_info.append({
                    'id': str(template['id']),
                    'name': str(template['name']),
                    'user_id': str(template['user_id']),
                    'code': str(template['code']),
                    'embed': str(template['embed']),
                    'image': str(template['image']),
                })
            return web.json_response(templates_info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def get_feedback(self, request):
        try:
            feedback = await self.bot.db.fetch("SELECT * FROM testimonials")
            feedback_info = []
            for message in feedback:
                feedback_info.append({
                    'guild_id': str(message['guild_id']),
                    'user_id': str(message['user_id']),
                    'message_id': str(message['message_id']),
                    'feedback': str(message['feedback']),
                    'approved': message['approved'],
                })
            return web.json_response(feedback_info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def get_avatars(self, request):
        try:
            avatars = await self.bot.db.fetch("SELECT * FROM avatar_history")
            avatars_info = []
            for avatar in avatars:
                avatars_info.append({
                    'user_id': str(avatar['user_id']),
                    'avatar': str(avatar['avatar']),
                    'timestamp': avatar['timestamp'],
                })
            return web.json_response(avatars_info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def get_user_avatars(self, request):
        try:
            user_id = int(request.match_info['user_id'])
            avatars = await self.bot.db.fetch("SELECT * FROM avatar_history WHERE user_id = $1", user_id)
            avatars_info = []
            for avatar in avatars:
                avatars_info.append({
                    'user_id': str(avatar['user_id']),
                    'avatar': str(avatar['avatar']),
                    'timestamp': avatar['timestamp'],
                })
            return web.json_response(avatars_info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def get_history(self, request):
        try:
            history = await self.bot.db.fetch("SELECT * FROM growth")
            history_info = []
            for entry in history:
                history_info.append({
                    'guilds': entry['guilds'],
                    'users': entry['users'],
                    'ping': entry['ping'],
                    'timestamp': entry['timestamp'].isoformat() if entry['timestamp'] else None
                })
            return web.json_response(history_info)
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    async def get_user(self, request):
        try:
            user_id = int(request.match_info['user_id'])
            user = self.bot.get_user(user_id)
            if not user:
                user = await self.bot.fetch_user(user_id)
                if not user:
                    return web.json_response({'error': 'User not found'}, status=404)

            activity_name = ""
            activity_details = ""
            activity_state = ""
            activity_image = ""
            activity_emoji = ""

            guild = self.bot.get_guild(self.bot.logging_guild)
            if guild:
                member = guild.get_member(user.id)
                if member and member.activity:
                    if member.activity.type.value == 4:
                        activity_name = member.activity.name
                        activity_state = ""
                        activity_emoji = member.activity.emoji.url if member.activity.emoji else ""
                    elif isinstance(member.activity, Spotify):
                        activity_name = "Spotify"
                        activity_details = f"{member.activity.title}"
                        activity_state = f"by {member.activity.artist}"
                        activity_image = member.activity.album_cover_url
                    elif member.activity.type.value in [0, 1, 2, 3]:
                        activity_name = member.activity.name
                        activity_details = getattr(member.activity, 'details', '')
                        activity_state = getattr(member.activity, 'state', '')
                        activity_image = getattr(member.activity, 'large_image_url', '')

            if user_id in self.banners:
                banner = self.banners[user_id]
            else:
                user_obj = await self.bot.fetch_user(user_id)
                banner = user_obj.banner.url if user_obj.banner else f"https://place-hold.it/680x240/000001?text=%20"
                self.banners[user_id] = banner
                asyncio.get_event_loop().call_later(60, lambda: self.banners.pop(user_id, None))

            if user_id in self.decorations:
                decoration = self.decorations[user_id]
            else:
                decoration = user_obj.avatar_decoration.url if user_obj.avatar_decoration else None
                self.decorations[user_id] = decoration
                asyncio.get_event_loop().call_later(60, lambda: self.decorations.pop(user_id, None))

            return web.json_response({
                'user': user.name,
                'avatar': user.avatar.url if user.avatar else user.default_avatar.url,
                'banner': user.banner.url if user.banner else banner,
                'decoration': user.avatar_decoration.url if user.avatar_decoration else decoration,
                'activity': {
                    'name': activity_name,
                    'details': activity_details,
                    'state': activity_state,
                    'image': activity_image,
                    'emoji': activity_emoji
                }
            })
        except Exception as e:
            return web.json_response({'error': str(e)}, status=500)

    def parse_duration(self, duration_str):
        duration_pattern = r'(?P<value>\d+)\s*(?P<unit>seconds?|minutes?|hours?|days?)'
        match = re.match(duration_pattern, duration_str)
        if not match:
            raise ValueError(f"Unsupported duration format: {duration_str}")
        value = int(match.group('value'))
        unit = match.group('unit').lower()
        if 'second' in unit:
            return timedelta(seconds=value)
        elif 'minute' in unit:
            return timedelta(minutes=value)
        elif 'hour' in unit:
            return timedelta(hours=value)
        elif 'day' in unit:
            return timedelta(days=value)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

    def get_shards_data(self):
        shard_data = []
        for shard_id, shard in self.bot.shards.items():
            latency_ms = float('inf') if shard.latency == float('inf') else round(shard.latency * 1000)
            uptime = self.bot.uptime
            if isinstance(uptime, str):
                try:
                    uptime_duration = self.parse_duration(uptime)
                    uptime = datetime.now() - uptime_duration
                except ValueError:
                    uptime = None
            shard_info = {
                'shard_id': shard_id,
                'is_ready': not shard.is_closed(),
                'server_count': sum(1 for guild in self.bot.guilds if guild.shard_id == shard_id),
                'member_count': sum(guild.member_count for guild in self.bot.guilds if guild.shard_id == shard_id),
                'uptime': (datetime.now() - uptime).total_seconds() if uptime else None,
                'latency': latency_ms,
                'last_updated': datetime.now().isoformat()
            }
            shard_data.append(shard_info)
        return shard_data

    async def get_shards(self, request):
        return web.json_response(self.get_shards_data())

    async def get_commands_endpoint(self, request):
        commands_info = get_commands_info(self.bot.commands)
        return web.json_response(commands_info)

    @Cog.listener("on_message")
    async def on_message(self, _):
        if self.bot.is_ready():
            check = await self.bot.db.fetchrow("SELECT timestamp FROM growth ORDER BY timestamp DESC LIMIT 1")
            if not check or check[0] < datetime.now() - timedelta(minutes=1):
                guilds = len(self.bot.guilds)
                users = sum(g.member_count or 0 for g in self.bot.guilds)
                latency = self.bot.latency
                ping = round(latency * 1000) if latency != float('inf') else -1
                await self.bot.db.execute(
                    "INSERT INTO growth (guilds, users, ping, timestamp) VALUES ($1, $2, $3, $4)",
                    guilds, users, ping, datetime.now()
                )

    async def cog_unload(self):
        if self.api_runner:
            await self.api_runner.cleanup()
        if self.static_runner:
            await self.static_runner.cleanup()

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Api(bot))