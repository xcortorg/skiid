import config

from contextlib import suppress

from discord import Embed, InteractionResponded, WebhookMessage
from discord import Interaction


async def neutral(
    self, content: str, color: int = config.COLORS.NEUTRAL, emoji: str = "", **kwargs
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
    self, content: str, emoji: str = config.EMOJIS.CONTEXT.APPROVE, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.COLORS.APPROVE,
            description=f"{emoji} {self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


async def warn(
    self, content: str, emoji: str = config.EMOJIS.CONTEXT.WARN, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.COLORS.WARN,
            description=f"{emoji} {self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


async def deny(
    self, content: str, emoji: str = config.EMOJIS.CONTEXT.DENY, **kwargs
) -> WebhookMessage:
    with suppress(InteractionResponded):
        await self.response.defer(
            ephemeral=True,
        )

    return await self.followup.send(
        embed=Embed(
            color=config.COLORS.DENY,
            description=f"{emoji} {self.user.mention}: {content}",
        ),
        ephemeral=True,
        **kwargs,
    )


Interaction.neutral = neutral
Interaction.approve = approve
Interaction.warn = warn
Interaction.deny = deny
