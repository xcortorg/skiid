from core.tools import CompositeMetaClass

from .snipe import Snipe


class Extended(
    Snipe,
    metaclass=CompositeMetaClass,
):
    """
    Join all extended utility cogs into one.
    """
