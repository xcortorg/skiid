import discord
from discord.ext import commands
from discord import app_commands

class AboutCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name='about', description="Displays information about Playfair or Heresy.")
    @app_commands.describe(option="Select either Playfair or Heresy")
    @app_commands.choices(
        option=[
            app_commands.Choice(name="Playfair", value="playfair"),
            app_commands.Choice(name="Heresy", value="Heresy"),
        ]
    )
    async def about(self, interaction: discord.Interaction, option: app_commands.Choice[str]):
        """Displays information about Playfair or Heresy in an embed."""
        option_value = option.value.lower()


        if option_value == 'playfair':
            embed = discord.Embed(
                title="About Playfair",
                description="Developer of Heresy and other Discord Bots.",
                color=discord.Color.pink()
            )
            embed.add_field(name="Developer", value="<@785042666475225109>", inline=False)
            embed.add_field(name="Description", value="Playfairs, or Playfair, is the Bot Developer of this and many other bots, also being the owner of /Heresy, that is all.", inline=False)
            embed.add_field(name="Useful Links", value="[guns.lol](https://guns.lol/playfair) | [about.me](https://about.me/creepfully)", inline=False)
            embed.set_footer(text="For more information, visit https://about.me/creepfully to learn more about the Bot Developer.")

        elif option_value == 'heresy':
            embed = discord.Embed(
                title="About Heresy",
                description="Discord Bot created and coded by <@785042666475225109>.",
                color=discord.Color.green()
            )
            embed.add_field(name="Developer", value="<@785042666475225109>", inline=False)
            embed.add_field(name="Description", value="Heresy, originally Heresy, is a all-in-one Discord Bot created by <@785042666475225109>, built for versatility", inline=False)
            embed.add_field(name="Useful Links", value="[Server](https://discord.gg/heresy) | [Website](https://playfairs.cc) | [Invite](https://discord.com/oauth2/authorize?client_id=1284037026672279635&permissions=8&integration_type=0&scope=bot)", inline=False)
            embed.set_footer(text="For more information, DM @playfairs, or check ,help for more info.")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="links", description="Displays useful links.")
    async def links(self, interaction: discord.Interaction):
        """Displays useful links in an embed."""
        embed = discord.Embed(
            title="Useful Links",
            description="Hi",
            color=discord.Color.blurple()
        )
        embed.add_field(name="Guns.lol", value="[playfair](https://guns.lol/playfair)", inline=False)
        embed.add_field(name="Wanted.lol", value="[suicideboys](https://wanted.lol/suicideboys)", inline=False)
        embed.add_field(name="About.me", value="[creepfully](https://about.me/creepfully)", inline=False)
        embed.add_field(name="TikTok", value="[playfairs](https://tiktok.com/playfairs)", inline=False)
        embed.set_footer(text="More details can be found in the about.me")

        await interaction.response.send_message(embed=embed)

    @commands.command(name="abt", hidden=True)
    async def about_bot(self, ctx):
        """Displays information about the bot."""
        embed = discord.Embed(
            title="About This Bot",
            description="Heresy is a Discord Bot packed with a whole bunch of commands, designed for versatility (NOT HOSTED 24/7)",
            color=0x3498db
        )
        embed.add_field(name="Developer", value="@playfairs", inline=False)
        embed.add_field(name="Language", value="Python", inline=True)
        embed.add_field(name="Library", value="discord.py", inline=True)
        embed.add_field(name="Purpose", value="Meant for managing and adding a bit of fun to your server(s)!", inline=False)
        embed.set_footer(text="Thanks for using Heresy, if you have any questions about the bot then hit up the developer and ask your questions!")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AboutCog(bot))
