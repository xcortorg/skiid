import discord
from discord.ext import commands
import sqlite3

class Reactions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.custom_reactions = {}
        self.skull_targets = set()
        self.auto_react_targets = {}
        
        self.db_path = "reactions.db"
        self.setup_database()
        self.load_data()

    def setup_database(self):
        """Create the database and tables if they do not exist."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS skull_targets (user_id INTEGER PRIMARY KEY)''')
        c.execute('''CREATE TABLE IF NOT EXISTS auto_react (user_id INTEGER, emojis TEXT, PRIMARY KEY (user_id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS custom_reactions (word TEXT PRIMARY KEY, emoji TEXT)''')
        conn.commit()
        conn.close()

    def load_data(self):
        """Load skull targets and auto-reaction settings from the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        c.execute('SELECT user_id FROM skull_targets')
        for (user_id,) in c.fetchall():
            self.skull_targets.add(user_id)
        
        c.execute('SELECT user_id, emojis FROM auto_react')
        for (user_id, emojis) in c.fetchall():
            self.auto_react_targets[user_id] = emojis.split(",")
        
        c.execute('SELECT word, emoji FROM custom_reactions')
        for (word, emoji) in c.fetchall():
            self.custom_reactions[word.lower()] = emoji
        
        conn.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listens for specific keywords and reacts accordingly."""
        if message.author == self.bot.user:
            return

        if "@everyone" in message.content:
            await message.reply("https://cdn.discordapp.com/attachments/1258207125797208064/1274904156234317926/caption-2.gif?ex=673fdf85&is=673e8e05&hm=54c8c2e29ab8e5e9b923245b2d66f55bf9b9b8e85a89d4fb8ac1e730e3882e6d&")

        if message.author.id in self.skull_targets:
            await message.add_reaction("💀")
        elif "sob" in message.content.lower():
            await message.add_reaction("😭")
        elif message.content.lower() in self.custom_reactions:
            await message.add_reaction(self.custom_reactions[message.content.lower()])
        
        if message.author.id in self.auto_react_targets:
            for emoji in self.auto_react_targets[message.author.id]:
                await message.add_reaction(emoji)

    @commands.command(name="skull")
    async def skull(self, ctx, user: discord.Member):
        """Toggles the skull reaction targeting for a user."""
        if user.id in self.skull_targets:
            self.skull_targets.remove(user.id)
            embed = discord.Embed(
                title="Skull Reaction Target Removed",
                description=f"{user.mention} will no longer receive a 💀 reaction.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('DELETE FROM skull_targets WHERE user_id = ?', (user.id,))
            conn.commit()
            conn.close()
        else:
            self.skull_targets.add(user.id)
            embed = discord.Embed(
                title="Skull Reaction Targeted",
                description=f"{user.mention} will receive a 💀 reaction whenever they send a message.",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)

            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT OR IGNORE INTO skull_targets (user_id) VALUES (?)', (user.id,))
            conn.commit()
            conn.close()

    @commands.command(name="skullreset")
    async def skullreset(self, ctx):
        """Resets all users targeted by the skull command."""
        self.skull_targets.clear()
        
        embed = discord.Embed(
            title="Skull Targets Reset",
            description="All skull targets have been reset.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM skull_targets')
        conn.commit()
        conn.close()

    @commands.command(name="ar", aliases= ["autoreactor, autoreaction, reactions"])
    async def auto_react(self, ctx, user: discord.Member, *emojis):
        """Sets up auto-react for a specified user with given emojis."""
        if user.id not in self.auto_react_targets:
            self.auto_react_targets[user.id] = []

        self.auto_react_targets[user.id].extend(emojis)
        
        embed = discord.Embed(
            title="Auto-Reaction Set",
            description=f"{user.mention} will receive reactions: {', '.join(emojis)}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO auto_react (user_id, emojis) VALUES (?, ?)', (user.id, ",".join(self.auto_react_targets[user.id])))
        conn.commit()
        conn.close()

    @commands.command(name="arreset", aliases= ["reactionsreset, removereactions, reactionsremove"])
    async def auto_react_reset(self, ctx):
        """Resets all auto-react settings."""
        self.auto_react_targets.clear()
        
        embed = discord.Embed(
            title="Auto-Reactions Reset",
            description="All auto-reaction settings have been reset.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM auto_react')
        conn.commit()
        conn.close()

    @commands.group(name="reaction", invoke_without_command=True)
    async def reaction(self, ctx):
        """Base command for custom reactions."""
        await ctx.send("Available subcommands: `add`, `remove`, `reset`")

    @reaction.command(name="add")
    async def custom_word_add(self, ctx, word: str, emoji: str):
        """Adds a custom word for auto-reaction."""
        word_lower = word.lower()
        self.custom_reactions[word_lower] = emoji
        
        embed = discord.Embed(
            title="Custom Reaction Added",
            description=f"Now reacting to '{word}' with {emoji}",
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)

        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('INSERT OR REPLACE INTO custom_reactions (word, emoji) VALUES (?, ?)', (word_lower, emoji))
            conn.commit()
        except Exception as e:
            print(f"Error saving to database: {e}")
        finally:
            conn.close()

    @reaction.command(name="remove")
    async def custom_word_remove(self, ctx, word: str):
        """Removes a custom word for auto-reaction."""
        word_lower = word.lower()
        if word_lower in self.custom_reactions:
            del self.custom_reactions[word_lower]
            embed = discord.Embed(
                title="Custom Reaction Removed",
                description=f"Removed reaction for the word '{word}'.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)

            try:
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute('DELETE FROM custom_reactions WHERE word = ?', (word_lower,))
                conn.commit()
            except Exception as e:
                print(f"Error removing from database: {e}")
            finally:
                conn.close()
        else:
            embed = discord.Embed(
                title="Word Not Found",
                description=f"There is no custom reaction for '{word}'.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)

    @reaction.command(name="reset")
    async def custom_word_reset(self, ctx):
        """Resets all custom keyword reactions."""
        self.custom_reactions.clear()
        
        embed = discord.Embed(
            title="Custom Reactions Reset",
            description="All custom keyword reactions have been reset.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM custom_reactions')
        conn.commit()
        conn.close()

async def setup(bot):
    await bot.add_cog(Reactions(bot))
