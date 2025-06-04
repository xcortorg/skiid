import discord
from discord.ext import commands

class Enslave(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="enslave", description="Assign the 'heresy's Victims' role to a mentioned user.")
    async def enslave(self, ctx, member: discord.Member):
        """Assigns the 'heresy's Victims' role to the mentioned user if the user has manage_roles permissions."""

        if not ctx.author.guild_permissions.manage_roles:
            embed = discord.Embed(
                description="You need the **Manage Roles** permission to use this command.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
            return

        role_name = "heresy's Victims"

        role = discord.utils.get(ctx.guild.roles, name=role_name)

        if role is None:
            try:
                role = await ctx.guild.create_role(
                    name=role_name,
                    color=discord.Color.red(),
                    reason="Created for heresy's Victims command"
                )
                embed = discord.Embed(
                    description=f"Created the role **'{role_name}'** and assigned it to {member.mention}.",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            except discord.Forbidden:
                embed = discord.Embed(
                    description="I don't have permission to create the role.",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, delete_after=5)
                return
            except discord.HTTPException as e:
                embed = discord.Embed(
                    description=f"An error occurred while creating the role: {e}",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed, delete_after=5)
                return

        try:
            await member.add_roles(role, reason="Enslaved by the bot for testing purposes")
            embed = discord.Embed(
                description=f"{member.mention} has been successfully assigned the role **'{role_name}'**!",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        except discord.Forbidden:
            embed = discord.Embed(
                description="I don't have permission to assign roles.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)
        except discord.HTTPException as e:
            embed = discord.Embed(
                description=f"An error occurred while assigning the role: {e}",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed, delete_after=5)

async def setup(bot):
    await bot.add_cog(Enslave(bot))
