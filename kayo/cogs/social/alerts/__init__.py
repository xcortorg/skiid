from tools import CompositeMetaClass

from .twitch import TwitchAlerts

# from .twitter import TwitterAlerts


class Alerts(
    TwitchAlerts,
    # TwitterAlerts,
    metaclass=CompositeMetaClass,
):
    """
    Join all extended alert cogs into one.
    """
