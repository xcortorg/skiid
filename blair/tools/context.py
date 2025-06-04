import datetime

import discord
from discord.ext import commands
from discord.ext.commands import Command
from tools.config import color, emoji
from tools.paginator import Simple


class Context(commands.Context):

    async def invisible(self, message) -> discord.Message:
        embed = discord.Embed(
            description=f"> {self.author.mention}: {message}", color=color.default
        )
        return await self.send(embed=embed)

    async def agree(self, message) -> discord.Message:
        embed = discord.Embed(
            description=f"> {emoji.agree} {self.author.mention}: {message}",
            color=color.agree,
        )
        return await self.send(embed=embed)

    async def deny(self, message) -> discord.Message:
        embed = discord.Embed(
            description=f"> {emoji.deny} {self.author.mention}: {message}",
            color=color.deny,
        )
        return await self.send(embed=embed)

    async def warn(self, message) -> discord.Message:
        embed = discord.Embed(
            description=f"> {emoji.warn} {self.author.mention}: {message}",
            color=color.warn,
        )
        return await self.send(embed=embed)

    def get_command_permissions(self, command: Command):
        perms = []
        if hasattr(command, "checks"):
            for check in command.checks:
                if check.__closure__:
                    for closure in check.__closure__:
                        if isinstance(closure.cell_contents, dict):
                            permissions = closure.cell_contents.keys()
                            perms.extend(permissions)
        return ", ".join(perms) if perms else "n/a"

    async def send_help(self, command_name: str):
        command = self.bot.get_command(command_name)
        if command is None:
            embed = discord.Embed(
                description=f"{emoji.deny} {self.author.mention}: Could not **find** the command: `{command_name}`",
                color=color.deny,
            )
            return await self.send(embed=embed)

        embed = discord.Embed(
            title=f"Command: {command.name}",
            description=f"> {command.description}" if command.description else "",
            color=color.default,
        )

        if command.cog_name:
            user_pfp = (
                self.author.avatar.url
                if self.author.avatar
                else self.author.default_avatar.url
            )
            embed.set_author(name=self.author.name, icon_url=user_pfp)
            embed.set_footer(
                text=f"Category: {command.cog_name.lower()}",
                icon_url=self.bot.user.avatar.url,
            )

        aliases = ", ".join(command.aliases) if command.aliases else "n/a"
        embed.add_field(
            name=f"{emoji.channel} Aliases", value=f"```{aliases}```", inline=True
        )

        perms = self.get_command_permissions(command)
        embed.add_field(
            name=f"{emoji.warn} Permissions", value=f"```{perms}```", inline=True
        )

        def format_parameters(signature):
            parameters = signature.split()
            formatted_parameters = []
            for param in parameters:
                if param.startswith("<") and param.endswith(">"):
                    param = param[1:-1]
                if param.startswith("[") and param.endswith("]"):
                    formatted_parameters.append(f"({param[1:-1]})")
                else:
                    formatted_parameters.append(f"[{param}]")
            return " ".join(formatted_parameters)

        usage = (
            command.usage
            if command.usage
            else f"{command.name} {format_parameters(command.signature)}"
        )
        if isinstance(command, commands.Group):
            usage = f"{command.qualified_name} {format_parameters(command.signature)}"

        embed.add_field(name=f"{emoji.cmd} Usage", value=f"```{usage}```", inline=False)

        embeds = [embed]

        if isinstance(command, commands.Group):
            subcommands = list(command.walk_commands())
            for subcommand in subcommands:
                sub_usage = (
                    subcommand.usage
                    if subcommand.usage
                    else f"{command.qualified_name} {subcommand.name} {format_parameters(subcommand.signature)}"
                )
                sub_embed = discord.Embed(
                    title=f"Subcommand: {command.name} {subcommand.name}",
                    description=(
                        f"> {subcommand.description}" if subcommand.description else ""
                    ),
                    color=color.default,
                )
                sub_embed.set_author(name=self.author.name, icon_url=user_pfp)

                sub_aliases = (
                    ", ".join(subcommand.aliases) if subcommand.aliases else "n/a"
                )
                sub_embed.add_field(
                    name=f"{emoji.channel} Aliases",
                    value=f"```{sub_aliases}```",
                    inline=True,
                )

                sub_embed.add_field(
                    name=f"{emoji.warn} Permissions",
                    value=f"```{self.get_command_permissions(subcommand)}```",
                    inline=True,
                )
                sub_embed.add_field(
                    name=f"{emoji.cmd} Usage", value=f"```{sub_usage}```", inline=False
                )
                embeds.append(sub_embed)

            paginator = Simple(AllowExtInput=False)
            await paginator.start(self, embeds)
        else:
            await self.send(embed=embed)
