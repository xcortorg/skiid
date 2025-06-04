import discord
from discord.ext import commands
import os

class Patch(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.version = "v2.2.0"  # Set your version dynamically if needed

    @commands.command(name="patch")
    @commands.has_permissions(manage_guild=True)
    async def patch(self, ctx):
        """Sends the patch update from the patch.txt file with role mention."""
        patch_file_path = os.path.join("Cogs", "Info", "Patch", "patch.txt")

        if not os.path.exists(patch_file_path):
            await ctx.send("No patch notes are available at the moment.")
            return

        with open(patch_file_path, "r") as file:
            patch_notes = file.read()

        role = discord.utils.get(ctx.guild.roles, name="Heresy Updates")
        if role is None:
            await ctx.send("Role not found.")
            return

        embed = discord.Embed(
            title=f"**{self.version} Patch Update**",
            description=patch_notes,
            color=0x3498db
        )
        embed.set_footer(
            text=f"Heresy is currently running {self.version} | For more info type ,help or DM @playfairs for more details about heresy."
        )

        await ctx.send(f"||{role.mention}||", embed=embed)

    @commands.command(name="hotfix")
    @commands.has_permissions(manage_guild=True)
    async def hotfix(self, ctx):
        """Sends the hotfix update from the hotfix.txt file with role mention."""
        hotfix_file_path = os.path.join("Cogs", "Info", "Patch", "hotfix.txt")
        print(f"Looking for file at: {hotfix_file_path}")

        if not os.path.exists(hotfix_file_path):
            await ctx.send("No hotfix notes are available at the moment.")
            return

        try:
            with open(hotfix_file_path, "r", encoding="utf-8") as file:
                patch_notes = file.read()
        except UnicodeDecodeError as e:
            await ctx.send(f"Failed to read the hotfix file due to encoding issues: {str(e)}")
            return

        role = discord.utils.get(ctx.guild.roles, name="Heresy Updates")
        if role is None:
            await ctx.send("Role not found.")
            return

        embed = discord.Embed(
            title=f"**{self.version} Hotfix**",
            description=patch_notes,
            color=0x3498db
        )
        embed.set_footer(
            text=f"Heresy is currently running {self.version} | For more info type ,help or DM @playfairs for more details about Heresy."
        )

        await ctx.send(f"||{role.mention}||", embed=embed)


async def setup(bot):
    await bot.add_cog(Patch(bot))
