import discord
from discord.ext import commands
import aiohttp
import os

class MirrorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.mirrored_user = None
        self.default_avatar_path = "C:\\Users\\fnafl\\Downloads\\Kybalion v2\\Assets\\Static\\Kybalionav.gif"
        self.default_banner_path = "C:\\Users\\fnafl\\Downloads\\Kybalion v2\\Assets\\Static\\Kybalionbanner.gif"

    @commands.command(name='mirror')
    async def mirror_user(self, ctx, user: discord.Member):
        self.mirrored_user = user

        try:
            await ctx.guild.me.edit(nick=user.display_name)
        except discord.Forbidden:
            await ctx.send("I don't have permission to change my nickname in this server.")
            return

        async with aiohttp.ClientSession() as session:
            async with session.get(str(user.display_avatar.url)) as response:
                if response.status == 200:
                    avatar_bytes = await response.read()
                    await self.bot.user.edit(avatar=avatar_bytes)
                    await ctx.send(f"Now mirroring {user.mention} and updated the bot's display name and avatar to match theirs!")
                else:
                    await ctx.send(f"Failed to fetch {user.name}'s avatar. Starting mirroring without avatar change.")

    @commands.Cog.listener()
    async def on_message(self, message):
        if self.mirrored_user and message.author == self.mirrored_user and not message.author.bot:
            if message.author == self.bot.user:
                return
            await message.channel.send(message.content)

    @commands.command(name='stopmirror')
    async def stop_mirror(self, ctx):
        if self.mirrored_user:
            await ctx.send(f"Stopped mirroring {self.mirrored_user.mention}.")
            self.mirrored_user = None

            try:
                await ctx.guild.me.edit(nick=None)
            except discord.Forbidden:
                await ctx.send("I don't have permission to change my nickname in this server.")

            # Reset the bot's avatar from a local file
            try:
                with open(self.default_avatar_path, 'rb') as avatar_file:
                    avatar_bytes = avatar_file.read()
                    await self.bot.user.edit(avatar=avatar_bytes)
                    await ctx.send("Bot's avatar has been reset to the default image.")
            except Exception as e:
                await ctx.send(f"Failed to reset bot's avatar: {e}")
            
            # Reset the bot's banner from a local file
            try:
                with open(self.default_banner_path, 'rb') as banner_file:
                    banner_bytes = banner_file.read()
                    await self.bot.user.edit(banner=banner_bytes)
                    await ctx.send("Bot's banner has been reset to the default image.")
            except Exception as e:
                await ctx.send(f"Failed to reset bot's banner: {e}")
        else:
            await ctx.send("No user is currently being mirrored.")

async def setup(bot):
    await bot.add_cog(MirrorCog(bot))
