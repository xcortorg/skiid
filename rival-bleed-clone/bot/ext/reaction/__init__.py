from .commands import Commands
from .events import Events
from discord import Client


class Reaction(Commands, Events):
    def __init__(self, bot: Client):
        Events.__init__(self, bot)
        Commands.__init__(self, bot)


async def setup(bot: Client):
    await bot.add_cog(Reaction(bot))
