import discord
from discord.ext import commands
from discord.ext.commands import Context, Command, Group
from discord import Embed
from discord.ui import View
from urllib.parse import quote_plus as urlencode
import datetime
from fast_string_match import closest_match
from typing import List, Generator, Optional, Dict, Any, Mapping, Literal
from tool.exceptions import InvalidSubCommand
from logging import getLogger
from contextlib import asynccontextmanager
import inspect
from tuuid import tuuid
from tool.emotes import EMOJIS

logger = getLogger(__name__)
GLOBAL_COMMANDS = {}

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.3"
}

METHOD = Optional[Literal["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]]
HEADERS = Optional[Dict[str, Any]]


class OnCooldown(Exception):
    pass


def check_command(command) -> bool:
    source_lines, _ = inspect.getsourcelines(command.callback)
    for line in source_lines:
        if "if ctx.invoked_subcommand is None:" in line:
            if len(source_lines[source_lines.index(line) :]) < 3:
                return False
    return True


def find_command(bot, query):
    query = query.lower()
    if len(GLOBAL_COMMANDS) == 4000:
        _commands = [c for c in bot.walk_commands()]
        commands = {}
        for command in _commands:
            if isinstance(command, Group):
                aliases = command.aliases
                for cmd in command.walk_commands():
                    for a in aliases:
                        commands[
                            f"{cmd.qualified_name.replace(f'{command.qualified_name}', f'{a}')}"
                        ] = cmd
                    commands[cmd.qualified_name] = cmd
                if check_command(command):
                    commands[command.qualified_name] = command
            else:
                commands[command.qualified_name] = command
                for alias in command.aliases:
                    commands[alias] = command
        GLOBAL_COMMANDS.update(commands)
    if not bot.command_dict:
        bot.get_command_dict()
    if query in bot.command_dict:
        return bot.get_command(query)
    if MATCH := closest_match(query, bot.command_dict):
        return bot.get_command(MATCH)
    return None


class HelpModal(discord.ui.Modal, title="Help"):
    def __init__(self, bot, ctx):
        super().__init__()
        self.bot = bot
        self.ctx = ctx

    firstfield = discord.ui.TextInput(
        label="Required",
        placeholder="Search for a command...",
        min_length=1,
        max_length=500,
        style=discord.TextStyle.short,
    )

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.data["components"][0]["components"][0]["value"]:
            name = interaction.data["components"][0]["components"][0]["value"]
            command = find_command(self.bot, name)
            if not command:
                await interaction.message.edit(
                    embed=Embed(
                        color=0xffffff,
                        description=f"no command could be found close to `{name}`",
                    ),
                    view=BotHelpView(self.bot, self.ctx),
                )
                return await interaction.response.defer()
            embed = Embed(color=0xffffff, timestamp=datetime.datetime.now())
            embed.set_author(
                name=self.ctx.author.display_name,
                icon_url=self.ctx.author.display_avatar.url,
            )
            embed.set_image(
                url=f"https://greed.rocks/{command.qualified_name.replace(' ', '_')}.png?{tuuid()}"
            )
            await interaction.message.edit(
                view=BotHelpView(self.bot, self.ctx), embed=embed
            )
            return await interaction.response.defer()


class BotHelpView(View):
    def __init__(self, bot, ctx):
        super().__init__(timeout=None)
        self.bot = bot
        self.ctx = ctx

    @discord.ui.button(
        style=discord.ButtonStyle.grey,
        label="Search for commands...",
        emoji="<:greedsearch:1274197214603907164>",
        custom_id="search_button",
    )
    async def search(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            embed = discord.Embed(
                description=f"> psst you see this embed u freak? dont touch it..",
                color=0xffffff,
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        return await interaction.response.send_modal(HelpModal(self.bot, self.ctx))


def shorten(text: Optional[str], limit: int) -> str:
    if text is None:
        return ""
    return text[: limit - 3] + "..." if len(text) >= limit else text


class HelpInterface(View):
    def __init__(self, bot, options):
        super().__init__(timeout=None)
        self.bot = bot
        self.options = options
        self.add_item(HelpSelectMenu(self.bot, self.options))


class HelpSelectMenu(discord.ui.Select):
    def __init__(self, bot, options: dict, placeholder: Optional[str] = "options..."):
        self.bot = bot
        self._options = options
        options = [
            discord.SelectOption(
                label=_["name"],
                description=shorten(_["description"], 100),
                value=_["name"],
            )
            for k, _ in options.items()
        ]
        super().__init__(
            custom_id="Help:Select",
            placeholder="Options...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        self.values.clear()
        await interaction.response.defer()
        self.view.children[0].placeholder = value
        return await interaction.message.edit(
            embed=self._options[value]["embed"], view=self.view
        )


def generate(ctx: Context, c: Command, example: str = "", usage=False) -> str:
    params = " ".join(f"<{param}>" for param in c.clean_params.keys())
    if usage:
        ex = f"\nexample: {example}" if example else ""
        return f"syntax: {ctx.prefix}{c.qualified_name} {params}{ex}"
    return f"{'view ' if len(c.clean_params.keys()) == 0 else 'change '}the {c.name.lower()}{' for ' + c.qualified_name.lower().split(' ')[-1] + 's' if len(c.qualified_name.lower().split(' ')) > 2 else ''}"


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


class CommandSelect(discord.ui.Select):
    ctx: Context

    def __init__(self, categories):
        options = [
            discord.SelectOption(
                label=category, description=f"View commands in {category}"
            )
            for category in categories
        ]
        super().__init__(placeholder="Choose a category", options=options)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if retry_after := await self.view.bot.glory_cache.ratelimited(
            f"rl:help:{interaction.user.id}", 2, 4
        ):
            await interaction.response.send_message(
                "You're doing that too fast!", ephemeral=True
            )
            return False

        if interaction.user != self.ctx.author:
            embed = Embed(
                description=f"This is {self.ctx.author.mention}'s selection!",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        return interaction.user == self.ctx.author

    async def callback(self, interaction: discord.Interaction):
        selected_category = self.values[0]
        commands_list = self.get_commands_by_category(selected_category)
        embed = discord.Embed(
            title=f"**Commands in {selected_category}**",
            color=0xffffff,
            description=(
                f"```ansi\n\u001b[35m{', '.join(commands_list)}\u001b[0m\n```"
                if commands_list
                else "No commands available in this category."
            ),
        )
        embed.set_thumbnail(url=self.view.bot.user.display_avatar.url)
        embed.set_footer(text="Use the dropdown to switch categories.")
        await interaction.response.edit_message(embed=embed)

    def get_commands_by_category(self, category):
        return [
            command.name
            for command in self.view.bot.commands
            if command.cog_name and command.cog_name.lower() == category.lower()
        ]


class HelpView(discord.ui.View):
    def __init__(self, bot, categories, ctx):
        super().__init__()
        self.bot = bot
        self.ctx = ctx
        select = CommandSelect(categories)
        select.ctx = ctx
        self.add_item(select)


class MyHelpCommand(commands.HelpCommand):
    async def send_bot_help(self, mapping: Optional[Mapping[str, commands.Command]]):
        if retry_after := await self.context.bot.glory_cache.ratelimited(
            f"rl:help:{self.context.author.id}", 1, 5
        ):
            raise commands.CommandOnCooldown(commands.BucketType.user, retry_after, 1)

        embed = discord.Embed(
            title="Menu",
            description=f"<:settings:1356196294900846753> open the drop down to view commands in that category\n-# <:00_line:1336685727836274799> type **,help [command name]** for more help.\n-# <:00_line:1336685727836274799> **[support](https://discord.gg/greedbot)**\n-# <:line:1336409552786161724> **[website](https://greed.rocks)**",
            color=0xffffff,
        )
        embed.set_author(
            name=self.context.bot.user.name, icon_url=self.context.bot.user.avatar
        )

        categories = {
            command.cog_name
            for command in self.context.bot.walk_commands()
            if command.cog_name
            and command.cog_name not in ["Owner", "Jishaku", "errors", "webserver"]
        }
        view = HelpView(self.context.bot, sorted(categories), self.context)
        await self.context.send(embed=embed, view=view)

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
        if group.cog_name in ["Owner", "Jishaku"]:
            return
        if retry_after := await self.context.bot.glory_cache.ratelimited(
            f"rl:ghelp:{self.context.author.id}", 1, 5
        ):
            raise commands.CommandOnCooldown(commands.BucketType.user, retry_after, 1)

        embed = Embed(color=0xffffff, timestamp=datetime.datetime.now())
        ctx = self.context
        group_commands = [c for c in group.walk_commands()] + [group]
        group_commands = [c for c in group_commands if check_command(c)]
        embeds = {}

        for i, command in enumerate(group_commands, start=1):
            embed = Embed(color=0xffffff, timestamp=datetime.datetime.now())
            brief = command.brief or generate(ctx, command)
            params = ", ".join(f"{c}" for c in command.clean_params.keys()).replace(
                "_", ", "
            )
            embed.add_field(name="Parameters", value=params, inline=True)
            if command.example:
                example = command.example.replace(",", self.context.prefix)
            else:
                example = ""
            embed.description = brief
            embed.add_field(
                name="Usage",
                value=f"```ruby\n{generate(ctx, command, example, True)}\n```",
                inline=False,
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
                        flag_value = (
                            "number"
                            if flag.get("converter", None) == int
                            else (
                                "true/false"
                                if flag.get("converter", None) == bool
                                else "text"
                            )
                        )
                        m = (
                            f"(default: `{flag['default']}`)"
                            if flag.get("default")
                            else ""
                        )
                        f = (
                            f"{flag.get('description')} "
                            if flag.get("description")
                            else ""
                        )
                        d.append(
                            f" ```ruby\n{flag_name.title()}: {f}{flag_value} {m}```"
                        )
                embed.add_field(
                    name="Flags", value="".join(f"{_}\n" for _ in d), inline=True
                )
            aliases = ", ".join(f"{a}" for a in command.aliases) or "N/A"
            embed.set_footer(
                text=f"Aliases: {aliases}・Module: {command.cog_name.replace('.py','')}・{i}/{len(group_commands)}"
            )
            embed.set_author(
                name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
            )
            embeds[command.qualified_name] = {
                "embed": embed,
                "name": command.qualified_name,
                "description": command.brief,
            }

        if len(embeds) > 25:
            pages = ctx.paginate(embeds)
        else:
            await self.context.send(
                embed=Embed(
                    color=0xffffff,
                    title=f"**Need help with {group.qualified_name}?**",
                    url="https://greed.rocks/Commands",
                    description=f"<:settings:1356196294900846753> **Usage**\n> **{group.qualified_name}** has {len([i for i in group.walk_commands()])} sub commands that can be used. To view all commands for **{group.qualified_name}**, use the help menu below or visit our [**website**](https://greed.rocks/)",
                ),
                view=HelpInterface(self.context.bot, embeds),
            )

    async def send_command_help(self, command):
        if command.cog_name in ["Owner", "Jishaku"]:
            return

        if retry_after := await self.context.bot.glory_cache.ratelimited(
            f"rl:chelp:{self.context.author.id}", 1, 5
        ):
            raise commands.CommandOnCooldown(None, retry_after, None)
        embed = Embed(color=0xffffff, timestamp=datetime.datetime.now())
        aliases = ", ".join(command.aliases)
        embed.set_author(
            name=self.context.author.display_name,
            icon_url=self.context.author.display_avatar.url,
        )
        ctx = self.context
        perms = command.perms
        embed.title = f"{command.qualified_name}"
        brief = command.brief or generate(ctx, command)
        params = ", ".join(f"{c}" for c in command.clean_params.keys()).replace(
            "_", ", "
        )
        embed.add_field(name="Parameters", value=params, inline=True)
        if perms and perms[0].lower() != "send_messages":
            embed.add_field(
                name="Permissions",
                value=f"`{perms[0].replace('_',' ').title()}`",
                inline=True,
            )
        example = (
            command.example.replace(",", self.context.prefix)
            if command.example
            else self.get_example(command)
        )
        embed.description = brief
        embed.add_field(
            name="Usage",
            value=f"```ruby\n{generate(ctx, command, example, True)}\n```",
            inline=False,
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
                    flag_value = (
                        "number"
                        if flag.get("converter", None) == int
                        else (
                            "true/false"
                            if flag.get("converter", None) == bool
                            else "text"
                        )
                    )
                    m = f"(default: `{flag['default']}`)" if flag.get("default") else ""
                    f = f"{flag.get('description')} " if flag.get("description") else ""
                    d.append(f"> {flag_name.title()}: {f}{flag_value} {m}")
            embed.add_field(
                name="Flags", value="".join(f"{_}\n" for _ in d), inline=True
            )
        aliases = ", ".join(f"{a}" for a in command.aliases) or "N/A"
        cog_name = (
            command.cog_name.replace(".py", "") if command.cog_name else "No Category"
        )
        embed.set_footer(text=f"Aliases: {aliases}・Module: {cog_name}")
        await ctx.send(embed=embed)

    def get_example(self, command):
        if len(command.clean_params.keys()) == 0:
            return ""
        ex = f"{self.context.prefix}{command.qualified_name} "
        for key, value in command.clean_params.items():
            if "user" in repr(value).lower() or "member" in repr(value).lower():
                ex += "@b1o5 "
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
        if retry_after := await self.context.bot.glory_cache.ratelimited(
            f"cnf:{self.context.author.id}", 1, 5
        ):
            raise commands.CommandOnCooldown(None, retry_after, None)
        raise commands.CommandError(f"**No command** named **{string}** exists")
