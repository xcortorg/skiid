import asyncio
import contextlib
import importlib.metadata
import logging
import platform
import sys
import traceback
from datetime import datetime, timedelta, timezone
from typing import Tuple

import aiohttp
import discord
import rich
from packaging.requirements import Requirement
from rich import box
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from grief.core import data_manager
from grief.core.bot import ExitCodes
from grief.core.commands import HelpSettings, RedHelpFormatter
from grief.core.i18n import Translator, set_contextual_locales_from_guild

from .. import __version__ as red_version
from .. import version_info as red_version_info
from . import commands
from .config import get_latest_confs
from .utils._internal_utils import (expected_version,
                                    fetch_latest_red_version_info,
                                    format_fuzzy_results, fuzzy_command_search,
                                    send_to_owners_with_prefix_replaced)
from .utils.chat_formatting import format_perms_list, inline

log = logging.getLogger("grief")

INTRO = r"""
"""

_ = Translator(__name__, __file__)


def init_events(bot, cli_flags):
    @bot.event
    async def on_connect():
        if bot._uptime is None:
            log.info("Connected to Discord. Getting ready...")

    @bot.event
    async def on_ready():
        try:
            await _on_ready()
        except Exception as exc:
            log.critical("The bot failed to get ready!", exc_info=exc)
            sys.exit(ExitCodes.CRITICAL)

    async def _on_ready():
        if bot._uptime is not None:
            return

        bot._uptime = datetime.utcnow()

        guilds = len(bot.guilds)
        users = len(set([m for m in bot.get_all_members()]))

        invite_url = discord.utils.oauth_url(bot.application_id, scopes=("bot",))

        prefixes = cli_flags.prefix or (await bot._config.prefix())
        lang = await bot._config.locale()
        dpy_version = discord.__version__

        table_general_info = Table(show_edge=False, show_header=False, box=box.MINIMAL)
        table_general_info.add_row("Prefixes", ", ".join(prefixes))
        table_general_info.add_row("Language", lang)
        table_general_info.add_row("Discord.py version", dpy_version)
        table_general_info.add_row("Storage type", data_manager.storage_type())

        table_counts = Table(show_edge=False, show_header=False, box=box.MINIMAL)
        table_counts.add_row("Shards", str(bot.shard_count))
        table_counts.add_row("Servers", str(guilds))
        if bot.intents.members:  # Lets avoid 0 Unique Users
            table_counts.add_row("Unique Users", str(users))

        rich_console = rich.get_console()
        rich_console.print(INTRO, style="red", markup=False, highlight=False)
        if guilds:
            rich_console.print(
                Columns(
                    [
                        Panel(table_general_info, title=bot.user.display_name),
                        Panel(table_counts),
                    ],
                    equal=True,
                    align="center",
                )
            )
        else:
            rich_console.print(
                Columns([Panel(table_general_info, title=bot.user.display_name)])
            )

        rich_console.print(
            "Loaded {} cogs with {} commands".format(len(bot.cogs), len(bot.commands))
        )

        if invite_url:
            rich_console.print(
                f"\nInvite URL: {Text(invite_url, style=f'link {invite_url}')}"
            )
            # We generally shouldn't care if the client supports it or not as Rich deals with it.

        bot._red_ready.set()

    @bot.event
    async def on_command_completion(ctx: commands.Context):
        await bot._delete_delay(ctx)

    @bot.event
    async def on_command_error(ctx, error, unhandled_by_cog=False):
        if not unhandled_by_cog:
            if hasattr(ctx.command, "on_error"):
                return

            if ctx.cog:
                if ctx.cog.has_error_handler():
                    return
        if not isinstance(error, commands.CommandNotFound):
            asyncio.create_task(bot._delete_delay(ctx))
        converter = getattr(ctx.current_parameter, "converter", None)
        argument = ctx.current_argument

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send_help()
        elif isinstance(error, commands.ArgParserFailure):
            msg = _("`{user_input}` is not a valid value for `{command}`").format(
                user_input=error.user_input, command=error.cmd
            )
            if error.custom_help_msg:
                msg += f"\n{error.custom_help_msg}"
            await ctx.send(msg)
            if error.send_cmd_help:
                await ctx.send_help()
        elif isinstance(error, commands.RangeError):
            if isinstance(error.value, int):
                if error.minimum == 0 and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be a positive integer."
                    )
                elif error.minimum is None and error.maximum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be an integer no more than {maximum}."
                    )
                elif error.minimum is not None and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be an integer no less than {minimum}."
                    )
                elif error.maximum is not None and error.minimum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be an integer between {minimum} and {maximum}."
                    )
            elif isinstance(error.value, float):
                if error.minimum == 0 and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be a positive number."
                    )
                elif error.minimum is None and error.maximum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a number no more than {maximum}."
                    )
                elif error.minimum is not None and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be a number no less than {maximum}."
                    )
                elif error.maximum is not None and error.minimum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a number between {minimum} and {maximum}."
                    )
            elif isinstance(error.value, str):
                if error.minimum is None and error.maximum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a string with a length of no more than {maximum}."
                    )
                elif error.minimum is not None and error.maximum is None:
                    message = _(
                        "Argument `{parameter_name}` must be a string with a length of no less than {minimum}."
                    )
                elif error.maximum is not None and error.minimum is not None:
                    message = _(
                        "Argument `{parameter_name}` must be a string with a length of between {minimum} and {maximum}."
                    )
            await ctx.send(
                message.format(
                    maximum=error.maximum,
                    minimum=error.minimum,
                    parameter_name=ctx.current_parameter.name,
                )
            )
            return
        elif isinstance(error, commands.BadArgument):
            if isinstance(converter, commands.Range):
                if converter.annotation is int:
                    if converter.min == 0 and converter.max is None:
                        message = _(
                            "Argument `{parameter_name}` must be a positive integer."
                        )
                    elif converter.min is None and converter.max is not None:
                        message = _(
                            "Argument `{parameter_name}` must be an integer no more than {maximum}."
                        )
                    elif converter.min is not None and converter.max is None:
                        message = _(
                            "Argument `{parameter_name}` must be an integer no less than {minimum}."
                        )
                    elif converter.max is not None and converter.min is not None:
                        message = _(
                            "Argument `{parameter_name}` must be an integer between {minimum} and {maximum}."
                        )
                elif converter.annotation is float:
                    if converter.min == 0 and converter.max is None:
                        message = _(
                            "Argument `{parameter_name}` must be a positive number."
                        )
                    elif converter.min is None and converter.max is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a number no more than {maximum}."
                        )
                    elif converter.min is not None and converter.max is None:
                        message = _(
                            "Argument `{parameter_name}` must be a number no less than {minimum}."
                        )
                    elif converter.max is not None and converter.min is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a number between {minimum} and {maximum}."
                        )
                elif converter.annotation is str:
                    if error.minimum is None and error.maximum is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a string with a length of no more than {maximum}."
                        )
                    elif error.minimum is not None and error.maximum is None:
                        message = _(
                            "Argument `{parameter_name}` must be a string with a length of no less than {minimum}."
                        )
                    elif error.maximum is not None and error.minimum is not None:
                        message = _(
                            "Argument `{parameter_name}` must be a string with a length of between {minimum} and {maximum}."
                        )
                await ctx.send(
                    message.format(
                        maximum=converter.max,
                        minimum=converter.min,
                        parameter_name=ctx.current_parameter.name,
                    )
                )
                return
            if isinstance(error.__cause__, ValueError):
                if converter is int:
                    await ctx.send(
                        _('"{argument}" is not an integer.').format(argument=argument)
                    )
                    return
                if converter is float:
                    await ctx.send(
                        _('"{argument}" is not a number.').format(argument=argument)
                    )
                    return
            if error.args:
                await ctx.send(error.args[0])
            else:
                await ctx.send_help()
        elif isinstance(error, commands.UserInputError):
            await ctx.send_help()
        elif isinstance(error, commands.DisabledCommand):
            disabled_message = await bot._config.disabled_command_msg()
            if disabled_message:
                await ctx.send(disabled_message.replace("{command}", ctx.invoked_with))
        elif isinstance(error, commands.CommandInvokeError):
            log.exception(
                "Exception in command '{}'".format(ctx.command.qualified_name),
                exc_info=error.original,
            )
            exception_log = "Exception in command '{}'\n" "".format(
                ctx.command.qualified_name
            )
            exception_log += "".join(
                traceback.format_exception(type(error), error, error.__traceback__)
            )
            bot._last_exception = exception_log

            message = await bot._config.invoke_error_msg()
            if not message:
                if ctx.author.id in bot.owner_ids:
                    message = inline(
                        _(
                            "Error in command '{command}'. Check your console or logs for details."
                        )
                    )
                else:
                    message = inline(_("Error in command '{command}'."))
            await ctx.send(message.replace("{command}", ctx.command.qualified_name))
        elif isinstance(error, commands.CommandNotFound):
            help_settings = await HelpSettings.from_context(ctx)
            fuzzy_commands = await fuzzy_command_search(
                ctx,
                commands=RedHelpFormatter.help_filter_func(
                    ctx, bot.walk_commands(), help_settings=help_settings
                ),
            )
            if not fuzzy_commands:
                pass
            elif await ctx.embed_requested():
                await ctx.send(
                    embed=await format_fuzzy_results(ctx, fuzzy_commands, embed=True)
                )
            else:
                await ctx.send(
                    await format_fuzzy_results(ctx, fuzzy_commands, embed=False)
                )
        elif isinstance(error, commands.BotMissingPermissions):
            if bin(error.missing.value).count("1") == 1:  # Only one perm missing
                msg = _(
                    "I require the {permission} permission to execute that command."
                ).format(permission=format_perms_list(error.missing))
            else:
                msg = _(
                    "I require {permission_list} permissions to execute that command."
                ).format(permission_list=format_perms_list(error.missing))
            await ctx.send(msg)
        elif isinstance(error, commands.UserFeedbackCheckFailure):
            if error.message:
                await ctx.send(error.message)
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(_("That command is not available in DMs."))
        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.send(_("That command is only available in DMs."))
        elif isinstance(error, commands.NSFWChannelRequired):
            await ctx.send(_("That command is only available in NSFW channels."))
        elif isinstance(error, commands.CheckFailure):
            pass
        elif isinstance(error, commands.CommandOnCooldown):
            if bot._bypass_cooldowns and ctx.author.id in bot.owner_ids:
                ctx.command.reset_cooldown(ctx)
                new_ctx = await bot.get_context(ctx.message)
                await bot.invoke(new_ctx)
                return
            relative_time = discord.utils.format_dt(
                datetime.now(timezone.utc) + timedelta(seconds=error.retry_after), "R"
            )
            msg = _("This command is on cooldown. Try again {relative_time}.").format(
                relative_time=relative_time
            )
            await ctx.send(msg, delete_after=error.retry_after)
        elif isinstance(error, commands.MaxConcurrencyReached):
            if error.per is commands.BucketType.default:
                if error.number > 1:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used {number} times concurrently."
                    ).format(number=error.number)
                else:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used once concurrently."
                    )
            elif error.per in (commands.BucketType.user, commands.BucketType.member):
                if error.number > 1:
                    msg = _(
                        "That command is still completing,"
                        " it can only be used {number} times per {type} concurrently."
                    ).format(number=error.number, type=error.per.name)
                else:
                    msg = _(
                        "That command is still completing,"
                        " it can only be used once per {type} concurrently."
                    ).format(type=error.per.name)
            else:
                if error.number > 1:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used {number} times per {type} concurrently."
                    ).format(number=error.number, type=error.per.name)
                else:
                    msg = _(
                        "Too many people using this command."
                        " It can only be used once per {type} concurrently."
                    ).format(type=error.per.name)
            await ctx.send(msg)
        else:
            log.exception(type(error).__name__, exc_info=error)

    @bot.event
    async def on_message(message, /):
        await set_contextual_locales_from_guild(bot, message.guild)

        await bot.process_commands(message)
        discord_now = message.created_at
        if (
            not bot._checked_time_accuracy
            or (discord_now - timedelta(minutes=60)) > bot._checked_time_accuracy
        ):
            system_now = datetime.now(timezone.utc)
            diff = abs((discord_now - system_now).total_seconds())
            if diff > 60:
                log.warning(
                    "Detected significant difference (%d seconds) in system clock to discord's "
                    "clock. Any time sensitive code may fail.",
                    diff,
                )
            bot._checked_time_accuracy = discord_now

    @bot.event
    async def on_command_add(command: commands.Command):
        if command.cog is not None:
            return

        await _disable_command_no_cog(command)

    async def _guild_added(guild: discord.Guild):
        disabled_commands = await bot._config.guild(guild).disabled_commands()
        for command_name in disabled_commands:
            command_obj = bot.get_command(command_name)
            if command_obj is not None:
                command_obj.disable_in(guild)

    @bot.event
    async def on_guild_join(guild: discord.Guild):
        await _guild_added(guild)

    @bot.event
    async def on_guild_available(guild: discord.Guild):
        # We need to check guild-disabled commands here since some cogs
        # are loaded prior to `on_ready`.
        await _guild_added(guild)

    @bot.event
    async def on_guild_remove(guild: discord.Guild):
        # Clean up any unneeded checks
        disabled_commands = await bot._config.guild(guild).disabled_commands()
        for command_name in disabled_commands:
            command_obj = bot.get_command(command_name)
            if command_obj is not None:
                command_obj.enable_in(guild)

    @bot.event
    async def on_cog_add(cog: commands.Cog):
        confs = get_latest_confs()
        for c in confs:
            uuid = c.unique_identifier
            group_data = c.custom_groups
            await bot._config.custom("CUSTOM_GROUPS", c.cog_name, uuid).set(group_data)

        await _disable_commands_cog(cog)

    async def _disable_command(
        command: commands.Command, global_disabled: list, guilds_data: dict
    ):
        if command.qualified_name in global_disabled:
            command.enabled = False
        for guild_id, data in guilds_data.items():
            guild_disabled_cmds = data.get("disabled_commands", [])
            if command.qualified_name in guild_disabled_cmds:
                command.disable_in(discord.Object(id=guild_id))

    async def _disable_commands_cog(cog: commands.Cog):
        global_disabled = await bot._config.disabled_commands()
        guilds_data = await bot._config.all_guilds()
        for command in cog.walk_commands():
            await _disable_command(command, global_disabled, guilds_data)

    async def _disable_command_no_cog(command: commands.Command):
        global_disabled = await bot._config.disabled_commands()
        guilds_data = await bot._config.all_guilds()
        await _disable_command(command, global_disabled, guilds_data)
