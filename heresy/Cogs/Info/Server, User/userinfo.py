import discord
from discord.ext import commands
from discord import app_commands

class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="Get information about a user")
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        """Displays basic information about the specified user or the interaction user if no member is specified."""
        member = member or interaction.user
        embed = discord.Embed(title=f"{member}'s Info", color=discord.Color.blue())
        embed.add_field(name="ID", value=member.id, inline=False)
        embed.add_field(name="Name", value=member.name, inline=False)
        embed.add_field(name="Created At", value=member.created_at.strftime("%m/%d/%Y, %H:%M:%S"), inline=False)
        embed.set_thumbnail(url=member.avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="av", aliases= ['pfp', 'avatar'], description="Show your avatar.")
    async def avatar(self, ctx, member: discord.Member = None):
        """Displays the avatar of the specified user or yourself if no one is mentioned."""
        member = member or ctx.author
        embed = discord.Embed(title=f"{member.name}'s Avatar", color=discord.Color.blue())
        embed.set_image(url=member.avatar.url)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.command(name="banner", description="Show your banner.")
    async def banner(self, ctx, member: discord.Member = None):
        """Displays the banner of the specified user or yourself if no one is mentioned."""
        member = member or ctx.author
        user = await self.bot.fetch_user(member.id)

        if user.banner:
            embed = discord.Embed(title=f"{user.name}'s Banner", color=discord.Color.blue())
            embed.set_image(url=user.banner.url)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{member.mention} does not have a banner.")

    @commands.command(name="sav", description="Show your server avatar.")
    async def sav(self, ctx, member: discord.Member = None):
        """Displays the server avatar of the specified user or yourself if no one is mentioned."""
        member = member or ctx.author

        if member.guild_avatar:
            embed = discord.Embed(title=f"{member.name}'s Server Avatar", color=discord.Color.blue())
            embed.set_image(url=member.guild_avatar.url)
            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f"{member.mention} does not have a server avatar.")

async def setup(bot):
    await bot.add_cog(UserInfo(bot))
