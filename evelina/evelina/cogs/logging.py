import json

from typing import Union

from discord import User, TextChannel, Thread, Embed, Role, utils
from discord.ext.commands import Cog, has_guild_permissions, group
from discord.errors import Forbidden

from modules.styles import colors
from modules.helpers import EvelinaContext
from modules.evelinabot import Evelina

class Logging(Cog):
    def __init__(self, bot: Evelina):
        self.bot = bot

    async def update_logging_blacklist(self, ctx: EvelinaContext, column: str, item_id: int, add: bool):
        current_blacklist = await self.bot.db.fetchval(f"SELECT {column} FROM logging WHERE guild_id = $1", ctx.guild.id)
        if not current_blacklist:
            current_list = []
        else:
            current_list = json.loads(current_blacklist) if isinstance(current_blacklist, str) else current_blacklist
        if column == "ignored_roles":
            clean_column = "roles"
            item = ctx.guild.get_role(item_id)
            item_mention = item.mention if item else f"<@&{item_id}>"
        elif column == "ignored_channels":
            clean_column = "channels"
            item = ctx.guild.get_channel(item_id)
            item_mention = item.mention if item else f"<#{item_id}>"
        elif column == "ignored_users":
            clean_column = "users"
            item = ctx.guild.get_member(item_id) or await self.bot.fetch_user(item_id)
            item_mention = item.mention if item else f"<@{item_id}>"
        if add:
            if item_id in current_list:
                return await ctx.send_warning(f"This {clean_column[:-1]} is already in the logging ignore list")
            current_list.append(item_id)
            message = f"Added {clean_column[:-1]} {item_mention} to the logging ignore list"
        else:
            if item_id not in current_list:
                return await ctx.send_warning(f"This {clean_column[:-1]} is not in the logging ignore list")
            current_list.remove(item_id)
            message = f"Removed {clean_column[:-1]} {item_mention} from the logging ignore list"
        await self.bot.db.execute(f"UPDATE logging SET {column} = $1 WHERE guild_id = $2", json.dumps(current_list), ctx.guild.id)
        await ctx.send_success(message)

    @group(name="logs", aliases=["logging"], description="Log events in your server", invoke_without_command=True, case_insensitive=True)
    async def logs(self, ctx: EvelinaContext):
        return await ctx.create_pages()
    
    @logs.command(name="list", brief="manage guild", description="List all the logging channels")
    async def logs_list(self, ctx: EvelinaContext):
        record = await self.bot.db.fetchrow("SELECT * FROM logging WHERE guild_id = $1", ctx.guild.id)
        if not record:
            return await ctx.send_warning("No logging channels are set.")
        embed = Embed(color=colors.NEUTRAL, title="Logging Channels")
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        for key, value in record.items():
            if value:
                channel = ctx.guild.get_channel(value)
                if not channel:
                    continue
                embed.add_field(name=key.title(), value=channel.mention, inline=True)
        await ctx.send(embed=embed)

    @logs.group(name="add", description="Add logging for specific events", invoke_without_command=True, case_insensitive=True)
    async def logs_add(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @logs.group(name="remove", description="Remove logging for specific events", invoke_without_command=True, case_insensitive=True)
    async def logs_remove(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    async def add_logging(self, ctx: EvelinaContext, column: str, channel: Union[TextChannel, Thread]):
        await self.bot.db.execute(f"INSERT INTO logging (guild_id, {column}) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET {column} = $2", ctx.guild.id, channel.id)
        await ctx.send_success(f"Sending **{column.replace('_', ' ')} logs** to {channel.mention}")

    async def remove_logging(self, ctx, column: str):
        if await self.bot.db.fetchval(f"SELECT {column} FROM logging WHERE guild_id = $1", ctx.guild.id):
            await self.bot.db.execute(f"UPDATE logging SET {column} = $1 WHERE guild_id = $2", None, ctx.guild.id)
            return await ctx.send_success(f"No longer logging **{column.replace('_', ' ')}**")
        return await ctx.send_warning(f"{column.replace('_', ' ')} logging is **not** enabled.")

    @logs_add.command(name="messages", brief="manage guild", usage="logs add messages #message-logs", description="Log message related events")
    @has_guild_permissions(manage_guild=True)
    async def add_messages(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread]):
        await self.add_logging(ctx, "messages", channel)

    @logs_add.command(name="guild", brief="manage guild", usage="logs add guild #guild-logs", description="Log guild related events")
    @has_guild_permissions(manage_guild=True)
    async def add_guild(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread]):
        await self.add_logging(ctx, "guild", channel)

    @logs_add.command(name="roles", brief="manage guild", usage="logs add roles #role-logs", description="Log role related events")
    @has_guild_permissions(manage_guild=True)
    async def add_roles(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread]):
        await self.add_logging(ctx, "roles", channel)

    @logs_add.command(name="channels", brief="manage guild", usage="logs add channels #channel-logs", description="Log channel related events")
    @has_guild_permissions(manage_guild=True)
    async def add_channels(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread]):
        await self.add_logging(ctx, "channels", channel)

    @logs_add.command(name="members", brief="manage guild", usage="logs add members #member-logs", description="Log member related events")
    @has_guild_permissions(manage_guild=True)
    async def add_members(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread]):
        await self.add_logging(ctx, "members", channel)

    @logs_add.command(name="moderation", brief="manage guild", usage="logs add moderation #moderation-logs", description="Log moderation related events")
    @has_guild_permissions(manage_guild=True)
    async def add_moderation(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread]):
        await self.add_logging(ctx, "moderation", channel)

    @logs_add.command(name="voice", brief="manage guild", usage="logs add voice #voice-logs", description="Log voice related events")
    @has_guild_permissions(manage_guild=True)
    async def add_voice(self, ctx: EvelinaContext, *, channel: Union[TextChannel, Thread]):
        await self.add_logging(ctx, "voice", channel)

    @logs_remove.command(name="messages", brief="manage guild", description="Stop logging message related events")
    @has_guild_permissions(manage_guild=True)
    async def remove_messages(self, ctx: EvelinaContext):
        await self.remove_logging(ctx, "messages")

    @logs_remove.command(name="guild", brief="manage guild", description="Stop logging guild related events")
    @has_guild_permissions(manage_guild=True)
    async def remove_guild(self, ctx: EvelinaContext):
        await self.remove_logging(ctx, "guild")

    @logs_remove.command(name="roles", brief="manage guild", description="Stop logging role related events")
    @has_guild_permissions(manage_guild=True)
    async def remove_roles(self, ctx: EvelinaContext):
        await self.remove_logging(ctx, "roles")

    @logs_remove.command(name="channels", brief="manage guild", description="Stop logging channel related events")
    @has_guild_permissions(manage_guild=True)
    async def remove_channels(self, ctx: EvelinaContext):
        await self.remove_logging(ctx, "channels")

    @logs_remove.command(name="members", brief="manage guild", description="Stop logging member related events")
    @has_guild_permissions(manage_guild=True)
    async def remove_members(self, ctx: EvelinaContext):
        await self.remove_logging(ctx, "members")

    @logs_remove.command(name="moderation", brief="manage guild", description="Stop logging moderation related events")
    @has_guild_permissions(manage_guild=True)
    async def remove_moderation(self, ctx: EvelinaContext):
        await self.remove_logging(ctx, "moderation")

    @logs_remove.command(name="voice", brief="manage guild", description="Stop logging voice related events")
    @has_guild_permissions(manage_guild=True)
    async def remove_voice(self, ctx: EvelinaContext):
        await self.remove_logging(ctx, "voice")

    @logs.group(name="ignore", brief="manage guild", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def logs_ignore(self, ctx: EvelinaContext):
        """Manage the logging ignore list"""
        return await ctx.create_pages()

    @logs_ignore.command(name="add", brief="manage guild", usage="logs ignore add comminate")
    @has_guild_permissions(manage_guild=True)
    async def logs_ignore_add(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Add a user, role or channel to the logging ignore list"""
        if isinstance(target, User):
            await self.update_logging_blacklist(ctx, "ignored_users", str(target.id), add=True)
        elif isinstance(target, Role):
            await self.update_logging_blacklist(ctx, "ignored_roles", str(target.id), add=True)
        elif isinstance(target, TextChannel):
            await self.update_logging_blacklist(ctx, "ignored_channels", str(target.id), add=True)

    @logs_ignore.command(name="remove", brief="manage guild", usage="logs ignore remove comminate")
    @has_guild_permissions(manage_guild=True)
    async def logs_ignore_remove(self, ctx: EvelinaContext, target: Union[User, Role, TextChannel]):
        """Remove a user, role or channel from the logging ignore list"""
        if isinstance(target, User):
            await self.update_logging_blacklist(ctx, "ignored_users", str(target.id), add=False)
        elif isinstance(target, Role):
            await self.update_logging_blacklist(ctx, "ignored_roles", str(target.id), add=False)
        elif isinstance(target, TextChannel):
            await self.update_logging_blacklist(ctx, "ignored_channels", str(target.id), add=False)

    @logs_ignore.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def logs_ignore_list(self, ctx: EvelinaContext):
        """View the logging ignore list"""
        categories = ["ignored_users", "ignored_roles", "ignored_channels"]
        content = []
        for column in categories:
            current_blacklist = await self.bot.db.fetchval(f"SELECT {column} FROM logging WHERE guild_id = $1", ctx.guild.id)
            if not current_blacklist:
                current_list = []
            else:
                current_list = json.loads(current_blacklist) if isinstance(current_blacklist, str) else current_blacklist
            if current_list:
                if column == "ignored_users":
                    content.extend([f"<@{item_id}>" for item_id in current_list])
                elif column == "ignored_roles":
                    content.extend([f"<@&{item_id}>" for item_id in current_list])
                elif column == "ignored_channels":
                    content.extend([f"<#{item_id}>" for item_id in current_list])
        if not content:
            await ctx.send_warning("No users, roles, or channels are ignored for logging")
            return
        await ctx.paginate(content, "Logging Blacklisted", {
            "name": ctx.guild.name,
            "icon_url": ctx.guild.icon.url if ctx.guild.icon else None
        })

    @logs.command(name="setup", brief="Setup logging channels", description="Set up all logging channels in a category")
    @has_guild_permissions(manage_guild=True)
    async def logs_setup(self, ctx: EvelinaContext):
        category_name = "Logging Channels"
        logging_types = ["messages", "guild", "roles", "channels", "members", "moderation", "voice"]
        category = utils.get(ctx.guild.categories, name=category_name)
        if not category:
            category = await ctx.guild.create_category(name=category_name)
        existing_channels = await self.bot.db.fetchrow("SELECT * FROM logging WHERE guild_id = $1", ctx.guild.id)
        existing_channels = existing_channels or {}
        embed = Embed(title="Logging Setup", color=colors.NEUTRAL)
        embed.set_author(name=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        try:
            for log_type in logging_types:
                if existing_channels.get(log_type):
                    channel = ctx.guild.get_channel(existing_channels[log_type])
                    if channel:
                        embed.add_field(name=f"{log_type.title()} Logging", value=f"{channel.mention}", inline=True)
                    continue
                channel_name = f"{log_type}-logs"
                new_channel = await ctx.guild.create_text_channel(name=channel_name, category=category)
                await new_channel.set_permissions(ctx.guild.default_role, view_channel=False)
                await self.bot.db.execute(
                    f"INSERT INTO logging (guild_id, {log_type}) VALUES ($1, $2) "
                    f"ON CONFLICT (guild_id) DO UPDATE SET {log_type} = $2",
                    ctx.guild.id, new_channel.id
                )
                embed.add_field(name=f"{log_type.title()} Logging", value=f"{new_channel.mention}", inline=True)
            await ctx.send(embed=embed)
        except Forbidden:
            await ctx.send_warning("I don't have the required permissions to create channels in this category")

async def setup(bot: Evelina) -> None:
    return await bot.add_cog(Logging(bot))