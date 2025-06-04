import importlib.machinery

import discord

from grief.core.utils.chat_formatting import humanize_number

from .i18n import Translator

_ = Translator(__name__, __file__)

__all__ = (
    "RedError",
    "PackageAlreadyLoaded",
    "CogLoadError",
    "ConfigError",
    "StoredTypeError",
    "CannotSetSubfield",
)


class RedError(Exception):
    """Base error class for Red-related errors."""


class PackageAlreadyLoaded(RedError):
    """Raised when trying to load an already-loaded package."""

    def __init__(self, spec: importlib.machinery.ModuleSpec, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spec: importlib.machinery.ModuleSpec = spec

    def __str__(self) -> str:
        return (
            f"There is already a package named {self.spec.name.split('.')[-1]} loaded"
        )


class CogLoadError(RedError):
    """Raised by a cog when it cannot load itself.
    The message will be sent to the user."""

    pass


class MissingExtraRequirements(RedError):
    """Raised when an extra requirement is missing but required."""


class ConfigError(RedError):
    """Error in a Config operation."""


class StoredTypeError(ConfigError, TypeError):
    """A TypeError pertaining to stored Config data.

    This error may arise when, for example, trying to increment a value
    which is not a number, or trying to toggle a value which is not a
    boolean.
    """


class CannotSetSubfield(StoredTypeError):
    """Tried to set sub-field of an invalid data structure.

    This would occur in the following example::

        >>> import asyncio
        >>> from grief import Config
        >>> config = Config.get_conf(None, 1234, cog_name="Example")
        >>> async def example():
        ...     await config.foo.set(True)
        ...     await config.set_raw("foo", "bar", False)  # Should raise here
        ...
        >>> asyncio.run(example())

    """
