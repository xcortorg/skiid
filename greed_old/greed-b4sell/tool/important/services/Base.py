"""
Author: cop-discord
Email: cop@catgir.ls
Discord: aiohttp
"""

from xxhash import xxh3_64_hexdigest as hash_
from typing import List, Optional
from redis.asyncio import Redis
from asyncio import ensure_future
from typing import Callable, Any, get_type_hints
import functools
from loguru import logger
import orjson, ujson
from dataclasses import dataclass


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
    """

    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs) -> Any:
            self.status = True
            redis_client = self.redis
            val = f"{self.__class__.__name__}.{func.__name__}-{'-'.join(str(m) for m in args)}{orjson.dumps(kwargs, option=orjson.OPT_SORT_KEYS)}"
            key = hash_(val)

            if redis_client and hasattr(
                redis_client, "get"
            ):  # Verify Redis client is valid
                if kwargs.pop("cached", True) is not False:
                    type_hints = get_type_hints(func)
                    return_type = type_hints.get("return", None)
                    try:
                        cached_value = await redis_client.get(key)
                        if cached_value:
                            try:
                                # Always try to decode bytes first
                                if isinstance(cached_value, bytes):
                                    data = orjson.loads(cached_value)
                                elif isinstance(cached_value, str):
                                    data = ujson.loads(cached_value)
                                elif isinstance(cached_value, (dict, list)):
                                    data = cached_value
                                else:
                                    logger.warning(
                                        f"Unexpected cache value type: {type(cached_value)}"
                                    )
                                    data = None

                                if data and isinstance(data, dict):
                                    data["cached"] = True
                                    self.status = False
                                    if return_type:
                                        try:
                                            return return_type(**data)
                                        except Exception as e:
                                            logger.warning(
                                                f"Failed to construct return type from cached data: {e}"
                                            )
                                            # Clear invalid cache
                                            if hasattr(redis_client, "delete"):
                                                await redis_client.delete(key)
                                    else:
                                        return data

                            except (ValueError, TypeError, AttributeError) as e:
                                logger.warning(f"Failed to parse cached value: {e}")
                                # Clear invalid cache
                                if hasattr(redis_client, "delete"):
                                    await redis_client.delete(key)

                    except Exception as e:
                        logger.error(f"Cache retrieval error: {str(e)}")
                        # Don't re-raise, continue to get fresh data

            self.last_query = kwargs.get("query")
            self.queries += 1

            try:
                result = await func(self, *args, **kwargs)
                if (
                    redis_client and hasattr(redis_client, "set") and result
                ):  # Verify Redis client is valid
                    try:
                        cache_data = None
                        if hasattr(result, "dict"):
                            try:
                                cache_data = result.dict()
                            except Exception as e:
                                logger.warning(f"Failed to convert result to dict: {e}")
                                cache_data = None
                        elif isinstance(result, (dict, list)):
                            cache_data = result

                        if cache_data:
                            try:
                                serialized_data = orjson.dumps(cache_data)
                                if self.ttl:
                                    ensure_future(
                                        redis_client.set(
                                            key, serialized_data, ex=self.ttl
                                        )
                                    )
                                else:
                                    ensure_future(
                                        redis_client.set(key, serialized_data)
                                    )
                            except Exception as e:
                                logger.error(f"Failed to serialize cache data: {e}")

                    except Exception as e:
                        logger.error(f"Failed to cache result: {str(e)}")

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
