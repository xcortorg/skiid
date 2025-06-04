from pydantic import BaseModel
from typing import Optional, Any
from discord.ext.commands import CommandError
from aiohttp import ClientSession
from lib.services.cache import cache


class Meta(BaseModel):
    gamerscore: int
    accountTier: str
    xboxOneRep: Optional[str] = "GoodPlayer"
    preferredColor: str
    realName: Optional[str] = "N/A"
    bio: Optional[str] = "No bio set"
    tenureLevel: int
    watermarks: Optional[str] = None
    location: Optional[str] = "N/A"
    showUserAsAvatar: Optional[int] = None


class Player(BaseModel):
    id: str
    meta: Meta
    username: str
    avatar: Optional[str] = None


class Data(BaseModel):
    player: Player


class XboxResponse(BaseModel):
    code: str
    message: Optional[str] = None
    data: Data
    success: bool

    @classmethod
    async def from_gamertag(cls, gamertag: str):
        async with ClientSession() as session:
            async with session.get(
                f"https://playerdb.co/api/player/xbox/{gamertag}"
            ) as response:
                if response.status != 200:
                    raise CommandError(
                        f"**Xbox's API** returned a `{int(response.status)}` - try again later"
                    )
                data = await response.json()
        return cls(**data)


@cache(ttl=300, key="xbox:{gamertag}")
async def fetch_xbox_profile(gamertag: str):
    return await XboxResponse.from_gamertag(gamertag)
