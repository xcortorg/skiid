from discord.ext.commands import (
    Cog,
)
from discord import Client, AuditLogEntry, Member, Object, Guild

from discord.ext.tasks import loop
from aiohttp import ClientSession
from typing import Optional, List, Dict
from lib.classes.models.antinuke import Configuration, Module
from lib.classes.ratelimit import ratelimiter


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self.config: Dict[int, Configuration] = dict()

    async def cog_load(self) -> None:
        self.revalidate_config.start()

    async def cog_unload(self) -> None:
        self.revalidate_config.cancel()

    def get_changes(self, entry: AuditLogEntry) -> dict:
        return {k: v for k, v in entry.changes.before.__iter__()}

    @loop(seconds=30)
    async def revalidate_config(self):
        schedule_deletion: List[int] = list()

        for row in await self.bot.db.fetch(
            """
            SELECT * FROM antinuke
            """
        ):
            guild_id: int = row.get("guild_id")
            if self.bot.get_guild(guild_id):
                self.config[guild_id] = Configuration(**row)
            else:
                schedule_deletion.append(guild_id)

        if schedule_deletion:
            await self.bot.db.executemany(
                """
                DELETE FROM antinuke
                WHERE guild_id = $1
                """,
                [(guild_id) for guild_id in schedule_deletion],
            )

    async def do_antinuke(self, entry: AuditLogEntry, module: Module):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return

        elif not module.status:
            return

        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return

    async def strip(self, user: Member, reason: str):
        roles = [r for r in user.roles if not r.is_assignable()]
        await user.edit(roles=roles, reason=reason)

    def get_object(self, guild: Guild, guild_object: Object):
        if role := guild.get_role(guild_object.id):
            return role
        elif channel := guild.get_channel(guild_object.id):
            return channel
        elif member := guild.get_member(guild_object.id):
            return member
        else:
            return None

    async def do_punishment(
        self, entry: AuditLogEntry, module: Module, configuration: Configuration
    ):
        if not configuration:
            return

        elif not module.status:
            return

        elif not (
            ratelimiter(
                bucket=f"antinuke:{str(entry.action)}:{entry.guild.id}",
                key=entry.user.id,
                rate=module.threshold,
                per=9,
            )
        ):
            return
        reason = f"antinuke: {str(entry.action)} X/{module.threshold} in 9 seconds"

        if module.punishment == "kick":
            await entry.guild.kick(entry.user, reason=reason)
        elif module.punishment == "ban":
            await entry.guild.ban(entry.user, reason=reason)
        elif module.punishment == "stripstaff":
            await self.strip(entry.user, reason)
        else:
            return

    @Cog.listener()
    async def on_audit_log_entry_ban(self, entry: AuditLogEntry) -> None:
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return

        elif not data.ban.status:
            return

        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        await entry.guild.unban(entry.target, reason="AntiNuke Ban")
        return await self.do_punishment(entry, data.ban, data)

    @Cog.listener()
    async def on_audit_log_entry_kick(self, entry: AuditLogEntry) -> None:
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return

        elif not data.kick.status:
            return

        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return

        return await self.do_punishment(entry, data.kick, data)

    @Cog.listener()
    async def on_audit_log_entry_member_role_update(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.role.status:
            return

        try:
            await entry.target.edit(roles=entry.changes.before.roles)
        except Exception:
            pass
        return await self.do_punishment(entry, data.role, data)

    @Cog.listener()
    async def on_audit_log_entry_role_update(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.role.status:
            return
        try:
            await entry.target.edit(
                **{k: v for k, v in entry.changes.before.__iter__()}
            )
        except Exception:
            pass
        return await self.do_punishment(entry, data.role, data)

    @Cog.listener()
    async def on_audit_log_entry_role_delete(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.role.status:
            return
        try:
            await entry.guild.create_role(**{k: v for k, v in entry.before.__iter__()})
        except Exception:
            pass
        return await self.do_punishment(entry, data.role, data)

    @Cog.listener()
    async def on_audit_log_entry_role_create(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.role.status:
            return
        try:
            await entry.target.delete()
        except Exception:
            pass
        return await self.do_punishment(entry, data.role, data)

    @Cog.listener()
    async def on_audit_log_entry_channel_create(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.channel.status:
            return
        try:
            await entry.target.delete(reason="Antinuke Channel")
        except Exception:
            pass
        return await self.do_punishment(entry, data.channel, data)

    @Cog.listener()
    async def on_audit_log_entry_channel_delete(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.channel.status:
            return
        kwargs = {k: v for k, v in entry.before.__iter__() if k not in ("flags")}
        if overwrites := kwargs.pop("overwrites"):
            overwrites = {
                self.get_object(entry.guild, k) if isinstance(k, Object) else k: v
                for k, v in overwrites
            }
            kwargs["overwrites"] = overwrites
        try:
            await entry.guild._create_channel(**kwargs)
        except Exception:
            pass
        return await self.do_punsihment(entry, data.channel, data)

    @Cog.listener()
    async def on_audit_log_entry_channel_update(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.channel.status:
            return
        kwargs = {
            k: v for k, v in entry.before.__iter__() if k not in ("flags", "type")
        }
        if overwrites := kwargs.pop("overwrites"):
            overwrites = {
                self.get_object(entry.guild, k) if isinstance(k, Object) else k: v
                for k, v in overwrites
            }
            kwargs["overwrites"] = overwrites
        try:
            await entry.target.edit(**kwargs)
        except Exception:
            pass
        return await self.do_punishment(entry, data.channel, data)

    @Cog.listener()
    async def on_audit_log_entry_webhook_create(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.webhook.status:
            return
        channel = entry.changes.after.channel
        try:
            if channel:
                for webhook in await channel.webhooks():
                    if webhook.id == entry.target.id:
                        await webhook.delete()
                        break
        except Exception:
            pass
        return await self.do_punishment(entry, data.webhook, data)

    @Cog.listener()
    async def on_audit_log_entry_bot_add(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.botadd.status:
            return
        await entry.target.kick(reason="Anti Bot")
        return await self.do_punishment(entry, data.botadd, data)

    @Cog.listener()
    async def on_audit_log_entry_webhook_update(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.webhook.status:
            return
        try:
            channel = entry.changes.after.channel
            if channel:
                for webhook in await channel.webhooks():
                    if webhook.id == entry.target.id:
                        await webhook.edit(**entry.changes.before.__iter__())
                        break
        except Exception:
            pass
        await self.do_punishment(entry, data.webhook, data)

    @Cog.listener()
    async def on_audit_log_entry_webhook_delete(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.role.status:
            return
        return await self.do_punishment(entry, data.webhook, data)

    @Cog.listener()
    async def on_audit_log_entry_emoji_create(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.emoji.status:
            return
        try:
            await entry.target.delete(reason="Anti Emoji Create")
        except Exception:
            pass
        return await self.do_punishment(entry, data.emoji, data)

    async def get_emoji(self, emoji_id: int) -> Optional[bytes]:
        image = None
        async with ClientSession() as session:
            async with session.get(
                f"https://cdn.discordapp.com/emojis/{emoji_id}"
            ) as response:
                if response.status == 200:
                    image = await response.read()
        return image

    @Cog.listener()
    async def on_audit_log_entry_emoji_delete(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.emoji.status:
            return
        try:
            kwargs = {k: v for k, v in entry.before.__iter__()}
            if emoji := await self.get_emoji(entry.target.id):
                kwargs["image"] = emoji
                await entry.guild.create_custom_emoji(**entry.before)
        except Exception:
            pass
        return await self.do_punishment(entry, data.emoji, data)

    @Cog.listener()
    async def on_audit_log_entry_emoji_update(self, entry: AuditLogEntry):
        data: Configuration = self.config.get(entry.guild.id)
        if not data:
            return
        elif entry.user.id in (
            data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
        ):
            return
        elif not data.emoji.status:
            return
        try:
            await entry.target.edit(**{k: v for k, v in entry.before.__iter__()})
        except Exception:
            pass

    # @Cog.listener()
    # async def on_audit_log_entry_(self, entry: AuditLogEntry):
    #     data: Configuration = self.config.get(entry.guild.id)
    #     if not data:
    #         return
    #     elif entry.user.id in (
    #         data.whitelist + data.admins + [entry.guild.owner_id, entry.guild.me.id]
    #     ):
    #         return
    #     elif not data.role.status:
    #         return
