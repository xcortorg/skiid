from discord import ButtonStyle, Interaction
from discord.ui import View, Button, button

class InviteView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @button(label="Accept", style=ButtonStyle.green, custom_id="persistent:accept_invite")
    async def accept_invite(self, interaction: Interaction, button: Button):
        data = await interaction.client.db.fetchrow("SELECT * FROM company_invites WHERE message_id = $1", interaction.message.id)
        if not data:
            if interaction.response.is_done():
                await interaction.followup.edit_message(interaction.message.id, view=None)
            else:
                await interaction.message.edit(view=None)
            return await interaction.warn("This invite has expired.", ephemeral=False)
        user_company = await interaction.client.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", interaction.user.id)
        if user_company:
            if user_company and user_company['id'] == data['company_id']:
                if interaction.response.is_done():
                    await interaction.followup.edit_message(interaction.message.id, view=None)
                else:
                    await interaction.message.edit(view=None)
                return await interaction.warn("You are already in this company.", ephemeral=False)
            else:
                if interaction.response.is_done():
                    await interaction.followup.edit_message(interaction.message.id, view=None)
                else:
                    await interaction.message.edit(view=None)
                return await interaction.warn("You are already in a company.", ephemeral=False)
        company = await interaction.client.db.fetchrow("SELECT * FROM company WHERE id = $1", data['company_id'])
        limit = await interaction.client.db.fetchrow("SELECT * FROM company_upgrades WHERE level = $1", company['level'])
        if len(company['members']) >= limit['members']:
            if interaction.response.is_done():
                await interaction.followup.edit_message(interaction.message.id, view=None)
            else:
                await interaction.message.edit(view=None)
            return await interaction.warn(f"The company is already at the maximum member limit of **{limit['members']}**", ephemeral=True)
        await interaction.client.db.execute("DELETE FROM company_invites WHERE message_id = $1", interaction.message.id)
        await interaction.client.db.execute("UPDATE company SET members = array_append(members, $1) WHERE id = $2", interaction.user.id, company['id'])
        if interaction.response.is_done():
            await interaction.followup.edit_message(interaction.message.id, view=None)
        else:
            await interaction.message.edit(view=None)
        return await interaction.approve(f"Accepted the company invite.", ephemeral=False)

    @button(label="Decline", style=ButtonStyle.red, custom_id="persistent:decline_invite")
    async def decline_invite(self, interaction: Interaction, button: Button):
        await interaction.client.db.execute("DELETE FROM company_invites WHERE message_id = $1", interaction.message.id)
        if interaction.response.is_done():
            await interaction.followup.edit_message(interaction.message.id, view=None)
        else:
            await interaction.message.edit(view=None)
        return await interaction.approve(f"Declined the company invite.", ephemeral=False)