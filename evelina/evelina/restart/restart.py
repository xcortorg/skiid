#!/usr/bin/env python3
# restart.py

import discord_ios                # patch in “mobile” presence
import os
import subprocess
import discord
from discord.ext import commands
from discord.ui import View, button
from discord import Colour
from discord.utils import utcnow

OWNER_IDS = [
    320288667329495040,
    585689685771288600,
    660204203834081284,
    659438962624167957
]

ALLOWED_ROLE_ID = 1364711001550884978
REPO_PATH       = "/root/evelina"
PM2_PROCESS     = "6"
EMBED_COLOR     = 0x729BB0

APPROVE_EMOJI = "<:approve_1:1364239632547708978>"
DENY_EMOJI    = "<:deny:1364258827565928528>"

# Intents
intents = discord.Intents.default()
intents.presences       = True
intents.members         = True
intents.message_content = True

# Presence
activity = discord.CustomActivity(name="🔗 evelina.bot")

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    help_command=None,
    status=discord.Status.online,
    activity=activity
)

@bot.check
async def has_permission(ctx: commands.Context) -> bool:
    if ctx.author.id in OWNER_IDS:
        return True
    if ctx.guild and ctx.author.guild_permissions.administrator:
        return True
    if ctx.guild and any(role.id == ALLOWED_ROLE_ID for role in ctx.author.roles):
        return True
    return False

class ConfirmRestart(View):
    def __init__(self, author: discord.Member, option: str):
        super().__init__(timeout=60)
        self.author = author
        self.option = option

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.author:
            await interaction.response.send_message("This confirmation isn't for you.", ephemeral=True)
        return interaction.user == self.author

    @button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, btn: discord.ui.Button):
        self.stop()
        if self.option == "--pull":
            old = subprocess.run(
                ["git", "-C", REPO_PATH, "rev-parse", "HEAD"],
                capture_output=True, text=True
            ).stdout.strip()
            subprocess.run(
                ["git", "-C", REPO_PATH, "pull"],
                capture_output=True, text=True
            )
            new = subprocess.run(
                ["git", "-C", REPO_PATH, "rev-parse", "HEAD"],
                capture_output=True, text=True
            ).stdout.strip()
            if not old or not new or old == new:
                embed = discord.Embed(
                    description=f"ℹ️ {self.author.mention}: No update found. Aborting...",
                    color=Colour.yellow(),
                )
                embed.set_footer(text="Checked at")
                return await interaction.response.edit_message(embed=embed, view=None)

        subprocess.run(
            ["pm2", "restart", PM2_PROCESS],
            capture_output=True, text=True
        )
        embed = discord.Embed(
            description=f"{APPROVE_EMOJI} {self.author.mention}: Successfully restarted the main bot",
            color=Colour.green(),
        )
        await interaction.response.edit_message(embed=embed, view=None)

    @button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, btn: discord.ui.Button):
        self.stop()
        embed = discord.Embed(
            description=f"{DENY_EMOJI} {self.author.mention}: Restart got canceled",
            color=Colour.red(),
        )
        await interaction.response.edit_message(embed=embed, view=None)

@bot.command(name="h", aliases=["help"], brief="Show help for a command")
async def help_cmd(ctx: commands.Context, command_name: str = None):
    if command_name and command_name.lower() == "restart":
        embed = discord.Embed(color=EMBED_COLOR)
        embed.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar.url)
        embed.title = "Command: restart"
        embed.add_field(name="Aliases",    value="N/A",    inline=True)
        embed.add_field(name="Parameters", value="option", inline=True)
        embed.add_field(
            name="Information",
            value="<:warning_1:1364625479193198733> Bot Developer",
            inline=True
        )
        embed.add_field(
            name="Usage",
            value="```Syntax: !restart [option]```",
            inline=False
        )
        embed.set_footer(text="Page: 1/1 · Module: developer.py")
        return await ctx.send(embed=embed)

    fallback = discord.Embed(color=EMBED_COLOR)
    fallback.set_author(name=ctx.bot.user.name, icon_url=ctx.bot.user.avatar.url)
    fallback.title = "Help"
    fallback.add_field(
        name="!h restart",
        value="Show usage for the restart command",
        inline=False
    )
    await ctx.send(embed=fallback)

@bot.command(name="restart", brief="Restart main bot; --pull to update first")
async def restart(ctx: commands.Context, *, option: str = ""):
    desc = (
        "Are you sure you want to pull & restart the main bot?"
        if option == "--pull"
        else "Are you sure you want to restart the main bot?"
    )
    embed = discord.Embed(title="Confirm Restart", description=desc, color=EMBED_COLOR)
    view = ConfirmRestart(ctx.author, option)
    await ctx.send(embed=embed, view=view)

if __name__ == "__main__":
    token = os.getenv("RESTART_BOT_TOKEN")
    if not token:
        raise RuntimeError("RESTART_BOT_TOKEN not set in environment")
    bot.run(token)