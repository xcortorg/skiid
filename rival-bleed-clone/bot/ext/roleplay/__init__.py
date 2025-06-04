from .commands import Commands
from discord import Client


class Roleplay(Commands):
    def __init__(self, bot: Client):
        Commands.__init__(self, bot)


async def setup(bot: Client):
    await bot.add_cog(Roleplay(bot))
