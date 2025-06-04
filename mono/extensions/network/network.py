import os
from base64 import b64decode  # Import b64decode
from functools import wraps
from typing import Callable

import config
import tuuid  # Ensure tuuid is installed and imported
from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from aiohttp.web import BaseRequest, Request, Response, StreamResponse
from aiohttp_cors import ResourceOptions
from aiohttp_cors import setup as cors_setup
from core.Mono import Mono
from core.tools.logging import logger as log
from discord.ext.commands import Cog, Command, Group


class AccessLogger(AbstractAccessLogger):
    def log(
        self: "AccessLogger",
        request: BaseRequest,
        response: StreamResponse,
        time: float,
    ) -> None:
        self.logger.info(
            f"Request for {request.path!r} with status of {response.status!r}."
        )


def route(pattern: str, method: str = "GET") -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self: "Network", request: Request) -> None:
            try:
                return await func(self, request)
            except Exception as e:
                log.error(f"Error handling request for {pattern}: {e}")
                return web.json_response({"error": "Internal server error"}, status=500)

        wrapper.pattern = pattern
        wrapper.method = method
        return wrapper

    return decorator


class Network(Cog):
    def __init__(self, bot: Mono):
        self.bot: Mono = bot
        self.app = web.Application(logger=log)
        self.decoded_assets = {}  # Initialize decoded_assets

        # Set up CORS
        self.cors = cors_setup(
            self.app,
            defaults={
                "*": ResourceOptions(
                    allow_credentials=False,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*",
                )
            },
        )

        # Add routes
        for module in dir(self):
            route = getattr(self, module)
            if not hasattr(route, "pattern"):
                continue
            resource = self.app.router.add_route(route.method, route.pattern, route)
            self.cors.add(resource)  # Enable CORS for this route

        # Add root route
        root_resource = self.app.router.add_get("/", self.root_handler)
        self.cors.add(root_resource)

    def build_tree(self) -> str:
        tree = ""
        for cog_name, cog in self.bot.cogs.items():
            tree += f"┌── {cog_name}\n"
            for command in cog.get_commands():
                tree += self._build_command_tree(command, depth=1)
        return tree

    def _build_command_tree(self, command: Command, depth: int = 0) -> str:
        if command.hidden:
            return ""

        line = "├──"
        aliases = "|".join(command.aliases)
        if aliases:
            aliases = f"[{aliases}]"

        tree = f"{'│    ' * depth}{line} {command.qualified_name}{aliases}: {command.short_doc}\n"
        if isinstance(command, Group):
            for subcommand in command.commands:
                tree += self._build_command_tree(subcommand, depth + 1)

        return tree

    async def root_handler(self, request):
        return web.json_response(
            {
                "latency": self.bot.latency * 1000,
                "cache": {
                    "guilds": len(self.bot.guilds),
                    "users": len(self.bot.users),
                },
            }
        )

    async def cog_load(self: "Network") -> None:
        host = config.Network.host
        port = config.Network.port
        self.bot.loop.create_task(
            web._run_app(
                self.app,
                host=host,
                port=port,
                print=None,
                access_log=log,
                access_log_class=AccessLogger,
            ),
            name="Internal-API",
        )
        log.info(f"{host}:{port}")

    async def cog_unload(self: "Network") -> None:
        await self.app.shutdown()
        await self.app.cleanup()
        log.info("Gracefully shutdown the API")

    @route("/commands")
    async def commands(self: "Network", request: Request) -> Response:
        """
        Export command information as JSON, including subcommands.
        """

        def get_command_info(command):
            return {
                "category": command.cog_name or "Uncategorized",
                "description": command.help or "",
                "name": command.qualified_name,
                "parameters": [
                    {"name": param.name, "optional": param.default != param.empty}
                    for param in command.clean_params.values()
                ],
                "permissions": (
                    [perm for perm in command.permissions]
                    if command.permissions
                    else ["N/A"]
                ),
                "subcommands": [
                    get_command_info(subcommand)
                    for subcommand in getattr(command, "commands", [])
                ],
            }

        commands_info = [get_command_info(command) for command in self.bot.commands]
        return web.json_response(commands_info)

    @route("/status")
    async def status(self, request: Request) -> Response:
        return web.json_response(
            {
                "shards": [
                    {
                        "guilds": f"{len([guild for guild in self.bot.guilds if guild.shard_id == shard.id])}",
                        "id": f"{shard.id}",
                        "ping": f"{(shard.latency * 1000):.2f}ms",
                        "uptime": f"{int(self.bot.uptime2)}",
                        "users": f"{len([user for guild in self.bot.guilds for user in guild.members if guild.shard_id == shard.id])}",
                    }
                    for shard in self.bot.shards.values()
                ]
            }
        )

    @route("/commandlist")
    async def commandlist(self: "Network", request: Request) -> Response:
        """
        Export command list in a structured format.
        """
        command_list = self.build_tree()
        return web.Response(text=command_list, content_type="text/plain")

    @route("/decode")
    async def decode(self: "Network", request: Request) -> Response:
        data = await request.json()
        image = data.get("image")
        content_type = data.get("content-type")
        name = data.get("name") or tuuid.tuuid()
        if not image:
            raise TypeError()
        if content_type:
            base64_str = image
        else:
            try:
                content_type, base64_str = (
                    image.split(",")[0].split(":")[1].split(";")[0],
                    image.split(",")[1],
                )
            except:
                print(image)
        # Decode the Base64 string
        image_data = b64decode(base64_str)
        self.decoded_assets[name] = [
            image_data,
            content_type,
        ]  # Use self.decoded_assets
        return web.json_response(
            status=200,
            content={
                "url": f"https://cdn.rival.rocks/assets/{name}.{content_type.split('/')[1].replace('jpeg', 'jpg')}"
            },
        )

    @route("/assets/{file}")
    async def assets(self: "Network", request: Request, file: str) -> Response:
        fn, ext = file.split(".", 1)
        if fn in self.decoded_assets:  # Use self.decoded_assets
            return web.Response(
                content=self.decoded_assets[fn][0],
                media_type=self.decoded_assets[fn][1],
                status=200,
            )
        else:
            return web.json_response(
                status=404, content={"message": "Asset unavailable"}
            )
