import discord
from discord import Embed, __version__, app_commands
from discord.ext import commands
from managers.bot import Luma
from managers.helpers import Context


class Info(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot

    @commands.hybrid_command()
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def ping(self: "Info", ctx: Context):
        """
        Check the bots latency
        """
        await ctx.reply(f"ping `{round(self.bot.latency * 1000)}ms`")

    @commands.hybrid_command(aliases=["bi"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def botinfo(self: "Info", ctx: Context):
        """
        Check the bots stats
        """
        embed = Embed(
            color=self.bot.color,
            description=f"```guilds: {len(self.bot.guilds)}\nusers: {sum(g.member_count for g in self.bot.guilds):,}\nping: {round(self.bot.latency * 1000)}ms\ndpy: {__version__}\ncommands: {len(self.bot.commands)}\nlines: {self.bot.lines}```",
        ).set_footer(text=self.bot.uptime)
        await ctx.reply(embed=embed)

    @commands.hybrid_command(aliases=["up"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def uptime(self: "Info", ctx: Context):
        """
        Check the bots runtime
        """
        await ctx.reply(self.bot.uptime)

    @commands.hybrid_command(aliases=["inv"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def invite(self: "Info", ctx: Context):
        """
        Get the bot invite link
        """
        await ctx.reply(
            discord.utils.oauth_url(
                self.bot.user.id, permissions=discord.Permissions(permissions=8)
            )
        )

    @commands.hybrid_command()
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def vote(self: "Info", ctx: Context):
        """
        Vote for luma on top.gg
        """
        await ctx.reply(
            f"[Vote](<https://top.gg/bot/1263203971846242317>) for **{self.bot.user.name}**"
        )


async def setup(bot: Luma):
    return await bot.add_cog(Info(bot))
