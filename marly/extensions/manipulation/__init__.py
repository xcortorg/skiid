from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from system import Marly


async def setup(bot: "Marly"):
    from .manipulation import Manipulation

    await bot.add_cog(Manipulation(bot))
