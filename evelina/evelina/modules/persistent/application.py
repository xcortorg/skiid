import json

from discord import Embed, Interaction, ButtonStyle, Button, TextStyle
from discord.ui import View, Modal, TextInput, button

from modules.styles import emojis, colors

class ApplicationModerationModal(Modal):
    def __init__(self, action: str, callback):
        super().__init__(title=f"{action} Application")
        self.action = action
        self.callback = callback
        self.reason = TextInput(label="Reason", style=TextStyle.paragraph, required=True, max_length=1024)
        self.add_item(self.reason)

    async def on_submit(self, interaction: Interaction):
        await self.callback(interaction, self.reason.value)

class ApplicationModerationView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Accept", style=ButtonStyle.success, custom_id="persistent:accept")
    async def accept(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(ApplicationModerationModal("Accept", self.process_accept))

    @button(label="Reject", style=ButtonStyle.danger, custom_id="persistent:reject")
    async def reject(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(ApplicationModerationModal("Reject", self.process_reject))

    @button(label="👍 0", style=ButtonStyle.secondary, custom_id="persistent:upvote")
    async def upvote(self, interaction: Interaction, button: Button):
        await self.handle_vote(interaction, vote=1)

    @button(label="👎 0", style=ButtonStyle.secondary, custom_id="persistent:downvote")
    async def downvote(self, interaction: Interaction, button: Button):
        await self.handle_vote(interaction, vote=-1)


    async def process_accept(self, interaction: Interaction, reason: str):
        response = await self.bot.db.fetchrow("SELECT * FROM application_responses WHERE id = $1", interaction.message.id)
        if not response:
            return await interaction.warn("Application not found.", ephemeral=True)
        response_application = await self.bot.db.fetchrow("SELECT * FROM applications WHERE name = $1 AND guild_id = $2", response["application_name"], interaction.guild.id)
        if not response_application:
            return await interaction.warn("Application not found.", ephemeral=True)
        user = interaction.guild.get_member(response["user_id"])
        if not user:
            return await interaction.warn("User not found.", ephemeral=True)
        roles = response_application["roles"]
        if isinstance(roles, str):
            try:
                roles = json.loads(roles)
            except json.JSONDecodeError:
                roles = []
        if not isinstance(roles, list):
            roles = []
        for role_id in roles:
            if not role_id.isdigit():
                continue
            role = interaction.guild.get_role(int(role_id))
            if role:
                try:
                    await user.add_roles(role, reason=f"Application for {response['application_name']}")
                except Exception:
                    continue
        await interaction.approve(f"Application from {user.mention} for `{response['application_name']}` has been accepted. Reason:\n```{reason}```")
        for button in self.children:
            button.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        try:
            embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {user.mention}: Your application for `{response['application_name']}` has been accepted. Reason:\n```{reason}```")
            await user.send(embed=embed)
        except:
            pass

    async def process_reject(self, interaction: Interaction, reason: str):
        message = await interaction.channel.fetch_message(interaction.message.id)
        response = await self.bot.db.fetchrow("SELECT * FROM application_responses WHERE id = $1", message.id)
        if not response:
            return await interaction.warn("Application not found.", ephemeral=True)
        user = await interaction.client.fetch_user(response["user_id"])
        if not user:
            return await interaction.warn("User not found.", ephemeral=True)
        await interaction.approve(f"Application from {user.mention} for `{response['application_name']}` has been rejected. Reason:\n```{reason}```")
        for button in self.children:
            button.disabled = True
        await interaction.followup.edit_message(message_id=interaction.message.id, view=self)
        try:
            embed = Embed(color=colors.ERROR, description=f"{emojis.DENY} {user.mention}: Your application for `{response['application_name']}` has been rejected. Reason:\n```{reason}```")
            await user.send(embed=embed)
        except:
            pass

    async def handle_vote(self, interaction: Interaction, vote: int):
        message_id = interaction.message.id
        user_id = interaction.user.id
        current_vote = await self.bot.db.fetchval("SELECT vote FROM application_votes WHERE message_id = $1 AND user_id = $2", message_id, user_id)
        if current_vote == vote:
            await self.bot.db.execute("DELETE FROM application_votes WHERE message_id = $1 AND user_id = $2", message_id, user_id)
            if vote == 1:
                await self.bot.db.execute("UPDATE application_responses SET upvotes = upvotes - 1 WHERE id = $1", message_id)
            else:
                await self.bot.db.execute("UPDATE application_responses SET downvotes = downvotes - 1 WHERE id = $1", message_id)
        else:
            if current_vote is not None:
                if current_vote == 1:
                    await self.bot.db.execute("UPDATE application_responses SET upvotes = upvotes - 1 WHERE id = $1", message_id)
                else:
                    await self.bot.db.execute("UPDATE application_responses SET downvotes = downvotes - 1 WHERE id = $1", message_id)
            await self.bot.db.execute(
                "INSERT INTO application_votes (message_id, user_id, vote) VALUES ($1, $2, $3) "
                "ON CONFLICT (message_id, user_id) DO UPDATE SET vote = EXCLUDED.vote",
                message_id, user_id, vote
            )
            if vote == 1:
                await self.bot.db.execute("UPDATE application_responses SET upvotes = upvotes + 1 WHERE id = $1", message_id)
            else:
                await self.bot.db.execute("UPDATE application_responses SET downvotes = downvotes + 1 WHERE id = $1", message_id)
        counts = await self.bot.db.fetchrow("SELECT upvotes, downvotes FROM application_responses WHERE id = $1", message_id)
        for child in self.children:
            if child.custom_id == "persistent:upvote":
                child.label = f"👍 {counts['upvotes']}"
            elif child.custom_id == "persistent:downvote":
                child.label = f"👎 {counts['downvotes']}"
        await interaction.response.edit_message(view=self)