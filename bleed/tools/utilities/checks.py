import json

import config
import discord
from discord.ext import commands
from discord.ext.commands import CommandError, MissingPermissions


def has_permissions(**permissions):
    """
    Check if the user has permissions to execute the command (fake permissions included)
    """

    async def predicate(ctx: commands.Context):

        if ctx.author.id in [
            ,
            ,
            ,
        ]:
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

    async def predicate(ctx: commands.Context):
        try:
            await ctx.author.send()
        except discord.HTTPException as error:
            if error.code == 50007:
                raise commands.CommandError(
                    "You need to enable **DMs** to use this command"
                )

        return True

    return commands.check(predicate)


def donator(booster: bool = False):
    """Check if the user is a donator"""

    async def predicate(ctx: commands.Context):
        guild = ctx.bot.get_guild()
        role = guild.get_role()
        user = guild.get_member(ctx.author.id)

        if booster:
            if role in user.roles:
                return True

            if not user or not user.premium_since:
                raise commands.CommandError(
                    f"You must **boost** the {config.Bleed.servername} [**Discord Server**]({config.Bleed.support}) to use `{ctx.command.qualified_name}`"
                )

            return True

        donator_check = await ctx.bot.db.fetchrow(
            "SELECT * FROM donators WHERE user_id = $1", ctx.author.id
        )

        if not donator_check:
            raise commands.CommandError(
                f"You must be a **donator** to use `{ctx.command.qualified_name}` - [**Discord Server**]({config.Bleed.support})"
            )

        return True

    return commands.check(predicate)


def require_boost():
    """Check if the user has boosted the server"""

    async def predicate(ctx: commands.Context):
        if ctx.author.id in [
            ,
            ,
            ,
        ]:
            return True

        if not ctx.author.premium_since:
            raise commands.CommandError(
                f"You must **boost** the server to use `{ctx.command.qualified_name}`"
            )

        return True

    return commands.check(predicate)

commands.has_permissions = has_permissions