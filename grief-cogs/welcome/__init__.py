import json
from pathlib import Path

from .welcome import Welcome


async def setup(bot):
    n = Welcome(bot)
    await bot.add_cog(n)
