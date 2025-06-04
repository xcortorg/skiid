from grief.core.bot import Grief

from .tools import Admin


async def setup(bot: Grief) -> None:
    await bot.add_cog(Admin(bot))
