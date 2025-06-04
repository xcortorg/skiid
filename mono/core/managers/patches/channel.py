import config
from discord import Embed, Message
from discord.channel import TextChannel


async def neutral(
    self, content: str, color: int = config.Color.base, emoji: str = "", **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=color,
            description=f"{content}",
        ),
        **kwargs,
    )


async def approve(
    self, content: str, emoji: str = config.Emojis.approve, **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.approve,
            description=f"{content}",
        ),
        **kwargs,
    )


async def warn(
    self, content: str, emoji: str = config.Emojis.warn, **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.warn,
            description=f"{content}",
        ),
        **kwargs,
    )


async def deny(
    self, content: str, emoji: str = config.Emojis.deny, **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.deny,
            description=f"{content}",
        ),
        **kwargs,
    )


TextChannel.neutral = neutral
TextChannel.approve = approve
TextChannel.warn = warn
TextChannel.deny = deny
