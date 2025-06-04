import os
import json
import logging
import config
import asyncio
import time
import discord
import aiohttp
import stripe
import orjson
import hashlib
import hmac
import functools
import traceback
import uuid

from discord import Status, Activity
from discord.activity import Spotify

from main import Evict

from aiohttp import web
from aiohttp.abc import AbstractAccessLogger
from aiohttp_cors import setup as cors_setup, ResourceOptions
from aiohttp.web import BaseRequest, Request, Response, StreamResponse

from discord import Status, Embed
from discord.ext.commands import Cog, Group, FlagConverter

from typing import (
    Callable, 
    Optional, 
    Any, 
    Dict, 
    List
)
from functools import wraps
from cashews import cache
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel  

CONFIG = {
    "github_allowed_repos": [
        "EvictServices/evict",
        "EvictServices/instance",
        "EvictServices/discord.py",
        "EvictServices/vesta",
        "accurs/evict.bot"
    ],
    "token": config.DISCORD.TOKEN, 
    "updates_channel_id": 1319095893831581697 
}

class Owner(BaseModel):
    name: Optional[str] = None
    email: Optional[Any] = None
    login: Optional[str] = None
    id: Optional[int] = None
    node_id: Optional[str] = None
    avatar_url: Optional[str] = None
    gravatar_id: Optional[str] = None
    url: Optional[str] = None
    html_url: Optional[str] = None
    followers_url: Optional[str] = None
    following_url: Optional[str] = None
    gists_url: Optional[str] = None
    starred_url: Optional[str] = None
    subscriptions_url: Optional[str] = None
    organizations_url: Optional[str] = None
    repos_url: Optional[str] = None
    events_url: Optional[str] = None
    received_events_url: Optional[str] = None
    type: Optional[str] = None
    user_view_type: Optional[str] = None
    site_admin: Optional[bool] = None


class License(BaseModel):
    key: Optional[str] = None
    name: Optional[str] = None
    spdx_id: Optional[str] = None
    url: Optional[str] = None
    node_id: Optional[str] = None


class Repository(BaseModel):
    id: Optional[int] = None
    node_id: Optional[str] = None
    name: Optional[str] = None
    full_name: Optional[str] = None
    private: Optional[bool] = None
    owner: Optional[Owner] = None
    html_url: Optional[str] = None
    description: Optional[Any] = None
    fork: Optional[bool] = None
    url: Optional[str] = None
    forks_url: Optional[str] = None
    keys_url: Optional[str] = None
    collaborators_url: Optional[str] = None
    teams_url: Optional[str] = None
    hooks_url: Optional[str] = None
    issue_events_url: Optional[str] = None
    events_url: Optional[str] = None
    assignees_url: Optional[str] = None
    branches_url: Optional[str] = None
    tags_url: Optional[str] = None
    blobs_url: Optional[str] = None
    git_tags_url: Optional[str] = None
    git_refs_url: Optional[str] = None
    trees_url: Optional[str] = None
    statuses_url: Optional[str] = None
    languages_url: Optional[str] = None
    stargazers_url: Optional[str] = None
    contributors_url: Optional[str] = None
    subscribers_url: Optional[str] = None
    subscription_url: Optional[str] = None
    commits_url: Optional[str] = None
    git_commits_url: Optional[str] = None
    comments_url: Optional[str] = None
    issue_comment_url: Optional[str] = None
    contents_url: Optional[str] = None
    compare_url: Optional[str] = None
    merges_url: Optional[str] = None
    archive_url: Optional[str] = None
    downloads_url: Optional[str] = None
    issues_url: Optional[str] = None
    pulls_url: Optional[str] = None
    milestones_url: Optional[str] = None
    notifications_url: Optional[str] = None
    labels_url: Optional[str] = None
    releases_url: Optional[str] = None
    deployments_url: Optional[str] = None
    created_at: Optional[int] = None
    updated_at: Optional[str] = None
    pushed_at: Optional[int] = None
    git_url: Optional[str] = None
    ssh_url: Optional[str] = None
    clone_url: Optional[str] = None
    svn_url: Optional[str] = None
    homepage: Optional[Any] = None
    size: Optional[int] = None
    stargazers_count: Optional[int] = None
    watchers_count: Optional[int] = None
    language: Optional[str] = None
    has_issues: Optional[bool] = None
    has_projects: Optional[bool] = None
    has_downloads: Optional[bool] = None
    has_wiki: Optional[bool] = None
    has_pages: Optional[bool] = None
    has_discussions: Optional[bool] = None
    forks_count: Optional[int] = None
    mirror_url: Optional[Any] = None
    archived: Optional[bool] = None
    disabled: Optional[bool] = None
    open_issues_count: Optional[int] = None
    license: Optional[License] = None
    allow_forking: Optional[bool] = None
    is_template: Optional[bool] = None
    web_commit_signoff_required: Optional[bool] = None
    topics: Optional[List] = None
    visibility: Optional[str] = None
    forks: Optional[int] = None
    open_issues: Optional[int] = None
    watchers: Optional[int] = None
    default_branch: Optional[str] = None
    stargazers: Optional[int] = None
    master_branch: Optional[str] = None
    organization: Optional[str] = None
    custom_properties: Optional[Dict[str, Any]] = None


class Pusher(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class Organization(BaseModel):
    login: Optional[str] = None
    id: Optional[int] = None
    node_id: Optional[str] = None
    url: Optional[str] = None
    repos_url: Optional[str] = None
    events_url: Optional[str] = None
    hooks_url: Optional[str] = None
    issues_url: Optional[str] = None
    members_url: Optional[str] = None
    public_members_url: Optional[str] = None
    avatar_url: Optional[str] = None
    description: Optional[str] = None


class Sender(BaseModel):
    login: Optional[str] = None
    id: Optional[int] = None
    node_id: Optional[str] = None
    avatar_url: Optional[str] = None
    gravatar_id: Optional[str] = None
    url: Optional[str] = None
    html_url: Optional[str] = None
    followers_url: Optional[str] = None
    following_url: Optional[str] = None
    gists_url: Optional[str] = None
    starred_url: Optional[str] = None
    subscriptions_url: Optional[str] = None
    organizations_url: Optional[str] = None
    repos_url: Optional[str] = None
    events_url: Optional[str] = None
    received_events_url: Optional[str] = None
    type: Optional[str] = None
    user_view_type: Optional[str] = None
    site_admin: Optional[bool] = None


class Author(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None


class Committer(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    username: Optional[str] = None


class Commit(BaseModel):
    id: Optional[str] = None
    tree_id: Optional[str] = None
    distinct: Optional[bool] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None
    author: Optional[Author] = None
    committer: Optional[Committer] = None
    added: Optional[List] = None
    removed: Optional[List] = None
    modified: Optional[List[str]] = None


class HeadCommit(BaseModel):
    id: Optional[str] = None
    tree_id: Optional[str] = None
    distinct: Optional[bool] = None
    message: Optional[str] = None
    timestamp: Optional[str] = None
    url: Optional[str] = None
    author: Optional[Author] = None
    committer: Optional[Committer] = None
    added: Optional[List] = None
    removed: Optional[List] = None
    modified: Optional[List[str]] = None


class GithubPushEvent(BaseModel):
    ref: Optional[str] = None
    before: Optional[str] = None
    after: Optional[str] = None
    repository: Optional[Repository] = None
    pusher: Optional[Pusher] = None
    organization: Optional[Organization] = None
    sender: Optional[Sender] = None
    created: Optional[bool] = None
    deleted: Optional[bool] = None
    forced: Optional[bool] = None
    base_ref: Optional[Any] = None
    compare: Optional[str] = None
    commits: Optional[List[Commit]] = None
    head_commit: Optional[HeadCommit] = None

    @property
    def to_embed(self) -> Embed:
        if not self.head_commit:
            return None
            
        added_count = len(self.head_commit.added or [])
        deleted_count = len(self.head_commit.removed or [])
        modified_count = len(self.head_commit.modified or [])

        added_message = (
            f"+ Added {added_count} {'files' if added_count > 1 else 'file'}"
            if added_count > 0
            else ""
        )
        deleted_message = (
            f"- Deleted {deleted_count} {'files' if deleted_count > 1 else 'file'}"
            if deleted_count > 0
            else ""
        )
        modified_message = (
            f"! Modified {modified_count} {'files' if modified_count > 1 else 'file'}"
            if modified_count > 0
            else ""
        )

        change_message = "\n".join(
            filter(None, [added_message, deleted_message, modified_message])
        )

        branch = self.ref.split('/')[-1]
        commit_count = len(self.commits or [])
        
        description = (
            f">>> There has been **{commit_count}** {'commit' if commit_count == 1 else 'commits'} "
            f"to [`{self.repository.full_name}`]({self.repository.html_url}/tree/{branch})\n"
            f"```diff\n{change_message}\n```"
        )

        embed = Embed(
            title=f"New {'Commit' if commit_count == 1 else 'Commits'} to {self.repository.name} ({branch})",
            url=self.compare,  
            description=description,
            color=0x2ea043  
        )

        valid_commit = False
        for commit in (self.commits or []):
            if commit.message and len(commit.message.strip()) >= 5:
                valid_commit = True
                commit_url = f"{self.repository.html_url}/commit/{commit.id}"
                embed.add_field(
                    name=f"{commit.id[:7]}",
                    value=f"[View Commit]({commit_url})\n```fix\n{commit.message.strip()}\n```",
                    inline=False,
                )

        if not valid_commit:
            return None

        if self.sender:
            embed.set_author(
                name=str(self.sender.login),
                icon_url=str(self.sender.avatar_url),
                url=str(self.sender.html_url)
            )
            
        embed.set_footer(
            text=f"📁 {self.repository.size or 0}KB | 📝 {self.repository.open_issues_count or 0} issues | 👥 {self.repository.watchers_count or 0} watchers",
            icon_url="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png"
        )
            
        embed.timestamp = datetime.now()
        return embed

    async def send_message(self):
        if not (embed := self.to_embed):
            return
        log.info(f"Received embed: {embed}")
        channel_id = CONFIG["updates_channel_id"]
        for _ in range(5):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages",
                        headers={
                            "Authorization": f"Bot {CONFIG['token']}",
                            "Content-Type": "application/json"
                        },
                        json={"embeds": [embed.to_dict()]}
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        
                        if response.status != 429:
                            log.error(f"Failed to send message: {response.status}")
                            
                await asyncio.sleep(1)
                        
            except Exception as e:
                log.error(f"Error sending message: {e}")
                await asyncio.sleep(1)

    async def send_message(self):
        if not (embed := self.to_embed):
            return

        channel_id = CONFIG["updates_channel_id"]
        token = CONFIG["token"]

        for _ in range(5):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"https://discord.com/api/v10/channels/{channel_id}/messages",
                        headers={
                            "Authorization": f"Bot {token}",
                            "Content-Type": "application/json"
                        },
                        json={"embeds": [embed.to_dict()]}
                    ) as response:
                        if response.status == 200:
                            return await response.json()
                        
                        if response.status != 429: 
                            log.error(f"Failed to send message: {response.status}")
                            
                await asyncio.sleep(1)  
                        
            except Exception as e:
                log.error(f"Error sending message: {e}")
                await asyncio.sleep(1)

        return None


class Module(BaseModel):
    threshold: int
    duration: int
    
    def __init__(self, **data):
        super().__init__(**data)
        self.last_trigger = 0
        self.count = 0

cache.setup("mem://")
log = logging.getLogger(__name__)


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


def requires_auth(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(self: "Network", request: Request) -> Response:
        auth_header = request.headers.get("Authorization")
        if auth_header != "87cef2df-be53-43e2-b974-5df9d980cd94":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await func(self, request)

    return wrapper

def requires_not_auth(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(self: "Network", request: Request) -> Response:
        auth_header = request.headers.get("Authorization")
        if auth_header != "a70c1ab9-2b72-4371-a3cb-a499f24f127f":
            return web.json_response({"error": "Unauthorized"}, status=401)
        return await func(self, request)

    return wrapper

def ratelimit(requests: int, window: int):
    def decorator(func):
        async def wrapper(self, request: Request, *args, **kwargs):
            global_key = "global_ratelimit"
            
            ip = (
                request.headers.get("CF-Connecting-IP")
                or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or request.remote
            )
            
            global_current = await self.bot.redis.get(global_key)
            if global_current and int(global_current) >= 30000:
                return web.json_response({"error": "Global rate limit exceeded"}, status=429)
            
            key = f"ratelimit:{ip}:{func.__name__}"
            current = await self.bot.redis.get(key)
            if current and int(current) >= requests:
                return web.json_response({"error": "Rate limit exceeded"}, status=429)
                
            pipe = self.bot.redis.pipeline()
            pipe.incr(key)
            if not current:
                pipe.expire(key, window)
            await pipe.execute()
            
            response = await func(self, request, *args, **kwargs)
            
            if response.status < 400:
                pipe = self.bot.redis.pipeline()
                pipe.incr(global_key)
                if not global_current:
                    pipe.expire(global_key, 60)
                await pipe.execute()
            
            return response
        return wrapper
    return decorator

def requires_special_auth(f):
    @functools.wraps(f)
    async def wrapped(self, request: Request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        token = auth_header.split(" ")[1]
        user_id = request.query.get("user_id")
        
        if not user_id or not await self.verify_token(token, int(user_id)):
            return web.json_response({"error": "Invalid token"}, status=401)
            
        return await f(self, request, *args, **kwargs)
    return wrapped


def route(pattern: str, method: str | list[str] = "GET") -> Callable:
    def decorator(func: Callable) -> Callable: 
        @wraps(func)
        async def wrapper(self: "Network", request: Request) -> None:
            start_time = datetime.now(timezone.utc)
            allowed_methods = [method] if isinstance(method, str) else method.copy()
            
            if request.method not in allowed_methods:
                response = web.json_response(
                    {"error": f"Method {request.method} not allowed"}, 
                    status=405,
                    headers={"Allow": ", ".join(allowed_methods)}
                )

                return response
            
            try:
                response = await func(self, request)

                return response
            except Exception as e:
                log.error(f"Error in {pattern}: {e}")
                response = web.json_response(
                    {"error": "Internal server error"}, 
                    status=500
                )

                return response

        wrapper.methods = [method] if isinstance(method, str) else method.copy()
        wrapper.pattern = pattern
        return wrapper
    return decorator


class Network(Cog):
    def __init__(self, bot: Evict):
        self.bot: Evict = bot
        self.app = web.Application(
            client_max_size=1024**2, 
            middlewares=[]
        )
        self.runner = None 
        self.site = None  
        self.previous_idle_time = 0
        self.previous_total_time = 0
        self.last_cpu_check = 0
        
        self.cors = cors_setup(
            self.app,
            defaults={
                "*": ResourceOptions(
                    allow_credentials=False,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods=["GET", "POST", "OPTIONS"],
                    max_age=3600
                )
            },
        )

        async def request_middleware(request, handler):
            start_time = time.time()
            request_id = str(uuid.uuid4())[:8]

            try:
                response = await handler(request)
                
                if response.status == 429:
                    ratelimit_key = f"ratelimit_log:{request.remote}:{request.path}"
                    if not await self.bot.redis.exists(ratelimit_key):
                        log.info(f"[{request_id}] Rate limited {request.method} {request.path} from {request.remote}")
                        await self.bot.redis.set(ratelimit_key, "1", ex=60)
                else:
                    log_key = f"weblogs:{request.path}:{request.remote}"
                    should_log = not await self.bot.redis.exists(log_key)
                    if should_log:
                        log.info(f"[{request_id}] {request.method} {request.path} from {request.remote}")
                        await self.bot.redis.set(log_key, "1", ex=60)
                
                return response
                    
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                log.error(
                    f"[{request_id}] Request timed out after {duration:.2f}s: "
                    f"{request.method} {request.path}"
                )
                return web.json_response(
                    {"error": "Request timed out"}, 
                    status=504
                )
                
            except Exception as e:
                duration = time.time() - start_time
                log.error(
                    f"[{request_id}] Error handling request after {duration:.2f}s: "
                    f"{request.method} {request.path}"
                )
                log.error(f"[{request_id}] Error details: {e}")
                log.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
                
                return web.json_response(
                    {"error": "Internal server error"},
                    status=500
                )

        self.app.middlewares.append(web.middleware(request_middleware))

        for module in dir(self):
            route = getattr(self, module)
            if not hasattr(route, "pattern"):
                continue
            
            resource = self.app.router.add_resource(route.pattern)
            
            methods = route.methods if isinstance(route.methods, list) else [route.methods]
            methods = [m for m in methods if m != "OPTIONS"]
            
            for method in methods:
                handler = resource.add_route(method, route)
                self.cors.add(handler)

        root_resource = self.app.router.add_get("/", self.root_handler)
        self.cors.add(root_resource)

        # self.ws_connections = {}  # {guild_id: {auth_token: ws}}
        # self.app.router.add_get("/ws/music/{guild_id}", self.music_websocket)

        # self.failed_payment_notifications = defaultdict(list)

    def required_xp(self, level: int, multiplier: int = 1) -> int:
        """
        Calculate the required XP for a given level.
        """
        xp = sum((i * 100) + 75 for i in range(level))
        return int(xp * multiplier)

    async def root_handler(self, request):
        return web.json_response(
            {
            "commands": {len([cmd for cmd in self.bot.walk_commands() if cmd.cog_name != 'Jishaku' and cmd.cog_name != 'Owner'])},
            "latency": self.bot.latency * 1000,
            "cache": {
                "guilds": len(self.bot.guilds),
                "users": len([user for user in self.bot.users if not user.bot]),
            },
            }
        )

    async def cog_load(self) -> None:
        host = config.NETWORK.HOST
        port = config.NETWORK.PORT
        
        if hasattr(self, 'app'):
            await self.app.cleanup()
            
        self.app = web.Application(
            client_max_size=1024**2,  
            middlewares=[
                
            ]
        )
        self.cors = cors_setup(
            self.app,
            defaults={
                "*": ResourceOptions(
                    allow_credentials=False,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods=["GET", "POST", "OPTIONS"],
                    max_age=3600
                )
            },
        )
        
        for module in dir(self):
            route = getattr(self, module)
            if not hasattr(route, "pattern"):
                continue
            
            resource = self.app.router.add_resource(route.pattern)
            for method in route.methods:
                handler = resource.add_route(method, route)
                self.cors.add(handler)
                
        # self.app.router.add_get("/music/{guild_id}", self.music_websocket)
        
        self.runner = web.AppRunner(
            self.app,
            access_log=log, 
            handle_signals=True,
            keepalive_timeout=75.0, 
            tcp_keepalive=True,
            shutdown_timeout=60.0
        )
        await self.runner.setup()
        
        self.site = web.TCPSite(
            self.runner, 
            host, 
            port,
            backlog=1024,
            reuse_address=True,
            reuse_port=True
        )
        await self.site.start()
        
        log.info(f"Started the internal API on {host}:{port}.")

    async def cog_unload(self) -> None:
        if self.site:
            await self.site.stop()
            log.info("Stopped the TCP site")
        
        if self.runner:
            await self.runner.cleanup()
            log.info("Cleaned up the runner")
        
        await self.app.shutdown()
        await self.app.cleanup()
        log.info("Gracefully shutdown the API")

    @route("/health")
    @requires_not_auth
    @ratelimit(5, 60)
    async def health(self, request: Request) -> Response:
        return web.json_response({
            "status": "ok",
            "timestamp": int(time.time()),
            "uptime": int(self.bot.uptime2)
        })

    @route("/commands")
    # @ratelimit(5, 60)
    async def commands(self: "Network", request: Request) -> Response:
        """
        Export command information as JSON, including commands within groups.
        """
        def get_flags(param):
            if isinstance(param.annotation, type) and issubclass(param.annotation, FlagConverter):
                flags = param.annotation.get_flags()
                return {
                    "required": [
                        {
                            "name": name,
                            "description": flag.description
                        }
                        for name, flag in flags.items()
                        if not flag.default
                    ],
                    "optional": [
                        {
                            "name": name,
                            "description": flag.description
                        }
                        for name, flag in flags.items()
                        if flag.default
                    ]
                }
            return None
        
        def get_donator(command):
            if command.checks:
                for check in command.checks:
                    if check.__name__ == "predicate" and check.__qualname__.startswith("donator"):
                        return True
            return False

        def get_permissions(command):
            try:
                perms = [perm.lower().replace("n/a", "None").replace("_", " ") 
                        for perm in command.permissions]
                
                if "antinuke" in command.qualified_name.lower():
                    perms.extend(["antinuke admin", "guild owner"])
                    
                if len(perms) > 1:
                    perms = [p for p in perms if p.lower() not in ("none", "n/a")]
                    
                return perms
            except AttributeError:
                perms = []
                for check in command.checks if command.checks else []:
                    if hasattr(check, 'closure') and check.closure:
                        for cell in check.closure:
                            if hasattr(cell, 'cell_contents') and isinstance(cell.cell_contents, dict):
                                perms.extend(cell.cell_contents.keys())
                                
                if "antinuke" in command.qualified_name.lower():
                    perms.extend(["antinuke admin", "guild owner"])
                    
                perms = [perm.replace('_', ' ').title() for perm in perms] if perms else ["N/A"]
                
                if len(perms) > 1:
                    perms = [p for p in perms if p.lower() not in ("n/a", "none")]
                    
                return perms

        def format_parameters(command):
            def clean_type(annotation):
                if hasattr(annotation, '__name__'):
                    return annotation.__name__
                if str(annotation).startswith('<'): 
                    return str(annotation.__class__.__name__)
                if str(annotation).startswith('typing.Optional'):
                    return 'Optional[' + clean_type(annotation.__args__[0]) + ']'
                return str(annotation)

            return [
                {
                    "name": name,
                    "type": clean_type(param.annotation),
                    "default": None if param.default == param.empty else str(param.default),
                    "flags": get_flags(param),
                    "optional": param.default != param.empty
                }
                for name, param in command.clean_params.items()
            ]

        IGNORED_CATEGORIES = [
            "Jishaku",
            "Network",
            "API", 
            "Owner",
            "Status",
            "Listeners",
            "Hog"
        ]

        commands_info = []
        categories = sorted(list(set([
            cog.qualified_name for cog in self.bot.cogs.values() 
            if cog.qualified_name not in IGNORED_CATEGORIES
            and "cogs" in getattr(cog, "__module__", "")
        ])))

        for cog in self.bot.cogs.values():
            if cog.qualified_name in IGNORED_CATEGORIES:
                continue

            for command in cog.get_commands():
                if isinstance(command, Group):
                    commands_info.append({
                        "name": command.qualified_name,
                        "description": command.description or command.help or "No description",
                        "aliases": command.aliases,
                        "parameters": format_parameters(command),
                        "category": command.cog.qualified_name if command.cog else "No Category",
                        "permissions": get_permissions(command),
                        "donator": get_donator(command) 
                    })
                    
                    seen_commands = {command.qualified_name}
                    
                    for subcommand in command.walk_commands():
                        if subcommand.qualified_name not in seen_commands:
                            seen_commands.add(subcommand.qualified_name)
                            commands_info.append({
                                "name": subcommand.qualified_name, 
                                "description": subcommand.description or subcommand.help or "No description", 
                                "aliases": subcommand.aliases,
                                "parameters": format_parameters(subcommand),
                                "category": subcommand.cog.qualified_name if subcommand.cog else "No Category",
                                "permissions": get_permissions(subcommand),
                                "donator": get_donator(subcommand)
                            })
                else:
                    commands_info.append({
                        "name": command.qualified_name,
                        "description": command.description or command.help or "No description",
                        "aliases": command.aliases,
                        "parameters": format_parameters(command),
                        "category": command.cog.qualified_name if command.cog else "No Category", 
                        "permissions": get_permissions(command),
                        "donator": get_donator(command)
                    })

        return web.json_response({"categories": categories, "commands": commands_info})

    @route("/status")
    # @ratelimit(5, 60)
    async def status(self, request: Request) -> Response:
        return web.json_response(
            {
                "shards": [
                    {
                        "guilds": f"{len([guild for guild in self.bot.guilds if guild.shard_id == shard.id])}",
                        "id": f"{shard.id}",
                        "ping": f"{(shard.latency * 1000):.2f}ms",
                        "uptime": f"{int(self.bot.uptime2)}",
                        "users": f"{sum(guild.member_count for guild in self.bot.guilds if guild.shard_id == shard.id)}",
                    }
                    for shard in self.bot.shards.values()
                ]
            }
        )

    @route("/tickets")
    @ratelimit(5, 60)
    @requires_auth
    async def tickets(self: "Network", request: Request) -> Response:
        ticket_id = request.query.get("id")
        user_id = request.headers.get("User-ID")
        authorization = request.headers.get("Authorization")

        log.info(
            f"Request received for ticket {ticket_id} with Authorization: {authorization} and User-ID: {user_id}"
        )

        if not ticket_id:
            return web.json_response({"error": "Missing ticket ID"}, status=400)
        if not user_id:
            return web.json_response({"error": "Missing User-ID header"}, status=400)

        ticket_path = f"/root/tickets/{ticket_id}.json"
        user_ids_path = f"/root/tickets/{ticket_id}_ids.json"

        if not os.path.isfile(ticket_path):
            log.warning(f"Ticket {ticket_id} not found.")
            return web.json_response({"error": "Ticket not found"}, status=404)

        if not os.path.isfile(user_ids_path):
            log.warning(f"Access list for ticket {ticket_id} not found.")
            return web.json_response(
                {"error": "Access list not found for ticket"}, status=404
            )

        try:
            with open(user_ids_path, "r") as ids_file:
                user_data = json.load(ids_file)
                if user_id not in map(str, user_data.get("ids", [])):
                    log.warning(
                        f"User {user_id} is not authorized to access ticket {ticket_id}."
                    )
                    return web.json_response(
                        {"error": "User not authorized to access this ticket"},
                        status=403,
                    )

            with open(ticket_path, "r") as file:
                ticket_data = json.load(file)

            log.info(f"Ticket {ticket_id} successfully fetched for User-ID: {user_id}.")
            return web.json_response(ticket_data)

        except Exception as e:
            log.error(f"Error reading ticket {ticket_id}: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

    @route("/tickets", ["POST"])
    @ratelimit(5, 60)
    @requires_auth
    async def create_ticket(self: "Network", request: Request) -> Response:
        try:
            data = await request.json()
            
            if "ticket_id" not in data:
                return web.json_response({"error": "Missing ticket_id"}, status=400)
            if "ticket_data" not in data:
                return web.json_response({"error": "Missing ticket_data"}, status=400)
            if "user_ids" not in data:
                return web.json_response({"error": "Missing user_ids"}, status=400)
                
            ticket_id = data["ticket_id"]
            ticket_data = data["ticket_data"]
            user_ids = data["user_ids"]
            
            ticket_path = f"/root/tickets/{ticket_id}.json"
            user_ids_path = f"/root/tickets/{ticket_id}_ids.json"
            
            if os.path.isfile(ticket_path):
                return web.json_response(
                    {"error": f"Ticket {ticket_id} already exists"}, 
                    status=409
                )
                
            os.makedirs("/root/tickets", exist_ok=True)
            
            try:
                with open(ticket_path, "w") as f:
                    json.dump(ticket_data, f, indent=4)
                    
                with open(user_ids_path, "w") as f:
                    json.dump({"ids": user_ids}, f, indent=4)
                    
                log.info(f"Created ticket {ticket_id} with access for users: {user_ids}")
                
                return web.json_response({
                    "success": True,
                    "message": f"Ticket {ticket_id} created successfully",
                    "ticket_id": ticket_id
                })
                
            except IOError as e:
                log.error(f"Failed to write ticket files: {e}")
                for path in [ticket_path, user_ids_path]:
                    if os.path.exists(path):
                        os.remove(path)
                return web.json_response(
                    {"error": "Failed to save ticket files"}, 
                    status=500
                )
                
        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON in request body"}, 
                status=400
            )
        except Exception as e:
            log.error(f"Error creating ticket: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500
            )

    @route("/levels")
    @ratelimit(5, 60)
    @requires_auth
    async def levels(self: "Network", request: Request) -> Response:
        """
        Fetch level information for all members in a guild including user avatar, username, display name, roles, and level roles.
        """
        guild_id = request.headers.get("X-GUILD-ID")
        if not guild_id:
            return web.json_response({"error": "Missing X-GUILD-ID header"}, status=400)

        try:
            guild_id = int(guild_id)
        except ValueError:
            return web.json_response({"error": "Invalid X-GUILD-ID header"}, status=400)

        guild_exists_query = """
        SELECT EXISTS(SELECT 1 FROM level.member WHERE guild_id = $1);
        """
        guild_exists = await self.bot.db.fetchval(guild_exists_query, guild_id)
        if not guild_exists:
            return web.json_response({"error": "Guild ID does not exist"}, status=404)

        level_query = """
        SELECT user_id, xp, level, total_xp, formula_multiplier
        FROM level.member
        INNER JOIN level.config
        ON level.member.guild_id = level.config.guild_id
        WHERE level.member.guild_id = $1;
        """
        level_records = await self.bot.db.fetch(level_query, guild_id)

        users_data = []
        for record in level_records:
            user = self.bot.get_user(record["user_id"])
            if user:
                avatar_url = (
                    str(user.avatar)
                    if user.avatar
                    else (
                        str(user.default_avatar_url)
                        if user.default_avatar_url
                        else None
                    )
                )

                users_data.append(
                    {
                        "user_id": record["user_id"],
                        "xp": record["xp"],
                        "level": record["level"],
                        "total_xp": record["total_xp"],
                        "max_xp": self.required_xp(
                            record["level"] + 1, record["formula_multiplier"]
                        ),
                        "avatar_url": avatar_url,
                        "username": user.name if user.name else "Unknown",
                        "display_name": (
                            user.display_name if user.display_name else "Unknown"
                        ),
                    }
                )

        level_roles_query = """
        SELECT role_id, level
        FROM level.role
        WHERE guild_id = $1
        """
        level_roles_records = await self.bot.db.fetch(level_roles_query, guild_id)

        level_roles = []
        guild = self.bot.get_guild(guild_id)
        for role in level_roles_records:
            discord_role = discord.utils.get(guild.roles, id=role["role_id"])
            if discord_role:
                level_roles.append(
                    {
                        "role_id": role["role_id"],
                        "level": role["level"],
                        "role_name": discord_role.name,
                        "hex_color": (
                            str(discord_role.color) if discord_role.color else None
                        ),
                    }
                )

        response_data = {
            "guild_id": guild_id,
            "guild_name": guild.name if guild else "Unknown Guild",
            "level_roles": level_roles,
            "users": users_data,
        }

        return web.json_response(response_data)

    @route("/spotify/auth", ["POST"])
    @ratelimit(5, 60)
    @requires_not_auth
    async def spotify_auth(self: "Network", request: Request) -> Response:
        try:
            data = await request.json()
            
            required_fields = {
                "user_id": data.get("user_id"),
                "spotify_access_token": data.get("spotify_access_token"), 
                "spotify_refresh_token": data.get("spotify_refresh_token"),
                "expires_in": data.get("expires_in"),
                "spotify_id": data.get("spotify_id")
            }

            if missing := [k for k, v in required_fields.items() if not v]:
                return web.json_response(
                    {"error": f"Missing required fields: {', '.join(missing)}"},
                    status=400
                )

            current_time = datetime.now(timezone.utc)
            expires_at = (current_time + timedelta(seconds=int(required_fields["expires_in"])))
            
            expires_at_ts = expires_at.replace(tzinfo=None)

            await self.bot.db.execute(
                """
                INSERT INTO user_spotify (
                    user_id, access_token, refresh_token, token_expires_at, spotify_id
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    refresh_token = EXCLUDED.refresh_token, 
                    token_expires_at = EXCLUDED.token_expires_at,
                    spotify_id = EXCLUDED.spotify_id
                """,
                int(required_fields["user_id"]),
                required_fields["spotify_access_token"],
                required_fields["spotify_refresh_token"], 
                expires_at_ts, 
                required_fields["spotify_id"]
            )

            return web.json_response({"success": True})
            
        except Exception as e:
            log.error(f"Error processing Spotify auth: {str(e)}", exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500)

    async def handle_options(self, request):
        return web.Response(status=200)

    @route("/lastfm/auth", ["POST"])
    @ratelimit(5, 60)
    @requires_not_auth
    async def lastfm_auth(self: "Network", request: Request) -> Response:
        try:
            data = await request.json()
            
            required_fields = {
                "user_id": data.get("user_id"),
                "access_token": data.get("access_token"),
                "username": data.get("username")
            }

            if missing := [k for k, v in required_fields.items() if not v]:
                return web.json_response(
                    {"error": f"Missing required fields: {', '.join(missing)}"},
                    status=400
                )

            await self.bot.db.execute(
                """
                INSERT INTO lastfm.config (
                    user_id, access_token, username, web_authentication
                ) VALUES ($1, $2, $3, true)
                ON CONFLICT (user_id) DO UPDATE SET
                    access_token = EXCLUDED.access_token,
                    username = EXCLUDED.username,
                    web_authentication = true
                """,
                int(required_fields["user_id"]),
                required_fields["access_token"],
                required_fields["username"]
            )

            return web.json_response({"success": True})
            
        except Exception as e:
            log.error(f"Error processing Last.fm auth: {str(e)}", exc_info=True)
            return web.json_response({"error": "Internal server error"}, status=500)

    async def can_send_failure_notification(self, user_id: int) -> bool:
        """Check if we can send a failure notification to the user (max 2 per hour)"""
        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        
        self.failed_payment_notifications[user_id] = [
            timestamp for timestamp in self.failed_payment_notifications[user_id]
            if timestamp > hour_ago
        ]
        
        return len(self.failed_payment_notifications[user_id]) < 2

    @route("/stripe-webhook", ["POST"])
    @ratelimit(10, 60)
    async def stripe_webhook(self: "Network", request: Request) -> Response:
        try:
            payload = await request.text()
            sig_header = request.headers.get('Stripe-Signature')

            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, "whsec_g6TrcTmDAJKTLNnVYl06SYWd6JS1ZWD5"
                )
            except ValueError:
                log.error("Invalid Stripe payload received")
                return web.json_response({"error": "Invalid payload"}, status=400)
            except stripe.error.SignatureVerificationError:
                log.error("Invalid Stripe signature")
                return web.json_response({"error": "Invalid signature"}, status=400)

            log_channel = self.bot.get_channel(1319933684576550922)
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                discord_id = None
                if 'custom_fields' in session:
                    for field in session['custom_fields']:
                        if field['key'] == 'useriddiscord':
                            discord_id = field['text']['value']
                            break

                if discord_id:
                    try:
                        user = await self.bot.fetch_user(int(discord_id))
                        guild = self.bot.get_guild(892675627373699072)
                        member = await guild.fetch_member(int(discord_id))

                        if session['payment_link'] == 'plink_1QYrwcRum1fE9ZQoomgy3AO2':
                            await self.bot.db.execute(
                                """
                                INSERT INTO instances 
                                (user_id, payment_id, amount, purchased_at, expires_at, status, email)
                                VALUES ($1, $2, $3, NOW(), NOW() + INTERVAL '30 days', 'pending', $4)
                                """,
                                int(discord_id),
                                session['payment_intent'],
                                session['amount_total'] / 100,
                                session['customer_details']['email']
                            )

                            guild = self.bot.get_guild(892675627373699072)
                            if guild:
                                member = await guild.fetch_member(int(discord_id))
                                if member:
                                    role = guild.get_role(1320428924215496704)
                                    if role and role not in member.roles:
                                        await member.add_roles(role, reason="Instance purchased")

                            embed = Embed(
                                title="Thank You for Purchasing an Evict Instance!",
                                description=(
                                    "Your instance purchase has been processed successfully! 🎉\n\n"
                                    "To complete the setup process, there's a small monthly hosting fee of $3 to "
                                    "keep your instance running smoothly. This helps us maintain the infrastructure "
                                    "and ensure high availability for your bot.\n\n"
                                    "**Next Steps:**\n"
                                    "- Complete the hosting subscription: [Click Here](https://buy.stripe.com/aEU5n64tXcb02OYeV1)\n"
                                    "- Once subscribed, your instance will be ready for setup\n"
                                    "- You'll receive a message on how to edit your instance\n\n"
                                    "*Note: The hosting subscription ensures your "
                                    "instance stays online and receives regular updates and maintenance.*"
                                ),
                                color=0x2ecc71
                            )
                            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                            await user.send(embed=embed)
                        
                            if log_channel:
                                log_embed = Embed(
                                    title="New Instance Purchase",
                                    description=(
                                        f"User: {user.mention} (`{user.id}`)\n"
                                        f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                        f"Payment ID: `{session['payment_intent']}`"
                                    ),
                                    color=0x2ecc71,
                                    timestamp=datetime.now(timezone.utc)
                                )
                                await log_channel.send(embed=log_embed)

                        elif session['payment_link'] == 'plink_1QYrxkRum1fE9ZQoD8WqKNKP':
                            instance = await self.bot.db.fetchrow(
                                """
                                SELECT * FROM instances 
                                WHERE user_id = $1 AND status = 'pending'
                                """,
                                int(discord_id)
                            )
                            
                            if not instance:
                                embed = Embed(
                                    title="Hosting Subscription Error",
                                    description=(
                                        "Oops! It looks like you haven't purchased an instance yet.\n\n"
                                        "Please purchase an instance first before activating the hosting subscription:\n"
                                        "[Purchase Instance](https://buy.stripe.com/8wMcPygcFej81KU006)\n\n"
                                        "If you believe this is an error, please contact our support team."
                                    ),
                                    color=0xff0000
                                )
                                embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                                await user.send(embed=embed)
                                return web.json_response({"error": "No pending instance found"}, status=400)

                            await self.bot.db.execute(
                                """
                                UPDATE instances 
                                SET status = 'active'
                                WHERE user_id = $1 AND status = 'pending'
                                """,
                                int(discord_id)
                            )

                            embed = Embed(
                                title="Instance Hosting Subscription Activated!",
                                description=(
                                    "Your instance hosting subscription has been activated! 🎉\n\n"
                                    "To set up your instance, use the following command:\n"
                                    "`;instance setup <name> <prefix>`\n\n"
                                    "After setup, you can customize your instance using:\n"
                                    "- `[prefix]customize` - Change bot appearance\n"
                                    "- `[prefix]activity` - Set bot status/activity\n\n"
                                    "Want custom commands? Create a ticket in our "
                                    "[support server](https://discord.gg/evict)\n\n"
                                    "If you need any assistance, our support team is ready to help!"
                                ),
                                color=0x2ecc71
                            )
                            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                            await user.send(embed=embed)

                            if log_channel:
                                log_embed = Embed(
                                    title="Instance Hosting Subscription Activated",
                                    description=(
                                        f"User: {user.mention} (`{user.id}`)\n"
                                        f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                        f"Payment ID: `{session['payment_intent']}`"
                                    ),
                                    color=0x2ecc71,
                                    timestamp=datetime.now(timezone.utc)
                                )
                                await log_channel.send(embed=log_embed)

                        else:
                            check = await self.bot.db.fetchrow(
                                """
                                SELECT user_id 
                                FROM donators 
                                WHERE user_id = $1
                                """,
                                int(discord_id)
                            )
                            if check is None:
                                await self.bot.db.execute(
                                    """
                                    INSERT INTO donators 
                                    VALUES ($1)
                                    """, 
                                    int(discord_id)
                                )

                            embed = Embed(
                                title="Thank You for Supporting evict!",
                                description=(
                                    "Your donation has been received and processed successfully! 🎉\n\n"
                                    "You now have access to premium features including:\n"
                                    "- Custom bot reskins\n"
                                    "- Extended limits for OpenAI features\n"
                                    "- Enhanced transcription capabilities\n"
                                    "- Priority support\n\n"
                                    "Thank you for helping keep evict running! ❤️"
                                ),
                                color=0x2ecc71
                            )
                            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                            await user.send(embed=embed)

                            role = guild.get_role(1318054098666389534)
                            if role and role not in member.roles:
                                await member.add_roles(role, reason="Donation received")

                            if log_channel:
                                log_embed = Embed(
                                    title="New Donation Received",
                                    description=(
                                        f"User: {user.mention} (`{user.id}`)\n"
                                        f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                        f"Payment ID: `{session['payment_intent']}`"
                                    ),
                                    color=0x2ecc71,
                                    timestamp=datetime.now(timezone.utc)
                                )
                                await log_channel.send(embed=log_embed)

                        return web.json_response({"success": True})

                    except Exception as e:
                        log.error(f"Failed to process donation for user {discord_id}: {e}")
                        if log_channel:
                            error_embed = Embed(
                                title="Donation Processing Failed",
                                description=(
                                    f"Failed to process donation for Discord ID: `{discord_id}`\n"
                                    f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                    f"Payment ID: `{session['payment_intent']}`\n"
                                    f"Error: ```{str(e)}```"
                                ),
                                color=0xff0000,
                                timestamp=datetime.now(timezone.utc)
                            )
                            await log_channel.send(embed=error_embed)
                        return web.json_response(
                            {"error": f"Failed to process donation: {str(e)}"}, 
                            status=500
                        )
                else:
                    if log_channel:
                        error_embed = Embed(
                            title="Donation Processing Failed",
                            description=(
                                "Payment received but no Discord ID provided\n"
                                f"Amount: ${session['amount_total'] / 100:.2f} {session['currency'].upper()}\n"
                                f"Payment ID: `{session['payment_intent']}`\n"
                                f"Raw session data: ```{json.dumps(session, indent=2)}```"
                            ),
                            color=0xff0000,
                            timestamp=datetime.now(timezone.utc)
                        )
                        await log_channel.send(embed=error_embed)
                    return web.json_response(
                        {"error": "Missing discord_user_id in metadata"}, 
                        status=400
                    )

            elif event['type'] == 'checkout.session.expired':
                session = event['data']['object']
                discord_id = session['metadata'].get('discord_user_id')
                if log_channel:
                    embed = Embed(
                        title="Checkout Session Expired",
                        description=(
                            f"Discord ID: `{discord_id if discord_id else 'Not provided'}`\n"
                            f"Session ID: `{session['id']}`"
                        ),
                        color=0xffa500,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=embed)

            elif event['type'] == 'payment_intent.payment_failed':
                intent = event['data']['object']
                discord_id = None
                
                if 'custom_fields' in intent:
                    for field in intent['custom_fields']:
                        if field['key'] == 'useriddiscord':
                            discord_id = field['text']['value']
                            break
                
                if log_channel:
                    embed = Embed(
                        title="Payment Failed",
                        description=(
                            f"Discord ID: `{discord_id if discord_id else 'Not provided'}`\n"
                            f"Payment ID: `{intent['id']}`\n"
                            f"Error: `{intent['last_payment_error']['message'] if intent.get('last_payment_error') else 'Unknown error'}`"
                        ),
                        color=0xff0000,
                        timestamp=datetime.now(timezone.utc)
                    )
                    await log_channel.send(embed=embed)

                if discord_id:
                    try:
                        user_id = int(discord_id)
                        if await self.can_send_failure_notification(user_id):
                            user = await self.bot.fetch_user(user_id)
                            error_message = (
                                intent['last_payment_error']['message'] 
                                if intent.get('last_payment_error') 
                                else 'Unknown error'
                            )
                            
                            embed = Embed(
                                title="Payment Failed",
                                description=(
                                    "Your payment to evict could not be processed.\n\n"
                                    f"Reason: {error_message}\n\n"
                                    "You can try again with a different payment method or contact your bank "
                                    "if you believe this is an error."
                                ),
                                color=0xff0000,
                                timestamp=datetime.now(timezone.utc)
                            )
                            embed.set_thumbnail(url=self.bot.user.display_avatar.url)
                            await user.send(embed=embed)
                            
                            self.failed_payment_notifications[user_id].append(datetime.now(timezone.utc))
                    except Exception as e:
                        log.error(f"Failed to send payment failure notification to user {discord_id}: {e}")

            return web.json_response({"success": True})

        except Exception as e:
            log.error(f"Error processing webhook: {e}")
            if log_channel:
                error_embed = Embed(
                    title="Webhook Processing Error",
                    description=f"Error: ```{str(e)}```",
                    color=0xff0000,
                    timestamp=datetime.now(timezone.utc)
                )
                await log_channel.send(embed=error_embed)
            return web.json_response({"error": "Internal server error"}, status=500)

    @route("/users/presence", ["GET"])
    @requires_not_auth
    @ratelimit(10, 60)
    async def get_users_presence(self: "Network", request: Request) -> Response:
        try:
            guild = self.bot.get_guild(892675627373699072)
            if not guild:
                return web.json_response({"success": False, "error": "Guild not found"}, status=404)

            tracked_roles = [
                guild.get_role(1265473601755414528), 
                guild.get_role(1264110559989862406),
                guild.get_role(1323255508609663098)
            ]

            response_data = {"data": [], "success": True}

            for role in tracked_roles:
                if not role:
                    continue

                for member in role.members:
                    activities = []
                    spotify_data = None
                    
                    for activity in member.activities:
                        if activity.name == "Spotify":
                            default_art = "https://cdn.discordapp.com/attachments/1356584666894831666/1357762676943618140/default-png.png?ex=67f16288&is=67f01108&hm=bd46675075863e567c03142951e349c3e600b0d953fe2fb55731a1fcc8a5775d"
                            
                            album_art = default_art
                            if getattr(activity, "album_cover_url", None):
                                try:
                                    album_art = f"https://i.scdn.co/image/{activity.album_cover_url.split(':', 1)[1]}"
                                except (AttributeError, IndexError):
                                    album_art = default_art
                            
                            track_id = getattr(activity, "track_id", None)
                            spotify_data = {
                                "timestamps": getattr(activity, "timestamps", {}),
                                "album": getattr(activity, "album", None),
                                "album_art_url": album_art,
                                "artist": getattr(activity, "artists", ["Unknown Artist"])[0],
                                "song": getattr(activity, "title", "Unknown Song"),
                                "track_id": track_id
                            }
                            
                        activity_data = {
                            "flags": getattr(activity, "flags", 0),
                            "id": getattr(activity, "application_id", None), 
                            "name": activity.name,
                            "type": activity.type.value,
                            "state": getattr(activity, "state", None),
                            "details": getattr(activity, "details", None),
                            "created_at": int(activity.created_at.timestamp() * 1000) if hasattr(activity, "created_at") else None,
                            "timestamps": getattr(activity, "timestamps", {}),
                            "assets": {
                                "large_image": getattr(activity.assets, "large_image", None) if hasattr(activity, "assets") else None,
                                "large_text": getattr(activity.assets, "large_text", None) if hasattr(activity, "assets") else None,
                                "small_image": getattr(activity.assets, "small_image", None) if hasattr(activity, "assets") else None,
                                "small_text": getattr(activity.assets, "small_text", None) if hasattr(activity, "assets") else None
                            } if hasattr(activity, "assets") else None
                        }

                        if activity.name == "Spotify":
                            activity_data["sync_id"] = getattr(activity, "track_id", None)
                            activity_data["party"] = {"id": f"spotify:{member.id}"}
                        
                        activities.append(activity_data)

                    public_flags = member.public_flags.value
                    badges = []
                    
                    if public_flags & (1 << 0): badges.append("Discord_Staff")
                    if public_flags & (1 << 1): badges.append("Discord_Partner")
                    if public_flags & (1 << 2): badges.append("HypeSquad_Events")
                    if public_flags & (1 << 3): badges.append("Bug_Hunter_Level_1")
                    if public_flags & (1 << 6): badges.append("House_Bravery")
                    if public_flags & (1 << 7): badges.append("Early_Supporter")
                    if public_flags & (1 << 8): badges.append("House_Balance")
                    if public_flags & (1 << 9): badges.append("House_Brilliance")
                    if public_flags & (1 << 14): badges.append("Bug_Hunter_Level_2")
                    if public_flags & (1 << 16): badges.append("Verified_Bot_Developer")
                    if public_flags & (1 << 17): badges.append("Early_Verified_Bot_Developer")
                    if public_flags & (1 << 22): badges.append("Active_Developer")
                    
                    if member.premium_since:
                        badges.append("Discord_Nitro")
                        badges.append("Nitro_Boost")

                    links = await self.bot.db.fetch(
                        """
                        SELECT type, url 
                        FROM user_links 
                        WHERE user_id = $1
                        """,
                        member.id
                    )
                    
                    user_data = {
                        "kv": {},
                        "discord_user": {
                            "id": str(member.id),
                            "username": member.name,
                            "avatar": member.avatar.key if member.avatar else None,
                            "discriminator": member.discriminator,
                            "clan": {
                                "tag": None,
                                "identity_guild_id": "",
                                "badge": None,
                                "identity_enabled": True
                            },
                            "avatar_decoration_data": {
                                "sku_id": member.avatar_decoration_sku_id,
                                "asset": member.avatar_decoration.key if member.avatar_decoration else None,
                                "expires_at": None 
                            } if member.avatar_decoration else None,
                            "bot": member.bot,
                            "global_name": member.global_name,
                            "primary_guild": {
                                "tag": None,
                                "identity_guild_id": None,
                                "badge": None,
                                "identity_enabled": True
                            },
                            "display_name": member.display_name,
                            "public_flags": public_flags,
                            "badges": badges,
                            "roles": [str(role.id)],
                            "links": {
                                link['type']: link['url']
                                for link in links
                            } if links else {}
                        },
                        "activities": activities,
                        "discord_status": str(member.status),
                        "active_on_discord_web": member.web_status != Status.offline,
                        "active_on_discord_desktop": member.desktop_status != Status.offline,
                        "active_on_discord_mobile": member.mobile_status != Status.offline,
                        "listening_to_spotify": bool(spotify_data),
                        "spotify": spotify_data
                    }

                    response_data["data"].append(user_data)

            return web.json_response(response_data)

        except Exception as e:
            log.error(f"Error in get_users_presence: {e}", exc_info=True)
            return web.json_response(
                {"success": False, "error": "Internal server error"}, 
                status=500
            )

    @route("/avatars/{user_id}")
    @ratelimit(10, 60)
    @requires_auth
    async def avatars(self, request: Request) -> Response:
        """
        Get avatar history for a user.
        """
        try:
            user_id = int(request.match_info["user_id"])
            
            avatars = await self.bot.db.fetch(
                """
                SELECT avatar_url, timestamp::text
                FROM avatar_history
                WHERE user_id = $1 AND deleted_at IS NULL
                ORDER BY timestamp DESC
                """,
                user_id
            )

            if not avatars:
                return web.json_response({"error": "No avatar history found"}, status=404)

            user = self.bot.get_user(user_id)
            if not user:
                try:
                    user = await self.bot.fetch_user(user_id)
                except:
                    return web.json_response({"error": "User not found"}, status=404)

            return web.json_response({
                "user": {
                    "id": str(user.id),
                    "name": user.name,
                    "discriminator": user.discriminator if hasattr(user, "discriminator") else None,
                    "avatar": str(user.avatar.url) if user.avatar else None,
                    "display_name": user.display_name if hasattr(user, "display_name") else user.name
                },
                "avatars": [
                    {
                        "url": avatar["avatar_url"],
                        "timestamp": avatar["timestamp"]
                    }
                    for avatar in avatars
                ],
                "total": len(avatars)
            })

        except ValueError:
            return web.json_response({"error": "Invalid user ID"}, status=400)
        except Exception as e:
            log.error(f"Error fetching avatar history: {e}")
            return web.json_response({"error": "Internal server error"}, status=500)

    @route("/login", ["POST"])
    @ratelimit(5, 60)
    async def login(self, request: Request) -> Response:
        """
        Handle login and access token creation.
        """
        if "X-Special-Auth" not in request.headers:
            cache_key = f"missing_auth_log:{request.remote}"
            if not await self.bot.redis.exists(cache_key):
                log.warning(f"Missing X-Special-Auth header from {request.remote}")
                await self.bot.redis.set(cache_key, "1", ex=60)
            return web.json_response({"error": "Unauthorized"}, status=401)
        
        try:
            auth_header = request.headers.get("X-Special-Auth")
            if not auth_header:
                log.warning("Missing X-Special-Auth header")
                return web.json_response(
                    {"error": "Unauthorized"}, 
                    status=401
                )

            if auth_header != (os.getenv('SPECIAL_AUTH_SECRET') or 'fzx62lRok3h57XHccs4KWCRubruFKSXu'):
                log.warning("Invalid auth token")
                return web.json_response(
                    {"error": "Invalid authentication"}, 
                    status=401
                )

            data = await request.json()
            user_id = data.get("user_id")
            discord_token = data.get("access_token")

            if not user_id or not discord_token:
                return web.json_response(
                    {"error": "Missing user_id or access_token"}, 
                    status=400
                )

            timestamp = int(datetime.now(timezone.utc).timestamp())
            token_data = f"{user_id}-{timestamp}"
            token = hashlib.sha256(
                f"{token_data}-{os.getenv('TOKEN_SECRET') or 'fzx62lRok3h57XHccs4KWCRubruFKSXu'}".encode()
            ).hexdigest()

            await self.bot.db.execute(
                """
                INSERT INTO access_tokens (user_id, token, discord_token, created_at, expires_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '14 days')
                ON CONFLICT (user_id) 
                DO UPDATE SET 
                    token = $2,
                    discord_token = $3,
                    created_at = CURRENT_TIMESTAMP,
                    expires_at = CURRENT_TIMESTAMP + INTERVAL '14 days'
                """,
                int(user_id), token, discord_token
            )

            return web.json_response({
                "success": True,
                "token": token,
                "expires_in": 1209600  
            })

        except Exception as e:
            log.error(f"Error in login endpoint: {e}")
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500
            )

    async def verify_token(self, token: str, user_id: int) -> bool:
        """Verify if a token is valid for a user"""
        try:
            result = await self.bot.db.fetchrow(
                """
                SELECT EXISTS(
                    SELECT 1 
                    FROM access_tokens 
                    WHERE token = $1 
                    AND user_id = $2 
                    AND expires_at > CURRENT_TIMESTAMP
                )
                """,
                token, user_id
            )
            return result[0] if result else False
        except Exception as e:
            log.error(f"Error verifying token: {e}")
            return False

    @route("/github/webhook", ["POST"])
    @ratelimit(5, 60)
    async def github_webhook(self, request: Request) -> Response:
        """
        Handle GitHub webhook events.
        """
        try:
            event_type = request.headers.get('X-GitHub-Event')
            if event_type == 'ping':
                return web.json_response({"message": "Pong!"})

            if event_type != 'push':
                return web.json_response(
                    {"error": "Only push events are handled"}, 
                    status=400
                )

            payload = await request.read()
        
            signature = request.headers.get('X-Hub-Signature-256')
            if not signature:
                return web.json_response(
                    {"error": "Missing signature"}, 
                    status=401
                )

            secret = "gBvugfpLkOMh1aOBahGtHhduS4UcJI8Lm1ki4ABdw3rcf2yITZfFISubz0e7GdiPAyLkuQSYhIb".encode()
            expected_signature = 'sha256=' + hmac.new(
                secret,
                payload,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                log.warning(f"Invalid GitHub signature from {request.remote}")
                return web.json_response(
                    {"error": "Invalid signature"}, 
                    status=401
                )

            cache_key = f"github_webhook:{request.remote}"
            if await self.bot.redis.exists(cache_key):
                return web.json_response(
                    {"error": "Rate limited"}, 
                    status=429
                )
            await self.bot.redis.set(cache_key, "1", ex=2)  

            try:
                data = orjson.loads(payload)
            except Exception as e:
                log.error(f"Failed to parse webhook payload: {e}")
                return web.json_response(
                    {"error": "Invalid payload"}, 
                    status=400
                )

            repo_name = data.get('repository', {}).get('full_name')
            allowed_repos = CONFIG.get('github_allowed_repos', [])
            if repo_name not in allowed_repos:
                log.warning(f"Webhook received for unauthorized repo: {repo_name}")
                return web.json_response(
                    {"error": "Repository not authorized"}, 
                    status=403
                )

            try:
                event = GithubPushEvent.parse_obj(data)
                await event.send_message()
            except Exception as e:
                log.error(f"Error processing webhook: {e}", exc_info=True)
                return web.json_response(
                    {"error": "Failed to process webhook"}, 
                    status=500
                )

            return web.json_response({"success": True})

        except Exception as e:
            log.error(f"Webhook error: {e}", exc_info=True)
            return web.json_response(
                {"error": "Internal server error"}, 
                status=500
            )