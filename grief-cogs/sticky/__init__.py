"""Sticky - Sticky messages to a channel."""

import asyncio

from grief.core.bot import Grief

from .sticky import Sticky


async def setup(bot: Grief):
    """Load Sticky."""
    cog = Sticky(bot)
    if asyncio.iscoroutinefunction(bot.add_cog):
        await bot.add_cog(cog)
    else:
        bot.add_cog(cog)
