from typing import List, Union  # type: ignore

import discord
import orjson
from discord.ext.commands import Context
from orjson import dumps, loads
from tools.important.subclasses.builder import EmbedBuilder  # type: ignore


class Paginate:
    def __init__(self, bot):
        self.bot = bot

    async def create(self, ctx: Context, name: str, embeds: Union[List[str], str]):
        if check := self.bot.get_command(name):  # type: ignore  # noqa: F841
            return await ctx.fail(f"{name} is already a bot command")
        if isinstance(embeds, list):
            pass
        else:
            if not embeds.startswith("["):
                e = []
                for _ in embeds.split("{embed}"):
                    if _ is None or _ == "":  # await ctx.send(_)
                        continue
                    else:
                        e.append("{embed}" + f"{_}")
                embeds = e
            try:
                embeds = loads(dumps(embeds))
            except Exception:
                return await ctx.fail("please properly format the embeds")
        await self.bot.db.execute(
            """INSERT INTO paginator (guild_id, name, embeds) VALUES($1,$2,$3) ON CONFLICT(guild_id, name) DO UPDATE SET embeds = excluded.embeds""",
            ctx.guild.id,
            name,
            orjson.dumps(embeds),
        )
        return await ctx.success(
            f"**Created your paginator**, execute it using `{ctx.prefix}{name}`"
        )

    async def check(self, ctx: Context):
        name = ctx.message.content.replace(ctx.prefix, "").lstrip()
        if check := await self.bot.db.fetchval(
            "SELECT embeds FROM paginator WHERE guild_id = $1 AND name = $2",
            ctx.guild.id,
            name,
        ):
            embeds = orjson.loads(orjson.dumps(orjson.loads(check)))
            new_embeds = []
            for e in embeds:
                builder = EmbedBuilder(user=ctx.author)
                embed = await builder.build_embed(await builder.replace_placeholders(e))
                new_embeds.append(embed["embed"])
            #            await ctx.send(new_embeds)
            return await ctx.alternative_paginate(new_embeds)

    async def delete(self, ctx: Context, name: str):
        await self.bot.db.execute(
            """DELETE FROM paginator WHERE guild_id = $1 AND name = $2""",
            ctx.guild.id,
            name,
        )
        return await ctx.success(f"deleted the paginator **{name}**")

    async def list(self, ctx: Context):
        rows = [
            f"**{name.name}**"
            for name in await self.bot.db.fetch(
                "SELECT name FROM paginator WHERE guild_id = $1", ctx.guild.id
            )
        ]
        if len(rows) == 0:
            return await ctx.fail("no **paginators** found")
        return await self.bot.dummy_paginator(
            ctx, discord.Embed(title="Paginators", color=self.bot.color), rows
        )
