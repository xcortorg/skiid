import discord
from discord.ext import commands

class SelfDestruct(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def selfdestruct(self, ctx):
        embed = discord.Embed(
            title="Command Deprecated",
            description="This command was deprecated as of Heresy V2 and does not function anymore. See `,help` for the current list of commands.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(SelfDestruct(bot))
