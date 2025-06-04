from redis.asyncio import StrictRedis
import ujson


class Red(StrictRedis):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def ladd(self, key: str, *values: str, **kwargs):
        values = list(values)
        for index, value in enumerate(values):
            if type(value) in (dict, list, tuple):
                values[index] = ujson.dumps(value)

        result = await super().sadd(key, *values)
        if kwargs.get("ex"):
            await super().expire(key, kwargs.get("ex"))

        return result

    async def lget(self, key: str):
        _values = await super().smembers(key)

        values = list()
        for value in _values:
            try:
                value = ujson.loads(value)
            except ujson.JSONDecodeError:
                pass

            values.append(value)

        return values
