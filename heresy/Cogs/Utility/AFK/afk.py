import discord
from discord.ext import commands
import sqlite3
import time
import os

class AFK(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join("db", "afk_users.db")
        self.initialize_db()
        print("[AFK] Initialized AFK cog and database connection.")

    def initialize_db(self):
        """Initialize the database folder and file to store AFK users."""
        try:
            # Create 'db' directory if it doesn't exist
            if not os.path.exists("db"):
                os.makedirs("db")
                print("[AFK] Created 'db' directory for database files.")

            # Connect to the database file in the 'db' folder
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS afk_users (
                user_id INTEGER PRIMARY KEY,
                reason TEXT,
                afk_time INTEGER
            )''')
            conn.commit()
            conn.close()
            print("[AFK] Database initialized successfully.")
        except sqlite3.Error as e:
            print(f"[AFK] Error initializing database: {e}")

    def set_afk(self, user_id, reason):
        """Sets the AFK status for a user with the current timestamp."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''INSERT OR REPLACE INTO afk_users (user_id, reason, afk_time)
            VALUES (?, ?, ?)''', (user_id, reason, int(time.time())))
            conn.commit()
            conn.close()
            print(f"[AFK] AFK set for user {user_id} with reason: {reason}")
        except sqlite3.Error as e:
            print(f"[AFK] Error setting AFK: {e}")

    def get_afk_status(self, user_id):
        """Gets the AFK status and timestamp for a user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''SELECT reason, afk_time FROM afk_users WHERE user_id = ?''', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result
        except sqlite3.Error as e:
            print(f"[AFK] Error getting AFK status: {e}")
            return None

    def remove_afk(self, user_id):
        """Removes the AFK status for a user."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''DELETE FROM afk_users WHERE user_id = ?''', (user_id,))
            conn.commit()
            conn.close()
            print(f"[AFK] AFK removed for user {user_id}.")
        except sqlite3.Error as e:
            print(f"[AFK] Error removing AFK: {e}")

    def format_time_ago(self, afk_time):
        """Formats the time since the AFK status was set."""
        time_elapsed = int(time.time()) - afk_time
        if time_elapsed < 60:
            return "a few seconds ago"
        elif time_elapsed < 3600:
            minutes = time_elapsed // 60
            return f"{minutes} minutes ago"
        elif time_elapsed < 86400:
            hours = time_elapsed // 3600
            return f"{hours} hours ago"
        else:
            days = time_elapsed // 86400
            return f"{days} days ago"

    @commands.command(name='afk', aliases= ["kms", "despawn", "idle"])
    async def afk(self, ctx, *, reason: str = "AFK"):
        """Set the AFK status with an optional reason."""
        user_id = ctx.author.id
        self.set_afk(user_id, reason)

        embed = discord.Embed(
            description=f"<:check:1301903971535028314> {ctx.author.display_name}, you're now AFK with the status: **{reason}**.",
            color=discord.Color.blue()
        )
        await ctx.reply(embed=embed, mention_author=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.webhook_id is not None:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            print(f"[AFK Debug] Ignoring AFK removal for command: {message.content}")
            return

        afk_data = self.get_afk_status(message.author.id)
        
        if afk_data:
            print(f"[AFK Debug] Removing AFK for user: {message.author.id} due to manual message.")
            self.remove_afk(message.author.id)

            embed = discord.Embed(
                description=f"👋 Welcome back, {message.author.display_name}! You went AFK {self.format_time_ago(afk_data[1])}.",
                color=discord.Color.green()
            )
            await message.channel.send(embed=embed)

        for mentioned_user in message.mentions:
            afk_data = self.get_afk_status(mentioned_user.id)
            if afk_data:
                embed = discord.Embed(
                    description=f"{mentioned_user.display_name} is currently AFK: **{afk_data[0]}**.",
                    color=discord.Color.red()
                )
                await message.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        afk_data = self.get_afk_status(before.author.id)
        if afk_data:
            embed = discord.Embed(
                description=f"{before.author.display_name} is currently AFK: **{afk_data[0]}**.",
                color=discord.Color.red()
            )
            await after.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot:
            return
        
        afk_data = self.get_afk_status(message.author.id)
        if afk_data:
            embed = discord.Embed(
                description=f"{message.author.display_name} is AFK: **{afk_data[0]}**.",
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(AFK(bot))