import asyncio
from collections import defaultdict
from logging import Logger, getLogger
from typing import List, Optional, Tuple, cast

import discord

from grief.core import Config, commands, i18n
from grief.core.bot import Grief
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import (bold, box, humanize_timedelta,
                                              inline, pagify)
from grief.core.utils.common_filters import (escape_spoilers_and_mass_mentions,
                                             filter_invites,
                                             filter_various_mentions)

from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)


@cog_i18n(_)
class Names(commands.Cog):
    """Moderation tools."""

    def format_help_for_context(self, ctx: commands.Context) -> str:
        pre_processed = super().format_help_for_context(ctx)
        return f"{pre_processed}\n"

    default_member_settings = {"past_nicks": []}
    default_user_settings = {"past_names": [], "past_display_names": []}
    default_global_settings = {
        "track_all_names": True,
    }
    default_guild_settings = {
        "track_nicknames": True,
    }

    def __init__(self, bot: Grief):
        super().__init__()
        self.bot: Grief = bot
        self.logger: Logger = getLogger("grief.usernames")
        self.config = Config.get_conf(self, 4961522000, force_registration=True)
        self.config.register_member(**self.default_member_settings)
        self.config.register_user(**self.default_user_settings)
        self.config.register_global(**self.default_global_settings)
        self.config.register_guild(**self.default_guild_settings)
        self.cache: dict = {}

    async def get_names(
        self, member: discord.Member
    ) -> Tuple[List[str], List[str], List[str]]:
        user_data = await self.config.user(member).all()
        usernames, display_names = (
            user_data["past_names"],
            user_data["past_display_names"],
        )
        nicks = await self.config.member(member).past_nicks()
        usernames = list(
            map(escape_spoilers_and_mass_mentions, filter(None, usernames))
        )
        display_names = list(
            map(escape_spoilers_and_mass_mentions, filter(None, display_names))
        )
        nicks = list(map(escape_spoilers_and_mass_mentions, filter(None, nicks)))
        return usernames, display_names, nicks

    @commands.command()
    async def names(self, ctx: commands.Context, *, member: discord.Member = None):
        """Show previous usernames, global display names, and server nicknames of a member."""
        author = ctx.author
        if not member:
            member = author
        usernames, display_names, nicks = await self.get_names(member)
        parts = []
        for header, names in (
            (_(f"Past 20 usernames: \n"), usernames),
            (_(f"Past 20 global display names:\n"), display_names),
            (_(f"Past 20 server nicknames:\n"), nicks),
        ):
            if names:
                parts.append(bold(header) + ", ".join(names))
        if parts:
            for msg in pagify(filter_various_mentions("\n\n".join(parts))):
                await ctx.send(msg)
        else:
            await ctx.send(
                _("That member doesn't have any recorded name or nickname change.")
            )

    @commands.is_owner()
    @commands.command()
    async def tracknicknames(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle whether server nickname changes should be tracked.

        This setting will be overridden if trackallnames is disabled.
        """
        guild = ctx.guild
        if enabled is None:
            state = await self.config.guild(guild).track_nicknames()
            if state:
                msg = _("Nickname changes are currently being tracked.")
            else:
                msg = _("Nickname changes are not currently being tracked.")
            await ctx.send(msg)
            return

        if enabled:
            msg = _("Nickname changes will now be tracked.")
        else:
            msg = _("Nickname changes will no longer be tracked.")
        await self.config.guild(guild).track_nicknames.set(enabled)
        await ctx.send(msg)

    @commands.command()
    @commands.is_owner()
    async def trackallnames(self, ctx: commands.Context, enabled: bool = None):
        """
        Toggle whether all name changes should be tracked.

        Toggling this off also overrides the tracknicknames setting.
        """
        if enabled is None:
            state = await self.config.track_all_names()
            if state:
                msg = _("Name changes are currently being tracked.")
            else:
                msg = _("All name changes are currently not being tracked.")
            await ctx.send(msg)
            return

        if enabled:
            msg = _("Name changes will now be tracked.")
        else:
            msg = _(
                "All name changes will no longer be tracked.\n"
                "To delete existing name data, use {command}."
            ).format(command=inline(f"{ctx.clean_prefix}modset deletenames"))
        await self.config.track_all_names.set(enabled)
        await ctx.send(msg)

    @commands.command()
    @commands.is_owner()
    async def deletenames(
        self, ctx: commands.Context, confirmation: bool = False
    ) -> None:
        """Delete all stored usernames, global display names, and server nicknames.

        Examples:
        - `[p]modset deletenames` - Did not confirm. Shows the help message.
        - `[p]modset deletenames yes` - Deletes all stored usernames, global display names, and server nicknames.

        **Arguments**

        - `<confirmation>` This will default to false unless specified.
        """
        if not confirmation:
            await ctx.send(
                _(
                    "This will delete all stored usernames, global display names,"
                    " and server nicknames the bot has stored.\nIf you're sure, type {command}"
                ).format(command=inline(f"{ctx.clean_prefix}modset deletenames yes"))
            )
            return

        async with ctx.typing():
            # Nickname data
            async with self.config._get_base_group(
                self.config.MEMBER
            ).all() as mod_member_data:
                guilds_to_remove = []
                for guild_id, guild_data in mod_member_data.items():
                    await asyncio.sleep(0)
                    members_to_remove = []

                    async for member_id, member_data in AsyncIter(
                        guild_data.items(), steps=100
                    ):
                        if "past_nicks" in member_data:
                            del member_data["past_nicks"]
                        if not member_data:
                            members_to_remove.append(member_id)

                    async for member_id in AsyncIter(members_to_remove, steps=100):
                        del guild_data[member_id]
                    if not guild_data:
                        guilds_to_remove.append(guild_id)

                async for guild_id in AsyncIter(guilds_to_remove, steps=100):
                    del mod_member_data[guild_id]

            # Username and global display name data
            async with self.config._get_base_group(
                self.config.USER
            ).all() as mod_user_data:
                users_to_remove = []
                async for user_id, user_data in AsyncIter(
                    mod_user_data.items(), steps=100
                ):
                    if "past_names" in user_data:
                        del user_data["past_names"]
                    if "past_display_names" in user_data:
                        del user_data["past_display_names"]
                    if not user_data:
                        users_to_remove.append(user_id)

                async for user_id in AsyncIter(users_to_remove, steps=100):
                    del mod_user_data[user_id]

        await ctx.send(
            _(
                "Usernames, global display names, and server nicknames"
                " have been deleted from Mod config."
            )
        )

    def handle_custom(self, user):
        a = [c for c in user.activities if c.type == discord.ActivityType.custom]
        if not a:
            return None, discord.ActivityType.custom
        a = a[0]
        c_status = None
        if not a.name and not a.emoji:
            return None, discord.ActivityType.custom
        elif a.name and a.emoji:
            c_status = _("Custom: {emoji} {name}").format(emoji=a.emoji, name=a.name)
        elif a.emoji:
            c_status = _("Custom: {emoji}").format(emoji=a.emoji)
        elif a.name:
            c_status = _("Custom: {name}").format(name=a.name)
        return c_status, discord.ActivityType.custom

    def handle_playing(self, user):
        p_acts = [c for c in user.activities if c.type == discord.ActivityType.playing]
        if not p_acts:
            return None, discord.ActivityType.playing
        p_act = p_acts[0]
        act = _("Playing: {name}").format(name=p_act.name)
        return act, discord.ActivityType.playing

    def handle_streaming(self, user):
        s_acts = [
            c for c in user.activities if c.type == discord.ActivityType.streaming
        ]
        if not s_acts:
            return None, discord.ActivityType.streaming
        s_act = s_acts[0]
        if isinstance(s_act, discord.Streaming):
            act = _("Streaming: [{name}{sep}{game}]({url})").format(
                name=discord.utils.escape_markdown(s_act.name),
                sep=" | " if s_act.game else "",
                game=discord.utils.escape_markdown(s_act.game) if s_act.game else "",
                url=s_act.url,
            )
        else:
            act = _("Streaming: {name}").format(name=s_act.name)
        return act, discord.ActivityType.streaming

    def handle_listening(self, user):
        l_acts = [
            c for c in user.activities if c.type == discord.ActivityType.listening
        ]
        if not l_acts:
            return None, discord.ActivityType.listening
        l_act = l_acts[0]
        if isinstance(l_act, discord.Spotify):
            act = _("Listening: [{title}{sep}{artist}]({url})").format(
                title=discord.utils.escape_markdown(l_act.title),
                sep=" | " if l_act.artist else "",
                artist=(
                    discord.utils.escape_markdown(l_act.artist) if l_act.artist else ""
                ),
                url=f"https://open.spotify.com/track/{l_act.track_id}",
            )
        else:
            act = _("Listening: {title}").format(title=l_act.name)
        return act, discord.ActivityType.listening

    def handle_watching(self, user):
        w_acts = [c for c in user.activities if c.type == discord.ActivityType.watching]
        if not w_acts:
            return None, discord.ActivityType.watching
        w_act = w_acts[0]
        act = _("Watching: {name}").format(name=w_act.name)
        return act, discord.ActivityType.watching

    def handle_competing(self, user):
        w_acts = [
            c for c in user.activities if c.type == discord.ActivityType.competing
        ]
        if not w_acts:
            return None, discord.ActivityType.competing
        w_act = w_acts[0]
        act = _("Competing in: {competing}").format(competing=w_act.name)
        return act, discord.ActivityType.competing

    def get_status_string(self, user):
        string = ""
        for a in [
            self.handle_custom(user),
            self.handle_playing(user),
            self.handle_listening(user),
            self.handle_streaming(user),
            self.handle_watching(user),
            self.handle_competing(user),
        ]:
            status_string, status_type = a
            if status_string is None:
                continue
            string += f"{status_string}\n"
        return string

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def userinfo(self, ctx, *, member: discord.Member = None):
        """Show information about a member.

        This includes fields for status, discord join date, server
        join date, voice state and previous usernames/global display names/nicknames.

        If the member has no roles, previous usernames, global display names, or server nicknames,
        these fields will be omitted.
        """

        author = ctx.author
        guild = ctx.guild
        if not member:
            member = author
        roles = member.roles[-1:0:-1]
        usernames, display_names, nicks = await self.get_names(member)
        joined_at = member.joined_at
        voice_state = member.voice
        member_number = (
            sorted(
                guild.members, key=lambda m: m.joined_at or ctx.message.created_at
            ).index(member)
            + 1
        )
        created_on = (
            f"{discord.utils.format_dt(member.created_at)}\n"
            f"{discord.utils.format_dt(member.created_at, 'R')}"
        )
        if joined_at is not None:
            joined_on = (
                f"{discord.utils.format_dt(joined_at)}\n"
                f"{discord.utils.format_dt(joined_at, 'R')}"
            )
        else:
            joined_on = _("Unknown")
        if any(a.type is discord.ActivityType.streaming for a in member.activities):
            statusemoji = "\N{LARGE PURPLE CIRCLE}"
        elif member.status.name == "online":
            statusemoji = "\N{LARGE GREEN CIRCLE}"
        elif member.status.name == "offline":
            statusemoji = "\N{MEDIUM WHITE CIRCLE}\N{VARIATION SELECTOR-16}"
        elif member.status.name == "dnd":
            statusemoji = "\N{LARGE RED CIRCLE}"
        elif member.status.name == "idle":
            statusemoji = "\N{LARGE ORANGE CIRCLE}"
        activity = _("Chilling in {} status").format(member.status)
        status_string = self.get_status_string(member)
        if roles:
            role_str = ", ".join([x.mention for x in roles])
            # 400 BAD REQUEST (error code: 50035): Invalid Form Body
            # In embed.fields.2.value: Must be 1024 or fewer in length.
            if len(role_str) > 1024:
                # Alternative string building time.
                # This is not the most optimal, but if you're hitting this, you are losing more time
                # to every single check running on users than the occasional user info invoke
                # We don't start by building this way, since the number of times we hit this should be
                # infinitesimally small compared to when we don't across all uses of Grief.
                continuation_string = _(
                    "and {numeric_number} more roles not displayed due to embed limits."
                )
                available_length = 1024 - len(
                    continuation_string
                )  # do not attempt to tweak, i18n

                role_chunks = []
                remaining_roles = 0
                for r in roles:
                    chunk = f"{r.mention}, "
                    chunk_size = len(chunk)

                    if chunk_size < available_length:
                        available_length -= chunk_size
                        role_chunks.append(chunk)
                    else:
                        remaining_roles += 1

                role_chunks.append(
                    continuation_string.format(numeric_number=remaining_roles)
                )

                role_str = "".join(role_chunks)
        else:
            role_str = None
        data = discord.Embed(description=status_string or activity, colour=0x313338)
        button1 = discord.ui.Button(
            emoji="<:info:1202073815140810772>",
            label=f"profile",
            style=discord.ButtonStyle.url,
            url=f"https://discordapp.com/users/{member.id}",
        )
        view = discord.ui.View()
        view.add_item(button1)
        data.add_field(name=_("Joined Discord on"), value=created_on)
        data.add_field(name=_("Joined this server on"), value=joined_on)
        if role_str is not None:
            data.add_field(
                name=_("Roles") if len(roles) > 1 else _("Role"),
                value=role_str,
                inline=False,
            )
        for single_form, plural_form, names in (
            (_("Previous Username"), _("Previous Usernames"), usernames),
            (
                _("Previous Global Display Name"),
                _("Previous Global Display Names"),
                display_names,
            ),
            (_("Previous Server Nickname"), _("Previous Server Nicknames"), nicks),
        ):
            if names:
                data.add_field(
                    name=plural_form if len(names) > 1 else single_form,
                    value=filter_invites(", ".join(names)),
                    inline=False,
                )
        if voice_state and voice_state.channel:
            data.add_field(
                name=_("Current voice channel"),
                value="{0.mention} ID: {0.id}".format(voice_state.channel),
                inline=False,
            )
        data.set_footer(text=_("Join Position: {}").format(member_number))
        name = str(member)
        name = " ~ ".join((name, member.nick)) if member.nick else name
        name = filter_invites(name)
        avatar = member.display_avatar.replace(static_format="png")
        data.set_author(name=f"{statusemoji} {name}", url=avatar)
        data.set_thumbnail(url=avatar)
        user = await self.bot.fetch_user(member.id)
        if user.banner is not None:
            data.set_image(url=user.banner.url)
        await ctx.reply(embed=data, view=view, mention_author=False)

    @staticmethod
    def _update_past_names(name: str, name_list: List[Optional[str]]) -> None:
        while None in name_list:  # clean out null entries from a bug
            name_list.remove(None)
        if name in name_list:
            # Ensure order is maintained without duplicates occurring
            name_list.remove(name)
        name_list.append(name)
        while len(name_list) > 20:
            name_list.pop(0)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.name != after.name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_names() as name_list:
                self._update_past_names(before.name, name_list)
        if before.display_name != after.display_name:
            track_all_names = await self.config.track_all_names()
            if not track_all_names:
                return
            async with self.config.user(before).past_display_names() as name_list:
                self._update_past_names(before.display_name, name_list)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick and before.nick is not None:
            guild = after.guild
            if (not guild) or await self.bot.cog_disabled_in_guild(self, guild):
                return
            track_all_names = await self.config.track_all_names()
            track_nicknames = await self.config.guild(guild).track_nicknames()
            if (not track_all_names) or (not track_nicknames):
                return
            async with self.config.member(before).past_nicks() as nick_list:
                self._update_past_names(before.nick, nick_list)


async def setup(bot: Grief) -> None:
    await bot.add_cog(Names(bot))
