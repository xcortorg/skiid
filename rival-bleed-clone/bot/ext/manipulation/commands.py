import tempfile
import asyncio
import os
import aiohttp
from discord.ext.commands import (
    Cog,
    command,
    group,
    CommandError,
    Converter,
    MemberConverter,
)
from lib.patch.context import Context
from discord import Client, File, Attachment, Message
from loguru import logger as log
from io import BytesIO
from typing import Literal, Any, Optional, Union, Sequence
from lib.worker import offloaded
from mimetypes import guess_type
from json import dumps, loads
from bs4 import BeautifulSoup
from pydantic import BaseModel, create_model
from yarl import URL


def create_model_from_dict(data: Union[dict, list]) -> BaseModel:
    if "data" in data:
        data = data["data"]

    raw = dumps(data).replace("#text", "text")
    data = loads(raw)

    if isinstance(data, dict):
        field_definitions = {}

        for key, value in data.items():
            if isinstance(value, dict):
                field_definitions[key] = (create_model_from_dict(value), ...)

            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    field_definitions[key] = (
                        list[create_model_from_dict(value[0])],
                        ...,
                    )
                else:
                    field_definitions[key] = (list, ...)

            else:
                field_definitions[key] = (value.__class__, ...)

    elif isinstance(data, list):
        definitions = []

        for value in data:
            definitions.append(create_model_from_dict(value))

        return definitions
    else:
        raise TypeError(f"Unexpected type: {type(data)}")

    model = create_model("ResponseModel", **field_definitions)

    return model(**data)


class ClientSession(aiohttp.ClientSession):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(
            timeout=aiohttp.ClientTimeout(total=15),
            raise_for_status=True,
        )

    async def request(self, *args, **kwargs) -> Union[aiohttp.ClientResponse, dict]:
        args = list(args)
        args[1] = URL(args[1])
        raise_for = kwargs.pop("raise_for", {})
        if kwargs.pop("proxy", False):
            kwargs["params"] = {"url": str(args[1]), **kwargs.get("params", {})}

        args = tuple(args)

        try:
            response = await super().request(*args, **kwargs)
        except aiohttp.ClientResponseError as e:
            if error_message := raise_for.get(e.status):
                raise CommandError(error_message)

            raise

        if response.content_type == "text/html":
            return BeautifulSoup(await response.text(), "html.parser")

        elif response.content_type in ("application/json", "text/javascript"):
            return create_model_from_dict(await response.json(content_type=None))

        elif response.content_type.startswith(("image/", "video/", "audio/")):
            return await response.read()

        return response


class Attachmentt(BaseModel):
    buffer: Any
    extension: str
    url: Optional[str]


def human_join(seq: Sequence[str], delim: str = ", ", final: str = "or") -> str:
    size = len(seq)
    if size == 0:
        return ""

    if size == 1:
        return seq[0]

    if size == 2:
        return f"{seq[0]} {final} {seq[1]}"

    return delim.join(seq[:-1]) + f" {final} {seq[-1]}"


@offloaded
def write_file(filepath: str, mode: str, data: Any):
    with open(filepath, mode) as f:
        f.write(data)
    return filepath


@offloaded
def read_file(filepath: str, mode: str, **kwargs):
    with open(filepath, mode, **kwargs) as file:
        data = file.read()
    return data


class PartialAttachment(Converter):
    def __init__(self, *acceptable_types: Literal["image", "video", "audio"]):
        self.acceptable_types = acceptable_types

    async def check_link(ctx: Context) -> Optional[File]:
        words = ctx.message.content.split()
        for word in words:
            if word.startswith(("http://", "https://")):
                try:
                    response = await ctx.bot.session.get(word)
                    if response.content_type.startswith(("image/", "video/", "audio/")):
                        return File(
                            fp=BytesIO(await response.read()),
                            filename=f'image.{response.content_type.split("/")[1]}',
                        )
                except:
                    continue

        if ctx.message.reference:
            replied = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            words = replied.content.split()
            for word in words:
                if word.startswith(("http://", "https://")):
                    try:
                        response = await ctx.bot.session.get(word)
                        if response.content_type.startswith(
                            ("image/", "video/", "audio/")
                        ):
                            return File(
                                fp=BytesIO(await response.read()),
                                filename=f'image.{response.content_type.split("/")[1]}',
                            )
                    except Exception:
                        continue

        return None

    async def run_before(self, ctx: Context) -> Optional[BytesIO]:
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
        elif ctx.replied_message and ctx.replied_message.attachments:
            attachment = ctx.replied_message.attachments[0]
        else:
            if file := await self.check_link(ctx):
                return file
            return

        if attachment.content_type.startswith(self.acceptable_types):
            return (
                File(
                    fp=BytesIO(await attachment.read()),
                    filename=f'image.{attachment.content_type.split("/")[1]}',
                ),
            )

    @classmethod
    async def imageonly_fallback(cls, ctx: Context):
        if len(ctx.message.attachments) > 0:
            return await ctx.message.attachments[0].to_file()
        elif ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if len(message.attachments) > 0:
                return await message.attachments[0].to_file()
            else:
                raise CommandError("No attachment provided")
        else:
            async for message in ctx.channel.history(limit=10):
                if len(message.attachments) > 0:
                    return await message.attachments[0].to_file()
            else:
                raise CommandError("No attachment provided")

    async def convert(self, ctx: Context, argument: str) -> File:
        buffer: BytesIO = None
        extension: str = None
        try:
            member = await MemberConverter().convert(ctx, argument)
            if not member:
                return
            return await member.display_avatar.to_file()

        except Exception as e:
            raise e
            pass

        if not (match := guess_type(argument)[0]) and match.startswith(
            self.acceptable_types
        ):
            raise CommandError(
                "Please provide a valid "
                + human_join([f"`{type}`" for type in self.acceptable_types])
                + " file"
            )

        try:
            response = await ctx.bot.session.get(argument)
            buffer = BytesIO(await response.read())
            extension = guess_type(argument)[0].split("/")[1]
        except:
            raise CommandError("Please provide a valid **URL**")

        if not response.content_type.startswith(self.acceptable_types):
            raise CommandError(
                "Please provide a valid "
                + human_join([f"`{type}`" for type in self.acceptable_types])
                + " file"
            )

        if not buffer:
            raise CommandError(
                "Please provide a valid "
                + human_join([f"`{type}`" for type in self.acceptable_types])
                + " file"
            )

        return File(fp=buffer, filename=f"image.{extension}")


async def flux(
    ctx: Context,
    operation: Literal[
        "ah-shit",
        "april-fools",
        "audio",
        "bloom",
        "blur",
        "caption",
        "deepfry",
        "fisheye",
        "flip-flop",
        "frame-shift",
        "frames",
        "general",
        "ghost",
        "gif",
        "globe",
        "grayscale",
        "info",
        "invert",
        "jpeg",
        "magik",
        "makesweet",
        "meme",
        "motivate",
        "neon",
        "overlay",
        "paint",
        "ping-pong",
        "pixelate",
        "posterize",
        "rainbow",
        "resize",
        "reverse",
        "rotate",
        "scramble",
        "set-loop",
        "speech-bubble",
        "speed",
        "spin",
        "spread",
        "swirl",
        "uncaption",
        "wormhole",
        "zoom",
        "zoom-blur",
    ],
    attachment: File,
    **payload: dict[str, Any],
) -> File:
    try:
        # Read input data
        data = getattr(attachment.fp, "read", lambda: attachment.read())()

        with tempfile.TemporaryDirectory() as temp_dir:
            input_path = os.path.join(temp_dir, "input.png")
            output_path = os.path.join(
                temp_dir,
                "output.mp4" if operation in ["video", "audio"] else "output.gif",
            )

            # Write input file
            await write_file(input_path, "wb", data)

            # Build command

            if operation == "caption" and "text" in payload:
                operation_str = f"caption[text={payload['text']}]"
            elif operation == "blur" and "radius" in payload:
                operation_str = f"blur[radius={payload['radius']}]"
            elif operation == "rotate" and "angle" in payload:
                operation_str = f"rotate[angle={payload['angle']}]"
            else:
                operation_str = operation

            cmd = ["flux", "-i", input_path, "-o", operation_str, output_path]

            # Run flux command
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                raise CommandError(f"Flux processing failed: {stderr.decode()}")

            # Return processed file
            buffer = BytesIO(await read_file(output_path, "rb"))
            return File(
                buffer,
                filename=(
                    f"{operation}_result.mp4"
                    if operation in ["ah-shit", "april-fools", "audio"]
                    else f"{operation}_result.gif"
                ),
            )

    except Exception as e:
        log.error(f"Failed to process image: {e}")
        raise CommandError("Failed to process image") from e


class Commands(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    @group(
        name="media",
        invoke_without_command=True,
    )
    async def media(self, ctx: Context) -> None:
        await ctx.send_help(ctx.command)

    @media.command(name="aprilfools", description="Put a troll thumbnail on a video")
    async def aprilfools(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "april-fools", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="spin", description="Put a spin effect on an image")
    async def spin(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "spin", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="rainbow", description="Put a rainbow effect on an image")
    async def rainbow(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "rainbow", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="ahshit", description="Turn an image into a ah shit moment")
    async def ahshit(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)
        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "ah-shit", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="deepfry", description="deep fry a image")
    async def deepfry(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Deep fry an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "deepfry", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="pixelate", description="Create a pixelate effect from a image")
    async def pixelate(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:

        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "pixelate", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="caption", description="Put a caption on an image")
    async def caption(
        self,
        ctx: Context,
        *text: str,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        if not text:
            raise CommandError("Please provide text for the caption.")

        text = " ".join(text)

        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "caption", attachment, text=text)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="speechbubble", description="Put a speech bubble on a image")
    async def speechbubble(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "speech-bubble", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="blur", description="Apply a blur effect to an image")
    async def blur(
        self,
        ctx: Context,
        radius: Optional[int] = 5,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a blur effect to an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "blur", attachment, radius=radius)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="toaster", description="Generate a toaster GIF")
    async def toaster(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Generate your image on a toaster GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "toaster", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="rubiks", description="Put your image onto a rubiks cube")
    async def rubiks(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your image onto a rubiks cube"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "rubiks", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(
        name="motivate", description="Create a motivation meme using your image"
    )
    async def motivate(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a motivation meme using your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "motivate", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(
        name="fortune", description="Put a given image inside a fortune cookie"
    )
    async def fortune(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put a given image inside a fortune cookie"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "fortune-cookie", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="flag", description="Put a selected image onto a flag GIF")
    async def flag(
        self,
        ctx: Context,
        flag_name: Optional[str] = None,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put a selected image onto a flag GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(
                    ctx, "flag", attachment, flag=flag_name if flag_name else None
                )
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="flag2", description="Put a selected image onto a flag GIF")
    async def flag2(
        self,
        ctx: Context,
        flag_name: Optional[str] = None,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put a selected image onto a flag GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(
                    ctx, "flag2", attachment, flag=flag_name if flag_name else None
                )
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="heart", description="Create a heart locket with your image")
    async def heart(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a heart locket with your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "heart-locket", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="spread", description="Apply a paint spread filter to a photo")
    async def spread(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a paint spread filter to a photo"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "spread", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="magik", description="Apply the Magik filter to a photo")
    async def magik(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply the Magik filter to a photo"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "magik", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(
        name="circuitboard", description="Put your picture on a circuitboard"
    )
    async def circuitboard(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your picture on a circuitboard"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "circuitboard", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="swirl", description="Apply a swirl effect to an image")
    async def swirl(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a swirl effect to an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "swirl", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="book", description="Put your photo in a book")
    async def book(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your photo in a book"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "book", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(
        name="wormhole", description="Create a wormhole effect with your image"
    )
    async def wormhole(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a wormhole effect with your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "wormhole", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="billboard", description="Put your photo on a billboard")
    async def billboard(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your photo on a billboard"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "billboard-cityscape", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="tattoo", description="Put your photo as a back tattoo")
    async def tattoo(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your photo as a back tattoo"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "back-tattoo", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="fisheye", description="Apply a fisheye effect to an image")
    async def fisheye(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a fisheye effect to an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "fisheye", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="neon", description="Create a neon effect from your image")
    async def neon(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a neon effect from your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "neon", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="grayscale", description="Convert image to grayscale")
    async def grayscale(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Convert image to grayscale"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "grayscale", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="invert", description="Invert the colors of an image")
    async def invert(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Invert the colors of an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "invert", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="scramble", description="Scramble the frames of a GIF")
    async def scramble(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Scramble the frames of a GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "scramble", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="reverse", description="Reverse the frames of a GIF")
    async def reverse(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Reverse the frames of a GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "reverse", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="zoom", description="Create a zoom effect with your image")
    async def zoom(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a zoom effect with your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "zoom", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="speed", description="Change the speed of a GIF")
    async def speed(
        self,
        ctx: Context,
        factor: Optional[float] = 2.0,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Change the speed of a GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "speed", attachment, factor=factor)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")

    @media.command(name="zoomblur", description="Apply a zoom blur effect to an image")
    async def zoomblur(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a zoom blur effect to an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if getattr(attachment, "format", "image") not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "zoom-blur", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError("Failed to **process image**")
