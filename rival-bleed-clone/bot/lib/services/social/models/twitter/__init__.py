from http.cookiejar import MozillaCookieJar
from json import loads
from pathlib import Path
from typing import Literal, Optional

from aiohttp import ClientSession as _ClientSession
from pydantic import BaseModel

#  This file is in the same directory as config.json
path = Path(__file__).parent / "api.json"
API = loads(path.read_text())


# jar = MozillaCookieJar()
# jar.load("cookies.txt")


class ClientSession(_ClientSession):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            **kwargs,
        )
        self.headers.update(
            {
                "Cookie": "guest_id=v1%3A163519131615142822; kdt=dGB7SfUPKd3OrrnASFrmXzaoRVOEwodvrPetTKqS; twid=u%3D247051251; auth_token=12a8e074d3f45bec8e665f3bfd3e6a0f7ff52a0d; ct0=4d22e1f52cd8f01c9acfd59114a937ec533d46a1c9efe08ff394bdf00bad17234b97a57e5d6db9d5244a1ae65fb3fba394fa871f415b88b4267f05dea26b45ef12a51e09db284df1bed6ff324c975a60; lang=en",
                "Sec-Ch-Ua": """-Not.A/Brand"";v=""8"", ""Chromium"";v=""102""",
                "X-Twitter-Client-Language": "en",
                "X-Csrf-Token": "4d22e1f52cd8f01c9acfd59114a937ec533d46a1c9efe08ff394bdf00bad17234b97a57e5d6db9d5244a1ae65fb3fba394fa871f415b88b4267f05dea26b45ef12a51e09db284df1bed6ff324c975a60",
                "Sec-Ch-Ua-Mobile": "?0",
                "Authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.63 Safari/537.36",
                "X-Twitter-Auth-Type": "OAuth2Session",
                "X-Twitter-Active-User": "yes",
                "Sec-Ch-Ua-Platform": """macOS""",
                "Accept": "*/*",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://twitter.com/markus",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            }
        )

    # async def __aenter__(self):
    #     resp = await self.post("https://api.twitter.com/1.1/guest/activate.json")
    #     json = await resp.json()
    #     self.headers.update(
    #         {
    #             "content-type": "application/json",
    #             "x-guest-token": json["guest_token"],
    #             "x-twitter-active-user": "yes",
    #         }
    #     )
    #     return self
