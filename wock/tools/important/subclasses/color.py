import asyncio
import math
import pickle
import re
from io import BytesIO
from itertools import chain
from typing import Any, List, Optional, Tuple, Union

import aiohttp
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import webcolors
from discord import Color, Embed, File, Member, User
from discord.ext import commands
from discord.ext.commands import Context
from fast_string_match import closest_match_distance as cmd
from loguru import logger
from PIL import Image, ImageDraw, ImageFont
from rival_tools import thread  # type: ignore


@thread
def generate_palette(hex_color: str):
    output = BytesIO()
    image = Image.new("RGB", (150, 150), hex_color)
    image.save(output, format="PNG")
    output.seek(0)
    return output
    sns.set_palette(sns.color_palette([hex_color]))
    sns.palplot(sns.color_palette(), linewidth=0)
    plt.figure(figsize=(8, 2))
    plt.gcf().set_facecolor("none")
    plt.savefig(output, format="PNG", transparent=True)
    output.seek(0)
    return output


def brightness(color_rgb):
    # Calculate brightness of a color
    return (0.299 * color_rgb[0] + 0.587 * color_rgb[1] + 0.114 * color_rgb[2]) / 255


def _generate_color_swatch(color_hex):
    # Create a 100x100 pixel image filled with the given color
    color_rgb = tuple(int(color_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    color_swatch = np.full((100, 100, 3), color_rgb, dtype=np.uint8)
    return color_swatch


def generate_color_swatch(color_hex):
    # Create a 100x100 pixel image filled with the given color
    color_rgb = tuple(int(color_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    color_swatch = np.full((100, 100, 3), color_rgb, dtype=np.uint8)
    return color_swatch


def get_shades(
    color_hex: str, amount: Optional[int] = 5, darker: Optional[bool] = True
) -> List[str]:
    rgb_color = mcolors.hex2color(color_hex)
    amount = amount - 1
    if darker is True:
        shades = [
            mcolors.rgb2hex(
                (
                    rgb_color[0] * (1 - i / amount),
                    rgb_color[1] * (1 - i / amount),
                    rgb_color[2] * (1 - i / amount),
                )
            )
            for i in range(1, amount + 1)
        ]
    else:
        shades = [
            mcolors.rgb2hex(
                (
                    min(rgb_color[0] + i / amount, 1),
                    min(rgb_color[1] + i / amount, 1),
                    min(rgb_color[2] + i / amount, 1),
                )
            )
            for i in range(1, amount + 1)
        ]
    shades.insert(0, color_hex)
    return shades


@thread
def generate_multi_palette(shades: List[str]):
    num_colors = len(shades)
    images = []

    num_per_row = (num_colors + 1) // 2  # Number of images per row

    for color_hex in shades:
        # Convert hexadecimal color code to RGB tuple
        color_rgb = tuple(int(color_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
        color_swatch = np.full((100, 100, 3), color_rgb, dtype=np.uint8)
        images.append(color_swatch)

    # Combine images into two rows in the collage
    images_row1 = images[:num_per_row]
    images_row2 = images[num_per_row:]

    collage_row1 = np.concatenate(images_row1, axis=1)
    collage_row2 = np.concatenate(images_row2, axis=1)

    collage_combined = np.concatenate([collage_row1, collage_row2], axis=0)
    collage_image = Image.fromarray(collage_combined)

    # Add color hex labels to the collage
    font = ImageFont.load_default(18)
    draw = ImageDraw.Draw(collage_image)

    for i, color_hex in enumerate(shades):
        row_index = i // num_per_row
        col_index = i % num_per_row
        x = col_index * 100 + 10
        y = row_index * 100 + 70

        # Convert hexadecimal color code to RGB tuple
        color_rgb = tuple(int(color_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))

        # Determine label color based on brightness of color swatch
        label_color = "black" if brightness(color_rgb) > 0.5 else "white"

        draw.text((x, y), color_hex, fill=label_color, font=font)

    # Save collage image to BytesIO object
    buf = BytesIO()
    collage_image.save(buf, format="PNG")
    buf.seek(0)
    return buf


def hex_to_brightness(color_hex: str) -> int:
    color_rgb = tuple(int(color_hex.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    return int(brightness(color_rgb) * 100.0)


def split_tuple_of_tuples(
    tuple_of_tuples: Tuple[Tuple[Any, Any]], size: Optional[int] = 4
):
    chunk_size = len(tuple_of_tuples) // size
    return tuple(
        tuple_of_tuples[i : i + chunk_size]
        for i in range(0, len(tuple_of_tuples), chunk_size)
    )


def load_color_map():
    with open("/root/colors.pkl", "rb") as file:
        _ = split_tuple_of_tuples(pickle.load(file))
    return _


colors = load_color_map()


async def color_picker_(query: str, colors: tuple):
    if match := cmd(query, [k[0] for k in colors]):
        return [m for m in colors if m[0] == match]
    return None


def hex_to_rgb(hex_color: Any):
    # Remove '#' if present and split into RGB components
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_distance(color1: Any, color2: Any):
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    return math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)


def nearest_color(target_color: Any, color_list: Any):
    target_rgb = hex_to_rgb(target_color)
    closest_color = None
    min_distance = float("inf")

    for color in color_list:
        color_rgb = hex_to_rgb(color)
        distance = rgb_distance(target_rgb, color_rgb)
        if distance < min_distance:
            min_distance = distance
            closest_color = color

    return closest_color


async def find_name(hex_: str):
    async def _find_name(hex_: str, colors: tuple):
        try:
            return [c for c in colors if c[1] == hex_][0]
        except Exception:
            return None

    data = await asyncio.gather(*[_find_name(hex_, c) for c in colors])
    data = [d for d in data if d is not None]
    if len(data) != 0:
        return data[0]
    else:
        return "unnamed"


def get_websafe(color_hex: str):
    rgb = webcolors.hex_to_rgb(color_hex)
    web_safe_rgb = [round(val / 51) * 51 for val in rgb]
    web_safe_hex = webcolors.rgb_to_hex(web_safe_rgb)
    return web_safe_hex


async def closest_color(
    color_hex: str, name: Optional[bool] = False, with_websafe: Optional[bool] = False
):
    color_list = []
    for colo in colors:
        _color_list = [c[1] for c in colo]
        color_list.extend(_color_list)
    nearest = nearest_color(color_hex, color_list)
    next((c for colo in colors for c in colo if c[1] == nearest), None)
    rgb = webcolors.hex_to_rgb(color_hex)
    web_safe_rgb = [round(val / 51) * 51 for val in rgb]
    web_safe_hex = webcolors.rgb_to_hex(web_safe_rgb)
    if name is True:
        color_name = await find_name(web_safe_hex)
        data = (color_name, nearest)
    else:
        data = nearest
    return data


async def color_info(ctx: commands.Context, query: str):
    if query.startswith("#"):
        hex = ((await closest_color(query, True))[0][0], query)
    else:
        try:
            Color.from_str(f"#{query}")
        except Exception:
            pass
        hex = await color_search(query)
    websafe = get_websafe(hex[1])
    palette = await generate_palette(hex[1])
    rg = webcolors.hex_to_rgb(hex[1])
    shades = get_shades(hex[1], 11)
    shades.extend(get_shades(hex[1], 11, False))
    palette2 = await generate_multi_palette(shades)
    shade = ", ".join(m.strip("#") for m in shades[:4])
    rgb = f"({rg.red}, {rg.green}, {rg.blue})"
    embed = Embed(title=f"{hex[0]} ({hex[1]})", color=Color.from_str(hex[1]))
    embed.add_field(name="Websafe", value=f"`{websafe}`", inline=True)
    embed.add_field(name="RGB", value=f"`{rgb}`", inline=True)
    embed.set_image(url="attachment://palette2.png")
    embed.add_field(name="Brightness", value=hex_to_brightness(hex[1]), inline=True)
    embed.add_field(name="Shades", value=f"```{shade}```", inline=False)
    embed.set_thumbnail(url="attachment://palette.png")
    return await ctx.send(
        files=[
            File(fp=palette2, filename="palette2.png"),
            File(fp=palette, filename="palette.png"),
        ],
        embed=embed,
    )


async def color_search(query: str, with_websafe: Optional[bool] = False):
    if query == "black":
        return ("Black", "#010101")
    if hex_match := re.match(r"#?[a-f0-9]{6}", query.lower()):  # noqa: F841
        color_name = await closest_color(query, True, True)
        return (color_name[1], query)
    matches = []
    matches = list(
        chain.from_iterable(
            await asyncio.gather(*[color_picker_(query, _) for _ in colors])
        )
    )
    match = cmd(query, tuple([k[0] for k in matches]))
    _ = [m for m in matches if m[0] == match][0]
    return _


async def get_dominant_color(u: Union[Member, User, str]) -> str:
    from colorgram_rs import get_dominant_color as get_dom

    @thread
    def get(url: str) -> str:
        return get_dom(url)

    if isinstance(
        u,
        (
            Member,
            User,
        ),
    ):
        _ = await get(await u.display_avatar.read())
    else:
        async with aiohttp.ClientSession() as session:
            async with session.get(u) as resp:
                _u = await resp.read()
        _ = await get(_u)
    return f"#{_}"


class ColorConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: Union[Color, str]):
        if isinstance(argument, Color):
            return argument
        elif argument.lower().startswith("0x"):
            return Color.from_str(argument)
        else:
            argument = str(argument).lower()
            try:
                if argument.startswith("#"):
                    return Color.from_str(argument)
                else:
                    return Color.from_str(f"#{argument}")
            except Exception:
                pass
            try:
                if argument.lower() in ("dom", "dominant"):
                    return Color.from_str(await get_dominant_color(ctx.author))
                else:
                    _ = await color_search(argument)
                    if isinstance(_, tuple):
                        _ = _[1]
                    return Color.from_str(_)
            except Exception as e:
                logger.info(f"Color Converter Errored with : {e}")
                raise commands.errors.CommandError("Invalid color hex given")


commands.ColourConverter.convert = ColorConverter.convert
