from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import greed


async def setup(bot: "greed") -> None:
    from .owner import Owner

    await bot.add_cog(Owner(bot))
