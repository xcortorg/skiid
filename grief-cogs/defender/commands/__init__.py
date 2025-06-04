from ..abc import CompositeMetaClass
from .manualmodules import ManualModules
from .settings import Settings
from .stafftools import StaffTools


class Commands(ManualModules, StaffTools, Settings, metaclass=CompositeMetaClass):  # type: ignore
    """Class joining all command subclasses"""
