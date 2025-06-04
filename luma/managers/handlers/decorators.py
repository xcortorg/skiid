from discord.ext import commands
from managers.helpers import Context


def has_guild_permissions(**perms: bool):
    async def predicate(ctx: Context):
        if ctx.author.guild_permissions.administrator:
            return True

        p = [x for x, y in perms.items() if y]

        if any((getattr(ctx.author.guild_permissions, g) for g in p)):
            return True

        roles = ", ".join((map(lambda g: str(g.id), ctx.author.roles[1:])))

        if not roles:
            raise commands.MissingPermissions(perms)

        results = await ctx.bot.db.fetch(
            f"SELECT permissions FROM fakeperms WHERE guild_id = $1 AND role_id IN ({roles})",
            ctx.guild.id,
        )

        flattend = list(
            set(ctx.bot.flatten(list(map(lambda r: r.permissions, results))))
        )
        if any((g in flattend for g in p)):
            return True

        raise commands.MissingPermissions(perms)

    return commands.check(predicate)


def server_owner():
    async def predicate(ctx: Context):
        owner = bool(ctx.guild.owner_id == ctx.author.id)
        if not owner:
            await ctx.warn("U dont own this server")
        return owner

    return commands.check(predicate)


def donor_perk():
    async def predicate(ctx: Context):
        if ctx.author.id in ctx.bot.owner_ids:
            return True

        if not await ctx.bot.db.fetchrow(
            "SELECT * FROM donor WHERE user_id = $1", ctx.author.id
        ):
            await ctx.error("U need [**donor**](https://discord.gg/luma)")
            return False
        return True

    return commands.check(predicate)


commands.server_owner = server_owner
commands.has_guild_permissions = has_guild_permissions
commands.donor_perk = donor_perk
