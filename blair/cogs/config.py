import asyncio

import aiohttp
import asyncpg
import discord
from discord.ext import commands


class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_table(self):
        """Create the server_prefixes table if it doesn't exist."""
        async with self.bot.db.acquire() as connection:
            await connection.execute(
                """
                CREATE TABLE IF NOT EXISTS server_prefixes (
                    guild_id BIGINT PRIMARY KEY,
                    prefix VARCHAR(5) NOT NULL
                );
            """
            )

    @commands.command(name="say")
    async def say(self, ctx, *, message: str):
        """Send a message through the bot and delete the user's command message."""
        await asyncio.gather(ctx.send(message), ctx.message.delete())

    @commands.group(name="set", invoke_without_command=True)
    @commands.has_permissions(manage_guild=True)
    async def set_group(self, ctx):
        """Modify your server with Evelina."""
        await ctx.send_help(ctx.command.qualified_name)

    @set_group.command(name="banner")
    @commands.has_permissions(manage_guild=True)
    async def set_banner(self, ctx, url: str):
        """Change your server's banner."""
        guild = ctx.guild
        try:
            await guild.edit(banner=await self.get_image(url))
            await ctx.agree("Banner changed successfully.")
        except Exception as e:
            await ctx.deny(f"Failed to change banner: {e}")

    @set_group.command(name="icon")
    @commands.has_permissions(manage_guild=True)
    async def set_icon(self, ctx, url: str):
        """Change your server's icon."""
        guild = ctx.guild
        try:
            icon_data = await self.get_image(url)
            await guild.edit(icon=icon_data)
            await ctx.agree("Icon changed successfully.")
        except Exception as e:
            await ctx.deny(f"Failed to change icon: {e}")

    @set_group.command(name="name")
    @commands.has_permissions(manage_guild=True)
    async def set_name(self, ctx, *, name: str):
        """Change your server's name."""
        guild = ctx.guild
        try:
            await guild.edit(name=name)
            await ctx.agree(f"Server name changed to `{name}`.")
        except Exception as e:
            await ctx.deny(f"Failed to change server name: {e}")

    @set_group.command(name="splash")
    @commands.has_permissions(manage_guild=True)
    async def set_splash(self, ctx, url: str):
        """Change your server's splash."""
        guild = ctx.guild
        try:
            await guild.edit(splash=await self.get_image(url))
            await ctx.agree("Splash changed successfully.")
        except Exception as e:
            await ctx.deny(f"Failed to change splash: {e}")

    async def get_image(self, url: str) -> bytes:
        """Download an image from a URL and return it as bytes."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception("Failed to download image.")
                return await response.read()


async def setup(bot):
    await bot.add_cog(Config(bot))
