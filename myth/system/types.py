from typing import TYPE_CHECKING

from discord.ext.commands import Cog

if TYPE_CHECKING:
    from system.myth import Myth


class CogMeta(Cog):
    bot: "Myth"

    def __init__(self, bot: "Myth") -> None:
        self.bot = bot
        super().__init__()
