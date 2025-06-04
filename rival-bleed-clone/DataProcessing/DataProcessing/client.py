from .services import (
    BingService,
    TranslationService,
    InstagramService,
    WikipediaService,
    FandomService,
    DuckDuckGoService,
    KickService,
    YouTubeService,
    SoundCloudService,
    BraveService,
    TikTokService,
    BlackBoxService,
    TwitterService,
    GoogleService,
    PinterestService,
    TwitchService,
    IPService,
)
from .models.authentication import Credentials
from typing import Optional
from redis.asyncio import Redis


class ServiceManager:
    def __init__(
        self: "ServiceManager",
        redis: Redis,
        credentials: Credentials,
        ttl: Optional[int] = None,
    ):
        self.credentials = credentials
        self.redis = redis
        self.ttl = ttl
        self.bing = BingService(self.redis, self.ttl)
        self.translation = TranslationService(self.redis, self.ttl)
        self.instagram = InstagramService(
            self.redis, self.credentials.instagram, self.ttl
        )
        self.wikipedia = WikipediaService(self.redis, self.ttl)
        self.fandom = FandomService(self.redis, self.ttl)
        self.duckduckgo = DuckDuckGoService(self.redis, self.ttl)
        self.kick = KickService(self.redis, self.ttl)
        self.soundcloud = SoundCloudService(self.redis, self.ttl)
        self.youtube = YouTubeService(self.redis, self.ttl)
        self.brave = BraveService(self.redis, self.ttl)
        self.tiktok = TikTokService(self.redis, self.ttl)
        self.blackbox = BlackBoxService(self.redis, self.ttl)
        self.google = GoogleService(self.redis, self.ttl)
        self.tiktok = TikTokService(self.redis, self.ttl)
        self.pinterest = PinterestService(self.redis, self.ttl)
        self.twitter = TwitterService(self.redis, self.ttl)
        self.twitch = TwitchService(self.redis, self.ttl)
        self.ip = IPService(self.redis, self.ttl)
