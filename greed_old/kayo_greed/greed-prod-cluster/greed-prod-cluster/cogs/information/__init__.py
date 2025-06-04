from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import greed


async def setup(bot: "greed") -> None:
    from .information import Information

    await bot.add_cog(Information(bot))
