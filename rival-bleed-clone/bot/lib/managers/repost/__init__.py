import asyncio

from discord import Client, Message
from .reposters import Instagram, TikTok, YouTube
from .reposters.base import Reposter
from typing import List, Union


class RepostManager:
    def __init__(self, bot: Client):
        self.bot = bot
        self.reposters: List[Union[Instagram, TikTok, YouTube]] = [
            Instagram(self.bot),
            TikTok(self.bot),
            YouTube(self.bot),
        ]

    def __str__(self) -> str:
        return "RepostManager"

    def __repr__(self) -> str:
        return f"<RepostManager instagram={self.reposters[0].__repr__()} tiktok={self.reposters[1].__repr__()} youtube={self.reposters[2].__repr__()} tasks={sum(len(i.tasks) for i in self.reposters)} posted={sum(i.posted for i in self.reposters)}>"

    async def repost(self, message: Message):
        return await asyncio.gather(
            *[reposter.repost(message) for reposter in self.reposters]
        )
