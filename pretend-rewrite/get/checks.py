import asyncio
import json
from typing import Any, Optional

import discord
from cogs.auth import owners
from discord.ext import commands


async def check_owner(ctx):
    check = await ctx.bot.db.fetchrow(
        "SELECT * FROM vcs WHERE voice = $1 AND user_id = $2",
        ctx.author.voice.channel.id,
        ctx.author.id,
    )
    if check is None:
        await ctx.send_warning("You are not the owner of this voice channel")
        return True


class Cache:
    def __init__(self):
        self.cache_inventory = {}

    def __repr__(self) -> str:
        return str(self.cache_inventory)

    async def do_expiration(self, key: str, expiration: int) -> None:
        await asyncio.sleep(expiration)
        self.cache_inventory.pop(key)

    def get(self, key: str) -> Any:
        """Get the object that is associated with the given key"""
        return self.cache_inventory.get(key)

    async def set(self, key: str, object: Any, expiration: Optional[int] = None) -> Any:
        """Set any object associatng with the given key"""
        self.cache_inventory[key] = object
        if expiration:
            asyncio.ensure_future(self.do_expiration(key, expiration))
        return object

    def remove(self, key: str) -> None:
        """An alias for delete method"""
        return self.delete(key)

    def delete(self, key: str) -> None:
        """Delete a key from the cache"""
        if self.get(key):
            del self.cache_inventory[key]
            return None


class ValidWebhookCode(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        check = await ctx.bot.db.fetchrow(
            "SELECT * FROM webhook WHERE guild_id = $1 AND code = $2",
            ctx.guild.id,
            argument,
        )
        if not check:
            raise commands.BadArgument("There is no webhook associated with this code")

        return argument


class Boosts:

    def get_level(boosts: int):
        async def predicate(ctx: commands.Context):
            if ctx.guild.premium_subscription_count < boosts:
                await ctx.send_warning(
                    f"This server needs to have more than **{boosts}** boosts in order to use this command"
                )
            return ctx.guild.premium_subscription_count >= boosts

        return commands.check(predicate)


class Joint:

    def check_joint():
        async def predicate(ctx: commands.Context):
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM joint WHERE guild_id = $1", ctx.guild.id
            )
            if not check:
                await ctx.bot.ext.send_error(
                    ctx,
                    f"This server **doesn't** have a **joint**. Use `{ctx.clean_prefix}joint toggle` to get one",
                )
            return check is not None

        return commands.check(predicate)

    def joint_owner():
        async def predicate(ctx: commands.Context):
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM joint WHERE guild_id = $1", ctx.guild.id
            )
            if check["holder"] != ctx.author.id:
                await ctx.send_warning(
                    f"You don't have the **joint**. Steal it from <@{check['holder']}>"
                )
            return check["holder"] == ctx.author.id

        return commands.check(predicate)


class Mod:

    def is_mod_configured():
        async def predicate(ctx: commands.Context):
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM mod WHERE guild_id = $1", ctx.guild.id
            )
            if not check:
                await ctx.send_warning(
                    f"Moderation isn't **enabled** in this server. Enable it using `{ctx.clean_prefix}setmod` command"
                )
                return False
            return True

        return commands.check(predicate)

    async def check_role_position(ctx: commands.Context, role: discord.Role) -> bool:
        if (
            role.position >= ctx.author.top_role.position
            and ctx.author.id != ctx.guild.owner_id
        ) or not role.is_assignable():
            await ctx.send_warning("I cannot manage this role for you")
            return False
        return True

    async def check_hieracy(ctx: commands.Context, member: discord.Member) -> bool:
        if member.id == ctx.bot.user.id:
            if ctx.command.name != "nickname":
                await ctx.reply("leave me alone!!")
                return False
        if (
            (
                ctx.author.top_role.position <= member.top_role.position
                and ctx.guild.owner_id != ctx.author.id
            )
            or ctx.guild.me.top_role <= member.top_role
            or (member.id == ctx.guild.owner_id and ctx.author.id != member.id)
        ):
            await ctx.send_warning("You can't do this action on **{}**".format(member))
            return False
        return True


class Messages:

    def good_message(message: discord.Message) -> bool:
        if not message.guild or message.author.bot or message.content == "":
            return False
        return True


class Owners:
    def check_owners():
        async def predicate(ctx: commands.Context):
            return ctx.author.id in owners

        return commands.check(predicate)


class Perms:

    def server_owner():
        async def predicate(ctx: commands.Context):
            if ctx.author.id != ctx.guild.owner_id:
                await ctx.send_warning(
                    f"This command can be used only by **{ctx.guild.owner}**"
                )
                return False
            return True

        return commands.check(predicate)

    def check_whitelist(module: str):
        async def predicate(ctx: commands.Context):
            if ctx.guild is None:
                return False
            if ctx.author.id == ctx.guild.owner.id:
                return True
            check = await ctx.bot.db.fetchrow(
                "SELECT * FROM whitelist WHERE guild_id = $1 AND object_id = $2 AND mode = $3 AND module = $4",
                ctx.guild.id,
                ctx.author.id,
                "user",
                module,
            )
            if check is None:
                await ctx.send_warning(f"You are not **whitelisted** for **{module}**")
                return False
            return True

        return commands.check(predicate)

    def get_perms(perm: str = None):
        async def predicate(ctx: commands.Context):
            if perm is None:
                return True
            if ctx.guild.owner == ctx.author:
                return True
            if ctx.author.guild_permissions.administrator:
                return True
            for r in ctx.author.roles:
                if perm in [str(p[0]) for p in r.permissions if p[1] is True]:
                    return True
                check = await ctx.bot.db.fetchrow(
                    "SELECT permissions FROM fake_permissions WHERE role_id = $1 and guild_id = $2",
                    r.id,
                    r.guild.id,
                )
                if check is None:
                    continue
                permissions = json.loads(check[0])
                if perm in permissions or "administrator" in permissions:
                    return True
            raise commands.MissingPermissions([perm])

        return commands.check(predicate)

    async def has_perms(ctx: commands.Context, perm: str = None):
        if perm is None:
            return True
        if ctx.guild.owner == ctx.author:
            return True
        if ctx.author.guild_permissions.administrator:
            return True
        for r in ctx.author.roles:
            if perm in [str(p[0]) for p in r.permissions if p[1] is True]:
                return True
            check = await ctx.bot.db.fetchrow(
                "SELECT permissions FROM fake_permissions WHERE role_id = $1 and guild_id = $2",
                r.id,
                r.guild.id,
            )
            if check is None:
                continue
            permissions = json.loads(check[0])
            if perm in permissions or "administrator" in permissions:
                return True
        return False
