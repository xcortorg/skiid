from contextlib import suppress
from datetime import datetime
from enum import Enum
from logging import getLogger
from typing import List, Optional

from aiohttp import ClientSession, ClientTimeout, ContentTypeError, CookieJar
from cashews import cache
from discord import Color
from discord.ext.commands import CommandError
from pydantic import BaseModel, Field

from main import swag
from tools import dominant_color

import config


log = getLogger("swag/gram")


class ExpiredCookie(Exception):
    pass


class ExpiredStory(Exception):
    pass


class InstagramError(CommandError):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class MediaType(Enum):
    PHOTO = 1
    VIDEO = 2
    ALBUM = 8
    NONE = 0


class Media(BaseModel):
    url: str
    media_type: MediaType
    expires: Optional[int] = None

    @property
    def ext(self) -> str:
        return {
            MediaType.PHOTO: "jpg",
            MediaType.VIDEO: "mp4",
            MediaType.PHOTO: "jpg",
        }[self.media_type]

    @cache(ttl="30m")
    async def color(self) -> Color:
        log.debug("Requesting color for %r.", self.url)

        async with ClientSession(timeout=ClientTimeout(total=5)) as client:
            with suppress(Exception):
                async with client.get(self.url) as response:
                    buffer = await response.read()
                    return await dominant_color(buffer)  # type: ignore

            return Color.default()

    async def buffer(self) -> bytes:
        async with ClientSession() as session:
            async with session.request("GET", self.url) as resp:
                return await resp.read()


class User(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    biography: Optional[str] = None
    avatar_url: str
    is_private: bool = False
    is_verified: bool = False
    post_count: int = 0
    following_count: int = 0
    follower_count: int = 0

    def __str__(self) -> str:
        return self.username

    @property
    def url(self) -> str:
        return f"https://www.instagram.com/{self.username}/"

    @cache(ttl="2h")
    async def color(self) -> Color:
        log.debug("Requesting color for %r.", self.username)

        async with ClientSession(timeout=ClientTimeout(total=5)) as client:
            with suppress(Exception):
                async with client.get(self.url) as response:
                    buffer = await response.read()
                    return await dominant_color(buffer)  # type: ignore

            return Color.default()


class Post(BaseModel):
    id: Optional[str] = Field(None)
    url: str
    user: User
    media: List[Media] = []
    created_at: datetime
    caption: Optional[str] = None


class InstagramIdCodec:
    ENCODING_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

    @staticmethod
    def encode(num, alphabet=ENCODING_CHARS):
        """Covert a numeric value to a shortcode."""

        num = int(num)
        if num == 0:
            return alphabet[0]
        arr = []
        base = len(alphabet)
        while num:
            rem = num % base
            num //= base
            arr.append(alphabet[rem])
        arr.reverse()
        return "".join(arr)

    @staticmethod
    def decode(shortcode, alphabet=ENCODING_CHARS):
        """Covert a shortcode to a numeric value."""

        base = len(alphabet)
        strlen = len(shortcode)
        return sum(
            alphabet.index(char) * base ** (strlen - (idx + 1))
            for idx, char in enumerate(shortcode)
        )


class Instagram:
    def __init__(self, bot: swag):
        self.bot: swag = bot
        self.jar = CookieJar(unsafe=True)
        self.session = ClientSession(
            cookie_jar=self.jar, timeout=ClientTimeout(total=5)
        )

        self.proxy = None
        self.proxy_auth = None

    @property
    def color(self):
        return int("ce0071", 16)

    async def close(self):
        await self.session.close()

    @staticmethod
    def parse_media(resource):
        resource_media_type = MediaType(int(resource["media_type"]))
        if resource_media_type == MediaType.PHOTO:
            res = resource["image_versions2"]["candidates"][0]
            return Media(url=res["url"], media_type=resource_media_type)

        elif resource_media_type == MediaType.VIDEO:
            res = resource["video_versions"][0]
            return Media(url=res["url"], media_type=resource_media_type)

        return Media(url="", media_type=resource_media_type)

    async def graphql_request(self, shortcode: str):
        log.debug("Requesting GraphQL data for %r.", shortcode)

        url = "https://www.instagram.com/graphql/query/"
        params = {
            "query_hash": "9f8827793ef34641b2fb195d4d41151c",
            "variables": '{"shortcode": "'
            + shortcode
            + '", "child_comment_count": 3, "fetch_comment_count": 40, '
            + '"parent_comment_count": 24, "has_threaded_comments": "true"}',
        }
        headers = {
            "Host": "www.instagram.com",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:104.0) Gecko/20100101 Firefox/104.0",
            "Accept": "*/*",
            "Accept-Language": "en,en-US;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Instagram-AJAX": "1006292718",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "198387",
            "X-IG-WWW-Claim": "0",
            "X-Requested-With": "XMLHttpRequest",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://www.instagram.com/p/Ci3_9mnrK9z/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "TE": "trailers",
            "Cookie": config.Authorization.INSTAGRAM.GRAPHQL[0],
        }
        async with self.session.get(url, headers=headers, params=params) as response:
            try:
                data = await response.json()
            except ContentTypeError as exc:
                if response.status == 404:
                    raise InstagramError("") from exc

                raise ExpiredCookie from exc

            if data["status"] != "ok":
                log.warning("[HTTP %s] %s", response.status, data.get("message"))
                raise InstagramError(
                    f"Instagram returned an exception (`{response.status}`)"
                )

        return data

    async def v1_api_request(self, endpoint: str, params: Optional[dict] = None):
        log.debug("Requesting v1 API data with endpoint %r %s.", endpoint, params)

        headers = {
            "Cookie": config.Authorization.INSTAGRAM.GRAPHQL[0],
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:104.0) Gecko/20100101 Firefox/104.0",
            "Accept": "*/*",
            "Accept-Language": "en,en-US;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Instagram-AJAX": "1006164448",
            "X-IG-App-ID": "936619743392459",
            "X-ASBD-ID": "198387",
            "Origin": "https://www.instagram.com",
            "DNT": "1",
            "Connection": "keep-alive",
            "Referer": "https://www.instagram.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "Pragma": "no-cache",
            "Cache-Control": "no-cache",
            "TE": "trailers",
        }
        base_url = "https://i.instagram.com/api/v1/"
        async with self.session.get(
            base_url + endpoint, headers=headers, params=params
        ) as response:
            try:
                data = await response.json()
            except ContentTypeError as exc:
                if response.status == 404:
                    if endpoint == "users/web_profile_info/":
                        if params:
                            raise InstagramError(
                                f"User `{params['username']}` was not found!"
                            )

                raise ExpiredCookie from exc

            if data["status"] != "ok":
                log.warning("[HTTP %s] %s", response.status, data.get("message"))
                raise InstagramError(
                    f"Instagram returned an exception (`{response.status}`)"
                )

        return data

    async def get_stories(self, username: str) -> List[Post]:
        log.debug("Requesting stories for %r.", username)

        user = await self.get_user(username)
        data = await self.v1_api_request(f"feed/user/{user.id}/story")
        if not data["reel"]:
            return []

        stories = data["reel"]["items"]
        return [
            Post(
                id=story["pk"],
                url=f"https://www.instagram.com/stories/{username}/{story['pk']}",
                user=user,
                media=[self.parse_media(story)],
                created_at=story["taken_at"],
            )
            for story in stories
        ]

    async def get_story(self, username: str, story_pk: str) -> Post:
        log.debug("Requesting story %r from %r.", story_pk, username)

        user = await self.get_user(username)
        data = await self.v1_api_request("feed/reels_media/", {"reel_ids": user.id})
        stories = data["reels"][user.id]["items"]
        try:
            story = next(filter(lambda x: x["pk"] == story_pk, stories))
        except StopIteration as exc:
            raise ExpiredStory from exc

        return Post(
            url=f"https://www.instagram.com/stories/{username}/{story_pk}",
            user=user,
            media=[self.parse_media(story)],
            created_at=story["taken_at"],
        )  # type: ignore

    async def get_user(self, username: str) -> User:
        log.debug("Requesting user %r.", username)

        data = await self.v1_api_request(
            "users/web_profile_info/",
            params={"username": username},
        )
        user = data["data"]["user"]
        if not user:
            raise InstagramError(f"{username} is not a valid Instagram username.")

        return User(
            id=user["id"],
            username=user["username"],
            full_name=user["full_name"],
            biography=user["biography"],
            avatar_url=user["profile_pic_url"],
            is_private=user["is_private"],
            is_verified=user["is_verified"],
            post_count=user["edge_owner_to_timeline_media"]["count"],
            follower_count=user["edge_followed_by"]["count"],
            following_count=user["edge_follow"]["count"],
        )

    async def get_post(self, shortcode: str) -> Post:  # type: ignore
        try:
            media_id = InstagramIdCodec.decode(shortcode[:11])
        except ValueError as exc:
            raise InstagramError("The shortcode is invalid") from exc

        data = await self.v1_api_request(f"media/{media_id}/info/")
        data = data["items"][0]

        resources = []
        media_type = MediaType(int(data["media_type"]))
        if media_type == MediaType.ALBUM:
            resources.extend(iter(data["carousel_media"]))
        else:
            resources = [data]

        media = [self.parse_media(resource) for resource in resources]
        user = data["user"]

        return Post(
            url=f"https://www.instagram.com/p/{shortcode}",
            user=User(
                id=user["pk"],
                username=user["username"],
                full_name=user["full_name"],
                avatar_url=user["profile_pic_url"],
            ),
            media=media,
            created_at=data["taken_at"],
            caption=data["caption"]["text"] if data.get("caption") else None,
        )  # type: ignore

    async def get_post(self, shortcode: str) -> Post:
        data = await self.graphql_request(shortcode)
        data = data["data"]["shortcode_media"]
        mediatype = to_mediatype(data["__typename"])
        user = data["owner"]

        media = []
        if mediatype == MediaType.ALBUM:
            for node in data["edge_sidecar_to_children"]["edges"]:
                node = node["node"]
                node_mediatype = to_mediatype(node["__typename"])
                display_url = node["display_resources"][-1]["src"]
                media.append(Media(url=display_url, media_type=node_mediatype))
        else:
            display_url = data["display_resources"][-1]["src"]
            media.append(Media(url=display_url, media_type=mediatype))

        return Post(
            url=f"https://www.instagram.com/p/{shortcode}",
            user=User(
                id=user["id"],
                username=user["username"],
                full_name=user["full_name"],
                avatar_url=user["profile_pic_url"],
                is_private=user["is_private"],
                is_verified=user["is_verified"],
                post_count=user["edge_owner_to_timeline_media"]["count"],
                follower_count=user["edge_followed_by"]["count"],
            ),
            media=media,
            created_at=data["taken_at_timestamp"],
        )  # type: ignore


def to_mediatype(typename: str) -> MediaType:
    match typename:
        case "GraphVideo":
            return MediaType.VIDEO
        case "GraphImage":
            return MediaType.PHOTO
        case "GraphSidecar":
            return MediaType.ALBUM
        case _:
            return MediaType.NONE


def get_best_candidate(
    candidates: list[dict],
    og_width: Optional[int] = None,
    og_height: Optional[int] = None,
) -> str:
    if og_height and og_width:
        best = next(
            filter(
                lambda img: img["width"] == og_width and img["height"] == og_height,
                candidates,
            )
        )
    else:
        best = sorted(
            candidates,
            key=lambda img: img["width"] * img["height"],
            reverse=True,
        )[0]

    return best["url"]
