import math
import random
from datetime import datetime
from collections import defaultdict
from asyncio import Lock, gather, create_task, sleep, Future, get_event_loop
from typing import Optional, Coroutine, Callable, Any, Dict, TypeVar, List, Set, Tuple
from asyncio.futures import Future
from typing_extensions import Self

from discord import (
    Message,
    Client,
    Guild,
    VoiceChannel,
    Member,
    VoiceState,
    Embed,
    File,
)
from discord.ext.commands import Context
from io import BytesIO
from loguru import logger
from humanize import naturaltime
from xxhash import xxh64_hexdigest as hash_

from tool.collage import _make_bar
from tool.worker.lazyload import lazy, LazyResult, compute_many, clear_cache

T = TypeVar("T")
Coro = Coroutine[Any, Any, T]
CoroT = TypeVar("CoroT", bound=Callable[..., Coro[Any]])


def get_timestamp() -> float:
    return datetime.now().timestamp()


class Level:
    def __init__(self, multiplier: float = 0.5, bot: Optional[Client] = None):
        self.multiplier = multiplier
        self.bot = bot
        self.logger = logger

        self.locks = defaultdict(Lock)
        self.text_cache_lock = Lock()

        # Use LRU caches with size limits to prevent memory issues
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.messages: Dict[str, Message] = {}
        self.text_cache: Dict[str, Dict[str, Any]] = {}
        self.level_cache: Dict[str, Any] = {}
        
        # Configuration for batch processing
        self.batch_size = 1000
        self.flush_interval = 30  # Increased from 10 to reduce DB load
        self.max_cache_size = 100000  # Maximum entries in text_cache
        self.cleanup_interval = 300  # Clean up caches every 5 minutes
        
        self.flush_task: Optional[Future] = None
        self.cleanup_task: Optional[Future] = None
        
        # Track cache statistics for monitoring
        self.cache_stats = {
            "cache_hits": 0,
            "cache_misses": 0,
            "max_cache_size_reached": 0,
            "total_messages_processed": 0
        }

    async def setup(self, bot: Client) -> Self:
        """
        Setup the leveling system. Registers the on_message listener and
        starts the periodic flush task for text XP.
        """
        self.bot = bot
        self.logger.info("Starting levelling loop")
        
        # Create a proper coroutine wrapper for the message event
        async def message_handler(message: Message):
            try:
                # Get the lazy result and compute it
                lazy_result = self.do_message_event(message)
                await lazy_result.compute()
            except Exception as e:
                self.logger.error(f"Error in message handler: {e}")
        
        # Create a proper coroutine wrapper for the voice state update event
        async def voice_state_handler(member: Member, before: VoiceState, after: VoiceState):
            try:
                # Get the lazy result and compute it
                lazy_result = self.voice_update(member, before, after)
                await lazy_result.compute()
            except Exception as e:
                self.logger.error(f"Error in voice state handler: {e}")
        
        # Add the wrapped handlers as listeners
        self.bot.add_listener(message_handler, "on_message")
        self.bot.add_listener(voice_state_handler, "on_voice_state_update")
        
        # Start periodic tasks
        self.flush_task = create_task(self.periodic_flush_text_cache())
        self.cleanup_task = create_task(self.periodic_cleanup())
        
        self.logger.info("Levelling loop started")
        return self

    async def periodic_flush_text_cache(self):
        """Periodically flush the aggregated text XP cache to the database."""
        while True:
            try:
                await sleep(self.flush_interval)
                # Check if cache size exceeds threshold for adaptive flushing
                if len(self.text_cache) > self.max_cache_size // 2:
                    self.logger.info(f"Cache size {len(self.text_cache)} triggered flush")
                    await self.flush_text_cache()
                else:
                    await self.flush_text_cache()
            except Exception as e:
                self.logger.error(f"Error during periodic flush: {e}")

    async def periodic_cleanup(self):
        """Periodically clean up caches to prevent memory bloat."""
        while True:
            try:
                await sleep(self.cleanup_interval)
                self.logger.info("Running periodic cache cleanup")
                
                # Clean up message cache
                async with self.text_cache_lock:
                    # Remove old messages from cache
                    if len(self.messages) > self.max_cache_size // 2:
                        self.logger.info(f"Cleaning up message cache (size: {len(self.messages)})")
                        # Keep only the most recent messages
                        excess = len(self.messages) - (self.max_cache_size // 4)
                        for _ in range(excess):
                            if self.messages:
                                self.messages.pop(next(iter(self.messages)))
                
                # Clean up voice cache
                if len(self.cache) > self.max_cache_size // 2:
                    self.logger.info(f"Cleaning up voice cache (size: {len(self.cache)})")
                    # Keep only the most recent entries
                    excess = len(self.cache) - (self.max_cache_size // 4)
                    for _ in range(excess):
                        if self.cache:
                            self.cache.pop(next(iter(self.cache)))
                
                # Force garbage collection to release memory
                import gc
                gc.collect()
                
                # Log cache statistics
                self.logger.info(f"Cache stats: {self.cache_stats}")
                
            except Exception as e:
                self.logger.error(f"Error during periodic cleanup: {e}")

    @lazy(pure=False, batch_size=1000)
    async def _batch_update_text_levels(self, updates: List[Dict[str, Any]]) -> None:
        """Execute a batch of text level updates using executemany for better performance."""
        if not updates:
            return
            
        try:
            # Group updates by guild for better sharding compatibility
            guild_batches = defaultdict(list)
            for update in updates:
                guild_batches[update["guild_id"]].append(update)
                
            # Process each guild batch
            for guild_id, guild_updates in guild_batches.items():
                # Use executemany for better performance
                await self.bot.db.executemany(
                    """INSERT INTO text_levels (guild_id, user_id, xp, msgs) 
                       VALUES($1, $2, $3, $4)
                       ON CONFLICT(guild_id, user_id) DO UPDATE 
                       SET xp = text_levels.xp + $3,
                           msgs = text_levels.msgs + $4""",
                    [(u["guild_id"], u["user_id"], u["xp"], u["msgs"]) for u in guild_updates]
                )
            
            self.logger.debug(f"Flushed {len(updates)} text cache entries in batch")
        except Exception as e:
            self.logger.error(f"Failed to flush text cache batch: {e}")

    @lazy(pure=False, batch_size=1000)
    async def _batch_update_voice_levels(self, updates: List[Dict[str, Any]]) -> None:
        """Execute a batch of voice level updates using executemany for better performance."""
        if not updates:
            return
            
        try:
            # Group updates by guild for better sharding compatibility
            guild_batches = defaultdict(list)
            for update in updates:
                guild_batches[update["guild_id"]].append(update)
                
            # Process each guild batch
            for guild_id, guild_updates in guild_batches.items():
                # Use executemany for better performance
                await self.bot.db.executemany(
                    """INSERT INTO voice_levels (guild_id, user_id, xp, time_spent) 
                       VALUES($1, $2, $3, $4)
                       ON CONFLICT(guild_id, user_id) DO UPDATE 
                       SET xp = voice_levels.xp + $3,
                           time_spent = voice_levels.time_spent + $4""",
                    [(u["guild_id"], u["user_id"], u["xp"], u["time_spent"]) for u in guild_updates]
                )
            
            self.logger.debug(f"Processed {len(updates)} voice level updates in batch")
        except Exception as e:
            self.logger.error(f"Failed to process voice level batch: {e}")

    async def flush_text_cache(self):
        """Flush all cached text-level data in batches."""
        async with self.text_cache_lock:
            if not self.text_cache:
                return
                
            # Prepare batch updates
            updates = []
            keys_to_remove = []
            
            for key, data in self.text_cache.items():
                # Calculate added XP - make sure to await all compute() calls
                added_xp = 0
                for m in data["messages"]:
                    xp_task = self.add_xp_from_data(m)
                    added_xp += await xp_task.compute()
                    
                updates.append({
                    "guild_id": data["guild_id"],
                    "user_id": data["user_id"],
                    "xp": added_xp,
                    "msgs": data["amount"]
                })
                keys_to_remove.append(key)
                
                # Process in batches to avoid memory issues
                if len(updates) >= self.batch_size:
                    update_task = self._batch_update_text_levels(updates)
                    await update_task.compute()
                    for k in keys_to_remove:
                        self.text_cache.pop(k, None)
                    updates = []
                    keys_to_remove = []
                    
            # Process remaining updates
            if updates:
                update_task = self._batch_update_text_levels(updates)
                await update_task.compute()
                for k in keys_to_remove:
                    self.text_cache.pop(k, None)

    @lazy(pure=True)
    def get_xp(self, level: int) -> int:
        base = (level - 1) / (0.05 * (1 + math.sqrt(5)))
        return math.ceil(math.pow(base, 2))

    @lazy(pure=True)
    def get_level(self, xp: int) -> int:
        return math.floor(0.05 * (1 + math.sqrt(5)) * math.sqrt(xp)) + 1

    @lazy(pure=True)
    async def xp_to_next_level(
        self, current_level: Optional[int] = None, current_xp: Optional[int] = None
    ) -> int:
        if current_xp is not None:
            level_task = self.get_level(current_xp)
            current_level = await level_task.compute()
        next_level_xp_task = self.get_xp(current_level + 1)
        current_level_xp_task = self.get_xp(current_level)
        next_level_xp = await next_level_xp_task.compute()
        current_level_xp = await current_level_xp_task.compute()
        return next_level_xp - current_level_xp

    @lazy(pure=True)
    def add_xp(self, message: Optional[Message] = None) -> int:
        if message:
            eligible = sum(1 for w in message.content.split() if len(w) > 1)
            xp = eligible + (10 * len(message.attachments))
            return min(xp, 50) if xp > 0 else 1
        return int(random.randint(1, 50) / self.multiplier)

    @lazy(pure=True)
    def difference(self, ts: float) -> int:
        return int(get_timestamp()) - int(ts)

    @lazy(pure=True, key="get_key")
    def get_key(
        self, guild: Guild, member: Member, channel: Optional[VoiceChannel] = None
    ) -> str:
        return hash_(f"{guild.id}-{channel.id if channel else ''}-{member.id}")

    @lazy(pure=False)
    async def validate(
        self, guild: Guild, channel: VoiceChannel, member: Member
    ) -> bool:
        """
        Validate and update a voice-level entry. If a cached entry exists,
        update the DB with new XP and dispatch level-up if necessary.
        """
        key_task = self.get_key(guild, member, channel)
        key = await key_task.compute()
        
        if key in self.cache:
            # Get current XP from database
            before_xp = (
                await self.bot.db.fetchval(
                    """SELECT xp FROM voice_levels WHERE guild_id = $1 AND user_id = $2""",
                    guild.id,
                    member.id,
                    cached=False,
                )
                or 0
            )
            
            # Calculate added XP and time spent
            added_xp_task = self.add_xp()
            added_xp = await added_xp_task.compute()
            
            diff_task = self.difference(self.cache[key]["ts"])
            time_spent = await diff_task.compute()
            
            # Update database
            update = {
                "guild_id": guild.id,
                "user_id": member.id,
                "xp": added_xp,
                "time_spent": time_spent
            }
            
            # Queue the update for batch processing
            update_task = self._batch_update_voice_levels([update])
            after_xp = before_xp + added_xp
            
            # Check for level up
            before_level_task = self.get_level(int(before_xp))
            after_level_task = self.get_level(int(after_xp))
            
            before_level = await before_level_task.compute()
            after_level = await after_level_task.compute()
            
            if before_level != after_level:
                self.bot.dispatch(
                    "voice_level_up",
                    guild,
                    channel,
                    member,
                    after_level,
                )
                
            # Process the update and remove from cache
            await update_task.compute()
            self.cache.pop(key, None)
            return True
            
        # Add to cache if not present
        self.cache[key] = {
            "guild": guild,
            "channel": channel,
            "member": member,
            "ts": int(get_timestamp()),
        }
        
        # Enforce cache size limit
        if len(self.cache) > self.max_cache_size:
            # Remove oldest entries (simple approach)
            excess = len(self.cache) - self.max_cache_size
            for _ in range(excess):
                if self.cache:
                    self.cache.pop(next(iter(self.cache)))
                    
        return False

    @lazy(pure=False)
    async def check_level_up(self, message: Message) -> bool:
        try:
            # Get current XP from database
            before_xp = (
                await self.bot.db.fetchval(
                    """SELECT xp FROM text_levels WHERE guild_id = $1 AND user_id = $2""",
                    message.guild.id,
                    message.author.id,
                    cached=False,
                )
                or 0
            )
            
            key = f"{message.guild.id}-{message.author.id}"
            if key not in self.text_cache:
                return False
                
            # Calculate added XP - make sure to await all compute() calls
            added_xp = 0
            for m in self.text_cache[key]["messages"]:
                xp_task = self.add_xp_from_data(m)
                added_xp += await xp_task.compute()
                
            after_xp = before_xp + added_xp
            
            # Check for level up
            before_level_task = self.get_level(int(before_xp))
            after_level_task = self.get_level(int(after_xp))
            
            before_level = await before_level_task.compute()
            after_level = await after_level_task.compute()
            
            if before_level != after_level:
                # Dispatch level up event
                self.bot.dispatch(
                    "text_level_up", message.guild, message.author, after_level
                )
                
                # Update database immediately for level up
                update = {
                    "guild_id": message.guild.id,
                    "user_id": message.author.id,
                    "xp": added_xp,
                    "msgs": self.text_cache[key]["amount"]
                }
                
                update_task = self._batch_update_text_levels([update])
                await update_task.compute()
                
                # Remove from cache
                self.text_cache.pop(key, None)
                return True
                
        except Exception as e:
            self.logger.error(f"Error checking level up: {e}")
            
        return False

    @lazy(pure=False)
    async def validate_text(self, message: Message, execute: bool = False) -> bool:
        """
        Accumulate text XP for a message. If 'execute' is True, the XP is
        immediately processed; otherwise, it is queued for the periodic flush.
        """
        msg_id = f"{message.guild.id}-{message.channel.id}-{message.id}"
        if msg_id in self.messages:
            self.cache_stats["cache_hits"] += 1
            return False
            
        # Use a more granular lock based on guild ID to reduce contention
        guild_lock = self.locks[f"text_levels:{message.guild.id}"]
        async with guild_lock:
            if msg_id not in self.messages:
                # Store only essential message data to reduce memory usage
                self.cache_stats["total_messages_processed"] += 1
                
                # Create a lightweight message representation
                lightweight_msg = {
                    "content": message.content,
                    "attachments_count": len(message.attachments),
                    "id": message.id,
                    "author_id": message.author.id,
                    "guild_id": message.guild.id,
                    "channel_id": message.channel.id
                }
                
                self.messages[msg_id] = lightweight_msg
                
                # Limit messages cache size
                if len(self.messages) > self.max_cache_size:
                    self.cache_stats["max_cache_size_reached"] += 1
                    # Remove oldest entries (simple approach)
                    excess = len(self.messages) - self.max_cache_size
                    for _ in range(excess):
                        if self.messages:
                            self.messages.pop(next(iter(self.messages)))
            
            key = f"{message.guild.id}-{message.author.id}"
            async with self.text_cache_lock:
                if key in self.text_cache:
                    self.text_cache[key]["amount"] += 1
                    # Store only essential message data
                    self.text_cache[key]["messages"].append({
                        "content": message.content,
                        "attachments_count": len(message.attachments)
                    })
                else:
                    self.text_cache[key] = {
                        "amount": 1,
                        "messages": [{
                            "content": message.content,
                            "attachments_count": len(message.attachments)
                        }],
                        "guild_id": message.guild.id,
                        "user_id": message.author.id,
                    }
                    
            if execute:
                # Process immediately if requested
                async with self.text_cache_lock:
                    data = self.text_cache.pop(key, None)
                    
                if data:
                    # Calculate added XP - make sure to await all compute() calls
                    added_xp = 0
                    for m in data["messages"]:
                        xp_task = self.add_xp_from_data(m)
                        added_xp += await xp_task.compute()
                        
                    update = {
                        "guild_id": message.guild.id,
                        "user_id": message.author.id,
                        "xp": added_xp,
                        "msgs": data["amount"]
                    }
                    
                    update_task = self._batch_update_text_levels([update])
                    await update_task.compute()
                return True
                
            # Check for level up
            level_up_task = self.check_level_up(message)
            await level_up_task.compute()
            return True

    @lazy(pure=False)
    async def check_guild(self, guild: Guild) -> bool:
        return bool(
            await self.bot.db.fetchrow(
                """SELECT 1 FROM text_level_settings WHERE guild_id = $1""", guild.id
            )
        )

    @lazy(pure=False)
    async def get_statistics(self, member: Member, type: str) -> Optional[List[Any]]:
        xp, amount = 0, 0
        if type.lower() == "text":
            # Get data from database
            data = await self.bot.db.fetchrow(
                """SELECT xp, msgs FROM text_levels WHERE guild_id = $1 AND user_id = $2""",
                member.guild.id,
                member.id,
                cached=False,
            )
            
            if data:
                xp += int(data.xp)
                amount += int(data.msgs)
                
            # Add data from cache
            key = f"{member.guild.id}-{member.id}"
            if key in self.text_cache:
                # Calculate added XP - make sure to await all compute() calls
                for m in self.text_cache[key]["messages"]:
                    xp_task = self.add_xp_from_data(m)
                    xp += await xp_task.compute()
                    
                amount += len(self.text_cache[key]["messages"])
        else:
            # Voice levels
            data = await self.bot.db.fetchrow(
                """SELECT xp, time_spent FROM voice_levels WHERE guild_id = $1 AND user_id = $2""",
                member.guild.id,
                member.id,
                cached=False,
            )
            
            if data:
                xp += int(data.xp)
                amount += int(data.time_spent)
                
            # Check if user is currently in voice
            for channel in member.guild.voice_channels:
                if member in channel.members:
                    key_task = self.get_key(member.guild, member, channel)
                    key = await key_task.compute()
                    
                    if key in self.cache:
                        # Add current session XP and time
                        added_xp_task = self.add_xp()
                        added_xp = await added_xp_task.compute()
                        
                        diff_task = self.difference(self.cache[key]["ts"])
                        time_spent = await diff_task.compute()
                        
                        xp += added_xp
                        amount += time_spent
                        
        return [xp, amount] if xp or amount else None

    @lazy(pure=False, batch_size=10)
    async def do_voice_levels(self):
        """Process voice levels in batches per guild to avoid overwhelming the system."""
        if not self.bot or not hasattr(self.bot, 'is_ready') or not self.bot.is_ready():
            await self.bot.wait_until_ready()
            
        # Process guilds in batches
        guild_batch_size = 10  # Process 10 guilds at a time
        all_guilds = list(self.bot.guilds)
        
        for i in range(0, len(all_guilds), guild_batch_size):
            guild_batch = all_guilds[i:i+guild_batch_size]
            guild_tasks = []
            
            for guild in guild_batch:
                # Process each guild
                guild_tasks.append(self._process_guild_voice(guild))
                
            if guild_tasks:
                await gather(*guild_tasks)
                
            # Small delay between batches to avoid CPU spikes
            await sleep(0.1)

    @lazy(pure=False)
    async def _process_guild_voice(self, guild: Guild):
        """Process voice channels for a single guild."""
        channel_tasks = []
        
        for vc in guild.voice_channels:
            if vc.members:
                # Process each channel with members
                channel_tasks.append(self._process_voice_channel(guild, vc))
                
        if channel_tasks:
            await gather(*channel_tasks)

    @lazy(pure=False, batch_size=20)
    async def _process_voice_channel(self, guild: Guild, channel: VoiceChannel):
        """Process members in a voice channel."""
        if not channel.members:
            return
            
        # Process members in batches
        member_batch_size = 20
        all_members = list(channel.members)
        
        for i in range(0, len(all_members), member_batch_size):
            member_batch = all_members[i:i+member_batch_size]
            member_tasks = []
            
            for member in member_batch:
                # Skip bots
                if member.bot:
                    continue
                    
                # Validate each member
                member_tasks.append(self.validate(guild, channel, member))
                
            if member_tasks:
                await gather(*member_tasks)

    @lazy(pure=False)
    async def member_left(
        self, guild: Guild, channel: VoiceChannel, member: Member
    ) -> bool:
        key_task = self.get_key(guild, member, channel)
        key = await key_task.compute()
        
        if key in self.cache:
            validate_task = self.validate(guild, channel, member)
            await validate_task.compute()
            return True
            
        return False

    @lazy(pure=False)
    async def voice_update(self, member: Member, before: VoiceState, after: VoiceState):
        # Skip bots
        if member.bot:
            return
            
        if before.channel:
            # Access guild through member, not through VoiceState
            left_task = self.member_left(member.guild, before.channel, member)
            await left_task.compute()
            
        if after.channel:
            # Access guild through member, not through VoiceState
            validate_task = self.validate(member.guild, after.channel, member)
            await validate_task.compute()

    @lazy(pure=False)
    async def do_message_event(self, message: Message):
        # Skip messages from bots, DMs, or guilds without leveling enabled
        if (
            not self.bot
            or message.author.bot
            or not message.guild
        ):
            return
            
        # Check if guild has leveling enabled
        check_guild_task = self.check_guild(message.guild)
        if not await check_guild_task.compute():
            return
            
        # Skip command messages
        ctx = await self.bot.get_context(message)
        if not ctx.valid:
            validate_task = self.validate_text(message)
            await validate_task.compute()

    @lazy(pure=True)
    def get_voice_time(self, time: int) -> str:
        return naturaltime(datetime.fromtimestamp(int(get_timestamp()) + time))

    @lazy(pure=False)
    async def get_member_xp(self, ctx: Context, type: str, member: Member) -> Embed:
        # Get statistics
        stats_task = self.get_statistics(member, type)
        data = await stats_task.compute()
        
        if not data:
            return await ctx.fail("No data found yet")
            
        xp, amount = data
        amount_type = "VC Time" if type.lower() == "voice" else "messages"
        
        if type.lower() == "voice":
            time_task = self.get_voice_time(amount)
            amount = f"`{await time_task.compute()}`"
            
        # Calculate level and progress
        level_task = self.get_level(xp)
        current_level = await level_task.compute()
        
        next_level_xp_task = self.get_xp(current_level + 1)
        needed_xp = await next_level_xp_task.compute()
        
        percentage = int((xp / needed_xp) * 100)
        
        # Generate progress bar
        bar_img = BytesIO(
            await _make_bar(percentage, "#2f4672", 100 - percentage, "black")
        )
        bar = File(fp=bar_img, filename="bar.png")

        embed = (
            Embed(
                title=f"{member}'s {type.lower()} Level",
                url="https://greed.rocks/",
                color=0x2F4672,
            )
            .add_field(name=amount_type, value=amount, inline=False)
            .add_field(name="Level", value=current_level, inline=False)
            .add_field(name="XP", value=f"{xp} / {needed_xp}", inline=False)
            .set_image(url=f"attachment://{bar.filename}")
        )
        
        # Don't send the message here, just return the embed and file
        # This allows the calling function to handle sending the message
        return embed, bar

    def get_coroutine_names_with_kwarg(self, kwarg_name: str) -> List[str]:
        """
        Get names of coroutine methods that accept a specific keyword argument.
        """
        from inspect import getmembers, iscoroutinefunction, signature

        members = getmembers(self, predicate=iscoroutinefunction)
        coroutine_names = []
        for name, func in members:
            if kwarg_name in signature(func).parameters:
                coroutine_names.append(name)
        return coroutine_names

    @lazy(pure=True)
    def add_xp_from_data(self, message_data: Dict[str, Any]) -> int:
        """Calculate XP from lightweight message data instead of full Message objects."""
        eligible = sum(1 for w in message_data["content"].split() if len(w) > 1)
        xp = eligible + (10 * message_data["attachments_count"])
        return min(xp, 50) if xp > 0 else 1

    async def close(self):
        """Clean up resources when shutting down."""
        if self.flush_task:
            self.flush_task.cancel()
            
        if self.cleanup_task:
            self.cleanup_task.cancel()
            
        # Final flush of caches
        await self.flush_text_cache()
        
        # Clear caches
        self.cache.clear()
        self.messages.clear()
        self.text_cache.clear()
        self.level_cache.clear()
        
        # Clear lazy computation cache
        clear_cache()
        
        self.logger.info("Level system resources cleaned up")
