import re
from var.variables import INSTAGRAM_POST

TIKTOK = [
    re.compile(
        r"(?:http\:|https\:)?\/\/(?:www\.)?tiktok\.com\/@.*\/(?:photo|video)\/\d+"
    ),
    re.compile(r"(?:http\:|https\:)?\/\/(?:www|vm|vt|m).tiktok\.com\/(?:t/)?(\w+)"),
]
