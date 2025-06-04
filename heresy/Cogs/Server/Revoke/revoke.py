import discord
from discord.ext import commands

class Revoke(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blacklisted_guilds = set()

    @commands.command(name="revoke")
    @commands.is_owner()
    async def revoke(self, ctx, guild_id: int = None):
        """
        Makes the bot leave a server.
        - If no guild ID is provided, it leaves the current server.
        - If a guild ID is provided, it leaves the specified server.
        """
        if guild_id is None:
            guild = ctx.guild
            await ctx.send(f"Leaving the current server: `{guild.name}` ({guild.id}).")
            await guild.leave()
        else:
            guild = self.bot.get_guild(guild_id)
            if guild:
                await ctx.send(f"Leaving server: `{guild.name}` ({guild.id}).")
                await guild.leave()
            else:
                await ctx.send(f"No server found with ID `{guild_id}`.")

    @commands.command(name="blacklist")
    @commands.is_owner()
    async def blacklist(self, ctx, guild_id: int):
        """
        Blacklists a server by its ID.
        If the bot is already in the server, it leaves immediately.
        """
        self.blacklisted_guilds.add(guild_id)

        guild = self.bot.get_guild(guild_id)
        if guild:
            await ctx.send(f"Guild `{guild.name}` ({guild.id}) has been blacklisted and will be left immediately.")
            await guild.leave()
        else:
            await ctx.send(f"Guild with ID `{guild_id}` has been blacklisted. The bot will leave if it is added.")

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """
        Listener to check if the bot joins a blacklisted server.
        If the server is blacklisted, the bot will leave immediately.
        """
        if guild.id in self.blacklisted_guilds:
            await guild.leave()
            print(f"Left blacklisted guild: {guild.name} ({guild.id})")

async def setup(bot):
    await bot.add_cog(Revoke(bot))
