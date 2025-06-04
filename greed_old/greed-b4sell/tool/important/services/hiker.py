from dataclasses import dataclass
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, AnyUrl
import aiohttp
import arrow
import orjson
import discord
import humanize
from typing import List
from logging import getLogger

logger = getLogger(__name__)
PROXY_URL = None
PROXY_USER = None
PROXY_PASS = None
# key="1tmDAlqo05E639f573UeP3PvzPyWTJdx"
key = "87FFdm4qaGyO7ZPyeerzdHglfGMilRHG"
IG_COOKIE = "63019138462:2O2Cob2mGTNAZl:10:AYdzVrgdqiGG0GwBD-YOD69_frZd9_q0YZK1fg9R_A"


class UserResponse(BaseModel):
    pk: str = Field(..., title="Pk")
    username: str = Field(..., title="Username")
    full_name: str = Field(..., title="Full Name")
    is_private: bool = Field(..., title="Is Private")
    profile_pic_url: AnyUrl = Field(..., title="Profile Pic Url")
    profile_pic_url_hd: Optional[AnyUrl] = Field(None, title="Profile Pic Url Hd")
    is_verified: bool = Field(..., title="Is Verified")
    media_count: int = Field(..., title="Media Count")
    follower_count: int = Field(..., title="Follower Count")
    following_count: int = Field(..., title="Following Count")
    biography: Optional[str] = Field("", title="Biography")
    external_url: Optional[str] = Field(None, title="External Url")
    account_type: Optional[int] = Field(None, title="Account Type")
    is_business: bool = Field(..., title="Is Business")
    public_email: Optional[str] = Field(None, title="Public Email")
    contact_phone_number: Optional[str] = Field(None, title="Contact Phone Number")
    public_phone_country_code: Optional[str] = Field(
        None, title="Public Phone Country Code"
    )
    public_phone_number: Optional[str] = Field(None, title="Public Phone Number")
    business_contact_method: Optional[str] = Field(
        None, title="Business Contact Method"
    )
    business_category_name: Optional[str] = Field(None, title="Business Category Name")
    category_name: Optional[str] = Field(None, title="Category Name")
    category: Optional[str] = Field(None, title="Category")
    address_street: Optional[str] = Field(None, title="Address Street")
    city_id: Optional[str] = Field(None, title="City Id")
    city_name: Optional[str] = Field(None, title="City Name")
    latitude: Optional[float] = Field(None, title="Latitude")
    longitude: Optional[float] = Field(None, title="Longitude")
    zip: Optional[str] = Field(None, title="Zip")
    instagram_location_id: Optional[str] = Field(None, title="Instagram Location Id")
    interop_messaging_user_fbid: Optional[str] = Field(
        None, title="Interop Messaging User Fbid"
    )

    def format(self, text):
        if " thousand" in text:
            text = text.replace(" thousand", "k")
        if " million" in text:
            text = text.replace(" million", "m")
        return text

    def make_embed(self, ctx) -> discord.Embed:
        embed = discord.Embed(
            title=f"{self.full_name} (@{self.username}) ",
            url=f"https://instagram.com/{self.username}",
            description=f"{self.biography}",
            color=int("ce0071", 16),
        ).set_author(
            name=ctx.author.display_name if ctx.author.nick else str(ctx.author),
            icon_url=ctx.author.display_avatar,
        )
        embed.set_thumbnail(url=f"{self.profile_pic_url}")
        embed.add_field(
            name="Posts",
            value=f"{self.format(humanize.intword(self.media_count))}",
            inline=True,
        )
        embed.add_field(
            name="Followers",
            value=f"{self.format(humanize.intword(self.follower_count))}",
            inline=True,
        )
        embed.add_field(
            name="Following",
            value=f"{self.format(humanize.intword(self.following_count))}",
            inline=True,
        )
        embed.set_footer(
            icon_url="https://rival.rocks/instagram.png",
            text="Instagram | Powered by Rival API",
        )
        return embed

    # https://www.designpieces.com/wp-content/uploads/2016/05/Instagram-v051916-150x150.png

    @classmethod
    async def from_url(cls, ctx, username: str):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.hikerapi.com/v1/user/by/username?username={username}",
                headers={
                    "accept": "application/json",
                    "x-access-key": "87FFdm4qaGyO7ZPyeerzdHglfGMilRHG",
                },
            ) as r:
                return cls.parse_raw(await r.read())


class ExpiredCookie(Exception):
    pass


class ExpiredStory(Exception):
    pass


class InstagramError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(message)


class MediaType(Enum):
    PHOTO = 1
    VIDEO = 2
    ALBUM = 8
    NONE = 0


@dataclass
class IgMedia:
    media_type: MediaType
    url: str


@dataclass
class IgUser:
    id: int
    username: str
    avatar_url: str
    full_name: str = None


@dataclass
class IgPost:
    user: IgUser
    media: List[IgMedia]
    timestamp: int
    likes: int = None
    comments: int = None
    caption: str = None


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
        num = 0
        idx = 0
        for char in shortcode:
            power = strlen - (idx + 1)
            num += alphabet.index(char) * (base**power)
            idx += 1
        return num


class Datalama:
    BASE_URL = "https://api.hikerapi.com"

    def __init__(self, bot):
        self.bot = bot

    async def api_request(self, endpoint: str, params: dict) -> dict:
        headers = {
            "accept": "application/json",
            "x-access-key": key,
        }
        async with self.bot.session.get(
            self.BASE_URL + endpoint, params=params, headers=headers
        ) as response:
            data = await response.json()
            if (
                response.status != 200
                or data.get("exc_type") is not None
                or data.get("detail") is not None
            ):
                raise InstagramError(
                    f"ERROR {response.status} | {data.get('exc_type')} | {data.get('detail')}"
                )
            return data

    async def get_post(
        self, shortcode: Optional[str] = None, url: Optional[str] = None
    ) -> IgPost:
        # 		if data := await self.bot.redis.get(
        if url is not None:
            if data := await self.bot.redis.get(url):
                data = data
            else:
                data = await self.api_request("v1/media/by/url", {"url": url})
                await self.bot.redis.set(url, orjson.dumps(data))
        else:
            if data := await self.bot.redis.get(shortcode):
                data = data
            else:
                data = await self.api_request("/v1/media/by/code", {"code": shortcode})
                await self.bot.redis.set(shortcode, orjson.dumps(data))
        media = []
        post_media_type = MediaType(data["media_type"])

        if post_media_type == MediaType.ALBUM:
            for resource in data["resources"]:
                resource_media_type = MediaType(resource["media_type"])
                if resource_media_type == MediaType.PHOTO:
                    display_url = resource["image_versions"][0]["url"]
                elif resource_media_type == MediaType.VIDEO:
                    display_url = resource["video_url"]
                else:
                    display_url = ""
                media.append(IgMedia(resource_media_type, display_url))
        elif post_media_type == MediaType.VIDEO:
            media.append(IgMedia(post_media_type, data["video_url"]))
        else:
            media.append(IgMedia(post_media_type, data["image_versions"][0]["url"]))

        user = data["user"]
        user = IgUser(
            user["pk"], user["username"], user["profile_pic_url"], user["full_name"]
        )

        try:
            timestamp = int(arrow.get(data["taken_at"]).timestamp())
        except Exception:
            ts = arrow.get(data["taken_at"]).datetime
            timestamp = ts.timestamp()
        if not data.get("comment_count"):
            comments = 0
        else:
            comments = data["comment_count"]
        if not data.get("like_count"):
            likes = 0
        else:
            likes = data["like_count"]
        if not data.get("caption_text"):
            caption = None
        else:
            caption = data["caption_text"]

        return IgPost(user, media, timestamp, comments, likes, caption)

    async def get_story(self, story_pk: str) -> IgPost:
        data = await self.api_request("/v1/story/by/id", {"id": story_pk})

        media = []
        post_media_type = MediaType(data["media_type"])

        if post_media_type == MediaType.VIDEO:
            media.append(IgMedia(post_media_type, data["video_url"]))
        else:
            media.append(IgMedia(post_media_type, data["thumbnail_url"]))

        user = data["user"]
        user = IgUser(
            user["pk"], user["username"], user["profile_pic_url"], user["full_name"]
        )
        try:
            timestamp = int(arrow.get(data["taken_at"]).timestamp())
        except Exception:
            ts = arrow.get(data["taken_at"]).datetime
            timestamp = ts.timestamp()
        if not data.get("comment_count"):
            comments = 0
        else:
            comments = data["comment_count"]
        if not data.get("like_count"):
            likes = 0
        else:
            likes = data["like_count"]
        if not data.get("caption_text"):
            caption = None
        else:
            caption = data["caption_text"]

        return IgPost(user, media, timestamp, comments, likes, caption)


class Instagram:
    def __init__(
        self,
        bot,
        use_proxy: bool = False,
    ):
        self.bot = bot
        self.jar = aiohttp.CookieJar(unsafe=True)
        self.session = aiohttp.ClientSession(cookie_jar=self.jar)

        proxy_url = PROXY_URL
        proxy_user = PROXY_USER
        proxy_pass = PROXY_PASS

        if use_proxy:
            self.proxy = proxy_url
            self.proxy_auth = aiohttp.BasicAuth(proxy_user, proxy_pass)
        else:
            self.proxy = None
            self.proxy_auth = None

    @property
    def emoji(self):
        return "<:ig:949073464638201856>"

    @property
    def color(self):
        return int("ce0071", 16)

    async def close(self):
        await self.session.close()
        logger.info("closed")

    def parse_media(self, resource):
        resource_media_type = MediaType(int(resource["media_type"]))
        if resource_media_type == MediaType.PHOTO:
            res = resource["image_versions2"]["candidates"][0]
            return IgMedia(resource_media_type, res["url"])
        elif resource_media_type == MediaType.VIDEO:
            res = resource["video_versions"][0]
            return IgMedia(resource_media_type, res["url"])
        else:
            return IgMedia(resource_media_type, "")

    async def graphql_request(self, shortcode: str):
        url = "https://www.instagram.com/graphql/query/"
        params = {
            "query_hash": "9f8827793ef34641b2fb195d4d41151c",
            "variables": '{"shortcode": "'
            + shortcode
            + '", "child_comment_count": 3, "fetch_comment_count": 40, "parent_comment_count": 24, "has_threaded_comments": "true"}',
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
            "Cookie": IG_COOKIE,
        }
        async with self.session.get(
            url,
            headers=headers,
            proxy=self.proxy,
            params=params,
            proxy_auth=self.proxy_auth,
        ) as response:
            try:
                data = await response.json(loads=orjson.loads)
            except aiohttp.ContentTypeError:
                raise ExpiredCookie

            if data["status"] != "ok":
                raise InstagramError(f'[HTTP {response.status}] {data.get("message")}')

        return data

    async def v1_api_request(self, endpoint: str, params: Optional[dict] = None):
        headers = {
            "Cookie": IG_COOKIE,
            "Host": "i.instagram.com",
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
            base_url + endpoint,
            headers=headers,
            proxy=self.proxy,
            params=params,
            proxy_auth=self.proxy_auth,
        ) as response:
            try:
                data = await response.json(loads=orjson.loads)
            except aiohttp.ContentTypeError:
                logger.info("Expired Cookie")
                raise ExpiredCookie
            if data["status"] != "ok":
                raise InstagramError(data.get("message"))
        return data

    async def get_story(self, username: str, story_pk: str) -> IgPost:
        user = await self.get_user(username)
        data = await self.v1_api_request("feed/reels_media/", {"reel_ids": user.id})
        stories = data["reels"][user.id]["items"]
        try:
            story = next(filter(lambda x: x["pk"] == story_pk, stories))
        except StopIteration:
            raise ExpiredStory

        return IgPost(
            user,
            [self.parse_media(story)],
            story["taken_at"],
            data["comment_count"],
            data["like_count"],
            data["caption_text"],
        )

    async def get_user(self, username) -> IgUser:
        data = await self.v1_api_request(
            "users/web_profile_info/", {"username": username}
        )
        user = data["data"]["user"]
        return IgUser(
            user["id"], user["username"], user["profile_pic_url"], data["full_name"]
        )

    async def get_post(self, shortcode: str) -> IgPost:
        """Extract all media from given Instagram post"""
        try:
            real_media_id = InstagramIdCodec.decode(shortcode[:11])
        except ValueError:
            raise InstagramError("Not a valid Instagram link")

        data = await self.v1_api_request(f"media/{real_media_id}/info/")
        data = data["items"][0]

        resources = []
        media = []

        media_type = MediaType(int(data["media_type"]))
        if media_type == MediaType.ALBUM:
            for carousel_media in data["carousel_media"]:
                resources.append(carousel_media)
        else:
            resources = [data]

        for resource in resources:
            media.append(self.parse_media(resource))

        timestamp = data["taken_at"]
        user = data["user"]
        user = IgUser(
            user["pk"], user["username"], user["profile_pic_url"], user["full_name"]
        )
        logger.info(data)
        return IgPost(
            user,
            media,
            timestamp,
            data["comment_count"],
            data["like_count"],
            data["caption_text"],
        )

    async def get_post_graphql(self, shortcode: str) -> IgPost:
        data = await self.graphql_request(shortcode)
        data = data["data"]["shortcode_media"]
        mediatype = to_mediatype(data["__typename"])

        media = []
        if mediatype == MediaType.ALBUM:
            for node in data["edge_sidecar_to_children"]["edges"]:
                node = node["node"]
                node_mediatype = to_mediatype(node["__typename"])
                display_url = node["display_resources"][-1]["src"]
                media.append(IgMedia(node_mediatype, display_url))
        else:
            display_url = data["display_resources"][-1]["src"]
            media.append(IgMedia(mediatype, display_url))

        timestamp = data["taken_at_timestamp"]
        user = data["owner"]
        user = IgUser(
            user["id"], user["username"], user["profile_pic_url"], user["full_name"]
        )
        logger.info(data)
        return IgPost(
            user,
            media,
            timestamp,
            data["comment_count"],
            data["like_count"],
            data["caption_text"],
        )


def to_mediatype(typename: str):
    if typename == "GraphVideo":
        return MediaType.VIDEO
    if typename == "GraphImage":
        return MediaType.PHOTO
    if typename == "GraphSidecar":
        return MediaType.ALBUM
    else:
        return MediaType.NONE
