from core.tools.utils import COLORS
from discord import Color
from discord.ext.commands import BadArgument, CommandError, Context, Converter

from .basic import *
from .discord import *
from .kayo import *


class CustomColorConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Color:
        argument = argument.lower()
        # Reverse the COLORS dictionary to map names to hex values
        name_to_hex = {v.lower(): k for k, v in COLORS.items()}

        if argument in name_to_hex:
            hex_value = name_to_hex[argument]
        else:
            hex_value = argument

        try:
            return Color(int(hex_value.lstrip("#"), 16))
        except ValueError:
            raise BadArgument(
                f"**{argument}** is not a valid **color** name or **hex** code."
            )
