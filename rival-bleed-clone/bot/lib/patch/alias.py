from fast_string_match import closest_match
from discord.ext.commands import Context, Command, Group
from discord.ext.commands.errors import CommandError
from discord.ext.commands.converter import Converter
from typing import Optional, Union, List


class CommandAlias(object):
    def __init__(self, command: Union[Command, Group, str], alias: str):
        self.command = command
        self.alias = alias


async def fill_commands(ctx: Context):
    if not hasattr(ctx.bot, "command_list"):
        commands = {}
        for command in ctx.bot.walk_commands():
            commands[command.qualified_name.lower()] = command
            for alias in command.aliases:
                if command.parent is not None:
                    c = f"{command.parent.qualified_name.lower()} "
                else:
                    c = ""
                commands[f"{c}{alias.lower()}"] = command
        ctx.bot.command_list = commands
        del commands
    return ctx.bot.command_list


class CommandConverter(Converter):
    async def convert(
        self, ctx: Context, argument: str
    ) -> Optional[Union[Command, Group]]:
        if not hasattr(ctx.bot, "command_list"):
            await fill_commands(ctx)
        if command := ctx.bot.get_command(argument):
            return command
        else:
            if match := closest_match(
                argument, [c.qualified_name for c in ctx.bot.walk_commands()]
            ):
                return ctx.bot.get_command(match)
            else:
                raise CommandError(f"Cannot find a command named **{argument}**")


class AliasConverter(Converter):
    async def convert(self, ctx: Context, argument: str) -> Optional[CommandAlias]:
        if not hasattr(ctx.bot, "command_list"):
            await fill_commands(ctx)
        if "," not in argument:
            raise CommandError("please include a `,` between the command and alias")
        else:
            command, a = argument.split(",")
            command = command.rstrip().lstrip().lower()
            a = a.rstrip().lstrip().lower()
            if a in ctx.bot.command_list:
                raise CommandError(
                    f"You cannot alias **{command}** as **{a}** as its already a command"
                )
            else:
                c = await CommandConverter().convert(ctx, command)
                cmd = CommandAlias(command=c, alias=a)
                return cmd


async def handle_aliases(ctx: Context, aliases: List[CommandAlias]):
    for a in aliases:
        msg = ctx.message.content.lower()
        msg = msg.replace(ctx.prefix, "")
        if a.alias.lower() in msg.split(" "):
            message = ctx.message
            if isinstance(a.command, str):
                b = a.command
            else:
                b = a.command.qualified_name
            message.content = message.content.replace(a.alias, b)
            return await ctx.bot.process_commands(message)
    return None