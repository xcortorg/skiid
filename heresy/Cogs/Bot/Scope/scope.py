import discord
from discord.ext import commands

class ScopeCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.keyword = "scope2o"

    @commands.command(name="scope")
    async def generate_invite(self, ctx, keyword: str = None):
        """
        Generates an invite link for the bot with the 'Bot' scope and 'Administrator' permissions.
        Only works if the correct keyword is provided.
        """
        if keyword != self.keyword:
            await ctx.send("Provide the correct keyword, otherwise you are not authorized to generate an invite link.")
            return

        app_info = await self.bot.application_info()
        bot_id = app_info.id

        permissions = discord.Permissions(administrator=True)
        invite_url = discord.utils.oauth_url(client_id=bot_id, permissions=permissions, scopes=["bot"])

        embed = discord.Embed(
            title="Here's the Invite Link.",
            description=f"Click the link below to invite me to your server with the required permissions.\n\n[Invite Link]({invite_url})",
            color=discord.Color.blue()
        )
        embed.set_footer(text="This invite link requires Administrator permissions.")

        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ScopeCog(bot))
