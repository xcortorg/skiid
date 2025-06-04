from sanic import Sanic, json, raw
from discord.ext.commands import Cog, AutoShardedBot
from discord import Client
from sanic.request import Request
from loguru import logger
from discord.ext import tasks
from ..patch.help import map_check
from tuuid import tuuid
from base64 import b64decode
from ..worker import offloaded
from .cors import setup_options, add_cors_headers

import traceback
import datetime
import socket


ADDRESS = {
    "host": "127.0.0.1",
    "port": 1274
}

DOMAIN = "api.kainu.sh"

def check_port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
        except socket.error:
            return True  # Port is in use
    return False  # Port is available

@offloaded
def check_port(port: int):
    EXCLUDED = ["cloudflar"]
    import subprocess
    result = subprocess.run(
        ['sudo', 'lsof', '-n', f'-i:{port}'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # Check and print output
    lines = result.stdout.splitlines()
    data = []
    row_names = ['command', 'pid', 'user', 'fd', 'type', 'device', 'size/off', 'node', 'range', 'status']
    for i, line in enumerate(lines, start = 1):
        if i != 1:
            rows = [m for m in line.split(" ") if m != '']
            data.append({row_names[num-1]: value for num, value in enumerate(rows, start = 1)})
    return [d for d in data if d.get('name') not in EXCLUDED]

@offloaded
def kill_process(data: list):
    import subprocess
    killed_processes = []
    for d in data:
        if d['pid'] in killed_processes:
            continue
        try:
            subprocess.run(
                [
                    'kill',
                    '-9',
                    str(d['pid'])
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            killed_processes.append(d['pid'])
        except Exception:
            pass
    return True

class WebServer(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.app = Sanic(name = f"{self.bot.user.name.title().replace(' ', '-')}")
        self.app.register_listener(setup_options, "before_server_start")
        self.app.register_middleware(add_cors_headers, "response")
        self.server = None
        self._commands = None
        self.statistics = None
        self.domain = DOMAIN
        self.assets = {}
        self.app.add_route(self.lastfm_token, "/lastfm", methods = ["GET", "POST"])
        self.app.add_route(self.index, "/", methods = ["GET", "POST"])
        self.app.add_route(self.statistics_, "/statistics", methods = ["GET", "POST"])
        self.app.add_route(self.status, "/status", methods = ["GET", "POST"])
        self.app.add_route(self.asset, "/asset/<path>", methods = ["GET"])
        self.app.add_route(self.shards, "/shards", methods = ["GET"])
        self.app.add_route(self.avatar, "/avatar.png", methods = ["GET"])
        self.app.add_route(self.giveaway, "/giveaway/<guild_id>/<channel_id>/<message_id>", methods = ["GET", "OPTIONS"])

    async def lastfm_token(self, request: Request):
        logger.info(request.url)
        await self.bot.db.execute("""INSERT INTO lastfm_data (user_id, token) VALUES($1, $2) ON CONFLICT(user_id) DO UPDATE SET token = excluded.token""", request.url.split("?user_id=", 1)[1].split("&", 1)[0], request.url.split("&token=", 1)[1])
        return json({"message": "Token saved"})

    @tasks.loop(minutes = 1)
    async def redump_loop(self):
        logger.info("dumping statistics and commands to the webserver")
        try:
            self._commands = await self.dump_commandsXD()
            self.statistics = {"guilds": len(self.bot.guilds), "users": sum(self.bot.get_all_members())}
        except Exception as error:
            exc = "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            logger.error(
                f'Unhandled exception in internal background task redump_loop. {type(error).__name__:25} > \n {error} \n {exc}'
            )

    async def run(self):
        if check_port_in_use(ADDRESS['host'], ADDRESS['port']):
            await kill_process(await check_port(ADDRESS['port']))
        self.server = await self.app.create_server(
            **ADDRESS, return_asyncio_server=True
        )

        if self.server is None:
            return

        await self.server.startup()
        await self.server.serve_forever()

    async def giveaway(self, request: Request, guild_id: int, channel_id: int, message_id: int):
        data = await self.bot.db.fetchrow("""SELECT expiration FROM giveaways WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""", guild_id, channel_id, message_id)
        if data is None:
            return json({"message": "No giveaway found"})
        return json({"end": data.expiration.timestamp()})

    async def dump_commandsXD(self):
        commands = {"Kick": []}
        def get_usage(command):
            if not command.clean_params:
                return "None"
            return ", ".join(m for m in [str(c) for c in command.clean_params.keys()])

        def get_aliases(command):
            if len(command.aliases) == 0:
                return ["None"]
            return command.aliases

        def get_category(command):
            if "settings" not in command.qualified_name:
                return command.cog_name
            else:
                return "settings"

        excluded = ["owner", "errors", "webserver", "jishaku", "control"]
        for command in self.bot.walk_commands():
            description = command.description or command.help
            if cog := command.cog_name:
                if cog.lower() in excluded:
                    continue
                if command.hidden or not description:
                    continue
                if not commands.get(command.cog_name):
                    commands[command.cog_name] = []
                if not command.perms:
                    permissions = ["send_messages"]
                else:
                    permissions = command.perms
                if len(command.checks) > 0:
                    permissions.extend([map_check(c).replace("`", "") for c in command.checks if map_check(c)])
                permissions = list(set(permissions))
                cog_name = command.extras.get("cog_name", command.cog_name)
                commands[cog_name].append(
                    {
                        "name": command.qualified_name,
                        "help": description or "",
                        "brief": [permissions.replace("_", " ").title()]
                        if not isinstance(permissions, list)
                        else [_.replace("_", " ").title() for _ in permissions],
                        "usage": [f"{k.replace('_', ' or ')}" for k in command.clean_params.keys()],
                        "example": command.example or ""
                    }
                )
        return commands
    
    async def index(self, request: Request):
        if not self._commands or len(list(self._commands.keys())) == 1:
            self._commands = await self.dump_commandsXD()
        return json(self._commands)
    
    async def statistics_(self, request: Request):
        if not self.statistics:
            self.statistics = {"guilds": len(self.bot.guilds), "users": sum(self.bot.get_all_members())}
        return json(self.statistics)

    async def avatar(self, request: Request):
        byte = await self.bot.user.avatar.read()
        return raw(byte, status=200, content_type="image/png")
    
    async def shards(self, request: Request):
        data = {}
        for sh in self.bot.shards:
            shard = self.bot.get_shard(sh)
            if shard.is_ws_ratelimited():
                status = "Partial Outage"
            else:
                status = "Operational"
            data[str(shard.id)] = {}
            members = [
                len(guild.members)
                for guild in self.bot.guilds
                if guild.shard_id == shard.id
            ]
            shard_guilds = [
                int(g.id) for g in self.bot.guilds if g.shard_id == shard.id
            ]
            data[str(shard.id)]["shard_id"] = shard.id
            data[str(shard.id)]["shard_name"] = f"Shard {shard.id}"
            data[str(shard.id)]["status"] = status
            data[str(shard.id)]["guilds"] = len(shard_guilds)
            data[str(shard.id)]["users"] = sum(members)
            data[str(shard.id)]["latency"] = round(shard.latency * 1000)
            data[str(shard.id)]["pinged"] = int(datetime.datetime.now().timestamp())
            data[str(shard.id)]["uptime"] = int(self.bot.startup_time.timestamp())
            data[str(shard.id)]["guild_ids"] = shard_guilds
        return json(data)
    
    async def status(self, request: Request):
        data = []
        if isinstance(self.bot, AutoShardedBot):
            for shard_id, shard in self.bot.shards.items():
                guilds = [g for g in self.bot.guilds if g.shard_id == shard_id]
                users = sum([len(g.members) for g in guilds])
                data.append(
                    {
                        "uptime": self.bot.startup_time.timestamp(),
                        "latency": round(shard.latency * 1000),
                        "servers": len(
                            [g for g in self.bot.guilds if g.shard_id == shard_id]
                        ),
                        "users": users,
                        "shard": shard_id,
                    }
                )
        else:
            data.append({"uptime": self.bot.startup_time.timestamp(), "latency": round(self.bot.latency * 1000), "servers": len(self.bot.guilds), "users": sum(self.bot.get_all_members()), "shard_id": -1})
        return json(data)
    
    async def asset(self, request: Request, path: str):
        if not (entry := self.assets.get(path.split(".")[0])):
            return json({"message": "File not found"}, status=404)
        image_data, content_type = entry
        return raw(image_data, status=200, content_type=content_type)
    
    async def add_asset(self, b64_string: str, **kwargs):
        content_type, base64_str = b64_string.split(",")[0].split(":")[1].split(";")[0], b64_string.split(",")[1]
        image_data = b64decode(base64_str)
        name = kwargs.pop("name", tuuid())
        self.assets[name] = (image_data, content_type)
        return f"https://{self.domain}/asset/{name}"
    
    async def cog_load(self):
        self.redump_loop.start()
        self.bot.loop.create_task(self.run())

    async def cog_unload(self):
        self.redump_loop.stop()
        self.bot.loop.create_task(self.server.close())

async def setup(bot: Client):
    await bot.add_cog(WebServer(bot))