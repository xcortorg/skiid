import asyncio
import sys
from io import BytesIO
from discord import (
    TextChannel, Thread, Member, Message, Embed, MessageType, HTTPException, Object, Reaction, RawReactionActionEvent, RawReactionClearEmojiEvent, RawBulkMessageDeleteEvent, RawMessageDeleteEvent, Guild, File
)
from discord.abc import GuildChannel
from weakref import WeakValueDictionary
from contextlib import suppress
from typing import Union
from asyncpg import Record
from main import greed
from tools.client import Context
from tools import MixinMeta, CompositeMetaClass
import config
from logging import getLogger
from discord.ext.commands import Cog, group, has_permissions, BucketType, cooldown

from tools import dominant_color
log = getLogger("greed/starboard")

def shorten(value: str, length: int = 20) -> str:
    if length < 3:
        raise ValueError("Provide more than 3")
    return value[: length - 2].rstrip() + ".." if len(value) > length else value

class Starboard(MixinMeta, metaclass=CompositeMetaClass):
    """Starboard cog"""

    def __init__(self, bot):
        self.bot = bot
        self._locks = WeakValueDictionary()
        self._about_to_be_deleted = set()

    async def reaction_logic(self, fmt: str, payload: RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, TextChannel):
            return
        method = getattr(self, f"{fmt}_message", None)
        if not method:
            return

        starboard = await self.bot.db.fetchrow(
            "SELECT channel_id, emoji, threshold FROM starboard WHERE guild_id = $1 AND emoji = $2",
            guild.id, str(payload.emoji)
        )
        if not starboard:
            return

        starboard_channel = guild.get_channel(starboard["channel_id"])
        if not starboard_channel or channel.id == starboard_channel.id or not starboard_channel.permissions_for(guild.me).send_messages:
            return

        member = payload.member or guild.get_member(payload.user_id)
        if not member:
            return

        try:
            await method(starboard, starboard_channel, guild, channel, member, payload.message_id)
        except Exception as e:
            log.error(f"Error in reaction logic: {e}")

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GuildChannel):
        if isinstance(channel, (TextChannel, Thread)):
            await self.bot.db.execute(
                "DELETE FROM starboard WHERE guild_id = $1 AND channel_id = $2",
                channel.guild.id, channel.id
            )

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        await self.reaction_logic("star", payload)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        await self.reaction_logic("unstar", payload)

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: RawReactionClearEmojiEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        channel = guild.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, TextChannel):
            return

        starboard_entry = await self.bot.db.fetchrow(
            "DELETE FROM starboard_entries WHERE message_id = $1 RETURNING emoji, starboard_message_id",
            payload.message_id
        )
        if not starboard_entry:
            return

        starboard = await self.bot.db.fetchrow(
            "SELECT channel_id FROM starboard WHERE guild_id = $1 AND emoji = $2",
            guild.id, starboard_entry["emoji"]
        )
        if not starboard:
            return

        starboard_channel = guild.get_channel(starboard["channel_id"])
        if not starboard_channel:
            return

        with suppress(HTTPException):
            await starboard_channel.delete_messages([Object(id=starboard_entry["starboard_message_id"])])

    @Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        if payload.message_id in self._about_to_be_deleted:
            self._about_to_be_deleted.discard(payload.message_id)
            return

        await self.bot.db.execute(
            "DELETE FROM starboard_entries WHERE guild_id = $1 AND starboard_message_id = $2",
            payload.guild_id, payload.message_id
        )

    @Cog.listener()
    async def on_raw_bulk_message_delete(self, payload: RawBulkMessageDeleteEvent):
        if payload.message_ids <= self._about_to_be_deleted:
            self._about_to_be_deleted.difference_update(payload.message_ids)
            return

        await self.bot.db.execute(
            "DELETE FROM starboard_entries WHERE guild_id = $1 AND starboard_message_id = ANY($2::BIGINT[])",
            payload.guild_id, list(payload.message_ids)
        )

    async def star_message(self, starboard: Record, starboard_channel: Union[TextChannel, Thread], guild: Guild, channel: TextChannel, member: Member, message_id: int):
        lock = self._locks.get(guild.id, asyncio.Lock())
        self._locks[guild.id] = lock
        async with lock:
            if channel.is_nsfw() and not starboard_channel.is_nsfw():
                return
            message = await channel.fetch_message(message_id)
            if not message or (message.author.id == member.id and not starboard.get("self_star", True)):
                return
            if not message.content and not message.attachments:
                return
            reaction = next((r for r in message.reactions if str(r.emoji) == starboard["emoji"]), None)
            if not reaction or reaction.count < starboard.get("threshold", 1):
                return

            starboard_message_id = await self.bot.db.fetchval(
                "SELECT starboard_message_id FROM starboard_entries WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4",
                guild.id, channel.id, message.id, starboard["emoji"]
            )
            content, embed, files = await self.render_starboard_entry(starboard, reaction, message)
            if starboard_message_id:
                starboard_message = starboard_channel.get_partial_message(starboard_message_id)
                try:
                    await starboard_message.edit(content=content, embed=embed, files=files)
                except HTTPException:
                    pass
            else:
                try:
                    starboard_message = await starboard_channel.send(content=content, embed=embed, files=files)
                except HTTPException:
                    return
                await self.bot.db.execute(
                    "INSERT INTO starboard_entries (guild_id, channel_id, message_id, emoji, starboard_message_id) VALUES ($1, $2, $3, $4, $5) ON CONFLICT (guild_id, channel_id, message_id, emoji) DO UPDATE SET starboard_message_id = $5",
                    guild.id, channel.id, message.id, starboard["emoji"], starboard_message.id
                )

    async def unstar_message(self, starboard: Record, starboard_channel: Union[TextChannel, Thread], guild: Guild, channel: TextChannel, member: Member, message_id: int):
        lock = self._locks.get(guild.id, asyncio.Lock())
        self._locks[guild.id] = lock
        async with lock:
            starboard_message_id = await self.bot.db.fetchval(
                "SELECT starboard_message_id FROM starboard_entries WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4",
                guild.id, channel.id, message_id, starboard["emoji"]
            )
            if not starboard_message_id:
                return

            message = await channel.fetch_message(message_id)
            if not message:
                return

            reaction = next((r for r in message.reactions if str(r.emoji) == starboard["emoji"]), None)
            if not reaction:
                with suppress(HTTPException):
                    await starboard_channel.delete_messages([Object(id=starboard_message_id)])
                await self.bot.db.execute("DELETE FROM starboard_entries WHERE starboard_message_id = $1", starboard_message_id)
                return

            content, embed, files = await self.render_starboard_entry(starboard, reaction, message)
            try:
                await starboard_channel.get_partial_message(starboard_message_id).edit(content=content, embed=embed, files=files)
            except HTTPException:
                await self.bot.db.execute("DELETE FROM starboard_entries WHERE starboard_message_id = $1", starboard_message_id)

    async def render_starboard_entry(self, starboard: Record, reaction: Reaction, message: Message):
        embed = Embed(color=0xffffff)
        embed.set_author(name=message.author.display_name, icon_url=message.author.display_avatar.url, url=message.jump_url)
        embed.description = shorten(message.content or (message.embeds[0].description if message.embeds else ""), 2048)

        files = []
        image_set = False
        for attachment in message.attachments:
            byte_data = await attachment.read()
            file = File(BytesIO(byte_data), filename=attachment.filename, spoiler=attachment.is_spoiler())
            if sys.getsizeof(byte_data) <= message.guild.filesize_limit:
                files.append(file)
                if not image_set and attachment.content_type.startswith("image"):
                    embed.set_image(url='attachment://' + file.filename)
                    embed.color(await dominant_color(byte_data))
                    image_set = True

        if message.embeds and not image_set:
            embed_to_copy = message.embeds[0]
            if embed_to_copy.image:
                embed.set_image(url=embed_to_copy.image.url)
            if embed_to_copy.thumbnail:
                embed.set_thumbnail(url=embed_to_copy.thumbnail.url)
            if embed_to_copy.footer:
                embed.set_footer(text=embed_to_copy.footer.text, icon_url=embed_to_copy.footer.icon_url)
            if embed_to_copy.author:
                embed.set_author(name=embed_to_copy.author.name, url=embed_to_copy.author.url, icon_url=embed_to_copy.author.icon_url)
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
    async def starboard(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @starboard.command(
        help="Set a starboard channel",
        usage="[channel] [emoji] [threshold]",
        aliases=["set"],
        brief="#gen 💀 1",
        description="Manage guild"
    )
    @cooldown(1, 5, BucketType.user)
    async def add(self, ctx: Context, channel: Union[TextChannel, Thread], emoji: str, threshold: int = 3):
        num_starboards = await self.bot.db.fetchval("SELECT COUNT(*) FROM starboard WHERE guild_id = $1", ctx.guild.id)
        if num_starboards >= 2:
            return await ctx.warn("Guild already has the max of 2 channels, consider removing one")
        if not (1 <= threshold <= 120):
            return await ctx.warn("Threshold must be between 1 and 120")

        try:
            await ctx.message.add_reaction(emoji)
        except HTTPException:
            return await ctx.warn(f"**{emoji}** is not a valid emoji")

        try:
            await self.bot.db.execute(
                "INSERT INTO starboard (guild_id, channel_id, emoji, threshold) VALUES ($1, $2, $3, $4)",
                ctx.guild.id, channel.id, emoji, threshold
            )
            await ctx.approve(f"Added a **starboard** for {channel.mention} using **{emoji}** with the threshold of **{threshold}**")
        except Exception as e:
            await ctx.warn(f"There is already a **starboard** using **{emoji}**")

    @starboard.command(
        help="Removes a starboard channel from the server",
        usage="[channel] [emoji] [threshold]",
        aliases=["rem"],
        brief="#gen",
        description="Manage guild"
    )
    @cooldown(1, 5, BucketType.user)
    async def remove(self, ctx: Context, channel: Union[TextChannel, Thread]):
        try:
            await self.bot.db.execute(
                "DELETE FROM starboard WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id, channel.id
            )
            await ctx.warn(f"Removed all **starboards** for {channel.mention}")
        except Exception as e:
            await ctx.warn(f"There isn't a **starboard** for {channel.mention}")

    @starboard.command(
        help="Shows the list of starboards in the server and their emojis and threshold",
        aliases=["show"],
        description="Manage guild"
    )
    @cooldown(1, 5, BucketType.user)
    async def list(self, ctx: Context):
        starboards = [
            f"{ctx.guild.get_channel(row['channel_id']).mention} - **{row['emoji']}** (threshold: `{row['threshold']}`)"
            for row in await self.bot.db.fetch(
                "SELECT channel_id, emoji, threshold FROM starboard WHERE guild_id = $1",
                ctx.guild.id
            )
        ]
        if not starboards:
            return await ctx.warn("No **starboards** have been set up")
        await ctx.send(embed=Embed(title="Starboards", description="\n".join(starboards)))