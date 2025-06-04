from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import Bleed


async def setup(bot: "Bleed"):
    from .information import Information

    await bot.add_cog(Information(bot))
