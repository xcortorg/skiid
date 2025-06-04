from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from system import Marly


async def setup(bot: "Marly"):
    from .welcome import Welcome

    await bot.add_cog(Welcome(bot))
