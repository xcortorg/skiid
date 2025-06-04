import asyncio  # type: ignore
from dataclasses import dataclass as dc
from typing import Optional

import orjson
from aiofiles import open as async_open
from discord.ext.commands import CommandError
from fast_string_match import closest_match_distance as cmd
from loguru import logger


def log(message: str):
    logger.info(message)
    print(message)


@dc
class ColorResult:
    hex: str  # type: ignore
    name: Optional[str] = None
    url: Optional[str] = None


class ColorPicker:
    def __init__(self, colordb_path: Optional[str] = "/root/allcolors.json"):
        self.colordb_path = colordb_path
        self.colors = None

    async def setup(self):
        async with async_open(self.colordb_path, "rb") as file:
            colors = orjson.loads(await file.read())
        self.colors = colors

    async def search(self, query: str) -> Optional[ColorResult]:
        if self.colors is None:
            log("Color DB Not loaded... loading now...")
            await self.setup()
            log("Color DB Loaded, now finding color match!")
        keys = list(self.colors.keys())
        if match := cmd(query, keys):
            result = ColorResult(
                hex=self.colors.get(match),
                name=match,
                url=f"https://color-name.com/hex/{self.colors.get(match).strip('#')}",
            )
        else:
            del keys
            raise CommandError(f"Couldn't find a color under the name `{query}")
        del keys
        return result


async def test():
    color = ColorPicker("allcolors.json")
    from tools import timeit

    async with timeit() as timer:
        search = await color.search("purp")
        log(search)
    log(f"Took {timer.elapsed} seconds")
    return search


asyncio.run(test())
