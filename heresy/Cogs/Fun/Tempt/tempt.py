import discord
from discord.ext import commands

class Tempt(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="THE_EVIL_THAT_MEN_DO")
    async def the_evil_that_men_do(self, ctx):
        """
        A completely useless command that displays a specific phrase.
        """
        embed = discord.Embed(
            description=(
                "**Who the fuck said ruby done lost his touch?**\n\n"
                "[Listen on Spotify](https://open.spotify.com/track/5diz02QLFSmDur9R9M6bcD?si=2a4b70a6d4a241e3)"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="THE_EVIL_THAT_MEN_DO")
        await ctx.reply(embed=embed, mention_author=False)

async def setup(bot):
    await bot.add_cog(Tempt(bot))
