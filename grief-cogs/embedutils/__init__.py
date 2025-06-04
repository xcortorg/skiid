from .embed import EmbedUtils


async def setup(bot):
    cog = EmbedUtils(bot)
    await bot.add_cog(cog)
