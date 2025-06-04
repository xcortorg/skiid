import os
from typing import Dict, Any


DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "/",
    "Accept-Language": "en-US,en;q=0.5",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}


class Defaults:
    INSTAGRAM_SESSION_ID = os.environ.get("INSTAGRAM_SESSION_ID")
    INSTAGRAM_CSRF_TOKEN = os.environ.get("INSTAGRAM_CSRF_TOKEN")
    INSTAGRAM_APP_ID = os.environ.get("INSTAGRAM_APP_ID")

    YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY")

    TWITTER_AUTH_TOKEN = os.environ.get("TWITTER_AUTH_TOKEN")
    TWITTER_CLIENT_ID = os.environ.get("TWITTER_CLIENT_ID")
    TWITTER_AUTHORIZATION = f"Bearer {os.environ.get('TWITTER_AUTHORIZATION')}"
    TWITTER_CSFR_TOKEN = os.environ.get("TWITTER_CSFR_TOKEN")


JSON = Dict[Any, Any]
