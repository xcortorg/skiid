from random import choice
from typing import TYPE_CHECKING

from aiohttp import ClientSession as OriginalClientSession
from aiohttp import ClientTimeout, TCPConnector
from colorama import Fore
from config import Api
from core.tools.logging import logger as log
from yarl import URL

if TYPE_CHECKING:
    from core.Mono import Mono

BASE_URL = URL.build(
    scheme="https",
    host="ws.audioscrobbler.com",
)


class AsyncClient(OriginalClientSession):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, connector=TCPConnector(ssl=False))

    async def get(self, *args, **kwargs):
        kwargs["params"] = {
            "api_key": choice(Api.LASTFM),
            "autocorrect": 1,
            "format": "json",
            **kwargs.get("params", {}),
        }
        log.debug(
            f"GET {Fore.LIGHTMAGENTA_EX}{kwargs['params']['method']}{Fore.RESET} with {Fore.LIGHTRED_EX}{kwargs['params']['api_key']}{Fore.RESET}."
        )

        response = await super().get(*args, **kwargs)
        if response.status == 429:
            log.warning("Last.fm API rate limit exceeded, changing API key...")
            kwargs["api_key"] = choice(Api.LASTFM)
            return await self.get(*args, **kwargs)

        return response


http = AsyncClient(
    headers={
        "User-Agent": "Glo Last.fm Integration (DISCORD BOT)",
    },
    base_url=BASE_URL.human_repr(),
    timeout=ClientTimeout(total=20),
)


async def setup(bot: "Mono") -> None:
    from .lastfm import Lastfm

    await bot.add_cog(Lastfm(bot))
