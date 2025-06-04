from typing import Dict, Optional, Union
from discord.ext import commands, tasks
from discord.ext.commands import (
    Cog,
    group,
    has_permissions,
    parameter,
    Range,
    BadArgument,
    cooldown,
    max_concurrency,
    BadUnionArgument,
    BucketType,
)
from discord import (
    Message,
    File,
    PartialEmoji,
    Embed,
    GuildSticker,
    Emoji,
    HTTPException,
    RateLimited,
)
from io import BytesIO
import cairosvg
from asyncio import gather
from contextlib import suppress
from system.base.context import Context
from system.tools.converters.image import resize as resize_image
from system.tools.metaclass import CompositeMetaClass, MixinMeta
from re import compile, sub, finditer
from loguru import logger as log
from discord import Emoji as DiscordEmoji
from system.tools.utils import codeblock
from system.tools.converters import PartialAttachment
from datetime import datetime, timedelta
from humanize import precisedelta
from aiohttp import ClientSession
from system.tools.converters.emojis import EmojiFinder, ImageFinder
from system.tools.utils import Plural
from zipfile import ZipFile


DISCORD_EMOJI = compile(r"<(?P<animated>a)?:(?P<name>[a-zA-Z0-9_]+):(?P<id>\d+)>")
UNICODE_EMOJI = compile(
    r"(?:\U0001f1e6[\U0001f1e8-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f2\U0001f1f4\U0001f1f6-\U0001f1fa\U0001f1fc\U0001f1fd\U0001f1ff])|(?:\U0001f1e7[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ef\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1e8[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ee\U0001f1f0-\U0001f1f5\U0001f1f7\U0001f1fa-\U0001f1ff])|(?:\U0001f1e9[\U0001f1ea\U0001f1ec\U0001f1ef\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1ff])|(?:\U0001f1ea[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ed\U0001f1f7-\U0001f1fa])|(?:\U0001f1eb[\U0001f1ee-\U0001f1f0\U0001f1f2\U0001f1f4\U0001f1f7])|(?:\U0001f1ec[\U0001f1e6\U0001f1e7\U0001f1e9-\U0001f1ee\U0001f1f1-\U0001f1f3\U0001f1f5-\U0001f1fa\U0001f1fc\U0001f1fe])|(?:\U0001f1ed[\U0001f1f0\U0001f1f2\U0001f1f3\U0001f1f7\U0001f1f9\U0001f1fa])|(?:\U0001f1ee[\U0001f1e8-\U0001f1ea\U0001f1f1-\U0001f1f4\U0001f1f6-\U0001f1f9])|(?:\U0001f1ef[\U0001f1ea\U0001f1f2\U0001f1f4\U0001f1f5])|(?:\U0001f1f0[\U0001f1ea\U0001f1ec-\U0001f1ee\U0001f1f2\U0001f1f3\U0001f1f5\U0001f1f7\U0001f1fc\U0001f1fe\U0001f1ff])|(?:\U0001f1f1[\U0001f1e6-\U0001f1e8\U0001f1ee\U0001f1f0\U0001f1f7-\U0001f1fb\U0001f1fe])|(?:\U0001f1f2[\U0001f1e6\U0001f1e8-\U0001f1ed\U0001f1f0-\U0001f1ff])|(?:\U0001f1f3[\U0001f1e6\U0001f1e8\U0001f1ea-\U0001f1ec\U0001f1ee\U0001f1f1\U0001f1f4\U0001f1f5\U0001f1f7\U0001f1fa\U0001f1ff])|\U0001f1f4\U0001f1f2|(?:\U0001f1f4[\U0001f1f2])|(?:\U0001f1f5[\U0001f1e6\U0001f1ea-\U0001f1ed\U0001f1f0-\U0001f1f3\U0001f1f7-\U0001f1f9\U0001f1fc\U0001f1fe])|\U0001f1f6\U0001f1e6|(?:\U0001f1f6[\U0001f1e6])|(?:\U0001f1f7[\U0001f1ea\U0001f1f4\U0001f1f8\U0001f1fa\U0001f1fc])|(?:\U0001f1f8[\U0001f1e6-\U0001f1ea\U0001f1ec-\U0001f1f4\U0001f1f7-\U0001f1f9\U0001f1fb\U0001f1fd-\U0001f1ff])|(?:\U0001f1f9[\U0001f1e6\U0001f1e8\U0001f1e9\U0001f1eb-\U0001f1ed\U0001f1ef-\U0001f1f4\U0001f1f7\U0001f1f9\U0001f1fb\U0001f1fc\U0001f1ff])|(?:\U0001f1fa[\U0001f1e6\U0001f1ec\U0001f1f2\U0001f1f3\U0001f1f8\U0001f1fe\U0001f1ff])|(?:\U0001f1fb[\U0001f1e6\U0001f1e8\U0001f1ea\U0001f1ec\U0001f1ee\U0001f1f3\U0001f1fa])|(?:\U0001f1fc[\U0001f1eb\U0001f1f8])|\U0001f1fd\U0001f1f0|(?:\U0001f1fd[\U0001f1f0])|(?:\U0001f1fe[\U0001f1ea\U0001f1f9])|(?:\U0001f1ff[\U0001f1e6\U0001f1f2\U0001f1fc])|(?:[#*0-9]\uFE0F\u20E3)|(?:\u2764\uFE0F)|(?:\u2122\uFE0F)|(?:\u2611\uFE0F)|(?:\u26A0\uFE0F)|(?:\u2B06\uFE0F)|(?:\u2B07\uFE0F)|(?:\u2934\uFE0F)|(?:\u2935\uFE0F)|[\u2190-\u21ff]"
)
ALL_EMOJI = compile(f"{DISCORD_EMOJI.pattern}|{UNICODE_EMOJI.pattern}")


class CustomEmoji:
    def __init__(self, name: str, url: str, id: int, animated: bool):
        self.name = name
        self.url = url
        self.id = id
        self.animated = animated

    async def read(self):
        async with ClientSession() as session:
            async with session.get(self.url) as response:
                return await response.read()


class emoji(MixinMeta, metaclass=CompositeMetaClass):
    emoji_stats_cache: Dict[tuple[int, str], int] = {}

    def __init__(self):
        super().__init__()

    async def cog_load(self) -> None:
        self.update_emoji_cache.start()

    def cog_unload(self):
        self.update_emoji_cache.cancel()

    @tasks.loop(seconds=60.0)
    async def update_emoji_cache(self):
        if not hasattr(self, "emoji_stats_cache"):
            self.emoji_stats_cache = {}
            return

        if not self.emoji_stats_cache:
            return

        try:
            stats_data = [
                (guild_id, emoji_id, uses)
                for (guild_id, emoji_id), uses in self.emoji_stats_cache.items()
            ]

            async with self.bot.db.pool.acquire() as conn:
                await conn.executemany(
                    """
                    INSERT INTO emoji_stats (guild_id, emoji_id, uses)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (guild_id, emoji_id)
                    DO UPDATE SET uses = emoji_stats.uses + EXCLUDED.uses
                """,
                    stats_data,
                )

            self.emoji_stats_cache.clear()

        except Exception as e:
            log.exception(f"Failed to update emoji stats: {e}")

    @update_emoji_cache.before_loop
    async def before_update_emoji_cache(self):
        await self.bot.wait_until_ready()

    @Cog.listener()
    async def on_message(self, message: Message):
        if not message.guild or message.author.bot:
            return

        if not hasattr(self, "emoji_stats_cache"):
            self.emoji_stats_cache = {}

        for match in DISCORD_EMOJI.finditer(message.content):
            if emoji_id := match.group("id"):
                cache_key = (message.guild.id, emoji_id)
                self.emoji_stats_cache[cache_key] = (
                    self.emoji_stats_cache.get(cache_key, 0) + 1
                )

    async def get_emoji_stats(self, guild_id: int, emoji_id: str) -> int:
        if not hasattr(self, "emoji_stats_cache"):
            self.emoji_stats_cache = {}

        cache_key = (guild_id, emoji_id)
        cached_uses = self.emoji_stats_cache.get(cache_key, 0)

        if result := await self.bot.db.fetchrow(
            "SELECT uses FROM emoji_stats WHERE guild_id = $1 AND emoji_id = $2",
            guild_id,
            emoji_id,
        ):
            return cached_uses + result["uses"]
        return cached_uses

    @group(
        name="emoji",
        usage="(subcommand) <args>",
        aliases=["emote", "e"],
        example="🔥",
        invoke_without_command=True,
    )
    async def emoji(self, ctx: Context, *, emoji: EmojiFinder | PartialEmoji = None):
        """
        View an emoji in full size
        """
        if not emoji:
            return await ctx.send_help(ctx.command)

        async with ctx.typing():
            async with self.bot.session.get(emoji.url, timeout=5) as response:
                if response.status != 200:
                    return await ctx.warn("Failed to fetch emoji")

                content_type = response.headers.get("Content-Type", "")
                image_data = await response.read()

                if "svg" in content_type:
                    log.info(f"SVG Data: {image_data[:100]}...")
                    try:
                        from cairosvg import svg2png

                        image_data = svg2png(
                            bytestring=image_data,
                            output_width=256,
                            output_height=256,
                        )
                    except Exception as e:
                        log.error(f"SVG conversion failed: {e}")
                        return await ctx.warn("**emoji** is not a valid **image**")

                is_gif = "gif" in content_type or getattr(emoji, "animated", False)

                if is_gif:
                    try:
                        from wand.image import Image

                        with Image(blob=image_data) as img:
                            width, height = img.size
                            ratio = min(256 / width, 256 / height)
                            new_size = (int(width * ratio), int(height * ratio))
                            img.resize(*new_size)

                            processed_data = BytesIO(img.make_blob())

                    except Exception as e:
                        log.error(f"GIF resize failed: {e}")
                        processed_data = BytesIO(image_data)
                else:
                    processed_data = await resize_image(BytesIO(image_data), (256, 256))

                file = File(
                    processed_data,
                    filename=f"emoji.{'gif' if is_gif else 'png'}",
                )
            return await ctx.send(file=file, reference=ctx.message)

    @emoji.command(
        name="add",
        usage="(emoji or url) [name]",
        example=" cdn.discordapp.com/emojis/768...png mommy",
        aliases=["create", "copy"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_add(
        self,
        ctx: Context,
        emoji: DiscordEmoji | PartialEmoji | ImageFinder | int | None,
        *,
        name: str = None,
    ):
        """
        Downloads emote and adds to server
        """

        if not emoji:
            try:
                emoji = await ImageFinder.search(ctx, history=False)
            except Exception:
                return await ctx.warn("Could not convert **emoji** into `Emote or URL`")

        if isinstance(emoji, Emoji) and emoji.guild_id == ctx.guild.id:
            return await ctx.warn("That **emoji** is already in this server")

        # Determine if emoji is animated and set name
        is_animated = False
        if type(emoji) in (Emoji, PartialEmoji):
            name = name or emoji.name
            is_animated = emoji.animated
        elif isinstance(emoji, int):
            emoji = f"https://cdn.discordapp.com/emojis/{emoji}.png"
            if not name:  # Need name for URL/integer emoji IDs
                return await ctx.warn("Missing **name** for server emote")
        elif isinstance(emoji, str):
            if not name:
                return await ctx.warn("Missing **name** for server emote")
            is_animated = emoji.endswith(".gif")

        if len(name) < 2:
            return await ctx.warn("Emote name needs to be **2 characters** or **more**")
        name = name[:32].replace(" ", "_")

        # Count current animated and normal emojis
        animated_count = sum(1 for e in ctx.guild.emojis if e.animated)
        normal_count = len(ctx.guild.emojis) - animated_count

        # Check appropriate limit
        if is_animated and animated_count >= ctx.guild.emoji_limit:
            return await ctx.warn(
                f"The maximum amount of **animated emojis** has been reached (`{ctx.guild.emoji_limit}`)"
            )
        elif not is_animated and normal_count >= ctx.guild.emoji_limit:
            return await ctx.warn(
                f"The maximum amount of **normal emojis** has been reached (`{ctx.guild.emoji_limit}`)"
            )

        response = await self.bot.session.get(
            emoji if isinstance(emoji, str) else emoji.url
        )
        image = await response.read()

        try:
            emoji = await ctx.guild.create_custom_emoji(
                name=name, image=image, reason=f"{ctx.author}: Emoji added"
            )
        except RateLimited as error:
            return await ctx.warn(
                f"Please try again in **{error.retry_after:.2f} seconds**"
            )
        except HTTPException:
            return await ctx.warn(
                f"Failed to add **emote** [`:{name}:`]({response.url})"
            )

        await ctx.approve(
            f"Added **emote** [`:{emoji.name}:`]({emoji.url}) {emoji}",
        )

    @emoji.command(
        name="addmany",
        usage="(emojis)",
        example="hella_emotes_here",
        aliases=["am"],
    )
    @has_permissions(manage_emojis=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_add_many(self, ctx: Context, *, emojis: str = None):
        """
        Bulk add emojis to the server
        """
        if not emojis:
            return await ctx.warn("Please provide some emojis to add!")

        if len(ctx.guild.emojis) >= ctx.guild.emoji_limit:
            return await ctx.warn(
                f"This server has reached its emoji limit ({ctx.guild.emoji_limit})"
            )

        matches = list(finditer(DISCORD_EMOJI, emojis))
        if not matches:
            return await ctx.warn(
                "No valid Discord emojis found! Make sure you're using custom emojis, not Unicode emojis.\n"
                "Example: `:emoji_name:`"
            )

        existing_emoji_ids = {emoji.id for emoji in ctx.guild.emojis}
        emojis_to_add = []

        for match in matches:
            emoji_id = int(match.group("id"))
            if emoji_id not in existing_emoji_ids:
                emojis_to_add.append(
                    CustomEmoji(
                        name=match.group("name"),
                        url=f"https://cdn.discordapp.com/emojis/{match.group('id')}{'.gif' if match.group('animated') else '.png'}",
                        id=emoji_id,
                        animated=bool(match.group("animated")),
                    )
                )

        if not emojis_to_add:
            return await ctx.warn(
                "All provided emojis either already exist in this server or are invalid!"
            )

        available_slots = ctx.guild.emoji_limit - len(ctx.guild.emojis)
        if len(emojis_to_add) > available_slots:
            await ctx.warn(
                f"Only adding the first {available_slots} emojis due to server limit"
            )
            emojis_to_add = emojis_to_add[:available_slots]

        emojis_added = []
        failed = []

        async with ctx.typing():
            for emoji in emojis_to_add:
                try:
                    async with self.bot.session.get(emoji.url) as response:
                        if response.status != 200:
                            failed.append(emoji.name)
                            continue
                        image = await response.read()

                    new_emoji = await ctx.guild.create_custom_emoji(
                        name=emoji.name,
                        image=image,
                        reason=f"{ctx.author}: Emoji added (bulk)",
                    )
                    emojis_added.append(new_emoji)

                except (RateLimited, HTTPException) as error:
                    retry_after = getattr(error, "retry_after", None)
                    if retry_after:  # This is a rate limit error
                        await ctx.warn(
                            f"Rate limited! Please wait **{precisedelta(timedelta(seconds=retry_after))}**"
                            + (
                                f"\nSuccessfully added {len(emojis_added)} emojis before being rate limited"
                                if emojis_added
                                else ""
                            )
                        )
                        break
                    else:  # This is a different HTTP error
                        failed.append(emoji.name)
                        log.error(f"Failed to add emoji {emoji.name}: {str(error)}")
                        continue

        response = []
        if emojis_added:
            response.append(
                f"Successfully added **{Plural(len(emojis_added)):new emote}**\n{' '.join(str(e) for e in emojis_added)}"
            )
        if failed:
            response.append(f"Failed to add: {', '.join(failed)}")

        if response:
            await ctx.approve("\n".join(response))
        else:
            await ctx.warn("No **emojis** were added to the server")

    @emoji.command(
        name="remove",
        usage="(emoji)",
        example="🦮",
        aliases=["delete", "del"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_remove(self, ctx: Context, emoji: DiscordEmoji):
        """
        Remove an emoji from the server
        """
        if emoji.guild_id != ctx.guild.id:
            return await ctx.warn("That emoji is not from this server")

        try:
            await emoji.delete(reason=f"{ctx.author}: Emoji removed")
            await ctx.approve(f"Removed emoji `:{emoji.name}:`")
        except HTTPException:
            await ctx.warn(f"Failed to remove emoji `:{emoji.name}:`")

    @emoji.command(
        name="removemany",
        usage="(emojis)",
        example="🦮 🐕 🐶",
        aliases=["rm", "deletemany"],
    )
    @has_permissions(manage_emojis=True)
    @max_concurrency(1, BucketType.guild)
    async def emoji_remove_many(self, ctx: Context, *emojis: DiscordEmoji):
        """
        Remove multiple emojis from the server
        """
        if not emojis:
            return await ctx.warn("Please provide some emojis to remove!")

        # Filter out emojis not from this server
        valid_emojis = [emoji for emoji in emojis if emoji.guild_id == ctx.guild.id]

        if not valid_emojis:
            return await ctx.warn("None of the provided emojis are from this server")

        removed = []
        failed = []

        async with ctx.typing():
            for emoji in valid_emojis:
                try:
                    await emoji.delete(reason=f"{ctx.author}: Emoji removed (bulk)")
                    removed.append(emoji.name)
                except HTTPException:
                    failed.append(emoji.name)
                    continue

        response = []
        if removed:
            response.append(
                f"Successfully removed **{Plural(len(removed)):emoji}**: {', '.join(removed)}"
            )
        if failed:
            response.append(f"Failed to remove: {', '.join(failed)}")

        if response:
            await ctx.approve("\n".join(response))
        else:
            await ctx.warn("No **emojis** were removed from the server")

    @emoji.command(
        name="rename",
        usage="(emoji) (new name)",
        example="🦮 daddy",
        aliases=["name"],
    )
    @has_permissions(manage_emojis=True)
    async def emoji_rename(
        self,
        ctx: Context,
        emoji: DiscordEmoji | PartialEmoji,
        *,
        new_name: str,
    ):
        """
        Rename a server emoji
        """
        # Check if emoji is from this server
        if not isinstance(emoji, DiscordEmoji) or emoji.guild_id != ctx.guild.id:
            return await ctx.warn("That emoji is not from this server")

        # Clean and validate the new name
        new_name = new_name.strip().replace(" ", "_")[:32]
        if len(new_name) < 2:
            return await ctx.warn("Emoji name must be at least 2 characters long")

        try:
            old_name = emoji.name
            await emoji.edit(name=new_name, reason=f"{ctx.author}: Emoji renamed")
            await ctx.approve(
                f"Renamed emoji from `:{old_name}:` to `:{new_name}:` {emoji}"
            )
        except HTTPException:
            await ctx.warn(f"Failed to rename emoji `:{emoji.name}:`")

    @emoji.command(
        name="stats", usage="(emote)", example="🔥", aliases=["usage", "uses"]
    )
    @has_permissions(manage_emojis=True)
    async def emoji_stats(self, ctx: Context, emote: PartialEmoji = None):
        """
        Get the usage statistics of emojis in the server.
        """
        if emote:
            uses = await self.get_emoji_stats(ctx.guild.id, str(emote.id or emote))
            return await ctx.embed(
                title="Emoji Statistics",
                description=f"{emote} has been used **{uses:,}** times in this server",
                author={
                    "name": ctx.author.display_name,
                    "icon_url": ctx.author.display_avatar.url,
                },
            )

        records = await self.bot.db.fetch(
            """
            SELECT emoji_id, uses 
            FROM emoji_stats 
            WHERE guild_id = $1 
            ORDER BY uses DESC
        """,
            ctx.guild.id,
        )

        if not records:
            return await ctx.warn("No emoji **statistics** for this server")

        valid_records = []
        for record in records:
            emoji_id = record["emoji_id"]

            if not emoji_id.isdigit() or (emoji := self.bot.get_emoji(int(emoji_id))):
                valid_records.append((emoji_id, record["uses"]))
                if len(valid_records) == 10:
                    break

        if not valid_records:
            return await ctx.warn("No active emoji statistics found for this server")

        total_uses = sum(uses for _, uses in valid_records)

        description = []
        for i, (emoji_id, uses) in enumerate(valid_records, 1):
            emoji = (
                self.bot.get_emoji(int(emoji_id)) if emoji_id.isdigit() else emoji_id
            )
            uses_per_day = round(uses / 30)
            percentage = (uses / total_uses) * 100

            description.append(
                f"`{i}` {emoji} has **{uses}** with "
                f"**{uses_per_day}** use{'s' if uses_per_day != 1 else ''} "
                f"a day `[{percentage:.1f}%]`"
            )

        await ctx.embed(
            title="Emote Leaderboard",
            description="**Top 10**\n" + "\n".join(description),
            author={
                "name": ctx.author.display_name,
                "icon_url": ctx.author.display_avatar.url,
            },
        )

    @emoji.command(
        name="removeduplicates",
    )
    @has_permissions(manage_emojis=True)
    @cooldown(1, 120, BucketType.user)
    async def emoji_removeduplicates(self, ctx: Context):
        """
        Remove all emojis that has a duplicate
        """

        if not ctx.guild.emojis:
            return await ctx.warn("There are **no emojis**")

        duplicates = set()
        seen = set()
        emojis_bytes = await gather(*(emoji.read() for emoji in ctx.guild.emojis))

        for emoji, emoji_bytes in zip(ctx.guild.emojis, emojis_bytes):
            if emoji_bytes in seen:
                duplicates.add(emoji)

            else:
                seen.add(emoji_bytes)

        removed = await gather(
            *(
                duplicate.delete(
                    reason=f"{self.bot.user.name.title()} Utilities[{ctx.author}]: Duplicate emoji"
                )
                for duplicate in duplicates
            )
        )
        if not removed:
            return await ctx.warn("No **duplicated** emojis found")

        return await ctx.approve(f"**Removed** `{len(removed)}` duplicated emojis")

    @group(name="sticker", invoke_without_command=True)
    @has_permissions(manage_expressions=True)
    async def sticker(self, ctx: Context) -> Message:
        """
        Various sticker related commands.
        """

        return await ctx.send_help(ctx.command)

    @sticker.command(
        name="add",
        aliases=["create", "upload"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_add(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]],
    ) -> Optional[Message]:
        """
        Add a sticker to the server.
        """

        if not ctx.message.stickers or not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.warn(
                "The server is at the **maximum** amount of stickers!"
            )

        sticker = await sticker.fetch()
        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the sticker!", codeblock(exc.text))

        return await ctx.add_check()

    @sticker.command(
        name="steal",
        aliases=["grab"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_steal(
        self,
        ctx: Context,
        name: Optional[Range[str, 2, 32]] = None,
    ) -> Optional[Message]:
        """
        Steal a sticker from a message.
        """

        message: Optional[Message] = ctx.replied_message
        if not message:
            async for _message in ctx.channel.history(limit=25, before=ctx.message):
                if _message.stickers:
                    message = _message
                    break

        if not message:
            return await ctx.warn(
                "I couldn't find a message with a sticker in the past 25 messages!"
            )

        if not message.stickers:
            return await ctx.warn("That message doesn't have any stickers!")

        if len(ctx.guild.stickers) == ctx.guild.sticker_limit:
            return await ctx.warn(
                "The server is at the **maximum** amount of stickers!"
            )

        sticker = await message.stickers[0].fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id == ctx.guild.id:
            return await ctx.warn("That sticker is already in this server!")

        try:
            await ctx.guild.create_sticker(
                name=name or sticker.name,
                description=sticker.description,
                emoji=sticker.emoji,
                file=File(BytesIO(await sticker.read())),
                reason=f"Created by {ctx.author} ({ctx.author.id})",
            )
        except RateLimited as exc:
            retry_after = timedelta(seconds=exc.retry_after)
            return await ctx.warn(
                f"The server is currently ratelimited, try again in **{precisedelta(retry_after)}**!"
            )

        except HTTPException as exc:
            return await ctx.warn("Failed to create the sticker!", codeblock(exc.text))

        return await ctx.add_check()

    @sticker.command(
        name="rename",
        aliases=["name"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_rename(
        self,
        ctx: Context,
        *,
        name: str,
    ) -> Message:
        """
        Rename an existing sticker.
        """

        if not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.warn("That sticker is not in this server!")

        elif len(name) < 2:
            return await ctx.warn(
                "The sticker name must be at least **2 characters** long!"
            )

        name = name[:32]
        await sticker.edit(
            name=name,
            reason=f"Updated by {ctx.author} ({ctx.author.id})",
        )

        return await ctx.approve(f"Renamed the sticker to **{name}**")

    @sticker.command(
        name="delete",
        aliases=["remove", "del"],
    )
    @has_permissions(manage_expressions=True)
    async def sticker_delete(
        self,
        ctx: Context,
    ) -> Optional[Message]:
        """
        Delete an existing sticker.
        """

        if not (sticker := ctx.message.stickers[0]):
            return await ctx.send_help(ctx.command)

        sticker = await sticker.fetch()

        if not isinstance(sticker, GuildSticker):
            return await ctx.warn("Stickers cannot be default stickers!")

        if sticker.guild_id != ctx.guild.id:
            return await ctx.warn("That sticker is not in this server!")

        await sticker.delete(reason=f"Deleted by {ctx.author} ({ctx.author.id})")
        return await ctx.add_check()

    @sticker.command(
        name="archive",
        aliases=["zip"],
    )
    @has_permissions(manage_expressions=True)
    @cooldown(1, 30, BucketType.guild)
    async def sticker_archive(self, ctx: Context) -> Message:
        """
        Archive all stickers into a zip file.
        """

        if ctx.guild.premium_tier < 2:
            return await ctx.warn(
                "The server must have at least Level 2 to use this command!"
            )

        await ctx.neutral("Starting the archival process...")

        async with ctx.typing():
            buffer = BytesIO()
            with ZipFile(buffer, "w") as zip:
                for index, sticker in enumerate(ctx.guild.stickers):
                    name = f"{sticker.name}.{sticker.format}"
                    if name in zip.namelist():
                        name = f"{sticker.name}_{index}.{sticker.format}"

                    __buffer = await sticker.read()

                    zip.writestr(name, __buffer)

            buffer.seek(0)

        if ctx.response:
            with suppress(HTTPException):
                await ctx.response.delete()

        return await ctx.reply(
            file=File(
                buffer,
                filename=f"{ctx.guild.name}_stickers.zip",
            ),
        )
