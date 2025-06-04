from discord import ButtonStyle, Interaction
from discord.ui import View, Button, button

class FeedbackView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Approve", style=ButtonStyle.green, custom_id="persistent:feedback_approve")
    async def feedback_approve(self, interaction: Interaction, button: Button):
        check = await self.bot.db.fetchrow("SELECT * FROM testimonials WHERE message_id = $1", interaction.message.id)
        if not check:
            return await interaction.warn("This feedback message has already been approved or denied.", ephemeral=True)
        await self.bot.db.execute("UPDATE testimonials SET approved = True WHERE message_id = $1", interaction.message.id)
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        return await interaction.approve("Feedback message has been approved.", ephemeral=True)
                                           
    @button(label="Deny", style=ButtonStyle.danger, custom_id="persistent:feedback_deny")
    async def feedback_deny(self, interaction: Interaction, button: Button):
        check = await self.bot.db.fetchrow("SELECT * FROM testimonials WHERE message_id = $1", interaction.message.id)
        if not check:
            return await interaction.warn("This feedback message has already been approved or denied.", ephemeral=True)
        await self.bot.db.execute("DELETE FROM testimonials WHERE message_id = $1", interaction.message.id)
        for child in self.children:
            child.disabled = True
        await interaction.message.edit(view=self)
        return await interaction.approve("Feedback message has been denied.", ephemeral=True)