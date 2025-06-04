import json
from pathlib import Path

from grief.core.bot import Grief

from .inviteblocklist import InviteBlocklist


async def setup(bot: Grief):
    cog = InviteBlocklist(bot)
    await bot.add_cog(cog)
