import asyncio
import importlib.util
import logging
from typing import TYPE_CHECKING

from discord import app_commands

from grief.core.errors import CogLoadError

from .say import Say

if TYPE_CHECKING:
    from grief.core.bot import Grief

log = logging.getLogger("grief.say")


async def setup(bot):
    cog = Say(bot)
    await bot.add_cog(cog)
