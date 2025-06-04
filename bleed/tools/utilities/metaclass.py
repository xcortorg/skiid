from abc import ABC

from discord.ext.commands import Cog


class CompositeMetaClass(type(Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


class MixinMeta(Cog, ABC, metaclass=CompositeMetaClass):
    """
    This is the base class for all mixins.
    With well-defined mixins, we can avoid the need for multiple inheritance.
    """
