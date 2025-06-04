import asyncio
from collections import defaultdict

import discord
from discord.ext import commands
from managers.bot import Luma
from managers.helpers import Context


class Emoji(commands.Cog):
    def __init__(self, bot: Luma):
        self.bot = bot
        self.locks = defaultdict(asyncio.Lock)

    @commands.group(invoke_without_command=True)
    async def emoji(self: "Emoji", ctx: Context):
        """
        Commands for emoji
        """
        return await ctx.send_help(ctx.command)

    @emoji.command(name="add", aliases=["steal"])
    @commands.has_guild_permissions(manage_expressions=True)
    @commands.bot_has_guild_permissions(manage_expressions=True)
    async def emoji_add(self: "Emoji", ctx: Context, *, emoji: discord.PartialEmoji):
        """
        Add an emoji to the server
        """
        emoji_added = await ctx.guild.create_custom_emoji(
            name=emoji.name,
            image=await emoji.read(),
            reason=f"Emoji added by {ctx.author}",
        )
        await ctx.confirm(f"Added {emoji_added} - **{emoji_added.name}**")

    @emoji.command(name="addmultiple", aliases=["am"])
    @commands.has_guild_permissions(manage_expressions=True)
    @commands.bot_has_guild_permissions(manage_expressions=True)
    async def emoji_am(self: "Emoji", ctx: Context, *emojis: discord.PartialEmoji):
        """
        Add multiple emojis to the server
        """
        if len(emojis) == 0:
            return await ctx.send_help(ctx.command)

        async with self.locks[ctx.channel.id]:
            emoji_list = []

            for emoji in emojis:
                emoj = await ctx.guild.create_custom_emoji(
                    name=emoji.name,
                    image=await emoji.read(),
                    reason=f"Emoji added by {ctx.author}",
                )
                emoji_list.append(f"{emoj}")

            await ctx.reply(
                embed=discord.Embed(
                    color=self.bot.color,
                    title=f"Added {len(emojis)} emojis",
                    description="".join(emoji_list),
                )
            )

    @emoji.command(name="delete")
    @commands.has_guild_permissions(manage_expressions=True)
    @commands.bot_has_guild_permissions(manage_expressions=True)
    async def emoji_delete(self: "Emoji", ctx: Context, *, emoji: discord.Emoji):
        """
        Delete an emoji from the server
        """
        await emoji.delete()
        await ctx.confirm("Emoji deleted")

    @emoji.command(name="list")
    async def emoji_list(self: "Emoji", ctx: Context):
        """
        Get a list with the emojis in the server
        """
        await ctx.paginate(
            [f"{emoji} - {emoji.name}" for emoji in ctx.guild.emojis],
            title=f"Emojis ({len(ctx.guild.emojis)})",
        )

    @emoji.command(name="search")
    async def emoji_search(self: "Emoji", ctx: Context, *, query: str):
        """
        Search for an emoji
        """
        emojis = [f"{e} - {e.name}" for e in self.bot.emojis if query in e.name]
        if not emojis:
            return await ctx.error("No emojis found")

        await ctx.paginate(emojis, title=f"Emojis for {query} ({len(emojis)})")


async def setup(bot: Luma):
    return await bot.add_cog(Emoji(bot))
