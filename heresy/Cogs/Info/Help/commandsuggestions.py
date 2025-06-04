import discord
from discord.ext import commands
import difflib
import asyncio

class CommandSuggestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # Check if the error is due to a command not being found
        if isinstance(error, commands.CommandNotFound):
            # Get the closest command match
            misspelled_command = ctx.message.content.split()[0].lstrip(ctx.prefix)
            all_commands = [cmd.name for cmd in self.bot.commands]
            # Add aliases to the list of possible commands
            for cmd in self.bot.commands:
                all_commands.extend(cmd.aliases)

            # Find the closest match
            close_matches = difflib.get_close_matches(misspelled_command, all_commands, n=1, cutoff=0.6)

            if close_matches:
                suggestion = close_matches[0]
                # Send suggestion and wait for user response
                suggestion_message = await ctx.reply(
                    f"{ctx.author.mention}, command `{misspelled_command}` not found. Did you mean `{ctx.prefix}{suggestion}`? Reply with 'yes' to run this command or 'no' to cancel.",
                    mention_author=True
                )

                # Set up a message collector
                def check(msg):
                    return msg.author == ctx.author and msg.channel == ctx.channel

                try:
                    # Wait for a reply from the user within 30 seconds
                    response = await self.bot.wait_for('message', check=check, timeout=30.0)

                    # If the user replied with "yes", run the suggested command
                    if response.content.lower() == "yes":
                        await ctx.invoke(self.bot.get_command(suggestion))
                    elif response.content.lower() == "no":
                        # If the user replies with "no", reply with "Oh ok"
                        await response.reply("Oh ok")

                except asyncio.TimeoutError:
                    # If no response is received in time
                    await ctx.reply("You did not respond in time. No command was executed.")

            else:
                await ctx.reply(f"{ctx.author.mention}, command `{misspelled_command}` not found. Use `{ctx.prefix}help` to see all available commands.", mention_author=True)

async def setup(bot):
    await bot.add_cog(CommandSuggestion(bot))
