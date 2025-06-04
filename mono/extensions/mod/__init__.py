from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.Mono import Mono


async def setup(bot: "Mono"):
    from .moderation import Moderation

    await bot.add_cog(Moderation(bot))
