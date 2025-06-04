from discord import Color as DiscordColor
from discord.ext.commands import BadArgument, CommandError, Context, Converter

colors = {
    "#4c4f56": "Abbey",
    "#0048ba": "Absolute Zero",
    "#1b1404": "Acadia",
    "#7cb0a1": "Acapulco",
    "#b0bf1a": "Acid Green",
    "#7cb9e8": "Aero",
    "#c9ffe5": "Aero Blue",
    "#714693": "Affair",
    "#b284be": "African Violet",
    "#00308f": "Air Force Blue",
    "#72a0c1": "Air Superiority Blue",
    "#d4c4a8": "Akaroa",
    "#af002a": "Alabama Crimson",
    "#fafafa": "Alabaster",
    "#f5e9d3": "Albescent White",
    "#93dfb8": "Algae Green",
    "#f0f8ff": "Alice Blue",
    "#84de02": "Alien Armpit",
    "#e32636": "Alizarin Crimson",
    "#c46210": "Alloy Orange",
    "#0076a3": "Allports",
    "#efdecd": "Almond",
    "#907b71": "Almond Frost",
    "#af8f2c": "Alpine",
    "#dbdbdb": "Alto",
    "#a9acb6": "Aluminium",
    "#e52b50": "Amaranth",
    "#f19cbb": "Amaranth Pink",
    "#ab274f": "Amaranth Purple",
    "#d3212d": "Amaranth Red",
    "#3b7a57": "Amazon",
    "#ffbf00": "Amber",
    "#ff033e": "American Rose",
    "#87756e": "Americano",
    "#9966cc": "Amethyst",
    "#a397b4": "Amethyst Smoke",
}


def get_color(value: str):
    if value.lower() in {"random", "rand", "r"}:
        return DiscordColor.random()
    if value.lower() in {"invisible", "invis"}:
        return DiscordColor.from_str("#2B2D31")
    if value.lower() in {"blurple", "blurp"}:
        return DiscordColor.blurple()
    if value.lower() in {"black", "negro"}:
        return DiscordColor.from_str("#000001")

    # Check if input is a hex code that exists in colors dict
    if value.startswith("#"):
        if value in colors:
            hex_value = value.lstrip("#")
            return DiscordColor(int(hex_value, 16))
    else:
        # Look up color name in reversed dictionary
        color_lookup = {v.lower(): k for k, v in colors.items()}
        if hex_code := color_lookup.get(value.lower()):
            hex_value = hex_code.lstrip("#")
            return DiscordColor(int(hex_value, 16))

    # Try parsing as direct hex value
    try:
        hex_value = value.replace("#", "")
        color = DiscordColor(int(hex_value, 16))
        return color if color.value <= 16777215 else None
    except ValueError:
        return None


class Color(Converter):
    @staticmethod
    async def convert(ctx: Context, argument: str):
        if ctx.command.qualified_name in ("lastfm color"):
            if argument.lower() in {"dominant", "dom"}:
                return "dominant"
            if argument.lower() in {
                "remove",
                "reset",
                "clear",
                "default",
                "none",
            }:
                return "remove"

        if argument.lower() in {"random", "rand", "r"}:
            return DiscordColor.random()
        if argument.lower() in {"invisible", "invis"}:
            return DiscordColor.from_str("#2B2D31")

        if color := get_color(argument):
            return color
        raise CommandError(f"Color **{argument}** not found")


class CustomColorConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Color:
        argument = argument.lower()

        # Handle special cases first
        if argument in {"random", "rand", "r"}:
            return DiscordColor.random()
        if argument in {"invisible", "invis"}:
            return DiscordColor.from_str("#2B2D31")
        if argument in {"blurple", "blurp"}:
            return DiscordColor.blurple()

        # Handle named colors - create reverse lookup
        color_lookup = {v.lower(): k for k, v in colors.items()}
        if hex_code := color_lookup.get(argument):
            hex_value = hex_code.lstrip("#")
            return DiscordColor(int(hex_value, 16))

        # Handle hex values
        try:
            # Clean up hex input
            hex_value = argument.lstrip("#")
            if len(hex_value) == 6:
                return DiscordColor(int(hex_value, 16))
            raise ValueError
        except ValueError:
            raise BadArgument(f"**{argument}** is an invalid hex code")
