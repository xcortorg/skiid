import json
from pathlib import Path

from grief.core.bot import Grief

from .customhelp import CustomHelp


async def setup(bot: Grief) -> None:
    cog = CustomHelp(bot)
    await bot.add_cog(cog)
