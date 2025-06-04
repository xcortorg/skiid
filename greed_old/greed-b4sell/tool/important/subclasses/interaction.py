from discord import Embed, Interaction
from discord.voice_client import VoiceProtocol
from typing import Optional
from typing_extensions import Self


class GreedInteraction(Interaction):
    def __init__(self: Self):
        super().__init__()

    @property
    def voice_client(self: Self) -> Optional[VoiceProtocol]:
        r"""Optional[:class:`.VoiceProtocol`]: A shortcut to :attr:`.Guild.voice_client`\, if applicable."""
        return self.guild.voice_client if self.guild else None

    async def success(self: Self, text: str, **kwargs) -> None:
        ephemeral = kwargs.pop("ephemeral", True)
        kwargs["ephemeral"] = ephemeral
        color = 0x2B2D31
        emoji = kwargs.pop("emoji", "")
        embed = Embed(color=color, description=f"> {emoji} {self.user.mention}: {text}")
        if footer := kwargs.pop("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.pop("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after", None):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.pop("return_embed", False) is True:
            return embed
        return await self.response.send_message(embed=embed, **kwargs)

    async def normal(self: Self, text: str, **kwargs):
        color = 0x2B2D31
        emoji = kwargs.pop("emoji", "")
        ephemeral = kwargs.pop("ephemeral", True)
        embed = Embed(color=color, description=f"> {emoji} {self.user.mention}: {text}")
        if footer := kwargs.get("footer", None):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author", None):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        if kwargs.get("return_embed", False) is True:
            return embed
        return await self.response.send_message(
            embed=embed, delete_after=delete_after, ephemeral=ephemeral
        )

    async def fail(self: Self, text: str, **kwargs):
        color = 0x2B2D31
        ephemeral = kwargs.pop("ephemeral", True)
        emoji = kwargs.pop("emoji", "")
        embed = Embed(color=color, description=f"> {emoji} {self.user.mention}: {text}")
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if kwargs.get("return_embed", False) is True:
            return embed
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        return await self.response.send_message(
            embed=embed, delete_after=delete_after, ephemeral=ephemeral
        )

    async def warning(self: Self, text: str, **kwargs):
        emoji = kwargs.pop("emoji", None)
        ephemeral = kwargs.pop("ephemeral", True)
        embed = Embed(
            color=0xFFA500,
            description=f"> {emoji or '<:greedwarning:1234264951091105843>'} {self.user.mention}: {text}",
        )
        if footer := kwargs.get("footer"):
            if isinstance(footer, tuple):
                embed.set_footer(text=footer[0], icon_url=footer[1])
            else:
                embed.set_footer(text=footer)
        if author := kwargs.get("author"):
            if isinstance(author, tuple):
                embed.set_author(name=author[0], icon_url=author[1])
            else:
                embed.set_author(name=author)
        if kwargs.get("return_embed", False) is True:
            return embed
        if delete_after := kwargs.get("delete_after"):
            delete_after = delete_after
        else:
            delete_after = None
        return await self.response.send_message(
            embed=embed, delete_after=delete_after, ephemeral=ephemeral
        )
