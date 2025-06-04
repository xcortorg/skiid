from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Literal, Optional, Union

from discord import Color
from discord.utils import utcnow
from pydantic import BaseModel

import config
from main import Evict


class Config:
    def __init__(
        self,
        user_id: int,
        username: str,
        color: Optional[int] = None,
        reactions: Optional[List[str]] = None,
        embed_mode: Optional[str] = None,
        command: Optional[str] = None,
        web_authentication: bool = False,
        access_token: Optional[str] = None,
        last_indexed: Optional[datetime] = None,
    ) -> None:
        self.user_id: int = user_id
        self.username: str = username
        self.color: Optional[int] = color
        self.reactions: Optional[List[str]] = reactions
        self.embed_mode: Optional[str] = embed_mode
        self.command: Optional[str] = command
        self.web_authentication: bool = web_authentication
        self.access_token: Optional[str] = access_token
        self.last_indexed: datetime = last_indexed or utcnow()

    @property
    def should_index(self) -> bool:
        return self.last_indexed < utcnow() - timedelta(hours=24)

    @property
    def embed_color(self) -> Color:  # sourcery skip: assign-if-exp, reintroduce-else
        if self.color in (None, 1337):
            return config.COLORS.APPROVE

        return Color(self.color)

    @property
    def reactions_disabled(self) -> bool:
        return "disabled" in self.reactions

    @classmethod
    async def fetch(cls, bot: Evict, user_id: int) -> Optional[Config]:
        record = await bot.db.fetchrow(
            """
            SELECT *
            FROM lastfm.config
            WHERE user_id = $1
            """,
            user_id,
        )
        if not record:
            return

        return cls(**record)
