from grief.core.bot import Grief

from .embedcreator import EmbedCreator


async def setup(bot: Grief):
    await bot.add_cog(EmbedCreator(bot))
