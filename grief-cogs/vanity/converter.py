from __future__ import annotations

import re
from typing import List, Optional, Tuple, Union

import discord
from discord.ext.commands import BadArgument, Converter
from red_commons.logging import getLogger

from grief.core import commands
from grief.core.i18n import Translator
from grief.core.utils.chat_formatting import humanize_list

log = getLogger("grief.vanity")
_ = Translator("Vanity", __file__)


_id_regex = re.compile(r"([0-9]{15,21})$")
_mention_regex = re.compile(r"<@!?([0-9]{15,21})>$")


class RawUserIds(Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        # This is for the hackban and unban commands, where we receive IDs that
        # are most likely not in the guild.
        # Mentions are supported, but most likely won't ever be in cache.

        if match := _id_regex.match(argument) or _mention_regex.match(argument):
            return int(match.group(1))

        raise BadArgument(_("{} doesn't look like a valid user ID.").format(argument))


class RoleHierarchyConverter(commands.RoleConverter):
    """Similar to d.py's RoleConverter but only returns if we have already
    passed our hierarchy checks.
    """

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        if not ctx.guild.me.guild_permissions.manage_roles:
            raise BadArgument(
                _("I require manage roles permission to use this command.")
            )
        if isinstance(ctx, discord.Interaction):
            author = ctx.user
        else:
            author = ctx.author
        try:
            role = await commands.RoleConverter().convert(ctx, argument)
        except commands.BadArgument:
            raise
        else:
            if getattr(role, "is_bot_managed", None) and role.is_bot_managed():
                raise BadArgument(
                    _(
                        "The {role} role is a bot integration role "
                        "and cannot be assigned or removed."
                    ).format(role=role.mention)
                )
            if getattr(role, "is_integration", None) and role.is_integration():
                raise BadArgument(
                    _(
                        "The {role} role is an integration role and cannot be assigned or removed."
                    ).fromat(role=role.mention)
                )
            if (
                getattr(role, "is_premium_subscriber", None)
                and role.is_premium_subscriber()
            ):
                raise BadArgument(
                    _(
                        "The {role} role is a premium subscriber role and can only "
                        "be assigned or removed by Nitro boosting the server."
                    ).format(role=role.mention)
                )
            if role >= ctx.guild.me.top_role:
                raise BadArgument(
                    _(
                        "The {role} role is higher than my highest role in the discord hierarchy."
                    ).format(role=role.mention)
                )
            if role >= author.top_role and author.id != ctx.guild.owner_id:
                raise BadArgument(
                    _(
                        "The {role} role is higher than your "
                        "highest role in the discord hierarchy."
                    ).format(role=role.mention)
                )
        return role
