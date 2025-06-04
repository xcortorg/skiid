from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .moderation import Moderation

    await bot.add_cog(Moderation(bot))
