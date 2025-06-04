from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .owner import Owner

    await bot.add_cog(Owner(bot))
