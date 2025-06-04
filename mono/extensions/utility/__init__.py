from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.Mono import Mono


async def setup(bot: "Mono"):
    from .utility import Utility

    await bot.add_cog(Utility(bot))
