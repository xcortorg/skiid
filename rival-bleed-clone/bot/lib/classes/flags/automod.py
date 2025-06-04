from discord.ext.commands import Flag, Converter, flag
from discord import AutoModRuleActionType
from lib.classes.flags import Flags
from lib.patch.context import Context
from typing import Optional

class ActionConverter(Converter):
    async def convert(self, ctx: Context, argument: str):
        a = argument.lower()
        if a in ("delete", "del"):
            return "delete"
        elif a == "kick":
            return "kick"
        elif a in ("mute", "timeout", "to"):
            return "mute"
        else:
            return "delete"



class FilterFlags(Flags):
    punishment: str = flag(name = "punishment", aliases = ["punish", "do", "action"], default = "delete", converter=ActionConverter)
    threshold: int = flag(name = "threshold", aliases = ["amt", "amount"], default = 100)

class SpamFilterFlags(Flags):
    punishment: str = flag(name = "punishment", aliases = ["punish", "do", "action"], default = "delete", converter=ActionConverter)
    threshold: int = flag(name = "threshold", aliases = ["amt", "amount"], default = 5)