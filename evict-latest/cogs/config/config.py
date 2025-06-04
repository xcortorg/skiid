from __future__ import annotations

import re
import datetime
import json

from main import Evict
from core.client.context import Context
from managers.paginator import Paginator
from .extended import Extended

from tools.formatter import vowel
from tools.parser import Script

from typing import Optional
from pathlib import Path
from asyncpg import UniqueViolationError

from discord import (
    Message, 
    TextChannel, 
    Embed, 
    Member, 
    Role
)

from discord.ext.commands import (
    group,
    has_permissions,
    Cog,
    BadArgument
)

from core.client.prefix import update_guild_prefix, update_user_prefix

poj_cache = {}


class Config(Extended, Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = "AntiNuke, image-only, boosterroles, vanityroles, etc..."

    @group(invoke_without_command=True)
    async def prefix(self, ctx: Context) -> Message:
        """
        View the current server prefixes.
        """
        guild_prefix = await self.bot.redis.get(f"prefix:guild:{ctx.guild.id}")
        
        if guild_prefix is None:
            guild = await self.bot.db.fetch(
                """
                SELECT DISTINCT prefix 
                FROM prefix 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )
            prefix = [record['prefix'] for record in guild]
        else:
            prefix = [guild_prefix]
        
        await ctx.neutral(f"The servers prefix is {', '.join(f'`{p}`' for p in prefix)}")

    @prefix.command(name="set", example=";")
    @has_permissions(manage_guild=True)
    async def prefix_set(self, ctx: Context, prefix: str) -> Message:
        """
        Set the server prefix.
        """
        if len(prefix) > 7:
            raise BadArgument("Prefix is too long!")

        if not prefix:
            return await ctx.warn(f"Prefix is too short!")
        
        await update_guild_prefix(self.bot, ctx.guild.id, prefix)
        
        return await ctx.approve(f"Guild prefix changed to `{prefix}`")

    @prefix.command(name="self", example="x")
    async def prefix_self(self, ctx: Context, prefix: str):
        """
        Set a custom prefix for yourself.
        """
        if len(prefix) > 7:
            raise BadArgument("Selfprefix is too long!")

        if not prefix:
            return await ctx.warn(f"Selfprefix is too short!")

        from core.client.prefix import update_user_prefix
        
        if prefix.lower() == "none":
            user_prefix = await self.bot.redis.get(f"prefix:user:{ctx.author.id}")
            if user_prefix is None:
                check = await self.bot.db.fetchrow(
                    """
                    SELECT * FROM 
                    selfprefix 
                    WHERE user_id = $1
                    """,
                    ctx.author.id
                )
                if check is None:
                    return await ctx.warn("You dont have a self prefix.")
            
            await ctx.prompt("Are you sure you want to remove your selfprefix?")
            await update_user_prefix(self.bot, ctx.author.id, None)
            return await ctx.approve("Removed your selfprefix.")
        else:
            await update_user_prefix(self.bot, ctx.author.id, prefix)
            return await ctx.approve(f"Set your **selfprefix** to `{prefix}`.")

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke(self, ctx: Context) -> Message:
        """
        Set custom moderation invoke messages.
        Accepts the `moderator` and `reason` variables.
        """
        return await ctx.send_help(ctx.command)

    @invoke.group(name="kick", invoke_without_command=True, example="{user.mention} was kicked for {reason}")
    @has_permissions(manage_guild=True)
    async def invoke_kick(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the kick invoke message.
        """
        await ctx.settings.update(invoke_kick=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **kick** message.",
            f"Use `{ctx.clean_prefix}invoke kick remove` to remove it.",
        )

    @invoke_kick.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_kick_remove(self, ctx: Context) -> Message:
        """
        Remove the kick invoke message.
        """
        await ctx.settings.update(invoke_kick=None)
        return await ctx.approve("Removed the **kick** invoke message!")

    @invoke.group(name="ban", invoke_without_command=True, example="{user.mention} was banned for {reason}")
    @has_permissions(manage_guild=True)
    async def invoke_ban(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the ban invoke message.
        """
        await ctx.settings.update(invoke_ban=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **ban** message.",
            f"Use `{ctx.clean_prefix}invoke ban remove` to remove it.",
        )

    @invoke_ban.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_ban_remove(self, ctx: Context) -> Message:
        """
        Remove the ban invoke message.
        """
        await ctx.settings.update(invoke_ban=None)
        return await ctx.approve("Removed the **ban** invoke message!")

    @invoke.group(name="unban", invoke_without_command=True, example="{user.mention} was unbanned for {reason}")
    @has_permissions(manage_guild=True)
    async def invoke_unban(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the unban invoke message.
        """
        await ctx.settings.update(invoke_unban=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **unban** message.",
            f"Use `{ctx.clean_prefix}invoke unban remove` to remove it.",
        )

    @invoke_unban.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_unban_remove(self, ctx: Context) -> Message:
        """
        Remove the unban invoke message.
        """
        await ctx.settings.update(invoke_unban=None)
        return await ctx.approve("Removed the **unban** invoke message!")

    @invoke.group(name="timeout", invoke_without_command=True, example="{user.mention} was timed out for {duration} ({expires})")
    @has_permissions(manage_guild=True)
    async def invoke_timeout(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the timeout invoke message.
        Accepts the `duration` and `expires` variables.
        """
        await ctx.settings.update(invoke_timeout=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **timeout** message.",
            f"Use `{ctx.clean_prefix}invoke timeout remove` to remove it.",
        )

    @invoke_timeout.command(name="remove", aliases=["delete", "del", "rm"])
    @has_permissions(manage_guild=True)
    async def invoke_timeout_remove(self, ctx: Context) -> Message:
        """
        Remove the timeout invoke message.
        """
        await ctx.settings.update(invoke_timeout=None)
        return await ctx.approve("Removed the **timeout** invoke message!")

    @invoke.group(name="untimeout", invoke_without_command=True, example="{user.mention} was untimed out")
    @has_permissions(manage_guild=True)
    async def invoke_untimeout(self, ctx: Context, *, script: Script) -> Message:
        """
        Set the untimeout invoke message.
        """
        await ctx.settings.update(invoke_untimeout=script.template)
        return await ctx.approve(
            f"Successfully set {vowel(script.format)} **untimeout** message.",
            f"Use `{ctx.clean_prefix}invoke untimeout remove` to remove it.",
        )

    @invoke_untimeout.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def invoke_untimeout_remove(self, ctx: Context) -> Message:
        """
        Remove the untimeout invoke message.
        """
        await ctx.settings.update(invoke_untimeout=None)
        return await ctx.approve("Removed the **untimeout** invoke message!")

    @invoke.group(name="dm", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def invoke_dm(self, ctx: Context) -> Message:
        """
        Configure DM notifications for moderation actions.
        """
        return await ctx.send_help(ctx.command)

    @invoke_dm.command(name="toggle", example="ban")
    @has_permissions(manage_guild=True)
    async def invoke_dm_toggle(self, ctx: Context, action: str) -> Message:
        """
        Toggle DM notifications for a specific action.
        Available actions: ban, unban, kick, jail, unjail, mute, unmute, warn, timeout, untimeout, antinuke_ban, antinuke_kick, antinuke_strip, antiraid_ban, antiraid_kick, antiraid_timeout, antiraid_strip, role_add, role_remove
        """
        valid_actions = [
            "ban", "unban", "kick", "jail", "unjail", 
            "mute", "unmute", "warn", "timeout", "untimeout",
            "antinuke_ban", "antinuke_kick", "antinuke_strip",
            "antiraid_ban", "antiraid_kick", "antiraid_timeout", "antiraid_strip",
            "role_add", "role_remove" 
        ]
        action = action.lower()
        if action not in valid_actions:
            return await ctx.warn(
                f"Invalid action. Choose from: {', '.join(f'`{a}`' for a in valid_actions)}"
            )

        try:
            exists = await self.bot.db.fetchval(
                """
                SELECT EXISTS(SELECT 1 FROM mod WHERE guild_id = $1)
                """,
                ctx.guild.id
            )
            
            if exists:
                await self.bot.db.execute(
                    """
                    UPDATE mod 
                    SET dm_{0} = NOT COALESCE(dm_{0}, false)
                    WHERE guild_id = $1
                    """.format(action),
                    ctx.guild.id
                )
            else:
                await self.bot.db.execute(
                    f"""
                    INSERT INTO mod (guild_id, dm_{action}, dm_enabled) 
                    VALUES ($1, true, true)
                    """,
                    ctx.guild.id
                )
            
            new_state = await self.bot.db.fetchval(
                f"""
                SELECT dm_{action} FROM mod 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )
            
            state = "enabled" if new_state else "disabled"
            return await ctx.approve(f"{state.title()} DM notifications for {action}")

        except Exception as e:
            return await ctx.error(f"Failed to toggle DM setting: {e}")

    @invoke_dm.command(name="view", example="ban")
    @has_permissions(manage_guild=True)
    async def invoke_dm_view(self, ctx: Context, action: str = None) -> Message:
        """View current DM message for an action or list all configured actions."""
        settings = await self.bot.db.fetchrow(
            """
            SELECT * FROM mod 
            WHERE guild_id = $1
            """, 
            ctx.guild.id
        )
        
        if not settings:
            return await ctx.warn("No DM messages configured!")

        if not action:
            configured = []
            for col in settings.keys():
                if col.startswith("dm_") and col != "dm_enabled" and settings[col]:
                    configured.append(f"`{col[3:]}`")
            
            if not configured:
                return await ctx.warn("No custom DM messages configured!")
            return await ctx.approve(f"Configured DM messages for: {', '.join(configured)}")

        action = action.lower()
        message = settings.get(f"dm_{action}")
        if not message:
            return await ctx.approve(f"Using default DM message for {action}")
        return await ctx.approve(f"Current {action} DM message:\n```\n{message}\n```")

    @invoke_dm.command(name="set", example="[ban] [{user.mention} was banned for {reason}]")
    @has_permissions(manage_guild=True)
    async def invoke_dm_set(self, ctx: Context, action: str, *, script: Optional[Script] = None) -> Message:
        """
        Set a custom DM message for an action.
        Available actions: ban, unban, kick, jail, unjail, mute, unmute, warn, timeout, untimeout, antinuke_ban, antinuke_kick, antinuke_strip, antiraid_ban, antiraid_kick, antiraid_timeout, antiraid_strip
        """
        valid_actions = [
            "ban", "unban", "kick", "jail", "unjail", 
            "mute", "unmute", "warn", "timeout", "untimeout",
            "antinuke_ban", "antinuke_kick", "antinuke_strip",
            "antiraid_ban", "antiraid_kick", "antiraid_timeout", "antiraid_strip"
        ]
        
        action = action.lower()
        if action not in valid_actions:
            return await ctx.warn(
                f"Invalid action. Choose from: {', '.join(f'`{a}`' for a in valid_actions)}"
            )

        if not script:
            await self.bot.db.execute(
                """
                UPDATE mod SET dm_" + action + " = NULL 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )
            return await ctx.approve(f"Reset to default DM message for {action}")

        exists = await self.bot.db.fetchval(
            """
            SELECT EXISTS(SELECT 1 FROM mod 
            WHERE guild_id = $1)
            """,
            ctx.guild.id
        )
        
        if exists:
            await self.bot.db.execute(
                f"""
                UPDATE mod SET dm_{action} = $1 
                WHERE guild_id = $2
                """,
                script.template,
                ctx.guild.id
            )
        else:
            await self.bot.db.execute(
                f"""
                INSERT INTO mod (guild_id, dm_{action}, dm_enabled) 
                VALUES ($1, $2, true)
                """,
                ctx.guild.id,
                script.template
            )

        return await ctx.approve(f"Updated {action} DM message")

    @group(invoke_without_command=True, aliases=["poj"])
    async def pingonjoin(self, ctx: Context):
        """
        Mention new members when they join the server.
        """
        await ctx.send_help(ctx.command)

    @pingonjoin.command(name="add", example="#general")
    @has_permissions(manage_guild=True)
    async def poj_add(self, ctx: Context, *, channel: TextChannel):
        """
        Add a channel to mention new members upon join.
        """
        check = await self.bot.db.fetchrow(
            """
            SELECT * FROM pingonjoin 
            WHERE guild_id = $1 
            AND channel_id = $2
            """,
            ctx.guild.id,
            channel.id,
        )

        if check is not None:
            return await ctx.warn(
                f"The channel {channel.mention} is already mentioning new members!"
            )

        elif check is None:
            await self.bot.db.execute(
                """
                INSERT INTO pingonjoin 
                VALUES ($1,$2)
                """, 
                channel.id, 
                ctx.guild.id
            )

        return await ctx.approve(f"I will now ping new members in {channel.mention}.")

    @pingonjoin.command(name="remove", example="#general")
    @has_permissions(manage_guild=True)
    async def poj_remove(self, ctx: Context, *, channel: TextChannel = None):
        """
        Remove a channel from mentioning new members upon join.
        """
        if channel is not None:
            check = await self.bot.db.fetchrow(
                """
                SELECT * FROM pingonjoin 
                WHERE guild_id = $1 
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            )

            if check is None:
                return await ctx.warn(
                    f"The channel {channel.mention} is **not** added as an pingonjoin channel!"
                )

            elif check is not None:
                await self.bot.db.execute(
                    """
                    DELETE FROM pingonjoin 
                    WHERE guild_id = $1 
                    AND channel_id = $2
                    """,
                    ctx.guild.id,
                    channel.id,
                )

            return await ctx.approve(
                f"No longer mentioning new members in {channel.mention}!"
            )

        check = await self.bot.db.fetch(
            """
            SELECT * FROM pingonjoin 
            WHERE guild_id = $1
            """,
            ctx.guild.id
        )

        if check is None:
            return await ctx.warn("There is no channel added!")

        elif check is not None:
            await self.bot.db.execute(
                """
                DELETE FROM pingonjoin 
                WHERE guild_id = $1
                """,
                ctx.guild.id
            )

        return await ctx.approve("No longer mentioning new members in any channel!")

    @Cog.listener("on_member_join")
    async def pingonjoin_listener(self, member: Member):
        if member.bot:
            return
        
        cache_key = f"poj:{member.guild.id}"
        channels = await self.bot.redis.get(cache_key)
        
        if not channels:
            records = await self.bot.db.fetch(
                """
                SELECT channel_id 
                FROM pingonjoin 
                WHERE guild_id = $1
                """,
                member.guild.id
            )
            channels = [record['channel_id'] for record in records]
            await self.bot.redis.set(cache_key, channels, ex=60)

        recent_joins = [
            m for m in member.guild.members
            if (datetime.datetime.now() - m.joined_at.replace(tzinfo=None)).total_seconds() < 180
        ]

        for channel_id in channels:
            if channel := member.guild.get_channel(int(channel_id)):
                try:
                    if len(recent_joins) < 10:
                        await channel.send(member.mention, delete_after=6)
                    else:
                        if not poj_cache.get(str(channel.id)):
                            poj_cache[str(channel.id)] = []
                        poj_cache[str(channel.id)].append(member.mention)
                        if len(poj_cache[str(channel.id)]) >= 10:
                            await channel.send(" ".join(poj_cache[str(channel.id)]), delete_after=6)
                            poj_cache[str(channel.id)] = []
                except:
                    continue

    @group(invoke_without_command=True)
    async def tag(self, ctx: Context, *, name: str = None) -> Message:
        """
        Create and manage custom tags.
        If no subcommand is given, searches for and displays the requested tag.
        """
        if not name:
            return await ctx.send_help(ctx.command)
            
        record = await self.bot.db.fetchrow(
            """
            SELECT original 
            FROM tag_aliases 
            WHERE guild_id = $1 
            AND LOWER(alias) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        if record:
            name = record['original']
            
        record = await self.bot.db.fetchrow(
            """
            SELECT template, owner_id, restricted_user, restricted_role
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")

        restricted_user = await self.bot.db.fetchval(
            """
            SELECT restricted_user 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )

        restricted_role = await self.bot.db.fetchval(
            """
            SELECT restricted_role 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )

        if restricted_user is not None or restricted_role is not None:
            if not ctx.author.guild_permissions.administrator:
                target = ctx.guild.get_role(restricted_role) or ctx.guild.get_member(restricted_user)
                if target and target not in ctx.author.roles and target != ctx.author:
                    return await ctx.warn(f"You do not have permission to use the tag `{name}`!")

        script = Script(
            record["template"],
            [ctx.guild, ctx.author, ctx.channel],
        )
        
        await self.bot.db.execute(
            """
            UPDATE tags 
            SET uses = uses + 1 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        return await script.send(ctx, normal=True)

    @tag.command(name="create", example="welcome Welcome to evict!")
    @has_permissions(manage_messages=True)
    async def tag_create(self, ctx: Context, name: str, *, template: str) -> Message:
        """
        Create a new tag.
        """
        if len(name) > 32:
            return await ctx.warn("Tag name cannot be longer than 32 characters!")
            
        if name.lower() in ctx.command.root_parent.all_commands:
            return await ctx.warn("That tag name is reserved for a subcommand!")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO tags 
                (guild_id, name, owner_id, template)
                VALUES ($1, $2, $3, $4)
                """,
                ctx.guild.id, 
                name, 
                ctx.author.id, 
                template
            )
        
        except UniqueViolationError:
            return await ctx.warn(f"A tag named `{name}` already exists!")

        return await ctx.approve(f"Created tag `{name}`")

    @tag.command(name="edit", example="welcome Welcome to our amazing evict!")
    @has_permissions(manage_messages=True)
    async def tag_edit(self, ctx: Context, name: str, *, template: str) -> Message:
        """
        Edit an existing tag.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name.lower()
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only edit tags you own!")

        await self.bot.db.execute(
            """
            UPDATE tags 
            SET template = $3 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name, 
            template
        )

        return await ctx.approve(f"Updated tag `{name}`")

    @tag.command(name="delete", aliases=["remove"], example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_delete(self, ctx: Context, *, name: str) -> Message:
        """
        Delete a tag.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only delete tags you own!")

        await self.bot.db.execute(
            """
            DELETE FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )

        return await ctx.approve(f"Deleted tag `{name}`")

    @tag.command(name="info", example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_info(self, ctx: Context, *, name: str) -> Message:
        """
        View information about a tag.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT name, owner_id, uses, created_at, template
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")

        aliases = await self.bot.db.fetch(
            """
            SELECT alias 
            FROM tag_aliases 
            WHERE guild_id = $1 
            AND LOWER(original) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        owner = ctx.guild.get_member(record['owner_id'])
        owner_text = owner.mention if owner else f"Unknown User ({record['owner_id']})"
        
        embed = Embed(title=f"Tag Information: {record['name']}")
        embed.add_field(name="Owner", value=owner_text, inline=True)
        embed.add_field(name="Uses", value=f"{record['uses']:,}", inline=True)
        embed.add_field(name="Created", value=f"<t:{int(record['created_at'].timestamp())}:R>", inline=True)
        
        if aliases:
            embed.add_field(
                name="Aliases", 
                value=", ".join(f"`{alias['alias']}`" for alias in aliases),
                inline=False
            )
            
        embed.add_field(name="Content", value=f"```\n{record['template']}\n```", inline=False)
        
        return await ctx.send(embed=embed)

    @tag.command(name="list", aliases=["all"])
    @has_permissions(manage_messages=True)
    async def tag_list(self, ctx: Context) -> Message:
        """
        List all tags in the server.
        """
        records = await self.bot.db.fetch(
            """
            SELECT name, uses 
            FROM tags 
            WHERE guild_id = $1 
            ORDER BY uses DESC
            """,
            ctx.guild.id
        )
        
        if not records:
            return await ctx.warn("No tags found in this server!")

        entries = [f"`{r['name']}` ({r['uses']:,} uses)" for r in records]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title=f"Tags in {ctx.guild.name}"),
            per_page=20
        )

        return await paginator.start()

    @tag.command(name="alias", example="welcome hey")
    @has_permissions(manage_messages=True)
    async def tag_alias(self, ctx: Context, name: str, alias: str) -> Message:
        """
        Create an alias for a tag.
        """
        if len(alias) > 32:
            return await ctx.warn("Alias cannot be longer than 32 characters!")

        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only create aliases for tags you own!")

        try:
            await self.bot.db.execute(
                """
                INSERT INTO tag_aliases (guild_id, alias, original)
                VALUES ($1, $2, $3)
                """,
                ctx.guild.id, 
                alias, 
                name
            )
        except UniqueViolationError:
            return await ctx.warn(f"An alias named `{alias}` already exists!")

        return await ctx.approve(f"Created alias `{alias}` for tag `{name}`")

    @tag.command(name="search", example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_search(self, ctx: Context, *, query: str) -> Message:
        """
        Search for tags.
        """
        record = await self.bot.db.fetch(
            """
            SELECT name, uses 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) LIKE LOWER($2)
            ORDER BY uses DESC
            """,
            ctx.guild.id,
            f"%{query}%"
        )
        
        if not record:
            return await ctx.warn(f"No tags found matching `{query}`!")

        entries = [f"`{r['name']}` ({r['uses']:,} uses)" for r in record]
        
        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title=f"Tags matching '{query}'"),
            per_page=10
        )
        return await paginator.start()

    @tag.command(name="raw", example="welcome")
    @has_permissions(manage_messages=True)
    async def tag_raw(self, ctx: Context, *, name: str) -> Message:
        """
        Show the raw content of a tag.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT template 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")

        return await ctx.send(f"```\n{record['template']}\n```")

    @tag.command(name="transfer", example="welcome @user")
    @has_permissions(manage_messages=True)
    async def tag_transfer(self, ctx: Context, name: str, *, member: Member) -> Message:
        """
        Transfer ownership of a tag to another user.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id 
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )
        
        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only transfer tags you own!")
            
        if member.bot:
            return await ctx.warn("You cannot transfer tags to bots!")

        await self.bot.db.execute(
            """
            UPDATE tags 
            SET owner_id = $3 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name, 
            member.id
        )

        return await ctx.approve(f"Transferred tag `{name}` to {member.mention}")
    
    @tag.group(name="restrict", invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def tag_restrict(self, ctx: Context):
        """
        Restrict a tag to a role or user.
        """
        return await ctx.send_help(ctx.command)
    
    @tag_restrict.command(name="role", example="welcome @role")
    @has_permissions(manage_messages=True)
    async def tag_restrict_add_role(self, ctx: Context, name: str, role: Role) -> Message:
        """
        Restrict a tag to a role or remove the restriction if no role is provided.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id, restricted_user, restricted_role
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, 
            name
        )

        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only restrict tags you own!")
        
        if record['restricted_user']:
            return await ctx.warn(f"Tag `{name}` is already restricted to user <@{record['restricted_user']}>!")

        if record['restricted_role']:
            await self.bot.db.execute(
                """
                UPDATE tags 
                SET restricted_role = NULL 
                WHERE guild_id = $1 
                AND LOWER(name) = LOWER($2)
                """,
                ctx.guild.id, 
                name
            )

            await ctx.prompt("Would you like to remove the role restriction from this tag?")
            return await ctx.approve(f"Removed role restriction from tag `{name}`!")

        if role:
            await self.bot.db.execute(
                """
                UPDATE tags 
                SET restricted_role = $3 
                WHERE guild_id = $1 
                AND LOWER(name) = LOWER($2)
                """,
                ctx.guild.id, 
                name, 
                role.id
            )

            return await ctx.approve(f"Restricted tag `{name}` to role {role.mention}")
        
    @tag_restrict.command(name="user", example="welcome @user")
    @has_permissions(manage_messages=True)
    async def tag_restrict_add_user(self, ctx: Context, name: str, user: Member) -> Message:
        """
        Restrict a tag to a user or remove the restriction if no user is provided.
        """
        record = await self.bot.db.fetchrow(
            """
            SELECT owner_id, restricted_user, restricted_role
            FROM tags 
            WHERE guild_id = $1 
            AND LOWER(name) = LOWER($2)
            """,
            ctx.guild.id, name
        )

        if not record:
            return await ctx.warn(f"Tag `{name}` not found!")
            
        if record['owner_id'] != ctx.author.id and not ctx.author.guild_permissions.administrator:
            return await ctx.warn("You can only restrict tags you own!")
        
        if record['restricted_role']:
            return await ctx.warn(f"Tag `{name}` is already restricted to role <@&{record['restricted_role']}>!")

        if record['restricted_user']:
            await self.bot.db.execute(
                """
                UPDATE tags 
                SET restricted_user = NULL 
                WHERE guild_id = $1 
                AND LOWER(name) = LOWER($2)
                """,
                ctx.guild.id, name
            )

            await ctx.prompt("Would you like to remove the user restriction from this tag?")
            return await ctx.approve(f"Removed user restriction from tag `{name}`!")

        if user:
            await self.bot.db.execute(
                """
                UPDATE tags 
                SET restricted_user = $3 
                WHERE guild_id = $1 
                AND LOWER(name) = LOWER($2)
                """,
                ctx.guild.id, name, user.id
            )
            return await ctx.approve(f"Restricted tag `{name}` to user {user.mention}")

    @group(name="translator")
    async def translator(self, ctx: Context):
        """
        Translation management commands.
        """
        if not ctx.invoked_subcommand:
            await ctx.send_help(ctx.command)

    @translator.command(name="set")
    async def translator_set(self, ctx: Context, *, translation: Optional[str] = None):
        """
        Set next untranslated string for your language.
        """
        lang_code = await self.bot.db.fetchval(
            """
            SELECT language_code FROM translation_contributors 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )
        
        if not lang_code:
            return await ctx.warn("You don't have an assigned language to translate! Contact the bot owner.")

        base_path = Path("langs")
        
        for file in base_path.rglob("en-US.json"):
            category = file.parent.name
            with open(file) as f:
                base_data = json.load(f)
            
            target_file = file.parent / f"{lang_code}.json"
            try:
                with open(target_file) as f:
                    target_data = json.load(f)
            except FileNotFoundError:
                target_data = {
                    "language_code": lang_code,
                    "language": lang_code,  
                    "language_local": lang_code  
                }

            def find_untranslated(base: dict, target: dict, prefix: str = "") -> Optional[tuple[str, str]]:
                for key, value in base.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        if key not in target or not isinstance(target[key], dict):
                            target[key] = {}
                        result = find_untranslated(value, target[key], current_path)
                        if result:
                            return result
                    elif isinstance(value, str):
                        if key not in target or not target[key]:
                            return (current_path, value)
                return None

            result = find_untranslated(base_data, target_data)
            if result:
                path, original = result
                
                if translation is None:
                    embed = Embed(title="Translation Needed")
                    embed.add_field(name="Category", value=category, inline=False)
                    embed.add_field(name="Path", value=path, inline=False)
                    embed.add_field(name="Original (en-US)", value=f"```{original}```", inline=False)
                    embed.set_footer(text=f"Use {ctx.prefix}translator set <translation>")
                    return await ctx.send(embed=embed)

                current = target_data
                parts = path.split('.')
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                if parts[-1] in current and current[parts[-1]] == translation:
                    return await ctx.warn("This translation is identical to the existing one!")

                def extract_vars(text: str) -> set[str]:
                    clean_text = re.sub(r'\*\*|__|\*|_', '', text)
                    return set(re.findall(r'\{([^}]+)\}', clean_text))

                orig_vars = extract_vars(original)
                trans_vars = extract_vars(translation)
                
                if orig_vars != trans_vars:
                    missing = orig_vars - trans_vars
                    extra = trans_vars - orig_vars
                    error_msg = []
                    
                    if missing:
                        error_msg.append(f"Missing variables: {', '.join(f'`{{{v}}}`' for v in missing)}")
                    if extra:
                        error_msg.append(f"Extra variables: {', '.join(f'`{{{v}}}`' for v in extra)}")
                        
                    return await ctx.warn("\n".join(error_msg))

                current[parts[-1]] = translation

                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(target_data, f, indent=4, ensure_ascii=False)

                return await ctx.approve(f"Set translation for `{path}` in `{lang_code}`")

        await ctx.neutral("All strings have been translated! 🎉")

    @translator.command(name="edit")
    async def translator_edit(self, ctx: Context, path: str, *, translation: str):
        """
        Edit an existing translation.
        """
        lang_code = await self.bot.db.fetchval(
            """
            SELECT language_code FROM translation_contributors 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )
        
        if not lang_code:
            return await ctx.warn("You don't have an assigned language to translate!")

        file_path = "/".join(path.split(".")[:-1]) 
        
        target_file = Path(f"langs/{file_path}/{lang_code}.json")
        if not target_file.exists():
            return await ctx.warn(f"No translation file found for `{lang_code}`. Use `translator set` first.")

        with open(target_file) as f:
            data = json.load(f)

        base_file = Path(f"langs/{file_path}/en-US.json")
        if not base_file.exists():
            return await ctx.warn(f"English source file not found: {base_file}")

        with open(base_file) as f:
            base_data = json.load(f)

        parts = path.split('.')
        original = base_data
        for part in parts[1:]:
            original = original.get(part, {})
            if not isinstance(original, (dict, str)):
                return await ctx.warn(f"Invalid path: {path}")

        if not isinstance(original, str):
            return await ctx.warn(f"Path does not point to a string: {path}")

        orig_vars = set(re.findall(r'\{([^}]+)\}', original))
        trans_vars = set(re.findall(r'\{([^}]+)\}', translation))
        if orig_vars != trans_vars:
            return await ctx.warn(f"Missing variables: {orig_vars - trans_vars}")

        current = data
        for part in parts[:-1]:
            if part not in current:
                return await ctx.warn(f"Path not found: {path}")
            current = current[part]

        current[parts[-1]] = translation

        with open(target_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

        await ctx.approve(f"Updated translation for `{path}`")

    @translator.command(name="instructions")
    async def translator_instructions(self, ctx: Context):
        """
        View instructions for translating.
        """
        embed = Embed(
            title="Translation Instructions",
            description="Here's how to help translate the bot!"
        )

        embed.add_field(
            name="Getting Started",
            value=(
                "1. Get assigned a language by the bot owner\n"
                "2. Use `translator set` to get your next string to translate\n"
                "3. Submit your translation with `translator set <translation>`"
            ),
            inline=False
        )

        embed.add_field(
            name="Available Commands", 
            value=(
                "`translator set` - Get next string/submit translation\n"
                "`translator edit <path> <translation>` - Edit existing translation\n"
                "`translator strings` - View all strings and their status\n"
                "`translator completion <lang>` - Check completion status"
            ),
            inline=False
        )

        embed.add_field(
            name="Variables",
            value=(
                "Some strings contain variables like `{user}` or `{count}`.\n"
                "These **must** be included in your translation exactly as they appear.\n"
                "Example: `You have {count} points` → `Ai {count} puncte`"
            ),
            inline=False
        )

        embed.add_field(
            name="Tips",
            value=(
                "- Keep formatting (bold, italic, etc) from original text\n"
                "- Maintain any newlines (line breaks) from original\n"
                "- Test variables by ensuring they're in the right place\n"
                "- Use `translator strings` to review your work"
            ),
            inline=False
        )

        return await ctx.send(embed=embed)

    @translator.command(name="strings")
    async def translator_strings(self, ctx: Context):
        """
        View all strings for your language.
        """
        lang_code = await self.bot.db.fetchval(
            """
            SELECT language_code FROM translation_contributors 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )
        
        if not lang_code:
            return await ctx.warn("You don't have an assigned language to translate!")

        entries = []
        base_path = Path("langs")
        
        for file in base_path.rglob("en-US.json"):
            category = file.parent.name
            with open(file) as f:
                base_data = json.load(f)
            
            target_file = file.parent / f"{lang_code}.json"
            target_data = {}
            if target_file.exists():
                with open(target_file) as f:
                    target_data = json.load(f)

            def collect_strings(base: dict, target: dict, prefix: str = ""):
                for key, value in base.items():
                    current_path = f"{prefix}.{key}" if prefix else key
                    if isinstance(value, dict):
                        collect_strings(value, target.get(key, {}), current_path)
                    elif isinstance(value, str):
                        status = "✅" if key in target and target[key] else "❌"
                        entries.append(f"{status} `{current_path}`\n**en-US**: {value}\n**{lang_code}**: {target.get(key, 'Not translated')}\n")

            collect_strings(base_data, target_data, category)

        if not entries:
            return await ctx.warn("No strings found!")

        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title=f"Translation Strings ({lang_code})"),
            per_page=5
        )
        return await paginator.start()

    @translator.command(name="completion")
    async def translator_completion(self, ctx: Context, lang_code: str):
        """
        Check translation completion percentage.
        """
        base_path = Path("langs")
        total_strings = 0
        translated_strings = 0
        category_stats = {}

        for en_file in base_path.rglob("en-US.json"):
            category = en_file.parent.name
            with open(en_file) as f:
                en_data = json.load(f)
            
            target_file = en_file.parent / f"{lang_code}.json"
            target_data = {}
            if target_file.exists():
                with open(target_file) as f:
                    target_data = json.load(f)

            def count_translations(en: dict, tr: dict) -> tuple[int, int]:
                total = 0
                translated = 0
                
                for key, value in en.items():
                    if isinstance(value, dict):
                        sub_total, sub_translated = count_translations(value, tr.get(key, {}))
                        total += sub_total
                        translated += sub_translated
                    elif isinstance(value, str) and value:  
                        total += 1
                        if key in tr and tr[key]:
                            translated += 1
                
                return total, translated

            cat_total, cat_translated = count_translations(en_data, target_data)
            total_strings += cat_total
            translated_strings += cat_translated
            
            if cat_total > 0: 
                cat_percent = (cat_translated / cat_total) * 100
                category_stats[category] = (cat_translated, cat_total, cat_percent)

        if total_strings == 0:
            return await ctx.warn("No strings found in English files!")

        embed = Embed(title=f"Translation Status: {lang_code}")
        
        total_percent = (translated_strings / total_strings) * 100
        embed.description = f"**Overall**: {total_percent:.1f}% complete ({translated_strings:,}/{total_strings:,} strings)"
        
        for category, (translated, total, percent) in sorted(category_stats.items()):
            embed.add_field(
                name=category,
                value=f"{percent:.1f}% ({translated}/{total})",
                inline=True
            )

        return await ctx.send(embed=embed)