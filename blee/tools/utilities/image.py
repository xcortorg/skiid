import asyncio
from io import BytesIO
from math import sqrt
from typing import Union

import discord
from aiohttp import ClientSession  # circular import
from colorthief import ColorThief
from discord import Color
from PIL import Image
from xxhash import xxh128_hexdigest
from yarl import URL

from .process import async_executor


@async_executor()
def sample_colors(buffer: bytes) -> int:
    color = (
        Image.open(BytesIO(buffer))
        .convert("RGBA")
        .resize((1, 1), resample=0)
        .getpixel((0, 0))
    )

    return f"{discord.Color(color[0] << 16 | color[1] << 8 | color[2]):x}"


@async_executor()
def rotate(image: bytes, degrees: int = 90):
    if isinstance(image, bytes):
        image = BytesIO(image)

    with Image.open(image) as img:
        img = img.convert("RGBA").resize(
            (img.width * 2, img.height * 2),
        )

        img = img.rotate(
            angle=-degrees,
            expand=True,
        )

        buffer = BytesIO()
        img.save(
            buffer,
            format="png",
        )
        buffer.seek(0)

        img.close()
        return buffer


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

    with Image.open(image) as img:
        # Handle animated GIFs
        if getattr(img, "is_animated", False):
            frames = []
            duration = []

            # Save the original format
            format = img.format

            # Process each frame
            for frame in range(img.n_frames):
                img.seek(frame)
                # Convert to RGBA to preserve transparency
                frame_image = img.convert("RGBA")
                # Resize frame
                frame_image = frame_image.resize(size, Image.Resampling.LANCZOS)
                frames.append(frame_image)
                # Store duration of each frame
                duration.append(img.info.get("duration", 100))

            buffer = BytesIO()
            # Save animated image
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
            # Handle static images
            # Convert to RGBA for transparency support
            img = img.convert("RGBA")
            img = img.resize(size, Image.Resampling.LANCZOS)

            buffer = BytesIO()
            # Preserve original format
            format = img.format or "PNG"

            if format == "JPEG":
                # Convert RGBA to RGB for JPEG
                img = img.convert("RGB")

            img.save(buffer, format=format, optimize=True, quality=95)

        buffer.seek(0)
        return buffer
