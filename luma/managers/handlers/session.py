import sys
from typing import Any

import aiohttp


class Session(aiohttp.ClientSession):
    def __init__(self: "Session", **kwagrs):
        if not kwagrs.get("headers"):
            kwagrs["headers"] = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9147 Chrome/120.0.6099.291 Electron/28.2.10 Safari/537.36"
            }
        super().__init__(
            raise_for_status=True, **kwagrs, timeout=aiohttp.ClientTimeout(total=10)
        )

    async def __do_request(self: "Session", url: str, method: str, **kwargs) -> Any:
        r = await super().request(method, url, **kwargs)

        if r.content_type.startswith(("image/", "video/", "audio/")):
            return await r.read()
        elif r.content_type.startswith("text/"):
            return await r.text()
        elif r.content_type == "application/json":
            return await r.json()

        return r

    async def get(self: "Session", url: str, **kwargs):
        return await self.__do_request(url, sys._getframe().f_code.co_name, **kwargs)
