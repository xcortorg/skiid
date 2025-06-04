from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import swag


async def setup(bot: "swag") -> None:
    from .social import Social

    await bot.add_cog(Social(bot))
