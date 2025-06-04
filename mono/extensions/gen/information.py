from io import BytesIO
from itertools import groupby
from typing import List, Optional

import config
from core.client.context import Context
from core.Mono import Mono
from core.tools import human_join, plural, short_timespan
from discord import (ActivityType, ButtonStyle, DiscordException, Embed, File,
                     Guild, HTTPException, Invite, Member, Message, NotFound,
                     PartialInviteGuild, Permissions, Role, Spotify, Streaming,
                     TextChannel, User, app_commands)
from discord.ext.commands import (Author, BucketType, Cog, Group, command,
                                  cooldown, group, has_permissions,
                                  hybrid_command, parameter)
from discord.ui import Button, View
from discord.utils import find, format_dt, oauth_url, utcnow
from humanize import ordinal
from loguru import logger as log
from psutil import Process
from xxhash import xxh128_hexdigest

# from core.tools.image import collage


class Information(Cog):
    def __init__(self, bot: Mono):
        self.bot: Mono = bot
        self.process = Process()

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

    @Cog.listener("on_user_update")
    async def submit_avatar(
        self,
        before: User,
        user: User,
    ):
        if before.avatar == user.avatar or not user.avatar:
            return

        channel = self.bot.get_channel(config.avatars_channel)
        if not isinstance(channel, TextChannel):
            return

        try:
            buffer = await user.avatar.read()
            key = xxh128_hexdigest(buffer, seed=1337)
        except (DiscordException, HTTPException, NotFound):
            return log.warn(f"Failed to download asset for {user.name} ({user.id})!")

        message = await channel.send(
            file=File(
                fp=BytesIO(buffer),
                filename=f"{key}."
                + ("png" if not user.avatar.is_animated() else "gif"),
            ),
        )
        await self.bot.db.execute(
            """
            INSERT INTO metrics.avatars (key, user_id, asset)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, key) DO UPDATE
            SET asset = EXCLUDED.asset
            """,
            key,
            user.id,
            message.attachments[0].url,
        )

        log.info(f"Redistributed asset for {user.name} ({user.id}).")

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

    @command(
        name="invite",
        aliases=["inv"],
    )
    async def invite(self, ctx: Context):
        """Invite the bot to your server"""
        return await ctx.neutral(
            f"Click **[here]({oauth_url(self.bot.user.id)})** to **invite me** to your server"
        )

    @command(aliases=["discord"])
    async def support(self, ctx: Context) -> Message:
        """
        Get an invite link for the bot's support server.
        """

        return await ctx.neutral(f"[**Support Server**]({config.support})")

    @command(aliases=["ii"])
    async def inviteinfo(self, ctx: Context, *, invite: Invite) -> Message:
        """
        View information about an invite.
        """

        if not isinstance(invite.guild, PartialInviteGuild):
            return await ctx.reply("shut up")

        guild = invite.guild
        embed = Embed(
            description=f"{format_dt(guild.created_at)} ({format_dt(guild.created_at, 'R')})"
        )
        embed.set_author(
            name=f"{guild.name} ({guild.id})",
            url=invite.url,
            icon_url=guild.icon,
        )

        if guild.banner:
            embed.set_image(url=guild.banner.url)

        embed.add_field(
            name="**Information**",
            value=(
                ""
                f"> **Invitier:** {invite.inviter or 'Vanity URL'}\n"
                f"> **Channel:** {invite.channel or 'Unknown'}\n"
                f"> **Created:** {format_dt(invite.created_at or guild.created_at)}\n"
                f"> **Temporary:** {invite.temporary}\n"
            ),
        )
        embed.add_field(
            name="**Guild**",
            value=(
                ""
                f"> **Members:** {invite.approximate_member_count:,}\n"
                f"> **Members Online:** {invite.approximate_presence_count:,}\n"
                f"> **Verification Level:** {guild.verification_level.name.title()}\n"
                f"> **Boosts:** {guild.premium_subscription_count:,}"
            ),
        )

        return await ctx.reply(embed=embed)

    @command(aliases=["sbanner"])
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
            return await ctx.warn(f"**{guild}** doesn't have a **banner** set!")

        embed = Embed(
            url=guild.banner,
            title=f"{guild}'s banner",
        )
        embed.set_image(url=guild.banner)
        return await ctx.send(embed=embed)

    @command(
        name="roleinfo",
        usage="<role>",
        example="@admin",
        aliases=["rinfo", "ri"],
    )
    async def roleinfo(self, ctx: Context, *, role_name: str):
        """
        View information about a role
        """
        try:
            # Check if the role_name is a mention
            if role_name.startswith("<@&") and role_name.endswith(">"):
                role_id = int(role_name[3:-1])
                role = ctx.guild.get_role(role_id)
            else:
                role_name_lower = role_name.lower()
                role = find(
                    lambda r: r.name.lower() == role_name_lower, ctx.guild.roles
                )

            if not role:
                await ctx.warn(
                    f"I was unable to find a role with the name: **{role_name}**",
                    reference=ctx.message,
                )
                return

            embed = Embed(title=role.name, color=role.color)

            embed.set_author(
                name=ctx.author.name, icon_url=ctx.author.display_avatar.url
            )

            embed.add_field(
                name="Role ID",
                value=f"`{role.id}`",
                inline=True,
            )
            embed.add_field(
                name="Guild",
                value=f"{ctx.guild.name} (`{ctx.guild.id}`)",
                inline=True,
            )
            embed.add_field(
                name="Color",
                value=f"`{role.color}`",
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

            members = role.members
            if members:
                member_list = ", ".join([member.name[:10] for member in members[:7]])
                embed.add_field(
                    name=f"{len(members)} Member(s)",
                    value=member_list + ("..." if len(members) > 7 else ""),
                    inline=False,
                )
            else:
                embed.add_field(
                    name="Members",
                    value="No members in this role",
                    inline=False,
                )

            # Adding permissions block
            permissions = role.permissions
            permissions_list = [perm[0] for perm in permissions if perm[1]]
            formatted_permissions = ", ".join(permissions_list)
            if formatted_permissions:
                embed.add_field(
                    name="Permissions",
                    value=f"```{formatted_permissions}```",
                    inline=False,
                )

            return await ctx.reply(embed=embed)
        except Exception as e:
            await ctx.warn(f"An error occurred: {str(e)}", reference=ctx.message)

    @hybrid_command(
        aliases=[
            "pfp",
            "avi",
            "av",
        ],
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
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
            color=config.Color.dark,
        )
        embed.set_image(url=user.avatar or user.default_avatar)

        if user.guild_avatar and user.guild == ctx.guild:
            embed.set_thumbnail(url=user.guild_avatar)
        view = View()

        if user.avatar:
            avatar_button = Button(
                style=ButtonStyle.link, label="Avatar", url=user.avatar.url
            )
            view.add_item(avatar_button)
        if user.guild_avatar and user.guild == ctx.guild:
            server_avatar_button = Button(
                style=ButtonStyle.link, label="Server Avatar", url=user.guild_avatar.url
            )
            view.add_item(server_avatar_button)

        return await ctx.send(embed=embed, view=view)

    @hybrid_command(
        aliases=[
            "spfp",
            "savi",
            "sav",
        ],
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
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
            color=config.Color.dark,
        )

        embed.set_image(url=member.guild_avatar)

        return await ctx.send(embed=embed)

    @hybrid_command(aliases=["userbanner", "ub"])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def banner(
        self,
        ctx: Context,
        *,
        user: Member | User = parameter(
            default=lambda ctx: ctx.author,
        ),
    ) -> Message:
        """
        View a user's banner if one is present.
        """

        if not isinstance(user, User):
            user = await self.bot.fetch_user(user.id)

        if not user.banner:
            return await ctx.warn(
                "You don't have a **banner** set!"
                if user == ctx.author
                else f"**{user}** doesn't have a **banner** set!"
            )

        embed = Embed(
            url=user.banner,
            title="Your banner" if user == ctx.author else f"{user.name}'s banner",
            color=config.Color.dark,
        )

        view = View()

        if user.banner:
            banner_button = Button(
                style=ButtonStyle.link, label="Banner", url=user.banner.url
            )
            view.add_item(banner_button)

        embed.set_image(url=user.banner)

        # Check if user is a Member to access guild attributes
        if isinstance(user, Member) and user.guild.banner:  # Change this line
            server_banner_button = Button(
                style=ButtonStyle.link, label="Server Banner", url=user.guild.banner
            )
            view.add_item(server_banner_button)

        return await ctx.send(embed=embed, view=view)

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

        embed.add_field(name="**Members**", value=f"{len(guild.members):,}")
        embed.add_field(name="**Humans**", value=f"{len(humans):,}")
        embed.add_field(name="**Bots**", value=f"{len(bots):,}")

        return await ctx.send(embed=embed)

    @command(aliases=["sinfo", "si"])
    async def serverinfo(
        self,
        ctx: Context,
        *,
        guild: Optional[Guild],
    ) -> Message:
        """
        View information about the server.
        """

        guild = guild or ctx.guild
        embed = Embed(
            description=f"Created {format_dt(guild.created_at)} ({format_dt(guild.created_at, 'R')})\n **{guild.name.upper()} IS ON SHARD {ctx.guild.shard_id}/{self.bot.shard_count}**",
        )
        embed.set_author(
            name=f"{guild.name} ({guild.id})",
            url=guild.vanity_url,
            icon_url=guild.icon,
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon)
        if guild.banner:
            embed.set_image(url=guild.banner)

        embed.add_field(
            name="**Information**",
            value=(
                ""
                f"> **Owner:** {guild.owner.mention} (`{guild.owner.name}`)\n"
                f"> **Verification:** {guild.verification_level.name.title()}\n"
                f"> **Nitro Boosts:** {guild.premium_subscription_count:,} (`Level {guild.premium_tier}`)\n"
                f"> **Vanity URL:** {guild.vanity_url or 'None Set'}\n"
            ),
        )
        embed.add_field(
            name="**Statistics**",
            value=(
                ""
                f"> **Members:** {guild.member_count:,}\n"
                f"> **Text Channels:** {len(guild.text_channels):,}\n"
                f"> **Voice Channels:** {len(guild.voice_channels):,}\n"
                f"> **Roles:** {len(guild.roles):,}\n"
            ),
        )

        if guild == ctx.guild and (roles := guild.roles[1:]):
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

        view = View()

        if guild.icon:
            icon_button = Button(
                style=ButtonStyle.link, label="Server Icon", url=guild.icon.url
            )
            view.add_item(icon_button)

        if guild.banner:
            banner_button = Button(
                style=ButtonStyle.link, label="Server Banner", url=guild.banner.url
            )
            view.add_item(banner_button)

        return await ctx.send(embed=embed, view=view)

    @command(aliases=["uinfo", "ui", "whois"], example="@base")
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
        # Fetch the user to get banner information
        fetched_user = await self.bot.fetch_user(user.id)

        embed = Embed(color=config.Color.base)
        embed.title = f"{user} {'[BOT]' if user.bot else ''}"
        embed.description = ""
        embed.set_thumbnail(url=user.display_avatar)
        embed.add_field(
            name="**Created**",
            value=(
                format_dt(user.created_at, "D")
                + "\n> "
                + format_dt(user.created_at, "R")
            ),
        )
        if fetched_user.banner:
            embed.set_image(url=fetched_user.banner.url)
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

            embed.set_footer(
                text=f"Join Position: {ordinal(join_pos + 1)} | Mutual Servers: {len(user.mutual_guilds)}",
                icon_url=user.display_avatar,
            )

        # Create a View to hold the buttons
        view = View()

        # Add Avatar Button if available
        if user.avatar:
            avatar_button = Button(
                style=ButtonStyle.link, label="Avatar", url=user.display_avatar.url
            )
            view.add_item(avatar_button)

        # Add Banner Button if available
        if fetched_user.banner:
            banner_button = Button(
                style=ButtonStyle.link, label="Banner", url=fetched_user.banner.url
            )
            view.add_item(banner_button)

        return await ctx.send(embed=embed, view=view)

    #    @command(
    #        aliases=["uinfo", "ui", "whois"],
    #        example="@base"
    #    )
    #    async def userinfo(
    #        self,
    #        ctx: Context,
    #        *,
    #        user: Member | User = parameter(
    #            default=lambda ctx: ctx.author,
    #        ),
    #    ) -> Message:
    #        """
    #        View information about a user.
    #        """
    #        # Fetch the user to get banner information
    #        fetched_user = await self.bot.fetch_user(user.id)
    #
    #        embed = Embed(color=config.Color.base)
    #        embed.title = f"{user}"
    #        embed.description = ""
    #        embed.set_thumbnail(url=user.display_avatar)
    #        embed.add_field(
    #            name="**Created**",
    #            value=(
    #                format_dt(user.created_at, "D")
    #                + "\n\n> "
    #                + format_dt(user.created_at, "R")
    #            ),
    #            inline=False,
    #        )
    #        if fetched_user.banner:
    #            embed.set_image(url=fetched_user.banner.url)
    #        if isinstance(user, Member) and user.joined_at:
    #            join_pos = sorted(
    #                user.guild.members,
    #                key=lambda member: member.joined_at or utcnow(),
    #            ).index(user)
    #
    #            embed.add_field(
    #                name=f"**Joined ({ordinal(join_pos + 1)})**",
    #                value=(
    #                    format_dt(user.joined_at, "D")
    #                    + "\n\n> "
    #                    + format_dt(user.joined_at, "R")
    #                ),
    #                inline=False,
    #            )
    #
    #            if user.premium_since:
    #                embed.add_field(
    #                    name="**Boosted**",
    #                    value=(
    #                        format_dt(user.premium_since, "D")
    #                        + "\n> "
    #                        + format_dt(user.premium_since, "R")
    #                    ),
    #                    inline=False,
    #                )
    #
    #            if roles := user.roles[1:]:
    #                embed.add_field(
    #                    name="**Roles**",
    #                    value=", ".join(role.mention for role in list(reversed(roles))[:5])
    #                    + (f" (+{len(roles) - 5})" if len(roles) > 5 else ""),
    #                    inline=False,
    #                )
    #
    #
    #        view = View()
    #
    #        if user.avatar:
    #            avatar_button = Button(
    #                style=ButtonStyle.link,
    #                label="Avatar",
    #                url=user.display_avatar.url
    #            )
    #            view.add_item(avatar_button)
    #
    #        if fetched_user.banner:
    #            banner_button = Button(
    #                style=ButtonStyle.link,
    #                label="Banner",
    #                url=fetched_user.banner.url
    #            )
    #            view.add_item(banner_button)
    #
    #        return await ctx.send(embed=embed, view=view)

    @group(
        aliases=["names", "nh"],
        example="@base",
        invoke_without_command=True,
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
            return await ctx.warn(f"**{user}** doesn't have any **names recorded**!")

        descriptions = [
            f"`{index:02}` **{record['username']}** ({format_dt(record['changed_at'], 'R')})"
            for index, record in enumerate(names, start=1)
        ]
        base_embed = Embed(title="Name History")
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

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

    @command(aliases=["rolelist"])
    async def roles(self, ctx: Context) -> Message:
        """
        View the server roles.
        """

        roles = list(reversed(ctx.guild.roles[1:]))
        if not roles:
            return await ctx.warn(f"**{ctx.guild}** doesn't have any roles!")

        descriptions = [
            f"`{index:02}` {role.mention} (`{role.id}`)"
            for index, role in enumerate(roles, start=1)
        ]
        base_embed = Embed(color=config.Color.base)
        if ctx.guild.icon:
            base_embed.set_author(
                name=f"Roles in {ctx.guild.name}", icon_url=ctx.guild.icon
            )

        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @command(example="@admin")
    async def inrole(self, ctx: Context, *, role: Optional[Role] = None) -> Message:
        """
        View members which have a role.
        """

        if role is None:
            return await ctx.send_help(ctx.command)

        members = role.members
        if not members:
            return await ctx.warn(f"{role.mention} doesn't have any members!")

        descriptions = [
            f"`{index:02}` {member.mention} (`{member.id}`)"
            for index, member in enumerate(members, start=1)
        ]
        base_embed = Embed(title=f"Members with {role}", color=config.Color.base)
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

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

        descriptions = [
            f"`{index:02}` {member.mention} (`{member.id}`)"
            for index, member in enumerate(
                sorted(members, key=lambda m: m.joined_at or utcnow(), reverse=True),
                start=1,
            )
        ]
        base_embed = Embed(
            color=config.Color.base,
        )
        if ctx.guild.icon:
            (base_embed.set_thumbnail(url=ctx.guild.icon),)
        base_embed.set_author(name=f"Bots in {ctx.guild.name}", icon_url=ctx.guild.icon)
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @group(invoke_without_command=True)
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

        descriptions = [
            f"`{index:02}` {member.mention} - boosted {format_dt(member.premium_since or utcnow(), 'R')}"
            for index, member in enumerate(
                sorted(
                    members,
                    key=lambda member: member.premium_since or utcnow(),
                    reverse=True,
                ),
                start=1,
            )
        ]
        base_embed = Embed(title="Boosters", color=config.Color.base)
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @boosters.command(name="lost")
    async def boosters_lost(self, ctx: Context) -> Message:
        """
        View all lost boosters.
        """

        records = await self.bot.db.fetch(
            """
            SELECT *
            FROM boosters_lost
            WHERE guild_id = $1
            ORDER BY ended_at DESC
            """,
            ctx.guild.id,
        )
        users = [
            f"`{index:02}` {user.mention} stopped {format_dt(record['ended_at'], 'R')} (lasted {short_timespan(record['lasted_for'])})"
            for index, record in enumerate(records, start=1)
            if (user := self.bot.get_user(record["user_id"]))
        ]
        if not users:
            return await ctx.warn("No boosters have been lost!")

        base_embed = Embed(title="Boosters Lost", color=config.Color.base)
        return await ctx.autopaginator(embed=base_embed, description=users)

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
            f"`{index:02}` [{invite.code}]({invite.url}) by {invite.inviter.mention if invite.inviter else '**Unknown**'} expires {format_dt(invite.expires_at, 'R') if invite.expires_at else '**Never**'}"
            for index, invite in enumerate(
                sorted(
                    invites,
                    key=lambda invite: invite.created_at or utcnow(),
                    reverse=True,
                ),
                start=1,
            )
        ]
        base_embed = Embed(title=f"Invites in {ctx.guild}", color=config.Color.base)
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
            f"`{index:02}` {emoji} ([`{emoji.id}`]({emoji.url}))"
            for index, emoji in enumerate(emojis, start=1)
        ]
        base_embed = Embed(title=f"Emojis in {ctx.guild}", color=config.Color.base)
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

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
        base_embed = Embed(title=f"Stickers in {ctx.guild}", color=config.Color.base)
        return await ctx.autopaginator(embed=base_embed, description=descriptions)

    @command(aliases=["firstmsg"])
    async def firstmessage(self, ctx: Context) -> Message:
        """
        View the first message sent.
        """

        message = [
            message async for message in ctx.channel.history(limit=1, oldest_first=True)
        ][0]
        return await ctx.neutral(
            f"Jump to the [**`first message`**]({message.jump_url}) sent by **{message.author}**"
        )

    @command()
    async def splash(self, ctx: Context) -> Message:
        """
        View the server splash.
        """

        if not ctx.guild.splash:
            return await ctx.warn("No **server splash** is set")

        embed = Embed(
            title=f"{ctx.guild}'s Splash",
            color=config.Color.base,
        )
        embed.set_image(url=ctx.guild.splash)
        return await ctx.send(embed=embed)

    @command(
        name="recentmembers",
        usage="<amount>",
        example="50",
        aliases=["recentusers", "recentjoins", "newmembers", "newusers", "recents"],
    )
    @has_permissions(manage_guild=True)
    async def recentmembers(self: "Information", ctx: Context, amount: int = 50):
        """View the most recent members to join the server"""
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

        await ctx.autopaginator(embed=embed, description=description, split=20)


#    @command(
#        name="avatarhistory",
#        aliases=["avh"],
#        invoke_without_command=True,
#    )
#    async def avatar_history(
#        self,
#        ctx: Context,
#        *,
#        user: Optional[Member | User],
#    ) -> Message:
#        """
#        View a user's previous avatars.
#        """
#
#        user = user or ctx.author
#        avatars = await self.bot.db.fetch(
#            """
#            SELECT asset
#            FROM metrics.avatars
#            WHERE user_id = $1
#            ORDER BY updated_at DESC
#            """,
#            user.id,
#        )
#
#        # Debug: Print the fetched avatars
#        print(f"Fetched avatars for {user}: {avatars}")
#
#        if not avatars:
#            return await ctx.warn(f"I haven't tracked any avatars for `{user}`!")
#
#        async with ctx.typing():
#            try:
#                collage_file = await collage(
#                    self.bot.session, [row["asset"] for row in avatars[:35]]
#                )
#            except ValueError as e:
#                return await ctx.warn(str(e))
#
#        embed = Embed(
#            title=("Your" if user == ctx.author else f"{user.name}'s")
#            + " avatar history",
#            description=(
#                f"Displaying `{len(avatars[:35])}` of {plural(avatars, md='`'):avatar}."
#                f"\n> View the full list including GIFs [__HERE__](https://api.skunkk.xyz/avatars/{user.id})."
#            ),
#        )
#        embed.set_image(url="attachment://collage.png")
#
#        return await ctx.send(
#            embed=embed,
#            file=collage_file,
#        )
#
#    @command(
#        name="clearavatars",
#        aliases=[
#            "sweep",
#            "clear",
#            "remove",
#        ],
#    )
#    async def avatar_history_clear(self: "Information", ctx: Context) -> Message:
#        """
#        Remove all of your tracked avatars.
#        """
#
#        await self.bot.db.execute(
#            """
#            DELETE FROM metrics.avatars
#            WHERE user_id = $1
#            """,
#            ctx.author.id,
#        )
#
#        return await ctx.approve("Successfully wiped your avatar history.")
#
