from .sendhook import Sendhook


async def setup(bot):
    await bot.add_cog(Sendhook())
