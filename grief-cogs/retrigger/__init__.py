import json
from pathlib import Path

from .retrigger import ReTrigger


async def setup(bot):
    cog = ReTrigger(bot)
    await bot.add_cog(cog)
