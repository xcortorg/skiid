from DataProcessing.client import ServiceManager
from discord import Client

async def setup(bot: Client) -> bool:
    bot.services = ServiceManager(bot.redis, None)
    return True