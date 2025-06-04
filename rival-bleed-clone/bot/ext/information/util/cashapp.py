import re
import json

from aiohttp import ClientSession
from pydantic import BaseModel
from typing import List, Optional, Any


class Avatar(BaseModel):
    image_url: Optional[str] = None
    initial: Optional[str] = None
    accent_color: Optional[str] = None


class CashAppProfile(BaseModel):
    display_name: str
    formatted_cashtag: str
    is_verified_account: bool
    rate_plan: str
    payment_button_type: str
    country_code: str
    avatar: Optional[Avatar] = None

    @classmethod
    async def from_cashtag(cls, cashtag: str):
        cashtag = cashtag.replace("$", "")
        async with ClientSession() as session:
            async with session.get(f"https://cash.app/${cashtag}") as response:
                if response.status != 200:
                    raise TypeError()
                data = await response.text()
        pattern = r"var profile = ({.*?});"
        match = re.search(pattern, data, re.DOTALL)
        match = json.loads(match.group(1))
        return cls(**match)
