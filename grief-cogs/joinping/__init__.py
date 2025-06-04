import json
from pathlib import Path

from .main import JoinPing


async def setup(bot):
    cog = JoinPing(bot)
    await cog._build_cache()
    await bot.add_cog(cog)
