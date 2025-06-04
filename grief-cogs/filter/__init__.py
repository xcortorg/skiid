from grief.core.bot import Grief

from .filter import Filter


async def setup(bot: Grief) -> None:
    await bot.add_cog(Filter(bot))
