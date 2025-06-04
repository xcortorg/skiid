from abc import ABC, abstractmethod
from typing import Optional

from grief.core import Config, commands
from grief.core.bot import Grief


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        self.config: Config
        self.bot: Grief
        self.cache: dict
