import asyncio
import datetime
import inspect
import itertools
import logging
import os
import platform
import re
import sys
import typing as t
from asyncio import TimeoutError as AsyncTimeoutError
from contextlib import suppress as sps
from datetime import datetime, timedelta
from textwrap import shorten
from time import perf_counter
from types import SimpleNamespace
from typing import Optional, Union

import aiohttp
import cpuinfo
import discord
import distro
import psutil
import requests
import yarl
from discord import Embed, File, Member, Role, TextChannel, User
from discord.ext import tasks
from discord.ui import Button, View
from fixcogsutils.dpy_future import TimestampStyle, get_markdown_timestamp
from fixcogsutils.formatting import bool_emojify
from tabulate import tabulate
from uwuipy import uwuipy

from grief import VersionInfo, version_info
from grief.core import checks, commands
from grief.core.bot import Grief
from grief.core.commands import GuildContext
from grief.core.i18n import cog_i18n
from grief.core.utils import AsyncIter
from grief.core.utils import chat_formatting as cf
from grief.core.utils import chat_formatting as chat
from grief.core.utils.chat_formatting import (bold, box, escape, humanize_list,
                                              humanize_number,
                                              humanize_timedelta, italics,
                                              pagify, text_to_file)
from grief.core.utils.common_filters import filter_invites
from grief.core.utils.menus import DEFAULT_CONTROLS, close_menu, menu
from grief.core.utils.predicates import ReactionPredicate

from .common_variables import (CHANNEL_TYPE_EMOJIS, GUILD_FEATURES,
                               KNOWN_CHANNEL_TYPES)
from .converters import (FuzzyMember, GuildConverter, MultiGuildConverter,
                         PermissionConverter)
from .embeds import emoji_embed, spotify_embed
from .menus import (ActivityPager, AvatarPages, BaseMenu, BaseView,
                    ChannelsMenu, ChannelsPager, EmojiPager, GuildPages,
                    ListPages, PagePager, Spotify)
from .utils import _
from .views import URLView


async def wait_reply(ctx: commands.Context, timeout: int = 60):
    def check(message: discord.Message):
        return message.author == ctx.author and message.channel == ctx.channel

    try:
        reply = await ctx.bot.wait_for("message", timeout=timeout, check=check)
        res = reply.content
        try:
            await reply.delete()
        except (
            discord.Forbidden,
            discord.NotFound,
            discord.DiscordServerError,
        ):
            pass
        return res
    except asyncio.TimeoutError:
        return None


def get_attachments(message: discord.Message) -> t.List[discord.Attachment]:
    """Get all attachments from context"""
    attachments = []
    if message.attachments:
        direct_attachments = [a for a in message.attachments]
        attachments.extend(direct_attachments)
    if hasattr(message, "reference"):
        try:
            referenced_attachments = [a for a in message.reference.resolved.attachments]
            attachments.extend(referenced_attachments)
        except AttributeError:
            pass
    return attachments


class Info(commands.Cog):
    """Suite of tools to grab banners, icons, etc."""

    def __init__(self, bot: Grief):
        super().__init__()
        self.bot = bot

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

    @commands.command(aliases=["av", "pfp"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def avatar(self, ctx: commands.Context, *, member: discord.User = None):
        """Fetch someone's pfp."""
        if member == None:
            member = ctx.author
        user = await self.bot.fetch_user(member.id)
        if user.avatar == None:
            em = discord.Embed(
                color=0x313338,
                description=f"{ctx.author.mention}: **{member}** doesn't have a pfp set.",
            )
            await ctx.reply(embed=em, mention_author=False)
        else:
            avatar_url = user.avatar.url
            button1 = Button(
                emoji="<:info:1202073815140810772>", label="avatar", url=avatar_url
            )
            e = discord.Embed(color=0x313338, url=user.avatar.url)
            e.set_author(
                name=f"{member.display_name}'s avatar",
                icon_url=f"{member.avatar}",
                url=f"https://discord.com/users/{member.id}",
            )
            e.set_image(url=avatar_url)
            view = View()
            view.add_item(button1)
            await ctx.reply(embed=e, view=view, mention_author=False)

    @commands.command(aliases=["sav"])
    async def serveravatar(self, ctx: commands.Context, user: discord.Member = None):
        """Get someone's server pfp (if they have one)."""
        if user is None:
            user = ctx.author
        gld_avatar = user.guild_avatar
        if gld_avatar is None:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: **{user}** doesn't have a server avatar set.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
        else:
            gld_avatar_url = gld_avatar.url
            embed = discord.Embed(colour=0x313338)
            embed.set_author(
                name=f"{user.display_name}'s server avatar",
                icon_url=f"{user.guild_avatar}",
                url=f"https://discord.com/users/{user.id}",
            )
            embed.set_image(url=gld_avatar_url)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=["sicon", "si", "sico", "savi"])
    @commands.cooldown(
        1,
        3,
        commands.BucketType.user,
    )
    async def servericon(self, ctx):
        """Fetch the server icon."""
        if ctx.guild.icon is None:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: **{ctx.guild.name}** doesn't have a icon set.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return
        e = discord.Embed(color=0x313338)
        e.set_author(
            name=f"{ctx.guild.name}'s server icon", icon_url=f"{ctx.guild.icon.url}"
        )
        e.set_image(url=f"{ctx.guild.icon.url}")
        avatar = Button(
            emoji="<:info:1202073815140810772>",
            label="server icon",
            url=f"{ctx.guild.icon.url}",
        )
        view = View()
        view.add_item(avatar)
        await ctx.reply(embed=e, view=view, mention_author=False)

    @commands.command(aliases=["sbanner", "sb", "sbnr"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def serverbanner(self, ctx):
        """Fetch the server banner."""
        if ctx.guild.banner is None:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: **{ctx.guild.name}** doesn't have a banner set.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return
        e = discord.Embed(color=0x313338)
        e.set_author(
            name=f"**{ctx.guild.name}'s server banner**",
            icon_url=f"{ctx.guild.icon.url}",
        )
        e.set_image(url=f"{ctx.guild.banner.url}")
        button = Button(
            emoji="<:info:1202073815140810772>",
            label="server banner",
            url=f"{ctx.guild.banner.url}",
        )
        view = View()
        view.add_item(button)
        await ctx.reply(view=view, embed=e, mention_author=False)

    @commands.command(aliases=["invsplash, isplash"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def invitesplash(self, ctx: commands.Context):
        """Fetch a servers invite splash."""
        if ctx.guild.splash == None:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: **{ctx.guild.name}** doesn't have a invite splash set.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
        else:
            invsplash_url = ctx.guild.splash
            button1 = Button(
                emoji="<:info:1202073815140810772>",
                label="invite splash",
                url=ctx.guild.splash.url,
            )
            e = discord.Embed(color=0x313338)
            e.set_author(name=f"{ctx.guild.name}'s server invite splash")
            e.set_image(url=invsplash_url)
            view = View()
            view.add_item(button1)
            await ctx.reply(embed=e, view=view, mention_author=False)

    @commands.command(aliases=["bnr"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def banner(self, ctx: commands.Context, *, member: discord.User = None):
        """Fetch a users banner."""
        if member == None:
            member = ctx.author
        user = await self.bot.fetch_user(member.id)
        if user.banner == None:
            embed = discord.Embed(
                description=f"{ctx.author.mention}: **{member}** doesn't have a banner set.",
                color=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
        else:
            banner_url = user.banner.url
            button1 = Button(
                emoji="<:info:1202073815140810772>", label="banner", url=banner_url
            )
            e = discord.Embed(color=0x313338)
            e.set_image(url=banner_url)
            e.title = f"{user.display_name}'s banner"
            view = View()
            view.add_item(button1)
            await ctx.reply(embed=e, view=view, mention_author=False)

    @commands.guild_only()
    @commands.command(aliases=["mc"])
    async def membercount(self, ctx: GuildContext) -> None:
        """Get count of all members + humans and bots separately."""
        guild = ctx.guild
        member_count = 0
        human_count = 0
        bot_count = 0
        for member in guild.members:
            if member.bot:
                bot_count += 1
            else:
                human_count += 1
            member_count += 1
        if await ctx.embed_requested():
            embed = discord.Embed(
                timestamp=datetime.now(), color=await ctx.embed_color()
            )
            embed.add_field(name="Members", value=str(member_count))
            embed.add_field(name="Humans", value=str(human_count))
            embed.add_field(name="Bots", value=str(bot_count))
            await ctx.reply(embed=embed, mention_author=False)
        else:
            await ctx.send(
                f"**Members:** {member_count}\n"
                f"**Humans:** {human_count}\n"
                f"**Bots:** {bot_count}"
            )

    @commands.guild_only()
    @commands.command()
    async def devices(self, ctx, *, member: discord.Member = None):
        """Show what devices a member is using."""
        if member is None:
            member = ctx.author
        d = str(member.desktop_status)
        m = str(member.mobile_status)
        w = str(member.web_status)
        # because it isn't supported in d.py, manually override if streaming
        if any([isinstance(a, discord.Streaming) for a in member.activities]):
            d = d if d == "offline" else "streaming"
            m = m if m == "offline" else "streaming"
            w = w if w == "offline" else "streaming"
        status = {
            "online": "\U0001f7e2",
            "idle": "\U0001f7e0",
            "dnd": "\N{LARGE RED CIRCLE}",
            "offline": "\N{MEDIUM WHITE CIRCLE}",
            "streaming": "\U0001f7e3",
        }
        embed = discord.Embed(
            title=f"**{member.display_name}'s devices:**",
            description=(
                f"{status[d]} Desktop\n" f"{status[m]} Mobile\n" f"{status[w]} Web"
            ),
            color=0x313338,
        )
        if discord.version_info.major == 1:
            embed.set_thumbnail(url=member.avatar_url)
        else:
            embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await ctx.reply(embed=embed, mention_author=False)
        except discord.errors.Forbidden:
            await ctx.send(
                f"{member.display_name}'s devices:\n"
                f"{status[d]} Desktop\n"
                f"{status[m]} Mobile\n"
                f"{status[w]} Web"
            )

    @commands.guild_only()
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def bans(self, ctx):
        """Displays the server's banlist."""
        try:
            banlist = [bans async for bans in ctx.guild.bans()]
        except discord.errors.Forbidden:
            await ctx.send("I do not have the `Ban Members` permission.")
            return
        bancount = len(banlist)
        ban_list = []
        if bancount == 0:
            msg = "No users are banned from this server."
        else:
            msg = ""
            for user_obj in banlist:
                user_name = f"{user_obj.user.name}#{user_obj.user.discriminator}"
                msg += f"`{user_obj.user.id} - {user_name}`\n"

        banlist = sorted(msg)
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            embed_list = []
            for page in cf.pagify(msg, shorten_by=1400):
                embed = discord.Embed(
                    description=f"**Total bans:** {bancount}\n\n{page}",
                    colour=await ctx.embed_colour(),
                )
                embed_list.append(embed)
            await menu(ctx, embed_list, DEFAULT_CONTROLS)
        else:
            text_list = []
            for page in cf.pagify(msg, shorten_by=1400):
                text = f"**Total bans:** {bancount}\n{page}"
                text_list.append(text)
            await menu(ctx, text_list, DEFAULT_CONTROLS)

    @commands.guild_only()
    @commands.command()
    async def einfo(self, ctx, emoji: discord.Emoji):
        """Emoji information."""
        yesno = {True: "Yes", False: "No"}
        header = f"{str(emoji)}\n"
        m = (
            f"[Name]:       {emoji.name}\n"
            f"[Guild]:      {emoji.guild}\n"
            f"[URL]:        {emoji.url}\n"
            f"[Animated]:   {yesno[emoji.animated]}"
        )
        await ctx.send(header + cf.box(m, lang="ini"))

    @commands.guild_only()
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def inrole(self, ctx, *, rolename: str):
        """Check members in the role specified."""
        guild = ctx.guild
        await ctx.typing()
        if rolename.startswith("<@&"):
            role_id = int(re.search(r"<@&(.{17,19})>$", rolename)[1])
            role = discord.utils.get(ctx.guild.roles, id=role_id)
        elif len(rolename) in [17, 18, 19] and rolename.isdigit():
            role = discord.utils.get(ctx.guild.roles, id=int(rolename))
        else:
            role = discord.utils.find(
                lambda r: r.name.lower() == rolename.lower(), guild.roles
            )

        if role is None:
            roles = []
            for r in guild.roles:
                if rolename.lower() in r.name.lower():
                    roles.append(r)

            if len(roles) == 1:
                role = roles[0]
            elif len(roles) < 1:
                await ctx.send(f"No roles containing `{rolename}` were found.")
                return
            else:
                msg = (
                    f"**{len(roles)} roles found with** `{rolename}` **in the name.**\n"
                    f"Type the number of the role you wish to see.\n\n"
                )
                tbul8 = []
                for num, role in enumerate(roles):
                    tbul8.append([num + 1, role.name])
                m1 = await ctx.send(msg + tabulate(tbul8, tablefmt="plain"))

                def check(m):
                    if (m.author == ctx.author) and (m.channel == ctx.channel):
                        return True

                try:
                    response = await self.bot.wait_for(
                        "message", check=check, timeout=25
                    )
                except asyncio.TimeoutError:
                    await m1.delete()
                    return
                if not response.content.isdigit():
                    await m1.delete()
                    return
                else:
                    response = int(response.content)

                if response not in range(0, len(roles) + 1):
                    return await ctx.send("Cancelled.")
                elif response == 0:
                    return await ctx.send("Cancelled.")
                else:
                    role = roles[response - 1]

        users_in_role = "\n".join(
            sorted(m.display_name for m in guild.members if role in m.roles)
        )
        if len(users_in_role) == 0:
            if ctx.channel.permissions_for(ctx.guild.me).embed_links:
                embed = discord.Embed(
                    description=cf.bold(f"0 users found in the {role.name} role."),
                    colour=await ctx.embed_colour(),
                )
                return await ctx.reply(embed=embed, mention_author=False)
            else:
                return await ctx.send(
                    cf.bold(f"0 users found in the {role.name} role.")
                )

        embed_list = []
        role_len = len([m for m in guild.members if role in m.roles])
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            for page in cf.pagify(users_in_role, delims=["\n"], page_length=200):
                embed = discord.Embed(
                    description=cf.bold(
                        f"{role_len} users found in the {role.name} role.\n"
                    ),
                    colour=await ctx.embed_colour(),
                )
                embed.add_field(name="Users", value=page)
                embed_list.append(embed)
            final_embed_list = []
            for i, embed in enumerate(embed_list):
                embed.set_footer(text=f"Page {i + 1}/{len(embed_list)}")
                final_embed_list.append(embed)
            if len(embed_list) == 1:
                close_control = {"\N{CROSS MARK}": close_menu}
                await menu(ctx, final_embed_list, close_control)
            else:
                await menu(ctx, final_embed_list, DEFAULT_CONTROLS)
        else:
            for page in cf.pagify(users_in_role, delims=["\n"], page_length=200):
                msg = f"**{role_len} users found in the {role.name} role.**\n"
                msg += page
                embed_list.append(msg)
            if len(embed_list) == 1:
                close_control = {"\N{CROSS MARK}": close_menu}
                await menu(ctx, embed_list, close_control)
            else:
                await menu(ctx, embed_list, DEFAULT_CONTROLS)

    @commands.guild_only()
    @commands.command()
    async def joined(self, ctx, user: discord.Member = None):
        """Show when a user joined the guild."""
        if not user:
            user = ctx.author
        if user.joined_at:
            user_joined = user.joined_at.strftime("%d %b %Y %H:%M")
            since_joined = (ctx.message.created_at - user.joined_at).days
            joined_on = f"{user_joined} ({since_joined} days ago)"
        else:
            joined_on = "a mysterious date that not even Discord knows."

        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            embed = discord.Embed(
                description=f"{user.mention} joined this guild on {joined_on}.",
                color=0x313338,
            )
            await ctx.send(embed=embed, mention_author=False)

    @commands.guild_only()
    @commands.command()
    async def perms(self, ctx, user: discord.Member = None):
        """Fetch a specific user's permissions."""
        if user is None:
            user = ctx.author

        perms = iter(ctx.channel.permissions_for(user))
        perms_we_have = ""
        perms_we_dont = ""
        for x in sorted(perms):
            if "True" in str(x):
                perms_we_have += "+ {0}\n".format(str(x).split("'")[1])
            else:
                perms_we_dont += "- {0}\n".format(str(x).split("'")[1])
        await ctx.send(cf.box(f"{perms_we_have}{perms_we_dont}", lang="diff"))

    @commands.guild_only()
    @commands.command(aliases=["listroles", "rolelist"])
    @commands.has_permissions(manage_roles=True)
    async def roles(self, ctx):
        """Displays the server's roles."""
        form = "`{rpos:0{zpadding}}` - `{rid}` - `{rcolor}` - {rment} "
        max_zpadding = max([len(str(r.position)) for r in ctx.guild.roles])
        rolelist = [
            form.format(
                rpos=r.position,
                zpadding=max_zpadding,
                rid=r.id,
                rment=r.mention,
                rcolor=r.color,
            )
            for r in ctx.guild.roles
        ]
        rolelist = sorted(rolelist, reverse=True)
        rolelist = "\n".join(rolelist)
        embed_list = []
        if ctx.channel.permissions_for(ctx.guild.me).embed_links:
            for page in cf.pagify(rolelist, shorten_by=1400):
                embed = discord.Embed(
                    description=f"**Total roles:** {len(ctx.guild.roles)}\n\n{page}",
                    colour=0x313338,
                )
                embed_list.append(embed)
        else:
            for page in cf.pagify(rolelist, shorten_by=1400):
                msg = f"**Total roles:** {len(ctx.guild.roles)}\n{page}"
                embed_list.append(msg)

        await menu(ctx, embed_list, DEFAULT_CONTROLS)

    @commands.is_owner()
    @commands.command(hidden=True)
    async def sharedservers(self, ctx, user: discord.Member = None):
        """Shows shared server info. Defaults to author."""
        if not user:
            user = ctx.author

        mutual_guilds = user.mutual_guilds
        data = f"[Guilds]:     {len(mutual_guilds)} shared\n"
        shared_servers = sorted(
            [g.name for g in mutual_guilds], key=lambda v: (v.upper(), v[0].islower())
        )
        data += f"[In Guilds]:  {cf.humanize_list(shared_servers, style='unit')}"

        for page in cf.pagify(data, ["\n"], page_length=1800):
            await ctx.send(cf.box(data, lang="ini"))

    @commands.command()
    @commands.has_permissions(read_message_history=True)
    async def firstmessage(
        self,
        ctx: commands.Context,
        channel: Optional[
            discord.TextChannel
            | discord.Thread
            | discord.DMChannel
            | discord.GroupChannel
            | discord.User
            | discord.Member
        ] = commands.CurrentChannel,
    ):
        """
        Provide a link to the first message in current or provided channel.
        """
        try:
            messages = [
                message async for message in channel.history(limit=1, oldest_first=True)
            ]

            chan = (
                f"<@{channel.id}>"
                if isinstance(
                    channel, discord.DMChannel | discord.User | discord.Member
                )
                else f"<#{channel.id}>"
            )

            embed: discord.Embed = discord.Embed(
                color=0x313338,
                timestamp=messages[0].created_at,
                description=f"[First message in]({messages[0].jump_url}) {chan}",
            )
            embed.set_author(
                name=messages[0].author.display_name,
                icon_url=(
                    messages[0].author.avatar.url
                    if messages[0].author.avatar
                    else messages[0].author.display_avatar.url
                ),
            )

        except (discord.Forbidden, discord.HTTPException, IndexError, AttributeError):
            return await ctx.maybe_send_embed(
                "Unable to read message history for that channel."
            )

        view = URLView(label="Jump to message", jump_url=messages[0].jump_url)

        await ctx.reply(embed=embed, view=view, mention_author=False)

    @staticmethod
    def count_months(days):
        lens = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        cy = itertools.cycle(lens)
        months = 0
        m_temp = 0
        mo_len = next(cy)
        for i in range(1, days + 1):
            m_temp += 1
            if m_temp == mo_len:
                months += 1
                m_temp = 0
                mo_len = next(cy)
                if mo_len == 28 and months >= 48:
                    mo_len += 1

        weeks, days = divmod(m_temp, 7)
        return months, weeks, days

    def category_format(self, cat_chan_tuple: tuple):
        cat = cat_chan_tuple[0]
        chs = cat_chan_tuple[1]

        chfs = self.channels_format(chs)
        if chfs != []:
            ch_forms = ["\t" + f for f in chfs]
            return "\n".join([f"{cat.name} :: {cat.id}"] + ch_forms)
        else:
            return "\n".join([f"{cat.name} :: {cat.id}"] + ["\tNo Channels"])

    @staticmethod
    def channels_format(channels: list):
        if channels == []:
            return []

        channel_form = "{name} :: {ctype} :: {cid}"

        def type_name(channel):
            return channel.__class__.__name__[:-7]

        name_justify = max([len(c.name[:24]) for c in channels])
        type_justify = max([len(type_name(c)) for c in channels])

        return [
            channel_form.format(
                name=c.name[:24].ljust(name_justify),
                ctype=type_name(c).ljust(type_justify),
                cid=c.id,
            )
            for c in channels
        ]

    def _dynamic_time(self, time):
        try:
            date_join = datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f%z")
        except ValueError:
            time = f"{str(time)}.0"
            date_join = datetime.strptime(str(time), "%Y-%m-%d %H:%M:%S.%f%z")
        date_now = discord.utils.utcnow()
        since_join = date_now - date_join

        mins, secs = divmod(int(since_join.total_seconds()), 60)
        hrs, mins = divmod(mins, 60)
        days, hrs = divmod(hrs, 24)
        mths, wks, days = self.count_months(days)
        yrs, mths = divmod(mths, 12)

        m = f"{yrs}y {mths}mth {wks}w {days}d {hrs}h {mins}m {secs}s"
        m2 = [x for x in m.split() if x[0] != "0"]
        s = " ".join(m2[:2])
        if s:
            return f"{s} ago"
        else:
            return ""

    @staticmethod
    def fetch_joined_at(user, guild):
        return user.joined_at

    async def message_from_message_link(self, ctx: commands.Context, message_link: str):
        bad_link_msg = (
            "That doesn't look like a message link, I can't reach that message, "
        )
        bad_link_msg += "or you didn't attach a sticker to the command message."
        no_guild_msg = "You aren't in that guild."
        no_channel_msg = "You can't view that channel."
        no_message_msg = "That message wasn't found."
        no_sticker_msg = "There are no stickers attached to that message."

        if not "discord.com/channels/" in message_link:
            return bad_link_msg
        ids = message_link.split("/")
        if len(ids) != 7:
            return bad_link_msg

        guild = self.bot.get_guild(int(ids[4]))
        if not guild:
            return bad_link_msg

        channel = guild.get_channel_or_thread(int(ids[5]))
        if not channel:
            channel = self.bot.get_channel(int(ids[5]))
        if not channel:
            return bad_link_msg

        if ctx.author not in guild.members:
            return no_guild_msg
        if not channel.permissions_for(ctx.author).read_messages:
            return no_channel_msg

        try:
            message = await channel.fetch_message(int(ids[6]))
        except discord.errors.NotFound:
            return no_message_msg

        if not message.stickers:
            return no_sticker_msg

        return message

    @staticmethod
    def role_from_string(guild, rolename, roles=None):
        if roles is None:
            roles = guild.roles
        if rolename.startswith("<@&"):
            role_id = int(re.search(r"<@&(.{17,19})>$", rolename)[1])
            role = guild.get_role(role_id)
        else:
            role = discord.utils.find(
                lambda r: r.name.lower() == str(rolename).lower(), roles
            )
        return role

    def sort_channels(self, channels):
        temp = {}

        channels = sorted(channels, key=lambda c: c.position)

        for c in channels[:]:
            if isinstance(c, discord.CategoryChannel):
                channels.pop(channels.index(c))
                temp[c] = list()

        for c in channels[:]:
            if c.category:
                channels.pop(channels.index(c))
                temp[c.category].append(c)

        category_channels = sorted(
            [
                (cat, sorted(chans, key=lambda c: c.position))
                for cat, chans in temp.items()
            ],
            key=lambda t: t[0].position,
        )
        return channels, category_channels

    @commands.command(aliases=["activity"])
    @commands.guild_only()
    async def status(self, ctx, *, member: discord.Member = None):
        """List user's activities"""
        if member is None:
            member = ctx.message.author
        if not (activities := member.activities):
            await ctx.send(chat.info(_("Right now this user is doing nothing")))
            return
        await BaseMenu(ActivityPager(activities)).start(ctx)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def invites(
        self, ctx: commands.Context, *, server: commands.GuildConverter = None
    ):
        """Get invites from server by id"""
        if server is None or not await self.bot.is_owner(ctx.author):
            server = ctx.guild
        if not server.me.guild_permissions.manage_guild:
            await ctx.send(
                _(
                    'I need permission "Manage Server" to access list of invites on server'
                )
            )
            return
        invites = await server.invites()
        if invites:
            inviteslist = "\n".join(f"{x} ({x.channel.name})" for x in invites)
            await BaseMenu(PagePager(list(chat.pagify(inviteslist)))).start(ctx)
        else:
            await ctx.send(_("There is no invites for this server"))

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    async def channels(self, ctx, *, server: commands.GuildConverter = None):
        """Get all channels on server"""
        # TODO: Use dpy menus for that
        if server is None or not await self.bot.is_owner(ctx.author):
            server = ctx.guild
        channels = {
            channel_type: ChannelsPager(getattr(server, type_data[0]))
            for channel_type, type_data in KNOWN_CHANNEL_TYPES.items()
        }
        await ChannelsMenu(channels, "category", len(server.channels)).start(ctx)

    @commands.command()
    @commands.guild_only()
    async def roleinfo(self, ctx, *, role: discord.Role):
        """Get info about role"""
        em = discord.Embed(
            title=chat.escape(role.name, formatting=True),
            color=0x313338,
        )
        em.add_field(name=_("ID"), value=role.id)
        em.add_field(
            name=_("Permissions"),
            value="[{0}](https://permissions.grief.cloud/?v={0})".format(
                role.permissions.value
            ),
        )
        em.add_field(
            name=_("Exists since"),
            value=get_markdown_timestamp(role.created_at, TimestampStyle.datetime_long),
        )
        em.add_field(name=_("Color"), value=role.colour)
        em.add_field(name=_("Members"), value=str(len(role.members)))
        em.add_field(name=_("Position"), value=role.position)
        em.add_field(name=_("Managed"), value=bool_emojify(role.managed))
        em.add_field(
            name=_("Managed by bot"), value=bool_emojify(role.is_bot_managed())
        )
        em.add_field(
            name=_("Managed by boosts"),
            value=bool_emojify(role.is_premium_subscriber()),
        )
        em.add_field(
            name=_("Managed by integration"), value=bool_emojify(role.is_integration())
        )
        em.add_field(name=_("Hoist"), value=bool_emojify(role.hoist))
        em.add_field(name=_("Mentionable"), value=bool_emojify(role.mentionable))
        em.add_field(name=_("Mention"), value=role.mention + "\n`" + role.mention + "`")
        em.set_thumbnail(
            url=f"https://xenforo.com/community/rgba.php?r={role.colour.r}&g={role.color.g}&b={role.color.b}&a=255"
        )
        await ctx.reply(embed=em, mention_author=False)

    @commands.command(aliases=["cperms"])
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def chanperms(
        self,
        ctx,
        member: Optional[discord.Member],
        *,
        channel: Union[
            discord.TextChannel,
            discord.VoiceChannel,
            discord.StageChannel,
            discord.CategoryChannel,
        ] = None,
    ):
        """Check user's permission for current or provided channel"""
        if not member:
            member = ctx.author
        if not channel:
            channel = ctx.channel
        perms = channel.permissions_for(member)
        await ctx.send(
            "{}\n{}".format(
                chat.inline(str(perms.value)),
                chat.box(
                    (
                        chat.format_perms_list(perms)
                        if perms.value
                        else _("No permissions")
                    ),
                    lang="py",
                ),
            )
        )

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def serverinfo(self, ctx, details: bool = True):
        """
        Show server information.

        `details`: Shows more information when set to `True`.
        Default to False.
        """
        guild = ctx.guild
        created_at = _("Created on {date_and_time}. That's {relative_time}.").format(
            date_and_time=discord.utils.format_dt(guild.created_at),
            relative_time=discord.utils.format_dt(guild.created_at, "R"),
        )
        online = humanize_number(
            len([m.status for m in guild.members if m.status != discord.Status.offline])
        )
        total_users = guild.member_count and humanize_number(guild.member_count)
        text_channels = humanize_number(len(guild.text_channels))
        voice_channels = humanize_number(len(guild.voice_channels))
        stage_channels = humanize_number(len(guild.stage_channels))
        if not details:
            data = discord.Embed(description=created_at, colour=0x313338())
            data.add_field(
                name=_("Users online"),
                value=f"{online}/{total_users}" if total_users else _("Not available"),
            )
            data.add_field(name=_("Text Channels"), value=text_channels)
            data.add_field(name=_("Voice Channels"), value=voice_channels)
            data.add_field(name=_("Roles"), value=humanize_number(len(guild.roles)))
            data.add_field(name=_("Owner"), value=str(guild.owner))
            data.set_footer(
                text=_("Server ID: ")
                + str(guild.id)
                + _("  •  Use {command} for more info on the server.").format(
                    command=f"{ctx.clean_prefix}serverinfo 1"
                )
            )
            if guild.icon:
                data.set_author(name=guild.name, url=guild.icon)
                data.set_thumbnail(url=guild.icon)
            else:
                data.set_author(name=guild.name)
        else:

            def _size(num: int):
                for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                    if abs(num) < 1024.0:
                        return "{0:.1f}{1}".format(num, unit)
                    num /= 1024.0
                return "{0:.1f}{1}".format(num, "YB")

            def _bitsize(num: int):
                for unit in ["B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"]:
                    if abs(num) < 1000.0:
                        return "{0:.1f}{1}".format(num, unit)
                    num /= 1000.0
                return "{0:.1f}{1}".format(num, "YB")

            shard_info = (
                _("\nShard ID: **{shard_id}/{shard_count}**").format(
                    shard_id=humanize_number(guild.shard_id + 1),
                    shard_count=humanize_number(ctx.bot.shard_count),
                )
                if ctx.bot.shard_count > 1
                else ""
            )
            # Logic from: https://github.com/TrustyJAID/Trusty-cogs/blob/master/serverstats/serverstats.py#L159
            online_stats = {
                _("Humans: "): lambda x: not x.bot,
                _(" • Bots: "): lambda x: x.bot,
                "\N{LARGE GREEN CIRCLE}": lambda x: x.status is discord.Status.online,
                "\N{LARGE ORANGE CIRCLE}": lambda x: x.status is discord.Status.idle,
                "\N{LARGE RED CIRCLE}": lambda x: x.status
                is discord.Status.do_not_disturb,
                "\N{MEDIUM WHITE CIRCLE}\N{VARIATION SELECTOR-16}": lambda x: (
                    x.status is discord.Status.offline
                ),
                "\N{LARGE PURPLE CIRCLE}": lambda x: any(
                    a.type is discord.ActivityType.streaming for a in x.activities
                ),
                "\N{MOBILE PHONE}": lambda x: x.is_on_mobile(),
            }
            member_msg = _("Users online: **{online}/{total_users}**\n").format(
                online=online, total_users=total_users
            )
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

            verif = {
                "none": _("0 - None"),
                "low": _("1 - Low"),
                "medium": _("2 - Medium"),
                "high": _("3 - High"),
                "highest": _("4 - Highest"),
            }

            joined_on = _(
                "{bot_name} joined this server on {bot_join}. That's over {since_join} days ago."
            ).format(
                bot_name=ctx.bot.user.name,
                bot_join=guild.me.joined_at.strftime("%d %b %Y %H:%M:%S"),
                since_join=humanize_number(
                    (ctx.message.created_at - guild.me.joined_at).days
                ),
            )

            data = discord.Embed(
                description=(f"{guild.description}\n\n" if guild.description else "")
                + created_at,
                colour=0x313338,
            )
            data.set_author(
                name=guild.name,
                icon_url=(
                    "https://cdn.discordapp.com/emojis/457879292152381443.png"
                    if "VERIFIED" in guild.features
                    else (
                        "https://cdn.discordapp.com/emojis/508929941610430464.png"
                        if "PARTNERED" in guild.features
                        else None
                    )
                ),
            )
            if guild.icon:
                data.set_thumbnail(url=guild.icon)
            data.add_field(name=_("Members:"), value=member_msg)
            data.add_field(
                name=_("Channels:"),
                value=_(
                    "\N{SPEECH BALLOON} Text: {text}\n"
                    "\N{SPEAKER WITH THREE SOUND WAVES} Voice: {voice}\n"
                    "\N{STUDIO MICROPHONE} Stage: {stage}"
                ).format(
                    text=bold(text_channels),
                    voice=bold(voice_channels),
                    stage=bold(stage_channels),
                ),
            )
            data.add_field(
                name=_("Utility:"),
                value=_(
                    "Owner: {owner}\nVerif. level: {verif}\nServer ID: {id}{shard_info}"
                ).format(
                    owner=bold(str(guild.owner)),
                    verif=bold(verif[str(guild.verification_level)]),
                    id=bold(str(guild.id)),
                    shard_info=shard_info,
                ),
                inline=False,
            )
            data.add_field(
                name=_("Misc:"),
                value=_(
                    "AFK channel: {afk_chan}\nAFK timeout: {afk_timeout}\nCustom emojis: {emoji_count}\nRoles: {role_count}"
                ).format(
                    afk_chan=(
                        bold(str(guild.afk_channel))
                        if guild.afk_channel
                        else bold(_("Not set"))
                    ),
                    afk_timeout=bold(humanize_timedelta(seconds=guild.afk_timeout)),
                    emoji_count=bold(humanize_number(len(guild.emojis))),
                    role_count=bold(humanize_number(len(guild.roles))),
                ),
                inline=False,
            )

            excluded_features = {
                # available to everyone since forum channels private beta
                "THREE_DAY_THREAD_ARCHIVE",
                "SEVEN_DAY_THREAD_ARCHIVE",
                # rolled out to everyone already
                "NEW_THREAD_PERMISSIONS",
                "TEXT_IN_VOICE_ENABLED",
                "THREADS_ENABLED",
                # available to everyone sometime after forum channel release
                "PRIVATE_THREADS",
            }
            custom_feature_names = {
                "VANITY_URL": "Vanity URL",
                "VIP_REGIONS": "VIP regions",
            }
            features = sorted(guild.features)
            if "COMMUNITY" in features:
                features.remove("NEWS")
            feature_names = [
                custom_feature_names.get(
                    feature, " ".join(feature.split("_")).capitalize()
                )
                for feature in features
                if feature not in excluded_features
            ]
            if guild.features:
                data.add_field(
                    name=_("Server features:"),
                    value="\n".join(
                        f"\N{WHITE HEAVY CHECK MARK} {feature}"
                        for feature in feature_names
                    ),
                )

            if guild.premium_tier != 0:
                nitro_boost = _(
                    "Tier {boostlevel} with {nitroboosters} boosts\n"
                    "File size limit: {filelimit}\n"
                    "Emoji limit: {emojis_limit}\n"
                    "VCs max bitrate: {bitrate}"
                ).format(
                    boostlevel=bold(str(guild.premium_tier)),
                    nitroboosters=bold(
                        humanize_number(guild.premium_subscription_count)
                    ),
                    filelimit=bold(_size(guild.filesize_limit)),
                    emojis_limit=bold(str(guild.emoji_limit)),
                    bitrate=bold(_bitsize(guild.bitrate_limit)),
                )
                data.add_field(name=_("Nitro Boost:"), value=nitro_boost)
            if guild.banner:
                data.set_image(url=guild.banner)
            data.set_footer(text=joined_on)

        await ctx.reply(embed=data, mention_author=False)

    @commands.command()
    async def botstats(self, ctx: commands.Context) -> None:
        """Display stats about the bot"""
        async with ctx.typing():
            servers = humanize_number(len(ctx.bot.guilds))
            members = humanize_number(len(self.bot.users))
            passed = f"<t:{int(ctx.me.created_at.timestamp())}:R>"
            since = f"<t:{int(ctx.me.created_at.timestamp())}:D>"
            msg = _(
                "{bot} is on {servers} servers serving {members} members.\n"
                "{bot} was created on **{since}**.\n"
                "That's over **{passed}**."
            ).format(
                bot=ctx.me.mention,
                servers=servers,
                members=members,
                since=since,
                passed=passed,
            )
            em = discord.Embed(
                description=msg, colour=0x313338, timestamp=ctx.message.created_at
            )
            if ctx.guild:
                em.set_author(
                    name=f"{ctx.me} {f'~ {ctx.me.nick}' if ctx.me.nick else ''}",
                    icon_url=ctx.me.avatar.url,
                )
            else:
                em.set_author(
                    name=f"{ctx.me}",
                    icon_url=ctx.me.avatar.url,
                )
            em.set_thumbnail(url=ctx.me.avatar.url)
        if ctx.channel.permissions_for(ctx.me).embed_links:
            await ctx.reply(embed=em, mention_author=False)
        else:
            await ctx.send(msg)

    @commands.command()
    @commands.guild_only()
    async def guildemojis(
        self,
        ctx: commands.Context,
        id_emojis: Optional[bool] = False,
        *,
        guild: GuildConverter = None,
    ) -> None:
        """
        Display all server emojis in a menu that can be scrolled through

        `id_emojis` return the id of emojis. Default to False, set True
         if you want to see emojis ID's.
        `guild_name` can be either the server ID or partial name
        """
        if not guild:
            guild = ctx.guild
        msg = ""
        embed = discord.Embed(timestamp=ctx.message.created_at)
        embed.set_author(name=guild.name, icon_url=guild.icon.url)
        regular = []
        for emoji in guild.emojis:
            if id_emojis:
                regular.append(
                    (
                        f"{emoji} = `:{emoji.name}:` "
                        f"`<{'a' if emoji.animated else ''}:{emoji.name}:{emoji.id}>`\n"
                    )
                )
            else:
                regular.append(f"{emoji} = `:{emoji.name}:`\n")
        if regular != "":
            embed.description = regular
        x = [regular[i : i + 10] for i in range(0, len(regular), 10)]
        emoji_embeds = []
        count = 1
        for page in x:
            em = discord.Embed(timestamp=ctx.message.created_at)
            em.set_author(name=guild.name + _(" Emojis"), icon_url=guild.icon.url)
            regular = []
            msg = ""
            for emoji in page:
                msg += emoji
            em.description = msg
            em.set_footer(text="Page {} of {}".format(count, len(x)))
            count += 1
            emoji_embeds.append(em)
        if len(emoji_embeds) == 0:
            await ctx.send(
                _("There are no emojis on {guild}.").format(guild=guild.name)
            )
        else:
            await BaseView(
                source=ListPages(pages=emoji_embeds),
                cog=self,
            ).start(ctx=ctx)

    @commands.hybrid_command()
    async def whois(self, ctx: commands.Context, *, user_id: discord.User) -> None:
        """
        Display servers a user shares with the bot

        `member` can be a user ID or mention
        """
        async with ctx.typing():
            if isinstance(user_id, int):
                try:
                    member = await self.bot.fetch_user(user_id)
                except AttributeError:
                    member = await self.bot.get_user_info(user_id)
                except discord.errors.NotFound:
                    await ctx.send(
                        str(user_id) + _(" doesn't seem to be a discord user.")
                    )
                    return
            else:
                member = user_id

            if await self.bot.is_owner(ctx.author):
                guild_list = []
                async for guild in AsyncIter(self.bot.guilds, steps=100):
                    if m := guild.get_member(member.id):
                        guild_list.append(m)
            else:
                guild_list = []
                async for guild in AsyncIter(self.bot.guilds, steps=100):
                    if not guild.get_member(ctx.author.id):
                        continue
                    if m := guild.get_member(member.id):
                        guild_list.append(m)
            embed_list = []
            robot = "\N{ROBOT FACE}" if member.bot else ""
            if guild_list != []:
                url = "https://discord.com/channels/{guild_id}"
                msg = f"**{member}** ({member.id}) {robot}" + _("is on:\n\n")
                embed_msg = ""
                for m in guild_list:
                    # m = guild.get_member(member.id)
                    guild_join = ""
                    guild_url = url.format(guild_id=m.guild.id)
                    if m.joined_at:
                        ts = int(m.joined_at.timestamp())
                        guild_join = f"Joined the server <t:{ts}:R>"
                    is_owner = ""
                    nick = ""
                    if m.id == m.guild.owner_id:
                        is_owner = "\N{CROWN}"
                    if m.nick:
                        nick = f"`{m.nick}` in"
                    msg += f"{is_owner}{nick} __[{m.guild.name}]({guild_url})__ {guild_join}\n\n"
                    embed_msg += f"{is_owner}{nick} __[{m.guild.name}]({guild_url})__ {guild_join}\n\n"
                if ctx.channel.permissions_for(ctx.me).embed_links:
                    for em in pagify(embed_msg, ["\n"], page_length=1024):
                        embed = discord.Embed()
                        since_created = f"<t:{int(member.created_at.timestamp())}:R>"
                        user_created = f"<t:{int(member.created_at.timestamp())}:D>"
                        public_flags = ""
                        if version_info >= VersionInfo.from_str("3.4.0"):
                            public_flags = "\n".join(
                                bold(i.replace("_", " ").title())
                                for i, v in member.public_flags
                                if v
                            )
                        created_on = _(
                            "Joined Discord on {user_created}\n"
                            "({since_created})\n"
                            "{public_flags}"
                        ).format(
                            user_created=user_created,
                            since_created=since_created,
                            public_flags=public_flags,
                        )
                        embed.description = created_on
                        embed.set_thumbnail(url=member.display_avatar)
                        embed.colour = 0x313338
                        embed.set_author(
                            name=f"{member} ({member.id}) {robot}",
                            icon_url=member.display_avatar,
                        )
                        embed.add_field(name=_("Shared Servers"), value=em)
                        embed_list.append(embed)
                else:
                    for page in pagify(msg, ["\n"]):
                        embed_list.append(page)
            else:
                if ctx.channel.permissions_for(ctx.me).embed_links:
                    embed = discord.Embed()
                    since_created = f"<t:{int(member.created_at.timestamp())}:R>"
                    user_created = f"<t:{int(member.created_at.timestamp())}:D>"
                    public_flags = ""
                    if version_info >= VersionInfo.from_str("3.4.0"):
                        public_flags = "\n".join(
                            bold(i.replace("_", " ").title())
                            for i, v in member.public_flags
                            if v
                        )
                    created_on = _(
                        "Joined Discord on {user_created}\n"
                        "({since_created})\n"
                        "{public_flags}"
                    ).format(
                        user_created=user_created,
                        since_created=since_created,
                        public_flags=public_flags,
                    )
                    embed.description = created_on
                    embed.set_thumbnail(url=member.display_avatar)
                    embed.colour = discord.Colour.dark_theme()
                    embed.set_author(
                        name=f"{member} ({member.id}) {robot}",
                        icon_url=member.display_avatar,
                    )
                    embed_list.append(embed)
                else:
                    msg = f"**{member}** ({member.id}) " + _(
                        "is not in any shared servers!"
                    )
                    embed_list.append(msg)
            await BaseView(
                source=ListPages(pages=embed_list),
                cog=self,
            ).start(ctx=ctx)

    @commands.command(name="inviteinfo", aliases=["ii"])
    async def inviteinfo(self, ctx, code: str):
        """Fetch information on a server from its invite/vanity code."""
        if "/" in code:
            code = code.split("/", -1)[-1].replace(" ", "")

        try:
            invite = await ctx.bot.fetch_invite(code)
        except discord.NotFound:
            return await ctx.send(
                embed=discord.Embed(
                    description="That was an invalid invite.", color=0x313338
                )
            )
        members_total = f"{invite.approximate_member_count:,}"
        members_online_total = f"{invite.approximate_presence_count:,}"
        embed = discord.Embed(title=f"Invite Info: {invite.guild}")
        owner_string = (
            f"**Owner:** {guild.owner}\n**Owner ID:** {guild.owner_id}\n"
            if (guild := self.bot.get_guild(invite.guild.id))
            else ""
        )
        ratio_string = (
            round(
                invite.approximate_presence_count / invite.approximate_member_count, 2
            )
            * 100
        )
        embed.description = f"**ID:** `{invite.guild.id}`\n**Created:** <t:{str(invite.guild.created_at.timestamp()).split('.')[0]}> (<t:{str(invite.guild.created_at.timestamp()).split('.')[0]}:R>)\n{owner_string}**Members:** {members_total}\n**Members Online:** {members_online_total}\n**Online Percent:** {ratio_string}\n**Verification Level:** {str(invite.guild.verification_level).title()}\n\n**Channel Name:** {invite.channel} (`{invite.channel.type}`)\n**Channel ID:** `{invite.channel.id}`\n**Invite Created:**<t:{str(invite.channel.created_at.timestamp()).split('.')[0]}> (<t:{str(invite.channel.created_at.timestamp()).split('.')[0]}:R>)\n"
        urls = ""

        if invite.guild.icon:
            icon_url = yarl.URL(str(invite.guild.icon.url))
            if "a_" in icon_url.path:
                icon_url = str(icon_url).replace("webp", "gif")
            urls += f"[**icon**]({icon_url}), "
            embed.set_thumbnail(url=icon_url)
        if invite.guild.banner:
            banner_url = yarl.URL(str(invite.guild.banner.url))
            if "a_" in banner_url.path:
                banner_url = str(banner_url).replace("webp", "gif")
            urls += f"[**banner**]({banner_url}), "
            lookup = str(invite.guild.banner.url)
            if lookup:
                embed.color = 0x313338
            embed.set_image(url=str(banner_url))

        if invite.guild.splash:
            urls += f"[**splash**]({invite.guild.splash.url}), "
        if len(urls) > 0:
            embed.add_field(name="**assets**", value=urls[:-2], inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command()
    @commands.guild_only()
    async def oldestchannels(self, ctx, amount: int = 10):
        """See which channel is the oldest"""
        async with ctx.typing():
            channels = [
                c
                for c in ctx.guild.channels
                if not isinstance(c, discord.CategoryChannel)
            ]
            c_sort = sorted(channels, key=lambda x: x.created_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {c.mention} "
                    f"created <t:{int(c.created_at.timestamp())}:f> (<t:{int(c.created_at.timestamp())}:R>)"
                    for i, c in enumerate(c_sort[:amount])
                ]
            )
            for p in pagify(txt, page_length=4000):
                em = discord.Embed(description=p, color=ctx.author.color)
                await ctx.reply(embed=em, mention_author=False)

    @commands.command(aliases=["oldestusers"])
    @commands.guild_only()
    async def oldestmembers(
        self,
        ctx,
        amount: t.Optional[int] = 10,
        include_bots: t.Optional[bool] = False,
    ):
        """
        See which users have been in the server the longest

        **Arguments**
        `amount:` how many members to display
        `include_bots:` (True/False) whether to include bots
        """
        async with ctx.typing():
            if include_bots:
                members = [m for m in ctx.guild.members]
            else:
                members = [m for m in ctx.guild.members if not m.bot]
            m_sort = sorted(members, key=lambda x: x.joined_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {m} "
                    f"joined <t:{int(m.joined_at.timestamp())}:f> (<t:{int(m.joined_at.timestamp())}:R>)"
                    for i, m in enumerate(m_sort[:amount])
                ]
            )
            for p in pagify(txt, page_length=4000):
                em = discord.Embed(description=p, color=ctx.author.color)
                await ctx.reply(embed=em, mention_author=False)

    @commands.command()
    @commands.guild_only()
    async def oldestaccounts(
        self,
        ctx,
        amount: t.Optional[int] = 10,
        include_bots: t.Optional[bool] = False,
    ):
        """
        See which users have the oldest Discord accounts

        **Arguments**
        `amount:` how many members to display
        `include_bots:` (True/False) whether to include bots
        """
        async with ctx.typing():
            if include_bots:
                members = [m for m in ctx.guild.members]
            else:
                members = [m for m in ctx.guild.members if not m.bot]
            m_sort = sorted(members, key=lambda x: x.created_at)
            txt = "\n".join(
                [
                    f"{i + 1}. {m} "
                    f"created <t:{int(m.created_at.timestamp())}:f> (<t:{int(m.created_at.timestamp())}:R>)"
                    for i, m in enumerate(m_sort[:amount])
                ]
            )
            for p in pagify(txt, page_length=4000):
                em = discord.Embed(description=p, color=ctx.author.color)
                await ctx.reply(embed=em, mention_author=False)

    @commands.command(aliases=["sp"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def spotify(self, ctx, user: discord.Member = None):
        "Sends what you or another user is listening to on Spotify."
        try:
            if user == None:
                user = ctx.author
                pass
            if user.activities:
                for activity in user.activities:
                    if str(activity).lower() == "spotify":
                        embed = discord.Embed(color=0x2B2D31)
                        embed.add_field(
                            name="**Song**",
                            value=f"**[{activity.title}](https://open.spotify.com/track/{activity.track_id})**",
                            inline=True,
                        )
                        embed.add_field(
                            name="**Artist**",
                            value=f"**[{activity.artist}](https://open.spotify.com/track/{activity.track_id})**",
                            inline=True,
                        )
                        embed.set_thumbnail(url=activity.album_cover_url)
                        embed.set_author(
                            name=ctx.message.author.name,
                            icon_url=ctx.message.author.avatar,
                        )
                        embed.set_footer(
                            text=f"Album: {activity.album}",
                            icon_url=activity.album_cover_url,
                        )
                        button1 = discord.ui.Button(
                            emoji="<:Spotifywhite:1208018664868286525>",
                            label="Listen on Spotify",
                            style=discord.ButtonStyle.url,
                            url=f"https://open.spotify.com/track/{activity.track_id}",
                        )
                        view = discord.ui.View()
                        view.add_item(button1)
                        await ctx.reply(embed=embed, view=view, mention_author=False)
                        return
            embed = discord.Embed(
                description=f"{ctx.message.author.mention}: **{user}** is not listening to Spotify",
                colour=0x313338,
            )
            await ctx.reply(embed=embed, mention_author=False)
            return
        except Exception as e:
            print(e)

    @commands.command(aliases=["bi"])
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def botinfo(self, ctx):
        "View information about Grief."
        td = datetime.utcnow() - datetime.fromtimestamp(psutil.boot_time())
        sys_uptime = humanize_timedelta(timedelta=td)
        async with ctx.typing():
            embed = discord.Embed(color=0x2B2D31, title=f"About")
        embed.add_field(
            name="Stats",
            value=f"Developer: [sin](https://slit.sh)\nUsers: {len(self.bot.users)}\nServers: {len(self.bot.guilds)}",
            inline=False,
        )
        embed.add_field(
            name="Backend:",
            value=f"Latency: {round(self.bot.latency * 1000)}ms\nLibrary: discord.py\nCPU Usage: {psutil.cpu_percent(interval=0)}%\nMemory Usage: {psutil.virtual_memory().percent}%",
            inline=False,
        )
        embed.add_field(
            name="System:",
            value=f"CPU: AMD Ryzen 5 3600\nRam: 62.7GB\nDisk: 435.8GB",
            inline=False,
        )
        embed.set_footer(
            text="grief",
            icon_url="https://cdn.discordapp.com/emojis/886356428116357120.gif",
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        # embed.add_field(name="Shard", value=f"This ShardID: {ctx.guild.shard_id}\nShardLatency: {self.bot.get_shard(ctx.guild.shard_id).latency} ms", inline=False)
        # embed.add_field(name="System:", value=f"`Latency:` `{round(self.bot.latency * 1000)}ms`\n`Language:` `Python`\n`System`: `{my_system.system}`\n`CPU Usage:` `{psutil.cpu_percent(interval=0.6)}%`\n`Memory Usage:` `{psutil.virtual_memory().percent}%`", inline=True
        button1 = discord.ui.Button(
            label="Invite",
            style=discord.ButtonStyle.url,
            url="https://discord.com/api/oauth2/authorize?client_id=716939297009434656&permissions=8&scope=bot%20applications.commands",
        )
        button2 = discord.ui.Button(
            label="Support",
            style=discord.ButtonStyle.url,
            url="https://discord.gg/seer",
        )
        view = discord.ui.View()
        view.add_item(button1)
        view.add_item(button2)
        await ctx.reply(embed=embed, view=view, mention_author=False)
