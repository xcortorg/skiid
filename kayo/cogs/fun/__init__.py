from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import swag


async def setup(bot: "swag") -> None:
    from .fun import Fun

    await bot.add_cog(Fun(bot))
