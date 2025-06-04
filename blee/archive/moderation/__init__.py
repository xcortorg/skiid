from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import Bleed


async def setup(bot: "Bleed"):
    from .moderation import Moderation

    await bot.add_cog(Moderation(bot))
