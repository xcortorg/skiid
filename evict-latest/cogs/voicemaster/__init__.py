from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Evict


async def setup(bot: "Evict") -> None:
    from .voicemaster import VoiceMaster

    await bot.add_cog(VoiceMaster(bot))
