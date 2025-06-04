from .commands import MusicCommands
from .events import MusicEvents
from discord import Client


async def setup(bot: Client):
    await bot.add_cog(MusicCommands(bot))
    await bot.add_cog(MusicEvents(bot))
