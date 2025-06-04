from .base import *  # noqa: F403
from .tiktok import TikTok
from .twitter import Twitter
from .youtube import YouTube
from .instagram import Instagram
from .twitch import Twitch
from .kick import Kick

FEEDS = [TikTok, Twitter, YouTube, Twitch, Kick, Instagram]
