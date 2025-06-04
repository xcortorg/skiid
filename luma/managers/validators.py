import discord
import humanfriendly
from discord.ext import commands

from .helpers import Context


class ValidAlias(commands.Converter):
    async def convert(self: "ValidAlias", ctx: Context, argument: str):
        aliases = ctx.bot.flatten(
            [
                list(map(lambda c: c.lower(), cmd.aliases))
                for cmd in set(ctx.bot.walk_commands())
                if cmd.aliases
            ]
        )
        if argument.lower() in aliases:
            raise commands.BadArgument("This alias already exists")

        return argument


class ValidCommand(commands.Converter):
    async def convert(self: "ValidCommand", ctx: Context, argument: str):
        command = ctx.bot.get_command(argument)
        if not command:
            raise commands.BadArgument("This is not a valid command")

        return command.qualified_name


class ValidNickname(commands.Converter):
    async def convert(self: "ValidNickname", ctx: Context, argument: str):
        if argument.lower() == "none":
            return None

        return argument


class ValidTime(commands.Converter):
    async def convert(self: "ValidTime", ctx: Context, argument: str):
        try:
            time = humanfriendly.parse_timespan(argument)
        except humanfriendly.InvalidTimespan:
            raise commands.BadArgument("This is not a valid timespan")

        return time


class ValidPermission(commands.Converter):
    async def convert(self: "ValidPermission", ctx: Context, argument: str):
        perms = [
            p
            for p in dir(ctx.author.guild_permissions)
            if type(getattr(ctx.author.guild_permissions, p)) == bool
        ]

        if not argument in perms:
            raise commands.BadArgument("This is **not** a valid guild permission")

        return argument


class RoleConvert(commands.RoleConverter):
    async def convert(self: "RoleConvert", ctx: Context, argument: str) -> discord.Role:
        try:
            role = await super().convert(ctx, argument)
        except:
            role = ctx.find_role(argument)
            if not role:
                raise commands.RoleNotFound(argument)
        finally:
            if not role.is_assignable():
                raise commands.BadArgument("I cannot manage this role")

            if ctx.author.id != ctx.guild.owner_id:
                if role >= ctx.author.top_role:
                    raise commands.BadArgument("You cannot manage this role")

            return role


class NoStaff(commands.MemberConverter):
    async def convert(self: "NoStaff", ctx: Context, argument: str):
        try:
            member = await super().convert(ctx, argument)
        except commands.BadArgument:
            raise commands.BadArgument("No member found")

        if ctx.guild.me.top_role.position <= member.top_role.position:
            raise commands.BadArgument(f"I cannot execute on {member.mention}")

        if ctx.author.id == ctx.guild.owner_id:
            return member
        if member.id == ctx.guild.owner_id:
            raise commands.BadArgument("You cannot execute on the server owner")
        if ctx.author.top_role.position <= member.top_role.position:
            raise commands.BadArgument(f"You cannot execute on {member.mention}")

        return member
