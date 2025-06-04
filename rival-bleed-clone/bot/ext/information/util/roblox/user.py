import arrow
import orjson
import asyncio

from roblox import Client, UserNotFound
from roblox.thumbnails import AvatarThumbnailType
from roblox.utilities.exceptions import BadRequest
from aiomisc.backoff import asyncretry
from lib.services.cache import cache
from pydantic import BaseModel, Field
from typing import Optional, Any, List
from loguru import logger as log


class BadgeItem(BaseModel):
    id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None


class RobloxUserProfileResponse(BaseModel):
    name: Optional[str] = None
    follower_count: Optional[int] = 0
    following_count: Optional[int] = 0
    friend_count: Optional[int] = 0
    display_name: Optional[str] = None
    description: Optional[str] = None
    presence: Optional[str] = None
    has_verified_badge: Optional[bool] = False
    created: Optional[float] = Field(
        None, description="UTC timestamp of when account was created"
    )
    is_banned: Optional[bool] = False
    id: Optional[int] = None
    last_online: Optional[float] = Field(
        None, description="UTC timestamp of when user last seen online"
    )
    last_location: Optional[str] = None
    avatar_url: Optional[str] = Field(
        None, description="The Roblox user's currently wearing image"
    )
    badges: Optional[List[BadgeItem]] = []
    previous_names: Optional[List[str]] = []


class UserSearchResult(BaseModel):
    user_id: Optional[int] = Field(None, alias="UserId")
    name: Optional[str] = Field(None, alias="Name")
    display_name: Optional[str] = Field(None, alias="DisplayName")
    blurb: Optional[str] = Field(None, alias="Blurb")
    previous_user_names_csv: Optional[str] = Field(None, alias="PreviousUserNamesCsv")
    is_online: Optional[bool] = Field(None, alias="IsOnline")
    last_location: Optional[Any] = Field(None, alias="LastLocation")
    user_profile_page_url: Optional[str] = Field(None, alias="UserProfilePageUrl")
    last_seen_date: Optional[Any] = Field(None, alias="LastSeenDate")
    primary_group: Optional[str] = Field(None, alias="PrimaryGroup")
    primary_group_url: Optional[str] = Field(None, alias="PrimaryGroupUrl")
    has_verified_badge: Optional[bool] = Field(False, alias="HasVerifiedBadge")


class UserSearchResponse(BaseModel):
    names: Optional[List[str]] = []
    keyword: Optional[str] = Field(None, alias="Keyword")
    start_index: Optional[int] = Field(None, alias="StartIndex")
    max_rows: Optional[int] = Field(None, alias="MaxRows")
    total_results: Optional[int] = Field(None, alias="TotalResults")
    user_search_results: Optional[List[UserSearchResult]] = Field(
        None, alias="UserSearchResults"
    )


@cache(ttl="1h", key="robloxuser2:{username}")
async def fetch_roblox_user(username: str):
    client = Client()
    resp = RobloxUserProfileResponse()
    try:
        user = await client.get_user_by_username(username)
    except (UserNotFound, BadRequest):
        return None
    resp.display_name = user.display_name
    resp.description = user.description
    resp.created = user.created
    resp.is_banned = user.is_banned
    resp.id = user.id
    resp.name = user.name
    resp.has_verified_badge = bool(user.__dict__["_data"]["hasVerifiedBadge"])

    @asyncretry(max_tries=2, pause=0.1)
    async def follower():
        resp.follower_count = await user.get_follower_count()

    @asyncretry(max_tries=2, pause=0.1)
    async def friends():
        resp.friend_count = await user.get_friend_count()

    @asyncretry(max_tries=2, pause=0.1)
    async def following():
        resp.following_count = await user.get_following_count()

    @asyncretry(max_tries=2, pause=0.1)
    async def presence():
        presence = await user.get_presence()
        resp.last_online = presence.last_online
        resp.presence = presence.user_presence_type.name
        if resp.presence == "in_game":
            resp.presence = "In game"
        resp.last_location = presence.last_location

    @asyncretry(max_tries=2, pause=0.1)
    async def headshots():
        thumbnails = await client.thumbnails.get_user_avatar_thumbnails(
            users=[user],
            type=AvatarThumbnailType.full_body,
            size=(420, 420),
        )
        resp.avatar_url = thumbnails[0].image_url
        if resp.avatar_url == "https://t3.rbxcdn.com/9fc30fe577bf95e045c9a3d4abaca05d":
            resp.avatar_url = None

    @asyncretry(max_tries=2, pause=0.1)
    async def badges():
        badges = await user.get_roblox_badges()
        resp.badges = []
        for badge in badges:
            resp.badges.append(
                BadgeItem(
                    id=badge.id,
                    name=badge.name,
                    description=badge.description,
                    image_url=badge.image_url,
                )
            )

    async def names():
        try:
            async for name in user.username_history():
                resp.previous_names.append(str(name))
        except BadRequest:
            return log.warning("Bad roblox names request for {}", username)

    await asyncio.gather(
        names(),
        badges(),
        headshots(),
        presence(),
        following(),
        follower(),
    )

    return resp
