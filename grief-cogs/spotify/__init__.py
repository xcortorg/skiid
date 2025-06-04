from .spotify import Spotify


async def setup(bot):
    cog = Spotify(bot)
    await bot.add_cog(cog)
