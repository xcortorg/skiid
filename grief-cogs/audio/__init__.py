from grief.core.bot import Grief

from .core import Audio


async def setup(bot: Grief) -> None:
    cog = Audio(bot)
    await bot.add_cog(cog)
    cog.start_up_task()
