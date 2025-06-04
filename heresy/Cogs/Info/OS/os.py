import platform
from discord.ext import commands

class Where(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="os?")
    async def os_command(self, ctx):
        """Tells the user which operating system the bot is running on."""
        os_name = platform.system()
        await ctx.send(f"The bot is running on **{os_name}**.")

async def setup(bot):
    await bot.add_cog(Where(bot))