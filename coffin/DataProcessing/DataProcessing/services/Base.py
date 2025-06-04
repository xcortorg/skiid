"""
Author: cop-discord
Email: cop@catgir.ls
Discord: aiohttp
"""

import functools
from asyncio import ensure_future
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, get_type_hints

import orjson
from loguru import logger
from redis.asyncio import Redis
from xxhash import xxh3_64_hexdigest as hash_


@dataclass
class Statistics:
    name: str
    status: bool
    queries: int
    failed: int
    succeeded: int
    last_query: str


def cache():
    """
    A decorator to cache coroutine results in Redis for class methods.
    It generates a cache key using the function name, class name, and kwargs.
    If a value exists in Redis for the function's name and kwargs, it returns the cached value.
    Otherwise, it executes the coroutine, caches the result, and returns it.
    If you supply cached=False to any cached coroutine it will not get the cached result
    but instead return a fresh result and cache the fresh result
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs) -> Any:
            self.status = True
            redis_client = self.redis
            val = f"{self.__class__.__name__}.{func.__name__}-{'-'.join(str(m) for m in args)}{orjson.dumps(kwargs, option=orjson.OPT_SORT_KEYS)}"
            key = hash_(val)
            logger.info(f"{val}\n{key}")
            if redis_client:
                if kwargs.pop("cached", True) is not False:
                    type_hints = get_type_hints(func)
                    return_type = type_hints.get("return", None)
                    if cached_value := await redis_client.get(key):
                        if isinstance(cached_value, bytes):
                            data = orjson.loads(cached_value)
                        else:
                            data = cached_value
                        data["cached"] = True
                        self.status = False
                        if return_type:
                            return return_type(**data)
                        else:
                            return data

            self.last_query = kwargs.get("query")
            self.queries += 1

            try:
                result = await func(self, *args, **kwargs)
                if redis_client:
                    if self.ttl:
                        ensure_future(
                            redis_client.set(
                                key,
                                (
                                    orjson.dumps(result.dict())
                                    if not isinstance(result, (bytes, dict, list))
                                    else result
                                ),
                                ex=self.ttl,
                            )
                        )
                    else:
                        ensure_future(
                            redis_client.set(
                                key,
                                (
                                    orjson.dumps(result.dict())
                                    if not isinstance(result, (bytes, dict, list))
                                    else result
                                ),
                            )
                        )
                self.succeeded += 1
                self.status = False
            except Exception as error:
                self.failed += 1
                self.status = False
                raise error

            return result

        return wrapper

    return decorator


class BaseService:
    name: str
    status: Optional[bool] = False
    queries: Optional[int] = 0
    failed: Optional[int] = 0
    succeeded: Optional[int] = 0
    last_query: Optional[str] = "No Last Query"

    def __init__(
        self: "BaseService", name: str, redis: Redis, ttl: Optional[int] = None
    ):
        self.name = name
        self.redis = redis
        self.ttl = ttl

    def __repr__(self: "BaseService") -> str:
        return f"<{self.name.title()} state={self.status} succeeded={self.succeeded} failed={self.failed} last_query={self.last_query}>"

    @property
    def statistics(self: "BaseService") -> Statistics:
        return Statistics(
            name=self.name,
            status=self.status,
            queries=self.queries,
            failed=self.failed,
            succeeded=self.succeeded,
            last_query=self.last_query,
        )
