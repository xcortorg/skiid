from .instagram import Instagram
from .instagram_story import InstagramStory
from .medal import Medal
from .pinterest import Pinterest
from .reddit import Reddit

# from .soundcloud import SoundCloud
from .streamable import Streamable
from .tiktok import TikTok
from .twitch import Twitch
from .youtube import YouTube

reposters = [
    TikTok,
    YouTube,
    Reddit,
    Instagram,
    InstagramStory,
    # SoundCloud,
    Twitch,
    Medal,
    Pinterest,
    Streamable,
]
