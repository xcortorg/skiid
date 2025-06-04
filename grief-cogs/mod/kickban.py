import asyncio
import contextlib
import logging
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Dict, List, Optional, Tuple, Union

import aiohttp
import discord
import msgpack
import orjson
from aiomisc.periodic import PeriodicCallback
from discord.utils import utcnow
from pydantic import BaseModel

from grief.core import Config, commands, i18n
from grief.core.bot import Grief
from grief.core.commands import RawUserIdConverter
from grief.core.commands.converter import TimedeltaConverter
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import (bold, format_perms_list,
                                              humanize_list, humanize_number,
                                              pagify)
from grief.core.utils.mod import get_audit_reason
from grief.core.utils.views import ConfirmView

from .abc import MixinMeta
from .converters import ImageFinder
from .utils import is_allowed_by_hierarchy

log = logging.getLogger("grief.mod")
_ = i18n.Translator("Mod", __file__)


class KickBanMixin(MixinMeta):
    """
    Kick and ban commands and tasks go here.
    """

    @staticmethod
    async def get_invite_for_reinvite(
        ctx: commands.Context, max_age: int = 86400
    ) -> str:
        """Handles the reinvite logic for getting an invite to send the newly unbanned user"""
        guild = ctx.guild
        my_perms: discord.Permissions = guild.me.guild_permissions
        if my_perms.manage_guild or my_perms.administrator:
            if guild.vanity_url is not None:
                return guild.vanity_url
            invites = await guild.invites()
        else:
            invites = []
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                # Invite is for the guild's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv.url
        else:  # No existing invite found that is valid
            channels_and_perms = (
                (channel, channel.permissions_for(guild.me))
                for channel in guild.text_channels
            )
            channel = next(
                (
                    channel
                    for channel, perms in channels_and_perms
                    if perms.create_instant_invite
                ),
                None,
            )
            if channel is None:
                return ""
            try:
                # Create invite that expires after max_age
                return (await channel.create_invite(max_age=max_age)).url
            except discord.HTTPException:
                return ""

    @staticmethod
    async def _voice_perm_check(
        ctx: commands.Context,
        user_voice_state: Optional[discord.VoiceState],
        **perms: bool,
    ) -> bool:
        """Check if the bot and user have sufficient permissions for voicebans.

        This also verifies that the user's voice state and connected
        channel are not ``None``.

        Returns
        -------
        bool
            ``True`` if the permissions are sufficient and the user has
            a valid voice state.

        """
        if user_voice_state is None or user_voice_state.channel is None:
            await ctx.send(_("That user is not in a voice channel."))
            return False
        voice_channel: discord.VoiceChannel = user_voice_state.channel
        required_perms = discord.Permissions()
        required_perms.update(**perms)
        if not voice_channel.permissions_for(ctx.me) >= required_perms:
            await ctx.send(
                _(
                    "I require the {perms} permission(s) in that user's channel to do that."
                ).format(perms=format_perms_list(required_perms))
            )
            return False
        if (
            ctx.permission_state is commands.PermState.NORMAL
            and not voice_channel.permissions_for(ctx.author) >= required_perms
        ):
            await ctx.send(
                _(
                    "You must have the {perms} permission(s) in that user's channel to use this "
                    "command."
                ).format(perms=format_perms_list(required_perms))
            )
            return False
        return True

    async def ban_user(
        self,
        user: Union[discord.Member, discord.User, discord.Object],
        ctx: commands.Context,
        days: int = 0,
        reason: str = None,
    ) -> Tuple[bool, str]:
        author = ctx.author
        guild = ctx.guild

        removed_temp = False

        if not (0 <= days <= 7):
            return False, _("Invalid days. Must be between 0 and 7.")

        if isinstance(user, discord.Member):
            if author == user:
                return (
                    False,
                    _("I cannot let you do that. Self-harm is bad {}").format(
                        "\N{PENSIVE FACE}"
                    ),
                )
            elif not await is_allowed_by_hierarchy(
                self.bot, self.config, guild, author, user
            ):
                return (
                    False,
                    _(
                        "I cannot let you do that. You are "
                        "not higher than the user in the role "
                        "hierarchy."
                    ),
                )
            elif guild.me.top_role <= user.top_role or user == guild.owner:
                return False, _("I cannot do that due to Discord hierarchy rules.")

            toggle = await self.config.guild(guild).dm_on_kickban()
            if toggle:
                with contextlib.suppress(discord.HTTPException):
                    em = discord.Embed(
                        title=bold(
                            _("You have been banned from {guild}.").format(guild=guild)
                        ),
                        color=await self.bot.get_embed_color(user),
                    )
                    em.add_field(
                        name=_("**Reason**"),
                        value=(
                            reason if reason is not None else _("No reason was given.")
                        ),
                        inline=False,
                    )
                    await user.send(embed=em)

            ban_type = "ban"
        else:
            tempbans = await self.config.guild(guild).current_tempbans()

            try:
                await guild.fetch_ban(user)
            except discord.NotFound:
                pass
            else:
                if user.id in tempbans:
                    async with self.config.guild(guild).current_tempbans() as tempbans:
                        tempbans.remove(user.id)
                    removed_temp = True
                else:
                    return (
                        False,
                        _("User with ID {user_id} is already banned.").format(
                            user_id=user.id
                        ),
                    )

            ban_type = "hackban"

        audit_reason = get_audit_reason(author, reason, shorten=True)

        if removed_temp:
            log.info(
                "%s (%s) upgraded the tempban for %s to a permaban.",
                author,
                author.id,
                user.id,
            )
            success_message = _(
                "User with ID {user_id} was upgraded from a temporary to a permanent ban."
            ).format(user_id=user.id)
        else:
            user_handle = str(user) if isinstance(user, discord.abc.User) else "Unknown"
            try:
                await guild.ban(
                    user, reason=audit_reason, delete_message_seconds=days * 86400
                )
                log.info(
                    "%s (%s) %sned %s (%s), deleting %s days worth of messages.",
                    author,
                    author.id,
                    ban_type,
                    user_handle,
                    user.id,
                    days,
                )
                success_message = None
            except discord.Forbidden:
                return False, _("I'm not allowed to do that.")
            except discord.NotFound:
                return False, _("User with ID {user_id} not found").format(
                    user_id=user.id
                )
            except Exception:
                log.exception(
                    "%s (%s) attempted to %s %s (%s), but an error occurred.",
                    author,
                    author.id,
                    ban_type,
                    user_handle,
                    user.id,
                )
                return False, _("An unexpected error occurred.")
        return True, success_message

    async def tempban_expirations_task(self) -> None:
        while True:
            try:
                await self._check_tempban_expirations()
            except Exception:
                log.exception("Something went wrong in check_tempban_expirations:")

            await asyncio.sleep(60)

    async def _check_tempban_expirations(self) -> None:
        guilds_data = await self.config.all_guilds()
        async for guild_id, guild_data in AsyncIter(guilds_data.items(), steps=100):
            if not (guild := self.bot.get_guild(guild_id)):
                continue
            if guild.unavailable or not guild.me.guild_permissions.ban_members:
                continue
            if await self.bot.cog_disabled_in_guild(self, guild):
                continue

            guild_tempbans = guild_data["current_tempbans"]
            if not guild_tempbans:
                continue
            async with self.config.guild(guild).current_tempbans.get_lock():
                if await self._check_guild_tempban_expirations(guild, guild_tempbans):
                    await self.config.guild(guild).current_tempbans.set(guild_tempbans)

    async def _check_guild_tempban_expirations(
        self, guild: discord.Guild, guild_tempbans: List[int]
    ) -> bool:
        changed = False
        for uid in guild_tempbans.copy():
            unban_time = datetime.fromtimestamp(
                await self.config.member_from_ids(guild.id, uid).banned_until(),
                timezone.utc,
            )
            if datetime.now(timezone.utc) > unban_time:
                try:
                    await guild.unban(
                        discord.Object(id=uid), reason=_("Tempban finished")
                    )
                except discord.NotFound:
                    # user is not banned anymore
                    guild_tempbans.remove(uid)
                    changed = True
                except discord.HTTPException as e:
                    # 50013: Missing permissions error code or 403: Forbidden status
                    if e.code == 50013 or e.status == 403:
                        log.info(
                            f"Failed to unban ({uid}) user from "
                            f"{guild.name}({guild.id}) guild due to permissions."
                        )
                        break  # skip the rest of this guild
                    log.info(f"Failed to unban member: error code: {e.code}")
                else:
                    # user unbanned successfully
                    guild_tempbans.remove(uid)
                    changed = True
        return changed

    @commands.command(autohelp=True, aliases=["k"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(kick_members=True)
    async def kick(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """
        Kick a user.
        """
        author = ctx.author
        guild = ctx.guild

        if reason == None:
            reason = "no reason given"

        if isinstance(member, discord.Member):
            if member.id in self.bot.owner_ids:
                embed = discord.Embed(
                    description=f"{ctx.author.mention} you cannot kick the bot owner.",
                    color=0x313338,
                )
                return await ctx.reply(embed=embed, mention_author=False)

        if author == member:
            embed = discord.Embed(
                description=f"> {ctx.author.mention}: you can't kick yourself.",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)
        elif not await is_allowed_by_hierarchy(
            self.bot, self.config, guild, author, member
        ):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif ctx.guild.me.top_role <= member.top_role or member == ctx.guild.owner:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: I cannot do that due to Discord hierarchy rules.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return
        audit_reason = get_audit_reason(author, reason, shorten=True)
        toggle = await self.config.guild(guild).dm_on_kickban()
        if toggle:
            with contextlib.suppress(discord.HTTPException):
                em = discord.Embed(
                    title=bold(
                        _("You have been kicked from {guild}.").format(guild=guild)
                    ),
                    color=await self.bot.get_embed_color(member),
                )
                em.add_field(
                    name=_("**Reason**"),
                    value=reason if reason is not None else _("No reason was given."),
                    inline=False,
                )
                await member.send(embed=em)
        try:
            await guild.kick(member, reason=audit_reason)
            embed = discord.Embed(
                description=f"{ctx.author.mention}: kicked **{member}** for {reason}",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)
        except discord.errors.Forbidden:
            embed = discord.Embed(
                description=f"> I'm not allowed to do that.", color=0x313338
            )
            return await ctx.reply(embed=embed, mention_author=False)
        except Exception:
            log.exception(
                "{}({}) attempted to kick {}({}), but an error occurred.".format(
                    author.name, author.id, member.name, member.id
                )
            )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(ban_members=True)
    @commands.admin_or_permissions(ban_members=True)
    async def ban(
        self,
        ctx: commands.Context,
        user: Union[discord.Member, RawUserIdConverter],
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        guild = ctx.guild
        if user in self.bot.owner_ids:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: you cannot ban the bot owner.",
                color=0x313338,
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if days is None:
            days = await self.config.guild(guild).default_days()

        if isinstance(user, int):
            user = self.bot.get_user(user) or discord.Object(id=user)

        message = await self.ban_user(user=user, ctx=ctx, days=days, reason=reason)

        await ctx.send(message)
        await ctx.tick()

    @commands.command(aliases=["hackban", "mb"], usage="<user_ids...> [days] [reason]")
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def massban(
        self,
        ctx: commands.Context,
        user_ids: commands.Greedy[RawUserIdConverter],
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Mass bans users from the server."""
        banned = []
        errors = {}
        upgrades = []

        async def show_results():
            text = _("Banned {num} users from the server.").format(
                num=humanize_number(len(banned))
            )
            if errors:
                text += _("\nErrors:\n")
                text += "\n".join(errors.values())
            if upgrades:
                text += _(
                    "\nFollowing user IDs have been upgraded from a temporary to a permanent ban:\n"
                )
                text += humanize_list(upgrades)

            for p in pagify(text):
                await ctx.send(p)

        def remove_processed(ids):
            return [_id for _id in ids if _id not in banned and _id not in errors]

        user_ids = list(set(user_ids))  # No dupes

        author = ctx.author
        guild = ctx.guild

        if isinstance(user, discord.Member):
            if user.id in self.bot.owner_ids:
                embed = discord.Embed(
                    description=f"> {ctx.author.mention} You cannot ban the bot owner.",
                    color=0x313338,
                )
                return await ctx.reply(embed=embed, mention_author=False)

        if not user_ids:
            await ctx.send_help()
            return

        if days is None:
            days = await self.config.guild(guild).default_days()

        if not (0 <= days <= 7):
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return

        if not guild.me.guild_permissions.ban_members:
            return await ctx.send(_("I lack the permissions to do this."))

        tempbans = await self.config.guild(guild).current_tempbans()

        for user_id in user_ids:
            if user_id in tempbans:
                # We need to check if a user is tempbanned here because otherwise they won't be processed later on.
                continue
            try:
                await guild.fetch_ban(discord.Object(user_id))
            except discord.NotFound:
                pass
            else:
                errors[user_id] = _("User with ID {user_id} is already banned.").format(
                    user_id=user_id
                )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        # We need to check here, if any of the users isn't a member and if they are,
        # we need to use our `ban_user()` method to do hierarchy checks.
        members: Dict[int, discord.Member] = {}
        to_query: List[int] = []

        for user_id in user_ids:
            member = guild.get_member(user_id)
            if member is not None:
                members[user_id] = member
            elif not guild.chunked:
                to_query.append(user_id)

        # If guild isn't chunked, we might possibly be missing the member from cache,
        # so we need to make sure that isn't the case by querying the user IDs for such guilds.
        while to_query:
            queried_members = await guild.query_members(
                user_ids=to_query[:100], limit=100
            )
            members.update((member.id, member) for member in queried_members)
            to_query = to_query[100:]

        # Call `ban_user()` method for all users that turned out to be guild members.
        for user_id, member in members.items():
            try:
                # using `reason` here would shadow the reason passed to command
                success, failure_reason = await self.ban_user(
                    user=member, ctx=ctx, days=days, reason=reason
                )
                if success:
                    banned.append(user_id)
                else:
                    errors[user_id] = _(
                        "Failed to ban user {user_id}: {reason}"
                    ).format(user_id=user_id, reason=failure_reason)
            except Exception as e:
                errors[user_id] = _("Failed to ban user {user_id}: {reason}").format(
                    user_id=user_id, reason=e
                )

        user_ids = remove_processed(user_ids)

        if not user_ids:
            await show_results()
            return

        for user_id in user_ids:
            user = discord.Object(id=user_id)
            audit_reason = get_audit_reason(author, reason, shorten=True)
            async with self.config.guild(guild).current_tempbans() as tempbans:
                if user_id in tempbans:
                    tempbans.remove(user_id)
                    upgrades.append(str(user_id))
                    log.info(
                        "{}({}) upgraded the tempban for {} to a permaban.".format(
                            author.name, author.id, user_id
                        )
                    )
                    banned.append(user_id)
                else:
                    try:
                        await guild.ban(
                            user,
                            reason=audit_reason,
                            delete_message_seconds=days * 86400,
                        )
                        log.info(
                            "{}({}) hackbanned {}".format(
                                author.name, author.id, user_id
                            )
                        )
                    except discord.NotFound:
                        errors[user_id] = _("User with ID {user_id} not found").format(
                            user_id=user_id
                        )
                        continue
                    except discord.Forbidden:
                        errors[user_id] = _(
                            "Could not ban user with ID {user_id}: missing permissions."
                        ).format(user_id=user_id)
                        continue
                    else:
                        banned.append(user_id)

    @commands.command(aliases=["tb"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def tempban(
        self,
        ctx: commands.Context,
        member: discord.Member,
        duration: Optional[commands.TimedeltaConverter] = None,
        days: Optional[int] = None,
        *,
        reason: str = None,
    ):
        """Temporarily ban a user from this server."""
        guild = ctx.guild
        author = ctx.author

        if isinstance(member, discord.Member):
            if member.id in self.bot.owner_ids:
                embed = discord.Embed(
                    description=f"{ctx.author.mention}: You cannot tempban the bot owner.",
                    color=0x313338,
                )
                return await ctx.reply(embed=embed, mention_author=False)

        if author == member:
            await ctx.send(_("You cannot ban yourself."))
            return

        elif not await is_allowed_by_hierarchy(
            self.bot, self.config, guild, author, member
        ):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return
        elif guild.me.top_role <= member.top_role or member == guild.owner:
            await ctx.send(_("I cannot do that due to Discord hierarchy rules."))
            return

        guild_data = await self.config.guild(guild).all()

        if duration is None:
            duration = timedelta(seconds=guild_data["default_tempban_duration"])
        unban_time = datetime.now(timezone.utc) + duration

        if days is None:
            days = guild_data["default_days"]

        if not (0 <= days <= 7):
            await ctx.send(_("Invalid days. Must be between 0 and 7."))
            return
        invite = await self.get_invite_for_reinvite(
            ctx, int(duration.total_seconds() + 86400)
        )

        await self.config.member(member).banned_until.set(unban_time.timestamp())
        async with self.config.guild(guild).current_tempbans() as current_tempbans:
            current_tempbans.append(member.id)

        with contextlib.suppress(discord.HTTPException):
            # We don't want blocked DMs preventing us from banning
            msg = _(
                "You have been temporarily banned from {server_name} until {date}."
            ).format(server_name=guild.name, date=discord.utils.format_dt(unban_time))
            if guild_data["dm_on_kickban"] and reason:
                msg += _("\n\n**Reason:** {reason}").format(reason=reason)
            if invite:
                msg += _(
                    "\n\nHere is an invite for when your ban expires: {invite_link}"
                ).format(invite_link=invite)
            await member.send(msg)

        audit_reason = get_audit_reason(author, reason, shorten=True)

        try:
            await ctx.tick()
            await guild.ban(
                member, reason=audit_reason, delete_message_seconds=days * 86400
            )
        except discord.Forbidden:
            await ctx.send(_("I can't do that for some reason."))
        except discord.HTTPException:
            await ctx.send(_("Something went wrong while banning."))

    @commands.command(aliases=["sbn"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def softban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Kick a user and delete 1 day's worth of their messages."""
        guild = ctx.guild
        author = ctx.author

        if isinstance(member, discord.Member):
            if member.id in self.bot.owner_ids:
                embed = discord.Embed(
                    description=f"{ctx.author.mention}: You cannot softban the bot owner.",
                    color=0x313338,
                )
                return await ctx.reply(embed=embed, mention_author=False)

        if author == member:
            await ctx.send(("You cannot ban yourself."))
            return
        elif not await is_allowed_by_hierarchy(
            self.bot, self.config, guild, author, member
        ):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return

        audit_reason = get_audit_reason(author, reason, shorten=True)

        invite = await self.get_invite_for_reinvite(ctx)

        try:  # We don't want blocked DMs preventing us from banning
            msg = await member.send(
                _(
                    "You have been banned and "
                    "then unbanned as a quick way to delete your messages.\n"
                    "You can now join the server again. {invite_link}"
                ).format(invite_link=invite)
            )
        except discord.HTTPException:
            msg = None
        try:
            await guild.ban(member, reason=audit_reason, delete_message_seconds=86400)
        except discord.errors.Forbidden:
            await ctx.send(_("My role is not high enough to softban that user."))
            if msg is not None:
                await msg.delete()
            return
        except discord.HTTPException:
            log.exception(
                "{}({}) attempted to softban {}({}), but an error occurred trying to ban them.".format(
                    author.name, author.id, member.name, member.id
                )
            )
            return
        try:
            await guild.unban(member)
        except discord.HTTPException:
            log.exception(
                "{}({}) attempted to softban {}({}), but an error occurred trying to unban them.".format(
                    author.name, author.id, member.name, member.id
                )
            )
            return
        else:
            log.info(
                "{}({}) softbanned {}({}), deleting 1 day worth "
                "of messages.".format(author.name, author.id, member.name, member.id)
            )

    @commands.command(aliases=["vk"])
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(move_members=True)
    async def voicekick(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Kick a member from a voice channel."""
        author = ctx.author
        guild = ctx.guild
        user_voice_state: discord.VoiceState = member.voice

        if isinstance(member, discord.Member):
            if member.id in self.bot.owner_ids:
                embed = discord.Embed(
                    description=f"{ctx.author.mention}: You cannot voicekick the bot owner.",
                    color=0x313338,
                )
                return await ctx.reply(embed=embed, mention_author=False)

        if (
            await self._voice_perm_check(ctx, user_voice_state, move_members=True)
            is False
        ):
            return
        elif not await is_allowed_by_hierarchy(
            self.bot, self.config, guild, author, member
        ):
            await ctx.send(
                _(
                    "I cannot let you do that. You are "
                    "not higher than the user in the role "
                    "hierarchy."
                )
            )
            return

        embed = discord.Embed(
            description=f"> {ctx.author.mention}: {member} has been voice kicked.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=True)

        try:
            await member.move_to(None)
        except discord.Forbidden:  # Very unlikely that this will ever occur
            await ctx.send(_("I am unable to kick this member from the voice channel."))
            return
        except discord.HTTPException:
            await ctx.send(
                _("Something went wrong while attempting to kick that member.")
            )
            return

    @commands.command(aliases=["vu"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(mute_members=True, deafen_members=True)
    async def voiceunban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Unban a user from speaking and listening in the server's voice channels."""
        user_voice_state = member.voice
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
            return

        embed = discord.Embed(
            description=f"{ctx.author.mention}: {member} has been un-voice banned.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)

        needs_unmute = True if user_voice_state.mute else False
        needs_undeafen = True if user_voice_state.deaf else False
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        if needs_unmute and needs_undeafen:
            await member.edit(mute=False, deafen=False, reason=audit_reason)
        elif needs_unmute:
            await member.edit(mute=False, reason=audit_reason)
        elif needs_undeafen:
            await member.edit(deafen=False, reason=audit_reason)
        else:
            await ctx.send(_("That user isn't muted or deafened by the server."))
            return

    @commands.command(aliases=["vb"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(mute_members=True, deafen_members=True)
    async def voiceban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = None
    ):
        """Ban a user from speaking and listening in the server's voice channels."""
        user_voice_state: discord.VoiceState = member.voice

        if isinstance(member, discord.Member):
            if member.id in self.bot.owner_ids:
                embed = discord.Embed(
                    description=f"{ctx.author.mention}: You cannot voiceban the bot owner.",
                    color=0x313338,
                )
                return await ctx.reply(embed=embed, mention_author=False)
        if (
            await self._voice_perm_check(
                ctx, user_voice_state, deafen_members=True, mute_members=True
            )
            is False
        ):
            return
        await ctx.tick()

        needs_mute = True if user_voice_state.mute is False else False
        needs_deafen = True if user_voice_state.deaf is False else False
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)
        author = ctx.author
        guild = ctx.guild
        if needs_mute and needs_deafen:
            await member.edit(mute=True, deafen=True, reason=audit_reason)
        elif needs_mute:
            await member.edit(mute=True, reason=audit_reason)
        elif needs_deafen:
            await member.edit(deafen=True, reason=audit_reason)
        else:
            await ctx.send(_("That user is already muted and deafened server-wide."))
            return

    @commands.command(aliases=["ub"])
    @commands.guild_only()
    @commands.cooldown(1, 3, commands.BucketType.guild)
    @commands.has_permissions(ban_members=True)
    async def unban(
        self, ctx: commands.Context, user_id: RawUserIdConverter, *, reason: str = None
    ):
        """Unban a user from this server."""
        guild = ctx.guild
        author = ctx.author
        audit_reason = get_audit_reason(ctx.author, reason, shorten=True)

        try:
            ban_entry = await guild.fetch_ban(discord.Object(user_id))
        except discord.NotFound:
            await ctx.send(_("It seems that user isn't banned!"))
            return
        try:
            await guild.unban(ban_entry.user, reason=audit_reason)
        except discord.HTTPException:
            await ctx.send(
                _("Something went wrong while attempting to unban that user.")
            )
            return

        if await self.config.guild(guild).reinvite_on_unban():
            user = ctx.bot.get_user(user_id)
            if not user:
                await ctx.send(
                    _(
                        "I don't share another server with this user. I can't reinvite them."
                    )
                )
                return

        embed = discord.Embed(
            description=f"{ctx.author.mention}: **{user}** has been unbanned.",
            color=0x313338,
        )
        await ctx.reply(embed=embed, mention_author=False)

        invite = await self.get_invite_for_reinvite(ctx)
        if invite:
            try:
                await user.send(
                    _(
                        "You've been unbanned from {server}.\n"
                        "Here is an invite for that server: {invite_link}"
                    ).format(server=guild.name, invite_link=invite)
                )
            except discord.Forbidden:
                await ctx.send(
                    _(
                        "I failed to send an invite to that user. "
                        "Perhaps you may be able to send it for me?\n"
                        "Here's the invite link: {invite_link}"
                    ).format(invite_link=invite)
                )
            except discord.HTTPException:
                await ctx.send(
                    _(
                        "Something went wrong when attempting to send that user "
                        "an invite. Here's the link so you can try: {invite_link}"
                    ).format(invite_link=invite)
                )

    @commands.group(
        name="gedit",
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def guildedit(self, ctx: commands.Context) -> None:
        """Vanity management for Grief."""

    @guildedit.command()
    async def banner(self, ctx, url: str = None):
        """Set the server banner.

        `<image>` URL to the image or image uploaded with running the
        command

        """

        if len(ctx.message.attachments) > 0:  # Attachments take priority
            data = await ctx.message.attachments[0].read()

        elif url is not None:
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        data = await r.read()
                except aiohttp.InvalidURL:
                    return await ctx.send(_("That URL is invalid."))
                except aiohttp.ClientError:
                    return await ctx.send(
                        _("Something went wrong while trying to get the image.")
                    )
        else:
            await ctx.guild.edit(banner=None)
            embed = discord.Embed(
                description=f"{ctx.author.mention}: server banner has been cleared.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        try:
            async with ctx.typing():
                await ctx.guild.edit(
                    banner=data, reason=f"server banner updated by {ctx.author}"
                )
        except discord.HTTPException:
            await ctx.send(_("Must be a valid image in either JPG or PNG format."))
        except ValueError:
            await ctx.send(_("JPG / PNG format only."))
        else:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: server banner has been updated.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)

    @guildedit.command()
    async def icon(self, ctx, url: str = None):
        """Set the server icon of the server.

        `<image>` URL to the image or image uploaded with running the
        command

        """
        if len(ctx.message.attachments) > 0:  # Attachments take priority
            data = await ctx.message.attachments[0].read()
        elif url is not None:
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        data = await r.read()
                except aiohttp.InvalidURL:
                    return await ctx.send(_("That URL is invalid."))
                except aiohttp.ClientError:
                    return await ctx.send(
                        _("Something went wrong while trying to get the image.")
                    )
        else:
            await ctx.guild.edit(icon=None)
            embed = discord.Embed(
                description=f"{ctx.author.mention}: server icon has been cleared.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        try:
            async with ctx.typing():
                await ctx.guild.edit(
                    icon=data, reason=f"server icon updated by {ctx.author}"
                )
        except discord.HTTPException:
            await ctx.send(_("must be a valid image in either JPG or PNG format."))
        except ValueError:
            await ctx.send(_("JPG / PNG format only."))
        else:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: server icon has been updated.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)

    @guildedit.command()
    async def splash(self, ctx, url: str = None):
        """Set the invite splash screen of the server.

        `<image>` URL to the image or image uploaded with running the
        command

        """

        if len(ctx.message.attachments) > 0:  # Attachments take priority
            data = await ctx.message.attachments[0].read()
        elif url is not None:
            if url.startswith("<") and url.endswith(">"):
                url = url[1:-1]

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(url) as r:
                        data = await r.read()
                except aiohttp.InvalidURL:
                    return await ctx.send(_("That URL is invalid."))
                except aiohttp.ClientError:
                    return await ctx.send(
                        _("Something went wrong while trying to get the image.")
                    )
        else:
            await ctx.guild.edit(splash=None)
            embed = discord.Embed(
                description=f"{ctx.author.mention}: server splash has been cleared.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return

        try:
            async with ctx.typing():
                await ctx.guild.edit(
                    splash=data, reason=f"server splash updated by {ctx.author}"
                )
        except discord.HTTPException:
            await ctx.send(
                _(
                    "Failed. Remember that you can edit my avatar "
                    "up to two times a hour. The URL or attachment "
                    "must be a valid image in either JPG or PNG format."
                )
            )
        except ValueError:
            await ctx.send(_("JPG / PNG format only."))
        else:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: server invite splash has been updated.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def naughty(self, ctx):
        """Make a channel NSFW for 30 seconds."""
        channel: discord.TextChannel = ctx.channel
        if channel.is_nsfw():
            return await ctx.send("The channel is already marked as NSFW.")
        try:
            await channel.edit(nsfw=True)
            await ctx.send(
                f"The channel {channel.mention} has been marked as NSFW for 30 seconds."
            )
            await asyncio.sleep(30)
            await channel.edit(nsfw=False)
            await ctx.send(
                f"The channel {channel.mention} is no longer marked as NSFW."
            )
        except discord.Forbidden:
            await ctx.send("I don't have the required permissions to manage channels.")

    @commands.command(aliases=["ci"])
    @commands.has_permissions(manage_guild=True)
    async def clearinvites(self, ctx):
        """Delete all invites in the server."""

        invites = await ctx.guild.invites()
        for invite in invites:
            await invite.delete()
        embed = discord.Embed(
            description="All existing invites have been removed.", color=0x313338
        )
        await ctx.send(embed=embed)
