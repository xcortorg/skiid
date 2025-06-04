import discord
from discord.ext import commands


class Authorization(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.is_owner()
    async def auth(self, ctx, server_id: int):
        """Authorize a server to use the bot."""
        async with self.bot.db.acquire() as connection:
            try:
                await connection.execute(
                    "INSERT INTO authorized_servers (server_id) VALUES ($1) ON CONFLICT DO NOTHING",
                    server_id,
                )
                await ctx.send(f"Server {server_id} has been authorized.")
            except Exception as e:
                await ctx.send("An error occurred while authorizing the server.")
                print(e)

    @commands.command()
    @commands.is_owner()
    async def unauth(self, ctx, server_id: int):
        """Deauthorize a server, causing the bot to leave."""
        async with self.bot.db.acquire() as connection:
            try:
                await connection.execute(
                    "DELETE FROM authorized_servers WHERE server_id = $1", server_id
                )
                await ctx.send(f"Server {server_id} has been deauthorized.")
                guild = self.bot.get_guild(server_id)
                if guild:
                    await guild.leave()
            except Exception as e:
                await ctx.send("An error occurred while deauthorizing the server.")
                print(e)


async def setup(bot) -> None:
    await bot.add_cog(Authorization(bot))
