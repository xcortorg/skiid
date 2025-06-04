import asyncio
import re

import aiohttp
import discord
from discord.ext import commands
from tools.config import color, emoji
from tools.context import Context


class Emoji(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def add_single_emoji(self, ctx, session, emoji_url, emoji_name, added_emojis):
        """Helper to fetch and add a single emoji quickly."""
        try:
            async with session.get(emoji_url) as response:
                if response.status == 200:
                    image_data = await response.read()
                    new_emoji = await ctx.guild.create_custom_emoji(
                        name=emoji_name, image=image_data
                    )
                    added_emojis.append(new_emoji)
                else:
                    await ctx.send(f"Failed to fetch emoji from {emoji_url}")
        except (discord.Forbidden, discord.HTTPException) as e:
            await ctx.send(f"Failed to add emoji: {e}")

    @commands.command(name="steal", aliases=["addemoji", "emojiadd"])
    @commands.has_permissions(manage_expressions=True)
    async def steal(self, ctx, emoji, *, name: str):
        """Steals an emoji from another server and adds it to the current server."""
        emoji_id_match = re.search(r"<(a)?:\w+:(\d+)>", emoji)
        if not emoji_id_match:
            await ctx.deny("Invalid emoji format. Please provide a custom emoji.")
            return

        is_animated = emoji_id_match.group(1) == "a"
        emoji_id = emoji_id_match.group(2)
        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if is_animated else 'png'}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(emoji_url) as response:
                    if response.status != 200:
                        await ctx.deny(
                            "Failed to fetch the emoji image. Please check the URL or emoji ID."
                        )
                        return
                    image_data = await response.read()
                    new_emoji = await ctx.guild.create_custom_emoji(
                        name=name, image=image_data
                    )
                    await ctx.agree(f"Added emoji: {new_emoji}")
            except discord.Forbidden:
                await ctx.deny("I don't have permission to add emojis in this server.")
            except discord.HTTPException as e:
                await ctx.deny(f"Failed to add emoji: {e}")

    @commands.command(name="enlarge", aliases=["download", "e", "jumbo"])
    async def enlarge(self, ctx, emoji: str):
        """Enlarges an emoji by providing the URL of its image at the highest quality available."""
        emoji_id_match = re.search(r"<(a)?:\w+:(\d+)>", emoji)
        if not emoji_id_match:
            await ctx.warn("Please provide a valid custom emoji.")
            return
        is_animated = emoji_id_match.group(1) == "a"
        emoji_id = emoji_id_match.group(2)
        emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if is_animated else 'png'}?size=4096"
        embed = discord.Embed(title="Here is the enlarged emoji!", color=color.default)
        embed.set_image(url=emoji_url)
        await ctx.send(embed=embed)

    @commands.command(name="addmulti", aliases=["multiadd"])
    @commands.has_permissions(manage_expressions=True)
    async def addmulti(self, ctx, *emojis):
        """Adds multiple emojis to the server at once."""
        if not emojis:
            await ctx.warn("Please provide emojis to add.")
            return

        added_emojis = []
        async with aiohttp.ClientSession() as session:
            tasks = []
            for emoji in emojis:
                emoji_id_match = re.search(r"<(a)?:\w+:(\d+)>", emoji)
                if emoji_id_match:
                    is_animated = emoji_id_match.group(1) == "a"
                    emoji_id = emoji_id_match.group(2)
                    emoji_url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{'gif' if is_animated else 'png'}"
                    emoji_name = f"emoji_{emoji_id}"
                    tasks.append(
                        self.add_single_emoji(
                            ctx, session, emoji_url, emoji_name, added_emojis
                        )
                    )
            await asyncio.gather(*tasks)

        if added_emojis:
            await ctx.agree(f"Added emojis: {' '.join(str(e) for e in added_emojis)}")
        else:
            await ctx.deny("No emojis were added. Check the format and try again.")


async def setup(bot):
    await bot.add_cog(Emoji(bot))
