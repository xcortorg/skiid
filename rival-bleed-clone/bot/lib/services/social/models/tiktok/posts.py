import asyncio
from datetime import datetime
from logging import getLogger
from typing import Iterator, List, Literal, Optional, Union
import json
from cashews import cache
from playwright.async_api import Response
from pydantic import BaseModel as BM, Field
from typing_extensions import Self
from loguru import logger
from classes.browser import Controller, PageManager

from .user import BasicUser
cache.setup('mem://')

log = logger

class BaseModel(BM):
    class Config:
        arbitrary_types_allowed = True

class Statistics(BaseModel):
    like_count: int = Field(alias="diggCount")
    comment_count: int = Field(alias="commentCount")
    play_count: int = Field(alias="playCount")
    share_count: int = Field(alias="shareCount")

    def __str__(self) -> str:
        return f"👀 {self.play_count:,} ❤️ {self.like_count:,}"


class Video(BaseModel):
    url: str = Field(alias="downloadAddr")
    width: int = Field(alias="width")
    height: int = Field(alias="height")
    duration: int = Field(alias="duration")


class Post(BaseModel):
    id: int
    author: BasicUser
    caption: Optional[str] = Field(alias="desc", default="..")
    created_at: datetime = Field(alias="createTime")
    statistics: Statistics = Field(alias="stats")
    video: Video

    def __str__(self) -> str:
        return self.caption or ".."

    @property
    def url(self) -> str:
        return f"{self.author.url}/video/{self.id}"


class Posts(BaseModel):
    user: Optional[BasicUser] = None
    posts: List[Post] = []
    responses: Optional[List[Response]] = []

    def __len__(self) -> int:
        return len(self.posts)

    def __iter__(self) -> Iterator[Post]:
        return iter(self.posts)

    def __bool__(self) -> bool:
        return bool(self.user or self.posts)

    @classmethod
    @cache(ttl="5m")
    async def fetch(
        cls,
        browser: "Controller",
        username: str,
    ) -> Union[Optional[Self], Literal[False]]:
        """
        Fetches a user's recent posts.
        """

        responses = []
        # res = cls()
        event = asyncio.Event()
        username = username.strip("@").lower()
        url = f"https://www.tiktok.com/@{username}"
        res = cls()
        async def handle_resp(resp: Response):
            try:
                if event.is_set():
                    return
                responses.append(resp)

                if "/api/post/item_list/" in resp.url:
                    print(resp.url)
                    attempt = 0
                    while True:
                        try:
                            data = await resp.json()
                            if data["statusCode"] != 0:
                                log.debug(
                                    "TikTok API returned an error for @%s / %s.",
                                    username,
                                    data["statusCode"],
                                )
                                return

                            for post in data["itemList"]:
                                if post.get("imagePost") or not post["video"].get("downloadAddr"):
                                    continue

                                try:
                                    res.user = BasicUser(**post["author"])
                                    res.posts.append(Post(**post))
                                except Exception as exc:
                                    log.warning(
                                        "Failed to parse TikTok post %s: %s",
                                        post["id"],
                                        exc,
                                    )
                                    break
                            event.set()
                            break
                        except json.decoder.JSONDecodeError:
                            pass
                            attempt+=1
                        if attempt >= 10:
                            break
            except:
                pass
        async with PageManager(browser) as page:
            try:
                page.page.on("response", handle_resp)
                await page.page.goto(url, timeout = None)
                attempts = 0
                while True:
                    if attempts >= 10:
                        await page.page.screenshot(path = "tiktok.png")
                        break
                    if refresh_button := page.page.get_by_text("Refresh"):
                        await refresh_button.click()
                        await asyncio.sleep(10)
                        await page.page.screenshot(path = "tiktok.png")
                        attempts+=1
            except:
                pass

            finally:
                page.page.remove_listener("response", handle_resp)
        return res

