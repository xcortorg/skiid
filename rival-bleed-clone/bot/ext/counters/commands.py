from discord.ext.commands import (
    Cog,
    Context,
    Converter,
    GuildChannelConverter,
    group,
    CommandError,
    has_permissions,
)
from discord import (
    Client,
    ChannelType,
    Embed,
)
from enum import Enum, auto
from typing import Optional

CHANNEL_OPTIONS = {
    ChannelType.stage_voice: ["stage", "s", "st"],
    ChannelType.voice: ["voice", "v", "vc"],
    ChannelType.text: ["text", "t", "txt"],
    ChannelType.category: ["category", "c", "cat"],
    ChannelType.news: ["news", "n"],
    ChannelType.forum: ["forum", "f", "frm"],
    ChannelType.media: ["media", "img", "imgs", "m", "md", "i"],
}

COUNTER_OPTIONS = {
    "members": ["members", "member", "mems", "m"],
    "boosters": ["boosters", "boosted", "bstrs"],
    "boosts": ["boosts", "bsts", "bst"],
}


class RemovalActionType(Enum):
    delete = auto()
    remove = auto()


class ChannelTypeConverter(Converter):
    async def convert(self: "ChannelType", ctx: Context, argument: str):
        """Converts a string to a ChannelType instance"""
        for key, values in CHANNEL_OPTIONS.items():
            for value in values:
                if argument.lower() == value.lower():
                    return key
        raise CommandError(f"{argument} was not a proper channel type")


class CounterOption(Converter):
    async def convert(self: "CounterOption", ctx: Context, argument: str):
        for key, values in COUNTER_OPTIONS.items():
            for value in values:
                if argument.lower() == value.lower():
                    return key
        raise CommandError(f"{argument} was not a proper counter type")


class RemovalAction(Converter):
    async def convert(
        self: "RemovalAction", ctx: Context, argument: str
    ) -> RemovalActionType:
        """Converts a string to a RemovalAction instance"""
        delete = ["del", "d", "delete"]
        rem = ["remove", "r", "rem"]
        if argument.lower() in delete:
            return RemovalActionType.delete
        elif argument.lower() in rem:
            return RemovalActionType.remove
        raise CommandError(f"{argument} was not a proper removal action")


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    @group(
        name="counter",
        description="Create a category or channel that will keep track of the member or booster count",
        invoke_without_command=True,
    )
    @has_permissions(manage_channels=True)
    async def counter(self: "Commands", ctx: Context):
        if ctx.invoked_subcommand is None:
            return await ctx.send_help(ctx.command.qualified_name)

    @counter.command(
        name="add",
        description="Create channel counter",
        example=",counter add members category",
    )
    @has_permissions(manage_channels=True)
    async def counter_add(
        self: "Commands",
        ctx: Context,
        option: CounterOption,
        *,
        channel_type: ChannelTypeConverter,
    ):
        existing = await self.bot.db.fetchrow(
            """SELECT * FROM counters WHERE guild_id = $1 AND counter_type = $2""",
            ctx.guild.id,
            option,
        )
        if existing:
            if not ctx.guild.get_channel(existing.channel_id):
                await self.bot.db.execute(
                    """DELETE FROM counters WHERE guild_id = $1 AND counter_type = $2""",
                    ctx.guild.id,
                    option,
                )
            else:
                return await ctx.fail(f"You already have a **{option}** counter")
        if option == "members":
            num = len(ctx.guild.members)
        elif option == "boosters":
            num = len(ctx.guild.premium_subscribers)
        else:
            num = ctx.guild.premium_subscription_count
        try:
            channel = await ctx.guild._create_channel(
                name=f"{num} {option}", channel_type=channel_type
            )
        except Exception:
            raise CommandError(
                f"Your guild **doesn't have access** to `{channel_type}` type of channels"
            )
        await self.bot.db.execute(
            """INSERT INTO counters (guild_id, channel_id, counter_type) VALUES($1, $2, $3)""",
            ctx.guild.id,
            int(channel["id"]),
            option,
        )
        return await ctx.success(
            f"<#{channel['id']}> will now keep track of the **{option}** count"
        )

    @counter.command(
        name="remove",
        description="Remove a channel or category counter",
        example=",counter remove #Members delete",
    )
    @has_permissions(manage_channels=True)
    async def counter_remove(
        self: "Commands",
        ctx: Context,
        channel: GuildChannelConverter,
        action: Optional[RemovalAction] = RemovalActionType.remove,
    ):
        if not await self.bot.db.fetchrow(
            """SELECT * FROM counters WHERE guild_id = $1 AND channel_id = $2""",
            ctx.guild.id,
            channel.id,
        ):
            return await ctx.fail(f"there is no counter in {channel.mention}")
        if action == RemovalActionType.delete:
            await channel.delete(reason=f"counter deleted by {str(ctx.author)}")
            msg = f"successfully **DELETED** {channel.mention}"
        else:
            msg = f"successfully **REMOVED** the counter for {channel.mention}"
        await self.bot.db.execute(
            """DELETE FROM counters WHERE guild_id = $1 AND channel_id = $2""",
            ctx.guild.id,
            channel.id,
        )
        return await ctx.success(msg)

    @counter.command(
        name="list",
        description="List every category or channel keeping track of members or boosters in this server",
    )
    @has_permissions(manage_channels=True)
    async def counter_list(self: "Commands", ctx: Context):
        counters = await self.bot.db.fetch(
            """SELECT * FROM counters WHERE guild_id = $1""", ctx.guild.id
        )
        if not counters:
            raise CommandError(
                "No category or channel are keeping track of members or boosts"
            )
        embed = Embed(title="Counters", description="Counters")
        rows = []
        for i, counter in enumerate(counters, start=1):
            rows.append(f"`{i}` <#{counter.channel_id}> - **{counter.counter_type}**")
        return await ctx.paginate(embed, rows, 10, "counter")
