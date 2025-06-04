from .deleter import Deleter


async def setup(bot):
    cog = Deleter(bot)
    await bot.add_cog(cog)
