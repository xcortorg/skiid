import discord
from discord.ext import commands
import json
import os
import subprocess
import asyncio

with open('config.json') as config_file:
    config = json.load(config_file)

TOKEN = config['token']
PREFIX = config['prefix']

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

async def load_cogs():
    cogs_loaded = 0
    for root, dirs, files in os.walk('./Cogs'):
        for file in files:
            if file.endswith('.py'):
                cog_path = root.replace('/', '.').replace('\\', '.')[2:] + f'.{file[:-3]}'
                try:
                    await bot.load_extension(cog_path)
                    cogs_loaded += 1
                    print(f'Loaded Cog: {cog_path.split(".")[-1]}')
                except Exception as e:
                    print(f'Failed to load {cog_path}: {e}')
    print(f'{cogs_loaded} cogs loaded successfully.')
    try:
        await bot.load_extension("ratelimit")
        print("Loaded Cog: Ratelimit")
    except Exception as e:
        print(f"Failed to load ratelimit: {e}")


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print ("Heresy v2.1.0")
    await load_cogs()

    synced_commands = await bot.tree.sync()
    print(f'Synced {len(synced_commands)} commands successfully.')

    print("Bot is ready and connected.")

@bot.event
async def on_guild_join(guild):
    """Triggered when the bot joins a new guild."""
    try:
        bot_role = discord.utils.find(lambda r: r.name == "𝐡𝐞𝐫𝐞𝐬𝐲", guild.roles)

        if bot_role:
            await bot_role.edit(color=discord.Color(0x000001))
            print(f"Updated bot role color in {guild.name} (ID: {guild.id}) to #000001")
        else:
            print(f"Bot role '𝐡𝐞𝐫𝐞𝐬𝐲' not found in {guild.name} (ID: {guild.id})")

    except Exception as e:
        print(f"Failed to update bot role color in {guild.name} (ID: {guild.id}): {e}")

bot.run(TOKEN)
