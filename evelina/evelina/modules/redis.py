import asyncio, contextlib, time

from time import time
from datetime import timedelta
from hashlib import sha1
from typing import Dict, Optional, Union

import humanize, orjson, tuuid
from async_timeout import timeout as Timeout
from loguru import logger as log
from xxhash import xxh3_64_hexdigest

from redis.asyncio import Redis
from redis.asyncio.connection import BlockingConnectionPool
from redis.asyncio.lock import Lock
from redis.backoff import EqualJitterBackoff
from redis.exceptions import LockError, NoScriptError
from redis.retry import Retry

REDIS_URL = "redis://localhost:6379"

def fmtseconds(seconds: Union[int, float], unit="microseconds") -> str:
    return humanize.naturaldelta(timedelta(seconds=seconds), minimum_unit=unit)

class ORJSONDecoder:
    def __init__(self, **kwargs):
        self.options = kwargs
    def decode(self, obj):
        return orjson.loads(obj)

class ORJSONEncoder:
    def __init__(self, **kwargs):
        self.options = kwargs
    def encode(self, obj):
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

class EvelinaLock(Lock):
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
        super().__init__(redis, name, max_lock_ttl, sleep, blocking, blocking_timeout, thread_local)

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

class EvelinaRedis(Redis):
    def __init__(self, *a, **ka):
        self._locks_created: Dict[Union[str, bytes, memoryview], EvelinaLock] = {}
        self._namespace = tuuid.tuuid()
        self.rl_prefix = "rl:"
        self.is_ratelimited = self.ratelimited
        self._closing = False
        super().__init__(*a, **ka)

    def json(self):
        return super().json(ORJSONEncoder(), ORJSONDecoder())

    @property
    def held_locks(self):
        return [{name: lock} for name, lock in self._locks_created.items() if lock.locked()]

    @property
    def locks(self):
        return self._locks_created

    def __repr__(self):
        return f"{self.__class__.__name__} {self._namespace} <{self.connection_pool!r}>"

    async def close(self) -> None:
        if self._closing:
            return
        self._closing = True
        try:
            for lock in self._locks_created.values():
                if lock.locked():
                    await lock.release()
            self._locks_created.clear()
            await asyncio.shield(super().close())
        except Exception as e:
            log.error(f"Error closing Redis connection: {e}")
        finally:
            self._closing = False

    async def jsonset(self, key, data: dict, **ka):
        return await self._json.set(key, ".", data, **ka)

    async def jsonget(self, key):
        return await self._json.get(key)

    async def jsondelete(self, key):
        return await self._json.delete(key)

    async def getstr(self, key):
        value = await self.get(key)
        if value is None:
            return None
        return value.decode("utf-8") if isinstance(value, bytes) else str(value)

    @classmethod
    async def from_url(cls, url=REDIS_URL, retry="jitter", attempts=100, timeout=120, **ka):
        retry_form = Retry(backoff=EqualJitterBackoff(3, 1), retries=attempts)
        pool = BlockingConnectionPool.from_url(url, timeout=timeout, max_connections=7000, retry=retry_form, **ka)
        instance = cls(connection_pool=pool)
        log.warning(f"New Redis! {url}: timeout: {timeout} retry: {retry} attempts: {attempts}")
        ping_time = 0
        async with Timeout(9):
            for _ in range(5):
                start = time()
                await instance.ping()
                ping_time += time() - start
        avg = ping_time / 5
        log.success(f"Connected. 5 pings latency: {fmtseconds(avg)}")
        return instance

    def rl_key(self, ident) -> str:
        return f"{self.rl_prefix}{xxh3_64_hexdigest(ident)}"

    async def ratelimited(self, resource_ident: str, request_limit: int, timespan: int = 60, increment=1) -> bool:
        rlkey = f"{self.rl_prefix}{xxh3_64_hexdigest(resource_ident)}"
        try:
            current_usage = await self.evalsha(INCREMENT_SCRIPT_HASH, 1, rlkey, timespan, increment)
        except NoScriptError:
            current_usage = await self.eval(INCREMENT_SCRIPT, 1, rlkey, timespan, increment)
        if int(current_usage) > request_limit:
            return True
        return False