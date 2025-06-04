from typing import Any, Dict, Union

from discord import Embed, Message, WebhookMessage
from discord.ext.commands import Context


class ResentContext(Context):
    flags: Dict[str, Any] = {}

    def __init__(self, **kwargs):
        """Custom commands.Context for the bot"""
        self.ec_emoji = "🏦"
        self.ec_color = 0xD3D3D3
        super().__init__(**kwargs)

    def __str__(self):
        return f"resent bot here in {self.channel.mention}"

    async def reskin_enabled(self) -> bool:
        return (
            await self.bot.db.fetchrow(
                "SELECT * FROM reskin_enabled WHERE guild_id = $1", self.guild.id
            )
            is not None
        )

    async def reply(self, *args, **kwargs) -> Union[Message, WebhookMessage]:
        return await self.send(*args, **kwargs)

    async def has_reskin(self) -> bool:
        """check if the author has a reskin or not"""
        return (
            await self.bot.db.fetchrow(
                "SELECT * FROM reskin WHERE user_id = $1", self.author.id
            )
            is not None
        )

    async def send_warning(self, message: str) -> Message:
        """Send a warning message to the channel"""
        return await self.send(
            embed=Embed(
                color=self.bot.warning_color,
                description=f"{self.bot.warning} {self.author.mention}: {message}",
            )
        )

    async def send_error(self, message: str) -> Message:
        """Send an error message to the channel"""
        return await self.send(
            embed=Embed(
                color=self.bot.no_color,
                description=f"{self.bot.no} {self.author.mention}: {message}",
            )
        )

    async def send_success(self, message: str) -> Message:
        """Send a success message to the channel"""
        return await self.send(
            embed=Embed(
                color=self.bot.yes_color,
                description=f"{self.bot.yes} {self.author.mention}: {message}",
            )
        )

    async def resent_send(self, message: str, **kwargs) -> Message:
        """Send a regular embed message to the channel"""
        return await self.send(
            embed=Embed(
                color=self.bot.color, description=f"{self.author.mention}: {message}"
            ),
            **kwargs,
        )

    async def lastfm_send(self, message: str, reference: Message = None) -> Message:
        """Send a lastfm type message to the channel"""
        return await self.send(
            embed=Embed(
                color=0xFF0000,
                description=f"<:lastfm:1188946307704959079> {self.author.mention}: {message}",
            )
        )
