from __future__ import annotations

from datetime import datetime
from json import dumps
from logging import getLogger
from typing import List, Optional

from cashews import cache
from discord.ext.commands import CommandError
from pydantic import BaseModel
from typing_extensions import Self

from cogs.social.models.instagram import ClientSession
from tools.client import Context

from .post import PartialPost

log = getLogger("swag/gram")


def validate(username: str) -> str:
    username = username.removeprefix("@").replace("'b", "").replace("'", "").lower()
    if len(username) > 30:
        raise CommandError("Username must be less than **30 characters**!")

    if username.endswith("."):
        raise CommandError("Username cannot end with a **period**!")

    for character in username:
        if not character.isalnum() and character not in ("_", "."):
            raise CommandError("Username does not appear to be valid!")

    return username


class StoryItem(BaseModel):
    id: int
    url: str
    ext: str
    is_video: bool
    created_at: datetime
    user: "User"

    @property
    def caption(self) -> Optional[str]:
        return None

    @property
    def extension(self) -> str:
        return self.ext

    async def buffer(self) -> bytes:
        async with ClientSession() as session:
            async with session.request("GET", self.url) as resp:
                return await resp.read()


class User(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    biography: Optional[str]
    avatar_url: str
    post_count: Optional[int] = 0
    follower_count: Optional[int] = 0
    following_count: Optional[int] = 0
    is_private: Optional[bool] = False
    is_verified: Optional[bool] = False
    posts: List[PartialPost] = []

    def __str__(self) -> str:
        return self.full_name or self.username

    @property
    def url(self) -> str:
        return f"https://www.instagram.com/{self.username}/"

    @classmethod
    def parse(cls, data: dict) -> Self:
        return cls(
            id=data["id"],
            username=data["username"],
            full_name=data["full_name"],
            biography=data["biography"],
            avatar_url=data["profile_pic_url_hd"],
            post_count=data["edge_owner_to_timeline_media"]["count"],
            follower_count=data["edge_followed_by"]["count"],
            following_count=data["edge_follow"]["count"],
            is_private=data["is_private"],
            is_verified=data["is_verified"],
        )

    @classmethod
    @cache(ttl="5m")
    async def fetch(cls, username: str) -> Optional[Self]:
        username = validate(username)
        async with ClientSession() as session:
            async with session.request(
                "GET",
                f"https://www.instagram.com/{username}/",
                params={
                    "__a": 1,
                    "__d": "dis",
                },
            ) as response:
                if not response.ok:
                    if response.status == 401:
                        log.warning(
                            "Instagram revoked our credentials, please update cookies!"
                        )

                    return None

                data = await response.json()
                print(data)
                if "graphql" not in data:
                    log.debug(
                        "Instagram returned invalid data: %s", dumps(data, indent=4)
                    )
                    return None

                data = data["graphql"]["user"]

                user = cls.parse(data)
                if not user.is_private:
                    user.posts = [
                        PartialPost.parse(post["node"])
                        for post in data["edge_owner_to_timeline_media"]["edges"]
                    ]

                return user

    @classmethod
    @cache(ttl="5m")
    async def stories(cls, user_id: int) -> List[StoryItem]:
        async with ClientSession() as session:
            async with session.request(
                "POST",
                "https://www.instagram.com/graphql/query/",
                json={
                    "query_hash": "c9c56db64beb4c9dea2d17740d0259d9",
                    "variables": dumps(
                        {
                            "reel_ids": [user_id],
                            "precomposed_overlay": False,
                            "show_story_viewer_list": True,
                            "story_viewer_fetch_count": 50,
                            "story_viewer_cursor": "",
                        }
                    ),
                },
            ) as response:
                if not response.ok:
                    return []

                data = await response.json()
                reels = data["data"]["reels_media"]
                if not reels:
                    return []

                data = reels[0]["items"]

                items: List[StoryItem] = []
                for item in data:
                    ext = "mp4" if item["is_video"] else "jpg"
                    items.append(
                        StoryItem(
                            id=item["id"],
                            url=item["display_url"]
                            if not item["is_video"]
                            else item["video_resources"][0]["src"],
                            ext=ext,
                            is_video=item["is_video"],
                            created_at=datetime.fromtimestamp(
                                item["taken_at_timestamp"]
                            ),
                            user=cls(
                                **item["owner"],
                                avatar_url=item["owner"]["profile_pic_url"],
                            ),
                        )
                    )

                return items

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        async with ctx.typing():
            if user := await cls.fetch(argument):
                return user

        raise CommandError("No **Instagram user** found with that name!")


StoryItem.update_forward_refs()
