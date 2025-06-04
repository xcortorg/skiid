from typing import TYPE_CHECKING

from .core.converters import Percentage, Position
from .core.player import Client

if TYPE_CHECKING:
    from main import swag


async def setup(bot: "swag") -> None:
    from .audio import Audio

    await bot.add_cog(Audio(bot))


__all__ = (
    "Client",
    "Percentage",
    "Position",
    "setup",
)
