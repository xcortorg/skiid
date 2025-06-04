from grief.core.bot import Grief

from .downloader import Downloader


async def setup(bot: Grief) -> None:
    cog = Downloader(bot)
    await bot.add_cog(cog)
    cog.create_init_task()
