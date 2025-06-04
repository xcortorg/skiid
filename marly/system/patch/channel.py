from copy import copy
from io import BytesIO, StringIO

from discord import Embed, File, Message
from discord.abc import Messageable
from discord.channel import TextChannel

import config
from system.tools.utils import shorten_lower as shorten
from cashews import cache


async def neutral(
    self,
    content: str,
    color: int = config.Color.neutral,
    emoji: str = "",
    **kwargs,
) -> Message:
    return await self.send(
        embed=Embed(
            color=color,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


async def approve(
    self, content: str, emoji: str = config.Emojis.Embeds.APPROVE, **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.approve,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


async def warn(
    self, content: str, emoji: str = config.Emojis.Embeds.WARN, **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.error,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


TextChannel.neutral = neutral
TextChannel.approve = approve
TextChannel.warn = warn
