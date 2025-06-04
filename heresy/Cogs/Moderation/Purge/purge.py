import discord
from discord.ext import commands, tasks
import asyncio
from collections import deque

class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sniped_messages = {}
        self.edited_messages = {}
        self.snipe_reset.start()
        self.sniped_reactions = {}
        self.users_triggered_bot = set()

    @commands.group(name="purge", invoke_without_command=True)
    @commands.has_permissions(manage_messages=True)
    async def purge(self, ctx, amount: int = None):
        """Purges a specified number of messages from the channel (1-1000), or filters by user or message ID."""
        if amount and 1 <= amount <= 1000:
            # If a number is provided, purge the last `amount` messages (including bot's messages)
            deleted = await ctx.channel.purge(limit=amount)
            await ctx.send(f"Deleted {len(deleted)} messages.", delete_after=5)
        else:
            await ctx.send("Please specify a valid subcommand: `from`, `before`, or `after`.", delete_after=5)

    @purge.command(name="from")
    @commands.has_permissions(manage_messages=True)
    async def purge_from(self, ctx, user: discord.User):
        """Purges the last 50 messages from a mentioned user."""
        # Fetch the last 50 messages from the channel
        messages = [message async for message in ctx.channel.history(limit=50)]
        user_messages = [message for message in messages if message.author == user]

        if user_messages:
            await ctx.channel.delete_messages(user_messages)
            await ctx.send(f"Deleted {len(user_messages)} messages", delete_after=5)
        else:
            await ctx.send(f"No messages found from {user.mention}.", delete_after=5)

    @purge.command(name="before")
    @commands.has_permissions(manage_messages=True)
    async def purge_before(self, ctx, message_id: int):
        """Purges messages before a specified message ID."""
        # Fetch the message by ID and purge before it
        message = await ctx.channel.fetch_message(message_id)
        deleted = await ctx.channel.purge(limit=1000, before=message, oldest_first=True)
        await ctx.send(f"Deleted {len(deleted)} messages", delete_after=5)

    @purge.command(name="after")
    @commands.has_permissions(manage_messages=True)
    async def purge_after(self, ctx, message_id: int):
        """Purges messages after a specified message ID."""
        # Fetch the message by ID and purge after it
        message = await ctx.channel.fetch_message(message_id)
        deleted = await ctx.channel.purge(limit=1000, after=message, oldest_first=True)
        await ctx.send(f"Deleted {len(deleted)} messages", delete_after=5)

    @commands.command(name="bc", aliases=['cleanup'], help="Clears recent bot messages and user-triggered bot replies.")
    @commands.has_permissions(manage_messages=True)
    async def bc(self, ctx):
        """Purges the last 50 bot messages and messages that triggered the bot."""
        try:
            # Fetch the last 50 messages from the channel
            messages = [message async for message in ctx.channel.history(limit=50)]

            # Filter messages that should be deleted
            messages_to_delete = []
            for message in messages:
                # Check if the message is from the bot or triggered by the bot
                if message.author == ctx.bot.user or message.author.id in self.users_triggered_bot:
                    messages_to_delete.append(message)

            if messages_to_delete:
                # Purge the messages we need to delete
                await ctx.channel.delete_messages(messages_to_delete)
                await ctx.send(f"Deleted {len(messages_to_delete)} messages.", delete_after=5)
            else:
                await ctx.send("No bot-related messages or user-triggered replies found.", delete_after=5)

        except Exception as e:
            await ctx.send(f"An error occurred: {e}")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that trigger the bot to reply, so we can track them."""
        if message.author == self.bot.user:
            return  # Avoid tracking the bot's own messages
        
        # If the bot responds to the message, mark that user
        if message.reference and message.reference.message_id:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
            if replied_message.author == self.bot.user:
                self.users_triggered_bot.add(message.author.id)
                print(f"Tracked user {message.author.id} for triggering bot reply.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that trigger the bot to reply, so we can track them."""
        if message.author == self.bot.user:
            return
        
        if message.reference and message.reference.message_id:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
            if replied_message.author == self.bot.user:
                self.users_triggered_bot.add(message.author.id)
                print(f"Tracked user {message.author.id} for triggering bot reply.")

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that trigger the bot to reply, so we can track them."""
        if message.author == self.bot.user:
            return

        if message.reference and message.reference.message_id:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
            if replied_message.author == self.bot.user:
                self.users_triggered_bot.add(message.author.id)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for messages that trigger the bot to reply, so we can track them."""
        if message.author == self.bot.user:
            return

        if message.reference and message.reference.message_id:
            replied_message = await message.channel.fetch_message(message.reference.message_id)
            if replied_message.author == self.bot.user:
                self.users_triggered_bot.add(message.author.id)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Store the last deleted message for sniping."""
        if message.channel.id not in self.sniped_messages:
            self.sniped_messages[message.channel.id] = deque(maxlen=10)
        self.sniped_messages[message.channel.id].appendleft(message)

    @commands.command(name="s", aliases=['snipe'], help="Snipes recently deleted messages")
    @commands.has_permissions(send_messages=True)
    async def snipe(self, ctx, number: int = 1):
        """Snipe the specified deleted message number."""
        sniped_messages = self.sniped_messages.get(ctx.channel.id, [])
        
        if not sniped_messages:
            await ctx.send("No deleted messages found in the past 2 hours!")
            return

        # Ensure the requested number is within bounds
        if number < 1 or number > len(sniped_messages):
            await ctx.send(f"Please specify a number between 1 and {len(sniped_messages)}.")
            return

        # Fetch the specific message based on the user's input
        sniped_message = sniped_messages[number - 1]

        embed = discord.Embed(
            title=f"Message sniped from {sniped_message.author}",
            description=sniped_message.content,
            color=discord.Color.green()
        )

        # If the sniped message has attachments, show the first one
        if sniped_message.attachments:
            embed.set_image(url=sniped_message.attachments[0].url)

        embed.set_footer(text=f"Message sniped {number}/{len(sniped_messages)}", icon_url=ctx.author.avatar.url)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        """Store the last edited message for snipe."""
        if before.content != after.content:
            self.edited_messages[before.channel.id] = (before, after)

    @commands.command(name="es")
    @commands.has_permissions(send_messages=True)
    async def edit_snipe(self, ctx):
        """Snipe the last edited message."""
        sniped_edit = self.edited_messages.get(ctx.channel.id)
        
        if sniped_edit:
            before, after = sniped_edit
            embed = discord.Embed(
                title=f"Edited message from {before.author}",
                color=discord.Color.orange()
            )
            embed.add_field(name="Before", value=before.content, inline=False)
            embed.add_field(name="After", value=after.content, inline=False)
            embed.set_footer(text=f"Sniped by {ctx.author}", icon_url=ctx.author.avatar.url)
            await ctx.send(embed=embed)
        else:
            await ctx.send("There's no recently edited message to snipe.")

    @commands.command(name="cs")
    @commands.has_permissions(manage_messages=True)
    async def clear_snipe(self, ctx):
        """Clear the snipe history."""
        if ctx.channel.id in self.sniped_messages:
            self.sniped_messages[ctx.channel.id].clear()
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❌")

    @commands.command(name="ce")
    @commands.has_permissions(manage_messages=True)
    async def clear_edit_snipe(self, ctx):
        """Clear the edit snipe history."""
        if ctx.channel.id in self.edited_messages:
            del self.edited_messages[ctx.channel.id]
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❌")

    @commands.command(name="nuke")
    @commands.has_permissions(administrator=True)
    async def nuke(self, ctx):
        """Nukes the current channel with confirmation."""
        embed = discord.Embed(
            title="Nuke Channel Confirmation",
            description="Are you sure you want to nuke this channel? Please reply with 'Yes' or 'No'.",
            color=discord.Color.red()
        )

        await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and m.content.lower() in ["yes", "no"]

        try:
            response = await self.bot.wait_for('message', check=check, timeout=30.0)

            if response.content.lower() == 'yes':
                channel_name = ctx.channel.name
                category = ctx.channel.category
                overwrites = ctx.channel.overwrites

                await ctx.channel.delete()

                new_channel = await ctx.guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites,
                    topic=ctx.channel.topic,
                    reason="Channel nuked"
                )

                custom_permissions = []
                for member, overwrite in overwrites.items():
                    if overwrite.is_empty():
                        continue
                    custom_permissions.append(f"{member.name}")

                custom_permissions_message = "\n".join(custom_permissions) if custom_permissions else "No Custom Permissions"

                nuke_embed = discord.Embed(
                    title="Channel Nuked",
                    description=f"Channel nuked by {ctx.author.mention}",
                    color=discord.Color.red()
                )

                nuke_embed.add_field(name="Settings Configured:", value=f"Permissions:\n{custom_permissions_message}\nCategory: {category.name if category else 'None'}", inline=False)

                await new_channel.send(embed=nuke_embed)

                await new_channel.send("First 😭")

            else:
                await ctx.send("Nuke operation cancelled.")

        except asyncio.TimeoutError:
            await ctx.send("You took too long to respond. Nuke operation cancelled.")

    @tasks.loop(minutes=120)
    async def snipe_reset(self):
        """Clears all sniped messages every 2 hours."""
        self.sniped_messages.clear()

    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """Store the reaction that was removed."""
        if reaction.message.channel.id not in self.sniped_reactions:
            self.sniped_reactions[reaction.message.channel.id] = []
        
        # Store the sniped reaction details (reaction, message, user)
        self.sniped_reactions[reaction.message.channel.id].append((reaction, user))
        
    @commands.command(name="rs", help="Snipes the last removed reaction in the channel.")
    @commands.has_permissions(send_messages=True)
    async def reaction_snipe(self, ctx):
        """Snipes the last removed reaction and sends it in an embed."""
        sniped_reactions = self.sniped_reactions.get(ctx.channel.id, [])
        
        if not sniped_reactions:
            await ctx.send("No reactions have been removed recently in this channel.")
            return
        
        # Get the last sniped reaction
        reaction, user = sniped_reactions[-1]
        
        embed = discord.Embed(
            title=f"Reaction sniped from {user.display_name}",
            description=f"Reaction `{reaction.emoji}` removed by {user.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Sniped by {ctx.author}", icon_url=ctx.author.avatar.url)
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Purge(bot))
