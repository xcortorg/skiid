from __future__ import annotations

import re
from typing import TYPE_CHECKING, Optional, Union, Type

from aiohttp import ClientSession
from discord import Asset, Forbidden, HTTPException, Member, Message, NotFound, User
from discord.ext.commands import (
    BadArgument,
    CommandError,
    MemberConverter,
)
from yarl import URL

import config
from system.tools.utils import human_join

if TYPE_CHECKING:
    from system.base.context import Context

UNICODE_EMOJI = re.compile(
    r"(?:\U0001f1e6[\U0001f1e8-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f2\U0001f1f4\U0001f1f6-\U0001f1fa\U0001f1fc\U0001f1fd\U0001f1ff])|(?:\U0001f1e7[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ef\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1e8[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ee\U0001f1f0-\U0001f1f5\U0001f1f7\U0001f1fa-\U0001f1ff])|(?:\U0001f1e9[\U0001f1ea\U0001f1ec\U0001f1ef\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1ff])|(?:\U0001f1ea[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ed\U0001f1f7-\U0001f1fa])|(?:\U0001f1eb[\U0001f1ee-\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1f7])|(?:\U0001f1ec[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ee\U0001f1f1-\U0001f1f3\U0001f1f5-\U0001f1fa\U0001f1fc\U0001f1fe])|(?:\U0001f1ed[\U0001f1f0\U0001f1f2\U0001f1f3\U0001f1f7\U0001f1f9\U0001f1fa])|(?:\U0001f1ee[\U0001f1e8-\U0001f1ea\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9])|(?:\U0001f1ef[\U0001f1ea\U0001f1f2\U0001f1f4\U0001f1f5])|(?:\U0001f1f0[\U0001f1ea\U0001f1ec-\U0001f1ee\U0001f1f2\U0001f1f3\U0001f1f5\U0001f1f7\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1f1[\U0001f1e6-\U0001f1e8\U0001f1ee\U0001f1f0\U0001f1f7-\U0001f1fb\U0001f1fe])|(?:\U0001f1f2[\U0001f1e6\U0001f1e8-\U0001f1ed\U0001f1f0-\U0001f1ff])|(?:\U0001f1f3[\U0001f1e6\U0001f1e8\U0001f1ea-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f4\U0001f1f5\U0001f1f7\U0001f1fa\U0001f1ff])|\U0001f1f4\U0001f1f2|(?:\U0001f1f4[\U0001f1f2])|(?:\U0001f1f5[\U0001f1e6\U0001f1ea-\U0001f1ed\U0001f1f0-\U0001f1f3\U0001f1f7-\U0001f1f9\U0001f1fc\U0001f1fe])|\U0001f1f6\U0001f1e6|(?:\U0001f1f6[\U0001f1e6])|(?:\U0001f1f7[\U0001f1ea\U0001f1f4\U0001f1f8\U0001f1fa\U0001f1fc])|(?:\U0001f1f8[\U0001f1e6-\U0001f1ea\U0001f1ec-\U0001f1f4\U0001f1f7-\U0001f1f9\U0001f1fb\U0001f1fd-\U0001f1ff])|(?:\U0001f1f9[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ed\U0001f1ef-\U0001f1f4\U0001f1f7\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1ff])|(?:\U0001f1fa[\U0001f1e6\U0001f1ec\U0001f1f2\U0001f1f3\U0001f1f8\U0001f1fe\U0001f1ff])|(?:\U0001f1fb[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ee\U0001f1f3\U0001f1fa])|(?:\U0001f1fc[\U0001f1eb\U0001f1f8])|\U0001f1fd\U0001f1f0|(?:\U0001f1fd[\U0001f1f0])|(?:\U0001f1fe[\U0001f1ea\U0001f1f9])|(?:\U0001f1ff[\U0001f1e6\U0001f1f2\U0001f1fc])|(?:[#*0-9]\uFE0F\u20E3)|(?:\u2764\uFE0F)|(?:\u2122\uFE0F)|(?:\u2611\uFE0F)|(?:\u26A0\uFE0F)|(?:\u2B06\uFE0F)|(?:\u2B07\uFE0F)|(?:\u2934\uFE0F)|(?:\u2935\uFE0F)|[\u2190-\u21ff]"
)

DISCORD_FILE_PATTERN = re.compile(
    r"(?:http\:|https\:)?\/\/.*\.(?P<mime>png|jpg|jpeg|webp|gif|mp4|mp3|mov|wav|ogg|zip|PNG|JPG|JPEG|WEBP|GIF)$"
)


CONTENT_TYPE_FORMATS = {
    "image/": "image",
    "video/": "video",
    "audio/": "audio",
    "application/": "archive",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class PartialAttachment:
    url: str
    buffer: bytes
    filename: str
    content_type: Optional[str]
    format: str

    def __init__(
        self,
        url: Union[URL, Asset, str],
        buffer: bytes,
        filename: Optional[str] = None,
        content_type: Optional[str] = None,
    ):
        self.url = str(url)
        self.buffer = buffer
        self.content_type = content_type
        self.format = self.determine_format(content_type)
        self.extension = content_type.split("/")[-1] if content_type else "bin"
        self.filename = filename or f"unknown.{self.extension}"

    def determine_format(self, content_type: Optional[str]) -> str:
        if content_type:
            for prefix, format_type in CONTENT_TYPE_FORMATS.items():
                if content_type.startswith(prefix):
                    return format_type
        return "unknown"

    def __str__(self) -> str:
        return self.filename

    @property
    def supported_formats(self) -> list[str]:
        return ["image", "video", "audio", "archive"]

    def is_supported_format(self, format_type: str) -> bool:
        return self.format == format_type

    @staticmethod
    async def read(url: Union[URL, str]) -> tuple[bytes, str]:
        async with ClientSession() as client:
            async with client.get(url, proxy=config.PROXY) as resp:
                if resp.content_length and resp.content_length > MAX_FILE_SIZE:
                    raise CommandError("Attachment exceeds the decompression limit!")

                if resp.status != 200:
                    if resp.status == 404:
                        raise NotFound(resp, "asset not found")
                    if resp.status == 403:
                        raise Forbidden(resp, "cannot retrieve asset")
                    raise HTTPException(resp, "failed to get asset")

                return await resp.read(), resp.content_type

    @classmethod
    def get_attachment(cls, message: Message) -> Optional[str]:
        if message.attachments:
            return message.attachments[0].url
        if message.stickers:
            return message.stickers[0].url
        if message.embeds:
            if message.embeds[0].image:
                return message.embeds[0].image.url
            if message.embeds[0].thumbnail:
                return message.embeds[0].thumbnail.url
        return None

    @classmethod
    async def convert(
        cls: Type["PartialAttachment"], ctx: Context, argument: str
    ) -> "PartialAttachment":
        if not (match := re.match(DISCORD_FILE_PATTERN, argument)):
            raise CommandError("The URL provided doesn't match the Discord regex!")

        allowed_formats = (
            "image/",
            "video/",
            "audio/",
        )  # Added image/ to allowed formats
        async with ctx.bot.session.get(match.group()) as response:
            if not any(
                response.content_type.startswith(fmt) for fmt in allowed_formats
            ):
                human_options = human_join(
                    [f"`{option.rstrip('/')}`" for option in allowed_formats]
                )
                raise CommandError(f"The URL provided must be a {human_options} file.")

            buffer = await response.read()
            return cls(
                url=match.group(),
                buffer=buffer,
                filename=match.group().split("/")[-1],  # Fixed filename extraction
                content_type=response.content_type,
            )

    @classmethod
    async def fallback(
        cls: Type["PartialAttachment"], ctx: Context
    ) -> "PartialAttachment":
        message = ctx.message

        if not message.attachments:
            raise CommandError("You must provide an attachment!")

        allowed_formats = ("audio/", "video/")
        attachment = message.attachments[0]

        if not attachment.content_type:
            raise CommandError("The attachment provided is invalid!")

        if not any(
            attachment.content_type.startswith(option) for option in allowed_formats
        ):
            human_options = human_join([f"`{option}`" for option in allowed_formats])
            raise CommandError(
                f"The attachment provided must be a {human_options} file."
            )

        buffer = await attachment.read()
        return cls(
            url=attachment.url,
            buffer=buffer,
            filename=attachment.filename,
            content_type=attachment.content_type,
        )

    @classmethod
    async def music_fallback(cls, ctx: Context) -> "PartialAttachment":
        async def check_audio_attachment(
            message: Message,
        ) -> Optional[tuple[str, bytes, str]]:
            if url := cls.get_attachment(message):
                try:
                    buffer, content_type = await cls.read(url)
                    if content_type.startswith(("audio/", "video/")):
                        return url, buffer, content_type
                except:
                    pass
            return None

        if ctx.replied_message:
            if result := await check_audio_attachment(ctx.replied_message):
                url, buffer, content_type = result
                return cls(
                    url=url,
                    buffer=buffer,
                    filename=f"{ctx.author.id}.{url.split('.')[-1].split('?')[0]}",
                    content_type=content_type,
                )

        async for message in ctx.channel.history(limit=50):
            if result := await check_audio_attachment(message):
                url, buffer, content_type = result
                return cls(
                    url=url,
                    buffer=buffer,
                    filename=f"{ctx.author.id}.{url.split('.')[-1].split('?')[0]}",
                    content_type=content_type,
                )

        raise BadArgument("No **audio or videos** found")

    @classmethod
    async def imageonly_fallback(cls, ctx: Context) -> "PartialAttachment":
        async def check_image_attachment(
            message: Message,
        ) -> Optional[tuple[str, bytes, str]]:
            if url := cls.get_attachment(message):
                try:
                    buffer, content_type = await cls.read(url)
                    if content_type.startswith("image/"):
                        return url, buffer, content_type
                except:
                    pass
            return None

        if ctx.replied_message:
            if result := await check_image_attachment(ctx.replied_message):
                url, buffer, content_type = result
                return cls(
                    url=url,
                    buffer=buffer,
                    filename=f"{ctx.author.id}.{url.split('.')[-1].split('?')[0]}",
                    content_type=content_type,
                )

        async for message in ctx.channel.history(limit=50):
            if result := await check_image_attachment(message):
                url, buffer, content_type = result
                return cls(
                    url=url,
                    buffer=buffer,
                    filename=f"{ctx.author.id}.{url.split('.')[-1].split('?')[0]}",
                    content_type=content_type,
                )

        raise BadArgument("No image attachments found")

    @classmethod
    async def emoji_fallback(cls, ctx: Context) -> "PartialAttachment":
        """Fallback method for emoji commands that checks for valid emojis in recent messages."""

        async def check_emoji_attachment(
            message: Message,
        ) -> Optional[tuple[str, bytes, str]]:
            # Check message content for Unicode emojis
            if match := UNICODE_EMOJI.search(message.content):
                raise BadArgument(
                    "Unicode emojis cannot be added to servers. Please use a custom emoji or image instead",
                    "Example: `:custom_emoji:` or upload an image",
                )

            # Check for attachments or embeds
            if url := cls.get_attachment(message):
                try:
                    buffer, content_type = await cls.read(url)
                    if content_type.startswith("image/"):
                        return url, buffer, content_type
                except:
                    pass
            return None

        # First check replied message if it exists
        if ctx.replied_message:
            if result := await check_emoji_attachment(ctx.replied_message):
                url, buffer, content_type = result
                return cls(
                    url=url,
                    buffer=buffer,
                    filename=f"{ctx.author.id}.{url.split('.')[-1].split('?')[0]}",
                    content_type=content_type,
                )

        # Then check recent message history
        async for message in ctx.channel.history(limit=50):
            if result := await check_emoji_attachment(message):
                url, buffer, content_type = result
                return cls(
                    url=url,
                    buffer=buffer,
                    filename=f"{ctx.author.id}.{url.split('.')[-1].split('?')[0]}",
                    content_type=content_type,
                )

        raise BadArgument("Could not convert **emoji** into `Emote or URL`")
