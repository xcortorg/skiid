from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .economy import Economy
    from .cards import Yugioh

    await bot.add_cog(Economy(bot))
    await bot.add_cog(Yugioh(bot))