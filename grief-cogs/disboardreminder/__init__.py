from .disboardreminder import DisboardReminder


async def setup(bot):
    cog = DisboardReminder(bot)
    await bot.add_cog(cog)
