from .Base import BaseService, cache
from typing import Optional, Union
from aiohttp import ClientSession
from redis.asyncio import Redis
from ..models.Twitter import Tweet, TwitterUser, Tweets
from ..utils import get_random_string
from .._impl.Twitter.twitter import UserNotFound, UserSuspended, TweetNotFound
import random
import re
import json

REQUEST_USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
REQUEST_PLATFORMS = ["Linux", "Windows"]
HEADERS = {
    "Cookie": 'guest_id=v1%3A170966731960022089; kdt=Tn4Yb03uRpenO0Oy23JpkAQzSrXMNUcJhb8B25iJ; auth_token=af412a83297ccc8e3968bf5b3746ce66b1d1b173; ct0=354e229d191f30df9837d933bba2ed9e6ea9f18e234b0737be90f4bbfa5d94b7598670be83ea3abf4f4d3a615135839ad055705230d74f3b71585f0724cc1616c0bc6472662a8f1eb03babf44ed919de; twid=u%3D1798794651178291200; guest_id_marketing=v1%3A170966731960022089; guest_id_ads=v1%3A170966731960022089; lang=en; d_prefs=MjoxLGNvbnNlbnRfdmVyc2lvbjoyLHRleHRfdmVyc2lvbjoxMDAw; personalization_id="v1_2eWvRpEgQDTL1XGiXmMFpg=="',
    "Sec-Ch-Ua": """-Not.A/Brand"";v=""8"", ""Chromium"";v=""102""",
    "X-Twitter-Client-Language": "en",
    "X-Csrf-Token": "354e229d191f30df9837d933bba2ed9e6ea9f18e234b0737be90f4bbfa5d94b7598670be83ea3abf4f4d3a615135839ad055705230d74f3b71585f0724cc1616c0bc6472662a8f1eb03babf44ed919de",
    "Sec-Ch-Ua-Mobile": "?0",
    "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36",
    "X-Twitter-Auth-Type": "OAuth2Session",
    "X-Twitter-Active-User": "yes",
    "Sec-Ch-Ua-Platform": """macOS""",
    "Accept": "*/*",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
    "Referer": "https://twitter.com/markus",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
}


class TwitterService(BaseService):
    def __init__(self: "TwitterService", redis: Redis, ttl: Optional[int] = None):
        self.redis = redis
        self.ttl = ttl
        super().__init__(self.redis, self.ttl)

    @cache()
    async def get_guest_token(self: "TwitterService") -> str:
        async with ClientSession() as session:
            async with session.request(
                "POST", "https://api.x.com/1.1/guest/activate.json", headers=HEADERS
            ) as response:
                data = await response.json()

        return data["guest_token"]

    def get_csrf_token(self: "TwitterService") -> str:
        return get_random_string(32)

    async def fetch_tweet(self: "TwitterService", url: str) -> Tweet:
        try:
            tweet_id = re.search(r"status/(\d+)", url).group(1)
        except AttributeError:
            raise TweetNotFound(url)
        async with ClientSession() as session:
            async with session.get(
                "https://cdn.syndication.twimg.com/tweet-result",
                params={"id": tweet_id, "lang": "en", "token": "4ds4bk3f3r"},
            ) as response:
                data = await response.read()
        return Tweet.parse_raw(data)

    async def fetch_user(
        self: "TwitterService", username: str, raw: Optional[bool] = False
    ) -> Union[TwitterUser, dict]:
        async with ClientSession() as session:
            async with session.get(
                "https://twitter.com/i/api/graphql/mCbpQvZAw6zu_4PvuAUVVQ/UserByScreenName?variables=%7B%22screen_name%22%3A%22"
                + username
                + "%22%2C%22withSafetyModeUserFields%22%3Atrue%2C%22withSuperFollowsUserFields%22%3Atrue%7D",
                headers=HEADERS,
            ) as response:
                if response.status == 404:
                    raise UserNotFound(username)
                data = await response.json()
                if raw:
                    return data
            user = TwitterUser(**data)
        if reason := user.data.user.result.reason:
            if reason == "Suspended":
                raise UserSuspended(username)
        if not user.data.user.result.id and not user.data.user.result.reason:
            raise UserNotFound(username)
        return user
