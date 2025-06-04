from core.client.context import Context
from discord.ext.commands import check
from discord.ext import commands


class ValidReskinName(commands.Converter):
    async def convert(self, ctx: Context, argument: str):
        texts = list(
            map(
                lambda t: t.strip(),
                open("/root/evict/tools/handlers/text.txt", "r").read().splitlines(),
            )
        )

        for arg in argument.split(" "):
            if arg.lower() in texts:
                raise commands.BadArgument("This name cannot be used for reskin!")

        return argument


def create_reskin():
    async def predicate(ctx: Context):

        check = await ctx.bot.db.fetchrow(
            """
            SELECT * FROM reskin
            WHERE user_id = $1
            """, 
            ctx.author.id
        )

        if not check:
            await ctx.bot.db.execute(
                """
                INSERT INTO reskin
                VALUES ($1,$2,$3)
                """,
                ctx.author.id,
                ctx.bot.user.name,
                ctx.bot.user.display_avatar.url,
            )

        return True

    return check(predicate)
