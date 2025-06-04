from .defender import Defender


async def setup(bot):
    await bot.add_cog(Defender(bot))
