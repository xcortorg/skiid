from __future__ import annotations

from datetime import datetime
from re import findall
from typing import List, Optional

from pydantic import BaseModel
from typing_extensions import Self
from xxhash import xxh32_hexdigest

from cogs.social.models.instagram import ClientSession

HASHTAG_PATTERN = r"(?<=[\s>])#(\d*[A-Za-z_]+\d*)\b(?!;)"
USERNAME_PATTERN = (
    r"@([A-Za-z0-9_](?:(?:[A-Za-z0-9_]|(?:\\.(?!\\.))){0,28}(?:[A-Za-z0-9_]))?)"
)


class PartialPost(BaseModel):
    shortcode: str
    caption: Optional[str] = None
    comments: int
    likes: int
    thumbnail_url: str
    created_at: datetime

    @property
    def id(self) -> str:
        return self.shortcode

    @property
    def url(self) -> str:
        return f"https://www.instagram.com/p/{self.shortcode}/"

    @classmethod
    def parse(cls, data: dict) -> PartialPost:
        return cls(
            shortcode=data["shortcode"],
            caption=data["edge_media_to_caption"]["edges"][0]["node"]["text"]
            if data["edge_media_to_caption"]["edges"]
            else None,
            comments=data["edge_media_to_comment"]["count"],
            likes=data["edge_liked_by"]["count"],
            thumbnail_url=data["display_url"],
            created_at=datetime.fromtimestamp(data["taken_at_timestamp"]),
        )


class PostAuthor(BaseModel):
    id: str
    username: str
    full_name: str
    avatar_url: str
    is_verified: bool

    @property
    def url(self) -> str:
        return f"https://www.instagram.com/{self.username}/"


class PostItem(BaseModel):
    type: str
    url: str
    thumbnail_url: Optional[str] = None

    @property
    def extension(self) -> str:
        return "jpg" if self.type == "image" else "mp4"

    @property
    def id(self) -> str:
        return f"Instagram{xxh32_hexdigest(self.url)}"

    async def buffer(self) -> bytes:
        async with ClientSession() as session:
            async with session.request("GET", self.url) as resp:
                return await resp.read()


class PostLocation(BaseModel):
    id: str
    name: str
    city: Optional[str]


class Post(PartialPost):
    author: PostAuthor
    location: Optional[PostLocation]
    media: List[PostItem] = []
    likes: int
    is_edited: bool
    hashtags: List[str] = []
    mentions: List[str] = []

    @classmethod
    async def fetch(cls, shortcode: str) -> Optional[Self]:
        async with ClientSession() as session:
            async with session.request(
                "GET",
                f"https://www.instagram.com/p/{shortcode}/",
                params={
                    "__a": 1,
                    "__d": "dis",
                },
            ) as response:
                if not response.ok:
                    return None

                data = await response.json()
                data = data["items"][0]

                post = cls(
                    shortcode=data["code"],
                    comments=data["comment_count"],
                    likes=data["like_count"],
                    is_edited=data["caption_is_edited"],
                    thumbnail_url=data["image_versions2"]["candidates"][0]["url"],
                    created_at=datetime.fromtimestamp(data["taken_at"]),
                    author=PostAuthor(
                        id=data["user"]["pk"],
                        username=data["user"]["username"],
                        full_name=data["user"]["full_name"],
                        avatar_url=data["user"]["hd_profile_pic_url_info"]["url"],
                        is_verified=data["user"]["is_verified"],
                    ),
                    location=PostLocation(
                        id=data["location"]["pk"],
                        name=data["location"]["name"],
                        city=data["location"]["city"],
                    )
                    if data.get("location")
                    else None,
                )
                if caption := data.get("caption"):
                    post.caption = caption["text"]
                    post.hashtags = findall(HASHTAG_PATTERN, caption["text"])
                    post.mentions = findall(USERNAME_PATTERN, caption["text"])

                if media := data.get("carousel_media"):
                    for item in media:
                        if item["media_type"] == 1:
                            post.media.append(
                                PostItem(
                                    type="image",
                                    url=item["image_versions2"]["candidates"][0]["url"],
                                )
                            )
                        elif item["media_type"] == 2:
                            post.media.append(
                                PostItem(
                                    type="video",
                                    url=item["video_versions"][0]["url"],
                                    thumbnail_url=item["image_versions2"]["candidates"][
                                        0
                                    ]["url"],
                                )
                            )

                elif data["media_type"] == 1:
                    post.media.append(
                        PostItem(
                            type="image",
                            url=data["image_versions2"]["candidates"][0]["url"],
                        )
                    )

                elif data["media_type"] == 2:
                    post.media.append(
                        PostItem(
                            type="video",
                            url=data["video_versions"][0]["url"],
                            thumbnail_url=data["image_versions2"]["candidates"][0][
                                "url"
                            ],
                        )
                    )

                return post
