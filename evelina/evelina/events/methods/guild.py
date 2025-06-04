import json
import math
import orjson
import aiohttp
import asyncio
import humanize

from datetime import datetime, timedelta

from discord import Guild, Invite, Role, TextChannel, AuditLogEntry, User, Embed, NotFound, Thread, utils
from discord.abc import GuildChannel

from modules.styles import colors, icons
from modules.evelinabot import Evelina, LoggingMeasures

class GuildMethods:
    def __init__(self, bot: Evelina):
        self.bot = bot
        self.log = LoggingMeasures(self.bot)

    async def on_guildname_change(self, before: Guild, after: Guild):
        if before.name != after.name:
            await self.bot.db.execute("INSERT INTO guildnames VALUES ($1,$2,$3)", after.id, str(before), int(datetime.now().timestamp()))

    async def on_vanity_change(self, before: Guild, after: Guild):
        if before.vanity_url_code != after.vanity_url_code:
            if before.vanity_url_code is None:
                return
            else:
                return await self.bot.db.execute("INSERT INTO vanitys VALUES ($1,$2,$3)", after.id, str(before.vanity_url_code), int(datetime.now().timestamp()))
            
    async def on_vanity_tracking(self, before: Guild, after: Guild):
        if before.vanity_url_code != after.vanity_url_code:
            if before.vanity_url_code is None:
                return
            results = await self.bot.db.fetch("SELECT * FROM webhook_vanity")
            headers = {"Content-Type": "application/json"}
            invalid_webhooks = []
            async with aiohttp.ClientSession(headers=headers) as session:
                for result in results:
                    if result["length"] is not None and len(before.vanity_url_code) > result["length"]:
                        continue
                    name = result['name'] if result['name'] else "Evelina - Vanitys"
                    avatar = result['avatar'] if result['avatar'] else icons.EVELINA
                    json_data = {
                        "username": name,
                        "avatar_url": avatar,
                        "content": f"New vanity available: **{before.vanity_url_code}**"
                    }
                    try:
                        async with session.post(result["webhook_url"], json=json_data) as r:
                            if r.status == 429:
                                retry_after = int(r.headers.get("Retry-After", 1))
                                await asyncio.sleep(retry_after)
                            elif r.status not in [204, 429]:
                                invalid_webhooks.append(result["webhook_url"])
                    except Exception:
                        invalid_webhooks.append(result["webhook_url"])
            if invalid_webhooks:
                await self.bot.db.execute("DELETE FROM webhook_vanity WHERE webhook_url = ANY($1)", invalid_webhooks)

    async def on_eventrole_delete(self, role: Role):
        for delete in ["autorole", "autorole_bots", "autorole_humans", "counters", "invites_rewards", 
                "jail", "level_multiplier", "level_multiplier_voice", "level_rewards", "booster_award", 
                "lockdown_role", "mute_images", "mute_reactions", "reactionrole", "suggestions_module",
                "voicerole_default", "warns_rewards", "restrictcommand"]:
            await self.bot.db.execute(f"DELETE FROM {delete} WHERE role_id = $1", role.id)

    async def on_moderation_event(self, channel: GuildChannel):
        try:
            if check := await self.bot.db.fetchrow("SELECT * FROM jail WHERE guild_id = $1", channel.guild.id):
                if role := channel.guild.get_role(int(check["role_id"])):
                    await channel.set_permissions(role, view_channel=False, reason="overwriting permissions for jail role")
        except Exception:
            pass
        try:
            if check:= await self.bot.db.fetchrow("SELECT * FROM mute_reactions WHERE guild_id = $1", channel.guild.id):
                if role := channel.guild.get_role(int(check["role_id"])):
                    await channel.set_permissions(role, add_reactions=False, reason="overwriting permissions for mute reactions role")
        except Exception:
            pass
        try:
            if check := await self.bot.db.fetchrow("SELECT * FROM mute_images WHERE guild_id = $1", channel.guild.id):
                if role := channel.guild.get_role(int(check["role_id"])):
                    await channel.set_permissions(role, attach_files=False, reason="overwriting permissions for mute images role")
                    await channel.set_permissions(role, embed_links=False, reason="overwriting permissions for mute images role")
        except Exception:
            pass

    async def on_ticketchannel_delete(self, channel: GuildChannel):
        if str(channel.type) == "text":
            await self.bot.db.execute("DELETE FROM ticket_opened WHERE guild_id = $1 AND channel_id = $2", channel.guild.id, channel.id)

    async def on_spamchannel_delete(self, channel: GuildChannel):
        if str(channel.type) == "text":
            check = await self.bot.db.fetchval("SELECT channels FROM automod_spam WHERE guild_id = $1", channel.guild.id)
            if check:
                channels = json.loads(check)
                if channel.id in channels:
                    channels.remove(channel.id)
                    await self.bot.db.execute("UPDATE automod_spam SET channels = $1 WHERE guild_id = $2", json.dumps(channels), channel.guild.id)

    async def on_repeatchannel_delete(self, channel: GuildChannel):
        if str(channel.type) == "text":
            check = await self.bot.db.fetchval("SELECT channels FROM automod_repeat WHERE guild_id = $1", channel.guild.id)
            if check:
                channels = json.loads(check)
                if channel.id in channels:
                    channels.remove(channel.id)
                    await self.bot.db.execute("UPDATE automod_repeat SET channels = $1 WHERE guild_id = $2", json.dumps(channels), channel.guild.id)

    async def on_eventchannel_delete(self, channel: GuildChannel):
        if channel.type.name == "text":
            for delete in ["welcome", "boost", "leave", "autopublish", 
                      "autoreact_channel", "autothread", "bumpreminder", "button_message", "button_role", 
                      "button_settings", "channel_disabled_commands", "channel_disabled_module", "confess", "giveaway",
                      "jail", "number_counter", "only_bot", "only_img",
                      "only_link", "only_text", "paginate_embeds", "paypal", "quotes",
                      "reactionrole", "reminder", "reposter_channels", "snipes", "snipes_edit",
                      "snipes_reaction", "starboard", "stickymessage", "suggestions_module", "timer",
                      "autopost_twitch", "vouches_settings"]:
                await self.bot.db.execute(f"DELETE FROM {delete} WHERE channel_id = $1", channel.id)
            for update in ["leveling"]:
                await self.bot.db.execute(f"UPDATE {update} SET channel_id = $1 WHERE channel_id = $1", channel.id)

    async def on_thread_update(self, before: Thread, after: Thread):
        if before.archived != after.archived:
            if after.archived:
                check = await self.bot.db.fetchval("SELECT state FROM thread_watcher WHERE guild_id = $1", before.guild.id)
                if check:
                    await after.edit(archived=False, reason="Thread unarchived through thread watcher")

    async def on_audit_log_entry_create_logging(self, entry: AuditLogEntry):
        if not entry.guild.me.guild_permissions.view_audit_log:
            return
        if getattr(entry, '_target_id', None) is None:
            return
        if entry.target is None:
            return
        if isinstance(entry.target, User) and await self.log.is_ignored(entry.guild.id, "users", entry.target.id):
            return
        if isinstance(entry.target, Role) and await self.log.is_ignored(entry.guild.id, "roles", entry.target.id):
            return
        if isinstance(entry.target, TextChannel) and await self.log.is_ignored(entry.guild.id, "channels", entry.target.id):
            return
        logs = await self.log.audit_log_handler.get_audit_logs_throttled(entry.guild)
        if logs is None:
            return
        record = await self.bot.db.fetchrow("SELECT * FROM logging WHERE guild_id = $1", entry.guild.id)
        channel_id = None
        if record:
            if entry.action.name in ["ban", "unban", "kick", "bot_add"]:
                channel_id = record['moderation']
            elif entry.action.name == "member_update":
                before = entry.changes.before
                after = entry.changes.after
                timed_out_before = getattr(before, 'timed_out_until', None)
                timed_out_after = getattr(after, 'timed_out_until', None)
                if timed_out_before != timed_out_after:
                    channel_id = record['moderation']
            elif entry.action.name.startswith("channel"):
                channel_id = record['channels']
            elif entry.action.name.startswith("role"):
                channel_id = record['roles']
            elif entry.action.name.startswith("guild"):
                channel_id = record['guild']
            elif entry.action.name == "member_role_update":
                channel_id = record['roles']
        channel = await self.log.fetch_logging_channel(entry.guild, channel_id)
        if isinstance(channel, (TextChannel, Thread)):
            if not channel.permissions_for(channel.guild.me).send_messages:
                return
            if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                return
            embed = Embed(color=colors.NEUTRAL, title=entry.action.name.title().replace("_", " ").replace("Member Update", "Timeout"), timestamp=entry.created_at)
            match entry.target:
                case User():
                    icon_url = entry.target.avatar.url if entry.target.avatar else entry.target.default_avatar.url
                case _:
                    icon_url = None
            try:
                match entry.action.name:
                    case "ban":
                        embed.description = f"<@{entry.target.id}> got banned"
                        embed.set_author(name=str(entry.target), icon_url=icon_url)
                        embed.add_field(name="User", value=f"**{entry.target}** (`{entry.target.id}`)", inline=False)
                        embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                        embed.set_footer(text=f"Members: {entry.guild.member_count} | ID: {entry.target.id}")
                        current_timestamp = utils.utcnow().timestamp()
                        if entry.user and entry.user.id != self.bot.user.id:
                            history_id = await self.log.insert_history(entry, "Ban", 'None', entry.reason, current_timestamp)
                            embed.title = f"Ban #{history_id}"
                        else:
                            return
                    case "unban":
                        embed.description = f"<@{entry.target.id}> got unbanned"
                        embed.set_author(name=str(entry.target), icon_url=icon_url)
                        embed.add_field(name="User", value=f"**{entry.target}** (`{entry.target.id}`)", inline=False)
                        embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                        embed.set_footer(text=f"Members: {entry.guild.member_count} | ID: {entry.target.id}")
                        current_timestamp = utils.utcnow().timestamp()
                        if entry.user and entry.user.id != self.bot.user.id:
                            history_id = await self.log.insert_history(entry, "Unban", 'None', entry.reason, current_timestamp)
                            embed.title = f"Unban #{history_id}"
                        else:
                            return
                    case "kick":
                        embed.description = f"<@{entry.target.id}> got kicked"
                        embed.set_author(name=str(entry.target), icon_url=icon_url)
                        embed.add_field(name="User", value=f"**{entry.target}** (`{entry.target.id}`)", inline=False)
                        embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                        embed.set_footer(text=f"Members: {entry.guild.member_count} | ID: {entry.target.id}")
                        current_timestamp = utils.utcnow().timestamp()
                        if entry.user and entry.user.id != self.bot.user.id:
                            history_id = await self.log.insert_history(entry, "Kick", 'None', entry.reason, current_timestamp)
                            embed.title = f"Kick #{history_id}"
                        else:
                            return
                    case "member_update":
                        before = entry.changes.before
                        after = entry.changes.after
                        timed_out_before = getattr(before, 'timed_out_until', None)
                        timed_out_after = getattr(after, 'timed_out_until', None)
                        if timed_out_before != timed_out_after:
                            if timed_out_after is None:
                                embed.description = f"<@{entry.target.id}> got unmuted"
                                current_timestamp = utils.utcnow().timestamp()
                                if entry.user.id != self.bot.user.id:
                                    history_id = await self.log.insert_history(entry, "Unmute", 'None', entry.reason, current_timestamp)
                                    embed.title = f"Unmute #{history_id}"
                                else:
                                    return
                            else:
                                timestamp = int(timed_out_after.timestamp())
                                embed.description = f"<@{entry.target.id}> got muted until <t:{timestamp}:f>"
                                current_timestamp = utils.utcnow().timestamp()
                                duration = timed_out_after - utils.utcnow()
                                duration_seconds = math.ceil(duration.total_seconds())
                                rounded_duration = timedelta(seconds=duration_seconds)
                                if entry.user.id != self.bot.user.id:
                                    history_id = await self.log.insert_history(entry, "Mute", humanize.naturaldelta(rounded_duration), entry.reason, current_timestamp)
                                    embed.title = f"Mute #{history_id}"
                                else:
                                    return
                            embed.set_author(name=str(entry.target), icon_url=entry.target.avatar.url if entry.target.avatar else entry.target.default_avatar.url)
                            embed.add_field(name="User", value=f"**{entry.target}** (`{entry.target.id}`)", inline=False)
                            embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                            embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
                            embed.set_footer(text=f"Members: {entry.guild.member_count} | ID: {entry.target.id}")
                    case "channel_create":
                        embed.description = f"<#{entry.target.id}> got created"
                        embed.set_author(name=entry.guild.name, icon_url=entry.guild.icon.url if entry.guild.icon else None)
                        embed.add_field(name="Channel", value=f"**{entry.target.name}** (`{entry.target.id}`)", inline=False)
                        embed.add_field(name="Created by", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.target.id}")
                    case "channel_delete":
                        embed.description = f"<#{entry.target.id}> got deleted"
                        embed.set_author(name=entry.guild.name, icon_url=entry.guild.icon.url if entry.guild.icon else None)
                        embed.add_field(name="Channel", value=f"**{entry.target.name}** (`{entry.target.id}`)", inline=False)
                        embed.add_field(name="Deleted by", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.target.id}")
                    case "channel_update":
                        if getattr(entry.before, "name", None) != getattr(entry.after, "name", None):
                            embed.description = (f"<#{entry.target.id}> got a different name")
                            embed.add_field(name="Before", value=entry.before.name, inline=True)
                            embed.add_field(name="After", value=entry.after.name, inline=True)
                        elif getattr(entry.before, "topic", None) != getattr(entry.after, "topic", None):
                            embed.description = (f"<#{entry.target.id}> got a different topic")
                            embed.add_field(name="Before", value=entry.before.topic, inline=False)
                            embed.add_field(name="After", value=entry.after.topic, inline=False)
                        elif getattr(entry.before, "nsfw", None) != getattr(entry.after, "nsfw", None):
                            embed.description = f"<#{entry.target.id}> {'is now **NSFW**' if entry.after.nsfw else 'is **not NSFW** anymore'}"
                        else:
                            return
                        embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.target.id}")
                    case "bot_add":
                        embed.description = (f"{entry.target.mention} got added to this server")
                        embed.set_author(name=str(entry.target), icon_url=(entry.target.avatar.url if entry.target.avatar else None))
                        embed.add_field(name="Bot created", value=f"{utils.format_dt(entry.target.created_at)} {utils.format_dt(entry.target.created_at, style='R')}", inline=False)
                        embed.add_field(name="Added by", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"Members: {entry.guild.member_count} | ID: {entry.target.id}")
                    case "role_create":
                        embed.add_field(name="Role", value=f"**{entry.target.name}** (`{entry.target.id}`)", inline=False)
                        embed.add_field(name="Created by", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.target.id}")
                    case "role_delete":
                        embed.add_field(name="Role", value=f"**{entry.before.name}** (`{entry.target.id}`)", inline=False)
                        embed.add_field(name="Deleted by", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.target.id}")
                    case "role_update":
                        if getattr(entry.before, "name", None) != getattr(entry.after, "name", None):
                            embed.description = (f"{entry.target.mention}'s name got updated")
                            embed.add_field(name="Before", value=entry.before.name, inline=True)
                            embed.add_field(name="After", value=entry.after.name, inline=True)
                        elif getattr(entry.before, "hoist", None) != getattr(entry.after, "hoist", None):
                            embed.description = f"{entry.target.mention} {'is **hoisted**' if entry.after.hoist else 'is **not** hoisted anymore'}"
                        elif getattr(entry.before, "mentionable", None) != getattr(entry.after, "mentionable", None):
                            embed.description = f"{entry.target.mention} {'is **mentionable**' if entry.after.mentionable else 'is **not** mentionable anymore'}"
                        else:
                            return
                        embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.target.id}")
                    case "guild_update":
                        if getattr(entry.before, "name", None) != getattr(entry.after, "name", None):
                            embed.description = "Server name updated"
                            embed.add_field(name=f"Before", value=entry.before.name, inline=True)
                            embed.add_field(name="After", value=entry.after.name, inline=True)
                        elif getattr(entry.before, "vanity_url_code", None) != getattr(entry.after, "vanity_url_code", None):
                            embed.description = "Server vanity updated"
                            embed.add_field(name="Before", value=entry.before.vanity_url_code, inline=True)
                            embed.add_field(name="After", value=entry.after.vanity_url_code, inline=True)
                        elif getattr(entry.before, "owner", None) != getattr(entry.after, "owner", None):
                            embed.description = f"Server ownership was transferred to **{entry.after.owner}** (`{entry.user.id}`)"
                        else:
                            return
                        embed.set_author(name=str(entry.guild), icon_url=entry.guild.icon)
                        embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.guild.id}")
                    case "member_role_update":
                        added_roles = [r for r in entry.changes.after.roles if not await self.log.is_ignored(entry.guild.id, "roles", r.id)]
                        removed_roles = [r for r in entry.changes.before.roles if not await self.log.is_ignored(entry.guild.id, "roles", r.id)]
                        if not added_roles and not removed_roles:
                            return
                        embed.description = (f"<@{entry.target.id}>'s roles got updated")
                        embed.add_field(name="Moderator", value=f"**{entry.user}** (`{entry.user.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {entry.target.id}")
                        if added_roles:
                            embed.add_field(name="Added Roles",
                                value=(", ".join([r.mention for r in added_roles])
                                    if len(added_roles) < 6
                                    else ", ".join([r.mention for r in added_roles[:5]]) + f" (+ {len(added_roles)-5} more)"), inline=False)
                        if removed_roles:
                            embed.add_field(name="Removed Roles", value=(
                                    ", ".join([r.mention for r in removed_roles])
                                    if len(removed_roles) < 6
                                    else ", ".join([r.mention for r in removed_roles[:5]]) + f" (+ {len(removed_roles)-5} more)"), inline=False)
                        embed.add_field(name="Reason", value=entry.reason or "No reason provided", inline=False)
            except Exception:
                return
            try:
                await self.log.add_to_queue(channel, embed, None)
            except Exception:
                pass

    async def on_invite_create(self, invite: Invite):
        guild = invite.guild
        try:
            invites = await guild.invites()
        except Exception:
            return
        invites_data = [{"code": invite.code, "uses": invite.uses, "inviter_id": invite.inviter.id if invite.inviter else None} for invite in invites]
        await self.bot.redis.set(f"invites_{guild.id}", orjson.dumps(invites_data).decode("utf-8"))

    async def on_invite_delete(self, invite: Invite):
        guild = invite.guild
        invites = await guild.invites()
        invites_data = [{"code": invite.code, "uses": invite.uses, "inviter_id": invite.inviter.id if invite.inviter else None} for invite in invites]
        await self.bot.redis.set(f"invites_{guild.id}", orjson.dumps(invites_data).decode("utf-8"))

    async def on_guild_join(self, guild: Guild):
        check = await self.bot.db.fetchrow("SELECT * FROM blacklist_server WHERE guild_id = $1", guild.id)
        if check:
            await guild.leave()