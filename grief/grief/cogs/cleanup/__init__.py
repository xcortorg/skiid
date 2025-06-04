from grief.core.bot import Grief

from .cleanup import Cleanup


async def setup(bot: Grief) -> None:
    await bot.add_cog(Cleanup(bot))
