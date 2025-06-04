import contextlib
import importlib
import json
from pathlib import Path

from grief.core import VersionInfo
from grief.core.bot import Grief

from . import vexutils
from .cmdlog import CmdLog


async def setup(bot: Grief):
    cog = CmdLog(bot)
    await bot.add_cog(cog)
