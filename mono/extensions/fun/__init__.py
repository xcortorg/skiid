from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.Mono import Mono


async def setup(bot: "Mono") -> None:
    from .fun import Fun

    await bot.add_cog(Fun(bot))
