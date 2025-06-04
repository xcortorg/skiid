from ..patch.context import Context
from discord.ext.commands import check, CommandError
from .converters import match_event
from functools import wraps
from loguru import logger
import discord
from .builtins import catch

def trusted():
    async def predicate(ctx: Context):
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        admins = set(
            await ctx.bot.db.fetchval(
                """
                SELECT admins FROM antinuke
                WHERE guild_id = $1
                """,
                ctx.guild.id,
            )
            or []
        )
        admins.add(ctx.guild.owner_id)

        if ctx.author.id not in admins:
            raise CommandError("you aren't the guild owner or an antinuke admin")
        return True
    return check(predicate)

def event_checks(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        with catch():
            class_name = args[0].__class__.__name__
            module_name = class_name.split("_Events", 1)[0].lower()
            bot = args[0].bot
            guild = None
            channel = None
            for argument in args:
                if isinstance(argument, discord.Member):
                    guild = argument.guild
                elif isinstance(argument, (discord.Message, Context)):
                    guild = argument.guild
                    channel = argument.channel
                elif isinstance(argument, discord.RawReactionActionEvent):
                    guild = bot.get_guild(argument.guild_id)
                    channel = guild.get_channel(argument.channel_id)
            event_name = func.__cog_listener_names__[0]
            if guild and channel:
                if event_type := match_event(event_name):
                    if disabled_event := await bot.db.fetchrow("""SELECT * FROM disabled_events WHERE guild_id = $1 AND event = $2""", guild.id, event_type):
                        if channel.id in disabled_event.channel_ids:
                            return logger.info(f"{event_name} has been disabled in {channel.name}")
                if disabled_module := await bot.db.fetchrow("""SELECT * FROM disabled_modules WHERE guild_id = $1 AND module = $2""", guild.id, module_name):
                    if channel.id in disabled_module.channel_ids:
                        return logger.info(f"{module_name} disabled in {channel.name}")
        return await func(*args, **kwargs)
    return wrapper

def is_booster():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.premium_since:
            return True
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        else:
            raise CommandError("you have not boosted the server")
    return check(predicate)

def guild_owner():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.id == ctx.guild.owner_id or ctx.author.id in ctx.bot.owner_ids:
            return True
        raise CommandError("you aren't the guild owner")
    return check(predicate)

def is_staff():
    async def predicate(ctx: Context) -> bool:
        if ctx.author.id in ctx.bot.owner_ids:
            return True
        return False
    return check(predicate)
