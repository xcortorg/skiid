from loguru import logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from modules.evelinabot import Evelina

class Cache:
    def __init__(self):
        self.log_emoji = False
        self.prefixes = {}
        self.bot = None

    def initialize(self, bot):
        self.bot = bot
        return self

    async def initialize_settings_cache(self):
        logger.info("Caching settings...")
        prefixes = await self.bot.db.fetch("SELECT guild_id, prefix FROM prefix")
        if prefixes:
            for guild_id, prefix in prefixes:
                self.prefixes[str(guild_id)] = prefix