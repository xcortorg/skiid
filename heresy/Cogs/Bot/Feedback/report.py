import os
from discord.ext import commands
import discord

class Feedback(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.reports_dir = './Reports'
        if not os.path.exists(self.reports_dir):
            os.makedirs(self.reports_dir)

    @commands.command(name="report", help="Report an issue with the bot.")
    async def report(self, ctx, *, description: str = None):
        """Allows users to report issues with the bot."""
        if not description:
            await ctx.send("Please describe the issue you want to report.")
            return

        existing_issues = [f for f in os.listdir(self.reports_dir) if f.startswith("Issue #")]
        issue_number = len(existing_issues) + 1
        issue_file = os.path.join(self.reports_dir, f"Issue #{issue_number}.txt")

        with open(issue_file, 'w') as file:
            file.write(f"Issue #{issue_number}\n")
            file.write(f"Reported by: {ctx.author} (ID: {ctx.author.id})\n\n")
            file.write(f"Description:\n{description}")

        await ctx.send(f"Thank you for reporting! Your issue has been logged as `Issue #{issue_number}`.")

    @commands.command(name="issues", help="View all reported issues.")
    async def issues(self, ctx):
        """Lists all reported issues in an embed."""
        existing_issues = [f for f in os.listdir(self.reports_dir) if f.startswith("Issue #")]

        if not existing_issues:
            await ctx.send("No issues have been reported yet.")
            return

        embed = discord.Embed(title="Reported Issues", color=discord.Color.orange())
        for issue in existing_issues:
            embed.add_field(name=issue, value=f"`{issue}` logged in reports.", inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="patched", help="Mark an issue as patched.")
    async def patched(self, ctx, case_number: str = None):
        """Marks an issue as resolved and removes it from the reports."""
        if not await self.bot.is_owner(ctx.author):
            await ctx.send("Only the bot owner can use this command.")
            return

        if not case_number:
            await ctx.send("Please provide the case number of the issue to patch. For example: `,patched #2`.")
            return

        issue_file = os.path.join(self.reports_dir, f"Issue {case_number}.txt")
        if not os.path.exists(issue_file):
            await ctx.send(f"Issue `{case_number}` does not exist.")
            return

        os.remove(issue_file)
        await ctx.send(f"Issue `{case_number}` has been patched and removed from the reports.")

async def setup(bot):
    await bot.add_cog(Feedback(bot))
