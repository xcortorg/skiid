import asyncio
from io import BytesIO
from math import sqrt

import discord
from aiohttp import ClientSession  # circular import
from PIL import Image
from xxhash import xxh128_hexdigest
from yarl import URL
from system.tools.asyncexecutor import async_executor
from typing import Union
from discord import Color
from colorthief import ColorThief
from PIL import ImageOps
from pathlib import Path
from discord import File
from wand.image import Image as WandImage


@async_executor()
def sample_colors(buffer: bytes) -> int:
    color = (
        Image.open(BytesIO(buffer))
        .convert("RGBA")
        .resize((1, 1), resample=0)
        .getpixel((0, 0))
    )

    return f"{discord.Color(color[0] << 16 | color[1] << 8 | color[2]):x}"


async def rotate(buffer: bytes, degrees: int) -> File:
    """Rotate an image by specified degrees"""
    image = Image.open(BytesIO(buffer))
    rotated = image.rotate(degrees, expand=True)

    output = BytesIO()
    rotated.save(output, format=image.format)
    output.seek(0)

    return File(output, filename=f"rotated.{image.format.lower()}")


@async_executor()
def image_hash(image: BytesIO) -> str:
    """Hash an image to a string"""
    if isinstance(image, bytes):
        image = BytesIO(image)

    return xxh128_hexdigest(image.getvalue())


async def dominant(session: ClientSession, url: str) -> Color:
    """Get the dominant color from an image URL"""
    async with session.get(url) as response:
        if response.status != 200:
            return Color.default()

        buffer = BytesIO(await response.read())
        try:
            thief = ColorThief(buffer)
            rgb = thief.get_color(quality=1)
            return Color.from_rgb(*rgb)
        except:
            return Color.default()


@async_executor()
def _collage_open(image: BytesIO):
    image = (
        Image.open(image)
        .convert("RGBA")
        .resize(
            (
                256,
                256,
            )
        )
    )
    return image


async def _collage_read(image: str):
    async with ClientSession() as session, session.get(image) as response:
        try:
            return await _collage_open(BytesIO(await response.read()))
        except Exception:
            return None


async def _collage_paste(image: Image, x: int, y: int, background: Image):
    background.paste(
        image,
        (
            x * 256,
            y * 256,
        ),
    )


@async_executor()
async def collage(images: list[str]):
    tasks = [_collage_read(image) for image in images]
    images = [image for image in await asyncio.gather(*tasks) if image]
    if not images:
        return None

    rows = int(sqrt(len(images)))
    columns = (len(images) + rows - 1) // rows

    background = Image.new(
        "RGBA",
        (
            columns * 256,
            rows * 256,
        ),
    )
    tasks = [
        _collage_paste(image, i % columns, i // columns, background)
        for i, image in enumerate(images)
    ]
    await asyncio.gather(*tasks)

    buffer = BytesIO()
    background.save(
        buffer,
        format="png",
    )
    buffer.seek(0)

    background.close()
    for image in images:
        image.close()

    return discord.File(
        buffer,
        filename="collage.png",
    )


# @async_executor()
# def resize(image: Union[bytes, BytesIO], size: tuple[int, int]) -> BytesIO:
#    """Resize an image while maintaining quality, supporting GIFs and other formats
#
#    Args:
#        image: Image data as bytes or BytesIO
#        size: Tuple of (width, height)
#
#    Returns:
#        BytesIO: Resized image buffer
#    """
#    if isinstance(image, bytes):
#        image = BytesIO(image)
#
#    buffer = BytesIO()
#    with WandImage(blob=image.getvalue()) as img:
#        # Set the format to PNG for lossless compression
#        img.format = 'PNG'
#
#        # Resize the image
#        img.resize(width=size[0], height=size[1])
#
#        # Save the image
#        img.save(file=buffer)
#
#    buffer.seek(0)
#    return buffer


@async_executor()
def upscale(image: Union[bytes, BytesIO], size: tuple[int, int]) -> BytesIO:
    """Upscale an image while maintaining quality

    Args:
        image: Image data as bytes or BytesIO
        size: Tuple of (width, height)

    Returns:
        BytesIO: Upscaled image buffer
    """
    if isinstance(image, bytes):
        image = BytesIO(image)

    buffer = BytesIO()
    with WandImage(blob=image.getvalue()) as img:
        # Set the format to PNG for lossless compression
        img.format = "PNG"

        # Upscale the image using a high-quality filter
        img.resize(width=size[0], height=size[1], filter="lanczos")

        # Save the image
        img.save(file=buffer)

    buffer.seek(0)
    return buffer


@async_executor()
def resize(image: Union[bytes, BytesIO], size: tuple[int, int]) -> BytesIO:
    """Resize an image while maintaining quality, supporting GIFs and other formats

    Args:
        image: Image data as bytes or BytesIO
        size: Tuple of (width, height)

    Returns:
        BytesIO: Resized image buffer
    """
    if isinstance(image, bytes):
        image = BytesIO(image)

    buffer = BytesIO()
    with WandImage(blob=image.getvalue()) as img:
        # Calculate aspect ratio while preserving original dimensions if smaller
        width, height = img.size
        if width <= size[0] and height <= size[1]:
            # Image is already smaller than target size, keep original
            img.save(file=buffer)
            buffer.seek(0)
            return buffer

        ratio = min(size[0] / width, size[1] / height)
        new_size = (int(width * ratio), int(height * ratio))

        # Configure for maximum quality
        img.compression_quality = 100
        img.alpha_channel = True  # Preserve transparency

        # Apply light unsharp mask before resize to preserve details
        img.unsharp_mask(radius=0.5, sigma=0.5, amount=0.5, threshold=0)

        # Use Lanczos with enhanced settings
        img.filter_type = "lanczos2"  # Higher quality Lanczos filter
        img.resize(
            width=new_size[0],
            height=new_size[1],
            filter="lanczos",
            blur=0.8,  # Slightly reduced blur for sharper image
        )

        # Apply light sharpening after resize
        img.unsharp_mask(radius=0.5, sigma=0.5, amount=0.8, threshold=0)

        # Save with original format and maximum quality
        img.save(file=buffer)

    buffer.seek(0)
    return buffer


@async_executor()
def invert(image: Union[bytes, BytesIO]) -> discord.File:
    """Invert the colors of an image while preserving transparency

    Args:
        image: Image data as bytes or BytesIO

    Returns:
        discord.File: Inverted image as a Discord file attachment
    """
    if isinstance(image, bytes):
        image = BytesIO(image)

    with Image.open(image) as img:
        # Handle animated GIFs
        if getattr(img, "is_animated", False):
            frames = []
            duration = []
            format = img.format

            for frame in range(img.n_frames):
                img.seek(frame)
                # Split into RGBA channels
                r, g, b, a = img.convert("RGBA").split()
                # Invert RGB channels
                r, g, b = ImageOps.invert(r), ImageOps.invert(g), ImageOps.invert(b)
                # Recombine with original alpha
                frame_image = Image.merge("RGBA", (r, g, b, a))
                frames.append(frame_image)
                duration.append(img.info.get("duration", 100))

            buffer = BytesIO()
            frames[0].save(
                buffer,
                format=format,
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=0,
                optimize=True,
            )

        else:
            # Split into RGBA channels
            r, g, b, a = img.convert("RGBA").split()
            # Invert RGB channels
            r, g, b = ImageOps.invert(r), ImageOps.invert(g), ImageOps.invert(b)
            # Recombine with original alpha
            inverted_img = Image.merge("RGBA", (r, g, b, a))

            buffer = BytesIO()
            format = img.format or "PNG"
            inverted_img.save(buffer, format=format)

        buffer.seek(0)
        return discord.File(buffer, filename=f"inverted.{format.lower()}")


@async_executor()
def compress(image: Union[bytes, BytesIO], quality: int) -> discord.File:
    """Compress an image with specified quality

    Args:
        image: Image data as bytes or BytesIO
        quality: Quality percentage (1-100)

    Returns:
        discord.File: Compressed image as a Discord file attachment
    """
    if isinstance(image, bytes):
        image = BytesIO(image)

    with Image.open(image) as img:
        # Handle animated GIFs
        if getattr(img, "is_animated", False):
            frames = []
            duration = []
            format = img.format

            for frame in range(img.n_frames):
                img.seek(frame)
                frame_image = img.convert(
                    "RGB"
                )  # Convert to RGB for better compression
                # Resize if image is large
                if max(frame_image.size) > 1024:
                    frame_image.thumbnail((1024, 1024), Image.Resampling.NEAREST)
                frames.append(frame_image)
                duration.append(img.info.get("duration", 100))

            buffer = BytesIO()
            frames[0].save(
                buffer,
                format="GIF",  # Force GIF format for animations
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=0,
                optimize=True,
                quality=quality,
            )

        else:
            buffer = BytesIO()
            # Convert to RGB for better compression
            img = img.convert("RGB")

            # Resize if image is large
            if max(img.size) > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

            # Force JPEG format for still images as it compresses better
            img.save(buffer, format="JPEG", optimize=True, quality=quality)

        buffer.seek(0)
        return discord.File(
            buffer, filename=f"compressed.jpg"
        )  # Always use .jpg extension for better compression
