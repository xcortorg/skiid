import discord
from discord import Embed
from discord.ext import commands
from discord.ui import Select, View


class HelpSelect(Select):
    def __init__(self, bot):
        options = [
            discord.SelectOption(
                label="Settings", description="Settings commands", value="settings"
            ),
            discord.SelectOption(
                label="Utilities", description="Utility commands", value="utilities"
            ),
        ]
        super().__init__(
            placeholder="Select a category...",
            options=options,
            min_values=1,
            max_values=1,
        )
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = Embed(title=f"{category.capitalize()} Commands", color=0x729BB0)
        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.avatar
        )

        # Define commands for each category
        commands = {
            "settings": [
                (
                    "set keeprole <bool_value>",
                    "Sets the keep role option for the guild.",
                ),
                ("set vanity <vanity>", "Sets the vanity for the guild."),
                (
                    "set notifications <bool_value>",
                    "Toggles the notifications for the guild.",
                ),
                ("set vanitylock <bool_value>", "Sets the vanity lock for the guild."),
                (
                    "set channel <notif_channel>",
                    "Sets the notification channel for the guild.",
                ),
                ("set role <role>", "Sets the role to be assigned for the guild."),
            ],
            "utilities": [
                ("settings", "Displays the current settings for the guild."),
                (
                    "stats",
                    "Displays the number of people who have the vanity in their status.",
                ),
            ],
        }

        if category in commands:
            for cmd, desc in commands[category]:
                embed.add_field(name=f"**{cmd}**", value=f"```{desc}```", inline=False)

        await interaction.response.edit_message(embed=embed)


class HelpView(View):
    def __init__(self, bot):
        super().__init__()
        self.add_item(HelpSelect(bot))


class CustomHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        """
        Displays an interactive help menu.
        """
        embed = Embed(
            description="Please select a category to view commands.", color=0x729BB0
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar)
        embed.set_footer(text="Select a category from the menu below.")

        view = HelpView(self.bot)
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(CustomHelp(bot))
