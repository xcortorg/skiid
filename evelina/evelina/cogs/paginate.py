from discord.ext.commands import Cog, group, has_guild_permissions

from discord import Embed, Interaction

from modules.styles import emojis, colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidMessage
from modules.handlers.embed import EmbedScript
from modules.persistent.pagination import PaginationView

class Paginate(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Paginate commands"

    async def fetch_embed(self, guild_id, channel_id, message_id, page):
        embed = await self.bot.db.fetchval("SELECT embed FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND page = $4", guild_id, channel_id, message_id, page)
        return embed

    async def get_current_page(self, message_id):
        query = "SELECT current_page FROM paginate_data WHERE message_id = $1"
        record = await self.bot.db.fetchrow(query, message_id)
        return record['current_page'] if record else 0

    async def set_current_page(self, message_id, page):
        query = """
        INSERT INTO paginate_data (message_id, current_page)
        VALUES ($1, $2)
        ON CONFLICT (message_id) DO UPDATE SET current_page = $2
        """
        await self.bot.db.execute(query, message_id, page)

    @group(name="paginate", invoke_without_command=True)
    async def paginate(self, ctx: EvelinaContext):
        """Create and manage paginated messages"""
        return await ctx.create_pages()

    @paginate.command(name="create", brief="manage messages", usage="paginate create {embed}$v{description: Hello world}")
    @has_guild_permissions(manage_messages=True)
    async def paginate_create(self, ctx: EvelinaContext, *, embed: str):
        """Creates a new paginated message starting with the first page"""
        view = PaginationView()
        embed_script = await EmbedScript.convert(self, ctx, embed)
        embed_script.pop('view', None)
        message = await ctx.send(**embed_script, view=view)
        await message.edit(view=view)
        await self.bot.db.execute("INSERT INTO paginate_embeds (guild_id, channel_id, message_id, embed, page) VALUES ($1, $2, $3, $4, $5)", message.guild.id, message.channel.id, message.id, embed, 1)
        await self.bot.db.execute("INSERT INTO paginate_data (message_id, current_page) VALUES ($1, 1)", message.id)

    @paginate.command(name="add", brief="manage messages", usage="paginate add .../channels/... {embed}$v{description: Hello world}")
    @has_guild_permissions(manage_messages=True)
    async def paginate_add(self, ctx: EvelinaContext, message: ValidMessage, *, embed: str):
        """Adds an embed to the next available page without gaps"""
        embed_script = await EmbedScript.convert(self, ctx, embed)
        embed_script.pop('view', None)
        existing_pages = await self.bot.db.fetch("SELECT page FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 ORDER BY page", message.guild.id, message.channel.id, message.id)
        page_number = len(existing_pages) + 1
        await self.bot.db.execute("INSERT INTO paginate_embeds (guild_id, channel_id, message_id, embed, page) VALUES ($1, $2, $3, $4, $5)", message.guild.id, message.channel.id, message.id, embed, page_number)
        await ctx.send_success(f"Embed added to **page {page_number}** for message {message.jump_url}")

    @paginate.command(name="remove", brief="manage messages", usage="paginate remove .../channels/... 3")
    @has_guild_permissions(manage_messages=True)
    async def paginate_remove(self, ctx: EvelinaContext, message: ValidMessage, page: int):
        """Removes an embed from a specified page, shifting pages to close gaps"""
        result = await self.bot.db.execute("DELETE FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND page = $4", message.guild.id, message.channel.id, message.id, page)
        if result == "DELETE 1":
            await self.bot.db.execute("UPDATE paginate_embeds SET page = page - 1 WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND page > $4", message.guild.id, message.channel.id, message.id, page)
            current_page = await self.get_current_page(message.id)
            if current_page >= page:
                new_current_page = max(1, current_page - 1)
                await self.set_current_page(message.id, new_current_page)
            await ctx.send_success(f"Removed **page {page}** for message {message.jump_url}")
        else:
            await ctx.send_warning(f"No **page {page}** found for message {message.id}")

    @paginate.command(name="edit", brief="manage messages", usage="paginate edit .../channels/... 3 {embed}$v{description: Hello world}")
    @has_guild_permissions(manage_messages=True)
    async def paginate_edit(self, ctx: EvelinaContext, message: ValidMessage, page: int, *, embed: str):
        """Edits an embed on a specified page"""
        result = await self.bot.db.execute("UPDATE paginate_embeds SET embed = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4 AND page = $5", embed, message.guild.id, message.channel.id, message.id, page)
        if result == "UPDATE 1":
            await ctx.send_success(f"Edited **page {page}** for message {message.jump_url}")
        else:
            await ctx.send_warning(f"No **page {page}** found for message {message.id}")

    @paginate.command(name="move", brief="manage messages", usage="paginate move .../channels/... 3 5")
    @has_guild_permissions(manage_messages=True)
    async def paginate_move(self, ctx: EvelinaContext, message: ValidMessage, page: int, new: int):
        """Swaps the embeds between two pages"""
        embed1 = await self.bot.db.fetchval("SELECT embed FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND page = $4", message.guild.id, message.channel.id, message.id, page)
        embed2 = await self.bot.db.fetchval("SELECT embed FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND page = $4", message.guild.id, message.channel.id, message.id, new)
        if embed1 is None or embed2 is None:
            await ctx.send_warning(f"One of the pages {page} or {new} does not exist for message {message.id}")
            return
        await self.bot.db.execute("UPDATE paginate_embeds SET embed = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4 AND page = $5", embed2, message.guild.id, message.channel.id, message.id, page)
        await self.bot.db.execute("UPDATE paginate_embeds SET embed = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4 AND page = $5", embed1, message.guild.id, message.channel.id, message.id, new)
        await ctx.send_success(f"Swapped **page {page}** with **page {new}** for message {message.jump_url}")

    @paginate.command(name="list", brief="manage messages", usage="paginate list")
    @has_guild_permissions(manage_messages=True)
    async def paginate_list(self, ctx: EvelinaContext):
        """Lists all paginated messages in the guild"""
        messages = await self.bot.db.fetch("SELECT message_id, channel_id FROM paginate_embeds WHERE guild_id = $1", ctx.guild.id)
        if not messages:
            return await ctx.send_warning("No paginated messages found")
        to_show = []
        for message in messages:
            message_link = f"https://discord.com/channels/{ctx.guild.id}/{message['channel_id']}/{message['message_id']}"
            to_show.append(f"[`{message['message_id']}`]({message_link}) - **{len(messages)} pages**")
        await ctx.paginate(to_show, title="Paginated Messages")

    @paginate.command(name="clear", brief="manage messages", usage="paginate clear .../channels/...")
    @has_guild_permissions(manage_messages=True)
    async def paginate_clear(self, ctx: EvelinaContext, message: ValidMessage):
        """Removes all embeds from a message"""
        async def yes_callback(interaction: Interaction) -> None:
            await self.bot.db.execute("DELETE FROM paginate_embeds WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3", message.guild.id, message.channel.id, message.id)
            await self.bot.db.execute("DELETE FROM paginate_data WHERE message_id = $1", message.id)
            return await interaction.response.edit_message(
                embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Cleared all pages for [message]({message.jump_url})"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(
                embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Message clearing canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to clear all pages for [this message]({message.jump_url})?", yes_callback, no_callback)

    @paginate.command(name="reset", brief="manage messages", usage="paginate reset")
    @has_guild_permissions(manage_messages=True)
    async def paginate_reset(self, ctx: EvelinaContext):
        """Removes all paginated messages"""
        async def yes_callback(interaction: Interaction) -> None:
            await self.bot.db.execute("DELETE FROM paginate_embeds WHERE guild_id = $1", ctx.guild.id)
            await self.bot.db.execute("DELETE FROM paginate_data WHERE message_id IN (SELECT message_id FROM paginate_embeds WHERE guild_id = $1)", ctx.guild.id)
            return await interaction.response.edit_message(
                embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Cleared **all** paginated messages in the guild"), view=None)
        async def no_callback(interaction: Interaction) -> None:
            return await interaction.response.edit_message(
                embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Paginated messages reset canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to reset all paginated messages in this guild?", yes_callback, no_callback)

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Paginate(bot))