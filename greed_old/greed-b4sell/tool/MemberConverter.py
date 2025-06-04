from discord.ext.commands.converter import MemberConverter
from typing import Optional, Union
from discord.ext.commands import Context, MemberNotFound
from discord import Member
from fast_string_match import closest_match_distance as cmd
import re

_ID_REGEX = re.compile(r"([0-9]{15,20})$")


class MemberConvert(MemberConverter):
    async def convert(self, ctx: Context, arg: Union[int, str]) -> Optional[Member]:
        _id = _ID_REGEX.match(arg) or re.match(r"<@!?([0-9]{15,20})>$", arg)
        if _id is not None:
            _id = int(_id.group(1))
            if member := ctx.guild.get_member(_id):
                return member
            else:
                raise MemberNotFound(arg)
        names = [
            {m.global_name: id for m in ctx.guild.members if m.global_name is not None},
            {m.nick: m.id for m in ctx.guild.members if m.nick is not None},
            {
                m.display_name: m.id
                for m in ctx.guild.members
                if m.display_name is not None
            },
            {m.name: m.id for m in ctx.guild.members if m.name is not None},
        ]
        matches = {}
        for i, obj in enumerate(names, start=0):
            if match := cmd(arg, list(obj.keys())):
                matches[match] = i
        final = cmd(arg, list(matches.keys()))
        return ctx.guild.get_member(names[matches[final]][final])


MemberConverter.convert = MemberConvert.convert
