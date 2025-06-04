import json
import time

from time import time

from discord import ButtonStyle, Interaction, Embed, utils, TextStyle
from discord.ui import View, Button, Modal, TextInput, button

from modules.styles import emojis, colors

class SuggestionModal(Modal):
    def __init__(self):
        super().__init__(title="Create a New Suggestion")
        self.suggestion = TextInput(label="Suggestion", placeholder="Enter your suggestion here...", style=TextStyle.long, required=True)
        self.add_item(self.suggestion)

    async def on_submit(self, interaction: Interaction):
        content = self.suggestion.value
        channel_id = await interaction.client.db.fetchval("SELECT channel_id FROM suggestions_module WHERE guild_id = $1", interaction.guild.id)
        if not channel_id:
            return await interaction.warn("Suggestion channel is not set up correctly.", ephemeral=True)
        channel = interaction.client.get_channel(channel_id)
        if not channel:
            return await interaction.warn("Suggestion channel not found or bot lacks permissions to access it.", ephemeral=True)
        embed = Embed(title="💡 New Suggestion", color=colors.WARNING)
        embed.set_author(name=f"{interaction.user.name} ({interaction.user.id})", icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.add_field(name="> Suggestion", value=f'```{content}```', inline=False)
        embed.add_field(name="> Upvotes", value="```0```", inline=True)
        embed.add_field(name="> Downvotes", value="```0```", inline=True)
        embed.set_footer(text=f'{interaction.user.name} - Use ;suggest for suggestions', icon_url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
        embed.timestamp = utils.utcnow()
        message = await channel.send(embed=embed, view=SuggestionView())
        await interaction.client.db.execute("INSERT INTO suggestions (guild_id, channel_id, message_id, author_id, content) VALUES ($1, $2, $3, $4, $5)", interaction.guild.id, interaction.channel.id, message.id, interaction.user.id, content)
        thread_enabled = await interaction.client.db.fetchval("SELECT threads FROM suggestions_module WHERE guild_id = $1", interaction.guild.id)
        if thread_enabled:
            try:
                await message.create_thread(name=f"Discussion for Suggestion from {interaction.user.name}", auto_archive_duration=10080)
            except:
                pass
        await interaction.approve(f'Your [**suggestion**]({message.jump_url}) has been submitted!', ephemeral=True)

class SuggestionView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.last_update_times = {}

    async def handle_vote(self, interaction: Interaction, vote_type: str):
        await interaction.response.defer(ephemeral=True)
        suggestion = await interaction.client.db.fetchrow("SELECT author_id, content, upvotes, downvotes FROM suggestions WHERE message_id = $1", interaction.message.id)
        if not suggestion:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: This suggestion is no longer available")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        upvotes = set(json.loads(suggestion["upvotes"]))
        downvotes = set(json.loads(suggestion["downvotes"]))
        user_id = interaction.user.id
        if user_id in upvotes and vote_type == "upvote":
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You have already **upvoted** this suggestion.")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if user_id in downvotes and vote_type == "downvote":
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You have already **downvoted** this suggestion.")
            return await interaction.followup.send(embed=embed, ephemeral=True)
        if vote_type == "upvote":
            if user_id in downvotes:
                downvotes.remove(user_id)
            upvotes.add(user_id)
        elif vote_type == "downvote":
            if user_id in upvotes:
                upvotes.remove(user_id)
            downvotes.add(user_id)
        await interaction.client.db.execute(
            "UPDATE suggestions SET upvotes = $1, downvotes = $2 WHERE message_id = $3",
            json.dumps(list(upvotes)), json.dumps(list(downvotes)), interaction.message.id
        )
        current_time = time()
        last_update_time = self.last_update_times.get(interaction.message.id, 0)
        if current_time - last_update_time >= 10:
            self.last_update_times[interaction.message.id] = current_time
            author = interaction.client.get_user(suggestion["author_id"])
            if author is None:
                author = await interaction.client.fetch_user(suggestion["author_id"])
            embed = interaction.message.embeds[0]
            embed.clear_fields()
            embed.set_author(name=f"{author.name} ({author.id})", icon_url=author.avatar.url if author.avatar else author.default_avatar.url)
            embed.add_field(name="> Suggestion", value=f'```{suggestion["content"]}```', inline=False)
            embed.add_field(name="> Upvotes", value=f'```{len(upvotes)}```', inline=True)
            embed.add_field(name="> Downvotes", value=f'```{len(downvotes)}```', inline=True)
            embed.set_footer(text=f'{author.name} - Use ;suggest for suggestions', icon_url=author.avatar.url if author.avatar else author.default_avatar.url)
            embed.set_thumbnail(url=author.avatar.url if author.avatar else author.default_avatar.url)
            embed.timestamp = interaction.message.created_at
            await interaction.message.edit(embed=embed)
        note = ''
        if current_time - last_update_time <= 10:
            note = "(Message will not update instant, because ratelimit)"
        embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Your **{vote_type}** has been recorded {note}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @button(label="Upvote", style=ButtonStyle.green, custom_id="persistent:upvote_suggestion")
    async def upvote_suggestion(self, interaction: Interaction, button: Button):
        await self.handle_vote(interaction, "upvote")

    @button(label="Downvote", style=ButtonStyle.red, custom_id="persistent:downvote_suggestion")
    async def downvote_suggestion(self, interaction: Interaction, button: Button):
        await self.handle_vote(interaction, "downvote")

    @button(label="Create Suggestion", style=ButtonStyle.blurple, custom_id="persistent:create_suggestion")
    async def create_suggestion(self, interaction: Interaction, button: Button):
        check = await interaction.client.db.fetchrow("SELECT suggestion FROM modules WHERE guild_id = $1", interaction.guild.id)
        if not check or check['suggestion'] is False:
            await interaction.warn(f"Suggestion module is **not** enabled", ephemeral=True)
        check = await interaction.client.db.fetchrow("SELECT reason FROM suggestions_blacklist WHERE guild_id = $1 AND user_id = $2", interaction.guild.id, interaction.user.id)
        if check:
            await interaction.warn(f"You got blacklisted from creating suggestion.\n> **Reason:** {check['reason']}", ephemeral=True)
        modal = SuggestionModal()
        await interaction.response.send_modal(modal)