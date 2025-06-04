from aiohttp import ClientSession
from discord import File
from typing import Optional, Union

TOKEN = ""


class Images:
    @staticmethod
    async def get(action: str, as_bytes: Optional[bool] = True) -> Union[bytes, str]:
        async with ClientSession() as session:
            async with session.get(
                f"https://api.otakugifs.xyz/gif?reaction={action}"
            ) as response:
                #            async with session.get(f"https://kawaii.red/api/gif/{action.lower()}?token={TOKEN}") as response:
                data = await response.json()
                data = data["url"]
                if as_bytes:
                    async with session.get(data) as response:
                        data = await response.read()
        return data
