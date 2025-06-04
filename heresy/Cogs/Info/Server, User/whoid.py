import discord
from discord.ext import commands

class WhoID(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="whoid", help="Show basic information about a user not in a server by ID.")
    async def whoid(self, ctx, user_id: int = None):
        """Displays basic user information: username, avatar, and ID."""
        
        try:
            if not user_id:
                await ctx.send("Please provide a User ID, You fucking moron, it's literally called whoID for a reason")
                return

            try:
                user = await self.bot.fetch_user(user_id)
            except discord.NotFound:
                await ctx.send(f"User with ID `{user_id}` was not found.")
                return
            except discord.Forbidden:
                await ctx.send("I do not have permission to access this user.")
                return
            except discord.HTTPException:
                await ctx.send("An error occurred while fetching the user.")
                return

            created_at = user.created_at.strftime("%B %d, %Y")
            embed = discord.Embed(
                title=f"{user.name}#{user.discriminator}",
                description=f"**User ID:** `{user.id}`\n**Created At:** {created_at}",
                color=discord.Color.blue()
            )
            if user.avatar:
                embed.set_thumbnail(url=user.avatar.url)

            embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url)

            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send("**Error**: Something went wrong.")
            raise e

async def setup(bot):
    await bot.add_cog(WhoID(bot))
