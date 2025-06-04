from discord.ext.commands import (
    command,
    Cog,
    group,
    parameter,
    UserConverter,
    cooldown,
    BucketType,
    has_permissions,
    hybrid_command,
)
from discord import (
    Member,
    User,
    Permissions,
    Spotify,
    Guild,
    Message,
    app_commands,
    TextChannel,
    VoiceChannel,
    CategoryChannel,
    Embed,
    Invite,
    PartialInviteGuild,
    utils,
    Role,
)
from extensions.music.player import Player
from typing import cast
from loguru import logger as log
from typing import Optional
from discord.utils import format_dt, oauth_url, utcnow
from itertools import groupby
from datetime import datetime, timezone
from discord.utils import find
from humanize import naturalsize
import pytz
from discord.ui import View, Button
from random import choice
from time import time
from yarl import URL

import config
from system import Marly
from config import Emojis, Color, Marly
from system.base.context import Context
from system.tools.utils import Plural, concatenate
from system.tools.utils import shorten
from .help import help
from .emoji import emoji


class Information(help, emoji, Cog):
    def __init__(self, bot: "Marly"):
        self.bot = bot

    @hybrid_command(aliases=["av"])
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def avatar(self, ctx: Context, user: UserConverter = parameter(default=None)):
        """
        View a user's avatar
        """
        user = user or ctx.author
        return await ctx.embed(
            title=f"> {f'Your avatar' if user == ctx.author else f'{user.name}\'s avatar'}",
            url=user.display_avatar.url,
            image=user.display_avatar.url,
        )

    @command()
    async def banner(self, ctx: Context, *, user: Member | User = None):
        """
        View a user's banner
        """
        user = user or ctx.author
        user = await self.bot.fetch_user(user.id)

        if not user.banner:
            return await ctx.warn(
                (
                    "You don't have a **banner** set "
                    if user == ctx.author
                    else f"`{user.name}` doesn't have a **banner** set"
                ),
            )

        return await ctx.embed(
            title=f"{f'Your banner' if user == ctx.author else f'{user.name}\'s banner'}",
            url=user.banner.url,
            image=user.banner.url,
        )

    @command()
    async def uptime(self, ctx: Context):
        """
        View the uptime of the bot
        """
        return await ctx.utility(
            f"> 🗿 **{self.bot.user.name}** has been online for {format_dt(self.bot.uptime, 'R')}"
        )

    @command()
    async def ping2(self, ctx: Context) -> Message:
        """
        View the bot's latency
        """

        start = time()
        message = await ctx.send(content="ping...")
        finished = (time() - start) * 1000

        return await message.edit(
            content=f"it took `{int(self.bot.latency * 1000)}ms` to ping **{choice(config.ping_responses)}** (edit: `{finished:.1f}ms`)"
        )

    @command()
    async def ping(self, ctx: Context) -> Message:
        """
        View the bot's latency
        """
        return await ctx.send(f"> `{round(self.bot.latency * 1000)}ms`")

    @command()
    async def credits(self, ctx: Context):
        """
        View the credits for the bot.
        """
        return await ctx.utility(
            "Developed by <@1247076592556183598> [`Github`](https://github.com/hiddeout?tab=repositories) \n> If i stole some of your code please contact me so i can block you"
        )

    @command()
    async def invite(self, ctx: Context):
        """
        Invite the bot to your server
        """
        return await ctx.utility(
            f"> Invite Me **[Here]({oauth_url(self.bot.user.id, permissions=Permissions(permissions=8))})**\n",
            f"> Support Server **[Here]({Marly.SUPPORT_SERVER})**",
        )

    @hybrid_command(aliases=["ui"])
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def userinfo(self, ctx: Context, *, user: Member | User = None):
        """
        View a user's information
        """
        user = user or ctx.author

        badges = []
        description = ""
        if not user.bot:
            if isinstance(user, User) and user.banner:
                badges.extend([Emojis.BADGES.NITRO, Emojis.BADGES.BOOST])
            elif user.display_avatar.is_animated():
                badges.append(Emojis.BADGES.NITRO)

            if Emojis.BADGES.BOOST not in badges:
                for guild in user.mutual_guilds:
                    member = guild.get_member(user.id)
                    if not member:
                        continue

                    if member.premium_since:
                        if Emojis.BADGES.NITRO not in badges:
                            badges.append(Emojis.BADGES.NITRO)
                        badges.append(Emojis.BADGES.BOOST)
                        break

            for flag in user.public_flags:
                if flag[1] and (badge := getattr(Emojis.BADGES, flag[0].upper(), None)):
                    badges.append(badge)

        fields = [
            {
                "name": "Created",
                "value": f"{format_dt(user.created_at, 'D')}\n> {format_dt(user.created_at, 'R')}",
                "inline": True,
            }
        ]

        if isinstance(user, Member) and user.joined_at:
            join_pos = sorted(
                ctx.guild.members,
                key=lambda member: member.joined_at or ctx.message.created_at,
            ).index(user)

            fields.append(
                {
                    "name": f"Joined ({join_pos + 1})",
                    "value": f"{format_dt(user.joined_at, 'D')}\n> {format_dt(user.joined_at, 'R')}",
                    "inline": True,
                }
            )

            if roles := user.roles[1:]:
                fields.append(
                    {
                        "name": f"Roles ({len(roles)})",
                        "value": "> "
                        + ", ".join(role.mention for role in list(reversed(roles))[:5])
                        + (f" (+{len(roles) - 5})" if len(roles) > 5 else ""),
                        "inline": False,
                    }
                )

            if (voice := user.voice) and voice.channel:
                members = len(voice.channel.members) - 1
                phrase = "Streaming in " if voice.self_stream else "In"
                description += f"\n{phrase} {voice.channel.mention} " + (
                    f"with **{Plural(members):other}**" if members else "themselves"
                )

            if (
                user.voice
                and ctx.voice_client
                and ctx.voice_client.channel == user.voice.channel
            ):
                player = cast(Player, ctx.voice_client)
                if player.current:
                    current_track = player.current
                    safe_title = (
                        shorten(current_track.title, 20)
                        .replace("[", "(")
                        .replace("]", ")")
                    )
                    description += f"\nListening to [`{safe_title}`]({current_track.uri}) on the **Bot**"

            for activity_type, activities in groupby(
                user.activities,
                key=lambda activity: activity.type,
            ):
                activities = list(activities)
                if isinstance(activities[0], Spotify):
                    activity = activities[0]
                    format_duration = (
                        lambda delta: f"{(int(delta.total_seconds()) // 60)}:{(int(delta.total_seconds()) % 60):02d}"
                    )
                    duration = lambda start, end: (
                        f"[`{format_duration(datetime.now(timezone.utc) - start)}/{format_duration(end - start)}`]"
                    )
                    description += (
                        f"\nListening to [`{shorten(activity.title, 10)}`]({activity.track_url}) "
                        f"by [`{shorten(activity.artists[0], 10)}`]({URL(f'https://google.com/search?q={activity.artists[0]}')}) on **Spotify**"
                    )

        footer_text = f"{len(user.mutual_guilds)} Mutual Servers"

        if isinstance(user, Member) and user.joined_at:
            join_pos = sorted(
                ctx.guild.members,
                key=lambda member: member.joined_at or ctx.message.created_at,
            ).index(user)
            footer_text = f"Join Position: {join_pos + 1} • {footer_text}"

        return await ctx.embed(
            title=f"{user.name} {' '.join(badges) if badges else ''}",
            description=description,
            fields=fields,
            thumbnail=user.display_avatar.url,
            footer={"text": footer_text, "icon_url": user.display_avatar.url},
        )

    @command()
    async def serverinfo(self, ctx: Context):
        """
        View the server's information
        """
        return await ctx.embed()

    @command(
        name="serverinfo",
        usage="<guild>",
        example="1115389989..",
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

        return await ctx.embed(
            title=guild.name,
            description=(
                "> **created** "
                + (
                    format_dt(guild.created_at, style="D")
                    + "("
                    + format_dt(guild.created_at, style="R")
                    + ")"
                )
                + f"\n> [**`shard`**]({Marly.WEBSITE_URL}/status) {guild.shard_id}/{self.bot.shard_count}"
            ),
            timestamp=utcnow(),
            thumbnail=guild.icon,
            fields=[
                {
                    "name": "**Owner**",
                    "value": f"> {guild.owner.mention if guild.owner else guild.owner_id}",
                    "inline": True,
                },
                {
                    "name": "**Members**",
                    "value": (
                        f"> **Total:** {guild.member_count:,}\n"
                        f"> **Humans:** {len([m for m in guild.members if not m.bot]):,}\n"
                        f"> **Bots:** {len([m for m in guild.members if m.bot]):,}"
                    ),
                    "inline": True,
                },
                {
                    "name": "**Information**",
                    "value": (
                        f"> **Verification:** {guild.verification_level.name.title()}\n"
                        f"> **Boosts:** {guild.premium_subscription_count:,} (level {guild.premium_tier})"
                    ),
                    "inline": True,
                },
                {
                    "name": "**Design**",
                    "value": (
                        f"> **Banner:** "
                        + (
                            f"[Click here]({guild.banner})\n"
                            if guild.banner
                            else "N/A\n"
                        )
                        + f"> **Splash:** "
                        + (
                            f"[`Click here]({guild.splash})\n"
                            if guild.splash
                            else "N/A\n"
                        )
                        + f"> **Icon:** "
                        + (f"[Click here]({guild.icon})\n" if guild.icon else "N/A\n")
                    ),
                    "inline": True,
                },
                {
                    "name": f"**Channels ({len(guild.channels)})**",
                    "value": f"> **Text:** {len(guild.text_channels)}\n> **Voice:** {len(guild.voice_channels)}\n> **Category:** {len(guild.categories)}\n",
                    "inline": True,
                },
                {
                    "name": "**Counts**",
                    "value": (
                        f"> **Roles:** {len(guild.roles)}/250\n"
                        f"> **Emojis:** {len(guild.emojis)}/{guild.emoji_limit}\n"
                        f"> **Boosters:** {len(guild.premium_subscribers):,}\n"
                    ),
                    "inline": True,
                },
            ],
            footer={"text": f"Guild ID: {guild.id}"},
            author={
                "name": ctx.author.display_name,
                "icon_url": ctx.author.display_avatar.url,
            },
        )

    @command(
        name="roleinfo",
        example="Friends",
        aliases=["rinfo", "ri"],
    )
    async def roleinfo(self, ctx: Context, *, role: str = None):
        """
        View information about a role
        """

        if role is None:
            role = ctx.author.top_role
        elif role.startswith("<@&") and role.endswith(">"):
            role_id = int(role[3:-1])
            role = ctx.guild.get_role(role_id)
        else:
            role_lower = role.lower()
            role = find(lambda r: r.name.lower() == role_lower, ctx.guild.roles)
        if not role:
            if role is None:
                role = ctx.author.top_role
            else:
                await ctx.warn(
                    f"I was unable to find a **role** with the name: **{role}**",
                )
                return
        return await ctx.embed(
            color=role.color,
            author={
                "name": ctx.author.display_name,
                "icon_url": ctx.author.display_avatar.url,
            },
            description=(
                "> **Created** "
                + format_dt(role.created_at, style="f")
                + " ("
                + format_dt(role.created_at, style="R")
                + ")"
            ),
            fields=[
                {
                    "name": "Role Info",
                    "value": f"> **Name:** {role.name} {role.mention}\n> **ID:** `{role.id}`\n> **Color:** [`{role.color}`](https://www.color-hex.com/color/{str(role.color)[1:]})",
                    "inline": True,
                },
                {
                    "name": f" Members ({len(role.members)})",
                    "value": (
                        (
                            ", ".join([member.mention for member in role.members[:7]])
                            + ("..." if len(role.members) > 7 else "")
                        )
                        if role.members
                        else "No members in this role"
                    ),
                    "inline": False,
                },
            ],
            thumbnail={"url": role.icon.url} if role.icon else None,
        )

    @command()
    async def status(self, ctx: Context) -> Message:
        """
        View the bot's status
        """

        return await ctx.send(
            f"{ctx.author.mention}: experiencing issues? check your shards status on https://example.bot/status"
        )

    @command()
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
            return await ctx.warn(f"**{ctx.guild}** doesn't have any **bots!**")

        pages = []
        chunks = [members[i : i + 10] for i in range(0, len(members), 10)]

        for index, chunk in enumerate(chunks):
            pages.append(
                await ctx.embed(
                    title="**List of bots**",
                    description="\n".join(
                        f"`{members.index(member) + 1:02}` **{member.mention}**"
                        for member in chunk
                    ),
                    author={
                        "name": f"{ctx.author.display_name}",
                        "icon_url": ctx.author.display_avatar,
                    },
                    footer={
                        "text": f"page {index + 1}/{len(chunks)} ({len(members)} entries)"
                    },
                )
            )

        return await ctx.paginate(pages=pages)

    @hybrid_command(
        name="botinfo",
        aliases=["bi", "about"],
    )
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    @app_commands.allowed_installs(guilds=True, users=True)
    async def botinfo(self, ctx: Context) -> Message:
        """
        View the bot's information
        """
        return await ctx.embed(
            fields=[
                {
                    "name": "Uptime",
                    "value": f"{format_dt(self.bot.uptime, 'R')}",
                    "inline": True,
                },
                {
                    "name": "PING",
                    "value": f"{round(self.bot.latency * 1000)}ms",
                    "inline": True,
                },
                {
                    "name": "RAM",
                    "value": f"{naturalsize(self.bot.process.memory_info().rss)}",
                    "inline": True,
                },
            ],
            footer={
                "text": f"{self.bot.user.name.upper()} {self.bot.version}    CPU : {self.bot.process.cpu_percent()}%   VM : {self.bot.process.memory_info().vms / 1024 / 1024:.2f} MB"
            },
        )

    @command()
    async def bans(self, ctx: Context) -> Message:
        """
        View the bans of the server
        """
        pages = []
        bans = [ban async for ban in ctx.guild.bans()]

        if not bans:
            return await ctx.warn(f" This server has **no** bans!")

        for index, ban in enumerate(bans):
            pages.append(
                await ctx.embed(
                    title=f"**{ctx.guild.name}** bans",
                    description=f"**{index + 1}** **{ban.user.name}#{ban.user.discriminator}**",
                )
            )

        return await ctx.paginate(pages=pages)

    @command()
    async def status(self, ctx: Context) -> Message:
        """
        View the bot's status
        """

        return await ctx.send(
            f"{ctx.author.mention}: experiencing issues? check your shards status on {config.Marly.WEBSITE_URL}/status"
        )

    @command()
    @has_permissions(manage_guild=True)
    async def invites(self, ctx: Context) -> Message:
        """
        View all server invites.
        """

        invites = await ctx.guild.invites()
        if not invites:
            return await ctx.warn("No invites are currently present!")

        descriptions = [
            f"`{index:02}` [`{invite.code}`]({invite.url}) by {invite.inviter.mention if invite.inviter else ''} • {invite.uses:,} uses • {'permanent' if invite.max_age == 0 else f'expires {format_dt(invite.expires_at, "R")}'}"
            for index, invite in enumerate(
                sorted(
                    invites,
                    key=lambda invite: invite.created_at or utcnow(),
                    reverse=False,
                ),
                start=1,
            )
        ]
        base_embed = Embed(title=f"Server Invites")
        base_embed.set_author(
            name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url
        )
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @command(
        name="urbandictionary",
        usage="(word)",
        example="Slatt",
        aliases=["ud", "urban"],
    )
    async def urban(self, ctx: Context, *, word: str):
        """
        Gets the definition of a word/slang from Urban Dictionary
        """

        embeds = []
        async with self.bot.session.get(
            "http://api.urbandictionary.com/v0/define", params={"term": word}
        ) as response:
            if response.status != 200:
                return await ctx.warn("Failed to fetch definition")

            data = await response.json()

        defs = data["list"]
        if len(defs) == 0:
            return await ctx.warn(
                f"No definition found for **{word}**", reference=ctx.message
            )

        for defi in defs:
            e = (
                Embed(
                    title=defi["word"],
                    description=defi["definition"],
                    url=defi["permalink"],
                )
                .set_author(
                    name=ctx.author.name, icon_url=ctx.author.display_avatar.url
                )
                .add_field(name="Example", value=defi["example"], inline=False)
                .add_field(
                    name="Votes",
                    value=f"👍 `{defi['thumbs_up']} / {defi['thumbs_down']}` 👎",
                    inline=False,
                )
                .set_footer(
                    text=f"Page {defs.index(defi) + 1}/{len(defs)} of Urban Dictionary Results",
                    icon_url=ctx.author.display_avatar.url,
                )
            )
            embeds.append(e)

        await ctx.paginate(embeds)

    @command(aliases=["firstmsg"])
    async def firstmessage(self, ctx: Context) -> Message:
        """
        View the first message sent.
        """

        message = [
            message async for message in ctx.channel.history(limit=1, oldest_first=True)
        ][0]
        return await ctx.utility(
            f"Click [`here`]({message.jump_url}) to jump to the **first message** sent by **{message.author}**"
        )

    @command(aliases=["mc"])
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

        embed.add_field(name="**Users**", value=f"{len(guild.members):,}")
        embed.add_field(name="**Humans**", value=f"{len(humans):,}")
        embed.add_field(name="**Bots**", value=f"{len(bots):,}")

        return await ctx.send(embed=embed)

    @command(
        aliases=[
            "spfp",
            "savi",
            "sav",
        ],
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
                "You don't have a **server avatar** set!"
                if member == ctx.author
                else f"**{member}** doesn't have a **server avatar** set!"
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

    @command(aliases=["gbanner"])
    async def guildbanner(
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
            return await ctx.warn(f"**{guild}** doesn't have a **banner** set!")

        embed = Embed(
            url=guild.banner,
            title=f"{guild}'s banner",
        )
        embed.set_image(url=guild.banner)
        return await ctx.send(embed=embed)

    @command(aliases=["sbanner"])
    async def serverbanner(self, ctx: Context, *, user: Member | User = None):
        """
        Get the server banner of a member or yourself
        """

        user = user or ctx.author
        if not user.guild_banner:
            return await ctx.warn(f"**{user}** doesn't have a **banner** set!")

        embed = Embed(
            url=user.guild_banner,
            title=f"> {f'Your Server Banner' if user == ctx.author else f'{user.name}\'s Server Banner'}",
        )
        embed.set_image(url=user.guild_banner)
        return await ctx.send(embed=embed)

    @command()
    async def splash(self, ctx: Context, *, invite: Optional[Invite]):
        """
        Returns splash background
        """

        guild = (
            invite.guild
            if isinstance(invite, Invite)
            and isinstance(invite.guild, PartialInviteGuild)
            else ctx.guild
        )
        if not guild.splash:
            return await ctx.warn(f"**{guild}** doesn't have a **splash** set!")

        embed = Embed(
            url=guild.splash,
            title=f"{guild}'s splash",
        )
        embed.set_image(url=guild.splash)
        return await ctx.send(embed=embed)

    @command(
        name="weather",
        example="New York",
    )
    @cooldown(1, 4, BucketType.user)
    async def weather(self, ctx: Context, *, location: str):
        """
        Get the weather for a location.
        """
        await ctx.typing()

        try:
            async with self.bot.session.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params={"q": location, "appid": config.Apis.WEATHER, "units": "metric"},
            ) as response:
                if response.status != 200:
                    return await ctx.warn(
                        f"Could not find weather data for **{location}**"
                    )

                data = await response.json()
        except Exception as e:
            return await ctx.warn(f"No location was found for: **{location}**")

        weather = data["weather"][0]
        main = data["main"]
        wind = data["wind"]
        sys = data["sys"]

        temp_celsius = main["temp"]
        temp_fahrenheit = (temp_celsius * 9 / 5) + 32

        local_tz = pytz.FixedOffset(data["timezone"] // 60)
        sunrise_time = (
            datetime.utcfromtimestamp(sys["sunrise"])
            .replace(tzinfo=pytz.utc)
            .astimezone(local_tz)
        )
        sunset_time = (
            datetime.utcfromtimestamp(sys["sunset"])
            .replace(tzinfo=pytz.utc)
            .astimezone(local_tz)
        )

        return await ctx.embed(
            title=f"{weather['description'].title()} in {data['name']}, {sys['country']}",
            thumbnail=f"http://openweathermap.org/img/wn/{weather['icon']}.png",
            fields=[
                {
                    "name": "Temperature",
                    "value": f"{temp_celsius:.2f} °C / {temp_fahrenheit:.2f} °F",
                    "inline": True,
                },
                {"name": "Wind", "value": f"{wind['speed']} mph", "inline": True},
                {"name": "Humidity", "value": f"{main['humidity']}%", "inline": True},
                {
                    "name": "Sunrise",
                    "value": utils.format_dt(sunrise_time, style="T"),
                    "inline": True,
                },
                {
                    "name": "Sunset",
                    "value": utils.format_dt(sunset_time, style="T"),
                    "inline": True,
                },
                {
                    "name": "Visibility",
                    "value": f"{data['visibility'] / 1000:.1f} km",
                    "inline": True,
                },
            ],
        )

    @command(aliases=["inrole"], example="@admin")
    async def members(self, ctx: Context, *, role: Optional[Role] = None) -> Message:
        """
        View members in a role
        """

        role = role or ctx.author.top_role  # Use author's top role if none provided
        members = role.members
        if not members:
            return await ctx.warn(f"{role.mention} doesn't have any members!")

        if len(members) > 1000:
            return await ctx.utility(
                f"{ctx.author.mention} Max view amount is **{len(members)}/1000** members",
                emoji="🔎",
            )

        descriptions = [
            f"`{index:02}` {member.mention} (`{member.id}`) - **{member.name}**"
            for index, member in enumerate(members, start=1)
        ]
        base_embed = Embed(title=f"Members in {role}")
        return await ctx.autopaginator(
            embed=base_embed, description=descriptions, split=20
        )

    @command(
        name="inviteinfo",
        usage="(invite)",
        example="rack",
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
                f"**Created:** {format_dt(invite.channel.created_at, 'f')} ({format_dt(invite.channel.created_at, 'R')})\n"
                "**Invite Expiration:** "
                + (
                    format_dt(invite.expires_at, "D")
                    + f" ({format_dt(invite.expires_at, 'R')})"
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
                f"**Created:** {format_dt(invite.guild.created_at, 'f')} ({format_dt(invite.guild.created_at, 'R')})\n"
                f"**Members:** {invite.approximate_member_count:,}\n"
                f"**Members Online:** {invite.approximate_presence_count:,}\n"
                f"**Verification Level:** {invite.guild.verification_level.name.title()}"
            ),
            inline=True,
        )
        embed.set_author(
            name=ctx.author.display_name,
            icon_url=ctx.author.display_avatar.url,
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

    @command()
    async def stickers(self, ctx: Context) -> Message:
        """
        view all server stickers.
        """

        stickers = ctx.guild.stickers
        if not stickers:
            return await ctx.warn("There are no **stickers** in this server!")

        descriptions = [
            f"`{index:02}` **{sticker.name}** (**[`{sticker.id}`]({sticker.url})**)"
            for index, sticker in enumerate(stickers, start=1)
        ]
        base_embed = Embed(title=f"Stickers in {ctx.guild}")
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @command(
        aliases=["emotes"],
    )
    async def emojis(self, ctx: Context) -> Message:
        """
        view all server emojis.
        """

        emojis = ctx.guild.emojis
        if not emojis:
            return await ctx.warn("There are no **emojis** in this server!")

        descriptions = [
            f"`{index:02}` {emoji} [**`{emoji.name}`**]({emoji.url})"
            for index, emoji in enumerate(emojis, start=1)
        ]
        base_embed = Embed(title=f"Emojis in {ctx.guild}")
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @command(
        name="recentmembers",
        usage="<amount>",
        example="50",
        aliases=["recentusers", "recentjoins", "newmembers", "newusers", "recents"],
    )
    @has_permissions(manage_guild=True)
    async def recentmembers(self: "Information", ctx: Context, amount: int = 50):
        """
        View the most recent members to join the server
        """
        description = [
            f"`{index:02}` {member.mention} (`{member.id}`) - {format_dt(member.joined_at, style='R')}"
            for index, member in enumerate(
                sorted(
                    ctx.guild.members,
                    key=lambda member: member.joined_at,
                    reverse=True,
                ),
                start=1,
            )
        ][:amount]

        embed = Embed(title="Recent Members")
        embed.set_author(
            name=f"{ctx.guild.name} ({ctx.guild.id})", icon_url=ctx.guild.icon
        )

        await ctx.autopaginator(embed=embed, description=description, split=10)

    @command(
        name="channelinfo",
        example="#general",
        aliases=["cinfo", "ci"],
    )
    async def channelinfo(
        self,
        ctx: Context,
        *,
        channel: Optional[TextChannel | VoiceChannel | CategoryChannel] = None,
    ):
        """
        View information about a channel
        """
        channel = channel or ctx.channel
        thread_count = len(channel.threads) if isinstance(channel, TextChannel) else 0
        active_threads = (
            len([t for t in channel.threads if not t.archived])
            if isinstance(channel, TextChannel)
            else 0
        )
        channel_type = {
            TextChannel: "Text Channel",
            VoiceChannel: "Voice Channel",
            CategoryChannel: "Category",
        }.get(type(channel), "Unknown")
        channel_specific = []
        if isinstance(channel, TextChannel):
            channel_specific.extend(
                [
                    f"> **Slowmode:** {channel.slowmode_delay or 'n/a'}",
                    f"> **NSFW:** {'Yes' if channel.is_nsfw() else 'No'}",
                    f"> **News Channel:** {'Yes' if channel.is_news() else 'No'}",
                    f"> **Threads:** {thread_count} ({active_threads} active)",
                ]
            )
        elif isinstance(channel, VoiceChannel):
            channel_specific.extend(
                [
                    f"> **Bitrate:** {channel.bitrate // 1000}kbps",
                    f"> **User Limit:** {channel.user_limit or 'Unlimited'}",
                    f"> **Connected Users:** {len(channel.members)}",
                ]
            )
        return await ctx.embed(
            author={
                "name": ctx.author.display_name,
                "icon_url": ctx.author.display_avatar.url,
            },
            description=(
                f"> **Created** {format_dt(channel.created_at, style='f')} "
                f"({format_dt(channel.created_at, style='R')})"
            ),
            fields=[
                {
                    "name": "Channel Info",
                    "value": (
                        f"> **Name:** {channel.name} {channel.mention}\n"
                        f"> **ID:** `{channel.id}`\n"
                        f"> **Type:** {channel_type}\n"
                        f"> **Category:** {channel.category.name if channel.category else 'n/a'}\n"
                        f"> **Topic:** `{channel.topic or 'n/a'}`\n"
                        + "\n".join(channel_specific)
                    ),
                    "inline": True,
                },
            ],
        )

    @command(
        aliases=["sc"],
        usage="(query)",
        example="Free Young Thug",
    )
    async def soundcloud(self, ctx: Context, *, query: str) -> Message:
        """
        Search a query on SoundCloud.
        You can also stream new tracks from a user.
        """

        response = await self.bot.session.get(
            URL.build(
                scheme="https",
                host="api-v2.soundcloud.com",
                path="/search/tracks",
                query={
                    "q": query,
                },
            ),
            headers={
                "Authorization": config.Apis.SOUNDCLOUD,
            },
        )
        data = await response.json()
        if not data["collection"]:
            return await ctx.warn(f"No results found for **{query}**!")

        links = [track["permalink_url"] for track in data["collection"]]
        pages = [f"({i + 1}/{len(links)}) {link}" for i, link in enumerate(links)]

        return await ctx.paginate(pages=pages)
