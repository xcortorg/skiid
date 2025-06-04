from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import swag


async def setup(bot: "swag") -> None:
    from .moderation import Moderation

    await bot.add_cog(Moderation(bot))
