import discord
from discord.ext import commands
import json
import os

CONFIG_FILE = "config.json"

class PicCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                json.dump({"servers": {}}, f)
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    @commands.group(name="vanity")
    async def vanity_group(self, ctx):
        """Group of commands to manage vanity settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send("Use `vanity set`, `vanity pic`, or `vanity logs`.")

    @vanity_group.command(name="set")
    @commands.has_permissions(administrator=True)
    async def set_vanity(self, ctx, *, vanity: str):
        """Set the vanity keyword for the server."""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config["servers"]:
            self.config["servers"][guild_id] = {}

        self.config["servers"][guild_id]["vanity"] = vanity
        self.save_config()
        await ctx.send(f"Vanity keyword set to `{vanity}` for this server.")

    @vanity_group.command(name="pic")
    @commands.has_permissions(administrator=True)
    async def set_pic_role(self, ctx, role: discord.Role):
        """Set the pic permissions role for the server."""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config["servers"]:
            self.config["servers"][guild_id] = {}

        self.config["servers"][guild_id]["pic_role"] = role.id
        self.save_config()
        await ctx.send(f"Pic permissions role set to `{role.name}`.")

    @vanity_group.command(name="logs")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel):
        """Set the log channel for vanity updates."""
        guild_id = str(ctx.guild.id)
        if guild_id not in self.config["servers"]:
            self.config["servers"][guild_id] = {}

        self.config["servers"][guild_id]["log_channel"] = channel.id
        self.save_config()
        await ctx.send(f"Log channel set to `{channel.name}`.")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Check member status and assign/remove pic perms."""
        guild_id = str(after.guild.id)
        if guild_id not in self.config["servers"]:
            return

        settings = self.config["servers"][guild_id]
        vanity = settings.get("vanity", "/vanity")
        pic_role_id = settings.get("pic_role")
        log_channel_id = settings.get("log_channel")

        if not pic_role_id or not log_channel_id:
            return

        role = after.guild.get_role(pic_role_id)
        log_channel = self.bot.get_channel(log_channel_id)

        if not role or not log_channel:
            return

        before_status = before.activities
        after_status = after.activities

        before_status_text = next(
            (str(activity.name) for activity in before_status if hasattr(activity, "name")), ""
        )
        after_status_text = next(
            (str(activity.name) for activity in after_status if hasattr(activity, "name")), ""
        )

        if vanity in after_status_text and role not in after.roles:
            await after.add_roles(role)
            embed = discord.Embed(
                title="Vanity Update",
                description=f"Gave pic perms to {after.mention}, user has '{vanity}' in status.",
                color=discord.Color.green(),
            )
            await log_channel.send(embed=embed)

        elif vanity not in after_status_text and role in after.roles:
            await after.remove_roles(role)
            embed = discord.Embed(
                title="Vanity Update",
                description=f"Removed pic perms from {after.mention}, user no longer has '{vanity}' in status.",
                color=discord.Color.red(),
            )
            await log_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PicCog(bot))
