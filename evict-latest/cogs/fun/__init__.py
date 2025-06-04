from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .fun import Fun

    await bot.add_cog(Fun(bot))
