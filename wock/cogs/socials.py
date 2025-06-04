import io

import discord
from aiohttp import ClientSession as Session
from discord.ext import commands
from discord.ext.commands import Context
from tools.pinpostmodels import Model  # type: ignore
from tools.pinterest import Pinterest  # type: ignore
from tuuid import tuuid


class Socials(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.pinterest = Pinterest()


async def setup(bot):
    await bot.add_cog(Socials(bot))
