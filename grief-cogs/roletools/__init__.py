from .roletools import RoleTools


async def setup(bot):
    cog = RoleTools(bot)
    await bot.add_cog(cog)
    if not await cog.config.enable_slash():
        bot.tree.remove_command("role-tools")
