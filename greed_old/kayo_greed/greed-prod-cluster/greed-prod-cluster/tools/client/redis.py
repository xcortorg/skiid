from __future__ import annotations

import time
from contextlib import suppress
from datetime import timedelta
from hashlib import sha1
from json import JSONDecodeError, dumps, loads
from logging import getLogger
from types import TracebackType
from typing import Any, List, Literal, Optional, Union
import urllib.parse

from redis.asyncio import Redis as DefaultRedis
from redis.asyncio.connection import BlockingConnectionPool
from redis.asyncio.lock import Lock
from redis.backoff import EqualJitterBackoff
from redis.exceptions import NoScriptError
from redis.retry import Retry
from redis.typing import AbsExpiryT, EncodableT, ExpiryT, FieldT, KeyT
from xxhash import xxh32_hexdigest

import config

log = getLogger("greed/redis")

password = urllib.parse.quote(config.REDIS.PASS)
REDIS_URL = (
    f"redis://:{password}@{config.REDIS.HOST}:{config.REDIS.PORT}/{config.REDIS.DB}"
)

INCREMENT_SCRIPT = b"""
    local key = KEYS[1]
    local timespan = tonumber(ARGV[1])
    local increment = tonumber(ARGV[2])
    local current = tonumber(redis.call("incrby", key, increment))
    if current == increment then
        redis.call("expire", key, timespan)
    end
    return current
    """

INCREMENT_SCRIPT_HASH = sha1(INCREMENT_SCRIPT).hexdigest()


class Redis(DefaultRedis):
    async def __aenter__(self) -> Redis:
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        log.info("Shutting down the Redis client.")
        await self.close()

    @classmethod
    async def from_url(
        cls,
        url: str = REDIS_URL,
        name: str = "greed",
        attempts: int = 100,
        timeout: int = 120,
        **kwargs,
    ) -> Redis:
        retry = Retry(backoff=EqualJitterBackoff(3, 1), retries=attempts)
        connection_pool = BlockingConnectionPool.from_url(
            url, timeout=timeout, max_connections=100, retry=retry, **kwargs
        )

        client = cls(
            connection_pool=connection_pool,
            auto_close_connection_pool=True,
            retry_on_timeout=True,
            health_check_interval=5,
            client_name=name,
        )

        total_duration = 0
        for _ in range(5):
            start_time = time.perf_counter()
            await client.ping()
            total_duration += time.perf_counter() - start_time

        avg_latency = (total_duration / 5) * 1e6
        log.debug(
            "Established a new Redis client with a %sμs latency.", int(avg_latency)
        )

        return client

    async def set(
        self,
        name: KeyT,
        value: EncodableT | dict | list | Any,
        ex: Optional[ExpiryT] = None,
        px: Optional[ExpiryT] = None,
        nx: bool = False,
        xx: bool = False,
        keepttl: bool = False,
        get: bool = False,
        exat: Optional[AbsExpiryT] = None,
        pxat: Optional[AbsExpiryT] = None,
    ) -> bool | Any:
        if isinstance(value, (dict, list)):
            value = dumps(value)
        return await super().set(
            name,
            value,
            ex=ex,
            px=px,
            nx=nx,
            xx=xx,
            keepttl=keepttl,
            get=get,
            exat=exat,
            pxat=pxat,
        )

    async def get(
        self,
        name: KeyT,
        validate: bool = True,
    ) -> Optional[str | int | dict | list]:
        output = await super().get(name)
        if output is None:
            return None

        if isinstance(output, bytes):
            output = output.decode("utf-8")

        if validate:
            if output.isnumeric():
                return int(output)
            with suppress(JSONDecodeError):
                return loads(output)

        return output

    async def getdel(
        self,
        name: KeyT,
        validate: bool = True,
    ) -> Optional[str | int | dict | list]:
        output = await super().get(name)

        if output is not None:
            await super().delete(name)

            if isinstance(output, bytes):
                output = output.decode("utf-8")

            if validate:
                if isinstance(output, str) and output.isnumeric():
                    return int(output)
                with suppress(JSONDecodeError):
                    return loads(output)

        return output

    async def sadd(
        self,
        name: KeyT,
        *values: str,
        ex: Optional[Union[int, timedelta]] = None,
    ) -> Optional[int]:
        result = await super().sadd(name, *values)
        if ex:
            await super().expire(name, ex)
        return result

    async def srem(
        self,
        name: KeyT,
        *values: str,
    ) -> Optional[int]:
        return await super().srem(name, *values)

    async def sget(self, name: KeyT) -> List[Any]:
        members = await super().smembers(name)
        result = []
        for member in members:
            member = member.decode("utf-8")
            if member.isnumeric():
                result.append(int(member))
            else:
                with suppress(JSONDecodeError):
                    result.append(loads(member))
        return result

    async def sismember(self, name: KeyT, value: str) -> bool:
        return await super().sismember(name, value)

    async def smembers(self, name: KeyT) -> List[str]:
        members = await super().smembers(name)
        return [member.decode("utf-8") for member in members]

    async def rpush(
        self,
        name: KeyT,
        *values: FieldT,
    ) -> int:
        return await super().rpush(name, *values)

    async def ltrim(
        self,
        name: KeyT,
        start: int,
        end: int,
    ) -> bool:
        return await super().ltrim(name, start, end)

    async def llen(self, name: KeyT) -> int:
        return await super().llen(name)

    async def lrange(self, name: KeyT, start: int, end: int) -> List[Any]:
        return await super().lrange(name, start, end)

    async def ratelimited(
        self,
        resource: str,
        limit: int,
        timespan: int = 60,
        increment: int = 1,
    ) -> bool:
        key = f"rl:{xxh32_hexdigest(resource)}"

        try:
            current_usage = await self.evalsha(
                INCREMENT_SCRIPT_HASH,
                1,
                key,
                timespan,
                increment,
            )
        except NoScriptError:
            current_usage = await self.eval(
                INCREMENT_SCRIPT,
                1,
                key,
                timespan,
                increment,
            )

        return int(current_usage) > limit

    def get_lock(
        self,
        name: KeyT,
        timeout: float = 500.0,
        sleep: float = 0.2,
        blocking: bool = True,
        blocking_timeout: Optional[float] = None,
        thread_local: bool = True,
    ) -> Lock:
        name = f"rlock:{xxh32_hexdigest(name)}"
        return self.lock(
            name=name,
            timeout=timeout,
            sleep=sleep,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
            thread_local=thread_local,
        )
