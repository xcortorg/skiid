from AAA3A_utils import Cog  # isort:skip
from grief.core.i18n import Translator, cog_i18n  # isort:skip
from grief.core.bot import Grief  # isort:skip
import typing  # isort:skip

# from .editautomod import EditAutoMod
from .editguild import EditGuild
from .edittextchannel import EditTextChannel
from .editthread import EditThread
from .editvoicechannel import EditVoiceChannel

# Credits:
# General repo credits.

_ = Translator("Tools", __file__)

BASES = [EditGuild, EditTextChannel, EditThread, EditVoiceChannel]  # EditAutoMod


@cog_i18n(_)
class Admin(*BASES, Cog):
    """A cog to edit Discord default objects, like guilds, roles, text channels, voice channels, threads and AutoMod."""

    def __init__(self, bot: Grief) -> None:
        super().__init__(bot=bot)

    async def red_delete_data_for_user(self, *args, **kwargs) -> None:
        """Nothing to delete."""
        return

    async def red_get_data_for_user(
        self, *args, **kwargs
    ) -> typing.Dict[str, typing.Any]:
        """Nothing to get."""
        return {}
