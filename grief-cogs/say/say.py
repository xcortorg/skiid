import asyncio
import logging
import re
from typing import TYPE_CHECKING, Optional

import discord
from discord import app_commands

from grief.core import checks, commands
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils.tunnel import Tunnel

if TYPE_CHECKING:
    from grief.core.bot import Grief

log = logging.getLogger("grief.say")
_ = Translator("Say", __file__)


ROLE_MENTION_REGEX = re.compile(r"<@&(?P<id>[0-9]{17,19})>")


@cog_i18n(_)
class Say(commands.Cog):
    """grief will repeat after you."""

    def __init__(self, bot: "Grief"):
        self.bot = bot
        self.interaction = []

    async def say(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        text: str,
        files: list,
        mentions: discord.AllowedMentions = None,
        delete: int = None,
    ):
        if not channel:
            channel = ctx.channel
        if not text and not files:
            await ctx.send_help()
            return

        author = ctx.author
        guild = ctx.guild

        # checking perms
        if not channel.permissions_for(guild.me).send_messages:
            if channel != ctx.channel:
                await ctx.send(
                    _("I am not allowed to send messages in ") + channel.mention,
                    delete_after=2,
                )
            else:
                await author.send(
                    _("I am not allowed to send messages in ") + channel.mention
                )
                # If this fails then fuck the command author
            return

        if files and not channel.permissions_for(guild.me).attach_files:
            try:
                await ctx.send(
                    _("I am not allowed to upload files in ") + channel.mention,
                    delete_after=2,
                )
            except discord.errors.Forbidden:
                await author.send(
                    _("I am not allowed to upload files in ") + channel.mention,
                    delete_after=15,
                )
            return

        try:
            await channel.send(
                text, files=files, allowed_mentions=mentions, delete_after=delete
            )
        except discord.errors.HTTPException:
            try:
                await ctx.send("An error occured when sending the message.")
            except discord.errors.HTTPException:
                pass
            log.error("Failed to send message.", exc_info=True)

    @commands.command(name="say")
    @commands.has_permissions(administrator=True, manage_guild=True)
    async def _say(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        *,
        text: str = "",
    ):
        """
        Make the bot say what you want in the desired channel.

        If no channel is specified, the message will be send in the current channel.
        You can attach some files to upload them to Discord.

        Example usage :
        - `!say #general hello there`
        - `!say owo I have a file` (a file is attached to the command message)
        """

        files = await Tunnel.files_from_attatch(ctx.message)
        await self.say(ctx, channel, text, files)

    @commands.command(name="sayad")
    @commands.has_permissions(administrator=True, manage_guild=True)
    async def _sayautodelete(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        delete_delay: int,
        *,
        text: str = "",
    ):
        """
        Same as say command, except it deletes the said message after a set number of seconds.
        """

        files = await Tunnel.files_from_attatch(ctx.message)
        await self.say(ctx, channel, text, files, delete=delete_delay)

    @commands.command(name="sayd", aliases=["sd"])
    @commands.has_permissions(administrator=True, manage_guild=True)
    async def _saydelete(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        *,
        text: str = "",
    ):
        """
        Same as say command, except it deletes your message.

        If the message wasn't removed, then I don't have enough permissions.
        """

        # download the files BEFORE deleting the message
        author = ctx.author
        files = await Tunnel.files_from_attatch(ctx.message)

        try:
            await ctx.message.delete()
        except discord.errors.Forbidden:
            try:
                await ctx.send(
                    _("Not enough permissions to delete messages."), delete_after=2
                )
            except discord.errors.Forbidden:
                await author.send(
                    _("Not enough permissions to delete messages."), delete_after=15
                )

        await self.say(ctx, channel, text, files)

    @commands.command(name="saym", aliases=["sm"])
    @commands.has_permissions(administrator=True, manage_guild=True)
    async def _saymention(
        self,
        ctx: commands.Context,
        channel: Optional[discord.TextChannel],
        *,
        text: str = "",
    ):
        """
        Same as say command, except role and mass mentions are enabled.
        """
        message = ctx.message
        channel = channel or ctx.channel
        guild = channel.guild
        files = await Tunnel.files_from_attach(message)

        role_mentions = list(
            filter(
                None,
                (
                    ctx.guild.get_role(int(x))
                    for x in ROLE_MENTION_REGEX.findall(message.content)
                ),
            )
        )
        mention_everyone = "@everyone" in message.content or "@here" in message.content
        if not role_mentions and not mention_everyone:
            # no mentions, nothing to check
            return await self.say(ctx, channel, text, files)
        non_mentionable_roles = [x for x in role_mentions if x.mentionable is False]

        if not channel.permissions_for(guild.me).mention_everyone:
            if non_mentionable_roles:
                await ctx.send(
                    _(
                        "I can't mention the following roles: {roles}\nTurn on "
                        "mentions or grant me the correct permissions.\n"
                    ).format(roles=", ".join([x.name for x in non_mentionable_roles]))
                )
                return
            if mention_everyone:
                await ctx.send(_("I don't have the permission to mention everyone."))
                return
        if not channel.permissions_for(ctx.author).mention_everyone:
            if non_mentionable_roles:
                await ctx.send(
                    _(
                        "You're not allowed to mention the following roles: {roles}\nTurn on "
                        "mentions for that role or have the correct permissions.\n"
                    ).format(roles=", ".join([x.name for x in non_mentionable_roles]))
                )
                return
            if mention_everyone:
                await ctx.send(
                    _("You don't have the permission yourself to do mass mentions.")
                )
                return
        await self.say(
            ctx,
            channel,
            text,
            files,
            mentions=discord.AllowedMentions(everyone=True, roles=True),
        )

    # ----- Slash commands -----
    @app_commands.command(name="say", description="Make the bot send a message")
    @app_commands.describe(
        message="The content of the message you want to send",
        channel="The channel where you want to send the message (default to current)",
        delete_delay="Delete the message sent after X seconds",
        mentions="Allow @everyone, @here and role mentions in your message",
        file="A file you want to attach to the message sent (message content becomes optional)",
    )
    @app_commands.default_permissions()
    @app_commands.guild_only()
    async def slash_say(
        self,
        interaction: discord.Interaction,
        message: Optional[str] = "",
        channel: Optional[discord.TextChannel] = None,
        delete_delay: Optional[int] = None,
        mentions: Optional[bool] = False,
        file: Optional[discord.Attachment] = None,
    ):
        guild = interaction.guild
        channel = channel or interaction.channel

        if not message and not file:
            await interaction.response.send_message(
                _("You cannot send an empty message."), ephemeral=True
            )
            return

        if not channel.permissions_for(guild.me).send_messages:
            await interaction.response.send_message(
                _("I don't have the permission to send messages there."), ephemeral=True
            )
            return
        if file and not channel.permissions_for(guild.me).attach_files:
            await interaction.response.send_message(
                _("I don't have the permission to upload files there."), ephemeral=True
            )
            return

        if mentions:
            mentions = discord.AllowedMentions(
                everyone=interaction.user.guild_permissions.mention_everyone,
                roles=interaction.user.guild_permissions.mention_everyone
                or [x for x in interaction.guild.roles if x.mentionable],
            )
        else:
            mentions = None

        file = await file.to_file(use_cached=True) if file else None
        try:
            await channel.send(message, file=file, delete_after=delete_delay)
        except discord.HTTPException:
            await interaction.response.send_message(
                _("An error occured when sending the message."), ephemeral=True
            )
            log.error(
                f"Cannot send message in {channel.name} ({channel.id}) requested by "
                f"{interaction.user} ({interaction.user.id}). "
                f"Command: {interaction.message.content}",
                exc_info=True,
            )
        else:
            # acknowledge the command, but don't actually send an additional message
            await interaction.response.defer(ephemeral=False)
            await interaction.followup.delete_message("@original")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user in self.interaction:
            channel = reaction.message.channel
            if isinstance(channel, discord.DMChannel):
                await self.stop_interaction(user)

    async def stop_interaction(self, user):
        self.interaction.remove(user)
        await user.send(_("Session closed"))

    async def cog_unload(self):
        for user in self.interaction:
            await self.stop_interaction(user)
