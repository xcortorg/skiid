from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import greed


async def setup(bot: "greed") -> None:
    from .fun import Fun

    await bot.add_cog(Fun(bot))