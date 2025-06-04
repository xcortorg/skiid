import discord
from discord.ext import commands
import json
import os


class IsHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.commands_json_path = os.path.join("Cogs", "Info", "Help", "commands.json")
        self.commands_data = self.load_commands_data()

    def load_commands_data(self):
        """Load and flatten the commands.json file."""
        if not os.path.exists(self.commands_json_path):
            print(f"File not found: {self.commands_json_path}")
            return set()

        try:
            with open(self.commands_json_path, "r") as f:
                data = json.load(f)

                # Flatten the structure to extract all command names
                flattened_commands = {
                    command_name
                    for category in data.get("commands", {}).values()
                    for command_name in category.keys()
                }
                return flattened_commands
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON in {self.commands_json_path}: {e}")
            return set()

    @commands.command(name="ishelp")
    async def is_help(self, ctx, command_name: str):
        """
        Check if a command has a help module in commands.json.
        """
        if command_name in self.commands_data:
            await ctx.send(f"`{command_name}` **is documented** in the help file.")
        else:
            await ctx.send(f"`{command_name}` **is not documented** in the help file.")

    @commands.command(name="notinhelp", aliases=["notdoc", "doc?"])
    async def not_in_help(self, ctx):
        """
        List all commands not present in commands.json.
        """
        # Get a list of all bot commands
        all_commands = [cmd.name for cmd in self.bot.commands]
        total_commands_count = len(all_commands)

        # Compare with the commands in the JSON file
        undocumented_commands = [
            cmd for cmd in all_commands if cmd not in self.commands_data
        ]

        if not undocumented_commands:
            await ctx.send(f"All {total_commands_count} commands are documented in the help file!")
            return

        # Sort the undocumented commands alphabetically
        undocumented_commands = sorted(undocumented_commands)

        # Calculate the total number of undocumented commands
        total_undocumented_commands = len(undocumented_commands)

        # Create an embed to display the undocumented commands
        embed = discord.Embed(
            title="Commands not Documented in Help",
            description="\n".join(f"`{cmd}`" for cmd in undocumented_commands),
            color=discord.Color.red(),
        )
        
        # Update footer with the number of undocumented commands
        embed.set_footer(text=f"{total_undocumented_commands} Commands need Documentation.")

        await ctx.send(embed=embed)

    @commands.command(name="cmdcount")
    async def cmd_count(self, ctx):
        """
        Displays command count and their documentation status in an embed.
        """
        # Get a list of all bot commands
        all_commands = [cmd.name for cmd in self.bot.commands]

        # Categorize commands into documented and undocumented
        documented_commands = [cmd for cmd in all_commands if cmd in self.commands_data]
        undocumented_commands = [cmd for cmd in all_commands if cmd not in self.commands_data]

        # Separate slash commands and prefix commands
        slash_commands = [cmd for cmd in all_commands if hasattr(self.bot.get_command(cmd), 'is_slash_command') and self.bot.get_command(cmd).is_slash_command]
        prefix_commands = [cmd for cmd in all_commands if cmd not in slash_commands]

        # Count the commands
        slash_documented_count = len([cmd for cmd in slash_commands if cmd in documented_commands])
        slash_undocumented_count = len([cmd for cmd in slash_commands if cmd in undocumented_commands])
        prefix_documented_count = len([cmd for cmd in prefix_commands if cmd in documented_commands])
        prefix_undocumented_count = len([cmd for cmd in prefix_commands if cmd in undocumented_commands])

        total_documented_count = slash_documented_count + prefix_documented_count
        total_undocumented_count = slash_undocumented_count + prefix_undocumented_count
        total_commands_count = len(all_commands)

        # Prepare the embed
        embed = discord.Embed(
            title="Command Count",
            description="Overview of the bot's commands and documentation status",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Slash Commands (This doesn't work for some reason)",
            value=f"{slash_documented_count} Documented, {slash_undocumented_count} Not Documented",
            inline=False
        )
        embed.add_field(
            name="Prefix Commands",
            value=f"{prefix_documented_count} Documented, {prefix_undocumented_count} Not Documented",
            inline=False
        )
        embed.add_field(
            name="Total Commands",
            value=f"{total_documented_count} Documented, {total_undocumented_count} Not Documented",
            inline=False
        )
        embed.add_field(
            name="Total Commands Count",
            value=f"There is a total of {total_commands_count} commands.",
            inline=False
        )

        # Send the embed
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(IsHelp(bot))
