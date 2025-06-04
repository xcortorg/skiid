from __future__ import annotations

from json import loads
from typing import Optional
from urllib.parse import quote_plus

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from pydantic import BaseModel


class Rank(BaseModel):
    name: str
    image_url: str
    value: Optional[int]


class Overview(BaseModel):
    wins: int
    kills: int
    deaths: int
    assists: int
    kd_ratio: float
    win_percentage: float
    matches_played: int
    time_played: str


class Accuracy(BaseModel):
    head: int
    body: int
    legs: int
    headshot_percentage: float


class Model(BaseModel):
    region: str
    name: str
    tagline: str
    level: int
    avatar_url: str
    rank: Rank
    overview: Overview
    accuracy: Accuracy

    @property
    def url(self) -> str:
        return f"https://tracker.gg/valorant/profile/riot/{quote_plus(f'{self.name}#{self.tagline}')}/overview"

    @classmethod
    async def from_username(
        cls,
        session: ClientSession,
        username: str,
        tagline: str,
    ) -> Optional[Model]:
        async with session.get(
            f"https://tracker.gg/valorant/profile/riot/{username}%23{tagline}/overview",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36"
                ),
            },
        ) as response:
            print(response.status, await response.text())

            data = await response.text()
            soup = BeautifulSoup(data, "lxml")

            script: Optional[dict] = next(
                (
                    loads(
                        _script.text.split("window.__INITIAL_STATE__ = ")[1].split(
                            ";\n"
                        )[0]
                    )
                    for _script in soup.find_all("script")
                    if "window.__INITIAL_STATE__" in _script.text
                ),
                None,
            )
            if not script:
                return

            user = script["stats"]["standardProfiles"][0]
            if not user["segments"]:
                return

            return cls(
                region=user["metadata"]["activeShard"].upper(),
                name=user["platformInfo"]["platformUserHandle"].split("#")[0],
                tagline=user["platformInfo"]["platformUserHandle"].split("#")[1],
                level=user["metadata"]["accountLevel"],
                avatar_url=user["platformInfo"]["avatarUrl"],
                rank=Rank(
                    name=user["segments"][0]["stats"]["rank"]["metadata"]["tierName"],
                    value=user["segments"][0]["stats"]["rank"]["value"],
                    image_url=user["segments"][0]["stats"]["rank"]["metadata"][
                        "iconUrl"
                    ],
                ),
                overview=Overview(
                    wins=user["segments"][0]["stats"]["matchesWon"]["value"],
                    kills=user["segments"][0]["stats"]["kills"]["value"],
                    deaths=user["segments"][0]["stats"]["deaths"]["value"],
                    assists=user["segments"][0]["stats"]["assists"]["value"],
                    kd_ratio=user["segments"][0]["stats"]["kDRatio"]["value"],
                    win_percentage=user["segments"][0]["stats"]["matchesWinPct"][
                        "value"
                    ],
                    matches_played=user["segments"][0]["stats"]["matchesPlayed"][
                        "value"
                    ],
                    time_played=user["segments"][0]["stats"]["timePlayed"][
                        "displayValue"
                    ],
                ),
                accuracy=Accuracy(
                    head=user["segments"][0]["stats"]["dealtHeadshots"]["value"],
                    body=user["segments"][0]["stats"]["dealtBodyshots"]["value"],
                    legs=user["segments"][0]["stats"]["dealtLegshots"]["value"],
                    headshot_percentage=user["segments"][0]["stats"][
                        "headshotsPercentage"
                    ]["value"],
                ),
            )
