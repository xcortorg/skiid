import discord
from discord.ext import commands
from datetime import datetime, timezone


class InfoCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="si", help="Show the server info.")
    async def server_info(self, ctx):
        """Shows the server information in a red embed."""
        
        if not ctx.guild.me.guild_permissions.embed_links:
            await ctx.send("I don't have permission to send embeds!")
            return

        guild = ctx.guild
        owner = guild.owner
        verification_level = guild.verification_level
        boosts = guild.premium_subscription_count
        members = guild.member_count
        bots = sum(1 for member in guild.members if member.bot)  # Count bots
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        roles = len(guild.roles) - 1  # Subtracting @everyone role
        vanity_url_code = guild.vanity_url_code  # Retrieve the vanity code
        vanity_url = f"/{vanity_url_code}" if vanity_url_code else "None"  # Format as "/vanity"
        server_description = guild.description or "No description available"
        creation_time = guild.created_at.strftime("%B %d, %Y %I:%M %p")

        now = datetime.now(timezone.utc)
        created_at = guild.created_at
        delta = now - created_at
        years = delta.days // 365
        time_since_creation = f"{years} year{'s' if years != 1 else ''} ago"

        server_icon_url = guild.icon.url if guild.icon else None

        embed = discord.Embed(
            description=f"{creation_time} ({time_since_creation})",
            color=discord.Color.red()
        )

        if server_icon_url:
            embed.set_thumbnail(url=server_icon_url)

        embed.title = f"{guild.name} \n{server_description}"

        embed.add_field(
            name="**Information**",
            value=(f"> Owner: {owner.mention}\n"
                   f"> Verification: {verification_level}\n"
                   f"> Boosts: {boosts}\n"
                   f"> Vanity: {vanity_url}"),
            inline=True
        )

        embed.add_field(
            name="**Statistics**",
            value=(f"> Members: {members}\n"
                   f"> Bots: {bots}\n"
                   f"> Text Channels: {text_channels}\n"
                   f"> Voice Channels: {voice_channels}\n"
                   f"> Categories: {categories}\n"
                   f"> Roles: {roles}"),
            inline=True
        )

        current_time = datetime.now().strftime("%I:%M %p")
        embed.set_footer(text=f"Guild ID: {guild.id} | Today at {current_time}")

        await ctx.send(embed=embed)


    @commands.command(name="mc")
    async def member_count(self, ctx):
        guild = ctx.guild
        bots = sum(1 for member in guild.members if member.bot)
        humans = guild.member_count - bots
        total = guild.member_count

        embed = discord.Embed(
            title=f"Member Count for {guild}",
            description=f"> **Humans**: {humans}\n> **Bots**: {bots}\n> **Total**: {total}",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    @commands.command(name="serverbanner")
    async def server_banner(self, ctx):
        """Shows the server banner in an embed."""
        if ctx.guild.banner:
            embed = discord.Embed(title=f"{ctx.guild.name} Server Banner", color=discord.Color.blurple())
            embed.set_image(url=ctx.guild.banner.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("This server does not have a banner set.")

    @commands.command(name="sicon")
    async def server_icon(self, ctx):
        """Shows the server icon in an embed."""
        if ctx.guild.icon:
            embed = discord.Embed(title=f"{ctx.guild.name} Server Icon", color=discord.Color.blurple())
            embed.set_image(url=ctx.guild.icon.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("This server does not have an icon set.")

    @commands.command(name="splash")
    async def server_splash(self, ctx):
        """Shows the server splash (invite banner) in an embed."""
        if ctx.guild.splash:
            embed = discord.Embed(title=f"{ctx.guild.name} Server Splash", color=discord.Color.blurple())
            embed.set_image(url=ctx.guild.splash.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("This server does not have a splash image set.")

async def setup(bot: commands.Bot):
    await bot.add_cog(InfoCog(bot))
