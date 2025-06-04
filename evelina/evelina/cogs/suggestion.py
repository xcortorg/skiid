import discord

from discord import TextStyle, Interaction, Embed, TextChannel, Role
from discord.ui import Modal, TextInput, View, Button
from discord.ext.commands import Cog, has_guild_permissions, command, group

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.predicates import suggestion_blacklisted, suggestion_enabled, suggestion_disabled
from modules.persistent.suggestion import SuggestionView

class Suggestion(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="suggestion", brief="Manage guild", invoke_without_command=True, case_insensitive=True)
    async def suggestion(self, ctx: EvelinaContext):
        """Suggestion commands"""
        return await ctx.create_pages()

    @suggestion.command(name="enable", brief="Manage guild")
    @has_guild_permissions(manage_guild=True)
    @suggestion_disabled()
    async def suggestions_enable(self, ctx: EvelinaContext):
        """Enable the suggestion module"""
        await self.bot.db.execute("INSERT INTO modules (guild_id, suggestion) VALUES ($1, TRUE) ON CONFLICT (guild_id) DO UPDATE SET suggestion = TRUE", ctx.guild.id)
        await ctx.send_success("Suggestion module has been **enabled** for this server")

    @suggestion.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @suggestion_enabled()
    async def suggestions_disable(self, ctx: EvelinaContext):
        """Disable the suggestion module"""
        async def yes_callback(interaction: Interaction) -> None:
            await interaction.client.db.execute("INSERT INTO modules (guild_id, suggestion) VALUES ($1, FALSE) ON CONFLICT (guild_id) DO UPDATE SET suggestion = FALSE", interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Suggestion module has been **disabled** in this server"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Suggestion deactivation got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **disable** suggestion", yes_callback, no_callback)

    @suggestion.command(name="channel", brief="Manage guild", usage="suggestion channel #suggestions")
    @has_guild_permissions(manage_guild=True)
    @suggestion_enabled()
    async def suggestions_channel(self, ctx: EvelinaContext, channel: TextChannel):
        """Set the suggestion channel"""
        await self.bot.db.execute("INSERT INTO suggestions_module (guild_id, channel_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET channel_id = $2", ctx.guild.id, channel.id)
        await ctx.send_success(f"Suggestion channel has been set to {channel.mention}")

    @suggestion.command(name="role", brief="Manage guild", usage="suggestion role @Suggestion Manager")
    @has_guild_permissions(manage_guild=True)
    @suggestion_enabled()
    async def suggestions_role(self, ctx: EvelinaContext, role: Role):
        """Set the suggestion role"""
        await self.bot.db.execute("INSERT INTO suggestions_module (guild_id, role_id) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET role_id = $2", ctx.guild.id, role.id)
        await ctx.send_success(f"Suggestion role has been set to {role.mention}")

    @suggestion.command(name="blacklist", brief="Manage guild", usage="suggestion blacklist comminate Spamming")
    @has_guild_permissions(manage_guild=True)
    @suggestion_enabled()
    async def suggestions_blacklist(self, ctx: EvelinaContext, user: discord.User, *, reason: str):
        """Blacklist a member from creating suggestions"""
        if user.id in self.bot.owner_ids:
            return await ctx.send_warning("Don't blacklist a bot owner, are you sure?")
        try:
            await self.bot.db.execute("INSERT INTO suggestions_blacklist (guild_id, user_id, reason) VALUES ($1, $2, $3)", ctx.guild.id, user.id, reason)
            await ctx.send_success(f"Blacklisted {user.mention} from creating suggestions for reason: **{reason}**")
        except Exception:
            await ctx.send_warning(f"User {user.mention} is **already** blacklisted from creating suggestions")
        
    @suggestion.command(name="unblacklist", brief="Manage guild", usage="suggestion unblacklist comminate")
    @has_guild_permissions(manage_guild=True)
    @suggestion_enabled()
    async def suggestions_unblacklist(self, ctx: EvelinaContext, user: discord.User):
        """Unblacklist a member from creating suggestions"""
        if user.id in self.bot.owner_ids:
            return await ctx.send_warning("Don't unblacklist a bot owner, are you sure?")
        try:
            result = await self.bot.db.fetchval("SELECT COUNT(*) FROM suggestions_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
            if result == 0:
                return await ctx.send_warning(f"{user.mention} isn't blacklisted from creating suggestions")
            await self.bot.db.execute("DELETE FROM suggestions_blacklist WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
            await ctx.send_success(f"Unblacklisted {user.mention} from creating suggestions")
        except Exception:
            await ctx.send_warning(f"User {user.mention} is **not** blacklisted from creating suggestions")
        
    @suggestion.command(name="blacklisted", brief="Manage guild")
    @has_guild_permissions(manage_guild=True)
    @suggestion_enabled()
    async def suggestions_blacklisted(self, ctx: EvelinaContext):
        """List all blacklisted users from creating suggestions"""
        results = await self.bot.db.fetch("SELECT user_id, reason FROM suggestions_blacklist WHERE guild_id = $1", ctx.guild.id)
        to_show = [f"**{self.bot.get_user(check['user_id'])}** (`{check['user_id']}`)\n{emojis.REPLY} **Reason:** {check['reason']}" for check in results]
        if to_show:
            await ctx.paginate(to_show, f"Suggestion Blacklisted", {"name": ctx.author, "icon_url": ctx.author.avatar.url})
        else:
            await ctx.send_warning("No suggestion blacklisted user found")

    @suggestion.command(name="thread", brief="Manage guild")
    @has_guild_permissions(manage_guild=True)
    @suggestion_enabled()
    async def suggestions_thread(self, ctx: EvelinaContext):
        """Enable/Disable thread creation for suggestions"""
        module_settings = await self.bot.db.fetchrow("SELECT threads FROM suggestions_module WHERE guild_id = $1", ctx.guild.id)
        if module_settings is None:
            await ctx.send_warning("Suggestions module is not configured for this server.")
            return
        thread_enabled = module_settings["threads"]
        if thread_enabled:
            await self.bot.db.execute("UPDATE suggestions_module SET threads = FALSE WHERE guild_id = $1", ctx.guild.id)
            await ctx.send_success("Thread creation for suggestions has been **disabled**")
        else:
            await self.bot.db.execute("UPDATE suggestions_module SET threads = TRUE WHERE guild_id = $1", ctx.guild.id)
            await ctx.send_success("Thread creation for suggestions has been **enabled**")

    @command(name="suggest", usage="suggest Add ... to the bot")
    @suggestion_blacklisted()
    @suggestion_enabled()
    async def suggest(self, ctx: EvelinaContext, *, content: str):
        """Submit a suggestion"""
        module_settings = await self.bot.db.fetchrow("SELECT channel_id, role_id FROM suggestions_module WHERE guild_id = $1", ctx.guild.id)
        if not module_settings or not module_settings["channel_id"] or not module_settings["role_id"]:
            return await ctx.send_warning(f"Suggestion settings are not properly configured for this server.\n> Be sure you setuped `{ctx.clean_prefix}suggestion channel` & `{ctx.clean_prefix}suggestion role`")
        channel = self.bot.get_channel(module_settings["channel_id"])
        if not channel:
            return await ctx.send_warning("Suggestion channel not found or bot lacks permissions to access it.")
        embed = discord.Embed(title="💡 New Suggestion", color=colors.WARNING)
        embed.set_author(name=f"{ctx.author.name} ({ctx.author.id})", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.add_field(name="> Suggestion", value=f"```{content}```", inline=False)
        embed.add_field(name="> Upvotes", value="```0```", inline=True)
        embed.add_field(name="> Downvotes", value="```0```", inline=True)
        embed.set_footer(text=f"{ctx.author.name} - Use ;suggest for suggestions", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.timestamp = ctx.message.created_at
        view = SuggestionView()
        message = await channel.send(embed=embed, view=view)
        await self.bot.db.execute("INSERT INTO suggestions (guild_id, channel_id, message_id, author_id, content) VALUES ($1, $2, $3, $4, $5)", ctx.guild.id, message.channel.id, message.id, ctx.author.id, content)
        thread_enabled = await self.bot.db.fetchval("SELECT threads FROM suggestions_module WHERE guild_id = $1", ctx.guild.id)
        if thread_enabled:
            try:
                await message.create_thread(name=f"Discussion for Suggestion from {ctx.author.name}", auto_archive_duration=10080)
            except:
                pass
        await ctx.send_success(f"Your [**suggestion**]({message.jump_url}) has been submitted!")
        try:
            await ctx.message.delete()
        except:
            pass

    async def handle_decision(self, interaction: discord.Interaction, message: discord.Message, decision_type: str):
        guild_id = interaction.guild.id
        module_settings = await self.bot.db.fetchrow("SELECT role_id FROM suggestions_module WHERE guild_id = $1", guild_id)
        if not module_settings:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Suggestion settings not configured for this server.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        required_role_id = module_settings["role_id"]
        if required_role_id and not interaction.user.get_role(required_role_id):
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You do not have the required role to manage this suggestion.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        suggestion = await self.bot.db.fetchrow("SELECT * FROM suggestions WHERE message_id = $1", message.id)
        if not suggestion:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't find the suggestion in the database")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        modal = DecisionModal(bot=self.bot, message_id=message.id, decision_type=decision_type)
        await interaction.response.send_modal(modal)

    async def handle_decision_logic(self, interaction: discord.Interaction, suggestion_id: int, decision_type: str, reason: str = "N/A"):
        await interaction.response.defer(ephemeral=True)
        suggestion = await self.bot.db.fetchrow("SELECT * FROM suggestions WHERE message_id = $1", suggestion_id)
        if not suggestion:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't find the suggestion in the database")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        channel = interaction.client.get_channel(suggestion["channel_id"])
        if not channel:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't find the channel for the suggestion")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            message = await channel.fetch_message(suggestion_id)
        except discord.NotFound:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: Couldn't find the suggestion message in the channel. It may have been deleted")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        except discord.Forbidden:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: I don't have permission to access the message in this channel")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if message.embeds:
            embed = message.embeds[0]
            embed.color = colors.SUCCESS if decision_type.lower() == "accept" else colors.ERROR
            embed.description = f"**Status:** `{decision_type.capitalize()}ed` **Moderator:** {interaction.user.mention}\n> **Reason:**\n```{reason}```"
            await message.edit(embed=embed, view=None)
        else:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: The suggestion message does not have an embed to update")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        try:
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Suggestion has been **{decision_type.lower()}ed**")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception:
            pass
        try:
            suggested_user = await interaction.client.fetch_user(suggestion["author_id"])
            embed = discord.Embed(description=f"💡 {suggested_user.mention}: Your suggestion got **{decision_type}ed** in reason of **{reason}**", color=colors.SUCCESS if decision_type.lower() == "accept" else colors.ERROR)
            view = View()
            view.add_item(Button(label="View Suggestion", style=discord.ButtonStyle.link, url=message.jump_url))
            return await suggested_user.send(embed=embed, view=view)
        except Exception:
            pass

class DecisionModal(Modal):
    def __init__(self, bot, message_id, decision_type):
        super().__init__(title=f"{decision_type.capitalize()} Suggestion")
        self.bot = bot
        self.message_id = message_id
        self.decision_type = decision_type
        self.reason = TextInput(label="Reason", placeholder="Enter the reason for your decision...", style=TextStyle.long, required=False)
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction):
        reason = self.reason.value or "N/A"
        await self.bot.get_cog("Suggestion").handle_decision_logic(interaction, self.message_id, self.decision_type, reason)

async def setup(bot: Evelina) -> None:
    await bot.add_cog(Suggestion(bot))