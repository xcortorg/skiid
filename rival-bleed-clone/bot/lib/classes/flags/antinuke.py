from typing import Literal

from discord.ext.commands import Flag, Range, Boolean, CommandError
from lib.patch.context import Context
from lib.classes.flags import Flags
from loguru import logger
from lib.classes.converters import AntinukeAction
ACTION = Literal["ban", "kick", "stripstaff"]
Parameters = {
    "punishment": {
        "converter": str,
    },
    "action": {
        "converter": str,
    },
    "do": {
        "converter": str,
    },
    "threshold": {
        "converter": int,
        "default": 3
    },
    "command": {
        "converter": Boolean,
        "default": False
    }
}

async def get_parameters(ctx: Context) -> dict:
    try:
        command = ctx.parameters.get("command", False)
        if command:
            try:
                command = await command or False
            except Exception:
                pass
    except:
        command = False
    if ctx.parameters.get("threshold") > 6 or 1 > ctx.parameters.get("threshold"):
        raise CommandError("Invalid value for parameter `threshold`, must be between 1 and 6")
    if p1 := ctx.parameters.get("punishment"):
        punishment = p1
    elif p2 := ctx.parameters.get("action"):
        punishment = p2
    elif p3 := ctx.parameters.get("do"):
        punishment = p3
    else:
        punishment = "kick"
    punishment = punishment.lower().lstrip().rstrip()
    if punishment not in ("ban", "kick", "stripstaff"):
        raise CommandError("Invalid value for parameter `punishment`, must be one of the following valid actions `ban`, `kick` and `stripstaff`")
    new_parameters = {
        "punishment": punishment, 
        "threshold": ctx.parameters.get("threshold"),
        "command": command,
    }
    return new_parameters

# class Parameters(Flags):
#     punishment: AntinukeAction = Flag(
#         aliases=["action", "do"],
#         default="kick",
#     )
#     threshold: Range[int, 1, 6] = 3
#     command: Boolean = False