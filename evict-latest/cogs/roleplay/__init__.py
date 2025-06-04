from typing import TYPE_CHECKING

from yarl import URL

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .roleplay import Roleplay

    await bot.add_cog(Roleplay(bot))
