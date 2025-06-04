import datetime
from collections import namedtuple
from typing import List, Tuple

import discord

from ..enums import Action, QAAction
from ..exceptions import MisconfigurationError

ACTIONS_VERBS = {
    Action.Ban: "banned",
    Action.Softban: "softbanned",
    Action.Kick: "kicked",
    Action.Punish: "punished",
    Action.NoAction: "",
}

QUICK_ACTION_EMOJIS = {
    "👢": Action.Kick,
    "🔨": Action.Ban,
    "💨": Action.Softban,
    "👊": Action.Punish,
    "👊🏻": Action.Punish,
    "👊🏼": Action.Punish,
    "👊🏾": Action.Punish,
    "👊🏿": Action.Punish,
    "🔂": QAAction.BanDeleteOneDay,
}

QuickAction = namedtuple("QuickAction", ("target", "reason"))


async def get_external_invite(guild: discord.Guild, invites: List[Tuple]):
    if not guild.me.guild_permissions.manage_guild:
        raise MisconfigurationError(
            "I need 'manage guild' permissions to fetch this server's invites."
        )

    has_vanity_url = "VANITY_URL" in guild.features
    vanity_url = await guild.vanity_invite() if has_vanity_url else ""
    if vanity_url:
        vanity_url = vanity_url.code

    own_invites = []
    for invite in await guild.invites():
        own_invites.append(invite.code)

    for invite in invites:
        if invite[1] == vanity_url:
            continue
        for own_invite in own_invites:
            if invite[1] == own_invite:
                break
        else:
            return invite[1]

    return None


def utcnow():
    if discord.version_info.major >= 2:
        return datetime.datetime.now(datetime.timezone.utc)
    else:
        return datetime.datetime.utcnow()


def timestamp(ts: datetime.datetime, relative=False):
    # Discord assumes UTC timestamps
    timestamp = int(ts.replace(tzinfo=datetime.timezone.utc).timestamp())

    if relative:
        return f"<t:{timestamp}:R>"
    else:
        return f"<t:{timestamp}>"
