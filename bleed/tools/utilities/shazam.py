# wock
from asyncio import create_subprocess_shell as shell
from asyncio.subprocess import PIPE
from dataclasses import dataclass
from os import remove

from aiofiles import open as async_open
from aiohttp import ClientSession
from loguru import logger
from shazamio import Shazam as ShazamClient
from tuuid import tuuid


@dataclass
class Track:
    song: str
    artist: str
    metadata: list
    cover_art: str
    url: str


class Recognizer:
    def __init__(self):
        self.session = None
        self.client = ShazamClient()

    async def get_bytes(self, url: str) -> bytes:
        if self.session is None:
            self.session = ClientSession()
        async with self.session.get(url) as response:
            data = await response.read()
        return data

    async def get_audio(self, file: str):
        process = await shell(
            f"ffmpeg -i {file} -q:a 0 -map a {file.split('.')[0]}.mp3", stdout=PIPE
        )
        await process.communicate()
        f = f"{file.split('.')[0]}.mp3"
        async with async_open(f, "rb") as ff:
            data = await ff.read()
        remove(file)
        remove(f)
        return data

    async def recognize(self, url: str):
        if ".mp3" not in url:
            extension = url.split("/")[-1].split(".")[1].split("?")[0]
            file = f"/root/{tuuid()}.{extension}"
            async with async_open(file, "wb") as ff:
                await ff.write(await self.get_bytes(url))
            bytes_ = await self.get_audio(file)
        else:
            if self.session is None:
                self.session = ClientSession()
            async with self.session.get(url) as r:
                if r.status == 200:
                    bytes_ = await r.read()
                else:
                    return None
        file = bytes_
        try:
            data = await self.client.recognize(file)
            #            logger.info(data)
            track = data["track"]
        except (IndexError, KeyError):
            return None
        return Track(
            track["title"],
            track["subtitle"],
            track["sections"][0]["metadata"],
            track["images"]["coverart"],
            track["url"],
        )
