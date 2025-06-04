from typing import Any, Callable, List, Mapping, Union

import discord
from discord import (Attachment, ButtonStyle, Embed, Guild, Interaction,
                     Member, Message, Role, SelectOption, StickerItem,
                     TextChannel, Thread, User, WebhookMessage, utils)
from discord.ext import commands
from discord.ext.commands import (Cog, Command, Context, Group, HelpCommand,
                                  MissingPermissions, check)
from discord.ui import Select, View

from .utils import PaginatorView


class PretendHelp(HelpCommand):
    def __init__(self, **kwargs):
        self.categories = {
            "home": "",
            "info": "",
            "automod": "",
            "antinuke": "",
            "config": "",
            "moderation": "",
            "fun": "",
            "music": "",
            "lastfm": "",
            "economy": "",
            "emoji": "",
            "roleplay": "",
            "donor": "",
            "utility": "",
        }
        super().__init__(**kwargs)

    async def send_bot_help(self, mapping):
        embed = Embed(color=self.context.bot.color)
        embed.description = "> Kindly select an option **via** the **dropdown.** For further** assistance**, join our support server [here](https://discord.gg/blonde)."
        options = []
        for c in self.categories:
            options.append(SelectOption(label=c, description=self.categories.get(c)))
        select = Select(options=options, placeholder="Select a category")

        async def select_callback(interaction: Interaction):
            if interaction.user.id != self.context.author.id:
                return await interaction.warn(
                    "This is not your message", ephemeral=True
                )
            if select.values[0] == "home":
                return await interaction.response.edit_message(embed=embed)
            selected_category = select.values[0]
            cmds = []
            for c in [
                cmd
                for cmd in set(self.context.bot.walk_commands())
                if cmd.help == select.values[0]
            ]:
                if c.parent:
                    if str(c.parent) in cmds:
                        continue
                    cmds.append(str(c.parent))
                else:
                    cmds.append(c.name)
            e = Embed(
                color=self.context.bot.color, title=f"Category: {selected_category}"
            )
            e.add_field(name="Commands", value=f"```{', '.join(cmds)}```")
            embed.set_author(
                name=self.context.bot.user.name,
                icon_url=self.context.bot.user.display_avatar.url,
            )
            return await interaction.response.edit_message(embed=e)

        select.callback = select_callback
        view = View()
        view.add_item(select)
        return await self.context.reply(embed=embed, view=view)

    async def send_command_help(self, command: Command):
        self.bot = self.context.bot
        embed = Embed(
            color=self.context.bot.color,
            title=f"Command: {command.qualified_name}",
            description=(
                command.description.capitalize() if command.description else None
            ),
        )
        embed.set_author(
            name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url
        )
        embed.add_field(name="Module", value=command.help)
        embed.add_field(
            name="Permission",
            value=f"<:warning:1305212823470866513> {command.brief if command.brief else 'any'}",
        )
        embed.add_field(
            name="Usage",
            value=f"```{self.context.clean_prefix}{command.qualified_name} {command.usage if command.usage else ''}```",
            inline=False,
        )
        if len(command.aliases) > 0:
            embed.set_footer(text=f"Aliases: {', '.join(a for a in command.aliases)}")
        await self.context.reply(embed=embed)

    async def send_group_help(self, group: Group):
        self.bot = self.context.bot
        embeds = []
        i = 0
        for command in group.commands:
            i += 1
            embeds.append(
                Embed(
                    color=self.bot.color,
                    title=f"Command: {command.qualified_name}",
                    description=(
                        command.description.capitalize()
                        if command.description
                        else None
                    ),
                )
                .set_author(
                    name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url
                )
                .add_field(
                    name="Usage",
                    value=f"```{command.qualified_name} {' '.join([f'[{a}]' for a in command.clean_params]) if command.clean_params != {} else ''}\n{command.usage or ''}```",
                    inline=False,
                )
                .set_footer(
                    text=f"Aliases: {', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'none'} ・ {i}/{len(group.commands)}"
                )
            )

        return await self.context.paginator(embeds)


class PretendInteraction(Interaction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def approve(self, message: str) -> Interaction:
        return await self.response.send_message(
            embed=Embed(
                color=self.client.yes_color,
                description=f"> {self.client.warn} {self.user.mention}: {message}",
            )
        )

    async def warn(self, message: str) -> Interaction:
        return await self.response.send_message(
            embed=Embed(
                color=self.client.warn_color,
                description=f"> {self.client.warn} {self.user.mention}: {message}",
            )
        )

    async def error(self, message: str) -> Interaction:
        return await self.response.send_message(
            embed=Embed(
                color=self.client.no_color,
                description=f"> {self.client.no} {self.user.mention}: {message}",
            )
        )


class PretendContext(commands.Context):
    def __init__(self, **kwargs):
        self.ec_emoji = "🏦"
        self.ec_color = 0xD3D3D3
        super().__init__(**kwargs)

    def find_role(self, name: str):
        for role in self.guild.roles:
            if role.name == "@everyone":
                continue
            if name.lower() in role.name.lower():
                return role
        return None

    async def reply(self, *args, **kwargs):
        return await self.send(*args, **kwargs)

    async def send_success(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=self.bot.approve,
                description=f"> {self.bot.yes} {self.author.mention}: {message}",
            )
        )

    async def send_error(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=self.bot.deny,
                description=f"> {self.bot.no} {self.author.mention}: {message}",
            )
        )

    async def send_warning(self, message: str) -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=self.bot.warn,
                description=f"> {self.bot.warning} {self.author.mention}: {message}",
            )
        )

    async def neutral(self, message: str, emoji: str = "") -> discord.Message:
        return await self.reply(
            embed=discord.Embed(
                color=self.bot.color,
                description=f"{emoji} {self.author.mention}: {message}",
            )
        )

    async def economy_send(self, message: str) -> Message:
        """economy cog sending message function"""
        embed = Embed(
            color=self.ec_color,
            description=f"{self.ec_emoji} {self.author.mention}: {message}",
        )
        return await self.send(embed=embed)

    async def paginator(self, embeds: List[discord.Embed]):
        if len(embeds) == 1:
            return await self.send(embed=embeds[0])
        view = PaginatorView(self, embeds)
        view.message = await self.reply(embed=embeds[0], view=view)

    async def cmdhelp(self):
        command = self.command
        commandname = (
            f"{str(command.parent)} {command.name}"
            if str(command.parent) != "None"
            else command.name
        )
        if command.cog_name == "owner":
            return
        embed = discord.Embed(
            color=self.bot.color,
            title=f"Command: {commandname}",
            description=f"{command.description}",
        )
        embed.set_author(name=self.bot.user.name, icon_url=self.bot.user.avatar.url)
        embed.add_field(name="Module", value=command.help)
        embed.add_field(
            name="Permission",
            value=f"<:warning:1305212823470866513> {command.brief if command.brief else 'any'}",
        )
        embed.add_field(
            name="Usage",
            value=f"```{commandname} {command.usage if command.usage else ''}```",
            inline=False,
        )
        if len(command.aliases) > 0:
            embed.set_footer(text=f"Aliases: {', '.join(a for a in command.aliases)}")
        await self.reply(embed=embed)

    async def create_pages(self):
        embeds = []
        i = 0
        for command in self.command.commands:
            commandname = (
                f"{str(command.parent)} {command.name}"
                if str(command.parent) != "None"
                else command.name
            )
            i += 1
            embeds.append(
                discord.Embed(
                    color=self.bot.color,
                    title=f"Command: {commandname}",
                    description=command.description,
                )
                .set_author(
                    name=self.bot.user.name, icon_url=self.bot.user.display_avatar.url
                )
                .add_field(
                    name="Usage",
                    value=f"```{commandname} {command.usage if command.usage else ''}```",
                    inline=False,
                )
                .set_footer(
                    text=f"Aliases: {', '.join(a for a in command.aliases) if len(command.aliases) > 0 else 'none'}・{i}/{len(self.command.commands)}"
                )
            )
        return await self.paginator(embeds)

    async def paginate(
        self,
        contents: List[str],
        title: str = None,
        author: dict = {"name": "", "icon_url": None},
    ):
        """Paginate a list of contents in multiple embeds"""
        iterator = [m for m in utils.as_chunks(contents, 10)]
        embeds = [
            Embed(
                color=self.bot.color,
                title=title,
                description="\n".join(
                    [f"`{(m.index(f)+1)+(iterator.index(m)*10)}.` {f}" for f in m]
                ),
            ).set_author(**author)
            for m in iterator
        ]
        return await self.paginator(embeds)
