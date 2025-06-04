import inspect
import re
from dataclasses import dataclass as dc
from typing import Optional

import discord
import orjson
from aiofiles import open as async_open
from discord import Color
from discord.ext.commands import Context
from discord.ext.commands.converter import Converter
from discord.ext.commands.errors import BadColorArgument, CommandError
from fast_string_match import closest_match_distance as cmd
from loguru import logger


def log(message: str):
    logger.info(message)
    print(message)


@dc
class ColorResult:
    hex: str
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

    async def search_hex(self, hex_: str) -> Optional[ColorResult]:
        if self.colors is None:
            log("Color DB Not loaded... loading now...")
            await self.setup()
            log("Color DB Loaded, now finding color match!")
        keys = list(self.colors.values())
        if match := cmd(hex_, keys):  # noqa: F841
            match_ = {
                k: v for k, v in self.colors.items() if v == hex_ or v == f"#{hex_}"
            }
            for k, v in match_:
                _hex = k
                name = v
                break
            result = ColorResult(
                hex=_hex, name=name, url=f"https://color-name.com/hex/{_hex.strip('#')}"
            )
        else:
            del keys
            raise CommandError(f"Couldn't find a color under the hex code `{hex}")
        del keys
        return result


class ColorConverter(Converter[Color]):
    async def convert(self, ctx: Context, argument: str):
        if argument == "black":
            argument = "010101"
        if hex_match := re.match(r"#?[a-f0-9]{6}", argument.lower()):  # noqa: F841
            return f"0x{argument.lower().strip('#')}"
        if not hasattr(ctx.bot, "colorpicker"):
            ctx.bot.colorpicker = ColorPicker()
            await ctx.bot.colorpicker.setup()
        if match := await ctx.bot.colorpicker.search(argument):
            if self.as_object is True:
                return match
            else:
                return Color.from_str(match.hex)
        try:
            is_method = False
            arg = argument.lower().replace(" ", "_")
            method = getattr(Color, arg, None)
            if (
                arg.startswith("from_")
                or method is None
                or not inspect.ismethod(method)
            ):
                is_method = False
            else:
                is_method = True
            if is_method is True:
                return method()
        except Exception:
            pass
        raise BadColorArgument(argument)


discord.ext.commands.converter.ColourConverter = ColorConverter
