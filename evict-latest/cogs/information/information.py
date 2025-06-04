from __future__ import annotations

from itertools import groupby
from typing import Optional, Literal
import aiohttp
import json
from uuid import UUID
from datetime import datetime, timezone, timedelta

from discord import (
    ActivityType,
    Colour,
    Embed,
    TextChannel,
    CategoryChannel,
    VoiceChannel,
    Guild,
    Invite,
    ButtonStyle,
    Member,
    Message,
    PartialInviteGuild,
    Permissions,
    Role,
    Spotify,
    Status,
    Streaming,
    User,
    app_commands,
    Interaction,
    TextStyle,
    SelectOption
)
from discord.ext.commands import (
    hybrid_command,
    hybrid_group,
    command,
    Cog,
    Group,
    has_permissions,
    parameter,
    flag
)
from discord.ui import Button, View, Modal, TextInput, Select
from discord.utils import format_dt, oauth_url, utcnow
from humanfriendly import format_size
from humanize import ordinal
from psutil import Process
from typing import Union
from typing import Annotated
from json import dumps

import config
import git
import discord
import time
from pathlib import Path

from main import Evict

from tools import dominant_color
from core.client.context import Context
from core.client import FlagConverter
from tools.formatter import human_join, plural, short_timespan
from tools.converters.basic import Location
from managers.paginator import Paginator

REPO_PATH = "/root/evict/.git"

class PollFlags(FlagConverter):
    title: str = flag(
        description="The title of the poll"
    )
    description: str = flag(
        description="The description/question of the poll"
    )
    duration: Optional[str] = flag(
        default=None,
        description="How long the poll should last (e.g. 1h, 1d)"
    )
    anonymous: bool = flag(
        default=False,
        description="Whether votes should be anonymous"
    )
    multiple_choice: bool = flag(
        default=False,
        description="Whether multiple options can be selected"
    )


class Information(Cog):
    def __init__(self, bot: Evict):
        self.bot = bot
        self.process = Process()
        self.weather_key = "64581e6f1d7d49ae834142709230804"
        self.description = "View information on various things."
        self._cached_commit = None
        self._cached_lines = None
        self._cached_files = None
        self._cached_imports = None
        self._cached_functions = None
        self._cached_commands = None
        self._cached_member_count = None
        self._last_cache_time = 0

    async def _update_cache(self):
        current_time = time.time()
        if (current_time - self._last_cache_time < 7200 and 
            all(x is not None for x in [
                self._cached_lines,
                self._cached_files, 
                self._cached_imports,
                self._cached_functions,
                self._cached_commit,
                self._cached_commands,
                self._cached_member_count
            ])):
            return
        
        try:
            repo = git.Repo(REPO_PATH)
            commit = repo.head.commit
            self._cached_commit = commit.hexsha[:7]
            
            self._cached_lines = sum(
                len(open(p, encoding='utf-8').readlines()) 
                for p in Path('.').rglob('*.py') 
                if not any(x in str(p) for x in [
                    '.venv', '.git', '__pycache__', 
                    '.pytest_cache', 'build', 'dist', 
                    '.eggs', '*.egg-info'
                ])
            )
            
            self._cached_files = len([
                p for p in Path('.').rglob('*.py') 
                if not any(x in str(p) for x in [
                    '.venv', '.git', '__pycache__', 
                    '.pytest_cache', 'build', 'dist', 
                    '.eggs', '*.egg-info'
                ])
            ])
            
            self._cached_imports = len(set(sum([list(mod.__dict__.keys()) for mod in [discord, config]], [])))
            
            self._cached_functions = len([f for f in dir(self.bot) if callable(getattr(self.bot, f)) and not f.startswith('_')])
            
            self._cached_commands = len([cmd for cmd in self.bot.walk_commands() 
                                      if cmd.cog_name not in ('Jishaku', 'Owner')])
            
            self._cached_member_count = sum(g.member_count for g in self.bot.guilds)
            
            self._last_cache_time = current_time
        except Exception as e:
            print(f"[Cache] Error updating cache: {str(e)}")

    @Cog.listener("on_guild_update")
    async def guild_name_listener(self, before: Guild, after: Guild):
        if before.name != after.name:
            await self.bot.db.execute(
                """
                INSERT INTO gnames (guild_id, name, changed_at) 
                VALUES ($1, $2, $3)
                """, 
                before.id, 
                before.name,
                datetime.now()
            )

    @Cog.listener("on_user_update")
    async def name_history_listener(self, before: User, after: User) -> None:
        if before.name == after.name and before.global_name == after.global_name:
            return

        await self.bot.db.execute(
            """
            INSERT INTO name_history (user_id, username)
            VALUES ($1, $2)
            """,
            after.id,
            (
                before.name
                if after.name != before.name
                else (before.global_name or before.name)
            ),
        )

    @Cog.listener()
    async def on_member_unboost(self, member: Member) -> None:
        if not member.premium_since:
            return

        await self.bot.db.execute(
            """
            INSERT INTO boosters_lost (guild_id, user_id, lasted_for)
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, user_id) DO UPDATE
            SET lasted_for = EXCLUDED.lasted_for
            """,
            member.guild.id,
            member.id,
            utcnow() - member.premium_since,
        )

    @hybrid_command(aliases=["beep"])
    async def ping(self, ctx: Context) -> None:
        """
        View the bot's latency.
        """
        latency = round(self.bot.latency * 1000)
        start_time = time.time()
        message = await ctx.neutral("ping...")
        end_time = time.time()
        edit_latency = round((end_time - start_time) * 1000)
        
        return await ctx.neutral(message=f"`{latency}ms` (edit: `{edit_latency}ms`)", patch=message)

    @hybrid_command()
    async def shards(self, ctx: Context):
        """
        View the bot shard latency.
        """

        embed = Embed(title=f"Total shards [{self.bot.shard_count}]")

        for shard in self.bot.shards:
            guilds = [g for g in self.bot.guilds if g.shard_id == shard]
            users = sum([g.member_count for g in guilds])
            shard_indicator = f"{config.EMOJIS.MISC.CONNECTION}" if ctx.guild.shard_id == shard else ""
            embed.add_field(
                name=f"Shard {shard} {shard_indicator}",
                value=f"**ping**: ``{round(self.bot.shards.get(shard).latency * 1000)}ms``\n**guilds**: ``{len(guilds)}``\n**users**: ``{users:,}``",
                inline=True,
            )
            embed.set_footer(text=f"You are on Shard {ctx.guild.shard_id}", icon_url=f"{self.bot.user.display_avatar.url}")

        await ctx.send(embed=embed)

    @command(aliases=["inv"])
    async def invite(self, ctx: Context) -> Message:
        """
        Get an invite link for the bot.
        """

        view = View()
        view.add_item(
            Button(
                url=config.CLIENT.INVITE_URL,
                style=ButtonStyle.link,
                emoji=config.EMOJIS.SOCIAL.WEBSITE,
            )
        )

        return await ctx.send(view=view)

    @command(aliases=["discord"])
    async def support(self, ctx: Context) -> Message:
        """
        Get an invite link for the bot's support server.
        """

        view = View()
        view.add_item(
            Button(
                url=config.CLIENT.SUPPORT_URL,
                style=ButtonStyle.link,
                emoji=config.EMOJIS.SOCIAL.DISCORD,
            )
        )

        return await ctx.send(view=view)

    @hybrid_command(name="about", aliases=["botinfo", "bi"])
    async def about(self, ctx: Context) -> Message:
        """
        View information about the bot.
        """
        await self._update_cache()

        regular_cogs = len(self.bot.cogs)
        extensions = len(self.bot.extensions)
        total_modules = regular_cogs + extensions

        lines = sum(
                len(open(p, encoding='utf-8').readlines()) 
                for p in Path('.').rglob('*.py') 
                if not any(x in str(p) for x in [
                    '.venv', '.git', '__pycache__', 
                    '.pytest_cache', 'build', 'dist', 
                    '.eggs', '*.egg-info'
                ])
            )
            
        files = len([
                p for p in Path('.').rglob('*.py') 
                if not any(x in str(p) for x in [
                    '.venv', '.git', '__pycache__', 
                    '.pytest_cache', 'build', 'dist', 
                    '.eggs', '*.egg-info'
                ])
            ])
            
        imports = len(set(sum([list(mod.__dict__.keys()) for mod in [discord, config]], [])))
            
        functions = len([f for f in dir(self.bot) if callable(getattr(self.bot, f)) and not f.startswith('_')])
            
        commands = len([cmd for cmd in self.bot.walk_commands() 
                                      if cmd.cog_name not in ('Jishaku', 'Owner')])
            
        member_count = sum(g.member_count for g in self.bot.guilds)

        embed = Embed(
            description=(
                f"Developed and maintained by [x](https://discord.com/users/1332327503062106154), [adam](https://discord.com/users/930383131863842816), [lego](https://discord.com/users/320288667329495040)\n"
                f"Utilizing ``{commands or 0:,}`` commands across ``{len(self.bot.cogs)}`` cogs (`{total_modules}` total modules)"
            ),
        )
        embed.set_author(
            name=self.bot.user.name,
            icon_url=self.bot.user.display_avatar.url,
            url=config.CLIENT.SUPPORT_URL
            or oauth_url(self.bot.user.id, permissions=Permissions(permissions=8)),
        )

        embed.add_field(
            name="**Bot**",
            inline=True,
            value="\n".join(
            [
                f"**Users:** `{member_count:,}`",
                f"**Servers:** `{len(self.bot.guilds):,}`",
                f"**Created:** <t:{int(self.bot.user.created_at.timestamp())}:R>",
            ]
            ),
        )

        embed.add_field(
            name="**System**",
            inline=True,
            value="\n".join(
                [
                    f"**CPU:** `{self.process.cpu_percent()}%`",
                    f"**Memory:** `{format_size(self.process.memory_info().rss)}`",
                    f"**Launched:** {format_dt(self.bot.uptime, 'R')}",
                ]
            ),
        )

        embed.add_field(
            name="**Code**",
            inline=True,
            value="\n".join(
                [
                    f"**Lines:** `{lines:,}`",
                    f"**Files:** `{files:,}`",
                    f"**Imports:** `{imports:,}`",
                    f"**Functions:** `{functions:,}`",
                ]
            ),
        )

        button1 = Button(
            label="GitHub",
            style=discord.ButtonStyle.gray,
            emoji=config.EMOJIS.SOCIAL.GITHUB,
            url="https://github.com/x32u",
        )

        button2 = Button(
            label="Support",
            style=discord.ButtonStyle.gray,
            emoji=config.EMOJIS.SOCIAL.DISCORD,
            url="https://discord.gg/evict",
        )

        button3 = Button(
            label="Website",
            style=discord.ButtonStyle.gray,
            emoji=config.EMOJIS.SOCIAL.WEBSITE,
            url="https://evict.bot",
        )

        view = discord.ui.View()
        view.add_item(button1)
        view.add_item(button2)
        view.add_item(button3)

        embed.set_footer(
            text=f"evict/v{self.bot.version} • Latest Commit: {self._cached_commit}"
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)

        return await ctx.send(embed=embed, view=view)

    @app_commands.command(name='botinfo')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def botinfo_slash(self, interaction: Interaction):
        """View information about the bot."""
        ctx = await Context.from_interaction(interaction)
        await self.about(ctx)

    @app_commands.command(name='botinfo')
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def botinfo_slash(self, interaction: Interaction):
        """View information about the bot."""
        ctx = await Context.from_interaction(interaction)
        await self.about(ctx)

    @command(example="evict", aliases=["ii"])
    async def inviteinfo(self, ctx: Context, *, invite: Invite) -> Message:
        """
        View information about an invite.
        """

        guild = invite.guild
        embed = Embed(
            description=f"{format_dt(guild.created_at)} ({format_dt(guild.created_at, 'R')})"
        )
        embed.set_author(
            name=f"{guild.name} ({guild.id})",
            url=invite.url,
            icon_url=guild.icon,
        )
        if guild.icon:
            buffer = await guild.icon.read()
            embed.color = await dominant_color(buffer)

        embed.add_field(
            name="**Information**",
            value=(
                ""
                f"**Invitier:** {invite.inviter or 'Vanity URL'}\n"
                f"**Channel:** {invite.channel or 'Unknown'}\n"
                f"**Created:** {format_dt(invite.created_at or guild.created_at)}"
            ),
        )
        embed.add_field(
            name="**Guild**",
            value=(
                ""
                f"**Members:** {invite.approximate_member_count:,}\n"
                f"**Members Online:** {invite.approximate_presence_count:,}\n"
                f"**Verification Level:** {guild.verification_level.name.title()}"
            ),
        )

        return await ctx.send(embed=embed)

    @command(example="evict", aliases=["sbanner"])
    async def serverbanner(
        self,
        ctx: Context,
        *,
        invite: Optional[Invite],
    ) -> Message:
        """
        View a server's banner if one is present.
        """

        guild = (
            invite.guild
            if isinstance(invite, Invite)
            and isinstance(invite.guild, PartialInviteGuild)
            else ctx.guild
        )
        if not guild.banner:
            return await ctx.warn(f"**{guild}** doesn't have a banner present!")

        embed = Embed(
            url=guild.banner,
            title=f"{guild}'s banner",
        )
        embed.set_image(url=guild.banner)

        return await ctx.send(embed=embed)

    @command(example="evict", aliases=["sicon"])
    async def servericon(
        self,
        ctx: Context,
        *,
        invite: Optional[Invite],
    ) -> Message:
        """
        View a server's icon if one is present.
        """

        guild = (
            invite.guild
            if isinstance(invite, Invite)
            and isinstance(invite.guild, PartialInviteGuild)
            else ctx.guild
        )
        if not guild.icon:
            return await ctx.warn(f"**{guild}** doesn't have a icon present!")

        embed = Embed(
            url=guild.icon,
            title=f"{guild}'s icon",
        )
        embed.set_image(url=guild.icon)

        return await ctx.send(embed=embed)

    @hybrid_command(
        aliases=[
            "pfp",
            "avi",
            "av",
        ],
        example="@x",
        with_app_command=True,
        fallback="view"
    )
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def avatar(
        self,
        ctx: Context,
        *,
        user: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View a user's avatar.
        """

        embed = Embed(
            url=user.avatar or user.default_avatar,
            title="Your avatar" if user == ctx.author else f"{user.name}'s avatar",
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=user.avatar or user.default_avatar)

        return await ctx.send(embed=embed)

    @hybrid_command(
        aliases=[
            "spfp",
            "savi",
            "sav",
        ],
        example="@x",
    )
    async def serveravatar(
        self,
        ctx: Context,
        *,
        member: Member = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View a user's avatar.
        """

        member = member or ctx.author
        if not member.guild_avatar:
            return await ctx.warn(
                "You don't have a server avatar present!"
                if member == ctx.author
                else f"**{member}** doesn't have a server avatar present!"
            )

        embed = Embed(
            url=member.guild_avatar,
            title=(
                "Your server avatar"
                if member == ctx.author
                else f"{member.name}'s server avatar"
            ),
        )
        embed.set_image(url=member.guild_avatar)

        return await ctx.send(embed=embed)

    @hybrid_command(
        aliases=[
            "mb",
        ],
        example="@x",
    )
    async def memberbanner(
        self,
        ctx: Context,
        *,
        member: Member = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View a user's server banner.
        """

        member = member or ctx.author
        if not member.guild_banner:
            return await ctx.warn(
                "You don't have a server banner present!"
                if member == ctx.author
                else f"**{member}** doesn't have a server banner present!"
            )

        embed = Embed(
            url=member.guild_banner,
            title=(
                "Your server banner"
                if member == ctx.author
                else f"{member.name}'s server banner"
            ),
        )
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=member.guild_banner)

        return await ctx.send(embed=embed)

    @hybrid_command(aliases=["userbanner", "ub"], example="@x", with_app_command=True, brief="View a user's banner.", fallback="view")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def banner(
        self,
        ctx: Context,
        *,
        user: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """View a user's banner if one is present."""

        fetched_user = await self.bot.fetch_user(user.id)

        if not fetched_user.banner:
            return await ctx.warn(
                "You don't have a banner present!"
                if user == ctx.author
                else f"**{user}** doesn't have a banner present!"
            )

        embed = Embed(
            url=fetched_user.banner.url,
            title="Your banner" if user == ctx.author else f"{user.name}'s banner",
        )
        embed.set_image(url=fetched_user.banner.url)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)

        return await ctx.send(embed=embed)

    @command(aliases=["mc"], example="evict")
    async def membercount(
        self,
        ctx: Context,
        *,
        guild: Optional[Guild],
    ) -> Message:
        """
        View the member count of a server.
        """

        guild = guild or ctx.guild
        embed = Embed()
        embed.set_author(
            name=guild,
            icon_url=guild.icon,
        )

        humans = list(list(filter(lambda member: not member.bot, guild.members)))
        bots = list(list(filter(lambda member: member.bot, guild.members)))

        embed.add_field(name="**Members**", value=f"{len(guild.members):,}")
        embed.add_field(name="**Humans**", value=f"{len(humans):,}")
        embed.add_field(name="**Bots**", value=f"{len(bots):,}")

        return await ctx.send(embed=embed)

    @hybrid_command(aliases=["sinfo", "si"], example="evict", with_app_command=True, brief="View server information.", fallback="view")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def serverinfo(
        self,
        ctx: Context,
        *,
        guild: str = None,
    ) -> Message:
        """
        View information about the server.
        """
        if guild:
            try:
                guild_id = int(guild)
                target_guild = self.bot.get_guild(guild_id)
            except ValueError:
                guild = guild.lower().strip()
                
                if 'discord.gg/' in guild:
                    invite_code = guild.split('discord.gg/')[-1]
                else:
                    invite_code = guild
                    
                try:
                    invite = await self.bot.fetch_invite(invite_code)
                    target_guild = invite.guild
                except (discord.NotFound, discord.HTTPException):
                    target_guild = discord.utils.get(self.bot.guilds, name=guild)
        else:
            target_guild = (
                self.bot.get_guild(892675627373699072)  
                if isinstance(ctx.channel, discord.DMChannel)
                else ctx.guild
            )

        if not target_guild:
            return await ctx.warn("Server not found!")

        embed = Embed(
            description=f"{format_dt(target_guild.created_at)} ({format_dt(target_guild.created_at, 'R')})"
        )
        embed.set_author(
            name=f"{target_guild.name} ({target_guild.id})",
            url=target_guild.vanity_url,
            icon_url=target_guild.icon,
        )
        if target_guild.icon:
            buffer = await target_guild.icon.read()
            embed.color = await dominant_color(buffer)

        embed.add_field(
            name="**Information**",
            value=(
                ""
                f"**Owner:** {target_guild.owner or target_guild.owner_id}\n"
                f"**Verification:** {target_guild.verification_level.name.title()}\n"
                f"**Nitro Boosts:** {target_guild.premium_subscription_count:,} (`Level {target_guild.premium_tier}`)"
            ),
        )
        embed.add_field(
            name="**Statistics**",
            value=(
                ""
                f"**Members:** {target_guild.member_count:,}\n"
                f"**Text Channels:** {len(target_guild.text_channels):,}\n"
                f"**Voice Channels:** {len(target_guild.voice_channels):,}\n"
            ),
        )

        if target_guild == ctx.guild and (roles := target_guild.roles[1:]):
            roles = list(reversed(roles))

            embed.add_field(
                name=f"**Roles ({len(roles)})**",
                value=(
                    ""
                    + ", ".join(role.mention for role in roles[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else "")
                ),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @hybrid_command(aliases=["uinfo", "ui"], example="@x", with_app_command=True, brief="View information about a user.", fallback="view")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def userinfo(
        self,
        ctx: Context,
        *,
        user: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View information about a user.
        """
        embed = Embed(color=user.color if user.color != Colour.default() else ctx.color)
        embed.title = f"{user} {'[BOT]' if user.bot else ''}"
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
        embed.description = ""

        if isinstance(user, Member):
            support_guild = self.bot.get_guild(892675627373699072)
            if support_guild:
                if not support_guild.chunked:
                    await support_guild.chunk()
                support_member = support_guild.get_member(user.id)
            else:
                support_member = None
            
            badges = []
            staff_eligible = False

            if user is ctx.guild.owner:
                badges.append(f"{config.EMOJIS.BADGES.SERVER_OWNER}")
            
            if support_member:  
                if any(role.id == 1265473601755414528 for role in support_member.roles):
                    badges.extend([f"{config.EMOJIS.STAFF.DEVELOPER}", f"{config.EMOJIS.STAFF.OWNER}"])
                    staff_eligible = True

                if any(role.id == 1330750312553644176 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.HEADSTAFF}")
                    staff_eligible = True

                if any(role.id == 1340989544656277565 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.HEADQA}")
                    staff_eligible = True
                    
                if any(role.id == 1264110559989862406 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.SUPPORT}")
                    staff_eligible = True
                    
                if any(role.id == 1323255508609663098 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.TRIAL}")
                    staff_eligible = True

                if any(role.id == 1325007612797784144 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.MODERATOR}")
                    staff_eligible = True

                if any(role.id == 1318054098666389534 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.DONOR}")
                    
                if any(role.id == 1320428924215496704 for role in support_member.roles):
                    badges.append(f"{config.EMOJIS.STAFF.INSTANCE}")
                
            if badges:
                if staff_eligible:
                    badges.append(f"{config.EMOJIS.STAFF.STAFF}")
                embed.description = f"{' '.join(badges)}"

        embed.set_thumbnail(url=user.display_avatar)
        embed.set_footer(text=f"{len(user.mutual_guilds)} mutual servers")

        embed.add_field(
            name="**Created**",
            value=(
                format_dt(user.created_at, "D")
                + "\n> "
                + format_dt(user.created_at, "R")
            ),
        )

        if isinstance(user, Member) and user.joined_at:
            join_pos = sorted(
                user.guild.members,
                key=lambda member: member.joined_at or utcnow(),
            ).index(user)

            embed.add_field(
                name=f"**Joined ({ordinal(join_pos + 1)})**",
                value=(
                    format_dt(user.joined_at, "D")
                    + "\n> "
                    + format_dt(user.joined_at, "R")
                ),
            )

            if user.premium_since:
                embed.add_field(
                    name="**Boosted**",
                    value=(
                        format_dt(user.premium_since, "D")
                        + "\n> "
                        + format_dt(user.premium_since, "R")
                    ),
                )

            if roles := user.roles[1:]:
                embed.add_field(
                    name="**Roles**",
                    value=", ".join(role.mention for role in list(reversed(roles))[:5])
                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else ""),
                    inline=False,
                )

            if (voice := user.voice) and voice.channel:
                members = len(voice.channel.members) - 1
                phrase = "Streaming inside" if voice.self_stream else "Inside"
                embed.description += f"🎙 {phrase} {voice.channel.mention} " + (
                    f"with {plural(members):other}" if members else "by themselves"
                )

            for activity_type, activities in groupby(
                user.activities,
                key=lambda activity: activity.type,
            ):
                activities = list(activities)
                if isinstance(activities[0], Spotify):
                    activity = activities[0]
                    embed.description += f"\n🎵 Listening to [**{activity.title}**]({activity.track_url}) by **{activity.artists[0]}**"

                elif isinstance(activities[0], Streaming):
                    embed.description += "\n🎥 Streaming " + human_join(
                        [
                            f"[**{activity.name}**]({activity.url})"
                            for activity in activities
                            if isinstance(activity, Streaming)
                        ],
                        final="and",
                    )

                elif activity_type == ActivityType.playing:
                    embed.description += "\n🎮 Playing " + human_join(
                        [f"**{activity.name}**" for activity in activities],
                        final="and",
                    )

                elif activity_type == ActivityType.watching:
                    embed.description += "\n📺 Watching " + human_join(
                        [f"**{activity.name}**" for activity in activities],
                        final="and",
                    )

                elif activity_type == ActivityType.competing:
                    embed.description += "\n🏆 Competing in " + human_join(
                        [f"**{activity.name}**" for activity in activities],
                        final="and",
                    )

            embed.title += " "

        return await ctx.send(embed=embed)

    @hybrid_group(
        aliases=["names", "nh"],
        invoke_without_command=True,
        example="@x",
    )
    async def namehistory(
        self,
        ctx: Context,
        *,
        user: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View a user's name history.
        """

        names = await self.bot.db.fetch(
            """
            SELECT *
            FROM name_history
            WHERE user_id = $1
            """
            + ("" if ctx.author.id in self.bot.owner_ids else "\nAND is_hidden = FALSE")
            + "\nORDER BY changed_at DESC",
            user.id,
        )
        if not names:
            return await ctx.warn(f"**{user}** doesn't have any name history!")

        paginator = Paginator(
            ctx,
            entries=[
                f"**{record['username']}** ({format_dt(record['changed_at'], 'R')})"
                for record in names
            ],
            embed=Embed(title="Name History"),
        )
        return await paginator.start()

    @namehistory.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    async def namehistory_clear(self, ctx: Context) -> Message:
        """
        Remove all your name history.
        """

        await self.bot.db.execute(
            """
            UPDATE name_history
            SET is_hidden = TRUE
            WHERE user_id = $1
            """,
            ctx.author.id,
        )

        return await ctx.approve("Successfully cleared your name history")

    @hybrid_command(
        aliases=[
            "device",
            "presence",
        ],
        example="@x",
    )
    async def devices(
        self,
        ctx: Context,
        *,
        member: Member = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View a member's platforms.
        """

        member = member or ctx.author
        if member.status == Status.offline:
            return await ctx.warn(
                "You're appearing offline!"
                if member == ctx.author
                else f"**{member}** doesn't appear to be online!"
            )

        emojis = {
            Status.offline: "⚪️",
            Status.online: "🟢",
            Status.idle: "🟡",
            Status.dnd: "🔴",
        }

        embed = Embed(
            title="Your devices" if member == ctx.author else f"{member.name}'s devices"
        )
        embed.description = ""
        for activity_type, activities in groupby(
            member.activities,
            key=lambda activity: activity.type,
        ):
            activities = list(activities)
            if isinstance(activities[0], Spotify):
                activity = activities[0]
                embed.description += f"\n🎵 Listening to [**{activity.title}**]({activity.track_url}) by **{activity.artists[0]}**"  # type: ignore

            elif isinstance(activities[0], Streaming):
                embed.description += "\n🎥 Streaming " + human_join(
                    [
                        f"[**{activity.name}**]({activity.url})"
                        for activity in activities
                        if isinstance(activity, Streaming)
                    ],
                    final="and",
                )  # type: ignore

            elif activity_type == ActivityType.playing:
                embed.description += "\n🎮 Playing " + human_join(
                    [f"**{activity.name}**" for activity in activities],
                    final="and",
                )

            elif activity_type == ActivityType.watching:
                embed.description += "\n📺 Watching " + human_join(
                    [f"**{activity.name}**" for activity in activities],
                    final="and",
                )

            elif activity_type == ActivityType.competing:
                embed.description += "\n🏆 Competing in " + human_join(
                    [f"**{activity.name}**" for activity in activities],
                    final="and",
                )

        embed.description += "\n" + "\n".join(
            [
                f"{emojis[status]} **{device}**"
                for device, status in {
                    "Mobile": member.mobile_status,
                    "Desktop": member.desktop_status,
                    "Browser": member.web_status,
                }.items()
                if status != Status.offline
            ]
        )

        return await ctx.send(embed=embed)

    @hybrid_command()
    async def roles(self, ctx: Context) -> Message:
        """
        View the server roles.
        """

        roles = reversed(ctx.guild.roles[1:])
        if not roles:
            return await ctx.warn(f"**{ctx.guild}** doesn't have any roles!")

        paginator = Paginator(
            ctx,
            entries=[f"{role.mention} (`{role.id}`)" for role in roles],
            embed=Embed(title=f"Roles in {ctx.guild}"),
        )
        return await paginator.start()

    @hybrid_command(example="@member")
    async def inrole(self, ctx: Context, *, role: Role) -> Message:
        """
        View members which have a role.
        """

        members = role.members
        if not members:
            return await ctx.warn(f"{role.mention} doesn't have any members!")

        paginator = Paginator(
            ctx,
            entries=[f"{member.mention} (`{member.id}`)" for member in members],
            embed=Embed(title=f"Members with {role}"),
        )
        return await paginator.start()

    @hybrid_group(invoke_without_command=True)
    async def boosters(self, ctx: Context) -> Message:
        """
        View server boosters.
        """

        members = list(
            filter(
                lambda member: member.premium_since is not None,
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn("No members are currently boosting!")

        paginator = Paginator(
            ctx,
            entries=[
                f"{member.mention} - boosted {format_dt(member.premium_since or utcnow(), 'R')}"
                for member in sorted(
                    members,
                    key=lambda member: member.premium_since or utcnow(),
                    reverse=True,
                )
            ],
            embed=Embed(title="Boosters"),
        )
        return await paginator.start()

    @boosters.command(name="lost")
    async def boosters_lost(self, ctx: Context) -> Message:
        """
        View all lost boosters.
        """
        users = [
            f"{user.mention} stopped {format_dt(record['ended_at'], 'R')} (lasted {short_timespan(record['lasted_for'])})"
            for record in await self.bot.db.fetch(
                """
                SELECT *
                FROM boosters_lost
                WHERE guild_id = $1
                ORDER BY ended_at DESC
                """,
                ctx.guild.id,
            )
            if (user := self.bot.get_user(record["user_id"]))
        ]
        if not users:
            return await ctx.warn("No boosters have been lost!")

        paginator = Paginator(
            ctx,
            entries=users,
            embed=Embed(title="Boosters Lost"),
        )
        return await paginator.start()

    @hybrid_command()
    async def bots(self, ctx: Context) -> Message:
        """
        View all bots in the server.
        """
        members = list(
            filter(
                lambda member: member.bot,
                ctx.guild.members,
            )
        )
        if not members:
            return await ctx.warn(f"**{ctx.guild}** doesn't have any bots!")

        paginator = Paginator(
            ctx,
            entries=[
                f"{member.mention} (`{member.id}`)"
                for member in sorted(
                    members,
                    key=lambda member: member.joined_at or utcnow(),
                    reverse=True,
                )
            ],
            embed=Embed(title=f"Bots in {ctx.guild}"),
        )
        return await paginator.start()
    
    @command(aliases=["bans"])
    @has_permissions(ban_members=True)
    async def banlist(self, ctx: Context) -> Message:
        """
        View all banned members.
        """
        bans = []
        async for ban in ctx.guild.bans():
            bans.append(ban)

        if not bans:
            return await ctx.warn("No members are currently banned!")

        paginator = Paginator(
            ctx,
            entries=[
                f"{ban.user.mention} (`{ban.user.id}`) - {ban.reason or 'No reason'}"
                for ban in bans
            ],
            embed=Embed(title=f"Banned Members [{len(bans)}]"),
        )
        
        return await paginator.start()

    @hybrid_command(aliases=["gi"])
    @has_permissions(manage_guild=True)
    async def guildinvites(self, ctx: Context) -> Message:
        """
        View all server invites.
        """
        invites = await ctx.guild.invites()
        if not invites:
            return await ctx.warn("No invites are currently present!")

        paginator = Paginator(
            ctx,
            entries=[
                f"[{invite.code}]({invite.url}) by {invite.inviter.mention if invite.inviter else '**Unknown**'} expires {format_dt(invite.expires_at, 'R') if invite.expires_at else '**Never**'}"
                for invite in sorted(
                    invites,
                    key=lambda invite: invite.created_at or utcnow(),
                    reverse=True,
                )
            ],
            embed=Embed(title=f"Invites in {ctx.guild}"),
        )
        return await paginator.start()

    @hybrid_command(aliases=["emotes"])
    async def emojis(self, ctx: Context) -> Message:
        """
        View all server emojis.
        """

        emojis = ctx.guild.emojis
        if not emojis:
            return await ctx.warn(f"**{ctx.guild}** doesn't have any emojis!")

        paginator = Paginator(
            ctx,
            entries=[f"{emoji} ([`{emoji.id}`]({emoji.url}))" for emoji in emojis],
            embed=Embed(title=f"Emojis in {ctx.guild}"),
        )
        return await paginator.start()

    @hybrid_command()
    async def stickers(self, ctx: Context) -> Message:
        """
        View all server stickers.
        """
        stickers = ctx.guild.stickers
        if not stickers:
            return await ctx.warn(f"**{ctx.guild}** doesn't have any stickers!")

        paginator = Paginator(
            ctx,
            entries=[
                f"[{sticker.name}]({sticker.url}) (`{sticker.id}`)"
                for sticker in stickers
            ],
            embed=Embed(title=f"Stickers in {ctx.guild}"),
        )
        return await paginator.start()

    @hybrid_command(aliases=["firstmsg"])
    async def firstmessage(self, ctx: Context) -> Message:
        """
        View the first message sent.
        """
        message = [
            message async for message in ctx.channel.history(limit=1, oldest_first=True)
        ][0]
        return await ctx.neutral(
            f"Jump to the [`first message`]({message.jump_url}) sent by **{message.author}**"
        )

    @hybrid_command(aliases=["pos"], example="@x")
    async def position(self, ctx: Context, *, member: Member = None):
        """
        Check member join position.
        """
        if member is None:
            member = ctx.author

        pos = (
            sum(
                1
                for m in ctx.guild.members
                if m.joined_at is not None and m.joined_at < member.joined_at
            )
            + 1
        )

        embed = Embed(description=f"{member.mention} is member number ``{pos}``.")

        await ctx.send(embed=embed)

    @command(example="#general", aliases=["chinfo", "cinfo", "ci"])
    async def channelinfo(
        self,
        ctx: Context,
        channel: Optional[Union[TextChannel, VoiceChannel, CategoryChannel]],
    ):
        """
        View information about a channel.
        """
        if channel is None:
            channel = ctx.channel

        embed = Embed(title=f"{channel.name}", color=ctx.author.top_role.color)

        embed.set_author(
            name=f"{ctx.author.display_name}",
            icon_url=f"{ctx.author.display_avatar.url}",
        )

        embed.add_field(name="Channel ID", value=f"``{channel.id}``", inline=False)

        embed.add_field(
            name="Type", value=f"``{str(channel.type).lower()}``", inline=False
        )

        if isinstance(channel, (TextChannel, VoiceChannel)):
            category = channel.category

            if category:
                embed.add_field(
                    name="Category",
                    value=f"``{category.name}`` (``{category.id}``)",
                    inline=False,
                )
            else:
                embed.add_field(name="Category", value="No category", inline=False)

        if isinstance(channel, TextChannel):
            embed.add_field(
                name="Topic",
                value=(
                    f"{channel.topic}" if channel.topic else "No topic on this channel"
                ),
                inline=False,
            )

        elif isinstance(channel, CategoryChannel):
            child_channels = [child.name for child in channel.channels]
            if child_channels:
                embed.add_field(
                    name=f"{len(child_channels)} Children",
                    value=", ".join(child_channels),
                    inline=False,
                )

        embed.add_field(
            name="Created On",
            value=f"{format_dt(channel.created_at)} ({format_dt(channel.created_at, 'R')})",
            inline=False,
        )

        await ctx.send(embed=embed)

    @command(example="@owner", aliases=["rinfo"])
    async def roleinfo(self, ctx: Context, role: Optional[Role]):
        """
        View information about a role.
        """
        if role is None:
            role = ctx.author.top_role

        embed = Embed(title=f"{role.name}", color=role.color)

        embed.set_author(
            name=f"{ctx.author.display_name}",
            icon_url=f"{ctx.author.display_avatar.url}",
        )
        embed.add_field(name="Role ID", value=f"``{role.id}``", inline=False)
        embed.add_field(name="Color", value=f"``{role.color}``", inline=False)

        specific_permissions = [
            "administrator",
            "ban_members",
            "kick_members",
            "manage_guild",
            "manage_channels",
            "manage_roles",
            "manage_messages",
            "view_audit_log",
            "manage_webhooks",
            "manage_expressions",
            "mute_members",
            "deafen_members",
            "move_members",
            "manage_nicknames",
            "mention_everyone",
            "view_guild_insights",
            "moderate_members",
        ]

        granted_permissions = [
            perm for perm in specific_permissions if getattr(role.permissions, perm)
        ]

        if granted_permissions:
            embed.add_field(
                name="Permissions",
                value=(
                    ", ".join(granted_permissions)
                    if len(granted_permissions) > 1
                    else granted_permissions[0]
                ),
                inline=False,
            )

        else:
            embed.add_field(
                name="Permissions",
                value="No dangerous permissions granted.",
                inline=False,
            )

        members_with_role = role.members
        member_names = [member.name for member in members_with_role][:5]

        if member_names:
            embed.add_field(
                name=f"{len(role.members)} Member(s)",
                value=(
                    ", ".join(member_names)
                    if len(member_names) > 1
                    else member_names[0]
                ),
                inline=False,
            )

        else:
            embed.add_field(
                name="Members with this Role",
                value="No members in this role.",
                inline=False,
            )

        if role.icon:
            embed.set_thumbnail(url=role.icon.url)

        if granted_permissions:
            embed.set_footer(
                text="Dangerous Permissions!",
                icon_url="https://cdn.discordapp.com/emojis/1308023743565529138.webp?size=64",
            )

        await ctx.send(embed=embed)

    @command(example="1203514684326805524", aliases=["gbi"])
    async def getbotinvite(self, ctx: Context, *, user: User):
        """
        Get a bots invite by providing the bots ID.
        """
        if not user.bot:
            return await ctx.warn("The ID provided is not a bot!")

        button = Button(
            style=ButtonStyle.link,
            label=f"Invite {user.name}",
            url=f"https://discord.com/api/oauth2/authorize?client_id={user.id}&permissions=8&scope=bot%20applications.commands",
        )

        view = View()
        view.add_item(button)

        await ctx.send(view=view)

    @command(example="892675627373699072")
    async def gnames(self, ctx: Context, guild: Optional[Guild]):
        """
        View a guild's name history.
        """
        if not guild:
            guild = ctx.guild

        names = await self.bot.db.fetch(
            """
            SELECT name, changed_at
            FROM gnames
            WHERE guild_id = $1
            ORDER BY changed_at DESC
            """,
            guild.id,
        )
        
        if not names:
            return await ctx.warn(f"**{guild}** doesn't have any name history!")

        paginator = Paginator(
            ctx,
            entries=[
                f"**{record['name']}** ({format_dt(record['changed_at'], 'R')})"
                for record in names
            ],
            embed=Embed(title=f"{guild.name} Name History"),
        )
        
        return await paginator.start()

    @command()
    @has_permissions(manage_guild=True)
    async def cleargnames(self, ctx: Context):
        """
        Clear the guild name history.
        """
        await self.bot.db.execute(
            """
            DELETE FROM gnames 
            WHERE guild_id = $1
            """, 
            ctx.guild.id
        )
        await ctx.approve("Cleared the guild name history!")

    @hybrid_command(name="weather", with_app_command=True, brief="Get the current weather for a city/country", fallback="view")
    @discord.app_commands.allowed_installs(guilds=True, users=True)
    @discord.app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @discord.app_commands.default_permissions(use_application_commands=True)
    async def weather(self, ctx: Context, *, location: str):
        """Get the current weather for a city/country"""
        
        location = location.replace(" ", "+")
        
        url = f"https://wttr.in/{location}?format=j1"
        async with self.bot.session.get(url) as response:
            if response.status != 200:
                return await ctx.warn(
                    f"Couldn't find weather data for `{location}`"
                )
                
            data = await response.json()
            current = data['current_condition'][0]
            
            weather_emojis = {
                'Sunny': '☀️',
                'Clear': '🌙',
                'Partly cloudy': '⛅',
                'Cloudy': '☁️',
                'Overcast': '☁️',
                'Mist': '🌫️',
                'Patchy rain': '🌦️',
                'Light rain': '🌧️',
                'Moderate rain': '🌧️',
                'Heavy rain': '⛈️',
                'Light snow': '🌨️',
                'Moderate snow': '🌨️',
                'Heavy snow': '❄️',
                'Thunder': '⛈️'
            }
            
            weather_desc = current['weatherDesc'][0]['value']
            weather_emoji = weather_emojis.get(weather_desc, '🌡️')

            embed = discord.Embed(
                title=f"Weather in {data['nearest_area'][0]['areaName'][0]['value']}",
                description=f"{weather_emoji} {weather_desc}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            temp_c = current['temp_C']
            temp_f = current['temp_F']
            feels_like_c = current['FeelsLikeC']
            feels_like_f = current['FeelsLikeF']
            
            embed.add_field(
                name="Temperature",
                value=f"🌡️ **{temp_c}°C** ({temp_f}°F)\n"
                    f"Feels like: {feels_like_c}°C ({feels_like_f}°F)",
                inline=True
            )
            
            embed.add_field(
                name="Humidity",
                value=f"💧 {current['humidity']}%",
                inline=True
            )
            
            embed.add_field(
                name="Wind",
                value=f"💨 {current['windspeedKmph']} km/h",
                inline=True
            )
            
            if 'cloudcover' in current:
                embed.add_field(
                    name="Cloud Cover",
                    value=f"☁️ {current['cloudcover']}%",
                    inline=True
                )
            
            if 'visibility' in current:
                embed.add_field(
                    name="Visibility",
                    value=f"👁️ {current['visibility']} km",
                    inline=True
                )
            
            if 'precipMM' in current:
                embed.add_field(
                    name="Precipitation",
                    value=f"🌧️ {current['precipMM']} mm",
                    inline=True
                )
            
            embed.set_thumbnail(url=f"https://wttr.in/{location}_0pq.png")
            
            await ctx.send(embed=embed)

    @hybrid_group(name="poll", invoke_without_command=True)
    @has_permissions(manage_messages=True)
    async def poll(self, ctx: Context) -> Message:
        """Poll management commands"""
        return await ctx.send_help(ctx.command)

    @poll.command(name="create")
    @has_permissions(manage_messages=True)
    async def poll_create(
        self,
        ctx: Context,
        *,
        flags: PollFlags
    ) -> Message:
        """Create a new poll using flags"""
        options = ["Yes", "No"] 
        
        if ctx.interaction: 
            modal = PollChoicesModal(title=flags.title)
            await ctx.interaction.response.send_modal(modal)
            await modal.wait()
            
            if not modal.choices:
                return await ctx.warn("Poll creation cancelled.")
            options = modal.choices

        ends_at = None
        if flags.duration:
            try:
                duration_seconds = parse_duration(flags.duration)
                ends_at = datetime.now(timezone.utc) + timedelta(seconds=duration_seconds)
            except ValueError:
                return await ctx.warn("Invalid duration format. Use 1h, 1d, etc.")

        settings = {
            "anonymous": flags.anonymous,
            "multiple_choice": flags.multiple_choice,
            "required_role": None,
            "show_voters": not flags.anonymous,
            "live_results": True
        }

        poll_id = await self.bot.db.fetchval("""
            INSERT INTO polls (
                guild_id, channel_id, message_id, creator_id,
                title, description, choices, settings, ends_at
            )
            VALUES ($1, $2, 0, $3, $4, $5, $6, $7, $8)
            RETURNING poll_id
        """, ctx.guild.id, ctx.channel.id, ctx.author.id,
            flags.title, flags.description, json.dumps(options),
            json.dumps(settings), ends_at)

        embed = await self.create_poll_embed(poll_id)
        view = PollView(poll_id)

        msg = await ctx.send(embed=embed, view=view)

        await self.bot.db.execute("""
            UPDATE polls 
            SET message_id = $1 
            WHERE poll_id = $2
        """, msg.id, poll_id)
        
        return msg

    async def create_poll_embed(self, poll_id: UUID) -> Embed:
        """Create the poll embed"""
        poll_data = await self.bot.db.fetchrow("""
            SELECT * FROM polls WHERE poll_id = $1
        """, poll_id)

        choices = json.loads(poll_data['choices'])
        settings = json.loads(poll_data['settings'])

        embed = Embed(
            title=poll_data['title'],
            description=poll_data['description'],
            color=config.COLORS.NEUTRAL,
            timestamp=poll_data['created_at']
        )

        for i, choice in enumerate(choices, 1):
            votes = await self.bot.db.fetchval("""
                SELECT COUNT(*) FROM poll_votes 
                WHERE poll_id = $1 AND $2 = ANY(choice_ids)
            """, poll_id, i)
            
            embed.add_field(
                name=f"Option {i}",
                value=f"{choice}\nVotes: {votes}",
                inline=True
            )

        footer_text = []
        if poll_data['ends_at']:
            footer_text.append(f"Ends {format_dt(poll_data['ends_at'], 'R')}")
        if settings['multiple_choice']:
            footer_text.append("Multiple choice enabled")
        if settings['anonymous']:
            footer_text.append("Anonymous voting")

        embed.set_footer(text=" • ".join(footer_text))

        return embed

    @poll.command(name="quick")
    @has_permissions(manage_messages=True)
    async def poll_quick(
        self,
        ctx: Context,
        question: str,
    ) -> Message:
        """Create a quick poll with simple yes/no or custom options
        """
        if not ctx.interaction:
            options = ["Yes", "No"]
        else:
            modal = PollChoicesModal("Quick Poll")
            await ctx.interaction.response.send_modal(modal)
            await modal.wait()

            if not modal.choices:
                options = ["Yes", "No"]
            else:
                options = modal.choices

        settings = {
            "anonymous": False,
            "multiple_choice": False,
            "required_role": None,
            "show_voters": True,
            "live_results": True
        }

        poll_id = await self.bot.db.fetchval("""
            INSERT INTO polls (
                guild_id, channel_id, message_id, creator_id,
                title, description, choices, settings
            )
            VALUES ($1, $2, 0, $3, $4, $5, $6, $7)
            RETURNING poll_id
        """, ctx.guild.id, ctx.channel.id, ctx.author.id,
            "Quick Poll", question, json.dumps(options),
            json.dumps(settings))

        embed = await self.create_poll_embed(poll_id)
        view = PollView(poll_id)
        
        msg = await ctx.send(embed=embed, view=view)
        
        await self.bot.db.execute("""
            UPDATE polls SET message_id = $1 WHERE poll_id = $2
        """, msg.id, poll_id)
        
        return msg

    @poll.command(name="list")
    async def poll_list(
        self,
        ctx: Context,
        creator: Optional[discord.Member] = None,
        sort_by: str = "time"
    ) -> Message:
        """
        List all active polls in the server
        """
        query = """
            SELECT p.*, COUNT(v.vote_id) as vote_count
            FROM polls p
            LEFT JOIN poll_votes v ON p.poll_id = v.poll_id
            WHERE p.guild_id = $1 AND p.is_active = true
        """
        params = [ctx.guild.id]
        
        if creator:
            query += " AND p.creator_id = $2"
            params.append(creator.id)
            
        query += " GROUP BY p.poll_id"
        
        if sort_by.lower() == "votes":
            query += " ORDER BY vote_count DESC"
        else:
            query += " ORDER BY p.created_at DESC"
            
        polls = await self.bot.db.fetch(query, *params)
        
        if not polls:
            return await ctx.warn(
                f"No active polls found{' for ' + creator.mention if creator else ''}!"
            )

        entries = []
        for poll in polls:
            vote_count = await self.bot.db.fetchval("""
                SELECT COUNT(*) FROM poll_votes WHERE poll_id = $1
            """, poll['poll_id'])
            
            entry = (
                f"**{poll['title']}**\n"
                f"Created by: {ctx.guild.get_member(poll['creator_id']).mention}\n"
                f"Votes: {vote_count}\n"
                f"ID: `{poll['poll_id']}`\n"
                f"Created: {format_dt(poll['created_at'], 'R')}"
            )
            if poll['ends_at']:
                entry += f"\nEnds: {format_dt(poll['ends_at'], 'R')}"
            entries.append(entry)

        paginator = Paginator(
            ctx,
            entries=entries,
            embed=Embed(title=f"Active Polls in {ctx.guild}"),
        )
        return await paginator.start()

    @poll.command(name="end")
    async def poll_end(self, ctx: Context, poll_id: str) -> Message:
        """
        End a poll early
        """
        try:
            poll_id = UUID(poll_id)
        except ValueError:
            return await ctx.warn("Invalid poll ID!")

        poll = await self.bot.db.fetchrow("""
            SELECT * FROM polls 
            WHERE poll_id = $1 AND guild_id = $2 AND is_active = true
        """, poll_id, ctx.guild.id)
        
        if not poll:
            return await ctx.warn("Poll not found or already ended!")
            
        if not (
            ctx.author.id == poll['creator_id'] 
            or ctx.author.guild_permissions.manage_guild
        ):
            return await ctx.warn("You can't end this poll!")
            
        await self.bot.db.execute("""
            UPDATE polls SET is_active = false WHERE poll_id = $1
        """, poll_id)
        
        try:
            channel = ctx.guild.get_channel(poll['channel_id'])
            message = await channel.fetch_message(poll['message_id'])
            embed = await self.create_poll_embed(poll_id)
            await message.edit(embed=embed, view=None)
        except:
            pass
            
        return await ctx.approve("Poll ended successfully!")

    @poll.command(name="results")
    async def poll_results(self, ctx: Context, poll_id: str) -> Message:
        """
        View detailed results of a poll
        """
        try:
            poll_id = UUID(poll_id)
        except ValueError:
            return await ctx.warn("Invalid poll ID!")

        results_view = PollResultsView(poll_id)
        results_embed = await results_view.generate_results(ctx)
        
        if not results_embed:
            return await ctx.warn("Poll not found!")
            
        return await ctx.send(embed=results_embed, view=results_view)

    @command()
    async def status(self, ctx: Context):
        """
        Check shard status.
        """
        await ctx.neutral(
            f"Experiencing issues? Check your shard status [here](https://evict.bot/status).\n"
            f"Your guild is on shard {ctx.guild.shard_id}"
        )
    
class PollVoteSelect(Select):
    def __init__(self, poll_id: UUID, choices: list[str], multiple: bool = False):
        self.poll_id = poll_id
        
        options = [
            SelectOption(
                label=f"Option {i+1}",
                description=choice[:100],  
                value=str(i+1)
            )
            for i, choice in enumerate(choices)
        ]
        
        super().__init__(
            placeholder="Select your choice(s)...",
            options=options,
            min_values=1,
            max_values=len(options) if multiple else 1,
            custom_id=f"poll_vote_{poll_id}"
        )

    async def callback(self, interaction: Interaction):
        try:
            poll_data = await interaction.client.db.fetchrow("""
                SELECT * FROM polls 
                WHERE poll_id = $1 AND is_active = true
            """, self.poll_id)
            
            if not poll_data:
                return await interaction.response.send_message(
                    "This poll has ended.", ephemeral=True
                )
                
            settings = json.loads(poll_data['settings'])
            
            if settings['required_role']:
                role = interaction.guild.get_role(settings['required_role'])
                if role and role not in interaction.user.roles:
                    return await interaction.response.send_message(
                        f"You need the {role.mention} role to vote!", 
                        ephemeral=True
                    )

            choice_ids = [int(value) for value in self.values]
            
            await interaction.client.db.execute("""
                INSERT INTO poll_votes (poll_id, user_id, choice_ids)
                VALUES ($1, $2, $3)
                ON CONFLICT (poll_id, user_id) 
                DO UPDATE SET choice_ids = $3
            """, self.poll_id, interaction.user.id, choice_ids)
            
            try:
                embed = await interaction.client.get_cog('Information').create_poll_embed(
                    self.poll_id
                )
                await interaction.message.edit(embed=embed)
            except discord.NotFound:
                pass 
            
            await interaction.response.send_message(
                "Your vote has been recorded!", ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                "Failed to record your vote. Please try again.", ephemeral=True
            )

class PollResultsView(View):
    def __init__(self, poll_id: UUID):
        super().__init__(timeout=None)
        self.poll_id = poll_id

    async def generate_results(self, interaction: Interaction) -> Embed:
        poll_data = await interaction.client.db.fetchrow(
            """
            SELECT * FROM polls 
            WHERE poll_id = $1
            """, 
            self.poll_id
        )
        
        choices = json.loads(poll_data['choices'])
        settings = json.loads(poll_data['settings'])
        
        embed = Embed(
            title=f"Results: {poll_data['title']}",
            color=config.COLORS.NEUTRAL
        )
        
        total_votes = await interaction.client.db.fetchval(
            """
            SELECT COUNT(*) 
            FROM poll_votes 
            WHERE poll_id = $1
            """, 
            self.poll_id
        )
        
        for i, choice in enumerate(choices, 1):
            votes = await interaction.client.db.fetchval(
                """
                SELECT COUNT(*) 
                FROM poll_votes 
                WHERE poll_id = $1 
                AND $2 = ANY(choice_ids)
                """, 
                self.poll_id, 
                i
            )
            
            percentage = (votes / total_votes * 100) if total_votes > 0 else 0
            
            bar_length = 8
            filled_bars = int(percentage / 10)
            
            bar = ""
            if filled_bars > 0:
                bar += f"{config.EMOJIS.POLL.BLR}"
                
                if filled_bars > 1:
                    bar += f"{config.EMOJIS.POLL.SQUARE}" * (filled_bars - 2)
                
                if filled_bars > 1:
                    bar += f"{config.EMOJIS.POLL.BRR}"
            
            empty_bars = bar_length - filled_bars
            if empty_bars > 0:
                if filled_bars == 0:
                    bar += f"{config.EMOJIS.POLL.WLR}"
                    if empty_bars > 2:
                        bar += {config.EMOJIS.POLL.WHITE} * (empty_bars - 2)
                    bar += f"{config.EMOJIS.POLL.WRR}"
                else:
                    bar += f"{config.EMOJIS.POLL.WHITE}" * empty_bars
            
            voters = []
            if settings['show_voters']:
                voter_records = await interaction.client.db.fetch("""
                    SELECT user_id FROM poll_votes 
                    WHERE poll_id = $1 AND $2 = ANY(choice_ids)
                """, self.poll_id, i)
                voters = [
                    interaction.guild.get_member(record['user_id']).mention
                    for record in voter_records
                    if interaction.guild.get_member(record['user_id'])
                ]
            
            embed.add_field(
                name=f"Option {i}: {choice}",
                value=(
                    f"{bar} {percentage:.1f}% ({votes} votes)\n"
                    + (f"Voters: {', '.join(voters)}\n" if voters else "")
                ),
                inline=True
            )
            
        if poll_data['ends_at']:
            if poll_data['ends_at'] > datetime.now(timezone.utc):
                embed.set_footer(text=f"Poll ends {format_dt(poll_data['ends_at'], 'R')}")
            else:
                embed.set_footer(text="Poll has ended")
                
        return embed

    @discord.ui.button(label="Back to Poll", style=ButtonStyle.secondary)
    async def back_button(self, interaction: Interaction, button: Button):
        poll_embed = await interaction.client.get_cog('Information').create_poll_embed(
            self.poll_id
        )
        poll_view = PollView(self.poll_id)
        await interaction.message.edit(embed=poll_embed, view=poll_view)
        await interaction.response.defer()

class PollView(View):
    def __init__(self, poll_id: UUID):
        super().__init__(timeout=None)
        self.poll_id = poll_id

    async def setup_vote_select(self, interaction: Interaction) -> Optional[PollVoteSelect]:
        poll_data = await interaction.client.db.fetchrow("""
            SELECT * FROM polls WHERE poll_id = $1 AND is_active = true
        """, self.poll_id)
        
        if not poll_data:
            return None
            
        choices = json.loads(poll_data['choices'])
        settings = json.loads(poll_data['settings'])
        
        return PollVoteSelect(
            self.poll_id,
            choices,
            multiple=settings['multiple_choice']
        )

    @discord.ui.button(label="Vote", style=ButtonStyle.primary, custom_id="vote")
    async def vote_button(self, interaction: Interaction, button: Button):
        select = await self.setup_vote_select(interaction)
        if not select:
            return await interaction.response.send_message(
                "This poll has ended.", ephemeral=True
            )
            
        view = View(timeout=60)
        view.add_item(select)
        await interaction.response.send_message(
            "Select your choice(s):", view=view, ephemeral=True
        )

    @discord.ui.button(label="Results", style=ButtonStyle.secondary, custom_id="results")
    async def results_button(self, interaction: Interaction, button: Button):
        results_view = PollResultsView(self.poll_id)
        results_embed = await results_view.generate_results(interaction)
        await interaction.message.edit(embed=results_embed, view=results_view)
        await interaction.response.defer()

class PollChoicesModal(Modal):
    def __init__(self, title: str):
        super().__init__(title="Poll Choices")
        self.poll_title = title
        self.choices = []

        for i in range(1, 6):  
            self.add_item(TextInput(
                label=f"Choice {i}",
                placeholder="Enter a choice...",
                required=i <= 2,
                max_length=100,
                style=TextStyle.short
            ))

    async def on_submit(self, interaction: Interaction):
        self.choices = [item.value for item in self.children if item.value]
        if len(self.choices) < 2:
            await interaction.response.send_message(
                "You must provide at least 2 choices.", ephemeral=True
            )
            return
        await interaction.response.defer()

def parse_duration(duration: str) -> int:
    """Convert duration string to seconds"""
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }
    
    amount = int(duration[:-1])
    unit = duration[-1].lower()
    
    if unit not in units:
        raise ValueError("Invalid duration unit")
        
    return amount * units[unit]