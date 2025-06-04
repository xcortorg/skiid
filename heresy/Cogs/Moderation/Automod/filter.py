import discord
from discord.ext import commands
import random
import string
import asyncio

# Function to generate random jumbled letters
def generate_random_string(length=8):
    characters = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return ''.join(random.choice(characters) for _ in range(length))

class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="filter")
    async def filter(self, ctx, action: str, *, keyword: str = None):
        """Create an AutoMod rule called 'HVAM'."""
        if action == "add":
            try:
                # Create or update the AutoMod rule with a fixed name "HVAM"
                rule = await ctx.guild.auto_moderation_rules.create(
                    name="HVAM",  # Heresy V Automod
                    event_type=1,  # MessageSend
                    trigger_type=1,  # Keyword
                    trigger_metadata={
                        "keyword_filter": [keyword] if keyword else [generate_random_string()]  # Use provided keyword or random string
                    },
                    actions=[
                        discord.AutoModerationAction(type=1),  # BlockMessage
                    ],
                    enabled=True,
                    exempt_roles=[],
                    exempt_channels=[],
                )
                await ctx.reply(f"The AutoMod rule 'HVAM' has been created with keyword: {keyword or 'random generated keyword'}")
            except discord.HTTPException as error:
                print(f"Error updating rule: {error}")
                await ctx.reply(f"There was an error updating the AutoMod rule: `{error.response['message']}`")
            except Exception as error:
                print(f"Unexpected error: {error}")
                await ctx.reply(f"There was an unexpected error: `{error}`")

    @commands.command(name="automod")
    async def automod(self, ctx):
        """Create 5 AutoMod rules with random jumbled letters."""
        try:
            # Create 5 AutoMod rules with random jumbled letters
            for i in range(5):
                random_keyword = generate_random_string()  # Generate a random keyword

                # Create AutoModeration rule
                await ctx.guild.auto_moderation_rules.create(
                    name=f"Automod Rule {i + 1}",
                    event_type=1,  # MessageSend
                    trigger_type=1,  # Keyword
                    trigger_metadata={
                        "keyword_filter": [random_keyword],  # Use the generated random string
                    },
                    actions=[
                        discord.AutoModerationAction(type=1),  # BlockMessage
                    ],
                    enabled=True,
                    exempt_roles=[],
                    exempt_channels=[],
                )

                print(f"Automod Rule {i + 1} created with keyword: {random_keyword}")

                # Wait 3 seconds before creating the next rule to avoid rate limit
                await asyncio.sleep(3)

            await ctx.reply("5 AutoMod rules have been created with random keywords.")

        except discord.HTTPException as error:
            print(f"Error creating rules: {error}")
            await ctx.reply(f"There was an error creating the AutoMod rules: `{error.response['message']}`")
        except Exception as error:
            print(f"Unexpected error: {error}")
            await ctx.reply(f"There was an unexpected error: `{error}`")

# Setup function to add the cog to the bot
async def setup(bot):
    await bot.add_cog(AutoMod(bot))
