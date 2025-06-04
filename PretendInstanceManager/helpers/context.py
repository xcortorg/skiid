from discord import Embed, Message
from discord.ext import commands


class Context(commands.Context):
    def __init__(self, *args, **kwargs) -> None:
        return super().__init__(*args, **kwargs)

    async def send(self, *args, **kwargs) -> Message:
        return await super().send(*args, **kwargs)

    async def send_success(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                description=f"{self.author.mention}: {message}", color=self.bot.color
            ),
            **kwargs,
        )

    async def send_warning(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                description=f"{self.author.mention}: {message}", color=self.bot.color
            ),
            **kwargs,
        )

    async def send_error(self, message: str, **kwargs) -> Message:
        return await self.send(
            embed=Embed(
                description=f"{self.author.mention}: {message}", color=self.bot.color
            ),
            **kwargs,
        )
