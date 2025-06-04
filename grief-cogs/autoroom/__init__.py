"""Package for AutoRoom cog."""

import json
from pathlib import Path

from grief.core.bot import Grief

from .autoroom import AutoRoom


async def setup(bot: Grief) -> None:
    """Load AutoRoom cog."""
    cog = AutoRoom(bot)
    await cog.initialize()
    await bot.add_cog(cog)
