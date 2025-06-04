from loguru import logger as log
from asyncpg import UniqueViolationError
from discord import Embed, HTTPException, Message, TextChannel, Guild, Thread
from discord.ext.commands import (
    Cog,
    group,
    has_permissions,
    cooldown,
    BucketType,
    CommandError,
)
from system.base.embed import EmbedScript
from system.tools.metaclass import CompositeMetaClass, MixinMeta
from system.base.context import Context
import config
from typing import List
from asyncio import gather


class Nuke(MixinMeta, metaclass=CompositeMetaClass):
    """Nuke a guild."""

    async def reconfigure_settings(
        self,
        guild: Guild,
        channel: TextChannel | Thread,
        new_channel: TextChannel | Thread,
    ) -> List[str]:
        """
        Update server wide settings for a channel.
        """
        reconfigured: List[str] = []

        # Update Discord system channels
        config_map = {
            "System Channel": "system_channel",
            "Public Updates Channel": "public_updates_channel",
            "Rules Channel": "rules_channel",
            "AFK Channel": "afk_channel",
        }
        for name, attr in config_map.items():
            try:
                value = getattr(channel.guild, attr, None)
                if value == channel:
                    await guild.edit(**{attr: new_channel})  # type: ignore
                    reconfigured.append(name)
            except Exception:
                continue

        # Database tables to update
        tables = [
            "sticky_message",
            "welcome_message",
            "goodbye_message",
            "boost_message",
        ]

        # Update database entries
        for table in tables:
            try:
                result = await self.bot.db.execute(
                    f"""
                    UPDATE {table}
                    SET channel_id = $2
                    WHERE channel_id = $1
                    """,
                    channel.id,
                    new_channel.id,
                )

                if result != "UPDATE 0":
                    pretty_name = table.replace("_", " ").title()
                    reconfigured.append(pretty_name)
            except Exception:
                continue

        return reconfigured

    @group(
        name="nuke",
        invoke_without_command=True,
    )
    @cooldown(1, 25, BucketType.user)
    @has_permissions(administrator=True)
    async def nuke(self, ctx: Context) -> Message:
        """Clone the current channel. This action is irreversible."""
        channel = ctx.channel
        if not isinstance(channel, TextChannel):
            return await ctx.warn("You can only nuke text channels!")

        await ctx.prompt(
            "Are you sure you want to **nuke** this channel?",
            "This action is **irreversible** and will delete the channel!",
        )

        new_channel = await channel.clone(
            reason=f"Nuked by {ctx.author} ({ctx.author.id})",
        )
        reconfigured = await self.reconfigure_settings(ctx.guild, channel, new_channel)
        await gather(
            new_channel.edit(position=channel.position),
            channel.delete(reason=f"Nuked by {ctx.author} ({ctx.author.id})"),
        )

        if ctx.settings.nuke_view:
            return await new_channel.send(ctx.settings.nuke_view)
        if reconfigured:
            log.info(f"Reconfigured {channel.name} to {new_channel.name}")
        return await new_channel.send("hi")

    @nuke.command(
        name="message",
        usage="(message)",
        example="nuked by {user.mention}",
        aliases=["msg"],
        notes="remove to reset",
    )
    @has_permissions(administrator=True)
    async def nuke_message(self, ctx: Context, *, message: str = None):
        """Set a custom message to be sent after nuking a channel."""
        if message is None or message.lower() == "remove":
            await ctx.settings.update(nuke_view=None)
            return await ctx.approve("Reset the **nuke message** to default")

        script = EmbedScript(message)
        await script.resolve_variables(
            user=ctx.author, guild=ctx.guild, channel=ctx.channel
        )

        formatted_message = str(script)

        await ctx.settings.update(nuke_view=formatted_message)
        return await ctx.approve(f"Set **nuke message** to\n```{formatted_message}```")

