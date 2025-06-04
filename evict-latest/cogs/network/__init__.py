from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .network import Network

    await bot.add_cog(Network(bot))
