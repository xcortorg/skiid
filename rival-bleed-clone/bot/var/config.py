from discord import Intents
from dotenv import load_dotenv
import os

load_dotenv(verbose=True)
CONFIG = {
    "prefix": ",",
    "token": "",
    "owners": {},
    "emoji_guild_id": 1296957636243226716,
    "emojis": {
    },
    "colors": {
        "success": 9493096,
        "warning": 15111941,
        "fail": 16737380,
        "bleed": None,
    },
    "Authorization": {
        "lastfm": {
            "default": "",
            "default_secret": "",
            "login": "",
            "secret": "",
        },
        "eros": "",
        "rival_api": "",
    },
    "domain": "https://",
    "invite_code": "",
    "slow_chunk": False,
}
