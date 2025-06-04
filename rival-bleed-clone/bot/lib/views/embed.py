import discord
from lib.patch.context import Context
from discord.ext.commands import ColorConverter
from lib.classes.embed import embed_to_code
from datetime import datetime
from typing import Any, Optional
from tuuid import tuuid

class BasicModal(discord.ui.Modal):
    title_input = discord.ui.TextInput(
        label="Title",
        placeholder=".",
        style=discord.TextStyle.short,  # Single-line input
        max_length = 256,
        required=False
    )
    
    description_input = discord.ui.TextInput(
        label="Description",
        placeholder="",
        style=discord.TextStyle.paragraph,  # Multi-line input
        max_length=4000,
        required=False
    )
    
    hex_input = discord.ui.TextInput(
        label="Hex Code",
        placeholder="",
        style=discord.TextStyle.short,  # Single-line input
        required=False
    )
    
    message_input = discord.ui.TextInput(
        label="Message Content",
        placeholder="",
        style=discord.TextStyle.paragraph,  # Multi-line input
        max_length=2000,
        required=False
    )

    def __init__(self, view: discord.ui.View):
        self.view = view
        super().__init__(title="Edit Basic Information")

    async def on_submit(self, interaction: discord.Interaction):
        hex_ = self.hex_input.value
        title = self.title_input.value
        description = self.description_input.value
        message = self.message_input.value
        if hex_:
            self.view.update_item("color", await ColorConverter().convert(self.view.ctx, hex_))
        if title:
            self.view.update_item("title", title)
        if description:
            self.view.update_item("description", description)
        if message:
            self.view.update_item("content", message)
        return await self.view.update_embed(interaction)
    
class AuthorModal(discord.ui.Modal):
    author_text = discord.ui.TextInput(
        label="Author Text",
        placeholder="",
        style=discord.TextStyle.short,  # Single-line input
        max_length = 256,
        required=False
    )
    author_url = discord.ui.TextInput(
        label="Author URL",
        placeholder="",
        style=discord.TextStyle.short,  # Single-line input
        required=False
    )
    author_icon = discord.ui.TextInput(
        label="Author Image",
        placeholder="https://coffin.bot/img/test.png",
        style=discord.TextStyle.short,  # Single-line input
        max_length = 256,
        required=False
    )
    def __init__(self, view: discord.ui.View):
        self.view = view
        super().__init__(title="Edit Author")

    async def on_submit(self, interaction: discord.Interaction):
        author_text = self.author_text.value
        author_url = self.author_url.value
        author_icon = self.author_icon.value
        if author_text:
            self.view.update_item("author", author_text)
        if author_url:
            self.view.update_item("author_url", author_url)
        if author_icon:
            self.view.update_item("author_icon", author_icon)
        return await self.view.update_embed(interaction)


class FooterModal(discord.ui.Modal):
    footer_text = discord.ui.TextInput(
        label="Footer Text",
        placeholder="",
        style=discord.TextStyle.short,  # Single-line input
        max_length = 2048,
        required=False
    )
    footer_icon = discord.ui.TextInput(
        label="Footer Image",
        placeholder="https://coffin.bot/img/test.png",
        style=discord.TextStyle.short,  # Single-line input
        required=False
    )
    timestamp = discord.ui.TextInput(
        label="Timestamp (yes or no)",
        placeholder="yes",
        style=discord.TextStyle.short
    )
    def __init__(self, view: discord.ui.View):
        self.view = view
        super().__init__(title="Edit Footer")
    
    async def on_submit(self, interaction: discord.Interaction):
        footer_text = self.footer_text.value
        footer_icon = self.footer_icon.value
        timestamp = self.timestamp.value.lower() == "yes"
        if footer_text:
            self.view.update_item("footer", footer_text)
        if footer_icon:
            self.view.update_item("footer_icon", footer_icon)
        if timestamp:
            self.view.update_item("timestamp", timestamp)
        return await self.view.update_embed(interaction)
    
class ImageModal(discord.ui.Modal):
    image = discord.ui.TextInput(
        label="Image",
        placeholder="https://coffin.bot/img/test.png",
        style=discord.TextStyle.short,  # Single-line input
        required=False
    )
    thumbnail = discord.ui.TextInput(
        label="Thumbnail",
        placeholder="https://coffin.bot/img/test.png",
        style=discord.TextStyle.short,  # Single-line input
        required=False
    )
    def __init__(self, view: discord.ui.View):
        self.view = view
        super().__init__(title = "Edit Images")

    async def on_submit(self, interaction: discord.Interaction):
        image = self.image.value
        thumbnail = self.thumbnail.value
        if image:
            self.view.update_item("image", image)
        if thumbnail:
            self.view.update_item("thumbnail", thumbnail)
        return await self.view.update_embed(interaction)

class EmbedView(discord.ui.View):
    def __init__(self, ctx: Context, name: Optional[str] = tuuid()):
        self.ctx = ctx
        self.bot = self.ctx.bot
        self.name = name
        self.content = None
        self.message = None
        self.embed = discord.Embed()
        super().__init__()

    async def check_author(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.fail("you are not the author of this embed")
            return False
        return True
    
    def update_item(self, item: str, value: Any):
        if item == "title":
            self.embed.title = value
        elif item == "description":
            self.embed.description = value
        elif item == "url":
            self.embed.url = value
        elif item == "timestamp":
            self.embed.timestamp = datetime.now()
        elif item == "color":
            self.embed.color = value
        elif item == "image":
            self.embed.set_image(url = value)
        elif item == "thumbnail":
            self.embed.set_thumbnail(url = value)
        elif item == "author":
            self.embed.author.name = value
        elif item == "author_url":
            self.embed.author.url = value
        elif item == "author_icon":
            self.embed.author.icon_url = value
        elif item == "footer":
            self.embed.footer.text = value
        elif item == "footer_icon":
            self.embed.footer.icon_url = value
        elif item == "content":
            self.content = value
        return
    
    async def update_embed(self, interaction: discord.Interaction):
        await self.message.edit(embed = self.embed, content = self.content)
        await self.bot.db.execute("""INSERT INTO server_embeds (guild_id, user_id, name, code) VALUES($1, $2, $3, $4) ON CONFLICT(guild_id, name) DO UPDATE SET code = excluded.code""", interaction.guild.id, interaction.user.id, self.name, embed_to_code(self.embed, self.content))
        return await interaction.response.defer()

    @discord.ui.button(label = "Edit Basic Information")
    async def edit_basic_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.check_author(interaction):
            modal = BasicModal(self)
            return await interaction.response.send_modal(modal)
        
    @discord.ui.button(label = "Edit Author")
    async def edit_author(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.check_author(interaction):
            modal = AuthorModal(self)
            return await interaction.response.send_modal(modal)
    
    @discord.ui.button(label = "Edit Footer")
    async def edit_footer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.check_author(interaction):
            modal = FooterModal(self)
            return await interaction.response.send_modal(modal)
        
    @discord.ui.button(label = "Edit Images")
    async def edit_images(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.check_author(interaction):
            modal = ImageModal(self)
            return await interaction.response.send_modal(modal)


    @discord.ui.button(label = "Code", emoji = "🔗")
    async def embed_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        if await self.check_author(interaction):
            return await interaction.response.send_message(content = f"```{embed_to_code(self.embed)}```", ephemeral = True)
    
    
class EmbedCodeView(discord.ui.View):
    def __init__(self, code: str):
        self.code = code
        super().__init__()

    @discord.ui.button(label = "Code", emoji = "🔗")
    async def embed_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        return await interaction.response.send_message(content = f"```{self.code}```", ephemeral = True)

