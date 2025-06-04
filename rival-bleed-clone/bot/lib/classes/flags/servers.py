from discord.ext.commands import Flag
from lib.classes.flags import Flags

class Parameters(Flags):
    self_destruct: int = Flag(
        aliases=["delete_after"],
        default=None,
    )