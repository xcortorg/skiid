import asyncio
from functools import wraps
from rival import Connection
from discord import Client, User, Member, Guild
from asyncio import gather
from typing import Optional, Any, Union, List
from itertools import chain
from .transform import Transformers, asDict
from discord.ext.commands import UserConverter
from inspect import getmembers, iscoroutinefunction, signature
from loguru import logger
import discord

EXCLUDED_METHODS = [
    "get_user_count",
    "get_guild_count",
    "get_role_count",
    "get_channel_count",
    "get_channel",
    "send_message",
]

NON_METHODS = ["roundtrip", "setup"]


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks of specified size."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


class IPC:
    def __init__(self, bot: Client):
        self.bot = bot
        self.transformers = Transformers(self.bot)
        self.shards_per_cluster = self.bot.shard_count // 4
        self.chunks = chunk_list(
            list(range(self.bot.shard_count)), self.bot.shard_count // 4
        )
        shard_ids = list(self.bot.shards.keys())
        self.cluster_id = next(
            (
                i
                for i, chunk in enumerate(self.chunks)
                if any(shard_id in chunk for shard_id in shard_ids)
            ),
            0,
        )
        self.bot.connection = Connection(
            local_name=f"cluster{str(self.cluster_id + 1)}",
            host="127.0.0.1",
            port=13254,
        )
        self.sources = [
            f"cluster{str(i)}" for i, chunk in enumerate(self.chunks, start=1)
        ][:4]
        self.max_retries = 3
        self.retry_delay = 1

    async def wait_for_connection(self):
        """Wait until the IPC connection is ready"""
        logger.info("Checking IPC connection status")
        if not self.bot.connection.authorized or self.bot.connection.on_hold:
            logger.info("IPC connection not ready, waiting for connection")
            try:
                await self.bot.connection.wait_until_ready()
                logger.info("IPC connection is now ready")
                return True
            except asyncio.TimeoutError:
                logger.warning("Timeout while waiting for IPC connection to be ready")
                return False
        logger.info("IPC connection is already ready")
        return True

    def get_coroutine_names_with_kwarg(self, kwarg_name: str):
        # Get all members of this class that are coroutine functions
        members = getmembers(self, predicate=iscoroutinefunction)
        coroutine_names = []
        for name, func in members:
            sig = signature(func)
            if kwarg_name in sig.parameters:
                coroutine_names.append(name)
        return coroutine_names

    async def setup(self):
        logger.info("Starting IPC setup")
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Attempting to start IPC connection (attempt {attempt + 1}/{self.max_retries})")
                await self.bot.connection.start()
                logger.info("IPC connection started successfully")
                
                logger.info("Getting coroutine names with 'source' parameter")
                coroutine_names = self.get_coroutine_names_with_kwarg("source")
                logger.info(f"Found coroutine names: {coroutine_names}")
                
                logger.info("Adding IPC routes")
                await gather(
                    *[
                        self.bot.connection.add_route(getattr(self, coroutine))
                        for coroutine in coroutine_names
                    ]
                )
                logger.info("Successfully setup the IPC routes")
                return
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"IPC setup failed after {self.max_retries} attempts: {str(e)}", exc_info=True)
                    raise
                logger.warning(
                    f"IPC setup failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}", exc_info=True
                )
                await asyncio.sleep(self.retry_delay * (attempt + 1))

    async def roundtrip(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Send a message to the IPC server and return the response with retry logic"""
        logger.info(f"IPC roundtrip called for method: {method}")
        
        coro = getattr(self, method)

        if not await self.wait_for_connection():
            logger.error("IPC connection is not ready")
            raise RuntimeError("IPC connection is not ready")

        timeout = 10 if method in ["get_guild_count", "get_user_count", "get_role_count", "get_channel_count"] else 60

        for attempt in range(self.max_retries):
            try:
                tasks = []
                logger.info(f"Sending {method} request to sources: {self.sources}")
                
                for s in self.sources:
                    if s != self.bot.connection.local_name:
                        tasks.append(asyncio.create_task(self.bot.connection.request(method, s, timeout=timeout, **kwargs)))
                tasks.append(asyncio.create_task(coro(self.bot.connection.local_name, *args, **kwargs)))

                try:
                    data = await asyncio.gather(*tasks, return_exceptions=True)
                    logger.info(f"Received responses for {method}: {data}")
                    
                    if method == "get_shards":
                        d = []
                        for i in data:
                            if not isinstance(i, Exception):
                                d.extend(i)
                        logger.info(f"Processed shard data: {len(d)} shards")
                        return d
                        
                    if method in ["get_guild_count", "get_user_count", "get_role_count", "get_channel_count"]:
                        valid_counts = []
                        for i in data:
                            if not isinstance(i, Exception) and isinstance(i, (int, float)):
                                valid_counts.append(i)
                        logger.info(f"Processed count data for {method}: {valid_counts}")
                        return valid_counts
                        
                    if method not in EXCLUDED_METHODS:
                        valid_data = []
                        for i in data:
                            if not isinstance(i, Exception):
                                if isinstance(i, list):
                                    valid_data.extend(i)
                                else:
                                    valid_data.append(i)
                        logger.info(f"Processed general data: {len(valid_data)} items")
                        return valid_data
                    
                    filtered_data = [d for d in data if not isinstance(d, Exception)]
                    logger.info(f"Filtered response data: {filtered_data}")
                    return filtered_data

                except asyncio.TimeoutError:
                    logger.warning(f"Timeout in roundtrip for method {method} (attempt {attempt + 1}/{self.max_retries})")
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                    continue

            except Exception as e:
                logger.error(f"IPC request failed (attempt {attempt + 1}/{self.max_retries}): {str(e)}", exc_info=True)
                if attempt == self.max_retries - 1:
                    raise
                await asyncio.sleep(self.retry_delay * (attempt + 1))

                if not self.bot.connection.authorized:
                    try:
                        await self.bot.connection.start()
                    except Exception as e:
                        logger.error(f"Failed to restart IPC connection: {str(e)}", exc_info=True)

        raise TimeoutError(f"All attempts failed for method {method}")

    async def get_shards(self, source: str, *args, **kwargs):
        data = []
        # Only process shards that belong to this cluster's chunk
        cluster_shards = self.chunks[self.cluster_id]
        for shard_id, shard in self.bot.shards.items():
            if shard_id not in cluster_shards:
                continue
            guilds = [g for g in self.bot.guilds if g.shard_id == shard_id]
            users = sum(guild.member_count for guild in guilds)
            data.append(
                {
                    "uptime": self.bot.startup_time.timestamp(),
                    "latency": round(shard.latency * 1000),
                    "servers": len(guilds),
                    "users": users,
                    "shard": shard_id,
                }
            )
        return data

    async def get_guild_count(self, source: str):
        try:
            logger.info(f"Getting guild count for source {source}")
            count = int(len(self.bot.guilds))
            logger.info(f"Guild count for source {source}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting guild count for source {source}: {e}", exc_info=True)
            return 0

    async def get_user_count(self, source: str):
        try:
            logger.info(f"Getting user count for source {source}")
            count = int(sum(guild.member_count for guild in self.bot.guilds))
            logger.info(f"User count for source {source}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting user count for source {source}: {e}", exc_info=True)
            return 0

    async def get_role_count(self, source: str):
        try:
            logger.info(f"Getting role count for source {source}")
            count = int(sum(len(guild.roles) for guild in self.bot.guilds))
            logger.info(f"Role count for source {source}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting role count for source {source}: {e}", exc_info=True)
            return 0

    async def get_channel_count(self, source: str):
        try:
            logger.info(f"Getting channel count for source {source}")
            count = int(sum(len(guild.channels) for guild in self.bot.guilds))
            logger.info(f"Channel count for source {source}: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting channel count for source {source}: {e}", exc_info=True)
            return 0

    async def start_instance(self, source: str, token: str, user_id: int):
        cog = self.bot.get_cog("Instances")
        if cog:
            await cog.start_instance(token, user_id)
            return True
        return False

    async def stop_instance(self, source: str, token: str, user_id: int):
        cog = self.bot.get_cog("Instances")
        if cog:
            await cog.stop_instance(token, user_id)
            return True
        return False

    async def restart_instance(self, source: str, token: str, user_id: int):
        cog = self.bot.get_cog("Instances")
        if cog:
            await cog.restart_instance(token, user_id)
            return True
        return False

    async def get_instance(self, source: str, user_id: int):
        cog = self.bot.get_cog("Instances")
        if cog:
            if user_id in self.bot.instances:
                return True
        return False

    async def get_instance_count(self, source: str):
        if hasattr(self.bot, "instances"):
            return len(self.bot.instances)
        else:
            return 0

    async def ipc_get_user_from_cache(self, source, user: Union[User, int]):
        try:
            u = await UserConverter().convert(self.bot, user)
        except Exception:
            return None
        if u:
            return u._to_minimal_user_json()
        else:
            return None

    async def get_guild(self, source: str, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild:
            return self.transformers.transform_guild(guild)
        else:
            return None

    async def leave_guild(self, source: str, guild_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()
            return True
        return False

    async def get_member(self, source: str, guild_id: int, user_id: int):
        guild = self.bot.get_guild(guild_id)
        if guild:
            member = guild.get_member(user_id)
            if member:
                return self.transformers.transform_member(member)
        return None

    async def get_user_mutuals(
        self, source: str, user_id: int, count: Optional[bool] = False
    ):
        user = self.bot.get_user(user_id)
        if not user:
            return 0 if count else []
        if count:
            return len(user.mutual_guilds)
        else:
            return [asDict(guild) for guild in user.mutual_guilds]

    async def get_channel(self, source: str, channel_id: int):
        channel = self.bot.get_channel(channel_id)
        if channel:
            # Return a dictionary mapping a key to the transformed channel
            return {"channel": self.transformers.transform_channel(channel)}
        else:
            return {}

    async def send_message(
        self,
        source: str,
        channel_id: int,
        content: Optional[str] = None,
        embed: Optional[dict] = None,
    ):
        """
        Send a message to one or multiple channels.

        Args:
            source: IPC source identifier
            channel_id: Channel ID or list of channel IDs
            content: Message content
            embed: Embed dictionary

        Returns:
            dict: Mapping of channel IDs to sent message data
        """
        from discord import Embed

        channel_ids = [channel_id] if isinstance(channel_id, int) else channel_id
        embed_obj = Embed.from_dict(embed) if embed else None
        messages = {}

        for cid in channel_ids:
            channel = self.bot.get_channel(cid)
            if channel and channel.permissions_for(channel.guild.me).send_messages:
                try:
                    msg = await channel.send(content=content, embed=embed_obj)
                    messages[str(cid)] = {
                        "id": msg.id,
                        "content": msg.content,
                        "embeds": [e.to_dict() for e in msg.embeds],
                    }
                except Exception as e:
                    logger.error(f"Failed to send message to channel {cid}: {e}")

        return messages
