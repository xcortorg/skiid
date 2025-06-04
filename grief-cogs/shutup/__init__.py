from __future__ import annotations

from .shutup import Shutup


async def setup(bot) -> None:
    n = Shutup(bot)
    await bot.add_cog(n)
