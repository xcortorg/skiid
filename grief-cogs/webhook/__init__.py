import json
from pathlib import Path

from .webhook import Webhook


async def setup(bot):
    cog = Webhook(bot)
    await bot.add_cog(cog)
