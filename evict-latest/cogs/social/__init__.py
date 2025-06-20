from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .social import Social

    await bot.add_cog(Social(bot))
