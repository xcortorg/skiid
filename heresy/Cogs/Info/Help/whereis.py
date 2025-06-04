import discord
from discord.ext import commands

class WhereIsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="whereis")
    async def whereis(self, ctx, command_name: str):
        """
        Finds the file path of the cog where a specified command is defined.
        Usage: ,whereis <command>
        """
        command = self.bot.get_command(command_name)
        if not command:
            await ctx.send(f"❌ Command `{command_name}` not found.")
            return

        cog = command.cog
        if cog:
            cog_name = cog.__class__.__name__
            file_path = cog.__module__.replace(".", "/") + ".py"
            await ctx.send(f"Command `{command_name}` is defined in the `{cog_name}` cog located at `{file_path}`.")
        else:
            await ctx.send(f"Command `{command_name}` is not part of a cog or is defined inline.")

async def setup(bot):
    await bot.add_cog(WhereIsCog(bot))
