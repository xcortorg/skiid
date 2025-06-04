import shlex
from typing import Dict, List, NamedTuple, Tuple, Union

import discord
from rapidfuzz import process
from unidecode import unidecode

from grief.core import commands

from .utils import (NoExitParser, is_allowed_by_hierarchy,
                    is_allowed_by_role_hierarchy)


class RoleArgumentConverter(NamedTuple):
    parsed: Dict[str, List[discord.Role]]

    @classmethod
    async def convert(
        cls, ctx: commands.Context, argument: str
    ) -> "RoleArgumentConverter":
        parser = NoExitParser(
            description="Role utils syntax help", add_help=False, allow_abbrev=True
        )
        parser.add_argument("--add", nargs="*", dest="add", default=[])
        parser.add_argument("--remove", nargs="*", dest="remove", default=[])
        try:
            vals = vars(parser.parse_args(shlex.split(argument)))
        except Exception as e:
            raise commands.BadArgument(str(e))
        if not vals["add"] and not vals["remove"]:
            raise commands.BadArgument("Must provide at least one or more actions.")
        for attr in ("add", "remove"):
            vals[attr] = [
                await commands.RoleConverter().convert(ctx, r) for r in vals[attr]
            ]
        return cls(vals)


# original converter from https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/converters.py#L19
class FuzzyRole(commands.RoleConverter):
    """
    This will accept role ID's, mentions, and perform a fuzzy search for
    roles within the guild and return a list of role objects
    matching partial names

    Guidance code on how to do this from:
    https://github.com/Rapptz/discord.py/blob/rewrite/discord/ext/commands/converter.py#L85
    https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L24
    """

    def __init__(self, response: bool = True) -> None:
        self.response: bool = response
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        try:
            basic_role = await super().convert(ctx, argument)
        except commands.BadArgument:
            pass
        else:
            return basic_role
        guild = ctx.guild
        result = [
            (r[2], r[1])
            for r in process.extract(
                argument,
                {r: unidecode(r.name) for r in guild.roles},
                limit=None,
                score_cutoff=75,
            )
        ]
        if not result:
            raise commands.BadArgument(
                f'Role "{argument}" not found.' if self.response else None
            )

        sorted_result = sorted(result, key=lambda r: r[1], reverse=True)
        return sorted_result[0][0]


class StrictRole(FuzzyRole):
    def __init__(self, response: bool = True, *, check_integrated: bool = True) -> None:
        self.response: bool = response
        self.check_integrated: bool = check_integrated
        super().__init__(response)

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Role:
        role = await super().convert(ctx, argument)
        if self.check_integrated and role.managed:
            raise commands.BadArgument(
                f"`{role}` is an integrated role and cannot be assigned."
                if self.response
                else None
            )
        allowed, message = await is_allowed_by_role_hierarchy(
            ctx.bot, ctx.me, ctx.author, role
        )
        if not allowed:
            raise commands.BadArgument(message if self.response else None)
        return role


class TouchableMember(commands.MemberConverter):
    def __init__(self, response: bool = True) -> None:
        self.response: bool = response
        super().__init__()

    async def convert(self, ctx: commands.Context, argument: str) -> discord.Member:
        member = await super().convert(ctx, argument)
        if not await is_allowed_by_hierarchy(ctx.bot, ctx.author, member):
            raise commands.BadArgument(
                f"You cannot do that since you aren't higher than {member} in hierarchy."
                if self.response
                else None
            )
        else:
            return member


class RealEmojiConverter(commands.EmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Union[discord.Emoji, str]:
        try:
            emoji = await super().convert(ctx, argument)
        except commands.BadArgument:
            try:
                await ctx.message.add_reaction(argument)
            except discord.HTTPException:
                raise commands.EmojiNotFound(argument)
            else:
                emoji = argument
        return emoji


class EmojiRole(StrictRole, RealEmojiConverter):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> Tuple[Union[discord.Emoji, str], discord.Role]:
        split = argument.split(";")
        if len(split) < 2:
            raise commands.BadArgument
        emoji = await RealEmojiConverter.convert(self, ctx, split[0])
        role = await StrictRole.convert(self, ctx, split[1])
        return emoji, role


class ObjectConverter(commands.IDConverter[discord.Object]):
    async def convert(self, ctx: commands.Context, argument: str) -> discord.Object:
        match = self._get_id_match(argument)
        if not match:
            raise commands.BadArgument
        return discord.Object(int(match.group(0)))


class TargeterArgs(commands.Converter[List[discord.Member]]):
    async def convert(
        self, ctx: commands.Context, argument: str
    ) -> List[discord.Member]:
        members = await ctx.bot.get_cog("Targeter").args_to_list(ctx, argument)
        if not members:
            raise commands.BadArgument(
                f"No one was found with the given args.\nCheck out `{ctx.clean_prefix}target help` for an explanation."
            )
        return members
