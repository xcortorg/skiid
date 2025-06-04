from .linkquoter import LinkQuoter


async def setup(bot):
    cog = LinkQuoter(bot)
    await bot.add_cog(cog)
