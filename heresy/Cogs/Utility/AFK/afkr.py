import discord
from discord.ext import commands
import sqlite3
import json
import time
import os

class AFKRaw(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = os.path.join("db", "afkr_users.db")
        self.initialize_db()
        print("[AFKRaw] Initialized AFKRaw cog and database connection.")

    def initialize_db(self):
        """Initialize the database folder and file to store AFK users."""
        if not os.path.exists("db"):
            os.makedirs("db")
            print("[AFKRaw] Created 'db' directory for database files.")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS afk_users (
            user_id INTEGER PRIMARY KEY,
            reason TEXT,
            afk_time INTEGER
        )''')
        conn.commit()
        conn.close()
        print("[AFKRaw] Database initialized successfully.")

    def set_afk(self, user_id, reason):
        """Sets the AFK status for a user with the current timestamp."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''INSERT OR REPLACE INTO afk_users (user_id, reason, afk_time)
        VALUES (?, ?, ?)''', (user_id, reason, int(time.time())))
        conn.commit()
        conn.close()
        print(f"[AFKRaw] AFK set for user {user_id} with reason: {reason}")

    def get_afk_status(self, user_id):
        """Gets the AFK status and timestamp for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''SELECT reason, afk_time FROM afk_users WHERE user_id = ?''', (user_id,))
        result = cursor.fetchone()
        conn.close()
        return result

    def remove_afk(self, user_id):
        """Removes the AFK status for a user."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM afk_users WHERE user_id = ?''', (user_id,))
        conn.commit()
        conn.close()
        print(f"[AFKRaw] AFK removed for user {user_id}.")

    @commands.command(name='afkr', aliases=["afkraw", "jsonafk", "rawafk"])
    async def afkr(self, ctx, *, reason: str = "AFK"):
        """Set the AFK status with raw JSON output."""
        user_id = ctx.author.id
        self.set_afk(user_id, reason)

        # JSON output
        afk_status = {
            "afk": True,
            "user_id": user_id,
            "username": str(ctx.author),
            "reason": reason,
            "timestamp": int(time.time())
        }
        raw_json = json.dumps(afk_status, indent=4)
        await ctx.reply(f"```json\n{raw_json}\n```", mention_author=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handles returning from AFK and mentions."""
        if message.author.bot or message.webhook_id is not None:
            return

        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return  # Ignore commands

        # Remove AFK if the user sends a message
        afk_data = self.get_afk_status(message.author.id)
        if afk_data:
            self.remove_afk(message.author.id)
            return_status = {
                "afk": False,
                "user_id": message.author.id,
                "username": str(message.author),
                "return_time": int(time.time())
            }
            raw_json = json.dumps(return_status, indent=4)
            await message.channel.send(f"```json\n{raw_json}\n```")

        # Check mentions for AFK status
        for mentioned_user in message.mentions:
            afk_data = self.get_afk_status(mentioned_user.id)
            if afk_data:
                afk_notification = {
                    "afk": True,
                    "user_id": mentioned_user.id,
                    "username": str(mentioned_user),
                    "reason": afk_data[0],
                    "afk_since": afk_data[1],
                    "mentioned_by": {
                        "user_id": message.author.id,
                        "username": str(message.author)
                    }
                }
                raw_json = json.dumps(afk_notification, indent=4)
                await message.channel.send(f"```json\n{raw_json}\n```")

async def setup(bot):
    await bot.add_cog(AFKRaw(bot))
