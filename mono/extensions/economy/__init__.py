from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.Mono import Mono


async def setup(bot: "Mono"):
    from .economy import Economy

    await bot.add_cog(Economy(bot))
