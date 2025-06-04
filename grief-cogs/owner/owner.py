### FROM SERVERSTATS
import asyncio
import concurrent
import datetime
import json
import logging
import os
import pathlib
import platform
import random
import re
import subprocess
import time
import typing as t
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from datetime import datetime, timedelta, timezone
from io import BytesIO
from sys import executable
from time import perf_counter
from typing import Dict, List, Literal, Optional, Tuple, Union, cast

import aiohttp
import colorama
import cpuinfo
import discord
import psutil
import speedtest
from discord import Embed
from discord.utils import get

from grief import VersionInfo, version_info
from grief.core import Config, checks, commands, data_manager
from grief.core.bot import Grief
from grief.core.commands.context import Context
from grief.core.i18n import Translator, cog_i18n
from grief.core.utils import AsyncIter
from grief.core.utils.chat_formatting import (bold, box, escape, humanize_list,
                                              humanize_number,
                                              humanize_timedelta, pagify,
                                              text_to_file)
from grief.core.utils.menus import start_adding_reactions
from grief.core.utils.predicates import MessagePredicate, ReactionPredicate

from .converters import (GuildConverter, MultiGuildConverter,
                         PermissionConverter)
from .diskspeed import get_disk_speed
from .dpymenu import DEFAULT_CONTROLS, confirm, menu
from .menus import BaseView, GuildPages, ListPages

_ = Translator("Owner", __file__)
log = logging.getLogger("grief.owner")


@cog_i18n(_)
class Owner(commands.Cog):
    """
    Gather useful information about servers the bot is in.
    """

    default_role = {"banned_members": []}

    def __init__(self, bot):
        self.bot = bot
        self.saveFolder = data_manager.cog_data_path(cog_instance=self)
        default_global: dict = {"join_channel": None}
        default_guild: dict = {
            "last_checked": 0,
            "members": {},
            "total": 0,
            "channels": {},
        }
        self.config: Config = Config.get_conf(
            self, 54853421465543, force_registration=True
        )
        self.config.register_role(**self.default_role)
        self.config.register_global(**default_global)
        self.config.register_guild(**default_guild)

    @staticmethod
    def get_size(num: float) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(num) < 1024.0:
                return "{0:.1f}{1}".format(num, unit)
            num /= 1024.0
        return "{0:.1f}{1}".format(num, "YB")

    @staticmethod
    def get_bitsize(num: float) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
            if abs(num) < 1000.0:
                return "{0:.1f}{1}".format(num, unit)
            num /= 1000.0
        return "{0:.1f}{1}".format(num, "YB")

    @staticmethod
    def get_bar(progress, total, perc=None, width: int = 20) -> str:
        fill = "▰"
        space = "▱"
        if perc is not None:
            ratio = perc / 100
        else:
            ratio = progress / total
        bar = fill * round(ratio * width) + space * round(width - (ratio * width))
        return f"{bar} {round(100 * ratio, 1)}%"

    async def do_shell_command(self, command: str):
        cmd = f"{executable} -m {command}"

        def exe():
            results = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
            )
            return results.stdout.decode("utf-8") or results.stderr.decode("utf-8")

        res = await asyncio.to_thread(exe)
        return res

    async def run_disk_speed(
        self,
        block_count: int = 128,
        block_size: int = 1048576,
        passes: int = 1,
    ) -> dict:
        reads = []
        writes = []
        with ThreadPoolExecutor(max_workers=1) as pool:
            futures = [
                self.bot.loop.run_in_executor(
                    pool,
                    lambda: get_disk_speed(self.path, block_count, block_size),
                )
                for _ in range(passes)
            ]
            results = await asyncio.gather(*futures)
            for i in results:
                reads.append(i["read"])
                writes.append(i["write"])
        results = {
            "read": sum(reads) / len(reads),
            "write": sum(writes) / len(writes),
        }
        return results

    @commands.command()
    @commands.is_owner()
    async def dm(self, ctx, user: discord.User, *, message: str):
        """
        Dm raw text to a user.
        """
        destination = get(self.bot.get_all_members(), id=user.id)
        if not destination:
            return await ctx.send(
                "Invalid ID or user not found. You can only send messages to people I share a server with.",
            )
        await destination.send(message)
        await ctx.tick()

    ### FROM SERVERSTATS
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.group(invoke_without_command=True)
    async def ping(self, ctx):
        """View bot latency."""
        start = time.monotonic()
        ref = ctx.message.to_reference(fail_if_not_exists=False)
        message = await ctx.send("Pinging...", reference=ref)
        end = time.monotonic()
        totalPing = round((end - start) * 1000, 2)
        e = discord.Embed(
            title="Pinging..", description=f"{'Overall Latency':<16}:{totalPing}ms"
        )
        await asyncio.sleep(0.25)
        try:
            await message.edit(content=None, embed=e)
        except discord.NotFound:
            return

        botPing = round(self.bot.latency * 1000, 2)
        e.description = e.description + f"\n{'Discord WS':<16}:{botPing}ms"
        await asyncio.sleep(0.25)

        averagePing = (botPing + totalPing) / 2
        if averagePing >= 1000:
            color = discord.Colour.dark_theme()
        elif averagePing >= 200:
            color = discord.Colour.dark_theme()
        else:
            color = discord.Colour.dark_theme()

        e.color = color

        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        loop = asyncio.get_event_loop()
        try:
            s = speedtest.Speedtest(secure=True)
            await loop.run_in_executor(executor, s.get_servers)
            await loop.run_in_executor(executor, s.get_best_server)
        except Exception as exc:
            host_latency = "`Failed`"
        else:
            result = s.results.dict()
            host_latency = round(result["ping"], 2)
            host_latency = f"{host_latency}ms"

        e.title = "Pong!"
        e.description = e.description + f"\n{'Host Latency':<16}:{host_latency}"
        await asyncio.sleep(0.25)
        try:
            await message.edit(embed=e)
        except discord.NotFound:
            return

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Build and send a message containing serverinfo when the bot joins a new server"""
        channel_id = await self.config.join_channel()
        if channel_id is None:
            return
        channel = self.bot.get_channel(channel_id)
        passed = f"<t:{int(guild.created_at.timestamp())}:R>"

        created_at = _(
            "{bot} has joined a server.\n "
            "That's **{num}** servers now.\n"
            "That's a total of **{users}** users .\n"
            "Server created on **{since}**. "
            "That's over **{passed}**."
        ).format(
            bot=channel.guild.me.mention,
            num=humanize_number(len(self.bot.guilds)),
            users=humanize_number(len(self.bot.users)),
            since=f"<t:{int(guild.created_at.timestamp())}:D>",
            passed=passed,
        )
        try:
            em = await self.guild_embed(guild)
            em.description = created_at
            await channel.send(embed=em)
        except Exception:
            log.error(
                f"Error creating guild embed for new guild ID {guild.id}", exc_info=True
            )

    async def guild_embed(self, guild: discord.Guild) -> discord.Embed:
        """
        Builds the guild embed information used throughout the cog
        """

        def _size(num):
            for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                if abs(num) < 1024.0:
                    return "{0:.1f}{1}".format(num, unit)
                num /= 1024.0
            return "{0:.1f}{1}".format(num, "YB")

        def _bitsize(num):
            for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                if abs(num) < 1000.0:
                    return "{0:.1f}{1}".format(num, unit)
                num /= 1000.0
            return "{0:.1f}{1}".format(num, "YB")

        created_at = _("Created on {date}. That's over {num}!").format(
            date=bold(f"<t:{int(guild.created_at.timestamp())}:D>"),
            num=bold(f"<t:{int(guild.created_at.timestamp())}:R>"),
        )
        total_users = humanize_number(guild.member_count)

        try:
            joined_at = guild.me.joined_at
        except AttributeError:
            joined_at = datetime.now(timezone.utc)
        bot_joined = f"<t:{int(joined_at.timestamp())}:D>"
        since_joined = f"<t:{int(joined_at.timestamp())}:R>"
        joined_on = _(
            "**{bot_name}** joined this server on **{bot_join}**.\n"
            "That's over **{since_join}**!"
        ).format(
            bot_name=self.bot.user.mention, bot_join=bot_joined, since_join=since_joined
        )

        shard = (
            _("\nShard ID: **{shard_id}/{shard_count}**").format(
                shard_id=humanize_number(guild.shard_id + 1),
                shard_count=humanize_number(self.bot.shard_count),
            )
            if self.bot.shard_count > 1
            else ""
        )
        colour = 0x313338

        online_stats = {
            _("Humans: "): lambda x: not x.bot,
            _(" • Bots: "): lambda x: x.bot,
            "\N{LARGE GREEN CIRCLE}": lambda x: x.status is discord.Status.online,
            "\N{LARGE ORANGE CIRCLE}": lambda x: x.status is discord.Status.idle,
            "\N{LARGE RED CIRCLE}": lambda x: x.status is discord.Status.do_not_disturb,
            "\N{MEDIUM WHITE CIRCLE}": lambda x: x.status is discord.Status.offline,
            "\N{LARGE PURPLE CIRCLE}": lambda x: (
                x.activity is not None
                and x.activity.type is discord.ActivityType.streaming
            ),
        }
        member_msg = _("Total Users: {}\n").format(bold(total_users))
        count = 1
        for emoji, value in online_stats.items():
            try:
                num = len([m for m in guild.members if value(m)])
            except Exception as error:
                print(error)
                continue
            else:
                member_msg += f"{emoji} {bold(humanize_number(num))} " + (
                    "\n" if count % 2 == 0 else ""
                )
            count += 1

        text_channels = len(guild.text_channels)
        nsfw_channels = len([c for c in guild.text_channels if c.is_nsfw()])
        voice_channels = len(guild.voice_channels)
        verif = {
            "none": _("0 - None"),
            "low": _("1 - Low"),
            "medium": _("2 - Medium"),
            "high": _("3 - High"),
            "extreme": _("4 - Extreme"),
            "highest": _("4 - Highest"),
        }

        features = {
            "ANIMATED_ICON": _("Animated Icon"),
            "BANNER": _("Banner Image"),
            "COMMERCE": _("Commerce"),
            "COMMUNITY": _("Community"),
            "DISCOVERABLE": _("Server Discovery"),
            "FEATURABLE": _("Featurable"),
            "INVITE_SPLASH": _("Splash Invite"),
            "MEMBER_LIST_DISABLED": _("Member list disabled"),
            "MEMBER_VERIFICATION_GATE_ENABLED": _("Membership Screening enabled"),
            "MORE_EMOJI": _("More Emojis"),
            "NEWS": _("News Channels"),
            "PARTNERED": _("Partnered"),
            "PREVIEW_ENABLED": _("Preview enabled"),
            "PUBLIC_DISABLED": _("Public disabled"),
            "VANITY_URL": _("Vanity URL"),
            "VERIFIED": _("Verified"),
            "VIP_REGIONS": _("VIP Voice Servers"),
            "WELCOME_SCREEN_ENABLED": _("Welcome Screen enabled"),
        }
        guild_features_list = [
            f"✅ {name}"
            for feature, name in features.items()
            if feature in guild.features
        ]

        em = discord.Embed(
            description=(f"{guild.description}\n\n" if guild.description else "")
            + f"{created_at}\n{joined_on}",
            colour=0x313338,
        )
        author_icon = None
        if "VERIFIED" in guild.features:
            author_icon = "https://cdn.discordapp.com/emojis/457879292152381443.png"
        if "PARTNERED" in guild.features:
            author_icon = "https://cdn.discordapp.com/emojis/508929941610430464.png"
        guild_icon = "https://cdn.discordapp.com/embed/avatars/1.png"
        if guild.icon:
            guild_icon = guild.icon.url
        em.set_author(
            name=guild.name,
            icon_url=author_icon,
            url=guild_icon,
        )
        em.set_thumbnail(
            url=(
                guild.icon.url
                if guild.icon
                else "https://cdn.discordapp.com/embed/avatars/1.png"
            )
        )
        em.add_field(name=_("Members:"), value=member_msg)
        em.add_field(
            name=_("Channels:"),
            value=_(
                "\N{SPEECH BALLOON} Text: {text}\n{nsfw}"
                "\N{SPEAKER WITH THREE SOUND WAVES} Voice: {voice}"
            ).format(
                text=bold(humanize_number(text_channels)),
                nsfw=(
                    _("\N{NO ONE UNDER EIGHTEEN SYMBOL} Nsfw: {}\n").format(
                        bold(humanize_number(nsfw_channels))
                    )
                    if nsfw_channels
                    else ""
                ),
                voice=bold(humanize_number(voice_channels)),
            ),
        )
        owner = (
            guild.owner
            if guild.owner
            else await self.bot.get_or_fetch_user(guild.owner_id)
        )
        em.add_field(
            name=_("Utility:"),
            value=_(
                "Owner: {owner_mention}\n{owner}\nVerif. level: {verif}\nServer ID: {id}{shard}"
            ).format(
                owner_mention=bold(str(owner.mention)),
                owner=bold(str(owner)),
                verif=bold(verif[str(guild.verification_level)]),
                id=bold(str(guild.id)),
                shard=shard,
            ),
            inline=False,
        )
        em.add_field(
            name=_("Misc:"),
            value=_(
                "AFK channel: {afk_chan}\nAFK timeout: {afk_timeout}\nCustom emojis: {emojis}\nRoles: {roles}"
            ).format(
                afk_chan=(
                    bold(str(guild.afk_channel))
                    if guild.afk_channel
                    else bold(_("Not set"))
                ),
                afk_timeout=bold(humanize_timedelta(seconds=guild.afk_timeout)),
                emojis=bold(humanize_number(len(guild.emojis))),
                roles=bold(humanize_number(len(guild.roles))),
            ),
            inline=False,
        )
        if guild_features_list:
            em.add_field(
                name=_("Server features:"), value="\n".join(guild_features_list)
            )
        if guild.premium_tier != 0:
            nitro_boost = _(
                "Tier {boostlevel} with {nitroboosters} boosters\n"
                "File size limit: {filelimit}\n"
                "Emoji limit: {emojis_limit}\n"
                "VCs max bitrate: {bitrate}"
            ).format(
                boostlevel=bold(str(guild.premium_tier)),
                nitroboosters=bold(humanize_number(guild.premium_subscription_count)),
                filelimit=bold(_size(guild.filesize_limit)),
                emojis_limit=bold(str(guild.emoji_limit)),
                bitrate=bold(_bitsize(guild.bitrate_limit)),
            )
            em.add_field(name=_("Nitro Boost:"), value=nitro_boost)
        if guild.splash:
            em.set_image(url=guild.splash.url)
        return em

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """Build and send a message containing serverinfo when the bot leaves a server"""
        channel_id = await self.config.join_channel()
        if channel_id is None:
            return
        channel = self.bot.get_channel(channel_id)
        passed = f"<t:{int(guild.created_at.timestamp())}:R>"
        created_at = _(
            "{bot} has left a server!\n "
            "That's **{num}** servers now!\n"
            "That's a total of **{users}** users !\n"
            "Server created on **{since}**. "
            "That's over **{passed}**!"
        ).format(
            bot=channel.guild.me.mention,
            num=humanize_number(len(self.bot.guilds)),
            users=humanize_number(len(self.bot.users)),
            since=f"<t:{int(guild.created_at.timestamp())}:D>",
            passed=passed,
        )
        try:
            em = await self.guild_embed(guild)
            em.description = created_at
            await channel.send(embed=em)
        except Exception:
            log.error(
                f"Error creating guild embed for old guild ID {guild.id}", exc_info=True
            )

    @commands.command()
    @checks.is_owner()
    @commands.bot_has_permissions(embed_links=True)
    @commands.guild_only()
    async def setguildjoin(
        self, ctx: commands.Context, channel: discord.TextChannel = None
    ) -> None:
        """
        Set a channel to see new servers the bot is joining
        """
        if channel is None:
            channel = ctx.message.channel
        await self.config.join_channel.set(channel.id)
        msg = _("Posting new servers and left servers in ") + channel.mention
        await ctx.send(msg)

    @commands.command()
    @checks.is_owner()
    async def removeguildjoin(self, ctx: commands.Context) -> None:
        """
        Stop bots join/leave server messages
        """
        await self.config.join_channel.clear()
        await ctx.send(_("No longer posting joined or left servers."))

    @staticmethod
    async def confirm_leave_guild(ctx: commands.Context, guild) -> None:
        await ctx.send(
            _("Are you sure you want me to leave {guild}? (reply yes or no)").format(
                guild=guild.name
            )
        )
        pred = MessagePredicate.yes_or_no(ctx)
        await ctx.bot.wait_for("message", check=pred)
        if pred.result is True:
            try:
                await ctx.send(_("Leaving {guild}.").format(guild=guild.name))
                await guild.leave()
            except Exception:
                log.error(
                    _("I couldn't leave {guild} ({g_id}).").format(
                        guild=guild.name, g_id=guild.id
                    ),
                    exc_info=True,
                )
                await ctx.send(_("I couldn't leave {guild}.").format(guild=guild.name))
        else:
            await ctx.send(_("Okay, not leaving {guild}.").format(guild=guild.name))

    @staticmethod
    async def get_guild_invite(
        guild: discord.Guild, max_age: int = 86400
    ) -> Optional[discord.Invite]:
        """Handles the reinvite logic for getting an invite
        to send the newly unbanned user
        :returns: :class:`Invite`

        https://github.com/Cog-Creators/Grief-DiscordBot/blob/V3/develop/redbot/cogs/mod/mod.py#L771
        """
        my_perms: discord.Permissions = guild.me.guild_permissions
        if my_perms.manage_guild or my_perms.administrator:
            if "VANITY_URL" in guild.features:
                # guild has a vanity url so use it as the one to send
                try:
                    return await guild.vanity_invite()
                except discord.errors.Forbidden:
                    invites = []
            invites = await guild.invites()
        else:
            invites = []
        for inv in invites:  # Loop through the invites for the guild
            if not (inv.max_uses or inv.max_age or inv.temporary):
                # Invite is for the guild's default channel,
                # has unlimited uses, doesn't expire, and
                # doesn't grant temporary membership
                # (i.e. they won't be kicked on disconnect)
                return inv
        else:  # No existing invite found that is valid
            channels_and_perms = zip(
                guild.text_channels,
                map(lambda x: x.permissions_for(guild.me), guild.text_channels),
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
                return
            try:
                # Create invite that expires after max_age
                return await channel.create_invite(max_age=max_age)
            except discord.HTTPException:
                return

    @commands.is_owner()
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.bot_has_permissions(
        read_message_history=True, add_reactions=True, embed_links=True
    )
    async def getguild(
        self, ctx: commands.Context, *, guild: GuildConverter = None
    ) -> None:
        """
        Display info about servers the bot is on

        `guild_name` can be either the server ID or partial name
        """
        async with ctx.typing():
            if not ctx.guild and not await ctx.bot.is_owner(ctx.author):
                return await ctx.send(_("This command is not available in DM."))
            guilds = [ctx.guild]
            page = 0
            if await ctx.bot.is_owner(ctx.author):
                if ctx.guild:
                    page = ctx.bot.guilds.index(ctx.guild)
                guilds = ctx.bot.guilds
                if guild:
                    page = ctx.bot.guilds.index(guild)

        await BaseView(
            source=GuildPages(guilds=guilds),
            cog=self,
            page_start=page,
            ctx=ctx,
        ).start(ctx=ctx)

    @commands.is_owner()
    @commands.hybrid_command()
    @commands.bot_has_permissions(embed_links=True)
    @commands.bot_has_permissions(
        read_message_history=True, add_reactions=True, embed_links=True
    )
    async def getguilds(
        self, ctx: commands.Context, *, guilds: MultiGuildConverter
    ) -> None:
        """
        Display info about multiple servers

        `guild_name` can be either the server ID or partial name
        """
        async with ctx.typing():
            page = 0
            if not guilds:
                guilds = ctx.bot.guilds
                page = ctx.bot.guilds.index(ctx.guild)
        await BaseView(
            source=GuildPages(guilds=guilds),
            cog=self,
            page_start=page,
        ).start(ctx=ctx)

    @commands.command()
    @commands.is_owner()
    async def banrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Ban all members with the specified role

        The bot's role must be higher than the role you want to ban
        """
        failures = "I failed to ban the following members:\n"
        failure_list = []
        mod_cog = self.bot.get_cog("Mod")
        async with self.config.role(role).banned_members() as banned_list:
            for member in role.members:
                try:
                    assert (
                        ctx.guild.me.top_role > member.top_role
                        and ctx.guild.owner != member
                    )
                    if (
                        mod_cog
                        and await mod_cog.config.guild(ctx.guild).respect_hierarchy()
                    ) or not mod_cog:
                        assert (
                            ctx.author.top_role > member.top_role
                            or ctx.author == ctx.guild.owner
                        )
                    await ctx.guild.ban(member)
                except (discord.HTTPException, AssertionError):
                    failure_list.append(
                        "{0.name}#{0.discriminator} (id {0.id})".format(member)
                    )
                else:
                    banned_list.append(member.id)
        if failure_list:
            failures += "\n".join(failure_list)
            for page in pagify(failures):
                await ctx.send(page)
        else:
            await ctx.tick()

    @commands.command()
    @commands.is_owner()
    async def unbanrole(self, ctx: commands.Context, *, role: discord.Role):
        """
        Unban members who were banned via banrole and who had the specified role at ban time
        """
        failures = "I failed to unban the following users:\n"
        failure_list = []
        async with self.config.role(role).banned_members() as banned_list:
            for uid in banned_list:
                try:
                    await ctx.guild.unban(discord.Object(id=uid))
                except discord.Forbidden:
                    failure_list.append(uid)
                    banned_list.remove(uid)
                except discord.NotFound:
                    failure_list.append(uid)
                    banned_list.remove(uid)
                else:
                    banned_list.remove(uid)
        if failure_list:
            failures += "\n".join(failure_list)
            for page in pagify(failures):
                await ctx.send(page)
        await ctx.tick()

    @commands.command()
    @commands.is_owner()
    async def botip(self, ctx: commands.Context):
        """Get the bots public IP address (in DMs)"""
        async with ctx.typing():
            embed = discord.Embed(
                title=f"{self.bot.user.name}'s public IP",
                description=dict()["client"]["ip"],
            )
            try:
                await ctx.author.send(embed=embed)
                await ctx.tick()
            except discord.Forbidden:
                await ctx.send(
                    "Your DMs appear to be disabled, please enable them and try again."
                )

    @commands.command()
    @commands.is_owner()
    async def runshell(self, ctx, *, command: str):
        """Run a shell command from within your bots venv"""
        async with ctx.typing():
            command = f"{command}"
            res = await self.do_shell_command(command)
            embeds = []
            page = 1
            for p in pagify(res):
                embed = discord.Embed(title="Shell Command Results", description=box(p))
                embed.set_footer(text=f"Page {page}")
                page += 1
                embeds.append(embed)
            if len(embeds) > 1:
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                if embeds:
                    await ctx.send(embed=embeds[0])
                else:
                    await ctx.send("Command ran with no results")

    @commands.command()
    @commands.is_owner()
    async def pip(self, ctx, *, command: str):
        """Run a pip command from within your bots venv"""
        async with ctx.typing():
            command = f"pip {command}"
            res = await self.do_shell_command(command)
            embeds = []
            pages = [p for p in pagify(res)]
            for idx, p in enumerate(pages):
                embed = discord.Embed(title="Pip Command Results", description=box(p))
                embed.set_footer(text=f"Page {idx + 1}/{len(pages)}")
                embeds.append(embed)
            if len(embeds) > 1:
                await menu(ctx, embeds, DEFAULT_CONTROLS)
            else:
                if embeds:
                    await ctx.send(embed=embeds[0])
                else:
                    await ctx.send("Command ran with no results")

    @commands.command(aliases=["diskbench"])
    @commands.is_owner()
    async def diskspeed(self, ctx: commands.Context):
        """
        Get disk R/W performance for the server your bot is on

        The results of this test may vary, Python isn't fast enough for this kind of byte-by-byte writing,
        and the file buffering and similar adds too much overhead.
        Still this can give a good idea of where the bot is at I/O wise.
        """

        def diskembed(data: dict) -> discord.Embed:
            if data["write5"] != "Waiting..." and data["write5"] != "Running...":
                embed = discord.Embed(title="Disk I/O", color=discord.Color.green())
                embed.description = "Disk Speed Check COMPLETE"
            else:
                embed = discord.Embed(title="Disk I/O", color=ctx.author.color)
                embed.description = "Running Disk Speed Check"
            first = f"Write: {data['write1']}\n" f"Read:  {data['read1']}"
            embed.add_field(
                name="128 blocks of 1048576 bytes (128MB)",
                value=box(first, lang="python"),
                inline=False,
            )
            second = f"Write: {data['write2']}\n" f"Read:  {data['read2']}"
            embed.add_field(
                name="128 blocks of 2097152 bytes (256MB)",
                value=box(second, lang="python"),
                inline=False,
            )
            third = f"Write: {data['write3']}\n" f"Read:  {data['read3']}"
            embed.add_field(
                name="256 blocks of 1048576 bytes (256MB)",
                value=box(third, lang="python"),
                inline=False,
            )
            fourth = f"Write: {data['write4']}\n" f"Read:  {data['read4']}"
            embed.add_field(
                name="256 blocks of 2097152 bytes (512MB)",
                value=box(fourth, lang="python"),
                inline=False,
            )
            fifth = f"Write: {data['write5']}\n" f"Read:  {data['read5']}"
            embed.add_field(
                name="256 blocks of 4194304 bytes (1GB)",
                value=box(fifth, lang="python"),
                inline=False,
            )
            return embed

        results = {
            "write1": "Running...",
            "read1": "Running...",
            "write2": "Waiting...",
            "read2": "Waiting...",
            "write3": "Waiting...",
            "read3": "Waiting...",
            "write4": "Waiting...",
            "read4": "Waiting...",
            "write5": "Waiting...",
            "read5": "Waiting...",
        }
        msg = None
        for i in range(6):
            stage = i + 1
            em = diskembed(results)
            if not msg:
                msg = await ctx.send(embed=em)
            else:
                await msg.edit(embed=em)
            count = 128
            size = 1048576
            if stage == 2:
                count = 128
                size = 2097152
            elif stage == 3:
                count = 256
                size = 1048576
            elif stage == 4:
                count = 256
                size = 2097152
            elif stage == 6:
                count = 256
                size = 4194304
            res = await self.run_disk_speed(
                block_count=count, block_size=size, passes=3
            )
            write = f"{humanize_number(round(res['write'], 2))}MB/s"
            read = f"{humanize_number(round(res['read'], 2))}MB/s"
            results[f"write{stage}"] = write
            results[f"read{stage}"] = read
            if f"write{stage + 1}" in results:
                results[f"write{stage + 1}"] = "Running..."
                results[f"read{stage + 1}"] = "Running..."
            await asyncio.sleep(1)

    @commands.command()
    @commands.is_owner()
    async def botip(self, ctx: commands.Context):
        """Get the bots public IP address (in DMs)"""
        async with ctx.typing():
            test = speedtest.Speedtest(secure=True)
            embed = discord.Embed(
                title=f"{self.bot.user.name}'s public IP",
                description=test.results.dict()["client"]["ip"],
            )
            try:
                await ctx.author.send(embed=embed)
                await ctx.tick()
            except discord.Forbidden:
                await ctx.send(
                    "Your DMs appear to be disabled, please enable them and try again."
                )

    @commands.command(aliases=["istats"])
    async def invitestats(self, ctx, invite_link: str):
        """Returns server stats from an invite link"""
        """Keep in mind the bot has to be in the target server to be able to retrieve the information"""
        async with ctx.channel.typing():
            try:
                invite = await ctx.bot.fetch_invite(invite_link)

                # Check if the invite is partial or full
                if isinstance(invite.guild, discord.PartialInviteGuild):
                    # Extract information from PartialInviteGuild
                    guild_id = invite.guild.id
                    guild_name = invite.guild.name
                    guild_description = invite.guild.description
                    guild_features = [
                        feature.replace("_", " ").title()
                        for feature in invite.guild.features
                    ]

                    guild_icon = invite.guild.icon
                    guild_banner = invite.guild.banner
                    guild_splash = invite.guild.splash
                    guild_vanity_url = invite.guild.vanity_url
                    guild_vanity_url_code = invite.guild.vanity_url_code
                    guild_nsfw_level = invite.guild.nsfw_level
                    guild_verification_level = invite.guild.verification_level
                    guild_premium_subscription_count = (
                        invite.guild.premium_subscription_count
                    )

                    # Check if the bot is in the guild before fetching members
                    if ctx.bot.get_guild(guild_id):
                        members = await invite.guild.chunk()
                        online_members = sum(
                            member.status == discord.Status.online for member in members
                        )
                        text_channels = len(invite.guild.text_channels)
                        voice_channels = len(invite.guild.voice_channels)
                        emojis_count = len(invite.guild.emojis)
                        stickers_count = len(invite.guild.stickers)
                        roles_count = len(invite.guild.roles)
                    else:
                        # If the bot is not in the guild, set member-related information to None
                        members = None
                        online_members = text_channels = voice_channels = (
                            emojis_count
                        ) = stickers_count = roles_count = None

                elif isinstance(invite, discord.Invite):
                    # Extract information from Invite
                    guild_id = invite.guild.id
                    guild_banner = invite.guild.banner
                    guild_name = invite.guild.name
                    owner_name = getattr(invite.guild.owner, "name", "N/A")
                    created_at = invite.guild.created_at.strftime("%Y-%m-%d %H:%M:%S")
                    approximate_member_count = invite.approximate_member_count
                    approximate_presence_count = invite.approximate_presence_count
                    channel = invite.channel
                    code = invite.code
                    guild_icon = invite.guild.icon
                    expires_at = invite.expires_at
                    inviter = invite.inviter
                    max_age = invite.max_age
                    max_uses = invite.max_uses
                    revoked = invite.revoked
                    scheduled_event = invite.scheduled_event
                    scheduled_event_id = invite.scheduled_event_id
                    target_application = invite.target_application
                    target_type = invite.target_type
                    target_user = invite.target_user
                    temporary = invite.temporary
                    url = invite.url
                    uses = invite.uses

                    # Check if the bot is in the guild before fetching members
                    bot_in_guild = ctx.bot.get_guild(guild_id)
                    if bot_in_guild:
                        members = await invite.guild.chunk()
                        online_members = sum(
                            member.status == discord.Status.online for member in members
                        )
                        online = str(
                            len(
                                [
                                    m.status
                                    for m in members
                                    if str(m.status) == "online"
                                    or str(m.status) == "idle"
                                ]
                            )
                        )
                        # total_users = str(len(members))
                        text_channels = len(invite.guild.text_channels)
                        voice_channels = len(invite.guild.voice_channels)
                        emojis_count = len(invite.guild.emojis)
                        stickers_count = len(invite.guild.stickers)
                        roles_count = len(invite.guild.roles)
                    else:
                        # If the bot is not in the guild, set member-related information to None
                        members = None
                        online_members = text_channels = voice_channels = (
                            emojis_count
                        ) = stickers_count = roles_count = 0

                else:
                    raise ValueError("Invalid invite type")

                # Create an embed
                embed = Embed(title="Server Stats", color=discord.Color.dark_theme())
                embed.add_field(name="Guild ID", value=guild_id, inline=True)
                embed.add_field(name="Guild Name", value=guild_name, inline=True)

                if isinstance(invite.guild, discord.PartialInviteGuild):
                    # Add Guild Description field only if guild_description is not None
                    if guild_description is not None:
                        embed.add_field(
                            name="Guild Description",
                            value=guild_description,
                            inline=False,
                        )
                    # add attachment image

                    # Format features in pairs
                    formatted_features = [
                        f"{guild_features[i]}\n{guild_features[i + 1]}"
                        for i in range(0, len(guild_features) - 1, 2)
                    ]

                    # If there is an odd number of features, add the last one without a pair
                    if len(guild_features) % 2 != 0:
                        formatted_features.append(f"{guild_features[-1]}\nN/A")

                    embed.set_thumbnail(url=guild_icon)
                    embed.add_field(
                        name="Guild Banner",
                        value=f"[Click here]({guild_banner})",
                        inline=True,
                    )
                    # Add Guild Splash field only if guild_splash is not None
                    if guild_splash is not None:
                        embed.add_field(
                            name="Guild Splash",
                            value=f"[Click here]({guild_splash})",
                            inline=True,
                        )
                    embed.add_field(
                        name="Guild Vanity URL", value=guild_vanity_url, inline=False
                    )
                    embed.add_field(
                        name="Guild Vanity URL Code",
                        value=guild_vanity_url_code,
                        inline=True,
                    )
                    embed.add_field(
                        name="Guild NSFW Level", value=guild_nsfw_level, inline=True
                    )
                    embed.add_field(
                        name="Guild Verification Level",
                        value=guild_verification_level,
                        inline=True,
                    )
                    embed.add_field(
                        name="Guild Premium Subscription Count",
                        value=guild_premium_subscription_count,
                        inline=True,
                    )
                    # Add guild features only if there are features to display
                    if formatted_features:
                        embed.add_field(
                            name="Guild Features",
                            value="\n".join(formatted_features),
                            inline=False,
                        )

                elif isinstance(invite, discord.Invite):
                    embed.add_field(name="Owner", value=owner_name, inline=True)
                    embed.add_field(name="Created At", value=created_at, inline=True)
                    embed.add_field(
                        name="Approximate Member Count",
                        value=approximate_member_count,
                        inline=True,
                    )
                    embed.add_field(
                        name="Approximate Presence Count",
                        value=approximate_presence_count,
                        inline=True,
                    )
                    embed.set_image(url=guild_banner)
                    embed.set_thumbnail(url=guild_icon)
                    embed.add_field(name="Channel", value=channel, inline=True)
                    embed.add_field(name="Code", value=code, inline=True)

                    # Check for None values before adding fields
                    if expires_at is not None:
                        embed.add_field(
                            name="Expires At", value=expires_at, inline=True
                        )
                    if inviter is not None:
                        embed.add_field(name="Inviter", value=inviter, inline=True)
                    if max_age is not None:
                        embed.add_field(name="Max Age", value=max_age, inline=True)
                    if max_uses is not None:
                        embed.add_field(name="Max Uses", value=max_uses, inline=True)
                    if revoked is not None:
                        embed.add_field(name="Revoked", value=revoked, inline=True)
                    if scheduled_event is not None:
                        embed.add_field(
                            name="Scheduled Event", value=scheduled_event, inline=True
                        )
                    if scheduled_event_id is not None:
                        embed.add_field(
                            name="Scheduled Event ID",
                            value=scheduled_event_id,
                            inline=True,
                        )
                    if target_application is not None:
                        embed.add_field(
                            name="Target Application",
                            value=target_application,
                            inline=True,
                        )
                    # Modify the display value for Target Type
                    target_type_value = (
                        "Non-Targetted"
                        if target_type == discord.InviteTarget.unknown
                        else target_type
                    )
                    embed.add_field(
                        name="Target Type", value=target_type_value, inline=True
                    )

                    if target_user is not None:
                        embed.add_field(
                            name="Target User", value=target_user, inline=True
                        )
                    if temporary is not None:
                        embed.add_field(name="Temporary", value=temporary, inline=True)
                    if url is not None:
                        embed.add_field(name="URL", value=url, inline=True)
                    if uses is not None:
                        embed.add_field(name="Uses", value=uses, inline=True)

                # Add member-related information only if the bot is in the guild
                # Add member-related information only if the bot is in the guild
                if members is not None:
                    if online_members is not None:
                        embed.add_field(
                            name="Online Members",
                            value=f"{online}/{len(members)} online",
                            inline=True,
                        )
                    if text_channels is not None:
                        embed.add_field(
                            name="Text Channels", value=text_channels, inline=True
                        )
                    if voice_channels is not None:
                        embed.add_field(
                            name="Voice Channels", value=voice_channels, inline=True
                        )
                    if emojis_count is not None:
                        embed.add_field(
                            name="Emojis Count", value=emojis_count, inline=True
                        )
                    if stickers_count is not None:
                        embed.add_field(
                            name="Stickers Count", value=stickers_count, inline=True
                        )
                    if roles_count is not None:
                        embed.add_field(
                            name="Roles Count", value=roles_count, inline=True
                        )

                # Send the guild id
                variable = f"{guild_id}"
                await ctx.send(variable)
                # Send the embed
                await ctx.send(embed=embed)

            except discord.errors.NotFound:
                await ctx.send("Invalid invite link or the invite has expired.")
            except ValueError as e:
                await ctx.send(str(e))
            except Exception as e:
                await ctx.send(
                    f"An error occurred while processing the invitacion! {str(e)}"
                )
                await ctx.send(f"Error: {str(e)}")

    @commands.command()
    @commands.has_permissions(manage_guild=True)
    async def serverinvites(self, ctx):
        """Get a list of server invites"""
        async with ctx.typing():
            server_name = ctx.guild.name
            embed = Embed(title=f"Server Invites for {server_name}:", description="")
            embed.set_footer(text="Non used invites won't be displayed.")
            # Obtain the guild banner
            guild_banner = ctx.guild.banner

            # Check if the guild has a banner
            if guild_banner:
                embed.set_image(url=guild_banner)
            invites = await ctx.guild.invites()

            for invite in invites:
                if not invite.expires_at or invite.expires_at > discord.utils.utcnow():
                    # Check if the invite has not expired
                    if invite.uses > 0:
                        invite_url = f"https://discord.gg/{invite.code}"
                        embed.description += f"\n[Invite Code: {invite.code}]({invite_url}) - Uses: {invite.uses} - Max Uses: {invite.max_uses}"

            await ctx.send(embed=embed)
