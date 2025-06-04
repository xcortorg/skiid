from AAA3A_utils import Cog, CogsUtils  # isort:skip
from grief.core import commands  # isort:skip
from grief.core.i18n import Translator, cog_i18n  # isort:skip
from grief.core.bot import Grief  # isort:skip
import discord  # isort:skip
import typing  # isort:skip

import datetime

from grief.core.commands.converter import get_timedelta_converter
from grief.core.utils.chat_formatting import box

TimedeltaConverter = get_timedelta_converter(
    default_unit="s",
    maximum=datetime.timedelta(seconds=21600),
    minimum=datetime.timedelta(seconds=0),
)


def _(untranslated: str) -> str:  # `redgettext` will found these strings.
    return untranslated


ERROR_MESSAGE = _(
    "I attempted to do something that Discord denied me permissions for. Your command failed to successfully complete.\n{error}"
)

_ = Translator("DiscordEdit", __file__)


class LocaleConverter(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        try:
            return discord.Locale(argument)
        except ValueError:
            raise commands.BadArgument(
                _("Converting to `Locale` failed for parameter `preferred_locale`.")
            )


@cog_i18n(_)
class EditGuild(Cog):
    """A cog to edit guilds!"""

    def __init__(self, bot: Grief) -> None:  # Never executed except manually.
        super().__init__(bot=bot)

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @commands.hybrid_group()
    async def editguild(self, ctx: commands.Context) -> None:
        """Commands for edit a guild."""
        pass

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="name")
    async def editguild_name(self, ctx: commands.Context, *, name: str) -> None:
        """Edit guild name."""
        guild = ctx.guild
        try:
            await guild.edit(
                name=name,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="description")
    async def editguild_description(
        self, ctx: commands.Context, *, description: typing.Optional[str] = None
    ) -> None:
        """Edit guild description."""
        guild = ctx.guild
        try:
            await guild.edit(
                description=description,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="community")
    async def editguild_community(self, ctx: commands.Context, community: bool) -> None:
        """Edit guild community state."""
        guild = ctx.guild
        try:
            await guild.edit(
                community=community,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="afkchannel")
    async def editguild_afk_channel(
        self,
        ctx: commands.Context,
        *,
        afk_channel: typing.Optional[discord.VoiceChannel] = None,
    ) -> None:
        """Edit guild afkchannel."""
        guild = ctx.guild
        try:
            await guild.edit(
                afk_channel=afk_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="afktimeout")
    async def editguild_afk_timeout(
        self, ctx: commands.Context, afk_timeout: int
    ) -> None:
        """Edit guild afktimeout."""
        guild = ctx.guild
        try:
            await guild.edit(
                afk_timeout=afk_timeout,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="verificationlevel")
    async def editguild_verification_level(
        self, ctx: commands.Context, verification_level: discord.VerificationLevel
    ) -> None:
        """Edit guild verification level."""
        guild = ctx.guild
        try:
            await guild.edit(
                verification_level=verification_level,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="defaultnotifications", aliases=["notificationslevel"])
    async def editguild_default_notifications(
        self, ctx: commands.Context, default_notifications: typing.Literal["0", "1"]
    ) -> None:
        """Edit guild notification level."""
        guild = ctx.guild
        default_notifications = discord.NotificationLevel(int(default_notifications))
        try:
            await guild.edit(
                default_notifications=default_notifications,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="explicitcontentfilter")
    async def editguild_explicit_content_filter(
        self, ctx: commands.Context, explicit_content_filter: discord.ContentFilter
    ) -> None:
        """Edit guild explicit content filter."""
        guild = ctx.guild
        try:
            await guild.edit(
                explicit_content_filter=explicit_content_filter,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="systemchannel")
    async def editguild_system_channel(
        self,
        ctx: commands.Context,
        system_channel: typing.Optional[discord.TextChannel] = None,
    ) -> None:
        """Edit guild system channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                system_channel=system_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="systemchannelflags")
    async def editguild_system_channel_flags(
        self, ctx: commands.Context, system_channel_flags: int
    ) -> None:
        """Edit guild system channel flags."""
        guild = ctx.guild
        _system_channel_flags = discord.SystemChannelFlags()
        _system_channel_flags.value = system_channel_flags
        try:
            await guild.edit(
                system_channel_flags=_system_channel_flags,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="ruleschannel")
    async def editguild_rules_channel(
        self,
        ctx: commands.Context,
        rules_channel: typing.Optional[discord.TextChannel] = None,
    ) -> None:
        """Edit guild rules channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                rules_channel=rules_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="publicupdateschannel")
    async def editguild_public_updates_channel(
        self,
        ctx: commands.Context,
        public_updates_channel: typing.Optional[discord.TextChannel] = None,
    ) -> None:
        """Edit guild public updates channel."""
        guild = ctx.guild
        try:
            await guild.edit(
                public_updates_channel=public_updates_channel,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="premiumprogressbarenabled")
    async def editguild_premium_progress_bar_enabled(
        self, ctx: commands.Context, premium_progress_bar_enabled: bool = None
    ) -> None:
        """Edit guild premium progress bar enabled."""
        guild = ctx.guild
        if premium_progress_bar_enabled is None:
            premium_progress_bar_enabled = not guild.premium_progress_bar_enabled
        try:
            await guild.edit(
                premium_progress_bar_enabled=premium_progress_bar_enabled,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="discoverable")
    async def editguild_discoverable(
        self, ctx: commands.Context, discoverable: bool
    ) -> None:
        """Edit guild discoverable state."""
        guild = ctx.guild
        try:
            await guild.edit(
                discoverable=discoverable,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @editguild.command(name="invitesdisabled")
    async def editguild_invites_disabled(
        self, ctx: commands.Context, invites_disabled: bool
    ) -> None:
        """Edit guild invites disabled state."""
        guild = ctx.guild
        try:
            await guild.edit(
                invites_disabled=invites_disabled,
                reason=f"{ctx.author} ({ctx.author.id}) has edited the guild {guild.name} ({guild.id}).",
            )
        except discord.HTTPException as e:
            raise commands.UserFeedbackCheckFailure(
                _(ERROR_MESSAGE).format(error=box(e, lang="py"))
            )
