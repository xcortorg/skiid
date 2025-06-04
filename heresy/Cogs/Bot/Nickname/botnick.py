import discord
from discord.ext import commands

class BotNick(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='botnick', aliases= ["rebrand"], description="Changes the bot's display name.")
    async def set_nick(self, ctx, *, new_name: str):
        """Change the bot's global display name (if possible) or server nickname."""
        authorized_user_id = 785042666475225109

        if ctx.author.id != authorized_user_id:
            await ctx.send("You don't have permission to use this command.")
            return
        
        try:
            await self.bot.user.edit(username=new_name)
            await ctx.send(embed=discord.Embed(
                title="Bot Nickname Updated",
                description=f"Successfully changed my global username to **{new_name}**.",
                color=discord.Color.green()
            ))
            return
        except discord.Forbidden:
            await ctx.send("Unable to change my global username due to permission restrictions.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred while trying to change my global username: {e}")

        try:
            await ctx.me.edit(nick=new_name)
            await ctx.send(embed=discord.Embed(
                title="Bot Nickname Updated",
                description=f"Successfully changed my server nickname to **{new_name}**.",
                color=discord.Color.green()
            ))
        except discord.Forbidden:
            await ctx.send("I don't have permission to change my nickname in this server.")
        except discord.HTTPException as e:
            await ctx.send(f"An error occurred while trying to change my server nickname: {e}")

async def setup(bot):
    await bot.add_cog(BotNick(bot))
