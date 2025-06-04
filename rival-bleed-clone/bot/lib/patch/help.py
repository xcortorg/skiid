import discord
import asyncio
from discord.ext import commands
from discord.ext.commands import Command, Group, CommandOnCooldown
from discord import Embed
from .context import Context
from discord.ui import View
from urllib.parse import quote_plus as urlencode
import datetime
from typing import List, Generator, Optional
from ..classes.exceptions import InvalidSubCommand
from var.config import CONFIG

class OnCooldown(Exception):
    pass


def shorten(text: str, limit: int) -> str:
    try:
        if len(text) >= limit:
            return text[: limit - 3] + "..."
        else:
            return text
    except Exception:
        return text
    

def map_check(check):
    if "is_booster" in check.__qualname__:
        return "`Guild Booster`"
    elif "trusted" in check.__qualname__:
        return "`Server Owner`"
    elif "guild_owner" in check.__qualname__:
        return "`Server Owner`"
    elif "is_donator" in check.__qualname__:
        return "`Donator`"
    elif "is_staff" in check.__qualname__:
        return "`Staff`"
    else:
        return None

def human_join(items: list, separator: Optional[str] = ", ", markdown: Optional[str] = "", replacements: Optional[dict] = None, start_content: Optional[str] = "", titled: Optional[bool] = False) -> str:
    if len(items) == 0:
        return ""
    if replacements:
        for key, value in replacements.items():
            items = [i.replace(key, value) for i in items]
    return f'{start_content}{separator.join(f"{markdown}{item.title() if titled else item}{markdown}" for item in items)}'


def generate(ctx: Context, c: Command, example: str = "", usage=False) -> str:
    params = None
    try:
        if len(c.clean_params.keys()) == 1:
            if "_" in list(c.clean_params.keys())[0]:
                params = " ".join(
                    f"({p})" for p in list(c.clean_params.keys())[0].split("_")
                )
    except Exception:
        pass
    if not params:
        params = " ".join(f"({param})" for param in c.clean_params.keys())
    if usage is True:
        if example != "":
            ex = f"\nExample: {example}```"
        else:
            ex = "```"
        return f"\n```Syntax: {ctx.prefix}{c.qualified_name} {params} {ex}"
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


class Help(commands.HelpCommand):
    async def send_bot_help(self, mapping):
        if retry_after := await self.context.bot.object_cache.ratelimited(
            f"rl:user_commands{self.context.author.id}", 2, 4
        ):
            raise CommandOnCooldown(None, retry_after, None)
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
            description=f"⚙️ {self.context.author.mention}: For help, visit our [website]({CONFIG['domain']}?prefix={urlencode(str(self.context.prefix))}) to view {total_commands} commands",
            color=0x6e879c,
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
        if retry_after := await self.context.bot.object_cache.ratelimited(
            f"rl:user_commands{self.context.author.id}", 2, 4
        ):
            raise CommandOnCooldown(None, retry_after, None)
    
        embed: Embed = Embed(color=0x6e879c, timestamp=datetime.datetime.now())
        ctx = self.context
        commands: List = []
        embeds = []
        commands_ = [c for c in group.walk_commands()]
#        commands = commands[::-1]
        commands_.insert(0, group)
    
        for i, command in enumerate(commands_, start=1):
            if not command.perms:
                try:
                    await command.can_run(ctx)
                except Exception:
                    pass
            perms = command.perms or ["send_messages"]  # Default to send_messages if no perms
    
            if command.cog_name.lower() == "premium":
                if command.perms:
                    perms = command.perms
                    perms.append("Donator")
                else:
                    perms = ["Donator"]
            if command.perms is None or len(command.perms) == 0:
                try:
                    await command.can_run(ctx)
                except Exception:
                    pass
    
            embed = Embed(color=0x6e879c, timestamp=datetime.datetime.now())
            embed.title = f"{'Group Command: ' if isinstance(command, Group) else 'Command: '}{command.qualified_name}"
    
            # Description
            description = command.description or command.help
            # Description
            description = description if description else generate(ctx, command)
            embed.description = description
    
            # Aliases (before Parameters)
            if len(command.aliases) > 0:
                aliases = ", ".join(command.aliases)
            else:
                aliases = "none"
            embed.add_field(name="Aliases", value=aliases, inline=True)
    
            # Parameters
            if len(command.clean_params.keys()) > 0:
                params = ", ".join(command.clean_params.keys()).replace("_", ", ")
                embed.add_field(name="Parameters", value=params, inline=True)
            else:
                embed.add_field(name="Parameters", value="none", inline=True)
            _checks = set([map_check(c) for c in command.checks if map_check(c)])
            checks = []
            for check in _checks:
                if check not in checks:
                    checks.append(check)
            information_text = "".join(f"\n{CONFIG['emojis']['warning']} {c}" for c in checks)
            # Permissions
            permissions_text = human_join([c for c in command.perms if c != "send_messages"], ", ", "`", {"_": " "}, "<:warning:1286583936113311755> ", True)
            embed.add_field(
                name="Information",
                value=f"{permissions_text}" + information_text,
                inline=True,
            )
    
            # Usage
            example = command.example.replace(",", self.context.prefix) if command.example else ""
            embed.add_field(
                name="Usage", value=generate(ctx, command, example, True), inline=False
            )
            cog_name = command.extras.get("cog_name", command.cog_name) 
            #footer
            embed.set_footer(
                text=f"Module: {cog_name.replace('.py','')}・Command - {i}/{len(commands_)}"
            )
            #author
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
    
            embeds.append(embed)
    
        return await self.context.paginate(embeds, commands)


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
        if retry_after := await self.context.bot.object_cache.ratelimited(  # noqa: F841
            f"cnf:{self.context.guild.id}", 1, 3
        ):
            raise OnCooldown()
        raise discord.ext.commands.CommandError(
            f"**No command** named **{string}** exists"
        )


    
    async def send_command_help(self, command):
        if retry_after := await self.context.bot.object_cache.ratelimited(
            f"rl:user_commands{self.context.author.id}", 2, 4
        ):
            raise commands.CommandOnCooldown(None, retry_after, None)
    
        embed = Embed(color=0x6e879c, timestamp=datetime.datetime.now())
        if command.qualified_name == "help":
            embed.title = "Command: help"
            embed.description = "View extended help for commands"
            embed.add_field(name = "Aliases", value = "commands, h", inline = True)
            embed.add_field(name = "Parameters", value = "command", inline = True)
            embed.add_field(name = "Information", value = "n/a", inline = True)
            embed.add_field(name = "Usage", value = "```No syntax has been set for this command```", inline = False)
            embed.set_author(name = self.context.author.display_name, icon_url = self.context.author.display_avatar.url)
            embed.set_footer(text = "Page 1/1 (1 entry) ∙ Module: misc")
            return await self.context.send(embed = embed)
        # Set the author to the command requester
        embed.set_author(
            name=self.context.author.display_name,
            icon_url=self.context.author.display_avatar.url,
        )
    
        ctx = self.context
        perms = command.perms or ["send_messages"]  # Default to send_messages if no perms
    
        if command.cog_name.lower() == "premium":
            if command.perms:
                perms = command.perms
                perms.append("Donator")
            else:
                perms = ["Donator"]
    
        # Command Title
        embed.title = f"{'Group Command: ' if isinstance(command, Group) else 'Command: '}{command.qualified_name}"
        description = command.description or command.help
        # Description
        description = description if description else generate(ctx, command)
        embed.description = description
    
        # Aliases (before Parameters)
        if len(command.aliases) > 0:
            aliases = ", ".join(command.aliases)
        else:
            aliases = "none"
        embed.add_field(name="Aliases", value=aliases, inline=True)
    
        # Parameters
        if len(command.clean_params.keys()) > 0:
            params = "".join(f"{c}, " for c in command.clean_params.keys()).strip(", ")
            params = params.replace("_", ", ")
            embed.add_field(name="Parameters", value=params, inline=True)
        else:
            embed.add_field(name="Parameters", value="none", inline=True)
    
        _checks = set([map_check(c) for c in command.checks if map_check(c)])
        checks = []
        for check in _checks:
            if check not in checks:
                checks.append(check)
        information_text = "".join(f"\n{CONFIG['emojis']['warning']} {c}" for c in checks)
        # Permissions
        permissions_text = human_join([c for c in command.perms if c != "send_messages"], ", ", "`", {"_": " "}, "<:warning:1286583936113311755> ", True)
        embed.add_field(
            name="Information",
            value=f"{permissions_text}" + information_text,
            inline=True,
        )
    
        # Usage
        example = command.example.replace(",", self.context.prefix) if command.example else self.get_example(command)
        embed.add_field(
            name="Usage", value=generate(ctx, command, example, True), inline=False
        )
        cog_name = command.extras.get("cog_name", command.cog_name) 
        # Set footer with module info
        try:
            embed.set_footer(text=f"Module: {cog_name.replace('.py','')}")
        except AttributeError:
            pass
    
        return await ctx.send(embed=embed)

































