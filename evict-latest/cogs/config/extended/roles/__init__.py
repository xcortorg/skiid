from .auto import AutoRoles
from .reaction import ReactionRoles
from .buttons import Buttons


class Roles(AutoRoles, ReactionRoles, Buttons): ...


__all__ = ("Roles",)
