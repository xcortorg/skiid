from discord.ext.commands import (
    Cog,
    command,
    Command,
    Author,
    Group,
    group,
    CommandError,
    CommandConverter,
    Converter,
    Timezone,
    guild_only,
    has_permissions,
    hybrid_command,
    param,
)
from discord import (
    Client,
    Embed,
    Asset,
    Role,
    Message,
    File,
    TextChannel,
    VoiceChannel,
    Status,
    CategoryChannel,
    Invite,
    Member,
    User,
    FFmpegPCMAudio,
    utils,
    Color,
    Guild,
)
from discord.ui import View, Button
from datetime import datetime
from aiohttp import ContentTypeError
from ..lastfm.commands import plural, shorten
from munch import DefaultMunch
from io import BytesIO
from typing import Type, Optional, Union, Literal, List
from lib.classes.color import get_dominant_color, color_info
from lib.classes.lastfm import api_request
from discord.utils import escape_markdown as escape_md, format_dt
from lib.classes.processing import human_timedelta
from lib.classes.builtins import get_error, shorten
from loguru import logger
from asyncio import sleep
from lib.classes.converters import get_timezone
from lib.patch import Context
from lib.classes.flags.screenshot import ScreenshotFlags
from lib.classes.exceptions import NSFWDetection, ConcurrencyLimit
from lib.services.Browser import screenshot
from osu_client import OsuClient
from lib.worker import offloaded
from .util.gif import GIF
from .util.roblox import fetch_roblox_user, get_outfits
from .util.tts import TTS
from .util.cashapp import CashAppProfile
from .util.file import FileProcessing
from .util.xbox import fetch_xbox_profile
from .util.snapchat import PageProps
from .util.steam import Steam
from .util.weather import WeatherResponse
from .util.github import GitHub, Repo
from humanize import intcomma

import aiohttp
import arrow
import random
import pytz
import re


def to_fahrenheit(celsius: float):
    fahrenheit = (celsius * 9.0 / 5.0) + 32.0
    return fahrenheit


def to_mph(ms: float):
    return ms * 2.23694


osu_id = "18969"
osu_secret = "jihfBD7YD0dwHZIr1Gb8Vjo2YQtkQDybrDrjKZ43"
GAMEMODES = ("osu", "taiko", "fruits", "mania")


@offloaded
def get_text(data: bytes):
    from PIL import Image, ImageEnhance
    from io import BytesIO
    import numpy as np
    import cv2
    import pytesseract

    image = Image.open(BytesIO(data))
    grey = image.convert("L")
    enhancer = ImageEnhance.Contrast(grey).enhance(2.5)
    arr = np.array(enhancer)
    binary = cv2.adaptiveThreshold(
        arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
    )
    result = Image.fromarray(binary)
    text = pytesseract.image_to_string(result, config=r"--oem 3 --psm 3")
    if not text.strip():
        return None
    else:
        return text


class CommandorGroup(Converter):
    async def convert(self, ctx: Context, argument: str):
        try:
            command = await CommandConverter().convert(ctx, argument)
            if not command:
                raise CommandError(f"No command found named **{argument[:25]}**")
        except Exception:
            raise CommandError(f"No command found named **{argument[:25]}**")
        return command


DISCORD_FILE_PATTERN = r"(https://|http://)?(cdn\.|media\.)discord(app)?\.(com|net)/(attachments|avatars|icons|banners|splashes)/[0-9]{17,22}/([0-9]{17,22}/(?P<filename>.{1,256})|(?P<hash>.{32}))\.(?P<mime>[0-9a-zA-Z]{2,4})?"


class Image:
    def __init__(self: "Image", fp: bytes, url: str, filename: str):
        self.fp = fp
        self.url = url
        self.filename = filename
        self.gif = GIF(discord=True)

    @property
    def buffer(self: "Image") -> BytesIO:
        buffer = BytesIO(self.fp)
        buffer.name = self.filename

        return buffer

    @classmethod
    async def fallback(cls: Type["Image"], ctx: Context) -> "Image":
        if ref := ctx.message.reference:
            message = await ctx.channel.fetch_message(ref.message_id)
        else:
            message = ctx.message
        if not message.attachments:
            raise CommandError("You must provide an image!")

        attachment = message.attachments[0]
        if not attachment.content_type:
            raise CommandError(
                f"The [attachment]({attachment.url}) provided is invalid!"
            )

        elif not attachment.content_type.startswith("image"):
            raise CommandError(
                f"The [attachment]({attachment.url}) provided must be an image file."
            )

        buffer = await attachment.read()
        return cls(
            fp=buffer,
            url=attachment.url,
            filename=attachment.filename,
        )

    @classmethod
    async def convert(cls: Type["Image"], ctx: Context, argument: str) -> "Image":
        if not (match := re.match(DISCORD_FILE_PATTERN, argument)):
            raise CommandError("The URL provided doesn't match the **Discord** regex!")

        response = await ctx.bot.session.get(match.group())
        if not response.content_type.startswith("image"):
            raise CommandError(f"The [URL]({argument}) provided must be an image file.")

        buffer = await response.read()
        return cls(
            fp=buffer,
            url=match.group(),
            filename=match.group("filename") or match.group("hash"),
        )


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot
        self.osu_api = OsuClient(osu_id, osu_secret)
        self.tts = TTS()
        self.file_processor = FileProcessing(self.bot)

    @command(
        name="reverse",
        aliases=["reversesearch"],
        description="Reverse search an image",
        example=",reverse https://coffin.bot/coffin.png",
    )
    async def reverse(
        self,
        ctx: Context,
        *,
        image: Image = param(
            default=Image.fallback,
            description="The image to search.",
        ),
    ):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    "POST",
                    "https://tineye.com/api/v1/result_json/",
                    params={
                        "sort": "score",
                        "order": "desc",
                    },
                    data={
                        "image": image.fp,
                    },
                ) as response:
                    data = DefaultMunch.fromDict(await response.json())
                    if not data.matches:
                        return await ctx.fail(
                            f"Couldn't find any matches for [`{data.query.hash}`]({image.url})!"
                        )
        except ContentTypeError:
            return await ctx.fail(
                f"Couldn't find any matches for [`this image`]({image.url})!"
            )

        embed = Embed(
            title="Reverse Image Lookup",
            description=(
                f"Found {plural(data.num_matches, md='`'):match|matches} for [`{image.filename}`]({image.url})."
            ),
            color=self.bot.color,
        )

        embed.set_thumbnail(url=image.url)

        for match in data.matches[:4]:
            backlink = match.backlinks[0]

            embed.add_field(
                name=match.domain,
                value=f"[`{shorten(backlink.backlink.replace('https://', '').replace('http://', ''))}`]({backlink.url})",
                inline=False,
            )

        return await ctx.send(embed=embed)

    @command(name="botinfo", description="")
    async def botinfo(self, ctx: Context):
        return await ctx.send("no")

    @hybrid_command(
        name="help",
        description="View extended help for commands",
        example=",help ban",
        with_app_command=True,
    )
    async def help(
        self, ctx: Context, *, command_or_group: Optional[CommandorGroup] = None
    ):
        from lib.patch.help import Help

        h = Help()
        h.context = ctx

        if not command_or_group:
            return await h.send_bot_help(None)

        elif isinstance(command_or_group, Group):
            return await h.send_group_help(command_or_group)
        else:
            return await h.send_command_help(command_or_group)

    async def get_lastfm_status(self, ctx: Context, member: Union[Member, User]):
        if not (
            data := await self.bot.db.fetchrow(
                """
				SELECT * 
				FROM lastfm.config
				WHERE user_id = $1
				""",
                member.id,
            )
        ):
            return ""
        data = await api_request(
            {"user": data.username, "method": "user.getrecenttracks", "limit": 1}
        )
        tracks = data["recenttracks"]["track"]
        lfmemote = self.bot.config["emojis"]["lastfm"]
        if not tracks:
            return ""
        artist = tracks[0]["artist"]["#text"]
        track = tracks[0]["name"]
        nowplaying = tracks[0].get("@attr")
        if nowplaying:
            np = f"\n{lfmemote} Listening to **[{escape_md(track)}](https://last.fm/)** by **{escape_md(artist)}**"
            return np
        else:
            return ""

    @command(
        name="roleinfo",
        example=",roleinfo Friends",
        aliases=[
            "rinfo",
            "ri",
        ],
    )
    async def roleinfo(self, ctx: Context, *, role: Role = None) -> Message:
        """
        View information about a role
        """

        role = role or ctx.author.top_role

        embed = Embed(
            color=role.color,
            title=role.name,
        )
        if isinstance(role.display_icon, Asset):
            embed.set_thumbnail(url=role.display_icon)

        embed.add_field(
            name="Role ID",
            value=f"`{role.id}`",
            inline=True,
        )
        embed.add_field(
            name="Guild",
            value=f"{ctx.guild} (`{ctx.guild.id}`)",
            inline=True,
        )
        embed.add_field(
            name="Color",
            value=f"`{str(role.color).upper()}`",
            inline=True,
        )
        embed.add_field(
            name="Creation Date",
            value=(
                format_dt(role.created_at, style="f")
                + " **("
                + format_dt(role.created_at, style="R")
                + ")**"
            ),
            inline=False,
        )
        embed.add_field(
            name=f"{len(role.members):,} Member(s)",
            value=(
                "No members in this role"
                if not role.members
                else ", ".join([user.name for user in role.members][:7])
                + ("..." if len(role.members) > 7 else "")
            ),
            inline=False,
        )

        return await ctx.send(embed=embed)

    @command(
        name="userinfo",
        aliases=["ui", "user", "whois"],
        description="View information about a member or yourself",
        example=",userinfo @kuzay",
    )
    async def userinfo(
        self, ctx: Context, member: Optional[Union[Member, User]] = Author
    ):
        if not member:
            member = await self.bot.fetch_user(member)

        def format_dt(dt: datetime) -> str:
            return dt.strftime("%m/%d/%Y, %I:%M %p")

        badges = []
        lastfm_status = await self.get_lastfm_status(ctx, member)
        flags = member.public_flags
        footer = ""
        dates = ""

        # for flag in (
        #     "bug_hunter",
        #     "bug_hunter_level_2",
        #     "discord_certified_moderator",
        #     "hypesquad_balance",
        #     "hypesquad_bravery",
        #     "hypesquad_brilliance",
        #     "active_developer",
        #     "early_supporter",
        #     "partner",
        #     "staff",
        #     "verified_bot",
        #     "verified_bot_developer",
        # ):
        #     if getattr(flags, flag, False) is True:
        #         if emoji := self.bot.config["emojis"]["badges"].get(flag):
        #             badges.append(emoji)
        badges = await member.trackcord_badges()

        # vc_status = f"\n{}"
        vc_status = ""
        dates += f"**Created**: {format_dt(member.created_at)} ({utils.format_dt(member.created_at, style = 'R')})"
        embed = Embed(description=f"{badges}{lastfm_status}{vc_status}")
        if isinstance(member, Member):
            dates += f"\n**Joined**: {format_dt(member.joined_at)} ({utils.format_dt(member.joined_at, style='R')})"
            if member.premium_since:
                dates += f"\n**Boosted**: {format_dt(member.premium_since)} ({utils.format_dt(member.premium_since, style='R')})"
        embed.add_field(name="Dates", value=dates, inline=False)
        if isinstance(member, Member):
            position = (
                sorted(ctx.guild.members, key=lambda m: m.joined_at).index(member) + 1
            )
            roles = [
                r for r in member.roles if not r.is_default() and not r.is_integration()
            ]
            roles = sorted(roles, key=lambda x: x.position, reverse=True)
            if len(roles) != 0:
                embed.add_field(
                    name=f"Roles ({len(roles)})",
                    value=", ".join(m.mention for m in roles) + "...",
                )
            footer += f"Join position: {position} ∙ "

        footer += f"{plural(len(member.mutual_guilds) or 0):mutual server}"
        embed.set_footer(text=footer)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(
            name=f"{str(member)} ({member.id})",
            icon_url=member.display_avatar.url,
            url=f"discord://-/users/{member.id}",
        )
        return await ctx.send(embed=embed)

    @command(
        name="channelinfo",
        example=",channelinfo #general",
        aliases=[
            "cinfo",
            "ci",
        ],
    )
    async def channelinfo(
        self,
        ctx: Context,
        *,
        channel: Optional[Union[TextChannel, VoiceChannel, CategoryChannel]] = None,
    ) -> Message:
        """
        View information about a channel
        """

        channel = channel or ctx.channel
        if not isinstance(
            channel,
            (TextChannel, VoiceChannel, CategoryChannel),
        ):
            return await ctx.send_help()

        embed = Embed(title=channel.name)

        embed.add_field(
            name="Channel ID",
            value=f"`{channel.id}`",
            inline=True,
        )
        embed.add_field(
            name="Type",
            value=f"`{channel.type}`",
            inline=True,
        )
        embed.add_field(
            name="Guild",
            value=f"{ctx.guild} (`{ctx.guild.id}`)",
            inline=True,
        )

        if category := channel.category:
            embed.add_field(
                name="Category",
                value=f"{category} (`{category.id}`)",
                inline=False,
            )

        if isinstance(channel, TextChannel) and channel.topic:
            embed.add_field(
                name="Topic",
                value=channel.topic,
                inline=False,
            )

        elif isinstance(channel, VoiceChannel):
            embed.add_field(
                name="Bitrate",
                value=f"{int(channel.bitrate / 1000)} kbps",
                inline=False,
            )
            embed.add_field(
                name="User Limit",
                value=(channel.user_limit or "Unlimited"),
                inline=False,
            )

        elif isinstance(channel, CategoryChannel) and channel.channels:
            embed.add_field(
                name=f"{len(channel.channels)} Children",
                value=", ".join([child.name for child in channel.channels]),
                inline=False,
            )

        embed.add_field(
            name="Creation Date",
            value=(
                format_dt(channel.created_at, style="f")
                + " **("
                + format_dt(channel.created_at, style="R")
                + ")**"
            ),
            inline=False,
        )

        return await ctx.send(embed=embed)

    @command(
        name="inviteinfo",
        example=",inviteinfo coffin",
        aliases=[
            "ii",
        ],
    )
    async def inviteinfo(self, ctx: Context, invite: Invite) -> Message:
        """
        View basic invite code information
        """

        embed = Embed(title=f"Invite Code: {invite.code}")
        embed.set_thumbnail(url=invite.guild.icon)

        embed.add_field(
            name="Channel & Invite",
            value=(
                f"**Name:** {invite.channel.name} (`{invite.channel.type}`)\n"
                f"**ID:** `{invite.channel.id}`\n"
                "**Created:** "
                + format_dt(
                    invite.channel.created_at,
                    style="f",
                )
                + "\n"
                "**Invite Expiration:** "
                + (
                    format_dt(
                        invite.expires_at,
                        style="R",
                    )
                    if invite.expires_at
                    else "Never"
                )
                + "\n"
                "**Inviter:** Unknown\n"
                "**Temporary:** N/A\n"
                "**Usage:** N/A"
            ),
            inline=True,
        )
        embed.add_field(
            name="Guild",
            value=(
                f"**Name:** {invite.guild.name}\n"
                f"**ID:** `{invite.guild.id}`\n"
                "**Created:** "
                + format_dt(
                    invite.guild.created_at,
                    style="f",
                )
                + "\n"
                f"**Members:** {invite.approximate_member_count:,}\n"
                f"**Members Online:** {invite.approximate_presence_count:,}\n"
                f"**Verification Level:** {invite.guild.verification_level.name.title()}"
            ),
            inline=True,
        )

        view = View()
        for button in [
            Button(
                emoji=emoji,
                label=key,
                url=asset.url,
            )
            for emoji, key, asset in [
                ("🖼", "Icon", invite.guild.icon),
                ("🎨", "Splash", invite.guild.splash),
                ("🏳", "Banner", invite.guild.banner),
            ]
            if asset
        ]:
            view.add_item(button)

        return await ctx.send(embed=embed, view=view)

    @group(
        name="boosters",
        invoke_without_command=True,
    )
    async def boosters(self, ctx: Context) -> Message:
        """
        View all recent server boosters
        """

        if not (
            members := sorted(
                filter(
                    lambda member: member.premium_since,
                    ctx.guild.members,
                ),
                key=lambda member: member.premium_since,
                reverse=True,
            )
        ):
            return await ctx.fail("No **members** are currently boosting!")

        return await ctx.paginate(
            Embed(
                title="Current boosters",
            ),
            [
                (
                    f"**{member}** boosted "
                    + format_dt(
                        member.premium_since,
                        style="R",
                    )
                )
                for member in members
            ],
        )

    @boosters.command(
        name="lost",
    )
    async def boosters_lost(self, ctx: Context) -> Message:
        """
        View list of most recent lost boosters
        """

        if not (
            boosters_lost := await self.bot.db.fetch(
                """
			SELECT *
			FROM boosters_lost
			ORDER BY expired_at DESC
			"""
            )
        ):
            return await ctx.fail("No **boosters** have been lost recently!")

        return await ctx.paginate(
            Embed(
                title="Recently lost boosters",
            ),
            [
                (
                    f"**{user}** stopped "
                    + format_dt(
                        row["expired_at"],
                        style="R",
                    )
                    + " (lasted "
                    + human_timedelta(
                        row["started_at"], accuracy=1, brief=True, suffix=False
                    )
                    + ")"
                )
                for row in boosters_lost
                if (user := self.bot.get_user(row["user_id"]))
            ],
        )

    @command(
        name="invites",
    )
    @has_permissions(manage_guild=True)
    async def invites(self, ctx: Context) -> Message:
        """
        View all active invites
        """

        if not (
            invites := sorted(
                await ctx.guild.invites(),
                key=lambda invite: invite.expires_at,
                reverse=True,
            )
        ):
            return await ctx.fail("No **active invites** found")

        return await ctx.paginate(
            Embed(
                title="Server invites",
            ),
            [
                (
                    f"[**{invite.code}**]({invite.url}) expires "
                    + format_dt(
                        invite.expires_at,
                        style="R",
                    )
                )
                for invite in invites
            ],
        )

    @command(
        name="roles",
    )
    async def roles(self, ctx: Context) -> Message:
        """
        View all roles in the server
        """

        if not (roles := reversed(ctx.guild.roles[1:])):
            return await ctx.fail("No **roles** found")

        return await ctx.paginate(
            Embed(title="List of roles"),
            [
                r.mention
                for r in sorted(
                    [role for role in roles], key=lambda x: x.position, reverse=True
                )
            ],
        )

    @command(
        name="membercount",
        aliases=["mc", "memberc", "usercount", "uc"],
        description="View server member count",
    )
    async def membercount(self, ctx: Context) -> Message:
        def num(number: int):
            return "{:,}".format(number)

        joins = (
            await self.bot.db.fetchval(
                """SELECT joins FROM statistics.member_count WHERE guild_id = $1""",
                ctx.guild.id,
            )
            or 0
        )
        try:
            if joins > 0:
                joins = f"+{joins}"
            else:
                joins = f"-{joins}"
        except Exception:
            joins = "+0"
        embed = Embed(color=self.bot.color)
        inline = True
        embed.add_field(
            name=f"**Users({joins})**",
            value=num(int(len([m for m in ctx.guild.members]))),
            inline=inline,
        )
        embed.add_field(
            name="**Humans**",
            value=num(int(len([m for m in ctx.guild.members if not m.bot]))),
            inline=inline,
        )
        embed.add_field(
            name="**Bots**",
            value=num(int(len([m for m in ctx.guild.members if m.bot]))),
            inline=inline,
        )
        embed.set_author(name=f"{ctx.guild.name}'s statistics", icon_url=ctx.guild.icon)
        return await ctx.send(embed=embed)

    @command(
        name="bots",
    )
    async def bots(self, ctx: Context) -> Message:
        """
        View all bots in the server
        """

        if not (
            bots := filter(
                lambda member: member.bot,
                ctx.guild.members,
            )
        ):
            return await ctx.fail("No **bots** found")

        return await ctx.paginate(
            Embed(title="List of bots"), [f"**{bot}**" for bot in bots]
        )

    @command(
        name="members",
        example=",members Friends",
        aliases=["inrole"],
    )
    async def members(self, ctx: Context, *, role: Role = None) -> Message:
        """
        View members in a role
        """

        role = role or ctx.author.top_role

        if not role.members:
            return await ctx.fail(f"No **members** have {role.mention}")

        return await ctx.paginate(
            Embed(
                title=f"Members in {role}",
            ),
            [
                (
                    f"**{member}**"
                    + (" (you)" if member == ctx.author else "")
                    + (" (BOT)" if member.bot else "")
                )
                for member in role.members
            ],
        )

    @command(
        name="avatar",
        example=",avatar jonathan",
        aliases=[
            "av",
            "avi",
            "pfp",
            "ab",
            "ag",
        ],
        information={"note": "User ID available"},
    )
    async def avatar(
        self, ctx: Context, *, user: Optional[Union[Member, User]] = None
    ) -> Message:
        """
        Get avatar of a member or yourself
        """

        user = user or ctx.author

        return await ctx.send(
            embed=Embed(
                url=(user.avatar or user.default_avatar),
                title=f"{user.name}'s avatar",
            ).set_image(url=(user.avatar or user.default_avatar))
        )

    @command(name="color", description="", example=",color purple")
    async def color(
        self, ctx: Context, *, query: Optional[Union[str, User, Member]] = None
    ):
        try:
            if isinstance(query, User):
                _ = await get_dominant_color(query)
                logger.info(_)
            elif isinstance(query, Member):
                _ = await get_dominant_color(query)
                logger.info(_)
            else:
                if query is None:
                    if len(ctx.message.attachments) > 0:
                        _ = await get_dominant_color(ctx.message.attachments[0].url)
                    else:
                        d = await self.bot.get_image(ctx, query)
                        if d is None:
                            return await ctx.send_help()
                        _ = await get_dominant_color(d)
                else:
                    if query.startswith("http"):
                        _ = await get_dominant_color(query)
                    else:
                        _ = query
            return await color_info(ctx, _)
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            return await ctx.send_help()

    @command(
        name="serveravatar",
        example=",serveravatar jonathan",
        aliases=[
            "sav",
            "savi",
            "spfp",
            "serverav",
            "gav",
            "guildav",
        ],
        information={"note": "User ID available"},
    )
    async def serveravatar(self, ctx: Context, *, member: Member = None) -> Message:
        """
        Get the server avatar of a member or yourself
        """

        member = member or ctx.author
        if not member.guild_avatar:
            return await ctx.fail(
                "You don't have a **server avatar** set!"
                if member == ctx.author
                else f"**{member}** doesn't have a **server avatar** set!"
            )

        return await ctx.send(
            embed=Embed(
                url=member.guild_avatar,
                title=f"{member.name}'s server avatar",
            ).set_image(url=member.guild_avatar)
        )

    @command(
        name="banner",
        example=",banner jonathan",
        aliases=[
            "ub",
            "userbanner",
        ],
        extras={"note": "User ID available"},
    )
    async def banner(
        self, ctx: Context, *, user: Optional[Union[Member, User]] = None
    ) -> Message:
        """
        Get the banner of a member or yourself
        """

        if not isinstance(user, User):
            user = await self.bot.fetch_user(user.id if user else ctx.author.id)

        banner_url = (
            user.banner
            if user.banner
            else (
                "https://singlecolorimage.com/get/"
                + str(user.accent_color or Color(0)).replace("#", "")
                + "/400x100"
            )
        )

        return await ctx.send(
            embed=Embed(
                url=banner_url,
                title=f"{user.name}'s banner",
            ).set_image(url=banner_url)
        )

    @command(
        name="icon",
        example=",icon 1115389989..",
        aliases=[
            "servericon",
            "guildicon",
            "sicon",
            "gicon",
        ],
        extras={"note": "Server ID & Invite available"},
    )
    async def icon(
        self, ctx: Context, *, guild: Optional[Union[Guild, Invite]] = None
    ) -> Message:
        """
        Returns guild icon
        """

        if isinstance(guild, Invite):
            guild = guild.guild
        else:
            guild = guild or ctx.guild

        if not guild.icon:
            return await ctx.fail("No **server icon** is set!")

        return await ctx.send(
            embed=Embed(
                url=guild.icon,
                title=f"{guild.name}'s icon",
            ).set_image(url=guild.icon)
        )

    # @command(
    # 	name="guildbanner",
    # 	example=",guildbanner 1115389989..",
    # 	aliases=[
    # 		"serverbanner",
    # 		"gbanner",
    # 		"sbanner",
    # 	],
    # 	extras={"note": "Server ID & Invite available"},
    # )
    # async def guildbanner(
    # 	self, ctx: Context, *, guild: Optional[Union[Guild, Invite]] = None
    # ) -> Message:
    # 	"""
    # 	Returns guild banner
    # 	"""

    # 	if isinstance(guild, Invite):
    # 		guild = guild.guild
    # 	else:
    # 		guild = guild or ctx.guild

    # 	if not guild.banner:
    # 		return await ctx.fail("No **server banner** is set!")

    # 	return await ctx.send(
    # 		embed=Embed(
    # 			url=guild.banner,
    # 			title=f"{guild.name}'s guild banner",
    # 		).set_image(url=guild.banner)
    # 	)

    # @command(
    # 	name="splash",
    # 	example=",splash 1115389989..",
    # 	extras={"note": "Server ID & Invite available"},
    # )
    # async def splash(
    # 	self, ctx: Context, *, guild: Optional[Union[Guild, Invite]] = None
    # ) -> Message:
    # 	"""
    # 	Returns splash background
    # 	"""

    # 	if isinstance(guild, Invite):
    # 		guild = guild.guild
    # 	else:
    # 		guild = guild or ctx.guild

    # 	if not guild.splash:
    # 		return await ctx.fail("No **server splash** is set!")

    # 	return await ctx.send(
    # 		embed=Embed(
    # 			url=guild.splash,
    # 			title=f"{guild.name}'s guild splash",
    # 		).set_image(url=guild.splash)
    # 	)

    @command(
        name="serverinfo",
        example=",serverinfo 1115389989..",
        aliases=[
            "guildinfo",
            "sinfo",
            "ginfo",
            "si",
            "gi",
        ],
    )
    async def serverinfo(self, ctx: Context, *, guild: Guild = None) -> Message:
        """
        View information about a guild
        """

        guild = guild or ctx.guild

        embed = Embed(
            title=guild.name,
            description=(
                "Server created on "
                + (
                    format_dt(guild.created_at, style="D")
                    + " **("
                    + format_dt(guild.created_at, style="R")
                    + ")**"
                )
                + f"\n__{guild.name}__ is on bot shard ID: **{guild.shard_id}/{self.bot.shard_count}**"
            ),
            timestamp=guild.created_at,
        )
        embed.set_thumbnail(url=guild.icon)

        embed.add_field(
            name="Owner",
            value=(guild.owner or guild.owner_id),
            inline=True,
        )
        embed.add_field(
            name="Members",
            value=(
                f"**Total:** {guild.member_count:,}\n"
                f"**Humans:** {len([m for m in guild.members if not m.bot]):,}\n"
                f"**Bots:** {len([m for m in guild.members if m.bot]):,}"
            ),
            inline=True,
        )
        embed.add_field(
            name="Information",
            value=(
                f"**Verification:** {guild.verification_level.name.title()}\n"
                f"**Level:** {guild.premium_tier}/{guild.premium_subscription_count:,} boosts"
            ),
            inline=True,
        )
        embed.add_field(
            name="Design",
            value=(
                f"**Banner:** "
                + (f"[Click here]({guild.banner})\n" if guild.banner else "N/A\n")
                + f"**Splash:** "
                + (f"[Click here]({guild.splash})\n" if guild.splash else "N/A\n")
                + f"**Icon:** "
                + (f"[Click here]({guild.icon})\n" if guild.icon else "N/A\n")
            ),
            inline=True,
        )
        embed.add_field(
            name=f"Channels ({len(guild.channels)})",
            value=f"**Text:** {len(guild.text_channels)}\n**Voice:** {len(guild.voice_channels)}\n**Category:** {len(guild.categories)}\n",
            inline=True,
        )
        embed.add_field(
            name="Counts",
            value=(
                f"**Roles:** {len(guild.roles)}/250\n"
                f"**Emojis:** {len(guild.emojis)}/{guild.emoji_limit}\n"
                f"**Boosters:** {len(guild.premium_subscribers):,}\n"
            ),
            inline=True,
        )

        if guild.features:
            embed.add_field(
                name="Features",
                value=(
                    "```\n"
                    + ", ".join(
                        [
                            feature.replace("_", " ").title()
                            for feature in guild.features
                        ]
                    )
                    + "```"
                ),
                inline=False,
            )

        embed.set_footer(text=f"Guild ID: {guild.id}")

        return await ctx.send(embed=embed)

    @command(
        name="screenshot",
        description="screenshot a webpage",
        example=",screenshot https://google.com --wait 3",
        aliases=["ss"],
    )
    async def screenshot(self, ctx: Context, url: str, *, flags: ScreenshotFlags):
        kwargs = {}
        safe = True if not ctx.channel.is_nsfw() else False
        message = await ctx.normal("Please wait while we fulfill this request...")
        if flags.wait:
            kwargs["wait"] = flags.wait

        if flags.wait_for:
            kwargs["wait_until"] = flags.wait_for

        if flags.full_page:
            kwargs["full_page"] = flags.full_page
        async with aiohttp.ClientSession() as session:
            async with session.request(
                "HEAD", f"https://{url.replace('https://', '').replace('http://', '')}"
            ) as response:
                if int(
                    response.headers.get("Content-Length", 5)
                ) > 52428800 or url.endswith(".txt"):
                    raise CommandError("Content Length Too Large")
        try:
            ss = await screenshot(url, safe, **kwargs)
            embed = Embed(
                title=f"{url.split('://')[1] if '://' in url else url}",
                url=f"https://{url.split('://')[1] if '://' in url else url}",
            ).set_image(url="attachment://screenshot.png")
            return await message.edit(attachments=[ss], embed=embed)
        except NSFWDetection as e:
            embed = await ctx.fail(str(e), return_embed=True)
            return await message.edit(embed=embed)
        except ConcurrencyLimit as e:
            embed = await ctx.fail(str(e), return_embed=True)
            return await message.edit(embed=embed)

    @command(
        name="osu",
        description="Retrieve simple OSU! profile information",
        example=",osu babyxgwen taiko",
    )
    async def osu(self, ctx: Context, username: str, gamemode: Optional[str] = None):
        kwargs = {}
        if gamemode:
            if gamemode.lower() not in GAMEMODES:
                raise CommandError(
                    f"Valid gamemodes are {', '.join(f'`{g}`' for g in GAMEMODES)}"
                )
            else:
                kwargs["gamemode"] = gamemode.lower()
        try:
            user = await self.osu_api.get_user(username, **kwargs)
            if not user or not user.join_date:
                raise CommandError(f"no osu profile named **{username}**")
            embed = Embed(
                title=username,
                color=self.bot.color,
                url=f"https://osu.ppy.sh/users/{username}",
            )
            embed.add_field(
                name="Joined",
                value=utils.format_dt(arrow.get(user.join_date).datetime, style="R"),
                inline=True,
            )
            embed.add_field(
                name="Seen",
                value=(
                    utils.format_dt(arrow.get(user.last_visit).datetime, style="R")
                    if user.last_visit
                    else "N/A"
                ),
                inline=True,
            )
            embed.add_field(
                name="Rank",
                value=f"{f'#{intcomma(user.statistics.global_rank)}' if user.statistics.global_rank else 'N/A'}",
                inline=True,
            )
            embed.add_field(
                name="Level", value=user.statistics.level.current, inline=True
            )
            embed.add_field(
                name="Max Combo", value=f"{user.statistics.maximum_combo}x", inline=True
            )
            embed.add_field(
                name="Play Time",
                value=f"{round(user.statistics.play_time / 60 / 60, 2)} hours",
                inline=True,
            )
            embed.set_footer(
                text="osu",
                icon_url="https://upload.wikimedia.org/wikipedia/commons/1/1e/Osu%21_Logo_2016.svg",
            )
            embed.set_author(
                name=str(ctx.author), icon_url=ctx.author.display_avatar.url
            )
            return await ctx.send(embed=embed)
        except Exception as e:
            raise e

    @command(
        name="define",
        description="Get definition of a word",
        aliases=["oxford"],
        example=",define dictionary",
    )
    async def define(self, ctx: Context, word: str):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.rival.rocks/oxford",
                    params={"word": word, "type": "english"},
                    headers={"api-key": self.bot.config["Authorization"]["rival_api"]},
                ) as f:
                    data = await f.json(content_type=None)
            if data.get("word") is None:
                raise CommandError(f"no definition found for **{word}**")
            if not data.get("wordtype"):
                raise CommandError(f"no definition found for **{word}**")
            word = data["word"]
            kind = data["wordtype"]
            definitions_embed = Embed(colour=self.bot.color)
            definitions_embed.description = ""
            definitions_embed.set_author(
                name=word, icon_url="https://i.imgur.com/vDvSmF3.png"
            )
            definitions_embed.add_field(
                name=kind,
                value=data["definition"],
                inline=False,
            )
            await ctx.send(embed=definitions_embed)
        except Exception as e:
            logger.info(f"define raised {e} - {get_error(e)}")
            raise CommandError(f"no definition found for **{word}**")

    @command(
        name="urbandictionary",
        aliases=["ud", "urban"],
        description="Gets the definition of a word/slang from Urban Dictionary",
        example=",urbandictionary footjob",
    )
    async def urbandictionary(self, ctx: Context, *, word: str):
        try:
            url = "https://api.urbandictionary.com/v0/define"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params={"term": word}) as response:
                    data = await response.json()
            pages = []
            if data["list"]:
                for i, entry in enumerate(data["list"], start=1):
                    definition = (
                        entry["definition"].replace("]", "**").replace("[", "**")
                    )
                    example = entry["example"].replace("]", "**").replace("[", "**")
                    timestamp = entry["written_on"]
                    content = Embed(
                        title=entry["word"],
                        url=entry["permalink"],
                        colour=Color.from_rgb(254, 78, 28),
                    )
                    content.description = f"{definition}"
                    if not example == "":
                        content.add_field(name="Example", value=example)
                    content.add_field(
                        name="Votes",
                        value=f"👍 `{entry.get('thumbs_up', 0)} / {entry.get('thumbs_down', 0)}`👎",
                        inline=False,
                    )
                    content.set_footer(
                        text=f"Page {i}/{len(data['list'])} • by {entry['author']}",
                        icon_url="https://cdn.notsobot.com/brands/urban-dictionary.png",
                    )
                    content.timestamp = arrow.get(timestamp).datetime
                    content.set_author(
                        name=entry["word"],
                        icon_url="https://i.imgur.com/yMwpnBe.png",
                        url=entry.get("permalink"),
                    )
                    pages.append(content)
                return await ctx.paginate(pages)
            else:
                raise CommandError(f"No **definition** for `{word}`")
        except Exception:
            raise CommandError(f"No **definition** for `{word}`")

    async def get_image(self, url: str):
        url = (
            f"https://proxy.rival.rocks?url={url}"
            if "discordapp.com" not in url or "discord.com" not in url
            else url
        )
        async with aiohttp.ClientSession() as session:
            async with session.request("HEAD", url) as req:
                if (
                    "image" in req.headers["Content-Type"].lower()
                    and int(req.headers.get("Content-Length", 50000)) < 50000000
                ):
                    async with session.request("GET", url) as response:
                        return await response.read()
                else:
                    raise CommandError(f"Image URL {url} is invalid")

    @command(name="ocr", description="Detects text in an image")
    @has_permissions(attach_files=True)
    async def ocr(self, ctx: Context, url: Optional[str] = None):
        if not url:
            if reference := ctx.message.reference:
                if message := await ctx.fetch_message(reference.message_id):
                    if message.attachments:
                        url = message.attachments[0].url
            elif ctx.message.attachments:
                url = ctx.message.attachments[0].url
            else:
                raise CommandError("No image attached")
        data = await self.get_image(url)
        text = await get_text(data)
        if text:
            if ctx.author.mobile_status != Status.offline:
                return await ctx.send(f"```{text[:-1]}```")
            else:
                return await ctx.success(f"```{text[:-1]}```")

    @command(
        name="makegif",
        aliases=["creategif", "cg", "mg"],
        description="Convert videos into a GIF",
    )
    @has_permissions(attach_files=True)
    async def makegif(
        self,
        ctx: Context,
        url: Optional[str] = None,
        quality: Optional[int] = None,
        fps: Optional[int] = None,
        fast_forward: Optional[int] = None,
    ):
        kwargs = {}
        if quality:
            kwargs["quality"] = quality
        if fps:
            kwargs["fps"] = fps
        if fast_forward:
            kwargs["fast_forward"] = fast_forward
        if not url:
            if reference := ctx.message.reference:
                if message := await ctx.fetch_message(reference.message_id):
                    if message.attachments:
                        url = message.attachments[0].url
            elif ctx.message.attachments:
                url = ctx.message.attachments[0].url
            else:
                raise CommandError("No image attached")
        return await self.gif.do_conversion(ctx, url, **kwargs)

    @command(name="ping", description="view the bot's latency")
    async def ping(self, ctx: Context):
        messages = [
            "it took `putlatencyherems` to ping **your mom's basement**",
            "it took `putlatencyherems` to ping **troy's family**",
            "it took `putlatencyherems` to ping **jitcoin api**",
            "it took `putlatencyherems` to ping **rival's vps**",
            "it took `putlatencyherems` to ping **haunt's vps**",
            "it took `putlatencyherems` to ping **ur step sis**",
            "it took `putlatencyherems` to ping **localhost**",
            "it took `putlatencyherems` to ping **twitter**",
            "it took `putlatencyherems` to ping **your house**",
            "it took `putlatencyherems` to ping **alexa**",
            "it took `putlatencyherems` to ping **a connection to the server**",
            "it took `putlatencyherems` to ping **@cop on discord**",
            "it took `putlatencyherems` to ping **rival**",
            "it took `putlatencyherems` to ping **some bitches**",
            "it took `putlatencyherems` to ping **@cop-discord on github**",
            "it took `putlatencyherems` to ping **a bot**",
            "it took `putlatencyherems` to ping **the database**",
        ]
        msg = random.choice(messages)
        ran = random.randrange(1, 4)
        msg = msg.replace(
            "putlatencyhere", str(11 + ran)
        )  # str(round(self.bot.latency*1000)))
        message = await ctx.send(content=f"{msg}")
        await sleep(0.1)
        rand = random.randrange(30, 110)
        await message.edit(content=f"{msg} (edit: `{15+rand}ms`)")

    async def do_tts(self, message: str, model: Optional[str] = "amy") -> str:
        try:
            return await self.tts.tts_api(model, "en_US", "low", message)
        except Exception as e:
            from aiogtts import aiogTTS  # type: ignore

            i = BytesIO()
            aiogtts = aiogTTS()
            await aiogtts.save(message, ".tts.mp3", lang="en")
            await aiogtts.write_to_fp(message, i, slow=False, lang="en")
            return ".tts.mp3"

    @command(
        name="texttospeech", aliases=["tts"], description="speak thru the bot in vc"
    )
    async def texttospeech(
        self,
        ctx,
        model: Optional[
            Literal[
                "amy",
                "danny",
                "arctic",
                "hfc_female",
                "hfc_male",
                "joe",
                "kathleen",
                "kusal",
                "lessac",
                "ryan",
            ]
        ] = "joe",
        *,
        ttstext: str,
    ):
        fp = await self.do_tts(ttstext, model)
        if ctx.voice_client is None:
            if ctx.author.voice is not None:
                vc = await ctx.author.voice.channel.connect()
            else:
                try:
                    msg = await self.file_processor.upload_to_discord(ctx.channel, fp)
                    await self.tts.delete_soon(fp.replace(".mp3", ".ogg"), 3)
                    await self.tts.delete_soon(fp, 3)
                    return msg
                except Exception:
                    await self.tts.delete_soon(fp, 3)
                    return await ctx.send(file=File(fp))

        else:
            vc = ctx.voice_client
        try:
            await ctx.message.add_reaction("🗣️")
        except Exception:
            pass
        vc.play(FFmpegPCMAudio(source=fp))
        while vc.is_playing():
            await sleep(1)
        await ctx.message.add_reaction("🙊")
        await self.tts.delete_soon(fp, 3)

    @group(
        name="roblox",
        aliases=["rb", "rblx"],
        description="",
        example=",roblox mooncricketslayer09",
        invoke_without_command=True,
    )
    async def roblox(self, ctx: Context, username: str):
        try:
            data = await fetch_roblox_user(username)
            if not data:
                raise TypeError()
        except Exception as e:
            if ctx.author.name == "aiohttp":
                raise e
            if isinstance(e, TypeError):
                raise CommandError(f"invalid roblox user **{username}**")
            else:
                raise CommandError(
                    "API is currently **ratelimited** please try again later"
                )
        e = Embed(color=self.bot.color)
        e.title = username
        e.url = f"https://www.roblox.com/users/{data.id}/profile"
        formatted_ts = f"<t:{int(data.created.timestamp())}:R>"
        if data.last_online is not None:
            e.add_field(
                name="Last Online",
                value=f"<t:{int(data.last_online.timestamp())}:R>",
                inline=True,
            )
        e.description = data.description
        e.add_field(name="Friends", value=data.friend_count.humanize(), inline=True)
        e.add_field(
            name="Following",
            value=data.following_count.humanize(),
            inline=True,
        )
        e.add_field(
            name="Followers",
            value=data.follower_count.humanize(),
            inline=True,
        )
        e.add_field(name="Created", value=formatted_ts, inline=False)
        e.set_footer(
            text=f"ID: {data.id}",
            icon_url="http://static.wikia.nocookie.net/ipod/images/5/59/Roblox.png/",
        )
        e.set_thumbnail(url=data.avatar_url)
        return await ctx.send(embed=e)

    @roblox.command(
        name="outfits",
        aliases=["fits"],
        description="View a roblox user's outfits",
        example=",roblox outfits mooncricketslayer09",
    )
    async def roblox_outfits(self, ctx: Context, username: str):
        try:
            outfits = await get_outfits(username)
        except Exception:
            return await ctx.search(f"`{username}` has no **outfits**")
        base = Embed(
            title=f"{username}'s Outfits",
            url=f"https://www.roblox.com/users/{outfits.user_id}/profile",
        ).set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embeds: List[Embed] = []
        for i, outfit in enumerate(outfits.data):
            embed = base.copy()
            embed.set_image(url=outfit.thumbnail)
            embed.set_footer(text=f"Page {i}/{len(outfits.data)}")
            embeds.append(embed)
        return await ctx.paginate(embeds)

    @command(
        name="weather",
        description="Gets simple weather from OpenWeatherMap",
        example=",weather los angeles",
    )
    async def weather(self, ctx: Context, *, city: str):
        try:
            city = await WeatherResponse.from_city(city)
        except Exception:
            raise CommandError(f"City `{city}` **not found**")
        city = city.data
        embed = Embed(
            title=f"{'Weather' if not city.weather else city.weather[0].description.title()} in {city.name}, {city.sys.country}"
        )
        embed.add_field(
            name="Temperature",
            value=f"{round(city.main.temp, 2)} °C / {round(to_fahrenheit(city.main.temp), 2)} °F",
            inline=True,
        )
        embed.add_field(
            name="Wind", value=f"{round(to_mph(city.wind.speed), 2)} mph", inline=True
        )
        embed.add_field(name="Humidity", value=f"{city.main.humidity}%", inline=True)
        embed.add_field(name="Sun Rise", value=f"<t:{city.sys.sunrise}:R>", inline=True)
        embed.add_field(name="Sun Set", value=f"<t:{city.sys.sunset}:R>", inline=True)
        embed.add_field(
            name="Visibility",
            value=f"{city.visibility / 1000}km / {int((city.visibility / 1000) * 1609.34)}m",
            inline=True,
        )
        embed.set_thumbnail(
            url=f"https://openweathermap.org/img/w/{city.weather[0].icon}"
        )
        return await ctx.send(embed=embed)

    @command(
        name="cashapp",
        aliases=["cash", "ca"],
        description="Retrieve simple CashApp profile information",
        example=",cashapp meow",
    )
    async def cashapp(self, ctx: Context, cashtag: str):
        cashtag = cashtag.replace("$", "")
        try:
            profile = await CashAppProfile.from_cashtag(cashtag)
        except Exception:
            raise CommandError(
                f"[`${cashtag}`](https://cash.app/${cashtag}) was **not found**"
            )
        embed = Embed(
            title=f"{profile.display_name} (@{cashtag}) {'☑️' if profile.is_verified_account else ''}",
            url=f"https://cash.app/${cashtag}",
            description=f"Pay [${cashtag}](https://cash.app/{cashtag}) here",
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        avatar = None
        if profile.avatar:
            if profile.avatar.image_url:
                avatar = profile.avatar.image_url
        embed.set_thumbnail(
            url=avatar
            or "https://www.shutterstock.com/image-vector/avatar-photo-default-user-icon-600nw-2345549599.jpg"
        )
        embed.set_footer(
            text="CashApp.",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/Square_Cash_app_logo.svg/1200px-Square_Cash_app_logo.svg.png",
        )
        return await ctx.send(embed=embed)

    @command(
        name="xbox",
        aliases=["xb"],
        description="Gets profile information on the given Xbox gamertag",
        example=",xbox jon",
    )
    async def xbox(self, ctx: Context, gamertag: str):
        profile = await fetch_xbox_profile(gamertag)
        profile = profile.data.player
        embed = Embed(
            title=f"{profile.username}",
            url=f"https://xboxgamertag.com/search/{profile.username}",
            color=Color.from_str("#cabda8"),
        )
        embed.add_field(
            name="Tenure Level", value=f"{profile.meta.tenureLevel}", inline=True
        )
        embed.add_field(
            name="Gamerscore", value=profile.meta.gamerscore.humanize(), inline=True
        )
        embed.add_field(
            name="Account Tier", value=profile.meta.accountTier, inline=True
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.set_footer(
            text="Xbox",
            icon_url="https://upload.wikimedia.org/wikipedia/commons/thumb/f/f9/Xbox_one_logo.svg/1200px-Xbox_one_logo.svg.png",
        )
        if profile.avatar:
            embed.set_image(url=profile.avatar)
        return await ctx.send(embed=embed)

    @command(
        name="steam",
        description="Get information about a steam profile",
        example=",steam jon",
    )
    async def steam(self, ctx: Context, username: str):
        try:
            profile = await Steam.from_username(username)
        except Exception:
            raise CommandError(
                f"[`{username}`](https://steamcommunity.com/id/{username}) is an invalid **Steam** user"
            )
        data = profile.data
        embed = Embed(
            url=data.player.meta.profileurl,
            title=data.player.username,
            description=f"💬{shorten(data.player.bio, 45)}\n**Registered**: <t:{data.player.meta.timecreated}:R>",
        )
        embed.set_thumbnail(url=data.player.meta.avatarfull)
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.add_field(
            name="IDs",
            value=f"**URL**: {data.meta.profileurl.split('/')[-2]}\n**ID64**: {data.player.meta.steam64id}",
        )
        return await ctx.send(embed=embed)

    @command(
        name="github",
        aliases=["gh"],
        description="Gets profile information on the given Github user",
        example=",github cop-discord",
    )
    async def github(self, ctx: Context, username: str):
        try:
            data = await GitHub.from_username(username)
        except Exception:
            raise CommandError(
                f"[{username}](https://github.com/{username}) is an invalid **GitHub** account"
            )
        embed = Embed()
        embed.set_footer(
            text=f"Created on • {data.created_at.strftime('%m/%d/%Y %I:%M %p')}",
            icon_url=f"https://cdn.discordapp.com/emojis/843537056541442068.png",
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        if data.location:
            location = (
                f"\n🌎[{data.location}](http://maps.google.com/?q={data.location})"
            )
        else:
            location = ""
        repos = sorted(data.repos, key=lambda x: x.created_at, reverse=True)

        def to_content(repo: Repo) -> str:
            return f"[`:star: {repo.stargazers_count}, {repo.created_at.strftime('%m/%d/%Y')} {repo.name}`]({repo.svn_url})"

        embed.add_field(name="Information", value=f"{data.bio}{location}", inline=False)
        embed.add_field(
            name=f"Repositories ({len(data.repos)})",
            value=f"{'\n'.join(to_content(f) for f in repos[:3])}",
            inline=False,
        )
        return await ctx.send(embed=embed)

    @command(
        name="snapchatstory",
        description="Gets all current stories for the given Snapchat user",
        example=",snapchatstory jon",
    )
    async def snapchatstory(self, ctx: Context, username: str):
        try:
            user = await PageProps.from_username(username)
        except Exception:
            raise CommandError("**SnapChat's API** returned `500` - try again later")
        contents = [
            f"**@{username}** — {story.snapUrls.mediaUrl} ({i}/{len(user.story.snapList)})"
            for i, story in enumerate(user.story.snapList, start=1)
        ]
        return await ctx.paginate(contents)

    @command(
        name="snapchat",
        aliases=["snap"],
        description="Get bitmoji and QR scan code for user",
        example=",snapchat jon",
    )
    async def snapchat(self, ctx: Context, username: str):
        try:
            user = await PageProps.from_username(username)
        except Exception:
            raise CommandError("**SnapChat's API** returned `500` - try again later")
        profile = user.userProfile.publicProfileInfo
        embed = Embed(
            title=f"{profile.title} (@{profile.username}) on Snapchat",
            url=f"https://www.snapchat.com/add/{user.username}",
            color=Color.from_str("#fbfb04"),
        )
        embed.description = profile.bio or "No biography set"
        embed.add_field(
            name="Subscribers", value=profile.subscriberCount.humanize(), inline=True
        )
        embed.set_thumbnail(
            url=f"https://us-east1-aws.api.snapchat.com/web-capture/www.snapchat.com/add/{username}/preview/square.jpeg?xp_id=1"
        )
        embed.set_footer(
            text="Snapchat",
            icon_url="https://assets.stickpng.com/images/580b57fcd9996e24bc43c536.png",
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        return await ctx.send(embed=embed)

    @group(
        name="timezone",
        aliases=["tz", "time"],
        description="View your current time or somebody elses",
        example=",timezone jonathan",
        invoke_without_command=True,
    )
    async def timezone(self, ctx: Context, *, member: Optional[Member] = None):
        member = member or ctx.author
        if not (
            timezone := await self.bot.db.fetchval(
                """SELECT timezone FROM timezones WHERE user_id = $1""", member.id
            )
        ):
            message = (
                f"Your **timezone** has not been set yet. Use `{ctx.prefix}timezone set (location)` to set it then try this command again."
                if member == ctx.author
                else f"**{str(member)}** does not have their **timezone** set."
            )
            raise CommandError(message)
        prefix = "Your" if member == ctx.author else f"**{str(member)}'s**"
        dt = arrow.now(timezone)
        return await ctx.send(
            embed=Embed(
                color=self.bot.color,
                description=f":alarm_clock: {ctx.author.mention}: {prefix} current time is **{dt.format('MMMM Do h:mm A')}**",
            )
        )

    @timezone.command(
        name="set", description="Set your timezone", example=",timezone set Los Angeles"
    )
    async def timezone_set(self, ctx: Context, *, location: Timezone):
        """Set your timezone."""
        await self.bot.db.execute(
            "INSERT INTO timezones (user_id, timezone) VALUES ($1, $2) ON CONFLICT(user_id) DO UPDATE SET timezone = excluded.timezone"
            "",
            ctx.author.id,
            location,
        )
        return await ctx.success(f"Your **timezone** has been set to `{location}`")

    @timezone.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View a list of every member's timezone",
    )
    async def timezone_list(self, ctx: Context):
        """List all timezones"""
        if not (
            timezones := await self.bot.db.fetch(
                "SELECT user_id, timezone FROM timezones WHERE user_id = ANY($1::BIGINT[])",
                [m.id for m in ctx.guild.members],
            )
        ):
            raise CommandError("No members have set their **timezone**")
        embed = Embed(title="Timezones").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        rows = [
            f"`{i}` **{utils.escape_markdown(str(ctx.guild.get_member(row.user_id)))}** - {row.timezone}"
            for i, row in enumerate(timezones, start=1)
        ]
        return await ctx.paginate(embed, rows)

    @command(
        name="guildicon",
        aliases=["servericon", "gicon", "sicon"],
        description="Returns the guild icon",
    )
    @guild_only()
    async def guildicon(self, ctx: Context, guild: Optional[Guild] = None):
        guild = guild or ctx.guild
        if not (icon := guild.icon):
            raise CommandError(
                f"{'This' if guild == ctx.guild else 'That'} **guild** has no **icon**"
            )
        embed = Embed(title=f"{shorten(guild.name, 20)}'s guild icon")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=guild.icon.url)
        return await ctx.send(embed=embed)

    @command(
        name="guildbanner", description="Returns the guild banner", aliases=["gbanner"]
    )
    @guild_only()
    async def guildbanner(self, ctx: Context, guild: Optional[Guild] = None):
        guild = guild or ctx.guild
        if not (banner := guild.banner):
            raise CommandError(
                f"{'This' if guild == ctx.guild else 'That'} **guild** has no **banner**"
            )
        embed = Embed(title=f"{shorten(guild.name, 20)}'s guild banner")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=guild.banner.url)
        return await ctx.send(embed=embed)

    @command(name="splash", description="Returns the splash background")
    @guild_only()
    async def splash(self, ctx: Context, guild: Optional[Guild] = None):
        guild = guild or ctx.guild
        if not (splash := guild.splash):
            raise CommandError(
                f"{'This' if guild == ctx.guild else 'That'} **guild** has no **splash background**"
            )
        embed = Embed(title=f"{shorten(guild.name, 20)}'s guild splash")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        embed.set_image(url=guild.splash.url)
        return await ctx.send(embed=embed)
