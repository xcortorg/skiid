from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.Mono import Mono


async def setup(bot: "Mono"):
    from .server import Server

    await bot.add_cog(Server(bot))
