from contextlib import suppress

import config
from discord import Embed, InteractionResponded, WebhookMessage
from discord.interactions import Interaction


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
    self, content: str, emoji: str = config.Emoji.approve, **kwargs
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
    self, content: str, emoji: str = config.Emoji.warn, **kwargs
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
