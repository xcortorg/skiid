import io
import zipline

from discord import Embed, Interaction
from discord.ext.commands import Cog, group

from modules.styles import emojis, colors
from modules.evelinabot import EvelinaContext, Evelina

class Storagevault(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    @group(name="storagevault", aliases=["sv"], invoke_without_command=True, case_insensitive=True)
    async def storagevault(self, ctx: EvelinaContext):
        """Manage your Storagevault account"""
        return await ctx.create_pages()
    
    @storagevault.command(name="login")
    async def storagevault_login(self, ctx: EvelinaContext):
        """Login to your Storagevault account"""
        check = await self.bot.db.fetchrow("SELECT * FROM storagevault WHERE user_id = $1", ctx.author.id)
        if check:
            return await ctx.send_warning("You are already logged in!")
        async def handle_modal_submit(interaction: Interaction, values: list[str]):
            async with zipline.Client("https://storagevault.cloud", values[0]) as client:
                try:
                    await client.get_user_stats()
                except zipline.errors.NotAuthenticated:
                    return await interaction.response.edit_message(embed=Embed(description=f"{emojis.WARNING} Invalid API-Key! Please try again.", color=colors.WARNING), view=None)
                await self.bot.db.execute("INSERT INTO storagevault (user_id, key) VALUES ($1, $2)", ctx.author.id, values[0])
                return await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} Successfully logged in! Check all commands with `{ctx.clean_prefix}help storagevault`", color=colors.SUCCESS), view=None)
        await ctx.modal_send(
            prompt=f"{emojis.QUESTION} {ctx.author.mention}: Please enter your Storagevault API-Key to authorize Evelina to access your account.",
            button_label="Enter API-Key",
            modal_title="Storagevault Authorization",
            fields=[("API-Key", "Enter your Storagevault API-Key!")],
            callback_func=handle_modal_submit
        )

    @storagevault.command(name="logout")
    async def storagevault_logout(self, ctx: EvelinaContext):
        """Logout from your Storagevault account"""
        check = await self.bot.db.fetchrow("SELECT * FROM storagevault WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send_warning("You are not logged in!")
        await self.bot.db.execute("DELETE FROM storagevault WHERE user_id = $1", ctx.author.id)
        return await ctx.send_success("Successfully logged out!")
    
    @storagevault.command(name="upload")
    async def storagevault_upload(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM storagevault WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send_warning("You are not logged in!")
        async with zipline.Client(f"{check['domain']}", f"{check['key']}") as client:
            try:
                await client.get_user_stats()
            except zipline.errors.NotAuthenticated:
                return await ctx.send_warning("Your API-Key is invalid! Please login again.")
        if not ctx.message.attachments:
            if not ctx.message.reference.resolved.attachments:
                return await ctx.send_warning("Please provide a file to upload or reply to a message with a file attachment")
        attachment = ctx.message.attachments[0] if ctx.message.attachments else ctx.message.reference.resolved.attachments[0]
        file_data = await attachment.read()
        async with zipline.Client(f"{check['domain']}", f"{check['key']}") as client:
            upload_data = zipline.FileData(io.BytesIO(file_data), filename=attachment.filename)
            uploaded_file = await client.upload_file(upload_data, format=zipline.NameFormat.uuid)
            file_url = uploaded_file.files[0].url
            file_url_raw = "/".join(file_url.split("/", 3)[:3] + ["raw"] + file_url.split("/", 3)[3:])
        return await ctx.send_success(f"Uploaded file to [**Storagevault**](https://storagevault.cloud)\n**File:** [`Click Here`]({file_url}) - **Raw:** [`Click Here`]({file_url_raw})")

    @storagevault.command(name="users")
    async def storagevault_users(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT * FROM storagevault WHERE user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send_warning("You are not logged in!")
        async with zipline.Client(f"{check['domain']}", f"{check['key']}") as client:
            try:
                users = await client.get_all_users()
            except zipline.errors.NotAuthenticated:
                return await ctx.send_warning("Your API-Key is invalid! Please login again.")
            except zipline.errors.Forbidden:
                return await ctx.send_warning("You don't have permission to view all users!")
        content = []
        for user in users:
            content.append(f"**{user.username}** - `{user.id}`")
        return await ctx.paginate(content, title="Storagevault Users", author={"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Storagevault(bot))