import json
from cashews import cache
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, Type, Self
from discord.ext.commands import CommandFailure

from system.services import Network

from system.tools.samutils import DEFAULT_HEADERS, Defaults, JSON


@dataclass
class TwitterUser:
    id: str
    full_name: str
    username: str
    media_count: int
    posts_count: int
    created_at: datetime
    followers: int
    following: int
    subscriptions: int
    banner: Optional[str] = None
    avatar: Optional[str] = None
    is_verified: Optional[bool] = False
    is_government_verified: Optional[bool] = False

    @classmethod
    def from_dict(cls: Type[Self], dict: JSON) -> Self:
        """
        Create a TwitterUser instance from a dictionary.
        Extracts necessary information from the response dictionary.

        Args:
            dict (JSON): The JSON response containing user details.

        Returns:
            Self: An instance of TwitterUser with the extracted details.
        """
        legacy: JSON = dict.get("legacy", {})

        return cls(
            id=dict["rest_id"],
            full_name=legacy["name"],
            username=legacy["screen_name"],
            media_count=legacy.get("media_count", 0),
            posts_count=legacy.get("statuses_count", 0),
            created_at=datetime.strptime(
                legacy["created_at"], "%a %b %d %H:%M:%S %z %Y"
            ),
            followers=legacy.get("followers_count", 0),
            following=legacy.get("friends_count", 0),
            subscriptions=dict.get("creator_subscriptions_count", 0),
            banner=legacy.get("profile_banner_url", None),
            avatar=legacy.get("profile_image_url_https", None),
            is_verified=legacy.get("verified") or dict.get("is_blue_verified", False),
            is_government_verified=(legacy.get("verified_type", "") == "Government"),
        )

    @classmethod
    @cache(ttl="3m", key="TWITTER:USER:{username}")
    async def fetch(cls: Type[Self], username: str, session: Network) -> Self:
        """
        Fetch user data from Twitter using the provided username.
        Caches the result for 3 minutes.

        Args:
            username (str): The Twitter username to fetch data for.
            session (Network): The network service to make the request with.

        Raises:
            CommandFailure: If the response does not contain valid data.

        Returns:
            Self: An instance of TwitterUser with the extracted details.
        """
        response = await session.request(
            url=f"https://twitter.com/i/api/graphql/xmU6X_CKVnQ5lSrCbAmJsg/UserByScreenName",
            params={
                "variables": json.dumps(
                    {
                        "screen_name": username,
                        "withSafetyModeUserFields": True,
                    }
                ),
                "features": json.dumps(
                    {
                        "hidden_profile_subscriptions_enabled": True,
                        "rweb_tipjar_consumption_enabled": True,
                        "responsive_web_graphql_exclude_directive_enabled": True,
                        "verified_phone_label_enabled": False,
                        "subscriptions_verification_info_is_identity_verified_enabled": True,
                        "subscriptions_verification_info_verified_since_enabled": True,
                        "highlights_tweets_tab_ui_enabled": True,
                        "responsive_web_twitter_article_notes_tab_enabled": True,
                        "subscriptions_feature_can_gift_premium": True,
                        "creator_subscriptions_tweet_preview_api_enabled": True,
                        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                        "responsive_web_graphql_timeline_navigation_enabled": True,
                    }
                ),
                "fieldToggles": json.dumps(
                    {
                        "withAuxiliaryUserLabels": False,
                    }
                ),
            },
            headers={
                **DEFAULT_HEADERS,
                "X-Client-UUID": Defaults.TWITTER_CLIENT_ID,
                "X-CSRF-TOKEN": Defaults.TWITTER_CSFR_TOKEN,
                "X-Twitter-Auth-Type": "OAuth2Session",
                "Authorization": Defaults.TWITTER_AUTHORIZATION,
                "Cookie": f"auth_token={Defaults.TWITTER_AUTH_TOKEN};ct0={Defaults.TWITTER_CSFR_TOKEN}",
            },
            status_responses={
                403: "The **Twitter API** authentication is invalid.",
                429: "The **Twitter API** has been **rate limited**.",
            },
        )

        if not isinstance(response, dict):
            raise CommandFailure("That Twitter user could not be found.")

        data: JSON = response.get("data", {}).get("user", {}).get("result", {})

        if not data:
            raise CommandFailure("That Twitter user could not be found.")

        if data.get("__typename") == "UserUnavailable":
            raise CommandFailure(
                f"Could not display account for reason: **{data.get('message', 'absolutely no fucking idea')}**"
            )

        return cls.from_dict(data)
