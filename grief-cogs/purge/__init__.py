from typing import List

from grief.core.bot import Grief
from grief.core.errors import CogLoadError

from .core import Purge

conflicting_cogs: List[str] = ["Cleanup"]


async def setup(bot: Grief) -> None:
    for cog_name in conflicting_cogs:
        if bot.get_cog(cog_name):
            raise CogLoadError(
                f"This cog conflicts with {cog_name} and both cannot be loaded at the same time."
            )

    cog = Purge(bot)
    await bot.add_cog(cog)
