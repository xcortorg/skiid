from __future__ import annotations

from datetime import datetime
from logging import getLogger
from typing import List, Optional

from aiohttp import ClientSession
from core.client.context import Context
from discord.ext.commands import CommandError
from pydantic import BaseModel
from typing_extensions import Self

log = getLogger("mono/beatstats")


class Track(BaseModel):
    id: int
    title: str
    plays: int
    created_at: datetime
    artwork_url: Optional[str] = None
    url: str
    user: "User"

    def __str__(self) -> str:
        return self.title

    @property
    def image_url(self) -> str:
        return self.artwork_url or "default_image_url"


class User(BaseModel):
    id: str
    username: str
    permalink: str
    created_at: Optional[datetime]
    track_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    followings_count: Optional[int] = 0
    avatar_url: str
    location: Optional[str] = None
    bio: Optional[str] = None
    social_links: Optional[List[dict]] = None
    plays: Optional[int] = 0

    def __str__(self) -> str:
        return self.username

    @property
    def url(self) -> str:
        return f"https://beatstars.com/{self.permalink}"

    @classmethod
    async def fetch(
        cls,
        session: ClientSession,
        username: str,
    ) -> Optional[Self]:
        user_url = "https://core.prod.beatstars.net/graphql"
        log.debug(f"Fetching user data for username: {username}")

        payload = {
            "operationName": "getMemberProfileByUsername",
            "variables": {"username": username},
            "query": """
                query getMemberProfileByUsername($username: String!) {
                    profileByUsername(username: $username) {
                        ...memberProfileInfo
                        __typename
                    }
                }

                fragment memberProfileInfo on Profile {
                    ...partialProfileInfo
                    location
                    bio
                    tags
                    badges
                    achievements
                    profileInventoryStatsWithUserContents {
                        ...mpGlobalMemberProfileUserContentStatsDefinition
                        __typename
                    }
                    socialInteractions(actions: [LIKE, FOLLOW, REPOST])
                    avatar {
                        assetId
                        fitInUrl(width: 200, height: 200)
                        sizes {
                            small
                            medium
                            large
                            mini
                            __typename
                        }
                        __typename
                    }
                    socialLinks {
                        link
                        network
                        profileName
                        __typename
                    }
                    activities {
                        follow
                        play
                        __typename
                    }
                    __typename
                }

                fragment partialProfileInfo on Profile {
                    displayName
                    username
                    memberId
                    location
                    v2Id
                    avatar {
                        assetId
                        sizes {
                            mini
                            __typename
                        }
                        __typename
                    }
                    __typename
                }

                fragment mpGlobalMemberProfileUserContentStatsDefinition on ProfileInventoryStats {
                    playlists
                    __typename
                }
            """,
        }

        async with session.post(user_url, json=payload) as response:
            log.debug(f"Response status for {username}: {response.status}")
            if response.status == 404:
                log.debug(f"User not found for username: {username} (404 Not Found)")
                return None
            if not response.ok:
                log.debug(
                    f"Failed to fetch user page for {username}: {response.status} - {await response.text()}"
                )
                return None

            json_response = await response.json()
            log.debug(f"API Response: {json_response}")
            if json_response.get("data") and json_response["data"].get(
                "profileByUsername"
            ):
                profile = json_response["data"]["profileByUsername"]
                stats = profile.get("profileInventoryStatsWithUserContents", {})
                social_links = profile.get("socialLinks", [])

                user = cls(
                    id=profile["memberId"],
                    username=profile["displayName"],
                    permalink=profile["username"],
                    created_at=datetime.now(),
                    avatar_url=profile["avatar"]["fitInUrl"],
                    followers_count=profile.get("socialInteractions", {}).get(
                        "FOLLOW", 0
                    ),
                    track_count=stats.get("playlists", 0),
                    location=profile.get("location"),
                    bio=profile.get("bio"),
                    social_links=[
                        {"network": link["network"], "url": link["link"]}
                        for link in social_links
                    ],
                    plays=profile.get("activities", {}).get("play", 0),
                )
                return user
            log.debug("User not found or unexpected response structure.")
            return None

    @classmethod
    async def fetch_followers(
        cls, session: ClientSession, permalink: str
    ) -> Optional[int]:
        followers_url = f"https://main.v2.beatstars.com/musician?permalink={permalink}&fields=profile,user_contents,stats,bulk_deals,social_networks"
        log.debug(f"Fetching followers for user: {permalink}")

        async with session.get(followers_url) as response:
            log.debug(f"Response status for {permalink}: {response.status}")
            if not response.ok:
                log.debug(
                    f"Failed to fetch followers for {permalink}: {response.status} - {await response.text()}"
                )
                return None

            json_response = await response.json()
            log.debug(f"API Response: {json_response}")
            if json_response.get("status") and json_response["response"].get("data"):
                followers_count = json_response["response"]["data"]["stats"].get(
                    "followers", 0
                )
                return followers_count
            log.debug("Unexpected response structure for followers.")
            return None

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> Self:
        async with ctx.typing():
            if user := await cls.fetch(ctx.bot.session, argument):
                return user
        raise CommandError("No **BeatStars user** found with that name!")


Track.update_forward_refs()
