from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from aiohttp import ClientSession
from pydantic import BaseModel

from config import AUTHORIZATION


class Model(BaseModel):
    user_id: int
    username: str
    join_date: datetime
    count300: float
    count100: float
    count50: float
    playcount: float
    ranked_score: int
    total_score: int
    pp_rank: float
    level: float
    pp_raw: float
    accuracy: float
    count_rank_ss: int
    count_rank_ssh: int
    count_rank_s: int
    count_rank_sh: int
    count_rank_a: int
    country: str
    total_seconds_played: int
    pp_country_rank: int
    events: List
    map: str

    @property
    def url(self) -> str:
        return f"https://osu.ppy.sh/users/{self.user_id}"

    @property
    def avatar_url(self) -> str:
        return f"https://a.ppy.sh/{self.user_id}"

    @classmethod
    async def from_username(
        cls,
        session: ClientSession,
        username: str,
        *,
        map: int = 0,
    ) -> Optional[Model]:
        async with session.get(
            "https://osu.ppy.sh/api/get_user",
            params={
                "k": AUTHORIZATION.OSU,
                "m": min(map, 3),
                "u": username,
            },
        ) as response:
            data = await response.json()

            return data and cls(
                **data[0],
                map={
                    0: "Standard",
                    1: "Taiko",
                    2: "Catch the Beat",
                    3: "Mania",
                }[min(map, 3)],
            )
