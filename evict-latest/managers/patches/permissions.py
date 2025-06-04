import discord
import json
from datetime import datetime

from discord.ext import commands
from discord.ext.commands import (
    MissingPermissions, 
    CommandError, 
    check, 
    BadArgument,
    Converter
)

from core.client.context import Context


class ValidPermission(Converter):
    async def convert(self, ctx: Context, argument: str):
        valid_permissions = [p[0] for p in ctx.author.guild_permissions]

        if not argument in valid_permissions:
            raise BadArgument(
                "This is **not** a valid permission. Please run `;fakepermissions permissions` to check all available permissions!"
            )

        return argument


def has_permissions(**permissions):
    """Check if the user has permissions to execute the command (fake permissions included)"""

    async def predicate(ctx: Context):

        if ctx.author.id in ctx.bot.owner_ids:
            return True

        if "guild_owner" in permissions:

            if ctx.author.id != ctx.guild.owner_id:
                raise CommandError(
                    f"You must be the **server owner** to use `{ctx.command.qualified_name}`"
                )

            return True

        author_permissions = [p[0] for p in ctx.author.guild_permissions if p[1]]
        if not any(p in author_permissions for p in permissions):

            roles = ", ".join(list(map(lambda r: str(r.id), ctx.author.roles)))
            results = await ctx.bot.db.fetch(
                f"SELECT permission FROM fake_permissions WHERE guild_id = $1 AND role_id IN ({roles})",
                ctx.guild.id,
            )

            for result in results:
                fake_perms = json.loads(result[0])

                if "administrator" in fake_perms:
                    return True

                if any(p in fake_perms for p in permissions):
                    return True

            raise MissingPermissions([p for p in permissions])
        return True

    return commands.check(predicate)


def require_dm():
    """Check if the bot can DM the user."""

    async def predicate(ctx: Context):
        try:
            await ctx.author.send()
        except discord.HTTPException as error:
            if error.code == 50007:
                raise CommandError(
                    "You need to enable **DMs** to use this command"
                )

        return True

    return check(predicate)


def donator(booster: bool = False):
    """Check if the user is a donator or has voted in the last 6 hours"""

    async def predicate(ctx: Context):
        guild = ctx.bot.get_guild(892675627373699072)
        role = guild.get_role(1318054098666389534)
        user = guild.get_member(ctx.author.id)

        if booster:
            if role in user.roles:
                return True

            if not user or not user.premium_since:
                raise CommandError(
                    f"You must **boost** the Evict [**Discord Server**](https://discord.gg/evict) to use `{ctx.command.qualified_name}`"
                )

            return True

        donator_check = await ctx.bot.db.fetchrow(
            "SELECT * FROM donators WHERE user_id = $1", ctx.author.id
        )
        
        if donator_check:
            return True

        last_vote = await ctx.bot.db.fetchval(
            """
            SELECT last_vote_time 
            FROM user_votes 
            WHERE user_id = $1
            """, 
            ctx.author.id
        )

        if last_vote and (datetime.now() - last_vote).total_seconds() <= 21600:
            return True

        raise CommandError(
            f"You must be a **donator** to use `{ctx.command.qualified_name}`, run `;donate` - [**Discord Server**](https://discord.gg/evict)\n"
            "Alternatively, you can vote for Evict on [Top.gg](https://top.gg/bot/1203514684326805524) (lasts 6 hours)"
        )

    return check(predicate)


def require_boost():
    """Check if the user has boosted the server"""

    async def predicate(ctx: Context):
        if not ctx.author.premium_since:
            raise CommandError(
                f"You must **boost** the server to use `{ctx.command.qualified_name}`"
            )

        return True

    return check(predicate)


commands.has_permissions = has_permissions
