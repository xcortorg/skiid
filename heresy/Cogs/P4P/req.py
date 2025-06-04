import discord
from discord.ext import commands

class P4PRequest(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="req", help="Post partnership requirements.")
    async def req(self, ctx):
        embed = discord.Embed(
            title="Requirements",
            description="> Minimum Members: 250\n> No Toxic, Dox, or 764 related Servers.\n> Preferably Vanity Servers, makes invite links more readable.",
            color=discord.Color.green()
        )
        embed.set_footer(text="If you have any questions, or want to partner, DM either @playfairs or ask <@&1311736090008485938>.")
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(P4PRequest(bot))
