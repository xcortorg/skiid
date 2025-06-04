import discord
from discord.ext import commands

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        await ctx.send(f"{ctx.author.mention} https://playfairs.cc/commands, for support join https://discord.gg/heresy, for commands, run `,commands`")

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
