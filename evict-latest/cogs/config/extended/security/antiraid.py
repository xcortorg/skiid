from asyncio import sleep
from contextlib import suppress
from datetime import timedelta, datetime, timezone
from logging import getLogger
from typing import Annotated, Dict, List, Literal, Optional, Tuple, TypedDict, cast, Union

from discord import Asset, Embed, Guild, HTTPException, Member, Message, Role, AutoModTrigger, AutoModRuleTriggerType, AutoModRuleEventType, AutoModRuleAction, AutoModRuleActionType
from discord import Status as DiscordStatus
from discord import User
from discord.ext.commands import (
    Cog,
    Range,
    UserInputError,
    flag,
    group,
    has_permissions,
)
from discord.http import Route
from discord.utils import utcnow
from xxhash import xxh32_hexdigest
import config

from tools import CompositeMetaClass, MixinMeta
from core.client import Context, FlagConverter
from tools.conversion import Status
from tools.formatter import plural
import discord 
from tools.conversion.embed1 import EmbedScript
from cogs.moderation.classes import ModConfig

log = getLogger("evict/raid")

class Flags(FlagConverter):
    punishment: Literal["ban", "kick", "timeout", "strip"] = flag(
        description="The punishment the member will receive.",
        aliases=["action", "punish", "do"],
        default="ban",
    )

    class Schema(TypedDict):
        punishment: str

class AutomodFlags(FlagConverter):
    punishment: Literal["delete", "timeout"] = flag(
        description="The punishment the member will receive when they violate automod.",
        aliases=["action", "punish", "do"],
        default="delete",
    )


class AmountFlags(Flags):
    amount: Range[int, 3] = flag(
        description="The threshold before activation.",
        aliases=["count", "threshold"],
        default=5,
    )

    class Schema(TypedDict):
        punishment: str
        amount: int


DEFAULT_AVATAR_HASHES = [
    "157e517cdbf371a47aaead44675714a3",
    "1628fc11e7961d85181295493426b775",
    "5445ffd7ffb201a98393cbdf684ea4b1",
    "79ee349b6511e2000af8a32fb8a6974e",
    "8569adcbd36c70a7578c017bf5604ea5",
    "f7f2e9361e8a54ce6e72580ac7b967af",
    "6c5996770c985bcd6e5b68131ff2ba04",
    "c82b3fa769ed6e6ffdea579381ed5f5c",
]


class AntiRaid(MixinMeta, metaclass=CompositeMetaClass):
    """
    Protect your server from flood attacks.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_cooldown = {}

    def is_default(self, avatar: Optional[Asset]) -> bool:
        return not avatar or avatar.key in DEFAULT_AVATAR_HASHES

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def antiraid(self, ctx: Context) -> Message:
        """
        The base command for managing raid security.
        """

        return await ctx.send_help(ctx.command)

    @antiraid.command(name="joins", aliases=["massjoin"], example="(on/off) (--threshold 5) (--punishment ban)")
    @has_permissions(manage_guild=True)
    async def antiraid_joins(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: AmountFlags,
    ) -> Message:
        """
        Security against accounts which join simultaneously.

        If multiple members join within the `threshold` then the
        members will automatically be punished.
        The `threshold` must be greater than 3.
        """

        if status is False:
            await self.bot.db.execute(
                """
                UPDATE antiraid
                SET joins = NULL
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            return await ctx.approve("Join protection has been disabled")

        await self.bot.db.execute(
            """
            INSERT INTO antiraid (guild_id, joins)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE
            SET joins = EXCLUDED.joins
            """,
            ctx.guild.id,
            dict(flags),
        )
        return await ctx.approve(
            "Join protection has been enabled.",
            f"Threshold set as `{flags.amount}` "
            f"with punishment: **{flags.punishment}**",
        )

    @antiraid.command(name="mentions", example="(on/off) (--threshold 5) (--punishment ban)")
    @has_permissions(manage_guild=True)
    async def antiraid_mentions(
        self,
        ctx: Context,
        status: Annotated[
            bool,
            Status,
        ],
        *,
        flags: AmountFlags,
    ) -> Message:
        """
        Security against accounts that spam excessive mentions.

        If a message contains `threshold` or more mentions then the
        member will be automatically be punished.
        The `threshold` must be greater than 3.

        This only applies for user mentions. Everyone or Role
        mentions are not included.
        """

        if status is False:
            await self.bot.db.execute(
                """
                UPDATE antiraid
                SET mentions = NULL
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            return await ctx.approve("Mention spam protection has been disabled")

        await self.bot.db.execute(
            """
            INSERT INTO antiraid (guild_id, mentions)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE
            SET mentions = EXCLUDED.mentions
            """,
            ctx.guild.id,
            dict(flags),
        )
        return await ctx.approve(
            "Mention spam protection has been enabled.",
            f"Threshold set as `{flags.amount}` "
            f"with punishment: **{flags.punishment}**",
        )

    @antiraid.command(name="avatar", aliases=["pfp"], example="(on/off) (--threshold 5) (--punishment ban)")
    @has_permissions(manage_guild=True)
    async def antiraid_avatar(
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
        Security against accounts which don't have an avatar.
        """

        if status is False:
            await self.bot.db.execute(
                """
                UPDATE antiraid
                SET avatar = NULL
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            return await ctx.approve("Default avatar protection has been disabled")

        await self.bot.db.execute(
            """
            INSERT INTO antiraid (guild_id, avatar)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE
            SET avatar = EXCLUDED.avatar
            """,
            ctx.guild.id,
            dict(flags),
        )
        return await ctx.approve(
            f"Default avatar protection has been enabled "
            f"with punishment as **{flags.punishment}**"
        )

    @antiraid.command(
        name="automation",
        aliases=[
            "selfbot",
            "browser",
            "web",
        ],
        example="(on/off) (--punishment ban)"
    )
    @has_permissions(manage_guild=True)
    async def antiraid_automation(
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
        Security against accounts which are only active on browser.

        This is a common trait of selfbots and other automation tools.
        """

        if status is False:
            await self.bot.db.execute(
                """
                UPDATE antiraid
                SET browser = NULL
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            return await ctx.approve("Automation protection has been disabled")

        members = list(
            filter(
                lambda member: member.web_status != DiscordStatus.offline
                and all(
                    status == DiscordStatus.offline
                    for status in [member.mobile_status, member.desktop_status]
                )
                and not member.bot
                and not member.premium_since,
                ctx.guild.members,
            )
        )
        if members:
            try:
                await ctx.prompt(
                    f"{plural(members, md='`'):member is|members are} currently only online via browser.",
                    f"Would you like to **{flags.punishment}** them now? This does not affect boosters",
                )
            except UserInputError:
                ...
            else:
                async with ctx.typing():
                    for member in members:
                        await self.do_punishment(
                            ctx.guild,
                            member,
                            punishment=flags.punishment,
                            reason="Automation detected",
                        )

        await self.bot.db.execute(
            """
            INSERT INTO antiraid (guild_id, browser)
            VALUES ($1, $2)
            ON CONFLICT (guild_id)
            DO UPDATE
            SET browser = EXCLUDED.browser
            """,
            ctx.guild.id,
            dict(flags),
        )
        return await ctx.approve(
            f"Automation protection has been enabled "
            f"with punishment as **{flags.punishment}**"
        )

    async def submit_incident(
        self,
        guild: Guild,
        members: List[Member],
        punishment: str,
    ) -> None:
        """
        Secure the server during a raid incident.
        """

        current_time = datetime.now(timezone.utc)
        error_key = f"antiraid_incident_{guild.id}"
        
        if error_key in self.error_cooldown:
            if (current_time - self.error_cooldown[error_key]).total_seconds() < 300:
                return

        try:
            properties = {
                "guild_id": str(guild.id),
                "guild_member_count": guild.member_count,
                "raid_size": len(members),
                "punishment": punishment,
                "raiders_data": [
                    {
                        "id": str(m.id),
                        "created_at": m.created_at.isoformat(),
                        "joined_at": m.joined_at.isoformat() if m.joined_at else None,
                        "has_avatar": bool(m.avatar),
                        "is_bot": m.bot,
                        "flags": [str(flag.name) for flag in m.public_flags]
                    }
                    for m in members
                ],
                "mitigation_actions": [
                    "invites_disabled",
                    "dms_disabled",
                    "lockdown"
                ],
                "timestamp": current_time.isoformat()
            }

        except Exception as e:
            self.error_cooldown[error_key] = current_time
            log.warning(f"Analytics failed for antiraid incident - Will retry in 5 minutes")

        await self.bot.db.execute(
            """
            UPDATE antiraid
            SET locked = TRUE
            WHERE guild_id = $1
            """,
            guild.id,
        )
        ends_at = utcnow() + timedelta(hours=1)

        route = Route(
            "PUT",
            "/guilds/{guild_id}/incident-actions",
            guild_id=guild.id,
        )
        await self.bot.http.request(
            route,
            json={
                "invites_disabled_until": ends_at,
                "dms_disabled_until": ends_at,
            },
        )

        with suppress(HTTPException):
            embed = Embed(
                title="Raid Detected",
                description=f"Detected {len(members)} simultaneous joins",
            )

            embed.add_field(
                name="**Action**",
                value=(
                    "New members & DMs "
                    "have been temporarily restricted for an **hour**"
                ),
                inline=True,
            )
            embed.set_footer(text="The mitigation task has been initialized")

            await self.bot.notify(
                guild,
                content=f"<@{guild.owner_id}>",
                embed=embed,
            )

        await sleep(5)
        await self.bot.db.execute(
            """
            UPDATE antiraid
            SET locked = FALSE
            WHERE guild_id = $1
            """,
            guild.id,
        )

        settings = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1",
            guild.id
        )
        
        if settings and settings.get("dm_enabled"):
            for member in members:
                try:
                    script = settings.get("dm_antiraid")
                    
                    if not script:
                        embed = Embed(
                            title="Anti-Raid Protection",
                            description=f"You were {punishment}ed due to raid detection",
                            color=discord.Color.red(),
                            timestamp=utcnow()
                        )
                        embed.add_field(
                            name="Server",
                            value=guild.name,
                            inline=True
                        )
                        embed.add_field(
                            name="Reason",
                            value=f"Detected {len(members)} simultaneous joins",
                            inline=True
                        )
                        await member.send(embed=embed)
                    else:
                        script_obj = EmbedScript(script)
                        await script_obj.send(
                            member,
                            guild=guild,
                            reason=f"Detected {len(members)} simultaneous joins",
                            punishment=punishment
                        )
                except (discord.Forbidden, discord.HTTPException):
                    pass

    async def notify_perpetrator(
        self,
        guild: Guild,
        member: Member,
        punishment: str,
        reason: str,
    ) -> None:
        """
        Create case and notify the member.
        """
        action = f"antiraid_{punishment}"
        
        current_time = datetime.now(timezone.utc)
        error_key = f"antiraid_action_{guild.id}"
        
        if error_key in self.error_cooldown:
            if (current_time - self.error_cooldown[error_key]).total_seconds() < 300:
                return
        
        await ModConfig.sendlogs(
            self.bot,
            action,
            self.bot.user,
            member,
            reason
        )

        settings = await self.bot.db.fetchrow(
            "SELECT * FROM mod WHERE guild_id = $1",
            guild.id
        )
        
        if settings and settings.get("dm_enabled"):
            try:
                script = settings.get("dm_antiraid")
                
                if not script:
                    embed = Embed(
                        title="Anti-Raid Protection",
                        description=f"You were {punishment}ed due to raid detection",
                        color=discord.Color.red(),
                        timestamp=utcnow()
                    )
                    embed.add_field(
                        name="Server",
                        value=guild.name,
                        inline=True
                    )
                    embed.add_field(
                        name="Reason",
                        value=reason,
                        inline=True
                    )
                    await member.send(embed=embed)
                else:
                    script_obj = EmbedScript(script)
                    await script_obj.send(
                        member,
                        guild=guild,
                        reason=reason,
                        punishment=punishment
                    )
            except (discord.Forbidden, discord.HTTPException):
                pass

    async def do_punishment(
        self,
        guild: Guild,
        member: Member | User,
        *,
        punishment: str,
        reason: str,
    ) -> bool:
        """
        Attempt to punish the member.
        """
        bot_member = guild.get_member(self.bot.user.id)
        if not bot_member:
            return False

        try:
            if punishment == "ban":
                await guild.ban(
                    member,
                    delete_message_days=7,
                    reason=reason,
                )
                await ModConfig.sendlogs(
                    self.bot,
                    "antiraid_ban",
                    bot_member,
                    member,
                    reason
                )
                return True

            elif isinstance(member, User):
                return False

            elif punishment == "kick":
                await member.kick(reason=reason)
                await ModConfig.sendlogs(
                    self.bot,
                    "antiraid kick", 
                    bot_member,
                    member,
                    reason
                )
                return True

            elif punishment == "timeout":
                await member.timeout(
                    duration=timedelta(days=27),
                    reason=reason
                )
                await ModConfig.sendlogs(
                    self.bot,
                    "antiraid timeout",
                    bot_member,
                    member,
                    reason,
                    timedelta(days=27)
                )
                return True

            elif punishment == "strip":
                await member.edit(roles=[], reason=reason)
                await ModConfig.sendlogs(
                    self.bot,
                    "antiraid strip",
                    bot_member,
                    member,
                    reason
                )
                return True

            return False

        except discord.HTTPException:
            return False

    @Cog.listener("on_member_join")
    async def check_raid(self, member: Member) -> None:
        """
        Check for simultaneous joins & default avatars.
        """

        if member.bot:
            return

        config = cast(
            Optional[Dict[str, AmountFlags.Schema]],
            await self.bot.db.fetchrow(
                """
                SELECT *
                FROM antiraid
                WHERE guild_id = $1
                """,
                member.guild.id,
            ),
        )
        if not config:
            return

        elif config["locked"] is True and (config := config["joins"]) is not None:
            punished = await self.do_punishment(
                member.guild,
                member,
                punishment=config["punishment"],
                reason="Server is on lockdown. (ANTIRAID ACTIVE)",
            )

            return log.info(
                "%s %s (%s) during an active raid in %s (%s).",
                "Punished" if punished else "Failed to punish",
                member,
                member.id,
                member.guild,
                member.guild.id,
            )

        elif (
            self.is_default(member.avatar)
            and (avatar := config.get("avatar")) is not None
        ):
            punished = await self.do_punishment(
                member.guild,
                member,
                punishment=avatar["punishment"],
                reason="Default avatar detected",
            )

            return log.debug(
                "Default avatar detected from %s (%s) in %s (%s) [%s].",
                member,
                member.id,
                member.guild,
                member.guild.id,
                "PUNISHED" if punished else "FAILED TO PUNISH",
            )

        elif (
            member.web_status != DiscordStatus.offline
            and all(
                status == DiscordStatus.offline
                for status in [member.mobile_status, member.desktop_status]
            )
            and (browser := config.get("browser")) is not None
        ):
            punished = await self.do_punishment(
                member.guild,
                member,
                punishment=browser["punishment"],
                reason="Spoofed gateway detected (BROWSER)",
            )

            return log.debug(
                "Spoofed gateway detected from %s (%s) in %s (%s) [%s].",
                member,
                member.id,
                member.guild,
                member.guild.id,
                "PUNISHED" if punished else "FAILED TO PUNISH",
            )

        elif not (config := config.get("joins")):
            return

        key = f"sec.joins:{member.guild.id}"

        pipe = self.bot.redis.pipeline()
        pipe.sadd(key, member.id)
        pipe.smembers(key)

        _, member_ids = cast(
            Tuple[bytes, List[bytes]],
            await pipe.execute(),
        )
        members: List[Member] = []

        pipe = self.bot.redis.pipeline()
        now = utcnow()

        for member_id in member_ids:
            m = member.guild.get_member(int(member_id))
            if not m or not m.joined_at:
                pipe.srem(key, member_id)
                continue

            dif = abs((now - m.joined_at).total_seconds())
            if dif >= 15:
                pipe.srem(key, member_id)
                continue

            members.append(m)

        self.bot.loop.create_task(pipe.execute())
        if len(members) < config["amount"]:
            return

        future = self.submit_incident(member.guild, members, config["punishment"])
        self.bot.loop.create_task(future)

        pipe = self.bot.redis.pipeline()
        for member in members:
            if not isinstance(member, Member):
                pipe.srem(key, member.id)
                continue

            await self.do_punishment(
                member.guild,
                member,
                punishment=config["punishment"],
                reason=f"Detected {len(members)}/{config['amount']} simultaneous joins",
            )

    @Cog.listener("on_message")
    async def check_mentions(self, message: Message) -> None:
        """
        Check for mention spam.
        """

        if (
            not message.guild
            or not isinstance(message.author, Member)
            or message.author.bot
            or message.author.guild_permissions.manage_messages
        ):
            return

        mentions = sum(
            not member.bot and member.id != message.author.id
            for member in message.mentions
        )
        if not mentions or mentions <= 2:
            return

        config = cast(
            Optional[AmountFlags.Schema],
            await self.bot.db.fetchval(
                """
                SELECT mentions
                FROM antiraid
                WHERE guild_id = $1
                """,
                message.guild.id,
            ),
        )
        if not config or config and not mentions > config["amount"]:
            return

        punished = await self.do_punishment(
            message.guild,
            message.author,
            punishment=config["punishment"],
            reason=f"Mention spam detected ({mentions}/{config['amount']})",
        )
        log.info(
            "Mention spam detected from %s (%s) in %s (%s) [%s].",
            message.author,
            message.author.id,
            message.guild,
            message.guild.id,
            "PUNISHED" if punished else "FAILED TO PUNISH",
        )

    @antiraid.group(name="filter", invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def antiraid_filter(self, ctx: Context) -> Message:
        """Configure Discord's AutoMod filters."""
        return await ctx.send_help(ctx.command)

    @antiraid_filter.command(name="links", example="(invites/external/all) (on/off) (--punishment delete)")
    @has_permissions(manage_guild=True)
    async def filter_links(
        self,
        ctx: Context,
        filter_type: Literal["invites", "external", "all"],
        status: Annotated[bool, Status],
        *,
        flags: AutomodFlags,
    ) -> Message:
        """Setup Discord AutoMod for link filtering
        
        Types:
        - invites - Only Discord invite links
        - external - Only non-Discord links
        - all - All types of links
        """
        patterns = {
            "invites": [
                r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|com/invite))/[a-zA-Z0-9-]+"
            ],
            "external": [
                r"(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?",
                r"(?:https?://)?(?:\d{1,3}\.){3}\d{1,3}(?:/[^\s]*)?"
            ],
            "all": [
                r"(?:https?://)?(?:www\.)?(?:discord\.(?:gg|com/invite))/[a-zA-Z0-9-]+",
                r"(?:https?://)?(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?",
                r"(?:https?://)?(?:\d{1,3}\.){3}\d{1,3}(?:/[^\s]*)?"
            ]
        }

        try:
            if not status:
                rules = await ctx.guild.fetch_automod_rules()
                for rule in rules:
                    if rule.name == f"Evict - {filter_type.title()} Filter":
                        await rule.delete()
                return await ctx.approve(f"Removed {filter_type} filter")

            actions = [AutoModRuleAction(type=AutoModRuleActionType.block_message)]
            
            if flags.punishment == "timeout":
                actions.append(
                    AutoModRuleAction(
                        type=AutoModRuleActionType.timeout,
                        duration=timedelta(hours=1)
                    )
                )

            trigger = AutoModTrigger(
                type=AutoModRuleTriggerType.keyword,
                regex_patterns=patterns[filter_type]
            )

            exempt_roles = [role for role in ctx.guild.roles if role.permissions.manage_guild]

            rule = await ctx.guild.create_automod_rule(
                name=f"Evict - {filter_type.title()} Filter",
                event_type=AutoModRuleEventType.message_send,
                trigger=trigger,
                actions=actions,
                enabled=True,
                exempt_roles=exempt_roles,
                reason="Created via Evict antiraid filter command"
            )
            return await ctx.approve(f"Created {filter_type} filter with **{flags.punishment}** punishment")

        except discord.Forbidden:
            return await ctx.warn("I need `manage_guild` permissions to manage AutoMod rules")
        except discord.HTTPException as e:
            return await ctx.warn(f"Failed to manage AutoMod rule: {e}")

    @antiraid_filter.group(name="exempt", aliases=["whitelist"], invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def filter_exempt(self, ctx: Context) -> Message:
        """Manage role exemptions for AutoMod filters"""
        return await ctx.send_help(ctx.command)

    @filter_exempt.command(name="add")
    @has_permissions(manage_guild=True)
    async def exempt_add(self, ctx: Context, target: Union[Role, Member]) -> Message:
        """Add a role or member to be exempt from AutoMod filters
        
        target: Can be either a role or member mention/ID"""
        try:
            rules = await ctx.guild.fetch_automod_rules()
            updated = False
            
            for rule in rules:
                if rule.name.startswith("Evict -"):
                    if isinstance(target, Role):
                        if target not in rule.exempt_roles:
                            await rule.edit(exempt_roles=[*rule.exempt_roles, target])
                            updated = True
                    else:  
                        if target not in rule.exempt_users:
                            await rule.edit(exempt_users=[*rule.exempt_users, target])
                            updated = True
            
            if updated:
                return await ctx.approve(f"Added {target.mention} to filter exemptions")
            else:
                return await ctx.warn("No active filter rules found")

        except discord.Forbidden:
            return await ctx.warn("I need `manage_guild` permissions to manage AutoMod rules")
        except discord.HTTPException as e:
            return await ctx.warn(f"Failed to update exemptions: {e}")

    @filter_exempt.command(name="remove")
    @has_permissions(manage_guild=True)
    async def exempt_remove(self, ctx: Context, role: Role) -> Message:
        """Remove a role's exemption from AutoMod filters"""
        try:
            rules = await ctx.guild.fetch_automod_rules()
            updated = False
            
            for rule in rules:
                if rule.name.startswith("Evict -"):
                    if role.id in rule.exempt_roles:
                        await rule.edit(exempt_roles=[r for r in rule.exempt_roles if r != role.id])
                        updated = True
            
            if updated:
                return await ctx.approve(f"Removed {role.mention} from filter exemptions")
            else:
                return await ctx.warn("Role was not exempt from any filters")

        except discord.Forbidden:
            return await ctx.warn("I need `manage_guild` permissions to manage AutoMod rules")
        except discord.HTTPException as e:
            return await ctx.warn(f"Failed to update exemptions: {e}")

    @filter_exempt.command(name="list")
    @has_permissions(manage_guild=True)
    async def exempt_list(self, ctx: Context) -> Message:
        """List all roles exempt from AutoMod filters"""
        try:
            rules = await ctx.guild.fetch_automod_rules()
            exempt_roles = set()
            
            for rule in rules:
                if rule.name.startswith("Evict -"):
                    exempt_roles.update(rule.exempt_roles)
            
            if not exempt_roles:
                return await ctx.warn("No roles are exempt from filters")
            
            roles = [ctx.guild.get_role(role_id) for role_id in exempt_roles]
            roles = [role.mention for role in roles if role]
            
            return await ctx.approve(
                "Exempt roles:",
                "\n".join(roles) if roles else "No valid exempt roles found"
            )

        except discord.Forbidden:
            return await ctx.warn("I need `manage_guild` permissions to manage AutoMod rules")
        except discord.HTTPException as e:
            return await ctx.warn(f"Failed to fetch exemptions: {e}")