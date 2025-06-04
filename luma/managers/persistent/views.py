import discord


class ConfirmView(discord.ui.View):
    def __init__(self, author_id: int, button1, button2):
        self.author_id = author_id
        self.yes = button1
        self.no = button2
        super().__init__(timeout=30)

    async def interaction_check(self, interaction: discord.Interaction):
        if self.author_id != interaction.user.id:
            await interaction.error("This is not your message")

        return self.author_id == interaction.user.id

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
    async def button1(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.yes(interaction)

    @discord.ui.button(label="No", style=discord.ButtonStyle.red)
    async def button2(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await self.no(interaction)
