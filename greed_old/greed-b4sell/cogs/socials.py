import asyncio
import re
import time
import requests
from tool.pinterest import Pinterest  # type: ignore
from discord.ext import commands
from discord import Embed, app_commands, Interaction, Message, File, HTTPException
from discord.ext.commands import Context, CommandError
from discord.utils import format_dt
from typing import Optional, Dict, List, Union
from contextlib import suppress
from datetime import datetime, timezone
from humanize import naturaltime

from cashews import cache
from asyncio import sleep
from roblox import AvatarThumbnailType, Client, UserNotFound, TooManyRequests
from roblox.users import User
from roblox.utilities.exceptions import BadRequest
from dataclasses import dataclass, field
from munch import DefaultMunch, Munch
from yt_dlp import DownloadError, YoutubeDL
from yarl import URL
from jishaku.functools import executor_function
import aiohttp
from collections import deque
from loguru import logger
from re import search, compile
from io import BytesIO
from bs4 import BeautifulSoup
import tempfile
import os
import urllib.parse
import orjson
from urllib.parse import parse_qs, urlparse
from tool.managers.bing.bing import BingService
from redis.asyncio import Redis
import shutil
import hashlib
import json
import logging
from functools import partial

from tool.important.services.twitch import TwitchService


@dataclass
class SearchResult:
    title: str
    link: str
    snippet: str


@dataclass
class TweetItem:
    url: str
    text: str
    footer: str


@dataclass
class Result:
    title: str
    url: str
    snippet: str
    highlight: str
    extended_links: List[SearchResult] = field(default_factory=list)


class GoogleScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    async def search(self, query: str, num_pages: int = 3) -> List[SearchResult]:
        results = []

        async with aiohttp.ClientSession(headers=self.headers) as session:
            for page in range(num_pages):
                start = page * 10
                params = {
                    "q": query,
                    "start": str(start),
                    "safe": "active",
                    "num": "20",  # Increased from 10 to get more results per page
                }

                try:
                    async with session.get(
                        "https://www.google.com/search",
                        params=params,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as response:
                        if response.status != 200:
                            continue

                        content = await response.text()
                        soup = BeautifulSoup(content, "lxml")

                        # Main search result containers
                        result_blocks = soup.find_all("div", class_="MjjYud")

                        for block in result_blocks:
                            # Extract title
                            title_elem = block.find("h3", class_="LC20lb")
                            if not title_elem:
                                continue

                            # Extract link
                            link_elem = block.find("a", href=True)
                            if not link_elem:
                                continue

                            link = link_elem["href"]
                            if link.startswith("/url?"):
                                parsed = parse_qs(urlparse(link).query)
                                link = parsed.get("q", [""])[0]

                            # Extract snippet
                            snippet_elem = block.find(
                                "div", class_=["VwiC3b", "lyLwlc"]
                            )
                            snippet = (
                                snippet_elem.get_text(strip=True, separator=" ")
                                if snippet_elem
                                else ""
                            )

                            # Handle featured snippets
                            if "ULSxyf" in block.get("class", []):
                                snippet = block.get_text(strip=True, separator=" ")

                            # Handle different result types
                            result_type = "unknown"
                            if "g" in block.get("class", []):
                                result_type = "organic"
                            elif "ULSxyf" in block.get("class", []):
                                result_type = "featured_snippet"

                            if link.startswith("http") and result_type in [
                                "organic",
                                "featured_snippet",
                            ]:
                                results.append(
                                    SearchResult(
                                        title=title_elem.get_text(strip=True),
                                        link=link,
                                        snippet=snippet,
                                    )
                                )

                except (aiohttp.ClientError, asyncio.TimeoutError):
                    continue

        return results

    def parse_tweets(self, soup: BeautifulSoup) -> List[TweetItem]:
        tweets = []
        tweet_blocks = soup.find_all("div", {"data-testid": "tweet"})

        for tweet in tweet_blocks:
            url_elem = tweet.find("a", {"href": True})
            text_elem = tweet.find("div", {"data-testid": "tweetText"})
            footer_elem = tweet.find("div", {"role": "group"})

            if all((url_elem, text_elem, footer_elem)):
                tweets.append(
                    TweetItem(
                        url=url_elem["href"],
                        text=text_elem.get_text(strip=True),
                        footer=footer_elem.get_text(strip=True),
                    )
                )

        return tweets


class GoogleImages:
    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0 Safari/537.36"
            )
        }

    async def search(self, query: str, num_pages: int = 5) -> list[str]:
        results = []

        for page in range(num_pages):
            url = URL.build(
                scheme="https",
                host="www.google.com",
                path="/search",
                query={
                    "q": query,
                    "tbm": "isch",
                    "safe": "active",
                    "start": str(page * 20),
                },
            )

            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        continue
                    content = await response.text()

            soup = BeautifulSoup(content, "html.parser")
            for img in soup.find_all("img"):
                if src := img.get("src"):
                    if src.startswith("http") and not src.startswith(
                        "https://www.google.com"
                    ):
                        results.append(src)
        logger.info(results)
        return results[:100]


client = Client()


@dataclass
class Badge:
    id: int
    name: str
    description: str
    image_url: str

    @property
    def url(self) -> str:
        """Generate the URL for the badge on Roblox."""
        return f"https://www.roblox.com/info/roblox-badges#Badge{self.id}"


@dataclass
class Presence:
    status: str
    location: Optional[str]
    last_online: Optional[datetime]


@dataclass
class RobloxUserModel:
    id: int
    name: str
    display_name: str
    description: str
    is_banned: bool
    created_at: datetime
    original: User = field(repr=False)

    @property
    def url(self) -> str:
        """Generate the profile URL for the Roblox user."""
        return f"https://www.roblox.com/users/{self.id}/profile"

    @cache(ttl=3600, key="avatar_url:{self.id}")
    async def avatar_url(self) -> Optional[str]:
        """Fetch the user's avatar URL."""
        thumbnails = await client.thumbnails.get_user_avatar_thumbnails(
            users=[self.id],
            type=AvatarThumbnailType.full_body,
            size=(420, 420),
        )
        return thumbnails[0].image_url if thumbnails else None

    @cache(ttl=3600, key="badges:{self.id}")
    async def badges(self) -> List[Badge]:
        """Fetch a list of the user's badges."""
        badges = await self.original.get_roblox_badges()
        return [
            Badge(
                id=badge.id,
                name=badge.name,
                description=badge.description,
                image_url=badge.image_url,
            )
            for badge in badges
        ]

    async def follower_count(self) -> int:
        """Fetch the count of followers."""
        try:
            return await self.original.get_follower_count()
        except TooManyRequests:
            raise CommandError(
                "The Roblox API rate limit has been exceeded. Please try again later."
            )

    async def following_count(self) -> int:
        """Fetch the count of users the user is following."""
        try:
            return await self.original.get_following_count()
        except TooManyRequests:
            raise CommandError(
                "The Roblox API rate limit has been exceeded. Please try again later."
            )

    async def friend_count(self) -> int:
        """Fetch the count of friends."""
        try:
            return await self.original.get_friend_count()
        except TooManyRequests:
            raise CommandError(
                "The Roblox API rate limit has been exceeded. Please try again later."
            )

    async def presence(self) -> Optional[Presence]:
        """Fetch the presence status of the user."""
        presence = await self.original.get_presence()
        return (
            Presence(
                status=presence.user_presence_type.name,
                location=presence.last_location,
            )
            if presence
            else None
        )

    @cache(ttl=3600, key="names:{self.id}")
    async def names(self) -> List[str]:
        """Fetch the username history of the user."""
        names = []
        with suppress(BadRequest):
            async for name in self.original.username_history():
                names.append(str(name))
        return names

    @classmethod
    async def fetch(cls, username: str) -> Optional["RobloxUserModel"]:
        """Fetch a Roblox user by their username."""
        try:
            user = await client.get_user_by_username(username, expand=True)
        except (UserNotFound, BadRequest, app_commands.errors.CommandInvokeError):
            return None
        except TooManyRequests:
            raise CommandError(
                "The Roblox API rate limit has been exceeded. Please try again later."
            )

        if isinstance(user, User):
            return cls(
                id=user.id,
                name=user.name,
                display_name=user.display_name,
                description=user.description,
                is_banned=user.is_banned,
                created_at=user.created,
                original=user,
            )
        return None

    @classmethod
    async def convert(cls, ctx: Context, argument: str) -> "RobloxUserModel":
        """Convert a username argument into a RobloxUserModel."""
        async with ctx.typing():
            if user := await cls.fetch(argument):
                return user
        raise CommandError("No **Roblox user** found with that name!")


@cache(ttl=3600)
async def fetch_instagram_data(username):
    """Fetch Instagram profile data using GraphQL API with fingerlogger.infoing."""

    url = (
        f"https://www.instagram.com/api/v1/users/web_profile_info/?username={username}"
    )

    # Browser-like headers with fingerlogger.infoing
    headers = {
        "authority": "www.instagram.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cookie": "csrftoken=5o2PA4bwEeq1wdDxc_9znG; datr=p49-Z3asiKca3ndgFsFI6CBm; ig_did=A3A1170B-1845-42A7-8102-008D6C7E9642; mid=Z36PpwALAAGD0PLqzGxxxFkjkg3G; sessionid=61688220172%3AUeUQEM8RZtp0Ba%3A10%3AAYdveNJCG_h5eaNW5z_1D-KrQgCzksMGXEsnlzy26w; ds_user_id=61688220172; wd=576x945;",  # Add your Instagram cookie here for authentication
        "dpr": "2",
        "referer": f"https://www.instagram.com/{username}/",
        "sec-ch-prefers-color-scheme": "dark",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "sec-ch-ua-full-version-list": '"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.6099.71"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-model": '""',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-platform-version": '"15.0.0"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36",
        "viewport-width": "1920",
        "x-asbd-id": "129477",
        "x-csrftoken": "",  # Add CSRF token here
        "x-ig-app-id": "936619743392459",
        "x-ig-www-claim": "0",
        "x-requested-with": "XMLHttpRequest",
    }

    try:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            if "data" in data and "user" in data["data"]:
                return data["data"]["user"], None
            return None, "User data not found"
        elif response.status_code == 404:
            return None, "Profile not found"
        else:
            return None, f"Error: Status code {response.status_code}"

    except requests.RequestException as e:
        return None, f"Request failed: {str(e)}"
    except ValueError as e:
        return None, f"JSON parsing failed: {str(e)}"


@cache(ttl=3600, key="instagram_stories:{username}")
async def fetch_instagram_stories(username):
    headers = {
        "authority": "www.instagram.com",
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "cookie": "csrftoken=5o2PA4bwEeq1wdDxc_9znG; datr=p49-Z3asiKca3ndgFsFI6CBm; ig_did=A3A1170B-1845-42A7-8102-008D6C7E9642; mid=Z36PpwALAAGD0PLqzGxxxFkjkg3G; sessionid=61688220172%3AUeUQEM8RZtp0Ba%3A10%3AAYdveNJCG_h5eaNW5z_1D-KrQgCzksMGXEsnlzy26w; ds_user_id=61688220172; wd=576x945;",  # Add your Instagram cookie here for authentication
        "dpr": "2",
        "referer": f"https://www.instagram.com/{username}/",
        "sec-ch-prefers-color-scheme": "dark",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
        "sec-ch-ua-full-version-list": '"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.6099.71"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-model": '""',
        "sec-ch-ua-platform": '"Windows"',
        "sec-ch-ua-platform-version": '"15.0.0"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.71 Safari/537.36",
        "viewport-width": "1920",
        "x-asbd-id": "129477",
        "x-csrftoken": "",
        "x-ig-app-id": "936619743392459",
        "x-ig-www-claim": "0",
        "x-requested-with": "XMLHttpRequest",
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        try:
            profile_url = f"https://i.instagram.com/api/v1/users/web_profile_info/?username={username}"
            async with session.get(profile_url) as resp:
                profile_data = await resp.json()

                if "data" not in profile_data or "user" not in profile_data["data"]:
                    raise ValueError("Invalid profile response structure")

                user_id = profile_data["data"]["user"]["id"]

            stories_url = (
                f"https://i.instagram.com/api/v1/feed/reels_media/?reel_ids={user_id}"
            )
            async with session.get(stories_url) as resp:
                stories_data = await resp.json()
                logger.info(stories_data)

                if "reels_media" not in stories_data or not stories_data["reels_media"]:
                    return []

                return [
                    item["image_versions2"]["candidates"][0]["url"]
                    for item in stories_data["reels_media"][0]["items"]
                ]

        except (KeyError, IndexError, orjson.JSONDecodeError) as e:
            raise ValueError(f"API response parsing error: {str(e)}")
        except aiohttp.ClientError as e:
            raise ValueError(f"Network error: {str(e)}")


TWITTER_BEARER_TOKENS = [
    "AAAAAAAAAAAAAAAAAAAAAFF3xQEAAAAAxq%2BVlmthJYK6LmfQT7P7arVPrRk%3DGG8roGZ2JVKlAn3dPNU4RtJ6ltjQ6r4EaA4lWCPD4495qywjxG",
    "AAAAAAAAAAAAAAAAAAAAAKSjxwEAAAAA5hdVoyx6WEE5nu7mRd5URE1RS8Q%3DYC3CN5b2CRKZAYe51pgyjaVqDn4yQ6WFEBVC8I48fWch8SmmY5",
    # Add more tokens here if available
]

profile_cache = {}
CACHE_EXPIRY_TIME = 3600  # Cache expiration time in seconds (1 hour)


class TwitterAPIClient:
    def __init__(self):
        self.token_index = 0
        self.session = requests.Session()
        self.request_queue = deque()

    def get_next_token(self):
        token = TWITTER_BEARER_TOKENS[self.token_index]
        self.token_index = (self.token_index + 1) % len(TWITTER_BEARER_TOKENS)
        return token

    def make_request_with_queue(self, url):
        # Queue-based rate-limit management
        self.add_to_queue(url)
        response = self.execute_from_queue()
        return response

    def add_to_queue(self, url):
        self.request_queue.append(url)

    def execute_from_queue(self):
        while self.request_queue:
            url = self.request_queue.popleft()
            response = self.make_request_with_limit_handling(url)
            if response:
                return response
        return None

    def make_request_with_limit_handling(self, url):
        headers = {"Authorization": f"Bearer {self.get_next_token()}"}

        # Make the request and handle rate limits
        response = self.session.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 429:  # Rate limit hit
            retry_after = int(
                response.headers.get("Retry-After", 60)
            )  # Get retry time from header
            logger.info(f"Rate limit hit. Retrying in {retry_after} seconds...")
            time.sleep(retry_after)  # Wait for the retry period
            return self.make_request_with_limit_handling(url)  # Retry after waiting
        else:
            logger.info(f"Error: {response.status_code}, {response.text}")
            return None

    def get_twitter_profile(self, username):
        # Check the cache first
        if (
            username in profile_cache
            and time.time() - profile_cache[username]["time"] < CACHE_EXPIRY_TIME
        ):
            return profile_cache[username]["data"]

        url = f"https://api.twitter.com/2/users/by/username/{username}?user.fields=username,public_metrics,name,profile_image_url"
        result = self.make_request_with_queue(url)

        if result:
            profile_cache[username] = {
                "data": result["data"],
                "time": time.time(),
            }  # Cache the result
            return result["data"]
        return None


SHZ_API_KEY = "153315b3a7msh91fdaf0f92e2df7p1abcfbjsn1a9bc21996f7"


class Socials(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scraper = GoogleScraper()
        self.images = GoogleImages()
        self.twitter_client = TwitterAPIClient()
        # Cache for media files - key: URL, value: (path, timestamp)
        self.media_cache = {}
        self.cache_dir = os.path.join(tempfile.gettempdir(), "greed_media_cache")
        self.cache_max_age = 3600 * 24  # 24 hours in seconds
        self.cache_max_size = 50  # Maximum number of items in cache

        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

        # Start a background task to clean the cache periodically
        self.cache_cleanup_task = self.bot.loop.create_task(
            self.cleanup_cache_periodically()
        )

        self.api_client = TwitterAPIClient()
        self.token_index = 0
        self.request_queue = deque()
        self.session = requests.Session()
        self.pinterest = Pinterest()
        self.services = {
            "youtube": compile(
                "(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?v=|shorts\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})"
            ),
            "SoundCloud": (
                r"(?:https?:\/\/)?(?:www\.)?soundcloud\.com\/(?P<username>[a-zA-Z0-9_-]+)\/(?P<slug>[a-zA-Z0-9_-]+)",
                r"(?:https?:\/\/)?(?:www\.)?soundcloud\.app\.goo\.gl\/([a-zA-Z0-9_-]+)",
                r"(?:https?:\/\/)?on\.soundcloud\.com\/([a-zA-Z0-9_-]+)",
            ),
            "tiktok": compile(
                r"(?:https?:\/\/)?(?:www\.|m\.)?(?:vm\.)?tiktok\.com\/(?:@[\w.-]+\/)?(?:video\/|t\/)?([a-zA-Z0-9-_]+)"
            ),
            "instagram": compile(
                r"(?:https?:\/\/)?(?:www\.|m\.)?instagram\.com\/(?:p|reels?)\/([a-zA-Z0-9-_]+)"
            ),
            "twitter": compile(
                r"(?:https?:\/\/)?(?:www\.|m\.)?(?:twitter\.com|x\.com)\/(?:#!\/)?(?:\w+)\/status(?:es)?\/(\d+)"
            ),
            "xiaohongshu": compile(
                r"(?:https?:\/\/)?(?:www\.)?xiaohongshu\.com\/(?:discovery|explore)\/(?:[a-zA-Z0-9]+)"
            ),
        }

        self.ytdl = YoutubeDL(
            {
                "format": "bestaudio/best",
                "quiet": True,
                "verbose": False,
                "merge_output_format": "mp4",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                },
            }
        )

        self._cooldown_mapping = commands.CooldownMapping.from_cooldown(
            1, 5, commands.BucketType.member
        )

    def cog_unload(self):
        # Cancel the cleanup task when the cog is unloaded
        if hasattr(self, "cache_cleanup_task"):
            self.cache_cleanup_task.cancel()

    async def cleanup_cache_periodically(self):
        """Periodically clean up old cache files."""
        try:
            while True:
                await asyncio.sleep(3600)  # Run every hour
                self.cleanup_cache()
        except asyncio.CancelledError:
            pass

    def cleanup_cache(self):
        """Remove old cache files."""
        current_time = time.time()
        # Clean memory cache
        expired_urls = [
            url
            for url, (_, timestamp) in self.media_cache.items()
            if current_time - timestamp > self.cache_max_age
        ]
        for url in expired_urls:
            del self.media_cache[url]

        # Clean disk cache
        for filename in os.listdir(self.cache_dir):
            file_path = os.path.join(self.cache_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > self.cache_max_age:
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        logger.error(f"Failed to remove cache file {file_path}: {e}")

    def get_cached_media(self, url: str) -> Optional[str]:
        """Get a cached media file if it exists and is not expired."""
        if url in self.media_cache:
            path, timestamp = self.media_cache[url]
            if time.time() - timestamp <= self.cache_max_age and os.path.exists(path):
                return path
            # Remove from cache if expired or file doesn't exist
            del self.media_cache[url]
        return None

    def cache_media(self, url: str, file_path: str) -> str:
        """Cache a media file and return the path to the cached file."""
        # Generate a unique filename based on URL
        url_hash = hashlib.md5(url.encode()).hexdigest()
        ext = os.path.splitext(file_path)[1]
        cache_filename = f"{url_hash}{ext}"
        cache_path = os.path.join(self.cache_dir, cache_filename)

        # Copy the file to the cache directory
        try:
            shutil.copy2(file_path, cache_path)
            # Add to memory cache
            self.media_cache[url] = (cache_path, time.time())

            # If cache is too large, remove oldest items
            if len(self.media_cache) > self.cache_max_size:
                oldest_url = min(self.media_cache.items(), key=lambda x: x[1][1])[0]
                del self.media_cache[oldest_url]

            return cache_path
        except Exception as e:
            logger.error(f"Failed to cache media file: {e}")
            return file_path  # Return original path if caching fails

    @property
    def shop_url(self) -> str:
        """
        Generate the Fortnite shop image URL for the current day.
        Returns a timestamped URL to prevent caching issues.
        """
        try:
            now = datetime.now(timezone.utc)
            base_url = "https://bot.fnbr.co/shop-image/fnbr-shop-"
            date_str = now.strftime("%-d-%-m-%Y")
            timestamp = int(now.timestamp())
            return f"{base_url}{date_str}.png?{timestamp}"
        except Exception as e:
            logger.error(f"Error generating shop URL: {e}")
            raise CommandError("Failed to generate Fortnite shop URL.")

    @executor_function
    def extract_data(self, url: Union[URL, str], **params) -> Optional[Munch]:
        data: Optional[Dict]
        try:
            data = self.ytdl.extract_info(
                url=str(url),
                download=True,
                **params,
            )
        except DownloadError:
            return

        if data:
            return DefaultMunch.fromDict(data)

    @commands.Cog.listener("on_message")
    async def check_service(self, message: Message):
        if message.author.bot or not message.guild or not message.content:
            return

        if not any(
            message.content.lower().startswith(prefix)
            for prefix in ("nigga", "greed", message.guild.me.display_name)
        ):
            return

        ctx = await self.bot.get_context(message)

        for service, pattern in self.services.items():
            try:
                if isinstance(pattern, tuple):
                    main_pattern, *short_patterns = pattern
                    for short_pattern in short_patterns:
                        if match := search(short_pattern, message.content):
                            async with self.bot.session.get(match.group()) as response:
                                message.content = str(response.url)
                                break
                    pattern = main_pattern

                if not (match := search(pattern, message.content)):
                    continue

                if bucket := self._cooldown_mapping.get_bucket(message):
                    if bucket.update_rate_limit():
                        break

                async with ctx.typing():
                    arguments = (
                        list(match.groupdict().values())
                        if match.groupdict()
                        else [URL(match.group())]
                    )
                    self.bot.dispatch(f"{service.lower()}_request", ctx, *arguments)

                await sleep(1)

                if message.embeds and not message.mentions[1:]:
                    with suppress(HTTPException):
                        await message.delete()
                break
            except Exception as e:
                logger.error(f"{service} link: {e}")
                continue

    @commands.Cog.listener("on_youtube_request")
    async def on_youtube_request(self, ctx: Context, url: URL) -> Message:
        data = await self.extract_data(str(url))
        if not data:
            return

        # Check if the video is already cached
        cached_path = self.get_cached_media(str(url))
        if cached_path:
            try:
                embed = Embed(
                    description=f"[{data.title}]({data.webpage_url})",
                    url=str(url),
                )

                if author := data.get("uploader"):
                    embed.set_author(name=author)

                likes, views = data.get("like_count"), data.get("view_count")
                if likes and views:
                    embed.set_footer(text=f"{likes:,} likes | {views:,} views")

                # Force MP4 extension
                file_extension = "mp4"

                async with ctx.typing():
                    with open(cached_path, "rb") as f:
                        await ctx.send(
                            embed=embed,
                            file=File(fp=f, filename=f"{data.title}.{file_extension}"),
                        )
                return
            except Exception as e:
                logger.error(f"Error using cached YouTube video: {e}")
                # Continue to download if using cache fails

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts = {
                    "format": "best",
                    "outtmpl": f"{temp_dir}/%(title)s.%(ext)s",
                    "merge_output_format": "mp4",
                }

                with YoutubeDL(ydl_opts) as ydl:
                    video_info = ydl.extract_info(str(url), download=True)
                    video_path = ydl.prepare_filename(video_info)

                    embed = Embed(
                        description=f"[{data.title}]({data.webpage_url})",
                        url=str(url),
                    )

                    if author := data.get("uploader"):
                        embed.set_author(name=author)

                    likes, views = data.get("like_count"), data.get("view_count")
                    if likes and views:
                        embed.set_footer(text=f"{likes:,} likes | {views:,} views")

                    # Force MP4 extension
                    file_extension = "mp4"

                    try:
                        async with ctx.typing():
                            for attempt in range(3):
                                try:
                                    # Cache the video before sending
                                    cached_path = self.cache_media(str(url), video_path)

                                    with open(cached_path, "rb") as f:
                                        await ctx.send(
                                            embed=embed,
                                            file=File(
                                                fp=f,
                                                filename=f"{data.title}.{file_extension}",
                                            ),
                                        )
                                    break
                                except (IndexError, ConnectionError) as e:
                                    if attempt == 2:
                                        logger.error(
                                            f"Failed to send YouTube video after 3 attempts: {e}"
                                        )
                                        return await ctx.error(
                                            "Failed to process the YouTube video. Please try again later."
                                        )
                                    await asyncio.sleep(1)
                    except Exception as e:
                        logger.error(f"Error in YouTube request handler: {e}")
                        await ctx.warning(
                            "An error occurred while processing your request."
                        )
        except Exception as e:
            logger.error(f"YouTube download failed: {e}")
            await ctx.fail("Failed to process that YouTube video!")

    def get_high_res_profile_image(self, profile_image_url):
        if profile_image_url:
            return profile_image_url.replace("_normal", "")
        return profile_image_url

    @commands.Cog.listener()
    async def on_instagram_request(self, ctx: Context, url: URL) -> Message:
        data = await self.extract_data(url)
        logger.info(data)
        if not data:
            return

        # Check if the video is already cached
        cached_path = self.get_cached_media(str(url))
        if cached_path:
            try:
                embed = Embed(
                    description=f"[{data.title}]({data.webpage_url})",
                    url=url,
                )

                if author := data.get("uploader"):
                    embed.set_author(
                        name=author, icon_url=data.thumbnail if data.thumbnail else None
                    )

                embed.set_footer(text=f"uploaded {naturaltime(data.upload_date)}")

                # Force MP4 extension
                file_extension = "mp4"

                with open(cached_path, "rb") as f:
                    await ctx.send(
                        embed=embed,
                        file=File(fp=f, filename=f"{data.title}.{file_extension}"),
                    )
                return
            except Exception as e:
                logger.error(f"Error using cached Instagram video: {e}")
                # Continue to download if using cache fails

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts = {
                    "format": "best",
                    "outtmpl": f"{temp_dir}/%(title)s.%(ext)s",
                    "merge_output_format": "mp4",
                }

                with YoutubeDL(ydl_opts) as ydl:
                    video_info = ydl.extract_info(str(url), download=True)
                    video_path = ydl.prepare_filename(video_info)

                    embed = Embed(
                        description=f"[{data.title}]({data.webpage_url})",
                        url=url,
                    )

                    if author := data.get("uploader"):
                        embed.set_author(
                            name=author,
                            icon_url=data.thumbnail if data.thumbnail else None,
                        )

                    embed.set_footer(text=f"uploaded {naturaltime(data.upload_date)}")

                    # Force MP4 extension
                    file_extension = "mp4"

                    # Cache the video before sending
                    cached_path = self.cache_media(str(url), video_path)

                    with open(cached_path, "rb") as f:
                        await ctx.send(
                            embed=embed,
                            file=File(fp=f, filename=f"{data.title}.{file_extension}"),
                        )
        except Exception as e:
            logger.error(f"Instagram download failed: {e}")
            await ctx.fail("Failed to process that Instagram post!")

    @commands.Cog.listener()
    async def on_soundcloud_request(self, ctx, username, slug):
        url = f"https://soundcloud.com/{username}/{slug}"

        # Check if the audio is already cached
        cached_path = self.get_cached_media(url)
        if cached_path:
            try:
                # Extract info without downloading
                ydl_opts = {
                    "format": "bestaudio/best",
                    "quiet": True,
                    "extract_flat": True,
                    "skip_download": True,
                }

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info["title"]

                    embed = Embed(
                        title=title,
                        url=url,
                        description=f"Duration: {info.get('duration_string', 'Unknown')}",
                    )

                    if uploader := info.get("uploader"):
                        embed.set_author(
                            name=uploader,
                            icon_url=(
                                ctx.author.avatar.url
                                if ctx.author.avatar
                                else ctx.author.default_avatar.url
                            ),
                        )

                    if thumbnail := info.get("thumbnail"):
                        embed.set_thumbnail(url=thumbnail)

                    if views := info.get("view_count"):
                        embed.set_footer(text=f"{views:,} plays")

                    with open(cached_path, "rb") as f:
                        await ctx.send(
                            embed=embed,
                            file=File(
                                fp=f,
                                filename=f"{title}.mp3",
                                description="voice-message",
                                spoiler=False,
                            ),
                        )
                return
            except Exception as e:
                logger.error(f"Error using cached SoundCloud track: {e}")
                # Continue to download if using cache fails

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts = {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "192",
                        }
                    ],
                    "quiet": True,
                    "logtostderr": True,
                    "extract_flat": False,
                    "no_warnings": True,
                    "outtmpl": f"{temp_dir}/%(title)s.%(ext)s",
                }

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    title = info["title"]
                    # The file will have .mp3 extension due to the postprocessor
                    final_file = os.path.join(temp_dir, f"{title}.mp3")

                    embed = Embed(
                        title=title,
                        url=url,
                        description=f"Duration: {info.get('duration_string', 'Unknown')}",
                    )

                    if uploader := info.get("uploader"):
                        embed.set_author(
                            name=uploader,
                            icon_url=(
                                ctx.author.avatar.url
                                if ctx.author.avatar
                                else ctx.author.default_avatar.url
                            ),
                        )

                    if thumbnail := info.get("thumbnail"):
                        embed.set_thumbnail(url=thumbnail)

                    if views := info.get("view_count"):
                        embed.set_footer(text=f"{views:,} plays")

                    # Cache the audio before sending
                    cached_path = self.cache_media(url, final_file)

                    with open(cached_path, "rb") as f:
                        await ctx.send(
                            embed=embed,
                            file=File(
                                fp=f,
                                filename=f"{title}.mp3",
                                description="voice-message",
                                spoiler=False,
                            ),
                        )
        except Exception as e:
            logger.error(f"SoundCloud request failed: {e}")
            await ctx.fail("That SoundCloud track could not be found!")

    @commands.Cog.listener()
    async def on_twitter_request(self, ctx: Context, url: URL):
        data = await self.extract_data(url)
        if not data:
            return
        logger.info(data)

        # Check if the video is already cached
        cached_path = self.get_cached_media(str(url))
        if cached_path:
            try:
                embed = Embed(
                    description=f"[{data.title}]({data.webpage_url})",
                    url=url,
                    timestamp=(
                        datetime.strptime(str(data.upload_date), "%Y%m%d")
                        if data.upload_date
                        else None
                    ),
                )

                if author := data.get("uploader"):
                    embed.set_author(name=author)
                    if data.get("thumbnail"):
                        embed.set_thumbnail(url=data.thumbnail)

                metrics = []
                if likes := data.get("like_count"):
                    metrics.append(f"❤️ {likes:,}")
                if reposts := data.get("repost_count"):
                    metrics.append(f"🔁 {reposts:,}")
                if comments := data.get("comment_count"):
                    metrics.append(f"💬 {comments:,}")

                if metrics:
                    embed.set_footer(text=" • ".join(metrics))

                with open(cached_path, "rb") as f:
                    await ctx.send(
                        embed=embed,
                        file=File(BytesIO(f.read()), filename=f"{data.title}.mp4"),
                    )
                return
            except Exception as e:
                logger.error(f"Error using cached Twitter video: {e}")
                # Continue to download if using cache fails

        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                ydl_opts = {
                    "format": "best",
                    "outtmpl": f"{temp_dir}/%(title)s.%(ext)s",
                    "merge_output_format": "mp4",
                }

                with YoutubeDL(ydl_opts) as ydl:
                    video_info = ydl.extract_info(str(url), download=True)
                    video_path = ydl.prepare_filename(video_info)

                    # Cache the video before reading it
                    cached_path = self.cache_media(str(url), video_path)

                    with open(cached_path, "rb") as f:
                        buffer = f.read()

        except Exception as e:
            return logger.error(f"Twitter request: {e}")

        embed = Embed(
            description=f"[{data.title}]({data.webpage_url})",
            url=url,
            timestamp=(
                datetime.strptime(str(data.upload_date), "%Y%m%d")
                if data.upload_date
                else None
            ),
        )

        if author := data.get("uploader"):
            embed.set_author(name=author)
            if data.get("thumbnail"):
                embed.set_thumbnail(url=data.thumbnail)

        metrics = []
        if likes := data.get("like_count"):
            metrics.append(f"❤️ {likes:,}")
        if reposts := data.get("repost_count"):
            metrics.append(f"🔁 {reposts:,}")
        if comments := data.get("comment_count"):
            metrics.append(f"💬 {comments:,}")

        if metrics:
            embed.set_footer(text=" • ".join(metrics))

        await ctx.send(
            embed=embed, file=File(BytesIO(buffer), filename=f"{data.title}.mp4")
        )

    def extract_soundcloud_url_parts(self, track: str) -> tuple[str, str]:
        """Extract username and slug from SoundCloud track URL or format string."""
        # Check if it's already a URL
        main_pattern, *short_patterns = self.services["SoundCloud"]

        # Try main pattern first
        if match := search(main_pattern, track):
            return match.group("username"), match.group("slug")

        # Try to resolve short URLs
        for pattern in short_patterns:
            if match := search(pattern, track):
                # Fetch the resolved URL
                short_url = track
                if not track.startswith(("http://", "https://")):
                    short_url = f"https://{track}"

                # Use a synchronous request here since we're in a sync method
                import requests

                try:
                    response = requests.get(short_url, allow_redirects=True)
                    if response.status_code == 200:
                        # Try to match the resolved URL
                        if resolved_match := search(main_pattern, response.url):
                            return resolved_match.group(
                                "username"
                            ), resolved_match.group("slug")
                except:
                    pass

        # If it's not a URL, assume it's in format "artist/track-name"
        if "/" in track:
            username, slug = track.split("/", 1)
            return username.strip(), slug.strip()

        raise commands.CommandError(
            "Invalid SoundCloud track format. Use 'artist/track-name' or a valid SoundCloud URL."
        )

    @app_commands.command(
        name="soundcloud",
        description="Download a track from SoundCloud.",
    )
    @app_commands.describe(track="The SoundCloud track (artist/track-name or URL)")
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def soundcloud_command(self, interaction: Interaction, track: str):
        """Download a track from SoundCloud."""
        try:
            username, slug = self.extract_soundcloud_url_parts(track)
            ctx = await Context.from_interaction(interaction)
            await self.on_soundcloud_request(ctx, username, slug)
        except Exception as e:
            logger.error(f"SoundCloud command failed: {e}")
            await interaction.followup.send("Failed to process that SoundCloud track!")

    @app_commands.command(
        name="roblox",
        description="Get information about a Roblox user.",
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(users=True, guilds=True)
    async def roblox_command(self, interaction: Interaction, username: str):
        """Get information about a Roblox user."""
        try:
            await interaction.response.defer()
            user = await RobloxUserModel.fetch(username)
            if not user:
                await interaction.followup.send("No Roblox user found with that name!")
                return

            embed = Embed(
                title=f"{user.display_name} ({user.name}) {'[BANNED]' if user.is_banned else ''}",
                description=f"{user.description} \n\n{format_dt(user.created_at, 'R')}",
                url=user.url,
            )

            if avatar_url := await user.avatar_url():
                embed.set_thumbnail(url=avatar_url)
            if badges := await user.badges():
                embed.add_field(
                    name="Badges",
                    value="\n".join(f"[{badge.name}]({badge.url})" for badge in badges),
                    inline=False,
                )

            if names := await user.names():
                embed.add_field(
                    name="Previous Names",
                    value="\n".join(names),
                    inline=False,
                )

            embed.set_footer(
                text=f"Followers: {await user.follower_count()} | Following: {await user.following_count()} | Friends: {await user.friend_count()}"
            )
            await interaction.followup.send(embed=embed)
        except TooManyRequests:
            await interaction.followup.send(
                "The Roblox API rate limit has been exceeded. Please try again later.",
                ephemeral=True,
            )
        except Exception as e:
            logger.error(f"Roblox command error: {e}")
            await interaction.followup.send(
                "An error occurred while fetching the Roblox profile.", ephemeral=True
            )

    @commands.command(name="twitter", aliases=["x"])
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def twitter(self, ctx, username: str):
        """
        Discord command to fetch Twitter profile details.
        """
        profile_data = self.twitter_client.get_twitter_profile(username)

        if profile_data:
            metrics = profile_data["public_metrics"]
            high_res_image = self.get_high_res_profile_image(
                profile_data.get("profile_image_url")
            )

            # Retrieve values safely, and provide defaults if missing
            def get_profile_info(key, default="N/A"):
                return profile_data.get(key, default)

            # Extract relevant user data
            name = get_profile_info("name")
            username_twitter = get_profile_info("username")
            bio = get_profile_info("description")
            followers = metrics.get("followers_count", 0)
            following = metrics.get("following_count", 0)
            tweets = metrics.get("tweet_count", 0)
            twitter_url = f"https://twitter.com/{username_twitter}"

            # Format numbers with commas
            followers_str = f"{followers:,}"
            following_str = f"{following:,}"
            tweets_str = f"{tweets:,}"

            # Get author info (command user)
            author_avatar_url = ctx.author.avatar.url
            author_name = ctx.author.name

            # Construct the Embed with the same style as TikTok
            embed = Embed(
                description=f"**[{name} (@{username_twitter})]({twitter_url})**",
                color=self.bot.color,
            )

            # Add fields for Tweets, Following, and Followers (inline for layout like TikTok)
            embed.add_field(name="Tweets", value=f"{tweets_str}", inline=True)
            embed.add_field(name="Followers", value=f"{followers_str}", inline=True)
            embed.add_field(name="Following", value=f"{following_str}", inline=True)

            # Set the thumbnail for the profile picture
            if high_res_image:
                embed.set_thumbnail(url=high_res_image)

            # Set author for the embed with the avatar
            embed.set_author(name=author_name, icon_url=author_avatar_url)

            # Set the footer with Twitter logo
            embed.set_footer(
                text="Twitter",
                icon_url="https://abs.twimg.com/icons/apple-touch-icon-192x192.png",
            )

            # Send the embed message to the Discord channel
            await ctx.send(embed=embed)

            # Log data for debugging (optional)
            logger.info(
                f"Twitter Profile Data for {username_twitter}:\n"
                f"Name: {name}\n"
                f"Bio: {bio}\n"
                f"Followers: {followers_str}\n"
                f"Following: {following_str}\n"
                f"Tweets: {tweets_str}\n"
                f"Profile Image: {high_res_image}"
            )

        else:
            await ctx.send(
                "Failed to fetch Twitter profile information. Please check the username."
            )

    @commands.command(
        name="roblox",
        aliases=["rblx"],
        brief="Get information about a Roblox user.",
        example=",roblox yurrionsolos",
    )
    async def roblox(self, ctx: Context, user: RobloxUserModel):
        """Get information about a Roblox user."""
        async with ctx.typing():
            try:
                embed = Embed(
                    title=f"{user.display_name} ({user.name}) {'[BANNED]' if user.is_banned else ''}",
                    description=f"{user.description} \n\n{format_dt(user.created_at, 'R')}",
                    url=user.url,
                )

                if avatar_url := await user.avatar_url():
                    embed.set_thumbnail(url=avatar_url)

                if badges := await user.badges():
                    embed.add_field(
                        name="Badges",
                        value="\n".join(
                            f"[{badge.name}]({badge.url})" for badge in badges
                        ),
                        inline=False,
                    )

                if names := await user.names():
                    embed.add_field(
                        name="Previous Names",
                        value="\n".join(names),
                        inline=False,
                    )

                embed.set_footer(
                    text=f"Followers: {await user.follower_count()} | Following: {await user.following_count()} | Friends: {await user.friend_count()}"
                )
            except TooManyRequests:
                return await ctx.fail(
                    "The Roblox API rate limit has been exceeded. Please try again later."
                )
            except Exception as e:
                return logger.error(f"Roblox command: {e}")
        await ctx.send(embed=embed)

    @commands.command(name="tiktok", aliases=["tt"])
    @commands.cooldown(
        1, 5, commands.BucketType.user
    )  # Apply rate limit of 5 seconds per user
    async def tiktok(self, ctx, username: str):
        """
        Discord command to fetch TikTok profile details.
        """
        url = "https://tiktok-api23.p.rapidapi.com/api/user/info"
        querystring = {"uniqueId": username}
        headers = {
            "x-rapidapi-key": "153315b3a7msh91fdaf0f92e2df7p1abcfbjsn1a9bc21996f7",  # Use your own API key here
            "x-rapidapi-host": "tiktok-api23.p.rapidapi.com",
        }

        try:
            # Send the request to the TikTok API
            response = requests.get(url, headers=headers, params=querystring)

            # Check if request was successful
            if response.status_code == 200:
                data = response.json()

                # Safely extract user info and stats
                if "userInfo" in data and "user" in data["userInfo"]:
                    user = data["userInfo"]["user"]
                    stats = data["userInfo"]["stats"]

                    # Retrieve values safely with a default
                    def get_user_info(key, default="N/A"):
                        return user.get(key, default)

                    # Get user stats with a default
                    def get_stat_info(key, default=0):
                        return stats.get(key, default)

                    # Extract relevant details from the response
                    username_tiktok = get_user_info("uniqueId")
                    full_name = get_user_info("nickname")
                    bio = get_user_info("signature")
                    followers = get_stat_info("followerCount")
                    following = get_stat_info("followingCount")
                    likes = get_stat_info("heartCount")
                    video_count = get_stat_info("videoCount")
                    profile_picture_url = get_user_info("avatarLarger")
                    tiktok_url = f"https://www.tiktok.com/@{username_tiktok}"

                    # Format numbers with commas
                    followers_str = f"{followers:,}"
                    following_str = f"{following:,}"
                    likes_str = f"{likes:,}"

                    # Get author info (command user)
                    author_avatar_url = ctx.author.avatar.url
                    author_name = ctx.author.name

                    # Create the embed
                    embed = Embed(
                        description=f"**[{full_name} (@{username_tiktok})]({tiktok_url})**\n {bio}",
                        color=self.bot.color,
                    )

                    # Add fields for Likes, Followers, and Following with formatted numbers
                    embed.add_field(name="Likes", value=f"{likes_str}", inline=True)
                    embed.add_field(
                        name="Followers", value=f"{followers_str}", inline=True
                    )
                    embed.add_field(
                        name="Following", value=f"{following_str}", inline=True
                    )

                    # Set the thumbnail of the user profile
                    if profile_picture_url:
                        embed.set_thumbnail(url=profile_picture_url)

                    # Set author for the embed with the avatar
                    embed.set_author(name=author_name, icon_url=author_avatar_url)

                    # Set footer with TikTok logo
                    embed.set_footer(
                        text="TikTok",
                        icon_url="https://cdn.discordapp.com/emojis/1309200047677898763.png",
                    )

                    # Send the embed message to the Discord channel
                    await ctx.send(embed=embed)

                    # Log the data for debugging purposes
                    logger.info(
                        f"TikTok Profile Data for {username_tiktok}:\n"
                        f"Full Name: {full_name}\n"
                        f"Bio: {bio}\n"
                        f"Followers: {followers_str}\n"
                        f"Following: {following_str}\n"
                        f"Likes: {likes_str}\n"
                        f"Video Count: {video_count}\n"
                        f"Profile Picture URL: {profile_picture_url}"
                    )
                else:
                    await ctx.fail(
                        f"Sorry, could not fetch data for TikTok user {username}."
                    )
            else:
                await ctx.fail(
                    f"Failed to fetch TikTok profile for {username}. Status Code: {response.status_code}"
                )

        except requests.RequestException as e:
            await ctx.fail(f"An error occurred while fetching the TikTok profile: {e}")

    @commands.command(
        name="google",
        aliases=["g", "ddg", "search", "bing"],
        brief="Search the web using Google.",
        example=",google how to make a sandwich",
    )
    async def search(self, ctx: Context, *, query: str):
        """Search the web using Google."""
        async with ctx.typing():
            bing = BingService(redis=self.bot.redis, ttl=3600)

            try:
                results = await bing.search(query, safe=True, pages=1)

                if not results.results:
                    return await ctx.fail("No results found for that query.")

                embeds = []
                for i in range(0, len(results.results), 3):
                    embed = Embed(title="Search Results")
                    for result in results.results[i : i + 3]:
                        embed.add_field(
                            name=result.title,
                            value=f"[{result.description}]({result.url})",
                            inline=False,
                        )
                        embed.set_footer(text=f"Page {i // 3 + 1}")
                    embeds.append(embed)

                if results.knowledge_panel:
                    kp = results.knowledge_panel
                    kp_embed = Embed(title=kp.title)
                    kp_embed.description = kp.description
                    if kp.url:
                        kp_embed.url = kp.url
                    if kp.additional_info:
                        for key, value in kp.additional_info.items():
                            kp_embed.add_field(name=key, value=value, inline=True)
                    embeds.insert(0, kp_embed)

            except KeyError as e:
                if str(e) == "'results'":
                    logger.error("Bing search error: No results found")
                    return await ctx.fail("No results found for that query.")
                else:
                    logger.error(f"Bing search error: {e}")
                    return await ctx.fail("An error occurred while searching.")

        await ctx.paginate(embeds)

    @commands.command(
        name="instagram",
        aliases=["ig"],
        brief="Fetch Instagram profile details.",
        example=",instagram username",
    )
    async def instagram(self, ctx: commands.Context, username: str):
        """Fetch Instagram profile details."""
        url = f"https://www.instagram.com/{username}"
        data, error = await fetch_instagram_data(username)

        if data:
            followers = f"{data.get('edge_followed_by', {}).get('count', 0):,}"
            following = f"{data.get('edge_follow', {}).get('count', 0):,}"

            status_indicators = []
            if data.get("is_private"):
                status_indicators.append("🔒")
            if data.get("is_verified"):
                status_indicators.append("<:Verified:1302156329502375968>")
            if data.get("is_joined_recently"):
                status_indicators.append("<:newjoin:1326569644693127234>")

            bio_links = data.get("bio_links", [])
            b = f"🔗 {len(bio_links)}" if bio_links else None

            status_suffix = (
                f" {' '.join(status_indicators)}" if status_indicators else ""
            )

            embed_description = f"**[{data.get('full_name')} (@{data.get('username')})]({url})**{status_suffix}\n{data.get('biography', '')}"

            if b:
                embed_description += f"\n [{b}]({url})"

            embed = Embed(description=embed_description, color=self.bot.color)

            embed.add_field(
                name="Posts",
                value=f"{data.get('edge_owner_to_timeline_media', {}).get('count', 0):,}",
                inline=True,
            )
            embed.add_field(name="Followers", value=followers, inline=True)
            embed.add_field(name="Following", value=following, inline=True)

            if profile_pic := data.get("profile_pic_url_hd"):
                embed.set_thumbnail(url=profile_pic)

            embed.set_author(
                name=ctx.author.name,
                icon_url=(
                    ctx.author.avatar.url
                    if ctx.author.avatar
                    else ctx.author.default_avatar.url
                ),
            )
            embed.set_footer(
                text="Instagram",
                icon_url="https://www.instagram.com/static/images/ico/favicon-192.png/68d99ba29cc8.png",
            )

            await ctx.send(embed=embed)
        else:
            await ctx.fail(
                f"Could not fetch Instagram profile for {username}. Error: {error}"
            )

    @commands.command(
        name="igstory",
        aliases=["igstories"],
        brief="Fetch Instagram stories.",
        example=",igstory wohtour",
    )
    @commands.is_owner()
    async def igstory(self, ctx: Context, username: str):
        """Fetch Instagram stories."""
        stories = await fetch_instagram_stories(username)
        if stories:
            for story in stories:
                await ctx.send(story)
        else:
            await ctx.fail(f"Could not fetch Instagram stories for {username}.")

    @commands.group(
        name="fortnite",
    )
    async def fortnite(self, ctx: Context):
        """Fortnite related commands."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @fortnite.command(
        name="shop",
        aliases=["store"],
        brief="Display the current Fortnite shop.",
    )
    async def fortnite_shop(self, ctx: Context):
        """Display the current Fortnite shop."""
        embed = Embed(title="Fortnite Item Shop", color=self.bot.color)
        embed.set_image(url=self.shop_url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Socials(bot))
