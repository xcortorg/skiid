from typing import List, Optional

import discord
from discord.ext import commands
from discord.ext.commands import Bot, hybrid_command
from discord.ui import Select, View
from tools.config import color, emoji
from tools.context import Context


class HelpDropdown(discord.ui.Select):
    def __init__(
        self, client, author, blacklisted, home, cog_options: List[discord.SelectOption]
    ):
        self.client = client
        self.author = author
        self.blacklisted = blacklisted
        self.home = home

        super().__init__(
            placeholder="Menu", min_values=1, max_values=1, options=cog_options
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.author:
            embed = discord.Embed(
                description=f"> {emoji.warn} {self.author.mention}: You **cannot** interact with this",
                color=color.warn,
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        selected_cog = self.values[0]
        if selected_cog == "Home":
            await interaction.response.edit_message(embed=self.home, view=self.view)
            return

        cog = self.client.get_cog(selected_cog)
        commands_list = [
            f"{command.name}*" if isinstance(command, commands.Group) else command.name
            for command in cog.get_commands()
        ]
        commands_description = "```\n" + ", ".join(commands_list) + "\n```"
        embed = discord.Embed(
            title=f"{selected_cog} commands",
            description=commands_description,
            color=color.default,
        )

        bot_avatar_url = (
            self.client.user.avatar.url
            if self.client.user.avatar
            else self.client.user.default_avatar.url
        )
        embed.set_footer(
            text=f"commands: {len(commands_list)}", icon_url=bot_avatar_url
        )
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(
        self, client, author, blacklisted, home, cog_options: List[discord.SelectOption]
    ):
        super().__init__()
        self.add_item(HelpDropdown(client, author, blacklisted, home, cog_options))


class Help(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.cog_options = self._precompute_cog_options()

    def _precompute_cog_options(self) -> List[discord.SelectOption]:
        options = [discord.SelectOption(label="Home", emoji="🏠")]
        custom_emojis = {
            "Information": "ℹ",
            "Donor": "💸",
            "Fun": "😋",
            "Economy": "💲",
            "Voicemaster": "🔊",
            "Moderation": "🔨",
            "Utility": "🔧",
        }

        for cog_name in self.client.cogs:
            if cog_name not in ["Dev", "Jishaku", "Help"]:
                cog = self.client.get_cog(cog_name)
                if cog.get_commands():
                    emoji = custom_emojis.get(cog_name)
                    options.append(discord.SelectOption(label=cog_name, emoji=emoji))

        return options

    @hybrid_command(aliases=["h"])
    @commands.has_permissions(manage_guild=True)
    async def help(self, ctx, *, command_name: Optional[str] = None):
        """Get info via blare's help menu"""
        if command_name:
            await ctx.send_help(command_name)
            return

        user_avatar_url = (
            ctx.author.avatar.url
            if ctx.author.avatar
            else ctx.author.default_avatar.url
        )
        bot_avatar_url = (
            self.client.user.avatar.url
            if self.client.user.avatar
            else self.client.user.default_avatar.url
        )

        cmds = sum(
            1
            for command in self.client.commands
            if not command.hidden and command.cog_name != "Jishaku"
        )
        cmds += sum(
            1
            for command in self.client.commands
            if isinstance(command, commands.Group)
            and not command.hidden
            and command.cog_name != "Jishaku"
            for subcommand in command.commands
            if not subcommand.hidden
        )

        embed = discord.Embed(title="Blare, the only bot you need", color=color.default)
        embed.add_field(
            name="",
            value=f"> **Created** by [Blare team](https://discord.gg/blare) \n> **Currently** having `{cmds}` commands",
            inline=True,
        )
        embed.add_field(
            name="",
            value=f"> Need **info?** Try -help [cmd] \n> **Current** version: `0.8`",
            inline=True,
        )
        embed.set_thumbnail(url=bot_avatar_url)
        embed.set_author(name=ctx.author.name, icon_url=user_avatar_url)

        view = HelpView(
            self.client, ctx.author, ["Dev", "Jishaku", "Help"], embed, self.cog_options
        )
        await ctx.send(embed=embed, view=view)


async def setup(client):
    await client.add_cog(Help(client))
