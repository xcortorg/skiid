import contextlib
import importlib
import json
from pathlib import Path

from grief.core import VersionInfo
from grief.core.bot import Grief

from . import vexutils
from .birthday import Birthday


async def setup(bot: Grief) -> None:
    cog = Birthday(bot)
    await bot.add_cog(cog)
