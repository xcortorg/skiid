import discord
from discord.ext import commands
import asyncio

class DebugCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.debug_mode = False
        self.owner_ids = {785042666475225109, 608450597347262472, 1268333988376739931}

    def is_owner(self, user):
        return user.id in self.owner_ids

    async def lock_commands(self):
        for command in self.bot.commands:
            command.add_check(self.owner_only)

    async def unlock_commands(self):
        for command in self.bot.commands:
            command.remove_check(self.owner_only)

    async def owner_only(self, ctx):
        return ctx.author.id in self.owner_ids

    @commands.command(name="dev", hidden=True)
    async def enter_debug_mode(self, ctx):
        if not self.is_owner(ctx.author):
            await ctx.send("You don't have permission to use this command.")
            return
        
        await ctx.send("Entering Developer Mode will lock commands to the owner's use only. Do you want to continue? (yes/no)")

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ['yes', 'no']

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send("Developer Mode setup timed out.")
            return

        if msg.content.lower() == 'yes':
            for guild in self.bot.guilds:
                try:
                    await guild.me.edit(nick="[DEBUG MODE]")
                except discord.Forbidden:
                    await ctx.send(f"⚠️ Missing permissions to change nickname in {guild.name}")
            
            await self.lock_commands()
            self.debug_mode = True
            await ctx.send("Developer Mode Enabled in all servers.")
        else:
            await ctx.send("Developer Mode setup canceled.")

    @commands.command(name="fix")
    async def exit_debug_mode(self, ctx):
        if not self.is_owner(ctx.author):
            await ctx.send("You don't have permission to use this command.")
            return

        for guild in self.bot.guilds:
            try:
                await guild.me.edit(nick=None)
            except discord.Forbidden:
                await ctx.send(f"⚠️ Missing permissions to change nickname in {guild.name}")

        await self.unlock_commands()
        self.debug_mode = False
        await ctx.send("Developer Mode has been disabled, all commands are now available.")

    @commands.command(name="ping")
    async def ping(self, ctx):
        latency = round(self.bot.latency * 1000)
        await ctx.send(f"Latency: {latency}ms")

    @commands.command(name="reload-cog")
    async def reload_cog(self, ctx, cog: str):
        if not self.is_owner(ctx.author):
            await ctx.send("You don't have permission to use this command.")
            return

        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            await ctx.send(f"Cog '{cog}' reloaded successfully.")
        except Exception as e:
            await ctx.send(f"Failed to reload cog '{cog}': {e}")

    @commands.command(name="reload-all")
    async def reload_all(self, ctx):
        if not self.is_owner(ctx.author):
            await ctx.send("You don't have permission to use this command.")
            return

        success_count = 0
        for extension in list(self.bot.extensions):
            try:
                await self.bot.reload_extension(extension)
                success_count += 1
            except Exception as e:
                await ctx.send(f"Failed to reload cog '{extension}': {e}")
        await ctx.send(f"Reloaded {success_count} cogs successfully.")

    @commands.command(name="restart")
    async def restart_bot(self, ctx):
        if not self.is_owner(ctx.author):
            await ctx.send("You don't have permission to use this command.")
            return

        await ctx.send("Restarting bot... Reloading all cogs to apply new changes.")

        for extension in list(self.bot.extensions):
            try:
                await self.bot.reload_extension(extension)
            except Exception as e:
                await ctx.send(f"Failed to reload cog '{extension}': {e}")

        await ctx.send("Bot has been restarted with all cogs reloaded.")

    @commands.command(name="unload-cog")
    async def unload_cog(self, ctx, cog: str):
        if not self.is_owner(ctx.author):
            await ctx.send("You don't have permission to use this command.")
            return

        try:
            await self.bot.unload_extension(f"cogs.{cog}")
            await ctx.send(f"Cog '{cog}' unloaded successfully.")
        except Exception as e:
            await ctx.send(f"Failed to unload cog '{cog}': {e}")

async def setup(bot):
    await bot.add_cog(DebugCog(bot))
