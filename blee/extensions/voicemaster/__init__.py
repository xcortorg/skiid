from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools import Bleed


async def setup(bot: "Bleed"):
    from .voicemaster import VoiceMaster

    await bot.add_cog(VoiceMaster(bot))
