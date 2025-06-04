from discord.ext.commands import (
    Cog,
    command,
    group,
    has_permissions,
    Converter,
    CommandError,
)
from discord import (
    Client,
    TextChannel,
    Guild,
    StageChannel,
    ForumChannel,
    Member,
    VoiceChannel,
    Embed,
)
from lib.patch.context import Context
from lib.classes.builtins import human_join
from .events import Config, Entry
from typing import Optional, Union

MODULES = ("messages", "members", "channels", "roles", "invites", "emojis", "voice")


class EventConverter(Converter):
    async def convert(self, ctx: Context, argument: str):
        if argument.lower() not in MODULES:
            raise CommandError(
                f"**Option** must be one of {human_join(MODULES, markdown='`')}"
            )
        return argument.lower()


class Commands(Cog):
    def __init__(self, bot: Client):
        self.bot = bot

    async def get_config(self, guild: Guild) -> Optional[Config]:
        if not (
            data := await self.bot.db.fetchrow(
                """SELECT events, channel_ids, webhooks, ignored FROM logs WHERE guild_id = $1""",
                guild.id,
            )
        ):
            return None

        entries = []
        for i, event in enumerate(data.events, start=0):
            entries.append(
                Entry(
                    channel_id=data.channel_ids[i],
                    event=event,
                    webhook_url=data.webhooks[i],
                    ignored=data.ignored,
                )
            )
        config = Config(modules=entries)
        return config

    @group(
        name="log",
        aliases=["logs"],
        description="Set up logging for your community",
        invoke_without_command=True,
    )
    async def log(self, ctx: Context):
        return await ctx.send_help()

    @log.command(
        name="remove",
        description="Remove events from a logging channel",
        example=",log remove #logs messages",
    )
    @has_permissions(manage_guild=True)
    async def log_remove(
        self, ctx: Context, channel: TextChannel, event: EventConverter
    ):
        data = await self.get_config(channel.guild)
        if not data:
            raise CommandError("No logging has been **setup** here")
        if not (
            entry := next(
                (
                    entry
                    for entry in data.modules
                    if entry.event == event and entry.channel_id == channel.id
                ),
                None,
            )
        ):
            raise CommandError(
                f"Logging for `{event}` hasn't been **enabled** in {channel.mention}"
            )
        data.modules.remove(entry)
        data = data.to_data()
        await self.bot.db.execute(
            """UPDATE logs SET events = $1, channel_ids = $2, webhooks = $3, ignored = $4 WHERE guild_id = $5""",
            *data,
            ctx.guild.id,
        )
        await ctx.send(f"Removed logging for **{event}** from {channel.mention}")

    @log.group(
        name="ignore",
        description="Ignore a member or channel from being logged",
        invoke_without_command=True,
    )
    @has_permissions(manage_guild=True)
    async def log_ignore(
        self,
        ctx: Context,
        *,
        member_or_channel: Union[
            TextChannel, VoiceChannel, ForumChannel, StageChannel, Member
        ],
    ):
        data = await self.get_config(ctx.guild)
        if not data:
            raise CommandError("No logging has been **setup** here")
        if data.modules[0].ignored:
            if member_or_channel.id in data.modules[0].ignored:
                data.modules[0].ignored.remove(member_or_channel.id)
                message = f"Removed **{str(member_or_channel)}** from the ignore list"
            else:
                data.modules[0].ignored.append(member_or_channel.id)
                message = f"Added **{str(member_or_channel)}** to the ignore list"
        else:
            data.modules[0].ignored = [member_or_channel.id]
            message = f"Added **{str(member_or_channel)}** to the ignore list"
        data = data.to_data()
        data = data[-1]
        await self.bot.db.execute(
            """UPDATE logs SET ignored = $1 WHERE guild_id = $2""", data, ctx.guild.id
        )
        return await ctx.success(message)

    @log_ignore.command(
        name="list",
        aliases=["ls", "show", "view"],
        description="View all ignored members and channels",
    )
    @has_permissions(manage_guild=True)
    async def log_ignore_list(self, ctx: Context):
        data = await self.get_config(ctx.guild)
        if not data:
            raise CommandError("No logging has been **setup** here")
        if not data.modules[0].ignored:
            raise CommandError("No members or channels are ignored from logging")
        embed = Embed(title="Ignored Objects").set_author(
            name=str(ctx.author), icon_url=ctx.author.display_avatar.url
        )

        def get_row(obj: int):
            if member := ctx.guild.get_member(obj):
                return f"**{member.mention}**"
            elif channel := ctx.guild.get_channel(obj):
                return f"**{channel.mention}**"
            else:
                return f"**Unknown** (`{obj}`)"

        rows = [
            f"`{i}` {get_row(ignore)}"
            for i, ignore in enumerate(data.modules[0].ignored, start=1)
        ]
        if not rows:
            raise CommandError("No members or channels are ignored from logging")
        return await ctx.paginate(embed, rows)

    @log.command(
        name="add",
        description="Set up logging in a channel",
        example=",log add #logs messages",
    )
    @has_permissions(manage_guild=True)
    async def log_add(self, ctx: Context, channel: TextChannel, event: EventConverter):
        data = await self.get_config(ctx.guild)

        if not data:
            data = [
                [event],
                [channel.id],
                [
                    (
                        await channel.create_webhook(
                            name="rival logs",
                            avatar=await self.bot.user.display_avatar.read(),
                            reason="Logging setup",
                        )
                    ).url
                ],
                None,
            ]
        else:
            if not (
                entry := next(
                    (
                        entry
                        for entry in data.modules
                        if entry.event == event and entry.channel_id == channel.id
                    ),
                    None,
                )
            ):
                raise CommandError(
                    f"Logging for `{event}` has already been **enabled** in {channel.mention}"
                )
            else:
                entry = Entry(
                    channel_id=channel.id,
                    event=event,
                    webhook_url=(
                        await channel.create_webhook(
                            name="rival logs",
                            avatar=await self.bot.user.display_avatar.read(),
                            reason="Logging setup",
                        )
                    ).url,
                    ignored=data.modules[0].ignored,
                )
                data.modules.append(entry)
                data = data.to_data()
        await self.bot.db.execute(
            """UPDATE logs SET events = $1, channel_ids = $2, webhooks = $3, ignored = $4, WHERE guild_id = $5""",
            *data,
            ctx.guild.id,
        )
        return await ctx.success(
            f"Logging for `{event}` has been **{channel.mention}**"
        )
