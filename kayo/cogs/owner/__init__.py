from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import swag


async def setup(bot: "swag") -> None:
    from .owner import Owner

    await bot.add_cog(Owner(bot))
