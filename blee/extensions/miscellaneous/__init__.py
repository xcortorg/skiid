from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import Bleed


async def setup(bot: "Bleed"):
    from .miscellaneous import Miscellaneous

    await bot.add_cog(Miscellaneous(bot))
