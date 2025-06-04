import discord
from discord.ext import commands
import json
import os

class Lore(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.lorebooks_dir = "Lorebooks"
        self.initialize_lorebooks_dir()

    def initialize_lorebooks_dir(self):
        """Ensure the 'Lorebooks' folder exists."""
        if not os.path.exists(self.lorebooks_dir):
            os.makedirs(self.lorebooks_dir)
            print("[Lore] Created 'Lorebooks' directory.")

    def get_lorebook_path(self, user_id):
        """Get the path to a user's lorebook JSON file."""
        return os.path.join(self.lorebooks_dir, f"{user_id}.json")

    def load_lorebook(self, user_id):
        """Load a user's lorebook, or return an empty list if none exists."""
        path = self.get_lorebook_path(user_id)
        if os.path.exists(path):
            with open(path, "r") as file:
                return json.load(file)
        return []

    def save_lorebook(self, user_id, lorebook):
        """Save a user's lorebook to their JSON file."""
        path = self.get_lorebook_path(user_id)
        with open(path, "w") as file:
            json.dump(lorebook, file, indent=4)

    @commands.command(name="loreadd", aliases=["addlore"])
    async def add_lore(self, ctx, user: discord.Member = None):
        """
        Adds a message to a user's lorebook. Must reply to a message.
        """
        if not ctx.message.reference:
            await ctx.reply("You need to reply to a message to add it as lore.", mention_author=False)
            return

        # Use the message author if no user is specified
        user = user or ctx.message.reference.resolved.author

        # Fetch the referenced message
        referenced_message = await ctx.channel.fetch_message(ctx.message.reference.message_id)

        # Load the current lorebook for the user
        lorebook = self.load_lorebook(user.id)

        # Add the lore entry
        lore_entry = {
            "message_id": referenced_message.id,
            "content": referenced_message.content
        }
        lorebook.append(lore_entry)
        self.save_lorebook(user.id, lorebook)

        await ctx.reply(
            f"Successfully added lore for {user.mention}:\n>>> {referenced_message.content}",
            mention_author=False
        )

    @commands.command(name="lore")
    async def show_lore(self, ctx, user: discord.Member):
        """
        Shows the lorebook for a user.
        """
        # Load the lorebook
        lorebook = self.load_lorebook(user.id)

        if lorebook:
            embed = discord.Embed(
                title=f"{user.display_name}'s Lorebook",
                color=discord.Color.blue()
            )

            # Add each lore entry to the embed
            for entry in lorebook:
                embed.add_field(
                    name=f"Entry {lorebook.index(entry) + 1}",
                    value=entry["content"],
                    inline=False
                )

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Congrats {user.mention}, you haven't been clipped yet..")

    @commands.command(name="find")
    async def find_message(self, ctx, message_id: int):
        """
        Finds a message in the server by its ID and reacts with 🤗.
        """
        for channel in ctx.guild.text_channels:
            try:
                message = await channel.fetch_message(message_id)
                await message.add_reaction("🤗")
                await ctx.send(f"Found the message! [Jump to Message]({message.jump_url})")
                return
            except discord.NotFound:
                continue
            except discord.Forbidden:
                print(f"[Lore] Missing permissions to read channel: {channel.name}")
            except discord.HTTPException as e:
                print(f"[Lore] HTTP error: {e}")

        await ctx.send(f"Message with ID `{message_id}` not found in this server.")

async def setup(bot):
    await bot.add_cog(Lore(bot))
