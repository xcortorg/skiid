from .commands import Commands
from .events import Events
from discord import Client
from .asset import Asset
from .birthday import Birthday


class Information(Commands, Events, Asset):  # , GuildStats):
    def __init__(self, bot: Client):
        Events.__init__(self, bot)
        Commands.__init__(self, bot)
        Asset.__init__(self, bot)
        Birthday.__init__(self, bot)


async def setup(bot: Client):
    await bot.add_cog(Information(bot))
