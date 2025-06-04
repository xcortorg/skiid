import discord

from discord import TextChannel
from discord.ext.commands import Cog, group, command, has_guild_permissions, bot_has_guild_permissions

from data.pfps import PFPS

from modules.styles import colors
from modules.evelinabot import Evelina
from modules.helpers import EvelinaContext
from modules.validators import ValidImageURL

class Autopost(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.description = "Automatically send pfps and banners to a channel"

    @group(name="autopfp", invoke_without_command=True, case_insensitive=True)
    async def autopfp(self, ctx: EvelinaContext):
        """Automatically send pfps to a channel"""
        return await ctx.create_pages()

    @autopfp.command(name="add", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(administrator=True)
    async def autopfp_add(self, ctx: EvelinaContext, channel: TextChannel, category: str = "random"):
        """Add an autopfp channel"""
        valid_categories = ["random", "females", "males", "animes"]
        if category not in valid_categories:
            return await ctx.send_warning(f"**Invalid category.**\nPlease choose from: **random**, **females**, **males**, **animes**.")
        await self.bot.db.execute("INSERT INTO autopost VALUES ($1,$2,$3,$4) ON CONFLICT (guild_id, type, category) DO UPDATE SET channel_id = $4", ctx.guild.id, "pfps", category, channel.id)
        return await ctx.send_success(f"Sending **{category}** pfps to {channel.mention}")

    @autopfp.command(name="remove", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(administrator=True)
    async def autopfp_remove(self, ctx: EvelinaContext, category: str = "random"):
        """Remove an autopfp channel"""
        valid_categories = ["random", "females", "males", "animes"]
        if category not in valid_categories:
            return await ctx.send_warning(f"**Invalid category.**\nPlease choose from: **random**, **females**, **males**, **animes**.")
        await self.bot.db.execute("DELETE FROM autopost WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "pfps", category)
        return await ctx.send_success(f"Stopped sending **{category}** pfps")

    @autopfp.command(name="name", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    async def autopfp_name(self, ctx: EvelinaContext, category: str, *, name: str):
        """Change the way how the bot webhook is named"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "pfps", category)
        if not res:
            return await ctx.send_warning(f"**{category}** is not an autopfp category.")
        if name in ["remove", "reset", "none"]:
            await self.bot.db.execute("UPDATE autopost SET webhook_name = NULL WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "pfps", category)
            return await ctx.send_success(f"Reset the name for **{category}**")
        else:
            await self.bot.db.execute("UPDATE autopost SET webhook_name = $4 WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "pfps", category, name)
            return await ctx.send_success(f"Set the webhook-name for **{category}** to **{name}**")

    @autopfp.command(name="avatar", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    async def autopfp_avatar(self, ctx: EvelinaContext, category: str, avatar: ValidImageURL):
        """Change the way how the bot webhook is avatar"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "pfps", category)
        if not res:
            return await ctx.send_warning(f"**{category}** is not an autopfp category.")
        if avatar is None:
            await self.bot.db.execute("UPDATE autopost SET webhook_avatar = NULL WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "pfps", category)
            return await ctx.send_success(f"Reset the avatar for **{category}**")
        else:
            await self.bot.db.execute("UPDATE autopost SET webhook_avatar = $4 WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "pfps", category, avatar)
            return await ctx.send_success(f"Set the webhook-avatar for **{category}** to [**this**]({avatar})")

    @group(name="autobanner", invoke_without_command=True, case_insensitive=True)
    async def autobanner(self, ctx: EvelinaContext):
        """Automatically send banners to a channel"""
        return await ctx.create_pages()

    @autobanner.command(name="add", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(administrator=True)
    async def autobanner_add(self, ctx: EvelinaContext, channel: discord.TextChannel):
        """Add an autobanner channel"""
        await self.bot.db.execute("INSERT INTO autopost (guild_id, type, category, channel_id) VALUES ($1, $2, $3, $4) ON CONFLICT (guild_id, type, category) DO UPDATE SET channel_id = $4", ctx.guild.id, "banners", "banners", channel.id)
        return await ctx.send_success(f"Sending **banners** to {channel.mention}")

    @autobanner.command(name="remove", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    @bot_has_guild_permissions(administrator=True)
    async def autobanner_remove(self, ctx: EvelinaContext):
        """Remove an autobanner channel"""
        await self.bot.db.execute("DELETE FROM autopost WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "banners", "banners")
        return await ctx.send_success(f"Stopped sending **banners**")

    @autobanner.command(name="name", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    async def autobanner_name(self, ctx: EvelinaContext, *, name: str):
        """Change the way how the bot webhook is named"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "banners", "banners")
        if not res:
            return await ctx.send_warning(f"Autopost for **banners** is **not** enabled.")
        if name in ["remove", "reset", "none"]:
            await self.bot.db.execute("UPDATE autopost SET webhook_name = NULL WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "banners", "banners")
            return await ctx.send_success(f"Reset the webhook-name for **banners**")
        else:
            await self.bot.db.execute("UPDATE autopost SET webhook_name = $4 WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "banners", "banners", name)
            return await ctx.send_success(f"Set the webhook-name for **banners** to **{name}**")

    @autobanner.command(name="avatar", brief="manage server")
    @has_guild_permissions(manage_guild=True)
    async def autobanner_avatar(self, ctx: EvelinaContext, avatar: ValidImageURL):
        """Change the way how the bot webhook is avatar"""
        res = await self.bot.db.fetchrow("SELECT * FROM autopost WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "banners", "banners")
        if not res:
            return await ctx.send_warning(f"Autopost for **banners** is **not** enabled.")
        if avatar is None:
            await self.bot.db.execute("UPDATE autopost SET webhook_avatar = NULL WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "banners", "banners")
            return await ctx.send_success(f"Reset the avatar for **banners**")
        else:
            await self.bot.db.execute("UPDATE autopost SET webhook_avatar = $4 WHERE guild_id = $1 AND type = $2 AND category = $3", ctx.guild.id, "banners", "banners", avatar)
            return await ctx.send_success(f"Set the avatar for **banners** to [**this**]({avatar})")

    @command(name="imagecount")
    async def imagecount(self, ctx: EvelinaContext):
        """Get the count of how much images are available for every category"""
        counts = {"Females": len(PFPS.females), "Males": len(PFPS.males), "Animes": len(PFPS.animes), "Banners": len(PFPS.banners)}
        embed = discord.Embed(title=f"Image Counts ({sum(counts.values()):,})", color=colors.NEUTRAL)
        embed.set_author(name=ctx.me.name, icon_url=ctx.me.display_avatar.url)
        embed.description = "\n".join(f"**{key}:** `{value:,}`" for key, value in counts.items())
        return await ctx.send(embed=embed)

async def setup(bot: Evelina):
    return await bot.add_cog(Autopost(bot))