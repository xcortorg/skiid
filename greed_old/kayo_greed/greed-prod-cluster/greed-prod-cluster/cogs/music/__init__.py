from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import greed


async def setup(bot: "greed"):
    from .music import Music

    await bot.add_cog(Music(bot))
