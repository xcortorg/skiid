from contextlib import suppress

from discord import Embed, InteractionResponded, WebhookMessage
from discord.interactions import Interaction

import config


async def neutral(
    self,
    content: str,
    color: int = config.Color.neutral,
    emoji: str = "",
    **kwargs,
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=color,
            description=f"{emoji} {self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


async def approve(
    self, content: str, emoji: str = config.Emojis.Embeds.APPROVE, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.Color.approve,
            description=f"{emoji} {self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


async def error(
    self, content: str, emoji: str = config.Emojis.Embeds.WARN, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.Color.warn,
            description=f"{emoji} {self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


Interaction.neutral = neutral
Interaction.approve = approve
Interaction.warn = error
