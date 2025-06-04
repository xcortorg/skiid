import asyncio
import contextlib
import re
import sys
from loguru import logger
from weakref import WeakValueDictionary

import discord
import traceback
from typing import Union
from asyncpg import Record
from asyncpg.exceptions import UniqueViolationError
from discord.ext import commands
from discord.ext.commands import Context
from contextlib import suppress


def shorten(value: str, length: int = 20):
    if len(value) > length:
        value = value[: length - 2] + (".." if len(value) > length else "").strip()
    return value


class starboard(commands.Cog, name="Starboard"):
    def __init__(self, bot):
        self.bot = bot
        self._locks: WeakValueDictionary[int, asyncio.Lock] = WeakValueDictionary()
        self._about_to_be_deleted: set[int] = set()

    async def reaction_logic(self, fmt: str, payload: discord.RawReactionActionEvent):
        """Handle starboard reaction logic."""
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        method = getattr(self, f"{fmt}_message", None)
        if not method:
            return

        starboard = await self.bot.db.fetchrow(
            """
            SELECT channel_id, emoji, threshold
            FROM starboard
            WHERE guild_id = $1 AND emoji = $2
            """,
            guild.id,
            str(payload.emoji),
        )
        if not starboard:
            return

        starboard_channel = guild.get_channel(starboard["channel_id"])
        if not (
            starboard_channel
            and starboard_channel.permissions_for(guild.me).send_messages
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
            logger.error(f"Error in starboard reaction logic: {traceback.format_exc()}")
            return

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel: discord.abc.GuildChannel):
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            return

        await self.bot.db.execute(
            "DELETE FROM starboard WHERE guild_id = $1 AND channel_id = $2",
            channel.guild.id,
            channel.id,
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        await self.reaction_logic("star", payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        await self.reaction_logic("unstar", payload)

    @commands.Cog.listener()
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

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent):
        if payload.message_id in self._about_to_be_deleted:
            self._about_to_be_deleted.discard(payload.message_id)
            return

        await self.bot.db.execute(
            "DELETE FROM starboard_entries WHERE guild_id = $1 AND starboard_message_id = $2",
            payload.guild_id,
            payload.message_id,
        )

    @commands.Cog.listener()
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
            with contextlib.suppress(discord.HTTPException, discord.NotFound):
                return await self._star_message(
                    starboard, starboard_channel, guild, channel, member, message_id
                )
        except Exception as e:
            exc = "".join(traceback.format_exception(type(e), e, e.__traceback__))
            logger.info(f"starboard error: {exc}")

    async def _star_message(
        self,
        starboard: Record,
        starboard_channel: Union[Union[discord.TextChannel, discord.Thread]],
        guild: discord.Guild,
        channel: discord.TextChannel,
        member: discord.Member,
        message_id: int,
    ):
        if await self.bot.glory_cache.ratelimited(
            f"star_msgrl:{guild.id}:{message_id}", 5, 15
        ):
            return

        lock = self._locks.get(guild.id)
        if not lock:
            self._locks[guild.id] = lock = asyncio.Lock()
        async with lock:
            if channel.is_nsfw() and not starboard_channel.is_nsfw():
                return

            if not (message := await channel.fetch_message(message_id)):
                return
            if message.author.id is self.bot.user.id:
                return

            ctx = await self.bot.get_context(message)
            if ctx.valid:
                return

            if message.author.id == member.id and not starboard.get("self_star", True):
                return

            if (
                len(message.content) == 0 and len(message.attachments) == 0
            ) or message.type not in (
                discord.MessageType.default,
                discord.MessageType.reply,
            ):
                return

            reaction = [
                reaction
                for reaction in message.reactions
                if str(reaction.emoji) == starboard["emoji"]
            ]
            if reaction:
                reaction = reaction[0]
            else:
                return
            count = len([r async for r in reaction.users() if r is not self.bot.user])
            if count >= starboard.threshold:
                pass
            else:
                return

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

            if starboard_message_id:
                try:
                    starboard_message = starboard_channel.get_partial_message(
                        starboard_message_id
                    )

                    if starboard_message:
                        await starboard_message.edit(
                            content=content,
                        )
                        return
                except discord.HTTPException:
                    pass

            starboard_message = await starboard_channel.send(
                content=content, embed=embed, files=files
            )
            await self.bot.db.execute(
                "INSERT INTO starboard_entries (guild_id, channel_id, message_id, emoji, starboard_message_id) VALUES ($1, $2, $3, $4, $5) ON"
                " CONFLICT (guild_id, channel_id, message_id, emoji) DO UPDATE SET starboard_message_id = $5",
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
        if await self.bot.glory_cache.ratelimited(
            f"unstar_msgrl:{guild.id}:{message_id}", 5, 15
        ):
            return

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
        if (
            message.embeds
            and (embed := message.embeds[0])
            and embed.type not in ("image", "gif", "gifv")
        ):
            embed = embed
        else:
            embed = discord.Embed(color=self.bot.color)

        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar,
            url=message.jump_url,
        )
        embed.description = f"{shorten(message.content, 2048) if message.system_content else ''}\n{shorten(embed.description, 2048) if embed.description else ''}"

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
                attachment = await attachment.to_file()
                if not sys.getsizeof(attachment.fp) > message.guild.filesize_limit:
                    files.append(attachment)

        if message.reference and (reference := message.reference.resolved):
            if not isinstance(reference, discord.DeletedReferencedMessage):
                embed.add_field(
                    name=f"**Replying to {reference.author.display_name}**",
                    value=f"[Jump to reply]({reference.jump_url})",
                    inline=False,
                )
            else:
                embed.add_field(
                    name="**Replying to deleted message**",
                    value="Original message was deleted",
                    inline=False,
                )

        embed.add_field(
            name=f"**#{message.channel}**",
            value=f"[Jump to message]({message.jump_url})",
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

    @commands.group(
        name="starboard",
        usage="(subcommand) <args>",
        example=",starboard",
        aliases=["board", "star", "skullboard", "clownboard", "cb", "skull"],
        brief="Create a channel saved of messsages reacted to with said reaction",
        invoke_without_command=True,
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard(self, ctx: Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @starboard.command(
        name="add",
        usage="(channel) (emoji)",
        example=",starboard add #shame 🤡 2",
        brief="Add a channel for the starboard to be set to, add an emoji for it to be saved when a message is reacted to with said emoji",
        aliases=["create"],
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard_add(
        self,
        ctx: Context,
        channel: Union[discord.TextChannel, discord.Thread],
        emoji: str,
        threshold: int,
    ):
        try:
            await ctx.message.add_reaction(emoji)
        except discord.HTTPException:
            return await ctx.fail(f"**{emoji}** is not a valid emoji")
        if threshold == 1:
            m = ""
        else:
            m = f"with a threshold of `{threshold}`"
        try:
            await self.bot.db.execute(
                "INSERT INTO starboard (guild_id, channel_id, emoji, threshold) VALUES ($1, $2, $3, $4)",
                ctx.guild.id,
                channel.id,
                emoji,
                threshold,
            )
        except Exception:
            await ctx.fail(f"There is already a **starboard** using **{emoji}**")
        else:
            await ctx.success(
                f"Added a **starboard** for {channel.mention} using **{emoji}** {m}"
            )

    @starboard.command(
        name="remove",
        usage="(channel) (emoji)",
        example=",starboard remove #shame 🤡",
        brief="remove a starboard from the starboard channel",
        aliases=["delete", "del", "rm"],
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard_remove(
        self,
        ctx: Context,
        channel: Union[discord.TextChannel, discord.Thread],
        emoji: str,
    ):
        """Remove a starboard from a channel"""

        try:
            await self.bot.db.execute(
                "DELETE FROM starboard WHERE guild_id = $1 AND channel_id = $2 AND emoji = $3",
                ctx.guild.id,
                channel.id,
                emoji,
            )
        except Exception:
            await ctx.fail(f"There isn't a **starboard** using **{emoji}**")
        else:
            await ctx.success(
                f"Removed the **starboard** for {channel.mention} using **{emoji}**"
            )

    @starboard.command(
        name="list",
        aliases=["show", "all"],
        brief="List all the Starboards currently set to the starboard channel",
        example=",starboard list",
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard_list(self, ctx: Context):
        starboards = [
            f"{channel.mention} - **{row['emoji']}** (threshold: `{row['threshold']}`)"
            async for row in self.bot.db.fetchiter(
                "SELECT channel_id, emoji, threshold FROM starboard WHERE guild_id = $1",
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(row["channel_id"]))
        ]
        if not starboards:
            return await ctx.fail("No **starboards** have been set up")

        await self.bot.dummy_paginator(
            ctx, discord.Embed(title="Starboards", color=self.bot.color), starboards
        )

    @starboard.command(
        name="ignore",
        example=",starboard ignore #shame",
        brief="Ignore a channel from being added to the starboard",
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard_ignore(self, ctx: Context, channel: discord.TextChannel):
        """Adds a channel to the ignored list for the starboard."""
        try:
            await self.bot.db.execute(
                "INSERT INTO starboard_ignored (guild_id, channel_id) VALUES ($1, $2)",
                ctx.guild.id,
                channel.id,
            )
        except UniqueViolationError:
            await ctx.fail(f"**{channel.mention}** is already being ignored")
        except Exception as e:
            logger.error(f"Error in starboard_ignore: {e}")
            await ctx.fail("An unexpected error occurred. Please try again later.")
        else:
            await ctx.success(f"Ignored **{channel.mention}**")

    @starboard.command(
        name="unignore",
        example=",starboard unignore #shame",
        brief="Unignore a channel from being added to the starboard",
    )
    @commands.has_permissions(manage_guild=True)
    async def starboard_unignore(self, ctx: Context, channel: discord.TextChannel):
        """Removes a channel from the ignored list for the starboard."""
        try:
            result = await self.bot.db.execute(
                "DELETE FROM starboard_ignored WHERE guild_id = $1 AND channel_id = $2",
                ctx.guild.id,
                channel.id,
            )
            if result == "DELETE 0":
                return await ctx.fail(f"**{channel.mention}** is not being ignored")

        except Exception as e:
            logger.error(f"Error in starboard_unignore: {e}")
            await ctx.fail("An unexpected error occurred. Please try again later.")
        else:
            await ctx.success(f"Unignored **{channel.mention}**")


async def setup(bot):
    await bot.add_cog(starboard(bot))
