from __future__ import annotations

import loguru
import asyncio
from logging import getLogger
from types import TracebackType
from typing import Any, Optional, Protocol, Union
from typing import Iterable, Sequence
import ujson, orjson
from asyncpg import Connection, Pool, Record as DefaultRecord, create_pool
from discord.ext.commands import Context, check

logger = getLogger(__name__)
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
        self.uri: str = (
            "postgres://postgres:admin@localhost:5432/greed"
        )
        self.pool: Optional[Pool] = None
        self.cache = {}

    def encoder(self, *data: Any):
        return ujson.dumps(data[1] if len(data) > 1 else data[0])

    def decoder(self, *data: Any):
        return ujson.loads(data[1] if len(data) > 1 else data[0])

    def encoderb(self, *data: Any):
        return orjson.dumps(data[1] if len(data) > 1 else data[0])

    def decoderb(self, *data: Any):
        return orjson.loads(data[1] if len(data) > 1 else data[0])

    async def settings(self, connection: Connection) -> None:
        await connection.set_type_codec(
            "json",
            encoder=self.encoder,
            decoder=self.decoder,
            schema="pg_catalog",
        )
        await connection.set_type_codec(
            "jsonb",
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

    async def execute_sql_file(self, file_path: str = "greed.sql") -> None:
        if not self.pool:
            raise RuntimeError(
                "Database connection pool is not initialized. Call 'connect()' first."
            )

        async with self.pool.acquire() as connection:
            await self.settings(connection)
            with open(file_path, "r") as file:
                sql = file.read()

            try:
                await connection.execute(sql)
                log.info(f"Executed SQL file {file_path} successfully.")
            except Exception as e:
                log.error(f"An error occurred while executing the SQL file: {e}")

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
        if "poke " not in sql.lower():
            if "economy" not in sql.lower():
                self.cache[f"{type} {sql} {args}"] = data

    async def search_and_delete(self, table: str):
        for k in self.cache.keys():
            if table.lower() in k.lower():
                self.cache.pop(k)

    async def fetch(self, sql: str, *args, **kwargs):
        cached = kwargs.get("cached", True)
        if cached:
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

    async def fetchrow(self, sql: str, *args, **kwargs):
        cached = kwargs.get("cached", True)
        if cached:
            if result := self.cache.get(f"fetchrow {sql} {args}"):
                return result
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                data = await conn.fetchrow(sql, *args)
                await self.add_to_cache(data, "fetchrow", sql, args)
                return data

    async def fetchval(self, sql: str, *args, **kwargs):
        cached = kwargs.get("cached", True)
        if cached:
            if result := self.cache.get(f"fetchval {sql} {args}"):
                return result
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                data = await conn.fetchval(sql, *args)
                await self.add_to_cache(data, "fetchval", sql, args)
                return data

    async def execute(self, sql: str, *args, **kwargs) -> Optional[Any]:
        if "DELETE" in sql and "giveaways" in sql:
            logger.info(f"executing query {sql} with {args}")
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
        cache_key = f"{sql} {args}"
        if cache_key in self.cache:
            self.cache.pop(cache_key)
        async with self.pool.acquire() as conn:
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

    async def fetch_config(self, guild_id: int, key: str):
        return await self.fetchval(
            f"SELECT {key} FROM reskin_config WHERE guild_id = $1", guild_id
        )

    async def update_config(self, guild_id: int, key: str, value: str):
        await self.execute(
            f"INSERT INTO reskin_config (guild_id, {key}) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET {key} = $2",
            guild_id,
            value,
        )
        return await self.fetchrow(
            f"SELECT * FROM reskin_config WHERE guild_id = $1", guild_id
        )
