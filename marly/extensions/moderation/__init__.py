from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from system import Marly


async def setup(bot: "Marly"):
    from .moderation import Moderation

    await bot.add_cog(Moderation(bot))
