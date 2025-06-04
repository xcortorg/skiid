import discord
from discord.ext import commands
import json

class ArmoryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Load command data from weapons.json
        with open('cogs/armory/interface/weapons.json', 'r') as f:
            self.command_data = json.load(f)

    @commands.command(name='armory', aliases=['armoryhelp', 'wpns', 'armor'], description="Shows the security-related features and command menu.")
    async def armory_command(self, ctx, command_name: str = None):
        if command_name is None:
            embed = discord.Embed(
                title="A.R.M.O.R.Y",
                description="This menu lists all security-related tools and features.\n > [] = optional, <> = required",
                color=discord.Color.gold()
            )
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            embed.add_field(name="Resources", value="[Invite](https://heresy.vercel.app) | [Discord Server](https://discord.gg/heresy)", inline=False)
            embed.set_footer(text="Select a feature category from the dropdown below.")

            # Get categories from weapons.json
            categories = self.command_data["commands"].keys()
            options = [discord.SelectOption(label=category) for category in categories]

            class Dropdown(discord.ui.Select):
                def __init__(self, outer_instance):
                    super().__init__(
                        placeholder="MY BEDROOM IT LOOKS LIKE AN ARMORY",
                        min_values=1,
                        max_values=1,
                        options=options
                    )
                    self.outer_instance = outer_instance

                async def callback(self, interaction: discord.Interaction):
                    selected = self.values[0]
                    category_embed = discord.Embed(
                        title=f"Armory: {selected} Feature",
                        description=f"Commands and details for the `{selected}` feature.",
                        color=discord.Color.gold()
                    )
                    commands_list = self.outer_instance.get_commands_for_category(selected)
                    command_count = len(commands_list)
                    commands_display = ", ".join(commands_list)
                    category_embed.add_field(name="Commands", value=f"```{commands_display}```", inline=False)
                    category_embed.set_footer(text=f"{command_count} commands for {selected}.")

                    await interaction.response.edit_message(embed=category_embed, view=view)

            view = discord.ui.View()
            view.add_item(Dropdown(self))

            await ctx.send(embed=embed, view=view)

        else:
            await self.command_help(ctx, command_name)

    def get_commands_for_category(self, category):
        """Returns a list of commands under the selected category."""
        return [
            f"{cmd}"
            for cmd, info in self.command_data["commands"].get(category, {}).items()
        ]

    async def command_help(self, ctx, command_name: str):
        """Displays detailed help for a specific command."""
        for category, commands in self.command_data["commands"].items():
            if command_name in commands:
                command_info = commands[command_name]
                embed = discord.Embed(
                    title=f"Command: {command_name.capitalize()}",
                    description=f"{command_info['description']}\n```ruby\nSyntax: {command_info['syntax']}\nExample: {command_info['example']}\n```",
                    color=discord.Color.gold()
                )
                embed.add_field(name="Permissions", value=command_info.get('permissions', 'None'))
                embed.add_field(name="Optional Flags", value=command_info.get('flags', 'None'))
                embed.add_field(name="Arguments", value=command_info.get('args', 'None'))
                embed.add_field(name="NOTE", value=command_info.get('note', 'None'))

                aliases = command_info.get('aliases', [])
                aliases_str = ', '.join(aliases) if isinstance(aliases, list) else 'None'
                embed.add_field(name="Aliases", value=aliases_str if aliases else 'None')

                await ctx.send(embed=embed)
                return

        await ctx.send(f"No information found for the command: `{command_name}`")

async def setup(bot):
    await bot.add_cog(ArmoryCog(bot))
