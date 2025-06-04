from typing import Any, Optional, Tuple, Union  # type: ignore

from discord.ext.commands import AutoShardedBot  # type: ignore
from tools.important.services.TikTok import (TikTokClient,  # type: ignore
                                             User, UserFeed, Video)
from typing_extensions import Self  # type: ignore

TikTokObject = Optional[Union[User, UserFeed, Video, Tuple[Video, Any]]]


class MediaHandler:
    def __init__(self: Self, bot: AutoShardedBot):
        self.bot = bot
        self._tiktok = TikTokClient(
            [
                "M0ZhoJVNBUzMsS6kaMGSMblq1qLxJLdK1iSzkK8wX5-F7T77f7J_B6LIfEUXGREuhv75wfVZRh9nPHtFZWJp5EECoilXuhF5xaiIqAFQhhM="
            ],
            1,
            5,
        )
        self.initialized = False

    async def initialize(self: Self):
        await self._tiktok.setup()

    async def tiktok(self: Self, type: int, **kwargs) -> TikTokObject:
        if not self.initialized:
            await self.initialize()
        if type == 1:
            return await self._tiktok.get_user(**kwargs)
        elif type == 2:
            return await self._tiktok.get_user_feed(**kwargs)
        elif type == 3:
            return await self._tiktok.get_video(**kwargs)
        else:
            return None
