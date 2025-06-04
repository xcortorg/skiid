from io import BytesIO
from typing import Optional, Union, Any
from PIL import Image
from aiohttp import ClientSession
from os import remove, path
from tuuid import tuuid
from asyncio import create_subprocess_shell as shell, sleep, ensure_future, Lock
from asyncio.subprocess import PIPE
from discord import File, Embed
from discord.ext.commands import Context, CommandError
from collections import defaultdict
from lib.worker import offloaded


@offloaded
def read_file(fp: str, mode: str) -> Union[str, bytes]:
    with open(fp, mode) as file:
        return file.read()


@offloaded
def write_file(fp: str, mode: str, data: Union[str, bytes], **kwargs: Any):
    with open(fp, mode, **kwargs) as file:
        file.write(data)
    return fp


def convert_to_hhmmss(total_seconds: int) -> str:
    # Calculate hours, minutes, and seconds
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60

    # Format the output as HH:MM:SS
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def format_time(total_seconds: int) -> str:
    return convert_to_hhmmss(total_seconds)


class GIF:
    def __init__(
        self, command: Optional[str] = "ffmpeg", discord: Optional[bool] = True
    ):
        self.command = command
        self.discord = discord
        self.locks = defaultdict(Lock)

    async def download(self, url: str) -> str:
        async with self.locks["download"]:
            async with ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.read()
            filepath = f"{tuuid()}.mp4"
            await write_file(filepath, "wb", data)
        return filepath

    async def delete_soon(self, fp: str):
        async def do_delete(fp: str):
            await sleep(10)
            remove(fp)

        ensure_future(do_delete(fp))
        return True

    async def convert(self, fp: str, kwargs: Any) -> Union[File, str]:
        fps = kwargs.pop("fps", 10)
        async with self.locks["conversion"]:
            if not path.exists(fp):
                raise ValueError("File doesn't exist..")
            new = f"{tuuid()}.gif"
            optional = ""
            ff = ""
            if quality := kwargs.pop("quality", None):
                optional += f",crf={quality}"
            if fast_forward := kwargs.pop("fast_forward", None):
                ff += f"-ss {format_time(fast_forward)}"
            process = await shell(
                f"{self.command} -i {fp} -vf 'fps={fps},scale=320:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse{optional}' -loop 0 {ff} {new}"
            )
            await process.communicate()
            remove(fp)
        if self.discord is True:
            return File(new)
        else:
            await self.delete_soon(new)
            return new

    async def do_conversion(self, ctx: Context, url: str, **kwargs: Any):
        filepath = await self.download(url)
        converted = await self.convert(filepath, **kwargs)
        await ctx.success(
            "heres your **gif**..",
            file=converted,
        )
        remove(converted.filename)
        return
