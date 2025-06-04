import discord
from discord.ext import commands
import aiohttp

class BotAppearance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.owner_id = 785042666475225109

    async def cog_unload(self):
        await self.session.close()

    @commands.command(name="changeav", description="Change the bot's avatar to a provided URL.")
    async def change_avatar(self, ctx, url: str):
        """Change the bot's avatar to the provided URL. Restricted to the bot owner."""
        
        if ctx.author.id != self.owner_id:
            await ctx.send("You are not authorized to use this command.", delete_after=5)
            return

        async with ctx.typing():
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        avatar_data = await response.read()
                        await self.bot.user.edit(avatar=avatar_data)
                        await ctx.send("Successfully updated the bot's avatar.", delete_after=5)
                    else:
                        await ctx.send("Failed to fetch the image from the provided URL.", delete_after=5)
            except Exception as e:
                await ctx.send(f"An error occurred: {e}", delete_after=5)

    @commands.command(name="changebanner", description="Change the bot's banner to a provided URL.")
    async def change_banner(self, ctx, url: str):
        """Change the bot's banner to the provided URL. Restricted to the bot owner."""

        if ctx.author.id != self.owner_id:
            await ctx.send("You are not authorized to use this command.", delete_after=5)
            return

        async with ctx.typing():
            try:
                async with self.session.get(url) as response:
                    if response.status == 200:
                        banner_data = await response.read()
                        await self.bot.user.edit(banner=banner_data)
                        await ctx.send("Successfully updated the bot's banner.", delete_after=5)
                    else:
                        await ctx.send("Failed to fetch the image from the provided URL.", delete_after=5)
            except Exception as e:
                await ctx.send(f"An error occurred: {e}", delete_after=5)


async def setup(bot):
    await bot.add_cog(BotAppearance(bot))
