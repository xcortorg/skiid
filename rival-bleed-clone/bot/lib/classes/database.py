from __future__ import annotations

import loguru
import asyncio
import glob
from logging import getLogger
from types import TracebackType
from typing import Any, Optional, Protocol, Union
from typing import Iterable, Sequence
import ujson
import json
from asyncpg import Connection, Pool, Record as DefaultRecord, create_pool
from discord.ext.commands import Context, check

logger = getLogger(__name__)
log = loguru.logger


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
    async def __aenter__(self) -> Connection:
        ...

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        ...


class Database:
    def __init__(self):
        self.uri: str = "postgres://postgres:FuckYou1266216121251275127512752171@localhost:5432/bot"
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
    
    def create_database(self, database: str, username: str, password: str, host: str, port: int):
        import psycopg2
        conn = psycopg2.connect(
            dbname='postgres', user=username, password=password, host=host, port=port
        )
        conn.autocommit = True  # Allow immediate execution of CREATE DATABASE
        
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {database};")
            logger.info(f"Database '{database}' created successfully.")
            with open("var/migrations.sql", "r") as file:
                cursor.execute(file.read())
        conn.close()
        return True

    async def connect(self) -> Pool:
        string, database_name = self.uri.replace("postgres://", "").split("/")
        auth, data = string.split("@")
        username, password = auth.split(":")
        host, port = data.split(":")
        try:
            self.pool = await self.create()
        except Exception:
            await asyncio.to_thread(self.create_database, database_name, username, password, host, int(port))
            self.pool = await self.create()
        await self.execute("""CREATE EXTENSION IF NOT EXISTS timescaledb;""")
        return self.pool

    async def close(self) -> None:
        if not self.pool:
            return
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
        args = [json.dumps(a) if isinstance(a, dict) else a for a in args]
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
            
    async def migrate(self):
        if await self.fetchval("""SELECT count(*) FROM pokemon.users""") > 10:
            logger.info(f"No migrations needed... returning!")
            return
        sql_files = sorted(glob.glob('var/migration_*.sql'), key=lambda x: int(x.split('_')[-1].split('.')[0]))
        migration = ""
        for sql_file in sql_files:
            with open(sql_file, 'r', encoding='utf-8') as f:
                migration += f.read()
        with open("var/migrations.sql", "w") as f:
            f.write(migration)
        return True

    async def executemany(self, sql: str, args: Iterable[Sequence]) -> Optional[Any]:
        if result := self.cache.get(f"{sql} {args}"):  # noqa: F841
            self.cache.pop(f"{sql} {args}")
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