from discord.ext.commands import (
    Cog,
    command,
    group,
    DiscordEmoji,
    CommandError,
    has_permissions,
    MissingRequiredArgument,
)
from discord import Client, Embed, File, Member, User, TextChannel, Message, Guild
from typing import Optional
from lib.patch.context import Context


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot

    @group(
        name="reaction",
        aliases=["react", "autoreact", "autoreaction"],
        description="Add a reaction(s) to a message",
        invoke_without_command=True,
        example=",reaction .../channels/... :skull:",
    )
    @has_permissions(manage_messages=True)
    async def reaction(
        self,
        ctx: Context,
        message: Optional[Message] = None,
        *,
        emoji: DiscordEmoji = None,
    ):
        if not ctx.invoked_subcommand:
            if ctx.invoked_with:
                return await ctx.send_help(ctx.command)
            else:
                if not message:
                    raise MissingRequiredArgument(
                        (ctx.command.clean_params())["message"]
                    )
                if not emoji:
                    raise MissingRequiredArgument((ctx.command.clean_params())["emoji"])
                try:
                    await message.add_reaction(emoji)
                    return await ctx.message.add_reaction("👍")
                except Exception:
                    return await ctx.message.add_reaction("👎")

    @reaction.command(
        name="clear", description="Removes every reaction trigger in guild"
    )
    @has_permissions(manage_expressions=True)
    async def reaction_clear(self, ctx: Context):
        await self.bot.db.execute(
            """DELETE FROM auto_reactions WHERE guild_id = $1""", ctx.guild.id
        )
        return await ctx.success("**Cleared** auto reactions")

    @reaction.command(
        name="add",
        description="Adds a reaction trigger to guild",
        example=",reaction add :skull: sup",
        parameters={"not_strict": {"no_value": True}},
    )
    @has_permissions(manage_expressions=True)
    async def reaction_add(self, ctx: Context, emoji: DiscordEmoji, trigger: str):
        strict = True if not ctx.parameters.get("not_strict") else False
        await ctx.message.add_reaction(str(emoji))
        await self.bot.db.execute(
            """
            INSERT INTO auto_reactions (guild_id, trigger, response, owner_id, strict)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (guild_id, trigger, response)
            DO UPDATE SET response = EXCLUDED.response;""",
            ctx.guild.id,
            trigger,
            [str(emoji)],
            ctx.author.id,
            strict,
        )
        return await ctx.success(f"Created **reaction trigger** `{trigger}`")

    @reaction.command(
        name="delete",
        description="Removes a reaction trigger in guild",
        aliases=["del", "d", "remove", "r"],
        example=",reaction remove :skull: Hi",
    )
    @has_permissions(manage_expressions=True)
    async def reaction_delete(self, ctx: Context, emoji: DiscordEmoji, trigger: str):
        await self.bot.db.execute(
            """DELETE FROM auto_reactions WHERE guild_id = $1 AND trigger = $2 AND response = $3""",
            ctx.guild.id,
            trigger,
            [str(emoji)],
        )
        return await ctx.sucess(f"Deleted **reaction trigger* `{trigger}`")

    @reaction.group(
        "messages",
        description="Add or remove auto reaction on messages",
        example=",reaction messages #text :skull: :fire: :100:",
        invoke_without_command=True,
    )
    @has_permissions(manage_expressions=True)
    async def reaction_messages(
        self,
        ctx: Context,
        channel: TextChannel,
        first: DiscordEmoji,
        second: Optional[DiscordEmoji] = None,
        third: Optional[DiscordEmoji] = None,
    ):
        if not channel.slowmode_delay >= 60:
            raise CommandError(
                "Set a **slowmode delay** of atleast `1 minute` then try again"
            )
        strict = True if not ctx.parameters.get("not_strict") else False
        responses = [str(first)]
        if second:
            responses.append(str(second))
        if third:
            responses.append(str(third))
        for i, r in enumerate(responses, start=1):
            try:
                await ctx.message.add_reaction(r)
            except Exception:
                raise CommandError(f"Invalid emoji detected in emoji `{i}`")
        await self.bot.db.execute(
            """
            INSERT INTO auto_reactions (guild_id, trigger, response, owner_id, strict)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (guild_id, trigger, response)
            DO UPDATE SET response = EXCLUDED.response;""",
            ctx.guild.id,
            str(channel.id),
            responses,
            ctx.author.id,
            strict,
        )
        return await ctx.success(
            f"Set {''.join(r for r in responses)} as **auto reactions** for {channel.mention}"
        )

    @reaction_messages.command(
        name="list",
        aliases=["show", "view", "ls"],
        description="List auto reactions for all channels",
    )
    @has_permissions(manage_expressions=True)
    async def reaction_messages_list(self, ctx: Context):
        reactions = await self.bot.db.fetchrow(
            """SELECT trigger, response FROM auto_reactions WHERE guild_id = $1""",
            ctx.guild.id,
        )
        rows = []
        for record in reactions:
            if record.trigger.isnumeric():
                if channel := ctx.guild.get_channel(int(record.trigger)):
                    rows.append(
                        f"{channel.mention} - {''.join(r for r in record.response)}"
                    )
        if len(rows) == 0:
            raise CommandError("No Auto Channel Reactions found")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        embed = Embed(color=self.bot.color, title="Auto Channel Reactions")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        return await ctx.paginate(embed, rows)

    @reaction.command(
        name="deleteall",
        description="Removes every reaction trigger for a specific word",
        example=",reaction deleteall hi",
    )
    @has_permissions(manage_expressions=True)
    async def reaction_deleteall(self, ctx: Context, trigger_word: str):
        await self.bot.db.execute(
            """DELETE FROM auto_reactions WHERE trigger = $1 AND guild_id = $2""",
            trigger_word,
            ctx.guild.id,
        )
        return await ctx.success(
            f"deleted **all auto reactions** triggered by `{trigger_word}`"
        )

    @reaction.command(
        name="list",
        aliases=["show", "view", "ls"],
        description="View a list of every reaction trigger in guild",
    )
    @has_permissions(manage_expressions=True)
    async def reaction_list(self, ctx: Context):
        reactions = await self.bot.db.fetch(
            """SELECT trigger, response FROM auto_reactions WHERE guild_id = $1""",
            ctx.guild.id,
        )
        rows = []
        for record in reactions:
            if record.trigger.isnumeric():
                if channel := ctx.guild.get_channel(int(record.trigger)):
                    continue
            rows.append(f"{record.trigger} - {''.join(r for r in record.response)}")
        rows = [f"`{i}` {row}" for i, row in enumerate(rows, start=1)]
        embed = Embed(color=self.bot.color, title="Reaction Triggers")
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        return await ctx.paginate(embed, rows)

    @reaction.command(
        name="owner",
        description="Gets the author of a trigger word",
        example=",reaction owner hi",
    )
    @has_permissions(manage_expressions=True)
    async def reaction_owner(self, ctx: Context, trigger_word: str):
        if not (
            owner_id := await self.bot.db.fetchval(
                """SELECT owner_id FROM auto_reactions WHERE trigger = $1 AND guild_id = $2""",
                trigger_word.lower(),
                ctx.guild.id,
            )
        ):
            raise CommandError(f"No **reaction trigger** found under `{trigger_word}`")
        if not (user := self.bot.get_user(owner_id)):
            user = await self.bot.fetch_user(owner_id)
        return await ctx.normal(
            f"**Reaction Trigger **{trigger_word}** author is `{str(user)}`", emoji="ℹ️"
        )
