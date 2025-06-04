from grief.core.bot import Grief

from .mod import Mod


async def setup(bot: Grief) -> None:
    cog = Mod(bot)
    await bot.add_cog(Mod(bot))
