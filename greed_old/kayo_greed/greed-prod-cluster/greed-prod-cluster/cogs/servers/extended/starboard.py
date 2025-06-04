import asyncio
import sys
from io import BytesIO
from discord import (
    TextChannel,
    Thread,
    Member,
    Message,
    Embed,
    HTTPException,
    Object,
    Reaction,
    RawReactionActionEvent,
    RawReactionClearEmojiEvent,
    RawBulkMessageDeleteEvent,
    RawMessageDeleteEvent,
    Guild,
    File,
)
from discord.abc import GuildChannel
from weakref import WeakValueDictionary
from contextlib import suppress
from asyncpg import Record
from tools.client import Context
from tools import MixinMeta, CompositeMetaClass, dominant_color
import config
from logging import getLogger
from discord.ext.commands import Cog, group, has_permissions, BucketType, cooldown

log = getLogger("greed/starboard")


def shorten(value: str, length: int = 20) -> str:
    """Shortens a string to a specified length, adding '..' if truncated."""
    if length < 3:
        raise ValueError("Provide more than 3")
    return value[: length - 2].rstrip() + ".." if len(value) > length else value


class Starboard(MixinMeta, metaclass=CompositeMetaClass):
    """Starboard cog for managing message reactions as starboards in Discord."""

    def __init__(self, bot) -> None:
        """Initializes the Starboard cog with bot instance and necessary containers."""
        self.bot = bot
        self._locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()
        self._about_to_be_deleted: set[int] = set()

    async def reaction_logic(self, fmt: str, payload: RawReactionActionEvent) -> None:
        """Handles reaction addition and removal for the starboard."""
        if not (guild := self.bot.get_guild(payload.guild_id)):
            return
        if not (channel := guild.get_channel(payload.channel_id)) or not isinstance(
            channel, TextChannel
        ):
            return
        if not (method := getattr(self, f"{fmt}_message", None)):
            return

        starboard = await self.bot.db.fetchrow(
            "SELECT channel_id, emoji, threshold FROM starboard WHERE guild_id = $1 AND emoji = $2",
            guild.id,
            str(payload.emoji),
        )
        if not starboard:
            return

        starboard_channel = guild.get_channel(starboard["channel_id"])
        if (
            not starboard_channel
            or channel.id == starboard_channel.id
            or not starboard_channel.permissions_for(guild.me).send_messages
        ):
            return

        member = payload.member or guild.get_member(payload.user_id)
        if not member:
            return

        try:
            await method(
                starboard, starboard_channel, guild, channel, member, payload.message_id
            )
        except Exception as e:
            log.error(f"Error in reaction logic: {e}")

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel) -> None:
        """Deletes starboard entries if the channel is deleted."""
        if isinstance(channel, TextChannel | Thread):
            await self.bot.db.execute(
                "DELETE FROM starboard WHERE guild_id = $1 AND channel_id = $2",
                channel.guild.id,
                channel.id,
            )

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """Triggers when a reaction is added to a message."""
        await self.reaction_logic("star", payload)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent) -> None:
        """Triggers when a reaction is removed from a message."""
        await self.reaction_logic("unstar", payload)

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionClearEmojiEvent) -> None:
        """Handles the clearing of reactions from a message."""
        if not (guild := self.bot.get_guild(payload.guild_id)):
            return
        if not (channel := guild.get_channel(payload.channel_id)) or not isinstance(
            channel, TextChannel
        ):
            return

        starboard_entry = await self.bot.db.fetchrow(
            "DELETE FROM starboard_entries WHERE message_id = $1 RETURNING emoji, starboard_message_id",
            payload.message_id,
        )
        if not starboard_entry:
            return

        starboard = await self.bot.db.fetchrow(
            "SELECT channel_id FROM starboard WHERE guild_id = $1 AND emoji = $2",
            guild.id,
            starboard_entry["emoji"],
        )
        if not starboard:
            return

        starboard_channel = guild.get_channel(starboard["channel_id"])
        if not starboard_channel:
            return

        with suppress(HTTPException):
            await starboard_channel.delete_messages(
                [Object(id=starboard_entry["starboard_message_id"])]
            )

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent) -> None:
        """Handles a single message deletion and updates starboard entries accordingly."""
        if payload.message_id in self._about_to_be_deleted:
            self._about_to_be_deleted.discard(payload.message_id)
            return

        await self.bot.db.execute(
            "DELETE FROM starboard_entries WHERE guild_id = $1 AND starboard_message_id = $2",
            payload.guild_id,
            payload.message_id,
        )

    @Cog.listener()
    async def on_raw_bulk_message_delete(
        self, payload: RawBulkMessageDeleteEvent
    ) -> None:
        """Handles bulk message deletions and updates starboard entries accordingly."""
        if payload.message_ids <= self._about_to_be_deleted:
            self._about_to_be_deleted.difference_update(payload.message_ids)
            return

        await self.bot.db.execute(
            "DELETE FROM starboard_entries WHERE guild_id = $1 AND starboard_message_id = ANY($2::BIGINT[])",
            payload.guild_id,
            list(payload.message_ids),
        )

    async def star_message(
        self,
        starboard: Record,
        starboard_channel: TextChannel | Thread,
        guild: Guild,
        channel: TextChannel,
        member: Member,
        message_id: int,
    ) -> None:
        """Stars a message and posts it to the starboard channel."""
        lock = self._locks.setdefault(guild.id, asyncio.Lock())
        async with lock:
            if channel.is_nsfw() and not starboard_channel.is_nsfw():
                return

            message = await channel.fetch_message(message_id)
            if not message or (
                message.author.id == member.id and not starboard.get("self_star", True)
            ):
                return
            if not message.content and not message.attachments:
                return

            reaction = next(
                (r for r in message.reactions if str(r.emoji) == starboard["emoji"]),
                None,
            )
            if not reaction or reaction.count < starboard.get("threshold", 1):
                return

            starboard_message_id = await self.bot.db.fetchval(
                """
                SELECT starboard_message_id
                FROM starboard_entries
                WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4
                """,
                guild.id,
                channel.id,
                message.id,
                starboard["emoji"],
            )

            content, embed, files = await self.render_starboard_entry(
                starboard, reaction, message
            )

            if starboard_message_id:
                # Fetch the full message instead of a partial one for editing
                try:
                    starboard_message = await starboard_channel.fetch_message(
                        starboard_message_id
                    )
                    await starboard_message.edit(content=content, embed=embed)
                    if files:
                        await starboard_message.delete()
                        await starboard_channel.send(
                            content=content, embed=embed, files=files
                        )
                except HTTPException:
                    log.error(
                        f"Failed to edit or resend starboard message: {starboard_message_id}"
                    )
            else:
                try:
                    starboard_message = await starboard_channel.send(
                        content=content, embed=embed, files=files
                    )
                    await self.bot.db.execute(
                        """
                        INSERT INTO starboard_entries (guild_id, channel_id, message_id, emoji, starboard_message_id)
                        VALUES ($1, $2, $3, $4, $5)
                        ON CONFLICT (guild_id, channel_id, message_id, emoji)
                        DO UPDATE SET starboard_message_id = $5
                        """,
                        guild.id,
                        channel.id,
                        message.id,
                        starboard["emoji"],
                        starboard_message.id,
                    )
                except HTTPException:
                    log.error(
                        f"Failed to send starboard message for message ID: {message.id}"
                    )

    async def unstar_message(
        self,
        starboard: Record,
        starboard_channel: TextChannel | Thread,
        guild: Guild,
        channel: TextChannel,
        member: Member,
        message_id: int,
    ) -> None:
        """Unstars a message and removes it from the starboard channel if needed."""
        lock = self._locks.setdefault(guild.id, asyncio.Lock())
        async with lock:
            starboard_message_id = await self.bot.db.fetchval(
                """
                SELECT starboard_message_id
                FROM starboard_entries
                WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4
                """,
                guild.id,
                channel.id,
                message_id,
                starboard["emoji"],
            )
            if not starboard_message_id:
                return

            message = await channel.fetch_message(message_id)
            if not message:
                return

            reaction = next(
                (r for r in message.reactions if str(r.emoji) == starboard["emoji"]),
                None,
            )
            if not reaction:
                await self._delete_starboard_message(
                    starboard_channel, starboard_message_id
                )
                await self.bot.db.execute(
                    "DELETE FROM starboard_entries WHERE starboard_message_id = $1",
                    starboard_message_id,
                )
                return

            content, embed, files = await self.render_starboard_entry(
                starboard, reaction, message
            )
            try:
                # Fetch the full message instead of a partial one for editing
                starboard_message = await starboard_channel.fetch_message(
                    starboard_message_id
                )
                await starboard_message.edit(content=content, embed=embed)
                if files:
                    await starboard_message.delete()
                    await starboard_channel.send(
                        content=content, embed=embed, files=files
                    )
            except HTTPException:
                await self.bot.db.execute(
                    "DELETE FROM starboard_entries WHERE starboard_message_id = $1",
                    starboard_message_id,
                )

    async def _delete_starboard_message(
        self, starboard_channel: TextChannel | Thread, starboard_message_id: int
    ) -> None:
        """Deletes a starboard message, handling HTTP exceptions."""
        with suppress(HTTPException):
            await starboard_channel.delete_messages([Object(id=starboard_message_id)])

    async def render_starboard_entry(
        self, starboard: Record, reaction: Reaction, message: Message
    ) -> tuple[str, Embed, list[File]]:
        """Renders the content, embed, and files for a starboard entry."""
        embed = Embed(color=0xFFFFFF)
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url,
            url=message.jump_url,
        )

        # Safely handle message content and embed descriptions
        message_content = message.content or ""
        embed_description = message_content
        if not embed_description and message.embeds:
            embed_description = message.embeds[0].description or ""

        embed.description = shorten(embed_description, 2048)

        files: list[File] = []
        image_set = False
        for attachment in message.attachments:
            byte_data = await attachment.read()
            file = File(
                BytesIO(byte_data),
                filename=attachment.filename,
                spoiler=attachment.is_spoiler(),
            )

            # Safely access message.guild and its filesize_limit
            guild = message.guild
            if guild and sys.getsizeof(byte_data) <= guild.filesize_limit:
                files.append(file)
                # Safely check if content_type starts with 'image'
                content_type = attachment.content_type or ""
                if not image_set and content_type.startswith("image"):
                    embed.set_image(url="attachment://" + file.filename)
                    embed.color = await dominant_color(byte_data)
                    image_set = True

        # If no images were set and there are embeds, copy over image details
        if message.embeds and not image_set:
            embed_to_copy = message.embeds[0]
            if embed_to_copy.image:
                embed.set_image(url=embed_to_copy.image.url)
            if embed_to_copy.thumbnail:
                embed.set_thumbnail(url=embed_to_copy.thumbnail.url)
            if embed_to_copy.footer:
                embed.set_footer(
                    text=embed_to_copy.footer.text,
                    icon_url=embed_to_copy.footer.icon_url,
                )
            if embed_to_copy.author:
                embed.set_author(
                    name=embed_to_copy.author.name,
                    url=embed_to_copy.author.url,
                    icon_url=embed_to_copy.author.icon_url,
                )
            embed.color = embed_to_copy.color

        if message.reference and (reference := message.reference.resolved):
            embed.add_field(
                name=f"{config.EMOJIS.UTILS.REPLY} **{reference.author.display_name}**",
                value=f"-# - [**jump to message**]({message.jump_url})",
                inline=False,
            )

        embed.add_field(
            name=f"{config.EMOJIS.UTILS.CHAT} **#{message.channel}**",
            value=f"-# - [**jump to message**]({message.jump_url})",
            inline=False,
        )
        embed.timestamp = message.created_at

        reactions = f"#{reaction.count:,}"
        if str(reaction.emoji) == "⭐":
            if 5 > reaction.count >= 0:
                reaction = "⭐"
            elif 10 > reaction.count >= 5:
                reaction = "🌟"
            elif 25 > reaction.count >= 10:
                reaction = "💫"
            else:
                reaction = "✨"
        else:
            reaction = str(reaction.emoji)

        return f"{reaction} **{reactions}**", embed, files

    @group(invoke_without_command=True)
    @has_permissions(manage_guild=True)
    async def starboard(self, ctx: Context) -> None:
        """Displays help for the starboard command."""
        await ctx.send_help(ctx.command)

    @starboard.command(
        help="Set a starboard channel",
        usage="[channel] [emoji] [threshold]",
        aliases=["set"],
        brief="#gen 💀 1",
        description="Manage guild",
    )
    @cooldown(1, 5, BucketType.user)
    async def add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        emoji: str,
        threshold: int = 3,
    ) -> None:
        """Adds a starboard channel to the server."""
        num_starboards = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM starboard WHERE guild_id = $1", ctx.guild.id
        )
        if num_starboards >= 2:
            return await ctx.warn(
                "Guild already has the max of 2 channels, consider removing one"
            )
        if not (1 <= threshold <= 120):
            return await ctx.warn("Threshold must be between 1 and 120")

        try:
            await ctx.message.add_reaction(emoji)
        except HTTPException:
            return await ctx.warn(f"**{emoji}** is not a valid emoji")

        try:
            await self.bot.db.execute(
                "INSERT INTO starboard (guild_id, channel_id, emoji, threshold) VALUES ($1, $2, $3, $4)",
                ctx.guild.id,
                channel.id,
                emoji,
                threshold,
            )
            await ctx.approve(
                f"Added a **starboard** for {channel.mention} using **{emoji}** with the threshold of **{threshold}**"
            )
        except Exception as e:
            await ctx.warn(f"There is already a **starboard** using **{emoji}**")

    @starboard.command(
        help="Removes a starboard channel from the server",
        usage="[channel] [emoji] [threshold]",
        aliases=["rem"],
        brief="#gen",
        description="Manage guild",
    )
    @cooldown(1, 5, BucketType.user)
    async def remove(self, ctx: Context, channel: TextChannel | Thread) -> None:
        """Removes a starboard channel from the server."""
        try:
            await self.bot.db.execute(
                "DELETE FROM starboard WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
            await ctx.warn(f"Removed all **starboards** for {channel.mention}")
        except Exception as e:
            await ctx.warn(f"There isn't a **starboard** for {channel.mention}")

    @starboard.command(
        help="Shows the list of starboards in the server and their emojis and threshold",
        aliases=["show"],
        description="Manage guild",
    )
    @cooldown(1, 5, BucketType.user)
    async def list(self, ctx: Context) -> None:
        """Lists all starboards in the server."""
        starboards = [
            f"{ctx.guild.get_channel(row['channel_id']).mention} - **{row['emoji']}** (threshold: `{row['threshold']}`)"
            for row in await self.bot.db.fetch(
                "SELECT channel_id, emoji, threshold FROM starboard WHERE guild_id = $1",
                ctx.guild.id,
            )
        ]
        if not starboards:
            return await ctx.warn("No **starboards** have been set up")
        await ctx.send(
            embed=Embed(title="Starboards", description="\n".join(starboards))
        )
