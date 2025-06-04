import re
import json
import uuid
import string
import random

from typing import Union
from datetime import datetime
from epic_games_free import EpicGames

from discord import Embed, Member, Attachment, Role, TextChannel, Message, File, ChannelType, Thread
from discord.ui import View, Button
from discord.ext.commands import Cog, command, has_guild_permissions, BadArgument, group, bot_has_guild_permissions, hybrid_group

from modules.styles import emojis, colors
from modules.converters import NewRoleConverter
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidPermission, ValidMessage, ValidCommand, ValidCog, ValidTime
from modules.handlers.embed import EmbedBuilder, EmbedScript

class Config(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Config commands"

    async def embed_json(self, member: Member, attachment: Attachment):
        if not attachment.filename.endswith(".json"):
            raise BadArgument("Attachment should be a **json** file created from discohook")
        try:
            data = json.loads(await attachment.read())
            message = data["backups"][0]["messages"][0]
            content = message["data"].get("content")
            if content:
                content = EmbedBuilder().embed_replacement(member, content)
            embeds = []
            for embed in message["data"]["embeds"]:
                e = json.loads(EmbedBuilder().embed_replacement(member, json.dumps(embed)))
                embeds.append(Embed.from_dict(e))
                if len(embeds) == 10:
                    break
            return {"content": content, "embeds": embeds}
        except json.JSONDecodeError:
            raise BadArgument("Couldn't decode JSON, are you sure this is a valid JSON file?")
        
    @group(invoke_without_command=True, case_insensitive=True)
    async def embed(self, ctx: EvelinaContext):
        """Create embeds using the bot"""
        return await ctx.create_pages()

    @command(name="say", usage="say #channel Hello world")
    @has_guild_permissions(manage_messages=True)
    async def say(self, ctx: EvelinaContext, channel: TextChannel, *, message: str):
        """Send a message through the bot"""
        if not channel.permissions_for(ctx.author).send_messages:
            return await ctx.send_warning(f"You don't have permission to send messages in {channel.mention}")
        if len(message) > 2000:
            return await ctx.send_warning("You can't send messages over **2000 characters**")
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            file = await attachment.to_file()
            await channel.send(message, file=file)
        else:
            await channel.send(message)
        try:
            await ctx.message.delete()
        except:
            pass

    @command(brief="manage messages", usage="ce {embed}$v{description: Hello world}")
    @has_guild_permissions(manage_messages=True)
    async def ce(self, ctx: EvelinaContext, *, code: EmbedScript = None):
        """Create an embed using an embed code\n> **Embed Builder:** https://evelina.bot/embed"""
        await self.embed_create(ctx, code=code)
        
    @embed.command(name="create", brief="manage messages", usage="embed create {embed}$v{description: Hello world}")
    @has_guild_permissions(manage_messages=True)
    async def embed_create(self, ctx: EvelinaContext, *, code: EmbedScript = None):
        """Create an embed using an embed code\n> **Embed Builder:** https://evelina.bot/embed"""
        try:
            if code is None:
                if ctx.message.attachments:
                    code = await self.embed_json(ctx.author, ctx.message.attachments[0])
                else:
                    return await ctx.send_help(ctx.command)
            await ctx.send(**code)
        except Exception as e:
            await ctx.send_warning(f"An error occurred while creating the embed:\n```{e}```")
        
    @embed.command(name="overwrite", brief="manage messages", usage="embed overwrite .../channels/... {embed}$v{description: Hello world}")
    @has_guild_permissions(manage_messages=True)
    async def embed_overwrite(self, ctx: EvelinaContext, message: Message, *, code: EmbedScript = None):
        """Overwrite an embed sent by evelina"""
        if message.author.id != self.bot.user.id:
            return await ctx.send_warning(f"This is not a message sent by **{self.bot.user}**")
        if code is None:
            if ctx.message.attachments:
                code = await self.embed_json(ctx.author, ctx.message.attachments[0])
            else:
                return await ctx.send_help(ctx.command)
        await message.edit(**code)
        await ctx.send_success(f"Overwrite message -> {message.jump_url}")

    @embed.command(name="edit", brief="manage messages", usage="embed edit .../channels/... description Hello world")
    @has_guild_permissions(manage_messages=True)
    async def embed_edit(self, ctx: EvelinaContext, message: Message, field: str, *, value: str):
        """Edit an embed sent by evelina"""
        if message.author.id != self.bot.user.id:
            return await ctx.send_warning(f"This is not a message sent by **{self.bot.user}**")#
        if field not in ("content", "description", "footer_text", "footer_image", "image", "thumbnail", "title", "url", "color", "author_icon", "author_name", "author_url") and not field.startswith("field_"):
            return await ctx.send_warning("Invalid field. Use: `content`, `description`, `footer_text`, `footer_image`, `image`, `thumbnail`, `title`, `url`, `color`, `author_icon`, `author_name`, `author_url`, `field_1_title`, `field_1_text` or `field_1_inline`")
        embed = message.embeds[0] if message.embeds else Embed()
        if field == "content":
            await message.edit(content=value)
        elif field == "description":
            embed.description = value
        elif field == "footer_text":
            embed.set_footer(text=value)
        elif field == "footer_image":
            embed.set_footer(icon_url=value)
        elif field == "image":
            embed.set_image(url=value)
        elif field == "thumbnail":
            embed.set_thumbnail(url=value)
        elif field == "title":
            embed.title = value
        elif field == "url":
            embed.url = value
        elif field == "color":
            try:
                embed.color = int(value.replace("#", ""), 16)
            except:
                embed.color = int("808080", 16)
        elif field == "author_icon":
            embed.set_author(icon_url=value)
        elif field == "author_name":
            embed.set_author(name=value)
        elif field == "author_url":
            embed.set_author(url=value)
        elif field.startswith("field_"):
            try:
                field_num = int(field.split('_')[1])
                if field.endswith("_title"):
                    if len(embed.fields) >= field_num:
                        embed.set_field_at(field_num - 1, name=value, value=embed.fields[field_num - 1].value, inline=False)
                    else:
                        embed.add_field(name=value, value="\u200b", inline=False)
                elif field.endswith("_text"):
                    if len(embed.fields) >= field_num:
                        embed.set_field_at(field_num - 1, name=embed.fields[field_num - 1].name, value=value, inline=False)
                    else:
                        embed.add_field(name="\u200b", value=value, inline=False)
                elif field.endswith("_inline"):
                    if len(embed.fields) >= field_num:
                        embed.set_field_at(field_num - 1, name=embed.fields[field_num - 1].name, value=embed.fields[field_num - 1].value, inline=True)
                    else:
                        embed.add_field(name="\u200b", value="\u200b", inline=True)
                else:
                    return await ctx.send_warning("Invalid field format. Use: field_X_title or field_X_text")
            except (ValueError, IndexError):
                return await ctx.send_warning("Invalid field format or value. Use: field_X_title or field_X_text")
        await message.edit(embed=embed)
        await ctx.send_success(f"Edited message -> {message.jump_url}")

    @embed.command(name="copy", usage="embed copy .../channels/...")
    async def embed_copy(self, ctx: EvelinaContext, message: ValidMessage):
        """Copy the embed code of each embed in the message as separate messages"""
        embed_codes = EmbedBuilder().copy_embed(message).split("\n\n\n\n\n")
        for embed_code in embed_codes:
            if len(embed_code) > 2000:
                with open('data/images/tmp/embed_code.txt', 'w') as file:
                    file.write(embed_code)
                await ctx.send(file=File('data/images/tmp/embed_code.txt'))
            else:
                await ctx.send(f"```{embed_code}```")

    @embed.command(name="save", usage="embed save .../channels/...")
    async def embed_save(self, ctx: EvelinaContext, message: ValidMessage):
        """Save the embed code of a certain embed"""
        source = string.ascii_letters + string.digits
        code = "".join((random.choice(source) for _ in range(8)))
        embed_code = EmbedBuilder().copy_embed(message)
        await self.bot.db.execute("INSERT INTO embeds VALUES ($1, $2, $3)", code, embed_code, ctx.author.id)
        await ctx.send_success(f"Saved the embed code as `{code}`")

    @embed.command(name="load", usage="embed load bZYdgLvu")
    async def embed_load(self, ctx: EvelinaContext, code: str):
        """Load a saved embed code"""
        result = await self.bot.db.fetchrow("SELECT * FROM embeds WHERE code = $1", code)
        if not result:
            return await ctx.send_warning(f"Embedcode `{code}` does not exist")
        embed_code = result['embed']
        if len(embed_code) > 2000:
            with open('data/images/tmp/embed_code.txt', 'w') as file:
                file.write(embed_code)
            await ctx.send(file=File('data/images/tmp/embed_code.txt'))
        else:
            await ctx.send(f"```{embed_code}```")

    @embed.command(name="post", brief="Embed Creator", usage="embed post Boost {embed}$v{description: Hello world}")
    async def embed_post(self, ctx: EvelinaContext, name: str, *, code: str):
        """Post an embed on evelina's web"""
        check = await self.bot.db.fetchrow("SELECT * FROM embeds_creator where user_id = $1", ctx.author.id)
        if not check:
            return await ctx.send_warning(f"You are not permited to post embeds")
        names = ["Welcome", "Leave", "Boost", "Vanity", "Autoresponder", "Last.fm", "Ban", "Unabn", "Kick", "Mute", "Unmute", "Jail", "Unjail"]
        if name not in names:
            formatted_names = ", ".join(f"`{f}`" for f in names[:-1]) + f" & `{names[-1]}`"
            return await ctx.send_warning(f"Invalid name. Valid names are: {formatted_names}")
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            file_data = await attachment.read()
            file_extension = attachment.filename.split('.')[-1]
            file_code = f"{str(uuid.uuid4())[:8]}"
            file_name = f"{file_code}.{file_extension}"
            content_type = attachment.content_type
            upload_res = await self.bot.r2.upload_file("evelina", file_data, file_name, content_type, "e")
            if upload_res:
                file_url = f"https://cdn.evelina.bot/e/{file_name}"
                await self.bot.db.execute("INSERT INTO embeds_templates (name, user_id, code, embed, image) VALUES ($1,$2,$3,$4,$5)", name, ctx.author.id, file_code, code, file_url)
                return await ctx.send_success(f"Posted your embed (`#{file_code}`) to [`evelina.bot/templates`](https://evelina.bot/templates)")
            else:
                return await ctx.send_warning(f"An error occurred while uploading your embed preview image")
        else:
            return await ctx.send_warning(f"You have to attach an image as embed preview")

    @group(invoke_without_command=True, case_insensitive=True)
    async def usertrack(self, ctx: EvelinaContext):
        """Start tracking usernames in a channel"""
        return await ctx.create_pages()

    @usertrack.command(name="add", brief="manage guild", usage="usertrack add #username")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def usernames_add(self, ctx: EvelinaContext, *, channel: TextChannel, length: int = None):
        """Add a channel for username tracking"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_username WHERE guild_id = $1", ctx.guild.id)
        if check:
            return await ctx.send_warning("The bot is already tracking usernames for this server")
        webhooks = [w for w in await channel.webhooks() if w.token]
        if len(webhooks) == 0:
            webhook = await channel.create_webhook(name="Evelina - Usernames")
        else:
            webhook = webhooks[0]
        await self.bot.db.execute("INSERT INTO webhook_username VALUES ($1,$2,$3)", ctx.guild.id, webhook.url, length)
        return await ctx.send_success(f"The bot will start tracking new available usernames in {channel.mention}")
    
    @usertrack.command(name="remove", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def usernames_remove(self, ctx: EvelinaContext):
        """Remove a channel for username tracking"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_username WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Username tracking is **not** enabled in this server")
        await self.bot.db.execute("DELETE FROM webhook_username WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Disabled username tracking in this server")
    
    @usertrack.command(name="name", brief="manage guild", usage="usertrack name /evelina")
    @has_guild_permissions(manage_guild=True)
    async def usernames_name(self, ctx: EvelinaContext, *, name: str):
        """Set a custom name for the username webhook"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_username WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Username tracking is **not** enabled in this server")
        await self.bot.db.execute("UPDATE webhook_username SET name = $1 WHERE guild_id = $2", name, ctx.guild.id)
        return await ctx.send_success(f"Username webhook name updated to `{name}`")
    
    @usertrack.command(name="avatar", brief="manage guild", usage="usertrack avatar https://cdn.evelina.bot/e/12345678.png")
    @has_guild_permissions(manage_guild=True)
    async def usernames_avatar(self, ctx: EvelinaContext, *, avatar: str):
        """Set a custom avatar for the username webhook"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_username WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Username tracking is **not** enabled in this server")
        await self.bot.db.execute("UPDATE webhook_username SET avatar = $1 WHERE guild_id = $2", avatar, ctx.guild.id)
        return await ctx.send_success(f"Username webhook avatar updated")
    
    @group(invoke_without_command=True, case_insensitive=True)
    async def vanitytrack(self, ctx: EvelinaContext):
        """Start tracking vanitys in a channel"""
        return await ctx.create_pages()

    @vanitytrack.command(name="add", brief="manage guild", usage="vanitytrack add #vanity")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def vanitytrack_add(self, ctx: EvelinaContext, *, channel: TextChannel, length: int = None):
        """Add a channel for vanity tracking"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_vanity WHERE guild_id = $1", ctx.guild.id)
        if check:
            return await ctx.send_warning("The bot is already tracking vanity for this server")
        webhooks = [w for w in await channel.webhooks() if w.token]
        if len(webhooks) == 0:
            webhook = await channel.create_webhook(name="Evelina - Vanitys")
        else:
            webhook = webhooks[0]
        await self.bot.db.execute("INSERT INTO webhook_vanity VALUES ($1,$2,$3)", ctx.guild.id, webhook.url, length)
        return await ctx.send_success(f"The bot will start tracking new available vanity in {channel.mention}")
    
    @vanitytrack.command(name="remove", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(manage_webhooks=True)
    async def vanitytrack_remove(self, ctx: EvelinaContext):
        """Remove a channel for vanity tracking"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_vanity WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Vanity tracking is **not** enabled in this server")
        await self.bot.db.execute("DELETE FROM webhook_vanity WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Disabled vanity tracking in this server")
    
    @vanitytrack.command(name="name", brief="manage guild", usage="vanitytrack name /evelina")
    @has_guild_permissions(manage_guild=True)
    async def vanitytrack_name(self, ctx: EvelinaContext, *, name: str):
        """Set a custom name for the vanity webhook"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_vanity WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Vanity tracking is **not** enabled in this server")
        await self.bot.db.execute("UPDATE webhook_vanity SET name = $1 WHERE guild_id = $2", name, ctx.guild.id)
        return await ctx.send_success(f"Vanity webhook name updated to `{name}`")

    @vanitytrack.command(name="avatar", brief="manage guild", usage="vanitytrack avatar https://cdn.evelina.bot/e/12345678.png")
    @has_guild_permissions(manage_guild=True)
    async def vanitytrack_avatar(self, ctx: EvelinaContext, *, avatar: str):
        """Set a custom avatar for the vanity webhook"""
        check = await self.bot.db.fetchrow("SELECT * FROM webhook_vanity WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("Vanity tracking is **not** enabled in this server")
        await self.bot.db.execute("UPDATE webhook_vanity SET avatar = $1 WHERE guild_id = $2", avatar, ctx.guild.id)
        return await ctx.send_success(f"Vanity webhook avatar updated")

    @hybrid_group(name="prefix", description="Manage prefixes for the server", invoke_without_command=True)
    async def prefix(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @prefix.command(name="set", brief="manage guild", usage="prefix set ,", description="Set command prefix for server")
    @has_guild_permissions(manage_guild=True)
    async def prefix_set(self, ctx: EvelinaContext, prefix: str):
        if len(prefix) > 7:
            raise BadArgument("Prefix is too long!")
        res = await self.bot.db.fetchrow("SELECT * FROM prefixes WHERE guild_id = $1", ctx.guild.id)
        if not res:
            args = ["INSERT INTO prefixes VALUES ($1,$2)", ctx.guild.id, prefix]
        else:
            args = ["UPDATE prefixes SET prefix = $1 WHERE guild_id = $2", prefix, ctx.guild.id]
        await self.bot.db.execute(*args)
        self.bot.prefix_cache["guilds"][ctx.guild.id] = prefix
        return await ctx.send_success(f"Guild prefix now **configured** as `{prefix}`")
    
    @prefix.command(name="remove", brief="manage guild", description="Remove command prefix for server")
    @has_guild_permissions(manage_guild=True)
    async def prefix_remove(self, ctx: EvelinaContext):
        check = await self.bot.db.fetchrow("SELECT prefix FROM prefixes WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("This server does **not** have any prefix")
        await self.bot.db.execute("DELETE FROM prefixes WHERE guild_id = $1", ctx.guild.id)
        self.bot.prefix_cache["guilds"].pop(ctx.guild.id, None)
        return await ctx.send_success("Guild prefix removed")
    
    @prefix.command(name="leaderboard", aliases=["lb"])
    async def prefix_leaderboard(self, ctx: EvelinaContext):
        """View the leaderboard of prefixes used for the bot"""
        prefixes = await self.bot.db.fetch("SELECT prefix, COUNT(*) as usage_count FROM prefixes GROUP BY prefix ORDER BY usage_count DESC")
        if not prefixes:
            return await ctx.send_warning("No prefixes found")
        leaderboard = [f"**{row['prefix']}** - {row['usage_count']} uses" for i, row in enumerate(prefixes)]
        return await ctx.paginate(leaderboard, "Prefix Leaderboard", {"name": ctx.author.name, "icon_url": ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url})
    
    @command()
    async def variables(self, ctx: EvelinaContext):
        """View all available variables for embed messages"""
        embed = Embed(color=colors.NEUTRAL, description=f"{ctx.author.mention}: Here are all the available variables for embed messages")
        view = View()
        view.add_item(Button(label="User", url="https://docs.evelina.bot/embeds/content-in-embeds/variables#user-related-variables"))
        view.add_item(Button(label="Guild", url="https://docs.evelina.bot/embeds/content-in-embeds/variables#guild-related-variables"))
        view.add_item(Button(label="Lastfm", url="https://docs.evelina.bot/embeds/content-in-embeds/variables#guild-related-variables-1"))
        view.add_item(Button(label="Levels", url="https://docs.evelina.bot/embeds/content-in-embeds/variables#levels-related-variables"))
        view.add_item(Button(label="Invoke", url="https://docs.evelina.bot/embeds/content-in-embeds/variables#punishments-related-variables"))
        return await ctx.send(embed=embed, view=view)

    @group(invoke_without_command=True, aliases=["fakeperms", "fp"], case_insensitive=True)
    async def fakepermissions(self, ctx: EvelinaContext):
        """Set up fake permissions for role through the bot"""
        return await ctx.create_pages()

    @fakepermissions.command(name="perms")
    async def fp_perms(self, ctx: EvelinaContext):
        """Get a list of valid permissions for the server"""
        return await ctx.paginate(list(map(lambda p: p[0], ctx.author.guild_permissions)), "Valid permissions")
    
    @fakepermissions.command(name="add", brief="administrator", usage="fakepermissions add mod manage_messages")
    @has_guild_permissions(administrator=True)
    async def fp_add(self, ctx: EvelinaContext, role: NewRoleConverter, permission: ValidPermission):
        """Grant a fake permission to a role"""
        check = await self.bot.db.fetchrow("SELECT perms FROM fake_perms WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if not check:
            await self.bot.db.execute("INSERT INTO fake_perms VALUES ($1,$2,$3)", ctx.guild.id, role.id, json.dumps([permission]))
        else:
            perms = json.loads(check[0])
            perms.append(permission)
            await self.bot.db.execute("UPDATE fake_perms SET perms = $1 WHERE guild_id = $2 AND role_id = $3", json.dumps(perms), ctx.guild.id, role.id)
        return await ctx.send_success(f"Added `{permission}` to the {role.mention}'s fake permissions")
    
    @fakepermissions.command(name="remove", brief="administrator", usage="fakepermissions remove mod manage_messages")
    @has_guild_permissions(administrator=True)
    async def fp_remove(self, ctx: EvelinaContext, role: NewRoleConverter, permission: ValidPermission):
        """Remove a fake permission from a role"""
        check = await self.bot.db.fetchrow("SELECT perms FROM fake_perms WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if not check:
            return await ctx.send_warning("There are no fake permissions associated with this role")
        perms = json.loads(check[0])
        if permission not in perms:
            return await ctx.send_warning(f"`{permission}` is not associated with the {role.mention}'s fake permissions")
        if len(perms) > 1:
            perms.remove(permission)
            await self.bot.db.execute("UPDATE fake_perms SET perms = $1 WHERE guild_id = $2 AND role_id = $3", json.dumps(perms), ctx.guild.id, role.id)
        else:
            await self.bot.db.execute("DELETE FROM fake_perms WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        return await ctx.send_success(f"Removed `{permission}` from the {role.mention}'s fake permissions")
    
    @fakepermissions.command(name="clear", brief="administrator", usage="fakepermissions clear mod")
    @has_guild_permissions(administrator=True)
    async def fp_clear(self, ctx: EvelinaContext, role: NewRoleConverter):
        """Clear all fake permissions for a role"""
        check = await self.bot.db.fetchrow("SELECT perms FROM fake_perms WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if not check:
            return await ctx.send_warning("There are no fake permissions associated with this role")
        await self.bot.db.execute("DELETE FROM fake_perms WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        return await ctx.send_success(f"Cleared all fake permissions for {role.mention}")

    @fakepermissions.command(name="reset", brief="administrator", usage="fakepermissions reset")
    @has_guild_permissions(administrator=True)
    async def fp_reset(self, ctx: EvelinaContext):
        """Reset all fake permissions for the server"""
        await self.bot.db.execute("DELETE FROM fake_perms WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Cleared all fake permissions for this server")
    
    @fakepermissions.command(name="list", brief="administrator", usage="fakepermissions list mod")
    @has_guild_permissions(administrator=True)
    async def fp_list(self, ctx: EvelinaContext, *, role: Role):
        """List all fake permissions"""
        result = await self.bot.db.fetchrow("SELECT perms FROM fake_perms WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if not result:
            return await ctx.send_warning("There are no fake permissions associated with this role")
        perms = json.loads(result[0])
        await ctx.paginate(perms, f"Fake permissions", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(name="bumpreminder", aliases=["bump"], invoke_without_command=True, case_insensitive=True)
    async def bumpreminder(self, ctx: EvelinaContext):
        """Get reminders to /bump your server on Disboard!"""
        return await ctx.create_pages()

    @bumpreminder.command(name="enable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_enable(self, ctx: EvelinaContext):
        """Enable the disboard bump reminder feature in your server"""
        check = await self.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if check:
            return await ctx.send_warning("The bump reminder is **already** enabled")
        await self.bot.db.execute("INSERT INTO bumpreminder (guild_id, thankyou, reminder) VALUES ($1,$2,$3)", ctx.guild.id, "{embed}{color: #181a14}$v{description: <:thumbsup:1263643054489993337> Thank you for bumping the server! I will remind you **in 2 hours** to do it again}$v{content: {user.mention}}", "{embed}{color: #181a14}$v{description: 🕰️ Bump the server using `/bump`}$v{content: {user.mention}}")
        return await ctx.send_success("Bump Reminder is now enabled")
    
    @bumpreminder.command(name="disable", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_disable(self, ctx: EvelinaContext):
        """Disable the disboard bump reminder feature"""
        check = await ctx.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"Bump reminder feature is **not** enabled\n> Use `{ctx.clean_prefix}bumpreminder enable` to enable it")
        await self.bot.db.execute("DELETE FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Bump reminder is now disabled")

    @bumpreminder.command(name="thankyou", aliases=["ty"], brief="manage guild", usage="bumpreminder thankyou Thanks, {user.mention}")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_thankyou(self, ctx: EvelinaContext, *, code: str = "{embed}{color: #24B8B8}$v{description: <:db_blush:1295202836581453865> Thank you for bumping the server! I will remind you **in 2 hours** to do it again}$v{content: {user.mention}}"):
        """Set the 'Thank You' message for successfully running /bump"""
        check = await ctx.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"Bump reminder feature is **not** enabled\n> Use `{ctx.clean_prefix}bumpreminder enable` to enable it")
        await self.bot.db.execute("UPDATE bumpreminder SET thankyou = $1 WHERE guild_id = $2", code, ctx.guild.id)
        return await ctx.send_success(f"Bump reminder thankyou message updated to\n```\n{code}```")
    
    @bumpreminder.command(name="reminder", brief="manage guild", usage="bumpreminder reminder Bump the server using `/bump`")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_reminder(self, ctx: EvelinaContext, *, code: str = "{embed}{color: #FF6465}$v{description: ⏰ Bump the server using `/bump`}$v{content: {user.mention}}"):
        """Set the reminder message to run /bump"""
        check = await ctx.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"Bump reminder feature is **not** enabled\n> Use `{ctx.clean_prefix}bumpreminder enable` to enable it")
        await self.bot.db.execute("UPDATE bumpreminder SET reminder = $1 WHERE guild_id = $2", code, ctx.guild.id)
        return await ctx.send_success(f"Bump reminder reminder message updated to\n```\n{code}```")
    
    @bumpreminder.command(name="leaderboard", aliases=["lb"])
    async def bumpreminder_leaderboard(self, ctx: EvelinaContext):
        """View the bump reminder leaderboard"""
        res = await self.bot.db.fetch("SELECT * FROM bumpreminder_leaderboard WHERE guild_id = $1 ORDER BY bumps DESC", ctx.guild.id)
        if not res:
            return await ctx.send_warning("No one has bumped the server yet")
        content = []
        for i, row in enumerate(res):
            bumps = row["bumps"]
            user_id = row["user_id"]
            if user_id:
                content.append(f"<@{user_id}> bumped `{bumps} times`")
        return await ctx.paginate(content, "Bump Reminder Leaderboard", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @bumpreminder.group(name="test", invoke_without_command=True, case_insensitive=True)
    async def bumpreminder_test(self, ctx: EvelinaContext):
        """Test your bump reminder/thankyou messages"""
        return await ctx.create_pages()
    
    @bumpreminder_test.command(name="reminder", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_test_reminder(self, ctx: EvelinaContext):
        """Test your bump reminder message"""
        check = await ctx.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"Bump reminder feature is **not** enabled\n> Use `{ctx.clean_prefix}bumpreminder enable` to enable it")
        res = await self.bot.db.fetchrow("SELECT * FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        embed = res["reminder"]
        x = await self.bot.embed_build.alt_convert(ctx.author, embed)
        try:
            return await ctx.send(**x)
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while sending the message\n```{e}```")
        
    @bumpreminder_test.command(name="thankyou", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_test_thankyou(self, ctx: EvelinaContext):
        """Test your bump thankyou message"""
        check = await ctx.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"Bump reminder feature is **not** enabled\n> Use `{ctx.clean_prefix}bumpreminder enable` to enable it")
        res = await self.bot.db.fetchrow("SELECT * FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        embed = res["thankyou"]
        x = await self.bot.embed_build.alt_convert(ctx.author, embed)
        try:
            return await ctx.send(**x)
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while sending the message\n```{e}```")
        
    @bumpreminder.group(name="view", invoke_without_command=True, case_insensitive=True)
    async def bumpreminder_view(self, ctx: EvelinaContext):
        """View your bump reminder/thankyou messages"""
        return await ctx.create_pages()
    
    @bumpreminder_view.command(name="reminder", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_view_reminder(self, ctx: EvelinaContext):
        """View your bump reminder message"""
        check = await ctx.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"Bump reminder feature is **not** enabled\n> Use `{ctx.clean_prefix}bumpreminder enable` to enable it")
        res = await self.bot.db.fetchrow("SELECT * FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        embed = res["reminder"]
        return await ctx.evelina_send(f"Your custom **bump reminder** message is:\n```{embed}```")
        
    @bumpreminder_view.command(name="thankyou", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def bumpreminder_view_thankyou(self, ctx: EvelinaContext):
        """View your bump thankyou message"""
        check = await ctx.bot.db.fetchrow("SELECT guild_id FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"Bump reminder feature is **not** enabled\n> Use `{ctx.clean_prefix}bumpreminder enable` to enable it")
        res = await self.bot.db.fetchrow("SELECT * FROM bumpreminder WHERE guild_id = $1", ctx.guild.id)
        embed = res["thankyou"]
        return await ctx.evelina_send(f"Your custom **bump thankyou** message is:\n```{embed}```")

    @group(name="alias", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def alias(self, ctx: EvelinaContext):
        """Create your own shortcuts for commands"""
        return await ctx.create_pages()

    @alias.command(name="add", brief="manage guild", usage="alias add byebye ban")
    @has_guild_permissions(manage_guild=True)
    async def alias_add(self, ctx: EvelinaContext, alias: str, command: str, *, args: str = None):
        """Create or update an alias for command"""
        _command = self.bot.get_command(command)
        if not _command:
            return await ctx.send_warning(f"`{command}` is not a command")
        if self.bot.get_command(alias):
            return await ctx.send_warning(f"`{alias}` is already a command")
        existing_alias = await self.bot.db.fetchrow("SELECT alias FROM aliases WHERE guild_id = $1 AND alias = $2", ctx.guild.id, alias)
        if existing_alias:
            await self.bot.db.execute("UPDATE aliases SET command = $1, args = $2 WHERE guild_id = $3 AND alias = $4", command, args, ctx.guild.id, alias)
            await ctx.send_success(f"Updated `{alias}` to now alias `{_command.qualified_name}`")
        else:
            if check := await self.bot.db.fetch("SELECT alias FROM aliases WHERE guild_id = $1", ctx.guild.id):
                if len(check) >= 75:
                    return await ctx.send_warning(f"You can only have **75 aliases**")
            await self.bot.db.execute("INSERT INTO aliases (guild_id, command, alias, args) VALUES ($1, $2, $3, $4)", ctx.guild.id, command, alias, args)
            await ctx.send_success(f"Added `{alias}` as an alias for `{_command.qualified_name}`")

    @alias.command(name="remove", brief="manage guild", usage="alias remove byebye")
    @has_guild_permissions(manage_guild=True)
    async def alias_remove(self, ctx: EvelinaContext, *, alias: str):
        """Remove an alias for command"""
        if not await self.bot.db.fetchrow("SELECT * FROM aliases WHERE guild_id = $1 AND alias = $2", ctx.guild.id, alias):
            return await ctx.send_warning(f"`{alias}` is **not** an alias")
        await self.bot.db.execute("DELETE FROM aliases WHERE guild_id = $1 AND alias = $2", ctx.guild.id, alias)
        return await ctx.send_success(f"Removed the **alias** `{alias}`")
    
    @alias.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def alias_list(self, ctx: EvelinaContext):
        """List every alias for all commands"""
        results = await self.bot.db.fetch("SELECT * FROM aliases WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"No **aliases** are set")
        await ctx.paginate([f"**{result['alias']}** - `{result['command']}{' ' if result['args'] else ''}{result['args'] if result['args'] else ''}`" for result in results], title=f"Aliases", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon or None})

    @group(name="restrictcommand", aliases=["restrictcmd", "rc"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def restrictcommand(self, ctx: EvelinaContext):
        """Only allows people with a certain role to use command"""
        return await ctx.create_pages()

    @restrictcommand.command(name="add", aliases=["make"], brief="manage guild", usage="restrictcommand add booster snipe")
    @has_guild_permissions(manage_guild=True)
    async def restrictcommand_add(self, ctx: EvelinaContext, role: Role, *, command: str):
        """Allows the specified role exclusive permission to use a command or cog"""
        if command.lower() == "all":
            if not await self.bot.db.fetchrow("SELECT * FROM restrictcommand WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, "all", role.id):
                await self.bot.db.execute("INSERT INTO restrictcommand VALUES ($1, $2, $3)", ctx.guild.id, "all", role.id)
                return await ctx.send_success(f"All commands are now restricted to members with {role.mention}")
            else:
                return await ctx.send_warning(f"All commands are **already** restricted to {role.mention}")
        _command = self.bot.get_command(command)
        if not _command:
            return await ctx.send_warning(f"Command `{command}` does not exist")
        if _command.name in ("help", "restrictcommand", "disablecmd", "enablecmd"):
            return await ctx.send("no lol")
        if not await self.bot.db.fetchrow("SELECT * FROM restrictcommand WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, _command.qualified_name, role.id):
            await self.bot.db.execute("INSERT INTO restrictcommand VALUES ($1, $2, $3)", ctx.guild.id, _command.qualified_name, role.id)
        else:
            return await ctx.send_warning(f"`{_command.qualified_name}` is **already** restricted to {role.mention}")
        await ctx.send_success(f"Allowing members with {role.mention} to use `{_command.qualified_name}`")

    @restrictcommand.command(name="remove", aliases=["delete", "del"], brief="manage guild", usage="restrictcommand remove booster snipe")
    @has_guild_permissions(manage_guild=True)
    async def restrictcommand_remove(self, ctx: EvelinaContext, role: Role, *, command: str):
        """Removes the specified role's exclusive permission to use a command or cog"""
        if command.lower() == "all":
            if await self.bot.db.fetchrow("SELECT * FROM restrictcommand WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, "all", role.id):
                await self.bot.db.execute("DELETE FROM restrictcommand WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, "all", role.id)
                return await ctx.send_success(f"All commands are no longer restricted to members with {role.mention}")
            else:
                return await ctx.send_warning(f"All commands are **not** restricted to {role.mention}")
        _command = self.bot.get_command(command)
        if not _command:
            return await ctx.send_warning(f"Command `{command}` does not exist")
        if await self.bot.db.fetchrow("SELECT * FROM restrictcommand WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, _command.qualified_name, role.id):
            await self.bot.db.execute("DELETE FROM restrictcommand WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, _command.qualified_name, role.id)
        else:
            return await ctx.send_warning(f"`{_command.qualified_name}` is **not** restricted to {role.mention}")
        await ctx.send_success(f"No longer allowing members with {role.mention} to use `{_command.qualified_name}`")

    @restrictcommand.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def restrictcommand_list(self, ctx: EvelinaContext):
        """View a list of every restricted command"""
        results = await self.bot.db.fetch("SELECT * FROM restrictcommand WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are **no** restricted commands")
        restricted_commands = []
        for result in results:
            role = ctx.guild.get_role(result['role_id'])
            if role:
                restricted_commands.append(f"**{result['command']}**: {role.mention}")
            else:
                restricted_commands.append(f"**{result['command']}**: `{result['role_id']}`")
        return await ctx.paginate(restricted_commands, title="Restricted Commands", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(name="restrictmodule", aliases=["restrictmod", "rm"], brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def restrictmodule(self, ctx: EvelinaContext):
        """Restrict a module to a role"""
        return await ctx.create_pages()

    @restrictmodule.command(name="add", aliases=["make"], brief="manage guild", usage="restrictmodule add fun booster")
    @has_guild_permissions(manage_guild=True)
    async def restrictmodule_add(self, ctx: EvelinaContext, role: Role, *, module: ValidCog):
        """Restrict a module to a role"""
        if not await self.bot.db.fetchrow("SELECT * FROM restrictmodule WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, module, role.id):
            await self.bot.db.execute("INSERT INTO restrictmodule VALUES ($1, $2, $3)", ctx.guild.id, module, role.id)
        else:
            return await ctx.send_warning(f"`{module}` is **already** restricted to {role.mention}")
        return await ctx.send_success(f"Restricting `{module}` to members with {role.mention}")

    @restrictmodule.command(name="remove", aliases=["delete", "del"], brief="manage guild", usage="restrictmodule remove fun booster")    
    @has_guild_permissions(manage_guild=True)
    async def restrictmodule_remove(self, ctx: EvelinaContext, role: Role, *, module: ValidCog):
        """Remove a module's restriction from a role"""
        if await self.bot.db.fetchrow("SELECT * FROM restrictmodule WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, module, role.id):
            await self.bot.db.execute("DELETE FROM restrictmodule WHERE guild_id = $1 AND command = $2 AND role_id = $3", ctx.guild.id, module, role.id)
        else:
            return await ctx.send_warning(f"`{module}` is **not** restricted to {role.mention}")
        return await ctx.send_success(f"Removing `{module}` restriction from {role.mention}")
    
    @restrictmodule.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def restrictmodule_list(self, ctx: EvelinaContext):
        """View a list of every restricted module"""
        results = await self.bot.db.fetch("SELECT * FROM restrictmodule WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are **no** restricted modules")
        restricted_modules = []
        for result in results:
            role = ctx.guild.get_role(result['role_id'])
            if role:
                restricted_modules.append(f"**{result['command']}**: {role.mention}")
            else:
                restricted_modules.append(f"**{result['command']}**: `{result['role_id']}`")
        return await ctx.paginate(restricted_modules, title="Restricted Modules", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(name="set", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def set(self, ctx: EvelinaContext):
        """Modify your server with evelina"""
        return await ctx.create_pages()

    @set.command(name="name", brief="manage guild", usage="set name evelina")
    @has_guild_permissions(manage_guild=True)
    async def set_name(self, ctx: EvelinaContext, *, name: str):
        """Change your server's name"""
        if len(name) > 100:
            return await ctx.send_warning(f"Server names can't be over **100 characters**")
        _name = ctx.guild.name
        await ctx.guild.edit(name=name)
        await ctx.send_success(f"Changed **{_name}**'s name")

    @set.command(name="icon", aliases=["picture", "pic"], brief="manage guild", usage="set icon https://evelina.bot/icon.png")
    @has_guild_permissions(manage_guild=True)
    async def set_icon(self, ctx: EvelinaContext, url: str = None):
        """Change your server's icon"""
        if not url:
            url = await ctx.get_attachment()
            if not url:
                return await ctx.send_help(ctx.command)
            url = url.url
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.send_warning("The image provided is not a valid URL")
        try:
            icon = await self.bot.session.get_bytes(url)
            if len(icon) > 10240 * 1024:
                return await ctx.send_warning("The image provided is larger than 10 MB and cannot be used as a server icon")
        except Exception as e:
            return await ctx.send_warning(f"Failed to download the image: {str(e)}")
        try:
            await ctx.guild.edit(icon=icon)
        except ValueError:
            return await ctx.send_warning("Invalid media type")
        await ctx.send_success(f"Set the server icon to [`Attachment`]({url})")

    @set.command(name="banner", brief="manage guild", usage="set banner https://evelina.bot/icon.png")
    @has_guild_permissions(manage_guild=True)
    async def set_banner(self, ctx: EvelinaContext, url: str = None):
        """Change your server's banner"""
        if ctx.guild.premium_tier < 2:
            return await ctx.send_warning(f"You haven't **unlocked** banners, you need at least **level 2**")
        if not url:
            url = await ctx.get_attachment()
            if not url:
                return await ctx.send_help(ctx.command)
            url = url.url
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.send_warning("The attachment provided is not a valid URL")
        banner_bytes = await self.bot.session.get_bytes(url)
        if len(banner_bytes) > 10 * 1024 * 1024:
            return await ctx.send_warning("The banner file is too large. The maximum allowed size is 10 MB.")
        try:
            await ctx.guild.edit(banner=banner_bytes)
        except ValueError:
            return await ctx.send_warning(f"Invalid **media type**")
        except Exception as e:
            return await ctx.send_warning(f"An error occurred while setting the banner: {e}")

    @set.command(name="splash", brief="manage guild", usage="set splash https://evelina.bot/icon.png")
    @has_guild_permissions(manage_guild=True)
    async def set_splash(self, ctx: EvelinaContext, url: str = None):
        """Change your server's splash"""
        if ctx.guild.premium_tier < 1:
            return await ctx.send_warning(f"You haven't **unlocked** splash")
        if not url:
            url = await ctx.get_attachment()
            if not url:
                return await ctx.send_help(ctx.command)
            url = url.url
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.send_warning("The image provided is not an url")
        icon = await self.bot.getbyte(url)
        _icon = icon.read()
        try:
            await ctx.guild.edit(splash=_icon)
        except ValueError:
            return await ctx.send_warning(f"Invalid **media type**")
        await ctx.send_success(f"Set the server icon to [`Attachment`]({url})")

    @group(name="imageonly", aliases=["imgonly", "gallery"], brief="manage channels", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def imageonly(self, ctx: EvelinaContext):
        """Let members only send images in channels"""
        return await ctx.create_pages()

    @imageonly.command(name="add", brief="manage channels", usage="imageonly add #general")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def imageonly_add(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Add an image only channel"""
        if await self.bot.db.fetchrow("SELECT * FROM only_img WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id):
            return await ctx.send_warning(f"{channel.mention} is **already** an image only channel")
        await self.bot.db.execute("INSERT INTO only_img VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"{channel.mention} is now an **image only** channel")

    @imageonly.command(name="remove", brief="manage channels", usage="imageonly remove #general")
    @has_guild_permissions(manage_channels=True)
    async def imageonly_remove(self, ctx: EvelinaContext, *, channel: Union[TextChannel, int]):
        """Remove an image only channel"""
        channel_id = self.bot.misc.convert_channel(channel)
        if not await self.bot.db.fetchrow("SELECT * FROM only_img WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id):
            return await ctx.send_warning(f"{self.bot.misc.humanize_channel(channel_id)} is **not** an image only channel")
        await self.bot.db.execute("DELETE FROM only_img WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"{self.bot.misc.humanize_channel(channel_id)} is no longer an **image only** channel")

    @imageonly.command(name="list", brief="manage channels")
    @has_guild_permissions(manage_channels=True)
    async def imageonly_list(self, ctx: EvelinaContext):
        """Returns a list of all image only channels"""
        results = await self.bot.db.fetch("SELECT * FROM only_img WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"There are **no** image only channels")
        channels = [self.bot.misc.humanize_channel(result['channel_id'], True) for result in results]
        return await ctx.paginate(channels, title="Image Only Channels", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @group(name="botonly", brief="manage channels", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def botonly(self, ctx: EvelinaContext):
        """Let only bots send in channels"""
        return await ctx.create_pages()

    @botonly.command(name="add", brief="manage channels", usage="botonly add #commands")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def botonly_add(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Add an bot only channel"""
        if await self.bot.db.fetchrow("SELECT * FROM only_bot WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id):
            return await ctx.send_warning(f"{channel.mention} is **already** an bot only channel")
        await self.bot.db.execute("INSERT INTO only_bot VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"{channel.mention} is now an **bot only** channel")

    @botonly.command(name="remove", brief="manage channels", usage="botonly remove #commands")
    @has_guild_permissions(manage_channels=True)
    async def botonly_remove(self, ctx: EvelinaContext, *, channel: Union[TextChannel, int]):
        """Remove an bot only channel"""
        channel_id = self.bot.misc.convert_channel(channel)
        if not await self.bot.db.fetchrow("SELECT * FROM only_bot WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id):
            return await ctx.send_warning(f"{self.bot.misc.humanize_channel(channel_id)} is **not** an bot only channel")
        await self.bot.db.execute("DELETE FROM only_bot WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"{self.bot.misc.humanize_channel(channel_id)} is no longer an **bot only** channel")

    @botonly.command(name="list", brief="manage channels")
    @has_guild_permissions(manage_channels=True)
    async def botonly_list(self, ctx: EvelinaContext):
        """Returns a list of all bot only channels"""
        results = await self.bot.db.fetch("SELECT * FROM only_bot WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"There are **no** bot only channels")
        channels = [self.bot.misc.humanize_channel(result['channel_id'], True) for result in results]
        return await ctx.paginate(channels, title=f"Bot Only Channels", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon if ctx.guild.icon else None})

    @group(name="textonly", brief="manage channels", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def textonly(self, ctx: EvelinaContext):
        """Let no bot commands working in channels"""
        return await ctx.create_pages()

    @textonly.command(name="add", brief="manage channels", usage="textonly add #general")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def textonly_add(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Add a text only channel"""
        if await self.bot.db.fetchrow("SELECT * FROM only_text WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id):
            return await ctx.send_warning(f"{channel.mention} is **already** a text only channel")
        await self.bot.db.execute("INSERT INTO only_text VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"{channel.mention} is now a **text only** channel")

    @textonly.command(name="remove", brief="manage channels", usage="textonly remove #general")
    @has_guild_permissions(manage_channels=True)
    async def textonly_remove(self, ctx: EvelinaContext, *, channel: Union[TextChannel, int]):
        """Remove a text only channel"""
        channel_id = self.bot.misc.convert_channel(channel)
        if not await self.bot.db.fetchrow("SELECT * FROM only_text WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id):
            return await ctx.send_warning(f"{self.bot.misc.humanize_channel(channel_id)} is **not** a text only channel")
        await self.bot.db.execute("DELETE FROM only_text WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"{self.bot.misc.humanize_channel(channel_id)} is no longer a **text only** channel")

    @textonly.command(name="list", brief="manage channels")
    @has_guild_permissions(manage_channels=True)
    async def textonly_list(self, ctx: EvelinaContext):
        """Returns a list of all text only channels"""
        results = await self.bot.db.fetch("SELECT * FROM only_text WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"There are **no** text only channels")
        channels = [self.bot.misc.humanize_channel(result['channel_id'], True) for result in results]
        return await ctx.paginate(channels, title=f"Text Only Channels", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon if ctx.guild.icon else None})

    @group(name="linkonly", brief="manage channels", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def linkonly(self, ctx: EvelinaContext):
        """Let members only send links in channels"""
        return await ctx.create_pages()

    @linkonly.command(name="add", brief="manage channels", usage="linkonly add #links")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def linkonly_add(self, ctx: EvelinaContext, *, channel: TextChannel):
        """Add a link only channel"""
        if await self.bot.db.fetchrow("SELECT * FROM only_link WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id):
            return await ctx.send_warning(f"{channel.mention} is **already** a link only channel")
        await self.bot.db.execute("INSERT INTO only_link VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"{channel.mention} is now a **link only** channel")

    @linkonly.command(name="remove", brief="manage channels", usage="linkonly remove #links")
    @has_guild_permissions(manage_channels=True)
    async def linkonly_remove(self, ctx: EvelinaContext, *, channel: Union[TextChannel, int]):
        """Remove a link only channel"""
        channel_id = self.bot.misc.convert_channel(channel)
        if not await self.bot.db.fetchrow("SELECT * FROM only_link WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id):
            return await ctx.send_warning(f"{self.bot.misc.humanize_channel(channel_id)} is **not** a link only channel")
        await self.bot.db.execute("DELETE FROM only_link WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"{self.bot.misc.humanize_channel(channel_id)} is no longer a **link only** channel")

    @linkonly.command(name="list", brief="manage channels")
    @has_guild_permissions(manage_channels=True)
    async def linkonly_list(self, ctx: EvelinaContext):
        """Returns a list of all link only channels"""
        results = await self.bot.db.fetch("SELECT * FROM only_link WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"There are **no** link only channels")
        channels = [self.bot.misc.humanize_channel(result['channel_id'], True) for result in results]
        return await ctx.paginate(channels, title=f"Link Only Channels", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon if ctx.guild.icon else None})

    @command(brief="manage guild", aliases=["dcmd"], usage="disablecmd all userinfo")
    @has_guild_permissions(manage_guild=True)
    async def disablecmd(self, ctx: EvelinaContext, scope: str, *, command: ValidCommand):
        """Disable a command in the server or a specific channel."""
        command = command.lower()
        if scope.lower() == "all":
            check = await self.bot.db.fetchrow("SELECT * FROM guild_disabled_commands WHERE guild_id = $1 AND cmd = $2", ctx.guild.id, command)
            if check:
                return await ctx.send_warning("This command is **already** disabled for the server")
            await self.bot.db.execute("INSERT INTO guild_disabled_commands (guild_id, cmd) VALUES ($1, $2)", ctx.guild.id, command)
            return await ctx.send_success(f"Successfully disabled `{command}` for the server")
        else:
            try:
                channel_id = int(scope.strip("<#>"))
            except ValueError:
                return await ctx.send_warning("Invalid channel specified. Please mention a **valid** channel or use **all**")
            check = await self.bot.db.fetchrow("SELECT * FROM channel_disabled_commands WHERE channel_id = $1 AND cmd = $2", channel_id, command)
            if check:
                return await ctx.send_warning(f"Command `{command}` is **already** disabled in <#{channel_id}>")
            await self.bot.db.execute("INSERT INTO channel_disabled_commands (guild_id, channel_id, cmd) VALUES ($1, $2, $3)", ctx.guild.id, channel_id, command)
            return await ctx.send_success(f"Successfully disabled `{command}` in <#{channel_id}>")
    
    @command(brief="manage guild", aliases=["ecmd"], usage="enablecmd all userinfo")
    @has_guild_permissions(manage_guild=True)
    async def enablecmd(self, ctx: EvelinaContext, scope: str, *, command: ValidCommand):
        """Enable a command in the server or a specific channel."""
        command = command.lower()
        if scope.lower() == "all":
            check = await self.bot.db.fetchrow("SELECT * FROM guild_disabled_commands WHERE guild_id = $1 AND cmd = $2", ctx.guild.id, command)
            if not check:
                return await ctx.send_warning("This command is **not** disabled for the server")
            await self.bot.db.execute("DELETE FROM guild_disabled_commands WHERE guild_id = $1 AND cmd = $2", ctx.guild.id, command)
            return await ctx.send_success(f"Successfully enabled `{command}` for the server")
        else:
            try:
                channel_id = int(scope.strip("<#>"))
            except ValueError:
                return await ctx.send_warning("Invalid channel specified. Please mention a **valid** channel or use **all**")
            check = await self.bot.db.fetchrow("SELECT * FROM channel_disabled_commands WHERE channel_id = $1 AND cmd = $2", channel_id, command)
            if not check:
                return await ctx.send_warning(f"Command `{command}` is **not** disabled in <#{channel_id}>")
            await self.bot.db.execute("DELETE FROM channel_disabled_commands WHERE channel_id = $1 AND cmd = $2", channel_id, command)
            return await ctx.send_success(f"Successfully enabled `{command}` in <#{channel_id}>")
        
    @command(brief="Manage guild", aliases=["dcmds"])
    @has_guild_permissions(manage_guild=True)
    async def disabledcmds(self, ctx: EvelinaContext):
        """View all disabled commands in the server"""
        guild_id = ctx.guild.id
        channel_disabled_query = "SELECT cmd, channel_id FROM channel_disabled_commands WHERE guild_id = $1"
        channel_disabled_commands = await self.bot.db.fetch(channel_disabled_query, guild_id)
        guild_disabled_query = "SELECT cmd FROM guild_disabled_commands WHERE guild_id = $1"
        guild_disabled_commands = await self.bot.db.fetch(guild_disabled_query, guild_id)
        if channel_disabled_commands:
            channel_disabled_list = "\n".join(f"`{i+1}.` **{commands['cmd']}** - <#{commands['channel_id']}>" for i, commands in enumerate(channel_disabled_commands))
            channel_disabled_color = colors.NEUTRAL
        else:
            channel_disabled_list = f"{emojis.WARNING} No disabled commands for specific channels."
            channel_disabled_color = colors.WARNING
        if guild_disabled_commands:
            guild_disabled_list = "\n".join(f"`{i+1}.` **{commands['cmd']}**" for i, commands in enumerate(guild_disabled_commands))
            guild_disabled_color = colors.NEUTRAL
        else:
            guild_disabled_list = f"{emojis.WARNING} No disabled commands for this server."
            guild_disabled_color = colors.WARNING
        embeds = [
            Embed(color=channel_disabled_color, title="Disabled Commands - Channels", description=channel_disabled_list),
            Embed(color=guild_disabled_color, title="Disabled Commands - Server", description=guild_disabled_list)
        ]
        await ctx.paginator(embeds)

    @command(brief="manage guild", aliases=["dmodule"], usage="disablemodule all leveling")
    @has_guild_permissions(manage_guild=True)
    async def disablemodule(self, ctx: EvelinaContext, scope: str, *, module: ValidCog):
        """Disable a module in the server or a specific channel."""
        module = module.lower()
        if scope.lower() == "all":
            check = await self.bot.db.fetchrow("SELECT * FROM guild_disabled_module WHERE guild_id = $1 AND module = $2", ctx.guild.id, module)
            if check:
                return await ctx.send_warning("This module is **already** disabled for the server")
            await self.bot.db.execute("INSERT INTO guild_disabled_module (guild_id, module) VALUES ($1, $2)", ctx.guild.id, module)
            return await ctx.send_success(f"Successfully disabled `{module}` for the server")
        else:
            try:
                channel_id = int(scope.strip("<#>"))
            except ValueError:
                return await ctx.send_warning("Invalid channel specified. Please mention a **valid** channel or use **all**")
            check = await self.bot.db.fetchrow("SELECT * FROM channel_disabled_module WHERE channel_id = $1 AND module = $2", channel_id, module)
            if check:
                return await ctx.send_warning(f"Module `{module}` is **already** disabled in <#{channel_id}>")
            await self.bot.db.execute("INSERT INTO channel_disabled_module (guild_id, channel_id, module) VALUES ($1, $2, $3)", ctx.guild.id, channel_id, module)
            return await ctx.send_success(f"Successfully disabled `{module}` in <#{channel_id}>")
    
    @command(brief="manage guild", aliases=["emodule"], usage="enablemodule all leveling")
    @has_guild_permissions(manage_guild=True)
    async def enablemodule(self, ctx: EvelinaContext, scope: str, *, module: ValidCog):
        """Enable a module in the server or a specific channel."""
        module = module.lower()
        if scope.lower() == "all":
            check = await self.bot.db.fetchrow("SELECT * FROM guild_disabled_module WHERE guild_id = $1 AND module = $2", ctx.guild.id, module)
            if not check:
                return await ctx.send_warning("This module is **not** disabled for the server")
            await self.bot.db.execute("DELETE FROM guild_disabled_module WHERE guild_id = $1 AND module = $2", ctx.guild.id, module)
            return await ctx.send_success(f"Successfully enabled `{module}` for the server")
        else:
            try:
                channel_id = int(scope.strip("<#>"))
            except ValueError:
                return await ctx.send_warning("Invalid channel specified. Please mention a **valid** channel or use **all**")
            check = await self.bot.db.fetchrow("SELECT * FROM channel_disabled_module WHERE channel_id = $1 AND module = $2", channel_id, module)
            if not check:
                return await ctx.send_warning(f"Module `{module}` is **not** disabled in <#{channel_id}>")
            await self.bot.db.execute("DELETE FROM channel_disabled_module WHERE channel_id = $1 AND module = $2", channel_id, module)
            return await ctx.send_success(f"Successfully enabled `{module}` in <#{channel_id}>")
    
    @command(brief="Manage guild", aliases=["dmodules"])
    @has_guild_permissions(manage_guild=True)
    async def disabledmodules(self, ctx: EvelinaContext):
        """View all disabled modules in the server"""
        guild_id = ctx.guild.id
        channel_disabled_query = "SELECT module, channel_id FROM channel_disabled_module WHERE guild_id = $1"
        channel_disabled_modules = await self.bot.db.fetch(channel_disabled_query, guild_id)
        guild_disabled_query = "SELECT module FROM guild_disabled_module WHERE guild_id = $1"
        guild_disabled_modules = await self.bot.db.fetch(guild_disabled_query, guild_id)
        if channel_disabled_modules:
            channel_disabled_list = "\n".join(f"`{i+1}.` **{module['module']}** - <#{module['channel_id']}>" for i, module in enumerate(channel_disabled_modules))
            channel_disabled_color = colors.NEUTRAL
        else:
            channel_disabled_list = f"{emojis.WARNING} No disabled modules for specific channels."
            channel_disabled_color = colors.WARNING
        if guild_disabled_modules:
            guild_disabled_list = "\n".join(f"`{i+1}.` **{module['module']}**" for i, module in enumerate(guild_disabled_modules))
            guild_disabled_color = colors.NEUTRAL
        else:
            guild_disabled_list = f"{emojis.WARNING} No disabled modules for this server."
            guild_disabled_color = colors.WARNING
        embeds = [
            Embed(color=channel_disabled_color, title="Disabled Modules - Channels", description=channel_disabled_list),
            Embed(color=guild_disabled_color, title="Disabled Modules - Server", description=guild_disabled_list)
        ]
        await ctx.paginator(embeds)

    @group(name="autopublish", aliases=["ap"], brief="manage channels", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_channels=True)
    async def autopublish(self, ctx: EvelinaContext):
        """Manage autopublish channels"""
        return await ctx.create_pages()

    @autopublish.command(name="add", brief="manage channels", usage="autopublish add #updates")
    @has_guild_permissions(manage_channels=True)
    async def autopublish_add(self, ctx: EvelinaContext, channel: TextChannel):
        """Add a channel to autopublish"""
        if channel.type != ChannelType.news:
            return await ctx.send_warning(f"Channel {channel.mention} is not an announcement channel")
        check = await self.bot.db.fetchrow("SELECT channel_id FROM autopublish WHERE channel_id = $1", channel.id)
        if check:
            return await ctx.send_warning(f"Channel {channel.mention} already exist for autopublish")
        await self.bot.db.execute("INSERT INTO autopublish (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Added {channel.mention} as autopublish channel")
    
    @autopublish.command(name="remove", brief="manage channels", usage="autopublish remove #updates")
    @has_guild_permissions(manage_channels=True)
    async def autopublish_remove(self, ctx: EvelinaContext, channel: TextChannel):
        """Remove a channel from autopublish"""
        check = await self.bot.db.fetchrow("SELECT channel_id FROM autopublish WHERE channel_id = $1", channel.id)
        if not check:
            return await ctx.send_warning(f"Channel {channel.mention} not exist for autopublish")
        await self.bot.db.execute("DELETE FROM autopublish WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Removed {channel.mention} as autopublsh channel")
    
    @autopublish.command(name="list", brief="manage channels")
    @has_guild_permissions(manage_channels=True)
    async def autopublish_list(self, ctx: EvelinaContext):
        """List all autopublish channels"""
        results = await self.bot.db.fetch("SELECT channel_id FROM autopublish WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are no autopublish channels set")
        channels = []
        for result in results:
            channel = self.bot.get_channel(result["channel_id"])
            if channel:
                channels.append(channel.mention)
            else:
                channels.append(result['channel_id'])
        await ctx.paginate(channels, "Autopublish Channels", {"name": ctx.guild.name, "icon_url": ctx.guild.icon if ctx.guild.icon else None})

    @group(name="reposter", aliases=["rp"], invoke_without_command=True, case_insensitive=True)
    async def reposter(self, ctx: EvelinaContext):
        """Fine tune reposts which can be used in your server"""

    @reposter.command(name="embed", brief="manage guild", usage="reposter embed on")
    @has_guild_permissions(manage_guild=True)
    async def reposter_embed(self, ctx: EvelinaContext, option: str):
        """Enable or disable embeds for reposts"""
        check = await self.bot.db.fetchrow("SELECT * FROM reposter WHERE guild_id = $1", ctx.guild.id)
        if option.lower() == "on":
            if check:
                await self.bot.db.execute("UPDATE reposter SET embed = $1 WHERE guild_id = $2", True, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO reposter (guild_id, embed) VALUES ($1, $2)", ctx.guild.id, True)
            return await ctx.send_success("Enabled embeds for reposts")
        elif option.lower() == "off":
            if check:
                await self.bot.db.execute("UPDATE reposter SET embed = $1 WHERE guild_id = $2", False, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO reposter (guild_id, embed) VALUES ($1, $2)", ctx.guild.id, False)
            return await ctx.send_success("Disabled embeds for reposts")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
        
    @reposter.command(name="prefix", brief="manage guild", usage="reposter prefix evelina")
    @has_guild_permissions(manage_guild=True)
    async def reposter_prefix(self, ctx: EvelinaContext, prefix: str):
        """Change the prefix for reposts"""
        check = await self.bot.db.fetchrow("SELECT * FROM reposter WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("UPDATE reposter SET prefix = $1 WHERE guild_id = $2", prefix, ctx.guild.id)
        else:
            await self.bot.db.execute("INSERT INTO reposter (guild_id, prefix) VALUES ($1, $2)", ctx.guild.id, prefix)
        return await ctx.send_success(f"Changed the prefix for reposts to `{prefix}`")
    
    @reposter.command(name="delete", brief="manage guild", usage="reposter delete on")
    @has_guild_permissions(manage_guild=True)
    async def reposter_delete(self, ctx: EvelinaContext, option: str):
        """Enable or disable deletion of trigger messages"""
        check = await self.bot.db.fetchrow("SELECT * FROM reposter WHERE guild_id = $1", ctx.guild.id)
        if option.lower() == "on":
            if check:
                await self.bot.db.execute("UPDATE reposter SET delete = $1 WHERE guild_id = $2", True, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO reposter (guild_id, delete) VALUES ($1, $2)", ctx.guild.id, True)
            return await ctx.send_success("Enabled deletion of reposted messages")
        elif option.lower() == "off":
            if check:
                await self.bot.db.execute("UPDATE reposter SET delete = $1 WHERE guild_id = $2", False, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO reposter (guild_id, delete) VALUES ($1, $2)", ctx.guild.id, False)
            return await ctx.send_success("Disabled deletion of reposted messages")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
        
    @reposter.command(name="status", brief="manage guild", usage="reposter status on")
    @has_guild_permissions(manage_guild=True)
    async def reposter_status(self, ctx: EvelinaContext, option: str):
        """Enable or disable reposts in your server"""
        check = await self.bot.db.fetchrow("SELECT * FROM reposter WHERE guild_id = $1", ctx.guild.id)
        if option.lower() == "on":
            if check:
                await self.bot.db.execute("UPDATE reposter SET status = $1 WHERE guild_id = $2", True, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO reposter (guild_id, status) VALUES ($1, $2)", ctx.guild.id, True)
            return await ctx.send_success("Enabled status for reposts")
        elif option.lower() == "off":
            if check:
                await self.bot.db.execute("UPDATE reposter SET status = $1 WHERE guild_id = $2", False, ctx.guild.id)
            else:
                await self.bot.db.execute("INSERT INTO reposter (guild_id, status) VALUES ($1, $2)", ctx.guild.id, False)
            return await ctx.send_success("Disabled status for reposts")
        else:
            return await ctx.send_warning("Invalid option. Valid options are: `on` & `off`")
        
    @reposter.command(name="channel", brief="manage guild", usage="reposter channel #repost")
    @has_guild_permissions(manage_guild=True)
    async def reposter_channel(self, ctx: EvelinaContext, channel: TextChannel):
        """Add or remove a channel for reposts blacklist"""
        check = await self.bot.db.fetchrow("SELECT * FROM reposter_channels WHERE guild_id = $1", ctx.guild.id)
        if check:
            await self.bot.db.execute("DELETE FROM reposter_channels WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
            return await ctx.send_success(f"Removed {channel.mention} from the reposts blacklist")
        else:
            await self.bot.db.execute("INSERT INTO reposter_channels (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
            return await ctx.send_success(f"Added {channel.mention} to the reposts blacklist")
        
    @group(name="cleanup", brief="administrator", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(administrator=True)
    async def cleanup(self, ctx: EvelinaContext):
        """Cleanup your server database"""
        return await ctx.create_pages()
    
    @cleanup.command(name="role", brief="administrator", usage="cleanup role 1272482302227910708")
    @has_guild_permissions(administrator=True)
    async def cleanup_role(self, ctx: EvelinaContext, role: int):
        """Delete a channel from database"""
        for guild in self.bot.guilds:
            role_obj = guild.get_role(role)
            if role_obj and guild.id is not ctx.guild.id:
                return await ctx.send_warning(f"Role isn't from this server")
        deleted_from = []
        for delete in ["autorole", "autorole_bots", "autorole_humans", "counters", "invites_rewards", 
                    "jail", "level_multiplier", "level_multiplier_voice", "level_rewards", "booster_award", 
                    "lockdown_role", "mute_images", "mute_reactions", "reactionrole", "suggestions_module",
                    "voicerole_default", "warns_rewards", "restrictcommand"]:
            existing_entries = await self.bot.db.fetch(f"SELECT * FROM {delete} WHERE role_id = $1", role)
            if existing_entries:
                await self.bot.db.execute(f"DELETE FROM {delete} WHERE role_id = $1", role)
                deleted_from.append(delete)
        if deleted_from:
            await ctx.send_success(f"Role **{role}** was deleted from the following features:\n```{', '.join(deleted_from)}```")
        else:
            await ctx.send_warning(f"No entries found for the role **{role}**")

    @cleanup.command(name="channel", brief="administrator", usage="cleanup channel 1272482302227910708")
    @has_guild_permissions(administrator=True)
    async def cleanup_channel(self, ctx: EvelinaContext, channel: int):
        """Delete a role from datebase"""
        for guild in self.bot.guilds:
            channel_obj = guild.get_channel(channel)
            if channel_obj and guild.id is not ctx.guild.id:
                return await ctx.send_warning(f"Channel isn't from this server")
        deleted_from = []
        for delete in ["welcome", "boost", "leave", "autopublish", 
                    "autoreact_channel", "autothread", "bumpreminder", "button_message", "button_role", 
                    "button_settings", "channel_disabled_commands", "channel_disabled_module", "confess", "giveaway",
                    "jail", "number_counter", "only_bot", "only_img",
                    "only_link", "only_text", "paginate_embeds", "paypal", "quotes",
                    "reactionrole", "reminder", "reposter_channels", "snipes", "snipes_edit",
                    "snipes_reaction", "starboard", "stickymessage", "suggestions_module", "timer",
                    "autopost_twitch", "vouches_settings"]:
            existing_entries = await self.bot.db.fetch(f"SELECT * FROM {delete} WHERE channel_id = $1", channel)
            if existing_entries:
                await self.bot.db.execute(f"DELETE FROM {delete} WHERE channel_id = $1", channel)
                deleted_from.append(delete)
        if deleted_from:
            await ctx.send_success(f"Channel **{channel}** was deleted from the following features:\n```{', '.join(deleted_from)}```")
        else:
            await ctx.send_warning(f"No entries found for the channel **{channel}**")

    @group(name="freegames", aliases=["fg"], invoke_without_command=True, case_insensitive=True)
    async def freegames(self, ctx: EvelinaContext):
        with EpicGames() as epic_games:
            free_games = epic_games.get_info_all_games()
        embeds = []
        for game in free_games:
            if game["discountPrice"] == "0":
                embed = Embed(title=game["title"], color=colors.NEUTRAL, description=game["description"])
                embed.add_field(name="Original Price", value=game["originalPrice"], inline=True)
                embed.add_field(name="Discount Price", value="$0.00", inline=True)
                embed.add_field(name="Epicgames Launcher", value=f"[Get Game](https://evelina.bot/epicgames/{game['gameSlug']})", inline=True)
                embed.set_image(url=game["gameImgUrl"])
                embeds.append(embed)
        return await ctx.paginator(embeds)
    
    @freegames.command(name="add", brief="administrator", usage="freegames add #freegames")
    @has_guild_permissions(administrator=True)
    async def freegames_add(self, ctx: EvelinaContext, channel: Union[TextChannel, Thread]):
        """Add a channel to freegames"""
        check = await self.bot.db.fetchrow("SELECT channel_id FROM freegames WHERE guild_id = $1", ctx.guild.id)
        if check:
            return await ctx.send_warning(f"Channel {self.bot.get_channel(check['channel_id'])} already exist for freegames")
        await self.bot.db.execute("INSERT INTO freegames (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Added {channel.mention} as freegames channel")
    
    @freegames.command(name="remove", brief="administrator")
    @has_guild_permissions(administrator=True)
    async def freegames_remove(self, ctx: EvelinaContext):
        """Remove a channel from freegames"""
        check = await self.bot.db.fetchrow("SELECT channel_id FROM freegames WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning(f"There are no freegames channels set")
        await self.bot.db.execute("DELETE FROM freegames WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success(f"Removed freegames channel")
    
    @freegames.command(name="list", brief="administrator")
    @has_guild_permissions(administrator=True)
    async def freegames_list(self, ctx: EvelinaContext):
        """List all freegames channels"""
        results = await self.bot.db.fetchrow("SELECT channel_id FROM freegames WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are no freegames channels set")
        return await ctx.evelina_send(f"Your freegames channel is {ctx.guild.get_channel_or_thread(results['channel_id']).mention}")

    @group(name="pingtimeout", aliases=["pto"], invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def pingtimeout(self, ctx: EvelinaContext):
        """Manage ping timeout"""
        return await ctx.create_pages()
    
    @pingtimeout.command(name="add", brief="manage guild", usage="pingtimeout add @games 5m")
    @has_guild_permissions(manage_guild=True)
    async def pingtimeout_add(self, ctx: EvelinaContext, role: NewRoleConverter, timeout: ValidTime):
        """Add a role to ping timeout"""
        check = await self.bot.db.fetchrow("SELECT * FROM pingtimeout WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if check:
            return await ctx.send_warning(f"Role {role.mention} already exist for ping timeout")
        await role.edit(mentionable=True)
        await self.bot.db.execute("INSERT INTO pingtimeout (guild_id, role_id, timeout, last_ping) VALUES ($1, $2, $3, $4)", ctx.guild.id, role.id, timeout, 0)
        return await ctx.send_success(f"Added {role.mention} with a {self.bot.misc.humanize_time(timeout)} timeout")
    
    @pingtimeout.command(name="remove", brief="manage guild", usage="pingtimeout remove @games")
    @has_guild_permissions(manage_guild=True)
    async def pingtimeout_remove(self, ctx: EvelinaContext, role: Union[Role, int]):
        """Remove a role from ping timeout"""
        role_id = self.bot.misc.convert_role(role)
        check = await self.bot.db.fetchrow("SELECT * FROM pingtimeout WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        if not check:
            return await ctx.send_warning(f"Role {self.bot.misc.humanize_role(ctx.guild, role_id)} not exist for ping timeout")
        await self.bot.db.execute("DELETE FROM pingtimeout WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        return await ctx.send_success(f"Removed {self.bot.misc.humanize_role(ctx.guild, role_id)} from ping timeout")
    
    @pingtimeout.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def pingtimeout_list(self, ctx: EvelinaContext):
        """List all ping timeout roles"""
        results = await self.bot.db.fetch("SELECT role_id, timeout, last_ping FROM pingtimeout WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are no ping timeout roles set")
        roles = []
        for result in results:
            role = self.bot.misc.humanize_role(ctx.guild, result["role_id"])
            timeout = self.bot.misc.humanize_time(result["timeout"])
            last_ping = f"<t:{result['last_ping']}:R>"
            roles.append(f"{role} - {timeout} ({last_ping})")
        return await ctx.paginate(roles, "Ping Timeout Roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon if ctx.guild.icon else None})

    @group(name="revive", aliases=["rv"], invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def revive(self, ctx: EvelinaContext):
        """Revive a channel"""
        return await ctx.create_pages()
    
    @revive.command(name="add", brief="manage guild", usage="revive add #general 15m @everyone, get active")
    @has_guild_permissions(manage_guild=True)
    async def revive_add(self, ctx: EvelinaContext, channel: TextChannel, timeout: ValidTime, *, code: str):
        """Add a channel to revive"""
        check = await self.bot.db.fetchrow("SELECT * FROM revive WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if check:
            return await ctx.send_warning(f"Channel {channel.mention} already exist for revive")
        await self.bot.db.execute("INSERT INTO revive (guild_id, channel_id, timeout, last_message, message) VALUES ($1, $2, $3, $4, $5)", ctx.guild.id, channel.id, timeout, datetime.now().timestamp(), code)
        return await ctx.send_success(f"Added {channel.mention} with a {self.bot.misc.humanize_time(timeout)} timeout for revive")
    
    @revive.command(name="remove", brief="manage guild", usage="revive remove #general")
    @has_guild_permissions(manage_guild=True)
    async def revive_remove(self, ctx: EvelinaContext, channel: Union[TextChannel, int]):
        """Remove a channel from revive"""
        channel_id = self.bot.misc.convert_channel(channel)
        check = await self.bot.db.fetchrow("SELECT * FROM revive WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        if not check:
            return await ctx.send_warning(f"Channel {self.bot.misc.humanize_channel(channel_id)} not exist for revive")
        await self.bot.db.execute("DELETE FROM revive WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"Removed {self.bot.misc.humanize_channel(channel_id)} from revive")
    
    @revive.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def revive_list(self, ctx: EvelinaContext):
        """List all revive channels"""
        results = await self.bot.db.fetch("SELECT channel_id, timeout, last_message FROM revive WHERE guild_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning("There are no revive channels set")
        channels = []
        for result in results:
            channel = self.bot.misc.humanize_channel(result["channel_id"])
            timeout = self.bot.misc.humanize_time(result["timeout"])
            last_message = f"<t:{result['last_message']}:R>"
            channels.append(f"{channel} - {timeout} ({last_message})")
        return await ctx.paginate(channels, "Revive Channels", {"name": ctx.guild.name, "icon_url": ctx.guild.icon if ctx.guild.icon else None})

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Config(bot))