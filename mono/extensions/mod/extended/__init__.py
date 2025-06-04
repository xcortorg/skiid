from core.tools import CompositeMetaClass

from .antinuke import AntiNuke, AntiRaid
from .jail import Jail
from .logging import Logging


class Extended(
    AntiRaid,
    AntiNuke,
    Jail,
    Logging,
    metaclass=CompositeMetaClass,
):
    """
    Join all extended config cogs into one.
    """
