import json
from pathlib import Path

from .extendedmodlog import ExtendedModLog


async def setup(bot):
    cog = ExtendedModLog(bot)
    await bot.add_cog(cog)
