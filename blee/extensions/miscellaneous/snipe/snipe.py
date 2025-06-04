import re
from contextlib import suppress
from typing import Optional, cast

from discord import Embed, File, HTTPException, Member, Message, Reaction, User
from discord.ext.commands import (BucketType, Cog, command, cooldown, group,
                                  has_permissions)
from discord.utils import format_dt, utcnow
from humanize import naturaldelta
from orjson import dumps, loads
from tools.client.context import Context
from tools.managers.paginator import Paginator
from tools.utilities import CompositeMetaClass, MixinMeta, Plural

from .models import EditSnipe, MessageSnipe, ReactionSnipe

INVITE_PATTERN = re.compile(
    r"(?:(?:https?://)?(?:www)?discord(?:app)?\.(?:(?:com|gg)/invite/[a-z0-9-_]+)|(?:https?://)?(?:www)?discord\.gg/[a-z0-9-_]+)"
)
LINK_PATTERN = re.compile(r"(https?://\S+)")


class Snipe(MixinMeta, metaclass=CompositeMetaClass):
    """
    Snipe deletion events.
    """

    @Cog.listener("on_message_edit")
    async def push_edit_snipe(self, before: Message, after: Message) -> None:
        """Push an edited message to the editsnipe cache."""
        if before.content == after.content:
            return

        await EditSnipe.push(self.bot.redis, before, after)

    @Cog.listener("on_message_delete")
    async def push_snipe(self, message: Message) -> None:
        """
        Push a message to the snipe cache.
        """

        await MessageSnipe.push(self.bot.redis, message)

    @Cog.listener("on_reaction_remove")
    async def push_reaction_snipe(
        self,
        reaction: Reaction,
        user: User,
    ) -> None:
        """
        Push a reaction to the snipe cache.
        """

        await ReactionSnipe.push(self.bot.redis, reaction, user)

    @command(example="3", aliases=["s"], notes="Results expire in 2h")
    @cooldown(2, 5, BucketType.member)
    #    @has_permissions(manage_messages=True)
    async def snipe(self, ctx: Context, index: int = 1) -> Message:
        """
        Snipe the latest message that was deleted
        """

        message = await MessageSnipe.get(self.bot.redis, ctx.channel.id, index)
        snipes = await self.bot.redis.llen(MessageSnipe.key(ctx.channel.id))

        if not message:
            return await ctx.utility(
                (
                    f"No **snipe** found for `Index {index}`"
                    if index != 1
                    else f"No **deleted messages** found in the past **2 hours**!"
                ),
                emoji=":mag_right:",
            )

        if (
            not ctx.channel.permissions_for(ctx.author).manage_messages
            and ctx.author.id not in self.bot.owner_ids
        ):
            if message.filtered:
                return await ctx.reply("bot filtered the msg lil bro")

            config = await self.bot.db.fetchrow(
                """
                    SELECT *, ARRAY(SELECT user_id FROM snipe.ignore WHERE guild_id = $1) AS ignored_ids
                    FROM snipe.filter
                    WHERE guild_id = $1
                    """,
                ctx.guild.id,
            )
            if config:
                if message.user_id in config.get("ignored_ids", []):
                    return await ctx.warn(
                        f"**{message.user_name}** is immune to being sniped!"
                    )

                if config["invites"]:
                    message.content = INVITE_PATTERN.sub(
                        "*`REDACTED INVITE`*", message.content
                    )

                if config["links"] and message.content.startswith("http"):
                    message.content = LINK_PATTERN.sub(
                        "*`REDACTED LINK`*", message.content
                    )

                for word in config["words"]:
                    if word in message.content.lower():
                        return await ctx.reply("that msg probably shouldn't be sniped")

        file: Optional[File] = None
        embed = Embed(description=message.content)
        embed.set_author(
            name=message.user_name,
            icon_url=message.user_avatar,
        )
        embed.set_footer(
            text="".join(
                [
                    f"Deleted {naturaldelta((utcnow() - message.deleted_at))} ago",
                    f" • {index}/{snipes} message",
                ]
            ),
        )

        if message.attachments:
            for attachment in message.attachments:
                if attachment.is_image():
                    embed.set_image(url=attachment.url)
                    break

                if attachment.size > 25e6:
                    continue

                async with ctx.typing():
                    with suppress(HTTPException):
                        file = await attachment.to_file(self.bot.http)
                        break

            embed.add_field(
                name=f"**Attachment{'s' if len(message.attachments) > 1 else ''}**",
                value="\n".join([attachment.url for attachment in message.attachments]),
            )

        elif message.stickers:
            sticker_url = message.stickers[0]
            embed.set_image(url=sticker_url)

        return await ctx.reply(embed=embed, file=file)

    @command(aliases=["clearsnipes", "cs"])
    @cooldown(1, 10, BucketType.channel)
    @has_permissions(manage_messages=True)
    async def clearsnipe(self, ctx: Context) -> None:
        """
        Clear all results for reactions, edits and messages
        """

        message_key = MessageSnipe.key(ctx.channel.id)
        reaction_key = ReactionSnipe.key(ctx.channel.id)
        edit_key = EditSnipe.key(ctx.channel.id)

        await self.bot.redis.delete(message_key, reaction_key, edit_key)

        return await ctx.add_check()

    @command(aliases=["rsnipe", "rs"])
    @cooldown(1, 3, BucketType.channel)
    async def reactionsnipe(self, ctx: Context, index: int = 1) -> Message:
        """
        Snipe the last removed reaction.
        """

        reaction = await ReactionSnipe.get(self.bot.redis, ctx.channel.id)
        if not reaction:
            return await ctx.utility(
                (
                    f"No **sniped reaction** available at index `{index}`!"
                    if index != 1
                    else f"No **removed reaction** found in the last **5 minutes**!"
                ),
                emoji=":mag_right:",
            )

        return await ctx.neutral(
            f"**{reaction.user_name}** reacted with **{reaction.emoji}** {format_dt(reaction.removed_at, 'R')}",
            reference=ctx.message,
        )

    @command(example="3", aliases=["es", "esnipe"], notes="Results expire in 2h")
    @cooldown(2, 5, BucketType.member)
    async def editsnipe(self, ctx: Context, index: int = 1) -> Message:
        """
        Snipe the latest message that was edited
        """

        edit = await EditSnipe.get(self.bot.redis, ctx.channel.id, index)
        edits = await self.bot.redis.llen(EditSnipe.key(ctx.channel.id))

        if not edit:
            return await ctx.utility(
                (
                    f"No **edit** found for `Index {index}`"
                    if index != 1
                    else f"No **edited messages** found in the past **2 hours**!"
                ),
                emoji=":mag_right:",
            )

        embed = Embed(description=f"{edit.before_content}")
        embed.set_author(
            name=edit.user_name,
            icon_url=edit.user_avatar,
        )
        embed.set_footer(
            text=f"Edited {naturaldelta((utcnow() - edit.edited_at))} ago ∙ {index}/{edits} edits"
        )

        return await ctx.reply(embed=embed)
