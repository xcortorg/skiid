from io import BytesIO
from typing import Optional
from yarl import URL
from discord import File, Message, Embed
from pydantic import BaseModel, Field
from cogs.social.reposters.base import Reposter
from cogs.social.reposters.extraction import download

from tools.client import Context
from main import greed


class SoundCloud(BaseModel):
    url: URL = Field(..., description="SoundCloud URL")
    title: str
    thumbnail: Optional[str]
    duration: int
    uploader: str
    uploader_url: URL
    description: str

    class Config:
        arbitrary_types_allowed = True

class SoundCloudReposter(Reposter):
    def __init__(self, bot: greed, **kwargs):
        super().__init__(
            bot,
            **kwargs,
            name="SoundCloud",
            regex=[
                r"https?://(?:www\.)?soundcloud\.com/[\w\d-]+/[\w\d-]+/?\??",
                r"https?://(?:www\.)?soundcloud\.com/[\w\d-]+/[\w\d-]+/likes/?\??",
                r"https?://(?:www\.)?soundcloud\.app\.goo\.gl/[\w\d-]+/?\??",
            ],
        )
    async def extract(self, url: URL) -> SoundCloud:
        return await download(url)

    async def dispatch(
        self, 
        ctx: Context, 
        data: SoundCloud, 
        buffer: BytesIO
    ) -> None:
        message = ctx.message
        soundcloud = data

        async with self.bot.session.get(str(soundcloud.url)) as response:
            buffer.write(await response.read())

        buffer.seek(0)

        await message.channel.send(
            embed=Embed(
                description=
                    f"**{soundcloud.title}**\n"
                    f"Uploaded by: ({soundcloud.uploader})[{soundcloud.uploader_url}]\n"
                    f"Duration: {soundcloud.duration} seconds\n"
                    f"{soundcloud.description}"
            ),
            file=File(buffer, filename=f"{soundcloud.title}.mp3")
        )
        