import json
from pathlib import Path

from .starboard import Starboard


async def setup(bot):
    cog = Starboard(bot)
    await bot.add_cog(cog)
