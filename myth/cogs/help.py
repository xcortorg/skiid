from typing import Optional

import discord
from config import color, emoji
from discord.ext import commands
from discord.ui import Select, View
from system.base.context import Context


class HelpDropdown(discord.ui.Select):
    def __init__(self, client, author, blacklisted, home):
        self.client = client
        self.author = author
        self.blacklisted = blacklisted
        self.home = home

        options = [discord.SelectOption(label="Home", emoji=f"🏠")]
        custom_emojis = {
            "Information": f"ℹ",
            "Moderation": f"🛡",
            "Roleplay": f"👤",
            "Miscellaneous": f"🛠",
            "Config": f"⚙",
            "Skullboard": f"☠",
            "Vanityroles": f"🔗",
            "VoiceMaster": f"🔊",
            "AutoMod": f"<:automod:1301127944084652052>",
            "Fun": f"😺",
            "Network": f"🌐",
            "AntiNuke": f"<:ModShield:1302295447947444365> ",
            "LastFM": f"<:LastFM:1302294719484661873>",
        }

        for cogs in client.cogs:
            if cogs in self.blacklisted:
                continue
            cog = client.get_cog(cogs)
            commands = cog.get_commands()
            if commands:
                emoji = custom_emojis.get(cogs, None)
                options.append(discord.SelectOption(label=cogs, emoji=emoji))

        super().__init__(
            placeholder="Menu", min_values=1, max_values=1, options=options
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
            await interaction.response.edit_message(
                content="", embed=self.home, view=self.view
            )
            return

        cog = self.client.get_cog(selected_cog)
        commands_list = [
            (
                f"{command.name}*"
                if isinstance(command, commands.Group)
                else f"{command.name}"
            )
            for command in cog.get_commands()
        ]
        commands_description = "```\n" + ", ".join(commands_list) + "\n```"
        embed = discord.Embed(
            title=f"{selected_cog} commands",
            description=commands_description,
            color=color.default,
        )
        bot_pfp = (
            self.client.user.avatar.url
            if self.client.user.avatar
            else self.client.user.default_avatar.url
        )
        avatar_url = (
            self.client.user.avatar.url
            if self.client.user.avatar
            else self.client.user.default_avatar.url
        )
        user_pfp = (
            self.author.avatar.url
            if self.author.avatar
            else self.author.default_avatar.url
        )
        embed.set_author(name=f"{self.author.name} | help", icon_url=user_pfp)
        embed.set_footer(text=f"commands: {len(commands_list)}", icon_url=avatar_url)
        await interaction.response.edit_message(content="", embed=embed, view=self.view)


class HelpView(discord.ui.View):
    def __init__(self, client, author, blacklisted, home):
        super().__init__()
        self.add_item(HelpDropdown(client, author, blacklisted, home))


class Help(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.command(description="Get info on commands", aliases=["help"])
    async def h(self, ctx, *, command_name: Optional[str] = None):
        if command_name:
            await ctx.send_help(command_name)
        else:
            blacklisted = ["Developer", "Jishaku", "Help", "Events"]
            user_pfp = (
                ctx.author.avatar.url
                if ctx.author.avatar
                else ctx.author.default_avatar.url
            )
            avatar_url = (
                self.client.user.avatar.url
                if self.client.user.avatar
                else self.client.user.default_avatar.url
            )

            embed = discord.Embed(description="", color=color.default)
            embed.add_field(
                name="Need details?",
                value=f"> Use ;help (cmd) to get more details on a cmd",
            )
            embed.add_field(
                name="Acknowledge",
                value=f"> Acknowledge that the bot is **not** perfect",
            )
            embed.set_thumbnail(url=avatar_url)
            embed.set_author(name=ctx.author.name, icon_url=user_pfp)

            view = HelpView(self.client, ctx.author, blacklisted, embed)
            await ctx.send(embed=embed, view=view)


async def setup(client):
    await client.add_cog(Help(client))
