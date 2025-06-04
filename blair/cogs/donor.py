import random

import discord
import google.generativeai as genai
from discord.ext import commands
from discord.ext.commands import hybrid_command
from tools.config import color, emoji
from tools.context import Context

api_keys = [
    "AIzaSyARqu0-ecLbA5gTpcCi8R8n8DQnM_y5SCc",
    "AIzaSyD6kJ3BEfJ9MoyiqkGQqmKwCH41rSAI7OY",
    "AIzaSyB5M5n1Y6FbzJn8ArixxWBCfwBRMkJReNw",
]

key = random.choice(api_keys)
genai.configure(api_key=key)
model = genai.GenerativeModel("gemini-pro")


class Donor(commands.Cog):
    def __init__(self, client):
        self.client = client

    @hybrid_command(aliases=["ask"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def chatgpt(self, ctx, *, prompt: str):
        if not await self.is_donor(ctx.author.id):
            await ctx.deny("You **must** be a donor to use `chatgpt`")
            return

        emb = discord.Embed(
            description=f"> {ctx.author.mention}: **__Please wait a moment.__**"
        )
        msg = await ctx.reply(embed=emb)

        response = await self.generate_response(prompt)

        if response:
            await msg.edit(embed=discord.Embed(description=response))
        else:
            await ctx.deny("Failed to generate a response. Please try again.")

    async def generate_response(self, prompt: str) -> str:
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Error generating response: {e}")
            return None

    @hybrid_command(aliases=["fnick"])
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def forcenickname(self, ctx, member: discord.Member, *, nickname: str):
        """Force a nickname for a member (donor only)."""
        if not await self.is_donor(ctx.author.id):
            await ctx.deny("You **must** be a donor to use `forcenickname`")
            return

        try:
            await member.edit(nick=nickname)
            await ctx.agree(f"Changed {member.mention}'s nickname to **{nickname}**.")
        except discord.Forbidden:
            await ctx.deny("Insufficient permission to change this user's nickname.")
        except discord.HTTPException:
            await ctx.deny("Failed to change nickname. Please try again.")

    @commands.group(name="selfprefix", invoke_without_command=True)
    async def selfprefix(self, ctx):
        """Manage your self prefix."""
        await ctx.send_help(ctx.command.qualified_name)

    @selfprefix.command(name="add")
    async def selfprefix_set(self, ctx, prefix: str):
        """Set your self prefix."""
        if not await self.is_donor(ctx.author.id):
            await ctx.deny("You **must** be a donor to set a self prefix.")
            return

        await self.client.pool.execute(
            "INSERT INTO prefixes (user_id, prefix) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET prefix = $2;",
            ctx.author.id,
            prefix,
        )
        await ctx.agree(f"Your self prefix has been set to `{prefix}`!")

    @selfprefix.command(name="remove")
    async def selfprefix_remove(self, ctx):
        """Remove your self prefix."""
        if not await self.is_donor(ctx.author.id):
            await ctx.deny("You **must** be a donor to remove your self prefix.")
            return

        await self.client.pool.execute(
            "DELETE FROM prefixes WHERE user_id = $1;", ctx.author.id
        )
        await ctx.agree("Your self prefix has been removed!")

    @selfprefix.command(name="show")
    async def selfprefix_show(self, ctx):
        """Show your current self prefix."""
        if not await self.is_donor(ctx.author.id):
            await ctx.deny("You **must** be a donor to check your self prefix.")
            return

        result = await self.client.pool.fetchrow(
            "SELECT prefix FROM prefixes WHERE user_id = $1;", ctx.author.id
        )

        if result:
            await ctx.agree(f"Your current self prefix is `{result['prefix']}`.")
        else:
            await ctx.deny("You do not have a self prefix set.")

    async def is_donor(self, user_id: int) -> bool:
        """Check if the user is a donor."""
        result = await self.client.pool.fetchrow(
            "SELECT is_donor FROM donors WHERE user_id = $1", user_id
        )
        return result is not None and result["is_donor"]

    @commands.command(name="selfpurge")
    async def selfpurge(self, ctx, amount: int):
        """Delete your own messages."""
        if not await self.is_donor(ctx.author.id):
            await ctx.deny("You **must** be a donor to use `selfpurge`.")
            return
        if amount < 1 or amount > 100:
            await ctx.deny("You can only delete between 1 and 100 messages.")
            return

        def is_author(msg):
            return msg.author == ctx.author

        deleted = await ctx.channel.purge(limit=amount, check=is_author)
        await ctx.agree(f"Deleted {len(deleted)} messages.")

    async def is_donor(self, user_id: int) -> bool:
        """Check if the user is a donor."""
        result = await self.client.pool.fetchrow(
            "SELECT is_donor FROM donors WHERE user_id = $1", user_id
        )
        return result is not None and result["is_donor"]


async def setup(bot):
    await bot.add_cog(Donor(bot))
