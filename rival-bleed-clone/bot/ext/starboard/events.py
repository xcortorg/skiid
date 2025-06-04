from discord.ext.commands import Cog
from discord import Client, Color
from weakref import WeakValueDictionary
from lib.classes.builtins import shorten
import asyncio
import sys
import discord
import re
from typing import Union
import contextlib
from lib.classes.database import Record
import traceback
import orjson

# from loguru import logger
import logging

logger = logging.getLogger(__name__)
from loguru import logger as log_


class Events(Cog):
    def __init__(self: "Events", bot: Client):
        self.bot = bot
        self._locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()
        self._about_to_be_deleted: set[int] = set()

    def log(self, message: str):
        return
        self.bot.yes = message
        log_.error(message)
        logger.error(message)

    async def reaction_logic(self, fmt: str, payload: discord.RawReactionActionEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return self.log("not guild")

        channel = guild.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return self.log("not channel")

        if not (method := getattr(self, f"{fmt}_message", None)):
            return self.log("not methid")

        if not (
            starboard := await self.bot.db.fetchrow(
                "SELECT * FROM starboard WHERE guild_id = $1",
                guild.id,
            )
        ):
            return self.log("no starboard")
        if not str(starboard.emoji) == str(payload.emoji):
            return self.log(
                f"{str(starboard.emoji)} isnt the same as {str(payload.emoji)}"
            )

        if not ((starboard_channel := guild.get_channel(starboard["channel_id"]))):
            return self.log("no channel")
        if not (starboard_channel.permissions_for(guild.me).send_messages):
            return self.log("not mass check")

        if not (member := payload.member or guild.get_member(payload.user_id)):
            return self.log("not member")
        if starboard.ignore_entries:
            starboard.ignore_entries = orjson.loads(starboard.ignore_entries)
            snowflakes = [member.id, channel.id]
            snowflakes.extend([r.id for r in member.roles])
            for entry in starboard.ignore_entries:
                if entry in snowflakes:
                    return self.log("ignored")
        if starboard.lock:
            return self.log("locked")
        try:
            await method(
                starboard, starboard_channel, guild, channel, member, payload.message_id
            )
        except Exception as e:
            exc = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            self.log(f"starboard error: {exc}")
            return

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        await self.bot.db.execute(
            "DELETE FROM starboard WHERE guild_id = $1 AND channel_id = $2",
            channel.guild.id,
            channel.id,
        )

    @Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.reaction_logic("star", payload)

    @Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.reaction_logic("unstar", payload)

    @Cog.listener()
    async def on_raw_reaction_clear(self, payload: discord.RawReactionClearEmojiEvent):
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        starboard_entry = await self.bot.db.fetchrow(
            "DELETE FROM starboard_entries WHERE message_id = $1 RETURNING emoji, starboard_message_id",
            payload.message_id,
        )
        if not starboard_entry:
            return

        if not (
            starboard := await self.bot.db.fetchrow(
                "SELECT channel_id FROM starboard WHERE guild_id = $1 AND emoji = $2",
                guild.id,
                starboard_entry["emoji"],
            )
        ):
            return

        if not (starboard_channel := guild.get_channel(starboard["channel_id"])):
            return

        with contextlib.suppress(discord.HTTPException):
            await starboard_channel.delete_messages(
                [discord.Object(id=starboard_entry["starboard_message_id"])]
            )

    @Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
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
        self, payload: discord.RawBulkMessageDeleteEvent
    ):
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
        starboard_channel: Union[discord.TextChannel, discord.Thread],
        guild: discord.Guild,
        channel: discord.TextChannel,
        member: discord.Member,
        message_id: int,
    ):
        try:
            return await self._star_message(
                starboard, starboard_channel, guild, channel, member, message_id
            )
        except Exception as e:
            exc = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            self.log(f"starboard error: {exc}")

    async def _star_message(
        self,
        starboard: Record,
        starboard_channel: Union[discord.TextChannel, discord.Thread],
        guild: discord.Guild,
        channel: discord.TextChannel,
        member: discord.Member,
        message_id: int,
    ):
        lock = self._locks.get(guild.id)
        if not lock:
            self._locks[guild.id] = lock = asyncio.Lock()
        async with lock:
            if channel.is_nsfw() and not starboard_channel.is_nsfw():
                return self.log("nsfw check failed")

            if not (message := await channel.fetch_message(message_id)):
                return self.log("no message")
            if message.author.id is self.bot.user.id:
                return self.log("bot is author")

            ctx = await self.bot.get_context(message)
            if ctx.valid:
                return self.log("valid")

            if message.author.id == member.id:
                if not starboard.get("self_star", True):
                    self.log("self star isnt on")
                    return

            if (
                len(message.content) == 0 and len(message.attachments) == 0
            ) or message.type not in (
                discord.MessageType.default,
                discord.MessageType.reply,
            ):
                return self.log("not right type")

            reaction = [
                reaction
                for reaction in message.reactions
                if str(reaction.emoji) == starboard["emoji"]
            ]
            if reaction:
                reaction = reaction[0]
            else:
                return self.log("no reaction")
            count = len([r async for r in reaction.users() if r is not self.bot.user])
            if count >= starboard.threshold:
                pass
            else:
                return self.log("not hit")

            starboard_message_id = await self.bot.db.fetchval(
                "SELECT starboard_message_id FROM starboard_entries WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4",
                guild.id,
                channel.id,
                message.id,
                starboard["emoji"],
            )

            content, embed, files = await self.render_starboard_entry(
                starboard, reaction, message
            )

            if starboard_message_id and (
                starboard_message := starboard_channel.get_partial_message(
                    starboard_message_id
                )
            ):
                try:
                    await starboard_message.edit(
                        content=content,
                    )
                except discord.HTTPException:
                    pass
                else:
                    return self.log("failed edit")

            try:
                starboard_message = await starboard_channel.send(
                    content=content,
                    embed=embed,
                    files=files,
                )
            except discord.HTTPException:
                return self.log("failed send")
            await self.bot.db.execute(
                "INSERT INTO starboard_entries (guild_id, channel_id, message_id, emoji, starboard_message_id) VALUES ($1, $2, $3, $4, $5)",
                guild.id,
                channel.id,
                message.id,
                starboard["emoji"],
                starboard_message.id,
            )

    async def unstar_message(
        self,
        starboard: Record,
        starboard_channel: Union[discord.TextChannel, discord.Thread],
        guild: discord.Guild,
        channel: discord.TextChannel,
        member: discord.Member,
        message_id: int,
    ):
        lock = self._locks.get(guild.id)
        if not lock:
            self._locks[guild.id] = lock = asyncio.Lock()

        async with lock:
            starboard_message_id = await self.bot.db.fetchval(
                "SELECT starboard_message_id FROM starboard_entries WHERE guild_id = $1 AND channel_id = $2 AND message_id = $3 AND emoji = $4",
                guild.id,
                channel.id,
                message_id,
                starboard["emoji"],
            )
            if not starboard_message_id:
                return

            if not (message := await channel.fetch_message(message_id)):
                return
            if message.author.id is self.bot.user.id:
                return
            ctx = await self.bot.get_context(message)
            if ctx.valid:
                return
            reaction = [
                reaction
                for reaction in message.reactions
                if str(reaction.emoji) == starboard["emoji"]
            ]
            if reaction:
                reaction = reaction[0]
            else:
                with contextlib.suppress(discord.HTTPException):
                    await starboard_channel.delete_messages(
                        [discord.Object(id=starboard_message_id)]
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
                await starboard_channel.get_partial_message(starboard_message_id).edit(
                    content=content,
                )
            except discord.HTTPException:
                await self.bot.db.execute(
                    "DELETE FROM starboard_entries WHERE starboard_message_id = $1",
                    starboard_message_id,
                )

    async def render_starboard_entry(
        self,
        starboard: Record,
        reaction: discord.Reaction,
        message: discord.Message,
    ):
        files = None
        if (
            message.embeds
            and (embed := message.embeds[0])
            and embed.type not in ("image", "gif", "gifv")
        ):
            embed = embed
        else:
            embed = discord.Embed(
                color=(
                    Color.from_str(starboard.color)
                    if starboard.color
                    else message.author.color
                )
            )

        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar,
        )
        if starboard.jump:
            embed.author.url = message.jump_url
        if starboard.ts:
            embed.timestamp = message.created_at
        embed.description = f"{shorten(message.content, 2048) if message.system_content else ''}\n{shorten(embed.description, 2048) if embed.description else ''}"
        if starboard.attachments:
            if (
                message.embeds
                and (_embed := message.embeds[0])
                and (_embed.url and _embed.type in ("image", "gifv"))
            ):
                embed.description = embed.description.replace(_embed.url, "")
                if _embed.type == "image":
                    embed.set_image(url=_embed.url)
                elif _embed.type == "gifv":
                    response = await self.bot.session.get(_embed.url)
                    if response.status == 200:
                        data = await response.text()
                        try:
                            tenor_url = re.findall(
                                r"(?i)\b((https?://c[.]tenor[.]com/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))[.]gif)",
                                data,
                            )[0][0]
                        except IndexError:
                            pass
                        else:
                            embed.set_image(url=tenor_url)
                    else:
                        embed.set_image(url=_embed.thumbnail.url)

            files = list()
            for attachment in message.attachments:
                if attachment.url.lower().endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".webp")
                ):
                    embed.set_image(url=attachment.url)
                elif attachment.url.lower().endswith(
                    (".mp4", ".mov", ".webm", "mp3", ".ogg", ".wav")
                ):
                    embed.set_image(url=attachment.url)
                    attachment = await attachment.to_file()
                    if not sys.getsizeof(attachment.fp) > message.guild.filesize_limit:
                        files.append(attachment)
        if message.reference and (reference := message.reference.resolved):
            embed.add_field(
                name=f"**Replying to {reference.author.display_name}**",
                value=f"[Jump to reply]({reference.jump_url})",
                inline=False,
            )

        if starboard.jump:

            embed.add_field(
                name=f"**#{message.channel}**",
                value=f"[Jump to message]({message.jump_url})",
                inline=False,
            )
        if starboard.ts:
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

        #        if not files: files = []
        return f"{reaction} **{reactions}**", embed, files
