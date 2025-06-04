import datetime
from typing import Generator, List

import discord
from discord import Embed
from discord.ext import commands
from discord.ext.commands import Command, Context, Group
from tools.exceptions import InvalidSubCommand


class OnCooldown(Exception):
    pass


def generate(ctx: Context, c: Command, example: str = "", usage=False) -> str:
    params = " ".join(f"<{param}>" for param in c.clean_params.keys())
    if usage is True:
        if example != "":
            ex = f"\n> [**Example:**](https://wock.bot) **{example}**"
        else:
            ex = ""
        return f"> [**Syntax:**](https://wock.bot) **{ctx.prefix}{c.qualified_name} {params}**{ex}"
    if len(c.qualified_name.lower().split(" ")) > 2:
        m = f" for {c.qualified_name.lower().split(' ')[-1]}s"
    else:
        m = ""
    if "add" in c.qualified_name.lower() or "create" in c.qualified_name.lower():
        if c.brief is None:
            return f"create a new {c.qualified_name.lower().split(' ')[0]}{m}"
    elif "remove" in c.qualified_name.lower() or "delete" in c.qualified_name.lower():
        if c.brief is None:
            return f"delete a {c.qualified_name.lower().split(' ')[0]}{m}"
    elif "clear" in c.qualified_name.lower():
        if c.brief is None:
            return f"clear {c.qualified_name.lower().split(' ')[0]}{m}"
    else:
        if c.brief is None:
            if m == "":
                if c.root_parent is not None:
                    m = f" {c.root_parent.name.lower()}"
            if len(c.clean_params.keys()) == 0:
                n = "view "
            else:
                n = "change "
            return f"{n}the {c.name.lower()}{m}"


def chunks(array: List, chunk_size: int) -> Generator[List, None, None]:
    for i in range(0, len(array), chunk_size):
        yield array[i : i + chunk_size]


class CogConverter(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        cogs = [i for i in ctx.bot.cogs]
        for cog in cogs:
            if cog.lower() == argument.lower():
                return ctx.bot.cogs.get(cog)
        return None


class MyHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        if retry_after := await self.context.bot.glory_cache.ratelimited(
            f"rl:user_commands{self.context.author.id}", 2, 4
        ):
            raise commands.CommandOnCooldown(None, retry_after, None)
        total_commands = len(
            [
                c
                for c in self.context.bot.walk_commands()
                if c.cog_name
                and c.cog_name.lower()
                not in ["owner", "jishaku", "errors", "webserver"]
            ]
        )
        embed = discord.Embed(
            description=f"[**Wocks Website**]({self.context.bot.domain}) has **{total_commands} commands** listed",
            color=0x2B2D31,
        )
        return await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        return

    def subcommand_not_found(self, command, string):
        if isinstance(command, Group) and len(command.all_commands) > 0:
            raise InvalidSubCommand(
                f'**Command** "{command.qualified_name}" has **no subcommand named** `{string}`'
            )
        raise InvalidSubCommand(
            f'**Command** "{command.qualified_name}" **has** `no subcommands.`'
        )

    async def send_group_help(self, group):
        if retry_after := await self.context.bot.glory_cache.ratelimited(
            f"rl:user_commands{self.context.author.id}", 2, 4
        ):
            raise commands.CommandOnCooldown(None, retry_after, None)

        embed: Embed = Embed(color=0x2B2D31, timestamp=datetime.datetime.now())
        ctx = self.context
        commands: List = []
        embeds = []

        commands = [c for c in group.walk_commands()]
        commands.append(group)
        for i, command in enumerate(commands, start=1):
            if command.perms is None or len(command.perms) == 0:
                await command.can_run(ctx)
            embed = Embed(color=0x2B2D31, timestamp=datetime.datetime.now())
            embed.title = f"{command.qualified_name}"
            if command.brief is not None and command.brief != "":
                brief = command.brief
            else:
                brief = generate(ctx, command)
            if len(command.clean_params.keys()) > 0:
                params = "".join(f"{c}, " for c in command.clean_params.keys())
                params = params[:-2]
                embed.add_field(name="Parameters", value=params, inline=True)
            try:
                if command.perms[0].lower() != "send_messages":
                    embed.add_field(
                        name="Permissions",
                        value=f"`{command.perms[0].replace('_',' ').title()}`",
                        inline=True,
                    )
            except Exception:
                pass
            if command.example is not None:
                example = command.example.replace(",", self.context.prefix)
            else:
                example = ""
            embed.description = brief
            embed.add_field(
                name="Usage", value=generate(ctx, command, example, True), inline=False
            )
            if flags := command.parameters:
                d = []
                descriptions = []
                for flag_name, flag in flags.items():
                    if (
                        flag.get("description")
                        and flag.get("description") not in descriptions
                    ):
                        descriptions.append(flag.get("description"))
                        if flag["converter"] == int:
                            flag_value = "number"
                        if flag["converter"] == bool:
                            flag_value = "true/false"
                        else:
                            flag_value = "text"
                        if default := flag.get("default"):
                            if "{embed}" not in str(default):
                                m = f"(default: `{flag['default']}`)"
                            else:
                                m = "(default: `embed object`)"
                        else:
                            m = ""
                        if description := flag.get("description"):
                            f = f"{description} "
                        else:
                            f = ""
                        d.append(
                            f"> [**{flag_name.title()}:**](https://wock.bot) **{f}{flag_value} {m}**"
                        )
                embed.add_field(
                    name="Flags", value="".join(f"{_}\n" for _ in d), inline=True
                )
            if len(command.aliases) > 0:
                aliases = "".join(f"{a}, " for a in command.aliases)
                aliases = aliases[:-2]
            else:
                aliases = "N/A"

            embed.set_footer(
                text=f"Aliases: {aliases}・Module: {command.cog_name.replace('.py','')}・{i}/{len(commands)}"
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            embeds.append(embed)
            continue
        return await self.context.paginate(embeds)

    def get_example(self, command):
        if len(command.clean_params.keys()) == 0:
            return ""
        ex = f"{self.context.prefix}{command.qualified_name} "
        for key, value in command.clean_params.items():
            if "user" in repr(value).lower() or "member" in repr(value).lower():
                ex += "@o_5v "
            elif "role" in repr(value).lower():
                ex += "@mod "
            elif "image" in repr(value).lower() or "attachment" in repr(value).lower():
                ex += "https://gyazo.com/273.png "
            elif "channel" in repr(value).lower():
                ex += "#text "
            elif key.lower() == "reason":
                ex += "being annoying "
            else:
                ex += f"<{key}> "
        return ex

    def get_usage(self, command):
        if len(command.clean_params.keys()) == 0:
            return ""
        usage = f"{self.context.prefix}{command.qualified_name} "
        for key, value in command.clean_params.items():
            usage += f"<{key}> "
        return usage

    async def command_not_found(self, string):
        if string.lower() == "music":
            return await self.send_cog_help(self.context.bot.cogs.get("Music"))
        if retry_after := await self.context.bot.glory_cache.ratelimited(  # noqa: F841
            f"cnf:{self.context.guild.id}", 1, 3
        ):
            raise OnCooldown()
        raise discord.ext.commands.CommandError(
            f"**No command** named **{string}** exists"
        )

    async def send_command_help(self, command):
        if retry_after := await self.context.bot.glory_cache.ratelimited(
            f"rl:user_commands{self.context.author.id}", 2, 4
        ):
            raise commands.CommandOnCooldown(None, retry_after, None)

        embed = Embed(color=0x2B2D31, timestamp=datetime.datetime.now())

        aliases: str = ", ".join(command.aliases)

        embed.set_author(
            name=self.context.author.display_name,
            icon_url=self.context.author.display_avatar.url,
        )
        ctx = self.context

        embed.set_footer(text=command.cog_name)

        if command.perms is None or len(command.perms) == 0:
            await command.can_run(ctx)
        embed.title = f"{command.qualified_name}"
        if command.brief is not None and command.brief != "":
            brief = command.brief
        else:
            brief = generate(ctx, command)
        if len(command.clean_params.keys()) > 0:
            params = "".join(f"{c}, " for c in command.clean_params.keys())
            params = params[:-2]
            embed.add_field(name="Parameters", value=params, inline=True)
        try:
            if command.perms[0].lower() != "send_messages":
                embed.add_field(
                    name="Permissions",
                    value=f"`{command.perms[0].replace('_',' ').title()}`",
                    inline=True,
                )
        except Exception:
            pass
        if command.example is not None:
            example = command.example.replace(",", self.context.prefix)
        else:
            example = self.get_example(command)
        embed.description = brief
        embed.add_field(
            name="Usage", value=generate(ctx, command, example, True), inline=False
        )
        if flags := command.parameters:
            d = []
            descriptions = []
            for flag_name, flag in flags.items():
                if (
                    flag.get("description")
                    and flag.get("description") not in descriptions
                ):
                    descriptions.append(flag.get("description"))
                    if flag["converter"] == int:
                        flag_value = "number"
                    if flag["converter"] == bool:
                        flag_value = "true/false"
                    else:
                        flag_value = "text"
                    if default := flag.get("default"):
                        if "{embed}" not in default:
                            m = f"(default: `{flag['default']}`)"
                        else:
                            m = "(default: `embed object`)"
                    else:
                        m = ""
                    if description := flag.get("description"):
                        f = f"{description} "
                    else:
                        f = ""
                    d.append(
                        f"> [**{flag_name.title()}:**](https://wock.bot) **{f}{flag_value} {m}**"
                    )
            embed.add_field(
                name="Flags", value="".join(f"{_}\n" for _ in d), inline=True
            )
        if len(command.aliases) > 0:
            aliases = "".join(f"{a}, " for a in command.aliases)
            aliases = aliases[:-2]
        else:
            aliases = "N/A"

        try:
            embed.set_footer(
                text=f"Aliases: {aliases}・Module: {command.cog_name.replace('.py','')}"
            )
        except AttributeError:
            pass
        return await ctx.send(embed=embed)
