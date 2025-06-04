from pydantic import BaseModel
from typing import Optional
from aiohttp import ClientSession
from lxml import html


class Meta(BaseModel):
    steam2id: str
    steam2id_new: str
    steam3id: str
    steam64id: int
    steamid: int
    communityvisibilitystate: int
    profilestate: int
    personaname: str
    commentpermission: int
    profileUrl: str
    avatar: Optional[str] = (
        "https://avatars.steamstatic.com/b5bd56c1aa4644a474a2e4972be27ef9e82e517e_full.jpg"
    )
    avatarmedium: Optional[str] = (
        "https://avatars.steamstatic.com/b5bd56c1aa4644a474a2e4972be27ef9e82e517e_full.jpg"
    )
    avatarfull: Optional[str] = (
        "https://avatars.steamstatic.com/b5bd56c1aa4644a474a2e4972be27ef9e82e517e_full.jpg"
    )
    avatarhash: Optional[str] = None
    personastate: int
    primaryclanid: int
    timecreated: int
    personastateflags: int
    loccountrycode: str


class Player(BaseModel):
    meta: Meta
    id: int
    avatar: Optional[str] = (
        "https://avatars.steamstatic.com/b5bd56c1aa4644a474a2e4972be27ef9e82e517e_full.jpg"
    )
    username: str
    bio: Optional[str] = "No information given."


class Data(BaseModel):
    player: Player


class Steam(BaseModel):
    code: str
    message: str
    data: Data
    success: bool

    @classmethod
    async def from_username(cls, username: str):
        async with ClientSession() as session:
            async with session.get(
                f"https://playerdb.co/api/player/steam/{username}"
            ) as response1:
                if response1.status != 200:
                    raise TypeError()
                data = await response1.json()
                _ = cls(**data)
            async with session.get(data.data.meta.profileUrl) as response2:
                tree = html.fromstring(await response2.text())
                bio = tree.xpath(
                    '//*[@id="responsive_page_template_content"]/div/div[1]/div/div/div/div[4]/div[3]/text()'
                )
                bio = bio[0] if len(bio) > 0 else "No information given."
                _.data.bio = bio
        return _
