import discord
from typing import Any, List, Optional


async def normal(self: discord.TextChannel, text: str, **kwargs: Any):
    color = kwargs.pop("color", 0x6E879C)
    emoji = kwargs.pop("emoji", "")
    embed = discord.Embed(color=color, description=f"{emoji} {text}")
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
    if delete_after := kwargs.get("delete_after"):
        delete_after = delete_after
    else:
        delete_after = None
    if kwargs.pop("return_embed", False) is True:
        return embed
    return await self.send(embed=embed, **kwargs)


discord.TextChannel.normal = normal


async def archive_pins(
    self: discord.TextChannel,
    destination: discord.TextChannel,
    unpin: Optional[bool] = False,
) -> List[discord.Message]:
    def to_embed(pin: discord.Message) -> discord.Embed:
        embed = discord.Embed(color=self._state._get_client().color)
        embed.set_author(name=str(pin.author), icon_url=pin.author.display_avatar.url)
        embed.timestamp = pin.created_at
        embed.description = f"{pin.clean_content}"
        if pin.attachments:
            if len(pin.attachments) == 1:
                embed.set_image(url=pin.attachments[0].url)
            else:
                if len(pin.content) == 0:
                    for i, attachment in enumerate(pin.attachments, start=1):
                        embed.description += (
                            f"**Attachment {i}**\n[Link]({attachment.proxy_url})\n"
                        )
        embed.set_footer(text=f"Pinned in #{pin.channel.name}")
        return embed

    pins = []
    for pin in await self.pins():
        if unpin:
            await pin.unpin()
        await destination.send(embed=to_embed(pin))
        pins.append(pin)
    return pins


discord.TextChannel.archive_pins = archive_pins
