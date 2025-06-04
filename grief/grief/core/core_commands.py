import asyncio
import contextlib
import datetime
import getpass
import importlib
import io
import itertools
import keyword
import logging
import os
import platform
import random
import re
import sys
import traceback
from collections import defaultdict
from pathlib import Path
from string import ascii_letters, digits
from typing import (TYPE_CHECKING, Dict, Iterable, List, Literal, Optional,
                    Sequence, Set, Tuple, Union)

import aiohttp
import discord
import markdown
import pip
import psutil
from babel import Locale as BabelLocale
from babel import UnknownLocaleError

from grief.core import app_commands, data_manager
from grief.core.commands import GuildConverter, RawUserIdConverter
from grief.core.data_manager import storage_type
from grief.core.utils.menus import menu
from grief.core.utils.views import SetApiView

from . import __version__, commands, errors, i18n
from . import version_info as red_version_info
from ._diagnoser import IssueDiagnoser
from .commands import CogConverter, CommandConverter
from .commands.help import HelpMenuSetting
from .commands.requires import PrivilegeLevel
from .utils import AsyncIter, can_user_send_messages_in
from .utils._internal_utils import fetch_latest_red_version_info
from .utils.chat_formatting import (box, escape, humanize_list,
                                    humanize_number, humanize_timedelta,
                                    inline, pagify, warning)
from .utils.predicates import MessagePredicate

_entities = {
    "*": "&midast;",
    "\\": "&bsol;",
    "`": "&grave;",
    "!": "&excl;",
    "{": "&lcub;",
    "[": "&lsqb;",
    "_": "&UnderBar;",
    "(": "&lpar;",
    "#": "&num;",
    ".": "&period;",
    "+": "&plus;",
    "}": "&rcub;",
    "]": "&rsqb;",
    ")": "&rpar;",
}

PRETTY_HTML_HEAD = """
<!DOCTYPE html>
<html>
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>3rd Party Data Statements</title>
<style type="text/css">
body{margin:2em auto;max-width:800px;line-height:1.4;font-size:16px;
background-color=#EEEEEE;color:#454545;padding:1em;text-align:justify}
h1,h2,h3{line-height:1.2}
</style></head><body>
"""  # This ends up being a small bit extra that really makes a difference.

HTML_CLOSING = "</body></html>"


def entity_transformer(statement: str) -> str:
    return "".join(_entities.get(c, c) for c in statement)


if TYPE_CHECKING:
    from grief.core.bot import Grief

__all__ = ["Core"]

log = logging.getLogger("Grief")

_ = i18n.Translator("Core", __file__)

TokenConverter = commands.get_dict_converter(delims=[" ", ",", ";"])

MAX_PREFIX_LENGTH = 25


class CoreLogic:
    def __init__(self, bot: "Grief"):
        self.bot = bot
        self.bot.register_rpc_handler(self._load)
        self.bot.register_rpc_handler(self._unload)
        self.bot.register_rpc_handler(self._reload)
        self.bot.register_rpc_handler(self._name)
        self.bot.register_rpc_handler(self._prefixes)
        self.bot.register_rpc_handler(self._version_info)
        self.bot.register_rpc_handler(self._invite_url)

    async def _load(
        self, pkg_names: Iterable[str]
    ) -> Dict[str, Union[List[str], Dict[str, str]]]:
        """
        Loads packages by name.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to load.

        Returns
        -------
        dict
            Dictionary with keys:
              ``loaded_packages``: List of names of packages that loaded successfully
              ``failed_packages``: List of names of packages that failed to load without specified reason
              ``invalid_pkg_names``: List of names of packages that don't have a valid package name
              ``notfound_packages``: List of names of packages that weren't found in any cog path
              ``alreadyloaded_packages``: List of names of packages that are already loaded
              ``failed_with_reason_packages``: Dictionary of packages that failed to load with
              a specified reason with mapping of package names -> failure reason
              ``repos_with_shared_libs``: List of repo names that use deprecated shared libraries
        """
        failed_packages = []
        loaded_packages = []
        invalid_pkg_names = []
        notfound_packages = []
        alreadyloaded_packages = []
        failed_with_reason_packages = {}
        repos_with_shared_libs = set()

        bot = self.bot

        pkg_specs = []

        for name in pkg_names:
            if not name.isidentifier() or keyword.iskeyword(name):
                invalid_pkg_names.append(name)
                continue
            try:
                spec = await bot._cog_mgr.find_cog(name)
                if spec:
                    pkg_specs.append((spec, name))
                else:
                    notfound_packages.append(name)
            except Exception as e:
                log.exception("Package import failed", exc_info=e)

                exception_log = "Exception during import of package\n"
                exception_log += "".join(
                    traceback.format_exception(type(e), e, e.__traceback__)
                )
                bot._last_exception = exception_log
                failed_packages.append(name)

        async for spec, name in AsyncIter(pkg_specs, steps=10):
            try:
                self._cleanup_and_refresh_modules(spec.name)
                await bot.load_extension(spec)
            except errors.PackageAlreadyLoaded:
                alreadyloaded_packages.append(name)
            except errors.CogLoadError as e:
                failed_with_reason_packages[name] = str(e)
            except Exception as e:
                if isinstance(e, commands.CommandRegistrationError):
                    if e.alias_conflict:
                        error_message = _(
                            "Alias {alias_name} is already an existing command"
                            " or alias in one of the loaded cogs."
                        ).format(alias_name=inline(e.name))
                    else:
                        error_message = _(
                            "Command {command_name} is already an existing command"
                            " or alias in one of the loaded cogs."
                        ).format(command_name=inline(e.name))
                    failed_with_reason_packages[name] = error_message
                    continue

                log.exception("Package loading failed", exc_info=e)

                exception_log = "Exception during loading of package\n"
                exception_log += "".join(
                    traceback.format_exception(type(e), e, e.__traceback__)
                )
                bot._last_exception = exception_log
                failed_packages.append(name)
            else:
                await bot.add_loaded_package(name)
                loaded_packages.append(name)
                # remove in Grief 3.4
                downloader = bot.get_cog("Downloader")
                if downloader is None:
                    continue
                try:
                    maybe_repo = await downloader._shared_lib_load_check(name)
                except Exception:
                    log.exception(
                        "Shared library check failed,"
                        " if you're not using modified Downloader, report this issue."
                    )
                    maybe_repo = None
                if maybe_repo is not None:
                    repos_with_shared_libs.add(maybe_repo.name)

        return {
            "loaded_packages": loaded_packages,
            "failed_packages": failed_packages,
            "invalid_pkg_names": invalid_pkg_names,
            "notfound_packages": notfound_packages,
            "alreadyloaded_packages": alreadyloaded_packages,
            "failed_with_reason_packages": failed_with_reason_packages,
            "repos_with_shared_libs": list(repos_with_shared_libs),
        }

    @staticmethod
    def _cleanup_and_refresh_modules(module_name: str) -> None:
        """Internally reloads modules so that changes are detected."""
        splitted = module_name.split(".")

        def maybe_reload(new_name):
            try:
                lib = sys.modules[new_name]
            except KeyError:
                pass
            else:
                importlib._bootstrap._exec(lib.__spec__, lib)

        # noinspection PyTypeChecker
        modules = itertools.accumulate(splitted, "{}.{}".format)
        for m in modules:
            maybe_reload(m)

        children = {
            name: lib
            for name, lib in sys.modules.items()
            if name == module_name or name.startswith(f"{module_name}.")
        }
        for child_name, lib in children.items():
            importlib._bootstrap._exec(lib.__spec__, lib)

    async def _unload(self, pkg_names: Iterable[str]) -> Dict[str, List[str]]:
        """
        Unloads packages with the given names.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to unload.

        Returns
        -------
        dict
            Dictionary with keys:
              ``unloaded_packages``: List of names of packages that unloaded successfully.
              ``notloaded_packages``: List of names of packages that weren't unloaded
              because they weren't loaded.
        """
        notloaded_packages = []
        unloaded_packages = []

        bot = self.bot

        for name in pkg_names:
            if name in bot.extensions:
                await bot.unload_extension(name)
                await bot.remove_loaded_package(name)
                unloaded_packages.append(name)
            else:
                notloaded_packages.append(name)

        return {
            "unloaded_packages": unloaded_packages,
            "notloaded_packages": notloaded_packages,
        }

    async def _reload(
        self, pkg_names: Sequence[str]
    ) -> Dict[str, Union[List[str], Dict[str, str]]]:
        """
        Reloads packages with the given names.

        Parameters
        ----------
        pkg_names : `list` of `str`
            List of names of packages to reload.

        Returns
        -------
        dict
            Dictionary with keys as returned by `CoreLogic._load()`
        """
        await self._unload(pkg_names)

        return await self._load(pkg_names)

    async def _name(self, name: Optional[str] = None) -> str:
        """
        Gets or sets the bot's username.

        Parameters
        ----------
        name : str
            If passed, the bot will change it's username.

        Returns
        -------
        str
            The current (or new) username of the bot.
        """
        if name is not None:
            return (await self.bot.user.edit(username=name)).name

        return self.bot.user.name

    async def _prefixes(self, prefixes: Optional[Sequence[str]] = None) -> List[str]:
        """
        Gets or sets the bot's global prefixes.

        Parameters
        ----------
        prefixes : list of str
            If passed, the bot will set it's global prefixes.

        Returns
        -------
        list of str
            The current (or new) list of prefixes.
        """
        if prefixes:
            await self.bot.set_prefixes(guild=None, prefixes=prefixes)
            return prefixes
        return await self.bot._prefix_cache.get_prefixes(guild=None)

    @classmethod
    async def _version_info(cls) -> Dict[str, str]:
        """
        Version information for Grief and discord.py

        Returns
        -------
        dict
            `grief` and `discordpy` keys containing version information for both.
        """
        return {"grief": __version__, "discordpy": discord.__version__}

    async def _invite_url(self) -> str:
        """
        Generates the invite URL for the bot.

        Returns
        -------
        str
            Invite URL.
        """
        return await self.bot.get_invite_url()

    @staticmethod
    async def _can_get_invite_url(ctx):
        is_owner = await ctx.bot.is_owner(ctx.author)
        is_invite_public = await ctx.bot._config.invite_public()
        return is_owner or is_invite_public


@i18n.cog_i18n(_)
class Core(commands.commands._RuleDropper, commands.Cog, CoreLogic):
    """
    The Core cog has many commands related to core functions.

    These commands come loaded with every Grief bot, and cover some of the most basic usage of the bot.
    """

    @commands.command()
    async def uptime(self, ctx: commands.Context):
        """Shows [botname]'s uptime."""
        delta = datetime.datetime.utcnow() - self.bot.uptime
        uptime = self.bot.uptime.replace(tzinfo=datetime.timezone.utc)
        uptime_str = humanize_timedelta(timedelta=delta) or _("Less than one second.")
        await ctx.send(
            _("I have been up for: **{time_quantity}** (since {timestamp})").format(
                time_quantity=uptime_str, timestamp=discord.utils.format_dt(uptime, "f")
            )
        )

    @commands.command()
    @commands.is_owner()
    async def traceback(self, ctx: commands.Context, public: bool = False):
        """Sends to the owner the last command exception that has occurred.

        If public (yes is specified), it will be sent to the chat instead.

        Warning: Sending the traceback publicly can accidentally reveal sensitive information about your computer or configuration.

        **Examples:**
        - `[p]traceback` - Sends the traceback to your DMs.
        - `[p]traceback True` - Sends the last traceback in the current context.

        **Arguments:**
        - `[public]` - Whether to send the traceback to the current context. Leave blank to send to your DMs.
        """
        channel = ctx.channel if public else ctx.author

        if self.bot._last_exception:
            try:
                await self.bot.send_interactive(
                    channel,
                    pagify(self.bot._last_exception, shorten_by=10),
                    user=ctx.author,
                    box_lang="py",
                )
            except discord.HTTPException:
                await ctx.channel.send(
                    "I couldn't send the traceback message to you in DM. "
                    "Either you blocked me or you disabled DMs in this server."
                )
                return
            if not public:
                await ctx.tick()
        else:
            await ctx.send(_("No exception has occurred yet."))

    @commands.command()
    @commands.check(CoreLogic._can_get_invite_url)
    async def invite(self, ctx):
        """Shows [botname]'s invite url.

        This will always send the invite to DMs to keep it private.

        This command is locked to the owner unless `[p]inviteset public` is set to True.

        **Example:**
        - `[p]invite`
        """
        message = await self.bot.get_invite_url()
        if (admin := self.bot.get_cog("Admin")) and await admin.config.serverlocked():
            message += "\n\n" + warning(
                _(
                    "This bot is currently **serverlocked**, meaning that it is locked "
                    "to its current servers and will leave any server it joins."
                )
            )
        try:
            await ctx.author.send(message)
            await ctx.tick()
        except discord.errors.Forbidden:
            await ctx.send(
                "I couldn't send the invite message to you in DM. "
                "Either you blocked me or you disabled DMs in this server."
            )

    @commands.group()
    @commands.is_owner()
    async def inviteset(self, ctx):
        """Commands to setup [botname]'s invite settings."""
        pass

    @inviteset.command()
    async def public(self, ctx, confirm: bool = False):
        """
        Toggles if `[p]invite` should be accessible for the average user.

        The bot must be made into a `Public bot` in the developer dashboard for public invites to work.

        **Example:**
        - `[p]inviteset public yes` - Toggles the public invite setting.

        **Arguments:**
        - `[confirm]` - Required to set to public. Not required to toggle back to private.
        """
        if await self.bot._config.invite_public():
            await self.bot._config.invite_public.set(False)
            await ctx.send("The invite is now private.")
            return
        app_info = await self.bot.application_info()
        if not app_info.bot_public:
            await ctx.send(
                "I am not a public bot. That means that nobody except "
                "you can invite me on new servers.\n\n"
                "You can change this by ticking `Public bot` in "
                "your token settings: "
                "https://discord.com/developers/applications/{0}/bot".format(
                    self.bot.user.id
                )
            )
            return
        if not confirm:
            await ctx.send(
                "You're about to make the `{0}invite` command public. "
                "All users will be able to invite me on their server.\n\n"
                "If you agree, you can type `{0}inviteset public yes`.".format(
                    ctx.clean_prefix
                )
            )
        else:
            await self.bot._config.invite_public.set(True)
            await ctx.send("The invite command is now public.")

    @inviteset.command()
    async def perms(self, ctx, level: int):
        """
        Make the bot create its own role with permissions on join.

        The bot will create its own role with the desired permissions when it joins a new server. This is a special role that can't be deleted or removed from the bot.

        For that, you need to provide a valid permissions level.
        You can generate one here: https://discordapi.com/permissions.html

        Please note that you might need two factor authentication for some permissions.

        **Example:**
        - `[p]inviteset perms 134217728` - Adds a "Manage Nicknames" permission requirement to the invite.

        **Arguments:**
        - `<level>` - The permission level to require for the bot in the generated invite.
        """
        await self.bot._config.invite_perm.set(level)
        await ctx.send("The new permissions level has been set.")

    @inviteset.command()
    async def commandscope(self, ctx: commands.Context):
        """
        Add the `applications.commands` scope to your invite URL.

        This allows the usage of slash commands on the servers that invited your bot with that scope.

        Note that previous servers that invited the bot without the scope cannot have slash commands, they will have to invite the bot a second time.
        """
        enabled = not await self.bot._config.invite_commands_scope()
        await self.bot._config.invite_commands_scope.set(enabled)
        if enabled is True:
            await ctx.send(
                _("The `applications.commands` scope has been added to the invite URL.")
            )
        else:
            await ctx.send(
                _(
                    "The `applications.commands` scope has been removed from the invite URL."
                )
            )

    @commands.command()
    @commands.is_owner()
    async def leave(self, ctx: commands.Context, *servers: GuildConverter):
        """
        Leaves servers.

        If no server IDs are passed the local server will be left instead.

        Note: This command is interactive.

        **Examples:**
        - `[p]leave` - Leave the current server.
        - `[p]leave "Grief - Discord Bot"` - Quotes are necessary when there are spaces in the name.
        - `[p]leave 133049272517001216 240154543684321280` - Leaves multiple servers, using IDs.

        **Arguments:**
        - `[servers...]` - The servers to leave. When blank, attempts to leave the current server.
        """
        guilds = servers
        if ctx.guild is None and not guilds:
            return await ctx.send(_("You need to specify at least one server ID."))

        leaving_local_guild = not guilds
        number = len(guilds)

        if leaving_local_guild:
            guilds = (ctx.guild,)
            msg = (
                _(
                    "You haven't passed any server ID. Do you want me to leave this server?"
                )
                + " (yes/no)"
            )
        else:
            if number > 1:
                msg = (
                    _("Are you sure you want me to leave these servers?")
                    + " (yes/no):\n"
                    + "\n".join(f"- {guild.name} (`{guild.id}`)" for guild in guilds)
                )
            else:
                msg = (
                    _("Are you sure you want me to leave this server?")
                    + " (yes/no):\n"
                    + f"- {guilds[0].name} (`{guilds[0].id}`)"
                )

        for guild in guilds:
            if guild.owner.id == ctx.me.id:
                return await ctx.send(
                    _(
                        "I cannot leave the server `{server_name}`: I am the owner of it."
                    ).format(server_name=guild.name)
                )

        for page in pagify(msg):
            await ctx.send(page)
        pred = MessagePredicate.yes_or_no(ctx)
        try:
            await self.bot.wait_for("message", check=pred, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send(_("Response timed out."))
            return
        else:
            if pred.result is True:
                if leaving_local_guild is True:
                    await ctx.send(_("Alright. Bye :wave:"))
                else:
                    if number > 1:
                        await ctx.send(
                            _("Alright. Leaving {number} servers...").format(
                                number=number
                            )
                        )
                    else:
                        await ctx.send(_("Alright. Leaving one server..."))
                for guild in guilds:
                    log.debug("Leaving guild '%s' (%s)", guild.name, guild.id)
                    await guild.leave()
            else:
                if leaving_local_guild is True:
                    await ctx.send(_("Alright, I'll stay then. :)"))
                else:
                    if number > 1:
                        await ctx.send(_("Alright, I'm not leaving those servers."))
                    else:
                        await ctx.send(_("Alright, I'm not leaving that server."))

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def load(self, ctx: commands.Context, *cogs: str):
        """Loads cog packages from the local paths and installed cogs.

        See packages available to load with `[p]cogs`.

        Additional cogs can be added using Downloader, or from local paths using `[p]addpath`.

        **Examples:**
        - `[p]load general` - Loads the `general` cog.
        - `[p]load admin mod mutes` - Loads multiple cogs.

        **Arguments:**
        - `<cogs...>` - The cog packages to load.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            outcomes = await self._load(cogs)

        output = []

        if loaded := outcomes["loaded_packages"]:
            loaded_packages = humanize_list([inline(package) for package in loaded])
            await ctx.tick()

        if already_loaded := outcomes["alreadyloaded_packages"]:
            if len(already_loaded) == 1:
                formed = _("The following package is already loaded: {pack}").format(
                    pack=inline(already_loaded[0])
                )
            else:
                formed = _("The following packages are already loaded: {packs}").format(
                    packs=humanize_list([inline(package) for package in already_loaded])
                )
            output.append(formed)

        if failed := outcomes["failed_packages"]:
            if len(failed) == 1:
                formed = _(
                    "Failed to load the following package: {pack}."
                    "\nCheck your console or logs for details."
                ).format(pack=inline(failed[0]))
            else:
                formed = _(
                    "Failed to load the following packages: {packs}"
                    "\nCheck your console or logs for details."
                ).format(packs=humanize_list([inline(package) for package in failed]))
            output.append(formed)

        if invalid_pkg_names := outcomes["invalid_pkg_names"]:
            if len(invalid_pkg_names) == 1:
                formed = _(
                    "The following name is not a valid package name: {pack}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(pack=inline(invalid_pkg_names[0]))
            else:
                formed = _(
                    "The following names are not valid package names: {packs}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(
                    packs=humanize_list(
                        [inline(package) for package in invalid_pkg_names]
                    )
                )
            output.append(formed)

        if not_found := outcomes["notfound_packages"]:
            if len(not_found) == 1:
                formed = _(
                    "The following package was not found in any cog path: {pack}."
                ).format(pack=inline(not_found[0]))
            else:
                formed = _(
                    "The following packages were not found in any cog path: {packs}"
                ).format(
                    packs=humanize_list([inline(package) for package in not_found])
                )
            output.append(formed)

        if failed_with_reason := outcomes["failed_with_reason_packages"]:
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason.items()])
            if len(failed_with_reason) == 1:
                formed = _(
                    "This package could not be loaded for the following reason:\n\n{reason}"
                ).format(reason=reasons)
            else:
                formed = _(
                    "These packages could not be loaded for the following reasons:\n\n{reasons}"
                ).format(reasons=reasons)
            output.append(formed)

        if repos_with_shared_libs := outcomes["repos_with_shared_libs"]:
            if len(repos_with_shared_libs) == 1:
                formed = _(
                    "**WARNING**: The following repo is using shared libs"
                    " which are marked for removal in the future: {repo}.\n"
                    "You should inform maintainer of the repo about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in the future: {repos}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(
                    repos=humanize_list(
                        [inline(repo) for repo in repos_with_shared_libs]
                    )
                )
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(
                total_message, delims=["\n", ", "], priority=True, page_length=1500
            ):
                if page.startswith(", "):
                    page = page[2:]
                await ctx.send(page)

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def unload(self, ctx: commands.Context, *cogs: str):
        """Unloads previously loaded cog packages.

        See packages available to unload with `[p]cogs`.

        **Examples:**
        - `[p]unload general` - Unloads the `general` cog.
        - `[p]unload admin mod mutes` - Unloads multiple cogs.

        **Arguments:**
        - `<cogs...>` - The cog packages to unload.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        outcomes = await self._unload(cogs)

        output = []

        if unloaded := outcomes["unloaded_packages"]:
            if len(unloaded) == 1:
                await ctx.tick()
            else:
                formed = _("The following packages were unloaded: {packs}.").format(
                    packs=humanize_list([inline(package) for package in unloaded])
                )
            output.append(formed)

        if failed := outcomes["notloaded_packages"]:
            if len(failed) == 1:
                formed = _("The following package was not loaded: {pack}.").format(
                    pack=inline(failed[0])
                )
            else:
                formed = _("The following packages were not loaded: {packs}.").format(
                    packs=humanize_list([inline(package) for package in failed])
                )
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(total_message):
                await ctx.send(page)

    @commands.command(require_var_positional=True)
    @commands.is_owner()
    async def reload(self, ctx: commands.Context, *cogs: str):
        """Reloads cog packages.

        This will unload and then load the specified cogs.

        Cogs that were not loaded will only be loaded.

        **Examples:**
        - `[p]reload general` - Unloads then loads the `general` cog.
        - `[p]reload admin mod mutes` - Unloads then loads multiple cogs.

        **Arguments:**
        - `<cogs...>` - The cog packages to reload.
        """
        cogs = tuple(map(lambda cog: cog.rstrip(","), cogs))
        async with ctx.typing():
            outcomes = await self._reload(cogs)

        output = []

        if loaded := outcomes["loaded_packages"]:
            loaded_packages = humanize_list([inline(package) for package in loaded])
            await ctx.tick()

        if failed := outcomes["failed_packages"]:
            if len(failed) == 1:
                formed = _(
                    "Failed to reload the following package: {pack}."
                    "\nCheck your console or logs for details."
                ).format(pack=inline(failed[0]))
            else:
                formed = _(
                    "Failed to reload the following packages: {packs}"
                    "\nCheck your console or logs for details."
                ).format(packs=humanize_list([inline(package) for package in failed]))
            output.append(formed)

        if invalid_pkg_names := outcomes["invalid_pkg_names"]:
            if len(invalid_pkg_names) == 1:
                formed = _(
                    "The following name is not a valid package name: {pack}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(pack=inline(invalid_pkg_names[0]))
            else:
                formed = _(
                    "The following names are not valid package names: {packs}\n"
                    "Package names cannot start with a number"
                    " and can only contain ascii numbers, letters, and underscores."
                ).format(
                    packs=humanize_list(
                        [inline(package) for package in invalid_pkg_names]
                    )
                )
            output.append(formed)

        if not_found := outcomes["notfound_packages"]:
            if len(not_found) == 1:
                formed = _(
                    "The following package was not found in any cog path: {pack}."
                ).format(pack=inline(not_found[0]))
            else:
                formed = _(
                    "The following packages were not found in any cog path: {packs}"
                ).format(
                    packs=humanize_list([inline(package) for package in not_found])
                )
            output.append(formed)

        if failed_with_reason := outcomes["failed_with_reason_packages"]:
            reasons = "\n".join([f"`{x}`: {y}" for x, y in failed_with_reason.items()])
            if len(failed_with_reason) == 1:
                formed = _(
                    "This package could not be reloaded for the following reason:\n\n{reason}"
                ).format(reason=reasons)
            else:
                formed = _(
                    "These packages could not be reloaded for the following reasons:\n\n{reasons}"
                ).format(reasons=reasons)
            output.append(formed)

        if repos_with_shared_libs := outcomes["repos_with_shared_libs"]:
            if len(repos_with_shared_libs) == 1:
                formed = _(
                    "**WARNING**: The following repo is using shared libs"
                    " which are marked for removal in the future: {repo}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(repo=inline(repos_with_shared_libs.pop()))
            else:
                formed = _(
                    "**WARNING**: The following repos are using shared libs"
                    " which are marked for removal in the future: {repos}.\n"
                    "You should inform maintainers of these repos about this message."
                ).format(
                    repos=humanize_list(
                        [inline(repo) for repo in repos_with_shared_libs]
                    )
                )
            output.append(formed)

        if output:
            total_message = "\n\n".join(output)
            for page in pagify(total_message):
                await ctx.send(page)

    @staticmethod
    def _is_submodule(parent: str, child: str):
        return parent == child or child.startswith(parent + ".")

    # TODO: Guild owner permissions for guild scope slash commands and syncing?
    @commands.group()
    @commands.is_owner()
    async def slash(self, ctx: commands.Context):
        """Base command for managing what application commands are able to be used on [botname]."""

    @slash.command(name="enable")
    async def slash_enable(
        self,
        ctx: commands.Context,
        command_name: str,
        command_type: Literal["slash", "message", "user"] = "slash",
    ):
        """Marks an application command as being enabled, allowing it to be added to the bot.

        See commands available to enable with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<command_name>` - The command name to enable. Only the top level name of a group command should be used.
            - `[command_type]` - What type of application command to enable. Must be one of `slash`, `message`, or `user`. Defaults to `slash`.
        """
        command_type = command_type.lower().strip()

        if command_type == "slash":
            raw_type = discord.AppCommandType.chat_input
            command_list = self.bot.tree._disabled_global_commands
            key = command_name
        elif command_type == "message":
            raw_type = discord.AppCommandType.message
            command_list = self.bot.tree._disabled_context_menus
            key = (command_name, None, raw_type.value)
        elif command_type == "user":
            raw_type = discord.AppCommandType.user
            command_list = self.bot.tree._disabled_context_menus
            key = (command_name, None, raw_type.value)
        else:
            await ctx.send(
                _("Command type must be one of `slash`, `message`, or `user`.")
            )
            return

        current_settings = await self.bot.list_enabled_app_commands()
        current_settings = current_settings[command_type]

        if command_name in current_settings:
            await ctx.send(_("That application command is already enabled."))
            return

        if key not in command_list:
            await ctx.send(
                _(
                    "That application command could not be found. "
                    "Use `{prefix}slash list` to see all application commands. "
                    "You may need to double check the command type."
                ).format(prefix=ctx.prefix)
            )
            return

        try:
            await self.bot.enable_app_command(command_name, raw_type)
        except app_commands.CommandLimitReached:
            await ctx.send(
                _("The command limit has been reached. Disable a command first.")
            )
            return

        await self.bot.tree.red_check_enabled()
        await ctx.send(
            _("Enabled {command_type} application command `{command_name}`").format(
                command_type=command_type, command_name=command_name
            )
        )

    @slash.command(name="disable")
    async def slash_disable(
        self,
        ctx: commands.Context,
        command_name: str,
        command_type: Literal["slash", "message", "user"] = "slash",
    ):
        """Marks an application command as being disabled, preventing it from being added to the bot.

        See commands available to disable with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<command_name>` - The command name to disable. Only the top level name of a group command should be used.
            - `[command_type]` - What type of application command to disable. Must be one of `slash`, `message`, or `user`. Defaults to `slash`.
        """
        command_type = command_type.lower().strip()

        if command_type == "slash":
            raw_type = discord.AppCommandType.chat_input
        elif command_type == "message":
            raw_type = discord.AppCommandType.message
        elif command_type == "user":
            raw_type = discord.AppCommandType.user
        else:
            await ctx.send(
                _("Command type must be one of `slash`, `message`, or `user`.")
            )
            return

        existing = self.bot.tree.get_command(command_name, type=raw_type)
        if existing is not None and existing.extras.get("red_force_enable", False):
            await ctx.send(
                _(
                    "That application command has been set as required for the cog to function "
                    "by the author, and cannot be disabled. "
                    "The cog must be unloaded to remove the command."
                )
            )
            return

        current_settings = await self.bot.list_enabled_app_commands()
        current_settings = current_settings[command_type]

        if command_name not in current_settings:
            await ctx.send(
                _("That application command is already disabled or does not exist.")
            )
            return

        await self.bot.disable_app_command(command_name, raw_type)
        await self.bot.tree.red_check_enabled()
        await ctx.send(
            _("Disabled {command_type} application command `{command_name}`").format(
                command_type=command_type, command_name=command_name
            )
        )

    @slash.command(name="enablecog")
    @commands.max_concurrency(1, wait=True)
    async def slash_enablecog(self, ctx: commands.Context, cog_name: str):
        """Marks all application commands in a cog as being enabled, allowing them to be added to the bot.

        See a list of cogs with application commands with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<cog_name>` - The cog to enable commands from. This argument is case sensitive.
        """
        enabled_commands = await self.bot.list_enabled_app_commands()
        to_add_slash = []
        to_add_message = []
        to_add_user = []

        # Fetch a list of command names to enable
        for name, com in self.bot.tree._disabled_global_commands.items():
            if self._is_submodule(cog_name, com.module):
                to_add_slash.append(name)
        for key, com in self.bot.tree._disabled_context_menus.items():
            if self._is_submodule(cog_name, com.module):
                name, guild_id, com_type = key
                com_type = discord.AppCommandType(com_type)
                if com_type is discord.AppCommandType.message:
                    to_add_message.append(name)
                elif com_type is discord.AppCommandType.user:
                    to_add_user.append(name)

        # Check that we are going to enable at least one command, for user feedback
        if not (to_add_slash or to_add_message or to_add_user):
            await ctx.send(
                _(
                    "Couldn't find any disabled commands from the cog `{cog_name}`. Use `{prefix}slash list` to see all cogs with application commands."
                ).format(cog_name=cog_name, prefix=ctx.prefix)
            )
            return

        SLASH_CAP = 100
        CONTEXT_CAP = 5
        total_slash = len(enabled_commands["slash"]) + len(to_add_slash)
        total_message = len(enabled_commands["message"]) + len(to_add_message)
        total_user = len(enabled_commands["user"]) + len(to_add_user)

        # If enabling would exceed any limit, exit early to not enable only a subset
        if total_slash > SLASH_CAP:
            await ctx.send(
                _(
                    "Enabling all application commands from that cog would enable a total of {count} "
                    "commands, exceeding the {cap} command limit for slash commands. "
                    "Disable some commands first."
                ).format(count=total_slash, cap=SLASH_CAP)
            )
            return
        if total_message > CONTEXT_CAP:
            await ctx.send(
                _(
                    "Enabling all application commands from that cog would enable a total of {count} "
                    "commands, exceeding the {cap} command limit for message commands. "
                    "Disable some commands first."
                ).format(count=total_message, cap=CONTEXT_CAP)
            )
            return
        if total_user > CONTEXT_CAP:
            await ctx.send(
                _(
                    "Enabling all application commands from that cog would enable a total of {count} "
                    "commands, exceeding the {cap} command limit for user commands. "
                    "Disable some commands first."
                ).format(count=total_user, cap=CONTEXT_CAP)
            )
            return

        # Enable the cogs
        for name in to_add_slash:
            await self.bot.enable_app_command(name, discord.AppCommandType.chat_input)
        for name in to_add_message:
            await self.bot.enable_app_command(name, discord.AppCommandType.message)
        for name in to_add_user:
            await self.bot.enable_app_command(name, discord.AppCommandType.user)

        # Update the tree with the new list of enabled cogs
        await self.bot.tree.red_check_enabled()

        # Output processing
        count = len(to_add_slash) + len(to_add_message) + len(to_add_user)
        names = to_add_slash.copy()
        names.extend(to_add_message)
        names.extend(to_add_user)
        formatted_names = humanize_list([inline(name) for name in names])
        await ctx.send(
            _("Enabled {count} commands from `{cog_name}`:\n{names}").format(
                count=count, cog_name=cog_name, names=formatted_names
            )
        )

    @slash.command(name="disablecog")
    async def slash_disablecog(self, ctx: commands.Context, cog_name):
        """Marks all application commands in a cog as being disabled, preventing them from being added to the bot.

        See a list of cogs with application commands with `[p]slash list`.

        This command does NOT sync the enabled commands with Discord, that must be done manually with `[p]slash sync` for commands to appear in users' clients.

        **Arguments:**
            - `<cog_name>` - The cog to disable commands from. This argument is case sensitive.
        """
        removed = []
        for name, com in self.bot.tree._global_commands.items():
            if self._is_submodule(cog_name, com.module):
                await self.bot.disable_app_command(
                    name, discord.AppCommandType.chat_input
                )
                removed.append(name)
        for key, com in self.bot.tree._context_menus.items():
            if self._is_submodule(cog_name, com.module):
                name, guild_id, com_type = key
                await self.bot.disable_app_command(
                    name, discord.AppCommandType(com_type)
                )
                removed.append(name)
        if not removed:
            await ctx.send(
                _(
                    "Couldn't find any enabled commands from the `{cog_name}` cog. Use `{prefix}slash list` to see all cogs with application commands."
                ).format(cog_name=cog_name, prefix=ctx.prefix)
            )
            return
        await self.bot.tree.red_check_enabled()
        formatted_names = humanize_list([inline(name) for name in removed])
        await ctx.send(
            _("Disabled {count} commands from `{cog_name}`:\n{names}").format(
                count=len(removed), cog_name=cog_name, names=formatted_names
            )
        )

    @slash.command(name="list")
    async def slash_list(self, ctx: commands.Context):
        """List the slash commands the bot can see, and whether or not they are enabled.

        This command shows the state that will be changed to when `[p]slash sync` is run.
        Commands from the same cog are grouped, with the cog name as the header.

        The prefix denotes the state of the command:
        - Commands starting with `- ` have not yet been enabled.
        - Commands starting with `+ ` have been manually enabled.
        - Commands starting with `++` have been enabled by the cog author, and cannot be disabled.
        """
        cog_commands = defaultdict(list)
        slash_command_names = set()
        message_command_names = set()
        user_command_names = set()

        for command in self.bot.tree._global_commands.values():
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (
                    command.name,
                    discord.AppCommandType.chat_input,
                    True,
                    command.extras.get("red_force_enable", False),
                )
            )
            slash_command_names.add(command.name)
        for command in self.bot.tree._disabled_global_commands.values():
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (
                    command.name,
                    discord.AppCommandType.chat_input,
                    False,
                    command.extras.get("red_force_enable", False),
                )
            )
        for key, command in self.bot.tree._context_menus.items():
            # Filter out guild context menus
            if key[1] is not None:
                continue
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (
                    command.name,
                    command.type,
                    True,
                    command.extras.get("red_force_enable", False),
                )
            )
            if command.type is discord.AppCommandType.message:
                message_command_names.add(command.name)
            elif command.type is discord.AppCommandType.user:
                user_command_names.add(command.name)
        for command in self.bot.tree._disabled_context_menus.values():
            module = command.module
            if "." in module:
                module = module[: module.find(".")]
            cog_commands[module].append(
                (
                    command.name,
                    command.type,
                    False,
                    command.extras.get("red_force_enable", False),
                )
            )

        # Commands added with evals will come from __main__, make them unknown instead
        if "__main__" in cog_commands:
            main_data = cog_commands["__main__"]
            del cog_commands["__main__"]
            cog_commands["(unknown)"] = main_data

        # Commands enabled but unloaded won't appear unless accounted for
        enabled_commands = await self.bot.list_enabled_app_commands()
        unknown_slash = set(enabled_commands["slash"]) - slash_command_names
        unknown_message = set(enabled_commands["message"]) - message_command_names
        unknown_user = set(enabled_commands["user"]) - user_command_names

        unknown_slash = [
            (n, discord.AppCommandType.chat_input, True, False) for n in unknown_slash
        ]
        unknown_message = [
            (n, discord.AppCommandType.message, True, False) for n in unknown_message
        ]
        unknown_user = [
            (n, discord.AppCommandType.user, True, False) for n in unknown_user
        ]

        cog_commands["(unknown)"].extend(unknown_slash)
        cog_commands["(unknown)"].extend(unknown_message)
        cog_commands["(unknown)"].extend(unknown_user)
        # Hide it when empty
        if not cog_commands["(unknown)"]:
            del cog_commands["(unknown)"]

        if not cog_commands:
            await ctx.send(_("There are no application commands to list."))
            return

        msg = ""
        for cog in sorted(cog_commands.keys()):
            msg += cog + "\n"
            for name, raw_command_type, enabled, forced in sorted(
                cog_commands[cog], key=lambda v: v[0]
            ):
                diff = "-  "
                if forced:
                    diff = "++ "
                elif enabled:
                    diff = "+  "
                command_type = "unknown"
                if raw_command_type is discord.AppCommandType.chat_input:
                    command_type = "slash"
                elif raw_command_type is discord.AppCommandType.message:
                    command_type = "message"
                elif raw_command_type is discord.AppCommandType.user:
                    command_type = "user"
                msg += diff + command_type.ljust(7) + " | " + name + "\n"
            msg += "\n"

        pages = pagify(msg, delims=["\n\n", "\n"], shorten_by=12)
        pages = [box(page, lang="diff") for page in pages]
        await menu(ctx, pages)

    @slash.command(name="sync")
    @commands.cooldown(1, 60)
    async def slash_sync(self, ctx: commands.Context, guild: discord.Guild = None):
        """Syncs the slash settings to discord.

        Settings from `[p]slash list` will be synced with discord, changing what commands appear for users.
        This should be run sparingly, make all necessary changes before running this command.

        **Arguments:**
            - `[guild]` - If provided, syncs commands for that guild. Otherwise, syncs global commands.
        """
        # This command should not be automated due to the restrictive rate limits associated with it.
        if ctx.assume_yes:
            return
        commands = []
        async with ctx.typing():
            try:
                commands = await self.bot.tree.sync(guild=guild)
            except discord.Forbidden as e:
                # Should only be possible when syncing a guild, but just in case
                if not guild:
                    raise e
                await ctx.send(
                    _(
                        "I need the `applications.commands` scope in this server to be able to do that. "
                        "You can tell the bot to add that scope to invite links using `{prefix}inviteset commandscope`, "
                        "and can then run `{prefix}invite` to get an invite that will give the bot the scope. "
                        "You do not need to kick the bot to enable the scope, just use that invite to "
                        "re-auth the bot with the scope enabled."
                    ).format(prefix=ctx.prefix)
                )
                return
            except Exception as e:
                raise e
        await ctx.send(_("Synced {count} commands.").format(count=len(commands)))

    @slash_sync.error
    async def slash_sync_error(
        self, ctx: commands.Context, error: commands.CommandError
    ):
        """Custom cooldown error message."""
        if not isinstance(error, commands.CommandOnCooldown):
            return await ctx.bot.on_command_error(ctx, error, unhandled_by_cog=True)
        await ctx.send(
            _(
                "You seem to be attempting to sync after recently syncing. Discord does not like it "
                "when bots sync more often than neccecary, so this command has a cooldown. You "
                "should enable/disable all commands you want to change first, and run this command "
                "one time only after all changes have been made. "
            )
        )

    @commands.command(name="shutdown")
    @commands.is_owner()
    async def _shutdown(self, ctx: commands.Context, silently: bool = True):
        """Shuts down the bot."""
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Shutting down... "))
        await ctx.bot.shutdown()

    @commands.command(name="restart")
    @commands.is_owner()
    async def _restart(self, ctx: commands.Context, silently: bool = True):
        """Attempts to restart Grief."""
        with contextlib.suppress(discord.HTTPException):
            if not silently:
                await ctx.send(_("Restarting..."))
        await ctx.bot.shutdown(restart=True)

    @commands.group(name="set")
    async def _set(self, ctx: commands.Context):
        """Commands for changing [botname]'s settings."""

    # -- Bot Metadata Commands -- ###

    @_set.group(name="bot", aliases=["metadata"])
    @commands.admin_or_permissions(manage_nicknames=True)
    async def _set_bot(self, ctx: commands.Context):
        """Commands for changing Grief's metadata."""

    @_set_bot.group(name="avatar", invoke_without_command=True)
    @commands.is_owner()
    async def _set_bot_avatar(self, ctx: commands.Context, url: str = None):
        """Sets Grief's avatar."""
        if len(ctx.message.attachments) > 0:  # Attachments take priority
            data = await ctx.message.attachments[0].read()
        elif url is not None:
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        data = await r.read()
                except aiohttp.InvalidURL:
                    return await ctx.send(_("That URL is invalid."))
                except aiohttp.ClientError:
                    return await ctx.send(
                        _("Something went wrong while trying to get the image.")
                    )
        else:
            await ctx.send_help()
            return

        try:
            async with ctx.typing():
                await ctx.bot.user.edit(avatar=data)
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Failed. Remember that you can edit my avatar "
                    "up to two times a hour. The URL or attachment "
                    "must be a valid image in either JPG or PNG format."
                )
            )
        except ValueError:
            await ctx.send(_("JPG / PNG format only."))
        else:
            await ctx.send(_("Done."))

    @_set_bot_avatar.command(name="remove", aliases=["clear"])
    @commands.is_owner()
    async def _set_bot_avatar_remove(self, ctx: commands.Context):
        """Removes Grief's avatar"""
        async with ctx.typing():
            await ctx.bot.user.edit(avatar=None)
        await ctx.send(_("Avatar removed."))

    # -- End Bot Metadata Commands -- ###
    # -- Bot Status Commands -- ###

    @_set.group(name="status")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status(self, ctx: commands.Context):
        """Commands for setting [botname]'s status."""

    @_set_status.command(
        name="streaming",
        aliases=["stream", "twitch"],
        usage="[(<streamer> <stream_title>)]",
    )
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_stream(
        self,
        ctx: commands.Context,
        streamer: commands.Range[str, 1, 489] = None,
        *,
        stream_title: commands.Range[str, 1, 128] = None,
    ):
        """Sets [botname]'s streaming status to a twitch stream.

        This will appear as `Streaming <stream_title>` or `LIVE ON TWITCH` depending on the context.
        It will also include a `Watch` button with a twitch.tv url for the provided streamer.

        Maximum length for a stream title is 128 characters.

        Leaving both streamer and stream_title empty will clear it.

        **Examples:**
        - `[p]set status stream` - Clears the activity status.
        - `[p]set status stream 26 Twentysix is streaming` - Sets the stream to `https://www.twitch.tv/26`.
        - `[p]set status stream https://twitch.tv/26 Twentysix is streaming` - Sets the URL manually.

        **Arguments:**
        - `<streamer>` - The twitch streamer to provide a link to. This can be their twitch name or the entire URL.
        - `<stream_title>` - The text to follow `Streaming` in the status."""
        status = ctx.bot.guilds[0].me.status if len(ctx.bot.guilds) > 0 else None

        if stream_title:
            stream_title = stream_title.strip()
            if "twitch.tv/" not in streamer:
                streamer = "https://www.twitch.tv/" + streamer
            activity = discord.Streaming(url=streamer, name=stream_title)
            await ctx.bot.change_presence(status=status, activity=activity)
        elif streamer is not None:
            await ctx.send_help()
            return
        else:
            await ctx.bot.change_presence(activity=None, status=status)
        await ctx.send(_("Done."))

    @_set_status.command(name="playing", aliases=["game"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_game(
        self, ctx: commands.Context, *, game: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s playing status.

        This will appear as `Playing <game>` or `PLAYING A GAME: <game>` depending on the context.

        Maximum length for a playing status is 128 characters.

        **Examples:**
        - `[p]set status playing` - Clears the activity status.
        - `[p]set status playing the keyboard`

        **Arguments:**
        - `[game]` - The text to follow `Playing`. Leave blank to clear the current activity status.
        """

        if game:
            game = discord.Game(name=game)
        else:
            game = None
        status = (
            ctx.bot.guilds[0].me.status
            if len(ctx.bot.guilds) > 0
            else discord.Status.online
        )
        await ctx.bot.change_presence(status=status, activity=game)
        if game:
            await ctx.send(_("Status set to `Playing {game.name}`.").format(game=game))
        else:
            await ctx.send(_("Game cleared."))

    @_set_status.command(name="listening")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_listening(
        self, ctx: commands.Context, *, listening: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s listening status.

        This will appear as `Listening to <listening>`.

        Maximum length for a listening status is 128 characters.

        **Examples:**
        - `[p]set status listening` - Clears the activity status.
        - `[p]set status listening jams`

        **Arguments:**
        - `[listening]` - The text to follow `Listening to`. Leave blank to clear the current activity status.
        """

        status = (
            ctx.bot.guilds[0].me.status
            if len(ctx.bot.guilds) > 0
            else discord.Status.online
        )
        if listening:
            activity = discord.Activity(
                name=listening, type=discord.ActivityType.listening
            )
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(
                _("Status set to `Listening to {listening}`.").format(
                    listening=listening
                )
            )
        else:
            await ctx.send(_("Listening cleared."))

    @_set_status.command(name="watching")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_watching(
        self, ctx: commands.Context, *, watching: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s watching status.

        This will appear as `Watching <watching>`.

        Maximum length for a watching status is 128 characters.

        **Examples:**
        - `[p]set status watching` - Clears the activity status.
        - `[p]set status watching [p]help`

        **Arguments:**
        - `[watching]` - The text to follow `Watching`. Leave blank to clear the current activity status.
        """

        status = (
            ctx.bot.guilds[0].me.status
            if len(ctx.bot.guilds) > 0
            else discord.Status.online
        )
        if watching:
            activity = discord.Activity(
                name=watching, type=discord.ActivityType.watching
            )
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(
                _("Status set to `Watching {watching}`.").format(watching=watching)
            )
        else:
            await ctx.send(_("Watching cleared."))

    @_set_status.command(name="competing")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_competing(
        self, ctx: commands.Context, *, competing: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s competing status.

        This will appear as `Competing in <competing>`.

        Maximum length for a competing status is 128 characters.

        **Examples:**
        - `[p]set status competing` - Clears the activity status.
        - `[p]set status competing London 2012 Olympic Games`

        **Arguments:**
        - `[competing]` - The text to follow `Competing in`. Leave blank to clear the current activity status.
        """

        status = (
            ctx.bot.guilds[0].me.status
            if len(ctx.bot.guilds) > 0
            else discord.Status.online
        )
        if competing:
            activity = discord.Activity(
                name=competing, type=discord.ActivityType.competing
            )
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(
                _("Status set to `Competing in {competing}`.").format(
                    competing=competing
                )
            )
        else:
            await ctx.send(_("Competing cleared."))

    @_set_status.command(name="custom")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_custom(
        self, ctx: commands.Context, *, text: commands.Range[str, 1, 128] = None
    ):
        """Sets [botname]'s custom status.

        This will appear as `<text>`.

        Maximum length for a custom status is 128 characters.

        **Examples:**
        - `[p]set status custom` - Clears the activity status.
        - `[p]set status custom Running cogs...`

        **Arguments:**
        - `[text]` - The custom status text. Leave blank to clear the current activity status.
        """

        status = (
            ctx.bot.guilds[0].me.status
            if len(ctx.bot.guilds) > 0
            else discord.Status.online
        )
        if text:
            activity = discord.CustomActivity(name=text)
        else:
            activity = None
        await ctx.bot.change_presence(status=status, activity=activity)
        if activity:
            await ctx.send(_("Custom status set to `{text}`.").format(text=text))
        else:
            await ctx.send(_("Custom status cleared."))

    async def _set_my_status(self, ctx: commands.Context, status: discord.Status):
        game = ctx.bot.guilds[0].me.activity if len(ctx.bot.guilds) > 0 else None
        await ctx.bot.change_presence(status=status, activity=game)
        return await ctx.send(_("Status changed to {}.").format(status))

    @_set_status.command(name="online")
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_online(self, ctx: commands.Context):
        """Set [botname]'s status to online."""
        await self._set_my_status(ctx, discord.Status.online)

    @_set_status.command(name="dnd", aliases=["donotdisturb", "busy"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_dnd(self, ctx: commands.Context):
        """Set [botname]'s status to do not disturb."""
        await self._set_my_status(ctx, discord.Status.do_not_disturb)

    @_set_status.command(name="idle", aliases=["away", "afk"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_idle(self, ctx: commands.Context):
        """Set [botname]'s status to idle."""
        await self._set_my_status(ctx, discord.Status.idle)

    @_set_status.command(name="invisible", aliases=["offline"])
    @commands.bot_in_a_guild()
    @commands.is_owner()
    async def _set_status_invisible(self, ctx: commands.Context):
        """Set [botname]'s status to invisible."""
        await self._set_my_status(ctx, discord.Status.invisible)

    # -- End Bot Status Commands -- ###
    # -- Set Api Commands -- ###

    @_set.group(name="api", invoke_without_command=True)
    @commands.is_owner()
    async def _set_api(
        self,
        ctx: commands.Context,
        service: Optional[str] = None,
        *,
        tokens: Optional[TokenConverter] = None,
    ):
        """
        Commands to set, list or remove various external API tokens.

        This setting will be asked for by some 3rd party cogs and some core cogs.

        If passed without the `<service>` or `<tokens>` arguments it will allow you to open a modal to set your API keys securely.

        To add the keys provide the service name and the tokens as a comma separated
        list of key,values as described by the cog requesting this command.

        Note: API tokens are sensitive, so this command should only be used in a private channel or in DM with the bot.

        **Examples:**
        - `[p]set api`
        - `[p]set api spotify`
        - `[p]set api spotify redirect_uri localhost`
        - `[p]set api github client_id,whoops client_secret,whoops`

        **Arguments:**
        - `<service>` - The service you're adding tokens to.
        - `<tokens>` - Pairs of token keys and values. The key and value should be separated by one of ` `, `,`, or `;`.
        """
        if service is None or tokens is None:
            view = SetApiView(default_service=service)
            msg = await ctx.send(
                _("Click the button below to set your keys."), view=view
            )
            await view.wait()
            await msg.edit(
                content=_("This API keys setup message has expired."), view=None
            )
        else:
            if ctx.bot_permissions.manage_messages:
                await ctx.message.delete()
            await ctx.bot.set_shared_api_tokens(service, **tokens)
            await ctx.send(
                _("`{service}` API tokens have been set.").format(service=service)
            )

    @_set_api.command(name="list")
    async def _set_api_list(self, ctx: commands.Context):
        """
        Show all external API services along with their keys that have been set.

        Secrets are not shown.

        **Example:**
        - `[p]set api list`
        """

        services: dict = await ctx.bot.get_shared_api_tokens()
        if not services:
            await ctx.send(_("No API services have been set yet."))
            return

        sorted_services = sorted(services.keys(), key=str.lower)

        joined = (
            _("Set API services:\n") if len(services) > 1 else _("Set API service:\n")
        )
        for service_name in sorted_services:
            joined += "+ {}\n".format(service_name)
            for key_name in services[service_name].keys():
                joined += "  - {}\n".format(key_name)
        for page in pagify(joined, ["\n"], shorten_by=16):
            await ctx.send(box(page.lstrip(" "), lang="diff"))

    @_set_api.command(name="remove", require_var_positional=True)
    async def _set_api_remove(self, ctx: commands.Context, *services: str):
        """
        Remove the given services with all their keys and tokens.

        **Examples:**
        - `[p]set api remove spotify`
        - `[p]set api remove github youtube`

        **Arguments:**
        - `<services...>` - The services to remove."""
        bot_services = (await ctx.bot.get_shared_api_tokens()).keys()
        services = [s for s in services if s in bot_services]

        if services:
            await self.bot.remove_shared_api_services(*services)
            if len(services) > 1:
                msg = _("Services deleted successfully:\n{services_list}").format(
                    services_list=humanize_list(services)
                )
            else:
                msg = _("Service deleted successfully: {service_name}").format(
                    service_name=services[0]
                )
            await ctx.send(msg)
        else:
            await ctx.send(_("None of the services you provided had any keys set."))

    # -- End Set Api Commands -- ###

    @_set.command(
        name="prefix",
        aliases=["prefixes", "globalprefix", "globalprefixes"],
        require_var_positional=True,
    )
    @commands.is_owner()
    async def _set_prefix(self, ctx: commands.Context, *prefixes: str):
        """Sets [botname]'s global prefix(es).

        Warning: This is not additive. It will replace all current prefixes.

        See also the `--mentionable` flag to enable mentioning the bot as the prefix.

        **Examples:**
        - `[p]set prefix !`
        - `[p]set prefix "! "` - Quotes are needed to use spaces in prefixes.
        - `[p]set prefix "@[botname] "` - This uses a mention as the prefix. See also the `--mentionable` flag.
        - `[p]set prefix ! ? .` - Sets multiple prefixes.

        **Arguments:**
        - `<prefixes...>` - The prefixes the bot will respond to globally.
        """
        if any(prefix.startswith("/") for prefix in prefixes):
            await ctx.send(
                _(
                    "Prefixes cannot start with '/', as it conflicts with Discord's slash commands."
                )
            )
            return
        if any(len(x) > MAX_PREFIX_LENGTH for x in prefixes):
            await ctx.send(
                _(
                    "Warning: A prefix is above the recommended length (25 characters).\n"
                    "Do you want to continue?"
                )
                + " (yes/no)"
            )
            pred = MessagePredicate.yes_or_no(ctx)
            try:
                await self.bot.wait_for("message", check=pred, timeout=30)
            except asyncio.TimeoutError:
                await ctx.send(_("Response timed out."))
                return
            else:
                if pred.result is False:
                    await ctx.send(_("Cancelled."))
                    return
        await ctx.bot.set_prefixes(guild=None, prefixes=prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Prefix set."))
        else:
            await ctx.send(_("Prefixes set."))

    @_set.command(name="serverprefix")
    @commands.has_permissions(manage_guild=True)
    async def _server_prefix(
        self, ctx: commands.Context, server: Optional[discord.Guild], *prefixes: str
    ):
        """Sets Grief's server prefix."""
        if server is None:
            server = ctx.guild

        if not prefixes:
            await ctx.bot.set_prefixes(guild=server, prefixes=[])
            await ctx.send(_("Server prefixes have been reset."))
            return
        if any(prefix.startswith("/") for prefix in prefixes):
            await ctx.send(
                _(
                    "Prefixes cannot start with '/', as it conflicts with Discord's slash commands."
                )
            )
            return
        if any(len(x) > MAX_PREFIX_LENGTH for x in prefixes):
            await ctx.send(_("You cannot have a prefix longer than 25 characters."))
            return
        prefixes = sorted(prefixes, reverse=True)
        await ctx.bot.set_prefixes(guild=server, prefixes=prefixes)
        if len(prefixes) == 1:
            await ctx.send(_("Server prefix set."))
        else:
            await ctx.send(_("Server prefixes set."))

    @_set.command(name="usebuttons")
    @commands.is_owner()
    async def _set_usebuttons(self, ctx: commands.Context, use_buttons: bool = None):
        """
        Set a global bot variable for using buttons in menus.

        When enabled, all usage of cores menus API will use buttons instead of reactions.

        This defaults to False.
        Using this without a setting will toggle.

        **Examples:**
            - `[p]set usebuttons True` - Enables using buttons.
            - `[p]helpset usebuttons` - Toggles the value.

        **Arguments:**
            - `[use_buttons]` - Whether to use buttons. Leave blank to toggle.
        """
        if use_buttons is None:
            use_buttons = not await ctx.bot._config.use_buttons()
        await ctx.bot._config.use_buttons.set(use_buttons)
        if use_buttons:
            await ctx.send(_("I will use buttons on basic menus."))
        else:
            await ctx.send(_("I will not use buttons on basic menus."))

    @_set.command(name="errormsg")
    @commands.is_owner()
    async def _set_errormsg(self, ctx: commands.Context, *, msg: str = None):
        """
        Set the message that will be sent on uncaught bot errors.

        To include the command name in the message, use the `{command}` placeholder.

        If you omit the `msg` argument, the message will be reset to the default one.

        **Examples:**
            - `[p]set errormsg` - Resets the error message back to the default: "Error in command '{command}'.". If the command invoker is one of the bot owners, the message will also include "Check your console or logs for details.".
            - `[p]set errormsg Oops, the command {command} has failed! Please try again later.` - Sets the error message to a custom one.

        **Arguments:**
            - `[msg]` - The custom error message. Must be less than 1000 characters. Omit to reset to the default one.
        """
        if msg is not None and len(msg) >= 1000:
            return await ctx.send(_("The message must be less than 1000 characters."))

        if msg is not None:
            await self.bot._config.invoke_error_msg.set(msg)
            content = _("Successfully updated the error message.")
        else:
            await self.bot._config.invoke_error_msg.clear()
            content = _("Successfully reset the error message back to the default one.")

        await ctx.send(content)

    @commands.group()
    @commands.is_owner()
    async def helpset(self, ctx: commands.Context):
        """
        Commands to manage settings for the help command.

        All help settings are applied globally.
        """
        pass

    @helpset.command(name="showsettings")
    async def helpset_showsettings(self, ctx: commands.Context):
        """
        Show the current help settings.

        Warning: These settings may not be accurate if the default formatter is not in use.

        **Example:**
        - `[p]helpset showsettings`
        """

        help_settings = await commands.help.HelpSettings.from_context(ctx)

        if type(ctx.bot._help_formatter) is commands.help.RedHelpFormatter:
            message = help_settings.pretty
        else:
            message = _(
                "Warning: The default formatter is not in use, these settings may not apply."
            )
            message += f"\n\n{help_settings.pretty}"

        for page in pagify(message):
            await ctx.send(page)

    @helpset.command(name="resetformatter")
    async def helpset_resetformatter(self, ctx: commands.Context):
        """
        This resets [botname]'s help formatter to the default formatter.

        **Example:**
        - `[p]helpset resetformatter`
        """

        ctx.bot.reset_help_formatter()
        await ctx.send(
            _(
                "The help formatter has been reset. "
                "This will not prevent cogs from modifying help, "
                "you may need to remove a cog if this has been an issue."
            )
        )

    @helpset.command(name="resetsettings")
    async def helpset_resetsettings(self, ctx: commands.Context):
        """
        This resets [botname]'s help settings to their defaults.

        This may not have an impact when using custom formatters from 3rd party cogs

        **Example:**
        - `[p]helpset resetsettings`
        """
        await ctx.bot._config.help.clear()
        await ctx.send(
            _(
                "The help settings have been reset to their defaults. "
                "This may not have an impact when using 3rd party help formatters."
            )
        )

    @helpset.command(name="usemenus")
    async def helpset_usemenus(
        self,
        ctx: commands.Context,
        use_menus: Literal["buttons", "reactions", "select", "selectonly", "disable"],
    ):
        """
        Allows the help command to be sent as a paginated menu instead of separate
        messages.

        When "reactions", "buttons", "select", or "selectonly" is passed,
         `[p]help` will only show one page at a time
        and will use the associated control scheme to navigate between pages.

         **Examples:**
        - `[p]helpset usemenus reactions` - Enables using reaction menus.
        - `[p]helpset usemenus buttons` - Enables using button menus.
        - `[p]helpset usemenus select` - Enables buttons with a select menu.
        - `[p]helpset usemenus selectonly` - Enables a select menu only on help.
        - `[p]helpset usemenus disable` - Disables help menus.

        **Arguments:**
            - `<"buttons"|"reactions"|"select"|"selectonly"|"disable">` - Whether to use `buttons`,
            `reactions`, `select`, `selectonly`, or no menus.
        """
        if use_menus == "selectonly":
            msg = _("Help will use the select menu only.")
            await ctx.bot._config.help.use_menus.set(4)
        if use_menus == "select":
            msg = _("Help will use button menus and add a select menu.")
            await ctx.bot._config.help.use_menus.set(3)
        if use_menus == "buttons":
            msg = _("Help will use button menus.")
            await ctx.bot._config.help.use_menus.set(2)
        if use_menus == "reactions":
            msg = _("Help will use reaction menus.")
            await ctx.bot._config.help.use_menus.set(1)
        if use_menus == "disable":
            msg = _("Help will not use menus.")
            await ctx.bot._config.help.use_menus.set(0)

        await ctx.send(msg)

    @helpset.command(name="showhidden")
    async def helpset_showhidden(self, ctx: commands.Context, show_hidden: bool = None):
        """
        This allows the help command to show hidden commands.

        This defaults to False.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset showhidden True` - Enables showing hidden commands.
        - `[p]helpset showhidden` - Toggles the value.

        **Arguments:**
        - `[show_hidden]` - Whether to use show hidden commands in help. Leave blank to toggle.
        """
        if show_hidden is None:
            show_hidden = not await ctx.bot._config.help.show_hidden()
        await ctx.bot._config.help.show_hidden.set(show_hidden)
        if show_hidden:
            await ctx.send(_("Help will not filter hidden commands."))
        else:
            await ctx.send(_("Help will filter hidden commands."))

    @helpset.command(name="showaliases")
    async def helpset_showaliases(
        self, ctx: commands.Context, show_aliases: bool = None
    ):
        """
        This allows the help command to show existing commands aliases if there is any.

        This defaults to True.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset showaliases False` - Disables showing aliases on this server.
        - `[p]helpset showaliases` - Toggles the value.

        **Arguments:**
        - `[show_aliases]` - Whether to include aliases in help. Leave blank to toggle.
        """
        if show_aliases is None:
            show_aliases = not await ctx.bot._config.help.show_aliases()
        await ctx.bot._config.help.show_aliases.set(show_aliases)
        if show_aliases:
            await ctx.send(_("Help will now show command aliases."))
        else:
            await ctx.send(_("Help will no longer show command aliases."))

    @helpset.command(name="usetick")
    async def helpset_usetick(self, ctx: commands.Context, use_tick: bool = None):
        """
        This allows the help command message to be ticked if help is sent to a DM.

        Ticking is reacting to the help message with a ✅.

        Defaults to False.
        Using this without a setting will toggle.

        Note: This is only used when the bot is not using menus.

        **Examples:**
        - `[p]helpset usetick False` - Disables ticking when help is sent to DMs.
        - `[p]helpset usetick` - Toggles the value.

        **Arguments:**
        - `[use_tick]` - Whether to tick the help command when help is sent to DMs. Leave blank to toggle.
        """
        if use_tick is None:
            use_tick = not await ctx.bot._config.help.use_tick()
        await ctx.bot._config.help.use_tick.set(use_tick)
        if use_tick:
            await ctx.send(_("Help will now tick the command when sent in a DM."))
        else:
            await ctx.send(_("Help will not tick the command when sent in a DM."))

    @helpset.command(name="verifychecks")
    async def helpset_permfilter(self, ctx: commands.Context, verify: bool = None):
        """
        Sets if commands which can't be run in the current context should be filtered from help.

        Defaults to True.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset verifychecks False` - Enables showing unusable commands in help.
        - `[p]helpset verifychecks` - Toggles the value.

        **Arguments:**
        - `[verify]` - Whether to hide unusable commands in help. Leave blank to toggle.
        """
        if verify is None:
            verify = not await ctx.bot._config.help.verify_checks()
        await ctx.bot._config.help.verify_checks.set(verify)
        if verify:
            await ctx.send(_("Help will only show for commands which can be run."))
        else:
            await ctx.send(
                _("Help will show up without checking if the commands can be run.")
            )

    @helpset.command(name="verifyexists")
    async def helpset_verifyexists(self, ctx: commands.Context, verify: bool = None):
        """
        Sets whether the bot should respond to help commands for nonexistent topics.

        When enabled, this will indicate the existence of help topics, even if the user can't use it.

        Note: This setting on its own does not fully prevent command enumeration.

        Defaults to False.
        Using this without a setting will toggle.

        **Examples:**
        - `[p]helpset verifyexists True` - Enables sending help for nonexistent topics.
        - `[p]helpset verifyexists` - Toggles the value.

        **Arguments:**
        - `[verify]` - Whether to respond to help for nonexistent topics. Leave blank to toggle.
        """
        if verify is None:
            verify = not await ctx.bot._config.help.verify_exists()
        await ctx.bot._config.help.verify_exists.set(verify)
        if verify:
            await ctx.send(_("Help will verify the existence of help topics."))
        else:
            await ctx.send(
                _(
                    "Help will only verify the existence of "
                    "help topics via fuzzy help (if enabled)."
                )
            )

    @helpset.command(name="pagecharlimit")
    async def helpset_pagecharlimt(self, ctx: commands.Context, limit: int):
        """Set the character limit for each page in the help message.

        Note: This setting only applies to embedded help.

        The default value is 1000 characters. The minimum value is 500.
        The maximum is based on the lower of what you provide and what discord allows.

        Please note that setting a relatively small character limit may
        mean some pages will exceed this limit.

        **Example:**
        - `[p]helpset pagecharlimit 1500`

        **Arguments:**
        - `<limit>` - The max amount of characters to show per page in the help message.
        """
        if limit < 500:
            await ctx.send(_("You must give a value of at least 500 characters."))
            return

        await ctx.bot._config.help.page_char_limit.set(limit)
        await ctx.send(
            _("Done. The character limit per page has been set to {}.").format(limit)
        )

    @helpset.command(name="maxpages")
    async def helpset_maxpages(self, ctx: commands.Context, pages: int):
        """Set the maximum number of help pages sent in a server channel.

        Note: This setting does not apply to menu help.

        If a help message contains more pages than this value, the help message will
        be sent to the command author via DM. This is to help reduce spam in server
        text channels.

        The default value is 2 pages.

        **Examples:**
        - `[p]helpset maxpages 50` - Basically never send help to DMs.
        - `[p]helpset maxpages 0` - Always send help to DMs.

        **Arguments:**
        - `<limit>` - The max pages allowed to send per help in a server.
        """
        if pages < 0:
            await ctx.send(_("You must give a value of zero or greater!"))
            return

        await ctx.bot._config.help.max_pages_in_guild.set(pages)
        await ctx.send(_("Done. The page limit has been set to {}.").format(pages))

    @helpset.command(name="deletedelay")
    @commands.bot_has_permissions(manage_messages=True)
    async def helpset_deletedelay(self, ctx: commands.Context, seconds: int):
        """Set the delay after which help pages will be deleted.

        The setting is disabled by default, and only applies to non-menu help,
        sent in server text channels.
        Setting the delay to 0 disables this feature.

        The bot has to have MANAGE_MESSAGES permission for this to work.

        **Examples:**
        - `[p]helpset deletedelay 60` - Delete the help pages after a minute.
        - `[p]helpset deletedelay 1` - Delete the help pages as quickly as possible.
        - `[p]helpset deletedelay 1209600` - Max time to wait before deleting (14 days).
        - `[p]helpset deletedelay 0` - Disable deleting help pages.

        **Arguments:**
        - `<seconds>` - The seconds to wait before deleting help pages.
        """
        if seconds < 0:
            await ctx.send(_("You must give a value of zero or greater!"))
            return
        if seconds > 60 * 60 * 24 * 14:  # 14 days
            await ctx.send(_("The delay cannot be longer than 14 days!"))
            return

        await ctx.bot._config.help.delete_delay.set(seconds)
        if seconds == 0:
            await ctx.send(_("Done. Help messages will not be deleted now."))
        else:
            await ctx.send(
                _("Done. The delete delay has been set to {} seconds.").format(seconds)
            )

    @helpset.command(name="reacttimeout")
    async def helpset_reacttimeout(self, ctx: commands.Context, seconds: int):
        """Set the timeout for reactions, if menus are enabled.

        The default is 30 seconds.
        The timeout has to be between 15 and 300 seconds.

        **Examples:**
        - `[p]helpset reacttimeout 30` - The default timeout.
        - `[p]helpset reacttimeout 60` - Timeout of 1 minute.
        - `[p]helpset reacttimeout 15` - Minimum allowed timeout.
        - `[p]helpset reacttimeout 300` - Max allowed timeout (5 mins).

        **Arguments:**
        - `<seconds>` - The timeout, in seconds, of the reactions.
        """
        if seconds < 15:
            await ctx.send(_("You must give a value of at least 15 seconds!"))
            return
        if seconds > 300:
            await ctx.send(_("The timeout cannot be greater than 5 minutes!"))
            return

        await ctx.bot._config.help.react_timeout.set(seconds)
        await ctx.send(
            _("Done. The reaction timeout has been set to {} seconds.").format(seconds)
        )

    @helpset.command(name="tagline")
    async def helpset_tagline(self, ctx: commands.Context, *, tagline: str = None):
        """
        Set the tagline to be used.

        The maximum tagline length is 2048 characters.
        This setting only applies to embedded help. If no tagline is specified, the default will be used instead.

        **Examples:**
        - `[p]helpset tagline Thanks for using the bot!`
        - `[p]helpset tagline` - Resets the tagline to the default.

        **Arguments:**
        - `[tagline]` - The tagline to appear at the bottom of help embeds. Leave blank to reset.
        """
        if tagline is None:
            await ctx.bot._config.help.tagline.set("")
            return await ctx.send(_("The tagline has been reset."))

        if len(tagline) > 2048:
            await ctx.send(
                _(
                    "Your tagline is too long! Please shorten it to be "
                    "no more than 2048 characters long."
                )
            )
            return

        await ctx.bot._config.help.tagline.set(tagline)
        await ctx.send(_("The tagline has been set."))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def datapath(self, ctx: commands.Context):
        """Prints the bot's data path."""
        from grief.core.data_manager import basic_config

        data_dir = Path(basic_config["DATA_PATH"])
        msg = _("Data path: {path}").format(path=data_dir)
        await ctx.send(box(msg))

    @commands.command(hidden=True)
    @commands.is_owner()
    async def debuginfo(self, ctx: commands.Context):
        """Shows debug information useful for debugging."""
        from grief.core._debuginfo import DebugInfo

        await ctx.send(await DebugInfo(self.bot).get_command_text())

    # You may ask why this command is owner-only,
    # cause after all it could be quite useful to guild owners!
    # Truth to be told, that would require us to make some part of this
    # more end-user friendly rather than just bot owner friendly - terms like
    # 'global call once checks' are not of any use to someone who isn't bot owner.
    @commands.is_owner()
    @commands.command()
    async def diagnoseissues(
        self,
        ctx: commands.Context,
        channel: Optional[
            Union[
                discord.TextChannel,
                discord.VoiceChannel,
                discord.StageChannel,
                discord.Thread,
            ]
        ] = commands.CurrentChannel,
        # avoid non-default argument following default argument by using empty param()
        member: Union[discord.Member, discord.User] = commands.param(),
        *,
        command_name: str,
    ) -> None:
        """
        Diagnose issues with the command checks with ease!

        If you want to diagnose the command from a text channel in a different server,
        you can do so by using the command in DMs.

        **Example:**
        - `[p]diagnoseissues #general @Slime ban` - Diagnose why @Slime can't use `[p]ban` in #general channel.

        **Arguments:**
        - `[channel]` - The text channel that the command should be tested for. Defaults to the current channel.
        - `<member>` - The member that should be considered as the command caller.
        - `<command_name>` - The name of the command to test.
        """
        if ctx.guild is None:
            await ctx.send(
                _(
                    "A text channel, voice channel, stage channel, or thread needs to be passed"
                    " when using this command in DMs."
                )
            )
            return

        command = self.bot.get_command(command_name)
        if command is None:
            await ctx.send("Command not found!")
            return

        # This is done to allow the bot owner to diagnose a command
        # while not being a part of the server.
        if isinstance(member, discord.User):
            maybe_member = channel.guild.get_member(member.id)
            if maybe_member is None:
                await ctx.send(
                    _("The given user is not a member of the diagnosed server.")
                )
                return
            member = maybe_member

        if not can_user_send_messages_in(member, channel):
            # Let's make Flame happy here
            await ctx.send(
                _(
                    "Don't try to fool me, the given member can't access the {channel} channel!"
                ).format(channel=channel.mention)
            )
            return
        issue_diagnoser = IssueDiagnoser(self.bot, ctx, channel, member, command)
        await ctx.send(await issue_diagnoser.diagnose())

    @commands.group()
    @commands.is_owner()
    async def blacklist(self, ctx: commands.Context):
        """
        Commands to manage the blacklist.
        Use `[p]blacklist clear` to disable the blacklist
        """
        pass

    @blacklist.command(name="add", require_var_positional=True)
    async def blacklist_add(
        self, ctx: commands.Context, *member: Union[discord.Member, int]
    ):
        """
        Adds users to the blacklist.
        """
        user = await self.bot.fetch_user(member.id)

        if await ctx.bot.is_owner():
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: you may not blacklist another bot owner.",
                color=0x313338,
            )
            return await ctx.send(embed=embed, mention_author=False)

        await self.bot.add_to_blacklist(user)
        embed = discord.Embed(
            description=f"> {ctx.author.mention}: added **{member}** to the blacklist.",
            color=0x313338,
        )
        await ctx.send(embed=embed, mention_author=False)

    @blacklist.command(name="list")
    async def blacklist_list(self, ctx: commands.Context):
        """
        Lists users on the blacklist.
        """
        curr_list = await self.bot.get_blacklist()

        if not curr_list:
            await ctx.send("Blocklist is empty.")
            return
        if len(curr_list) > 1:
            msg = _("Users on the blacklist:")
        else:
            msg = _("User on the blacklist:")
        for user_id in curr_list:
            user = self.bot.get_user(user_id)
            if not user:
                user = _("Unknown or Deleted User")
            msg += f"\n\t- {user_id} ({user})"

        for page in pagify(msg):
            await ctx.send(box(page))

    @blacklist.command(name="remove", require_var_positional=True)
    async def blacklist_remove(
        self, ctx: commands.Context, *users: Union[discord.Member, int]
    ):
        """
        Removes users from the blacklist.
        """
        await self.bot.remove_from_blacklist(users)
        if len(users) > 1:
            await ctx.send(_("Users have been removed from the blacklist."))
        else:
            await ctx.send(_("User has been removed from the blacklist."))

    @blacklist.command(name="clear")
    async def blacklist_clear(self, ctx: commands.Context):
        """
        Clears the blacklist.
        """
        await self.bot.clear_blacklist()
        await ctx.send(_("Blocklist has been cleared."))

    @commands.guildowner_or_permissions(administrator=True)
    @commands.group(name="command")
    async def command_manager(self, ctx: commands.Context):
        """Commands to enable and disable commands and cogs."""
        pass

    @commands.is_owner()
    @command_manager.command(name="defaultdisablecog")
    async def command_default_disable_cog(
        self, ctx: commands.Context, *, cog: CogConverter
    ):
        """Set the default state for a cog as disabled.

        This will disable the cog for all servers by default.
        To override it, use `[p]command enablecog` on the servers you want to allow usage.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
        - `[p]command defaultdisablecog Economy`
        - `[p]command defaultdisablecog ModLog`

        **Arguments:**
        - `<cog>` - The name of the cog to make disabled by default. Must be title-case.
        """
        cogname = cog.qualified_name
        if isinstance(cog, commands.commands._RuleDropper):
            return await ctx.send(_("You can't disable this cog by default."))
        await self.bot._disabled_cog_cache.default_disable(cogname)
        await ctx.send(
            _("{cogname} has been set as disabled by default.").format(cogname=cogname)
        )

    @commands.is_owner()
    @command_manager.command(name="defaultenablecog")
    async def command_default_enable_cog(
        self, ctx: commands.Context, *, cog: CogConverter
    ):
        """Set the default state for a cog as enabled.

        This will re-enable the cog for all servers by default.
        To override it, use `[p]command disablecog` on the servers you want to disallow usage.

        Note: This will only work on loaded cogs, and must reference the title-case cog name.

        **Examples:**
        - `[p]command defaultenablecog Economy`
        - `[p]command defaultenablecog ModLog`

        **Arguments:**
        - `<cog>` - The name of the cog to make enabled by default. Must be title-case.
        """
        cogname = cog.qualified_name
        await self.bot._disabled_cog_cache.default_enable(cogname)
        await ctx.send(
            _("{cogname} has been set as enabled by default.").format(cogname=cogname)
        )

    @command_manager.group(name="listdisabled", invoke_without_command=True)
    async def list_disabled(self, ctx: commands.Context):
        """
        List disabled commands.

        If you're the bot owner, this will show global disabled commands by default.
        Otherwise, this will show disabled commands on the current server.

        **Example:**
        - `[p]command listdisabled`
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.list_disabled_global)
        else:
            await ctx.invoke(self.list_disabled_guild)

    @list_disabled.command(name="global")
    async def list_disabled_global(self, ctx: commands.Context):
        """List disabled commands globally.

        **Example:**
        - `[p]command listdisabled global`
        """
        disabled_list = await self.bot._config.disabled_commands()
        if not disabled_list:
            return await ctx.send(_("There aren't any globally disabled commands."))

        if len(disabled_list) > 1:
            header = _("{} commands are disabled globally.\n").format(
                humanize_number(len(disabled_list))
            )
        else:
            header = _("1 command is disabled globally.\n")
        paged = [box(x) for x in pagify(humanize_list(disabled_list), page_length=1000)]
        paged[0] = header + paged[0]
        await ctx.send_interactive(paged)

    @commands.guild_only()
    @list_disabled.command(name="guild")
    async def list_disabled_guild(self, ctx: commands.Context):
        """List disabled commands in this server.

        **Example:**
        - `[p]command listdisabled guild`
        """
        disabled_list = await self.bot._config.guild(ctx.guild).disabled_commands()
        if not disabled_list:
            return await ctx.send(
                _("There aren't any disabled commands in {}.").format(ctx.guild)
            )

        if len(disabled_list) > 1:
            header = _("{} commands are disabled in {}.\n").format(
                humanize_number(len(disabled_list)), ctx.guild
            )
        else:
            header = _("1 command is disabled in {}.\n").format(ctx.guild)
        paged = [box(x) for x in pagify(humanize_list(disabled_list), page_length=1000)]
        paged[0] = header + paged[0]
        await ctx.send_interactive(paged)

    @command_manager.group(name="disable", invoke_without_command=True)
    async def command_disable(
        self, ctx: commands.Context, *, command: CommandConverter
    ):
        """
        Disable a command.

        If you're the bot owner, this will disable commands globally by default.
        Otherwise, this will disable commands on the current server.

        **Examples:**
        - `[p]command disable userinfo` - Disables the `userinfo` command in the Mod cog.
        - `[p]command disable urban` - Disables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to disable.
        """
        # Select the scope based on the author's privileges
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_disable_global, command=command)
        else:
            await ctx.invoke(self.command_disable_guild, command=command)

    @commands.is_owner()
    @command_disable.command(name="global")
    async def command_disable_global(
        self, ctx: commands.Context, *, command: CommandConverter
    ):
        """
        Disable a command globally.

        **Examples:**
        - `[p]command disable global userinfo` - Disables the `userinfo` command in the Mod cog.
        - `[p]command disable global urban` - Disables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to disable globally.
        """
        if self.command_manager in command.parents or self.command_manager == command:
            await ctx.send(
                _(
                    "The command to disable cannot be `command` or any of its subcommands."
                )
            )
            return

        if isinstance(command, commands.commands._RuleDropper):
            await ctx.send(
                _(
                    "This command is designated as being always available and cannot be disabled."
                )
            )
            return

        async with ctx.bot._config.disabled_commands() as disabled_commands:
            if command.qualified_name not in disabled_commands:
                disabled_commands.append(command.qualified_name)

        if not command.enabled:
            await ctx.send(_("That command is already disabled globally."))
            return
        command.enabled = False

        await ctx.tick()

    @commands.guild_only()
    @command_disable.command(name="server", aliases=["guild"])
    async def command_disable_guild(
        self, ctx: commands.Context, *, command: CommandConverter
    ):
        """
        Disable a command in this server only.

        **Examples:**
        - `[p]command disable server userinfo` - Disables the `userinfo` command in the Mod cog.
        - `[p]command disable server urban` - Disables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to disable for the current server.
        """
        if self.command_manager in command.parents or self.command_manager == command:
            await ctx.send(
                _(
                    "The command to disable cannot be `command` or any of its subcommands."
                )
            )
            return

        if isinstance(command, commands.commands._RuleDropper):
            await ctx.send(
                _(
                    "This command is designated as being always available and cannot be disabled."
                )
            )
            return

        if command.requires.privilege_level is not None:
            if command.requires.privilege_level > await PrivilegeLevel.from_ctx(ctx):
                await ctx.send(_("You are not allowed to disable that command."))
                return

        async with ctx.bot._config.guild(
            ctx.guild
        ).disabled_commands() as disabled_commands:
            if command.qualified_name not in disabled_commands:
                disabled_commands.append(command.qualified_name)

        done = command.disable_in(ctx.guild)

        if not done:
            await ctx.send(_("That command is already disabled in this server."))
        else:
            await ctx.tick()

    @command_manager.group(name="enable", invoke_without_command=True)
    async def command_enable(self, ctx: commands.Context, *, command: CommandConverter):
        """Enable a command.

        If you're the bot owner, this will try to enable a globally disabled command by default.
        Otherwise, this will try to enable a command disabled on the current server.

        **Examples:**
        - `[p]command enable userinfo` - Enables the `userinfo` command in the Mod cog.
        - `[p]command enable urban` - Enables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to enable.
        """
        if await ctx.bot.is_owner(ctx.author):
            await ctx.invoke(self.command_enable_global, command=command)
        else:
            await ctx.invoke(self.command_enable_guild, command=command)

    @commands.is_owner()
    @command_enable.command(name="global")
    async def command_enable_global(
        self, ctx: commands.Context, *, command: CommandConverter
    ):
        """
        Enable a command globally.

        **Examples:**
        - `[p]command enable global userinfo` - Enables the `userinfo` command in the Mod cog.
        - `[p]command enable global urban` - Enables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to enable globally.
        """
        async with ctx.bot._config.disabled_commands() as disabled_commands:
            with contextlib.suppress(ValueError):
                disabled_commands.remove(command.qualified_name)

        if command.enabled:
            await ctx.send(_("That command is already enabled globally."))
            return

        command.enabled = True
        await ctx.tick()

    @commands.guild_only()
    @command_enable.command(name="server", aliases=["guild"])
    async def command_enable_guild(
        self, ctx: commands.Context, *, command: CommandConverter
    ):
        """
            Enable a command in this server.

        **Examples:**
        - `[p]command enable server userinfo` - Enables the `userinfo` command in the Mod cog.
        - `[p]command enable server urban` - Enables the `urban` command in the General cog.

        **Arguments:**
        - `<command>` - The command to enable for the current server.
        """
        if command.requires.privilege_level is not None:
            if command.requires.privilege_level > await PrivilegeLevel.from_ctx(ctx):
                await ctx.send(_("You are not allowed to enable that command."))
                return

        async with ctx.bot._config.guild(
            ctx.guild
        ).disabled_commands() as disabled_commands:
            with contextlib.suppress(ValueError):
                disabled_commands.remove(command.qualified_name)

        done = command.enable_in(ctx.guild)

        if not done:
            await ctx.send(_("That command is already enabled in this server."))
        else:
            await ctx.tick()

    @commands.is_owner()
    @command_manager.command(name="disabledmsg")
    async def command_disabledmsg(self, ctx: commands.Context, *, message: str = ""):
        """Set the bot's response to disabled commands.

        Leave blank to send nothing.

        To include the command name in the message, include the `{command}` placeholder.

        **Examples:**
        - `[p]command disabledmsg This command is disabled`
        - `[p]command disabledmsg {command} is disabled`
        - `[p]command disabledmsg` - Sends nothing when a disabled command is attempted.

        **Arguments:**
        - `[message]` - The message to send when a disabled command is attempted.
        """
        await ctx.bot._config.disabled_command_msg.set(message)
        await ctx.tick()

    # RPC handlers
    async def rpc_load(self, request):
        cog_name = request.params[0]

        spec = await self.bot._cog_mgr.find_cog(cog_name)
        if spec is None:
            raise LookupError("No such cog found.")

        self._cleanup_and_refresh_modules(spec.name)

        await self.bot.load_extension(spec)

    async def rpc_unload(self, request):
        cog_name = request.params[0]

        await self.bot.unload_extension(cog_name)

    async def rpc_reload(self, request):
        await self.rpc_unload(request)
        await self.rpc_load(request)
