from typing import TYPE_CHECKING

from yarl import URL

if TYPE_CHECKING:
    from main import greed

BASE_URL = URL.build(
    scheme="https",
    host="nekos.best",
)


async def setup(bot: "greed") -> None:
    from .roleplay import Roleplay

    await bot.add_cog(Roleplay(bot))
