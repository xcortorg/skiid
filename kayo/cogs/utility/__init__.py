from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import swag


async def setup(bot: "swag") -> None:
    from .utility import Utility

    await bot.add_cog(Utility(bot))
