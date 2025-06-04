from aiohttp import ClientSession
from shazamio import Shazam
from loguru import logger
from dataclasses import dataclass, asdict
from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE
from io import BytesIO
from tool.worker import offloaded


@dataclass
class Track:
    song: str
    artist: str
    metadata: list
    cover_art: str
    url: str

    def to_dict(self):
        return asdict(self)


@offloaded
def process_audio(audio_bytes: bytes, is_mp3: bool) -> bytes:
    if not is_mp3:
        import ffmpeg

        input_buffer = BytesIO(audio_bytes)
        output_buffer = BytesIO()

        stream = ffmpeg.input("pipe:", format="mp4")
        stream = ffmpeg.output(stream, "pipe:", format="mp3", acodec="libmp3lame", q=0)
        stdout, _ = ffmpeg.run(stream, input=input_buffer.read(), capture_stdout=True)
        return stdout
    return audio_bytes


@offloaded
async def get_bytes(self, url: str) -> bytes:
    async with Recognizer().session.get(url) as response:
        return await response.read()


@offloaded
async def recognize_track(data_bytes: bytes) -> dict:
    shazam = Shazam()
    try:
        data = await shazam.recognize(data_bytes)
        track = data["track"]
        track_info = Track(
            song=track["title"],
            artist=track["subtitle"],
            metadata=track["sections"][0]["metadata"],
            cover_art=track["images"]["coverart"],
            url=track["url"],
        )
        return track_info.to_dict()
    except (IndexError, KeyError):
        return None


class Recognizer:
    def __init__(self):
        self.session = ClientSession()

    async def recognize(self, url: str):
        is_mp3 = url.endswith(".mp3")
        bytes_ = await self.get_bytes(url)
        p = await process_audio(bytes_, is_mp3)
        return await recognize_track(p)

    async def close(self):
        await self.session.close()
