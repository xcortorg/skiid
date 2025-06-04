import asyncio, contextlib, time, itertools
from datetime import timedelta
from hashlib import sha1
from typing import Dict, Optional, Union, List, Any
from discord import Message, Guild, User, Member, TextChannel
from discord.ext.commands import Context
import humanize, orjson, tuuid
from async_timeout import timeout as Timeout
from loguru import logger as log, logger
from xxhash import xxh3_64_hexdigest
from redis.asyncio import Redis
from redis.asyncio.connection import BlockingConnectionPool
from redis.asyncio.lock import Lock
from redis.backoff import EqualJitterBackoff
from redis.exceptions import LockError, NoScriptError
from redis.retry import Retry
from .semaphore import Semaphore

REDIS_URL = "redis://127.0.0.1:6379"

def fmtseconds(seconds: Union[int, float], unit="microseconds") -> str:
    """String representation of the amount of time passed.

    Args:
        seconds (Union[int, float]): seconds from ts
        minimum_unit: str

    """

    return humanize.naturaldelta(timedelta(seconds=seconds), minimum_unit=unit)


class ORJSONDecoder:
    def __init__(self, **kwargs):
        # eventually take into consideration when deserializing
        self.options = kwargs

    def decode(self, obj):
        return orjson.loads(obj)


class ORJSONEncoder:
    def __init__(self, **kwargs):
        # eventually take into consideration when serializing
        self.options = kwargs

    def encode(self, obj):
        # decode back to str, as orjson returns bytes
        return orjson.dumps(obj).decode("utf-8")


INCREMENT_SCRIPT = b"""
    local current
    current = tonumber(redis.call("incrby", KEYS[1], ARGV[2]))
    if current == tonumber(ARGV[2]) then
        redis.call("expire", KEYS[1], ARGV[1])
    end
    return current
"""

INCREMENT_SCRIPT_HASH = sha1(INCREMENT_SCRIPT).hexdigest()

MESSAGE_SCRIPT = b"""
    local key = KEYS[1]
    local message = ARGV[1]

    redis.call('RPUSH', key, message)  -- Add message to the end of the list
    redis.call('LTRIM', key, -200, -1)  -- Trim the list to keep only the last 50 messages
"""


class RivalLock(Lock):
    def __init__(
        self,
        redis: Redis,
        name: Union[str, bytes, memoryview],
        max_lock_ttl: float = 30.0,
        extension_time: float = 0.5,
        sleep: float = 0.2,
        blocking: bool = True,
        blocking_timeout: float = None,
        thread_local: bool = False,
    ) -> None:
        self.extension_time = extension_time
        self.extend_task: Optional[asyncio.Task] = None
        self._held = False

        super().__init__(
            redis, name, max_lock_ttl, sleep, blocking, blocking_timeout, thread_local
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__} <Held in CtxManager: {self._held!r}>"

    async def extending_task(self):
        while True:
            await asyncio.sleep(self.extension_time)
            await self.reacquire()


    async def __aexit__(self, exc_type, exc_value, traceback):
        if self.extend_task:
            self.extend_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.extend_task
            self.extend_task = None

        await self.release()
        self._held = False

    async def __aenter__(self):
        if await self.acquire():
            self._held = True
            if self.extension_time:
                self.extend_task = asyncio.create_task(self.extending_task())
            return self
        raise LockError("Unable to acquire lock within the time specified")


class RivalRedis(Redis):
    def __init__(self, *a, **ka):
        self._locks_created: Dict[Union[str, bytes, memoryview], RivalLock] = {}
        self._namespace = tuuid.tuuid()
        self.rl_prefix = "rlb:"
        self.is_ratelimited = self.ratelimited
        self.rl_keys = {}
        self.channels = []
        self.__semaphores: Dict[ str, Semaphore ] = {}
        super().__init__(*a, **ka)

    def json(self):
        return super().json(ORJSONEncoder(), ORJSONDecoder())

    @property
    def held_locks(self):
        return [
            {name: lock} for name, lock in self._locks_created.items() if lock.locked()
        ]

    @property
    def pubsubs(self):
        return self._pubsub_

    @property
    def locks(self):
        return self._locks_created

    def __repr__(self):
        return f"{self.__class__.__name__} {self._namespace} <{self.connection_pool!r}>"

    async def jsonset(self, key, data: dict, **ka):
        return await self._json.set(key, ".", data, **ka)

    async def subscribe(self, channel, dispatcher):
        if channel not in self.channels:
            if not hasattr(self, "pubsub"):
                self._pubsub_ = self._pubsub_()
            await self._pubsub_.subscribe(channel)
            self.dispatcher = dispatcher
            self.channels.append(channel)
            return True
        return False
    
    def get_semaphore(
        self, 
        resource_ident: str,
        value: int
    ) -> Semaphore:
        key = f"sem:{xxh3_64_hexdigest(resource_ident)}"
        return Semaphore(self, count = value, namespace = key)
#        if key not in self.__semaphores or self.__semaphores[key]._value != value:
 #           self.__semaphores[key] = Semaphore(value)
  #      return self.__semaphores[key]

    async def read_messages(self):
        if sub := getattr(self, "_pubsub_"):
            async def reader(pubsub):
                while True:
                    try:
                        message = await asyncio.wait_for(pubsub.get_message(ignore_subscribe_messages=True), timeout=10)
                        if message:
                            await self.dispatcher.dispatch("message_received", message)
                        else:
                            await asyncio.sleep(0.01)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                         logger.info(f"read_messages raised: {e}")
            await reader(sub)

    async def jsonget(self, key):
        return await self._json.get(key)

    async def jsondelete(self, key):
        return await self._json.delete(key)

    async def getstr(self, key):
        return (await self.get(key)).decode("UTF-8")

    @classmethod
    async def from_url(
        cls, url=REDIS_URL, retry="jitter", attempts=100, timeout=120, **ka
    ):
        retry_form = Retry(backoff=EqualJitterBackoff(3, 1), retries=attempts)
        cls = cls(
            connection_pool=BlockingConnectionPool.from_url(
                url, timeout=timeout, max_connections=7000, retry=retry_form, **ka
            )
        )
        log.warning(
            f"New Redis! {url}: timeout: {timeout} retry: {retry} attempts: {attempts} "
        )

        ping_time = 0
        async with Timeout(9):
            for _ in range(5):
                start = time.time()
                await cls.ping()
                ping_time += time.time() - start
        avg = ping_time / 5

        log.success(f"Connected. 5 pings latency: {fmtseconds(avg)}")
        return cls

    def rl_key(self, ident) -> str:
        return f"{self.rl_prefix}{xxh3_64_hexdigest(ident)}"
    
    async def aclose(self, close_connection_pool: Optional[bool] = None) -> None:
        """
        Closes Redis client connection

        Args:
            close_connection_pool:
                decides whether to close the connection pool used by this Redis client,
                overriding Redis.auto_close_connection_pool.
                By default, let Redis.auto_close_connection_pool decide
                whether to close the connection pool.
        """
        conn = self.connection
        if conn:
            self.connection = None
            await self.connection_pool.release(conn)
        if close_connection_pool or (
            close_connection_pool is None and self.auto_close_connection_pool
        ):
            await self.connection_pool.disconnect()

    async def ratelimited(
        self, resource_ident: str, request_limit: int, timespan: int = 60, increment=1
    ) -> bool:
        rlkey = f"{self.rl_prefix}{xxh3_64_hexdigest(resource_ident)}"
        try:
            current_usage = await self.evalsha(
                INCREMENT_SCRIPT_HASH, 1, rlkey, timespan, increment
            )
        except NoScriptError:
            current_usage = await self.eval(
                INCREMENT_SCRIPT, 1, rlkey, timespan, increment
            )
        self.rl_keys[resource_ident]=rlkey
        if int(current_usage) > request_limit:
            return True
        return False

        name = f"lock:{xxh3_64_hexdigest(name)}"
        if name:
            if lock := self._locks_created.get(name):
                return lock
        else:
            name = f"{xxh3_64_hexdigest(tuuid.tuuid())}_l"
        self._locks_created[name] = RivalLock(
            redis=self, name=name, blocking_timeout=timeout, *a, **ka
        )
        self._locks_created[name]._namespace = self._namespace
        return self._locks_created[name]

    async def add_message(self, message: Message):
        key = xxh3_64_hexdigest(f"{message.guild.id}-{message.channel.id}-{message.author.id}")
        await self.eval(MESSAGE_SCRIPT, 1, key, message.clean_content)
        return True

    async def get_all_messages(self, guild: Union[Guild,int], user: Union[User, Member], channels: Optional[List[Any]] = None):
        async def get_msg(guild: Union[int,Guild], channel: Union[int,TextChannel], user: Union[User, Member]):
            if isinstance(guild, Guild): key = xxh3_64_hexdigest(f"{guild.id}-{channel.id}-{user.id}")
            else: key = xxh3_64_hexdigest(f"{guild}-{channel}-{user.id}")
            if messages := await self.lrange(key, 0, -1):
                return messages
            return None
        if isinstance(guild, Guild):
            m = await asyncio.gather(*[get_msg(guild, ch, user) for ch in guild.text_channels])
        else: m = await asyncio.gather(*[get_msg(guild, c, user) for c in channels])
        m = [_ for _ in m if _ != None]
        return list(itertools.chain.from_iterable(m))

    async def get_messages(self, ctx: Context):
        message = ctx.message
        key = xxh3_64_hexdigest(f"{message.guild.id}-{message.channel.id}-{message.author.id}")
        messages = await self.lrange(key, 0, -1)
        return messages
