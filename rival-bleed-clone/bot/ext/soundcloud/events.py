from discord.ext.commands import Cog
from discord import Client


class Events(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
