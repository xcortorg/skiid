from color_processing import ColorHolder
from discord import Color, ext, Member, User
from discord.ext.commands import (
    ColorConverter as CV,
    ColourConverter,
    Converter,
    Context,
)
from tool.worker import offloaded
from typing import Union


class ColorInfo(Converter):
    async def convert(self, ctx: Context, argument: Union[Color, str, Member, User]):
        if isinstance(argument, Color):
            argument = str(argument)
        colors = ColorHolder.get_colors(offloaded)
        information = await colors.color_info(argument)
        return await information.to_message(ctx)


class ColorConverter(Converter):
    async def convert(self, ctx: Context, argument: Union[Color, str]):
        colors = ColorHolder.get_colors(offloaded)
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
                    return Color.from_str(await colors.get_dominant_color(ctx.author))
                else:
                    _ = await colors.color_search(argument)
                    if isinstance(_, tuple):
                        _ = _[1]
                    return Color.from_str(_)
            except Exception as e:
                logger.info(f"Color Converter Errored with : {e}")
                raise CommandError("Invalid color hex given")


CV.convert = ColorConverter.convert
ColourConverter.convert = ColorConverter.convert
ext.commands.converter.ColorInfo = ColorInfo
