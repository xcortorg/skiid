import asyncio
from typing import Optional, cast

from asyncpg import UniqueViolationError
from core.client.context import Context
from core.managers.script import EmbedScript, EmbedScriptValidator
from core.tools import (CompositeMetaClass, MixinMeta, codeblock,
                        quietly_delete, vowel)
from discord import Embed, HTTPException, Message, TextChannel, Thread
from discord.ext.commands import Cog, group, has_permissions
from discord.utils import utcnow
from xxhash import xxh32_hexdigest


class Sticky(MixinMeta, metaclass=CompositeMetaClass):
    """
    Stick messages to the bottom of a channel.
    """

    @Cog.listener("on_message")
    async def sticky_listener(self, message: Message) -> None:
        """
        Stick messages to the bottom of a channel.
        We don't want to send sticky messages constantly, so we'll
        only send them if messages haven't been sent within 3 seconds.
        """

        if (
            not message.guild
            or message.author.bot
            or not isinstance(
                message.channel,
                (TextChannel, Thread),
            )
        ):
            return

        guild = message.guild
        channel = message.channel
        record = await self.bot.db.fetchrow(
            """
            SELECT message_id, template
            FROM sticky_message
            WHERE guild_id = $1
            AND channel_id = $2
            """,
            guild.id,
            channel.id,
        )
        if not record:
            return

        key = xxh32_hexdigest(f"sticky:{channel.id}")
        locked = await self.bot.redis.get(key)
        if locked:
            return

        await self.bot.redis.set(key, 1, 6)
        last_message = channel.get_partial_message(record["message_id"])
        time_since = utcnow() - last_message.created_at
        time_to_wait = 6 - time_since.total_seconds()
        if time_to_wait > 1:
            await asyncio.sleep(time_to_wait)

        script = EmbedScript(record["template"])

        try:
            new_message = await script.send(
                channel,
                guild=guild,
                channel=channel,
                user=message.author,
            )
        except HTTPException:
            await self.bot.db.execute(
                """
                DELETE FROM sticky_message
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                guild.id,
                channel.id,
            )
        else:
            await self.bot.db.execute(
                """
                UPDATE sticky_message
                SET message_id = $3
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                guild.id,
                channel.id,
                new_message.id,
            )
        finally:
            await self.bot.redis.delete(key)
            await quietly_delete(last_message)

    @group(
        name="sticky",
        usage="(subcommand) <args>",
        example="add #selfie Oh look at me!",
        aliases=["stickymessage", "sm"],
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def sticky(self, ctx: Context):
        """Set up sticky messages in one or multiple channels"""
        await ctx.send_help(ctx.command)

    @sticky.command(
        name="add",
        usage="(channel) (message)",
        example="#selfie Oh look at me!",
        aliases=["create"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_add(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
        *,
        script: EmbedScriptValidator,
    ) -> Message:
        """Add a sticky message to a channel"""

        try:
            message = await script.send(
                channel,
                guild=ctx.guild,
                channel=channel,
                user=ctx.author,
            )
            await self.bot.db.execute(
                """
                INSERT INTO sticky_message (
                    guild_id,
                    channel_id,
                    message_id,
                    template
                )
                VALUES ($1, $2, $3, $4)
                """,
                ctx.guild.id,
                channel.id,
                message.id,
                script.script,
            )
        except UniqueViolationError:
            return await ctx.warn(
                "A sticky message already exists for that channel!",
            )
        except HTTPException as exc:
            return await ctx.warn(
                "Your sticky message wasn't able to be sent!", codeblock(exc.text)
            )

        return await ctx.approve(
            f"Added {vowel(script.type())} sticky message to {channel.mention}",
        )

    @sticky.command(
        name="remove",
        usage="(channel)",
        example="#selfie",
        aliases=["delete", "del", "rm"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_remove(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
    ) -> Message:
        """Remove a sticky message from a channel"""

        message_id = cast(
            Optional[int],
            await self.bot.db.fetchval(
                """
                DELETE FROM sticky_message
                WHERE guild_id = $1
                AND channel_id = $2
                RETURNING message_id
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if not message_id:
            return await ctx.warn(f"{channel.mention} doesn't have a sticky message!")

        message = channel.get_partial_message(message_id)
        await quietly_delete(message)

        return await ctx.approve(f"Removed the sticky message from {channel.mention}")

    @sticky.command(
        name="view",
        usage="(channel)",
        example="#selfie",
        aliases=["check", "test", "emit"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_view(
        self,
        ctx: Context,
        channel: TextChannel | Thread,
    ) -> Message:
        """View an existing sticky message"""

        template = cast(
            Optional[str],
            await self.bot.db.fetchval(
                """
                SELECT template
                FROM sticky_message
                WHERE guild_id = $1
                AND channel_id = $2
                """,
                ctx.guild.id,
                channel.id,
            ),
        )
        if not template:
            return await ctx.warn(f"{channel.mention} doesn't have a sticky message!")

        script = EmbedScript(template)

        await ctx.reply(codeblock(script.script))
        return await script.send(
            ctx.channel,
            guild=ctx.guild,
            channel=channel,
            user=ctx.author,
        )

    @sticky.command(
        name="list",
        aliases=["show", "all"],
    )
    @has_permissions(manage_guild=True)
    async def sticky_list(self, ctx: Context) -> Message:
        """View all channels with sticky messages"""

        channels = [
            f"{channel.mention} (`{channel.id}`) - [Message]({message.jump_url})"
            for record in await self.bot.db.fetch(
                """
                SELECT channel_id, message_id
                FROM sticky_message
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            if (channel := ctx.guild.get_channel(record["channel_id"]))
            and isinstance(channel, (TextChannel, Thread))
            and (message := channel.get_partial_message(record["message_id"]))
        ]
        if not channels:
            return await ctx.warn("No sticky messages exist for this server!")

        embed = Embed(title="Sticky Messages", color=ctx.bot.color)
        return await ctx.autopaginator(embed=embed, description=channels, split=10)


#    @sticky.command(
#        name="setup",
#        usage="(channel)",
#        example="#announcements",
#        aliases=["quickstart", "guide"],
#    )
#    @has_permissions(manage_guild=True)
#    async def sticky_setup(
#        self,
#        ctx: Context,
#        channel: TextChannel | Thread,
#    ) -> Message:
#        """Set up a sticky message with a guided process"""
#
#        await ctx.send(f"Let's set up a sticky message for {channel.mention}!")
#
#        await ctx.send("Please enter the content for your sticky message. You can use Discord's standard formatting, and even include embeds using our special syntax.")
#
#        def check(m):
#            return m.author == ctx.author and m.channel == ctx.channel
#
#        try:
#            message = await self.bot.wait_for('message', timeout=300.0, check=check)
#        except asyncio.TimeoutError:
#            return await ctx.warn("Setup timed out. Please try again.")
#
#        script = EmbedScriptValidator(message.content)
#
#        try:
#            sticky_message = await script.send(
#                channel,
#                guild=ctx.guild,
#                channel=channel,
#                user=ctx.author,
#            )
#            await self.bot.db.execute(
#                """
#                INSERT INTO sticky_message (
#                    guild_id,
#                    channel_id,
#                    message_id,
#                    template
#                )
#                VALUES ($1, $2, $3, $4)
#                """,
#                ctx.guild.id,
#                channel.id,
#                sticky_message.id,
#                script.script,
#            )
#        except UniqueViolationError:
#            return await ctx.warn(
#                "A sticky message already exists for that channel! You can remove it with `sticky remove` before setting up a new one.",
#            )
#        except HTTPException as exc:
#            return await ctx.warn(
#                "Your sticky message wasn't able to be sent!", codeblock(exc.text)
#            )
#
#        await ctx.approve(
#            f"Successfully set up {vowel(script.type())} sticky message in {channel.mention}",
#        )
#
#        return await ctx.send(
#            "Here are some tips for managing your sticky message:\n"
#            f"• To edit it, use `{ctx.prefix}sticky remove {channel.mention}` and then set it up again.\n"
#            f"• To remove it, use `{ctx.prefix}sticky remove {channel.mention}`.\n"
#            f"• To view all sticky messages in this server, use `{ctx.prefix}sticky list`.\n"
#            "Enjoy your new sticky message!"
#        )
