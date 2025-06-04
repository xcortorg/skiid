from tools import CompositeMetaClass

from .conversion import Conversion
from .crypto import Crypto
from .fortnite import Fortnite
from .giveaway import Giveaway
from .snipe import Snipe

from .highlight import Highlight


class Extended(
    Snipe,
    Crypto,
    Fortnite,
    Giveaway,
    Highlight,
    Conversion,
    metaclass=CompositeMetaClass,
):
    """
    Join all extended utility cogs into one.
    """
