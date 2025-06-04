from contextlib import suppress
from datetime import timedelta
from logging import getLogger
from time import time
from typing import Annotated, List, Optional, cast
from colorama import Fore

from config import EMOJIS
import discord

from discord import (
    AuditLogEntry,
    Embed,
    Guild,
    HTTPException,
    Member,
    Message,
    Object,
    User,
)
from discord.ext.commands import Cog, Range, flag, group, hybrid_command, hybrid_group
from discord.utils import utcnow
from humanize import naturaldelta
from pydantic import BaseConfig, BaseModel, validator
from typing_extensions import Self
from xxhash import xxh32_hexdigest

from config import CLIENT
from main import Evict
from tools import CompositeMetaClass, MixinMeta
from core.client import Context, FlagConverter
from tools.conversion import Duration, Status
from tools.formatter import codeblock, plural
from managers.paginator import Paginator
from tools.conversion.embed1 import EmbedScript
from cogs.moderation.classes import ModConfig
from datetime import datetime, timezone
import config
from processors.antinuke import (
    process_audit_threshold,
    process_whitelist_check,
    process_punishment_data
)

log = getLogger("evict/nuke")


class Flags(FlagConverter):
    threshold: Range[int, 1, 12] = flag(
        default=3,
        aliases=["limit"],
        description="The threshold for the module to trigger.",
    )
    duration: timedelta = flag(
        aliases=["time", "per"],
        converter=Duration(
            max=timedelta(hours=12),
        ),
        default=timedelta(minutes=60),
        description="The duration before the threshold resets.",
    )
    punishment: str = flag(
        default="ban",
        description="The punishment to apply (ban/kick/strip)"
    )


class Module(BaseModel):
    threshold: int = 5
    duration: int = 60
    punishment: str = "ban"

    @validator("punishment", allow_reuse=True)
    def validate_punishment(cls, v):
        if v not in ["ban", "kick", "strip"]:
            raise ValueError("Punishment must be ban, kick, or strip")
        return v


class Settings(BaseModel):
    guild: Guild
    whitelist: List[int] = []
    trusted_admins: List[int] = []
    bot: bool = False
    ban: Optional[Module]
    kick: Optional[Module]
    role: Optional[Module]
    channel: Optional[Module]
    webhook: Optional[Module]
    emoji: Optional[Module]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __bool__(self) -> bool:
        """
        Check if the settings are enabled.
        """

        return any(
            getattr(self, module)
            for module in ("ban", "kick", "role", "channel", "webhook", "emoji")
        )

    def is_trusted(self, member: Context | Member) -> bool:
        """
        Check if a member is trusted.
        """

        if isinstance(member, Context):
            member = member.author

        return member.id in {
            self.guild.owner_id,
            *self.trusted_admins,
            *CLIENT.OWNER_IDS,
        }

    def is_whitelisted(self, member: Member) -> bool:
        """
        Check if a member is whitelisted.
        """

        return member.id in {
            self.guild.owner_id,
            self.guild.me.id,
            *self.whitelist,
            *self.trusted_admins,
            *CLIENT.OWNER_IDS,
        }

    async def dispatch_log(
        self,
        bot: Evict,
        perpetrator: Member,
        *,
        module: str,
        elapsed: float,
        failure: bool = False,
        details: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs,
    ) -> None:
        """
        Dispatch a log message.
        """
        current_time = datetime.now(timezone.utc)
        module_config = getattr(self, module)
        if not module_config:
            return

        action = f"antinuke {module_config.punishment}"
        reason = description or f"Mass {module} attempt detected"
        if details:
            reason += f" | {details}"

        bot_member = self.guild.get_member(bot.user.id)
        if not bot_member:
            return

        await ModConfig.sendlogs(
            bot,
            action,
            bot_member,
            perpetrator,
            reason
        )

    async def check_threshold(self, bot: Evict, member: Member, module: str) -> bool:
        """
        Check if a member exceeds the threshold for a module.
        """

        if self.is_whitelisted(member):
            return False

        config: Optional[Module] = getattr(self, module)
        if not config:
            return False

        key = f"antinuke_{module}:{self.guild.id}-{member.id}"
        pipe = bot.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, config.duration)
        value, _ = cast(
            tuple[int, int],
            await pipe.execute(),
        )

        if value >= config.threshold:
            log.debug(
                f"{Fore.LIGHTMAGENTA_EX}{member}{Fore.RESET} exceeded the antinuke {Fore.LIGHTCYAN_EX}{module}{Fore.RESET} threshold in {Fore.LIGHTYELLOW_EX}{self.guild}{Fore.RESET}."
            )
            return True

        return False

    @classmethod
    async def revalidate(cls, bot: Evict, guild: Guild) -> Optional[Self]:
        """
        Revalidate the settings for a guild.
        This will update the cache in redis.
        """

        key = f"antinuke:{guild.id}"
        await bot.redis.delete(key)

        record = await bot.db.fetchrow(
            """
            SELECT *
            FROM antinuke
            WHERE guild_id = $1
            """,
            guild.id,
        )
        if not record:
            return

        settings = cls(**record, guild=guild)
        await bot.redis.set(key, settings.dict(exclude={"guild"}))
        return settings

    @classmethod
    async def fetch(cls, bot: Evict, guild: Guild) -> Self:
        """
        Fetch the settings for a guild.
        This will cache the settings in redis.
        """

        key = f"antinuke:{guild.id}"
        cached = cast(
            Optional[dict],
            await bot.redis.get(key),
        )
        if cached:
            return cls(**cached, guild=guild)

        record = await bot.db.fetchrow(
            """
            SELECT * FROM antinuke 
            WHERE guild_id = $1
            """,
            guild.id,
        )
        
        if not record:
            record = await bot.db.fetchrow(
                """
                INSERT INTO antinuke (guild_id)
                VALUES ($1)
                RETURNING *
                """,
                guild.id,
            )

        settings = cls(**record or {}, guild=guild)
        await bot.redis.set(key, settings.dict(exclude={"guild"}))
        return settings

    class Config(BaseConfig):
        arbitrary_types_allowed = True


class AntiNuke(MixinMeta, metaclass=CompositeMetaClass):
    """
    Protect your server from malicious administrators.
    """

    async def cog_load(self) -> None:
        self.bot.add_check(self.is_trusted_admin)
        return await super().cog_load()

    async def cog_unload(self) -> None:
        self.bot.remove_check(self.is_trusted_admin)
        return await super().cog_unload()

    async def is_trusted_admin(self, target: Context | Member) -> bool:
        """
        Check if the author of the command is trusted.

        They'll be trusted if they're the owner of the server,
        or if they were manually added as a trusted member by the owner.
        """

        if isinstance(target, Context):
            command = target.command
            member = target.author
            guild = target.guild
            if not command.qualified_name.startswith("antinuke"):
                return True

        else:
            member = target
            guild = member.guild

        if member.id in {guild.owner_id, *self.bot.owner_ids}:
            return True

        settings = await Settings.fetch(self.bot, guild)
        if not settings.is_trusted(member):
            if isinstance(target, Context):
                await target.warn(
                    "You must be a **trusted administrator** to use this command!"
                )

            return False

        return True

    @hybrid_group(
        aliases=[
            "antiwizz",
            "an",
            "aw",
        ],
        invoke_without_command=True,
        with_app_command=False,
        brief="antinuke admin or guild owner",
    )
    async def antinuke(self, ctx: Context) -> Message:
        """
        Protect your server from malicious administrators.
        """

        return await ctx.send_help(ctx.command)

    @antinuke.command(
        name="settings",
        aliases=["config"],
        brief="antinuke admin or guild owner",
    )
    async def antinuke_settings(self, ctx: Context) -> Message:
        """
        View the antinuke settings.
        """
        config = await Settings.fetch(self.bot, ctx.guild)
        if not config:
            return await ctx.warn("The **antinuke system** hasn't been configured yet!")

        embed = Embed(title=f"Anti-Nuke Settings")

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        def format_module(module: Optional[Module | bool]) -> str:
            if isinstance(module, bool):
                return "Enabled" if module else "Disabled"
            elif module:
                threshold = module.threshold
                duration = naturaldelta(timedelta(seconds=module.duration))
                return f"> Threshold: {threshold}\n> Duration: {duration}"
            return ""

        protection_modules = [
            ("Bot", config.bot),
            ("Ban", config.ban),
            ("Kick", config.kick),
            ("Role", config.role),
            ("Channel", config.channel),
            ("Webhook", config.webhook),
            ("Emoji", config.emoji),
        ]

        for name, module in protection_modules:
            emoji = EMOJIS.ANTINUKE.ENABLE if module else EMOJIS.ANTINUKE.DISABLE
            embed.add_field(
                name=f"{emoji} {name} ", value=format_module(module), inline=True
            )

        whitelist_str = "None"
        if config.whitelist:
            whitelisted = []
            for member_id in config.whitelist:
                member = ctx.guild.get_member(member_id)
                if member:
                    whitelisted.append(f"{member} (`{member.id}`)")
                else:
                    whitelisted.append(f"Unknown User (`{member_id}`)")
            whitelist_str = "\n".join(whitelisted[:3])
            if len(config.whitelist) > 3:
                whitelist_str += f"\n... and {len(config.whitelist) - 3} more"

        embed.add_field(name="Whitelisted Members", value=whitelist_str, inline=True)

        trusted_str = "None"
        if config.trusted_admins:
            trusted = []
            for admin_id in config.trusted_admins:
                admin = ctx.guild.get_member(admin_id)
                if admin:
                    trusted.append(f"{admin} (`{admin.id}`)")
                else:
                    trusted.append(f"Unknown User (`{admin_id}`)")
            trusted_str = "\n".join(trusted[:3])
            if len(config.trusted_admins) > 3:
                trusted_str += f"\n... and {len(config.trusted_admins) - 3} more"

        embed.add_field(name="Trusted Admins", value=trusted_str, inline=True)

        return await ctx.send(embed=embed)

    @antinuke.group(
        name="whitelist",
        aliases=["wl"],
        invoke_without_command=True,
        brief="antinuke admin or guild owner",
        example="@x"
    )
    async def antinuke_whitelist(self, ctx: Context, *, member: User) -> Message:
        """
        Whitelist a member from the antinuke system.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if member.id in config.whitelist:
            await ctx.prompt(
                f"**{member}** is already whitelisted from the **antinuke system**!",
                "Would you like to remove them from the whitelist?",
            )
            config.whitelist.remove(member.id)
        else:
            config.whitelist.append(member.id)

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET whitelist = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.whitelist,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        return await ctx.approve(
            f"Now exempting **{member}** from being punished"
            if member.id in config.whitelist
            else f"Now punishing **{member}** for malicious actions"
        )

    @antinuke_whitelist.command(
        name="list",
        aliases=["ls"],
        brief="antinuke admin or guild owner",
    )
    async def antinuke_whitelist_list(self, ctx: Context) -> Message:
        """
        View all whitelisted members.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        members = [
            f"**{member}** (`{member.id}`)"
            for member_id in config.whitelist
            if (member := ctx.guild.get_member(member_id))
        ]
        if not members:
            return await ctx.warn("No members are exempt from the **antinuke system**!")

        paginator = Paginator(
            ctx,
            entries=members,
            embed=Embed(title="Whitelisted Members"),
        )
        return await paginator.start()

    @antinuke.group(
        name="trust",
        aliases=["admin"],
        invoke_without_command=True,
        brief="antinuke admin or guild owner",
        example="@x",
    )
    async def antinuke_trust(self, ctx: Context, *, member: User) -> Message:
        """
        Allow a member to manage the antinuke system.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if member.id in config.trusted_admins:
            await ctx.prompt(
                f"**{member}** is already trusted with the **antinuke system**!",
                "Would you like to remove them from the trusted list?",
            )
            config.trusted_admins.remove(member.id)
        else:
            config.trusted_admins.append(member.id)

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET trusted_admins = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.trusted_admins,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        return await ctx.approve(
            f"{'Now' if member.id in config.trusted_admins else 'No longer'} allowing **{member}** to manage the **antinuke system**"
        )

    @antinuke_trust.command(
        name="list",
        aliases=["ls"],
        brief="antinuke admin or guild owner",
    )
    async def antinuke_trust_list(self, ctx: Context) -> Message:
        """
        View all trusted admins.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        members = [
            f"**{member}** (`{member.id}`)"
            for member_id in config.trusted_admins
            if (member := ctx.guild.get_member(member_id))
        ]
        if not members:
            return await ctx.warn(
                "No members are allowed to manage the **antinuke system**!"
            )

        paginator = Paginator(
            ctx,
            entries=members,
            embed=Embed(title="Trusted Admins"),
        )
        return await paginator.start()

    @antinuke.command(
        name="bot",
        aliases=[
            "bots",
            "botadd",
        ],
        brief="antinuke admin or guild owner",
        example="on",
    )
    async def antinuke_bot(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
    ) -> Message:
        """
        Prevent bots from being added to the server.

        Whitelisted members will be exempt from this.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if config.bot == status:
            return await ctx.warn(
                f"Protection against bots is already **{'enabled' if status else 'disabled'}**!"
            )

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET bot = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            status,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        return await ctx.approve(
            f"{'Now' if status else 'No longer'} preventing bots from being added to the server"
        )

    @antinuke.command(
        name="ban",
        aliases=["bans"],
        brief="antinuke admin or guild owner",
        example="(on/off) (--threshold 5) (--time 1h) (--punishment ban)",
    )
    async def antinuke_ban(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: Flags,
    ) -> Message:
        """
        Prevent members from being banned.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not status and not config.ban:
            return await ctx.warn(
                "The **antinuke system** isn't preventing members from being banned!"
            )

        punishment = flags.punishment.lower()
        if punishment not in ["ban", "kick", "strip"]:
            return await ctx.warn("Punishment must be `ban`, `kick`, or `strip`")

        config.ban = None
        if status:
            config.ban = Module(
                threshold=flags.threshold,
                duration=int(flags.duration.total_seconds()),
                punishment=punishment
            )

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET ban = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.ban.dict() if config.ban else None,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        if not status:
            return await ctx.approve("No longer preventing members from being banned")

        return await ctx.approve(
            f"Now applying **{punishment}** punishment if {plural(flags.threshold, md='`'):member is|members are} banned within **{naturaldelta(flags.duration)}**"
        )

    @antinuke.command(
        name="kick",
        aliases=["kicks"],
        brief="antinuke admin or guild owner",
        example="(on/off) (--threshold 5) (--time 1h) (--punishment ban)",
    )
    async def antinuke_kick(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: Flags,
    ) -> Message:
        """
        Prevent members from being kicked.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not status and not config.kick:
            return await ctx.warn(
                "The **antinuke system** isn't preventing members from being kicked!"
            )

        config.kick = None
        if status:
            config.kick = Module(
                threshold=flags.threshold,
                duration=int(flags.duration.total_seconds()),
                punishment=flags.punishment
            )

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET kick = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.kick.dict() if config.kick else None,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        if not status:
            return await ctx.approve("No longer monitoring members from being kicked")

        return await ctx.approve(
            f"Now punishing the perpetrator if {plural(flags.threshold, md='`'):member is|members are} kicked within **{naturaldelta(flags.duration)}**"
        )

    @antinuke.command(
        name="role",
        aliases=["roles"],
        brief="antinuke admin or guild owner",
        example="(on/off) (--threshold 5) (--time 1h) (--punishment ban)",
    )
    async def antinuke_role(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: Flags,
    ) -> Message:
        """
        Prevent roles from being created, deleted, or modified.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not status and not config.role:
            return await ctx.warn(
                "The **antinuke system** isn't preventing roles from being modified!"
            )

        config.role = None
        if status:
            config.role = Module(
                threshold=flags.threshold,
                duration=int(flags.duration.total_seconds()),
                punishment=flags.punishment
            )

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET role = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.role.dict() if config.role else None,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        if not status:
            return await ctx.approve("No longer monitoring role modifications")

        return await ctx.approve(
            f"Now punishing the perpetrator if {plural(flags.threshold, md='`'):role is|roles are} modified within **{naturaldelta(flags.duration)}**"
        )

    @antinuke.command(
        name="channel",
        aliases=["channels"],
        brief="antinuke admin or guild owner",
        example="(on/off) (--threshold 5) (--time 1h) (--punishment ban)",
    )
    async def antinuke_channel(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: Flags,
    ) -> Message:
        """
        Prevent channels from being created, deleted, or modified.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not status and not config.channel:
            return await ctx.warn(
                "The **antinuke system** isn't preventing channels from being modified!"
            )

        config.channel = None
        if status:
            config.channel = Module(
                threshold=flags.threshold,
                duration=int(flags.duration.total_seconds()),
                punishment=flags.punishment
            )

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET channel = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.channel.dict() if config.channel else None,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        if not status:
            return await ctx.approve("No longer monitoring channel modifications")

        return await ctx.approve(
            f"Now punishing the perpetrator if {plural(flags.threshold, md='`'):channel is|channels are} modified within **{naturaldelta(flags.duration)}**"
        )

    @antinuke.command(
        name="webhook",
        aliases=[
            "webhooks",
            "hook",
            "hooks",
            "wh",
        ],
        brief="antinuke admin or guild owner",
        example="(on/off) (--threshold 5) (--time 1h) (--punishment ban)",
    )
    async def antinuke_webhook(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: Flags,
    ) -> Message:
        """
        Prevent webhooks from being created, deleted, or modified.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not status and not config.webhook:
            return await ctx.warn(
                "The **antinuke system** isn't preventing webhooks from being modified!"
            )

        config.webhook = None
        if status:
            config.webhook = Module(
                threshold=flags.threshold,
                duration=int(flags.duration.total_seconds()),
                punishment=flags.punishment
            )

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET webhook = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.webhook.dict() if config.webhook else None,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        if not status:
            return await ctx.approve("No longer monitoring webhook modifications")

        return await ctx.approve(
            f"Now punishing the perpetrator if {plural(flags.threshold, md='`'):webhook is|webhooks are} modified within **{naturaldelta(flags.duration)}**"
        )

    @antinuke.command(
        name="emoji",
        aliases=[
            "emojis",
            "emote",
            "emotes",
            "em",
        ],
        brief="antinuke admin or guild owner",
        example="(on/off) (--threshold 5) (--time 1h) (--punishment ban)",
    )
    async def antinuke_emoji(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: Flags,
    ) -> Message:
        """
        Prevent emojis from being created, deleted, or modified.
        """

        config = await Settings.fetch(self.bot, ctx.guild)
        if not status and not config.emoji:
            return await ctx.warn(
                "The **antinuke system** isn't preventing emojis from being modified!"
            )

        config.emoji = None
        if status:
            config.emoji = Module(
                threshold=flags.threshold,
                duration=int(flags.duration.total_seconds()),
                punishment=flags.punishment
            )

        await self.bot.db.execute(
            """
            UPDATE antinuke
            SET emoji = $2
            WHERE guild_id = $1
            """,
            ctx.guild.id,
            config.emoji.dict() if config.emoji else None,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        if not status:
            return await ctx.approve("No longer monitoring emoji modifications")

        return await ctx.approve(
            f"Now punishing the perpetrator if {plural(flags.threshold, md='`'):emoji is|emojis are} modified within **{naturaldelta(flags.duration)}**"
        )

    @antinuke.command(
        name="reset",
        brief="antinuke admin or guild owner",
    )
    async def antinuke_reset(self, ctx: Context) -> Message:
        """
        Reset the antinuke settings.
        """

        await ctx.prompt(
            "Are you sure you want to reset the **antinuke settings**?",
            "This will remove all whitelisted members and trusted admins!",
        )

        await self.bot.db.execute(
            """
            DELETE FROM antinuke
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        await Settings.revalidate(self.bot, ctx.guild)

        return await ctx.approve("Successfully  reset the **antinuke settings**")

    @Cog.listener("on_audit_log_entry_bot_add")
    async def antinuke_monitor_bot(self, entry: AuditLogEntry):
        start = time()
        guild = entry.guild
        perpetrator = entry.user
        application = cast(Member | User | Object, entry.target)
        if not isinstance(perpetrator, Member):
            return

        config = await Settings.fetch(self.bot, guild)
        if (
            not config
            or not config.bot
            or config
            and config.bot
            and config.is_whitelisted(perpetrator)
        ):
            return

        elapsed = time() - start
        try:
            await guild.ban(
                application,
                reason="Bot addition attempt detected!",
            )
            await guild.ban(
                perpetrator,
                reason="Bot addition attempt detected!",
            )
        except HTTPException as exc:
            return await config.dispatch_log(
                self.bot,
                perpetrator,
                module="bot",
                elapsed=elapsed,
                failure=True,
                details=exc.text,
                application=application,
            )

        await config.dispatch_log(
            self.bot,
            perpetrator,
            module="bot",
            elapsed=elapsed,
            application=application,
        )

    @Cog.listener("on_audit_log_entry_ban")
    async def antinuke_monitor_ban(self, entry: AuditLogEntry):
        start = time()
        guild = entry.guild
        perpetrator = entry.user
        if not isinstance(perpetrator, Member):
            return

        config = await Settings.fetch(self.bot, guild)
        if (
            not config
            or not config.ban
            or config
            and config.ban
            and config.is_whitelisted(perpetrator)
        ):
            return

        elif not await config.check_threshold(self.bot, perpetrator, "ban"):
            return

        elapsed = time() - start
        try:
            if config.ban.punishment == "ban":
                await guild.ban(perpetrator, reason="Mass ban attempt detected")
            elif config.ban.punishment == "kick":
                await guild.kick(perpetrator, reason="Mass ban attempt detected")
            elif config.ban.punishment == "strip":
                await perpetrator.edit(roles=[], reason="Mass ban attempt detected")
        except HTTPException as exc:
            return await config.dispatch_log(
                self.bot,
                perpetrator,
                module="ban",
                elapsed=elapsed,
                failure=True,
                details=exc.text,
            )

        await config.dispatch_log(
            self.bot,
            perpetrator,
            module="ban",
            elapsed=elapsed,
        )

        await self.notify_perpetrator(
            self.bot,
            perpetrator,
            module="ban",
            details=exc.text,
        )

    @Cog.listener("on_audit_log_entry_kick")
    async def antinuke_monitor_kick(self, entry: AuditLogEntry):
        start = time()
        guild = entry.guild
        perpetrator = entry.user
        if not isinstance(perpetrator, Member):
            return

        config = await Settings.fetch(self.bot, guild)
        if (
            not config
            or not config.kick
            or config
            and config.kick
            and config.is_whitelisted(perpetrator)
        ):
            return

        elif not await config.check_threshold(self.bot, perpetrator, "kick"):
            return

        elapsed = time() - start
        try:
            if config.kick.punishment == "ban":
                await guild.ban(perpetrator, reason="Mass kick attempt detected")
            elif config.kick.punishment == "kick":
                await guild.kick(perpetrator, reason="Mass kick attempt detected")
            elif config.kick.punishment == "strip":
                await perpetrator.edit(roles=[], reason="Mass kick attempt detected")
        except HTTPException as exc:
            return await config.dispatch_log(
                self.bot,
                perpetrator,
                module="kick",
                elapsed=elapsed,
                failure=True,
                details=exc.text,
            )

        await config.dispatch_log(
            self.bot,
            perpetrator,
            module="kick",
            elapsed=elapsed,
        )

        await self.notify_perpetrator(
            self.bot,
            perpetrator,
            module="kick",
            details=exc.text,
        )

    @Cog.listener("on_audit_log_entry_role_create")
    @Cog.listener("on_audit_log_entry_role_delete")
    @Cog.listener("on_audit_log_entry_role_update")
    async def antinuke_monitor_role(self, entry: AuditLogEntry):
        start = time()
        guild = entry.guild
        perpetrator = entry.user
        if not isinstance(perpetrator, Member):
            return

        config = await Settings.fetch(self.bot, guild)
        if (
            not config
            or not config.role
            or config
            and config.role
            and config.is_whitelisted(perpetrator)
        ):
            return

        elif not await config.check_threshold(self.bot, perpetrator, "role"):
            return

        elapsed = time() - start
        verb = (
            ("created", "creation")
            if entry.action == "role_create"
            else (
                ("deleted", "deletion")
                if entry.action == "role_delete"
                else ("updated", "modification")
            )
        )
        try:
            if config.role.punishment == "ban":
                await guild.ban(perpetrator)
            elif config.role.punishment == "kick":
                await guild.kick(perpetrator)
            elif config.role.punishment == "strip":
                await perpetrator.remove_roles(*perpetrator.roles[1:])
        except HTTPException as exc:
            return await config.dispatch_log(
                self.bot,
                perpetrator,
                module="role",
                elapsed=elapsed,
                failure=True,
                details=exc.text,
                description=f"Role {verb[1]} attempt has been detected!",
            )

        await config.dispatch_log(
            self.bot,
            perpetrator,
            module="role",
            elapsed=elapsed,
            description=f"Role {verb[1]} attempt has been detected!",
        )

        await self.notify_perpetrator(
            self.bot,
            perpetrator,
            module="role",
            details=exc.text,
            description=f"Role {verb[1]} attempt has been detected!",
        )

    @Cog.listener("on_audit_log_entry_channel_create")
    @Cog.listener("on_audit_log_entry_channel_delete")
    @Cog.listener("on_audit_log_entry_channel_update")
    async def antinuke_monitor_channel(self, entry: AuditLogEntry):
        start = time()
        guild = entry.guild
        perpetrator = entry.user
        if not isinstance(perpetrator, Member):
            return

        config = await Settings.fetch(self.bot, guild)
        if (
            not config
            or not config.channel
            or config
            and config.channel
            and config.is_whitelisted(perpetrator)
        ):
            return

        elif not await config.check_threshold(self.bot, perpetrator, "channel"):
            return

        elapsed = time() - start
        verb = (
            ("created", "creation")
            if entry.action == "channel_create"
            else (
                ("deleted", "deletion")
                if entry.action == "channel_delete"
                else ("updated", "modification")
            )
        )
        try:
            if config.channel.punishment == "ban":
                await guild.ban(perpetrator, reason=f"Channel {verb[1]} attempt detected")
            elif config.channel.punishment == "kick":
                await guild.kick(perpetrator, reason=f"Channel {verb[1]} attempt detected")
            elif config.channel.punishment == "strip":
                await perpetrator.edit(roles=[], reason=f"Channel {verb[1]} attempt detected")
        except HTTPException as exc:
            return await config.dispatch_log(
                self.bot,
                perpetrator,
                module="channel",
                elapsed=elapsed,
                failure=True,
                details=exc.text,
            )

        await config.dispatch_log(
            self.bot,
            perpetrator,
            module="channel",
            elapsed=elapsed,
        )

        await self.notify_perpetrator(
            self.bot,
            perpetrator,
            module="channel",
            details=exc.text,
        )

    @Cog.listener("on_audit_log_entry_webhook_create")
    async def antinuke_monitor_webhook(self, entry: AuditLogEntry):
        start = time()
        guild = entry.guild
        perpetrator = entry.user
        if not isinstance(perpetrator, Member):
            return

        config = await Settings.fetch(self.bot, guild)
        if (
            not config
            or not config.webhook
            or config
            and config.webhook
            and config.is_whitelisted(perpetrator)
        ):
            return

        elif not await config.check_threshold(self.bot, perpetrator, "webhook"):
            return

        elapsed = time() - start
        try:
            if config.webhook.punishment == "ban":
                await guild.ban(perpetrator, reason="Webhook creation attempt detected")
            elif config.webhook.punishment == "kick":
                await guild.kick(perpetrator, reason="Webhook creation attempt detected")
            elif config.webhook.punishment == "strip":
                await perpetrator.edit(roles=[], reason="Webhook creation attempt detected")
        except HTTPException as exc:
            return await config.dispatch_log(
                self.bot,
                perpetrator,
                module="webhook",
                elapsed=elapsed,
                failure=True,
                details=exc.text,
            )

        await config.dispatch_log(
            self.bot,
            perpetrator,
            module="webhook",
            elapsed=elapsed,
        )

        await self.notify_perpetrator(
            self.bot,
            perpetrator,
            module="webhook",
            details=exc.text,
        )

    @Cog.listener("on_audit_log_entry_emoji_create")
    @Cog.listener("on_audit_log_entry_emoji_delete")
    @Cog.listener("on_audit_log_entry_emoji_update")
    async def antinuke_monitor_emoji(self, entry: AuditLogEntry):
        start = time()
        guild = entry.guild
        perpetrator = entry.user
        if not isinstance(perpetrator, Member):
            return

        config = await Settings.fetch(self.bot, guild)
        if (
            not config
            or not config.emoji
            or config
            and config.emoji
            and config.is_whitelisted(perpetrator)
        ):
            return

        elif not await config.check_threshold(self.bot, perpetrator, "emoji"):
            return

        elapsed = time() - start
        verb = (
            ("created", "creation")
            if entry.action == "emoji_create"
            else (
                ("deleted", "deletion")
                if entry.action == "emoji_delete"
                else ("updated", "modification")
            )
        )
        try:
            if config.emoji.punishment == "ban":
                await guild.ban(perpetrator, reason=f"Emoji {verb[1]} attempt detected")
            elif config.emoji.punishment == "kick":
                await guild.kick(perpetrator, reason=f"Emoji {verb[1]} attempt detected")
            elif config.emoji.punishment == "strip":
                await perpetrator.edit(roles=[], reason=f"Emoji {verb[1]} attempt detected")
        except HTTPException as exc:
            return await config.dispatch_log(
                self.bot,
                perpetrator,
                module="emoji",
                elapsed=elapsed,
                failure=True,
                details=exc.text,
            )

        await config.dispatch_log(
            self.bot,
            perpetrator,
            module="emoji",
            elapsed=elapsed,
        )

        await self.notify_perpetrator(
            self.bot,
            perpetrator,
            module="emoji",
            details=exc.text,
        )

    async def notify_perpetrator(
        self,
        bot: Evict,
        perpetrator: Member,
        *,
        module: str,
        details: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Create case and notify the perpetrator.
        """
        config = await Settings.fetch(bot, perpetrator.guild)
        if not config:
            return
            
        bot_member = perpetrator.guild.get_member(bot.user.id)
        if not bot_member:
            return

        module_config = getattr(config, module)
        if not module_config:
            return

        action = f"antinuke {module_config.punishment}" 
        reason = description or f"Mass {module} attempt detected"
        if details:
            reason += f" | {details}"

        await ModConfig.sendlogs(
            bot,
            action,
            bot_member,
            perpetrator,
            reason
        )
