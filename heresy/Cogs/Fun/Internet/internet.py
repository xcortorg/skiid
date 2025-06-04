import discord
from discord.ext import commands
import requests
import os

MERRIAM_WEBSTER_API_KEY = os.getenv("MERRIAM_WEBSTER_API_KEY") or "key"

class Internet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="urban", help="Fetches the definition of a word from Urban Dictionary.")
    async def urban(self, ctx, *, word: str):
        url = f"https://api.urbandictionary.com/v0/define?term={word}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            if data['list']:
                definition_data = data['list'][0]
                word = definition_data['word']
                definition = definition_data['definition']
                example = definition_data.get('example', 'No example available.')

                embed = discord.Embed(title=f"Urban Dictionary: {word}", color=discord.Color.blue())
                embed.add_field(name="Definition", value=definition, inline=False)
                embed.add_field(name="Example", value=example, inline=False)
                embed.set_footer(text="Provided by Urban Dictionary")

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"No definitions found for **{word}**.")
        else:
            await ctx.send("Failed to fetch data from Urban Dictionary. Please try again later.")

    @commands.command(name="define", help="Fetches the definition of a word from Merriam-Webster.")
    async def dictionary(self, ctx, *, word: str):
        if not MERRIAM_WEBSTER_API_KEY:
            await ctx.send("The API key is not set.")
            return

        api_url = f"https://www.dictionaryapi.com/api/v3/references/collegiate/json/{word}?key={MERRIAM_WEBSTER_API_KEY}"
        response = requests.get(api_url)

        if response.status_code != 200:
            await ctx.send("Sorry, I couldn't fetch the definition at the moment. Please try again later.")
            return

        data = response.json()

        if not data or isinstance(data[0], str):
            await ctx.send(f"No definition found for **{word}**.")
            return

        definition_data = data[0]
        word_definition = definition_data.get("shortdef", ["No definition available."])[0]
        part_of_speech = definition_data.get("fl", "Unknown")

        embed = discord.Embed(title=f"Definition of {word}", color=discord.Color.blue())
        embed.add_field(name="Word", value=word, inline=False)
        embed.add_field(name="Part of Speech", value=part_of_speech, inline=True)
        embed.add_field(name="Definition", value=word_definition, inline=False)

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Internet(bot))
