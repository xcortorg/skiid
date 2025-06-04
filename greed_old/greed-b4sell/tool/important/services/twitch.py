from .Base import BaseService, Redis, Optional, logger, cache
from asyncio import sleep, ensure_future
from typing import Any
from aiohttp import ClientSession
from .models.Twitch import Channel, ChannelResponse, Stream, StreamResponse
from os import environ
import traceback

USER_URL = "https://api.twitch.tv/helix/users?login={}"
STREAM_URL = "https://api.twitch.tv/helix/streams?user_id={}"
AUTH_URL = "https://id.twitch.tv/oauth2/token?client_id={}&client_secret={}&grant_type=client_credentials"


class TwitchService(BaseService):
    def __init__(self: "TwitchService", redis: Redis, ttl: Optional[int] = 300):
        self.redis = redis
        self.ttl = ttl
        self.bearer = None
        super().__init__(self.redis, self.ttl)

    @property
    def client_id(self: "TwitchService") -> str:
        return "qfmjqljx7tyjrm6xfgz0vcq61fhbbh"

    @property
    def client_secret(self: "TwitchService") -> str:
        return "c9q4b428s6ygzgaq12cps6f4ltm4oo"

    @property
    def base_headers(self: "TwitchService") -> dict:
        """Get base headers for Twitch API requests."""
        data = {"Client-ID": self.client_id}
        if self.bearer:
            data["Authorization"] = f"Bearer {self.bearer}"
        return data

    async def reauthorize(self):
        await sleep(86400 * 30)
        return await self.authorize()

    async def authorize(self: "TwitchService"):
        """
        Authorize with Twitch API and get access token.

        Raises:
            ValueError: If client credentials are not configured
            Exception: If authorization fails
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Twitch API credentials not configured")

        try:
            async with ClientSession() as session:
                auth_url = AUTH_URL.format(self.client_id, self.client_secret)
                headers = {"Content-Type": "application/x-www-form-urlencoded"}

                async with session.post(auth_url, headers=headers) as response:
                    if response.status != 200:
                        error_data = await response.text()
                        logger.error(
                            f"Failed to get Twitch access token. Status: {response.status}, Response: {error_data}"
                        )
                        logger.error(f"Request URL: {auth_url}")
                        raise Exception(
                            f"Failed to authorize with Twitch. Status: {response.status}"
                        )

                    try:
                        data = await response.json()
                    except Exception as e:
                        logger.error(f"Failed to parse Twitch token response: {e}")
                        raise Exception("Invalid response format from Twitch API")

                    if "access_token" not in data:
                        logger.error(f"Invalid Twitch token response: {data}")
                        raise Exception("Invalid token response from Twitch")

                    self.bearer = data["access_token"]
                    ensure_future(self.reauthorize())

        except Exception as e:
            logger.error(f"Authorization failed: {str(e)}")
            raise

    @cache()
    async def get_channel(self: "TwitchService", username: str, **kwargs: Any):
        """
        Get a channel's information from Twitch API.

        Args:
            username: The Twitch username to look up
            **kwargs: Additional arguments to pass to the API

        Returns:
            ChannelResponse: The channel information

        Raises:
            Exception: If the API request fails or returns invalid data
        """
        if not self.bearer:
            await self.authorize()

        try:
            async with ClientSession() as session:
                async with session.get(
                    USER_URL.format(username), headers=self.base_headers
                ) as response:
                    if response.status != 200:
                        error_data = await response.text()
                        logger.error(
                            f"Twitch API error for {username}. Status: {response.status}, Response: {error_data}"
                        )
                        raise Exception(f"Twitch API error: {response.status}")

                    data = await response.json()
                    if not data or "data" not in data:
                        logger.error(f"Invalid response data for {username}: {data}")
                        raise Exception("Invalid response from Twitch API")

                    return ChannelResponse(**data)

        except Exception as e:
            logger.error(f"Failed to get channel data for {username}: {str(e)}")
            raise Exception(f"Failed to get channel data: {str(e)}") from e

    async def get_streams(
        self: "TwitchService",
        *,
        username: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> StreamResponse:
        """
        Get a channel's streams from Twitch API.

        Args:
            username: Optional username to get streams for
            user_id: Optional user ID to get streams for

        Returns:
            StreamResponse: The stream data from Twitch API

        Raises:
            Exception: If the API request fails
        """
        if not self.bearer:
            await self.authorize()

        try:
            if username and not user_id:
                user_data = await self.get_channel(username)
                if not user_data or not user_data.channel:
                    logger.error(f"Could not get user ID for username: {username}")
                    return StreamResponse(data=[])
                user_id = user_data.channel.id

            async with ClientSession() as session:
                async with session.get(
                    STREAM_URL.format(user_id), headers=self.base_headers
                ) as response:
                    if response.status != 200:
                        error_data = await response.text()
                        logger.error(
                            f"Twitch API error getting streams. Status: {response.status}, Response: {error_data}"
                        )
                        return StreamResponse(data=[])

                    data = await response.json()
                    if not data:
                        logger.error("Empty response from Twitch API")
                        return StreamResponse(data=[])

                    return StreamResponse(**data)

        except Exception as e:
            logger.error(f"Failed to get stream data: {str(e)}")
            logger.error(traceback.format_exc())
            return StreamResponse(data=[])
