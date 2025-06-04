import aiohttp
from discord import Emoji, Member
from discord.ext.commands import (
    CommandError,
    Converter,
)
from orjson import dumps
from yarl import URL
from system.tools import regex
from system.base.context import Context
from loguru import logger as log


class Emoji:  # noqa: F811
    def __init__(self, name: str, url: str, **kwargs):
        self.name: str = name
        self.url: str = url
        self.id: int = int(kwargs.get("id", 0))
        self.animated: bool = kwargs.get("animated", False)

    async def read(self):
        async with (
            aiohttp.ClientSession() as session,
            session.get(self.url) as response,
        ):
            return await response.read()

    def __str__(self):
        if self.id:
            return f"<{'a' if self.animated else ''}:{self.name}:{self.id}>"
        return self.name

    def __repr__(self):
        return f"<name={self.name!r} url={self.url!r}>"


class EmojiFinder(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        # Skip the command name if it was accidentally parsed as the argument
        if argument.lower() in ("emoji", "emote", "e"):
            log.error(f"Command name provided as argument: {argument!r}")
            raise CommandError("Please provide a valid emoji")

        log.info(f"Converting emoji argument: {argument!r}")

        # Check if it's a Discord emoji
        if match := regex.DISCORD_EMOJI.match(argument):
            log.info(f"Found Discord emoji: {argument!r}")
            return Emoji(
                match.group("name"),
                "https://cdn.discordapp.com/emojis/"
                + match.group("id")
                + (".gif" if match.group("animated") else ".png"),
                id=int(match.group("id")),
                animated=bool(match.group("animated")),
            )

        # Handle URLs directly
        if any(x in argument.lower() for x in ("discord", "emojis", ".gif", ".png")):
            try:
                url = URL(argument)
                name = url.parts[-1].split(".")[0]
                return Emoji(name, str(url), animated=".gif" in argument.lower())
            except Exception as e:
                log.error(f"Failed to parse URL {argument!r}: {e}")
                raise CommandError(f"Invalid emoji URL format")

        # Show warning since no valid emoji was found yet
        await ctx.warn(f"**`{argument}`** is not a valid emoji")

        # Check if the input is actually an emoji
        if not any(ord(c) > 127 for c in argument):
            log.error(f"Not a valid emoji (ASCII only): {argument!r}")
            raise CommandError("Please provide a valid emoji")

        # Try to parse as Unicode emoji
        try:
            characters = []
            for char in argument:
                hex_char = hex(ord(char))[2:]
                if hex_char not in ("fe0f", "200d", "20e3"):
                    characters.append(hex_char)

            if not characters:
                log.error(f"No valid emoji characters found: {argument!r}")
                raise CommandError("Please provide a valid emoji")

            hexcode = "-".join(characters)
            url = f"https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/svg/{hexcode}.svg"

            async with ctx.bot.session.get(url) as response:
                if response.status == 404:
                    log.error(f"Twemoji not found at URL: {url} for {argument!r}")
                    raise CommandError("Please provide a valid emoji")

                content_type = response.headers.get("Content-Type", "")
                if "svg" not in content_type:
                    log.error(
                        f"Invalid content type ({content_type}) for emoji: {argument!r}"
                    )
                    raise CommandError("Please provide a valid emoji")

            log.info(f"Successfully converted Unicode emoji: {argument!r}")
            return Emoji(argument, url)

        except CommandError:
            raise
        except Exception as e:
            log.error(f"Unexpected error converting emoji {argument!r}: {e}")
            raise CommandError("Please provide a valid emoji")


class ImageFinder(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        try:
            member = await Member().convert(ctx, argument)
            if member:
                return member.display_avatar.url
        except Exception:
            pass

        if match := regex.DISCORD_ATTACHMENT.match(argument):
            if match.group("mime") not in (
                "png",
                "jpg",
                "jpeg",
                "webp",
                "gif",
            ):
                raise CommandError(f"Invalid image format: **{match.group('mime')}**")
            return match.group()
        if match := regex.IMAGE_URL.match(argument):
            return match.group()
        raise CommandError("Couldn't find an **image**")

    async def search(self, history: bool = True):
        if message := self.replied_message:
            for attachment in message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                    "gif",
                ):
                    return attachment.url
            for embed in message.embeds:
                if image := embed.image:
                    if match := regex.DISCORD_ATTACHMENT.match(image.url):
                        if match.group("mime") not in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                            "gif",
                        ):
                            raise CommandError(
                                f"Invalid image format: **{match.group('mime')}**"
                            )
                        return match.group()
                    if match := regex.IMAGE_URL.match(image.url):
                        return match.group()
                elif thumbnail := embed.thumbnail:
                    if match := regex.DISCORD_ATTACHMENT.match(thumbnail.url):
                        if match.group("mime") not in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                            "gif",
                        ):
                            raise CommandError(
                                f"Invalid image format: **{match.group('mime')}**"
                            )
                        return match.group()
                    if match := regex.IMAGE_URL.match(thumbnail.url):
                        return match.group()

        if self.message.attachments:
            for attachment in self.message.attachments:
                if attachment.content_type.split("/", 1)[1] in (
                    "png",
                    "jpg",
                    "jpeg",
                    "webp",
                    "gif",
                ):
                    return attachment.url

        if history:
            async for message in self.channel.history(limit=50):
                if message.attachments:
                    for attachment in message.attachments:
                        if attachment.content_type.split("/", 1)[1] in (
                            "png",
                            "jpg",
                            "jpeg",
                            "webp",
                            "gif",
                        ):
                            return attachment.url
                if message.embeds:
                    for embed in message.embeds:
                        if image := embed.image:
                            if match := regex.DISCORD_ATTACHMENT.match(image.url):
                                if match.group("mime") not in (
                                    "png",
                                    "jpg",
                                    "jpeg",
                                    "webp",
                                    "gif",
                                ):
                                    raise CommandError(
                                        f"Invalid image format: **{match.group('mime')}**"
                                    )
                                return match.group()
                            if match := regex.IMAGE_URL.match(image.url):
                                return match.group()
                        elif thumbnail := embed.thumbnail:
                            if match := regex.DISCORD_ATTACHMENT.match(thumbnail.url):
                                if match.group("mime") not in (
                                    "png",
                                    "jpg",
                                    "jpeg",
                                    "webp",
                                    "gif",
                                ):
                                    raise CommandError(
                                        f"Invalid image format: **{match.group('mime')}**"
                                    )
                                return match.group()
                            if match := regex.IMAGE_URL.match(thumbnail.url):
                                return match.group()

        raise CommandError("Please **provide** an image")
