import discord
from discord.ext import commands

class AutoResponder(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.responses = {}

    @commands.command(name="autoresponder")
    @commands.has_permissions(administrator=True)
    async def autoresponder(self, ctx, action: str, *, args: str):
        """Main command for managing autoresponses."""
        if action.lower() == "add":
            await self.add_response(ctx, args)
        elif action.lower() == "remove":
            await self.remove_response(ctx, args)
        else:
            await self.send_help(ctx)

    async def add_response(self, ctx, args):
        """Add a new autoresponse."""
        # Split the args into keyword and response by the first comma
        if ',' in args:
            keyword, response = map(str.strip, args.split(',', 1))
            if keyword and response:
                guild_id = ctx.guild.id
                if guild_id not in self.responses:
                    self.responses[guild_id] = {}
                self.responses[guild_id][keyword.lower()] = response  # Store keyword in lowercase for case-insensitive matching
                
                embed = discord.Embed(
                    title="Autoresponse Added",
                    description=f"Keyword: `{keyword}`\nResponse: `{response}`",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
            else:
                await self.send_error(ctx, "Keyword and response cannot be empty.")
        else:
            await self.send_error(ctx, "Invalid syntax. Usage: `,autoresponder add <keyword> <response>`.")

    async def remove_response(self, ctx, args):
        """Remove an autoresponse."""
        keyword = args.strip()
        guild_id = ctx.guild.id
        
        if guild_id in self.responses and keyword in self.responses[guild_id]:
            del self.responses[guild_id][keyword]
            embed = discord.Embed(
                title="Autoresponse Removed",
                description=f"Keyword: `{keyword}` has been removed.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
        else:
            await self.send_error(ctx, f"No autoresponse found for keyword: `{keyword}`.")

    async def send_error(self, ctx, message):
        """Send an error message in an embed."""
        embed = discord.Embed(
            title="Error",
            description=message,
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)

    async def send_help(self, ctx):
        """Send help information for the autoresponder command."""
        embed = discord.Embed(
            title="Autoresponder Help",
            description="Manage autoresponses for your server.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Add Response",
            value="Usage: `,autoresponder add <keyword> <response>`",
            inline=False
        )
        embed.add_field(
            name="Remove Response",
            value="Usage: `,autoresponder remove <keyword>`",
            inline=False
        )
        embed.add_field(
            name="Permissions",
            value="Administrator",
            inline=False
        )
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages to respond with autoresponses."""
        if message.author == self.bot.user or message.guild is None:
            return

        guild_id = message.guild.id
        if guild_id in self.responses:
            for keyword, response in self.responses[guild_id].items():
                if keyword.lower() in message.content.lower():
                    await message.channel.send(response)
                    break

async def setup(bot):
    await bot.add_cog(AutoResponder(bot))
