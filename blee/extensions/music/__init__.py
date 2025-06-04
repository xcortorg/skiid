from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import Bleed


async def setup(bot: "Bleed"):
    from .music import Music

    await bot.add_cog(Music(bot))
