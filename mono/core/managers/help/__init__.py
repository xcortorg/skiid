from __future__ import annotations

import config
from core.managers.paginator import Paginator
from discord import Embed, Interaction, SelectOption, Status
from discord.ext.commands import (Cog, Command, Context, FlagConverter, Group,
                                  MinimalHelpCommand)
from discord.ext.commands.flags import FlagsMeta
from discord.ui import Select, View
from discord.utils import MISSING, oauth_url


class MonoHelp(MinimalHelpCommand):
    context: "Context"

    def __init__(self, **options):
        super().__init__(
            command_attrs={
                "help": "Shows help about the bot, a command, or a category of commands.",
                "aliases": ["h"],
                "example": "lastfm",
            },
            **options,
        )
        self.bot_user = None

    async def initialize_bot_user(self):
        if not self.bot_user:
            self.bot_user = self.context.bot.user

    async def create_main_help_embed(self, ctx):
        embed = Embed(
            description=f"List of commands **[`Here`]({config.Mono.website}/commands)**",
            color=config.Color.base,
        )
        embed.add_field(
            name="Information",
            value=f"> **[`Invite`]({oauth_url(ctx.bot.user.id)})** \n"
            f"> **[`Support`]({config.Mono.support})** \n"
            f"> **[`Website`]({config.Mono.website})**",
            inline=False,
        )
        embed.set_author(
            name=f"{ctx.bot.user.name}", icon_url=ctx.bot.user.display_avatar.url
        )
        embed.set_thumbnail(url=ctx.bot.user.display_avatar.url)

        def count_commands(commands):
            total = 0
            for command in commands:
                total += 1
                if isinstance(command, Group):
                    total += count_commands(command.commands)
            return total

        command_count = count_commands(ctx.bot.commands)
        embed.set_footer(text=f"{command_count:,} commands")
        return embed

    async def send_default_help_message(self, command: Command):
        await self.initialize_bot_user()
        syntax = self.format_command_syntax(command)

        embed = Embed(
            color=config.Color.base,
            title=f"Command: {command.qualified_name}",
            description="get help on a command",
        )
        embed.add_field(
            name="",
            value=f"```Ruby\nSyntax: {syntax}\nExample: {self.context.clean_prefix}{command.qualified_name} {command.example or ''}```",
            inline=False,
        )
        await self.context.reply(embed=embed)

    async def send_bot_help(self, mapping):
        await self.initialize_bot_user()
        embed = await self.create_main_help_embed(self.context)
        embed.set_thumbnail(url=self.context.bot.user.display_avatar.url)

        categories = sorted(
            [
                cog.qualified_name
                for cog in mapping.keys()
                if cog
                and cog.qualified_name
                not in ["Jishaku", "Network", "API", "Owner", "Developer", "developer"]
                and "extensions" in cog.__module__
            ]
        )

        if not categories:
            await self.context.reply("No categories available.")
            return

        view = self.create_category_select_view(mapping, categories)
        await self.context.reply(embed=embed, view=view)

    def create_category_select_view(self, mapping, categories):
        select = Select(
            placeholder="Choose An Extension...",
            options=[
                SelectOption(label=category, value=category) for category in categories
            ],
        )

        async def select_callback(interaction: Interaction):
            if interaction.user.id != self.context.author.id:
                await interaction.warn(
                    interaction, "You cannot interact with this menu."
                )
                return

            selected_category = interaction.data["values"][0]
            selected_cog = next(
                cog
                for cog in mapping.keys()
                if cog and cog.qualified_name == selected_category
            )
            commands = mapping[selected_cog]
            command_list = ", ".join(
                f"{command.name}{'*' if isinstance(command, Group) else ''}"
                for command in commands
            )

            embed = Embed(
                title=f"Extension: {selected_category}",
                description=f"**```\n{command_list}\n```**",
                color=config.Color.base,
            )
            await interaction.response.edit_message(embed=embed, view=view)

        select.callback = select_callback
        view = View(timeout=180)
        view.add_item(select)
        return view

    async def send_group_help(self, group: Group):
        await self.initialize_bot_user()
        embeds = []
        for command in group.commands:
            if "extensions" not in command.cog.__module__:
                continue
            syntax = self.format_command_syntax(command)
            permissions = self.get_command_permissions(command)

            embed = self.create_command_embed(command, permissions, syntax)
            embed.title = f"{command.qualified_name}"
            embed.set_footer(
                text=f"Aliases: {', '.join(a for a in command.aliases) if command.aliases else 'none'} • Command {len(embeds) + 1}/{len(group.commands)}  • Extension: {command.cog_name}",
                icon_url=self.context.author.display_avatar.url,
            )
            embeds.append(embed)

        if embeds:
            paginator_instance = Paginator(embeds, self.context)
            await paginator_instance.start()
        else:
            await self.context.reply("No commands available in this group.")

    async def send_command_help(self, command: Command):
        await self.initialize_bot_user()
        if command.cog is None or "extensions" not in getattr(
            command.cog, "__module__", ""
        ):
            await self.send_default_help_message(command)
            return

        syntax = self.format_command_syntax(command)
        permissions = self.get_command_permissions(command)
        embed = self.create_command_embed(command, permissions, syntax)
        await self.context.reply(embed=embed)

    async def send_error_message(self, error: str):
        if not error or not error.strip():
            return

        embed = Embed(title="Error", description=error, color=config.Color.base)
        await self.context.send(embed=embed)

    async def command_not_found(self, string: str):
        if not string:
            return

        error_message = (
            f"> {self.context.author.mention}: Command `{string}` does not exist"
        )
        embed = Embed(description=error_message, color=config.Color.warn)
        await self.context.reply(embed=embed)

    async def subcommand_not_found(self, command: str, subcommand: str):
        if not command or not subcommand:
            return

        error_message = f"> {self.context.author.mention}: Command `{command} {subcommand}` does not exist"
        embed = Embed(description=error_message, color=config.Color.warn)
        await self.context.reply(embed=embed)

    def format_command_syntax(self, command):
        try:
            return f"{self.context.clean_prefix}{command.qualified_name} {' '.join([f'<{param.name}>' if not param.optional else f'[{param.name}]' for param in command.arguments])}"
        except AttributeError:
            return f"{self.context.clean_prefix}{command.qualified_name}"

    def get_command_permissions(self, command):
        try:
            return ", ".join(
                perm.lower().replace("n/a", "None").replace("_", " ")
                for perm in command.permissions
            )
        except AttributeError:
            return ""

    def create_command_embed(self, command, permissions, syntax):
        embed = Embed(
            color=config.Color.base,
            title=f"{command.qualified_name.lower()}",
            description=f"> {command.description.capitalize() if command.description else (command.help.capitalize() if command.help else None)}",
        )
        embed.add_field(
            name="",
            value=f"```Syntax: {syntax}\nExample: {self.context.clean_prefix}{command.qualified_name} {command.example or ''}```",
            inline=False,
        )

        if permissions and permissions.lower() != "none":
            embed.add_field(
                name="Permissions",
                value=permissions,
                inline=True,
            )

        if command.brief:
            embed.add_field(
                name=(
                    "Additional Info"
                    if permissions and permissions.lower() != "none"
                    else "Permissions"
                ),
                value=command.brief,
                inline=True,
            )

        for param in command.clean_params.values():
            if isinstance(param.annotation, FlagsMeta):
                self._add_flag_formatting(param.annotation, embed)

        embed.set_footer(
            text=f"Aliases: {', '.join(command.aliases) or 'none'} • Extension: {command.cog_name}",
            icon_url=self.context.author.display_avatar.url,
        )
        return embed

    def _add_flag_formatting(self, annotation: FlagConverter, embed: Embed):
        optional = [
            f"`--{name}{' on/off' if isinstance(flag.annotation, Status) else ''}`: {flag.description}"
            for name, flag in annotation.get_flags().items()
            if flag.default is not MISSING
        ]
        required = [
            f"`--{name}{' on/off' if isinstance(flag.annotation, Status) else ''}`: {flag.description}"
            for name, flag in annotation.get_flags().items()
            if flag.default is MISSING
        ]

        if required:
            embed.add_field(
                name="Required Flags", value="\n".join(required), inline=True
            )

        if optional:
            embed.add_field(
                name="Optional Flags", value="\n".join(optional), inline=True
            )
