from discord.ext.commands import Cog, Context, command, has_permissions, CommandError
from discord import Client, Embed, Message, utils
from lib.classes.database import Record
import arrow
import orjson
import json
from typing import Optional
from datetime import datetime
from lib.managers.logs import Logs


class Commands(Cog):
    def __init__(self: "Commands", bot: Client):
        self.bot = bot
        self.bot.logs = Logs(self.bot)

    @command(
        name="snipe",
        aliases=["s"],
        example=",snipe 4",
        description="Retrive a recently deleted message",
    )
    async def snipe(self: "Commands", ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="snipe", index=index
            )
        ):
            return await ctx.fail(
                f"There are **no deleted messages** for {ctx.channel.mention}"
            )
        total = snipe[1]
        snipe = snipe[0]
        if content := snipe.get("content"):
            if (
                "discord.gg/" in content.lower()
                or "discord.com/" in content.lower()
                or "discordapp.com/" in content.lower()
            ):
                return await ctx.fail("snipe had **filtered content**")
            content = "".join(c for c in content if c.isalnum() or c.isspace())
            if (
                "discord.gg" in content.lower()
                or "discord.com/" in content.lower()
                or "discordapp.com" in content.lower()
            ):
                return await ctx.fail("snipe had **filtered content**")
        embed = Embed(
            color=self.bot.color,
            description=(
                snipe.get("content")
                or (
                    snipe["embeds"][0].get("description") if snipe.get("embeds") else ""
                )
            ),
            timestamp=datetime.fromtimestamp(snipe.get("timestamp")),
        )

        embed.set_author(
            name=snipe.get("author").get("name"),
            icon_url=snipe.get("author").get("avatar"),
        )

        if att := snipe.get("attachments"):
            embed.set_image(url=att[0])

        elif sticks := snipe.get("stickers"):
            embed.set_image(url=sticks[0])

        embed.set_footer(
            text=f"Deleted {arrow.get(snipe.get('timestamp')).humanize()} | {index}/{total}"
        )

        return await ctx.send(embed=embed)

    @command(
        name="editsnipe",
        aliases=["es"],
        example=",editsnipe 2",
        description="Retrieve a messages original text before edited",
    )
    async def editsnipe(self: "Commands", ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="editsnipe", index=index
            )
        ):
            return await ctx.fail("There is nothing to snipe.")
        total = snipe[1]
        snipe = snipe[0]
        if content := snipe.get("content"):
            if (
                "discord.gg/" in content.lower()
                or "discord.com/" in content.lower()
                or "discordapp.com/" in content.lower()
            ):
                return await ctx.fail("snipe had **filtered content**")
            content = "".join(c for c in content if c.isalnum() or c.isspace())
            if (
                "discord.gg" in content.lower()
                or "discord.com/" in content.lower()
                or "discordapp.com/" in content.lower()
            ):
                return await ctx.fail("snipe had **filtered content**")
        embed = Embed(
            color=self.bot.color,
            description=(
                snipe.get("content")
                or ("Message contains an embed" if snipe.get("embeds") else "")
            ),
            timestamp=datetime.fromtimestamp(snipe.get("timestamp")),
        )

        embed.set_author(
            name=snipe.get("author").get("name"),
            icon_url=snipe.get("author").get("avatar"),
        )

        if att := snipe.get("attachments"):
            embed.set_image(url=att[0])

        elif sticks := snipe.get("stickers"):
            embed.set_image(url=sticks[0])

        embed.set_footer(
            text=f"Edited {arrow.get(snipe.get('timestamp')).humanize()} | {index}/{total}",
            icon_url=ctx.author.display_avatar,
        )

        return await ctx.send(embed=embed)

    @command(
        name="reactionsnipe",
        aliases=["reactsnipe", "rs"],
        description="Retrieve a deleted reaction from a message",
        example=",reactionsipe 2",
    )
    async def reactionsnipe(self: "Commands", ctx: Context, index: int = 1):
        if not (
            snipe := await self.bot.snipes.get_entry(
                ctx.channel, type="reactionsnipe", index=index
            )
        ):
            return await ctx.fail("There is nothing to snipe.")
        snipe[1]  # type: ignore
        snipe = snipe[0]
        embed = Embed(
            color=self.bot.color,
            description=(
                f"""**{str(snipe.get('author').get('name'))}** reacted with {snipe.get('reaction')
                if not snipe.get('reaction').startswith('https://cdn.discordapp.com/')
                else str(snipe.get('reaction'))} <t:{int(snipe.get('timestamp'))}:R>"""
            ),
        )

        return await ctx.send(embed=embed)

    @command(
        name="clearsnipe",
        aliases=["cs"],
        description="Clear all deleted messages from coffin",
        example=",clearsnipe",
    )
    @has_permissions(manage_messages=True)
    async def clearsnipes(self: "Commands", ctx: Context):
        await self.bot.snipes.clear_entries(ctx.channel)
        return await ctx.success(f"**Cleared** snipes for {ctx.channel.mention}")

    @command(
        name="reactionhistory",
        description="See logged reactions for a message",
        usage=",reactionhistory (message link)",
        example=",reactionhistory discordapp.com/channels/...",
    )
    async def reactionhistory(
        self: "Commands", ctx: Context, message: Optional[Message] = None
    ):
        if not message:
            if not (message := await self.bot.get_reference(ctx.message)):
                raise CommandError("You must **reply** or provide a **message id**")
        data = await self.bot.db.fetch(
            """SELECT * FROM reaction_history WHERE message_id = $1""", message.id
        )
        if not data:
            return await ctx.fail(
                f"No **reactions logged** for the [message]({message.jump_url}) provided"
            )

        async def get_row(number: int, record: Record) -> str:
            user = self.bot.get_user(record.user_id)
            if not user:
                user = await self.bot.fetch_user(record.user_id)
            return f"`{number}` **{str(user)}** added {str(record.reaction)} {utils.format_dt(record.ts, style='R')}"

        rows = [await get_row(i, record) for i, record in enumerate(data, start=1)]
        return await ctx.paginate(
            Embed(
                title="Reaction history", url=message.jump_url, color=self.bot.color
            ).set_author(
                name=str(ctx.author.display_name),
                icon_url=ctx.author.display_avatar.url,
            ),
            rows,
            10,
            "reaction",
        )

    @command(
        name="removesnipe",
        aliases=["rms"],
        description="Remove a snipe from the snipe index",
        example=",removesnipe 1",
    )
    @has_permissions(manage_messages=True)
    async def removesnipe(self: "Commands", ctx: Context, index: int = 1):
        try:
            await self.bot.snipes.delete_entry(ctx.channel, "snipe", index)
            return await ctx.success(f"Deleted **snipe** at index `{index}`")
        except Exception:
            raise CommandError(f"No **snipe** found at index `{index}`")
