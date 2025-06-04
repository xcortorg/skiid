import json
from pathlib import Path

from grief.core.bot import Grief

from .baron import Baron


async def setup(bot: Grief) -> None:
    cog = Baron(bot)
    await bot.add_cog(cog)
