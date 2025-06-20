import config
import discord 
import logging

from contextlib import suppress
from typing import Annotated, List, Optional, cast
from aiohttp import TCPConnector, ClientSession
from discord.ext.commands import BucketType, cooldown

from datetime import datetime
from asyncpraw import reddit
from json import dumps
from asyncprawcore import AsyncPrawcoreException
from cashews import cache

from discord import (
    ButtonStyle,
    Embed,
    HTTPException,
    Interaction,
    Message,
    TextChannel,
    Thread,
)

from discord.ext.commands import (
    Cog,
    CommandError,
    command,
    flag,
    group,
    has_permissions,
    parameter,
)

from discord.utils import format_dt
from typing_extensions import Self
from yarl import URL
from io import BytesIO

from cogs.social.models.pinterest.user import Board as PinterestBoard
from config import AUTHORIZATION
from main import Evict
from tools import Button, View
from core.client import Context, FlagConverter
from tools.conversion import PartialAttachment, Status
from tools.formatter import plural
from managers.paginator import Paginator
from tools.conversion.script import Script
from cogs.social.classes.igstories import StoryPaginator

from .alerts import Alerts
from .feeds import feeds
from .feeds.base import Feed
from .models import (
    CashApp,
    Osu,
    PinterestLens,
    PinterestUser,
    Roblox,
    Snapchat,
)

from .models.soundcloud import User as SoundCloudUser
from .models.tiktok.user import User as TikTokUser
from .models.twitter.user import User as TwitterUser
# from .reposters import reposters
# from .reposters.base import Reposter

log = logging.getLogger(__name__)

class PinterestBoardSelection(View):
    value: Optional[PinterestBoard]
    boards: List[PinterestBoard]

    def __init__(self, ctx: Context, boards: List[PinterestBoard]):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.boards = boards
        self.value = None
        for board in boards:
            self.add_item(
                Button(
                    style=ButtonStyle.secondary,
                    label=board.name,
                    custom_id=board.id,
                )
            )

    async def callback(self, interaction: Interaction, button: Button):
        self.value = [board for board in self.boards if board.id == button.custom_id][0]
        self.stop()


class PinterestFlags(FlagConverter):
    board: Optional[str] = flag(description="The board to stream pins from.")
    embeds: Annotated[bool, Status] = flag(
        aliases=["embed"],
        description="Display an embed for pins.",
        default=True,
    )
    new: Annotated[bool, Status] = flag(
        aliases=["recent"],
        description="Only stream newly saved pins.",
        default=True,
    )


class Subreddit(reddit.Subreddit):
    @classmethod
    @cache(ttl="1h", key="reddit:{argument}")
    async def convert(cls, ctx: Context, argument: str) -> Self:
        async with ctx.typing():
            try:
                subreddit = await ctx.bot.reddit.subreddit(
                    argument.lstrip("r/"), fetch=True
                )
            except AsyncPrawcoreException as exc:
                raise CommandError("No **Subreddit** found with that name!") from exc

            return subreddit


class Social(Alerts, Cog):
    # reposters: List[Reposter]
    feeds: List[Feed]

    def __init__(self, bot: Evict):
        self.bot = bot
        self.description = (
            "Allows seamless integration between various social media platforms."
        )
        # self.reposters = []
        self.feeds = []

    # async def cog_load(self) -> None:
    #     for reposter in reposters:
    #         self.reposters.append(reposter(self.bot))

    #     for feed in feeds:
    #         self.feeds.append(feed(self.bot))

    #     return await super().cog_load()

    # async def cog_unload(self) -> None:
    #     for reposter in self.reposters:
    #         self.bot.remove_listener(reposter.listener, "on_message")

    #     for feed in self.feeds:
    #         await feed.stop()

    #     return await super().cog_unload()

    # @group(
    #     aliases=["event"],
    #     invoke_without_command=True,
    # )
    # @has_permissions(manage_guild=True)
    # async def reposter(self, ctx: Context) -> Message:
    #     """
    #     Fine tune reposters which can be used in your server.
    #     """
    #     return await ctx.send_help(ctx.command)

    # @reposter.command(name="prefix")
    # @has_permissions(manage_guild=True)
    # async def reposter_prefix(self, ctx: Context) -> Message:
    #     """
    #     Toggle the reposter prefix.
    #     """
    #     await ctx.settings.update(reposter_prefix=not ctx.settings.reposter_prefix)
    #     return await ctx.approve(
    #         f"{'Now' if ctx.settings.reposter_prefix else 'No longer'} using `evict` as the reposter prefix"
    #     )

    # @reposter.command(name="delete", aliases=["del"])
    # @has_permissions(manage_guild=True)
    # async def reposter_delete(self, ctx: Context) -> Message:
    #     """
    #     Toggle deleting reposted messages.
    #     """
    #     await ctx.settings.update(reposter_delete=not ctx.settings.reposter_delete)
    #     return await ctx.approve(
    #         f"Reposted messages will **{'now' if ctx.settings.reposter_delete else 'no longer'}** be deleted"
    #     )

    # @reposter.command(name="embed", aliases=["embeds"])
    # @has_permissions(manage_guild=True)
    # async def reposter_embed(self, ctx: Context) -> Message:
    #     """
    #     Toggle displaying an embed.
    #     """
    #     await ctx.settings.update(reposter_embed=not ctx.settings.reposter_embed)
    #     return await ctx.approve(
    #         f"Reposted messages will **{'now' if ctx.settings.reposter_embed else 'no longer'}** display an embed"
    #     )

    # @reposter.group(
    #     name="disable",
    #     invoke_without_command=True,
    #     example="#general tiktok",
    # )
    # @has_permissions(manage_guild=True)
    # async def reposter_disable(
    #     self,
    #     ctx: Context,
    #     channel: Optional[TextChannel],
    #     *,
    #     reposter: Reposter,
    # ) -> Message:
    #     """
    #     Disable a reposter in a specific channel.
    #     If no channel is provided, the reposter will be disabled globally.
    #     """
    #     if channel is None and not ctx.guild.text_channels:
    #         return await ctx.warn("This server has no text channels!")
    #     channel_ids: List[int] = [
    #         record["channel_id"]
    #         for record in await self.bot.db.fetch(
    #             """
    #             SELECT channel_id
    #             FROM reposters.disabled
    #             WHERE guild_id = $1
    #             AND reposter = $2
    #             """,
    #             ctx.guild.id,
    #             reposter.name,
    #         )
    #     ]
    #     if channel and channel.id in channel_ids:
    #         return await ctx.warn(
    #             f"The **{reposter}** reposter is already disabled in {channel.mention}!"
    #         )
    #     elif not channel and all(
    #         channel_id in channel_ids for channel_id in ctx.guild.text_channels
    #     ):
    #         return await ctx.warn(
    #             f"The **{reposter}** reposter is already disabled in all channels!"
    #         )
    #     await self.bot.db.executemany(
    #         """
    #         INSERT INTO reposters.disabled (guild_id, channel_id, reposter)
    #         VALUES ($1, $2, $3)
    #         ON CONFLICT (guild_id, channel_id, reposter)
    #         DO NOTHING
    #         """,
    #         [
    #             (ctx.guild.id, channel.id, reposter.name)
    #             for channel in (
    #                 ctx.guild.text_channels if channel is None else [channel]
    #             )
    #         ],
    #     )
    #     if not channel:
    #         return await ctx.approve(
    #             f"Disabled **{reposter}** reposting in {plural(len(ctx.guild.text_channels), md='**'):channel}"
    #         )
    #     return await ctx.approve(
    #         f"Disabled **{reposter}** reposting in {channel.mention}"
    #     )

    # @reposter_disable.command(
    #     name="list",
    #     aliases=["ls"],
    # )
    # @has_permissions(manage_guild=True)
    # async def command_disable_list(self, ctx: Context) -> Message:
    #     """
    #     View all reposter restrictions.
    #     """
    #     reposters = [
    #         f"**{record['reposter']}** - {', '.join(channel.mention for channel in channels[:2])}"
    #         + (f" (+{len(channels) - 2})" if len(channels) > 2 else "")
    #         for record in await self.bot.db.fetch(
    #             """
    #             SELECT reposter, ARRAY_AGG(channel_id) AS channel_ids
    #             FROM reposters.disabled
    #             WHERE guild_id = $1
    #             GROUP BY guild_id, reposter
    #             """,
    #             ctx.guild.id,
    #         )
    #         if (
    #             channels := [
    #                 channel
    #                 for channel_id in record["channel_ids"]
    #                 if (channel := ctx.guild.get_channel(channel_id))
    #             ]
    #         )
    #     ]
    #     if not reposters:
    #         return await ctx.warn("No reposters are disabled for this server!")
    #     paginator = Paginator(
    #         ctx,
    #         entries=reposters,
    #         embed=Embed(
    #             title="Reposters Disabled",
    #         ),
    #     )
    #     return await paginator.start()

    # @reposter.command(name="enable", example="#general tiktok")
    # @has_permissions(manage_guild=True)
    # async def reposter_enable(
    #     self,
    #     ctx: Context,
    #     channel: Optional[TextChannel],
    #     *,
    #     reposter: Reposter,
    # ) -> Message:
    #     """
    #     Enable a reposter in a specific channel.
    #     If no channel is provided, the reposter will be enabled globally.
    #     """
    #     channel_ids: List[int] = [
    #         record["channel_id"]
    #         for record in await self.bot.db.fetch(
    #             """
    #             SELECT channel_id
    #             FROM reposters.disabled
    #             WHERE guild_id = $1
    #             AND reposter = $2
    #             """,
    #             ctx.guild.id,
    #             reposter.name,
    #         )
    #     ]
    #     if channel and channel.id not in channel_ids:
    #         return await ctx.warn(
    #             f"The **{reposter}** reposter is already enabled in {channel.mention}!"
    #         )
    #     elif not channel and not channel_ids:
    #         return await ctx.warn(
    #             f"The **{reposter}** reposter is already enabled in all channels!"
    #         )
    #     await self.bot.db.execute(
    #         """
    #         DELETE FROM reposters.disabled
    #         WHERE guild_id = $1
    #         AND reposter = $2
    #         AND channel_id = ANY($3::BIGINT[])
    #         """,
    #         ctx.guild.id,
    #         reposter.name,
    #         channel_ids if channel is None else [channel.id],
    #     )
    #     if not channel:
    #         return await ctx.approve(
    #             f"Enabled **{reposter}** reposting in {plural(len(channel_ids), md='**'):channel}"
    #         )
    #     return await ctx.approve(
    #         f"Enabled **{reposter}** reposting in {channel.mention}"
    #     )

    @command(aliases=["rbx"], example="bingywingy03")
    async def roblox(
        self,
        ctx: Context,
        user: Roblox,
    ) -> Message:
        """
        Look up a user on Roblox.
        """

        embed = Embed(
            url=user.url,
            title=(
                f"{user.display_name} (@{user.name})"
                if user.display_name and user.display_name != user.name
                else f"@{user.name}"
            )
            + (" [BANNED]" if user.is_banned else ""),
            description=f"{format_dt(user.created_at)} ({format_dt(user.created_at, 'R')})\n{user.description}",
        )
        embed.set_thumbnail(url=await user.avatar_url())

        embed.add_field(
            name="**Followers**",
            value=f"{await user.follower_count():,}",
        )
        embed.add_field(
            name="**Following**",
            value=f"{await user.following_count():,}",
        )
        embed.add_field(
            name="**Friends**",
            value=f"{await user.friend_count():,}",
        )

        if presence := await user.presence():
            embed.add_field(
                name=f"**Presence ({presence.status.title()})**",
                value=(
                    (
                        f"> **Location:** {presence.location}"
                        if presence.location
                        else ""
                    )
                    + (
                        f"\n> **Last Online:** {format_dt(presence.last_online, 'R')}"
                        if presence.last_online
                        else ""
                    )
                ),
                inline=False,
            )

        if badges := await user.badges():
            embed.add_field(
                name=f"**Badges ({len(badges)})**",
                value=", ".join(
                    f"[`{badge.name}`]({badge.url})" for badge in badges[:5]
                ),
                inline=False,
            )

        if names := await user.names():
            embed.add_field(
                name="**Name History**",
                value=", ".join((f"`{name}`" for name in names[:17])),
                inline=False,
            )

        return await ctx.send(embed=embed)

    @command(aliases=["osu!"], example="peppy")
    async def osu(
        self,
        ctx: Context,
        username: str,
        map: int = 0,
    ) -> Message:
        """
        Look up a user on osu!
        """

        async with ctx.typing():
            user = await Osu.from_username(self.bot.session, username, map=map)
            if not user:
                return await ctx.warn(f"User `{username}` was not found!")

            embed = Embed(
                url=user.url,
                title=f"{user.username} ({user.map})",
                description=f"{format_dt(user.join_date)} ({format_dt(user.join_date, 'R')})",
            )
            embed.set_thumbnail(url=user.avatar_url)

            embed.add_field(
                name="**Level**",
                value=f"{user.level:.2f} (`{user.pp_raw:,} PP`)",
            )
            embed.add_field(
                name="**Accuracy**",
                value=f"{user.accuracy:.2f}%",
            )
            embed.add_field(
                name="**Score**",
                value=f"{user.total_score:,}",
            )
            embed.add_field(
                name="**Rank**",
                value=(
                    f"{user.ranked_score:,} (`{user.country}: #{user.pp_country_rank:,}`)"
                    "\n"
                    + " | ".join(
                        (
                            f"**A:** `{user.count_rank_a}`",
                            f"**S:** `{user.count_rank_s}`",
                            f"**SS:** `{user.count_rank_ss}`",
                        )
                    )
                ),
            )

        return await ctx.send(embed=embed)

    @group(
        aliases=["pint", "autopfp"],
        invoke_without_command=True,
        example="prettybiglies"
    )
    async def pinterest(
        self,
        ctx: Context,
        user: PinterestUser,
    ) -> Message:
        """
        Look up a user on Pinterest.
        You can also stream saved pins from a user.
        """

        embed = Embed(
            url=user.url,
            title=(
                f"{user.full_name} (@{user.username})"
                if user.full_name and user.full_name != user.username
                else f"@{user.username}"
            )
            + (" 🔒" if user.is_private_profile else ""),
            description=user.about or user.website_url,
        )
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(
            name="**Pins**",
            value=f"{user.pin_count:,}",
        )
        embed.add_field(
            name="**Following**",
            value=f"{user.following_count:,}",
        )
        embed.add_field(
            name="**Followers**",
            value=f"{user.follower_count:,}",
        )

        return await ctx.send(embed=embed)

    @pinterest.command(
        name="lens",
        aliases=["visual", "search"],
    )
    async def pinterest_lens(
        self,
        ctx: Context,
        attachment: PartialAttachment = parameter(
            default=PartialAttachment.fallback,
        ),
    ) -> Message:
        """
        Search an image using Pinterest Visual Search.
        """

        if not attachment.is_image():
            return await ctx.warn("The attachment must be an image!")

        async with ctx.typing():
            posts = await PinterestLens.from_image(
                self.bot.session,
                attachment.buffer,
            )
            if not posts:
                return await ctx.warn(
                    f"No results were found for [`{attachment.filename}`]({attachment.url})!"
                )

        paginator = Paginator(
            ctx,
            entries=[
                Embed(
                    url=post.url,
                    title=f"Pinterest Visual Search ({plural(post.repin_count):repin})",
                    description=post.description,
                ).set_image(
                    url=post.image_url,
                )
                for post in posts
            ],
        )
        return await paginator.start()

    @pinterest.command(
        name="add",
        aliases=["feed"],
        example="#pins prettybiglies",
    )
    @has_permissions(manage_channels=True)
    async def pinterest_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        user: PinterestUser,
        *,
        flags: PinterestFlags,
    ) -> Message:
        """
        Add a channel to receive saved pins from a user.
        """

        if user.is_private_profile:
            return await ctx.warn(
                f"You can't stream posts from [**{user}**]({user.url}) because their account is private!"
            )

        if not user.pin_count:
            return await ctx.warn(f"User [**{user}**]({user.url}) has no saved pins!")

        if ctx.author.id not in self.bot.owner_ids:
            data = cast(
                int,
                await self.bot.db.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM feeds.pinterest
                    WHERE guild_id = $1
                    AND channel_id = $2
                    """,
                    ctx.guild.id,
                    channel.id,
                ),
            )
            if data >= 3:
                return await ctx.warn(
                    "You can only receive saved pins from **3 users** per channel!"
                )

            data = cast(
                int,
                await self.bot.db.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM feeds.pinterest
                    WHERE guild_id = $1
                    AND channel_id = ANY($2::BIGINT[])
                    """,
                    ctx.guild.id,
                    [
                        _channel.id
                        for _channel in ctx.guild.text_channels
                        + list(ctx.guild.threads)
                    ],
                ),
            )
            if data >= 8:
                return await ctx.warn(
                    "You can only receive saved pins from **8 users** per server!"
                )

        board: Optional[PinterestBoard] = None
        if flags.board:
            boards = await user.boards(self.bot.session)
            if not boards:
                return await ctx.warn(
                    f"User [**{user}**]({user.url}) doesn't have any public boards!"
                )

            elif flags.board.lower() not in [board.name.lower() for board in boards]:
                view = PinterestBoardSelection(ctx, boards)
                message = await ctx.neutral(
                    "The specified board wasn't found!",
                    f"Select which board from [**{user}**]({user.url}) to stream",
                    view=view,
                )

                await view.wait()
                with suppress(HTTPException):
                    await message.delete()

                if not isinstance(view.value, PinterestBoard):
                    return message

                board = view.value

            else:
                board = [
                    board
                    for board in boards
                    if flags.board.lower() in board.name.lower()
                ][0]

        await self.bot.db.execute(
            """
            INSERT INTO feeds.pinterest (
                guild_id,
                channel_id,
                pinterest_id,
                pinterest_name,
                board,
                board_id,
                embeds,
                only_new
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (guild_id, pinterest_id)
            DO UPDATE SET
                channel_id = EXCLUDED.channel_id,
                board = EXCLUDED.board,
                board_id = EXCLUDED.board_id,
                embeds = EXCLUDED.embeds,
                only_new = EXCLUDED.only_new
            """,
            ctx.guild.id,
            channel.id,
            user.id,
            user.username,
            board.name if board else None,
            board.id if board else None,
            flags.embeds,
            flags.new,
        )
        return await ctx.approve(
            f"Now streaming **{'newly' if flags.new else 'old'} saved pins** from [**{user}**]({user.url}){f' (`{board.name}`)' if board else ''} to {channel.mention} {'with an embed' if flags.embeds else 'in batches of `3`'}",
        )

    @pinterest.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#pins prettybiglies",
    )
    @has_permissions(manage_channels=True)
    async def pinterest_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        user: PinterestUser,
    ) -> Message:
        """
        Remove a channel from receiving saved pins from a user.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.pinterest
            WHERE guild_id = $1
            AND pinterest_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"Saved pins from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"No longer streaming saved pins from [**{user}**]({user.url})"
        )

    @pinterest.command(name="embeds", example="#pins prettybiglies")
    @has_permissions(manage_channels=True)
    async def pinterest_embeds(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        user: PinterestUser,
    ) -> Message:
        """
        Enable or disable embeds when a pin is received.
        """

        status = cast(
            Optional[bool],
            await self.bot.db.fetchval(
                """
                UPDATE feeds.pinterest
                SET embeds = NOT embeds
                WHERE guild_id = $1
                AND pinterest_id = $2
                RETURNING embeds
                """,
                ctx.guild.id,
                user.id,
            ),
        )
        if status is None:
            return await ctx.warn(
                f"Saved pins from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"{'Now' if status else 'No longer'} displaying **embeds** for [**{user}**]({user.url})"
        )

    @pinterest.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_channels=True)
    async def pinterest_clear(self, ctx: Context) -> Message:
        """
        Remove all Pinterest feeds.
        """

        await ctx.prompt(
            "Are you sure you want to remove all **Pinterest feeds**?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.pinterest
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No **Pinterest feeds** exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):Pinterest feed}"
        )

    @pinterest.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def pinterest_list(self, ctx: Context) -> Message:
        """
        View all Pinterest feeds.
        """

        channels = [
            f"{channel.mention} - [**@{record['pinterest_name']}**](https://pinterest.com/{record['pinterest_name']}) (`{record['board'] or 'all'}`)"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, pinterest_name, board
                FROM feeds.pinterest
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No **Pinterest feeds** exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="Pinterest Feeds"),
        )
        return await paginator.start()

    @command(aliases=["snap"], example="resentdev")
    @cooldown(1, 5, BucketType.user)
    async def snapchat(
        self,
        ctx: Context,
        user: Snapchat,
    ) -> Message:
        """
        Look up a user on Snapchat.
        """

        embed = Embed(
            url=user.url,
            title=(
                f"{user.display_name} (@{user.username})"
                if user.display_name and user.display_name != user.username
                else f"@{user.username}"
            ),
            description=user.description,
        )
        embed.set_image(url=user.bitmoji_url or user.snapcode_url)

        return await ctx.send(embed=embed)

    @command(aliases=["ca"], example="evictbot")
    @cooldown(1, 5, BucketType.user)
    async def cashapp(
        self,
        ctx: Context,
        user: CashApp,
    ) -> Message:
        """
        Look up a user on CashApp.
        """

        embed = Embed(
            color=user.avatar.color,
            url=user.url,
            title=(
                f"{user.display_name} (@{user.username})"
                if user.display_name and user.display_name != user.username
                else f"@{user.username}"
            ),
        )
        embed.set_image(url=user.avatar.url)

        return await ctx.send(embed=embed)

    @command(aliases=["x", "tw"], example="evictbot")
    @cooldown(1, 5, BucketType.user)
    async def twitter(self, ctx: Context, *, user: str) -> Message:
        """Fetch information about a Twitter user."""

        async with ctx.typing():
            connector = TCPConnector()

            async with ClientSession(connector=connector) as session:
                url = f"https://api.fulcrum.lol/twitter?username={user}"
                async with session.get(url, proxy=config.CLIENT.WARP) as response:
                    if response.status != 200:
                        return await ctx.warn(
                            f"The user ``{user}`` is an **invalid** username or the API is down!"
                        )

                    twitter_data = await response.json()

        username = twitter_data["username"]
        bio = twitter_data["bio"]
        avatar = twitter_data["avatar"]
        url = twitter_data["url"]
        followers = twitter_data["followers"]
        following = twitter_data["following"]
        display_name = twitter_data["display_name"]
        posts = twitter_data["posts"]

        followers_formatted = f"{followers:,}" if followers > 1000 else str(followers)
        following_formatted = f"{following:,}" if following > 1000 else str(following)
        posts_formatted = f"{posts:,}" if posts > 1000 else str(posts)

        embed = Embed(title=f"{display_name} (@{username})", url=url, description=bio)
        embed.add_field(name="Posts", value=posts_formatted)
        embed.add_field(name="Following", value=following_formatted)
        embed.add_field(name="Followers", value=followers_formatted)
        embed.set_thumbnail(url=avatar)
        return await ctx.send(embed=embed)

    @command(example="evictbot", aliases=["instagramuser"])
    @cooldown(1, 5, BucketType.guild)
    async def instagramu(self, ctx: Context, *, user: str) -> Message:
        """
        Fetch information about an Instagram user.
        """
        async with ctx.typing():
            connector = TCPConnector()

            async with ClientSession(connector=connector) as session:
                url = f"https://api.fulcrum.lol/instagram?username={user}"
                async with session.get(url, proxy=config.CLIENT.WARP) as response:
                    if response.status != 200:
                        return await ctx.warn(
                            f"The user ``{user}`` is an **invalid** username or the API is down!"
                        )

                    instagram_data = await response.json()

        username = instagram_data["username"]
        bio = instagram_data["bio"]
        avatar = instagram_data["avatar_url"]
        url = instagram_data["url"]
        followers = instagram_data["followers"]
        following = instagram_data["following"]
        full_name = instagram_data["full_name"]
        posts = instagram_data["posts"]

        followers_formatted = f"{followers:,}" if followers > 1000 else str(followers)
        following_formatted = f"{following:,}" if following > 1000 else str(following)
        posts_formatted = f"{posts:,}" if posts > 1000 else str(posts)

        embed = Embed(
            title=f"{full_name} (@{username})", 
            url=f"{url}", 
            description=f"{bio}"
        )

        embed.add_field(
            name="Posts", 
            value=posts_formatted
        )
        
        embed.add_field(
            name="Following", 
            value=following_formatted
        )
        
        embed.add_field(
            name="Followers", 
            value=followers_formatted
        )
        embed.set_thumbnail(url=avatar)
        
        return await ctx.send(embed=embed)
    
    @command(aliases=["igstory", "igstories"], example="evictbot")
    @cooldown(1, 5, BucketType.guild)
    async def instagramstory(self, ctx: Context, *, user: str) -> Message:
        """Fetch stories on an Instagram user."""

        async with ctx.typing():
            connector = TCPConnector()

            async with ClientSession(connector=connector) as session:
                url = f"https://api.fulcrum.lol/instagram/story?username={user}"
                async with session.get(url, proxy=config.CLIENT.WARP) as response:
                    if response.status != 200:
                        return await ctx.warn(
                            f"The user ``{user}`` is an **invalid** username or the API is down!"
                        )

                    instagram_data = await response.json()

        instagram_url = f"https://instagram.com/{user}"
        story_data = instagram_data['stories']
        count = instagram_data['count']
        if not story_data:
            return await ctx.warn(f"No stories found for user ``{user}``!")

        embeds = []
        files = []
        for idx, story in enumerate(story_data, start=1):
            story_url = story['url']
            is_video = story_url.endswith('.mp4') or 'video_dashinit' in story_url or 'strext=1' in story_url
            
            embed = Embed(
                title=f"{user} ({count})",
                url=f"{instagram_url}",
                timestamp = datetime.now()
            )
            embed.set_footer()
            embeds.append(embed)

            async with ClientSession() as session:
                async with session.get(story_url) as resp:
                    if resp.status == 200:
                        media_data = await resp.read()
                        
                        file = discord.File(
                            fp=BytesIO(media_data),
                            filename=f"story_{idx}.{'mp4' if is_video else 'jpg'}"
                        )
                        files.append(file)

        if not embeds:
            return await ctx.warn(f"Failed to process any stories for user ``{user}``!")
        
        paginator = StoryPaginator(
            ctx,
            entries=embeds,
            files=files
        )
        return await paginator.start()

    @group(
        aliases=["tt"],
        invoke_without_command=True,
        example="evictbot"
    )
    @cooldown(1, 5, BucketType.user)
    async def tiktok(self, ctx: Context, user: TikTokUser) -> Message:
        """
        Look up a user on TikTok.
        You can also stream new posts from a user.
        """

        embed = Embed(
            url=user.url,
            title=(
                f"{user.full_name} (@{user.username})"
                if user.full_name and user.full_name != user.username
                else f"@{user.username}"
            ),
            description=user.biography,
        )
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(
            name="**Likes**",
            value=f"{user.statistics.heart_count:,}",
        )
        embed.add_field(
            name="**Following**",
            value=f"{user.statistics.following_count:,}",
        )
        embed.add_field(
            name="**Followers**",
            value=f"{user.statistics.follower_count:,}",
        )

        return await ctx.send(embed=embed)

    @tiktok.command(
        name="add",
        aliases=["feed"],
        example="#tiktok evictbot"
    )
    @cooldown(1, 5, BucketType.user)
    @has_permissions(manage_channels=True)
    async def tiktok_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        user: TikTokUser,
    ) -> Message:
        """
        Add a channel to receive posts from a user.
        """

        if user.is_private:
            return await ctx.warn(
                f"You can't stream posts from [**{user}**]({user.url}) because their account is private!"
            )

        if ctx.author.id not in self.bot.owner_ids:
            records = cast(
                int,
                await self.bot.db.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM feeds.tiktok
                    WHERE guild_id = $1
                    AND channel_id = ANY($2::BIGINT[])
                    """,
                    ctx.guild.id,
                    [
                        _channel.id
                        for _channel in ctx.guild.text_channels
                        + list(ctx.guild.threads)
                    ],
                ),
            )
            if records >= 5:
                return await ctx.warn(
                    "You can only receive posts from **5 users** at a time!"
                )

        await self.bot.db.execute(
            """
            INSERT INTO feeds.tiktok (
                guild_id,
                channel_id,
                tiktok_id,
                tiktok_name
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, tiktok_id)
            DO UPDATE SET channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id,
            user.id,
            user.username,
        )
        return await ctx.approve(
            f"Now streaming new posts from [**{user}**]({user.url}) to {channel.mention}"
        )

    @tiktok.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#tiktok evictbot"
    )
    @has_permissions(manage_channels=True)
    async def tiktok_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        user: TikTokUser,
    ) -> Message:
        """
        Remove a channel from receiving posts from a user.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.tiktok
            WHERE guild_id = $1
            AND tiktok_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"Posts from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"No longer streaming posts from [**{user}**]({user.url})"
        )

    @tiktok.group(
        name="message",
        aliases=["msg"],
        invoke_without_command=True,
        example="#tiktok evictbot Hello!"
    )
    @has_permissions(manage_channels=True)
    async def tiktok_message(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        user: Optional[TikTokUser],
        *,
        script: Script,
    ) -> Message:
        """
        Set a message to be sent when a post is received.
        """

        if not user:
            await ctx.prompt(
                "You didn't specify a valid **TikTok username**!",
                "Are you sure you want to set the message for **ALL** feeds?",
            )

            result = await self.bot.db.execute(
                """
                UPDATE feeds.tiktok
                SET template = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                script.template,
            )
            if result == "UPDATE 0":
                return await ctx.warn("No **TikTok feeds** were modified!")

            return await ctx.approve(
                "Updated the post message for all **TikTok feeds**"
            )

        result = await self.bot.db.execute(
            """
            UPDATE feeds.tiktok
            SET template = $3
            WHERE guild_id = $1
            AND tiktok_id = $2
            """,
            ctx.guild.id,
            user.id,
            script.template,
        )
        if result == "UPDATE 0":
            return await ctx.warn(
                f"Posts from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"Updated the post message for [**{user}**]({user.url})"
        )

    @tiktok_message.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#tiktok evictbot"
    )
    @has_permissions(manage_channels=True)
    async def tiktok_message_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        user: Optional[TikTokUser],
    ) -> Message:
        """
        Remove the message sent when a post is received.
        """

        if not user:
            await ctx.prompt(
                "You didn't specify a valid **TikTok username**!",
                "Are you sure you want to remove the message for **ALL** feeds?",
            )

            result = await self.bot.db.execute(
                """
                UPDATE feeds.tiktok
                SET template = NULL
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if result == "UPDATE 0":
                return await ctx.warn("No **TikTok feeds** were modified!")

            return await ctx.approve("Reset the post message for all **TikTok feeds**")

        result = await self.bot.db.execute(
            """
            UPDATE feeds.tiktok
            SET template = NULL
            WHERE guild_id = $1
            AND tiktok_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if result == "UPDATE 0":
            return await ctx.warn(
                f"Posts from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(f"Reset the post message for [**{user}**]({user.url})")

    @tiktok.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_channels=True)
    async def tiktok_clear(self, ctx: Context) -> Message:
        """
        Remove all TikTok feeds.
        """

        await ctx.prompt(
            "Are you sure you want to remove all **TikTok feeds**?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.tiktok
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No **TikTok feeds** exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):TikTok feed}"
        )

    @tiktok.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def tiktok_list(self, ctx: Context) -> Message:
        """
        View all TikTok feeds.
        """

        channels = [
            f"{channel.mention} - [**@{record['tiktok_name']}**](https://tiktok.com/@{record['tiktok_name']})"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, tiktok_name
                FROM feeds.tiktok
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No **TikTok feeds** exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="TikTok Feeds"),
        )
        return await paginator.start()

    @group(
        aliases=["sc"],
        invoke_without_command=True,
        example="evictbot"
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
                "Authorization": AUTHORIZATION.SOUNDCLOUD,
            },
        )
        data = await response.json()
        if not data["collection"]:
            return await ctx.warn(f"No results found for **{query}**!")

        paginator = Paginator(
            ctx,
            entries=[track["permalink_url"] for track in data["collection"]],
        )
        return await paginator.start()

    @soundcloud.command(
        name="add",
        aliases=["feed"],
        example="#music prettybiglies"
    )
    @has_permissions(manage_channels=True)
    async def soundcloud_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        user: SoundCloudUser,
    ) -> Message:
        """
        Add a channel to receive tracks from a user.
        """

        if ctx.author.id not in self.bot.owner_ids:
            records = cast(
                int,
                await self.bot.db.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM feeds.soundcloud
                    WHERE guild_id = $1
                    AND channel_id = ANY($2::BIGINT[])
                    """,
                    ctx.guild.id,
                    [
                        _channel.id
                        for _channel in ctx.guild.text_channels
                        + list(ctx.guild.threads)
                    ],
                ),
            )
            if records >= 5:
                return await ctx.warn(
                    "You can only receive tracks from **5 users** at a time!"
                )

        await self.bot.db.execute(
            """
            INSERT INTO feeds.soundcloud (
                guild_id,
                channel_id,
                soundcloud_id,
                soundcloud_name
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, soundcloud_id)
            DO UPDATE SET channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id,
            user.id,
            user.permalink,
        )
        return await ctx.approve(
            f"Now streaming new tracks from [**{user}**]({user.url}) to {channel.mention}"
        )

    @soundcloud.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#music prettybiglies"
    )
    @has_permissions(manage_channels=True)
    async def soundcloud_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        user: SoundCloudUser,
    ) -> Message:
        """
        Remove a channel from receiving tracks from a user.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.soundcloud
            WHERE guild_id = $1
            AND soundcloud_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"Tracks from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"No longer streaming tracks from [**{user}**]({user.url})"
        )

    @soundcloud.group(
        name="message",
        aliases=["msg"],
        invoke_without_command=True,
        example="#music prettybiglies Hello!"
    )
    @has_permissions(manage_channels=True)
    async def soundcloud_message(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        user: Optional[SoundCloudUser],
        *,
        script: Script,
    ) -> Message:
        """
        Set a message to be sent when a track is received.
        """

        if not user:
            await ctx.prompt(
                "You didn't specify a valid **SoundCloud username**!",
                "Are you sure you want to set the message for **ALL** feeds?",
            )

            result = await self.bot.db.execute(
                """
                UPDATE feeds.soundcloud
                SET template = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                script.template,
            )
            if result == "UPDATE 0":
                return await ctx.warn("No **SoundCloud feeds** were modified!")

            return await ctx.approve(
                "Updated the track message for all **SoundCloud feeds**"
            )

        result = await self.bot.db.execute(
            """
            UPDATE feeds.soundcloud
            SET template = $3
            WHERE guild_id = $1
            AND soundcloud_id = $2
            """,
            ctx.guild.id,
            user.id,
            script.template,
        )
        if result == "UPDATE 0":
            return await ctx.warn(
                f"Tracks from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"Updated the track message for [**{user}**]({user.url})"
        )

    @soundcloud_message.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def soundcloud_message_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        user: Optional[SoundCloudUser],
    ) -> Message:
        """
        Remove the message sent when a track is received.
        """

        if not user:
            await ctx.prompt(
                "You didn't specify a valid **SoundCloud username**!",
                "Are you sure you want to remove the message for **ALL** feeds?",
            )

            result = await self.bot.db.execute(
                """
                UPDATE feeds.soundcloud
                SET template = NULL
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if result == "UPDATE 0":
                return await ctx.warn("No **SoundCloud feeds** were modified!")

            return await ctx.approve(
                "Reset the track message for all **SoundCloud feeds**"
            )

        result = await self.bot.db.execute(
            """
            UPDATE feeds.soundcloud
            SET template = NULL
            WHERE guild_id = $1
            AND soundcloud_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if result == "UPDATE 0":
            return await ctx.warn(
                f"Tracks from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"Reset the track message for [**{user}**]({user.url})"
        )

    @soundcloud.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_channels=True)
    async def soundcloud_clear(self, ctx: Context) -> Message:
        """
        Remove all SoundCloud feeds.
        """

        await ctx.prompt(
            "Are you sure you want to remove all **SoundCloud feeds**?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.soundcloud
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No **SoundCloud feeds** exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):SoundCloud feed}"
        )

    @soundcloud.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def soundcloud_list(self, ctx: Context) -> Message:
        """
        View all SoundCloud feeds.
        """

        channels = [
            f"{channel.mention} - [**@{record['soundcloud_name']}**](https://soundcloud.com/{record['soundcloud_name']})"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, soundcloud_name
                FROM feeds.soundcloud
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No **SoundCloud feeds** exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="SoundCloud Feeds"),
        )
        return await paginator.start()

    @group(
        aliases=["subreddit"],
        invoke_without_command=True,
        example="aww"
    )
    async def reddit(self, ctx: Context, *, subreddit: Subreddit) -> Message:
        """
        Look up a Subreddit.
        You can also stream new submissions.
        """

        embed = Embed(
            url=f"https://reddit.com{subreddit.url}",
            title=subreddit.title or subreddit.display_name,
        )
        embed.set_thumbnail(url=subreddit.community_icon)

        embed.add_field(
            name="**Subscribers**",
            value=f"{subreddit.subscribers:,}",
        )
        embed.add_field(
            name="**Active Users**",
            value=f"{subreddit.accounts_active:,}",
        )
        embed.set_image(url=subreddit.banner_background_image)

        return await ctx.send(embed=embed)

    @reddit.command(
        name="add",
        aliases=["feed"],
        example="#reddit aww"
    )
    @has_permissions(manage_channels=True)
    async def reddit_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        subreddit: Subreddit,
    ) -> Message:
        """
        Add a channel to receive submissions from a Subreddit.
        """

        if ctx.author.id not in self.bot.owner_ids:
            records = cast(
                int,
                await self.bot.db.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM feeds.reddit
                    WHERE guild_id = $1
                    AND channel_id = ANY($2::BIGINT[])
                    """,
                    ctx.guild.id,
                    [
                        _channel.id
                        for _channel in ctx.guild.text_channels
                        + list(ctx.guild.threads)
                    ],
                ),
            )
            if records >= 15:
                return await ctx.warn(
                    "You can only receive posts from **15 subreddits** at a time!"
                )

        await self.bot.db.execute(
            """
            INSERT INTO feeds.reddit (
                guild_id,
                channel_id,
                subreddit_name
            )
            VALUES ($1, $2, $3)
            ON CONFLICT (guild_id, subreddit_name)
            DO UPDATE SET channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id,
            subreddit.display_name,
        )
        return await ctx.approve(
            f"Now streaming new submissions from [**{subreddit.display_name_prefixed}**](https://reddit.com{subreddit.url}) to {channel.mention}"
        )

    @reddit.command(
        name="remove",
        aliases=["delete", "del", "rm"],
        example="#reddit aww"
    )
    @has_permissions(manage_channels=True)
    async def reddit_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        subreddit: Subreddit,
    ) -> Message:
        """
        Remove a channel from receiving submissions from a Subreddit.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.reddit
            WHERE guild_id = $1
            AND subreddit_name = $2
            """,
            ctx.guild.id,
            subreddit.display_name,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"Submissions from [**{subreddit.display_name_prefixed}**](https://reddit.com{subreddit.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"No longer streaming submissions from [**{subreddit.display_name_prefixed}**](https://reddit.com{subreddit.url})"
        )

    @reddit.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_channels=True)
    async def reddit_clear(self, ctx: Context) -> Message:
        """
        Remove all Subreddit feeds.
        """

        await ctx.prompt(
            "Are you sure you want to remove all **Subreddit feeds**?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.reddit
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No **Subreddit feeds** exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):Subreddit feed}"
        )

    @reddit.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def reddit_list(self, ctx: Context) -> Message:
        """
        View all Subreddit feeds.
        """

        channels = [
            f"{channel.mention} - [**r/{record['subreddit_name']}**](https://reddit.com/r/{record['subreddit_name']})"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, subreddit_name
                FROM feeds.reddit
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No **Subreddit feeds** exist for this server!")

        paginator = Paginator(
            ctx,
            entries=channels,
            embed=Embed(title="Subreddit Feeds"),
        )
        return await paginator.start()
