from .menus import AvatarPages, BaseView, GuildPages, ListPages
from .owner import Owner


async def setup(bot):
    await bot.add_cog(Owner(bot))
