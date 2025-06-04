import discord
from discord.ext import commands

class Invites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="createinvite")
    @commands.has_permissions(create_instant_invite=True)
    async def create_invite(self, ctx):
        """Creates an invite link with a 7-day expiry and unlimited uses."""
        try:
            invite = await ctx.channel.create_invite(
                max_age=604800,
                max_uses=0
            )
            await ctx.send(f"Here is your invite link: {invite.url}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to create invites in this channel.")
        except discord.HTTPException:
            await ctx.send("There was an error creating the invite link.")

async def setup(bot):
    await bot.add_cog(Invites(bot))
