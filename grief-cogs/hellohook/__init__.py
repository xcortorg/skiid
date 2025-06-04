from grief.core.utils import get_end_user_data_statement

from .hellohook import Hellohook

__red_end_user_data_statement__ = get_end_user_data_statement(__file__)


async def setup(bot):
    await bot.add_cog(Hellohook(bot))
