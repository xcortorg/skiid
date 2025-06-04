########## SENSITIVE SECTION WARNING ###########
################################################
# Any edits of any of the exported names       #
# may result in a breaking change.             #
# Ensure no names are removed without warning. #
################################################

### DEP-WARN: Check this *every* discord.py update
from discord.ext.commands import ArgumentParsingError as ArgumentParsingError
from discord.ext.commands import Author as Author
from discord.ext.commands import AutoShardedBot as AutoShardedBot
from discord.ext.commands import BadArgument as BadArgument
from discord.ext.commands import BadBoolArgument as BadBoolArgument
from discord.ext.commands import BadColorArgument as BadColorArgument
from discord.ext.commands import BadColourArgument as BadColourArgument
from discord.ext.commands import BadFlagArgument as BadFlagArgument
from discord.ext.commands import BadInviteArgument as BadInviteArgument
from discord.ext.commands import BadLiteralArgument as BadLiteralArgument
from discord.ext.commands import BadUnionArgument as BadUnionArgument
from discord.ext.commands import Bot as Bot
from discord.ext.commands import BotMissingAnyRole as BotMissingAnyRole
from discord.ext.commands import BotMissingRole as BotMissingRole
from discord.ext.commands import BucketType as BucketType
from discord.ext.commands import \
    CategoryChannelConverter as CategoryChannelConverter
from discord.ext.commands import ChannelNotFound as ChannelNotFound
from discord.ext.commands import ChannelNotReadable as ChannelNotReadable
from discord.ext.commands import CheckAnyFailure as CheckAnyFailure
from discord.ext.commands import CheckFailure as CheckFailure
from discord.ext.commands import CogMeta as CogMeta
from discord.ext.commands import ColorConverter as ColorConverter
from discord.ext.commands import ColourConverter as ColourConverter
from discord.ext.commands import CommandError as CommandError
from discord.ext.commands import CommandInvokeError as CommandInvokeError
from discord.ext.commands import CommandNotFound as CommandNotFound
from discord.ext.commands import CommandOnCooldown as CommandOnCooldown
from discord.ext.commands import \
    CommandRegistrationError as CommandRegistrationError
from discord.ext.commands import ConversionError as ConversionError
from discord.ext.commands import Converter as Converter
from discord.ext.commands import Cooldown as Cooldown
from discord.ext.commands import CooldownMapping as CooldownMapping
from discord.ext.commands import CurrentChannel as CurrentChannel
from discord.ext.commands import CurrentGuild as CurrentGuild
from discord.ext.commands import DefaultHelpCommand as DefaultHelpCommand
from discord.ext.commands import DisabledCommand as DisabledCommand
from discord.ext.commands import \
    DynamicCooldownMapping as DynamicCooldownMapping
from discord.ext.commands import EmojiConverter as EmojiConverter
from discord.ext.commands import EmojiNotFound as EmojiNotFound
from discord.ext.commands import \
    ExpectedClosingQuoteError as ExpectedClosingQuoteError
from discord.ext.commands import \
    ExtensionAlreadyLoaded as ExtensionAlreadyLoaded
from discord.ext.commands import ExtensionError as ExtensionError
from discord.ext.commands import ExtensionFailed as ExtensionFailed
from discord.ext.commands import ExtensionNotFound as ExtensionNotFound
from discord.ext.commands import ExtensionNotLoaded as ExtensionNotLoaded
from discord.ext.commands import Flag as Flag
from discord.ext.commands import FlagConverter as FlagConverter
from discord.ext.commands import FlagError as FlagError
from discord.ext.commands import ForumChannelConverter as ForumChannelConverter
from discord.ext.commands import GameConverter as GameConverter
from discord.ext.commands import Greedy as Greedy
from discord.ext.commands import GuildChannelConverter as GuildChannelConverter
from discord.ext.commands import GuildConverter as GuildConverter
from discord.ext.commands import GuildNotFound as GuildNotFound
from discord.ext.commands import GuildStickerConverter as GuildStickerConverter
from discord.ext.commands import GuildStickerNotFound as GuildStickerNotFound
from discord.ext.commands import HelpCommand as HelpCommand
from discord.ext.commands import HybridCommandError as HybridCommandError
from discord.ext.commands import IDConverter as IDConverter
from discord.ext.commands import \
    InvalidEndOfQuotedStringError as InvalidEndOfQuotedStringError
from discord.ext.commands import InviteConverter as InviteConverter
from discord.ext.commands import MaxConcurrency as MaxConcurrency
from discord.ext.commands import MaxConcurrencyReached as MaxConcurrencyReached
from discord.ext.commands import MemberConverter as MemberConverter
from discord.ext.commands import MemberNotFound as MemberNotFound
from discord.ext.commands import MessageConverter as MessageConverter
from discord.ext.commands import MessageNotFound as MessageNotFound
from discord.ext.commands import MinimalHelpCommand as MinimalHelpCommand
from discord.ext.commands import MissingAnyRole as MissingAnyRole
from discord.ext.commands import MissingFlagArgument as MissingFlagArgument
from discord.ext.commands import MissingPermissions as MissingPermissions
from discord.ext.commands import \
    MissingRequiredArgument as MissingRequiredArgument
from discord.ext.commands import \
    MissingRequiredAttachment as MissingRequiredAttachment
from discord.ext.commands import MissingRequiredFlag as MissingRequiredFlag
from discord.ext.commands import MissingRole as MissingRole
from discord.ext.commands import NoEntryPointError as NoEntryPointError
from discord.ext.commands import NoPrivateMessage as NoPrivateMessage
from discord.ext.commands import NotOwner as NotOwner
from discord.ext.commands import NSFWChannelRequired as NSFWChannelRequired
from discord.ext.commands import ObjectConverter as ObjectConverter
from discord.ext.commands import ObjectNotFound as ObjectNotFound
from discord.ext.commands import Paginator as Paginator
from discord.ext.commands import Parameter as Parameter
from discord.ext.commands import \
    PartialEmojiConversionFailure as PartialEmojiConversionFailure
from discord.ext.commands import PartialEmojiConverter as PartialEmojiConverter
from discord.ext.commands import \
    PartialMessageConverter as PartialMessageConverter
from discord.ext.commands import PrivateMessageOnly as PrivateMessageOnly
from discord.ext.commands import Range as Range
from discord.ext.commands import RangeError as RangeError
from discord.ext.commands import RoleConverter as RoleConverter
from discord.ext.commands import RoleNotFound as RoleNotFound
from discord.ext.commands import \
    ScheduledEventConverter as ScheduledEventConverter
from discord.ext.commands import \
    ScheduledEventNotFound as ScheduledEventNotFound
from discord.ext.commands import StageChannelConverter as StageChannelConverter
from discord.ext.commands import TextChannelConverter as TextChannelConverter
from discord.ext.commands import ThreadConverter as ThreadConverter
from discord.ext.commands import ThreadNotFound as ThreadNotFound
from discord.ext.commands import TooManyArguments as TooManyArguments
from discord.ext.commands import TooManyFlags as TooManyFlags
from discord.ext.commands import UnexpectedQuoteError as UnexpectedQuoteError
from discord.ext.commands import UserConverter as UserConverter
from discord.ext.commands import UserInputError as UserInputError
from discord.ext.commands import UserNotFound as UserNotFound
from discord.ext.commands import VoiceChannelConverter as VoiceChannelConverter
from discord.ext.commands import after_invoke as after_invoke
from discord.ext.commands import before_invoke as before_invoke
from discord.ext.commands import bot_has_any_role as bot_has_any_role
from discord.ext.commands import \
    bot_has_guild_permissions as bot_has_guild_permissions
from discord.ext.commands import bot_has_role as bot_has_role
from discord.ext.commands import check as check
from discord.ext.commands import check_any as check_any
from discord.ext.commands import clean_content as clean_content
from discord.ext.commands import cooldown as cooldown
from discord.ext.commands import dm_only as dm_only
from discord.ext.commands import dynamic_cooldown as dynamic_cooldown
from discord.ext.commands import flag as flag
from discord.ext.commands import guild_only as guild_only
from discord.ext.commands import has_any_role as has_any_role
from discord.ext.commands import has_role as has_role
from discord.ext.commands import is_nsfw as is_nsfw
from discord.ext.commands import max_concurrency as max_concurrency
from discord.ext.commands import param as param
from discord.ext.commands import parameter as parameter
from discord.ext.commands import run_converters as run_converters
from discord.ext.commands import when_mentioned as when_mentioned
from discord.ext.commands import when_mentioned_or as when_mentioned_or

from .commands import RESERVED_COMMAND_NAMES as RESERVED_COMMAND_NAMES
from .commands import Cog as Cog
from .commands import CogCommandMixin as CogCommandMixin
from .commands import CogGroupMixin as CogGroupMixin
from .commands import CogMixin as CogMixin
from .commands import Command as Command
from .commands import Group as Group
from .commands import GroupCog as GroupCog
from .commands import GroupMixin as GroupMixin
from .commands import HybridCommand as HybridCommand
from .commands import HybridGroup as HybridGroup
from .commands import RedUnhandledAPI as RedUnhandledAPI
from .commands import command as command
from .commands import group as group
from .commands import hybrid_command as hybrid_command
from .commands import hybrid_group as hybrid_group
from .context import Context as Context
from .context import DMContext as DMContext
from .context import GuildContext as GuildContext
from .converter import CogConverter as CogConverter
from .converter import CommandConverter as CommandConverter
from .converter import DictConverter as DictConverter
from .converter import NoParseOptional as NoParseOptional
from .converter import RawUserIdConverter as RawUserIdConverter
from .converter import RelativedeltaConverter as RelativedeltaConverter
from .converter import TimedeltaConverter as TimedeltaConverter
from .converter import UserInputOptional as UserInputOptional
from .converter import finite_float as finite_float
from .converter import get_dict_converter as get_dict_converter
from .converter import get_timedelta_converter as get_timedelta_converter
from .converter import parse_relativedelta as parse_relativedelta
from .converter import parse_timedelta as parse_timedelta
from .converter import positive_int as positive_int
from .errors import ArgParserFailure as ArgParserFailure
from .errors import BotMissingPermissions as BotMissingPermissions
from .errors import UserFeedbackCheckFailure as UserFeedbackCheckFailure
from .help import HelpSettings as HelpSettings
from .help import RedHelpFormatter as RedHelpFormatter
from .help import red_help as red_help
from .requires import CheckPredicate as CheckPredicate
from .requires import GlobalPermissionModel as GlobalPermissionModel
from .requires import GuildPermissionModel as GuildPermissionModel
from .requires import PermissionModel as PermissionModel
from .requires import PermState as PermState
from .requires import PrivilegeLevel as PrivilegeLevel
from .requires import Requires as Requires
from .requires import admin as admin
from .requires import \
    admin_or_can_manage_channel as admin_or_can_manage_channel
from .requires import admin_or_permissions as admin_or_permissions
from .requires import bot_can_manage_channel as bot_can_manage_channel
from .requires import bot_can_react as bot_can_react
from .requires import bot_has_permissions as bot_has_permissions
from .requires import bot_in_a_guild as bot_in_a_guild
from .requires import can_manage_channel as can_manage_channel
from .requires import guildowner as guildowner
from .requires import \
    guildowner_or_can_manage_channel as guildowner_or_can_manage_channel
from .requires import guildowner_or_permissions as guildowner_or_permissions
from .requires import has_guild_permissions as has_guild_permissions
from .requires import has_permissions as has_permissions
from .requires import is_owner as is_owner
from .requires import mod as mod
from .requires import mod_or_can_manage_channel as mod_or_can_manage_channel
from .requires import mod_or_permissions as mod_or_permissions
from .requires import permissions_check as permissions_check

__all__ = (
    "Cog",
    "CogMixin",
    "CogCommandMixin",
    "CogGroupMixin",
    "Command",
    "Group",
    "GroupCog",
    "GroupMixin",
    "command",
    "HybridCommand",
    "HybridGroup",
    "hybrid_command",
    "hybrid_group",
    "group",
    "RedUnhandledAPI",
    "RESERVED_COMMAND_NAMES",
    "Context",
    "GuildContext",
    "DMContext",
    "DictConverter",
    "RelativedeltaConverter",
    "TimedeltaConverter",
    "get_dict_converter",
    "get_timedelta_converter",
    "parse_relativedelta",
    "parse_timedelta",
    "NoParseOptional",
    "UserInputOptional",
    "RawUserIdConverter",
    "CogConverter",
    "CommandConverter",
    "BotMissingPermissions",
    "UserFeedbackCheckFailure",
    "ArgParserFailure",
    "red_help",
    "RedHelpFormatter",
    "HelpSettings",
    "CheckPredicate",
    "GlobalPermissionModel",
    "GuildPermissionModel",
    "PermissionModel",
    "PrivilegeLevel",
    "PermState",
    "Requires",
    "permissions_check",
    "bot_has_permissions",
    "bot_in_a_guild",
    "bot_can_manage_channel",
    "bot_can_react",
    "has_permissions",
    "can_manage_channel",
    "has_guild_permissions",
    "is_owner",
    "guildowner",
    "guildowner_or_can_manage_channel",
    "guildowner_or_permissions",
    "admin",
    "admin_or_can_manage_channel",
    "admin_or_permissions",
    "mod",
    "mod_or_can_manage_channel",
    "mod_or_permissions",
    "BadArgument",
    "EmojiConverter",
    "GuildConverter",
    "InvalidEndOfQuotedStringError",
    "MemberConverter",
    "BotMissingRole",
    "PrivateMessageOnly",
    "HelpCommand",
    "MinimalHelpCommand",
    "DisabledCommand",
    "ExtensionFailed",
    "Bot",
    "NotOwner",
    "CategoryChannelConverter",
    "CogMeta",
    "ConversionError",
    "UserInputError",
    "Converter",
    "InviteConverter",
    "ExtensionError",
    "Cooldown",
    "CheckFailure",
    "PartialMessageConverter",
    "MessageConverter",
    "MissingPermissions",
    "BadUnionArgument",
    "DefaultHelpCommand",
    "ExtensionNotFound",
    "UserConverter",
    "MissingRole",
    "CommandOnCooldown",
    "MissingAnyRole",
    "ExtensionNotLoaded",
    "clean_content",
    "CooldownMapping",
    "ArgumentParsingError",
    "RoleConverter",
    "CommandError",
    "TextChannelConverter",
    "UnexpectedQuoteError",
    "Paginator",
    "BucketType",
    "NoEntryPointError",
    "CommandInvokeError",
    "TooManyArguments",
    "Greedy",
    "ExpectedClosingQuoteError",
    "ColourConverter",
    "ColorConverter",
    "VoiceChannelConverter",
    "StageChannelConverter",
    "NSFWChannelRequired",
    "IDConverter",
    "MissingRequiredArgument",
    "GameConverter",
    "CommandNotFound",
    "BotMissingAnyRole",
    "NoPrivateMessage",
    "AutoShardedBot",
    "ExtensionAlreadyLoaded",
    "PartialEmojiConverter",
    "check_any",
    "max_concurrency",
    "CheckAnyFailure",
    "MaxConcurrency",
    "MaxConcurrencyReached",
    "bot_has_guild_permissions",
    "CommandRegistrationError",
    "GuildNotFound",
    "MessageNotFound",
    "MemberNotFound",
    "UserNotFound",
    "ChannelNotFound",
    "ChannelNotReadable",
    "BadColourArgument",
    "RoleNotFound",
    "BadInviteArgument",
    "EmojiNotFound",
    "PartialEmojiConversionFailure",
    "BadBoolArgument",
    "TooManyFlags",
    "MissingRequiredFlag",
    "flag",
    "FlagError",
    "ObjectNotFound",
    "GuildStickerNotFound",
    "ThreadNotFound",
    "GuildChannelConverter",
    "run_converters",
    "Flag",
    "BadFlagArgument",
    "BadColorArgument",
    "dynamic_cooldown",
    "BadLiteralArgument",
    "DynamicCooldownMapping",
    "ThreadConverter",
    "GuildStickerConverter",
    "ObjectConverter",
    "FlagConverter",
    "MissingFlagArgument",
    "ScheduledEventConverter",
    "ScheduledEventNotFound",
    "check",
    "guild_only",
    "cooldown",
    "dm_only",
    "is_nsfw",
    "has_role",
    "has_any_role",
    "bot_has_role",
    "when_mentioned_or",
    "when_mentioned",
    "bot_has_any_role",
    "before_invoke",
    "after_invoke",
    "CurrentChannel",
    "Author",
    "param",
    "MissingRequiredAttachment",
    "Parameter",
    "ForumChannelConverter",
    "CurrentGuild",
    "Range",
    "RangeError",
    "parameter",
    "HybridCommandError",
)
