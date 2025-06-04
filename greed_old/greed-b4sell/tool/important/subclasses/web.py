from __future__ import annotations

import datetime
import hashlib
import aiohttp
import discord
import json
import uuid
from typing import TypedDict, Union, Optional, List, Dict, Any
from aiohttp.web import Application, Request, Response, _run_app, json_response, StreamResponse
import aiohttp.web
from aiohttp_cors import setup as setup_cors, ResourceOptions, CorsViewMixin
from discord.ext.commands import Cog, Group, Command
from discord.ext.commands.errors import CommandError
from prometheus_async import aio
import socket
from tool.greed import Greed
import urllib.parse
from config import Authorization
import asyncio
import hmac
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont


class CommandData(TypedDict):
    name: str
    brief: Optional[str]
    description: str
    permissions: Optional[List[str]]
    bot_permissions: Optional[List[str]]
    usage: Optional[str]
    example: Optional[str]


class OutageData(TypedDict):
    id: str
    title: str
    description: str
    status: str
    createdAt: str
    updatedAt: str
    affectedComponents: List[str]


class WebServer(Cog):
    def __init__(self, bot: Greed) -> None:
        self.bot = bot
        self.app = Application(middlewares=[self.cors_middleware])
        self._setup_routes()
        self._setup_cors()
        self.server_task = None
        self.api_key = Authorization.Outages.api_key
        
        # Define service components for status tracking
        self.service_components = [
            "Bot", "Website", "API", "Database", "Voice", "Music"
        ]

    def _setup_routes(self) -> None:
        routes = [
            ("GET", "/", self.index),
            ("GET", "/commands", self.commands),
            ("GET", "/raw", self.command_dump),
            ("GET", "/status", self.status),
            ("GET", "/status/image", self.status_image),
            ("GET", "/outages", self.get_outages),
            ("POST", "/outages", self.post_outage),
            ("PATCH", "/outages/{outage_id}", self.update_outage),
            ("POST", "/validate-key", self.validate_api_key),
            ("OPTIONS", "/outages", self.options_handler),
            ("OPTIONS", "/outages/{outage_id}", self.options_handler),
            ("OPTIONS", "/validate-key", self.options_handler),
            ("GET", "/metrics", aio.web.server_stats),
            ("GET", "/callback", self.lastfm_callback),
        ]
        for method, path, handler in routes:
            self.app.router.add_route(method, path, handler)

    def _setup_cors(self) -> None:
        # Setup CORS for all routes with a simpler configuration
        # that won't conflict with our middleware
        cors = setup_cors(
            self.app,
            defaults={
                # Allow specific origins including localhost development server
                "http://localhost:3000": ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                ),
                # Also allow all origins as a fallback
                "*": ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
                ),
            },
        )

        # We don't need to add CORS to each route manually
        # as we're using middleware for that

    async def cog_load(self) -> None:
        if self.bot.connection.local_name != "cluster1":
            return
        # Create outages table if it doesn't exist
        await self._create_outages_table()
        self.server_task = self.bot.loop.create_task(self._run())

    async def cog_unload(self) -> None:
        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass

        await self.app.shutdown()
        await self.app.cleanup()

    async def _run(self) -> None:
        runner = aiohttp.web.AppRunner(self.app)
        await runner.setup()
        site = aiohttp.web.TCPSite(runner, "0.0.0.0", 2027)
        self.runner = runner
        await site.start()

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            await runner.cleanup()
            raise

    @staticmethod
    async def index(request: Request) -> Response:
        response = Response(text="API endpoint operationaeeeeeeeeeeeeel", status=200)
        # Add CORS headers explicitly for better compatibility
        origin = request.headers.get("Origin", "")

        # If there's an origin header, reflect it back to allow any origin
        if origin:
            # For localhost and other trusted origins, allow credentials
            if origin == "http://localhost:3000" or origin.endswith(".greed.rocks"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            else:
                # For other origins, allow the request but without credentials
                response.headers["Access-Control-Allow-Origin"] = origin
        else:
            # Fallback to wildcard if no origin is specified
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        return response

    async def status(self, request: Request) -> Response:
        response = json_response({"status": "ok"})
        # Add CORS headers explicitly for better compatibility
        origin = request.headers.get("Origin", "")

        # If there's an origin header, reflect it back to allow any origin
        if origin:
            # For localhost and other trusted origins, allow credentials
            if origin == "http://localhost:3000" or origin.endswith(".greed.rocks"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            else:
                # For other origins, allow the request but without credentials
                response.headers["Access-Control-Allow-Origin"] = origin
        else:
            # Fallback to wildcard if no origin is specified
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        return response

    def _get_permissions(
        self, command: Union[Command, Group], bot: bool = False
    ) -> Optional[List[str]]:
        perms = command.bot_permissions if bot else command.permissions
        if not perms:
            return None

        permissions = []
        if isinstance(perms, list):
            permissions.extend(p.replace("_", " ").title() for p in perms)
        else:
            permissions.append(perms.replace("_", " ").title())
        return permissions

    async def command_dump(self, request: Request) -> Response:
        # Organize commands by cog/category
        command_categories = {}
        
        # List of cogs to exclude
        excluded_cogs = ["Jishaku", "Owner", "Network"]
        
        for cmd in self.bot.walk_commands():
            if (
                cmd.hidden
                or (isinstance(cmd, Group) and not cmd.description)
                or cmd.qualified_name == "help"
            ):
                continue
                
            # Get the cog name or use "Uncategorized" if no cog
            cog_name = cmd.cog.qualified_name if cmd.cog else "Uncategorized"
            
            # Skip excluded cogs
            if cog_name in excluded_cogs:
                continue
            
            # Create category if it doesn't exist
            if cog_name not in command_categories:
                command_categories[cog_name] = []
                
            # Format example with the bot's prefix if it exists
            example = None
            if hasattr(cmd, 'example') and cmd.example:
                example = cmd.example
            
            # Add command to its category
            command_categories[cog_name].append(
                {
                    "name": cmd.qualified_name,
                    "brief": cmd.brief,
                    "description": cmd.description,
                    "permissions": self._get_permissions(cmd),
                    "bot_permissions": self._get_permissions(cmd, True),
                    "usage": cmd.usage,
                    "example": example
                }
            )
            
        # Sort categories alphabetically
        sorted_categories = dict(sorted(command_categories.items()))
        
        # Create response
        response = json_response(sorted_categories)
        
        # Add CORS headers
        return self._add_cors_headers(response, request)

    async def commands(self, request: Request) -> Response:
        def format_command(cmd: Command, level: int = 0) -> str:
            prefix = "|    " * level
            aliases = f"({', '.join(cmd.aliases)})" if cmd.aliases else ""
            usage = f" {cmd.usage}" if cmd.usage else ""
            return f"{prefix}├── {cmd.qualified_name}{aliases}{usage}: {cmd.brief or 'No description'}"

        # List of cogs to exclude
        excluded_cogs = ["Jishaku", "Owner", "Network"]
        
        output = []
        for name, cog in sorted(self.bot.cogs.items(), key=lambda x: x[0].lower()):
            if name in excluded_cogs or name.lower() in ("jishaku", "developer"):
                continue
            commands = [
                format_command(cmd, level=1)
                for cmd in cog.walk_commands()
                if not cmd.hidden
            ]
            if commands:
                output.extend([f"┌── {name}"] + commands)

        response = json_response("\n".join(output))
        # Add CORS headers explicitly for better compatibility
        origin = request.headers.get("Origin", "")

        # If there's an origin header, reflect it back to allow any origin
        if origin:
            # For localhost and other trusted origins, allow credentials
            if origin == "http://localhost:3000" or origin.endswith(".greed.rocks"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            else:
                # For other origins, allow the request but without credentials
                response.headers["Access-Control-Allow-Origin"] = origin
        else:
            # Fallback to wildcard if no origin is specified
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        return response

    async def lastfm_callback(self, request: Request) -> Response:
        """Handle the callback from LastFM OAuth authentication"""
        # This is the token returned by LastFM after authorization
        lastfm_token = request.query.get("token")

        # Helper function to add CORS headers to responses
        def add_cors_headers(response):
            origin = request.headers.get("Origin", "")

            # If there's an origin header, reflect it back to allow any origin
            if origin:
                # For localhost and other trusted origins, allow credentials
                if origin == "http://localhost:3000" or origin.endswith(".greed.rocks"):
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                else:
                    # For other origins, allow the request but without credentials
                    response.headers["Access-Control-Allow-Origin"] = origin
            else:
                # Fallback to wildcard if no origin is specified
                response.headers["Access-Control-Allow-Origin"] = "*"

            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
            return response

        try:
            # If no token is provided, return an error
            if not lastfm_token:
                response = Response(text="No token provided", status=400)
                return add_cors_headers(response)

            tracking_id = request.query.get("tracking_id")
            if not tracking_id:
                return Response(text="No tracking ID provided", status=400)

            # Get user ID from Redis
            user_id_str = await self.bot.redis.get(f"lastfm:auth:{tracking_id}")
            if not user_id_str:
                return Response(text="Invalid or expired tracking ID", status=400)

            user_id = int(user_id_str)

            try:
                # Generate signature for LastFM API
                api_sig = hashlib.md5(
                    f"api_key{Authorization.LastFM.api_key}methodauth.getSessiontoken{lastfm_token}{Authorization.LastFM.api_secret}".encode()
                ).hexdigest()

                # Get session key from LastFM
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        "http://ws.audioscrobbler.com/2.0/",
                        params={
                            "method": "auth.getSession",
                            "api_key": Authorization.LastFM.api_key,
                            "token": lastfm_token,
                            "api_sig": api_sig,
                            "format": "json",
                        },
                    ) as resp:
                        data = await resp.json()

                        if "error" in data:
                            return Response(
                                text="Failed to get session key", status=400
                            )

                        session_key = data["session"]["key"]
                        username = data["session"]["name"]

                        # Ensure the schema exists
                        try:
                            await self.bot.db.execute(
                                "CREATE SCHEMA IF NOT EXISTS lastfm"
                            )
                        except Exception:
                            pass

                        # Check if the table exists, create it if not
                        try:
                            await self.bot.db.execute(
                                """
                                CREATE TABLE IF NOT EXISTS lastfm.conf (
                                    user_id BIGINT PRIMARY KEY,
                                    username TEXT NOT NULL,
                                    session_key TEXT
                                )
                            """
                            )
                        except Exception:
                            pass

                        # Store in database with error handling
                        try:
                            # Try to insert/update the record
                            await self.bot.db.execute(
                                """INSERT INTO lastfm.conf (user_id, username, session_key) 
                                   VALUES ($1, $2, $3) 
                                   ON CONFLICT (user_id) 
                                   DO UPDATE SET username = $2, session_key = $3""",
                                user_id,
                                username,
                                session_key,
                            )
                        except Exception as e:
                            # If that fails, try to close and reset the connection pool
                            try:
                                # Close all connections in the pool
                                await self.bot.db.execute(
                                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = current_database()"
                                )

                                # Try the insert/update again
                                await self.bot.db.execute(
                                    """INSERT INTO lastfm.conf (user_id, username, session_key) 
                                       VALUES ($1, $2, $3) 
                                       ON CONFLICT (user_id) 
                                       DO UPDATE SET username = $2, session_key = $3""",
                                    user_id,
                                    username,
                                    session_key,
                                )
                            except Exception as e2:
                                response = Response(
                                    text=f"Database error: {str(e2)}", status=500
                                )
                                return add_cors_headers(response)

                        # Send DM to user
                        user = self.bot.get_user(user_id)
                        if user:
                            embed = discord.Embed(
                                title="LastFM Authentication Successful",
                                description=f"You have been successfully logged in as **{username}**",
                                color=0x2B2D31,
                            )
                            try:
                                await user.send(embed=embed)
                            except discord.Forbidden:
                                pass

                        # Delete the tracking ID from Redis
                        await self.bot.redis.delete(f"lastfm:auth:{tracking_id}")

                        response = Response(
                            text="LastFM Authorized - You can close this window",
                            status=200,
                        )
                        return add_cors_headers(response)

            except Exception as e:
                response = Response(text=f"An error occurred: {str(e)}", status=500)
                return add_cors_headers(response)

        except Exception as e:
            response = Response(text=f"An error occurred: {str(e)}", status=500)
            return add_cors_headers(response)

    @staticmethod
    async def cors_middleware(app, handler):
        async def middleware_handler(request):
            # Handle preflight requests
            if request.method == "OPTIONS":
                response = Response(status=204)
                origin = request.headers.get("Origin", "")

                if origin:
                    if origin == "http://localhost:3000" or origin.endswith(".greed.rocks") or origin.endswith(".vercel.app"):
                        response.headers["Access-Control-Allow-Origin"] = origin
                        response.headers["Access-Control-Allow-Credentials"] = "true"
                    else:
                        response.headers["Access-Control-Allow-Origin"] = origin
                else:
                    response.headers["Access-Control-Allow-Origin"] = "*"

                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
                response.headers["Access-Control-Max-Age"] = "3600"
                response.headers["Access-Control-Expose-Headers"] = "*"
                return response

            # Handle actual request
            response = await handler(request)
            origin = request.headers.get("Origin", "")

            if origin:
                if origin == "http://localhost:3000" or origin.endswith(".greed.rocks") or origin.endswith(".vercel.app"):
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                else:
                    response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"

            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            response.headers["Access-Control-Expose-Headers"] = "*"
            return response

        return middleware_handler

    async def _create_outages_table(self) -> None:
        """Create the outages table if it doesn't exist"""
        try:
            # Create schema if it doesn't exist
            await self.bot.db.execute("CREATE SCHEMA IF NOT EXISTS status")

            # Create outages table
            await self.bot.db.execute(
                """
                CREATE TABLE IF NOT EXISTS status.outages (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    affected_components TEXT[] NOT NULL
                )
            """
            )
        except Exception as e:
            self.bot.logger.error(f"Failed to create outages table: {e}")

    async def get_outages(self, request: Request) -> Response:
        """Get all outages"""
        try:
            # Query the database for outages
            outages = await self.bot.db.fetch(
                """
                SELECT 
                    id, 
                    title, 
                    description, 
                    status, 
                    created_at, 
                    updated_at, 
                    affected_components
                FROM status.outages
                ORDER BY updated_at DESC
            """
            )

            # Format the outages for the response
            formatted_outages = []
            for outage in outages:
                formatted_outages.append(
                    {
                        "id": outage["id"],
                        "title": outage["title"],
                        "description": outage["description"],
                        "status": outage["status"],
                        "createdAt": outage["created_at"].isoformat(),
                        "updatedAt": outage["updated_at"].isoformat(),
                        "affectedComponents": outage["affected_components"],
                    }
                )

            response = json_response(formatted_outages)

            # Add CORS headers
            origin = request.headers.get("Origin", "")
            if origin:
                if origin == "http://localhost:3000" or origin.endswith(".greed.rocks"):
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                else:
                    response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"

            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
            return response

        except Exception as e:
            self.bot.logger.error(f"Error getting outages: {e}")
            response = json_response(
                {"error": "Failed to retrieve outages"}, status=500
            )

            # Add CORS headers
            origin = request.headers.get("Origin", "")
            if origin:
                if origin == "http://localhost:3000" or origin.endswith(".greed.rocks"):
                    response.headers["Access-Control-Allow-Origin"] = origin
                    response.headers["Access-Control-Allow-Credentials"] = "true"
                else:
                    response.headers["Access-Control-Allow-Origin"] = origin
            else:
                response.headers["Access-Control-Allow-Origin"] = "*"

            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
            return response

    async def post_outage(self, request: Request) -> Response:
        """Create a new outage"""
        # Check API key for authentication
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            response = json_response({"error": "Unauthorized"}, status=401)
            return self._add_cors_headers(response, request)

        api_key = auth_header.replace("Bearer ", "")
        if api_key != self.api_key:
            response = json_response({"error": "Invalid API key"}, status=401)
            return self._add_cors_headers(response, request)

        try:
            # Parse the request body
            body = await request.json()

            # Validate required fields
            required_fields = ["title", "description", "status"]
            for field in required_fields:
                if field not in body:
                    response = json_response(
                        {"error": f"Missing required field: {field}"}, status=400
                    )
                    return self._add_cors_headers(response, request)

            # Validate status
            valid_statuses = ["investigating", "identified", "monitoring", "resolved"]
            if body["status"] not in valid_statuses:
                response = json_response(
                    {
                        "error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
                    },
                    status=400,
                )
                return self._add_cors_headers(response, request)

            # Generate a unique ID
            outage_id = str(uuid.uuid4())

            # Get current timestamp
            now = datetime.datetime.now()

            # Extract affected components or use empty array
            affected_components = body.get("affectedComponents", [])
            if not isinstance(affected_components, list):
                response = json_response(
                    {"error": "affectedComponents must be an array"}, status=400
                )
                return self._add_cors_headers(response, request)

            # Insert the outage into the database
            await self.bot.db.execute(
                """
                INSERT INTO status.outages (
                    id, 
                    title, 
                    description, 
                    status, 
                    created_at, 
                    updated_at, 
                    affected_components
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                outage_id,
                body["title"],
                body["description"],
                body["status"],
                now,
                now,
                affected_components,
            )

            # Return the created outage
            outage = {
                "id": outage_id,
                "title": body["title"],
                "description": body["description"],
                "status": body["status"],
                "createdAt": now.isoformat(),
                "updatedAt": now.isoformat(),
                "affectedComponents": affected_components,
            }

            response = json_response(outage, status=201)
            return self._add_cors_headers(response, request)

        except json.JSONDecodeError:
            response = json_response({"error": "Invalid JSON"}, status=400)
            return self._add_cors_headers(response, request)
        except Exception as e:
            self.bot.logger.error(f"Error creating outage: {e}")
            response = json_response({"error": "Failed to create outage"}, status=500)
            return self._add_cors_headers(response, request)

    def _add_cors_headers(self, response: Response, request: Request) -> Response:
        """Helper method to add CORS headers to a response"""
        origin = request.headers.get("Origin", "")

        if origin:
            if origin == "http://localhost:3000" or origin.endswith(".greed.rocks") or origin.endswith(".vercel.app"):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
            else:
                response.headers["Access-Control-Allow-Origin"] = origin
        else:
            response.headers["Access-Control-Allow-Origin"] = "*"

        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PATCH, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        return response

    async def _validate_outage_data(self, data: dict) -> tuple[bool, str]:
        """Validate outage data"""
        if not isinstance(data, dict):
            return False, "Invalid data format"

        # Validate title
        if "title" in data:
            if not isinstance(data["title"], str):
                return False, "Title must be a string"
            if len(data["title"]) > 200:  # Reasonable limit
                return False, "Title too long"
            if not data["title"].strip():
                return False, "Title cannot be empty"

        # Validate description
        if "description" in data:
            if not isinstance(data["description"], str):
                return False, "Description must be a string"
            if len(data["description"]) > 5000:  # Reasonable limit
                return False, "Description too long"
            if not data["description"].strip():
                return False, "Description cannot be empty"

        # Validate status
        if "status" in data:
            valid_statuses = ["investigating", "identified", "monitoring", "resolved"]
            if data["status"] not in valid_statuses:
                return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"

        # Validate affected components
        if "affectedComponents" in data:
            if not isinstance(data["affectedComponents"], list):
                return False, "affectedComponents must be an array"
            for component in data["affectedComponents"]:
                if not isinstance(component, str):
                    return False, "All components must be strings"
                if len(component) > 100:  # Reasonable limit
                    return False, "Component name too long"
                if not component.strip():
                    return False, "Component name cannot be empty"
            if len(data["affectedComponents"]) > 20:  # Reasonable limit
                return False, "Too many affected components"

        return True, ""

    async def update_outage(self, request: Request) -> Response:
        """Update an existing outage"""
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            response = json_response({"error": "Unauthorized"}, status=401)
            return self._add_cors_headers(response, request)

        api_key = auth_header.replace("Bearer ", "")
        if not await self._verify_api_key(api_key):
            response = json_response({"error": "Invalid API key"}, status=401)
            return self._add_cors_headers(response, request)
    
        outage_id = request.match_info.get("outage_id", "").strip()
        if not outage_id or len(outage_id) > 100:
            response = json_response({"error": "Invalid outage ID"}, status=400)
            return self._add_cors_headers(response, request)

        try:
            # Parse and validate request body
            try:
                body = await request.json()
            except json.JSONDecodeError:
                response = json_response({"error": "Invalid JSON"}, status=400)
                return self._add_cors_headers(response, request)

            # Validate input data
            is_valid, error_message = await self._validate_outage_data(body)
            if not is_valid:
                response = json_response({"error": error_message}, status=400)
                return self._add_cors_headers(response, request)

            # Check if outage exists
            existing = await self.bot.db.fetchrow(
                """
                SELECT * FROM status.outages WHERE id = $1
                """,
                outage_id,
            )

            if not existing:
                response = json_response({"error": "Outage not found"}, status=404)
                return self._add_cors_headers(response, request)

            # Prepare update fields
            update_fields = {}

            # Title
            if "title" in body:
                update_fields["title"] = body["title"].strip()

            # Description
            if "description" in body:
                update_fields["description"] = body["description"].strip()

            # Status
            if "status" in body:
                update_fields["status"] = body["status"]

            # Affected components
            if "affectedComponents" in body:
                update_fields["affected_components"] = [
                    comp.strip() for comp in body["affectedComponents"] if comp.strip()
                ]

            if not update_fields:
                response = json_response({"error": "No fields to update"}, status=400)
                return self._add_cors_headers(response, request)

            now = datetime.datetime.now()
            update_fields["updated_at"] = now

            set_clauses = []
            params = [outage_id]

            for i, (key, value) in enumerate(update_fields.items(), start=2):
                set_clauses.append(f"{key} = ${i}")
                params.append(value)

            query = f"""
                UPDATE status.outages 
                SET {', '.join(set_clauses)}
                WHERE id = $1
                RETURNING id, title, description, status, created_at, updated_at, affected_components
            """

            updated = await self.bot.db.fetchrow(query, *params)

            # Return updated outage
            outage = {
                "id": updated["id"],
                "title": updated["title"],
                "description": updated["description"],
                "status": updated["status"],
                "createdAt": updated["created_at"].isoformat(),
                "updatedAt": updated["updated_at"].isoformat(),
                "affectedComponents": updated["affected_components"],
            }

            response = json_response(outage)
            return self._add_cors_headers(response, request)

        except Exception as e:
            self.bot.logger.error(f"Error updating outage: {e}")
            response = json_response({"error": "Failed to update outage"}, status=500)
            return self._add_cors_headers(response, request)

    async def options_handler(self, request: Request) -> Response:
        """Handle OPTIONS requests for CORS preflight"""
        response = Response(status=204)
        return self._add_cors_headers(response, request)

    async def validate_api_key(self, request: Request) -> Response:
        """Validate an API key"""
        try:
            body = await request.json()
            api_key = body.get("api_key")

            if not api_key:
                response = json_response({"valid": False, "error": "No API key provided"}, status=400)
                return self._add_cors_headers(response, request)

            is_valid = hmac.compare_digest(str(api_key), str(self.api_key))
            response = json_response({"valid": is_valid})
            return self._add_cors_headers(response, request)

        except Exception as e:
            response = json_response({"valid": False, "error": str(e)}, status=400)
            return self._add_cors_headers(response, request)

    async def _verify_api_key(self, api_key: str) -> bool:
        """Helper method to verify API key in a constant-time manner"""
        if not api_key:
            return False
        return hmac.compare_digest(str(api_key), str(self.api_key))

    async def status_image(self, request: Request) -> StreamResponse:
        """Generate a status image showing service availability"""
        try:
            # Get current outages
            outages = await self.bot.db.fetch(
                """
                SELECT 
                    id, 
                    title, 
                    status, 
                    affected_components
                FROM status.outages
                WHERE status != 'resolved'
                ORDER BY updated_at DESC
                """
            )
            
            affected_components = set()
            for outage in outages:
                affected_components.update(outage["affected_components"])
            
            image_bytes = await self._generate_status_image(affected_components)
            
            response = StreamResponse(status=200)
            response.content_type = 'image/png'
            
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "*"
            response.headers["Access-Control-Expose-Headers"] = "*"
            
            await response.prepare(request)
            await response.write(image_bytes)
            await response.write_eof()
            return response
            
        except Exception as e:
            self.bot.logger.error(f"Error generating status image: {e}")
            response = json_response(
                {"error": "Failed to generate status image"}, status=500
            )
            return self._add_cors_headers(response, request)
    
    async def _generate_status_image(self, affected_components: set) -> bytes:
        """Generate a status image showing service availability"""
        width, height = 1200, 630
        
        image = Image.new('RGB', (width, height), color=(47, 49, 54))
        draw = ImageDraw.Draw(image)
        
        try:
            title_font = ImageFont.truetype("arial.ttf", 60)
            subtitle_font = ImageFont.truetype("arial.ttf", 36)
            service_font = ImageFont.truetype("arial.ttf", 32)
        except IOError:
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            service_font = ImageFont.load_default()
        
        title = "Greed Status"
        title_width = draw.textlength(title, font=title_font)
        draw.text(
            ((width - title_width) // 2, 60),
            title,
            font=title_font,
            fill=(255, 255, 255)
        )
        
        status_text = "All Systems Operational"
        status_color = (67, 181, 129)
        
        if affected_components:
            status_text = "Some Systems Degraded"
            status_color = (255, 165, 0)
            
        subtitle_width = draw.textlength(status_text, font=subtitle_font)
        draw.text(
            ((width - subtitle_width) // 2, 140),
            status_text,
            font=subtitle_font,
            fill=status_color
        )

        import humanize
        current_time = datetime.datetime.now()
        timestamp = f"Last updated: {humanize.naturaltime(current_time)}"
        timestamp_width = draw.textlength(timestamp, font=service_font)
        draw.text(
            ((width - timestamp_width) // 2, height - 80),
            timestamp,
            font=service_font,
            fill=(180, 180, 180)
        )
        
        y_position = 220
        x_position_left = width // 4
        x_position_right = width // 2 + 100
        
        services_left = self.service_components[:len(self.service_components)//2]
        services_right = self.service_components[len(self.service_components)//2:]
        
        for service in services_left:
            is_affected = service in affected_components
            
            status_text = "Degraded" if is_affected else "Operational"
            status_color = (255, 165, 0) if is_affected else (67, 181, 129)
            
            draw.text(
                (x_position_left - 150, y_position),
                service,
                font=service_font,
                fill=(255, 255, 255)
            )
            
            circle_x = x_position_left + 50
            circle_y = y_position + 16
            circle_radius = 12
            draw.ellipse(
                (circle_x - circle_radius, circle_y - circle_radius, 
                 circle_x + circle_radius, circle_y + circle_radius),
                fill=status_color
            )
            
            draw.text(
                (circle_x + 25, y_position),
                status_text,
                font=service_font,
                fill=status_color
            )
            
            y_position += 60
        
        y_position = 220
        
        for service in services_right:
            is_affected = service in affected_components
            
            status_text = "Degraded" if is_affected else "Operational"
            status_color = (255, 165, 0) if is_affected else (67, 181, 129)
            
            draw.text(
                (x_position_right - 150, y_position),
                service,
                font=service_font,
                fill=(255, 255, 255)
            )
            
            circle_x = x_position_right + 50
            circle_y = y_position + 16
            circle_radius = 12
            draw.ellipse(
                (circle_x - circle_radius, circle_y - circle_radius, 
                 circle_x + circle_radius, circle_y + circle_radius),
                fill=status_color
            )
            
            draw.text(
                (circle_x + 25, y_position),
                status_text,
                font=service_font,
                fill=status_color
            )
            
            y_position += 60
        
        img_byte_arr = BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()


async def setup(bot) -> None:
    await bot.add_cog(WebServer(bot))
