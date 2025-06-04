import datetime

from discord import Embed

from modules.styles import colors, emojis
from modules.helpers import EvelinaContext

async def fetch_all_restrictions(ctx: EvelinaContext):
    if ctx.guild is None:
        return None
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    user_id = ctx.author.id
    command_name = str(ctx.command)
    cog_name = ctx.command.cog_name.lower() if ctx.command.cog_name else None
    query = """
    SELECT 'guild_disabled_commands' AS table_name, cmd AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM guild_disabled_commands WHERE guild_id = $1 AND cmd = $2
    UNION ALL
    SELECT 'channel_disabled_commands' AS table_name, cmd AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM channel_disabled_commands WHERE channel_id = $3 AND cmd = $2
    UNION ALL
    SELECT 'guild_disabled_module' AS table_name, NULL::TEXT AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM guild_disabled_module WHERE guild_id = $1 AND module = $5
    UNION ALL
    SELECT 'channel_disabled_module' AS table_name, NULL::TEXT AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM channel_disabled_module WHERE channel_id = $3 AND module = $5
    UNION ALL
    SELECT 'global_disabled_commands' AS table_name, command AS command, NULL::BIGINT AS role_id, status::BOOLEAN AS status, reason::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM global_disabled_commands WHERE $4 LIKE command || '%'
    UNION ALL
    SELECT 'global_beta_commands' AS table_name, command AS command, NULL::BIGINT AS role_id, status::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM global_beta_commands WHERE $4 LIKE command || '%'
    UNION ALL
    SELECT 'only_text' AS table_name, NULL::TEXT AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM only_text WHERE guild_id = $1 AND channel_id = $3
    UNION ALL
    SELECT 'restrictcommand' AS table_name, command AS command, role_id::BIGINT AS role_id, NULL::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM restrictcommand WHERE guild_id = $1 AND (command = $2 OR command = 'all')
    UNION ALL
    SELECT 'restrictmodule' AS table_name, command AS command, role_id::BIGINT AS role_id, NULL::BOOLEAN AS status, NULL::TEXT AS reason, NULL::BIGINT AS duration, NULL::BIGINT AS timestamp
    FROM restrictmodule WHERE guild_id = $1 AND (command = $5 OR command = 'all')
    UNION ALL
    SELECT 'blacklist_user' AS table_name, NULL::TEXT AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, reason::TEXT AS reason, duration::BIGINT AS duration, timestamp::BIGINT AS timestamp
    FROM blacklist_user WHERE user_id = $6
    UNION ALL
    SELECT 'blacklist_server' AS table_name, NULL::TEXT AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, reason::TEXT AS reason, duration::BIGINT AS duration, timestamp::BIGINT AS timestamp
    FROM blacklist_server WHERE guild_id = $1
    UNION ALL
    SELECT 'blacklist_cog' AS table_name, NULL::TEXT AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, reason::TEXT AS reason, duration::BIGINT AS duration, timestamp::BIGINT AS timestamp
    FROM blacklist_cog WHERE user_id = $6 AND cog = $5
    UNION ALL
    SELECT 'blacklist_cog_server' AS table_name, NULL::TEXT AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, reason::TEXT AS reason, duration::BIGINT AS duration, timestamp::BIGINT AS timestamp
    FROM blacklist_cog_server WHERE guild_id = $1 AND cog = $5
    UNION ALL
    SELECT 'blacklist_command' AS table_name, command AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, reason::TEXT AS reason, duration::BIGINT AS duration, timestamp::BIGINT AS timestamp
    FROM blacklist_command WHERE user_id = $6 AND command = $2
    UNION ALL
    SELECT 'blacklist_command_server' AS table_name, command AS command, NULL::BIGINT AS role_id, NULL::BOOLEAN AS status, reason::TEXT AS reason, duration::BIGINT AS duration, timestamp::BIGINT AS timestamp
    FROM blacklist_command_server WHERE guild_id = $1 AND command = $2
    """
    return await ctx.bot.db.fetch(query, guild_id, command_name, channel_id, command_name, cog_name, user_id)

async def disabled_command(ctx: EvelinaContext):
    if ctx.guild is None:
        await ctx.send_warning("You can't use this command in DMs")
        return False
    restrictions = await fetch_all_restrictions(ctx)
    if not restrictions:
        return True
    for restriction in restrictions:
        table = restriction["table_name"]
        if table == "guild_disabled_commands" and not (ctx.author.guild_permissions.administrator or ctx.author.id in ctx.bot.owner_ids):
            await ctx.send_warning(f"Command `{ctx.command}` is **disabled** in this server")
            return False
        elif table == "channel_disabled_commands" and not (ctx.author.guild_permissions.administrator or ctx.author.id in ctx.bot.owner_ids):
            await ctx.send_warning(f"Command `{ctx.command}` is **disabled** in {ctx.channel.mention}")
            return False
        elif table == "global_disabled_commands" and restriction.get("status") and ctx.author.id not in ctx.bot.owner_ids:
            reason = restriction.get("reason", "No reason provided")
            await ctx.send_warning(f"Command `{ctx.command}` is globally disabled.\n> **Reason:** {reason}")
            return False
        elif table == "global_beta_commands" and restriction.get("status") and ctx.author.id not in ctx.bot.owner_ids:
            await ctx.send_warning(f"Command `{ctx.command}` is restricted to beta testers.")
            return False
        elif table == "only_text" and not (ctx.author.guild_permissions.administrator or ctx.author.id in ctx.bot.owner_ids):
            await ctx.message.delete()
            return False
    return True

async def disabled_module(ctx: EvelinaContext):
    if ctx.guild is None:
        await ctx.send_warning("You can't use this command in DMs")
        return False
    restrictions = await fetch_all_restrictions(ctx)
    if not restrictions:
        return True
    for restriction in restrictions:
        table = restriction["table_name"]
        if table == "guild_disabled_module" and not (ctx.author.guild_permissions.administrator or ctx.author.id in ctx.bot.owner_ids):
            await ctx.send_warning(f"Module `{ctx.command.cog_name.lower()}` is **disabled** in this server")
            return False
        elif table == "channel_disabled_module" and not (ctx.author.guild_permissions.administrator or ctx.author.id in ctx.bot.owner_ids):
            await ctx.send_warning(f"Module `{ctx.command.cog_name.lower()}` is **disabled** in {ctx.channel.mention}")
            return False
    return True

async def restricted_command(ctx: EvelinaContext):
    if ctx.guild is None:
        await ctx.send_warning("You can't use this command in DMs")
        return False
    restrictions = await fetch_all_restrictions(ctx)
    if not restrictions:
        return True
    matched_restrictions = [
        r for r in restrictions
        if r["table_name"] == "restrictcommand"
        and (r["command"] == "all" or ctx.command.qualified_name.startswith(r["command"]))
    ]
    if not matched_restrictions:
        return True
    for restriction in matched_restrictions:
        role_id = restriction["role_id"]
        role = ctx.guild.get_role(role_id)
        if role and role in ctx.author.roles:
            return True
    required_roles = [
        ctx.guild.get_role(r["role_id"])
        for r in matched_restrictions
        if ctx.guild.get_role(r["role_id"]) is not None
    ]
    role_mentions = ", ".join(role.mention for role in required_roles)
    await ctx.send_warning(f"You can't use `{ctx.command}`. Required roles: {role_mentions}")
    return False

async def restricted_module(ctx: EvelinaContext):
    if ctx.guild is None:
        await ctx.send_warning("You can't use this command in DMs")
        return False
    restrictions = await fetch_all_restrictions(ctx)
    if not restrictions or not ctx.command or not ctx.command.cog_name:
        return True
    cog_name = ctx.command.cog_name.lower()
    matched_restrictions = [
        r for r in restrictions
        if r["table_name"] == "restrictmodule"
        and (r["command"] == "all" or r["command"] == cog_name)
    ]
    if not matched_restrictions:
        return True
    for restriction in matched_restrictions:
        role_id = restriction["role_id"]
        role = ctx.guild.get_role(role_id)
        if role and role in ctx.author.roles:
            return True
    required_roles = [
        ctx.guild.get_role(r["role_id"])
        for r in matched_restrictions
        if ctx.guild.get_role(r["role_id"]) is not None
    ]
    role_mentions = ", ".join(role.mention for role in required_roles)
    await ctx.send_warning(f"You can't use `{cog_name}` module. Required roles: {role_mentions}")
    return False

async def blacklisted(ctx: EvelinaContext):
    restrictions = await fetch_all_restrictions(ctx)
    if not restrictions:
        return True
    now = datetime.datetime.now().timestamp()
    for restriction in restrictions:
        table = restriction["table_name"]
        if table in ["blacklist_user", "blacklist_server", "blacklist_cog", "blacklist_command", "blacklist_cog_server", "blacklist_command_server"]:
            if restriction["duration"] is None or now < restriction["timestamp"] + restriction["duration"]:
                reason = restriction.get("reason", "No reason provided")
                remaining_time = None
                if restriction["duration"] is not None:
                    remaining_time = restriction["timestamp"] + restriction["duration"] - now
                    remaining_time = ctx.bot.misc.humanize_time(int(remaining_time))
                if table == "blacklist_user":
                    await ctx.send_warning(f"You are blacklisted from using **evelina**.\n> **Reason:** {reason}\n> **Duration:** {remaining_time if remaining_time else 'Permanent'}")
                elif table == "blacklist_server":
                    await ctx.send_warning(f"You are blacklisted from using **evelina** in this server.\n> **Reason:** {reason}\n> **Duration:** {remaining_time if remaining_time else 'Permanent'}")
                elif table == "blacklist_cog":
                    cog = restriction.get("cog", "Unknown cog")
                    await ctx.send_warning(f"You are blacklisted from using `{ctx.command.cog_name.lower()}` system.\n> **Reason:** {reason}\n> **Duration:** {remaining_time if remaining_time else 'Permanent'}")
                elif table == "blacklist_cog_server":
                    cog = restriction.get("cog", "Unknown cog")
                    await ctx.send_warning(f"You are blacklisted from using `{ctx.command.cog_name.lower()}` system in this server.\n> **Reason:** {reason}\n> **Duration:** {remaining_time if remaining_time else 'Permanent'}")
                elif table == "blacklist_command":
                    command = restriction.get("command", "Unknown command")
                    await ctx.send_warning(f"You are blacklisted from using `{ctx.command.name.lower()}`.\n> **Reason:** {reason}\n> **Duration:** {remaining_time if remaining_time else 'Permanent'}")
                elif table == "blacklist_command_server":
                    command = restriction.get("command", "Unknown command")
                    await ctx.send_warning(f"You are blacklisted from using `{ctx.command.name.lower()}` in this server.\n> **Reason:** {reason}\n> **Duration:** {remaining_time if remaining_time else 'Permanent'}")
                return False
    return True

# async def check_availability(ctx: EvelinaContext) -> bool:
#     if ctx.guild is None:
#         await ctx.send_warning("You can't use this command in DMs")
#         return False
#     if ctx.guild.me == None:
#         return True
#     check_whitelist = await ctx.bot.db.fetchrow("SELECT * FROM instance WHERE user_id = $1 AND guild_id = $2", ctx.bot.application_id, ctx.guild.id)
#     if not check_whitelist:
#         check_whitelist_addon = await ctx.bot.db.fetchrow("SELECT * FROM instance_addon WHERE user_id = $1 AND guild_id = $2", ctx.bot.application_id, ctx.guild.id)    
#         if not check_whitelist_addon:
#             check_authorized = await ctx.bot.db.fetchrow("SELECT * FROM authorized WHERE guild_id = $1", ctx.guild.id)
#             if not check_authorized:
#                 embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} **{ctx.guild.name}** is not whitelisted from evelina.")
#                 try:
#                     await ctx.send(embed=embed)
#                 except Exception:
#                     pass
#                 try:
#                     await ctx.guild.leave()
#                 except Exception:
#                     pass
#                 return False
#             return True
#         return True
#     return True