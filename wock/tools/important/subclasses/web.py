import datetime
from contextlib import suppress
from typing import List, Optional, Union

import ujson
from aiohttp.web import Application, Request, Response, _run_app, json_response
from discord.ext.commands import Cog, Command, Group
from prometheus_async import aio  # type: ignore

ADDRESS = {
    "host": "0.0.0.0",
    "port": 8493,
}


class WebServer(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.app = Application()
        self.app.router.add_get("/", self.index)
        self.app.router.add_get("/avatars/{id}", self.avatars)
        self.app.router.add_get("/commands", self.commandz)
        self.app.router.add_get("/raw", self.command_dump)
        self.app.router.add_get("/status", self.status)
        self.app.router.add_get("/metrics", aio.web.server_stats)

    async def cog_load(self):
        self.bot.loop.create_task(self.run())

    async def cog_unload(self):
        await self.app.shutdown()

    async def run(self):
        await _run_app(self.app, **ADDRESS, print=None)  # type: ignore

    @staticmethod
    async def index(request: Request) -> Response:
        return Response(text="hey this site belongs to icy.com kid", status=200)

    async def status(self, request: Request) -> Response:
        data = []
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
        return json_response(data)

    async def avatars(self, request: Request) -> Response:
        id = request.match_info["id"]
        if data := await self.bot.db.fetch(
            "SELECT * FROM avatars WHERE user_id = $1 ORDER BY time ASC", int(id)
        ):
            user = self.bot.get_user(int(id))
            data2 = {
                "id": data[0]["user_id"],
                "avatars": [x["avatar"] for x in data],
                "time": datetime.datetime.fromtimestamp(int(data[0]["time"])).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            }
            if user:
                data2["user"] = (
                    {
                        "name": user.name,
                        "discriminator": user.discriminator,
                        "id": user.id,
                    },
                )
            else:
                data2["user"] = {
                    "name": data[0]["username"],
                    "discriminator": "0000",
                    "id": id,
                }
            return json_response(data2)
        else:
            return json_response({"error": "No data found"}, status=404)

    def get_permissions(
        self, command: Union[Command, Group], bot: Optional[bool] = False
    ) -> Optional[List[str]]:
        permissions = []
        if not bot:
            if command.permissions:
                if isinstance(command.permissions, list):
                    permissions.extend(
                        [c.replace("_", " ").title() for c in command.permissions]
                    )
                else:
                    permissions.append(command.permissions.replace("_", " ").title())
                if command.cog_name.title() == "Premium":
                    permissions.append("Donator")
        else:
            if command.bot_permissions:
                if isinstance(command.bot_permissions, list):
                    permissions.extend(
                        [c.replace("_", " ").title() for c in command.bot_permissions]
                    )
                else:
                    permissions.append(
                        command.bot_permissions.replace("_", " ").title()
                    )
        return permissions

    async def command_dump(self, request: Request) -> Response:
        commands = []
        for command in self.bot.walk_commands():
            if command.hidden:
                continue
            if isinstance(command, Group):
                if not command.description:
                    continue
            if command.qualified_name == "help":
                continue
            commands.append(
                {
                    "name": command.qualified_name,
                    "description": command.brief,
                    "permissions": self.get_permissions(command),
                    "bot_permissions": self.get_permissions(command, True),
                    "usage": command.usage,
                    "example": command.example,
                }
            )
        return json_response(commands)

    async def commandz(self, req: Request) -> Response:
        output = ""
        for name, cog in sorted(self.bot.cogs.items(), key=lambda cog: cog[0].lower()):
            if name.lower() in ("jishaku", "Develoepr"):
                continue

            _commands = list()
            for command in cog.walk_commands():
                if command.hidden:
                    continue

                usage = " " + command.usage if command.usage else ""
                aliases = (
                    "(" + ", ".join(command.aliases) + ")" if command.aliases else ""
                )
                if isinstance(command, Group) and not command.root_parent:
                    _commands.append(
                        f"|    ├── {command.name}{aliases}: {command.brief or 'No description'}"
                    )
                elif not isinstance(command, Group) and command.root_parent:
                    _commands.append(
                        f"|    |   ├── {command.qualified_name}{aliases}{usage}: {command.brief or 'No description'}"
                    )
                elif isinstance(command, Group) and command.root_parent:
                    _commands.append(
                        f"|    |   ├── {command.qualified_name}{aliases}: {command.brief or 'No description'}"
                    )
                else:
                    _commands.append(
                        f"|    ├── {command.qualified_name}{aliases}{usage}: {command.brief or 'No description'}"
                    )

            if _commands:
                output += f"┌── {name}\n" + "\n".join(_commands) + "\n"

        out = ujson.dumps(output)
        return Response(text=out, content_type="application/json")


async def setup(bot):
    await bot.add_cog(WebServer(bot))
