# SPDX-FileCopyrightText: 2024 Your Name <your@email.com>
# SPDX-License-Identifier: MPL-2.0

from functools import wraps
from typing import Callable
from datetime import datetime
from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from aiohttp.web import BaseRequest, Request, Response, StreamResponse
from discord.ext import commands, tasks
from loguru import logger as log
from aiohttp_cors import setup as cors_setup, ResourceOptions
from discord.utils import utcnow
import config
import time

from system import Marly


class AccessLogger(AbstractAccessLogger):
    """Custom access logger for the API"""

    def log(self, request: BaseRequest, response: StreamResponse, time: float) -> None:
        self.logger.info(
            f"Request for {request.path!r} with status of {response.status!r}."
        )


def route(pattern: str, method: str = "GET") -> Callable:
    """Decorator for API route handlers with error handling"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self: "Network", request: Request) -> Response:
            try:
                return await func(self, request)
            except Exception as e:
                log.error(f"Error handling request for {pattern}: {e}")
                return web.json_response({"error": "Internal server error"}, status=500)

        wrapper.pattern = pattern
        wrapper.method = method
        return wrapper

    return decorator


class Network(commands.Cog):
    """API cog handling HTTP endpoints and caching"""

    def __init__(self, bot: Marly):
        self.bot: Marly = bot
        self.app = web.Application(logger=log)
        self.status_cache = {}
        self.commands_cache = {}

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

        # Register routes
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Set up API routes and CORS"""
        # Add decorated routes
        for module in dir(self):
            route = getattr(self, module)
            if not hasattr(route, "pattern"):
                continue
            resource = self.app.router.add_route(route.method, route.pattern, route)
            self.cors.add(resource)

        # Add root route
        root_resource = self.app.router.add_get("/", self.root_handler)
        self.cors.add(root_resource)

    @tasks.loop(minutes=5)
    async def update_status_cache(self):
        """Task to update the status cache every 5 minutes"""
        try:
            self.status_cache = {
                "shards": [
                    {
                        "shard_id": shard.id,
                        "server_count": len(
                            [
                                guild
                                for guild in self.bot.guilds
                                if guild.shard_id == shard.id
                            ]
                        ),
                        "cached_user_count": len(
                            [
                                user
                                for guild in self.bot.guilds
                                for user in guild.members
                                if guild.shard_id == shard.id
                            ]
                        ),
                        "uptime": self.bot.uptime2,
                        "latency": round(shard.latency * 1000, 2),
                        "last_updated": int(time.time() * 1000),
                    }
                    for shard in self.bot.shards.values()
                ]
            }
        except Exception as e:
            log.error(f"Error updating status cache: {e}")

    @tasks.loop(minutes=5)
    async def update_commands_cache(self):
        """Task to update the commands cache every 5 minutes"""
        try:
            commands_by_category = {}
            excluded_cogs = {"Developer", "Jishaku"}

            for command in self.bot.commands:
                category = command.cog_name or "Uncategorized"
                if category in excluded_cogs:
                    continue

                if category not in commands_by_category:
                    commands_by_category[category] = []

                # Process main command
                command_info = self._build_command_info(command)
                commands_by_category[category].append(command_info)

                # Process subcommands if any
                if hasattr(command, "commands"):
                    for subcommand in command.commands:
                        subcmd_info = self._build_command_info(
                            subcommand, parent=command
                        )
                        commands_by_category[category].append(subcmd_info)

            self.commands_cache = commands_by_category
        except Exception as e:
            log.error(f"Error updating commands cache: {e}")

    @update_status_cache.before_loop
    @update_commands_cache.before_loop
    async def before_cache_update(self):
        """Wait for the bot to be ready before starting cache updates"""
        await self.bot.wait_until_ready()

    @update_status_cache.error
    @update_commands_cache.error
    async def cache_update_error(self, error):
        """Handle errors in cache update tasks"""
        log.error(f"Error in cache update task: {error}")

    def _build_command_info(
        self, command: commands.Command, parent: commands.Command = None
    ) -> dict:
        """Helper method to build command info dictionary"""
        name = (
            f"{parent.qualified_name} {command.name}"
            if parent
            else command.qualified_name
        )

        # Get permissions from command checks directly
        permissions = []
        try:
            for check in command.checks:
                check_str = str(check)
                if "has_permissions" in check_str:
                    # Extract permissions directly from the check's closure
                    closure_vars = check.__closure__[0].cell_contents
                    if isinstance(closure_vars, dict):
                        permissions.extend(
                            perm.replace("_", " ").title()
                            for perm, value in closure_vars.items()
                            if value is True
                        )
                elif "is_owner" in check_str:
                    permissions.append("Bot Owner")

            if not permissions:
                permissions = ["none"]  # le default permission

        except Exception as e:
            log.error(f"Error getting permissions for {name}: {e}")
            permissions = ["Send Messages"]  # Fallback permission

        return {
            "name": name,
            "help": command.help or "",
            "brief": permissions,
            "usage": [param.name for param in command.clean_params.values()],
            "example": command.example if hasattr(command, "example") else "",
        }

    def build_tree(self) -> str:
        """Build a text tree of all commands"""
        tree = ""
        for cog_name, cog in self.bot.cogs.items():
            tree += f"┌── {cog_name}\n"
            for command in cog.get_commands():
                tree += self._build_command_tree(command, depth=1)
        return tree

    def _build_command_tree(self, command: commands.Command, depth: int = 0) -> str:
        """Helper method to build command tree structure"""
        if command.hidden:
            return ""

        line = "├──"
        aliases = f"[{('|'.join(command.aliases))}]" if command.aliases else ""
        tree = f"{'│    ' * depth}{line} {command.qualified_name}{aliases}: {command.short_doc}\n"

        if isinstance(command, commands.Group):
            for subcommand in command.commands:
                tree += self._build_command_tree(subcommand, depth + 1)

        return tree

    # Route handlers
    async def root_handler(self, request: Request) -> Response:
        """Handle root endpoint requests"""
        return web.json_response(
            {
                "latency": self.bot.latency * 1000,
                "cache": {
                    "guilds": len(self.bot.guilds),
                    "users": len(self.bot.users),
                },
            }
        )

    @route("/commands")
    async def commands(self, request: Request) -> Response:
        """Return cached command information"""
        return web.json_response(self.commands_cache)

    @route("/status")
    async def status(self, request: Request) -> Response:
        """Return cached status information"""
        return web.json_response(self.status_cache)

    @route("/commandlist")
    async def commandlist(self, request: Request) -> Response:
        """Return command list in text tree format"""
        return web.Response(text=self.build_tree(), content_type="text/plain")

    @route("/api/timestamp")
    async def timestamp(self, request: Request) -> Response:
        """Handle timestamp conversion requests"""
        date_param = request.query.get("date")

        if date_param:
            try:
                day, month, year = map(int, date_param.split("-"))
                date_obj = datetime(year, month, day)
                return web.json_response(
                    {"date": date_param, "timestamp": int(date_obj.timestamp())}
                )
            except (ValueError, TypeError):
                return web.json_response(
                    {"error": "Invalid date format. Use DD-MM-YYYY"}, status=400
                )

        current = utcnow()
        return web.json_response(
            {
                "date": current.strftime("%d-%m-%Y"),
                "timestamp": int(current.timestamp()),
            }
        )

    async def cog_load(self) -> None:
        """Start the API server and cache update tasks"""
        host = config.Network.host
        port = config.Network.port

        # Start web server
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

        # Start cache update tasks
        self.update_status_cache.start()
        self.update_commands_cache.start()

        log.info(f"API server started on {host}:{port}")

    async def cog_unload(self) -> None:
        """Gracefully shutdown the API server and stop tasks"""
        self.update_status_cache.cancel()
        self.update_commands_cache.cancel()
        await self.app.shutdown()
        await self.app.cleanup()
        log.info("API server shutdown complete")
