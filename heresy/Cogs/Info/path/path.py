import os
import shutil
import discord
from discord.ext import commands
from fuzzywuzzy import process

class PathHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.deprecated_folder = "Deprecated"
        self.authorized_user_id = 785042666475225109  # Replace with the authorized user's ID

    async def cog_check(self, ctx):
        """Restricts access to the cog's commands to a specific user."""
        if ctx.author.id != self.authorized_user_id:
            await ctx.send("You are not authorized to use this command.")
            return False
        return True

    @commands.command(name="deprecate")
    async def deprecate(self, ctx, cog_name: str):
        """Moves a cog to the 'Deprecated' folder and disables it."""
        if not os.path.exists(self.deprecated_folder):
            os.makedirs(self.deprecated_folder)

        # Find the cog file
        cog_path = None
        for root, dirs, files in os.walk("."):
            for file in files:
                if file.lower() == f"{cog_name.lower()}.py":
                    cog_path = os.path.join(root, file)
                    break
            if cog_path:
                break

        if not cog_path:
            await ctx.send(f"Cog '{cog_name}' not found.")
            return

        # Move the cog file to the 'Deprecated' folder
        dest_path = os.path.join(self.deprecated_folder, os.path.basename(cog_path))
        shutil.move(cog_path, dest_path)

        await ctx.send(f"Cog '{cog_name}' has been deprecated and moved to '{self.deprecated_folder}'.")

    @commands.command(name="path?")
    async def path_query(self, ctx, query_type: str, name: str):
        """Displays the path for a specific cog or command."""
        query_type = query_type.lower()

        if query_type == "cog":
            results = []
            for root, _, files in os.walk("."):
                for file in files:
                    if file.endswith(".py"):
                        with open(os.path.join(root, file), "r") as f:
                            content = f.read()
                            if f"class {name.capitalize()}(commands.Cog)" in content:
                                results.append(os.path.join(root, file))

            if results:
                best_match = process.extractOne(name, [os.path.basename(res) for res in results])[0]
                path = next(res for res in results if best_match in res)
                await ctx.send(f"Path for cog '{name}': `{path}`")
            else:
                await ctx.send(f"Cog '{name}' not found.")

        elif query_type == "cmd":
            command = self.bot.get_command(name)
            if command:
                cog_name = command.cog_name
                cog = self.bot.get_cog(cog_name)
                if cog:
                    cog_file = cog.__module__.replace(".", "/") + ".py"
                    await ctx.send(f"Path for command '{name}': `{cog_file}`")
                else:
                    await ctx.send(f"Command '{name}' found, but the cog file is missing.")
            else:
                await ctx.send(f"Command '{name}' not found.")

        else:
            await ctx.send("Invalid query type. Use 'cog' or 'cmd'.")

    @commands.command(name="howpath")
    async def howpath(self, ctx):
        """Explains how the bot resolves paths for cogs and commands."""
        explanation = (
            "The bot resolves paths using the following rules:\n"
            "1. **Cogs**: It searches for Python files (`.py`) in the bot directory. It looks for the class declaration pattern `class CogName(commands.Cog)` to identify the cog's name.\n"
            "2. **Commands**: It uses the `bot.get_command()` method to locate the command, retrieves its associated cog, and maps it to the corresponding cog file.\n"
            "Paths are case-insensitive and allow fuzzy matching for easier queries."
        )
        await ctx.send(explanation)

async def setup(bot):
    await bot.add_cog(PathHelp(bot))
