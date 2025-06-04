import re
import json
import emoji
import langcodes
import validators

from discord.ext import commands

from modules import config
from modules.helpers import EvelinaContext
from .handlers.lastfm import Handler
from .exceptions import LastFmException, WrongMessageLink

class ValidNickname(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if argument.lower() == "none":
            return None
        else:
            return argument
        
class ValidTime(commands.Converter):
    async def convert(self, ctx, argument: str):
        time_pattern = re.compile(r'(?:(\d+)y)?(?:(\d+)w)?(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?')
        match = time_pattern.fullmatch(argument)
        if not match:
            raise commands.BadArgument(f"**{argument}** is an invalid timespan")
        years, weeks, days, hours, minutes, seconds = match.groups()
        years = int(years) if years else 0
        weeks = int(weeks) if weeks else 0
        days = int(days) if days else 0
        hours = int(hours) if hours else 0
        minutes = int(minutes) if minutes else 0
        seconds = int(seconds) if seconds else 0
        total_seconds = (
            years * 365 * 24 * 60 * 60 +
            weeks * 7 * 24 * 60 * 60 +
            days * 24 * 60 * 60 + 
            hours * 60 * 60 +
            minutes * 60 +
            seconds
        )
        return total_seconds
    
class ValidLanguage(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        try:
            language = langcodes.get(argument.lower())
            if not language.is_valid():
                raise commands.BadArgument(f"This is **not** a valid language code: `{argument}`\nPlease check the list of valid language codes [**here**](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)")
            return language.language_name()
        except langcodes.LanguageTagError:
            raise commands.BadArgument(f"This is **not** a valid language code: `{argument}`\nPlease check the list of valid language codes [**here**](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)")

class ValidWebhookCode(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        check = await ctx.bot.db.fetchrow("SELECT * FROM webhook WHERE guild_id = $1 AND code = $2", ctx.guild.id, argument)
        if not check:
            raise commands.BadArgument("There is no webhook associated with this code")
        return argument

class ValidEmoji(commands.EmojiConverter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        try:
            emoj = await super().convert(ctx, argument)
        except commands.BadArgument:
            if not emoji.is_emoji(argument):
                raise commands.BadArgument("This is not an emoji")
            emoj = argument
        return emoj

class ValidPermission(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        valid_permissions = [p[0] for p in ctx.author.guild_permissions]

        if not argument in valid_permissions:
            raise commands.BadArgument("This is **not** a valid permission. Please run `;fakepermissions perms` to check all available permissions")
        return argument

class ValidCommand(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if not argument:
            return None
        command = ctx.bot.get_command(argument)
        if not command:
            raise commands.CommandNotFound(f"The command **{argument}** doesn't exist")
        if command.qualified_name in ["disablecmd", "enablecmd"] or command.cog_name.lower() in ["jishaku", "owner"]:
            raise commands.BadArgument("You can't disable that command")
        return command.qualified_name

class ValidCog(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if not argument:
            return None
        cog = ctx.bot.get_cog(argument.capitalize())
        if not cog:
            raise commands.BadArgument(f"The module **{argument}** doesn't exist")
        if str(cog.qualified_name).lower() in ["jishaku", "owner", "auth", "info", "config"]:
            raise commands.CommandRegistrationError("no lol")
        return cog.qualified_name.lower()

class ValidAutoreact(commands.EmojiConverter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        try:
            emoj = await super().convert(ctx, argument)
        except commands.BadArgument:
            if not emoji.is_emoji(argument):
                return None
            emoj = argument
        return emoj

class ValidLastFmName(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        bot = ctx.bot
        self.lastfmhandler = Handler(bot, config.API.LASTFM)
        check = await ctx.bot.db.fetchrow("SELECT username FROM lastfm WHERE user_id = $1", ctx.author.id)
        existing_user = await ctx.bot.db.fetchrow("SELECT user_id FROM lastfm WHERE username = $1", argument)
        if not await self.lastfmhandler.lastfm_user_exists(argument):
            raise LastFmException("This account **doesn't** exist")
        if existing_user and existing_user['user_id'] != ctx.author.id:
            raise LastFmException("This username is **already** registered to another user")
        if check:
            if check[0] == argument:
                raise LastFmException(f"You are **already** registered with this name")
            await ctx.bot.db.execute("UPDATE lastfm SET username = $1 WHERE user_id = $2", argument, ctx.author.id)
        else:
            await ctx.bot.db.execute("INSERT INTO lastfm VALUES ($1,$2,$3,$4,$5)", ctx.author.id, argument, json.dumps(["🔥", "🗑️"]), None, None)
        return await self.lastfmhandler.get_user_info(argument)

class ValidMessage(commands.MessageConverter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        try:
            message = await super().convert(ctx, argument)
        except:
            raise commands.BadArgument("This is **not** a message id or a message link")
        if message.guild.id != ctx.guild.id:
            raise WrongMessageLink()
        return message
    
class ValidCompanyName(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        forbidden_words = ["nigga", "nigger", "niga", "niger", "negga", "negger"]
        if len(argument) < 5:
            raise commands.BadArgument("Company name can't be shorter than 5 characters")
        if len(argument) > 25:
            raise commands.BadArgument("Company name can't be longer than 25 characters")
        if not all(char.isalnum() or char.isspace() for char in argument):
            raise commands.BadArgument("Company name can only contain letters, numbers, and spaces")
        if any(word in argument.lower() for word in forbidden_words):
            raise commands.BadArgument("Company name contains forbidden words")
        company = await ctx.bot.db.fetchrow("SELECT * FROM company WHERE LOWER(name) = LOWER($1)", argument)
        if company:
            raise commands.BadArgument("Company with this name already exists.")
        return argument
    
class ValidCompanyTag(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if len(argument) < 3:
            raise commands.BadArgument("Company tag can't be shorter than 3 characters")
        if len(argument) > 4:
            raise commands.BadArgument("Company tag can't be longer than 4 characters")
        if not argument.isalnum():
            raise commands.BadArgument("Company tag can only contain letters and numbers")
        tag_company = await ctx.bot.db.fetchrow("SELECT * FROM company WHERE tag = $1", argument)
        if tag_company:
            raise commands.BadArgument("Company with this tag already exists.")
        return argument
    
class ValidCompanyDescription(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if len(argument) < 10:
            raise commands.BadArgument("Company description can't be shorter than 10 characters")
        if len(argument) > 250:
            raise commands.BadArgument("Company description can't be longer than 250 characters")
        return argument
    
class ValidImageURL(commands.Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if argument.lower() in ["none", "remove", "reset"]:
            return None
        else:
            v = validators.url(argument)
            if v:
                return argument
            else:
                raise commands.BadArgument("This is **not** a valid Image URL")