import random
from datetime import datetime, timezone
from typing import Tuple

import discord


class GiveawayError(Exception):
    def __init__(self, message: str):
        self.message = message


class GiveawayExecError(GiveawayError):
    pass


class GiveawayEnterError(GiveawayError):
    pass


class Giveaway:
    def __init__(
        self,
        guildid: int,
        channelid: int,
        messageid: int,
        endtime: datetime,
        prize: str = None,
        emoji: str = "🎉",
        *,
        entrants=None,
        **kwargs,
    ) -> None:
        self.guildid = guildid
        self.channelid = channelid
        self.messageid = messageid
        self.endtime = endtime
        self.prize = prize
        self.entrants = entrants or []
        self.emoji = emoji
        self.kwargs = kwargs

    async def add_entrant(
        self, user: discord.Member, *, bot, session
    ) -> Tuple[bool, GiveawayError]:
        if not self.kwargs.get("multientry", False) and user.id in self.entrants:
            raise GiveawayEnterError("You have already entered this giveaway.")
        if self.kwargs.get("roles", []) and all(
            int(role) not in [x.id for x in user.roles]
            for role in self.kwargs.get("roles", [])
        ):
            raise GiveawayEnterError(
                "You do not have the required roles to join this giveaway."
            )

        if self.kwargs.get("blacklist", []) and any(
            int(role) in [x.id for x in user.roles]
            for role in self.kwargs.get("blacklist", [])
        ):
            raise GiveawayEnterError("Your role is blacklisted from this giveaway.")
        if (
            self.kwargs.get("joined", None) is not None
            and (
                datetime.now(timezone.utc) - user.joined_at.replace(tzinfo=timezone.utc)
            ).days
            <= self.kwargs["joined"]
        ):
            raise GiveawayEnterError("Your account is too new to join this giveaway.")
        if (
            self.kwargs.get("created", None) is not None
            and (
                datetime.now(timezone.utc)
                - user.created_at.replace(tzinfo=timezone.utc)
            ).days
            <= self.kwargs["created"]
        ):
            raise GiveawayEnterError("Your account is too new to join this giveaway.")

        if required_server := self.kwargs.get("server", None):
            required_server = int(required_server[0])
            partner_guild: discord.Guild = bot.get_guild(required_server)
            if not partner_guild:
                raise GiveawayExecError
            if not partner_guild.get_member(user.id):
                msg = f"You must be a member of {partner_guild} to participate in this giveaway!"
                raise GiveawayEnterError(msg)

        self.entrants.append(user.id)
        if self.kwargs.get("multi", None) is not None and any(
            int(role) in [x.id for x in user.roles]
            for role in self.kwargs.get("multi-roles", [])
        ):
            for _ in range(self.kwargs["multi"] - 1):
                self.entrants.append(user.id)
        return

    def remove_entrant(self, userid: int) -> None:
        self.entrants = [x for x in self.entrants if x != userid]

    def draw_winner(self) -> int:
        winners = self.kwargs.get("winners") or 1
        if len(self.entrants) < winners:
            return None
        winner = random.sample(self.entrants, winners)
        self.remove_entrant(winner)
        return winner

    def __str__(self) -> str:
        return f"{self.prize} - {self.endtime}"
