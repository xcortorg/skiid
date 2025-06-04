from core.client.context import Context
from discord.ext.commands import CommandError, Converter


class Bank(Converter):
    async def convert(self: "Bank", ctx: Context, argument: str):
        if not argument.isdigit() and argument.lower() != "all":
            raise CommandError("This is not a number")

        bank = await ctx.bot.db.fetchval(
            "SELECT bank FROM economy WHERE user_id = $1", ctx.author.id
        )
        points = bank if argument.lower() == "all" else int(argument)

        if points == 0:
            raise CommandError("The value cannot be 0")

        if points > bank:
            raise CommandError(
                f"You do not have `{int(argument):,}` credits in your bank"
            )

        return points


class Value(Converter):
    async def convert(self: "Value", ctx: Context, argument: str):
        if not argument.isdigit() and argument.lower() != "all":
            raise CommandError("This is not a number")

        credits = await ctx.bot.db.fetchval(
            "SELECT credits FROM economy WHERE user_id = $1", ctx.author.id
        )
        points = credits if argument.lower() == "all" else int(argument)

        if points == 0:
            raise CommandError("The value cannot be 0")

        if points > credits:
            raise CommandError(f"You do not have `{int(argument):,}` credits")

        return points
