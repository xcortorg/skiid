import random
import string

import aiohttp
import discord
from discord.ext.commands import (Cog, bot_has_guild_permissions, group,
                                  has_guild_permissions)
from get.checks import ValidWebhookCode
from get.utils import EmbedScript


class Webhooks(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.description = "Webhook building commands"
        self.headers = {"Content-Type": "application/json"}

    @group(invoke_without_command=True, name="webhook")
    async def webhook_editor(self, ctx):
        await ctx.create_pages()

    @webhook_editor.command(
        description="Create a webhook in a channel",
        usage="#channel",
        name="create",
        brief="manage webhooks",
    )
    @has_guild_permissions(manage_webhooks=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def webhook_create(
        self, ctx, channel: discord.TextChannel, *, name: str = None
    ):
        """
        config
        """

        webhook = await channel.create_webhook(
            name="pretend - webhook", reason=f"Webhook created by {ctx.author}"
        )
        source = string.ascii_letters + string.digits
        code = "".join((random.choice(source) for _ in range(8)))

        # Update SQL INSERT query to include channel_id if necessary
        await self.bot.db.execute(
            """
          INSERT INTO webhook 
          (guild_id, code, url, channel, name, avatar_url) 
          VALUES ($1, $2, $3, $4, $5, $6)
          """,
            ctx.guild.id,
            code,
            webhook.url,
            channel.mention,
            name or self.bot.user.name,
            str(self.bot.user.display_avatar.url),
        )
        return await ctx.send_success(
            f"Created webhook named **{name or self.bot.user.name}** in {channel.mention} with the code `{code}`. Please save it in order to send webhooks with it"
        )

    @webhook_editor.group(
        help="config", invoke_without_command=True, name="edit", brief="manage webhooks"
    )
    async def webhook_edit(self, ctx):
        """
        Edit the webhook's look
        """

        await ctx.create_pages()

    @webhook_edit.command(
        description="Edit a webhook's name",
        usage="[code] [name]",
        name="name",
        brief="manage webhooks",
    )
    @has_guild_permissions(manage_webhooks=True)
    async def webhook_edit_name(self, ctx, code: ValidWebhookCode, *, name: str):
        """
        config
        """

        await self.bot.db.execute(
            """
      UPDATE webhook 
      SET name = $1 
      WHERE guild_id = $2 
      AND code = $3
      """,
            name,
            ctx.guild.id,
            code,
        )
        return await ctx.send_success(f"Webhook name changed to **{name}**")

    @webhook_edit.command(
        help="config",
        description="edit a webhook avatar",
        usage="[code] [avatar url]",
        name="avatar",
        aliases=["icon"],
        brief="manage webhooks",
    )
    @has_guild_permissions(manage_webhooks=True)
    async def webhook_edit_avatar(self, ctx, code: ValidWebhookCode, url: str = None):
        if not url:
            if not ctx.message.attachments:
                return await ctx.send_error("Avatar not found")

            if not ctx.message.attachments[0].filename.endswith(
                (".png", ".jpeg", ".jpg")
            ):
                return await ctx.send_error("Attachment must be a png or jpeg")

            url = ctx.message.attachments[0].proxy_url

        await self.bot.db.execute(
            """
          UPDATE webhook 
          SET avatar_url = $1 
          WHERE guild_id = $2 
          AND code = $3
          """,
            url,
            ctx.guild.id,
            code,
        )
        return await ctx.send_success("Changed webhook's avatar")

    @webhook_editor.command(
        description="Send a webhook",
        usage="[code] [discohook json file / embed code / text]",
        name="send",
        brief="manage webhooks",
    )
    @has_guild_permissions(manage_webhooks=True)
    async def webhook_send(
        self, ctx, code: ValidWebhookCode, *, script: EmbedScript = None
    ):
        """
        config
        """
        check = await self.bot.db.fetchrow(
            "SELECT * FROM webhook WHERE guild_id = $1 AND code = $2",
            ctx.guild.id,
            code,
        )
        if not check:
            return await ctx.send_error("No webhook found with this code")

        if script is None:
            if ctx.message.attachments:
                script = await self.embed_json(ctx.author, ctx.message.attachments[0])
            else:
                return await ctx.send_help(ctx.command)

        script.update(
            {"wait": True, "username": check["name"], "avatar_url": check["avatar_url"]}
        )

        async with aiohttp.ClientSession(headers=self.headers) as session:
            webhook = discord.Webhook.from_url(url=check["url"], session=session)

            if not webhook:
                return await ctx.send_error("No webhook found with this code")

            try:
                w = await self.bot.fetch_webhook(webhook.id)
                mes = await w.send(**script)
                await ctx.send_success(f"Sent webhook -> {mes.jump_url}")
            except discord.errors.NotFound:
                return await ctx.send_error("Webhook not found or invalid")

    @webhook_editor.command(name="list")
    async def webhook_list(self, ctx):
        results = await self.bot.db.fetch(
            "SELECT * FROM webhook WHERE guild_id = $1", ctx.guild.id
        )
        if len(results) == 0:
            return await ctx.send_warning(
                "There are no **webhooks** created by the bot in this server"
            )
        i = 0
        k = 1
        l = 0
        mes = ""
        number = []
        messages = []
        for result in results:
            mes = f"{mes}`{k}` <#{result['channel_id']}> - `{result['code']}`\n"
            k += 1
            l += 1
            if l == 10:
                messages.append(mes)
                number.append(
                    discord.Embed(
                        color=self.bot.color,
                        title=f"webhooks in {ctx.guild.name} ({len(results)})",
                        description=messages[i],
                    )
                )
                i += 1
                mes = ""
                l = 0

        messages.append(mes)
        number.append(
            discord.Embed(
                color=self.bot.color,
                title=f"webhooks in {ctx.guild.name} ({len(results)})",
                description=messages[i],
            )
        )
        await ctx.paginator(number)

    @webhook_editor.command(usage="[code]", name="delete", brief="manage webhooks")
    @has_guild_permissions(manage_webhooks=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def webhook_delete(self, ctx, code: ValidWebhookCode):
        """
        Delete a webhook created by the bot
        """

        check = await self.bot.db.fetchrow(
            "SELECT * FROM webhook WHERE guild_id = $1 AND code = $2",
            ctx.guild.id,
            code,
        )
        async with aiohttp.ClientSession(headers=self.headers) as session:
            webhook = discord.Webhook.from_url(check["url"], session=session)
            await self.bot.db.execute(
                "DELETE FROM webhook WHERE guild_id = $1 AND code = $2",
                ctx.guild.id,
                code,
            )
            await webhook.delete(reason=f"Webhook deleted by {ctx.author}")

        return await ctx.send_success("Deleted webhook")


async def setup(bot) -> None:
    return await bot.add_cog(Webhooks(bot))
