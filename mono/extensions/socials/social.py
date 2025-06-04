from contextlib import suppress
from io import BytesIO
from typing import Annotated, List, Literal, Optional, cast

from aiohttp import ClientSession
from asyncpraw import reddit
from asyncprawcore import AsyncPrawcoreException
from cashews import cache
from config import Authorization
from core.client.context import Context
from core.managers.parser import Button, Script, View
from core.Mono import Mono
from core.tools import FlagConverter, Status, plural
from core.tools.converters.kayo import PartialAttachment
from discord import (ButtonStyle, Color, Embed, File, HTTPException,
                     Interaction, Message, TextChannel, Thread, app_commands)
from discord.ext.commands import (BucketType, Cog, CommandError, cooldown,
                                  flag, group, has_permissions, hybrid_command,
                                  parameter)
from discord.utils import as_chunks, format_dt
from extensions.socials.models.beastars.beatstars import User as BeatStarsUser
from extensions.socials.models.pinterest.user import Board as PinterestBoard
from extensions.socials.reposters.extraction.instagram import Instagram
from loguru import logger as log
from typing_extensions import Self
from yarl import URL

from .feeds import feeds
from .feeds.base import Feed
from .models import PinterestLens, PinterestUser
from .models.soundcloud import User as SoundCloudUser
from .models.youtube.channel import Channel as YouTubeChannel
from .reposters import reposters
from .reposters.base import Reposter

# from .models.twitter.user import User as TwitterUser





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


class Social(Cog):
    instagram_client: Instagram
    reposters: List[Reposter]
    feeds: List[Feed]

    def __init__(self, bot: Mono):
        self.bot = bot
        self.reposters = []
        self.feeds = []
        self.instagram_client = Instagram(bot)

    async def cog_load(self) -> None:
        for reposter in reposters:
            self.reposters.append(reposter(self.bot))

        for feed in feeds:
            self.feeds.append(feed(self.bot))

        return await super().cog_load()

    async def cog_unload(self) -> None:
        for reposter in self.reposters:
            self.bot.remove_listener(reposter.listener, "on_message")

        for feed in self.feeds:
            await feed.stop()

        return await super().cog_unload()

    @group(
        aliases=["sc"],
        invoke_without_command=True,
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
                "Authorization": Authorization.SOUNDCLOUD,
            },
        )
        data = await response.json()
        if not data["collection"]:
            return await ctx.warn(f"No results found for **{query}**!")

        links = [track["permalink_url"] for track in data["collection"]]
        pages = [f"({i + 1}/{len(links)}) {link}" for i, link in enumerate(links)]

        return await ctx.paginate(pages=pages)

    @soundcloud.command(
        name="add",
        aliases=["feed"],
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

        embed = Embed(title="SoundCloud Feeds")
        return await ctx.autopaginator(embed=embed, description=channels)

    @group(
        aliases=["pint", "autopfp"],
        invoke_without_command=True,
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

        embeds = [
            Embed(
                url=post.url,
                title=f"Pinterest Visual Search ({plural(post.repin_count):repin})",
                description=post.description,
            ).set_image(
                url=post.image_url,
            )
            for post in posts
        ]

        # Use autopaginator to handle pagination
        return await ctx.autopaginator(embed=Embed(), description=embeds)

    @pinterest.command(
        name="add",
        aliases=["feed"],
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

        if user.username == "teenagemaniac" and ctx.author.id not in self.bot.owner_ids:
            return await ctx.reply("no")

        elif user.is_private_profile:
            return await ctx.warn(
                f"You can't stream posts from [**{user}**]({user.url}) because their account is private!"
            )

        elif not user.pin_count:
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

    @pinterest.command(name="embeds")
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

        embed = Embed(title="Pinterest Feeds")

        # Use autopaginator to handle pagination
        return await ctx.autopaginator(embed=embed, description=channels)

    @group(
        aliases=["yt"],
        invoke_without_command=True,
    )
    async def youtube(self, ctx: Context, *, query: str) -> Message:
        """
        Search a query on YouTube.
        You can also stream new videos from a user.
        """

        command = self.bot.get_command("google youtube")
        if not command:
            return await ctx.reply("This command is currently disabled!")

        return await command(ctx, query=query)

    @youtube.command(
        name="add",
        aliases=["feed"],
    )
    @has_permissions(manage_channels=True)
    async def youtube_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        user: YouTubeChannel,
    ) -> Message:
        """
        Add a channel to receive videos from a user.
        """

        if ctx.author.id not in self.bot.owner_ids:
            records = cast(
                int,
                await self.bot.db.fetchval(
                    """
                    SELECT COUNT(*)
                    FROM feeds.youtube
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
                    "You can only receive videos from **15 users** at a time!"
                )

        await self.bot.db.execute(
            """
            INSERT INTO feeds.youtube (
                guild_id,
                channel_id,
                youtube_id,
                youtube_name
            )
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (guild_id, youtube_id)
            DO UPDATE SET channel_id = EXCLUDED.channel_id
            """,
            ctx.guild.id,
            channel.id,
            user.id,
            user.name,
        )

        return await ctx.approve(
            f"Now streaming new videos from [**{user}**]({user.url}) to {channel.mention}"
        )

    @youtube.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def youtube_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        user: YouTubeChannel,
    ) -> Message:
        """
        Remove a channel from receiving videos from a user.
        """

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.youtube
            WHERE guild_id = $1
            AND youtube_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if result == "DELETE 0":
            return await ctx.warn(
                f"Videos from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"No longer streaming videos from [**{user}**]({user.url})"
        )

    @youtube.command(name="shorts")
    @has_permissions(manage_channels=True)
    async def youtube_shorts(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        user: YouTubeChannel,
    ) -> Message:
        """
        Enable or disable YouTube Shorts notifications.
        """

        status = cast(
            Optional[bool],
            await self.bot.db.fetchval(
                """
                UPDATE feeds.youtube
                SET shorts = NOT shorts
                WHERE guild_id = $1
                AND youtube_id = $2
                RETURNING shorts
                """,
                ctx.guild.id,
                user.id,
            ),
        )
        if status is None:
            return await ctx.warn(
                f"Videos from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"{'Now' if status else 'No longer'} receiving **YouTube Shorts** for [**{user}**]({user.url})"
        )

    @youtube.group(
        name="message",
        aliases=["msg"],
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def youtube_message(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        user: Optional[YouTubeChannel],
        *,
        script: Script,
    ) -> Message:
        """
        Set a message to be sent when a video is received.
        """

        if not user:
            await ctx.prompt(
                "You didn't specify a valid **YouTube channel**!",
                "Are you sure you want to set the message for **ALL** feeds?",
            )

            result = await self.bot.db.execute(
                """
                UPDATE feeds.youtube
                SET template = $2
                WHERE guild_id = $1
                """,
                ctx.guild.id,
                script.template,
            )
            if result == "UPDATE 0":
                return await ctx.warn("No **YouTube feeds** were modified!")

            return await ctx.approve(
                "Updated the video message for all **YouTube feeds**"
            )

        result = await self.bot.db.execute(
            """
            UPDATE feeds.youtube
            SET template = $3
            WHERE guild_id = $1
            AND youtube_id = $2
            """,
            ctx.guild.id,
            user.id,
            script.template,
        )
        if result == "UPDATE 0":
            return await ctx.warn(
                f"Videos from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"Updated the video message for [**{user}**]({user.url})"
        )

    @youtube_message.command(
        name="remove",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_channels=True)
    async def youtube_message_remove(
        self,
        ctx: Context,
        channel: Optional[TextChannel | Thread],
        *,
        user: Optional[YouTubeChannel],
    ) -> Message:
        """
        Remove the message sent when a video is received.
        """

        if not user:
            await ctx.prompt(
                "You didn't specify a valid **YouTube channel**!",
                "Are you sure you want to remove the message for **ALL** feeds?",
            )

            result = await self.bot.db.execute(
                """
                UPDATE feeds.youtube
                SET template = NULL
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if result == "UPDATE 0":
                return await ctx.warn("No **YouTube feeds** were modified!")

            return await ctx.approve(
                "Reset the video message for all **YouTube feeds**"
            )

        result = await self.bot.db.execute(
            """
            UPDATE feeds.youtube
            SET template = NULL
            WHERE guild_id = $1
            AND youtube_id = $2
            """,
            ctx.guild.id,
            user.id,
        )
        if result == "UPDATE 0":
            return await ctx.warn(
                f"Videos from [**{user}**]({user.url}) are not being streamed!"
            )

        return await ctx.approve(
            f"Reset the video message for [**{user}**]({user.url})"
        )

    @youtube.command(
        name="clear",
        aliases=["clean", "reset"],
    )
    @has_permissions(manage_channels=True)
    async def youtube_clear(self, ctx: Context) -> Message:
        """
        Remove all YouTube feeds.
        """

        await ctx.prompt(
            "Are you sure you want to remove all **YouTube feeds**?",
        )

        result = await self.bot.db.execute(
            """
            DELETE FROM feeds.youtube
            WHERE guild_id = $1
            """,
            ctx.guild.id,
        )
        if result == "DELETE 0":
            return await ctx.warn("No **YouTube feeds** exist for this server!")

        return await ctx.approve(
            f"Successfully  removed {plural(result, md='`'):YouTube feed}"
        )

    @youtube.command(
        name="list",
        aliases=["ls"],
    )
    @has_permissions(manage_guild=True)
    async def youtube_list(self, ctx: Context) -> Message:
        """
        View all YouTube feeds.
        """

        channels = [
            f"{channel.mention} - [**{record['youtube_name']}**](https://youtube.com/channel/{record['youtube_id']})"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, youtube_id, youtube_name
                FROM feeds.youtube
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
        ]
        if not channels:
            return await ctx.warn("No **YouTube feeds** exist for this server!")

        embed = Embed(title="YouTube Feeds")
        return await ctx.autopaginator(embed=embed, description=channels, split=10)

    @hybrid_command(name="beatstars")
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def beatstars(self, ctx: Context, username: str) -> Message:
        """
        Fetch and display BeatStars user information.
        """
        log.debug(
            f"Fetching BeatStars user: {username}"
        )  # Log the username being fetched
        user = await BeatStarsUser.fetch(ctx.bot.session, username)
        if user is None:
            log.debug(
                f"No BeatStars user found for username: {username}"
            )  # Log if no user is found
            return await ctx.warn(
                f"No **BeatStars user** found with the username **{username}**!"
            )

        # Fetch followers count
        followers_count = await BeatStarsUser.fetch_followers(
            ctx.bot.session, user.permalink
        )
        user.followers_count = followers_count if followers_count is not None else 0

        embed = Embed(
            title=f"{user.username} (@{user.username})",
            description=user.bio or "No bio available.",
            url=user.url,
        )
        embed.set_thumbnail(url=user.avatar_url)
        embed.add_field(name="Followers", value=user.followers_count, inline=True)
        embed.add_field(name="Plays", value=user.plays, inline=True)
        embed.add_field(
            name="Location", value=user.location or "Not specified", inline=True
        )
        #        embed.add_field(name="Tracks", value=user.track_count, inline=True)  # Added track count field

        return await ctx.send(embed=embed)

    #    @group(
    #        aliases=["tw", "x"],
    #        invoke_without_command=True,
    #    )
    #    async def twitter(
    #        self,
    #        ctx: Context,
    #        user: TwitterUser,
    #    ) -> Message:
    #        """
    #        Look up a user on Twitter.
    #        You can also stream new tweets from a user.
    #        """
    #
    #        embed = Embed(
    #            url=user.url,
    #            title=(
    #                f"{user.name} (@{user.screen_name})"
    #                if user.name and user.name != user.screen_name
    #                else f"@{user.screen_name}"
    #            ),
    #            description=user.description,
    #        )
    #        embed.set_thumbnail(url=user.avatar_url)
    #
    #        embed.add_field(
    #            name="**Tweets**",
    #            value=f"{user.statuses_count:,}",
    #        )
    #        embed.add_field(
    #            name="**Following**",
    #            value=f"{user.friends_count:,}",
    #        )
    #        embed.add_field(
    #            name="**Followers**",
    #            value=f"{user.followers_count:,}",
    #        )
    #
    #        return await ctx.send(embed=embed)
    #
    #    @twitter.command(
    #        name="add",
    #        aliases=["feed"],
    #    )
    #    @has_permissions(manage_channels=True)
    #    async def twitter_add(
    #        self,
    #        ctx: Context,
    #        channel: TextChannel | Thread,
    #        user: TwitterUser,
    #    ) -> Message:
    #        """
    #        Add a channel to receive tweets from a user.
    #        """
    #
    #        if ctx.author.id not in self.bot.owner_ids:
    #            records = cast(
    #                int,
    #                await self.bot.db.fetchval(
    #                    """
    #                    SELECT COUNT(*)
    #                    FROM feeds.twitter
    #                    WHERE guild_id = $1
    #                    AND channel_id = ANY($2::BIGINT[])
    #                    """,
    #                    ctx.guild.id,
    #                    [
    #                        _channel.id
    #                        for _channel in ctx.guild.text_channels
    #                        + list(ctx.guild.threads)
    #                    ],
    #                ),
    #            )
    #            if records >= 5:
    #                return await ctx.warn(
    #                    "You can only receive tweets from **5 users** at a time!"
    #                )
    #
    #        await self.bot.db.execute(
    #            """
    #            INSERT INTO feeds.twitter (
    #                guild_id,
    #                channel_id,
    #                twitter_id,
    #                twitter_name
    #            )
    #            VALUES ($1, $2, $3, $4)
    #            ON CONFLICT (guild_id, twitter_id)
    #            DO UPDATE SET channel_id = EXCLUDED.channel_id
    #            """,
    #            ctx.guild.id,
    #            channel.id,
    #            user.id,
    #            user.screen_name,
    #        )
    #        return await ctx.approve(
    #            f"Now streaming new tweets from [**{user}**]({user.url}) to {channel.mention}"
    #        )
    #
    #    @twitter.command(
    #        name="remove",
    #        aliases=["delete", "del", "rm"],
    #    )
    #    @has_permissions(manage_channels=True)
    #    async def twitter_remove(
    #        self,
    #        ctx: Context,
    #        channel: Optional[TextChannel | Thread],
    #        user: TwitterUser,
    #    ) -> Message:
    #        """
    #        Remove a channel from receiving tweets from a user.
    #        """
    #
    #        result = await self.bot.db.execute(
    #            """
    #            DELETE FROM feeds.twitter
    #            WHERE guild_id = $1
    #            AND twitter_id = $2
    #            """,
    #            ctx.guild.id,
    #            user.id,
    #        )
    #        if result == "DELETE 0":
    #            return await ctx.warn(
    #                f"Tweets from [**{user}**]({user.url}) are not being streamed!"
    #            )
    #
    #        return await ctx.approve(
    #            f"No longer streaming tweets from [**{user}**]({user.url})"
    #        )
    #
    #    @twitter.command(
    #        name="color",
    #        aliases=["colour"],
    #    )
    #    @has_permissions(manage_channels=True)
    #    async def twitter_color(
    #        self,
    #        ctx: Context,
    #        channel: Optional[TextChannel | Thread],
    #        color: Literal["random"] | Color,
    #        user: Optional[TwitterUser],
    #    ) -> Message:
    #        """
    #        Set a custom color for tweet embeds.
    #        """
    #
    #        if not user:
    #            await ctx.prompt(
    #                "You didn't specify a valid **Twitter username**!",
    #                "Are you sure you want to set the color for **ALL** feeds?",
    #            )
    #
    #            result = await self.bot.db.execute(
    #                """
    #                UPDATE feeds.twitter
    #                SET color = $2
    #                WHERE guild_id = $1
    #                """,
    #                ctx.guild.id,
    #                str(color.value) if isinstance(color, Color) else "random",
    #            )
    #            if result == "UPDATE 0":
    #                return await ctx.warn("No **Twitter feeds** were modified!")
    #
    #            return await ctx.approve(
    #                f"Now using {f'`{color}`' if isinstance(color, Color) else '**random colors**'} for new tweets",
    #                color=color if isinstance(color, Color) else None,
    #            )
    #
    #        result = await self.bot.db.execute(
    #            """
    #            UPDATE feeds.twitter
    #            SET color = $3
    #            WHERE guild_id = $1
    #            AND twitter_id = $2
    #            """,
    #            ctx.guild.id,
    #            user.id,
    #            str(color.value) if isinstance(color, Color) else "random",
    #        )
    #        if result == "UPDATE 0":
    #            return await ctx.warn(
    #                f"Tweets from [**{user}**]({user.url}) are not being streamed!"
    #            )
    #
    #        return await ctx.approve(
    #            f"Now using {f'`{color}`' if isinstance(color, Color) else '**random colors**'} for new tweets from [**{user}**]({user.url})",
    #            color=color if isinstance(color, Color) else None,
    #        )
    #
    #    @twitter.group(
    #        name="message",
    #        aliases=["msg"],
    #        invoke_without_command=True,
    #    )
    #    @has_permissions(manage_channels=True)
    #    async def twitter_message(
    #        self,
    #        ctx: Context,
    #        channel: Optional[TextChannel | Thread],
    #        user: Optional[TwitterUser],
    #        *,
    #        script: Script,
    #    ) -> Message:
    #        """
    #        Set a message to be sent when a tweet is received.
    #        """
    #
    #        if not user:
    #            await ctx.prompt(
    #                "You didn't specify a valid **Twitter username**!",
    #                "Are you sure you want to set the message for **ALL** feeds?",
    #            )
    #
    #            result = await self.bot.db.execute(
    #                """
    #                UPDATE feeds.twitter
    #                SET template = $2
    #                WHERE guild_id = $1
    #                """,
    #                ctx.guild.id,
    #                script.template,
    #            )
    #            if result == "UPDATE 0":
    #                return await ctx.warn("No **Twitter feeds** were modified!")
    #
    #            return await ctx.approve(
    #                "Updated the tweet message for all **Twitter feeds**"
    #            )
    #
    #        result = await self.bot.db.execute(
    #            """
    #            UPDATE feeds.twitter
    #            SET template = $3
    #            WHERE guild_id = $1
    #            AND twitter_id = $2
    #            """,
    #            ctx.guild.id,
    #            user.id,
    #            script.template,
    #        )
    #        if result == "UPDATE 0":
    #            return await ctx.warn(
    #                f"Tweets from [**{user}**]({user.url}) are not being streamed!"
    #            )
    #
    #        return await ctx.approve(
    #            f"Updated the tweet message for [**{user}**]({user.url})"
    #        )
    #
    #    @twitter_message.command(
    #        name="remove",
    #        aliases=["delete", "del", "rm"],
    #    )
    #    @has_permissions(manage_channels=True)
    #    async def twitter_message_remove(
    #        self,
    #        ctx: Context,
    #        channel: Optional[TextChannel | Thread],
    #        user: Optional[TwitterUser],
    #    ) -> Message:
    #        """
    #        Remove the message sent when a tweet is received.
    #
    #        This does not apply to the tweet's embed.
    #        """
    #
    #        if not user:
    #            await ctx.prompt(
    #                "You didn't specify a valid **Twitter username**!",
    #                "Are you sure you want to remove the message for **ALL** feeds?",
    #            )
    #
    #            result = await self.bot.db.execute(
    #                """
    #                UPDATE feeds.twitter
    #                SET template = NULL
    #                WHERE guild_id = $1
    #                """,
    #                ctx.guild.id,
    #            )
    #            if result == "UPDATE 0":
    #                return await ctx.warn("No **Twitter feeds** were modified!")
    #
    #            return await ctx.approve(
    #                "Reset the tweet message for all **Twitter feeds**"
    #            )
    #
    #        result = await self.bot.db.execute(
    #            """
    #            UPDATE feeds.twitter
    #            SET template = NULL
    #            WHERE guild_id = $1
    #            AND twitter_id = $2
    #            """,
    #            ctx.guild.id,
    #            user.id,
    #        )
    #        if result == "UPDATE 0":
    #            return await ctx.warn(
    #                f"Tweets from [**{user}**]({user.url}) are not being streamed!"
    #            )
    #
    #        return await ctx.approve(
    #            f"Reset the tweet message for [**{user}**]({user.url})"
    #        )
    #
    #    @twitter.command(
    #        name="clear",
    #        aliases=["clean", "reset"],
    #    )
    #    @has_permissions(manage_channels=True)
    #    async def twitter_clear(self, ctx: Context) -> Message:
    #        """
    #        Remove all Twitter feeds.
    #        """
    #
    #        await ctx.prompt(
    #            "Are you sure you want to remove all **Twitter feeds**?",
    #        )
    #
    #        result = await self.bot.db.execute(
    #            """
    #            DELETE FROM feeds.twitter
    #            WHERE guild_id = $1
    #            """,
    #            ctx.guild.id,
    #        )
    #        if result == "DELETE 0":
    #            return await ctx.warn("No **Twitter feeds** exist for this server!")
    #
    #        return await ctx.approve(
    #            f"Successfully  removed {plural(result, md='`'):Twitter feed}"
    #        )
    #
    #    @twitter.command(
    #        name="list",
    #        aliases=["ls"],
    #    )
    #    @has_permissions(manage_guild=True)
    #    async def twitter_list(self, ctx: Context) -> Message:
    #        """
    #        View all Twitter feeds.
    #        """
    #
    #        channels = [
    #            f"{index + 1:02}. {channel.mention} - [**@{record['twitter_name']}**](https://twitter.com/{record['twitter_name']})"
    #            for index, record in enumerate(await self.bot.db.fetch(
    #                """
    #                SELECT channel_id, twitter_name
    #                FROM feeds.twitter
    #                WHERE guild_id = $1
    #                """,
    #                ctx.guild.id,
    #            ))
    #            if (channel := ctx.guild.get_channel_or_thread(record["channel_id"]))
    #        ]
    #
    #        if not channels:
    #            return await ctx.warn("No **Twitter feeds** exist for this server!")
    #
    #        # Use autopaginator to paginate the channels
    #        embed = Embed(title="Twitter Feeds")
    #        return await ctx.autopaginator(embed=embed, description=channels, split=10)

    @hybrid_command(
        aliases=["insta", "ig"],
        invoke_without_command=True,
    )
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def instagram(
        self,
        ctx: Context,
        username: str,
    ) -> Message:
        """
        Look up a user on Instagram.
        """

        user = await self.instagram_client.get_user(username)
        if not user:
            return await ctx.warn(f"User `{username}` was not found!")

        embed = Embed(
            url=user.url,
            title=(
                f"{user.full_name} (@{user.username})"
                if user.full_name and user.full_name != user.username
                else f"@{user.username}"
            )
            + (" 🔒" if user.is_private else "")
            + (" :ballot_box_with_check:" if user.is_verified else ""),
            description=user.biography,
        )
        embed.set_thumbnail(url=user.avatar_url)

        embed.add_field(
            name="**Posts**",
            value=f"{user.post_count:,}",
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
