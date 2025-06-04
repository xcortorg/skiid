from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import greed


async def setup(bot: "greed") -> None:
    from .hog import Hog

    await bot.add_cog(Hog(bot))
