from discord.ext.commands import Cog, command, group, CommandError, has_permissions
from lib.patch.context import Context
from discord import (
    Client,
    Embed,
    File,
    RawReactionActionEvent,
    Message,
    AllowedMentions,
    Member,
    User,
    TextChannel,
    Guild,
)
from datetime import datetime, timedelta
from asyncio import sleep, Lock, ensure_future, gather
from lib.classes.database import Record
from lib.classes.embed import Script
from collections import defaultdict

import re

MUSIC_CONTENT_TYPES = [
    # Lossy Formats
    "audio/mpeg",  # MP3
    "audio/aac",  # AAC
    "audio/x-aac",  # AAC (alternative MIME)
    "audio/ogg",  # OGG (Ogg Vorbis)
    "audio/x-ms-wma",  # WMA
    "audio/amr",  # AMR
    # Lossless Formats
    "audio/flac",  # FLAC
    "audio/alac",  # ALAC
    "audio/x-alac",  # ALAC (alternative MIME)
    "audio/ape",  # APE (Monkey's Audio)
    "audio/wavpack",  # WavPack
    # Uncompressed Formats
    "audio/wav",  # WAV
    "audio/x-wav",  # WAV (alternative MIME)
    "audio/aiff",  # AIFF
    "audio/x-aiff",  # AIFF (alternative MIME)
    # Streaming and Specialized Formats
    "audio/midi",  # MIDI
    "audio/x-midi",  # MIDI (alternative MIME)
    "audio/opus",  # Opus
    "audio/vnd.rn-realaudio",  # RealAudio
    "audio/mod",  # MOD (Tracker Music Format)
    "audio/s3m",  # S3M (Scream Tracker 3 Module)
    # Container Formats with Audio Tracks
    "audio/mp4",  # MP4 (Audio in MP4)
    "audio/x-m4a",  # MP4 (alternative MIME)
    "audio/x-matroska",  # MKV (Matroska Audio)
    "audio/3gpp",  # 3GP (Audio in 3GPP)
]


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self.locks = defaultdict(Lock)
        self.last_messages = {}
        self.link_regex = r"(http|ftp|https):\/\/(?!open\.spotify\.com|tenor\.com)([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])"

    async def ping_on_join(self, member: Member):
        if not (
            channel_ids := await self.bot.db.fetchval(
                """SELECT channel_ids FROM pingonjoin WHERE guild_id = $1""",
                member.guild.id,
            )
        ):
            return
        for channel_id in channel_ids:
            if not (channel := member.guild.get_channel(channel_id)):
                continue
            await channel.send(
                f"{member.mention}", allowed_mentions=AllowedMentions(users=True)
            )

    @Cog.listener("on_member_agree")
    async def send_join_message(self, member: Member) -> None:
        if (
            await self.bot.object_cache.ratelimited(
                f"welcome_messages:{member.guild.id}", 1, 5
            )
            != 0
        ):
            await sleep(5)
        async with self.locks[f"welcome_messages:{member.guild.id}"]:
            await self.ping_on_join(member)
            for row in await self.bot.db.fetch(
                """
                SELECT * FROM join_messages
                WHERE guild_id = $1;
                """,
                member.guild.id,
            ):
                channel: TextChannel
                if not (channel := member.guild.get_channel(row["channel_id"])):
                    continue
                builder = await self.create_embed(
                    row.message, member=member, user=member
                )
                if row.delete_after:
                    builder.data["delete_after"] = row.delete_after
                try:
                    return await builder.send(channel)
                except Exception:
                    pass

    @Cog.listener("on_member_remove")
    async def send_leave_message(self, member: Member) -> None:
        if (
            await self.bot.object_cache.ratelimited(
                f"leave_messages:{member.guild.id}", 1, 5
            )
            != 0
        ):
            await sleep(5)
        async with self.locks[f"leave_messages:{member.guild.id}"]:
            for row in await self.bot.db.fetch(
                """
                SELECT * FROM leave_messages
                WHERE guild_id = $1;
                """,
                member.guild.id,
            ):
                channel: TextChannel
                if not (channel := member.guild.get_channel(row["channel_id"])):
                    continue

                builder = await self.create_embed(
                    row.message, member=member, user=member
                )
                if row.delete_after:
                    builder.data["delete_after"] = row.delete_after
                try:
                    return await builder.send(channel)
                except Exception:
                    pass

    @Cog.listener("on_member_boost")
    async def send_boost_message(self, member: Member) -> None:
        for row in await self.bot.db.fetch(
            """
            SELECT * FROM boost_messages
            WHERE guild_id = $1;
            """,
            member.guild.id,
        ):
            channel: TextChannel
            if not (channel := member.guild.get_channel(row["channel_id"])):
                continue

            builder = await self.create_embed(row.message, member=member, user=member)
            if row.delete_after:
                builder.data["delete_after"] = row.delete_after
            try:
                return await builder.send(channel)
            except Exception:
                pass

        if not (
            role_id := await self.bot.db.fetchval(
                """SELECT award_id FROM booster_roles WHERE guild_id = $1""",
                member.guild.id,
            )
        ):
            return
        if not (role := member.guild.get_role(role_id)):
            return
        await member.add_roles(role, reason="Member boosted the server")

    async def filter_message(self, ctx: Context):
        block = False
        message = ctx.message

        async def punish(punishment: str, reason: str):
            if punishment == "mute":
                if message.author.is_bannable:
                    await message.author.timeout(timedelta(seconds=60), reason=reason)
            elif punishment == "delete":
                await message.delete()
            else:
                await message.delete()

        async def mentions():
            nonlocal block
            async with self.locks[str(message.id)]:
                if not (
                    config := await self.bot.db.fetchrow(
                        """SELECT channel_ids, threshold, exempt_roles, action FROM moderation.mention WHERE guild_id = $1""",
                        message.guild.id,
                    )
                ):
                    return
                if not message.channel.id in config.channel_ids:
                    return
                if len(message.mentions) >= config.threshold and not any(
                    role.id in config.exempt_roles for role in message.author.roles
                ):
                    block = True
                    return await punish(config.action, "Mass Mention")

        async def musicfiles():
            nonlocal block
            async with self.locks[str(message.id)]:
                if block:
                    return
                if not (
                    config := await self.bot.db.fetchrow(
                        """SELECT channel_ids, exempt_roles, action FROM moderation.music WHERE guild_id = $1""",
                        message.guild.id,
                    )
                ):
                    return
                if message.channel.id not in config.channel_ids:
                    return
                for attachment in message.attachments:
                    if attachment.content_type in MUSIC_CONTENT_TYPES and not any(
                        role.id in config.exempt_roles for role in message.author.roles
                    ):
                        block = True
                        return await punish(config.action, "Music File")

        async def caps():
            nonlocal block
            async with self.locks[str(message.id)]:
                if block:
                    return
                if not (
                    config := await self.bot.db.fetchrow(
                        """SELECT channel_ids, exempt_roles, threshold, action FROM moderation.caps WHERE guild_id = $1""",
                        message.guild.id,
                    )
                ):
                    return
                if message.channel.id not in config.channel_ids:
                    return
                if len(
                    m for m in message.content if m.isupper()
                ) >= config.threshold and not any(
                    role.id in config.exempt_roles for role in message.author.roles
                ):
                    block = True
                    return await punish(config.action, "Caps")

        async def invites():
            nonlocal block
            async with self.locks[str(message.id)]:
                if block:
                    return
                if not (
                    config := await self.bot.db.fetchrow(
                        """SELECT channel_ids, exempt_roles, whitelist, action FROM moderation.invites WHERE guild_id = $1""",
                        ctx.guild.id,
                    )
                ):
                    return
                if message.channel.id not in config.channel_ids:
                    return
                if any(role.id in config.exempt_roles for role in message.author.roles):
                    return
                if any(
                    invite.split("/")[-1] not in config.whitelist
                    for invite in message.invites
                ):
                    block = True
                    return await punish(config.action, "Invite")

        async def spoilers():
            nonlocal block
            async with self.locks[str(message.id)]:
                if block:
                    return
                if not (
                    config := await self.bot.db.fetchrow(
                        """SELECT channel_ids, exempt_roles, threshold, action FROM moderation.spoilers WHERE guild_id = $1""",
                        message.guild.id,
                    )
                ):
                    return
                if message.channel.id not in config.channel_ids:
                    return
                if any(role.id in config.exempt_roles for role in message.author.roles):
                    return
                count = message.content.count("||")
                if count > 1 and count / 2 > config.threshold:
                    block = True
                    return await punish(config.action, "Spoilers")

        async def links():
            nonlocal block
            async with self.locks[str(message.id)]:
                if block:
                    return
                if not (
                    config := await self.bot.db.fetchrow(
                        """SELECT channel_ids, exempt_roles, whitelist, action FROM moderation.links WHERE guild_id = $1""",
                        ctx.guild.id,
                    )
                ):
                    return
                if message.channel.id not in config.channel_ids:
                    return
                if any(role.id in config.exempt_roles for role in message.author.roles):
                    return

                for match in re.finditer(self.link_regex, message.content):
                    if match.group(2).lower() not in config.whitelist:
                        block = True
                        return await punish(config.action, "Link")

        async def emojis():
            nonlocal block
            async with self.locks[str(message.id)]:
                if block:
                    return
                if not (
                    config := await self.bot.db.fetchrow(
                        """SELECT channel_ids, exempt_roles, threshold, action FROM moderation.emoji WHERE guild_id = $1""",
                        message.guild.id,
                    )
                ):
                    return
                if message.channel.id not in config.channel_ids:
                    return
                if any(role.id in config.exempt_roles for role in message.author.roles):
                    return
                if len(message.emojis) >= config.threshold:
                    block = True
                    return await punish(config.action, "Emojis")

        async def regex():
            nonlocal block
            async with self.locks[str(message.id)]:
                if block:
                    return
                if not (
                    rows := await self.bot.db.fetch(
                        """SELECT regex, action FROM moderation.regex WHERE guild_id = $1""",
                        ctx.guild.id,
                    )
                ):
                    return
                whitelist = (
                    await self.bot.db.fetchval(
                        """SELECT exempt_roles FROM moderation.regex_exempt WHERE guild_id = $1""",
                        ctx.guild.id,
                    )
                    or []
                )
                if any(role.id in whitelist for role in message.author.roles):
                    return
                for row in rows:
                    for match in re.finditer(row.regex, message.content):
                        block = True
                        return await punish(row.action, "Regex")

        await gather(
            *[
                mentions(),
                musicfiles(),
                caps(),
                invites(),
                spoilers(),
                links(),
                emojis(),
                regex(),
            ]
        )
        return block

    @Cog.listener("on_valid_message")
    async def on_sticky_message(self, ctx: Context):
        async with self.locks[f"sticky_message:{ctx.channel.id}"]:
            if not (
                config := await self.bot.db.fetchrow(
                    """SELECT code, last_message FROM sticky_message WHERE guild_id = $1 AND channel_id = $2""",
                    ctx.guild.id,
                    ctx.channel.id,
                )
            ):
                return
            if last_message_id := self.last_messages.get(ctx.channel.id):
                try:
                    msg = await self.bot.http.delete_message(
                        ctx.channel.id, last_message_id
                    )
                except Exception:
                    pass
            elif config.last_message:
                try:
                    msg = await self.bot.http.delete_message(
                        ctx.channel.id, config.last_message
                    )
                except Exception:
                    pass
            message = await self.bot.send_embed(
                ctx.channel, config.code, user=ctx.author
            )
            await self.bot.db.execute(
                """UPDATE sticky_message SET last_message = $1 WHERE guild_id = $2 AND channel_id = $3""",
                message.id,
                ctx.guild.id,
                ctx.channel.id,
            )
            self.last_messages[message.channel.id] = message.id

    async def send_response(self, ctx: Context, record: Record):
        if (
            await self.bot.object_cache.ratelimited(
                f"auto_responder:{ctx.guild.id}", 1, 5
            )
            != 0
        ):
            await sleep(5)
        # command checks
        if not record.ignore_command_checks:
            if ctx.valid:
                return

        role_ids = [r.id for r in ctx.author.roles]
        matches = list(set(role_ids) & set(record.denied_role_ids))

        # ignored role ID check
        if matches:
            return

        channel_matches = list(set([ctx.channel.id]) & set(record.denied_channel_ids))

        # ignored channel ID check
        if channel_matches:
            return

        if record.reply:
            kwargs = {"reference": ctx.message}
        else:
            kwargs = {}
        return await ctx.send(
            record.response, delete_after=record.self_destruct, **kwargs
        )

    @Cog.listener("on_context")
    async def on_auto_responder(self, ctx: Context):
        if await self.filter_message(ctx):
            return
        async with self.locks[f"auto_responder:{ctx.channel.id}"]:
            if not (
                data := await self.bot.db.fetch(
                    """SELECT * FROM auto_responders WHERE guild_id = $1""",
                    ctx.guild.id,
                )
            ):
                return
            for record in data:
                if (
                    not record.strict
                    and record.trigger.lower() in ctx.message.content.lower()
                ):
                    await self.send_response(ctx, record)
                elif (
                    record.strict
                    and record.trigger.lower() in ctx.message.content.lower().split(" ")
                ):
                    await self.send_response(ctx, record)

    @Cog.listener("on_vanity_change")
    async def vanity_tracker(self, vanity: str):
        async def emit_vanity_change(guild: Guild, vanity: str, channel_ids: list):
            if len(channel_ids) == 0:
                return
            for channel_id in channel_ids:
                if not (channel := guild.get_channel(channel_id)):
                    continue
                await channel.send(content=f"**/{vanity}** is now available")

        if not (
            trackers := await self.bot.db.fetch(
                """SELECT guild_id, channel_ids FROM trackers WHERE tracker_type = $1""",
                "vanity",
            )
        ):
            return
        for tracker in trackers:
            if not (guild := self.bot.get_guild(tracker.guild_id)):
                continue
            if not tracker.channel_ids:
                continue
            ensure_future(emit_vanity_change(guild, vanity, tracker.channel_ids))

    @Cog.listener("on_username_change")
    async def username_tracker(self, username: str):
        async def emit_username_change(guild: Guild, username: str, channel_ids: list):
            if len(channel_ids) == 0:
                return
            for channel_id in channel_ids:
                if not (channel := guild.get_channel(channel_id)):
                    continue
                await channel.send(content=f"**{username}** is now available")

        if not (
            trackers := await self.bot.db.fetch(
                """SELECT guild_id, channel_ids FROM trackers WHERE tracker_type = $1""",
                "username",
            )
        ):
            return
        for tracker in trackers:
            if not (guild := self.bot.get_guild(tracker.guild_id)):
                continue
            if not tracker.channel_ids:
                continue
            ensure_future(emit_username_change(guild, username, tracker.channel_ids))

    @Cog.listener("on_raw_reaction_add")
    async def check_paginator_update(self, payload: RawReactionActionEvent):
        if payload.user_id == self.bot.user.id:
            return
        if not payload.guild_id:
            return
        if not (guild := self.bot.get_guild(payload.guild_id)):
            return
        if not (channel := guild.get_channel(payload.channel_id)):
            return
        if not (
            paginator := await self.bot.db.fetchrow(
                """SELECT * FROM pagination WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3""",
                payload.guild_id,
                payload.channel_id,
                payload.message_id,
            )
        ):
            return
        message = await channel.fetch_message(payload.message_id)
        self.bot.dispatch(
            "paginator_update", message, paginator, paginator.current_page + 1
        )

    @Cog.listener("on_paginator_update")
    async def emit_paginator_update(
        self, message: Message, paginator: Record, page: int
    ):
        if not (channel := message.channel):
            return
        if page >= len(paginator.pages):
            page = 0

        try:
            page = page - 1 if page > 0 else page
            script = Script(paginator.pages[page], self.bot.user)
            await self.bot.db.execute(
                """UPDATE pagination SET current_page = $1 WHERE guild_id = $2 AND channel_id = $3 AND message_id = $4""",
                page,
                message.guild.id,
                message.channel.id,
                message.id,
            )
            embed = await script.data(True)
            await message.edit(**embed)
            for reaction in message.reactions:
                reactions = [
                    a async for a in reaction.users() if a.id != self.bot.user.id
                ]
                if len(reactions) > 0:
                    for user in reactions:
                        await reaction.remove(user)
        except Exception:
            pass
