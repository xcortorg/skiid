import re
from aiohttp import ClientSession

TIKTOK_URL_PATTERN = re.compile(
    r"https:\/\/(?:www\.)?tiktok\.com\/@.*?\/(?:video|photo)?\/(\d+)"
)
TIKTOK_MOBILE_PATTERN = re.compile(
    r"https:\/\/(?:www\.)?tiktok\.com\/t\/([a-zA-Z0-9]+)(?:\/)?"
)


async def get_aweme_id(url: str):
    RETURN = None
    match = TIKTOK_URL_PATTERN.match(url)
    if match:
        RETURN = match.groups(1)
        print(type(RETURN))
    elif TIKTOK_MOBILE_PATTERN.match(url):
        NEW_URL = None
        async with ClientSession() as session:
            async with session.request("HEAD", url) as response:
                NEW_URL = str(response.url)
        if NEW_URL:
            match = TIKTOK_URL_PATTERN.match(NEW_URL)
            if match:
                RETURN = match.groups(1)
            else:
                raise ValueError(f"Couldn't find the aweme ID of {NEW_URL}")
        else:
            raise ValueError("could not find a new URL")
    else:
        raise ValueError(f"couldn't match a pattern to {url}")
    if not RETURN:
        raise ValueError("couldn't get an AWEME ID")
    else:
        if isinstance(RETURN, (list, tuple)):
            if len(RETURN) > 1:
                return str(RETURN[1])
            else:
                return str(RETURN[0])
        else:
            return str(RETURN)
