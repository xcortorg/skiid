from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from system import Marly


async def setup(bot: "Marly"):
    from .server import Server

    await bot.add_cog(Server(bot))
