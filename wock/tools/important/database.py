from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any, Iterable, Optional, Protocol, Sequence, Union

import loguru
import ujson
from asyncpg import Connection, Pool
from asyncpg import Record as DefaultRecord
from asyncpg import create_pool
from discord.ext.commands import Context, check

log: loguru.logger = loguru.logger


def query_limit(table: str, limit: int = 5):
    async def predicate(ctx: Context):
        check = await ctx.bot.db.fetchval(
            f"SELECT COUNT(*) FROM {table} WHERE guild_id = $1", ctx.guild.id
        )
        if check == limit:
            await ctx.fail(f"You cannot create more than **{limit}** {table}s")
            return False
        return True

    return check(predicate)


class Record(DefaultRecord):
    def __getattr__(self: "Record", name: Union[str, Any]) -> Any:
        attr: Any = self[name]
        return attr

    def __dict__(self: "Record") -> dict[str, Any]:
        return dict(self)


class ConnectionContextManager(Protocol):
    async def __aenter__(self) -> Connection: ...

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None: ...


class Database:
    def __init__(self):
        self.uri: str = "postgres://postgres:artist@localhost:5432/wockdata"
        self.pool: Optional[Pool] = None
        self.cache = {}

    def encoder(self, *data: Any):
        return ujson.dumps(data[1])

    def decoder(self, *data: Any):
        return ujson.loads(data[1])

    async def settings(self, connection: Connection) -> None:
        await connection.set_type_codec(
            "json",
            encoder=self.encoder,
            decoder=self.decoder,
            schema="pg_catalog",
        )

    async def create(self) -> Pool:
        pool: Pool = await create_pool(
            dsn=self.uri, init=self.settings, record_class=Record
        )
        log.info(f"Initialized database connection {pool.__hash__()}")
        return pool

    async def connect(self) -> Pool:
        self.pool = await self.create()
        return self.pool

    async def close(self) -> None:
        if self.pool:
            await self.pool.close()
            log.info(f"Closed database connection {self.pool.__hash__()}")

    async def delete_cache_entry(self, type: str, sql: str, *args):
        await asyncio.sleep(60)
        try:
            self.cache.pop(f"{type} {sql} {args}")
        except Exception:
            pass

    async def add_to_cache(self, data: Any, type: str, sql: str, *args):
        if "economy" not in sql.lower():
            self.cache[f"{type} {sql} {args}"] = data

    async def search_and_delete(self, table: str):
        for k in self.cache.keys():
            if table.lower() in k.lower():
                self.cache.pop(k)

    async def fetch(self, sql: str, *args):
        if result := self.cache.get(f"fetch {sql} {args}"):
            return result
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                data = await conn.fetch(sql, *args)
                await self.add_to_cache(data, "fetch", sql, args)
                return data

    async def fetchiter(self, sql: str, *args):
        output = await self.fetch(sql, *args)
        for row in output:
            yield row

    async def fetchrow(self, sql: str, *args):
        if result := self.cache.get(f"fetchrow {sql} {args}"):
            return result
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                data = await conn.fetchrow(sql, *args)
                await self.add_to_cache(data, "fetchrow", sql, args)
                return data

    async def fetchval(self, sql: str, *args):
        if result := self.cache.get(f"fetchval {sql} {args}"):
            return result
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                data = await conn.fetchval(sql, *args)
                await self.add_to_cache(data, "fetchval", sql, args)
                return data

    async def execute(self, sql: str, *args) -> Optional[Any]:
        try:
            table = sql.lower().split("from")[1].split("where")[0]
            await self.search_and_delete(table, args)
        except Exception:
            pass
        try:
            if sql.lower().startswith("update"):
                table = sql.lower().split("set")[0].split("update")[1].strip()
                await self.search_and_delete(table, args)
        except Exception:
            pass
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                return await conn.fetchval(sql, *args)

    async def executemany(self, sql: str, args: Iterable[Sequence]) -> Optional[Any]:
        if result := self.cache.get(f"{sql} {args}"):  # noqa: F841
            self.cache.pop(f"{sql} {args}")
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                return await conn.executemany(sql, args)

    async def purge_data(self, column_name: str, value: Any):
        tables = [
            t.table_name
            for t in await self.fetch(
                """SELECT table_name FROM information_schema.columns WHERE table_schema = 'public' AND column_name = $1""",
                column_name,
            )
        ]
        tasks = [
            self.execute(f"""DELETE FROM {t} WHERE {column_name} = $1""", value)
            for t in tables
        ]
        return await asyncio.gather(*tasks)
