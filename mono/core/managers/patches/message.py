import config
from discord import Embed
from discord import Message as MessageSuper
from discord.message import Message


async def neutral(self, content: str, **kwargs) -> Message:
    return await self.channel.send(
        embed=Embed(
            color=config.Color.base,
            description=f"{self.author.mention}: {content}",
        ),
        reference=self,
        **kwargs,
    )


MessageSuper.neutral = neutral
