from discord.ext.commands import Cog, CommandError
from discord import (
    Client,
    Embed,
    User,
    File,
    Member,
    Message,
    Guild,
    TextChannel,
    VoiceChannel,
    ForumChannel,
    StageChannel,
    utils,
    Invite,
    AuditLogEntry,
    AuditLogAction,
    Role,
    VoiceState,
    Webhook,
)
from asyncio import Lock, Event, Task, create_task, ensure_future, gather
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from tools import ratelimit
from typing import List, Optional, Any, Union


@dataclass
class Entry:
    channel_id: int
    event: str
    webhook_url: str
    ignored: Optional[List[int]] = None


@dataclass
class Config:
    modules: List[Entry]

    def to_data(self) -> list:
        events = []
        channel_ids = []
        webhooks = []
        for module in self.modules:
            events.append(module.event)
            channel_ids.append(module.channel_id)
            webhooks.append(module.webhook_url)
        return [events, channel_ids, webhooks, self.modules[0].ignored]


class Events(Cog):
    def __init__(self, bot: Client):
        self.bot = bot
        self.locks = defaultdict(Lock)

    async def get_config(self, guild: Guild) -> Optional[Config]:
        if not (
            data := await self.bot.db.fetchrow(
                """SELECT events, channel_ids, webhooks, ignored FROM logs WHERE guild_id = $1""",
                guild.id,
            )
        ):
            return None

        entries = []
        for i, event in enumerate(data.events, start=0):
            entries.append(
                Entry(
                    channel_id=data.channel_ids[i],
                    event=event,
                    webhook_url=data.webhooks[i],
                    ignored=data.ignored,
                )
            )
        config = Config(modules=entries)
        return config

    @ratelimit("send_log:{webhook_url}", 5, 10, True)
    async def send_log(
        self, webhook_url: str, channel: TextChannel, embed: Embed, **kwargs: Any
    ):
        async with self.locks[str(channel.guild.id)]:
            webhook = Webhook.from_url(webhook_url, client=self.bot)
            await webhook.send(embed=embed, **kwargs)

    @Cog.listener("on_message_edit")
    async def message_edits(self, before: Message, after: Message):
        if not before.guild:
            return
        if before.content == after.content:
            return
        if before.author.id == self.bot.user.id:
            return
        if before.author.bot:
            return
        if not (config := await self.get_config(before.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "messages"), None
            )
        ):
            return
        if not (channel := before.guild.get_channel(entry.channel_id)):
            return
        if entry.ignored:
            if before.channel.id in entry.ignored or before.author.id in entry.ignored:
                return
        embed = Embed(
            description=f"Message from {before.author.mention} edited {utils.format_dt(datetime.now(), style = 'R')}\n[View the message in #{before.channel.name}]({before.jump_url})"
        )
        embed.set_author(
            name="Message Edited", icon_url=before.author.display_avatar.url
        )
        embed.add_field(name="Before", value=str(before.content), inline=False)
        embed.add_field(name="After", value=str(after.content), inline=False)
        embed.set_footer(text="User ID: {message.author.id}")
        embed.timestamp = utils.utcnow()
        await self.send_log(entry.webhook_url, channel, embed)

    @Cog.listener("on_message_delete")
    async def message_delete(self, message: Message):
        if not message.guild:
            return
        if message.author.bot:
            return
        if not (config := await self.get_config(message.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "messages"), None
            )
        ):
            return
        if entry.ignored:
            if (
                message.channel.id in entry.ignored
                or message.author.id in entry.ignored
            ):
                return
        if not (channel := message.guild.get_channel(entry.channel_id)):
            return
        kwargs = {}
        embed = Embed(
            description=f"Message from {message.author.mention} deleted in {message.channel.mention}\nIt was sent at {utils.format_dt(message.created_at, style = 'F')}"
        )
        embed.set_author(
            name="Message Deleted", icon_url=message.author.display_avatar.url
        )
        if message.content:
            embed.add_field(name="Message Content", value=message.content, inline=False)
        if message.attachments:
            attachments = ""
            kwargs["files"] = []
            for i, attachment in enumerate(message.attachments, start=1):
                n = "\n" if i != 1 else ""
                attachments += f"{n}[{attachment.filename}]({attachment.url})"
                kwargs["files"].append(await attachment.to_file())
            embed.add_field(name="Attachments", value=attachments, inline=False)
        if message.stickers:
            embed.set_image(url=message.stickers[0].url)
        embed.timestamp = utils.utcnow()
        embed.set_footer(text=f"User ID: {message.author.id}")
        await self.send_log(entry.webhook_url, channel, embed, **kwargs)

    @Cog.listener("on_member_remove")
    async def member_leave(self, member: Member):
        if not member.guild:
            return
        if not (config := await self.get_config(member.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "members"), None
            )
        ):
            return
        if not (channel := member.guild.get_channel(entry.channel_id)):
            return
        embed = Embed(
            description=f"Account was created {utils.format_dt(member.created_at, style = 'F')} ({utils.format_dt(member.created_at, style = 'R')})\nJoined server on {utils.format_dt(member.joined_at, style = 'F')} ({utils.format_dt(member.joined_at, style = 'R')})"
        )
        embed.set_author(name=f"{str(member)} left", icon_url=member.display_avatar.url)
        embed.timestamp = utils.utcnow()
        embed.set_footer(text=f"User ID: {member.id}")
        await self.send_log(entry.webhook_url, channel, embed)

    @Cog.listener("on_member_join")
    async def member_join(self, member: Member):
        if not member.guild:
            return
        if not (config := await self.get_config(member.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "members"), None
            )
        ):
            return
        if not (channel := member.guild.get_channel(entry.channel_id)):
            return
        embed = Embed(
            description=f"{utils.format_dt(member.created_at, style = 'F')} ({utils.format_dt(member.created_at, style = 'R')})"
        )
        embed.set_author(
            name=f"{str(member)} joined", icon_url=member.display_avatar.url
        )
        embed.timestamp = utils.utcnow()
        embed.set_footer(text=f"User ID: {member.id}")
        await self.send_log(entry.webhook_url, channel, embed)

    @Cog.listener("on_member_role_update")
    async def roles_updated(
        self,
        member: Member,
        new_roles: Optional[List[Role]],
        old_roles: Optional[List[Role]],
        moderator: Member,
    ):
        if not member.guild:
            return
        if not (config := await self.get_config(member.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "members"), None
            )
        ):
            return
        if not (channel := member.guild.get_channel(entry.channel_id)):
            return
        granted = (
            f"{member.mention} was granted {', '.join(r.mention for r in new_roles)}"
            if new_roles
            else None
        )
        revoked = (
            f"{member.mention} was removed from {', '.join(r.mention for r in old_roles)}"
            if old_roles
            else None
        )
        entries = []
        if granted:
            entries.append(granted)
        if revoked:
            entries.append(revoked)
        embed = Embed(description="\n".join(e for e in entries))
        embed.set_author(
            name="Member Roles Updated", icon_url=member.display_avatar.url
        )
        embed.timestamp = utils.utcnow()
        embed.add_field(
            name="Moderator",
            value=f"{moderator.mention} (`{moderator.id}`)",
            inline=False,
        )
        embed.set_footer(text=f"User ID: {member.id}")
        await self.send_log(entry.webhook_url, channel, embed)

    @Cog.listener("on_invite_create")
    async def invite_created(self, invite: Invite):
        if not (config := await self.get_config(invite.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "invites"), None
            )
        ):
            return
        if not (channel := invite.guild.get_channel(entry.channel_id)):
            return

        if entry.ignored:
            if invite.channel.id in entry.ignored:
                return
            if invite.inviter.id in entry.ignored:
                return
        embed = Embed(
            description=f"New Invite [`{invite.code}`]({invite.url}) created by {invite.inviter.mention}"
        )
        embed.set_footer(text=f"User ID: {invite.inviter.id}")
        embed.timestamp = utils.utcnow()
        embed.set_author(
            name="Invite Created", icon_url=invite.inviter.display_avatar.url
        )
        await self.send_log(entry.webhook_url, channel, embed)

    @Cog.listener("on_invite_deleted")
    async def invite_deleted(self, invite: Invite, deleter: Member):
        if not (config := await self.get_config(invite.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "invites"), None
            )
        ):
            return
        if not (channel := invite.guild.get_channel(entry.channel_id)):
            return
        if entry.ignored:
            if deleter.id in entry.ignored:
                return
        embed = Embed(
            description=f"Invite [`{invite.code}`]({invite.url}) deleted by {deleter.mention}"
        )
        embed.set_footer(text=f"User ID: {deleter.id}")
        embed.timestamp = utils.utcnow()
        embed.set_author(name="Invite Deleted", icon_url=deleter.display_avatar.url)
        await self.send_log(entry.webhook_url, channel, embed)

    @Cog.listener("on_role_create")
    async def role_created(self, role: Role, member: Member):
        if not (config := await self.get_config(member.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "roles"), None
            )
        ):
            return
        if not (channel := member.guild.get_channel(entry.channel_id)):
            return
        if entry.ignored:
            if member in entry.ignored:
                return
        embed = Embed(description=f"Role {role.mention} created by {member.mention}")
        embed.set_author(name="Role Created", icon_url=member.display_avatar.url)
        embed.add_field(name="Name", value=role.name, inline=False)
        embed.add_field(
            name="Color",
            value=f"`#{str(role.color.value)}`".replace("##", "#"),
            inline=False,
        )
        embed.set_footer(text=f"User ID: {member.id}")
        embed.timestamp = utils.utcnow()
        await self.send_log(entry.webhook_url, channel, embed)

    @Cog.listener("on_channel_create")
    async def channel_created(
        self,
        channel: Union[TextChannel, VoiceChannel, StageChannel, ForumChannel],
        member: Member,
    ):
        if not member.guild:
            return
        if not (config := await self.get_config(member.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "channels"), None
            )
        ):
            return
        if not (log_channel := member.guild.get_channel(entry.channel_id)):
            return
        if entry.ignored:
            if member in entry.ignored:
                return
        embed = Embed(
            description=f"{str(channel.type).title()} Channel {channel.mention} created by {member.mention}"
        )
        embed.set_author(name="Channel Created", icon_url=member.display_avatar.url)
        embed.set_footer(text=f"User ID: {member.id}")
        embed.timestamp = utils.utcnow()
        await self.send_log(entry.webhook_url, log_channel, embed)

    @Cog.listener("on_audit_log_entry_create")
    async def audit_log_parser(self, log: AuditLogEntry):
        if not (config := await self.get_config(log.guild)):
            return

        async def invite_deleted():
            if log.action != AuditLogAction.invite_delete:
                return
            member = log.guild.get_member(log.user.id)
            self.bot.dispatch("invite_deleted", log.target, member)

        async def member_role_update():
            if log.action != AuditLogAction.member_role_update:
                new_roles = [
                    r for r in log.changes.after if r not in log.changes.before
                ]
                old_roles = roles = [
                    r for r in log.changes.before if r not in log.changes.after
                ]
                if not new_roles and not old_roles:
                    return
                member = log.guild.get_member(log.user.id)
                self.bot.dispatch(
                    "member_role_update", log.target, new_roles, old_roles, member
                )

        async def role_create():
            if log.action != AuditLogAction.role_create:
                return
            member = log.guild.get_member(log.user.id)
            self.bot.dispatch("role_create", log.target, member)

        async def channel_create():
            if log.action != AuditLogAction.channel_create:
                return
            member = log.guild.get_member(log.user.id)
            self.bot.dispatch("channel_create", log.target, member)

        async def channel_delete():
            if log.action != AuditLogAction.channel_delete:
                return

            member = log.guild.get_member(log.user.id)
            self.bot.dispatch("channel_delete", log.target, member)

        tasks = [
            invite_deleted(),
            member_role_update(),
            role_create(),
            channel_create(),
            channel_delete(),
        ]
        await gather(*tasks)

    @Cog.listener("on_voice_state_update")
    async def voice_logs(self, member: Member, before: VoiceState, after: VoiceState):
        if not (config := await self.get_config(member.guild)):
            return
        if not (
            entry := next(
                (entry for entry in config.modules if entry.event == "voice"), None
            )
        ):
            return
        if not (channel := member.guild.get_channel(entry.channel_id)):
            return
        current_channel = None
        description = None
        if not before.channel and after.channel:
            description = f"{member.mention} joined **{str(after.channel)}**"
            current_channel = after.channel
        elif before.channel and not after.channel:
            description = f"{member.mention} left **{str(before.channel)}**"
        elif before.channel and after.channel:
            if before.channel.id != after.channel.id:
                description = f"{member.mention} moved from **{str(before.channel)}** to **{str(after.channel)}**"
                current_channel = after.channel
            else:
                if not before.mute and after.mute:
                    description = f"{member.mention} was muted by a moderator"
                elif not before.deaf and after.deaf:
                    description = f"{member.mention} was deafened by a moderator"
                elif before.mute and not after.mute:
                    description = f"{member.mention} was unmuted by a moderator"
                elif before.deaf and not after.deaf:
                    description = f"{member.mention} was undeafened by a moderator"
                current_channel = before.channel

        if entry.ignored:
            if before.channel:
                if before.channel.id in entry.ignored:
                    return
            elif after.channel:
                if after.channel.id in entry.ignored:
                    return
            if member.id in entry.ignored:
                return
        if description:
            embed = Embed(description=description)
            if current_channel:
                embed.add_field(
                    name="Current Channel", value=channel.mention, inline=False
                )
            embed.set_author(
                name="Voice State Updated", icon_url=member.display_avatar.url
            )
            embed.set_footer(text=f"User ID: {member.id}")
            embed.timestamp = utils.utcnow()
            await self.send_log(entry.webhook_url, channel, embed)
