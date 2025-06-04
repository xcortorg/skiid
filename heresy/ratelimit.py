import discord
from discord.ext import commands, tasks
import asyncio

class RateLimit(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.rate_limit_triggered = False
        self.cooldown_seconds = 10
        self.cog_folder = "Cogs"  # The folder where all cogs are stored

    async def unload_and_reload_cogs(self):
        """
        Unloads all cogs in the specified folder and reloads them after a cooldown.
        """
        print("Rate limit detected. Unloading all cogs...")
        loaded_cogs = list(self.bot.extensions.keys())
        cogs_to_reload = [cog for cog in loaded_cogs if cog.startswith(self.cog_folder)]
        
        for cog in cogs_to_reload:
            try:
                await self.bot.unload_extension(cog)
                print(f"Unloaded: {cog}")
            except Exception as e:
                print(f"Error unloading {cog}: {e}")

        print(f"Waiting {self.cooldown_seconds} seconds before reloading cogs...")
        await asyncio.sleep(self.cooldown_seconds)

        print("Reloading all cogs...")
        for cog in cogs_to_reload:
            try:
                await self.bot.load_extension(cog)
                print(f"Reloaded: {cog}")
            except Exception as e:
                print(f"Error reloading {cog}: {e}")

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        """
        Listens for errors and checks for rate-limiting issues.
        """
        if "rate limited" in str(args).lower():
            if not self.rate_limit_triggered:
                self.rate_limit_triggered = True
                await self.unload_and_reload_cogs()
                self.rate_limit_triggered = False

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Handles command errors to detect rate-limiting and trigger cog reloads.
        """
        if isinstance(error, commands.CommandInvokeError):
            if "rate limited" in str(error).lower():
                if not self.rate_limit_triggered:
                    self.rate_limit_triggered = True
                    await self.unload_and_reload_cogs()
                    self.rate_limit_triggered = False

async def setup(bot):
    await bot.add_cog(RateLimit(bot))
