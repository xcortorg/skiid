from discord.ext.commands import (
    command,
    Cog,
    group,
    parameter,
    UserConverter,
    has_permissions,
    cooldown,
    flag,
    CommandError,
    Range,
    BasicFlags,
    max_concurrency,
    BucketType,
)
from datetime import timedelta
from asyncio import gather
from discord import (
    Member,
    VoiceChannel,
    StageChannel,
    Thread,
    User,
    HTTPException,
    Permissions,
    PermissionOverwrite,
    Guild,
    NotFound,
    Message,
    Forbidden,
    Embed,
    TextChannel,
    Role,
)
from humanfriendly import format_timespan

from time import perf_counter
from typing import Annotated, Callable, List, Literal, Optional, cast
from discord.utils import format_dt, utcnow, sleep_until
from contextlib import suppress
from asyncio import Lock
from discord.ext import tasks
from system.tools.converters import (
    CustomFlagConverter,
)
from system import Marly
from config import Emojis, Color, Marly
from system.base.context import Context
from system.base.embed import EmbedScriptValidator, EmbedScript
from system.tools.converters.Member import TouchableMember, StrictRole
from system.tools.utils import Plural, Duration
from .classes import ModConfig
from .logging import Logging
from .logging.enums import LogType
from .thread.thread import Thread
from .nuke.nuke import Nuke
import config


class ModerationFlags(BasicFlags):
    silent: bool = False


class Moderation(Thread, Logging, Nuke, Cog):
    def __init__(self, bot: "Marly"):
        self.bot = bot
        self.case_lock = Lock()

    async def moderation_entry(
        self: "Moderation",
        ctx: Context,
        target: Member | User | Role | TextChannel | str,
        action: str,
        reason: str = "no reason provided",
    ):
        """Create a log entry for moderation actions."""
        settings = await ctx.settings.fetch(self.bot, ctx.guild)
        channel = ctx.guild.get_channel(settings.mod_log)
        if not channel:
            return

        async with self.case_lock:
            case = await self.bot.db.fetchval(
                "SELECT COALESCE(MAX(case_id), 0) + 1 FROM cases WHERE guild_id = $1",
                ctx.guild.id,
            )

            if type(target) in (Member, User):
                _TARGET = "Member"
            elif type(target) is Role:
                _TARGET = "Role"
            elif type(target) is TextChannel:
                _TARGET = "Channel"
            else:
                _TARGET = "Target"

            embed = Embed(
                description=format_dt(utcnow(), "F")
                + " ("
                + format_dt(utcnow(), "R")
                + ")",
                color=config.Color.baseColor,
            )
            embed.add_field(
                name=f"**Case #{case:,} | {action.title()}** ",
                value=f"""
                > **Moderator:** {ctx.author} \n> {ctx.author.mention} (`{ctx.author.id}`)
                > **{_TARGET}:** {target} \n> {target.mention} (`{target.id}`)
                > **Reason:** {reason}
                """,
            )
            embed.set_author(
                name=f"Modlog Entry | {ctx.author.name}",
                icon_url=ctx.author.display_avatar.url,
            )

            try:
                message = await channel.send(embed=embed)
            except Forbidden:
                return await self.bot.db.execute(
                    "UPDATE settings SET mod_log = $1 WHERE guild_id = $2",
                    None,
                    ctx.guild.id,
                )

            await self.bot.db.execute(
                "INSERT INTO cases (guild_id, case_id, case_type, message_id, moderator_id, target_id, moderator, target, reason, timestamp)"
                " VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)",
                ctx.guild.id,
                case,
                action.lower(),
                message.id,
                ctx.author.id,
                target.id,
                str(ctx.author),
                str(target),
                reason,
                message.created_at,
            )

    def create_mod_action_embed(
        self, action: str, guild, moderator, reason: str
    ) -> Embed:
        """
        Creates a standardized embed for moderation actions
        """
        in_actions = {"warned", "jailed", "muted"}

        preposition = "in" if action.lower() in in_actions else "from"

        embed = Embed(
            title=action.title(),
            description=f"> You've been {action.lower()} {preposition} {guild.name}",
            color=config.Color.dm_yellow,
            timestamp=utcnow(),
        )
        embed.set_author(name=guild.name, icon_url=guild.icon)
        embed.add_field(name="Moderator", value=moderator)
        embed.add_field(name="Reason", value=reason)
        embed.set_thumbnail(url=guild.icon)
        return embed

    async def setup_mod_role_permissions(self, guild, roles):
        """
        Set up moderation role permissions for all channels
        """
        jail_role, image_mute_role, mute_role, reaction_mute_role = roles

        permission_tasks = []
        for channel in guild.channels:
            try:
                permission_tasks.extend(
                    [
                        channel.set_permissions(
                            jail_role,
                            view_channel=False,
                            reason="Moderation system setup",
                        ),
                        channel.set_permissions(
                            mute_role,
                            send_messages=False,
                            reason="Moderation system setup",
                        ),
                        channel.set_permissions(
                            image_mute_role,
                            attach_files=False,
                            embed_links=False,
                            reason="Moderation system setup",
                        ),
                        channel.set_permissions(
                            reaction_mute_role,
                            add_reactions=False,
                            use_external_emojis=False,
                            reason="Moderation system setup",
                        ),
                    ]
                )
            except Exception as e:
                print(f"Failed to create permission tasks for {channel.name}: {e}")
                continue

        if permission_tasks:
            await gather(*permission_tasks, return_exceptions=True)

    async def check_silent_mode(self, ctx: Context) -> bool:
        """
        Check if silent mode is enabled for the guild
        """
        settings = await ctx.settings.fetch(self.bot, ctx.guild)
        return settings.invoke_silent_mode

    @Cog.listener()
    async def on_member_join(self, member: Member):
        """
        Reapply jail role if member was jailed before leaving
        """
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM settings WHERE guild_id = $1", member.guild.id
        )
        if not settings or not settings["mod_log"]:
            return

        # Check if user was jailed
        is_jailed = await self.bot.db.fetchrow(
            "SELECT * FROM jailed WHERE guild_id = $1 AND user_id = $2",
            member.guild.id,
            member.id,
        )

        if is_jailed:
            jail_role = member.guild.get_role(settings["jail_role"])
            jail_channel = member.guild.get_channel(settings["jail_channel"])

            if jail_role:
                try:
                    await member.add_roles(
                        jail_role, reason="Reapplying jail role after rejoin"
                    )

                    if jail_channel:
                        await jail_channel.send(
                            f"{member.mention} you have been re-jailed as you left while jailed."
                        )
                except HTTPException as e:
                    print(f"Failed to reapply jail role to {member}: {e}")

    @Cog.listener()
    async def on_guild_channel_create(self, channel):
        """
        Add moderation role permissions to newly created channels
        """
        settings = await self.bot.db.fetchrow(
            "SELECT * FROM settings WHERE guild_id = $1", channel.guild.id
        )
        if not settings or not settings["mod_log"]:
            return
        roles = [
            channel.guild.get_role(settings["jail_role"]),
            channel.guild.get_role(settings["mute_role"]),
            *[
                channel.guild.get_role(role_id)
                for role_id in settings["image_mute_role_id"]
            ],
            channel.guild.get_role(settings["reaction_mute_role"]),
        ]

        roles = [role for role in roles if role is not None]

        if not roles:
            return
        try:
            await gather(
                *[
                    channel.set_permissions(
                        roles[0],
                        view_channel=False,
                        reason="Automatic moderation role setup",
                    ),
                    channel.set_permissions(
                        roles[1],
                        send_messages=False,
                        reason="Automatic moderation role setup",
                    ),
                    *[
                        channel.set_permissions(
                            role,
                            attach_files=False,
                            embed_links=False,
                            reason="Automatic moderation role setup",
                        )
                        for role in roles[2:-1]
                    ],  # Image mute roles
                    channel.set_permissions(
                        roles[-1],
                        add_reactions=False,
                        use_external_emojis=False,
                        reason="Automatic moderation role setup",
                    ),
                ]
            )
        except Exception as e:
            print(f"Failed to set permissions in {channel.name}: {e}")

    @command(aliases=["setme"])
    @has_permissions(administrator=True)
    @cooldown(1, 60, BucketType.user)
    async def setup(self, ctx: Context):
        """
        Start process for setting up the moderation system
        """
        settings = await ctx.settings.fetch(self.bot, ctx.guild)

        if settings.mod_log:
            raise CommandError(
                "The moderation system is **already** enabled in this server!"
            )

        await ctx.typing()

        try:
            roles = await gather(
                ctx.guild.create_role(name="jail"),
                ctx.guild.create_role(name="imuted"),
                ctx.guild.create_role(name="muted"),
                ctx.guild.create_role(name="rmuted"),
            )
        except Exception as e:
            raise CommandError(f"Failed to create roles: {e}")

        # Set up permissions for all channels
        await self.setup_mod_role_permissions(ctx.guild, roles)

        jail_role, image_mute_role, mute_role, reaction_mute_role = roles

        overwrite = {
            jail_role: PermissionOverwrite(view_channel=True),
            ctx.guild.default_role: PermissionOverwrite(view_channel=False),
        }

        over = {ctx.guild.default_role: PermissionOverwrite(view_channel=False)}

        try:
            category = await ctx.guild.create_category(
                name=f"{self.bot.user.name} moderation", overwrites=over
            )

            text, jail, logs = await gather(
                ctx.guild.create_text_channel(
                    name="mod-logs", overwrites=over, category=category
                ),
                ctx.guild.create_text_channel(
                    name="jail", overwrites=overwrite, category=category
                ),
                ctx.guild.create_text_channel(
                    name="server-logs", overwrites=over, category=category
                ),
            )
        except Exception as e:
            raise CommandError(f"Failed to create channels: {e}")

        try:
            await gather(
                ctx.settings.update(
                    mod_log=text.id,
                    jail_channel=jail.id,
                    jail_role=jail_role.id,
                    image_mute_role_id=[image_mute_role.id],
                    mute_role=mute_role.id,
                    reaction_mute_role=reaction_mute_role.id,
                ),
                self.bot.db.execute(
                    "INSERT INTO cases VALUES ($1,$2) ON CONFLICT DO NOTHING",
                    ctx.guild.id,
                    0,
                ),
                # Enable all logging events for the server-logs channel
                self.bot.db.execute(
                    """
                    INSERT INTO logging (guild_id, channel_id, events)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, channel_id) 
                    DO UPDATE SET events = EXCLUDED.events
                    """,
                    ctx.guild.id,
                    logs.id,
                    LogType.ALL(),
                ),
            )
        except Exception as e:
            raise CommandError(f"Failed to update settings: {e}")

        return await ctx.approve(
            "**Moderation system** set up has been **completed**. Please make sure that all of your channels and roles have been configured properly."
        )

    @command(aliases=["removeme", "resetme", "unset"])
    @has_permissions(administrator=True)
    @cooldown(1, 60, BucketType.user)
    async def reset(self, ctx: Context):
        """Remove the moderation system setup"""
        settings = await ctx.settings.fetch(self.bot, ctx.guild)

        if not settings.mod_log:
            raise CommandError(
                "The **moderation system** is not enabled in this server!"
            )

        await ctx.prompt(
            "Are you sure you want to remove the **moderation system**?",
            "This will delete all moderation channels, roles, and cases!",
        )

        await ctx.typing()

        try:
            mod_channel = ctx.guild.get_channel(settings.mod_log)
            if mod_channel and mod_channel.category:
                category = mod_channel.category

                await gather(
                    *[channel.delete() for channel in category.channels],
                    category.delete(),
                )

            role_deletion_tasks = []
            for role_id in [
                settings.jail_role,
                settings.mute_role,
                settings.reaction_mute_role,
                *settings.image_mute_role_id,
            ]:
                if role := ctx.guild.get_role(role_id):
                    role_deletion_tasks.append(role.delete())

            await gather(
                *role_deletion_tasks,
                ctx.settings.update(
                    mod_log=None,
                    jail_channel=None,
                    jail_role=None,
                    mute_role=None,
                    reaction_mute_role=None,
                    image_mute_role_id=[],
                ),
                self.bot.db.execute(
                    "DELETE FROM cases WHERE guild_id = $1", ctx.guild.id
                ),
            )

            return await ctx.approve(
                "**Moderation system** has been successfully **removed** from this server."
            )

        except Exception as e:
            raise CommandError(
                f"An error occurred while removing the moderation system: {str(e)}"
            )

    @command(
        name="mute",
        usage="(member) (reason)",
        example="johndoe spamming",
        aliases=["m"],
    )
    @ModConfig.is_mod_configured()
    @has_permissions(moderate_members=True)
    async def mute(
        self, ctx: Context, member: Member, *, reason: str = "No reason provided"
    ):
        """
        Mute a member, preventing them from sending messages.
        """
        # Check if the mute role exists
        mute_role = ctx.guild.get_role(ctx.settings.mute_role)
        if not mute_role:
            return await ctx.warn("Mute role not found!")

        # Check if the member is already muted
        if mute_role in member.roles:
            return await ctx.warn(f"{member.mention} is already muted!")

        await member.add_roles(mute_role, reason=f"{ctx.author}: {reason}")
        action = "Muted"

        await self.moderation_entry(ctx, member, action, reason)

        if ctx.settings.invoke_mute_dm:
            script = EmbedScript(ctx.settings.invoke_mute_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                action.lower(), ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been {action.lower()}d for {reason}. I couldn't DM you more information."
                )

        if ctx.settings.invoke_mute_message:
            script = EmbedScript(ctx.settings.invoke_mute_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        name="unmute",
        usage="(member) (reason)",
        example="johndoe behavior improved",
        aliases=["um"],
    )
    @ModConfig.is_mod_configured()
    @has_permissions(moderate_members=True)
    async def unmute(
        self, ctx: Context, member: Member, *, reason: str = "No reason provided"
    ):
        """
        Unmute a member, allowing them to send messages.
        """
        mute_role = ctx.guild.get_role(ctx.settings.mute_role)
        if not mute_role:
            return await ctx.warn("Mute role not found!")
        if mute_role not in member.roles:
            return await ctx.warn(f"{member.mention} is not muted!")

        await member.remove_roles(mute_role, reason=f"{ctx.author}: {reason}")
        action = "Unmuted"

        await self.moderation_entry(ctx, member, action, reason)

        if ctx.settings.invoke_unmute_dm:
            script = EmbedScript(ctx.settings.invoke_unmute_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                action.lower(), ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been {action.lower()}d for {reason}. I couldn't DM you more information."
                )

        # Send channel message if configured
        if ctx.settings.invoke_unmute_message:
            script = EmbedScript(ctx.settings.invoke_unmute_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @group(
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
            reason=f"{ctx.author} ({ctx.author.id}) / {reason}",
        )

        # Add moderation entry
        await self.moderation_entry(ctx, member, "Timedout", reason)

        if ctx.settings.invoke_timeout_dm:
            script = EmbedScript(ctx.settings.invoke_timeout_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
                duration=format_timespan(duration),
                expires=format_dt(utcnow() + duration, "R"),
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                "timed out", ctx.guild, ctx.author, reason
            )
            embed.add_field(name="Duration", value=format_timespan(duration))
            embed.add_field(name="Expires", value=format_dt(utcnow() + duration, "R"))
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been timed out for {reason}. I couldn't DM you more information."
                )

        if ctx.settings.invoke_timeout_message:
            script = EmbedScript(
                ctx.settings.invoke_timeout_message,
                [
                    ctx.guild,
                    ctx.channel,
                    member,
                    (reason, "reason"),
                    (ctx.author, "moderator"),
                    (format_timespan(duration), "duration"),
                    (format_dt(utcnow() + duration, "R"), "expires"),
                    (str(int((utcnow() + duration).timestamp())), "expires_timestamp"),
                ],
            )
            with suppress(HTTPException):
                return await script.send(ctx)

        return await ctx.thumbsup()

    @timeout.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(moderate_members=True)
    async def timeout_list(self, ctx: Context) -> Message:
        """
        View all timed out members.
        """

        members = list(
            filter(
                lambda member: member.is_timed_out(),
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn("No members are currently timed out!")

        description = [
            f"{member.mention} - expires {format_dt(member.timed_out_until or utcnow(), 'R')}"
            for member in sorted(
                members,
                key=lambda member: member.timed_out_until or utcnow(),
            )
        ]

        embed = Embed(
            title="Timed Out Members",
        )

        return await ctx.autopaginator(
            embed=embed,
            description=description,
            split=10,
        )

    @group(
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

        # Add moderation entry
        await self.moderation_entry(ctx, member, "Untimedout", reason)

        if ctx.settings.invoke_untimeout_dm:
            script = EmbedScript(ctx.settings.invoke_untimeout_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                "removed from timeout", ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} your timeout has been removed for {reason}. I couldn't DM you more information."
                )

        if ctx.settings.invoke_untimeout_message:
            script = EmbedScript(
                ctx.settings.invoke_untimeout_message,
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

        return await ctx.thumbsup()

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

    @command(
        aliases=["imute"],
        usage="(member) (reason)",
        example="johndoe being mean",
    )
    @ModConfig.is_mod_configured()
    @has_permissions(moderate_members=True)
    async def imagemute(
        self,
        ctx: Context,
        member: Annotated[Member, TouchableMember],
        *,
        reason: str = "No reason provided",
    ):
        """
        Remove a member's attach files & embed links permission
        """
        is_muted = any(role in member.roles for role in ctx.settings.image_mute_role)

        if is_muted:
            await member.remove_roles(*ctx.settings.image_mute_role)
            action = "Image Unmuted"
        else:
            await member.add_roles(*ctx.settings.image_mute_role)
            action = "Image Muted"

        await self.moderation_entry(ctx, member, action, reason)

        if ctx.settings.invoke_mute_dm:
            script = EmbedScript(ctx.settings.invoke_mute_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                action.lower(), ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been {action.lower()}d for {reason}. I couldn't DM you more information."
                )

        if ctx.settings.invoke_mute_message:
            script = EmbedScript(ctx.settings.invoke_mute_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        aliases=["iunmute"],
        usage="(member) (reason)",
        example="johndoe behavior improved",
    )
    @ModConfig.is_mod_configured()
    @has_permissions(moderate_members=True)
    async def imageunmute(
        self,
        ctx: Context,
        member: Annotated[Member, TouchableMember],
        *,
        reason: str = "No reason provided",
    ):
        """
        Restore a member's attach files & embed links permission
        """

        has_mute_role = any(
            role in member.roles for role in ctx.settings.image_mute_role
        )

        if not has_mute_role:
            return await ctx.warn(f"{member.mention} is not image muted!")

        await member.remove_roles(*ctx.settings.image_mute_role)
        action = "Image Unmuted"

        await self.moderation_entry(ctx, member, action, reason)

        if ctx.settings.invoke_iunmute_message:
            script = EmbedScript(ctx.settings.invoke_iunmute_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        aliases=["rmute"],
        usage="(member) (reason)",
        example="johndoe spamming reactions",
    )
    @ModConfig.is_mod_configured()
    @has_permissions(moderate_members=True)
    async def reactionmute(
        self,
        ctx: Context,
        member: Annotated[Member, TouchableMember],
        *,
        reason: str = "No reason provided",
    ):
        """
        Remove a member's ability to add reactions and use external emojis
        """
        reaction_role = ctx.guild.get_role(ctx.settings.reaction_mute_role)
        if not reaction_role:
            return await ctx.warn("Reaction mute role not found!")

        if reaction_role in member.roles:
            await member.remove_roles(reaction_role)
            action = "Reaction Unmuted"
            dm_message = ctx.settings.invoke_runmute_dm
            channel_message = ctx.settings.invoke_runmute_message
        else:
            await member.add_roles(reaction_role)
            action = "Reaction Muted"
            dm_message = ctx.settings.invoke_rmute_dm
            channel_message = ctx.settings.invoke_rmute_message

        await self.moderation_entry(ctx, member, action, reason)

        if dm_message:
            script = EmbedScript(dm_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                action.lower(), ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been {action.lower()}d for {reason}. I couldn't DM you more information."
                )

        if channel_message:
            script = EmbedScript(channel_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        aliases=["runmute"],
        usage="(member) (reason)",
        example="johndoe behavior improved",
    )
    @ModConfig.is_mod_configured()
    @has_permissions(moderate_members=True)
    async def reactionunmute(
        self,
        ctx: Context,
        member: Annotated[Member, TouchableMember],
        *,
        reason: str = "No reason provided",
    ):
        """
        Restore a member's ability to add reactions and use external emojis
        """
        reaction_role = ctx.guild.get_role(ctx.settings.reaction_mute_role)
        if not reaction_role:
            return await ctx.warn("Reaction mute role not found!")

        if reaction_role not in member.roles:
            return await ctx.warn(f"{member.mention} is not reaction muted!")

        await member.remove_roles(reaction_role)
        action = "Reaction Unmuted"

        await self.moderation_entry(ctx, member, action, reason)

        if ctx.settings.invoke_iunmute_message:
            script = EmbedScript(ctx.settings.invoke_iunmute_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        name="warn",
        usage="(member) [reason] [--silent]",
        example="johndoe Being mean --silent",
        flag=ModerationFlags,
    )
    @ModConfig.is_mod_configured()
    @cooldown(1, 3, BucketType.user)
    @has_permissions(manage_messages=True)
    async def warn(
        self,
        ctx: Context,
        member: Annotated[Member, TouchableMember],
        reason: str = "No reason provided",
    ):
        """
        Warns the mentioned user
        """
        flags = cast(ModerationFlags, ctx.flag)

        await self.moderation_entry(ctx, member, "Warn", reason)

        if flags.silent or await self.check_silent_mode(ctx):
            await ctx.send(f"{member.mention} has been warned silently.")
            return

        if ctx.settings.invoke_warn_dm:
            script = EmbedScript(ctx.settings.invoke_warn_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                "warned", ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been warned for {reason}. I couldn't DM you more information."
                )

        if ctx.settings.invoke_warn_message:
            script = EmbedScript(ctx.settings.invoke_warn_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        name="kick",
        usage="(member) <reason>",
        example="johndoe trolling",
        aliases=["boot", "k"],
        flag=ModerationFlags,
    )
    @ModConfig.is_mod_configured()
    @has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: Context,
        member: Annotated[Member, TouchableMember],
        *,
        reason: str = "No reason provided",
    ):
        """
        Kick a member from the server
        """
        flags = cast(ModerationFlags, ctx.flag)

        if member.premium_since:
            await ctx.prompt(
                "Are you sure you want to kick {member.mention}?",
                "They're currently **boosting** the server",
            )

        try:
            await ctx.guild.kick(member, reason=f"{ctx.author}: {reason}")
        except Forbidden:
            raise CommandError(f"I don't have **permissions** to kick {member.mention}")

        await self.moderation_entry(ctx, member, "Kick", reason)
        if flags.silent or await self.check_silent_mode(ctx):
            await ctx.send(f"{member.mention} has been kicked silently.")
            return

        if ctx.settings.invoke_kick_dm:
            script = EmbedScript(ctx.settings.invoke_kick_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                "kicked", ctx.guild, ctx.author, reason
            )
            with suppress(HTTPException):
                await member.send(embed=embed)

        if ctx.settings.invoke_kick_message:
            script = EmbedScript(ctx.settings.invoke_kick_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        await ctx.thumbsup()

    @group(
        name="ban",
        usage="(user) <delete history> <reason>",
        example="johndoe 1 Threatening members",
        aliases=["b"],
        notes="1-7 not 1d-7d",
        invoke_without_command=True,
    )
    @ModConfig.is_mod_configured()
    @has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: Context,
        user: Annotated[Member | User, TouchableMember],
        delete_history: Optional[Range[int, 0, 7]] = parameter(
            default=lambda ctx: ctx.settings.ban_delete_days
        ),
        *,
        reason: str = "No reason provided",
    ):
        """Ban a member from the server"""
        if isinstance(user, Member):
            await TouchableMember().check(ctx, user)
            if user.premium_since:
                await ctx.prompt(
                    f"Are you sure you want to **ban** {user.mention}?",
                    "They are currently **boosting** the server",
                )

        if ctx.settings.invoke_ban_dm:
            script = EmbedScript(ctx.settings.invoke_ban_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=user,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(user)
        else:
            embed = self.create_mod_action_embed(
                "banned", ctx.guild, ctx.author, reason
            )
            with suppress(HTTPException):
                await user.send(embed=embed)

        try:
            await ctx.guild.ban(
                user,
                reason=f"{ctx.author}: {reason}",
                delete_message_days=delete_history or 0,
            )
        except Forbidden:
            raise CommandError(f"I don't have **permissions** to ban {user.mention}")

        await self.moderation_entry(ctx, user, "Ban", reason)

        if ctx.settings.invoke_ban_message:
            script = EmbedScript(ctx.settings.invoke_ban_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=user,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        await ctx.thumbsup()

    @ban.command(
        name="recent",
        aliases=["list"],
    )
    @has_permissions(ban_members=True)
    async def ban_recent(self, ctx: Context):
        """
        View recently banned users
        """
        try:
            bans = [entry async for entry in ctx.guild.bans(limit=10)]
        except Forbidden:
            raise CommandError("I don't have permission to view bans")

        if not bans:
            raise CommandError("No recent bans found")

        embed = Embed(
            title="Recent Bans",
            color=config.Color.baseColor,
            timestamp=utcnow(),
        )

        descriptions = []
        for entry in bans:
            user = entry.user
            descriptions.append(
                f"**{user}** (`{user.id}`)\n"
                f"> **Reason:** {entry.reason or 'No reason provided'}\n"
            )

        await ctx.autopaginator(embed=embed, description=descriptions, split=5)

    @ban.command(
        name="purge",
        usage="(delete history)",
        example="3",
    )
    @has_permissions(ban_members=True, manage_guild=True)
    async def ban_purge(
        self,
        ctx: Context,
        delete_history: Range[int, 0, 7],
    ):
        """
        Set default message history purge upon ban
        """
        await ctx.prompt(
            f"u sure you want to set the **purge period** to **`{delete_history}`** days?",
            "This will affect all future bans",
        )

        await self.bot.db.execute(
            """UPDATE settings 
               SET ban_delete_days = $1 
               WHERE guild_id = $2""",
            delete_history,
            ctx.guild.id,
        )

        return await ctx.approve(
            f"Set **default purge period** to **`{delete_history}`** days"
        )

    @command(
        name="unban",
        usage="(user) <reason>",
        example="johndoe appealed",
        aliases=["ub"],
        notes="Generates one-time use invite for member",
    )
    @ModConfig.is_mod_configured()
    @has_permissions(ban_members=True)
    async def unban(
        self,
        ctx: Context,
        user: User,
        *,
        reason: str = "No reason provided",
    ):
        """
        Unban a user from the server
        """
        try:
            ban_entry = await ctx.guild.fetch_ban(user)
        except NotFound:
            raise CommandError(f"**{user}** is not banned from this server")

        try:
            await ctx.guild.unban(user, reason=f"{ctx.author}: {reason}")
        except Forbidden:
            raise CommandError(f"I don't have **permissions** to unban {user.mention}")

        try:
            invite = await ctx.channel.create_invite(
                max_uses=1,
                max_age=86400,  # 24 hours
                reason=f"One-time use invite for unbanned user: {user}",
            )
        except Forbidden:
            invite = None

        if ctx.settings.invoke_unban_dm:
            script = EmbedScript(ctx.settings.invoke_unban_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=user,
                moderator=ctx.author,
                reason=reason,
            )
            try:
                await script.send(user)
                if invite:
                    await user.send(
                        f"Here's your invite link to rejoin {ctx.guild.name}: {invite.url}"
                    )
            except Forbidden:
                await ctx.send(
                    f"{user} has been unbanned from {ctx.guild.name}. I couldn't DM the user more information."
                )
            except HTTPException:
                pass
        else:
            embed = self.create_mod_action_embed(
                "unbanned", ctx.guild, ctx.author, reason
            )
            if invite:
                embed.add_field(name="Invite Link", value=invite.url, inline=False)
            try:
                await user.send(embed=embed)
            except (Forbidden, HTTPException):
                await ctx.send(
                    f"{user} has been unbanned from {ctx.guild.name}. I couldn't DM the user more information."
                )

        await self.moderation_entry(ctx, user, "Unban", reason)

        if ctx.settings.invoke_unban_message:
            script = EmbedScript(ctx.settings.invoke_unban_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=user,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        await ctx.thumbsup()

    @group(
        name="unbanall",
        aliases=["uball"],
        brief="server owner",
        invoke_without_command=True,
    )
    @max_concurrency(1, BucketType.guild)
    @has_permissions(guild_owner=True)
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
            f"Are you sure you want to unban {Plural(users, md='`'):user}?",
        )

        async with ctx.typing():
            for user in users:
                with suppress(HTTPException):
                    await ctx.guild.unban(
                        user, reason=f"{ctx.author} ({ctx.author.id}) / UNBAN ALL"
                    )

        return await ctx.add_check()

    @unban_all.command(
        name="cancel",
        aliases=["stop"],
        brief="server owner",
    )
    @has_permissions(guild_owner=True)
    async def unban_all_cancel(self, ctx: Context) -> Message:
        """
        Cancel any pending unban all operations.
        """
        if not ctx.command.parent._max_concurrency.get_bucket(ctx).is_active():
            return await ctx.warn("There is no active **unban all** operation!")

        ctx.command.parent._max_concurrency.get_bucket(ctx).reset()

        return await ctx.approve("Cancelled the **unban all** operation")

    @group(
        name="history",
        usage="(user)",
        example="johndoe",
        invoke_without_command=True,
    )
    @has_permissions(manage_messages=True)
    async def history(self, ctx: Context, *, user: Member | User):
        """View punishment history for a user"""
        cases = await self.bot.db.fetch(
            "SELECT * FROM cases WHERE guild_id = $1 AND target_id = $2 ORDER BY case_id DESC",
            ctx.guild.id,
            user.id,
        )
        if not cases:
            return await ctx.neutral(
                f" No **moderation actions** have been recorded for {user.mention}",
                emoji=":mag_right:",
            )

        embed = Embed(
            title=f"Punishment History for {user}",
            color=config.Color.baseColor,
            timestamp=utcnow(),
        )

        descriptions = []
        for case in cases:
            moderator = self.bot.get_user(case["moderator_id"])
            moderator_display = moderator.name if moderator else case["moderator"]

            descriptions.append(
                f"**Case Log #{case['case_id']} | {case['case_type'].title()}**\n"
                f"> **When:** {format_dt(case['timestamp'], 'F')} ({format_dt(case['timestamp'], 'R')})\n"
                f"> **Moderator:** {moderator_display}\n"
                f"> **Reason:** {case['reason']}\n"
            )

        await ctx.autopaginator(embed, descriptions, split=2)

    @history.command(
        name="remove",
        usage="(user) (case ID)",
        example="johndoe 2",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_messages=True)
    async def history_remove(
        self,
        ctx: Context,
        user: Member | User,
        case_id: int,
    ):
        """Remove a punishment from a user's history"""
        if not (
            await self.bot.db.fetchrow(
                "SELECT * FROM cases WHERE guild_id = $1 AND target_id = $2 AND case_id = $3",
                ctx.guild.id,
                user.id,
                case_id,
            )
        ):
            raise CommandError(
                f"Couldn't find a **case** with the ID `{case_id}` for **{user}**"
            )

        await self.bot.db.execute(
            "DELETE FROM cases WHERE guild_id = $1 AND target_id = $2 AND case_id = $3",
            ctx.guild.id,
            user.id,
            case_id,
        )

        return await ctx.thumbsup()

    @history.command(
        name="reset",
        usage="(user)",
        example="johndoe",
        aliases=["clear"],
    )
    @has_permissions(manage_messages=True)
    async def history_reset(self, ctx: Context, user: Member | User):
        """
        Reset a user's punishment history
        """
        await ctx.prompt(
            f"Are you sure you want to **reset** all punishment history for **{user}**?"
        )

        cases = await self.bot.db.fetch(
            "SELECT * FROM cases WHERE guild_id = $1 AND target_id = $2",
            ctx.guild.id,
            user.id,
        )

        if not cases:
            raise CommandError(f"**{user}** doesn't have any **cases** in this server")

        await self.bot.db.execute(
            "DELETE FROM cases WHERE guild_id = $1 AND target_id = $2",
            ctx.guild.id,
            user.id,
        )
        return await ctx.react_check()

    @command(
        name="reason",
        usage="<case ID> (reason)",
        example="User was spamming",
        aliases=["rsn"],
    )
    @has_permissions(manage_messages=True)
    async def reason(self, ctx: Context, case_id: int | None, *, reason: str):
        """
        Update a moderation case reason
        """
        case = await self.bot.db.fetchrow(
            "SELECT * FROM cases WHERE guild_id = $1 AND (case_id = $2 OR case_id = (SELECT MAX(case_id) FROM cases WHERE guild_id = $1))",
            ctx.guild.id,
            case_id or 0,
        )
        if not case:
            raise CommandError("There aren't any **cases** in this server")
        if case_id and case["case_id"] != case_id:
            raise CommandError(f"Couldn't find a **case** with the ID `{case_id}`")

        with suppress(Exception):
            mod_log = await self.bot.db.fetchval(
                "SELECT mod_log FROM config WHERE guild_id = $1", ctx.guild.id
            )
            if channel := self.bot.get_channel(mod_log):
                message = await channel.fetch_message(case["message_id"])

                embed = message.embeds[0]
                field = embed.fields[0]
                embed.set_field_at(
                    0,
                    name=field.name,
                    value=(
                        field.value.replace(
                            f"**Reason:** {case['reason']}",
                            f"**Reason:** {reason}",
                        )
                    ),
                )
                await message.edit(embed=embed)
        await self.bot.db.execute(
            "UPDATE cases SET reason = $3 WHERE guild_id = $1 AND case_id = $2",
            ctx.guild.id,
            case["case_id"],
            reason,
        )
        return await self.invoke_message(
            ctx, ctx.add_check, case_id=case["case_id"], reason=reason
        )

    @command(
        name="case",
        usage="(case ID)",
        example="1",
        aliases=["viewcase"],
    )
    @has_permissions(manage_messages=True)
    async def case(self, ctx: Context, case_id: int):
        """
        View details about a specific moderation case
        """
        case = await self.bot.db.fetchrow(
            "SELECT * FROM cases WHERE guild_id = $1 AND case_id = $2",
            ctx.guild.id,
            case_id,
        )

        if not case:
            raise CommandError(f"Couldn't find a **case** with the ID `{case_id}`")

        moderator = self.bot.get_user(case["moderator_id"])
        moderator_display = moderator.name if moderator else case["moderator"]

        target_id = case["target_id"]
        target = await self.bot.fetch_user(target_id)
        target_display = str(target) if target else case["target"]

        embed = Embed(
            title=f"Case #{case_id} Information",
            color=config.Color.baseColor,
            timestamp=case["timestamp"],
        )

        embed.add_field(
            name="Details",
            value=f"""
            > **Type:** {case['case_type'].title()}
            > **Target:** {target_display} (`{target_id}`)
            > **Moderator:** {moderator_display} (`{case['moderator_id']}`)
            > **Reason:** {case['reason']}
            > **When:** {format_dt(case['timestamp'], 'F')} ({format_dt(case['timestamp'], 'R')})
            """,
            inline=False,
        )

        return await ctx.send(embed=embed)

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

        if isinstance(channel, Thread):
            if channel.locked:
                return await ctx.warn(f"{channel.mention} is already locked!")
        else:
            perms = channel.overwrites_for(ctx.settings.lock_role)
            if perms.send_messages is False:
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

        return await ctx.thumbsup()

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
            f"Successfully locked down `{len(ctx.guild.text_channels) - len(ctx.settings.lock_ignore)}` channels in `{perf_counter() - start:.2f}s`",
            patch=ctx.response,
        )

    @lockdown.command(
        name="add",
        aliases=["a"],
        example="general",
    )
    @has_permissions(manage_channels=True)
    async def ignore_add(
        self,
        ctx: Context,
        *,
        channel: TextChannel,
    ) -> Message:
        """
        Add a channel to the lockdown ignore list.
        """
        if channel in ctx.settings.lock_ignore:
            return await ctx.warn(f"{channel.mention} is already being ignored!")

        ctx.settings.lock_ignore_ids.append(channel.id)
        await ctx.settings.update()
        return await ctx.approve(f"Now ignoring {channel.mention} from lockdown")

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

    @lockdown_ignore.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_channels=True)
    async def lockdown_ignore_list(self, ctx: Context) -> Message:
        """
        View all channels being ignored.
        """
        if not ctx.settings.lock_ignore:
            return await ctx.warn("No channels are being ignored!")

        embed = Embed(title="Ignored Channels", color=config.Color.baseColor)
        descriptions = [
            f"{channel.mention} (`{channel.id}`)"
            for channel in ctx.settings.lock_ignore
        ]

        return await ctx.autopaginator(embed=embed, description=descriptions, split=10)

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

        if isinstance(channel, Thread):
            if not channel.locked:
                return await ctx.warn(f"{channel.mention} is already unlocked!")
        else:
            perms = channel.overwrites_for(ctx.settings.lock_role)
            if perms.send_messages is None or perms.send_messages is True:
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

        return await ctx.thumbsup()

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
            channels_to_unlock = [
                channel
                for channel in ctx.guild.text_channels
                if (
                    channel.overwrites_for(ctx.settings.lock_role).send_messages
                    is not True
                    and channel not in ctx.settings.lock_ignore
                )
            ]
            unlock_tasks = []
            for channel in channels_to_unlock:
                overwrite = channel.overwrites_for(ctx.settings.lock_role)
                overwrite.send_messages = True
                unlock_tasks.append(
                    channel.set_permissions(
                        ctx.settings.lock_role,
                        overwrite=overwrite,
                        reason=f"{ctx.author.name} / {reason} (SERVER UNLOCKDOWN)",
                    )
                )
            if unlock_tasks:
                await gather(*unlock_tasks)

        return await ctx.approve(
            f"Successfully unlocked `{len(channels_to_unlock)}` channels in `{perf_counter() - start:.2f}s`",
            patch=ctx.response,
        )

    @command()
    @has_permissions(administrator=True)
    @cooldown(1, 10, BucketType.user)
    async def moveall(
        self,
        ctx: Context,
        *,
        channel: VoiceChannel | StageChannel,
    ) -> Message:
        """
        Move all members in current channel to another channel
        """
        return await ctx.invoke(self.drag_all, channel=channel)

    # Update the jail command
    @command(
        name="jail",
        usage="(member) (reason)",
        example="johndoe breaking rules",
        aliases=["j"],
    )
    @ModConfig.is_mod_configured()
    @has_permissions(manage_channels=True)
    async def jail(
        self,
        ctx: Context,
        member: Annotated[Member, TouchableMember],
        *,
        reason: str = "No reason provided",
    ):
        """
        Jail a member, restricting their access to channels
        """
        jail_role = ctx.guild.get_role(ctx.settings.jail_role)
        if not jail_role:
            return await ctx.warn("Jail role not found!")

        if jail_role in member.roles:
            return await ctx.warn(f"{member.mention} is already jailed!")

        # Get jail channel
        jail_channel = ctx.guild.get_channel(ctx.settings.jail_channel)
        if not jail_channel:
            return await ctx.warn("Jail channel not found!")

        await member.add_roles(jail_role, reason=f"{ctx.author}: {reason}")
        action = "Jailed"

        # Add to jailed table
        await self.bot.db.execute(
            "INSERT INTO jailed (guild_id, user_id) VALUES ($1, $2)",
            ctx.guild.id,
            member.id,
        )

        await self.moderation_entry(ctx, member, action, reason)

        await jail_channel.send(
            f"{member.mention}, you have been jailed! Wait for a staff member to unjail you and check direct messages if you have received one!"
        )

        if ctx.settings.invoke_jail_dm:
            script = EmbedScript(ctx.settings.invoke_jail_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                action.lower(), ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been {action.lower()}d for {reason}. I couldn't DM you more information."
                )

        if ctx.settings.invoke_jail_message:
            script = EmbedScript(ctx.settings.invoke_jail_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        name="unjail",
        usage="(member) (reason)",
        example="johndoe behavior improved",
        aliases=["uj"],
    )
    @ModConfig.is_mod_configured()
    @has_permissions(manage_channels=True)
    async def unjail(
        self,
        ctx: Context,
        member: Member,
        *,
        reason: str = "No reason provided",
    ):
        """
        Unjail a member, restoring their channel access
        """
        jail_role = ctx.guild.get_role(ctx.settings.jail_role)
        if not jail_role:
            return await ctx.warn("Jail role not found!")

        if jail_role not in member.roles:
            return await ctx.warn(f"{member.mention} is not jailed!")

        await member.remove_roles(jail_role, reason=f"{ctx.author}: {reason}")
        action = "Unjailed"

        # Remove from jailed table
        await self.bot.db.execute(
            "DELETE FROM jailed WHERE guild_id = $1 AND user_id = $2",
            ctx.guild.id,
            member.id,
        )

        await self.moderation_entry(ctx, member, action, reason)

        if ctx.settings.invoke_unjail_dm:
            script = EmbedScript(ctx.settings.invoke_unjail_dm)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            with suppress(HTTPException):
                await script.send(member)
        else:
            embed = self.create_mod_action_embed(
                action.lower(), ctx.guild, ctx.author, reason
            )
            try:
                await member.send(embed=embed)
            except Forbidden:
                await ctx.send(
                    f"{member.mention} you have been {action.lower()}d for {reason}. I couldn't DM you more information."
                )

        if ctx.settings.invoke_unjail_message:
            script = EmbedScript(ctx.settings.invoke_unjail_message)
            await script.resolve_variables(
                guild=ctx.guild,
                channel=ctx.channel,
                user=member,
                moderator=ctx.author,
                reason=reason,
            )
            return await script.send(ctx.channel)

        return await ctx.thumbsup()

    @command(
        name="jaillist",
        aliases=["jlist", "jailed"],
    )
    @ModConfig.is_mod_configured()
    @has_permissions(manage_channels=True)
    async def jaillist(self, ctx: Context) -> Message:
        """
        View all currently jailed members
        """
        # Fetch all jailed members in this guild
        jailed_members = await self.bot.db.fetch(
            """
            SELECT user_id, jailed_at 
            FROM jailed 
            WHERE guild_id = $1 
            ORDER BY jailed_at DESC
            """,
            ctx.guild.id,
        )

        if not jailed_members:
            return await ctx.warn("No members are currently jailed!")

        embed = Embed(
            title="Jailed Members",
            color=config.Color.baseColor,
            timestamp=utcnow(),
        )

        descriptions = []
        for record in jailed_members:
            user_id = record["user_id"]
            jailed_at = record["jailed_at"]

            member = ctx.guild.get_member(user_id)
            if member:
                user_text = f"{member.mention} (`{member.id}`)"
            else:
                user_text = f"User ID: `{user_id}`"

            descriptions.append(
                f"**{user_text}**\n"
                f"> Jailed: {format_dt(jailed_at, 'F')} ({format_dt(jailed_at, 'R')})\n"
            )

        return await ctx.autopaginator(
            embed=embed,
            description=descriptions,
            split=10,
        )
