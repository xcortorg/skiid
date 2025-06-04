from discord import Client
from .commands import Commands


class Manipulation(Commands):
    def __init__(self, bot: Client):
        Commands.__init__(self, bot)


async def setup(bot: Client):
    await bot.add_cog(Manipulation(bot))
