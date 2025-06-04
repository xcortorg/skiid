from grief.core.bot import Grief

from .fun import Fun


async def setup(bot: Grief) -> None:
    await bot.add_cog(Fun(bot))
