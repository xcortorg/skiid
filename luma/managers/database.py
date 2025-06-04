from typing import Any, Optional

import aiofiles
from asyncpg import Pool, Record, create_pool


class Record(Record):
    def __getattr__(self, attr: str) -> Any:
        return self.get(attr)


async def setup(pool: Pool) -> Pool:
    async with aiofiles.open("./managers/schema.sql", "r", encoding="UTF-8") as f:
        schema = await f.read()
        await pool.execute(schema)

    return pool


async def connect(**kwargs):
    kwargs["record_class"] = Record

    pool: Optional[Pool] = await create_pool(**kwargs)

    if not pool:
        raise Exception("Could not establish a connection to database")

    return await setup(pool)
