from autokick.autokick import AutoKick


async def setup(bot):
    await bot.add_cog(AutoKick(bot))
