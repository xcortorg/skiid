import discord
from discord.ext import commands
import platform

class VersionInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(
        name="version", 
        aliases=[],
        description="Shows the version info about the bot, discord.py, and Python."
    )
    async def version_info(self, ctx):
        """Displays version information for the bot, discord.py, and Python."""
        await self.send_version_info(ctx)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listener for custom '--version' and '--v' commands."""
        if message.author.bot:
            return

        content = message.content.strip()
        ctx = await self.bot.get_context(message)

        if content == "--version":
            await self.send_version_info(ctx)
        elif content == "--v":
            await self.send_version_info(ctx)
        elif content == "--v Kybalion":
            await self.send_individual_info(ctx, "Kybalion", "v2.1.1")
        elif content == "--v python":
            await self.send_individual_info(ctx, "Python", platform.python_version())
        elif content == "--v discord.py":
            await self.send_individual_info(ctx, "discord.py", discord.__version__)
        elif content == "-version":
            await ctx.send("It's `--version`, not `-version`. Please use the correct format!")

    async def send_version_info(self, ctx):
        """Helper function to send version information."""
        bot_version = "v2.1.1"
        armory_version = "v1.0.1"
        discordpy_version = discord.__version__
        python_version = platform.python_version()

        embed = discord.Embed(title="Bot Version Information", color=0x3498db)
        embed.add_field(name="Kybalion", value=bot_version, inline=False)
        embed.add_field(name="Armory", value=armory_version, inline=False)
        embed.add_field(name="discord.py", value=discordpy_version, inline=False)
        embed.add_field(name="Python", value=python_version, inline=False)
        embed.set_footer(
            text="For more info about Kybalion, please check with @playfairs, for more info about Python or Packages, check https://pypi.org"
        )

        await ctx.send(embed=embed)

    async def send_individual_info(self, ctx, name, version):
        """Helper function to send individual version information."""
        embed = discord.Embed(
            title=f"{name}",
            description=f"**{name}** is running as `{version}`.",
            color=0x3498db
        )
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(VersionInfo(bot))
