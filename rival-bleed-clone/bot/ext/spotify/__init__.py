from .commands import Commands
from discord.ext.commands import Cog
from discord import Client


class Spotify(Commands):
    def __init__(self, bot: Client):
        Commands.__init__(self, bot)


async def setup(bot: Client):
    await bot.add_cog(Spotify(bot))
