from discord.ext.commands import Flag
from lib.classes.flags import Flags

class Parameters(Flags):
    self_destruct: int = Flag(
        aliases=["delete_after"],
        default=None,
    )
    reply: bool = Flag(
        aliases=["respond"],
        default=False,
    )
    not_string: bool = Flag(aliases = ["notstrict", "ns"], default = False)
    strict: bool = Flag(aliases = [], default = True)
    ignore_command_check: bool = Flag(aliases=["ignore", "icc"], default = False)

