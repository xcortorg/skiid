########## SENSITIVE SECTION WARNING ###########
################################################
# Any edits of any of the exported names       #
# may result in a breaking change.             #
# Ensure no names are removed without warning. #
################################################

### DEP-WARN: Check this *every* discord.py update
from discord.app_commands import AllChannels as AllChannels
from discord.app_commands import AppCommand as AppCommand
from discord.app_commands import AppCommandChannel as AppCommandChannel
from discord.app_commands import AppCommandError as AppCommandError
from discord.app_commands import AppCommandGroup as AppCommandGroup
from discord.app_commands import AppCommandPermissions as AppCommandPermissions
from discord.app_commands import AppCommandThread as AppCommandThread
from discord.app_commands import Argument as Argument
from discord.app_commands import BotMissingPermissions as BotMissingPermissions
from discord.app_commands import CheckFailure as CheckFailure
from discord.app_commands import Choice as Choice
from discord.app_commands import Command as Command
from discord.app_commands import \
    CommandAlreadyRegistered as CommandAlreadyRegistered
from discord.app_commands import CommandInvokeError as CommandInvokeError
from discord.app_commands import CommandLimitReached as CommandLimitReached
from discord.app_commands import CommandNotFound as CommandNotFound
from discord.app_commands import CommandOnCooldown as CommandOnCooldown
from discord.app_commands import \
    CommandSignatureMismatch as CommandSignatureMismatch
from discord.app_commands import CommandSyncFailure as CommandSyncFailure
from discord.app_commands import CommandTree as CommandTree
from discord.app_commands import ContextMenu as ContextMenu
from discord.app_commands import Cooldown as Cooldown
from discord.app_commands import Group as Group
from discord.app_commands import \
    GuildAppCommandPermissions as GuildAppCommandPermissions
from discord.app_commands import MissingAnyRole as MissingAnyRole
from discord.app_commands import MissingApplicationID as MissingApplicationID
from discord.app_commands import MissingPermissions as MissingPermissions
from discord.app_commands import MissingRole as MissingRole
from discord.app_commands import Namespace as Namespace
from discord.app_commands import NoPrivateMessage as NoPrivateMessage
from discord.app_commands import Parameter as Parameter
from discord.app_commands import Range as Range
from discord.app_commands import Transform as Transform
from discord.app_commands import Transformer as Transformer
from discord.app_commands import TransformerError as TransformerError
from discord.app_commands import TranslationContext as TranslationContext
from discord.app_commands import \
    TranslationContextLocation as TranslationContextLocation
from discord.app_commands import \
    TranslationContextTypes as TranslationContextTypes
from discord.app_commands import TranslationError as TranslationError
from discord.app_commands import Translator as Translator
from discord.app_commands import autocomplete as autocomplete
from discord.app_commands import check as check
from discord.app_commands import choices as choices
from discord.app_commands import command as command
from discord.app_commands import context_menu as context_menu
from discord.app_commands import default_permissions as default_permissions
from discord.app_commands import describe as describe
from discord.app_commands import guild_only as guild_only
from discord.app_commands import guilds as guilds
from discord.app_commands import locale_str as locale_str
from discord.app_commands import rename as rename

from . import checks as checks

__all__ = (
    "AllChannels",
    "AppCommand",
    "AppCommandChannel",
    "AppCommandError",
    "AppCommandGroup",
    "AppCommandPermissions",
    "AppCommandThread",
    "Argument",
    "BotMissingPermissions",
    "Command",
    "CommandAlreadyRegistered",
    "CommandInvokeError",
    "CommandLimitReached",
    "CommandNotFound",
    "CommandOnCooldown",
    "CommandSignatureMismatch",
    "CommandSyncFailure",
    "CommandTree",
    "ContextMenu",
    "Cooldown",
    "Group",
    "GuildAppCommandPermissions",
    "MissingAnyRole",
    "MissingApplicationID",
    "MissingPermissions",
    "MissingRole",
    "Namespace",
    "NoPrivateMessage",
    "Parameter",
    "Range",
    "Transform",
    "Transformer",
    "TransformerError",
    "TranslationContext",
    "TranslationContextLocation",
    "TranslationContextTypes",
    "TranslationError",
    "Translator",
    "autocomplete",
    "check",
    "CheckFailure",
    "Choice",
    "choices",
    "command",
    "context_menu",
    "default_permissions",
    "describe",
    "guild_only",
    "guilds",
    "locale_str",
    "rename",
    "checks",
)
