# Standard library imports

from typing import Optional

# Third-party imports
from discord import (
    Message,
)
from discord.ext.commands import (
    command,
    Cog,
    group,
    cooldown,
    CommandError,
    BucketType,
)
from loguru import logger as log

import config
from config import Color
from system import Marly
from system.base.context import Context
from system.tools.converters import (
    PartialAttachment,
)

from system.tools.flux import flux


class Manipulation(Cog):
    def __init__(self, bot: Marly) -> None:
        self.bot = bot

    @group(
        name="media",
        invoke_without_command=True,
    )
    async def media(self, ctx: Context) -> None:
        """
        Image manipulation for photos, videos and GIFs
        """
        await ctx.send_help(ctx.command)

    @media.command(name="aprilfools")
    @cooldown(1, 5, BucketType.user)
    async def aprilfools(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """troll thumbnail on a april fools video"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "april-fools", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="spin")
    @cooldown(1, 5, BucketType.user)
    async def spin(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put a spin effect on an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "spin", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="rainbow")
    @cooldown(1, 5, BucketType.user)
    async def rainbow(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put a rainbow effect on an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "rainbow", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="ahshit")
    @cooldown(1, 5, BucketType.user)
    async def ahshit(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Turn an image into a ah shit moment"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "ah-shit", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="deepfry")
    @cooldown(1, 5, BucketType.user)
    async def deepfry(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Deep fry an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "deepfry", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="pixelate")
    @cooldown(1, 5, BucketType.user)
    async def pixelate(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """
        Create a pixelate effect from an image
        """
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "pixelate", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="caption")
    @cooldown(1, 5, BucketType.user)
    async def caption(
        self,
        ctx: Context,
        text: str,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Add a caption to an image

        Parameters
        -----------
        text: The caption text to add
        attachment: The image to caption (optional - uses last image in channel if not provided)
        """
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "caption", attachment, text=text)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="speechbubble")
    @cooldown(1, 5, BucketType.user)
    async def speechbubble(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "speech-bubble", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="blur")
    @cooldown(1, 5, BucketType.user)
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

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "blur", attachment, radius=radius)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="toaster")
    @cooldown(1, 5, BucketType.user)
    async def toaster(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Generate your image on a toaster GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "toaster", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="rubiks")
    @cooldown(1, 5, BucketType.user)
    async def rubiks(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your image onto a rubiks cube"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "rubiks", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="motivate")
    @cooldown(1, 5, BucketType.user)
    async def motivate(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a motivation meme using your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "motivate", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="fortune")
    @cooldown(1, 5, BucketType.user)
    async def fortune(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put a given image inside a fortune cookie"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "fortune-cookie", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="flag")
    @cooldown(1, 5, BucketType.user)
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

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(
                    ctx, "flag", attachment, flag=flag_name if flag_name else None
                )
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="flag2")
    @cooldown(1, 5, BucketType.user)
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

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(
                    ctx, "flag2", attachment, flag=flag_name if flag_name else None
                )
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="heart")
    @cooldown(1, 5, BucketType.user)
    async def heart(
        self,
        ctx: Context,
        text: Optional[str] = None,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a heart locket with your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                payload = {"text": text} if text else {}
                file = await flux(ctx, "heart-locket", attachment, **payload)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="spread")
    @cooldown(1, 5, BucketType.user)
    async def spread(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a paint spread filter to a photo"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "spread", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="magik")
    @cooldown(1, 5, BucketType.user)
    async def magik(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply the Magik filter to a photo"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "magik", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="circuitboard")
    @cooldown(1, 5, BucketType.user)
    async def circuitboard(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your picture on a circuitboard"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "circuitboard", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="swirl")
    @cooldown(1, 5, BucketType.user)
    async def swirl(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a swirl effect to an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "swirl", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="book")
    @cooldown(1, 5, BucketType.user)
    async def book(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your photo in a book"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "book", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="wormhole")
    @cooldown(1, 5, BucketType.user)
    async def wormhole(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a wormhole effect with your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "wormhole", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="billboard")
    @cooldown(1, 5, BucketType.user)
    async def billboard(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your photo on a billboard"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "billboard-cityscape", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="tattoo")
    @cooldown(1, 5, BucketType.user)
    async def tattoo(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Put your photo as a back tattoo"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "back-tattoo", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="fisheye")
    @cooldown(1, 5, BucketType.user)
    async def fisheye(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a fisheye effect to an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "fisheye", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="neon")
    @cooldown(1, 5, BucketType.user)
    async def neon(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a neon effect from your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "neon", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="grayscale")
    @cooldown(1, 5, BucketType.user)
    async def grayscale(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Convert image to grayscale"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "grayscale", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="invert")
    @cooldown(1, 5, BucketType.user)
    async def invert(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Invert the colors of an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "invert", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="scramble")
    @cooldown(1, 5, BucketType.user)
    async def scramble(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Scramble the frames of a GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "scramble", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="reverse")
    @cooldown(1, 5, BucketType.user)
    async def reverse(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Reverse the frames of a GIF"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "reverse", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="zoom")
    @cooldown(1, 5, BucketType.user)
    async def zoom(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Create a zoom effect with your image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "zoom", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="speed")
    @cooldown(1, 5, BucketType.user)
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

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "speed", attachment, factor=factor)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")

    @media.command(name="zoomblur")
    @cooldown(1, 5, BucketType.user)
    async def zoomblur(
        self,
        ctx: Context,
        *,
        attachment: Optional[PartialAttachment] = None,
    ) -> Message:
        """Apply a zoom blur effect to an image"""
        if attachment is None:
            attachment = await PartialAttachment.imageonly_fallback(ctx)

        if attachment.format not in ("image", "gif"):
            raise CommandError("The file must be an image or gif")

        async with ctx.typing():
            try:
                file = await flux(ctx, "zoom-blur", attachment)
                return await ctx.send(file=file)
            except Exception as e:
                log.error(f"Failed to process image: {e}")
                raise CommandError(f"Failed to **process image**")
