from contextlib import suppress

import config
from discord import Embed, InteractionResponded, WebhookMessage
from discord.interactions import Interaction


async def neutral(
    self, content: str, color: int = config.Color.neutral, emoji: str = "", **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=color,
            description=f"{self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


async def approve(
    self, content: str, emoji: str = config.Emojis.approve, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.Color.approve,
            description=f"{self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


async def warn(
    self, content: str, emoji: str = config.Emojis.warn, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.Color.warn,
            description=f"{self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


async def deny(
    self, content: str, emoji: str = config.Emojis.deny, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.Color.deny,
            description=f"{self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


Interaction.neutral = neutral
Interaction.approve = approve
Interaction.warn = warn
Interaction.deny = deny
