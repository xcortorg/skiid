from aiohttp import ClientSession
from typing import Optional, List, Any
from pydantic import BaseModel


class OutfitThumbnail(BaseModel):
    targetId: int
    state: str
    imageUrl: Optional[str] = None
    version: Optional[str] = None


class OutfitThumbnailResponse(BaseModel):
    data: List[OutfitThumbnail]


class Outfit(BaseModel):
    id: int
    name: str
    isEditable: bool
    outfitType: Optional[Any] = None
    thumbnail: Optional[str] = None


class Outfits(BaseModel):
    filteredCount: int
    data: List[Outfit]
    total: int
    user_id: Optional[int] = None

    @classmethod
    async def from_username(cls, username: str):
        async with ClientSession() as session:
            async with session.request(
                "POST",
                "https://users.roblox.com/v1/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": True},
            ) as response1:
                data1 = await response1.json()
                user_id = data1[0]["id"]
            async with session.get(
                f"https://avatar.roblox.com/v1/users/{user_id}/outfits?page=1&itemsPerPage=100"
            ) as response2:
                data = await response2.read()
        _ = cls.parse_raw(data)
        _.user_id = user_id
        return _

    @classmethod
    async def from_userId(cls, user_id: int):
        async with ClientSession() as session:
            async with session.get(
                f"https://avatar.roblox.com/v1/users/{user_id}/outfits?page=1&itemsPerPage=100"
            ) as response2:
                data = await response2.read()
        _ = cls.parse_raw(data)
        _.user_id = user_id
        return _

    async def fill(
        self: "Outfits",
        format: Optional[str] = "Png",
        isCircular: Optional[bool] = False,
        size: Optional[str] = "420x420",
    ):
        asset_ids = [outfit.id for outfit in self.data]
        async with ClientSession() as session:
            async with session.get(
                "https://thumbnails.roblox.com/v1/users/outfits",
                params={
                    "userOutfitIds": ",".join(asset_ids),
                    "format": format,
                    "isCircular": isCircular,
                    "size": size,
                },
            ) as response:
                data = await response.read()
                outfits = OutfitThumbnailResponse.parse_raw(data)
        for outfit in outfits.data:
            if not (
                outfit_value := next(
                    (item for item in data if item["id"] == outfit.targetId), None
                )
            ):
                continue
            outfit_value.thumbnail = outfit.imageUrl


async def get_outfits(username: str):
    outfits = await Outfits.from_username(username)
    await outfits.fill()
    return outfits
