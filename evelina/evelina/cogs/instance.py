import re
import datetime

from typing import Union

from discord import CustomActivity, Invite
from discord.ext.commands import Cog, group

from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext

class Instance(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Instance commands"

    @group(name="instance", brief="Instance Owner", invoke_without_command=True)
    async def instance(self, ctx: EvelinaContext):
        """Instance commands"""
        return await ctx.create_pages()

    @instance.command(name="avatar", brief="Instance Owner", usage="instance avatar https://evelina.bot/img.png")
    async def instance_avatar(self, ctx: EvelinaContext, url: str = None):
        """Change avatar of your bot instance"""
        check = await self.bot.db.fetchrow("SELECT owner_id FROM instance WHERE user_id = $1", self.bot.application_id)
        if not check:
            return await ctx.send_warning("You can only use this command on a instance")
        if check['owner_id'] != ctx.author.id:
            return await ctx.send_warning("You are not **authorized** to use this command")
        if url == "none":
            await ctx.bot.user.edit(avatar=None)
            application = await self.bot.application_info()
            await application.edit(icon=image_data)
            return await ctx.send_success("Bot avatar has been successfully removed!")
        if url is None:
            url = await ctx.get_attachment()
            if url is None:
                return await ctx.send_help(ctx.command)
            else:
                url = url.url
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.send_warning("The image provided is not a valid URL")
        try:
            image_data = await self.bot.session.get_bytes(url)
            if not image_data:
                return await ctx.send_warning("Failed to fetch image from the URL provided.")
            await ctx.bot.user.edit(avatar=image_data)
            application = await self.bot.application_info()
            await application.edit(icon=image_data)
            await ctx.send_success("Bot avatar has been successfully updated!")
        except Exception as e:
            await ctx.send_warning(f"An error occurred while changing the avatar\n ```{e}```")

    @instance.command(name="banner", brief="Instance Owner", usage="instance banner https://evelina.bot/img.png")
    async def instance_banner(self, ctx: EvelinaContext, url: str = None):
        """Change banner of your bot instance"""
        check = await self.bot.db.fetchrow("SELECT owner_id FROM instance WHERE user_id = $1", self.bot.application_id)
        if not check:
            return await ctx.send_warning("You can only use this command on a instance")
        if check['owner_id'] != ctx.author.id:
            return await ctx.send_warning("You are not **authorized** to use this command")
        if url == "none":
            await ctx.bot.user.edit(banner=None)
            return await ctx.send_success("Bot banner has been successfully removed!")
        if url is None:
            url = await ctx.get_attachment()
            if url is None:
                return await ctx.send_help(ctx.command)
            else:
                url = url.url
        regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
        if not re.findall(regex, url):
            return await ctx.send_warning("The image provided is not a valid URL")
        try:
            image_data = await self.bot.session.get_bytes(url)
            if not image_data:
                return await ctx.send_warning("Failed to fetch image from the URL provided.")
            await ctx.bot.user.edit(banner=image_data)
            await ctx.send_success("Bot banner has been successfully updated!")
        except Exception as e:
            await ctx.send_warning(f"An error occurred while changing the banner\n ```{e}```")

    @instance.command(name="status", brief="Instance Owner", usage="instance status Doing something")
    async def instance_status(self, ctx: EvelinaContext, *, status: str):
        """Change status of your bot instance"""
        check = await self.bot.db.fetchrow("SELECT owner_id FROM instance WHERE user_id = $1", self.bot.application_id)
        if not check:
            return await ctx.send_warning("You can only use this command on a instance")
        if check['owner_id'] != ctx.author.id:
            return await ctx.send_warning("You are not **authorized** to use this command")
        if len(status) > 25:
            return await ctx.send_warning("Status should be less than 25 characters")
        await ctx.bot.change_presence(activity=CustomActivity(name=status))
        await self.bot.db.execute("UPDATE instance SET status = $1 WHERE user_id = $2", status, self.bot.application_id)
        return await ctx.send_success(f"Bot status has been successfully updated to:\n```{status}```")
    
    @instance.command(name="description", aliases=["bio"], brief="Instance Owner", usage="instance description Doing something")
    async def instance_bio(self, ctx: EvelinaContext, *, description: str):
        """Change description of your bot instance"""
        check = await self.bot.db.fetchrow("SELECT owner_id FROM instance WHERE user_id = $1", self.bot.application_id)
        if not check:
            return await ctx.send_warning("You can only use this command on a instance")
        if check['owner_id'] != ctx.author.id:
            return await ctx.send_warning("You are not **authorized** to use this command")
        if description == "none":
            application = await self.bot.application_info()
            await application.edit(description=None)
            return await ctx.send_success("Bot description has been successfully removed!")
        if len(description) > 400:
            return await ctx.send_warning("Description should be less than 400 characters")
        application = await self.bot.application_info()
        await application.edit(description=description)
        return await ctx.send_success(f"Bot description has been successfully updated to:\n```{description}```")
    
    @instance.command(name="whitelist", brief="Instance Owner", usage="instance whitelist /evelina")
    async def instance_whitelist(self, ctx: EvelinaContext, server: Invite):
        """Whitelist a server using a product key"""
        check = await self.bot.db.fetchrow("SELECT owner_id FROM instance WHERE user_id = $1", self.bot.application_id)
        if not check:
            return await ctx.send_warning("You can only use this command on a instance")
        if ctx.author.id != check['owner_id']:
            return await ctx.send_warning("You are not **authorized** to use this command")
        instance_data = await self.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1", self.bot.application_id)
        if not instance_data:
            return await ctx.send_warning(f"Instance **{ctx.me.mention}** not found")
        instance_check = await self.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1 AND guild_id = $2", self.bot.application_id, server.guild.id)
        if instance_check:
            return await ctx.send_warning(f"Instance **{ctx.me.mention}** is already in {await self.bot.manage.guild_name(server.guild.id, True)}")
        instance_check_addon = await self.bot.db.fetchrow("SELECT * FROM instance_addon WHERE user_id = $1 AND guild_id = $2", self.bot.application_id, server.guild.id)
        if instance_check_addon:
            return await ctx.send_warning(f"Instance **{ctx.me.mention}** is already in {await self.bot.manage.guild_name(server.guild.id, True)}")
        await self.bot.db.execute("INSERT INTO instance_addon VALUES ($1, $2, $3, $4)", self.bot.application_id, datetime.datetime.now().timestamp(), instance_data['owner_id'], server.guild.id)
        await self.bot.manage.logging(ctx.author, f"Whitelisted {self.bot.manage.guild_name(server.guild.id, True)}", "system")
        return await ctx.send_success(f"Instance **{ctx.me.mention}** has been successfully added to {await self.bot.manage.guild_name(server.guild.id, True)}")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Instance(bot))