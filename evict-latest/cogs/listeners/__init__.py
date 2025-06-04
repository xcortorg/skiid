from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .listeners import Listeners

    await bot.add_cog(Listeners(bot))
