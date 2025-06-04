import discord
from discord.ext import commands
from discord import app_commands
import json
import os

class JoinLogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.join_log_file = 'join_log_settings.json'
        self.join_log_settings = self.load_join_log_settings()

    def load_join_log_settings(self):
        if os.path.exists(self.join_log_file):
            with open(self.join_log_file, 'r') as f:
                return json.load(f)
        else:
            return {}

    def save_join_log_settings(self):
        with open(self.join_log_file, 'w') as f:
            json.dump(self.join_log_settings, f, indent=4)

    @commands.command(name="joinlogs")
    @commands.has_permissions(administrator=True)
    async def set_join_logs(self, ctx, channel: discord.TextChannel):
        """Sets the join log channel for the current server."""
        server_id = str(ctx.guild.id)
        if server_id not in self.join_log_settings:
            self.join_log_settings[server_id] = {}
        
        self.join_log_settings[server_id]["channel_id"] = channel.id
        self.save_join_log_settings()
        await ctx.send(f"Join logs have been set to {channel.mention} for this server.")

    @commands.command(name="joinmsg", aliases= ["welcmsg, joinmessage, welcomemessage, welcmessage"])
    @commands.has_permissions(administrator=True)
    async def set_join_message(self, ctx, *, message: str):
        """Sets a custom welcome message for the server and displays it in an embed."""
        server_id = str(ctx.guild.id)
        if server_id not in self.join_log_settings:
            self.join_log_settings[server_id] = {}
        
        self.join_log_settings[server_id]["welcome_message"] = message
        self.save_join_log_settings()

        embed = discord.Embed(
            title="Welcome Message Set",
            description=f"{message} {ctx.author.mention}",
            color=discord.Color.green()
        )
        await ctx.send("Custom welcome message has been set.", embed=embed)

    @commands.command(name="leavemsg")
    @commands.has_permissions(administrator=True)
    async def set_leave_message(self, ctx, *, message: str):
        """Sets a custom leave message for the server and displays it in an embed."""
        server_id = str(ctx.guild.id)
        if server_id not in self.join_log_settings:
            self.join_log_settings[server_id] = {}
        
        self.join_log_settings[server_id]["leave_message"] = message
        self.save_join_log_settings()

        embed = discord.Embed(
            title="Leave Message Set",
            description=f"{message} {ctx.author.mention}",
            color=discord.Color.red()
        )
        await ctx.send("Custom leave message has been set.", embed=embed)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        server_id = str(member.guild.id)
        if server_id in self.join_log_settings:
            channel_id = self.join_log_settings[server_id].get("channel_id")
            welcome_message = self.join_log_settings[server_id].get(
                "welcome_message",
                f"hi {member.mention}",
            )
            channel = self.bot.get_channel(channel_id)
            
            if channel:
                await channel.send(f"{welcome_message} {member.mention}")

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        server_id = str(member.guild.id)
        if server_id in self.join_log_settings:
            channel_id = self.join_log_settings[server_id].get("channel_id")
            leave_message = self.join_log_settings[server_id].get(
                "leave_message",
                f"damn, {member.mention} left, they prolly wont be back",
            )
            channel = self.bot.get_channel(channel_id)
            
            if channel:
                await channel.send(f"{leave_message} {member.mention}")

    @app_commands.command(name="testmsg")
    @commands.has_permissions(administrator=True)
    @app_commands.choices(
        message_type=[
            app_commands.Choice(name="join", value="join"),
            app_commands.Choice(name="leave", value="leave"),
        ]
    )
    async def test_message(self, interaction: discord.Interaction, message_type: app_commands.Choice[str]):
        """Tests the join or leave message using the command author as the member."""
        server_id = str(interaction.guild_id)
        if server_id not in self.join_log_settings:
            await interaction.response.send_message("Join log settings are not configured for this server.", ephemeral=True)
            return

        channel_id = self.join_log_settings[server_id].get("channel_id")
        channel = self.bot.get_channel(channel_id)
        if not channel:
            await interaction.response.send_message("The join log channel is not set or accessible.", ephemeral=True)
            return

        if message_type.value == "join":
            welcome_message = self.join_log_settings[server_id].get(
                "welcome_message",
                "hi",
            )
            await channel.send(f"{welcome_message} {interaction.user.mention}")
            await interaction.response.send_message("Join message tested.", ephemeral=True)
        elif message_type.value == "leave":
            leave_message = self.join_log_settings[server_id].get(
                "leave_message",
                "damn, they prolly wont be back",
            )
            await channel.send(f"{leave_message} {interaction.user.mention}")
            await interaction.response.send_message("Leave message tested.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(JoinLogCog(bot))
