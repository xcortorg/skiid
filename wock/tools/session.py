from typing import Optional

from aiohttp import ClientSession
from typing_extensions import Self


class Session:
    def __init__(self, proxy: Optional[str] = None):
        self.proxy = proxy
        self.session = None

    async def get(self: Self, url: str, check: Optional[bool] = True)