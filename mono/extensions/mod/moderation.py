# Standard library imports
import asyncio
import re
from base64 import b64encode
from contextlib import suppress
from datetime import datetime, timedelta
from enum import Enum
from io import BytesIO
from mimetypes import guess_type
from textwrap import wrap
from time import perf_counter
from typing import Annotated, Callable, List, Literal, Optional, cast
from zipfile import ZipFile

# Local imports
import config
from core.client.context import Context
from core.client.database import Record
from core.managers.script import EmbedScript
from core.Mono import Mono
from core.tools import (aenumerate, codeblock, convert_image, enlarge_emoji,
                        human_join, is_dangerous, plural, quietly_delete,
                        strip_roles, unicode_emoji, url_to_mime)
from core.tools.converters import (Duration, Error, StrictMember, StrictRole,
                                   StrictUser, TouchableMember)
from core.tools.converters.basic import Attachment, Sound
from core.tools.converters.kayo import PartialAttachment
from core.tools.logging import logger as log
# Third-party library imports
from discord import (AuditLogAction, AuditLogEntry, Color, Embed, Emoji, File,
                     Forbidden, Guild, GuildSticker, HTTPException, Member,
                     Message, NotFound, NotificationLevel, Object,
                     PartialEmoji, PermissionOverwrite, RateLimited, Role,
                     StageChannel, TextChannel, Thread, User, VoiceChannel,
                     utils)
from discord.abc import GuildChannel
from discord.ext.commands import (BadArgument, BucketType, Cog, CommandError,
                                  Greedy, MaxConcurrency, Range, check,
                                  command, cooldown, group, has_permissions,
                                  max_concurrency, parameter)
from discord.http import Route
from discord.utils import MISSING, format_dt, get, utcnow
# Module imports
from extensions.mod.extended.antinuke.antinuke import Settings
from extensions.mod.extended.logging.enums import LogType
from humanfriendly import format_timespan
from humanize import precisedelta
from typing_extensions import Self, Type
from xxhash import xxh64_hexdigest

from .extended import Extended

MASS_ROLE_CONCURRENCY = MaxConcurrency(1, per=BucketType.guild, wait=False)


class Action(Enum):
    UNKNOWN = 0
    KICK = 1
    BAN = 2
    HACKBAN = 3
    SOFTBAN = 4
    UNBAN = 5
    TIMEOUT = 6
    UNTIMEOUT = 7
    JAIL = 8
    UNJAIL = 9

    def __int__(self: "Action") -> int:
        return self.value

    def __str__(self: "Action") -> str:
        if self == Action.KICK:
            return "Kicked"

        elif self == Action.BAN:
            return "Banned"

        elif self == Action.HACKBAN:
            return "Hack Banned"

        elif self == Action.SOFTBAN:
            return "Soft Banned"

        elif self == Action.UNBAN:
            return "Unbanned"

        elif self == Action.TIMEOUT:
            return "Timed Out"

        elif self == Action.UNTIMEOUT:
            return "Timeout Lifted"

        elif self == Action.JAIL:
            return "Jailed"

        elif self == Action.UNJAIL:
            return "Unjailed"

        else:
            return "Unknown"


class Case:
    def __init__(self: "Case", case: Record, bot: Mono):
        self.bot: Mono = bot
        self.id: int = case.id
        self.guild_id: int = case.guild_id
        self.target_id: int = case.target_id
        self.moderator_id: int = case.moderator_id
        self.message_id: Optional[int] = case.message_id
        self.reason: str = case.reason
        self.action: Action = Action(case.action)
        self.action_expiration: Optional[datetime] = case.action_expiration
        self.action_processed: bool = case.action_processed
        self.created_at: datetime = case.created_at
        self.updated_at: Optional[datetime] = case.updated_at

    async def channel(self: "Case") -> Optional[TextChannel]:
        if channel_id := await self.bot.db.fetchval(
            """
                SELECT mod_log_channel_id
                FROM settings
                WHERE guild_id = $1
                """,
            self.guild_id,
        ):
            return self.bot.get_channel(channel_id)  # type: ignore

    async def embed(self: "Case") -> Embed:
        target = self.bot.get_user(self.target_id) or await self.bot.fetch_user(
            self.target_id
        )
        moderator = self.bot.get_user(self.moderator_id) or await self.bot.fetch_user(
            self.moderator_id
        )

        embed = Embed(color=config.Color.base)
        embed.set_author(
            name=f"Case #{self.id} | {self.action}",
            icon_url=moderator.display_avatar,
        )

        information = (
            f"{format_dt(self.created_at)} ({format_dt(self.created_at, 'R')})\n>>> "
            f"**Target:** {target.mention} (`{target.id}`)\n"
            f"**Moderator:** {moderator.mention} (`{moderator.id}`)\n"
        )

        if self.action_expiration:
            information += f"**Expiration:** {format_dt(self.action_expiration)} ({format_dt(self.action_expiration, 'R')})\n"

        if self.updated_at:
            information += f"**Updated:** {format_dt(self.updated_at)} ({format_dt(self.updated_at, 'R')})\n"

        if self.reason:
            information += f"**Reason:** {self.reason}\n"

        embed.description = information

        return embed

    async def send(self: "Case") -> Optional[Message]:
        channel = await self.channel()
        if not channel:
            return

        embed = await self.embed()
        try:
            message = await channel.send(embed=embed)
        except Forbidden:
            await self.bot.db.execute(
                """
                UPDATE settings
                SET mod_log_channel_id = NULL
                WHERE guild_id = $1
                """,
                self.guild_id,
            )
            return
        except HTTPException:
            return

        await self.bot.db.execute(
            """
            UPDATE cases
            SET message_id = $3
            WHERE guild_id = $1
            AND id = $2
            """,
            self.guild_id,
            self.id,
            message.id,
        )
        return message

    @classmethod
    async def convert(cls: Type[Self], ctx: Context, argument: str) -> Self:
        if not (match := re.match(r"^#?(\d+)$", argument)):
            raise Error("You must provide a valid case ID, example: `#27`.")

        case_id = int(match[1])
        case = await ctx.bot.db.fetchrow(
            """
            SELECT *
            FROM cases
            WHERE guild_id = $1
            AND id = $2
            """,
            ctx.guild.id,
            case_id,
        )
        if not case:
            raise Error(f"Case ID `#{case_id}` does not exist!")

        return cls(case, ctx.bot)

    def __repr__(self) -> str:
        return f"<Case id={self.id} action={self.action.name} reason={self.reason!r}>"


class Moderation(Extended, Cog):
    def __init__(self, bot: Mono):
        self.bot = bot

    @property
    def actions(self) -> dict[str, str]:
        return {
            "guild_update": "updated server",
            "channel_create": "created channel",
            "channel_update": "updated channel",
            "channel_delete": "deleted channel",
            "overwrite_create": "created channel permission in",
            "overwrite_update": "updated channel permission in",
            "overwrite_delete": "deleted channel permission in",
            "kick": "kicked member",
            "member_prune": "pruned members in",
            "ban": "banned member",
            "hardban": "hard banned member",
            "unban": "unbanned member",
            "member_update": "updated member",
            "member_role_update": "updated member roles for",
            "member_disconnect": "disconnected member",
            "member_move": "moved member",
            "bot_add": "added bot",
            "role_create": "created role",
            "role_update": "updated role",
            "role_delete": "deleted role",
            "invite_create": "created invite",
            "invite_update": "updated invite",
            "invite_delete": "deleted invite",
            "webhook_create": "created webhook",
            "webhook_update": "updated webhook",
            "webhook_delete": "deleted webhook",
            "emoji_create": "created emoji",
            "emoji_update": "updated emoji",
            "emoji_delete": "deleted emoji",
            "message_delete": "deleted message by",
            "message_bulk_delete": "bulk deleted messages in",
            "message_pin": "pinned message by",
            "message_unpin": "unpinned message by",
            "integration_create": "created integration",
            "integration_update": "updated integration",
            "integration_delete": "deleted integration",
            "sticker_create": "created sticker",
            "sticker_update": "updated sticker",
            "sticker_delete": "deleted sticker",
            "thread_create": "created thread",
            "thread_update": "updated thread",
            "thread_delete": "deleted thread",
        }

    async def reconfigure_settings(
        self,
        guild: Guild,
        channel: TextChannel | Thread,
        new_channel: TextChannel | Thread,
    ) -> List[str]:
        """
        Update server wide settings for a channel.
        """

        reconfigured: List[str] = []
        config_map = {
            "System Channel": "system_channel",
            "Public Updates Channel": "public_updates_channel",
            "Rules Channel": "rules_channel",
            "AFK Channel": "afk_channel",
        }
        for name, attr in config_map.items():
            value = getattr(channel.guild, attr, None)
            if value == channel:
                await guild.edit(**{attr: new_channel})  # type: ignore
                reconfigured.append(name)

        for table in (
            "logging",
            "gallery",
            "timer.message",
            "timer.purge",
            "sticky_message",
            "welcome_message",
            "goodbye_message",
            "boost_message",
            ("disboard.config", "last_channel_id"),
            "level.notification",
            "commands.disabled",
            "fortnite.rotation",
            "feeds.youtube",
            "alerts.twitch",
            "feeds.twitter",
            "feeds.tiktok",
            "feeds.pinterest",
            "feeds.reddit",
            "feeds.instagram",
            "feeds.twitter",
        ):
            table_name = table if isinstance(table, str) else table[0]
            column = "channel_id" if isinstance(table, str) else table[1]
            result = await self.bot.db.execute(
                f"""
                UPDATE {table_name}
                SET {column} = $2
                WHERE {column} = $1
                """,
                channel.id,
                new_channel.id,
            )
            if result != "UPDATE 0":
                pretty_name = (
                    table_name.replace("_", " ")
                    .replace(".", " ")
                    .title()
                    .replace("Feeds Youtube", "YouTube Notifications")
                    .replace("Alerts Twitch", "Twitch Notifications")
                    .replace("Feeds Twitter", "Twitter Notifications")
                    .replace("Feeds Tiktok", "TikTok Notifications")
                    .replace("Feeds Pinterest", "Pinterest Notifications")
                    .replace("Feeds Reddit", "Subreddit Notifications")
                    .replace("Feeds Twitter", "Twitter Notifications")
                    .replace("Feeds Instagram", "Instagram Notifications")
                )
                reconfigured.append(pretty_name)

        return reconfigured

    def hardban_key(self, guild: Guild) -> str:
        return xxh64_hexdigest(f"hardban:{guild.id}")

    def restore_key(self, guild: Guild, member: Member) -> str:
        return xxh64_hexdigest(f"roles:{guild.id}:{member.id}")

    def forcenick_key(self, guild: Guild, member: Member) -> str:
        return xxh64_hexdigest(f"forcenick:{guild.id}:{member.id}")

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        if (
            not message.guild
            or message.guild.id != 1128849931269062688
            or not isinstance(message.channel, TextChannel)
            or not isinstance(message.author, Member)
            or message.author.guild_permissions.administrator
        ):
            return

        if not await self.bot.redis.ratelimited(f"deletion:{message.author.id}", 5, 30):
            return

        channel = message.channel

        overwrite = channel.overwrites_for(message.author)
        overwrite.view_channel = False
        await channel.set_permissions(
            message.author,
            overwrite=overwrite,
        )
        await channel.send(f"{message.author.mention} was purging")

    @Cog.listener()
    async def on_member_remove(self, member: Member):
        if member.bot:
            return

        role_ids = [r.id for r in member.roles if r.is_assignable()]
        if role_ids:
            key = self.restore_key(member.guild, member)
            await self.bot.redis.set(key, role_ids, ex=3600)

    @Cog.listener("on_member_remove")
    async def store_roles_on_leave(self, member: Member):
        """
        Listener to store roles when a member leaves the guild.
        """
        for role in member.roles:
            if role.is_assignable():
                await self.bot.db.execute(
                    """
                    INSERT INTO member_roles (guild_id, member_id, role_id)
                    VALUES ($1, $2, $3)
                    ON CONFLICT DO NOTHING
                    """,
                    member.guild.id,
                    member.id,
                    role.id,
                )

    @Cog.listener("on_member_join")
    async def restore_roles_on_join(self, member: Member):
        """
        Listener to restore roles when a member rejoins if the feature is enabled.
        """
        # Fetch the setting to check if auto reassign is enabled
        record = await self.bot.db.fetchrow(
            """
            SELECT
                reassign_roles,
                reassign_ignore_ids
            FROM settings
            WHERE guild_id = $1
            """,
            member.guild.id,
        )

        # If the feature is not enabled, return early
        if not record or not record["reassign_roles"]:
            return

        # Retrieve stored roles for the member from the database
        role_ids = await self.bot.db.fetch(
            """
            SELECT role_id
            FROM member_roles
            WHERE guild_id = $1 AND member_id = $2
            """,
            member.guild.id,
            member.id,
        )

        if not role_ids:
            return  # No roles to restore

        # Filter roles that are assignable, not already assigned, not ignored, and not dangerous
        roles = [
            member.guild.get_role(role_id["role_id"])
            for role_id in role_ids
            if (role := member.guild.get_role(role_id["role_id"])) is not None
            and role.is_assignable()
            and role not in member.roles
            and role.id not in record.get("reassign_ignore_ids", [])
            and not is_dangerous(role)
        ]

        if roles:
            # Optionally, clean up the roles after reassignment
            await self.bot.db.execute(
                """
                DELETE FROM member_roles
                WHERE guild_id = $1 AND member_id = $2
                """,
                member.guild.id,
                member.id,
            )
            with suppress(HTTPException):
                await member.add_roles(*roles, reason="Auto-reassigned roles on rejoin")
                log.info(
                    "Restored %s for %s (%s) in %s (%s).",
                    format(plural(len(roles)), "role"),
                    member,
                    member.id,
                    member.guild,
                    member.guild.id,
                )

    @Cog.listener("on_member_join")
    async def hardban_event(self, member: Member):
        key = self.hardban_key(member.guild)
        if not await self.bot.redis.sismember(key, str(member.id)):
            return

        with suppress(HTTPException):
            await member.ban(reason="User is hard banned")

    @Cog.listener("on_member_update")
    async def forcenick_event(self, before: Member, after: Member):
        key = self.forcenick_key(before.guild, before)
        nickname = cast(
            Optional[str],
            await self.bot.redis.get(key),
        )

        if not nickname:
            return

        if nickname == after.display_name:
            return

        if await self.bot.redis.ratelimited(
            f"nick:{key}",
            limit=8,
            timespan=15,
        ):
            log.warning(
                "Ratelimit reached for forcenick on %s in %s (%s). Removing forcenick.",
                after,
                after.guild,
                after.guild.id,
            )
            await self.bot.redis.delete(key)
            return

        try:
            await after.edit(nick=nickname, reason="Forced nickname")
            log.info(
                "Set forced nickname for %s to %r in %s (%s).",
                after,
                nickname,
                after.guild,
                after.guild.id,
            )
        except HTTPException as e:
            log.error(
                "Failed to set forced nickname for %s in %s (%s): %s",
                after,
                after.guild,
                after.guild.id,
                str(e),
            )
            if "Cannot edit a guild owner" in str(e):
                await self.bot.redis.delete(key)
                log.info(
                    "Removed forcenick for guild owner %s in %s (%s).",
                    after,
                    after.guild,
                    after.guild.id,
                )

    @Cog.listener("on_audit_log_entry_member_update")
    async def forcenick_audit(self, entry: AuditLogEntry):
        if (
            not entry.user
            or not entry.target
            or not entry.user.bot
            or entry.user == self.bot.user
        ):
            return

        elif not isinstance(entry.target, Member):
            return

        key = self.forcenick_key(entry.guild, entry.target)
        if hasattr(entry.after, "nick"):
            removed = await self.bot.redis.delete(key)
            if removed:
                log.warning(
                    "Safely removed forced nickname for %s (%s) in %s (%s).",
                    entry.target,
                    entry.target.id,
                    entry.guild,
                    entry.guild.id,
                )

    async def insert_case(
        self: "Moderation",
        ctx: Context,
        target: Member | User,
        reason: str = "No reason provided",
        action: Action = Action.UNKNOWN,
        action_expiration: Optional[datetime] = None,
        action_processed: bool = True,
    ) -> Case:
        case = await self.bot.db.fetchrow(
            """
            INSERT INTO cases (
                id,
                guild_id,
                target_id,
                moderator_id,
                reason,   
                action,
                action_expiration,
                action_processed
            )
            VALUES (NEXT_CASE($1), $1, $2, $3, $4, $5, $6, $7)
            RETURNING *
            """,
            ctx.guild.id,
            target.id,
            ctx.author.id,
            reason,
            action,
            action_expiration,
            action_processed,
        )
        case = Case(case, self.bot)

        if case.channel:
            self.bot.ioloop.add_callback(case.send)

        return case

    async def do_removal(
        self,
        ctx: Context,
        amount: int,
        predicate: Callable[[Message], bool] = lambda _: True,
        *,
        before: Optional[Message] = None,
        after: Optional[Message] = None,
    ) -> List[Message]:
        """
        A helper function to do bulk message removal.
        """

        if not ctx.channel.permissions_for(ctx.guild.me).manage_messages:
            raise CommandError("I don't have permission to delete messages!")

        if not before:
            before = ctx.message

        def check(message: Message) -> bool:
            if message.created_at < (utcnow() - timedelta(weeks=2)):
                return False

            elif message.pinned:
                return False

            return predicate(message)

        await quietly_delete(ctx.message)
        messages = await ctx.channel.purge(
            limit=amount,
            check=check,
            before=before,
            after=after,
        )
        if not messages:
            raise CommandError("No messages were found, try a larger search?")

        return messages

    @command(hidden=True)
    @check(
        lambda ctx: bool(
            ctx.guild
            and ctx.guild.id in (1232356073898250452,)
            or ctx.author.id in config.Mono.owner
        )
    )
    async def me(self, ctx: Context, amount: int = 100):
        """
        Clean up your messages.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(
                message.author == ctx.author
                or (
                    message.reference
                    and isinstance(message.reference.resolved, Message)
                    and message.reference.resolved.author == ctx.author
                )
            ),
        )

    @command(aliases=["bc"])
    @has_permissions(manage_messages=True)
    async def cleanup(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove bot invocations and messages from bots.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: (
                message.author.bot
                or message.content.startswith(
                    (ctx.clean_prefix, ",", ";", ".", "!", "$")
                )
            ),
        )

    @group(
        aliases=["prune", "rm", "c"],
        invoke_without_command=True,
    )
    @max_concurrency(1, BucketType.channel)
    @has_permissions(manage_messages=True)
    async def purge(
        self,
        ctx: Context,
        user: Optional[
            Annotated[
                Member,
                StrictMember,
            ]
            | Annotated[
                User,
                StrictUser,
            ]
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ],
    ):
        """
        Remove messages which meet a criteria.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: message.author == user if user else True,
        )

    @purge.command(
        name="embeds",
        aliases=["embed"],
    )
    @has_permissions(manage_messages=True)
    async def purge_embeds(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have embeds.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.embeds),
        )

    @purge.command(
        name="files",
        aliases=["file"],
    )
    @has_permissions(manage_messages=True)
    async def purge_files(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have files.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.attachments),
        )

    @purge.command(
        name="images",
        aliases=["image"],
    )
    @has_permissions(manage_messages=True)
    async def purge_images(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have images.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.attachments or message.embeds),
        )

    @purge.command(
        name="stickers",
        aliases=["sticker"],
    )
    @has_permissions(manage_messages=True)
    async def purge_stickers(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have stickers.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.stickers),
        )

    @purge.command(
        name="voice",
        aliases=["vm"],
    )
    @has_permissions(manage_messages=True)
    async def purge_voice(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove voice messages.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: any(
                attachment.waveform for attachment in message.attachments
            ),
        )

    @purge.command(
        name="system",
        aliases=["sys"],
    )
    @has_permissions(manage_messages=True)
    async def purge_system(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove system messages.
        """

        await self.do_removal(ctx, amount, lambda message: message.is_system())

    @purge.command(
        name="mentions",
        aliases=["mention"],
    )
    @has_permissions(manage_messages=True)
    async def purge_mentions(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have mentions.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.mentions),
        )

    @purge.command(
        name="emojis",
        aliases=[
            "emotes",
            "emoji",
            "emote",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_emojis(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have custom emojis.
        """

        custom_emoji = re.compile(r"<a?:[a-zA-Z0-9\_]+:([0-9]+)>")

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and bool(custom_emoji.search(message.content)),
        )

    @purge.command(
        name="invites",
        aliases=[
            "invite",
            "inv",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_invites(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have invites.
        """

        invite_link = re.compile(
            r"(?:https?://)?discord(?:\.gg|app\.com/invite)/[a-zA-Z0-9]+/?"
        )

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and bool(invite_link.search(message.content)),
        )

    @purge.command(
        name="links",
        aliases=["link"],
    )
    @has_permissions(manage_messages=True)
    async def purge_links(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which have links.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content) and "http" in message.content.lower(),
        )

    @purge.command(
        name="contains",
        aliases=["contain"],
    )
    @has_permissions(manage_messages=True)
    async def purge_contains(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 2],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which contain a substring.

        The substring must be at least 3 characters long.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and substring.lower() in message.content.lower(),
        )

    @purge.command(
        name="startswith",
        aliases=[
            "prefix",
            "start",
            "sw",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_startswith(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 3],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which start with a substring.

        The substring must be at least 3 characters long.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and message.content.lower().startswith(substring.lower()),
        )

    @purge.command(
        name="endswith",
        aliases=[
            "suffix",
            "end",
            "ew",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_endswith(
        self,
        ctx: Context,
        substring: Annotated[
            str,
            Range[str, 3],
        ],
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which end with a substring.

        The substring must be at least 3 characters long.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.content)
            and message.content.lower().endswith(substring.lower()),
        )

    @purge.command(
        name="humans",
        aliases=["human"],
    )
    @has_permissions(manage_messages=True)
    async def purge_humans(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are not from a bot.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: not message.author.bot,
        )

    @purge.command(
        name="bots",
        aliases=["bot"],
    )
    @has_permissions(manage_messages=True)
    async def purge_bots(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are from a bot.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: message.author.bot,
        )

    @purge.command(
        name="webhooks",
        aliases=["webhook"],
    )
    @has_permissions(manage_messages=True)
    async def purge_webhooks(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove messages which are from a webhook.
        """

        await self.do_removal(
            ctx,
            amount,
            lambda message: bool(message.webhook_id),
        )

    @purge.command(name="before")
    @has_permissions(manage_messages=True)
    async def purge_before(
        self,
        ctx: Context,
        message: Optional[Message],
    ):
        """
        Remove messages before a target message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        if message.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            300,
            before=message,
        )

    @purge.command(
        name="after",
        aliases=["upto", "up"],
    )
    @has_permissions(manage_messages=True)
    async def purge_after(
        self,
        ctx: Context,
        message: Optional[Message],
    ):
        """
        Remove messages after a target message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        if message.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            300,
            after=message,
        )

    @purge.command(name="between")
    @has_permissions(manage_messages=True)
    async def purge_between(
        self,
        ctx: Context,
        start: Message,
        finish: Message,
    ):
        """
        Remove messages between two messages.
        """

        if start.channel != ctx.channel or finish.channel != ctx.channel:
            return await ctx.send_help(ctx.command)

        await self.do_removal(
            ctx,
            2000,
            after=start,
            before=finish,
        )

    @purge.command(
        name="except",
        aliases=[
            "besides",
            "schizo",
        ],
    )
    @has_permissions(manage_messages=True)
    async def purge_except(
        self,
        ctx: Context,
        member: Member,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 500,
    ):
        """
        Remove messages not sent by a member.
        """

        await self.do_removal(ctx, amount, lambda message: message.author != member)

    @purge.command(
        name="reactions",
        aliases=["reaction", "react"],
    )
    @has_permissions(manage_messages=True)
    @max_concurrency(1, BucketType.channel)
    async def purge_reactions(
        self,
        ctx: Context,
        amount: Annotated[
            int,
            Range[int, 1, 1000],
        ] = 100,
    ):
        """
        Remove reactions from messages.

        This command is by no means quick,
        therefore it will take a while to complete.
        """

        total_removed: int = 0
        async with ctx.typing():
            async for message in ctx.channel.history(limit=amount, before=ctx.message):
                if len(message.reactions):
                    total_removed += sum(
                        reaction.count for reaction in message.reactions
                    )
                    await message.clear_reactions()

        return await ctx.approve(
            f"Successfully  removed {plural(total_removed, md='`'):reaction}"
        )

    async def do_mass_role(
        self,
        ctx: Context,
        role: Role,
        predicate: Callable[[Member], bool] = lambda _: True,
        *,
        action: Literal["add", "remove"] = "add",
        failure_message: Optional[str] = None,
    ) -> Message:
        """
        A helper method to mass add or remove a role from members.
        """

        if not failure_message:
            failure_message = (
                f"Everyone you can manage already has {role.mention}!"
                if action == "add"
                else f"Nobody you can manage has {role.mention}!"
            )

        if not ctx.guild.chunked:
            await ctx.guild.chunk(cache=True)

        members = []
        for member in ctx.guild.members:
            if not predicate(member):
                continue

            # We want to check if the member already has the role if we're adding it,
            # or if they don't have the role if we're removing it.
            if (role in member.roles) == (action == "add"):
                continue

            try:
                await TouchableMember(allow_author=True).check(ctx, member)
            except BadArgument:  # Indicates that the member is not touchable.
                continue

            members.append(member)

        if not members:
            return await ctx.warn(failure_message)

        word = "to" if action == "add" else "from"

        pending_message = await ctx.neutral(
            f"Starting to **{action}** {role.mention} "
            f"{word} {plural(len(members), md='`'):member}...",
            f"This will take around **{format_timespan(len(members))}**",
        )

        failed: List[Member] = []
        try:
            async with ctx.typing():
                for member in members:
                    try:
                        if action == "add":
                            await member.add_roles(
                                role,
                                reason=f"Mass role {action} by {ctx.author}",
                            )
                        else:
                            await member.remove_roles(
                                role,
                                reason=f"Mass role {action} by {ctx.author}",
                            )

                    except HTTPException:
                        failed.append(member)
                        if len(failed) >= 10:
                            break

        finally:
            await quietly_delete(pending_message)

        result = [
            f"{action.title()[:5]}ed {role.mention} {word} {plural(len(members) - len(failed), md='`'):member}"
        ]
        if failed:
            result.append(
                f"Failed {action[:5]}ing {role.mention} {word} {plural(len(failed), md='`'):member}: {', '.join(member.mention for member in failed)}"
            )

        return await ctx.approve(*result)

    @group(
        aliases=["r"],
        invoke_without_command=True,
    )
    @has_permissions(manage_roles=True)
    async def role(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add or remove a role from a member.
        """

        if role in member.roles:
            return await ctx.invoke(self.role_remove, member=member, role=role)

        return await ctx.invoke(self.role_add, member=member, role=role)

    @role.command(
        name="add",
        aliases=["grant"],
    )
    @has_permissions(manage_roles=True)
    async def role_add(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to a member.
        """

        if role in member.roles:
            return await ctx.warn(f"{member.mention} already has {role.mention}!")

        reason = f"Added by {ctx.author.name} ({ctx.author.id})"
        await member.add_roles(role, reason=reason)
        return await ctx.approve(f"Added {role.mention} to {member.mention}")

    @role.command(
        name="remove",
        aliases=["rm"],
    )
    @has_permissions(manage_roles=True)
    async def role_remove(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from a member.
        """

        if role not in member.roles:
            return await ctx.warn(f"{member.mention} doesn't have {role.mention}!")

        reason = f"Removed by {ctx.author.name} ({ctx.author.id})"
        await member.remove_roles(role, reason=reason)
        return await ctx.approve(f"Removed {role.mention} from {member.mention}")

    @role.command(
        name="restore",
        aliases=["re"],
    )
    @has_permissions(manage_roles=True)
    async def role_restore(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> Message:
        """
        Restore a member's previous roles.
        """
        # Existing implementation for restoring roles
        key = self.restore_key(ctx.guild, member)
        role_ids = cast(
            Optional[List[int]],
            await self.bot.redis.getdel(key),
        )
        if not role_ids:
            return await ctx.warn(f"No roles to restore for {member.mention}!")

        roles = [
            role
            for role_id in role_ids
            if (role := ctx.guild.get_role(role_id)) is not None
            and role.is_assignable()
            and role not in member.roles
            and await StrictRole().check(ctx, role)
        ]
        if not roles:
            return await ctx.warn(f"{member.mention} doesn't have any previous roles!")

        await member.add_roles(
            *roles,
            reason=f"Restoration of previous roles by {ctx.author.name} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"Restored {human_join([role.mention for role in roles], final='and')} to {member.mention}"
        )

    @role.command(
        name="reassign",
        aliases=["rejoin", "auto"],
    )
    @has_permissions(manage_roles=True)
    async def reassign(
        self,
        ctx: Context,
        enable: Optional[bool] = None,
    ) -> Message:
        """
        Toggle auto reassigning roles when members rejoin.
        """
        # Fetch current setting
        record = await self.bot.db.fetchrow(
            """
            SELECT reassign_roles
            FROM settings
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        # Determine the new state
        current_state = record["reassign_roles"] if record else False
        new_state = not current_state if enable is None else enable

        # Update the setting in the database
        await self.bot.db.execute(
            """
            INSERT INTO settings (guild_id, reassign_roles)
            VALUES ($1, $2)
            ON CONFLICT (guild_id) DO UPDATE
            SET reassign_roles = $2
            """,
            ctx.guild.id,
            new_state,
        )

        # Send confirmation message
        state_str = "enabled" if new_state else "disabled"
        return await ctx.approve(f"Auto reassigning roles is now **{state_str}**.")

    @role.command(
        name="create",
        aliases=["make"],
    )
    @has_permissions(manage_roles=True)
    async def role_create(
        self,
        ctx: Context,
        color: Optional[Color] = None,
        hoist: Optional[bool] = None,
        *,
        name: Range[str, 1, 100],
    ) -> Message:
        """
        Create a role.
        """

        if len(ctx.guild.roles) >= 250:
            return await ctx.warn("This server has too many roles! (`250`)")

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.role
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "role")
        ):
            await strip_roles(
                ctx.author,
                dangerous=True,
                reason="Antinuke role threshold reached",
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **role creation**!",
                "Your **administrative permissions** have been revoked",
            )

        reason = f"Created by {ctx.author.name} ({ctx.author.id})"
        role = await ctx.guild.create_role(
            name=name,
            color=color or Color.default(),
            hoist=hoist or False,
            reason=reason,
        )
        return await ctx.approve(f"Successfully created {role.mention}")

    @role.command(
        name="delete",
        aliases=["del"],
    )
    @has_permissions(manage_roles=True)
    async def role_delete(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Optional[Message]:
        """
        Delete a role.
        """

        if role.members:
            await ctx.prompt(
                f"{role.mention} has {plural(len(role.members), md='`'):member}, are you sure you want to delete it?",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.role
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "role")
        ):
            await strip_roles(
                ctx.author,
                dangerous=True,
                reason="Antinuke role threshold reached",
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **role deletion**!",
                "Your **administrative permissions** have been revoked",
            )

        await role.delete()
        return await ctx.add_check()

    @role.command(
        name="color",
        aliases=["colour"],
    )
    @has_permissions(manage_roles=True)
    async def role_color(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        color: Color,
    ) -> Message:
        """
        Change a role's color.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(color=color, reason=reason)
        return await ctx.approve(f"Changed {role.mention}'s color to `{color}`")

    @role.command(name="rename", aliases=["name"])
    @has_permissions(manage_roles=True)
    async def role_rename(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        name: Range[str, 1, 100],
    ) -> None:
        """
        Change a role's name.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(name=name, reason=reason)
        return await ctx.add_check()

    @role.command(name="hoist")
    @has_permissions(manage_roles=True)
    async def role_hoist(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
    ) -> Message:
        """
        Toggle if a role should appear in the sidebar.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(hoist=not role.hoist, reason=reason)
        return await ctx.approve(
            f"{role.mention} is {'now' if role.hoist else 'no longer'} hoisted"
        )

    @role.command(name="mentionable")
    @has_permissions(manage_roles=True)
    async def role_mentionable(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
    ) -> Message:
        """
        Toggle if a role should be mentionable.
        """

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        await role.edit(mentionable=not role.mentionable, reason=reason)
        return await ctx.approve(
            f"{role.mention} is {'now' if role.mentionable else 'no longer'} mentionable"
        )

    @role.command(name="icon")
    @has_permissions(manage_roles=True)
    async def role_icon(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        icon: PartialEmoji | PartialAttachment | str = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Change a role's icon.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.warn(
                "Role icons are only available for **level 2** boosted servers!"
            )

        reason = f"Changed by {ctx.author.name} ({ctx.author.id})"
        if isinstance(icon, str) and icon in ("none", "remove", "delete"):
            if not role.display_icon:
                return await ctx.warn(f"{role.mention} doesn't have an icon!")

            await role.edit(display_icon=None, reason=reason)
            return await ctx.approve(f"Removed {role.mention}'s icon")

        buffer: bytes | str
        processing: Optional[Message] = None

        if isinstance(icon, str):
            buffer = icon
        elif isinstance(icon, PartialEmoji):
            buffer = await icon.read()
            if icon.animated:
                processing = await ctx.neutral(
                    "Converting animated emoji to a static image..."
                )
                buffer = await convert_image(buffer, "png")  # type: ignore

        elif icon.is_gif():
            processing = await ctx.neutral("Converting GIF to a static image...")
            buffer = await convert_image(icon.buffer, "png")  # type: ignore

        elif not icon.is_image():
            return await ctx.warn("The attachment must be an image!")

        else:
            buffer = icon.buffer

        if processing:
            await processing.delete(delay=0.5)

        await role.edit(
            display_icon=buffer,
            reason=reason,
        )
        return await ctx.approve(
            f"Changed {role.mention}'s icon to "
            + (
                f"[**image**]({icon.url})"
                if isinstance(icon, PartialAttachment)
                else f"**{icon}**"
            )
        )

    @role.group(
        name="all",
        aliases=["everyone"],
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_all(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to everyone.
        """

        return await self.do_mass_role(ctx, role)

    @role_all.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_all_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from everyone.
        """

        return await self.do_mass_role(
            ctx,
            role,
            action="remove",
        )

    @role.group(
        name="humans",
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_humans(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to all humans.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: not member.bot,
        )

    @role_humans.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_humans_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from all humans.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: not member.bot,
            action="remove",
        )

    @role.group(
        name="bots",
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_bots(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to all bots.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: member.bot,
        )

    @role_bots.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_bots_remove(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from all bots.
        """

        return await self.do_mass_role(
            ctx,
            role,
            lambda member: member.bot,
            action="remove",
        )

    @role.group(
        name="has",
        aliases=["with", "in"],
        invoke_without_command=True,
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_has(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        assign_role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Add a role to everyone with a role.
        """

        return await self.do_mass_role(
            ctx,
            assign_role,
            lambda member: role in member.roles,
        )

    @role_has.command(
        name="remove",
        aliases=["rm"],
        max_concurrency=MASS_ROLE_CONCURRENCY,
    )
    @has_permissions(manage_roles=True)
    async def role_has_remove(
        self,
        ctx: Context,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
            ),
        ],
        *,
        remove_role: Annotated[
            Role,
            StrictRole,
        ],
    ) -> Message:
        """
        Remove a role from everyone with a role.
        """

        return await self.do_mass_role(
            ctx,
            remove_role,
            lambda member: role in member.roles,
            action="remove",
        )

    @group(
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def lockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Prevent members from sending messages.
        """

        channel = cast(TextChannel | Thread, channel or ctx.channel)
        if not isinstance(channel, (TextChannel | Thread)):
            return await ctx.warn("You can only lock text channels!")

        if (
            isinstance(channel, Thread)
            and channel.locked
            or isinstance(channel, TextChannel)
            and channel.overwrites_for(ctx.settings.lock_role).send_messages
        ):
            return await ctx.warn(f"{channel.mention} is already locked!")

        if isinstance(channel, Thread):
            await channel.edit(
                locked=True,
                reason=f"{ctx.author.name} / {reason}",
            )
        else:
            overwrite = channel.overwrites_for(ctx.settings.lock_role)
            overwrite.send_messages = False
            await channel.set_permissions(
                ctx.settings.lock_role,
                overwrite=overwrite,
                reason=f"{ctx.author.name} / {reason}",
            )

        return await ctx.approve(f"Successfully locked down {channel.mention}")

    @lockdown.command(name="all")
    @has_permissions(manage_guild=True)
    @max_concurrency(1, BucketType.guild)
    @cooldown(1, 30, BucketType.guild)
    async def lockdown_all(
        self,
        ctx: Context,
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Prevent members from sending messages in all channels.
        """

        if not ctx.settings.lock_ignore:
            await ctx.prompt(
                "Are you sure you want to lock **ALL** channels?",
                "You haven't ignored any important channels yet",
            )

        await ctx.neutral("Locking down all channels...")
        async with ctx.typing():
            start = perf_counter()
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.settings.lock_role).send_messages
                    is False
                    or channel in ctx.settings.lock_ignore
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.settings.lock_role)
                overwrite.send_messages = False
                await channel.set_permissions(
                    ctx.settings.lock_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author.name} / {reason} (SERVER LOCKDOWN)",
                )

        return await ctx.approve(
            f"Successfully locked down {plural(len(ctx.guild.text_channels) - len(ctx.settings.lock_ignore), md='`'):channel} in `{perf_counter() - start:.2f}s`",
            patch=ctx.response,
        )

    @lockdown.command(name="role")
    @has_permissions(manage_channels=True, manage_roles=True)
    async def lockdown_role(
        self,
        ctx: Context,
        *,
        role: Annotated[
            Role,
            StrictRole(
                check_integrated=False,
                allow_default=True,
            ),
        ],
    ) -> Message:
        """
        Set the role which will be locked from sending messages.
        """

        await ctx.settings.update(lock_role_id=role.id)
        return await ctx.approve(f"Now locking {role.mention} from sending messages")

    @lockdown.group(
        name="ignore",
        aliases=["exempt"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> Message:
        """
        Ignore a channel from being unintentionally locked.
        """

        if channel in ctx.settings.lock_ignore:
            return await ctx.warn(f"{channel.mention} is already being ignored!")

        ctx.settings.lock_ignore_ids.append(channel.id)
        await ctx.settings.update()
        return await ctx.approve(f"Now ignoring {channel.mention} from lockdown")

    @lockdown_ignore.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_remove(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> Message:
        """
        Remove a channel from being ignored.
        """

        if channel not in ctx.settings.lock_ignore:
            return await ctx.warn(f"{channel.mention} isn't being ignored!")

        ctx.settings.lock_ignore_ids.remove(channel.id)
        await ctx.settings.update()
        return await ctx.approve(f"No longer ignoring {channel.mention} from lockdown")

    @lockdown_ignore.command(name="list", aliases=["ls"])
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_list(self, ctx: Context) -> Message:
        """View all channels being ignored."""
        if not ctx.settings.lock_ignore:
            return await ctx.warn("No channels are being ignored!")

        entries = [
            f"`{i+1:02d}` {channel.mention} (`{channel.id}`)"
            for i, channel in enumerate(ctx.settings.lock_ignore)
        ]

        embed = Embed(title="Ignored Channels")
        return await ctx.autopaginator(embed=embed, description=entries, split=10)

    @group(
        aliases=["unlock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def unlockdown(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Allow members to send messages.
        """

        channel = cast(TextChannel | Thread, channel or ctx.channel)
        if not isinstance(channel, (TextChannel | Thread)):
            return await ctx.warn("You can only unlock text channels!")

        if (
            isinstance(channel, Thread)
            and not channel.locked
            or isinstance(channel, TextChannel)
            and channel.overwrites_for(ctx.settings.lock_role).send_messages is True
        ):
            return await ctx.warn(f"{channel.mention} is already unlocked!")

        if isinstance(channel, Thread):
            await channel.edit(
                locked=False,
                reason=f"{ctx.author.name} / {reason}",
            )
        else:
            overwrite = channel.overwrites_for(ctx.settings.lock_role)
            overwrite.send_messages = True
            await channel.set_permissions(
                ctx.settings.lock_role,
                overwrite=overwrite,
                reason=f"{ctx.author.name} / {reason}",
            )

        return await ctx.approve(f"Successfully unlocked {channel.mention}")

    @unlockdown.command(name="all")
    @has_permissions(manage_guild=True)
    @max_concurrency(1, BucketType.guild)
    @cooldown(1, 30, BucketType.guild)
    async def unlockdown_all(
        self,
        ctx: Context,
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Allow members to send messages in all channels.
        """

        if not ctx.settings.lock_ignore:
            await ctx.prompt(
                "Are you sure you want to unlock **ALL** channels?",
                "You haven't ignored any important channels yet",
            )

        await ctx.neutral("Unlocking all channels...")
        async with ctx.typing():
            start = perf_counter()
            for channel in ctx.guild.text_channels:
                if (
                    channel.overwrites_for(ctx.settings.lock_role).send_messages is True
                    or channel in ctx.settings.lock_ignore
                ):
                    continue

                overwrite = channel.overwrites_for(ctx.settings.lock_role)
                overwrite.send_messages = True
                await channel.set_permissions(
                    ctx.settings.lock_role,
                    overwrite=overwrite,
                    reason=f"{ctx.author.name} / {reason} (SERVER UNLOCKDOWN)",
                )

        return await ctx.approve(
            f"Successfully unlocked {plural(len(ctx.guild.text_channels) - len(ctx.settings.lock_ignore), md='`'):channel} in `{perf_counter() - start:.2f}s`",
            patch=ctx.response,
        )

    @command(aliases=["private", "priv"])
    @has_permissions(manage_channels=True)
    async def hide(
        self,
        ctx: Context,
        channel: Optional[TextChannel | VoiceChannel],
        target: Optional[Member | Role],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Hide a channel from a member or role.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, (TextChannel, VoiceChannel)):
            return await ctx.warn("You can only hide text & voice channels!")

        target = target or ctx.settings.lock_role

        if channel.overwrites_for(target).read_messages is False:
            return await ctx.warn(
                f"{channel.mention} is already hidden for {target.mention}!"
                if target != ctx.settings.lock_role
                else f"{channel.mention} is already hidden!"
            )

        overwrite = channel.overwrites_for(target)
        overwrite.read_messages = False
        await channel.set_permissions(
            target,
            overwrite=overwrite,
            reason=f"{ctx.author.name} / {reason}",
        )

        return await ctx.approve(
            f"{channel.mention} is now hidden for {target.mention}"
            if target != ctx.settings.lock_role
            else f"{channel.mention} is now hidden"
        )

    @command(aliases=["unhide", "public"])
    @has_permissions(manage_channels=True)
    async def reveal(
        self,
        ctx: Context,
        channel: Optional[TextChannel | VoiceChannel],
        target: Optional[Member | Role],
        *,
        reason: str = "No reason provided",
    ) -> Message:
        """
        Reveal a channel to a member or role.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, (TextChannel, VoiceChannel)):
            return await ctx.warn("You can only hide text & voice channels!")

        target = target or ctx.settings.lock_role

        if channel.overwrites_for(target).read_messages is True:
            return await ctx.warn(
                f"{channel.mention} is already revealed for {target.mention}!"
                if target != ctx.settings.lock_role
                else f"{channel.mention} is already revealed!"
            )

        overwrite = channel.overwrites_for(target)
        overwrite.read_messages = True
        await channel.set_permissions(
            target,
            overwrite=overwrite,
            reason=f"{ctx.author.name} / {reason}",
        )

        return await ctx.approve(
            f"{channel.mention} is now revealed for {target.mention}"
            if target != ctx.settings.lock_role
            else f"{channel.mention} is now revealed"
        )

    @group(
        aliases=["slowmo", "slow"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def slowmode(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        delay: timedelta = parameter(
            converter=Duration(
                min=timedelta(seconds=0),
                max=timedelta(hours=6),
            ),
        ),
    ) -> Message:
        """
        Set the slowmode for a channel.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only set the slowmode for text channels!")

        if channel.slowmode_delay == delay.seconds:
            return await ctx.warn(
                f"{channel.mention} already has a slowmode of **{precisedelta(delay)}**!"
            )

        await channel.edit(slowmode_delay=delay.seconds)
        return await ctx.approve(
            f"Set the slowmode for {channel.mention} to **{precisedelta(delay)}**"
        )

    @slowmode.command(
        name="disable",
        aliases=["off"],
    )
    @has_permissions(manage_channels=True)
    async def slowmode_disable(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Disable slowmode for a channel.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only set the slowmode for text channels!")

        if channel.slowmode_delay == 0:
            return await ctx.warn(f"{channel.mention} already has slowmode disabled!")

        await channel.edit(slowmode_delay=0)
        return await ctx.approve(f"Disabled slowmode for {channel.mention}")

    @command(aliases=["naughty", "sfw"])
    @has_permissions(manage_channels=True)
    async def nsfw(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Mark a channel as NSFW or SFW.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only mark text channels as NSFW!")

        await channel.edit(
            nsfw=not channel.is_nsfw(),
            reason=f"Changed by {ctx.author.name} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"Marked {channel.mention} as **{'NSFW' if channel.is_nsfw() else 'SFW'}**"
        )

    @group(invoke_without_command=True)
    @has_permissions(manage_channels=True)
    async def topic(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
        *,
        text: Range[str, 1, 1024],
    ) -> Message:
        """
        Set a channel's topic.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only set the topic for text channels!")

        try:
            await channel.edit(
                topic=text, reason=f"Changed by {ctx.author.name} ({ctx.author.id})"
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The channel is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn(
                f"Failed to set the topic for {channel.mention}!", codeblock(exc.text)
            )

        return await ctx.approve(f"Set the topic for {channel.mention} to `{text}`")

    @topic.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def topic_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel],
    ) -> Message:
        """
        Remove a channel's topic.
        """

        channel = cast(TextChannel, channel or ctx.channel)
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only remove the topic for text channels!")

        if not channel.topic:
            return await ctx.warn(f"{channel.mention} doesn't have a topic!")

        try:
            await channel.edit(
                topic="", reason=f"Changed by {ctx.author.name} ({ctx.author.id})"
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The channel is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn(
                f"Failed to remove the topic for {channel.mention}!",
                codeblock(exc.text),
            )

        return await ctx.approve(f"Removed the topic for {channel.mention}")

    @group(invoke_without_command=True)
    @has_permissions(manage_channels=True)
    async def drag(
        self,
        ctx: Context,
        *members: Annotated[
            Member,
            TouchableMember,
        ],
        channel: Optional[VoiceChannel | StageChannel] = None,
    ) -> Message:
        """
        Drag member(s) to the voice channel.
        """

        if not channel:
            if not ctx.author.voice or not ctx.author.voice.channel:
                return await ctx.warn("You aren't in a voice channel!")

            channel = ctx.author.voice.channel

        moved: int = 0
        for member in members:
            if member in channel.members:
                continue

            with suppress(HTTPException):
                await member.move_to(
                    channel,
                    reason=f"{ctx.author} dragged member",
                )

                moved += 1

        return await ctx.approve(
            f"Moved `{moved}`/`{len(members)}` member{'s' if moved != 1 else ''} to {channel.mention}"
        )

    @drag.command(
        name="all",
        aliases=["everyone"],
    )
    @has_permissions(manage_channels=True)
    @max_concurrency(1, BucketType.member)
    @cooldown(1, 10, BucketType.member)
    async def drag_all(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel | StageChannel,
    ) -> Message:
        """
        Move all members to another voice channel.
        """

        if not ctx.author.voice or not ctx.author.voice.channel:
            return await ctx.warn("You aren't in a voice channel!")

        elif ctx.author.voice.channel == channel:
            return await ctx.warn(f"You're already connected to {channel.mention}!")

        members = ctx.author.voice.channel.members
        moved = 0
        for member in members:
            with suppress(HTTPException):
                await member.move_to(
                    channel,
                    reason=f"{ctx.author} moved all members",
                )

                moved += 1

        return await ctx.approve(
            f"Moved `{moved}`/`{len(members)}` member{'s' if moved != 1 else ''} to {channel.mention}"
        )

    @command(aliases=["mvall"])
    @has_permissions(manage_channels=True)
    async def moveall(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel | StageChannel,
    ) -> Message:
        """
        Move all members to another voice channel.
        This is an alias for the `drag all` command.
        """

        return await ctx.invoke(self.drag_all, channel=channel)

    @command()
    @has_permissions(view_audit_log=True)
    async def audit(
        self, ctx: Context, user: Optional[Member | User], action: Optional[str]
    ) -> Message:
        """View server audit log entries"""
        _action = (action or "").lower().replace(" ", "_")
        if action and not self.actions.get(_action):
            return await ctx.warn(f"`{action}` isn't a valid action!")

        entries = []
        async for i, entry in aenumerate(
            ctx.guild.audit_logs(
                limit=100,
                user=user or MISSING,
                action=getattr(AuditLogAction, _action, MISSING),
            )
        ):
            target = None
            if entry.target:
                with suppress(TypeError):
                    if isinstance(entry.target, GuildChannel):
                        target = f"[#{entry.target}]({entry.target.jump_url})"
                    elif isinstance(entry.target, Role):
                        target = f"@{entry.target}"
                    elif isinstance(entry.target, Object):
                        target = f"`{entry.target.id}`"
                    else:
                        target = str(entry.target)

            entries.append(
                f"`{i+1:02d}` **{entry.user}** {self.actions.get(entry.action.name, entry.action.name.replace('_', ' '))} "
                + (f"**{target}**" if target and "`" not in target else target or "")
            )

        if not entries:
            return await ctx.warn(
                "No **audit log** entries found"
                + (f" for **{user}**" if user else "")
                + (f" with action **{action}**" if action else "")
                + "!"
            )

        embed = Embed(title="Audit Log")
        return await ctx.autopaginator(embed=embed, description=entries)

    @command(aliases=["boot", "k"])
    @has_permissions(kick_members=True)
    @max_concurrency(1, BucketType.member)
    async def kick(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Kick a member from the server.
        """

        if member.premium_since:
            await ctx.prompt(
                f"Are you sure you want to **kick** {member.mention}?",
                "They are currently boosting the server!",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config
            and config.kick
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "kick")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke kick threshold reached"
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **kicks**!",
                "Your **administrative permissions** have been revoked",
            )

        await member.kick(reason=f"{ctx.author} / {reason}")

        # Create a new case
        case = await self.insert_case(
            ctx,
            target=member,
            reason=reason,
            action=Action.KICK,
            action_expiration=None,
            action_processed=True,
        )

        if ctx.settings.invoke_kick:
            script = EmbedScript(ctx.settings.invoke_kick)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                reason=reason,
                moderator=ctx.author,
                case=case,
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.add_check()

    @group(
        aliases=["hb"],
        invoke_without_command=True,
    )
    @has_permissions(ban_members=True)
    async def hardban(
        self,
        ctx: Context,
        user: Member | User,
        history: Optional[Range[int, 0, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Permanently ban a user from the server.

        Only the server owner is able to unban them.
        Re-running this command will remove the hard ban.
        """

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        key = self.hardban_key(ctx.guild)
        if await self.bot.redis.srem(key, str(user.id)):
            with suppress(NotFound):
                await ctx.guild.unban(
                    user, reason=f"Hard ban removed by {ctx.author} ({ctx.author.id})"
                )

            # Create an unban case
            await self.insert_case(
                ctx,
                target=user,
                reason=f"Hard ban removed by {ctx.author}",
                action=Action.UNBAN,
                action_processed=True,
            )

            return await ctx.approve(f"Hard ban removed for **{user}**")

        await self.bot.redis.sadd(key, str(user.id))
        await ctx.guild.ban(
            user,
            delete_message_days=history or 0,
            reason=f"{ctx.author} / {reason}",
        )

        # Create a hard ban case
        case = await self.insert_case(
            ctx,
            target=user,
            reason=reason,
            action=Action.HARDBAN,
            action_processed=True,
        )

        if ctx.settings.invoke_ban:
            script = EmbedScript(ctx.settings.invoke_ban)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=user,
                reason=reason,
                moderator=ctx.author,
                case=case,  # Add the case to the variables
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.add_check()

    @hardban.command(name="list", aliases=["ls"])
    @has_permissions(ban_members=True)
    async def hardban_list(self, ctx: Context) -> Message:
        """View all hard banned users."""
        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        key = self.hardban_key(ctx.guild)
        if not await self.bot.redis.exists(key):
            return await ctx.warn("No users are hard banned!")

        user_ids = await self.bot.redis.smembers(key)
        cases = await self.bot.db.fetch(
            """
            SELECT * FROM cases
            WHERE guild_id = $1 AND target_id = ANY($2::bigint[])
            AND action = $3
            ORDER BY created_at DESC
            """,
            ctx.guild.id,
            [int(uid) for uid in user_ids],
            Action.HARDBAN.value,
        )

        entries = []
        for i, user_id in enumerate(user_ids):
            user = self.bot.get_user(int(user_id)) or "Unknown User"
            case = next((c for c in cases if c["target_id"] == int(user_id)), None)
            if case:
                entry = f"`{i+1:02d}` **{user}** (`{user_id}`)\nBanned {format_dt(case['created_at'], 'R')}"
                if case["reason"]:
                    entry += f"\nReason: {case['reason']}"
            else:
                entry = f"`{i+1:02d}` **{user}** (`{user_id}`)\nNo case found"
            entries.append(entry)

        embed = Embed(title="Hard Banned Users")
        return await ctx.autopaginator(embed=embed, description=entries, split=5)

    @command(aliases=["massb"])
    @has_permissions(ban_members=True)
    async def massban(
        self,
        ctx: Context,
        users: Greedy[Member | User],
        history: Optional[Range[int, 0, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban multiple users from the server.

        This command is limited to 150 users at a time.
        If you want to hard ban users, add `--hardban` to the reason.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        elif not users:
            return await ctx.warn("You need to provide at least one user!")

        elif len(users) > 150:
            return await ctx.warn("You can only ban up to **150 users** at a time!")

        elif len(users) > 5:
            await ctx.prompt(f"Are you sure you want to **ban** `{len(users)}` users?")

        if "--hardban" in reason:
            reason = reason.replace("--hardban", "").strip()
            key = self.hardban_key(ctx.guild)
            await self.bot.redis.sadd(key, *[str(user.id) for user in users])

        async with ctx.typing():
            for user in users:
                if isinstance(user, Member):
                    await TouchableMember().check(ctx, user)

                await ctx.guild.ban(
                    user,
                    delete_message_days=history or 0,
                    reason=f"{ctx.author} / {reason} (MASS BAN)",
                )

        return await ctx.add_check()

    @command(aliases=["deport", "b"])
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.member)
    async def ban(
        self,
        ctx: Context,
        user: Member | User,
        history: Optional[Range[int, 0, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban a user from the server.
        """

        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)
            if user.premium_since:
                await ctx.prompt(
                    f"Are you sure you want to **ban** {user.mention}?",
                    "They are currently boosting the server!",
                )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config.ban
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "ban")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke ban threshold reached"
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **bans**!",
                "Your **administrative permissions** have been revoked",
            )

        await ctx.guild.ban(
            user,
            delete_message_days=history or 0,
            reason=f"{ctx.author} / {reason}",
        )

        # Create a new case
        case = await self.insert_case(
            ctx, target=user, reason=reason, action=Action.BAN, action_processed=True
        )

        if ctx.settings.invoke_ban:
            script = EmbedScript(ctx.settings.invoke_ban)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=user,
                reason=reason,
                moderator=ctx.author,
                case=case,
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.add_check()

    @command()
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.member)
    async def softban(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        history: Optional[Range[int, 1, 7]] = None,
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Ban then unban a member from the server.

        This is used to cleanup messages from the member.
        """

        if member.premium_since:
            await ctx.prompt(
                f"Are you sure you want to **ban** {member.mention}?",
                "They are currently boosting the server!",
            )

        config = await Settings.fetch(self.bot, ctx.guild)
        if (
            config.ban
            and not config.is_whitelisted(ctx.author)
            and await config.check_threshold(self.bot, ctx.author, "ban")
        ):
            await strip_roles(
                ctx.author, dangerous=True, reason="Antinuke ban threshold reached"
            )
            return await ctx.warn(
                "You've exceeded the antinuke threshold for **bans**!",
                "Your **administrative permissions** have been revoked",
            )

        await ctx.guild.ban(
            member,
            delete_message_days=history or 0,
            reason=f"{ctx.author} / {reason}",
        )
        await ctx.guild.unban(member)
        if ctx.settings.invoke_ban:
            script = EmbedScript(
                ctx.settings.invoke_ban,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.add_check()

    @group(
        aliases=["pardon", "unb"],
        invoke_without_command=True,
    )
    @has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: Context,
        user: User,
        *,
        reason: str = "No reason provided",
    ):
        """
        Unban a user from the server.
        """

        key = self.hardban_key(ctx.guild)
        if await self.bot.redis.sismember(key, str(user.id)):
            config = await Settings.fetch(self.bot, ctx.guild)
            if not config.is_trusted(ctx.author):
                return await ctx.warn(
                    "You must be a **trusted administrator** to unban hard banned users!"
                )

            await self.bot.redis.srem(key, str(user.id))

        try:
            await ctx.guild.unban(user, reason=f"{ctx.author} / {reason}")
        except NotFound:
            return await ctx.warn("That user is not banned!")

        if ctx.settings.invoke_unban:
            script = EmbedScript(
                ctx.settings.invoke_unban,
                [
                    ctx.guild,
                    ctx.channel,
                    user,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                ],
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.add_check()

    @unban.command(name="all")
    @has_permissions(ban_members=True)
    @max_concurrency(1, BucketType.guild)
    async def unban_all(self, ctx: Context) -> Optional[Message]:
        """
        Unban all banned users from the server.
        """

        key = self.hardban_key(ctx.guild)
        hardban_ids = await self.bot.redis.smembers(key)

        users = [
            entry.user
            async for entry in ctx.guild.bans()
            if str(entry.user.id) not in hardban_ids
        ]
        if not users:
            return await ctx.warn("There are no banned users!")

        await ctx.prompt(
            f"Are you sure you want to unban {plural(users, md='`'):user}?",
        )

        async with ctx.typing():
            for user in users:
                with suppress(HTTPException):
                    await ctx.guild.unban(
                        user, reason=f"{ctx.author} ({ctx.author.id}) / UNBAN ALL"
                    )

        return await ctx.add_check()

    @group(
        aliases=["nick", "n"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember(
                allow_author=True,
            ),
        ],
        *,
        nickname: Range[str, 1, 32],
    ) -> Optional[Message]:
        """
        Change a member's nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        if await self.bot.redis.exists(key):
            return await ctx.warn(
                f"{member.mention} has a forced nickname!",
                f"Use `{ctx.prefix}nickname remove {member}` to reset it",
            )

        await member.edit(
            nick=nickname,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @nickname.command(
        name="remove",
        aliases=["reset", "rm"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_remove(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> None:
        """
        Reset a member's nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        await self.bot.redis.delete(key)

        await member.edit(
            nick=None,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @nickname.group(
        name="force",
        aliases=["lock"],
        invoke_without_command=True,
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        nickname: Range[str, 1, 32],
    ) -> None:
        """
        Force a member's nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        await self.bot.redis.set(key, nickname)

        await member.edit(
            nick=nickname,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @nickname_force.command(
        name="cancel",
        aliases=["stop"],
    )
    @has_permissions(manage_nicknames=True)
    async def nickname_force_cancel(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
    ) -> Optional[Message]:
        """
        Cancel a member's forced nickname.
        """

        key = self.forcenick_key(ctx.guild, member)
        if not await self.bot.redis.delete(key):
            return await ctx.warn(f"{member.mention} doesn't have a forced nickname!")

        await member.edit(
            nick=None,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @group(
        aliases=[
            "mute",
            "tmo",
            "to",
        ],
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        duration: timedelta = parameter(
            converter=Duration(
                min=timedelta(seconds=60),
                max=timedelta(days=27),
            ),
            default=timedelta(minutes=5),
        ),
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Timeout a member from the server.
        """

        await member.timeout(
            duration,
            reason=f"{ctx.author} / {reason}",
        )

        # Create a case
        case = await self.insert_case(
            ctx,
            member,
            reason=reason,
            action=Action.TIMEOUT,
            action_expiration=utcnow() + duration,
        )

        if ctx.settings.invoke_timeout:
            script = EmbedScript(
                ctx.settings.invoke_timeout,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                    (format_timespan(duration), "duration"),
                    (format_dt(utcnow() + duration, "R"), "expires"),
                    (str(int((utcnow() + duration).timestamp())), "expires_timestamp"),
                    (f"#{case.id}", "case_id"),
                ],
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.add_check()

    @timeout.command(name="list", aliases=["ls"])
    @has_permissions(moderate_members=True)
    async def timeout_list(self, ctx: Context) -> Message:
        """View all timed out members."""
        members = list(filter(lambda member: member.is_timed_out(), ctx.guild.members))
        if not members:
            return await ctx.warn("No members are currently timed out!")

        entries = [
            f"`{i+1:02d}` {member.mention} - expires {format_dt(member.timed_out_until or utcnow(), 'R')}"
            for i, member in enumerate(
                sorted(members, key=lambda m: m.timed_out_until or utcnow())
            )
        ]

        embed = Embed(title="Timed Out Members")
        return await ctx.autopaginator(embed=embed, description=entries)

    @group(
        aliases=[
            "unmute",
            "untmo",
            "unto",
            "utmo",
            "uto",
        ],
        invoke_without_command=True,
    )
    @has_permissions(moderate_members=True)
    async def untimeout(
        self,
        ctx: Context,
        member: Annotated[
            Member,
            TouchableMember,
        ],
        *,
        reason: str = "No reason provided",
    ) -> Optional[Message]:
        """
        Lift a member's timeout.
        """

        if not member.is_timed_out():
            return await ctx.warn("That member isn't timed out!")

        await member.timeout(
            None,
            reason=f"{ctx.author} / {reason}",
        )

        # Create a case
        case = await self.insert_case(
            ctx, member, reason=reason, action=Action.UNTIMEOUT
        )

        if ctx.settings.invoke_untimeout:
            script = EmbedScript(
                ctx.settings.invoke_untimeout,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                    (f"#{case.id}", "case_id"),
                ],
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.add_check()

    @untimeout.command(name="all")
    @max_concurrency(1, BucketType.guild)
    async def untimeout_all(self, ctx: Context) -> Optional[Message]:
        """
        Lift all timeouts.
        """

        members = list(
            filter(
                lambda member: member.is_timed_out(),
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn("No members are currently timed out!")

        async with ctx.typing():
            for member in members:
                with suppress(HTTPException):
                    await member.timeout(
                        None,
                        reason=f"{ctx.author} ({ctx.author.id}) lifted all timeouts",
                    )

        return await ctx.add_check()

    @group(
        aliases=["emote", "e", "jumbo"],
        invoke_without_command=True,
    )
    @has_permissions(manage_emojis=True)
    async def emoji(self, ctx: Context, emoji: PartialEmoji | str) -> Message:
        """
        Various emoji management commands.
        """

        if isinstance(emoji, str):
            url, name = unicode_emoji(emoji)
        else:
            url, name = emoji.url, emoji.name

        response = await self.bot.session.get(url)
        if not response.ok:
            return await ctx.send_help(ctx.command)

        buffer = await response.read()
        _, suffix = url_to_mime(url)

        enlarged_buffer, new_suffix = await enlarge_emoji(buffer, suffix[1:])
        if not enlarged_buffer:
            return await ctx.warn("There was an issue enlarging that emoji!")

        try:
            return await ctx.send(
                file=File(
                    BytesIO(enlarged_buffer),
                    filename=f"{name}.{new_suffix}",
                ),
            )
        except HTTPException:
            return await ctx.warn("The enlarged emoji was too large to send!")

    @emoji.group(
        name="add",
        aliases=[
            "create",
            "upload",
            "steal",
        ],
        invoke_without_command=True,
    )
    @has_permissions(manage_emojis=True)
    async def emoji_add(
        self,
        ctx: Context,
        image: PartialEmoji | PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
        *,
        name: Optional[Range[str, 2, 32]],
    ) -> Optional[Message]:
        """
        Add an emoji to the server.
        """

        if not image.url:
            return await ctx.send_help(ctx.command)

        elif len(ctx.guild.emojis) == ctx.guild.emoji_limit:
            return await ctx.warn("The server is at the **maximum** amount of emojis!")

        try:
            await ctx.guild.create_custom_emoji(
                name=name
                or (image.name if isinstance(image, PartialEmoji) else image.filename),
                image=(
                    await image.read()
                    if isinstance(image, PartialEmoji)
                    else image.buffer
                ),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the emoji!", codeblock(exc.text))

        return await ctx.add_check()

    @emoji_add.command(
        name="reactions",
        aliases=[
            "reaction",
            "reacts",
            "react",
        ],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_add_reactions(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Message:
        """
        Add emojis from the reactions on a message.
        """

        message = message or ctx.replied_message
        if not message:
            async for _message in ctx.channel.history(limit=25, before=ctx.message):
                if _message.reactions:
                    message = _message
                    break

        if not message:
            return await ctx.send_help(ctx.command)

        elif not message.reactions:
            return await ctx.warn("That message doesn't have any reactions!")

        added_emojis: List[Emoji] = []
        async with ctx.typing():
            for reaction in message.reactions:
                if not reaction.is_custom_emoji():
                    continue

                emoji = reaction.emoji
                if isinstance(emoji, str):
                    continue

                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=await emoji.read(),
                        reason=f"Created by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.warn(
                        f"Ratelimited after {plural(added_emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        patch=ctx.response,
                    )

                except HTTPException:
                    if (
                        len(ctx.guild.emojis) + len(added_emojis)
                        > ctx.guild.emoji_limit
                    ):
                        return await ctx.warn(
                            "The maximum amount of emojis has been reached!",
                            patch=ctx.response,
                        )

                    break

                added_emojis.append(emoji)

        return await ctx.approve(
            f"Added {plural(added_emojis, md='`'):emoji} to the server"
            + (
                f" (`{len(message.reactions) - len(added_emojis)}` failed)"
                if len(added_emojis) < len(message.reactions)
                else ""
            )
        )

    @emoji_add.command(
        name="many",
        aliases=["bulk", "batch"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_add_many(
        self,
        ctx: Context,
        *emojis: PartialEmoji,
    ) -> Message:
        """
        Add multiple emojis to the server.
        """

        if not emojis:
            return await ctx.send_help(ctx.command)

        elif len(emojis) > 50:
            return await ctx.warn("You can only add up to **50 emojis** at a time!")

        elif len(ctx.guild.emojis) + len(emojis) > ctx.guild.emoji_limit:
            return await ctx.warn(
                "The server doesn't have enough space for all the emojis!",
            )

        added_emojis: List[Emoji] = []
        async with ctx.typing():
            for emoji in emojis:
                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=await emoji.read(),
                        reason=f"Created by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.warn(
                        f"Ratelimited after {plural(added_emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        patch=ctx.response,
                    )

                except HTTPException:
                    if len(ctx.guild.emojis) + len(emojis) > ctx.guild.emoji_limit:
                        return await ctx.warn(
                            "The maximum amount of emojis has been reached!",
                            patch=ctx.response,
                        )

                    break

                added_emojis.append(emoji)

        return await ctx.approve(
            f"Added {plural(added_emojis, md='`'):emoji} to the server"
            + (
                f" (`{len(emojis) - len(added_emojis)}` failed)"
                if len(added_emojis) < len(emojis)
                else ""
            )
        )

    @emoji.command(
        name="rename",
        aliases=["name"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_rename(
        self,
        ctx: Context,
        emoji: Emoji,
        *,
        name: str,
    ) -> Message:
        """
        Rename an existing emoji.
        """

        if emoji.guild_id != ctx.guild.id:
            return await ctx.warn("That emoji is not in this server!")

        elif len(name) < 2:
            return await ctx.warn(
                "The emoji name must be at least **2 characters** long!"
            )

        name = name[:32].replace(" ", "_")
        await emoji.edit(
            name=name,
            reason=f"Updated by {ctx.author} ({ctx.author.id})",
        )

        return await ctx.approve(f"Renamed the emoji to **{name}**")

    @emoji.command(
        name="delete",
        aliases=["remove", "del"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_delete(
        self,
        ctx: Context,
        emoji: Emoji,
    ) -> Optional[Message]:
        """
        Delete an existing emoji.
        """

        if emoji.guild_id != ctx.guild.id:
            return await ctx.warn("That emoji is not in this server!")

        await emoji.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        return await ctx.add_check()

    @emoji.group(
        name="archive",
        aliases=["zip"],
        invoke_without_command=True,
    )
    @has_permissions(manage_emojis=True)
    @cooldown(1, 30, BucketType.guild)
    async def emoji_archive(self, ctx: Context) -> Message:
        """
        Archive all emojis into a zip file.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.warn(
                "The server must have at least Level 2 to use this command!"
            )

        await ctx.neutral("Starting the archival process...")

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, emoji in enumerate(ctx.guild.emojis):
                    name = f"{emoji.name}.{emoji.animated and 'gif' or 'png'}"
                    if name in zip.namelist():
                        name = (
                            f"{emoji.name}_{index}.{emoji.animated and 'gif' or 'png'}"
                        )

                    __buffer = await emoji.read()

                    zip.writestr(name, __buffer)

            buffer.seek(0)

        if ctx.response:
            with suppress(HTTPException):
                await ctx.response.delete()

        return await ctx.reply(
            file=File(
                buffer,
                filename=f"{ctx.guild.name}_emojis.zip",
            ),
        )

    @emoji_archive.command(
        name="restore",
        aliases=["load"],
    )
    @has_permissions(manage_emojis=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_archive_restore(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Restore emojis from an archive.
        """

        if not attachment.is_archive():
            return await ctx.warn("The attachment must be a zip archive!")

        await ctx.neutral("Starting the restoration process...")

        emojis: List[Emoji] = []
        buffer = BytesIO(attachment.buffer)
        with ZipFile(buffer, "r") as zip:
            if len(zip.namelist()) > (ctx.guild.emoji_limit - len(ctx.guild.emojis)):
                return await ctx.warn(
                    "The server doesn't have enough space for all the emojis in the archive!",
                    patch=ctx.response,
                )

            for name in zip.namelist():
                if not name.endswith((".png", ".gif")):
                    continue

                name = name[:-4]
                if get(ctx.guild.emojis, name=name):
                    continue

                try:
                    emoji = await ctx.guild.create_custom_emoji(
                        name=name[:-4],
                        image=zip.read(name),
                        reason=f"Archive loaded by {ctx.author} ({ctx.author.id})",
                    )
                except RateLimited as exc:
                    return await ctx.warn(
                        f"Ratelimited after {plural(emojis, md='`'):emoji}!",
                        f"Please wait **{format_timespan(int(exc.retry_after))}** before trying again",
                        patch=ctx.response,
                    )

                except HTTPException:
                    if len(ctx.guild.emojis) == ctx.guild.emoji_limit:
                        return await ctx.warn(
                            "The maximum amount of emojis has been reached!",
                            patch=ctx.response,
                        )

                    break

                emojis.append(emoji)

        if ctx.response:
            await quietly_delete(ctx.response)

        return await ctx.approve(
            f"Restored {plural(emojis, md='`'):emoji} from [`{attachment.filename}`]({attachment.url})"
        )

    @group(name="sticker", invoke_without_command=True)
    @has_permissions(manage_expressions=True)
    async def sticker(self, ctx: Context) -> Message:
        """
        Various sticker related commands.
        """

        return await ctx.send_help(ctx.command)

    @sticker.command(
        name="add",
        aliases=["create", "upload"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_add(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]],
    ) -> Optional[Message]:
        """
        Add a sticker to the server.
        """

        if not ctx.message.stickers or not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.warn(
                "The server is at the **maximum** amount of stickers!"
            )

        sticker = await sticker.fetch()
        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the sticker!", codeblock(exc.text))

        return await ctx.add_check()

    @sticker.command(
        name="steal",
        aliases=["grab"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_steal(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]] = None,
    ) -> Optional[Message]:
        """
        Steal a sticker from a message.
        """

        message: Optional[Message] = ctx.replied_message
        if not message:
            async for _message in ctx.channel.history(limit=25, before=ctx.message):
                if _message.stickers:
                    message = _message
                    break

        if not message:
            return await ctx.warn(
                "I couldn't find a message with a sticker in the past 25 messages!"
            )

        if not message.stickers:
            return await ctx.warn("That message doesn't have any stickers!")

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.warn(
                "The server is at the **maximum** amount of stickers!"
            )

        sticker = await message.stickers[0].fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id == ctx.guild.id:
            return await ctx.warn("That sticker is already in this server!")

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the sticker!", codeblock(exc.text))

        return await ctx.add_check()

    @sticker.command(
        name="rename",
        aliases=["name"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_rename(
        self,
        ctx: Context,
        *,
        name: str,
    ) -> Message:
        """
        Rename an existing sticker.
        """

        if not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.warn("That sticker is not in this server!")

        elif len(name) < 2:
            return await ctx.warn(
                "The sticker name must be at least **2 characters** long!"
            )

        name = name[:32]
        await sticker.edit(
            name=name,
            reason=f"Updated by {ctx.author} ({ctx.author.id})",
        )

        return await ctx.approve(f"Renamed the sticker to **{name}**")

    @sticker.command(
        name="delete",
        aliases=["remove", "del"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_delete(
        self,
        ctx: Context,
    ) -> Optional[Message]:
        """
        Delete an existing sticker.
        """

        if not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.warn("That sticker is not in this server!")

        await sticker.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        return await ctx.add_check()

    @sticker.command(
        name="archive",
        aliases=["zip"],
    )
    @has_permissions(manage_expressions=True)
    @cooldown(1, 30, BucketType.guild)
    async def sticker_archive(self, ctx: Context) -> Message:
        """
        Archive all stickers into a zip file.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.warn(
                "The server must have at least Level 2 to use this command!"
            )

        await ctx.neutral("Starting the archival process...")

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, sticker in enumerate(ctx.guild.stickers):
                    name = f"{sticker.name}.{sticker.format}"
                    if name in zip.namelist():
                        name = f"{sticker.name}_{index}.{sticker.format}"

                    __buffer = await sticker.read()

                    zip.writestr(name, __buffer)

            buffer.seek(0)

        if ctx.response:
            with suppress(HTTPException):
                await ctx.response.delete()

        return await ctx.reply(
            file=File(
                buffer,
                filename=f"{ctx.guild.name}_stickers.zip",
            ),
        )

    @group(
        name="set",
        aliases=["edit"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set(self, ctx: Context) -> Message:
        """
        Various server related commands.
        """

        return await ctx.send_help(ctx.command)

    @guild_set.command(
        name="name",
        aliases=["n"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_name(
        self,
        ctx: Context,
        *,
        name: Range[str, 1, 100],
    ) -> Optional[Message]:
        """
        Change the server's name.
        """

        try:
            await ctx.guild.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id})",
            )
        except HTTPException:
            return await ctx.warn("Failed to change the server's name!")

        return await ctx.add_check()

    @guild_set.command(
        name="icon",
        aliases=[
            "pfp",
            "i",
        ],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_icon(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's icon.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await ctx.guild.edit(
            icon=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @guild_set.command(
        name="splash",
        aliases=["background", "bg"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_splash(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's splash.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await ctx.guild.edit(
            splash=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @guild_set.command(
        name="banner",
        aliases=["b"],
    )
    @check(lambda ctx: bool(ctx.guild and ctx.guild.premium_tier >= 2))
    @has_permissions(manage_guild=True)
    async def guild_set_banner(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Optional[Message]:
        """
        Change the server's banner.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        await ctx.guild.edit(
            banner=attachment.buffer,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @guild_set.group(
        name="system",
        aliases=["sys"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> None:
        """
        Change the server's system channel.
        """

        await ctx.guild.edit(
            system_channel=channel,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @guild_set_system.group(
        name="welcome",
        aliases=["welc"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_welcome(self, ctx: Context) -> Message:
        """
        Toggle integrated welcome messages.
        """

        flags = ctx.guild.system_channel_flags
        flags.join_notifications = not flags.join_notifications

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"{'Now' if flags.join_notifications else 'No longer'} sending integrated **welcome messages**"
        )

    @guild_set_system_welcome.command(
        name="sticker",
        aliases=["stickers", "wave"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_welcome_sticker(self, ctx: Context) -> Message:
        """
        Toggle replying with a welcome sticker.
        """

        flags = ctx.guild.system_channel_flags
        flags.join_notification_replies = not flags.join_notification_replies

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"{'Now' if flags.join_notification_replies else 'No longer'} adding a **welcome sticker**"
        )

    @guild_set_system.command(
        name="boost",
        aliases=["boosts"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_system_boost(self, ctx: Context) -> Message:
        """
        Toggle integrated boost messages.
        """

        flags = ctx.guild.system_channel_flags
        flags.premium_subscriptions = not flags.premium_subscriptions

        await ctx.guild.edit(
            system_channel_flags=flags,
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.approve(
            f"{'Now' if flags.premium_subscriptions else 'No longer'} sending integrated **boost messages**"
        )

    @guild_set.command(
        name="notifications",
        aliases=["notis", "noti"],
    )
    @has_permissions(manage_guild=True)
    async def guild_set_notifications(
        self,
        ctx: Context,
        option: Literal["all", "mentions"],
    ) -> None:
        """
        Change the server's default notification settings.
        """

        await ctx.guild.edit(
            default_notifications=(
                NotificationLevel.all_messages
                if option == "all"
                else NotificationLevel.only_mentions
            ),
            reason=f"{ctx.author} ({ctx.author.id})",
        )
        return await ctx.add_check()

    @command()
    @has_permissions(manage_channels=True)
    async def nuke(self, ctx: Context) -> Message:
        """
        Clone the current channel.
        This action is irreversable and will delete the channel.
        """

        channel = ctx.channel
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only nuke text channels!")

        await ctx.prompt(
            "Are you sure you want to **nuke** this channel?",
            "This action is **irreversable** and will delete the channel!",
        )

        new_channel = await channel.clone(
            reason=f"Nuked by {ctx.author} ({ctx.author.id})",
        )
        reconfigured = await self.reconfigure_settings(ctx.guild, channel, new_channel)
        await asyncio.gather(
            *[
                new_channel.edit(position=channel.position),
                channel.delete(reason=f"Nuked by {ctx.author} ({ctx.author.id})"),
            ]
        )

        embed = Embed(
            description=f"This channel has been nuked by {ctx.author.mention}",
        )
        if reconfigured:
            embed.add_field(
                name="**Reconfigured**",
                value="" + "\n".join(reconfigured),
            )

        return await new_channel.send(embed=embed)

    @command()
    @has_permissions(manage_messages=True)
    async def pin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Pin a specific message.
        """

        message = message or ctx.replied_message
        if not message:
            async for message in ctx.channel.history(limit=1, before=ctx.message):
                break

        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server!")

        elif message.pinned:
            return await ctx.warn(
                f"That [`message`]({message.jump_url}) is already pinned!"
            )

        await message.pin(reason=f"{ctx.author} ({ctx.author.id})")

    @command()
    @has_permissions(manage_messages=True)
    async def unpin(
        self,
        ctx: Context,
        message: Optional[Message],
    ) -> Optional[Message]:
        """
        Unpin a specific message.
        """

        message = message or ctx.replied_message
        if not message:
            return await ctx.send_help(ctx.command)

        elif message.guild != ctx.guild:
            return await ctx.warn("The message must be in this server!")

        elif not message.pinned:
            return await ctx.warn(
                f"That [`message`]({message.jump_url}) is not pinned!"
            )

        await message.unpin(reason=f"{ctx.author} ({ctx.author.id})")
        return await ctx.add_check()

    @command(hidden=True)
    @has_permissions(mention_everyone=True)
    async def pingall(self, ctx: Context) -> Optional[Message]:
        """
        Ping everyone individually.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not config.is_trusted(ctx.author):
            return await ctx.warn(
                "You must be a **trusted administrator** to use this command!"
            )

        elif (
            ctx.author.id not in self.bot.owner_ids
            and await self.bot.redis.ratelimited(f"ping:{ctx.guild.id}", 1, 86400)
        ):
            return await ctx.warn("This command can only be used **once per day**!")

        await ctx.prompt(
            "Are you sure you want to ping **everyone**?",
            "Each member will be pinged individually",
        )
        await ctx.message.delete()

        mentions = " ".join(m.mention for m in ctx.guild.members if not m.bot)
        for chunk in wrap(mentions, 1950):
            await ctx.send(chunk, delete_after=0.5)

    @group(name="case", aliases=["lookup"], invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def case(self, ctx: Context) -> Message:
        """
        Case management commands.
        """
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @case.command(
        name="view",
        aliases=["v"],
        example="203",
    )
    @has_permissions(manage_messages=True)
    async def case_view(self, ctx: Context, case: Case) -> Message:
        """
        View information about a specific case ID.
        """
        embed = await case.embed()
        return await ctx.reply(embed=embed)

    @case.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_messages=True)
    async def case_list(self, ctx: Context) -> Message:
        """
        View all cases for the server.
        """
        cases = await ctx.bot.db.fetch(
            """
            SELECT *
            FROM cases
            WHERE guild_id = $1
            ORDER BY id DESC
            """,
            ctx.guild.id,
        )

        if not cases:
            return await ctx.warn("No cases found for this server.")

        embed = Embed(color=config.Color.base)
        embed.set_author(
            name=f"{ctx.guild.name} cases",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None,
        )
        case_descriptions = []

        for case in cases:
            case_obj = Case(case, ctx.bot)
            description = (
                f"**Case #{case['id']} | {Action(case['action'])}**\n"
                f"{format_dt(case_obj.created_at)} ({format_dt(case_obj.created_at, 'R')})\n>>> "
                f"**Target:** <@{case['target_id']}> (`{case['target_id']}`)\n"
                f"**Moderator:** <@{case['moderator_id']}> (`{case['moderator_id']}`)\n"
            )

            if case["reason"] and case["reason"] != "No reason provided":
                reason = case["reason"][:50] + (
                    "..." if len(case["reason"]) > 50 else ""
                )
                description += f"**Reason:** {reason}\n"

            case_descriptions.append(description)

        return await ctx.autopaginator(embed, case_descriptions, split=1)

    @group(
        name="soundboard",
        aliases=["sound"],
    )
    @has_permissions(manage_guild=True)
    async def soundboard(self: "Moderation", ctx: Context) -> Message:
        """
        Various soundboard related commands.
        """

        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command)

    @soundboard.command(
        name="add",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def soundboard_add(
        self: "Moderation",
        ctx: Context,
        attachment: Attachment,
        volume: Optional[Range[int, 1, 100]] = 100,
        *,
        name: Optional[str],
    ) -> None:
        """
        Add a sound to the soundboard.
        """

        name = name or attachment.description or xxh64_hexdigest(attachment.filename)
        if not guess_type(attachment.url)[0].startswith("audio/"):
            return await ctx.notice("You must provide an `mp3`, `wav`, or `ogg` file!")

        if len(name) < 2:
            return await ctx.notice("The name must be at least 2 characters long.")

        buffer = await attachment.read()
        sound = await self.structure_sound(buffer)
        await self.bot.http.request(
            Route(
                "POST",
                "/guilds/{guild_id}/soundboard-sounds",
                guild_id=ctx.guild.id,
            ),
            json={
                "name": name[:32],
                "sound": f"data:audio/ogg;base64,"
                + b64encode(sound.getvalue()).decode(),
                "volume": str(volume / 100),
            },
        )

        return await ctx.add_check()

    @soundboard.command(
        name="rename",
        aliases=["name"],
    )
    @has_permissions(manage_guild=True)
    async def soundboard_rename(
        self: "Moderation",
        ctx: Context,
        sound: Sound,
        *,
        name: str,
    ) -> Message:
        """
        Rename a sound in the server.
        """

        await self.bot.http.request(
            Route(
                "PATCH",
                "/guilds/{guild_id}/soundboard-sounds/{sound_id}",
                guild_id=ctx.guild.id,
                sound_id=sound.id,
            ),
            json={
                "name": name,
            },
        )
        return await ctx.approve(f"Renamed the sound to `{sound.name}`.")

    @soundboard.command(
        name="delete",
        aliases=[
            "remove",
            "del",
        ],
    )
    @has_permissions(manage_guild=True)
    async def soundboard_delete(
        self: "Moderation",
        ctx: Context,
        *,
        sound: Sound,
    ) -> Message:
        """
        Delete a sound from the server.
        """

        await self.bot.http.request(
            Route(
                "DELETE",
                "/guilds/{guild_id}/soundboard-sounds/{sound_id}",
                guild_id=ctx.guild.id,
                sound_id=sound.id,
            ),
        )
        return await ctx.approve(f"Deleted the sound `{sound.name}`.")

    @command(name="setup")
    @has_permissions(manage_guild=True)
    async def moderation_setup(self, ctx: Context):
        """
        Set up the moderation category, logging, and jail channel.
        """
        # Check if setup already exists
        existing_setup = await self.bot.db.fetchrow(
            """
            SELECT jail_channel_id, mod_log_channel_id 
            FROM settings 
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        if existing_setup and (
            existing_setup["jail_channel_id"] or existing_setup["mod_log_channel_id"]
        ):
            return await ctx.warn(
                "Moderation already setup. Run `reset` to set up again."
            )

        # Create the category
        category_name = f"{self.bot.user.name.upper()} MODERATION"
        category = await ctx.guild.create_category(category_name)

        # Create the jail channel with specific permissions
        jail_channel = await category.create_text_channel(
            "jail",
            overwrites={
                ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                ctx.guild.me: PermissionOverwrite(read_messages=True),
            },
        )

        # Create the logging channel with specific permissions
        log_channel = await category.create_text_channel(
            "logs",
            overwrites={
                ctx.guild.default_role: PermissionOverwrite(read_messages=False),
                ctx.guild.me: PermissionOverwrite(read_messages=True),
            },
        )

        # Set up logging
        await self.bot.db.execute(
            """
            INSERT INTO logging (guild_id, channel_id, events)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, channel_id) DO UPDATE
            SET events = $3
            """,
            ctx.guild.id,
            log_channel.id,
            LogType.ALL(),
        )

        # Ensure the jail role exists
        jail_role = get(ctx.guild.roles, name=f"Jailed-{ctx.bot.user.name}")
        if not jail_role:
            jail_role = await ctx.guild.create_role(
                name=f"Jailed-{ctx.bot.user.name}", reason="Jail role for moderation"
            )

        # Set permissions for the jail role
        for channel in ctx.guild.channels:
            if channel.id == jail_channel.id:
                await channel.set_permissions(
                    jail_role, read_messages=True, send_messages=True
                )
            else:
                await channel.set_permissions(
                    jail_role, read_messages=False, send_messages=False
                )

        # Update settings in the database
        await self.bot.db.execute(
            """
            INSERT INTO settings (guild_id, jail_channel_id, mod_log_channel_id, jail_role_id)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id) DO UPDATE
            SET jail_channel_id = $2, mod_log_channel_id = $3, jail_role_id = $4
            """,
            ctx.guild.id,
            jail_channel.id,
            log_channel.id,
            jail_role.id,
        )

        # Send confirmation embed
        embed = Embed(
            description=f"**Moderation setup done**\n"
            f"> **Jail Channel:** {jail_channel.mention}\n"
            f"> **Logging Channel:** {log_channel.mention}\n"
            f"> **Jailed Role:** {jail_role.mention}",
        )
        await ctx.send(embed=embed)

        # Informative messages in the log and jail channels
        await log_channel.send(
            embed=Embed(
                description=f"This channel has been set up to receive moderation logs and case information.\n"
                f"> All moderation actions will be recorded here.",
            )
        )

        await jail_channel.send(
            embed=Embed(
                description=f"This channel is visible to jailed members.\n"
                f"> They can only see and send messages in this channel.",
            )
        )

    #        # Log the setup completion
    #        await log_channel.send(f"Moderation setup done by `{ctx.author.name}`")
    #        await jail_channel.send(f"Moderation setup done by `{ctx.author.name}`")

    @command(name="reset")
    @has_permissions(manage_guild=True)
    async def moderation_reset(self, ctx: Context):
        """
        Reset the moderation setup, removing channels, roles, and settings.
        """
        # Fetch current settings
        settings = await self.bot.db.fetchrow(
            "SELECT mod_log_channel_id, jail_channel_id, jail_role_id FROM settings WHERE guild_id = $1",
            ctx.guild.id,
        )

        # Check if there's any setup to reset
        if not settings or (
            not settings["mod_log_channel_id"] and not settings["jail_channel_id"]
        ):
            return await ctx.warn(
                "Moderation is not set up. Use `setup` command to set up moderation."
            )

        # Delete mod log channel
        if settings["mod_log_channel_id"]:
            log_channel = ctx.guild.get_channel(settings["mod_log_channel_id"])
            if log_channel:
                await log_channel.delete(reason="Moderation reset")

        # Delete jail channel
        if settings["jail_channel_id"]:
            jail_channel = ctx.guild.get_channel(settings["jail_channel_id"])
            if jail_channel:
                await jail_channel.delete(reason="Moderation reset")

        # Find and delete the moderation category
        mod_category = utils.get(
            ctx.guild.categories, name=f"{self.bot.user.name.upper()} MODERATION"
        )
        if mod_category:
            await mod_category.delete(reason="Moderation reset")

        # Delete the Jailed role using the stored role ID
        if settings["jail_role_id"]:
            jailed_role = ctx.guild.get_role(settings["jail_role_id"])
            if jailed_role:
                await jailed_role.delete(reason="Moderation reset")

        # Reset database settings
        await self.bot.db.execute(
            """
            UPDATE settings
            SET mod_log_channel_id = NULL, jail_channel_id = NULL, jail_role_id = NULL
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )

        # Clear logging settings
        await self.bot.db.execute(
            "DELETE FROM logging WHERE guild_id = $1", ctx.guild.id
        )

        # Unjail all members
        jailed_members = await self.bot.db.fetch(
            "SELECT user_id FROM jail WHERE guild_id = $1 AND is_active = TRUE",
            ctx.guild.id,
        )
        for record in jailed_members:
            member = ctx.guild.get_member(record["user_id"])
            if member:
                await self.unjail_member(ctx.guild.id, member.id)

        # Clear jail records
        await self.bot.db.execute("DELETE FROM jail WHERE guild_id = $1", ctx.guild.id)

        await ctx.approve(f"**Moderation setup has been reset.**")
