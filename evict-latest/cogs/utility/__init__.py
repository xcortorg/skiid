from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .utility import Utility

    await bot.add_cog(Utility(bot))
