from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import greed


async def setup(bot: "greed") -> None:
    from .voicemaster import VoiceMaster

    await bot.add_cog(VoiceMaster(bot))
