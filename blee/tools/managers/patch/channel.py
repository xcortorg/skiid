from copy import copy
from io import BytesIO, StringIO

import config
from cashews import cache
from discord import Embed, File, Message
from discord.abc import Messageable
from discord.channel import TextChannel
from tools.utilities.text import shorten


async def neutral(
    self,
    content: str,
    color: int = config.Color.neutral,
    emoji: str = "",
    **kwargs,
) -> Message:
    return await self.send(
        embed=Embed(
            color=color,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


async def approve(
    self, content: str, emoji: str = config.Emoji.approve, **kwargs
) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.approve,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


async def warn(self, content: str, emoji: str = config.Emoji.warn, **kwargs) -> Message:
    return await self.send(
        embed=Embed(
            color=config.Color.error,
            description=f"{emoji} {content}",
        ),
        **kwargs,
    )


async def send(self, *args, **kwargs):
    kwargs["files"] = kwargs.get("files") or []
    if file := kwargs.pop("file", None):
        kwargs["files"].append(file)

    if embed := kwargs.get("embed"):
        if not embed.color:
            embed.color = config.Color.neutral
        if embed.title:
            embed.title = shorten(embed.title, 256)
        if embed.description:
            embed.description = shorten(embed.description, 4096)
        if hasattr(embed, "_attachments") and embed._attachments:
            for attachment in embed._attachments:
                if isinstance(attachment, File):
                    kwargs["files"].append(
                        File(copy(attachment.fp), filename=attachment.filename)
                    )
                elif isinstance(attachment, tuple):
                    response = await self._state._get_client().session.get(
                        attachment[0]
                    )
                    if response.status == 200:
                        kwargs["files"].append(
                            File(
                                BytesIO(await response.read()),
                                filename=attachment[1],
                            )
                        )

    elif embeds := kwargs.get("embeds"):
        for embed in embeds:
            if not embed.color:
                embed.color = config.Color.neutral
            if embed.title:
                embed.title = shorten(embed.title, 256)
            if embed.description:
                embed.description = shorten(embed.description, 4096)
            if hasattr(embed, "_attachments") and embed._attachments:
                for attachment in embed._attachments:
                    if isinstance(attachment, File):
                        kwargs["files"].append(
                            File(
                                copy(attachment.fp),
                                filename=attachment.filename,
                            )
                        )
                    elif isinstance(attachment, tuple):
                        response = await self._state._get_client().session.get(
                            attachment[0]
                        )
                        if response.status == 200:
                            kwargs["files"].append(
                                File(
                                    BytesIO(await response.read()),
                                    filename=attachment[1],
                                )
                            )

    if content := (args[0] if args else kwargs.get("content")):
        content = str(content)
        if len(content) > 4000:
            kwargs["content"] = f"Response too large to send (`{len(content)}/4000`)"
            kwargs["files"].append(
                File(
                    StringIO(content),
                    filename="reiResult.txt",
                )
            )
            if args:
                args = args[1:]

    return await Messageable.send(self, *args, **kwargs)


TextChannel.send = send
TextChannel.neutral = neutral
TextChannel.approve = approve
TextChannel.warn = warn
