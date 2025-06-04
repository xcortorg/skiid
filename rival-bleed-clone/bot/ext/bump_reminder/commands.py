from discord.ext.commands import (
    Cog,
    Boolean,
    group,
    CommandError,
    EmbedConverter,
    has_permissions,
)
from discord import Client, Embed, TextChannel
from lib.patch.context import Context
from lib.classes.builtins import boolean_to_emoji
from datetime import datetime, timedelta
from typing import Optional
import humanize


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    def get_next_bump_time(
        self, last_bump: Optional[datetime] = None, formatted: Optional[bool] = True
    ):
        if not last_bump:
            if formatted:
                return "Now"
            else:
                return None
        time = last_bump + timedelta(hours=2)
        if not formatted:
            return time
        else:
            return humanize.naturaldelta(time)

    @group(
        name="bumpreminder",
        description="Get reminders to /bump your server on Disboard!",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder(self, ctx: Context):
        return await ctx.send_help(ctx.command)

    @bumpreminder.command(
        name="autoclean",
        description="Automatically delete messages that aren't /bump",
        example=",bumpreminder autoclean yes",
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_autoclean(self, ctx: Context, choice: Boolean):
        await self.bot.db.execute(
            """INSERT INTO bump_reminder (guild_id, auto_clean) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET auto_clean = excluded.auto_clean""",
            ctx.guild.id,
            choice,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if choice else 'DISABLED'}** auto cleaning of messages"
        )

    @bumpreminder.command(
        name="channel",
        description="Set Bump Reminder channel for the server",
        example=",bumpreminder channel #text",
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_channel(self, ctx: Context, *, channel: TextChannel):
        await self.bot.db.execute(
            """INSERT INTO bump_reminder (guild_id, channel_id) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET channel_id = excluded.channel_id""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(
            f"**Set** the bumpreminder **channel** to {channel.mention}"
        )

    @bumpreminder.command(
        name="config",
        aliases=["settings", "cfg"],
        description="View server configuration for Bump Reminder",
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_config(self, ctx: Context):
        if not (
            config := await self.bot.db.fetchrow(
                """SELECT * FROM bump_reminder WHERE guild_id = $1""", ctx.guild.id
            )
        ):
            raise CommandError("BumpReminder has not been **setup**")
        config_value = ""
        if channel_id := config.channel_id:
            if channel := ctx.guild.get_channel(channel_id):
                config_value += f"**Channel:** {channel.mention}\n"
            else:
                config_value += "**Channel:** N/A\n"
        else:
            config_value += "**Channel:** N/A\n"
        if reminder_message := config.message:
            config_value += f"**Reminder Message:** {reminder_message}\n"
        else:
            config_value += "**Reminder Message:** Default\n"
        if ty_message := config.thankyou_message:
            config_value += f"**Thank You Message:** {ty_message}\n"
        else:
            config_value += "**Thank You Message:** Default\n"
        next_bump = self.get_next_bump_time(config.last_bump) or "Now"
        config_value += f"**Next Bump:** {next_bump}\n"
        config_value += f"**Auto Clean:** {boolean_to_emoji(self.bot, config.auto_clean)}\n**Auto Lock:** {boolean_to_emoji(self.bot, config.auto_lock)}"
        embed = Embed(title="BumpReminder configuration").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )
        embed.add_field(name="Options", value=config_value, inline=False)
        return await ctx.send(embed=embed)

    @bumpreminder.command(
        name="autolock",
        description="Lock channel until ready to use /bump",
        example=",bumpreminder autolock yes",
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_autolock(self, ctx: Context, choice: Boolean):
        await self.bot.db.execute(
            """INSERT INTO bump_reminder (guild_id, auto_lock) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET auto_lock = excluded.auto_lock""",
            ctx.guild.id,
            choice,
        )
        return await ctx.success(
            f"successfully **{'ENABLED' if choice else 'DISABLED'}** auto lock"
        )

    @bumpreminder.group(
        name="thankyou",
        description="Set the 'Thank You' message for successfully running /bump",
        example=",bumpreminder thankyou {embed}{description: ...}",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_thankyou(self, ctx: Context, *, message: EmbedConverter):
        await self.bot.db.execute(
            """INSERT INTO bump_reminder (guild_id, thankyou_message) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET thankyou_message = excluded.thankyou_message""",
            ctx.guild.id,
            message,
        )
        return await ctx.success(f"**Set** the 'Thank You' message to `{message}`")

    @bumpreminder_thankyou.command(
        name="view", description="View the current Thank You message"
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_thankyou_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchrow(
                """SELECT thankyou_message FROM bump_reminder WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No Thank You message has been set")
        return await self.bot.send_embed(ctx, message, user=ctx.author)

    @bumpreminder.group(
        name="message",
        description="Set the reminder message to run /bump",
        example=",bumpreminder message {embed}{description: ...}",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_message(self, ctx: Context, *, message: EmbedConverter):
        await self.bot.db.execute(
            """INSERT INTO bump_reminder (guild_id, message) VALUES($1, $2) ON CONFLICT(guild_id) DO UPDATE SET message = excluded.message""",
            ctx.guild.id,
            message,
        )
        return await ctx.success(f"**Set** the 'Bump Reminder' message to `{message}`")

    @bumpreminder_message.command(
        name="view", description="View the current remind message"
    )
    @has_permissions(manage_channels=True)
    async def bumpreminder_message_view(self, ctx: Context):
        if not (
            message := await self.bot.db.fetchrow(
                """SELECT message FROM bump_reminder WHERE guild_id = $1""",
                ctx.guild.id,
            )
        ):
            raise CommandError("No Bump Reminder message has been set")
        return await self.bot.send_embed(ctx, message, user=ctx.author)
