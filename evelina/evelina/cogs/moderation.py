import re
import uuid
import time
import string
import random
import asyncpg
import json
import asyncio
import datetime

from io import BytesIO
from datetime import datetime, timedelta
from typing import Union, Optional
from collections import defaultdict, deque
from humanfriendly import format_timespan

from discord import Member, PermissionOverwrite, VoiceChannel, ButtonStyle, File, Embed, Interaction, utils, TextChannel, User, Object, Role, Forbidden, CategoryChannel, Message, Thread, Guild, HTTPException, NotFound, TextStyle
from discord.ui import Button, View
from discord.ext.commands import Cog, has_guild_permissions, command, group, CurrentChannel, bot_has_guild_permissions, cooldown, Author, BucketType
from discord.errors import HTTPException, Forbidden, NotFound

from modules.styles import emojis, colors
from modules.helpers import EvelinaContext, Invoking, DmInvoking, ChannelInvoking
from modules.measures import LoggingMeasures
from modules.converters import NoStaff, NewRoleConverter
from modules.predicates import is_jail, admin_antinuke
from modules.validators import ValidTime, ValidNickname, ValidMessage
from modules.misc.views import BoosterMod
from modules.persistent.appeal import AppealsView

class Moderation(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = LoggingMeasures(self.bot)
        self.description = "Moderation commands"
        self.locks = defaultdict(asyncio.Lock)
        self.role_lock = defaultdict(asyncio.Lock)
        self.message_queue = deque()
        self.task = asyncio.create_task(self.process_queue())

    async def process_queue(self):
        try:
            while True:
                if self.message_queue:
                    channel, embed, view, file = self.message_queue.popleft()
                    try:
                        if file:
                            await channel.send(embed=embed, view=view, file=file)
                        else:
                            await channel.send(embed=embed, view=view)
                    except Exception:
                        pass
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def add_to_queue(self, channel, embed, view, file=None):
        self.message_queue.append((channel, embed, view, file))

    async def fetch_logging_channel(self, guild: Guild, channel_id: Optional[int]) -> Optional[Union[TextChannel, Thread]]:
        if not channel_id:
            return None
        channel = guild.get_channel(channel_id) or guild.get_thread(channel_id)
        if not channel:
            try:
                channel = await guild.fetch_channel(channel_id)
            except (NotFound, Forbidden, HTTPException):
                return None
        if not channel.permissions_for(guild.me).send_messages:
            return None
        return channel
    
    async def stop(self):
        self.task.cancel()
        try:
            await self.task
        except asyncio.CancelledError:
            pass

    async def logging(self, guild: Guild, user: User, moderator: User, reason: str, description: str, punishment: str, history_id: int):
        if guild:
            record = await self.bot.db.fetchval("SELECT moderation FROM logging WHERE guild_id = $1", guild.id)
            if record:
                channel = await self.fetch_logging_channel(guild, record)
                if isinstance(channel, (TextChannel, Thread)):
                    if not channel.permissions_for(channel.guild.me).send_messages:
                        return
                    if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                        return
                    embed = Embed(color=colors.NEUTRAL, timestamp=datetime.utcnow())
                    embed.description = f"{user.mention} got {description}"
                    embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
                    embed.add_field(name="User", value=f"**{user.name}** (`{user.id}`)", inline=False)
                    embed.add_field(name="Moderator", value=f"**{moderator.name}** (`{moderator.id}`)", inline=False)
                    embed.add_field(name="Reason", value=reason or "N/A", inline=False)
                    embed.set_footer(text=f"Members: {guild.member_count} | ID: {user.id}")
                    embed.title = f"{punishment} #{history_id}"
                    try:
                        await self.add_to_queue(channel, embed, None)
                    except NotFound:
                        pass

    async def punish_a_bitch(self: "Moderation", module: str, member: Member, reason: str, role: Optional[Role] = None):
        if self.bot.an.get_bot_perms(member.guild):
            if await self.bot.an.is_module(module, member.guild):
                if not await self.bot.an.is_whitelisted(member):
                    if not role:
                        if not await self.bot.an.check_threshold(module, member):
                            return
                    if self.bot.an.check_hieracy(member, member.guild.me):
                        cache = await self.bot.cache.get(f"{module}-{member.guild.id}")
                        if not cache:
                            await self.bot.cache.set(f"{module}-{member.guild.id}", True, 5)
                            tasks = [self.bot.an.decide_punishment(module, member, reason)]
                            action_time = datetime.now()
                            check = await self.bot.db.fetchrow("SELECT owner_id, logs FROM antinuke WHERE guild_id = $1", member.guild.id)
                            await self.bot.an.take_action(reason, member, tasks, action_time, check["owner_id"], member.guild.get_channel(check["logs"]))
            
    async def insert_history(self, ctx, member, action_type, duration, reason, timestamp, msg_id=None):
        max_retries = 5
        attempts = 0
        while attempts < max_retries:
            try:
                record = await self.bot.db.fetchrow(
                    """
                    INSERT INTO history 
                    (id, guild_id, user_id, moderator_id, server_id, punishment, duration, reason, time, appeal_id) 
                    VALUES (
                        (SELECT COALESCE(MAX(id), 0) + 1 FROM history),
                        (SELECT COALESCE(MAX(guild_id), 0) + 1 FROM history WHERE server_id = $1), 
                        $2, $3, $4, $5, $6, $7, $8, $9
                    ) RETURNING guild_id
                    """,
                    ctx.guild.id, member.id, ctx.author.id, ctx.guild.id, action_type, duration, reason, timestamp, msg_id
                )
                if record:
                    return str(record['guild_id'])
                return None
            except asyncpg.UniqueViolationError:
                attempts += 1
                await asyncio.sleep(0.1)
                continue
            except Exception:
                return None
        return None

    @command(brief="manage roles", usage="restore comminate")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def restore(self, ctx: EvelinaContext, *, member: NoStaff):
        """Give a member their roles back after rejoining"""
        async with self.locks[ctx.guild.id]:
            check = await self.bot.db.fetchrow("SELECT roles FROM restore WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
            if not check:
                return await ctx.send_warning("This member doesn't have any roles saved.")
        roles = [ctx.guild.get_role(r) for r in json.loads(check["roles"]) if ctx.guild.get_role(r)]
        assignable_roles = [role for role in roles if role.is_assignable() and role.position < ctx.author.top_role.position and role.position < ctx.guild.me.top_role.position]
        if not assignable_roles:
            return await ctx.send_warning("No assignable roles were found to restore. Make sure your role hierarchy allows this.")
        restored_roles = []
        for role in assignable_roles:
            try:
                await member.add_roles(role, reason=f"Dangerous roles restored by {ctx.author}")
                restored_roles.append(role.mention)
            except Forbidden:
                return await ctx.send_warning(f"I don't have permission to assign the role: {role.mention}")
            except Exception:
                return await ctx.send_warning(f"An unexpected error occurred with the role: {role.mention}")
        if restored_roles:
            description = f"Successfully restored the following roles for {member.mention}: {', '.join(restored_roles)}."
            if len(description) > 4096:
                description = description[:4093] + "..."
            await ctx.send_success(description)
        else:
            await ctx.send_warning("No roles were restored due to permission issues or hierarchy conflicts")
        try:
            await self.bot.db.execute("DELETE FROM restore WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        except Exception:
            await ctx.send_warning("Roles were restored, but an error occurred while cleaning up the database")
        
    @command(brief="administrator")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def setjail(self, ctx: EvelinaContext):
        """Set up jail module"""
        async with self.locks[ctx.guild.id]:
            if await self.bot.db.fetchrow("SELECT * FROM jail WHERE guild_id = $1", ctx.guild.id):
                return await ctx.send_warning(f"Jail is **already** configured\n> Use `{ctx.clean_prefix}unsetjail` to disable it")
            mes = await ctx.send(embed=Embed(color=colors.LOADING, description=f"{emojis.LOADING} {ctx.author.mention}: Configuring **jail system** and creating needed **role/channel**"))
            async with ctx.typing():
                try:
                    role = await ctx.guild.create_role(name="jail", reason="creating jail role")
                except Forbidden:
                    return await ctx.send_warning("I don't have permission to create roles. Please check my permissions.")
                for channel in ctx.guild.channels:
                    try:
                        await channel.set_permissions(role, view_channel=False)
                        await asyncio.sleep(1)
                    except Exception:
                        continue
                overwrite = {role: PermissionOverwrite(view_channel=True), ctx.guild.default_role: PermissionOverwrite(view_channel=False)}
                try:
                    text = await ctx.guild.create_text_channel(name="jail-evelina", overwrites=overwrite, reason="creating jail channel")
                    await self.bot.db.execute("INSERT INTO jail VALUES ($1,$2,$3)", ctx.guild.id, text.id, role.id)
                except Exception:
                    try:
                        return await mes.edit(embed=Embed(color=colors.WARNING, description=f"{emojis.WARNING} {ctx.author.mention}: An error occurred while configuring jail"))
                    except Exception:
                        return await ctx.send_warning("An error occurred while configuring jail")
                try:
                    return await mes.edit(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: Jail successfully configured"))
                except Exception:
                    return await ctx.send_success("Jail successfully configured")
            
    @command(brief="administrator")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    @is_jail()
    async def unsetjail(self, ctx: EvelinaContext):
        """Disable the jail module"""
        async def yes_func(interaction: Interaction):
            check = await self.bot.db.fetchrow("SELECT * FROM jail WHERE guild_id = $1", interaction.guild.id)
            role = interaction.guild.get_role(check["role_id"])
            channel = interaction.guild.get_channel(check["channel_id"])
            if role:
                try:
                    await role.delete(reason=f"jail disabled by {ctx.author}")
                except Forbidden:
                    return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: I don't have permission to delete the jail role"), view=None)
                except NotFound:
                    pass
            if channel:
                try:
                    await channel.delete(reason=f"jail disabled by {ctx.author}")
                except Forbidden:
                    return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: I don't have permission to delete the jail channel"), view=None)
                except NotFound:
                    pass
            for idk in ["DELETE FROM jail WHERE guild_id = $1", "DELETE FROM jail_members WHERE guild_id = $1"]:
                await self.bot.db.execute(idk, interaction.guild.id)
            return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Disabled the jail module"), view=None)
        async def no_func(interaction: Interaction) -> None:
            await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Jail deactivation got canceled"), view=None)
        return await ctx.confirmation_send(f"{ctx.author.mention}: Are you sure you want to **disable** the jail module?\nThis action is **IRREVERSIBLE**", yes_func, no_func)
    
    @command(brief="manage messages", usage="jail comminate 1d reason --s", extras={"s": "Punish a user silently"})
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    @is_jail()
    async def jail(self, ctx: EvelinaContext, member: NoStaff, time: Optional[ValidTime] = None, *, reason: str = "No reason provided"):
        """Restrict someone from the server's channels"""
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        msg = None
        time = time or 2419200
        max_duration = 365 * 24 * 60 * 60
        formated_time = format_timespan(time)
        if time > max_duration:
            return await ctx.send_warning("You can't jail a user for more than **365 days**")
        if await self.bot.db.fetchrow("SELECT * FROM jail_members WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id):
            return await ctx.send_warning(f"{member.mention} is **already** jailed")
        check = await self.bot.db.fetchrow("SELECT * FROM jail WHERE guild_id = $1", ctx.guild.id)
        role = ctx.guild.get_role(check["role_id"])
        if not role:
            return await ctx.send_warning(f"Jail role **not found**. Please `{ctx.clean_prefix}unsetjail` and set it back")
        if ctx.guild.me.top_role <= role:
            return await ctx.send_warning(f"Role **{role.mention}** is over my highest role")
        old_roles = [r.id for r in member.roles if r.is_assignable()]
        roles = [r for r in member.roles if not r.is_assignable()]
        roles.append(role)
        try:
            await member.move_to(None)
        except Exception:
            pass
        try:
            await member.edit(roles=roles, reason=reason)
        except Exception:
            return await ctx.send_warning(f"I don't have permission to jail this member. Please check my role hierarchy")
        expiration_date = datetime.now() + timedelta(seconds=time)
        try:
            if send_dm:
                if not await DmInvoking(ctx).send(member, reason, case_id, formated_time):
                    embed = Embed(description=f"You have been jailed for **{formated_time}** on **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.ERROR)
                    msg = await member.send(embed=embed, view=AppealsView(self))
        except Exception:
            pass
        async with self.locks[ctx.guild.id]:
            if not await self.bot.db.fetchrow("SELECT * FROM jail_members WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id):
                await self.bot.db.execute("INSERT INTO jail_members VALUES ($1, $2, $3, $4, $5)", ctx.guild.id, member.id, json.dumps(old_roles), datetime.now(), expiration_date)
        current_timestamp = utils.utcnow().timestamp()
        duration = formated_time if time != 0 else 'Infinity'
        history_id = await self.insert_history(ctx, member, "Jail", duration, reason, current_timestamp, msg.id if msg else None)
        expiration_timestamp = expiration_date.timestamp()
        await self.logging(ctx.guild, member, ctx.author, reason, f"jailed until <t:{int(expiration_timestamp)}:f>", "Jail", history_id)
        if not await Invoking(ctx).send(member, reason, formated_time, history_id):
            await ctx.send_success(f"Jailed {member.mention} (`#{history_id}`) for {formated_time} - **{reason}**")
        channel = ctx.guild.get_channel(check["channel_id"])
        if channel:
            if not await ChannelInvoking(ctx, channel).send(member, reason, formated_time, history_id):
                return await channel.send(f"{member.mention} has been jailed for **{formated_time}** - **{reason}**")
        
    @command(brief="manage messages", usage="unjail comminate rassist --s", extras={"s": "Punish a user silently"})
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_roles=True)
    @is_jail()
    async def unjail(self, ctx: EvelinaContext, member: Member, *, reason: str = "No reason provided"):
        """Lift the jail restriction from a member"""
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        formated_time = None
        jailed_data = await self.bot.db.fetchrow("SELECT roles FROM jail_members WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        if not jailed_data:
            return await ctx.send_warning(f"{member.mention} is **not** jailed")
        jail_info = await self.bot.db.fetchrow("SELECT * FROM jail WHERE guild_id = $1", ctx.guild.id)
        jail_role = ctx.guild.get_role(jail_info["role_id"])
        if not jail_role:
            return await ctx.send_warning("Jail role **not found**. Please unset jail and set it back")
        if ctx.guild.me.top_role <= jail_role:
            return await ctx.send_warning(f"Role **{jail_role.mention}** is over my highest role")
        roles = [ctx.guild.get_role(role_id) for role_id in json.loads(jailed_data["roles"]) if ctx.guild.get_role(role_id)]
        manageable_roles = [role for role in roles if role and role.position < ctx.guild.me.top_role.position]
        if ctx.guild.premium_subscriber_role in member.roles:
            manageable_roles.append(ctx.guild.premium_subscriber_role)
        try:
            await member.edit(roles=manageable_roles, reason=reason)
        except Exception:
            pass
        try:
            if send_dm:
                if not await DmInvoking(ctx).send(member, reason, case_id, formated_time):
                    embed = Embed(description=f"You have been unjailed on **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.SUCCESS)
                    await member.send(embed=embed)
        except Exception:
            pass
        await self.bot.db.execute("DELETE FROM jail_members WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, member, "Unjail", 'None', reason, current_timestamp)
        await self.logging(ctx.guild, member, ctx.author, reason, "unjailed", "Unjail", history_id)
        if not await Invoking(ctx).send(member, reason, formated_time, history_id):
            await ctx.send_success(f"Unjailed {member.mention} (`#{history_id}`) - {reason}")
        
    @command()
    async def jailed(self, ctx: EvelinaContext):
        """Returns the jailed members"""
        results = await self.bot.db.fetch("SELECT * FROM jail_members WHERE guild_id = $1", ctx.guild.id)
        jailed = [f"<@{result['user_id']}> - {utils.format_dt(result['jailed_at'], style='R')}" for result in results if ctx.guild.get_member(result["user_id"])]
        if len(jailed) > 0:
            return await ctx.paginate(jailed, f"Jailed members", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
        else:
            return await ctx.send_warning("There are no jailed members")
        
    @group(name="history", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_messages=True)
    async def history(self, ctx: EvelinaContext):
        """History of moderation actions"""
        return await ctx.create_pages()

    @history.command(name="user", aliases=["u"], brief="manage messages", usage="history user comminate")
    @has_guild_permissions(manage_messages=True)
    async def history_user(self, ctx: EvelinaContext, user: User = None):
        """View a list of every punishment recorded of a given user"""
        if user is None:
            user = ctx.author
        results = await self.bot.db.fetch("SELECT * FROM history WHERE server_id = $1 AND user_id = $2 ORDER BY guild_id DESC", ctx.guild.id, user.id)
        if not results:
            return await ctx.send_warning(f"No **moderation actions** have been recorded for {user.mention}")
        embeds = []
        entries_per_page = 2
        total_pages = (len(results) + entries_per_page - 1) // entries_per_page
        for i in range(0, len(results), entries_per_page):
            page_number = (i // entries_per_page) + 1
            embed = Embed(title=f"Punishment History for {user.name}", color=colors.NEUTRAL).set_author(name=ctx.guild.name, icon_url=ctx.guild.icon if ctx.guild.icon else None)
            for entry in results[i:i + entries_per_page]:
                proof = f"**Proof:** {entry['proof']}\n" if entry['proof'] else ""
                duration = f"**Duration:** {entry['duration']}\n" if entry['duration'] != "None" else ""
                embed.add_field(
                    name=f"Case Log #{entry['guild_id']} | {entry['punishment']}",
                    value=f"**Punished:** <t:{entry['time']}:f>\n"
                        f"**Moderator:** {self.bot.get_user(entry['moderator_id'])} (`{entry['moderator_id']}`)\n"
                        f"**Reason:** {entry['reason']}\n"
                        f"{duration}{proof}",
                    inline=False
                )
            embed.set_footer(text=f"Page: {page_number}/{total_pages} ({len(results)} entries)")
            embeds.append(embed)
        await ctx.paginator(embeds)

    @history.command(name="moderator", aliases=["mod", "m"], brief="moderate members", usage="history moderator comminate")
    @has_guild_permissions(moderate_members=True)
    async def history_moderator(self, ctx: EvelinaContext, user: User = None):
        """View a list of every punishment recorded by a given moderator"""
        if user is None:
            user = ctx.author
        results = await self.bot.db.fetch("SELECT * FROM history WHERE server_id = $1 AND moderator_id = $2 ORDER BY id DESC", ctx.guild.id, user.id)
        if not results:
            return await ctx.send_warning(f"No **moderation actions** have been recorded for {user.mention}")
        embeds = []
        entries_per_page = 2
        total_pages = (len(results) + entries_per_page - 1) // entries_per_page
        for i in range(0, len(results), entries_per_page):
            page_number = (i // entries_per_page) + 1
            embed = Embed(title=f"Moderation History for {user.name}", color=colors.NEUTRAL).set_author(name=ctx.guild.name, icon_url=ctx.guild.icon if ctx.guild.icon else None)
            for entry in results[i:i + entries_per_page]:
                proof = f"**Proof:** {entry['proof']}\n" if entry['proof'] else ""
                duration = f"**Duration:** {entry['duration']}\n" if entry['duration'] != "None" else ""
                embed.add_field(
                    name=f"Case Log #{entry['guild_id']} | {entry['punishment']}",
                    value=f"**Punished:** <t:{entry['time']}:f>\n"
                        f"**User:** {self.bot.get_user(entry['user_id'])} (`{entry['user_id']}`)\n"
                        f"**Reason:** {entry['reason']}\n"
                        f"{duration}{proof}",
                    inline=False
                )
            embed.set_footer(text=f"Page: {page_number}/{total_pages} ({len(results)} entries)")
            embeds.append(embed)
        await ctx.paginator(embeds)

    @history.command(name="remove", brief="manage guild", usage="history remove 28")
    @has_guild_permissions(manage_guild=True)
    async def history_remove(self, ctx: EvelinaContext, id: int):
        """Remove a specific punishment entry by Guild ID"""
        results = await self.bot.db.execute("SELECT * FROM history WHERE server_id = $1 AND guild_id = $2", ctx.guild.id, id)
        if not results:
            return await ctx.send_warning(f"No history entry with ID **{id}** found")
        await self.bot.db.execute("DELETE FROM history WHERE server_id = $1 AND guild_id = $2", ctx.guild.id, id)
        return await ctx.send_success(f"History entry with ID **{id}** has been successfully removed")

    @history.group(name="clear", invoke_without_command=True, brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def history_clear(self, ctx: EvelinaContext):
        """Clear punishment history"""
        return await ctx.create_pages()

    @history_clear.command(name="user", brief="manage guild", usage="history clear user comminate")
    @has_guild_permissions(manage_guild=True)
    async def history_clear_user(self, ctx: EvelinaContext, user: User):
        """Clear all punishment history for a user"""
        results = await self.bot.db.fetch("SELECT * FROM history WHERE server_id = $1 AND user_id = $2", ctx.guild.id, user.id)
        if not results:
            return await ctx.send_warning(f"No user history entries found for {user.mention}")
        await self.bot.db.fetch("DELETE FROM history WHERE server_id = $1", ctx.guild.id)
        return await ctx.send_success(f"All history user entries for {user.mention} have been cleared")

    @history_clear.command(name="moderator", aliases=["mod", "m"], brief="manage guild", usage="history clear moderator comminate")
    @has_guild_permissions(manage_guild=True)
    async def history_clear_moderator(self, ctx: EvelinaContext, user: User):
        """Clear all punishment history for a moderator"""
        results = await self.bot.db.fetch("SELECT * FROM history WHERE server_id = $1 AND moderator_id = $2", ctx.guild.id, user.id)
        if not results:
            return await ctx.send_warning(f"No moderator history entries found for {user.mention}")
        await self.bot.db.fetch("DELETE FROM history WHERE server_id = $1", ctx.guild.id)
        return await ctx.send_success(f"All history moderator entries for {user.mention} have been cleared")

    @history_clear.command(name="all", brief="administrator")
    @has_guild_permissions(administrator=True)
    async def history_clear_all(self, ctx: EvelinaContext):
        """Clear all punishment history for everyone"""
        results = await self.bot.db.fetch("SELECT * FROM history WHERE server_id = $1", ctx.guild.id)
        if not results:
            return await ctx.send_warning(f"No history entries found")
        await self.bot.db.fetch("DELETE FROM history WHERE server_id = $1", ctx.guild.id)
        return await ctx.send_success(f"All history entries have been cleared")

    async def get_punishment_counts(self, user, guild):
        now = datetime.utcnow()
        seven_days_ago = now - timedelta(days=7)
        fourteen_days_ago = now - timedelta(days=14)
        seven_days_ago_timestamp = int(time.mktime(seven_days_ago.timetuple()))
        fourteen_days_ago_timestamp = int(time.mktime(fourteen_days_ago.timetuple()))
        query_alltime = """
            SELECT punishment, COUNT(*) FROM history
            WHERE moderator_id = $1 AND punishment IN ('Ban', 'Kick', 'Mute', 'Jail') AND server_id = $2
            GROUP BY punishment
        """
        query_last_7d = """
            SELECT punishment, COUNT(*) FROM history
            WHERE moderator_id = $1 AND time >= $2 AND punishment IN ('Ban', 'Kick', 'Mute', 'Jail') AND server_id = $3
            GROUP BY punishment
        """
        query_last_14d = """
            SELECT punishment, COUNT(*) FROM history
            WHERE moderator_id = $1 AND time >= $2 AND punishment IN ('Ban', 'Kick', 'Mute', 'Jail') AND server_id = $3
            GROUP BY punishment
        """
        alltime_data = await self.bot.db.fetch(query_alltime, user, guild)
        last_7d_data = await self.bot.db.fetch(query_last_7d, user, seven_days_ago_timestamp, guild)
        last_14d_data = await self.bot.db.fetch(query_last_14d, user, fourteen_days_ago_timestamp, guild)
        def format_data(data):
            return {row['punishment']: row['count'] for row in data}
        return {
            'alltime': format_data(alltime_data),
            'last_7d': format_data(last_7d_data),
            'last_14d': format_data(last_14d_data)
        }
 
    @command(name="modstats", brief="moderate members", usage="modstats comminate")
    @has_guild_permissions(moderate_members=True)
    async def modstats(self, ctx: EvelinaContext, user: User = Author):
        """View a summary of a moderator's punishment statistics"""
        counts = await self.get_punishment_counts(user.id, ctx.guild.id)
        embed = Embed(title="Punishment Statistics", color=colors.NEUTRAL)
        embed.set_author(name=user.name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)
        if counts['last_7d']:
            embed.add_field(name="7 Days", value="\n".join([f"{key}: {value}" for key, value in counts['last_7d'].items()]), inline=True)
        else:
            embed.add_field(name="7 Days", value="N/A", inline=True)
        if counts['last_14d']:
            embed.add_field(name="14 Days", value="\n".join([f"{key}: {value}" for key, value in counts['last_14d'].items()]), inline=True)
        else:
            embed.add_field(name="14 Days", value="N/A", inline=True)
        if counts['alltime']:
            embed.add_field(name="All Time", value="\n".join([f"{key}: {value}" for key, value in counts['alltime'].items()]), inline=True)
        else:
            embed.add_field(name="All Time", value="N/A", inline=True)
        await ctx.send(embed=embed)

    @command(name="voicemove", aliases=["drag"], brief="move members", usage="voicemove comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voicemove(self, ctx: EvelinaContext, member: Member):
        """Move a member to another voice channel"""
        if not member.voice:
            return await ctx.send_warning("This member is **not** in a voice channel")
        if not ctx.author.voice:
            return await ctx.send_warning("You are **not** in a voice channel")
        if not ctx.author.voice.channel:
            return await ctx.send_warning("You are **not** in a voice channel")
        if not member.voice.channel:
            return await ctx.send_warning("This member is **not** in a voice channel")
        if ctx.author.voice.channel == member.voice.channel:
            return await ctx.send_warning("You are **already** in the same voice channel as this member")
        if not ctx.guild.me.guild_permissions.move_members:
            return await ctx.send_warning("I don't have permission to move members")
        try:
            await member.move_to(ctx.author.voice.channel, reason=f"Member moved by {ctx.author}")
            await ctx.send_success(f"Moved {member.mention} to {ctx.author.voice.channel.mention}")
        except Forbidden:
            await ctx.send_warning("I don't have permission to move this member")

    @command(name="voicemoveall", aliases=["dragall"], brief="Move all members", usage="voicemoveall lounge lounge-2")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(move_members=True)
    async def voicemoveall(self, ctx: EvelinaContext, channel: VoiceChannel, other_channel: VoiceChannel = None):
        """Move all members from a specific voice channel to the author's channel"""
        if not channel:
            return await ctx.send_warning(f"No voice channel named `{channel.name}` found")
        if not ctx.author.voice:
            return await ctx.send_warning("You are **not** in a voice channel")
        author_channel = ctx.author.voice.channel
        target_channel = other_channel if other_channel else channel
        if not other_channel:
            members_to_move = [member for member in author_channel.members]
        else:
            members_to_move = [member for member in channel.members]
        if not members_to_move:
            return await ctx.send_warning(f"No members in `{channel.name}` to move")
        for member in members_to_move:
            if member.voice:
                await member.move_to(target_channel, reason=f"Moved by {ctx.author}")
            else:
                await ctx.send_warning(f"{member.mention} is not connected to a voice channel")
        await ctx.send_success(f"Moved {len(members_to_move)} member(s) from {author_channel.mention} to {channel.mention}")

    @command(name="voicekick", brief="move members", usage="voicekick comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voicekick(self, ctx: EvelinaContext, *, member: NoStaff = None):
        """Kick a member from a voice channel"""
        if member is None:
            member = ctx.author
        if not member.voice:
            return await ctx.send_warning("This member is **not** in a voice channel")
        await member.edit(voice_channel=None, reason=f"Member kicked from voice channel by {ctx.author}")
        await ctx.send_success(f"Kicked {member.mention} from the voice channel")

    @command(name="voicemute", brief="move members", usage="voicemute comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voicemute(self, ctx: EvelinaContext, *, member: NoStaff = None):
        """Voice mute a member"""
        if member is None:
            member = ctx.author
        if not member.voice:
            return await ctx.send_warning("This member is **not** in a voice channel")
        if member.voice.mute:
            return await ctx.send_warning("This member is **already** muted")
        await member.edit(mute=True, reason=f"Member voice muted by {ctx.author}")
        await ctx.send_success(f"Voice muted {member.mention}")

    @command(name="voiceunmute", brief="move members", usage="voiceunmute comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voiceunmute(self, ctx: EvelinaContext, *, member: NoStaff = None):
        """Voice unmute a member"""
        if member is None:
            member = ctx.author
        if not member.voice.mute:
            return await ctx.send_warning(f"This member is **not** voice muted")
        await member.edit(mute=False, reason=f"Member voice unmuted by {ctx.author}")
        await ctx.send_success(f"Voice unmuted {member.mention}")

    @command(name="voicedeafen", brief="move members", usage="voicedeafen comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voicedeafen(self, ctx: EvelinaContext, *, member: NoStaff = None):
        """Deafen a member in a voice channel"""
        if member is None:
            member = ctx.author
        if not member.voice:
            return await ctx.send_warning("This member is **not** in a voice channel")
        if member.voice.deaf:
            return await ctx.send_warning(f"This member is **already** voice deafened")
        await member.edit(deafen=True, reason=f"Member voice deafened by {ctx.author}")
        await ctx.send_success(f"Voice deafened {member.mention}")

    @command(name="voiceundeafen", brief="move members", usage="voiceundeafen comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voiceundeafen(self, ctx: EvelinaContext, *, member: NoStaff = None):
        """Voice undeafen a member"""
        if member is None:
            member = ctx.author
        if not member.voice.deaf:
            return await ctx.send_warning("This member is **not** deafened")
        await member.edit(deafen=False, reason=f"Voice undeafened by {ctx.author}")
        await ctx.send_success(f"Voice undeafened {member.mention}")

    @command(name="voiceban", brief="move members", usage="voiceban comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voiceban(self, ctx: EvelinaContext, *, member: NoStaff):
        """Voice ban a member"""
        check = await self.bot.db.fetchrow("SELECT * FROM voiceban WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        if check:
            return await ctx.send_warning(f"{member.mention} is **already** voice banned")
        if member.voice:
            await member.edit(voice_channel=None, reason=f"Voice ban by {ctx.author}")
        await self.bot.db.execute("INSERT INTO voiceban VALUES ($1, $2, $3, $4)", ctx.guild.id, member.id, ctx.author.id, datetime.now().timestamp())
        return await ctx.send_success(f"Voice banned {member.mention}")
    
    @command(name="voiceunban", brief="move members", usage="voiceunban comminate")
    @has_guild_permissions(move_members=True)
    @bot_has_guild_permissions(move_members=True)
    async def voiceunban(self, ctx: EvelinaContext, *, member: NoStaff):
        """Voice unban a member"""
        check = await self.bot.db.fetchrow("SELECT * FROM voiceban WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        if not check:
            return await ctx.send_warning(f"{member.mention} is **not** voice banned")
        await self.bot.db.execute("DELETE FROM voiceban WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        return await ctx.send_success(f"Voice unbanned {member.mention}")

    @group(name="clear", aliases=["purge", "c"], brief="manage messages", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    @cooldown(1, 10, BucketType.channel)
    async def clear(self, ctx: EvelinaContext, number: int, *, user: User = None):
        """Add/remove roles to/from a user"""
        if number:
            try:
                return await ctx.invoke(self.bot.get_command("clear messages"), number=number, user=user)
            except Exception:
                pass
        else:
            return await ctx.create_pages()

    @clear.command(name="invites", brief="manage messages", usage="clear invites")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clear_invites(self, ctx: EvelinaContext):
        """Clear messages that contain discord invite links"""
        regex = r"discord(?:\.com|app\.com|\.gg)/(?:invite/)?([a-zA-Z0-9\-]{2,32})"
        try:
            return await ctx.channel.purge(limit=300, check=lambda m: re.search(regex, m.content))
        except Exception:
            return

    @clear.command(brief="manage messages", usage="clear contains fuck")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def contains(self, ctx: EvelinaContext, *, word: str):
        """Clear messages that contain a certain word"""
        try:
            return await ctx.channel.purge(limit=300, check=lambda m: word in m.content)
        except Exception:
            return

    @clear.command(name="images", brief="manage messages", usage="clear images")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clear_images(self, ctx: EvelinaContext):
        """Clear messages that have attachments"""
        try:
            return await ctx.channel.purge(limit=300, check=lambda m: m.attachments)
        except Exception:
            return

    @clear.command(name="mentions", brief="manage message", usage="clear mentions comminate")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clear_mentions(self, ctx: EvelinaContext, user: User = None):
        """Clear message that have certain mentions"""
        if user is None:
            try:
                return await ctx.channel.purge(limit=300, check=lambda m: m.mentions)
            except Exception:
                return
        else:
            try:
                return await ctx.channel.purge(limit=300, check=lambda m: user in m.mentions)
            except Exception:
                return
        
    @clear.command(name="embeds", brief="manage messages", usage="clear embeds")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clear_embeds(self, ctx: EvelinaContext):
        """Clear messages that have embeds"""
        try:
            return await ctx.channel.purge(limit=300, check=lambda m: m.embeds)
        except Exception:
            return
    
    @clear.command(name="bots", brief="manage messages", usage="clear bots")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clear_bots(self, ctx: EvelinaContext):
        """Clear messages sent by bots"""
        try:
            return await ctx.channel.purge(limit=300, check=lambda m: m.author.bot)
        except Exception:
            return
    
    @clear.command(name="links", brief="manage messages", usage="clear links")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def clear_links(self, ctx: EvelinaContext):
        """Clear messages that contain links"""
        try:
            return await ctx.channel.purge(limit=300, check=lambda m: m.content and (m.content.startswith("http://") or m.content.startswith("https://")))
        except Exception:
            return

    @clear.command(name="messages", brief="Manage messages", usage="clear messages 20 @user")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    @cooldown(1, 10, BucketType.channel)
    async def clear_messages(self, ctx: EvelinaContext, number: int, *, user: User = None):
        """Delete multiple messages at once (up to 100)"""
        if number > 100:
            return await ctx.send_warning("You can only delete up to **100 messages** at once.")
        channel = ctx.channel
        if not channel:
            return await ctx.send_warning("Channel not found.")
        async with self.locks[channel.id]:
            try:
                await ctx.message.delete()
            except NotFound:
                pass
            messages = [msg async for msg in channel.history(limit=number) if not msg.pinned and (not user or msg.author.id == user.id)]
            recent, old = (
                [m for m in messages if (utils.utcnow() - m.created_at).days < 14],
                [m for m in messages if (utils.utcnow() - m.created_at).days >= 14],
            )
            total_deleted = 0
            if recent:
                try:
                    await channel.delete_messages(recent)
                    total_deleted += len(recent)
                except Forbidden:
                    await ctx.send_warning("I lack permission to bulk delete messages.")
                    return
                except Exception as e:
                    await ctx.send_warning(f"Failed to bulk delete messages: {e}")
            for msg in old:
                try:
                    await msg.delete()
                    total_deleted += 1
                    await asyncio.sleep(1)
                except NotFound:
                    continue
                except Exception as e:
                    pass
            if total_deleted > 0:
                messages = messages[::-1]
                guild = messages[0].guild
                message_channel = messages[0].channel
                if await self.log.is_ignored(guild.id, "channels", message_channel.id):
                    return
                record = await self.bot.db.fetchval("SELECT messages FROM logging WHERE guild_id = $1", guild.id)
                channel = await self.log.fetch_logging_channel(guild, record)
                if isinstance(channel, (TextChannel, Thread)):
                    if not channel.permissions_for(channel.guild.me).send_messages:
                        return
                    if isinstance(channel, Thread) and not channel.permissions_for(channel.guild.me).send_messages_in_threads:
                        return
                    async with self.locks[guild.id]:
                        button = Button(label="Message", style=ButtonStyle.link, url=f"https://discord.com/channels/{guild.id}/{message_channel.id}/{messages[0].id}")
                        view = View()
                        view.add_item(button)
                        text_file = BytesIO()
                        text_file.write(
                            bytes("\n".join([f"[{idx}] {message.author}: {message.clean_content}" for idx, message in enumerate(messages, start=1)]), encoding="utf-8"))
                        text_file.seek(0)
                        embed = (Embed(color=colors.NEUTRAL, title="Bulk Message Delete", description=f"`{len(messages)}` messages got deleted", timestamp=datetime.now()))
                        embed.add_field(name="Channel", value=f"<#{message_channel.id}> (`{message_channel.id}`)", inline=False)
                        embed.set_footer(text=f"ID: {messages[0].id}")
                        file = File(text_file, filename="messages.txt")
                        await self.log.add_to_queue(channel, embed, view, file)

    @command(brief="manage messages", aliases=["bc", "bp", "botpurge"])
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def botclear(self, ctx: EvelinaContext):
        """Delete messages sent by bots and messages starting with the command prefix"""
        async with self.locks[ctx.channel.id]:
            await ctx.channel.purge(
                limit=100,
                check=lambda m: (m.author.bot or m.content.startswith(ctx.clean_prefix)) and not m.pinned,
                reason=f"Bot and messages with prefix '{ctx.clean_prefix}' purged by {ctx.author}"
            )
            try:
                await ctx.message.delete()
            except NotFound:
                pass

    @command(name="lock", brief="manage roles", usage="lock #commands", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def lock(self, ctx: EvelinaContext, *, channel: Union[TextChannel, str] = CurrentChannel):
        """Lock a channel"""
        if isinstance(channel, Thread):
            return await ctx.send_warning("You can't lock a thread\n> Use `;thread lock` instead")
        check_roles = await self.bot.db.fetch("SELECT * FROM lockdown_role WHERE guild_id = $1", ctx.guild.id)
        if not check_roles:
            return await ctx.send_warning(f"No roles in the lockdown role list\n> Use `{ctx.clean_prefix}lockdown role add` to add a role")
        roles = [ctx.guild.get_role(role["role_id"]) for role in check_roles if ctx.guild.get_role(role["role_id"])]
        if not roles:
            return await ctx.send_warning("No valid roles found to lock the channel")
        if isinstance(channel, TextChannel):
            overwrites = {role: channel.overwrites_for(role) for role in roles}
            if all(ow.send_messages is False for ow in overwrites.values()):
                return await ctx.send_warning("Channel is **already** locked for all specified roles")
            for role, overwrite in overwrites.items():
                overwrite.send_messages = False
                await channel.set_permissions(role, overwrite=overwrite, reason=f"Channel locked by {ctx.author}")
            return await ctx.send_success(f"Locked {channel.mention} for all specified roles")
        if isinstance(channel, str) and channel.lower() == "all":
            check_channels = await self.bot.db.fetch("SELECT * FROM lockdown_channel WHERE guild_id = $1", ctx.guild.id)
            if not check_channels:
                return await ctx.send_warning(f"No channels in the lockdown channel list\n> Use `{ctx.clean_prefix}lockdown channel add` to add a channel")
            channels = [ctx.guild.get_channel(channel["channel_id"]) for channel in check_channels if ctx.guild.get_channel(channel["channel_id"])]
            if not channels:
                return await ctx.send_warning("No valid channels found to lock")
            for channel in channels:
                for role in roles:
                    overwrite = channel.overwrites_for(role)
                    overwrite.send_messages = False
                    await channel.set_permissions(role, overwrite=overwrite, reason=f"Channel locked by {ctx.author}")
            return await ctx.send_success(f"Locked all specified channels for all specified roles")
        else:
            return await ctx.send_help(ctx.command)
        
    @command(name="unlock", brief="manage roles", usage="unlock #commands", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def unlock(self, ctx: EvelinaContext, *, channel: Union[TextChannel, str] = CurrentChannel):
        """Unlock a channel"""
        if isinstance(channel, Thread):
            return await ctx.send_warning("You can't unlock a thread\n> Use `;thread unlock` instead")
        check_roles = await self.bot.db.fetch("SELECT * FROM lockdown_role WHERE guild_id = $1", ctx.guild.id)
        if not check_roles:
            return await ctx.send_warning(f"No roles in the lockdown role list\n> Use `{ctx.clean_prefix}lockdown role add` to add a role")
        roles = [ctx.guild.get_role(role["role_id"]) for role in check_roles if ctx.guild.get_role(role["role_id"])]
        if not roles:
            return await ctx.send_warning("No valid roles found to unlock the channel")
        if isinstance(channel, TextChannel):
            overwrites = {role: channel.overwrites_for(role) for role in roles}
            if all(ow.send_messages is True for ow in overwrites.values()):
                return await ctx.send_warning("Channel is **already** unlocked for all specified roles")
            for role, overwrite in overwrites.items():
                overwrite.send_messages = True
                await channel.set_permissions(role, overwrite=overwrite, reason=f"Channel unlocked by {ctx.author}")
            return await ctx.send_success(f"Unlocked {channel.mention} for all specified roles")
        if isinstance(channel, str) and channel.lower() == "all":
            check_channels = await self.bot.db.fetch("SELECT * FROM lockdown_channel WHERE guild_id = $1", ctx.guild.id)
            if not check_channels:
                return await ctx.send_warning(f"No channels in the lockdown channel list\n> Use `{ctx.clean_prefix}lockdown channel add` to add a channel")
            channels = [ctx.guild.get_channel(channel["channel_id"]) for channel in check_channels if ctx.guild.get_channel(channel["channel_id"])]
            if not channels:
                return await ctx.send_warning("No valid channels found to unlock")
            for channel in channels:
                for role in roles:
                    overwrite = channel.overwrites_for(role)
                    overwrite.send_messages = True
                    await channel.set_permissions(role, overwrite=overwrite, reason=f"Channel unlocked by {ctx.author}")
            return await ctx.send_success(f"Unlocked all specified channels for all specified roles")
        else:
            return await ctx.send_help(ctx.command)
        
    @group(name="lockdown", case_insensitive=True, invoke_without_command=True)
    async def lockdown(self, ctx: EvelinaContext):
        """Manage lockdown settings"""
        return await ctx.create_pages()
    
    @lockdown.group(name="role", case_insensitive=True, invoke_without_command=True)
    async def lockdown_role(self, ctx: EvelinaContext):
        """Manage lockdown role settings"""
        return await ctx.create_pages()
    
    @lockdown_role.command(name="add", brief="manage guild", usage="lockdown role add @member")
    @has_guild_permissions(manage_guild=True)
    async def lockdown_role_add(self, ctx: EvelinaContext, role: Role):
        """Add a role to the lockdown role list"""
        check = await self.bot.db.fetchrow("SELECT * FROM lockdown_role WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role.id)
        if check:
            return await ctx.send_warning(f"Role {role.mention} is already in the lockdown role list")
        await self.bot.db.execute("INSERT INTO lockdown_role (guild_id, role_id) VALUES ($1, $2)", ctx.guild.id, role.id)
        return await ctx.send_success(f"Role {role.mention} has been added to the lockdown role list")
    
    @lockdown_role.command(name="remove", brief="manage guild", usage="lockdown role remove @member")
    @has_guild_permissions(manage_guild=True)
    async def lockdown_role_remove(self, ctx: EvelinaContext, role: Union[Role, int]):
        """Remove a role from the lockdown role list"""
        role_id = self.bot.misc.convert_role(role)
        check = await self.bot.db.fetchrow("SELECT * FROM lockdown_role WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        if not check:
            return await ctx.send_warning(f"Role {self.bot.misc.humanize_role(ctx.guild, role_id)} is not in the lockdown role list")
        await self.bot.db.execute("DELETE FROM lockdown_role WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, role_id)
        return await ctx.send_success(f"Role {self.bot.misc.humanize_role(ctx.guild, role_id)} has been removed from the lockdown role list")
    
    @lockdown_role.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def lockdown_role_list(self, ctx: EvelinaContext):
        """List all roles in the lockdown role list"""
        check = await self.bot.db.fetch("SELECT role_id FROM lockdown_role WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("No roles in the lockdown role list")
        roles = []
        for role in check:
            roles.append(self.bot.misc.humanize_role(ctx.guild, role["role_id"], True))
        if not roles:
            return await ctx.send_warning("No roles in the lockdown role list")
        return await ctx.paginate(roles, "Lockdown Roles", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @lockdown.group(name="channel", case_insensitive=True, invoke_without_command=True)
    async def lockdown_channel(self, ctx: EvelinaContext):
        """Manage lockdown channel settings"""
        return await ctx.create_pages()
    
    @lockdown_channel.command(name="add", brief="manage guild", usage="lockdown channel add #commands")
    @has_guild_permissions(manage_guild=True)
    async def lockdown_channel_add(self, ctx: EvelinaContext, channel: TextChannel):
        """Add a channel to the lockdown channel list"""
        check = await self.bot.db.fetchrow("SELECT * FROM lockdown_channel WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if check:
            return await ctx.send_warning(f"Channel {channel.mention} is already in the lockdown channel list")
        await self.bot.db.execute("INSERT INTO lockdown_channel (guild_id, channel_id) VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Channel {channel.mention} has been added to the lockdown channel list")
    
    @lockdown_channel.command(name="remove", brief="manage guild", usage="lockdown channel remove #commands")
    @has_guild_permissions(manage_guild=True)
    async def lockdown_channel_remove(self, ctx: EvelinaContext, channel: Union[TextChannel, int]):
        """Remove a channel from the lockdown channel list"""
        channel_id = self.bot.misc.convert_channel(channel)
        check = await self.bot.db.fetchrow("SELECT * FROM lockdown_channel WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        if not check:
            return await ctx.send_warning(f"Channel {self.bot.misc.humanize_channel(channel_id)} is not in the lockdown channel list")
        await self.bot.db.execute("DELETE FROM lockdown_channel WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel_id)
        return await ctx.send_success(f"Channel {self.bot.misc.humanize_channel(channel_id)} has been removed from the lockdown channel list")
    
    @lockdown_channel.command(name="list", brief="manage guild")
    @has_guild_permissions(manage_guild=True)
    async def lockdown_channel_list(self, ctx: EvelinaContext):
        """List all channels in the lockdown channel list"""
        check = await self.bot.db.fetch("SELECT channel_id FROM lockdown_channel WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("No channels in the lockdown channel list")
        channels = []
        for channel in check:
            channels.append(self.bot.misc.humanize_channel(channel["channel_id"], True))
        if not channels:
            return await ctx.send_warning("No channels in the lockdown channel list")
        return await ctx.paginate(channels, "Lockdown Channels", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(name="hide", brief="manage roles", usage="hide #commands")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def hide(self, ctx: EvelinaContext, *, channel: TextChannel = CurrentChannel):
        """Hide a channel from everyone"""
        try:
            if isinstance(channel, TextChannel):
                if channel.overwrites_for(ctx.guild.default_role).view_channel is False:
                    return await ctx.send_warning("Channel is **already** hidden")
                overwrites = channel.overwrites_for(ctx.guild.default_role)
                overwrites.view_channel = False
                await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=f"Channel hidden by {ctx.author}")
                return await ctx.message.add_reaction("✅")
            else:
                return await ctx.send_warning("You can't hide threads")
        except HTTPException as e:
            if e.status == 400:
                await ctx.send_warning("You can't hide a **Onboarding** channel")

    @command(name="unhide", brief="manage roles", usage="unhide #commands")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def unhide(self, ctx: EvelinaContext, *, channel: TextChannel = CurrentChannel):
        """Unhide a channel from everyone"""
        if channel.overwrites_for(ctx.guild.default_role).view_channel is None:
            return await ctx.send_warning("Channel is **not** hidden")
        overwrites = channel.overwrites_for(ctx.guild.default_role)
        overwrites.view_channel = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrites, reason=f"Channel unhidden by {ctx.author}")
        try:
            await ctx.message.add_reaction("✅")
        except NotFound:
            pass

    @command(aliases=["cooldown"], brief="manage channels", usage="slowmode 10s #general")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def slowmode(self, ctx: EvelinaContext, time: ValidTime, *, channel: TextChannel = CurrentChannel):
        """Enable slowmode option in a text channel"""
        max_duration = 6 * 60 * 60
        formated_time = format_timespan(time)
        if time > max_duration:
            return await ctx.send_warning("You can't set a slowmode for more than **6 hours**")
        await channel.edit(slowmode_delay=time, reason=f"Slowmode invoked by {ctx.author}")
        await ctx.send_success(f"Slowmode for {channel.mention} set to **{formated_time}**")

    @command(brief="moderate members", aliases=["timeout"], usage="mute comminate 1d rassist --s", extras={"s": "Punish a user silently"})
    @has_guild_permissions(moderate_members=True)
    @bot_has_guild_permissions(moderate_members=True)
    async def mute(self, ctx: EvelinaContext, member: NoStaff, time: Optional[ValidTime] = None, *, reason: str = "No reason provided"):
        """Timeout a member"""
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        discord_reason = f"{reason} | {ctx.author.name} ({ctx.author.id})"
        msg = None
        time = time or 3600
        max_duration = 28 * 24 * 60 * 60
        if time > max_duration:
            return await ctx.send_warning("You can't mute a user for more than **28 days**")
        if member.is_timed_out():
            return await ctx.send_warning(f"{member.mention} is **already** muted")
        if member.guild_permissions.administrator:
            return await ctx.send_warning("You **can't** mute an administrator")
        formated_time = format_timespan(time)
        try:
            if send_dm:
                if not await DmInvoking(ctx).send(member, reason, case_id, formated_time):
                    embed = Embed(description=f"You have been muted for **{formated_time}** on **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.ERROR)
                    msg = await member.send(embed=embed, view=AppealsView(self))
        except Exception:
            pass
        await member.timeout(utils.utcnow() + timedelta(seconds=time), reason=discord_reason)
        current_timestamp = utils.utcnow().timestamp()
        duration = format_timespan(time) if time != 0 else 'Infinity'
        history_id = await self.insert_history(ctx, member, "Mute", duration, reason, current_timestamp, msg.id if msg else None)
        expiration_timestamp = (datetime.utcnow() + timedelta(seconds=time)).timestamp()
        await self.logging(ctx.guild, member, ctx.author, reason, f"muted until <t:{int(expiration_timestamp)}:f>", "Mute", history_id)
        if not await Invoking(ctx).send(member, reason, formated_time, history_id):
            await ctx.send_success(f"Muted {member.mention} (`#{history_id}`) for {formated_time} - **{reason}**")

    @command(brief="moderate members", aliases=["untimeout"], usage="unmute comminate rassist --s", extras={"s": "Punish a user silently"})
    @has_guild_permissions(moderate_members=True)
    @bot_has_guild_permissions(moderate_members=True)
    async def unmute(self, ctx: EvelinaContext, member: NoStaff, *, reason: str = "No reason provided"):
        """Remove the timeout from a member"""
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        discord_reason = f"{reason} | {ctx.author.name} ({ctx.author.id})"
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        formated_time = None
        if not member.is_timed_out():
            return await ctx.send_warning(f"{member.mention} is **not** muted")
        await member.timeout(None, reason=discord_reason)
        try:
            if send_dm:
                if not await DmInvoking(ctx).send(member, reason, case_id, formated_time):
                    embed = Embed(description=f"You have been unmuted on **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.SUCCESS)
                    await member.send(embed=embed)
        except Exception:
            pass
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, member, "Unmute", 'None', reason, current_timestamp)
        await self.logging(ctx.guild, member, ctx.author, reason, "unmuted", "Unmute", history_id)
        if not await Invoking(ctx).send(member, reason, formated_time, history_id):
            await ctx.send_success(f"Unmuted {member.mention} (`#{history_id}`) - {reason}")

    @command(brief="administrator")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def setmute(self, ctx: EvelinaContext):
        """Set up mute module"""
        async with self.locks[ctx.guild.id]:
            if await self.bot.db.fetchrow("SELECT * FROM mute_images WHERE guild_id = $1", ctx.guild.id) and await self.bot.db.fetchrow("SELECT * FROM mute_reactions WHERE guild_id = $1", ctx.guild.id):
                return await ctx.send_warning("Mute module is **already** configured")
            mes = await ctx.send(embed=Embed(color=colors.LOADING, description=f"{emojis.LOADING} {ctx.author.mention}: Configuring **mute system** and creating needed **roles**"))
            async with ctx.typing():
                image_role = await ctx.guild.create_role(name="imuted", reason="creating image mute role")
                reaction_role = await ctx.guild.create_role(name="rmuted", reason="creating reaction mute role")
                await self.bot.db.execute("INSERT INTO mute_images VALUES ($1, $2)", ctx.guild.id, image_role.id)
                await self.bot.db.execute("INSERT INTO mute_reactions VALUES ($1, $2)", ctx.guild.id, reaction_role.id)
                for channel in ctx.guild.text_channels:
                    overwrites = channel.overwrites_for(image_role)
                    overwrites.attach_files = False
                    overwrites.embed_links = False
                    try:
                        await channel.set_permissions(image_role, overwrite=overwrites, reason="Image muted role setup")
                    except NotFound:
                        continue
                    await asyncio.sleep(0.5)
                    overwrites = channel.overwrites_for(reaction_role)
                    overwrites.add_reactions = False
                    try:
                        await channel.set_permissions(reaction_role, overwrite=overwrites, reason="Reaction muted role setup")
                    except NotFound:
                        continue
                    await asyncio.sleep(0.5)
            await mes.edit(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: Mute system has been **configured**"))

    @command(brief="administrator")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def unsetmute(self, ctx: EvelinaContext):
        """Unset the mute module"""
        async with self.locks[ctx.guild.id]:
            image_role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_images WHERE guild_id = $1", ctx.guild.id)
            reaction_role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_reactions WHERE guild_id = $1", ctx.guild.id)
            if not image_role_id and not reaction_role_id:
                return await ctx.send_warning("Mute module is **not** configured\n> Use `;setmute` to set it up")
            image_role = ctx.guild.get_role(image_role_id)
            reaction_role = ctx.guild.get_role(reaction_role_id)
            if image_role:
                await image_role.delete(reason="Unsetting mute module")
            if reaction_role:
                await reaction_role.delete(reason="Unsetting mute module")
            await self.bot.db.execute("DELETE FROM mute_images WHERE guild_id = $1", ctx.guild.id)
            await self.bot.db.execute("DELETE FROM mute_reactions WHERE guild_id = $1", ctx.guild.id)
            await ctx.send_success("Mute system has been **unset**")

    @command(brief="moderate members", usage="imute comminate #chat")
    @has_guild_permissions(moderate_members=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def imute(self, ctx: EvelinaContext, member: NoStaff, channel: Union[TextChannel, str] = CurrentChannel):
        """Mute a member from sending images"""
        if isinstance(channel, TextChannel):
            if channel.overwrites_for(member).send_messages is False:
                return await ctx.send_warning(f"{member.mention} is **already** image muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.attach_files = False
            overwrites.embed_links = False
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Image muted by {ctx.author}")
            return await ctx.send_success(f"Image muted {member.mention} in {channel.mention}")
        if isinstance(channel, str) and channel.lower() == "all":
            role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_images WHERE guild_id = $1", ctx.guild.id)
            if not role_id:
                return await ctx.send_warning(f"Mute module not setuped, please use `{ctx.clean_prefix}setmute` to set the mute roles")
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send_warning("Mute role not found, please use `;unsetmute` and set it back")
            if role.position >= ctx.guild.me.top_role.position:
                return await ctx.send_warning("Mute role is over my highest role")
            if role in member.roles:
                return await ctx.send_warning(f"{member.mention} is **already** image muted")
            await member.add_roles(role, reason=f"Image muted by {ctx.author}")
            return await ctx.send_success(f"Image muted {member.mention} in **all** channels")
        if not isinstance(channel, TextChannel):
            channel = ctx.channel
            if channel.overwrites_for(member).send_messages is False:
                return await ctx.send_warning(f"{member.mention} is **already** image muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.attach_files = False
            overwrites.embed_links = False
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Image muted by {ctx.author}")
            return await ctx.send_success(f"Image muted {member.mention} in {channel.mention}")
        return await ctx.create_pages()
        
    @command(brief="moderate members", usage="iunmute comminate #chat")
    @has_guild_permissions(moderate_members=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def iunmute(self, ctx: EvelinaContext, member: NoStaff, channel: Union[TextChannel, str] = CurrentChannel):
        """Unmute a member from sending images"""
        if isinstance(channel, TextChannel):
            if channel.overwrites_for(member).send_messages is True:
                return await ctx.send_warning(f"{member.mention} is **not** image muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.attach_files = None
            overwrites.embed_links = None
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Image unmuted by {ctx.author}")
            return await ctx.send_success(f"Image unmuted {member.mention} in {channel.mention}")
        if isinstance(channel, str) and channel.lower() == "all":
            role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_images WHERE guild_id = $1", ctx.guild.id)
            if not role_id:
                return await ctx.send_warning(f"Mute module not setuped, please use `{ctx.clean_prefix}setmute` to set the mute roles")
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send_warning("Mute role not found, please use `;unsetmute` and set it back")
            if role not in member.roles:
                return await ctx.send_warning(f"{member.mention} is **not** image muted")
            await member.remove_roles(role, reason=f"Image unmuted by {ctx.author}")
            return await ctx.send_success(f"Image unmuted {member.mention} in **all** channels")
        if not isinstance(channel, TextChannel):
            channel = ctx.channel
            if channel.overwrites_for(member).send_messages is True:
                return await ctx.send_warning(f"{member.mention} is **not** image muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.attach_files = None
            overwrites.embed_links = None
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Image unmuted by {ctx.author}")
            return await ctx.send_success(f"Image unmuted {member.mention} in {channel.mention}")
        else:
            return await ctx.create_pages()
        
    @command(brief="moderate members", usage="rmute comminate #chat")
    @has_guild_permissions(moderate_members=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def rmute(self, ctx: EvelinaContext, member: NoStaff, channel: Union[TextChannel, str] = CurrentChannel):
        """Mute a member from reacting to messages"""
        if isinstance(channel, TextChannel):
            if channel.overwrites_for(member).add_reactions is False:
                return await ctx.send_warning(f"{member.mention} is **already** reaction muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.add_reactions = False
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Reaction muted by {ctx.author}")
            return await ctx.send_success(f"Reaction muted {member.mention} in {channel.mention}")
        if isinstance(channel, str) and channel.lower() == "all":
            role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_reactions WHERE guild_id = $1", ctx.guild.id)
            if not role_id:
                return await ctx.send_warning(f"Mute module not setuped, please use `{ctx.clean_prefix}setmute` to set the mute roles")
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send_warning("Mute role not found, please use `;unsetmute` and set it back")
            if role in member.roles:
                return await ctx.send_warning(f"{member.mention} is **already** reaction muted")
            await member.add_roles(role, reason=f"Reaction muted by {ctx.author}")
            return await ctx.send_success(f"Reaction muted {member.mention} in **all** channels")
        if not isinstance(channel, TextChannel):
            channel = ctx.channel
            if channel.overwrites_for(member).add_reactions is False:
                return await ctx.send_warning(f"{member.mention} is **already** reaction muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.add_reactions = False
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Reaction muted by {ctx.author}")
            return await ctx.send_success(f"Reaction muted {member.mention} in {channel.mention}")
        else:
            return await ctx.create_pages()
        
    @command(brief="moderate members", usage="runmute comminate #chat")
    @has_guild_permissions(moderate_members=True)
    @bot_has_guild_permissions(manage_channels=True, manage_roles=True)
    async def runmute(self, ctx: EvelinaContext, member: NoStaff, channel: Union[TextChannel, str] = CurrentChannel):
        """Unmute a member from reacting to messages"""
        if isinstance(channel, TextChannel):
            if channel.overwrites_for(member).add_reactions is True:
                return await ctx.send_warning(f"{member.mention} is **not** reaction muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.add_reactions = None
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Reaction unmuted by {ctx.author}")
            return await ctx.send_success(f"Reaction unmuted {member.mention} in {channel.mention}")
        if isinstance(channel, str) and channel.lower() == "all":
            role_id = await self.bot.db.fetchval("SELECT role_id FROM mute_reactions WHERE guild_id = $1", ctx.guild.id)
            if not role_id:
                return await ctx.send_warning(f"Mute module not setuped, please use `{ctx.clean_prefix}setmute` to set the mute roles")
            role = ctx.guild.get_role(role_id)
            if not role:
                return await ctx.send_warning("Mute role not found, please use `;unsetmute` and set it back")
            if role not in member.roles:
                return await ctx.send_warning(f"{member.mention} is **not** reaction muted")
            await member.remove_roles(role, reason=f"Reaction unmuted by {ctx.author}")
            return await ctx.send_success(f"Reaction unmuted {member.mention} in **all** channels")
        if not isinstance(channel, TextChannel):
            channel = ctx.channel
            if channel.overwrites_for(member).add_reactions is True:
                return await ctx.send_warning(f"{member.mention} is **not** reaction muted in {channel.mention}")
            overwrites = channel.overwrites_for(member)
            overwrites.add_reactions = None
            await channel.set_permissions(member, overwrite=overwrites, reason=f"Reaction unmuted by {ctx.author}")
            return await ctx.send_success(f"Reaction unmuted {member.mention} in {channel.mention}")
        else:
            return await ctx.create_pages()

    @command(brief="ban members", usage="ban comminate racist --days 7", extras={"s": "Punish a user silently", "days": "Delete messages from the user"})
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def ban(self, ctx: EvelinaContext, member: Union[Member, User], *, reason: str = "No reason provided"):
        """Ban a member from the server"""
        delete_message_seconds = 0
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        if " --days" in reason:
            try:
                reason, days_arg = reason.split(" --days")
                delete_message_days = max(0, min(7, int(days_arg.strip().split()[0])))
                delete_message_seconds = delete_message_days * 86400
            except (ValueError, IndexError):
                return await ctx.send_warning(f"Invalid `--days` value. Please provide a number between 0 and 7.\n> Example: `{ctx.clean_prefix}ban comminate rassist --days 1`")
        reason = reason.strip()[:128]
        discord_reason = f"{reason} | {ctx.author.name} ({ctx.author.id})"
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        formated_time = None
        msg = None
        try:
            await ctx.guild.fetch_ban(member)
            return await ctx.send_warning(f"{member.mention} is already banned.")
        except NotFound:
            pass
        if isinstance(member, Member):
            member = await NoStaff().convert(ctx, str(member.id))
            if member.premium_since:
                view = BoosterMod(ctx, member, reason)
                embed = Embed(color=colors.NEUTRAL, description=f"{ctx.author.mention}: Are you sure you want to **ban** {member.mention}?\n> They're boosting this server since **{self.bot.misc.humanize_date(datetime.fromtimestamp(member.premium_since.timestamp()))}**")
                return await ctx.reply(embed=embed, view=view)
        try:
            if send_dm:
                if isinstance(member, Member):
                    if not await DmInvoking(ctx).send(member, reason, case_id, formated_time):
                        embed = Embed(description=f"You have been banned from **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.ERROR)
                        msg = await member.send(embed=embed, view=AppealsView(self))
        except Exception:
            pass
        await ctx.guild.ban(member, reason=discord_reason, delete_message_seconds=delete_message_seconds)
        await self.punish_a_bitch("ban", ctx.author, "Banning Members")
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, member, "Ban", 'None', reason, current_timestamp, msg.id if msg else None)
        await self.logging(ctx.guild, member, ctx.author, reason, "banned", "Ban", history_id)
        if not await Invoking(ctx).send(member, reason, formated_time, history_id):
            await ctx.send_success(f"Banned {member.mention} (`#{history_id}`) - **{reason}**")
        
    @command(brief="kick members", usage="kick comminate rassist --s", extras={"s": "Punish a user silently"})
    @has_guild_permissions(kick_members=True)
    @bot_has_guild_permissions(kick_members=True)
    async def kick(self, ctx: EvelinaContext, member: NoStaff, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        discord_reason = f"{reason} | {ctx.author.name} ({ctx.author.id})"
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        formated_time = None
        msg = None
        if ctx.guild.premium_subscriber_role in member.roles:
            view = BoosterMod(ctx, member, reason)
            embed = Embed(color=colors.NEUTRAL, description=f"{ctx.author.mention}: Are you sure you want to **kick** {member.mention}? They're boosting this server since **{self.bot.misc.humanize_date(datetime.fromtimestamp(member.premium_since.timestamp()))}**")
            return await ctx.reply(embed=embed, view=view)
        try:
            if send_dm:
                if not await DmInvoking(ctx).send(member, reason, case_id, formated_time):
                    embed = Embed(description=f"You have been kicked from **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.ERROR)
                    msg = await member.send(embed=embed)
        except Exception:
            pass
        await member.kick(reason=discord_reason)
        await self.punish_a_bitch("kick", ctx.author, "Kicking Members")
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, member, "Kick", 'None', reason, current_timestamp, msg.id if msg else None)
        await self.logging(ctx.guild, member, ctx.author, reason, "kicked", "Kick", history_id)
        if not await Invoking(ctx).send(member, reason, formated_time, history_id):
            await ctx.send_success(f"Kicked {member.mention} (`#{history_id}`) - **{reason}**")
        
    @command(brief="ban members")
    @admin_antinuke()
    @bot_has_guild_permissions(ban_members=True)
    async def unbanall(self, ctx: EvelinaContext):
        """Unban all members from the server"""
        if len([m.user async for m in ctx.guild.bans()]) == 0:
            return await ctx.send_warning(f"There are no members that are banned")
        async def yes_callback(interaction: Interaction):
            async with self.locks[interaction.guild.id]:
                bans = [m.user async for m in interaction.guild.bans()]
                await interaction.response.edit_message(embed=Embed(description=f"{emojis.LOADING} {interaction.user.mention}: Unbanning in progress... **0/{len(bans)}** members unbanned", color=colors.LOADING), view=None)
                message = await interaction.original_response()
                for i, user in enumerate(bans, 1):
                    await interaction.guild.unban(Object(user.id))
                    await asyncio.sleep(1)
                    if i % 10 == 0:
                        embed = Embed(description=f"{emojis.LOADING} {interaction.user.mention}: Unbanning in progress... **{i}/{len(bans)}** members unbanned", 
                                    color=colors.LOADING)
                        await message.edit(embed=embed)
                embed = Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Successfully unbanned **{len(bans)}** members", 
                            color=colors.SUCCESS)
                await message.edit(embed=embed)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {ctx.author.mention}: Unban everyone got canceled", color=colors.ERROR), view=None)
        return await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure that you want to unban **{len([m.user async for m in ctx.guild.bans()])}** members?", yes_callback, no_callback)

    @command(brief="ban members", usage="unban comminate --s", extras={"s": "Punish a user silently"})
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def unban(self, ctx: EvelinaContext, user: User, *, reason: str = "No reason provided"):
        """Unban a member from the server"""
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        discord_reason = f"{reason} | {ctx.author.name} ({ctx.author.id})"
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        formated_time = None
        try:
            await ctx.guild.unban(user=user, reason=discord_reason)
        except NotFound:
            return await ctx.send_warning("Can't find this user in the ban list")
        try:
            if send_dm:
                if not await DmInvoking(ctx).send(user, reason, case_id, formated_time):
                    embed = Embed(description=f"You have been unbanned from **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.SUCCESS)
                    await user.send(embed=embed)
        except Exception:
            pass
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, user, "Unban", 'None', reason, current_timestamp)
        await self.logging(ctx.guild, user, ctx.author, reason, "unbanned", "Unban", history_id)
        await ctx.send_success(f"Unbanned **{user}** (`#{history_id}`) - {reason}")
        
    @command(brief="manage roles", usage="strip comminate")
    @has_guild_permissions(manage_roles=True)
    @bot_has_guild_permissions(manage_roles=True)
    async def strip(self, ctx: EvelinaContext, *, member: NoStaff):
        """Remove someone's dangerous roles, ignoring bot-managed roles"""
        bot_highest_role = member.guild.me.top_role
        roles_to_remove = []
        staff_roles = await self.bot.db.fetchval("SELECT staffs FROM antinuke WHERE guild_id = $1", member.guild.id,)
        if staff_roles:
            staff_roles_list = json.loads(staff_roles)
            if isinstance(staff_roles_list, list) and staff_roles_list:
                roles_to_remove = [role for role in member.roles if role.id in staff_roles_list and not role.managed and role.position < bot_highest_role.position]
        if not roles_to_remove:
            roles_to_remove = [role for role in member.roles if role.is_assignable() and self.bot.misc.is_dangerous(role) and not role.managed and role.position < bot_highest_role.position]
        if not roles_to_remove:
            return await ctx.send_warning(f"No dangerous roles found to strip from {member.mention}.")
        await self.bot.db.execute("""INSERT INTO restore_antinuke (guild_id, user_id, roles) VALUES ($1, $2, $3) ON CONFLICT (guild_id, user_id) DO UPDATE SET roles = EXCLUDED.roles""", member.guild.id, member.id, json.dumps([r.id for r in roles_to_remove]),)
        removed_roles = []
        failed_roles = []
        for role in roles_to_remove:
            try:
                await member.remove_roles(role, reason=f"Stripped by {ctx.author}")
                removed_roles.append(role.mention)
            except Exception:
                failed_roles.append(role.mention)
        if removed_roles:
            success_message = f"Successfully stripped the following roles from {member.mention}: {', '.join(removed_roles)}."
        else:
            success_message = f"No roles were successfully stripped from {member.mention}."
        if failed_roles:
            success_message += f"\nFailed to remove the following roles: {', '.join(failed_roles)}."
        return await ctx.send_success(success_message)
    
    @command(aliases=["nick"], brief="manage nicknames", usage="nickname comminate bender")
    @has_guild_permissions(manage_nicknames=True)
    @bot_has_guild_permissions(manage_nicknames=True)
    async def nickname(self, ctx: EvelinaContext, member: NoStaff, *, nick: ValidNickname):
        """Change a member's nickname"""
        if nick == None:
            await member.edit(nick=None, reason=f"Nickname removed by {ctx.author}")
            return await ctx.send_success(f"Removed {member.mention}'s nickname")
        if len(nick) > 32:
            return await ctx.send_warning("Nickname can't be longer than 32 characters")
        try:
            await member.edit(nick=nick, reason=f"Nickname changed by {ctx.author}")
            return await ctx.send_success(f"Changed {member.mention} nickname to **{nick}**" if nick else f"Removed {member.mention}'s nickname")
        except Forbidden:
            return await ctx.send_warning("I don't have permission to change this member's nickname. Please check the role hierarchy.")
        except HTTPException:
            return await ctx.send_warning("Display name contains community flagged words")

    
    @group(invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_messages=True)
    @cooldown(1, 5, BucketType.user)
    async def warn(self, ctx: EvelinaContext, member: NoStaff = None, *, reason: str = "No reason provided"):
        reason = reason[:128]
        send_dm = "--s" not in reason
        reason = reason.replace("--s", "").strip()
        case_id = "".join(random.choices(string.ascii_letters + string.digits, k=8))
        formated_time = None
        msg = None
        if member is None:
            return await ctx.create_pages()
        try:
            if send_dm:
                if not await DmInvoking(ctx).send(member, reason, case_id, formated_time):
                    embed = Embed(description=f"You have been warned on **{ctx.guild.name}** by {ctx.author.mention} for the following reason: **{reason}**", color=colors.ERROR)
                    msg = await member.send(embed=embed, view=AppealsView(self))
        except Exception:
            pass
        await self.bot.db.execute("""INSERT INTO warns VALUES ($1,$2,$3,$4,$5)""", ctx.guild.id, member.id, ctx.author.id, f"{datetime.now().day}/{f'0{datetime.now().month}' if datetime.now().month < 10 else datetime.now().month}/{str(datetime.now().year)[-2:]} at {datetime.strptime(f'{datetime.now().hour}:{datetime.now().minute}', '%H:%M').strftime('%I:%M %p')}", reason)
        warns = await self.bot.db.fetch("SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2 ORDER BY time", ctx.guild.id, member.id)
        for i in range(1, len(warns) + 1):
            role_id = await self.bot.db.fetchval("SELECT role_id FROM warns_rewards WHERE guild_id = $1 AND warn = $2", ctx.guild.id, i)
            if role_id:
                role = ctx.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role, reason=f"Warned {len(warns)} times")
                    except Forbidden:
                        pass
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, member, "Warn", 'None', reason, current_timestamp)
        await self.logging(ctx.guild, member, ctx.author, reason, f"warned {len(warns)} times", "Warn", history_id)
        if not await Invoking(ctx).send(member, reason, formated_time, history_id):
            await ctx.send_success(f"Warned {member.mention} (`#{history_id}`) - {reason}")
        return await self.decide_punishment(ctx, member, len(warns), reason)

    @warn.command(name="remove", brief="manage messages", usage="warn remove comminate 1")
    @has_guild_permissions(manage_messages=True)
    async def warn_remove(self, ctx: EvelinaContext, member: Member, warn: int, *, reason: str = "No reason provided"):
        """Remove a specific warn by its number"""
        warns = await self.bot.db.fetch("SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2 ORDER BY time", ctx.guild.id, member.id)
        if len(warns) == 0:
            return await ctx.send_warning(f"{member.mention} has no warnings.")
        if warn <= 0 or warn > len(warns):
            return await ctx.send_warning(f"Warn ID `{warn}` is **invalid**")
        warn_to_remove = warns[warn - 1]
        await self.bot.db.execute("DELETE FROM warns WHERE guild_id = $1 AND user_id = $2 AND time = $3", ctx.guild.id, member.id, warn_to_remove['time'])
        warns = await self.bot.db.fetch("SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2 ORDER BY time", ctx.guild.id, member.id)
        if warns:
            role_id = await self.bot.db.fetchval("SELECT role_id FROM warns_rewards WHERE guild_id = $1 AND warn = $2", ctx.guild.id, len(warns))
            if role_id:
                role = ctx.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role, reason=f"Warned {len(warns)} times")
                    except Forbidden:
                        pass
        else:
            for i in range(1, len(warns) + 2):
                role_id = await self.bot.db.fetchval("SELECT role_id FROM warns_rewards WHERE guild_id = $1 AND warn = $2", ctx.guild.id, i)
                if role_id:
                    role = ctx.guild.get_role(role_id)
                    if role in member.roles:
                        try:
                            await member.remove_roles(role, reason=f"Removed roles due to warning removal.")
                        except Forbidden:
                            pass
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, member, "Warn Remove", 'None', reason, current_timestamp)
        await ctx.send_success(f"Removed warning **#{warn}** from {member.mention}")

    @warn.command(name="clear", brief="manage messages", usage="warn clear comminate")
    @has_guild_permissions(manage_messages=True)
    async def warn_clear(self, ctx: EvelinaContext, member: NoStaff, *, reason: str = "No reason provided"):
        """Clear all warns from an user"""
        check = await self.bot.db.fetch("""SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2""", ctx.guild.id, member.id)
        if len(check) == 0:
            return await ctx.send_warning(f"{member.mention} has no warnings")
        await self.bot.db.execute("DELETE FROM warns WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, member.id)
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, member, "Warn Clear", 'None', reason, current_timestamp)
        await ctx.send_success(f"Removed {member.mention}'s warns")

    @warn.command(name="reset", brief="administrator")
    @has_guild_permissions(administrator=True)
    async def warn_reset(self, ctx: EvelinaContext):
        """Reset all warns from your server"""
        check = await self.bot.db.fetch("""SELECT * FROM warns WHERE guild_id = $1""", ctx.guild.id)
        if len(check) == 0:
            return await ctx.send_warning(f"Your server has no warnings")
        await self.bot.db.execute("DELETE FROM warns WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success(f"Removed all server warns")

    @warn.command(name="list", usage="warn list comminate")
    @has_guild_permissions(manage_messages=True)
    async def warn_list(self, ctx: EvelinaContext, *, member: Member):
        """Returns all warns that a user has"""
        check = await self.bot.db.fetch("""SELECT * FROM warns WHERE guild_id = $1 AND user_id = $2""", ctx.guild.id, member.id)
        if len(check) == 0:
            return await ctx.send_warning(f"{member.mention} has no warnings")
        formatted_warnings = []
        for result in check:
            time_str = result['time']
            try:
                timestamp = float(time_str)
                formatted_time = datetime.fromtimestamp(timestamp).strftime('<t:%s:F>' % int(timestamp))
            except ValueError:
                try:
                    formatted_time = datetime.strptime(time_str, '%d/%m/%y at %I:%M %p').strftime('<t:%s:R>' % int(datetime.strptime(time_str, '%d/%m/%y at %I:%M %p').timestamp()))
                except ValueError:
                    formatted_time = 'Unknown Time Format'
            formatted_warnings.append(f"<@!{result['author_id']}> {result['reason']} - {formatted_time}")
        return await ctx.paginate(formatted_warnings, f"Warnings", {"name": member.name, "icon_url": member.avatar.url if member.avatar else member.default_avatar.url})
    
    @warn.command(name="all")
    @has_guild_permissions(manage_messages=True)
    async def warn_all(self, ctx: EvelinaContext):
        """Returns all warns on the server"""
        check = await self.bot.db.fetch("""SELECT * FROM warns WHERE guild_id = $1""", ctx.guild.id)
        if len(check) == 0:
            return await ctx.send_warning("There are no warnings on this server.")
        formatted_warnings = []
        for result in check:
            member = ctx.guild.get_member(result['user_id'])
            member_name = member.name if member else "Unknown Member"
            time_str = result['time']
            try:
                timestamp = float(time_str)
                formatted_time = datetime.fromtimestamp(timestamp).strftime('<t:%s:F>' % int(timestamp))
            except ValueError:
                try:
                    formatted_time = datetime.strptime(time_str, '%d/%m/%y at %I:%M %p').strftime('<t:%s:R>' % int(datetime.strptime(time_str, '%d/%m/%y at %I:%M %p').timestamp()))
                except ValueError:
                    formatted_time = 'Unknown Time Format'
            formatted_warnings.append(f"<@!{result['user_id']}> {result['reason']} - {formatted_time}\n{emojis.REPLY} **Moderator:** <@!{result['author_id']}>")
        return await ctx.paginate(formatted_warnings, f"Server Warnings", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @warn.group(name="rewards", description="Manage the roles that get a user for certains warns", invoke_without_command=True, case_insensitive=True)
    async def warn_rewards(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @warn_rewards.command(name="add", brief="manage guild", usage="warn rewards add 3 dangerous", description="Assign a warn role to a warn level")
    @has_guild_permissions(manage_guild=True)
    async def warn_rewards_add(self, ctx: EvelinaContext, warn: int, *, role: NewRoleConverter):
        if warn < 1:
            return await ctx.send_warning("It's not possible to add a punishment for **{warn} warns**")
        if check := await self.bot.db.fetchrow("SELECT * FROM warns_rewards WHERE guild_id = $1 AND warn = $2", ctx.guild.id, warn):
            return await ctx.send_warning(f"There are already a reward for reaching **{check['warn']} warns**")
        await self.bot.db.execute("INSERT INTO warns_rewards VALUES ($1, $2, $3)", ctx.guild.id, warn, role.id)
        return await ctx.send_success(f"Added a reward for reaching **{warn} warns**")
    
    @warn_rewards.command(name="remove", brief="manage guild", usage="warn rewards remove 3", description="Remove a reward from a warn level")
    @has_guild_permissions(manage_guild=True)
    async def warn_rewards_remove(self, ctx: EvelinaContext, *, warn: int):
        if check := await self.bot.db.fetchrow("SELECT * FROM warns_rewards WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, warn):
            await self.bot.db.execute("DELETE FROM warns_rewards WHERE guild_id = $1 AND role_id = $2", ctx.guild.id, warn)
            return await ctx.send_success(f"Removed a reward for reaching **{check['warn']} warns**")
        return await ctx.send_warning(f"There are no rewards set for **{warn} warns**")
    
    @warn_rewards.command(name="reset", brief="manage guild", description="Remove every reward that was added")
    @has_guild_permissions(manage_guild=True)
    async def warn_rewards_reset(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM warns_rewards WHERE guild_id = $1", interaction.guild.id)
            await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed every reward that was saved in this server"), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Warn reward deletion got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure that you want to **remove** every reward saved in this server?", yes_callback, no_callback)

    @warn_rewards.command(name="list", brief="manage guild", description="Get a list of every role reward in this server")
    async def warn_rewards_list(self, ctx: EvelinaContext):
        check = await self.bot.db.fetch("SELECT role_id, warn FROM warns_rewards WHERE guild_id = $1", ctx.guild.id)
        roles = sorted(check, key=lambda c: c["warn"])
        if not roles:
            return await ctx.send_warning("There are no warn rewards set")
        def format_role(role_id):
            role = ctx.guild.get_role(role_id)
            return role.mention if role else f"`{role_id}`"
        return await ctx.paginate([f"{format_role(r['role_id'])} for **{r['warn']} warns**" for r in roles], "Warn rewards", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})
    
    @warn_rewards.command(name="sync", brief="manage guild", description="Sync all user's roles based on their warns")
    @has_guild_permissions(manage_guild=True)
    @cooldown(1, 3600, BucketType.guild)
    async def warn_rewards_sync(self, ctx: EvelinaContext):
        guild = ctx.guild
        warn_rewards = await self.bot.db.fetch("SELECT warn, role_id FROM warns_rewards WHERE guild_id = $1", guild.id)
        if not warn_rewards:
            return await ctx.send_warning("There are no warn rewards configured for this server")
        warn_rewards_dict = {}
        for reward in warn_rewards:
            warn_rewards_dict.setdefault(reward['warn'], []).append(reward['role_id'])
        users_warns = await self.bot.db.fetch("SELECT user_id, COUNT(*) FROM warns WHERE guild_id = $1 GROUP BY user_id", guild.id)
        if not users_warns:
            return await ctx.send_warning("No user warns found for this server")
        loading_message = await ctx.send_loading("Synchronizing all users roles with their warns...")
        batch_size = 5
        delay_between_batches = 2
        for i in range(0, len(users_warns), batch_size):
            batch = users_warns[i:i + batch_size]
            for user_data in batch:
                user_id = user_data['user_id']
                user_warns = user_data['count']
                member = guild.get_member(user_id)
                if not member:
                    continue
                roles_to_add = []
                for warn in range(1, user_warns + 1):
                    roles_to_add.extend(warn_rewards_dict.get(warn, []))
                roles_to_add = [guild.get_role(role_id) for role_id in roles_to_add if guild.get_role(role_id) not in member.roles]
                if roles_to_add:
                    try:
                        await member.add_roles(*roles_to_add, reason="Syncing warn rewards")
                    except HTTPException:
                        pass
                roles_to_remove = []
                for warn, role_ids in warn_rewards_dict.items():
                    if warn > user_warns:
                        roles_to_remove.extend([guild.get_role(role_id) for role_id in role_ids if guild.get_role(role_id) in member.roles])
                if roles_to_remove:
                    try:
                        await member.remove_roles(*roles_to_remove, reason="Syncing warn rewards")
                    except HTTPException:
                        pass
                await asyncio.sleep(delay_between_batches)
        embed = Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {ctx.author.mention}: All users roles have been synchronized based on their warns.")
        await loading_message.edit(embed=embed)

    @warn.group(name="punishment", brief="manage guild", description="Manage punishments that get a user for certains warns", invoke_without_command=True, case_insensitive=True)
    async def warn_punishment(self, ctx: EvelinaContext):
        return await ctx.create_pages()

    @warn_punishment.command(name="add", brief="manage guild", usage="warn punishment add 3 ban 12h", description="Assign a punishment to a warn level")
    @has_guild_permissions(manage_guild=True)
    async def warn_punishment_add(self, ctx: EvelinaContext, warn: int, action: str, time: ValidTime = None):
        if warn < 1:
            return await ctx.send_warning(f"It's not possible to add a punishment for **{warn} warns**")
        if await self.bot.db.fetchrow("SELECT * FROM warns_punishment WHERE guild_id = $1 AND warn = $2", ctx.guild.id, warn):
            return await ctx.send_warning(f"There are already a punishment set for **{warn} warns**")
        if action in ["ban", "kick"]:
            await self.bot.db.execute("INSERT INTO warns_punishment VALUES ($1, $2, $3, $4)", ctx.guild.id, warn, action, None)
            return await ctx.send_success(f"Added **{action}** as punishment for **{warn} warns**")
        elif action in ["jail", "mute"]:
            if time is None: 
                time = 3600
            if time > 28 * 24 * 60 * 60:
                return await ctx.send_warning("You can't set a duration with more than **28 days**")
            duration = format_timespan(time) if time != 0 else 'Infinity'
            await self.bot.db.execute("INSERT INTO warns_punishment VALUES ($1, $2, $3, $4)", ctx.guild.id, warn, action, time)
            return await ctx.send_success(f"Added **{action}** (`{duration}`) as punishment for **{warn} warns**")
        else:
            return await ctx.send_warning("Invalid action. Valid actions are: `ban`, `kick`, `jail` & `mute`")
        
    @warn_punishment.command(name="remove", brief="manage guild", usage="warn punishment remove 3", description="Remove a punishment from a warn level")
    @has_guild_permissions(manage_guild=True)
    async def warn_punishment_remove(self, ctx: EvelinaContext, warn: int):
        if warn < 1:
            return await ctx.send_warning(f"It's not possible to add a punishment for **{warn} warns**")
        check = await self.bot.db.fetchrow("SELECT * FROM warns_punishment WHERE guild_id = $1 AND warn = $2", ctx.guild.id, warn)
        if not check:
            return await ctx.send_warning(f"There are no punishment set for **{warn} warns**")
        await self.bot.db.execute("DELETE FROM warns_punishment WHERE guild_id = $1 AND warn = $2", ctx.guild.id, warn)
        return await ctx.send_success(f"Removed **{check['action']}** as punishment for **{warn} warns**")

    @warn_punishment.command(name="reset", brief="manage guild", description="Remove every punishment that was added")
    @has_guild_permissions(manage_guild=True)
    async def warn_punishment_reset(self, ctx: EvelinaContext):
        async def yes_callback(interaction: Interaction):
            await interaction.client.db.execute("DELETE FROM warns_punishment WHERE guild_id = $1", interaction.guild.id)
            await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Removed every punishment that was saved in this server"), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Warn punishment deletion got canceled"), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure that you want to **remove** every punishment saved in this server?", yes_callback, no_callback)

    @warn_punishment.command(name="list", brief="Manage guild", description="Get a list of every punishment in this server")
    async def warn_punishment_list(self, ctx: EvelinaContext):
        check = await self.bot.db.fetch("SELECT action, warn, time FROM warns_punishment WHERE guild_id = $1", ctx.guild.id)
        roles = sorted(check, key=lambda c: c["warn"])
        if not roles:
            return await ctx.send_warning("There are no punishments set for warns")
        content = []
        for r in roles:
            action = r['action']
            time = f" (`{format_timespan(r['time']) if r['time'] != 0 else 'Infinity'}`)" if r['time'] else ""
            content.append(f"{str(action).capitalize()}{time} for **{r['warn']} warns**")
        return await ctx.paginate(content, title="Warn Punishments", author={"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    async def decide_punishment(self, ctx, user, warns, reason):
        check = await self.bot.db.fetchrow("SELECT action, time FROM warns_punishment WHERE guild_id = $1 AND warn = $2", ctx.guild.id, warns)
        if not check:
            return
        punishment = check["action"]
        time = check["time"]
        if punishment == "mute":
            return await self.mute(ctx, user, time=time, reason=f"{reason} | {warns} warns")
        elif punishment == "jail":
            return await self.jail(ctx, user, time=time, reason=f"{reason} | {warns} warns")
        elif punishment == "kick":
            return await self.kick(ctx, user, reason=f"{reason} | {warns} warns")
        elif punishment == "ban":
            return await self.ban(ctx, user, reason=f"{reason} | {warns} warns")
    
    @command()
    async def warns(self, ctx: EvelinaContext, *, member: Member):
        """Shows all warns of an user"""
        return await ctx.invoke(self.bot.get_command("warn list"), member=member)

    def is_community_channel(self, channel: TextChannel) -> bool:
        if channel.guild.rules_channel and channel.id == channel.guild.rules_channel.id:
            return True
        if channel.guild.system_channel and channel.id == channel.guild.system_channel.id:
            return True
        if channel.guild.public_updates_channel and channel.id == channel.guild.public_updates_channel.id:
            return True
        return False

    @group(brief="administrator", invoke_without_command=True)
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def nuke(self, ctx: EvelinaContext):
        """Replace the current channel with a new one"""
        if self.is_community_channel(ctx.channel):
            return await ctx.send_warning("You can't delete channels that are **required** by community servers")
        async with self.locks[ctx.channel.id]:
            async def yes_callback(interaction: Interaction) -> None:
                new_channel = await interaction.channel.clone(name=interaction.channel.name, reason=f"Nuking channel invoked by {ctx.author}")
                message = ""
                await new_channel.edit(
                    topic=interaction.channel.topic if hasattr(interaction.channel, 'topic') else None,
                    position=interaction.channel.position,
                    nsfw=interaction.channel.nsfw if hasattr(interaction.channel, 'nsfw') else False,
                    slowmode_delay=interaction.channel.slowmode_delay if hasattr(interaction.channel, 'slowmode_delay') else 0,
                    type=interaction.channel.type,
                    reason=f"Nuking channel invoked by {ctx.author}",
                )
                for i in ["welcome", "leave", "boost", "nuke_scheduler", "stickymessage", "channel_disabled_commands", "channel_disabled_module"]:
                    if await self.bot.db.fetchrow(f"SELECT * FROM {i} WHERE guild_id = $1 AND channel_id = $2", interaction.guild.id, interaction.channel.id):
                        await self.bot.db.execute(f"UPDATE {i} SET channel_id = $1 WHERE guild_id = $2 AND channel_id = $3", new_channel.id, interaction.guild.id, interaction.channel.id)
                        message += f" - restored a {i} setup to {new_channel.mention}"
                try:
                    await interaction.channel.delete(reason="Channel nuked by the server administrator")
                except Exception:
                    pass
                try:
                    await new_channel.send(content=f"Channel nuked by {ctx.author.mention}")
                except Exception:
                    pass
                try:
                    await interaction.message.delete()
                except Exception:
                    return
            async def no_callback(interaction: Interaction) -> None:
                await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Channel nuke got canceled."), view=None)
            await ctx.confirmation_send(f"{ctx.author.mention}: Are you sure you want to **nuke** this channel?\nThis action is **IRREVERSIBLE**", yes_func=yes_callback, no_func=no_callback)

    @nuke.command(name="add", brief="administrator", usage="nuke add #general 24h")
    @admin_antinuke()
    @bot_has_guild_permissions(manage_channels=True)
    @has_guild_permissions(administrator=True)
    async def nuke_add_scheduler(self, ctx: EvelinaContext, channel: TextChannel, schedule: ValidTime):
        """Add a nuke schedule for a channel."""
        if schedule < 600:
            return await ctx.send_warning("The minimum nuke schedule is **10 minutes**")
        if self.is_community_channel(ctx.channel):
            return await ctx.send_warning("You can't delete channels that are **required** by community servers")
        existing_entry = await self.bot.db.fetchrow("SELECT * FROM nuke_scheduler WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        if existing_entry:
            return await ctx.send_warning("A nuke schedule for this channel **already** exists")
        await self.bot.db.execute("INSERT INTO nuke_scheduler (guild_id, channel_id, schedule, last_nuke) VALUES ($1, $2, $3, $4)", ctx.guild.id, channel.id, int(schedule), datetime.now().timestamp())
        await ctx.send_success("Nuke schedule added"f"\n> Channel: {channel.mention}\n> Schedule: **{self.bot.misc.humanize_time(schedule)}**")

    @nuke.command(name="remove", brief="administrator", usage="nuke remove #general")
    @admin_antinuke()
    @bot_has_guild_permissions(manage_channels=True)
    @has_guild_permissions(administrator=True)
    async def nuke_remove_scheduler(self, ctx: EvelinaContext, channel: TextChannel):
        """Remove a nuke schedule for a channel."""
        existing_entry = await self.bot.db.fetchrow("SELECT * FROM nuke_scheduler WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        if not existing_entry:
            return await ctx.send_warning("No nuke schedule **found** for this channel")
        await self.bot.db.execute("DELETE FROM nuke_scheduler WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, ctx.channel.id)
        await ctx.send_success(f"Nuke schedule removed for {channel.mention}")

    @nuke.command(name="list", brief="administrator")
    @admin_antinuke()
    @bot_has_guild_permissions(manage_channels=True)
    @has_guild_permissions(administrator=True)
    async def nuke_list_schedules(self, ctx: EvelinaContext):
        """List all nuke schedules for the current server with the next nuke time."""
        schedules = await self.bot.db.fetch("SELECT channel_id, schedule, last_nuke FROM nuke_scheduler WHERE guild_id = $1", ctx.guild.id)
        if not schedules:
            return await ctx.send_warning("No nuke schedules **found** for this server.")
        schedule_messages = []
        for schedule in schedules:
            channel_id = schedule['channel_id']
            schedule_interval = schedule['schedule']
            last_nuke_timestamp = schedule['last_nuke']
            humanized_schedule = self.bot.misc.humanize_time(schedule_interval)
            next_nuke_time = last_nuke_timestamp + schedule_interval
            channel = ctx.guild.get_channel(channel_id)
            channel_mention = channel.mention if channel else f"<#{channel_id}>"
            schedule_messages.append(f"{channel_mention}: **{humanized_schedule}**\n> **Next Nuke:** <t:{next_nuke_time}:R>")
        await ctx.paginate(schedule_messages, f"Nuke Schedules ({len(schedules)})", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url})

    @group(name="channel", brief="manage channels", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def channel(self, ctx: EvelinaContext):
        """Manage channels in your sever"""
        return await ctx.create_pages()

    @channel.command(name="create", aliases=["make"], brief="manage channels", usage="channel create #commands")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def channel_create(self, ctx: EvelinaContext, *, name: str):
        """Create a channel in your server"""
        channel = await ctx.guild.create_text_channel(name=name)
        return await ctx.send_success(f"Created {channel.mention}")

    @channel.command(name="remove", aliases=["delete", "del"], brief="manage channels", usage="channel remove #commands")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def channel_remove(self, ctx: EvelinaContext, *, channel: TextChannel = CurrentChannel):
        """Delete a channel in your server"""
        async def yes_callback(interaction: Interaction):
            try:
                await channel.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
            except Forbidden:
                return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Couldn't delete {channel.mention} due to insufficient permissions."), view=None)
            except HTTPException as e:
                if e.code == 50074:
                    return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Cannot delete {channel.mention} because it is required for community servers."), view=None)
                else:
                    raise
            if channel != ctx.channel:
                return await interaction.response.edit_message(embed=Embed(color=colors.SUCCESS, description=f"{emojis.APPROVE} {interaction.user.mention}: Channel `#{channel.name}` deleted successfully"), view=None)
            else:
                return
        async def no_callback(interaction: Interaction):
            return await interaction.response.edit_message(embed=Embed(color=colors.ERROR, description=f"{emojis.DENY} {interaction.user.mention}: Channel deletion was canceled."), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to delete the channel **{channel.name}**?", yes_func=yes_callback, no_func=no_callback)

    @channel.command(name="rename", aliases=["name"], brief="manage channels", usage="channel rename #commands cmds")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def channel_rename(self, ctx: EvelinaContext, channel: TextChannel, *, name: str):
        """Rename a channel"""
        if len(name) > 150:
            return await ctx.send_warning(f"Channel names can't be over **150 characters**")
        name = name.replace(" ", "-")
        try:
            await channel.edit(name=name)
        except Forbidden:
            return await ctx.send_warning(f"Couldn't rename {channel.mention}")
        await ctx.send_success(f"Renamed `#{channel.name}` to **{name}**")

    @channel.command(name="category", brief="manage channels", usage="channel category #commands home")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def channel_category(self, ctx: EvelinaContext, channel: TextChannel, *, category: CategoryChannel):
        """Move a channel to a new category"""
        try:
            await channel.edit(category=category)
        except Forbidden:
            return await ctx.send_warning(f"Couldn't change {channel.mention}'s category")
        await ctx.send_success(f"Moved {channel.mention} under {category.mention}")

    @channel.command(name="nsfw", aliases=["naughty"], brief="manage channels", usage="channel nsfw #images")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def channel_nsfw(self, ctx: EvelinaContext, *, channel: TextChannel = CurrentChannel):
        """Toggle NSFW for a channel"""
        try:
            await channel.edit(nsfw=not channel.nsfw)
        except Forbidden:
            return await ctx.send_warning(f"Couldn't mark/unmark {channel.mention} as NSFW")
        if ctx.message:
            await ctx.message.add_reaction("✅")

    @channel.command(name="topic", brief="manage channels", usage="channel topic [#channel] <topic>")
    @has_guild_permissions(manage_channels=True)
    @bot_has_guild_permissions(manage_channels=True)
    async def channel_topic(self, ctx: EvelinaContext, channel: Optional[TextChannel] = None, *, topic: str):
        """Change a channel's topic"""
        if channel is None:
            channel = ctx.channel
        if len(topic) > 1024:
            return await ctx.send_warning(f"Channel topics can't be over **1024 characters**")
        try:
            await channel.edit(topic=topic)
        except Forbidden:
            return await ctx.send_warning(f"Couldn't change {channel.mention}'s topic")
        await ctx.send_success(f"Changed {channel.mention}'s topic to `{topic}`")

    @group(name="category", brief="manage channels", case_insensitive=True, invoke_without_command=True)
    @has_guild_permissions(manage_channels=True)
    async def category(self, ctx: EvelinaContext):
        """Manage categories in your server"""
        return await ctx.create_pages()

    @category.command(name="create", brief="manage channels", usage="category create home")
    @has_guild_permissions(manage_channels=True)
    async def category_create(self, ctx: EvelinaContext, *, name: str):
        """Create a category in your server"""
        category = await ctx.guild.create_category(name=name)
        await ctx.send_success(f"Created category {category.mention}")

    @category.command(name="delete", brief="manage channels", usage="category delete home")
    @has_guild_permissions(manage_channels=True)
    async def category_delete(self, ctx: EvelinaContext, *, category: CategoryChannel):
        """Delete a category in your server"""
        async def yes_func(interaction: Interaction):
            await category.delete(reason=f"Deleted by {ctx.author} {ctx.author.id}")
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Deleted category `#{category.name}`", color=colors.SUCCESS))
        async def no_func(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {interaction.user.mention}: Category deletion got canceled", color=colors.ERROR))
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **delete** the category `#{category.name}`?", yes_func, no_func)

    @category.command(name="rename", brief="manage channels", usage="category rename home privat")
    @has_guild_permissions(manage_channels=True)
    async def category_rename(self, ctx: EvelinaContext, category: CategoryChannel, *, name: str):
        """Rename a category in your server"""
        _name = category.name
        await category.edit(name=name, reason=f"Edited by {ctx.author} ({ctx.author.id})")
        await ctx.send_success(f"Renamed **{_name}** to `{name}`")

    @category.command(name="duplicate", aliases=["clone", "remake"], usage="category duplicate home")
    @has_guild_permissions(manage_channels=True)
    async def category_duplicate(self, ctx: EvelinaContext, *, category: CategoryChannel):
        """Clone an already existing category in your server"""
        _category = await category.clone(name=category.name, reason=f"Cloned by {ctx.author} ({ctx.author.id})")
        await ctx.send_success(f"Cloned {category.mention} to {_category.mention}")

    @command(name="pin", brief="manage messages", usage="pin https://discord.com/channels/1228371886690537624/1228378130792579182/1256922127018233957")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def pin(self, ctx: EvelinaContext, message: ValidMessage = None):
        """Pin a message"""
        if not message:
            if ctx.message.reference:
                message = await ctx.fetch_message(int(ctx.message.reference.message_id))
            else:
                async for message in ctx.channel.history(limit=2):
                    message = message
        message: Message = message
        if message.pinned:
            return await ctx.send_warning(f"That message is already **pinned**")
        try:
            await message.pin(reason=f"Pinned by {ctx.author} ({ctx.author.id})")
        except Exception as e:
            if "can't execute action on a system message" in str(e):
                return await ctx.send_warning(f"You can't **pin** system messages")
        await ctx.message.add_reaction("✅")

    @command(name="unpin", brief="manage messages", usage="pin https://discord.com/channels/1228371886690537624/1228378130792579182/1256922127018233957")
    @has_guild_permissions(manage_messages=True)
    @bot_has_guild_permissions(manage_messages=True)
    async def unpin(self, ctx: EvelinaContext, message: ValidMessage = None):
        """Unpin a message"""
        if not message:
            if ctx.message.reference:
                message = await ctx.fetch_message(int(ctx.message.reference.message_id))
            else:
                async for message in ctx.channel.history(limit=2):
                    message = message
        message: Message = message
        if not message.pinned:
            return await ctx.send_warning(f"That message is **not** pinned")
        await message.unpin(reason=f"Unpinned by {ctx.author} ({ctx.author.id})")
        await ctx.message.add_reaction("✅")

    @group(name="thread", brief="manage threads", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread(self, ctx: EvelinaContext):
        """Manage threads"""
        return await ctx.create_pages()

    @command(name="tl", brief="manage threads", usage="tl #support")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def tl(self, ctx: EvelinaContext, thread: Thread = None):
        """Lock a thread"""
        await self.thread_lock(ctx, thread=thread)

    @thread.command(name="lock", brief="manage threads", usage="thraed lock #support")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_lock(self, ctx: EvelinaContext, thread: Thread = None):
        """Lock a thread"""
        thread = thread or ctx.channel
        if not isinstance(thread, Thread):
            return await ctx.send_warning(f"{thread.mention} is not a thread")
        if thread.locked:
            return await ctx.send_warning(f"{thread.mention} is already locked")
        await thread.edit(locked=True, reason=f"Locked by {ctx.author} ({ctx.author.id})")
        await ctx.send_success(f"Successfully **locked** {thread.mention}")
        await ctx.message.delete()

    @thread.command(name="unlock", brief="manage threads", usage="thread unlock #support")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_unlock(self, ctx: EvelinaContext, thread: Thread = None):
        """Unlock a locked thread"""
        thread = thread or ctx.channel
        if not isinstance(thread, Thread):
            return await ctx.send_warning(f"{thread.mention} is not a thread")
        if not thread.locked:
            return await ctx.send_warning(f"{thread.mention} is **not** locked")
        await thread.edit(locked=False, reason=f"Unlocked by {ctx.author} ({ctx.author.id})")
        await ctx.send_success(f"Successfully **unlocked** {thread.mention}")

    @thread.command(name="create", brief="manage threads", usage="thread create .../channels/...")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_create(self, ctx: EvelinaContext, message: ValidMessage, *, name: str):
        """Create a thread in a channel"""
        try:
            thread = await message.create_thread(name=name)
        except Exception:
            return await ctx.send_warning(f"Couldn't create a thread in {message.channel}")
        return await ctx.send_success(f"Created {thread.mention}")

    @thread.command(name="delete", brief="manage threads", usage="thread delete #support")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_delete(self, ctx: EvelinaContext, thread: Thread = None):
        """Delete a thread"""
        thread = thread or ctx.channel
        if not isinstance(thread, Thread):
            return await ctx.send_warning(f"{thread.mention} is not a thread")
        await thread.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        await ctx.send_success(f"Deleted {thread.mention}")

    @thread.command(name="add", brief="manage threads", usage="thread add comminate")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_add(self, ctx: EvelinaContext, member: Member):
        """Add a member to a thread"""
        if not isinstance(ctx.channel, Thread):
            return await ctx.send_warning(f"{ctx.channel.mention} is not a thread")
        if ctx.channel.archived:
            return await ctx.send_warning(f"{ctx.channel.mention} is archived. Unarchive it to add members.")
        if ctx.channel.locked:
            return await ctx.send_warning(f"{ctx.channel.mention} is locked. Unlock it to add members.")
        try:
            thread_member = await ctx.channel.fetch_member(member.id)
            if thread_member:
                return await ctx.send_warning(f"{member.mention} is already in {ctx.channel.mention}")
        except NotFound:
            pass
        try:
            await ctx.channel.add_user(member)
            await ctx.send_success(f"Added {member.mention} to {ctx.channel.mention}")
        except Forbidden:
            return await ctx.send_warning(f"Missing permissions to add {member.mention} to {ctx.channel.mention}")

    @thread.command(name="remove", brief="manage threads", usage="thread remove comminate")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_remove(self, ctx: EvelinaContext, member: Member):
        """Remove a member from a thread"""
        if not isinstance(ctx.channel, Thread):
            return await ctx.send_warning(f"{ctx.channel.mention} is not a thread")
        if member == ctx.author:
            return await ctx.send_warning("You can't remove yourself from a thread")
        try:
            thread_member = await ctx.channel.fetch_member(member.id)
        except NotFound:
            return await ctx.send_warning(f"{member.mention} is not in {ctx.channel.mention}")
        try:
            await ctx.channel.remove_user(member)
            await ctx.send_success(f"Removed {member.mention} from {ctx.channel.mention}")
        except Forbidden:
            return await ctx.send_warning(f"Missing permissions to remove {member.mention} from {ctx.channel.mention}")

    @thread.command(name="watch", brief="manage threads", usage="thread watch on")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_watch(self, ctx: EvelinaContext, mode: str):
        """Watch a thread"""
        if mode.lower() not in ["on", "off"]:
            return await ctx.send_warning("Invalid mode. Choose from `on` or `off`")
        if mode.lower() == "on":
            await self.bot.db.execute("INSERT INTO thread_watcher (guild_id, state) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET state = $2", ctx.guild.id, True)
            return await ctx.send_success(f"Threads in this server will be watched")
        if mode.lower() == "off":
            await self.bot.db.execute("INSERT INTO thread_watcher (guild_id, state) VALUES ($1, $2) ON CONFLICT (guild_id) DO UPDATE SET state = $2", ctx.guild.id, False)
            return await ctx.send_success(f"Threads in this server will **not** be watched")

    @thread.group(name="auto", brief="manage threads", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_auto(self, ctx: EvelinaContext):
        """Manage auto-thread settings"""
        return await ctx.create_pages()

    @thread_auto.command(name="add", brief="manage threads", usage="thread auto add #selfies")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_auto_add(self, ctx: EvelinaContext, channel: TextChannel):
        """Add a channel to auto-thread"""
        if await self.bot.db.fetchrow("SELECT * FROM autothread WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id):
            return await ctx.send_warning(f"{channel.mention} is already in auto-thread")
        await self.bot.db.execute("INSERT INTO autothread VALUES ($1, $2)", ctx.guild.id, channel.id)
        await ctx.send_success(f"Added {channel.mention} to auto-thread")

    @thread_auto.command(name="remove", brief="manage threads", usage="thread auto remove #selfies")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_auto_remove(self, ctx: EvelinaContext, channel: TextChannel):
        """Remove a channel from auto-thread"""
        if not await self.bot.db.fetchrow("SELECT * FROM autothread WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id):
            return await ctx.send_warning(f"{channel.mention} is not in auto-thread")
        await self.bot.db.execute("DELETE FROM autothread WHERE guild_id = $1 AND channel_id = $2", ctx.guild.id, channel.id)
        await ctx.send_success(f"Removed {channel.mention} from auto-thread")

    @thread_auto.command(name="list", brief="manage threads", usage="thread auto list")
    @has_guild_permissions(manage_threads=True)
    @bot_has_guild_permissions(manage_threads=True)
    async def thread_auto_list(self, ctx: EvelinaContext):
        """List all auto-thread channels"""
        channels = await self.bot.db.fetch("SELECT * FROM autothread WHERE guild_id = $1", ctx.guild.id)
        if not channels:
            return await ctx.send_warning("There are no auto-thread channels")
        formatted_channels = []
        for channel in channels:
            channel = ctx.guild.get_channel(channel['channel_id'])
            formatted_channels.append(channel.mention)
        return await ctx.paginate(formatted_channels, "Auto-Thread Channels", {"name": ctx.guild.name, "icon_url": ctx.guild.icon.url if ctx.guild.icon else None})

    @command(name="hardban", brief="administrator & antinuke admin", usage="hardban comminate rassist")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(ban_members=True)
    @admin_antinuke()
    async def hardban(self, ctx: EvelinaContext, member: NoStaff | User, *, reason: str = "No reason provided"):
        """Keep a member banned from the server"""
        async def yes_callback(interaction: Interaction):
            await self.bot.db.execute("INSERT INTO hardban VALUES ($1, $2, $3, $4)", ctx.guild.id, member.id, reason, ctx.author.id)
            try:
                await ctx.guild.ban(member, reason=f"Hardbanned by {ctx.author} ({ctx.author.id}): {reason}")
            except:
                pass
            current_timestamp = utils.utcnow().timestamp()
            history_id = await self.insert_history(ctx, member, "Hardban", 'None', reason, current_timestamp)
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.APPROVE} {interaction.user.mention}: Hardbanned {member.mention} (`#{history_id}`) - **{reason}**", color=colors.SUCCESS,), view=None)
        async def no_callback(interaction: Interaction):
            await interaction.response.edit_message(embed=Embed(description=f"{emojis.DENY} {interaction.user.mention}: Hardban got canceled", color=colors.ERROR), view=None)
        await ctx.confirmation_send(f"{emojis.QUESTION} {ctx.author.mention}: Are you sure you want to **hardban** {member.mention}?", yes_callback, no_callback)

    @command(name="unhardban", brief="administrator & antinuke admin", usage="unhardban comminate rassist")
    @has_guild_permissions(administrator=True)
    @bot_has_guild_permissions(ban_members=True)
    @admin_antinuke()
    async def unhardban(self, ctx: EvelinaContext, user: User, *, reason: str = "No reason provided"):
        """Unhardban a hardbanned member"""
        check = await self.bot.db.fetchrow("SELECT * FROM hardban WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
        if not check:
            return await ctx.send_warning(f"{user.mention} is **not** hardbanned")
        await self.bot.db.execute("DELETE FROM hardban WHERE guild_id = $1 AND user_id = $2", ctx.guild.id, user.id)
        try:
            await ctx.guild.unban(user, reason=f"Unhardbanned by {ctx.author} ({ctx.author.id}): {reason}")
        except:
            pass
        current_timestamp = utils.utcnow().timestamp()
        history_id = await self.insert_history(ctx, user, "Unhardban", 'None', reason, current_timestamp)
        await ctx.send_success(f"Unhardbanned {user.mention} (`#{history_id}`) - **{reason}**")

    @command(name="revokefiles", brief="manage messages", usage="revokefiles on comminate nsfw")
    @has_guild_permissions(manage_messages=True)
    async def revokefiles(self, ctx: EvelinaContext, state: str, member: NoStaff, *, reason: str = "No reason provided"):
        """Remove file attachment permissions from a member"""
        if not state.lower() in ("on", "off"):
            return await ctx.send_warning(f"Invalid state please provide **on** or **off**")
        if state.lower().strip() == "on":
            overwrite = ctx.channel.overwrites_for(member)
            overwrite.attach_files = False
            await ctx.channel.set_permissions(member, overwrite=overwrite, reason=f"{ctx.author} ({ctx.author.id}) removed file attachment permissions: {reason}")
        elif state.lower().strip() == "off":
            overwrite = ctx.channel.overwrites_for(member)
            overwrite.attach_files = True
            await ctx.channel.set_permissions(member, overwrite=overwrite, reason=f"{ctx.author} ({ctx.author.id}) removed file attachment permissions: {reason}")
        await ctx.message.add_reaction("✅")

    @group(name="case", brief="moderate members", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(moderate_members=True)
    async def case(self, ctx: EvelinaContext):
        """Manage cases"""
        return await ctx.create_pages()

    @case.command(name="reason", brief="moderate members", usage="case reason 11 He was being racist")
    @has_guild_permissions(moderate_members=True)
    async def case_reason(self, ctx: EvelinaContext, case: int, *, reason: str):
        """Change the reason of a case"""
        check = await self.bot.db.fetchrow("""SELECT * FROM history WHERE server_id = $1 AND guild_id = $2""", ctx.guild.id, case)
        if not check:
            return await ctx.send_warning(f"Case with ID `#{case}` not found")
        await self.bot.db.execute("UPDATE history SET reason = $1 WHERE server_id = $2 AND guild_id = $3", reason, ctx.guild.id, case)
        await ctx.send_success(f"Changed reason of case `#{case}` to **{reason}**")

    @case.command(name="proof", brief="moderate members", usage="case proof 11 [attachment|proof text]")
    @has_guild_permissions(moderate_members=True)
    async def case_proof(self, ctx: EvelinaContext, case: int, proof: str = None):
        """Add proof to a case"""
        if ctx.message.attachments:
            attachment = ctx.message.attachments[0]
            file_extension = attachment.filename.split('.')[-1]
            file_name = f"{str(uuid.uuid4())[:8]}.{file_extension}"
            response = await self.bot.session.get_bytes(attachment.url)
            if response:
                file_data = BytesIO(response)
                content_type = attachment.content_type
                await self.bot.r2.upload_file("evelina", file_data, file_name, content_type, "c")
                file_url = f"https://cdn.evelina.bot/c/{file_name}"
                await self.bot.db.execute("UPDATE history SET proof = $1 WHERE server_id = $2 AND guild_id = $3", file_url, ctx.guild.id, case)
                await ctx.send_success(f"Attachment [`{file_name}`]({file_url}) uploaded and saved to case `#{case}`")
        elif proof:
            await self.bot.db.execute("UPDATE history SET proof = $1 WHERE server_id = $2 AND guild_id = $3", proof, ctx.guild.id, case)
            await ctx.send_success(f"Proof saved to case `#{case}`")
        else:
            await ctx.send_warning("You must provide either an attachment or a proof text")

    @case.command(name="info", brief="moderate members", usage="case info 11")
    @has_guild_permissions(moderate_members=True)
    async def case_info(self, ctx: EvelinaContext, case: int):
        """Get information about a case"""
        check = await self.bot.db.fetchrow("""SELECT * FROM history WHERE server_id = $1 AND guild_id = $2""", ctx.guild.id, case)
        if not check:
            return await ctx.send_warning(f"Case with ID `#{case}` not found")
        user = await self.bot.fetch_user(check['user_id'])
        duration = f"**Duration:** {check['duration']}\n" if check['duration'] else ""
        proof = f"**Proof:** {check['proof']}" if check['proof'] else ""
        embed = Embed(color=colors.NEUTRAL)
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.add_field(
            name=f"Case Log #{case} | {check['punishment']}",
            value=(
                f"**Punished:** <t:{int(check['time'])}:f>\n"
                f"**User:** {user.mention} (`{user.id}`)\n"
                f"**Moderator:** <@{check['moderator_id']}>\n"
                f"**Reason:** {check['reason']}\n"
                f"{duration}{proof}"
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @group(name="appeal", brief="manage server", invoke_without_command=True, case_insensitive=True)
    @has_guild_permissions(manage_guild=True)
    async def appeal(self, ctx: EvelinaContext):
        """Manage appeals"""
        return await ctx.create_pages()
    
    @appeal.command(name="set", brief="manage server", usage="appeal set #appeals")
    @has_guild_permissions(manage_guild=True)
    async def appeal_set(self, ctx: EvelinaContext, channel: TextChannel):
        """Set the appeals channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM appeals WHERE guild_id = $1", ctx.guild.id)
        if check:
            return await ctx.send_warning("There is already an appeals channel set")
        await self.bot.db.execute("INSERT INTO appeals VALUES ($1, $2)", ctx.guild.id, channel.id)
        return await ctx.send_success(f"Set {channel.mention} as the appeals channel")

    @appeal.command(name="remove", brief="manage server", usage="appeal remove")
    @has_guild_permissions(manage_guild=True)
    async def appeal_remove(self, ctx: EvelinaContext):
        """Remove the appeals channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM appeals WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is no appeals channel set")
        await self.bot.db.execute("DELETE FROM appeals WHERE guild_id = $1", ctx.guild.id)
        return await ctx.send_success("Removed the appeals channel")
    
    @appeal.command(name="list", brief="manage server", usage="appeal list")
    @has_guild_permissions(manage_guild=True)
    async def appeal_list(self, ctx: EvelinaContext):
        """List the appeals channel"""
        check = await self.bot.db.fetchrow("SELECT * FROM appeals WHERE guild_id = $1", ctx.guild.id)
        if not check:
            return await ctx.send_warning("There is no appeals channel set")
        channel = ctx.guild.get_channel(check['channel_id'])
        return await ctx.evelina_send(f"Appeals channel: {channel.mention}")

async def setup(bot) -> None:
    return await bot.add_cog(Moderation(bot))