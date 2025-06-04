import discord
from discord.ext import commands
import json
import os
from datetime import timedelta

class AntiSelfbot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.file_path = "./json/selfbots.json"

        # Ensure the "json" folder and the JSON file exist
        os.makedirs("./json", exist_ok=True)
        if not os.path.exists(self.file_path):
            with open(self.file_path, "w") as f:
                json.dump([], f)

    def load_selfbots(self):
        """Loads the selfbots.json file."""
        with open(self.file_path, "r") as f:
            return json.load(f)

    def save_selfbots(self, data):
        """Saves data to the selfbots.json file."""
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=4)

    @commands.command(name="sb")
    async def sb(self, ctx, member: discord.Member):
        """Adds or removes a user from the selfbot list."""
        selfbots = self.load_selfbots()

        if member.id in selfbots:
            selfbots.remove(member.id)
            action = "removed"
        else:
            selfbots.append(member.id)
            action = "added"

        self.save_selfbots(selfbots)
        await ctx.send(f"{member.mention} has been {action} to the ignorant little fuck list.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Monitors messages for selfbot behavior."""
        if message.author.bot:
            return

        selfbots = self.load_selfbots()

        if message.author.id in selfbots:
            if len(message.content) > 100 or message.content.startswith("http") or "```" in message.content:
                await self.handle_selfbot_behavior(message)

    async def handle_selfbot_behavior(self, message):
        """Handles detected selfbot behavior."""
        try:
            await message.author.timeout(timedelta(seconds=60), reason="Detected selfbot behavior")
            
            try:
                await message.author.send("Stop being a prick.")
            except discord.Forbidden:
                pass
            
            timeout_message = (
                f"{message.author.mention} was timed out for 60 seconds for being an ignorant little fuck"
            )
            await message.channel.send(timeout_message)

        except discord.Forbidden:
            await message.channel.send("I don't have permission to timeout this user.")

async def setup(bot):
    await bot.add_cog(AntiSelfbot(bot))
