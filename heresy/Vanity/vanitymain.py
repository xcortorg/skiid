import discord
from discord.ext import commands
import os
import asyncio

# Initialize the bot instance
intents = discord.Intents.all()
vanity_bot = commands.Bot(command_prefix="v!", intents=intents, help_command=None)

# Event when the bot is ready
@vanity_bot.event
async def on_ready():
    print(f"Vanity bot logged in as {vanity_bot.user}")

# Function to load the cogs from the Vanity/cogs directory
async def load_vanity_cogs():
    # Correct the path to the cogs folder
    cogs_dir = os.path.join(os.path.dirname(__file__), "cogs")  # Absolute path to cogs folder
    print(f"Looking for cogs in directory: {cogs_dir}")  # Debug print to check the path
    
    if not os.path.exists(cogs_dir):
        print("The cogs directory does not exist!")
        return

    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            try:
                # Here we should just reference the file without the 'Vanity.' prefix
                await vanity_bot.load_extension(f"cogs.{filename[:-3]}")  # Load each cog
                print(f"Loaded Cog: {filename}")
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

# Define the main function
async def main():
    # Load cogs before running the bot
    await load_vanity_cogs()
    
    # Run the bot with its token
    await vanity_bot.start("MTI5NjIwNzM1NTk0MzQ1Mjc2NA.G4WbwX.SqBBKn0vCqLBXekufXFljmR8UvOTxqWnmL6XUc")  # Replace with your actual bot token

# Run the main function using asyncio.run
if __name__ == "__main__":
    asyncio.run(main())  # This is the recommended way to start async code in recent Python versions
