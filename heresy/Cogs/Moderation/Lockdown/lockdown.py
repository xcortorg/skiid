import discord
from discord.ext import commands
import json
import os
import io
import asyncio

class Lockdown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.exempt_channels = set()
        self.config_folder = "Member-Access-Roles"
        self.backup_folder = "Server Backups"
        os.makedirs(self.config_folder, exist_ok=True)
        os.makedirs(self.backup_folder, exist_ok=True)

    def save_json(self, data, filename):
        """Saves the provided data to a JSON file."""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    
    def load_json(self, filename):
        """Loads data from a JSON file."""
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                return json.load(f)
        return {}

    @commands.command(name="mem-role")
    @commands.has_permissions(administrator=True)
    async def set_member_role(self, ctx, role: discord.Role):
        """Sets the member role for the server and saves it in a unique file for each guild."""
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = {"member_role_id": role.id}
        self.save_json(data, filename)

        embed = discord.Embed(
            title="Member Role Set",
            description=f"Member role for **{ctx.guild.name}** has been set to **{role.name}**.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        await ctx.send(embed=embed)

    @commands.command(name="access-role")
    @commands.has_permissions(administrator=True)
    async def set_access_role(self, ctx, role: discord.Role):
        """Sets the access role for the server and saves it in a unique file for each guild."""
        filename = f"{self.config_folder}/{ctx.guild.name}_access_role.json"
        data = {"access_role_id": role.id}
        self.save_json(data, filename)

        embed = discord.Embed(
            title="Access Role Set",
            description=f"Access role for **{ctx.guild.name}** has been set to **{role.name}**.",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Role ID: {role.id}")
        await ctx.send(embed=embed)

    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock_channel(self, ctx, channel: discord.TextChannel = None):
        """Locks a specified or current channel."""
        channel = channel or ctx.channel
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            await channel.set_permissions(ctx.guild.default_role, send_messages=False)
            member_role = ctx.guild.get_role(member_role_id)
            if member_role:
                await channel.set_permissions(member_role, send_messages=False)
            await ctx.send(f"👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock_channel(self, ctx, channel: discord.TextChannel = None):
        """Unlocks a specified or current channel."""
        channel = channel or ctx.channel
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            await channel.set_permissions(ctx.guild.default_role, send_messages=True)
            member_role = ctx.guild.get_role(member_role_id)
            if member_role:
                await channel.set_permissions(member_role, send_messages=True)
            await ctx.send(f"👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="access")
    @commands.has_permissions(manage_channels=True)
    async def grant_access(self, ctx, channel: discord.TextChannel):
        """Grants access to a channel for the access role."""
        filename = f"{self.config_folder}/{ctx.guild.name}_access_role.json"
        data = self.load_json(filename)
        access_role_id = data.get("access_role_id")

        if access_role_id:
            access_role = ctx.guild.get_role(access_role_id)
            await channel.set_permissions(access_role, view_channel=True, send_messages=True)
            await ctx.send(f"👍")
        else:
            await ctx.send("Access role is not set. Use `access-role` to set it first.")

    @commands.command(name="exempt-user")
    @commands.has_permissions(manage_channels=True)
    async def exempt_user(self, ctx, target: discord.Member):
        """Exempts a user from lockdown."""
        pass

    @commands.command(name="hide")
    @commands.has_permissions(manage_channels=True)
    async def hide_channel(self, ctx, channel: discord.TextChannel = None):
        """Hides the current or specified channel from @everyone and member role."""
        channel = channel or ctx.channel
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            await channel.set_permissions(ctx.guild.default_role, view_channel=False)
            member_role = ctx.guild.get_role(member_role_id)
            if member_role:
                await channel.set_permissions(member_role, view_channel=False)
            await ctx.send(f"👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="hide-all")
    @commands.has_permissions(administrator=True)
    async def hide_all_channels(self, ctx):
        """Hides all channels from @everyone and member role."""
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            member_role = ctx.guild.get_role(member_role_id)
            for channel in ctx.guild.text_channels:
                await channel.set_permissions(ctx.guild.default_role, view_channel=False)
                if member_role:
                    await channel.set_permissions(member_role, view_channel=False)
            await ctx.send("👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="unhide")
    @commands.has_permissions(manage_channels=True)
    async def unhide_channel(self, ctx, channel: discord.TextChannel = None):
        """Unhides the current or specified channel."""
        channel = channel or ctx.channel
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            await channel.set_permissions(ctx.guild.default_role, view_channel=True)
            member_role = ctx.guild.get_role(member_role_id)
            if member_role:
                await channel.set_permissions(member_role, view_channel=True)
            await ctx.send(f"👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="unhide-all")
    @commands.has_permissions(administrator=True)
    async def unhide_all_channels(self, ctx):
        """Unhides all channels from @everyone and member role."""
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            member_role = ctx.guild.get_role(member_role_id)
            for channel in ctx.guild.text_channels:
                await channel.set_permissions(ctx.guild.default_role, view_channel=True)
                if member_role:
                    await channel.set_permissions(member_role, view_channel=True)
            await ctx.send("👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="lockdown")
    @commands.has_permissions(administrator=True)
    async def lockdown_all(self, ctx):
        """Locks and hides all channels in the server."""
        await self.lock_all_channels(ctx)
        await self.hide_all_channels(ctx)
        await ctx.send("👍")

    @commands.command(name="create-backup")
    @commands.has_permissions(administrator=True)
    async def backup(self, ctx):
        """Creates a backup file of the current channel permissions."""
        backup_data = {}
        for channel in ctx.guild.text_channels:
            perms = channel.overwrites_for(ctx.guild.default_role)
            backup_data[channel.id] = {
                "send_messages": perms.send_messages,
                "view_channel": perms.view_channel
            }
        filename = f"{self.backup_folder}/{ctx.guild.name}_backup.json"
        self.save_json(backup_data, filename)
        await ctx.send(f"Backup created for {ctx.guild.name}.")

    @commands.command(name="restore")
    @commands.has_permissions(administrator=True)
    async def restore(self, ctx):
        """Restores channel permissions from a specified backup file (uploaded as a JSON file)."""

        await ctx.send("Please upload the backup file as a JSON attachment in response to this message.")

        def check(m):
            return (
                m.author == ctx.author
                and m.channel == ctx.channel
                and m.attachments
                and m.attachments[0].filename.endswith(".json")
            )

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            backup_file = await msg.attachments[0].read()
            backup_data = self.load_json_from_file(io.BytesIO(backup_file))
            
            if not backup_data:
                await ctx.send("Failed to load backup data. Please ensure it's a valid JSON file.")
                return

            for channel_id, perms in backup_data.items():
                channel = ctx.guild.get_channel(int(channel_id))
                if channel:
                    await channel.set_permissions(
                        ctx.guild.default_role,
                        send_messages=perms.get("send_messages"),
                        view_channel=perms.get("view_channel")
                    )

            await ctx.send(f"Permissions restored for `{ctx.guild.name}` from the uploaded backup file.")

        except asyncio.TimeoutError:
            await ctx.send("No file was uploaded in time. Please try the restore command again.")

    @commands.command(name="lock-all")
    @commands.has_permissions(administrator=True)
    async def lock_all_channels(self, ctx):
        """Locks all channels in the server, skipping exempted channels."""
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            member_role = ctx.guild.get_role(member_role_id)
            for channel in ctx.guild.text_channels:
                if channel.id not in self.exempt_channels:
                    await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                    if member_role:
                        await channel.set_permissions(member_role, send_messages=False)
            await ctx.send("👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="unlock-all")
    @commands.has_permissions(administrator=True)
    async def unlock_all_channels(self, ctx):
        """Unlocks all channels in the server, skipping exempted channels."""
        filename = f"{self.config_folder}/{ctx.guild.name}_member_role.json"
        data = self.load_json(filename)
        member_role_id = data.get("member_role_id")

        if member_role_id:
            member_role = ctx.guild.get_role(member_role_id)
            for channel in ctx.guild.text_channels:
                if channel.id not in self.exempt_channels:
                    await channel.set_permissions(ctx.guild.default_role, send_messages=True)
                    if member_role:
                        await channel.set_permissions(member_role, send_messages=True)
            await ctx.send("👍")
        else:
            await ctx.send("Member role is not set. Use `mem-role` to set it first.")

    @commands.command(name="ignore", aliases= ['exempt'])
    @commands.has_permissions(manage_channels=True)
    async def exempt_channel(self, ctx, channel: discord.TextChannel = None):
        """
        Exempts a channel from being locked or unlocked.
        """
        channel = channel or ctx.channel

        if channel.id in self.exempt_channels:
            self.exempt_channels.remove(channel.id)
            await ctx.send(f"🚫 {channel.mention} is no longer exempted.")
        else:
            self.exempt_channels.add(channel.id)
            await ctx.send(f"✅ {channel.mention} will now be ignored during lockdown.")


async def setup(bot):
    await bot.add_cog(Lockdown(bot))
