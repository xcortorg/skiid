from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from system import Marly


async def setup(bot: "Marly"):
    from .utility import Utility

    await bot.add_cog(Utility(bot))
