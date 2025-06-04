from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import Bleed


async def setup(bot: "Bleed"):
    from .developer import Developer

    await bot.add_cog(Developer(bot))
