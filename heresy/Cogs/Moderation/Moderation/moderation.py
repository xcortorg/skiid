import discord
from discord.ext import commands
import os
import json
from datetime import timedelta

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hardban_file = "json/hardbanned_users.json"
        if not os.path.exists("json"):
            os.makedirs("json")
        self.load_hardbans()

    def load_hardbans(self):
        """Load the hardbanned users from the JSON file."""
        if os.path.exists(self.hardban_file):
            with open(self.hardban_file, 'r') as f:
                self.hardbanned_users = json.load(f)
        else:
            self.hardbanned_users = {}

    def save_hardbans(self):
        """Save the hardbanned users to the JSON file."""
        with open(self.hardban_file, 'w') as f:
            json.dump(self.hardbanned_users, f)

    async def get_member(self, ctx, member: discord.Member = None, user_id: int = None):
        if member:
            return member
        if user_id:
            try:
                return await ctx.guild.fetch_member(user_id)
            except discord.NotFound:
                await ctx.send("User not found.")
        return None

    @commands.command(name='hardban', help='Hard bans a member by mention or User ID. Only admins or owner can unban.')
    @commands.has_permissions(administrator=True)
    async def hardban(self, ctx, member: discord.Member = None, user_id: int = None):
        target = await self.get_member(ctx, member, user_id)
        if not target:
            await ctx.send("You must specify a user to hardban (mention or User ID).")
            return

        server_id = str(ctx.guild.id)
        if server_id not in self.hardbanned_users:
            self.hardbanned_users[server_id] = []

        if str(target.id) in self.hardbanned_users[server_id]:
            await ctx.send(f"{target} is already hardbanned.")
            return

        try:
            await target.ban(reason=f"Hardbanned by {ctx.author}")
            self.hardbanned_users[server_id].append(str(target.id))
            self.save_hardbans()
            await ctx.send(f"👍")
        except discord.Forbidden:
            await ctx.send("no")
        except discord.HTTPException:
            await ctx.send("Failed to hardban the user.")

    @commands.command(name='ban', aliases=['fuck', 'rape'], help='Bans a member by mention or User ID.')
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member = None, user_id: int = None):
        target = await self.get_member(ctx, member, user_id)
        if not target:
            await ctx.send("You must specify a user to ban (mention or User ID).")
            return

        # Check if the target is the bot
        if target == self.bot.user:
            await ctx.send("Why the fuck is this nigga tryna ban me with my own command?")
            return

        # Check if the target is a specific user (e.g., unbannable user)
        unbannable_user_id = 785042666475225109  # Replace with the actual user ID
        if target.id == unbannable_user_id:
            await ctx.send("no")
            return

        try:
            await target.ban(reason=f"Banned by {ctx.author}")
            await ctx.send(":thumbsup:")
        except discord.Forbidden:
            await ctx.send("I do not have permission to ban this user.")
        except discord.HTTPException:
            await ctx.send("Failed to ban the user.")

    async def get_member(self, ctx, member, user_id):
        if member:
            return member
        if user_id:
            try:
                return await ctx.guild.fetch_member(user_id)
            except discord.NotFound:
                return None
        return None

    @commands.command(name='unban', aliases= ['befree'], help='Unbans a member by User ID.')
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, user_id: int):
        user = discord.Object(id=user_id)
        try:
            await ctx.guild.unban(user)
            await ctx.send("👍")
        except discord.NotFound:
            await ctx.send("User not found in the ban list.")
        except discord.Forbidden:
            await ctx.send("I do not have permission to unban this user.")
        except discord.HTTPException:
            await ctx.send("Failed to unban the user.")

    @commands.command(name='kick', aliases= ['soccer'], help='Kicks a member by mention or User ID.')
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member = None, user_id: int = None):
        target = await self.get_member(ctx, member, user_id)
        if not target:
            await ctx.send("You must specify a user to kick (mention or User ID).")
            return

        try:
            await target.kick(reason=f"Kicked by {ctx.author}")
            await ctx.send("👍")
        except discord.Forbidden:
            await ctx.send("I do not have permission to kick this user.")
        except discord.HTTPException:
            await ctx.send("Failed to kick the user.")

    @commands.command(name='warn', help='Warns a member by mention or User ID.')
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, member: discord.Member = None, user_id: int = None):
        target = await self.get_member(ctx, member, user_id)
        if not target:
            await ctx.send("You must specify a user to warn (mention or User ID).")
            return

        log_dir = "Warn Logs"
        os.makedirs(log_dir, exist_ok=True)

        with open(os.path.join(log_dir, f"{target.name}.txt"), 'a') as f:
            f.write(f"Warned by {ctx.author}: {ctx.message.content}\n")

        await ctx.send(f"{target} has been warned.")

    @commands.command(name='timeout', aliases= ['to', 'bdsm', 'ballgag', 'stfu', 'sybau', 'touch', 'smd'], help='Times out a member by mention or User ID for a specified duration (default is 1 minute).')
    @commands.has_permissions(moderate_members=True)
    async def timeout(self, ctx, member: discord.Member = None, user_id: int = None, seconds: int = 300):
        target = await self.get_member(ctx, member, user_id)
        if not target:
            await ctx.send("You must specify a user to timeout (mention or User ID).")
            return

        try:
            await target.timeout(discord.utils.utcnow() + timedelta(seconds=seconds), reason=f"Timed out by {ctx.author}")
            await ctx.send("👍")
        except discord.Forbidden:
            await ctx.send("I do not have permission to timeout this user.")
        except discord.HTTPException:
            await ctx.send("Failed to timeout the user.")

    @commands.command(name='untimeout', aliases= ['uto', 'getmydickoutyamouth'], help='Removes the timeout from a member by mention or User ID.')
    @commands.has_permissions(moderate_members=True)
    async def remove_timeout(self, ctx, member: discord.Member = None, user_id: int = None):
        target = await self.get_member(ctx, member, user_id)
        if not target:
            await ctx.send("You must specify a user to remove timeout (mention or User ID).")
            return

        try:
            await target.timeout(None, reason=f"Timeout removed by {ctx.author}")
            await ctx.send("👍")
        except discord.Forbidden:
            await ctx.send("I do not have permission to remove timeout from this user.")
        except discord.HTTPException:
            await ctx.send("Failed to remove timeout from the user.")

    @commands.command(name='nick', aliases= ['fn', 'forcenick'])
    @commands.has_permissions(manage_nicknames=True)
    async def nick(self, ctx, member: discord.Member, *, new_nick: str):
        """Changes the nickname of the mentioned user."""
        if ctx.author.top_role <= member.top_role:
            await ctx.send("You cannot change the nickname of this user.")
            return

        try:
            await member.edit(nick=new_nick)
            await ctx.send(f"Nickname for {member.mention} changed to `{new_nick}`.")
        except discord.Forbidden:
            await ctx.send("I do not have permission to change this user's nickname.")
        except discord.HTTPException:
            await ctx.send("Failed to change the nickname. Please try again.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
