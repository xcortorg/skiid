import discord
from discord.ext import commands
import os

OWNER_ID = 785042666475225109

class TaskKill(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='taskkill', aliases= ['kill', 'terminate', 'taskkill/windows-terminal.exe', 'TASKKILL /IM Heresy.py /F'])
    async def taskkill(self, ctx):
        if ctx.author.id != OWNER_ID:
            await ctx.send("You are not authorized to use this command.")
            return

        try:
            os.system("TASKKILL /IM WindowsTerminal.exe /F")
            await ctx.send("Windows Terminal process has been terminated.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

async def setup(bot):
    await bot.add_cog(TaskKill(bot))
