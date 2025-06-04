from tool.worker import offloaded  # type: ignore
import asyncio
from typing import Optional, Union, Any, List
from functools import wraps, partial
from io import BytesIO
from math import sqrt
from PIL import Image, ImageDraw, ImageMath
import aiohttp
import discord
from loguru import logger


def _collage_paste(image: Image, x: int, y: int, background: Image):
    background.paste(image, (x * 256, y * 256))


def async_executor():
    def outer(func):
        @wraps(func)
        async def inner(*args, **kwargs):
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, partial(func, *args, **kwargs))

        return inner

    return outer


def _collage_open(image: BytesIO, resize: Optional[bool] = False):
    img = Image.open(image).convert("RGBA")
    if resize:
        img = img.resize((256, 256))
    return img


@offloaded
def validate_image(data: bytes):
    image_formats = {
        "JPEG": [b"\xff\xd8\xff"],
        "PNG": [b"\x89\x50\x4e\x47\x0d\x0a\x1a\x0a"],
        "GIF": [b"\x47\x49\x46\x38\x37\x61", b"\x47\x49\x46\x38\x39\x61"],
        "WEBP": [b"\x52\x49\x46\x46\x00\x00\x00\x00\x57\x45\x42\x50"],
        "JPG": [b"\xff\xd8\xff"],
    }
    file_header = data[:12]
    for magic_numbers in image_formats.values():
        for magic_number in magic_numbers:
            if file_header.startswith(magic_number):
                return True
    return False


async def _validate_image_(data: bytes):
    try:
        return await validate_image(data)
    except Exception as e:
        logger.info(f"validating image raised: {e}")
        return False


@offloaded
def _make_bar(
    percentage_1: float,
    color_1: str,
    percentage_2: float,
    color_2: str,
    bar_width: int = 10,
    height: int = 1,
    corner_radius: float = 0.2,
) -> bytes:
    import matplotlib.pyplot as plt
    from matplotlib.patches import PathPatch, Path
    import matplotlib

    matplotlib.use("Agg")

    if not (0 <= percentage_1 <= 100 and 0 <= percentage_2 <= 100):
        raise ValueError("Percentages must be between 0 and 100.")
    if percentage_1 + percentage_2 > 100:
        raise ValueError("The sum of percentages cannot exceed 100.")

    fig, ax = plt.subplots(figsize=(bar_width, height))

    width_1 = (percentage_1 / 100) * bar_width
    width_2 = (percentage_2 / 100) * bar_width

    if width_1 > 0:
        path_data = [
            (Path.MOVETO, [corner_radius, 0]),
            (Path.LINETO, [width_1, 0]),
            (Path.LINETO, [width_1, height]),
            (Path.LINETO, [corner_radius, height]),
            (Path.CURVE3, [0, height]),
            (Path.CURVE3, [0, height - corner_radius]),
            (Path.LINETO, [0, corner_radius]),
            (Path.CURVE3, [0, 0]),
            (Path.CURVE3, [corner_radius, 0]),
        ]
        codes, verts = zip(*path_data)
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor=color_1, edgecolor="none")
        ax.add_patch(patch)

    if width_2 > 0:
        path_data = [
            (Path.MOVETO, [width_1, 0]),
            (Path.LINETO, [width_1 + width_2 - corner_radius, 0]),
            (Path.CURVE3, [width_1 + width_2, 0]),
            (Path.CURVE3, [width_1 + width_2, corner_radius]),
            (Path.LINETO, [width_1 + width_2, height - corner_radius]),
            (Path.CURVE3, [width_1 + width_2, height]),
            (Path.CURVE3, [width_1 + width_2 - corner_radius, height]),
            (Path.LINETO, [width_1, height]),
            (Path.LINETO, [width_1, 0]),
        ]
        codes, verts = zip(*path_data)
        path = Path(verts, codes)
        patch = PathPatch(path, facecolor=color_2, edgecolor="none")
        ax.add_patch(patch)

    ax.set_xlim(0, bar_width)
    ax.set_ylim(0, height)
    ax.axis("off")

    buffer = BytesIO()
    plt.savefig(
        buffer, format="png", transparent=True, bbox_inches="tight", pad_inches=0
    )
    plt.close(fig)

    image = Image.open(buffer).convert("RGBA")
    bbox = image.getbbox()
    output_buffer = BytesIO()

    if bbox:
        image_cropped = image.crop(bbox)
        image_cropped.save(output_buffer, format="PNG")
    return output_buffer.getvalue()


@offloaded
def _make_chart(name: str, data: list, avatar: bytes) -> bytes:
    import matplotlib
    import matplotlib.pyplot as plt
    from humanize import naturaldelta
    from datetime import timedelta

    matplotlib.use("agg")
    plt.switch_backend("agg")
    status = ["online", "idle", "dnd", "offline"]
    seconds = [0, 0, 0, 0]
    for i, s in enumerate(status):
        seconds[i] += data[i]
    durations = [naturaldelta(timedelta(seconds=s)) for s in seconds]
    colors = ["#43b581", "#faa61a", "#f04747", "#747f8d"]
    fig, ax = plt.subplots(figsize=(6, 8))
    wedges, _ = ax.pie(
        seconds, colors=colors, startangle=90, wedgeprops=dict(width=0.3)
    )
    ax.axis("equal")
    ax.set_aspect("equal")
    img = Image.open(BytesIO(avatar)).convert("RGBA")
    if img.format == "GIF":
        img = img.convert("RGBA").copy()
    mask = Image.new("L", img.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + img.size, fill=255)
    alpha = ImageMath.eval("a*b/255", a=img.split()[3], b=mask).convert("L")
    img.putalpha(alpha)
    width, height = img.size
    aspect_ratio = height / width
    half_width = 0.91
    half_height = aspect_ratio * half_width
    extent = [-half_width, half_width, -half_height, half_height]
    plt.imshow(img, extent=extent, zorder=-1)
    legend = ax.legend(
        wedges,
        durations,
        title=f"{name}'s activity overall",
        loc="upper center",
        bbox_to_anchor=(0.5, 0.08),
    )
    frame = legend.get_frame()
    frame.set_facecolor("#2C2F33")
    frame.set_edgecolor("#23272A")
    for text in legend.get_texts():
        text.set_color("#FFFFFF")
    plt.setp(legend.get_title(), color="w")
    buffer = BytesIO()
    plt.savefig(buffer, transparent=True)
    buffer.seek(0)
    return buffer.getvalue()


async def make_chart(
    member: Union[discord.Member, discord.User], data: Any, avatar: bytes
) -> bytes:
    return await _make_chart(member.name, data, avatar)


async def _collage_read(image: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(image) as response:
            try:
                resp = await response.read()
            except Exception:
                return None
    try:
        return _collage_open(BytesIO(resp))
    except Exception as e:
        logger.info(f"_collage_read raised {e}")
        return None


async def collage(images: list):
    tasks = [_collage_read(image) for image in images]
    results = await asyncio.gather(*tasks)
    valid_images = [img for img in results if img]
    return await __collage(valid_images)


@offloaded
def __collage(images: list):
    if not images:
        return None

    def open_image(image: bytes):
        return Image.open(BytesIO(image)).convert("RGBA")

    images = [open_image(i) for i in images]
    rows = int(sqrt(len(images)))
    columns = (len(images) + rows - 1) // rows

    background = Image.new("RGBA", (columns * 256, rows * 256))
    for i, image in enumerate(images):
        _collage_paste(image, i % columns, i // columns, background)

    buffer = BytesIO()
    background.save(buffer, format="png")
    buffer.seek(0)

    background.close()
    for image in images:
        image.close()
    return buffer.getvalue()
