import random
import string
import discord
import aiohttp

from discord.ext.commands import group, Cog, has_guild_permissions, bot_has_guild_permissions

from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidWebhookCode, ValidMessage
from modules.handlers.embed import EmbedScript

class Webhooks(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Webhook commands"
        self.headers = {"Content-Type": "application/json"}

    @group(invoke_without_command=True, name="webhook", case_insensitive=True)
    async def webhook_editor(self, ctx: EvelinaContext):
        """Set up webhooks in your server"""
        return await ctx.create_pages()

    @webhook_editor.command(name="create", brief="manage webhooks", usage="webhook create #welcome evelina")
    @has_guild_permissions(manage_webhooks=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def webhook_create(self, ctx: EvelinaContext, channel: discord.TextChannel, *, name: str = None):
        """Create webhook to forward messages to"""
        webhook = await channel.create_webhook(name="evelina - webhook", reason=f"Webhook created by {ctx.author}")
        source = string.ascii_letters + string.digits
        code = "".join((random.choice(source) for _ in range(8)))
        await self.bot.db.execute("INSERT INTO webhook VALUES ($1,$2,$3,$4,$5,$6)", ctx.guild.id, code, webhook.url, channel.mention, name or self.bot.user.name, self.bot.user.avatar.url if self.bot.user.avatar else None)
        return await ctx.send_success(f"Created webhook named **{name or self.bot.user.name}** in {channel.mention} with the code `{code}`. Please save it in order to send webhooks with it")

    @webhook_editor.command(name="delete", brief="manage webhooks", usage="webhook delete bZYdgLvu")
    @has_guild_permissions(manage_webhooks=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def webhook_delete(self, ctx: EvelinaContext, code: ValidWebhookCode):
        """Delete webhook for a channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook WHERE guild_id = $1 AND code = $2", ctx.guild.id, code)
        lock = await self.bot.get_connection_lock(f"webhook_{code}")
        async with lock:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                webhook = discord.Webhook.from_url(check["url"], session=session)
                await self.bot.db.execute("DELETE FROM webhook WHERE guild_id = $1 AND code = $2", ctx.guild.id, code)
                await webhook.delete(reason=f"Webhook deleted by {ctx.author}")
        return await ctx.send_success(f"Deleted webhook `{code}`")

    @webhook_editor.command(name="send", brief="manage webhooks", usage="webhook send bZYdgLvu hello world")
    @has_guild_permissions(manage_webhooks=True)
    async def webhook_send(self, ctx: EvelinaContext, code: ValidWebhookCode, *, script: EmbedScript = None):
        """Send a message to an existing channel webhook."""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook WHERE guild_id = $1 AND code = $2", ctx.guild.id, code)
        if script is None:
            return await ctx.send_help(ctx.command)
        if not (1 <= len(check["name"]) <= 80):
            return await ctx.send_warning("The webhook username must be between `1` and `80` characters")
        if "discord" in str(check["name"]).lower():
            return await ctx.send_warning('The webhook username cannot contain the word `discord`')
        avatar_url = check["avatar"]
        if avatar_url and not avatar_url.startswith(('http://', 'https://')):
            avatar_url = self.bot.user.avatar.url if self.bot.user.avatar else None
        script.update({"wait": True, "username": check["name"], "avatar_url": avatar_url})
        
        lock = await self.bot.get_connection_lock(f"webhook_{code}")
        async with lock:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                webhook = discord.Webhook.from_url(url=check["url"], session=session)
                if not webhook:
                    return await ctx.send_warning("No webhook found with this code")
                w = await self.bot.fetch_webhook(webhook.id)
                try:
                    mes = await w.send(**script)
                    await ctx.send_success(f"Sent webhook -> {mes.jump_url}")
                except discord.NotFound:
                    await ctx.send_warning("No webhook found with this code")

    @webhook_editor.command(name="list", usage="webhook list")
    async def webhook_list(self, ctx: EvelinaContext):
        """List all available webhooks in the server"""
        results = await self.bot.db.fetch("SELECT * FROM webhook WHERE guild_id = $1", ctx.guild.id)
        if len(results) == 0:
            return await ctx.send_warning("There are no webhooks in this server")
        await ctx.paginate([f"`{result['code']}` - {result['channel']}" for result in results], f"Webhooks", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @webhook_editor.group(invoke_without_command=True, name="edit", brief="manage webhooks", case_insensitive=True)
    async def webhook_edit(self, ctx: EvelinaContext):
        """Edit the webhook's look"""
        return await ctx.create_pages()

    @webhook_edit.command(name="name", brief="manage webhooks", usage="webhook edit name bZYdgLvu evelina")
    @has_guild_permissions(manage_webhooks=True)
    async def webhook_edit_name(self, ctx: EvelinaContext, code: ValidWebhookCode, *, name: str):
        """Edit a webhook's name"""
        await self.bot.db.execute("UPDATE webhook SET name = $1 WHERE guild_id = $2 AND code = $3", name, ctx.guild.id, code)
        return await ctx.send_success(f"Webhook name changed to **{name}**")

    @webhook_edit.command(name="avatar", aliases=["icon"], brief="manage webhooks", usage="webhook edit avatar bZYdgLvu https://evelina.bot/icon.png")
    @has_guild_permissions(manage_webhooks=True)
    async def webhook_edit_avatar(self, ctx: EvelinaContext, code: ValidWebhookCode, url: str = None):
        """Edit the webhook's avatar"""
        if not url:
            if not ctx.message.attachments:
                return await ctx.send_warning("Avatar not found")
            if not ctx.message.attachments[0].filename.endswith(
                (".png", ".jpeg", ".jpg")
            ):
                return await ctx.send_warning("Attachment must be a png or jpeg")
            url = ctx.message.attachments[0].proxy_url
        await self.bot.db.execute("UPDATE webhook SET avatar = $1 WHERE guild_id = $2 AND code = $3", url, ctx.guild.id, code)
        return await ctx.send_success("Changed webhook's avatar")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Webhooks(bot))
