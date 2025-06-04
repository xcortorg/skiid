import discord
from discord.ext import commands
import json
import os

class Developers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.owners_file = "owners.json"
        if not os.path.exists(self.owners_file):
            with open(self.owners_file, "w") as f:
                json.dump([], f)

    def load_owners(self):
        with open(self.owners_file, "r") as f:
            return json.load(f)

    def save_owners(self, owners):
        with open(self.owners_file, "w") as f:
            json.dump(owners, f, indent=4)

    @commands.command(name="owners")
    async def owners(self, ctx):
        """Displays an embed of the owners of Heresy."""
        owners = self.load_owners()
        if not owners:
            await ctx.send("No owners have been registered yet.")
            return

        embed = discord.Embed(
            title="Owners of heresy",
            description="\n".join([f"<@{owner_id}> | {owner_id}" for owner_id in owners]),
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

    @commands.command(name="isdev")
    async def isdev(self, ctx, user: discord.User):
        """Logs a user as one of the developers of Heresy. Only the bot owner can run this command."""
        owner_id = 785042666475225109  # Replace with your Discord user ID

        if ctx.author.id != owner_id:
            await ctx.send("You do not have permission to run this command.")
            return

        owners = self.load_owners()
        if user.id in owners:
            await ctx.send(f"{user.mention} is already listed as a developer.")
            return

        owners.append(user.id)
        self.save_owners(owners)
        await ctx.send(f"{user.mention} has been added as a developer.")

async def setup(bot):
    await bot.add_cog(Developers(bot))
