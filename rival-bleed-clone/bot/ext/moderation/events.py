from discord.ext.commands import Cog, command, group, CommandError, has_permissions
from discord.ext import tasks
from discord import (
    Client,
    Embed,
    File,
    Member,
    User,
    Object,
    utils,
    AuditLogEntry,
    Guild,
)
from typing import Union, Optional
from datetime import datetime, timedelta
from lib.services.ModLogs import Handler
from lib.classes.builtins import catch
from lib.classes.database import Record
import asyncio


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self.modlogs = Handler(self.bot)

    async def cog_load(self):
        self.temp_moderation_loop.start()

    async def cog_unload(self):
        self.temp_moderation_loop.stop()

    @tasks.loop(seconds=2)
    async def temp_moderation_loop(self):
        with catch():

            async def temp_roles():
                delete = []

                def schedule_deletion(record: Record):
                    delete.append(
                        (
                            """DELETE FROM temproles WHERE guild_id = $1 AND user_id = $2 AND role_id = $3""",
                            record.guild_id,
                            record.user_id,
                            record.role_id,
                        )
                    )

                async def do_deletion():
                    for args in delete:
                        await self.bot.db.execute(*args)

                temp_roles = await self.bot.db.fetch("""SELECT * FROM temproles""")
                for record in temp_roles:
                    if not (guild := self.bot.get_guild(record.guild_id)):
                        continue
                    if not record.expiration <= datetime.now():
                        continue
                    if not (role := guild.get_role(record.role_id)):
                        schedule_deletion(record)
                        continue
                    if not (member := guild.get_member(record.member_id)):
                        schedule_deletion(record)
                        continue
                    if role not in member.roles:
                        schedule_deletion(record)
                        continue
                    await member.remove_roles(role, reason="Temporary Role Expired")
                await do_deletion()
                return

            async def temp_bans():
                temp_bans = await self.bot.db.fetch("""SELECT * FROM tempbans""")
                for record in temp_bans:
                    if not (guild := self.bot.get_guild(record.guild_id)):
                        continue
                    if not (moderator := guild.get_member(record.moderator_id)):
                        continue
                    if utils.utcnow() >= record.expiration:
                        self.bot.dispatch(
                            "tempban_expire",
                            record.user_id,
                            guild,
                            moderator,
                            record.expiration,
                            record.reason,
                        )

            async def temp_jails():
                temp_jails = await self.bot.db.fetch(
                    """SELECT * FROM jailed WHERE expiration IS NOT NULL"""
                )
                for record in temp_jails:
                    if not (guild := self.bot.get_guild(record.guild_id)):
                        continue
                    if not (member := guild.get_member(record.user_id)):
                        continue
                    if not (moderator := guild.get_member(record.moderator_id)):
                        continue
                    if utils.utcnow() >= record.expiration:
                        self.bot.dispatch(
                            "jail_expire",
                            member,
                            guild,
                            moderator,
                            record.expiration,
                            record.reason,
                        )

            await asyncio.gather(*[temp_bans(), temp_jails(), temp_roles()])

    async def get_message_configuration(self, guild: Guild, message_type: str):
        if not (
            data := await self.bot.db.fetchval(
                """SELECT dm_code FROM invocation WHERE guild_id = $1 AND command = $2""",
                guild.id,
                message_type.lower(),
            )
        ):
            return None
        return data

    @Cog.listener("on_audit_log_entry_create")
    async def moderation_logs(self, entry: AuditLogEntry):
        return await self.modlogs.do_log(entry)

    @Cog.listener("on_member_update")
    async def forcenick_check(self, before: Member, after: Member):
        if forced := await self.bot.db.fetchval(
            """SELECT nickname FROM forcenick WHERE guild_id = $1 AND user_id = $2""",
            before.guild.id,
            before.id,
        ):
            if after.nick != forced:
                await after.edit(nick=forced)

    @Cog.listener("on_member_join")
    async def forcenick_check2(self, member: Member):
        if forced := await self.bot.db.fetchval(
            """SELECT nickname FROM forcenick WHERE guild_id = $1 AND user_id = $2""",
            member.guild.id,
            member.id,
        ):
            await member.edit(nick=forced)

    @Cog.listener("on_softban_create")
    async def softban_create(self, member: User, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "softban")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_kick_create")
    async def kick_create(self, member: Member, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "kick")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_jail_create")
    async def jail_create(
        self,
        member: Member,
        guild: Guild,
        moderator: Member,
        timeframe: Optional[int] = None,
        expiration: Optional[datetime] = None,
        reason: Optional[str] = "No Reason Provided",
    ):
        if not (data := await self.get_message_configuration(guild, "jail")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_jail_delete")
    async def unjail_create(self, member: Member, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "unjail")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_jail_expire")
    async def jail_expired(
        self,
        member: Member,
        guild: Guild,
        moderator: Member,
        expiration: datetime,
        reason: Optional[str] = "No Reason Provided",
    ):
        jailed = utils.get(guild.roles, name="jailed")
        roles = await self.bot.db.fetchval(
            """SELECT role_ids FROM jailed WHERE guild_id = $1 AND user_id = $2""",
            guild.id,
            member.id,
        )
        new_roles = member.roles
        new_roles.remove(jailed)
        for role in roles:
            if r := guild.get_role(role):
                new_roles.append(r)
        await member.edit(roles=new_roles, reason=f"jail expired")
        await self.bot.db.execute(
            """DELETE FROM jailed WHERE guild_id = $1 AND user_id = $2""",
            guild.id,
            member.id,
        )

        if not (data := await self.get_message_configuration(guild, "unjail")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_timeout_create")
    async def timeout_create(self, member: Member, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "timeout")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_timeout_delete")
    async def untimeout_create(self, member: Member, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "untimeout")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_ban_create")
    async def ban_create(self, member: User, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "ban")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_ban_delete")
    async def unban_create(self, member: User, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "unban")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_hardban_create")
    async def hardban_create(self, member: User, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "hardban")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_hardban_delete")
    async def hardban_delete(self, member: User, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "unhardban")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_tempban_create")
    async def tempban_create(
        self,
        member: User,
        guild: Guild,
        moderator: Member,
        expiration: datetime,
        reason: str,
    ):
        if not (data := await self.get_message_configuration(guild, "tempban")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)

    @Cog.listener("on_tempban_expire")
    async def tempban_expired(
        self,
        member: Union[User, int],
        guild: Guild,
        moderator: Member,
        expiration: datetime,
        reason: str,
    ):
        await guild.unban(
            Object(member.id) if not isinstance(member, int) else Object(member),
            reason="tempban ban expired",
        )
        await self.bot.db.execute(
            """DELETE FROM tempbans WHERE guild_id = $1 AND user_id = $2""",
            guild.id,
            member.id if not isinstance(member, int) else member,
        )

    @Cog.listener("on_warn_create")
    async def warn_create(self, member: Member, guild: Guild, moderator: Member):
        if not (data := await self.get_message_configuration(guild, "warn")):
            return
        with catch():
            await self.bot.send_embed(member, data, user=member, moderator=moderator)
