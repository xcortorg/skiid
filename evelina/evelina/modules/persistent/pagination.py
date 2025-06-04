import time

from discord import ButtonStyle, Interaction, Embed
from discord.ui import View, button

from modules.styles import emojis, colors
from modules.handlers.embed import EmbedScript

class PaginationView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.last_interaction = {}

    async def get_current_page(self, interaction: Interaction, message_id):
        query = "SELECT current_page FROM paginate_data WHERE message_id = $1"
        record = await interaction.client.db.fetchrow(query, message_id)
        return record["current_page"] if record else 0

    async def fetch_embed(self, interaction: Interaction, guild_id, channel_id, message_id, page):
        embed = await interaction.client.db.fetchval("SELECT embed FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND page = $4", guild_id, channel_id, message_id, page)
        return embed

    async def set_current_page(self, interaction: Interaction, message_id, page):
        query = """
        INSERT INTO paginate_data (message_id, current_page)
        VALUES ($1, $2)
        ON CONFLICT (message_id) DO UPDATE SET current_page = $2
        """
        await interaction.client.db.execute(query, message_id, page)

    async def handle_page_change(self, interaction: Interaction, change: int):
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        message_id = interaction.message.id
        user_id = interaction.user.id
        now = time.time()
        last_time = self.last_interaction.get(user_id, 0)
        if now - last_time < 2:
            embed = Embed(color=colors.WARNING, description=f"{emojis.WARNING} {interaction.user.mention}: You are too fast, please wait a little bit...")
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        self.last_interaction[user_id] = now
        current_page = await self.get_current_page(interaction, message_id)
        total_pages = await interaction.client.db.fetchval("SELECT COUNT(*) FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", guild_id, channel_id, message_id)
        next_page = current_page + change
        if next_page < 1:
            next_page = total_pages
        elif next_page > total_pages:
            next_page = 1
        embed = await self.fetch_embed(interaction, guild_id, channel_id, message_id, next_page)
        await self.set_current_page(interaction, message_id, next_page)
        embed_script = await EmbedScript().old_convert(interaction.user, embed)
        embed_script.pop('view', None)
        await interaction.response.defer()
        await interaction.message.edit(**embed_script, view=self)

    @button(emoji=emojis.LEFT, style=ButtonStyle.primary, custom_id="persistent:pagination_previous")
    async def previous_page(self, interaction: Interaction, button):
        await self.handle_page_change(interaction, change=-1)

    @button(emoji=emojis.RIGHT, style=ButtonStyle.primary, custom_id="persistent:pagination_next")
    async def next_page(self, interaction: Interaction, button):
        await self.handle_page_change(interaction, change=1)