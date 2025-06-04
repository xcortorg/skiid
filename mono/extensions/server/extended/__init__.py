from core.tools import CompositeMetaClass

from .alias import Alias
# from .command import CommandManagement
from .boosterrole import BoosterRole
from .disboard import Disboard
from .gallery import Gallery
from .level import Level
from .roles import Roles
from .starboard import Starboard
from .statistics import Statistics
from .sticky import Sticky
from .system import System
from .ticket import Ticket
from .webhook import Webhook


class Extended(
    Ticket,
    Alias,
    Roles,
    Starboard,
    Sticky,
    Statistics,
    System,
    Webhook,
    Level,
    Disboard,
    #     CommandManagement,
    BoosterRole,
    Gallery,
    metaclass=CompositeMetaClass,
):
    """
    Join all extended utility cogs into one.
    """
