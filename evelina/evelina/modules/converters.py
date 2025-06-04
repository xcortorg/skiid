from decimal import ROUND_DOWN, Decimal, InvalidOperation
import re
import json
import math
from urllib.parse import urlparse
import emoji
import string
import matplotlib

from discord.ext.commands import Converter, BadArgument, MemberConverter, RoleConverter, BotMissingPermissions

from pydantic import BaseModel
from modules.helpers import EvelinaContext

class ColorSchema(BaseModel):
  hex: str 
  value: int

class AnyEmoji(Converter):
  async def convert(self, ctx: EvelinaContext, argument: str):
    if emoji.is_emoji(argument):
      return argument 
    emojis = re.findall(r'<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>', argument)
    if len(emojis) == 0:
      raise BadArgument(f"**{argument}** is **not** an emoji")
    emoj = emojis[0]
    format = ".gif" if emoj[0] == "a" else ".png"
    return await ctx.bot.session.get_bytes(f"https://cdn.discordapp.com/emojis/{emoj[2]}{format}")
  
class EligibleVolume(Converter):
 async def convert(self, ctx: EvelinaContext, argument: str): 
  try: 
    volume = int(argument)
  except ValueError:
    raise BadArgument(f"**{argument}** is **not** a number")
  if volume < 0 or volume > 500: 
    raise BadArgument("Volume has to be between **0** and **500**")
  return volume  

class HexColor(Converter): 
    async def convert(self, ctx: EvelinaContext, argument: str) -> ColorSchema: 
        if argument.lower() in ['pfp', 'avatar']:
            dominant = await ctx.bot.misc.dominant_color(ctx.author.avatar)
            if dominant > 16777215:
                raise BadArgument(f"Dominant color {dominant} exceeds maximum allowed value.")
            payload = {"hex": f"#{hex(dominant).replace('0x', '')}", "value": dominant}
        else:
            color = matplotlib.colors.cnames.get(argument.lower())
            if not color: 
                color = argument.replace("#", "")
                digits = set(string.hexdigits)
                if not all(c in digits for c in color) or len(color) != 6:
                    raise BadArgument(f"**{argument}** is not a valid hex code")
            color = color.replace("#", "")
            color_value = int(color, 16)
            if color_value > 16777215:
                raise BadArgument(f"Color value {color_value} exceeds maximum allowed value.")
            payload = {'hex': f"#{color}", 'value': color_value}
        return ColorSchema(**payload)

class AbleToMarry(MemberConverter):
 async def convert(self, ctx: EvelinaContext, argument: str): 
    try:
      member = await super().convert(ctx, argument) 
    except BadArgument: 
      raise BadArgument(f"Member **{argument}** couldn't be found")
    if member == ctx.author: 
      raise BadArgument("You can't marry yourself")
    if member.bot: 
      raise BadArgument("You can't marry a bot")
    if await ctx.bot.db.fetchrow("SELECT * FROM marry WHERE $1 IN (author, soulmate)", member.id):
      raise BadArgument(f"**{member}** is already married")
    if await ctx.bot.db.fetchrow("SELECT * FROM marry WHERE $1 IN (author, soulmate)", ctx.author.id): 
      raise BadArgument("You are already **married**. Are you trying to cheat?? 🤨") 
    return member
     
class NoStaff(MemberConverter): 
  async def convert(self, ctx: EvelinaContext, argument: str):
    try: 
      member = await super().convert(ctx, argument)
    except BadArgument:
      raise BadArgument(f"Member **{argument}** couldn't be found") 
    if ctx.guild.me.top_role.position <= member.top_role.position: 
      raise BadArgument(f"Bot can't manage **{argument}**, he has a higher role than me")
    if ctx.command.qualified_name in ['ban', 'kick', 'softban', 'strip', 'jail', 'mute']:
      if ctx.author.id == member.id: 
       if ctx.author.id == ctx.guild.owner_id: 
        raise BadArgument("You can't execute this command on yourself")
    else: 
     if ctx.author.id == member.id: 
      return member 
    if ctx.author.id == ctx.guild.owner_id:
      return member 
    if member.id == ctx.guild.owner_id: 
      raise BadArgument("You can't punish the server owner")
    if ctx.author.top_role.position <= member.top_role.position: 
      raise BadArgument(f"You can't manage **{member.mention}**") 
    return member

class LevelMember(MemberConverter): 
  async def convert(self, ctx: EvelinaContext, argument: str):
    try: 
      member = await super().convert(ctx, argument)
    except BadArgument:
      raise BadArgument(f"Member **{argument}** couldn't be found") 
    if ctx.author.id == member.id: 
      return member 
    if member.id == ctx.guild.owner_id: 
      raise BadArgument("You can't change the level of the server owner")
    if ctx.author.id == ctx.guild.owner_id:
      return member
    if ctx.author.top_role.position <= member.top_role.position: 
      raise BadArgument(f"You can't manage **{member.mention}**, he has a higher role than you") 
    return member

class CounterMessage(Converter):
  async def convert(self, ctx: EvelinaContext, argument: str):
   if not "{target}" in argument: 
    raise BadArgument("Variable `{target}` is **missing** from the channel name\n> Add `{target}` to the channel name")
   return argument

class ChannelType(Converter):
  async def convert(self, ctx: EvelinaContext, argument: str):
   if not argument in ['voice', 'stage', 'text', 'category']:
    raise BadArgument(f"**{argument}** is not a **valid** channel type\n> Valid channel types: `voice`, `stage`, `text` & `category`")
   return argument

class CounterType(Converter):
  async def convert(self, ctx: EvelinaContext, argument: str):
    if not argument in ["members", "voice", "boosters", "humans", "bots", "role", "boosts"]:
      raise BadArgument(f"**{argument}** is not an **available** counter.\n> Available counters: `members`, `voice`, `boosters`, `humans`, `bots`, `role` & `boosts`") 
    return argument
  
class NewRoleConverter(RoleConverter): 
  async def convert(self, ctx: EvelinaContext, argument: str): 
   try: 
    role = await super().convert(ctx, argument)
   except BadArgument: 
    role = ctx.find_role(argument)
    if not role: 
     raise BadArgument(f"Role **{argument}** couldn't be found") 
   if not ctx.guild.me.guild_permissions.manage_roles: 
    raise BotMissingPermissions("Bot are **missing** the following permission: `manage_roles`")
   if role.position >= ctx.guild.me.top_role.position: 
    raise BadArgument(f"Role **{argument}** is over my highest role") 
   if not role.is_assignable():
    raise BadArgument(f"Role **{argument}** can't be managed by anyone")
   if ctx.author.id == ctx.guild.owner_id:
    return role
   if role.position >= ctx.author.top_role.position:
    raise BadArgument("You can't manage this role")
   return role
  
class DangerousRoleConverter(RoleConverter): 
  async def convert(self, ctx: EvelinaContext, argument: str): 
   try: 
    role = await super().convert(ctx, argument)
   except BadArgument: 
    role = ctx.find_role(argument)
    if not role: 
     raise BadArgument(f"Role **{argument}** couldn't be found") 
   if not ctx.guild.me.guild_permissions.manage_roles: 
    raise BotMissingPermissions("Bot are **missing** the following permission: `manage_roles`")
   if role.position >= ctx.guild.me.top_role.position: 
    raise BadArgument(f"Role **{argument}** is over my highest role") 
   if not role.is_assignable():
    raise BadArgument(f"Role **{argument}** can't be managed by anyone")
   if ctx.author.id == ctx.guild.owner_id:
    return role
   if role.position >= ctx.author.top_role.position:
    raise BadArgument("You can't manage this role")
   if ctx.is_dangerous(role):
        check = await ctx.bot.db.fetchrow("SELECT owner_id, admins FROM antinuke WHERE guild_id = $1", ctx.guild.id)
        if check:
            allowed = [check["owner_id"]]
            if check["admins"]:
                allowed.extend([id for id in json.loads(check["admins"])])
            if not ctx.author.id in allowed:
                raise BadArgument("You **can't** use this command, you need to be an Antinuke admin")
            return role
        else:
            raise BadArgument(f"Antinuke is **not** configured\n> Use `{ctx.clean_prefix}antinuke setup` to configure it")
   return role

class EligibleEconomyMember(MemberConverter):
  async def convert(self, ctx: EvelinaContext, argument: str):
   try: 
    member = await super().convert(ctx, argument)
   except BadArgument: 
    raise BadArgument(f"Member **{argument}** couldn't be found") 
   if member.id == ctx.author.id: 
    raise BadArgument("You can't transfer money to yourself")
   check = await ctx.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", member.id)
   if not check: 
    raise BadArgument(f"Member **{argument}** does not have an economy account created")
   return member
  
class Amount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a number")
        multipliers = {
            'k': Decimal(1_000),
            'm': Decimal(1_000_000),
            'b': Decimal(1_000_000_000)
        }
        try:
            if argument[-1].lower() in multipliers:
                multiplier = multipliers[argument[-1].lower()]
                amount = (Decimal(argument[:-1]) * multiplier).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            else:
                amount = Decimal(argument).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            if len(str(amount).split('.')[-1]) > 2:
                raise BadArgument("The number **cannot** have more than **2** decimals")
        except InvalidOperation:
            raise BadArgument("This is **not** a number.")
        if amount < 0:
            raise BadArgument("You cannot use less than **0** 💳")
        if amount == 0:
            raise BadArgument(f"You cannot use **0** 💳")
        return float(amount)

class CardAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        card_balance = await ctx.bot.db.fetchval(
            "SELECT card FROM economy WHERE user_id = $1", ctx.author.id
        )
        if card_balance is None:
            raise BadArgument("You do **not** have an economy account created.")
        if card_balance == 0:
            raise BadArgument("You do **not** have any cash in your **bank**.")
        if card_balance < 0:
            raise BadArgument("Your balance is negative. __You are in debt.__ :neutral_face:")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument("This is **not** a number.")
        card_balance_decimal = Decimal(card_balance)
        multipliers = {
            'k': Decimal(1_000),
            'm': Decimal(1_000_000),
            'b': Decimal(1_000_000_000)
        }
        if argument.lower() == "all":
            amount = card_balance_decimal
        elif argument.lower() == "half":
            amount = (card_balance_decimal / Decimal(2)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        elif argument.endswith('%'):
            try:
                percentage = Decimal(argument[:-1]) / Decimal(100)
                amount = (card_balance_decimal * percentage).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            except InvalidOperation:
                raise BadArgument("This is **not** a valid percentage.")
        else:
            try:
                if argument[-1].lower() in multipliers:
                    multiplier = multipliers[argument[-1].lower()]
                    amount = (Decimal(argument[:-1]) * multiplier).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                else:
                    amount = Decimal(argument).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                if len(str(amount).split('.')[-1]) > 2:
                    raise BadArgument("The number **cannot** have more than **2** decimals")
            except InvalidOperation:
                raise BadArgument("This is **not** a number.")
        if amount < 0:
            raise BadArgument("You cannot use less than **0** 💳")
        if amount == 0:
            raise BadArgument(f"You cannot use **0** 💳")
        if card_balance_decimal < amount:
            raise BadArgument("You do **not** have enough cash in your **bank**.")
        return float(amount)

class CashAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        cash = await ctx.bot.db.fetchval(
            "SELECT cash FROM economy WHERE user_id = $1", ctx.author.id
        )
        if cash is None:
            raise BadArgument("You do **not** have an economy account created.")
        if cash == 0:
            raise BadArgument("You do **not** have any cash in your **pockets**.")
        if cash < 0:
            raise BadArgument("Your balance is negative. __You are in debt.__ :neutral_face:")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument("This is **not** a number.")
        cash_decimal = Decimal(cash)
        multipliers = {
            'k': Decimal(1_000),
            'm': Decimal(1_000_000),
            'b': Decimal(1_000_000_000)
        }
        if argument.lower() == "all":
            amount = cash_decimal
        elif argument.lower() == "half":
            amount = (cash_decimal / Decimal(2)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        elif argument.endswith('%'):
            try:
                percentage = Decimal(argument[:-1]) / Decimal(100)
                amount = (cash_decimal * percentage).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            except InvalidOperation:
                raise BadArgument("This is **not** a valid percentage.")
        else:
            try:
                if argument[-1].lower() in multipliers:
                    multiplier = multipliers[argument[-1].lower()]
                    amount = (Decimal(argument[:-1]) * multiplier).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                else:
                    amount = Decimal(argument).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                
                if len(str(amount).split('.')[-1]) > 2:
                    raise BadArgument("The number **cannot** have more than **2** decimals")
            except InvalidOperation:
                raise BadArgument("This is **not** a number.")
        if amount < 0:
            raise BadArgument(f"You cannot use less than **0** 💵")
        if amount == 0:
            raise BadArgument(f"You cannot use **0** 💵")
        if cash_decimal < amount:
            raise BadArgument("You do **not** have enough cash in your **pockets**.")
        return float(amount)

class TransferAmount(Converter):
    async def convert(self, ctx, argument: str):
        check = await ctx.bot.db.fetchrow("SELECT card FROM economy WHERE user_id = $1", ctx.author.id)
        if check is None:
            raise BadArgument("You don't have an economy account created.")
        card_balance = Decimal(check["card"])
        if card_balance <= 0:
            raise BadArgument("You don't have enough money on your **card** to use.")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a number")
        multipliers = {
            'k': Decimal(1_000),
            'm': Decimal(1_000_000),
            'b': Decimal(1_000_000_000)
        }
        if argument.lower() == "all":
            amount = card_balance
        elif argument.lower() == "half":
            amount = (card_balance / Decimal(2)).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
        elif argument.endswith('%'):
            try:
                percentage = Decimal(argument[:-1]) / Decimal(100)
                if percentage < Decimal(0.01) or percentage > Decimal(1):
                    raise BadArgument("Percentage must be between 1% and 100%")
                amount = (card_balance * percentage).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            except:
                raise BadArgument(f"**{argument}** is **not** a valid percentage")
        else:
            try:
                if argument[-1].lower() in multipliers:
                    multiplier = multipliers[argument[-1].lower()]
                    amount = (Decimal(argument[:-1]) * multiplier).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                else:
                    amount = Decimal(argument).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                if len(str(amount).split('.')[-1]) > 2:
                    raise BadArgument("The number **cannot** have more than **2** decimals")
            except:
                raise BadArgument(f"**{argument}** is **not** a number")
        if amount <= 0:
            raise BadArgument("You can't transfer **0** or a negative amount 💳")
        if amount > card_balance:
            raise BadArgument("You don't have enough money on your **card** to use")
        return float(amount)

class DepositAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        check = await ctx.bot.db.fetchrow("SELECT cash, card, item_bank FROM economy WHERE user_id = $1", ctx.author.id)
        if check is None:
            raise BadArgument("You do **not** have an economy account created.")
        cash = Decimal(check["cash"])
        current_card = Decimal(check["card"])
        bank_limit = Decimal(check["item_bank"])
        available_space = bank_limit - current_card
        if available_space <= 0:
            raise BadArgument("Your bank balance is already full!")
        if cash == 0:
            raise BadArgument("You don't have any money in your **pocket** to use.")
        if cash < 0:
            raise BadArgument("Your balance is negative dude :skull:")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a number")
        multipliers = {
            'k': Decimal(1_000),
            'm': Decimal(1_000_000),
            'b': Decimal(1_000_000_000)
        }
        if argument.lower() == "all":
            amount = min(cash, available_space)
        elif argument.lower() == "half":
            amount = min((cash / Decimal(2)).quantize(Decimal('0.00'), rounding=ROUND_DOWN), available_space)
        elif argument.endswith('%'):
            try:
                percentage = Decimal(argument[:-1]) / Decimal(100)
                if percentage < Decimal(0.01) or percentage > Decimal(1):
                    raise BadArgument("Percentage must be between 1% and 100%")
                amount = (cash * percentage).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            except:
                raise BadArgument(f"**{argument}** is **not** a valid percentage")
        else:
            try:
                if argument[-1].lower() in multipliers:
                    multiplier = multipliers[argument[-1].lower()]
                    amount = (Decimal(argument[:-1]) * multiplier).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                else:
                    amount = Decimal(argument).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                if len(str(amount).split('.')[-1]) > 2:
                    raise BadArgument("The number **cannot** have more than **2** decimals")
            except:
                raise BadArgument(f"**{argument}** is **not** a number")
        if amount < 0:
            raise BadArgument("You can't use less than **0** 💵")
        if amount == 0:
            raise BadArgument("You can't use **0** 💵")
        if amount > available_space:
            amount = available_space
        if cash < amount:
            raise BadArgument("You don't have enough money in your **pocket** to use")
        return float(amount)

class BetConverter(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        argument = argument.lower()
        valid_bets = {"odd", "even", "red", "black", "green", "low", "middle", "high"}
        if argument in valid_bets:
            return argument
        if argument.isdigit():
            number = int(argument)
            if 1 <= number <= 36:
                return number
        raise BadArgument(
            f"**{argument}** is not a valid bet.\n"
            f"> **Allowed are:** `odd`, `even`, `red`, `black`, `green`, `low`, `middle`, `high` or `1` to `36`."
        )

class BankAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        bank = await ctx.bot.db.fetchval("SELECT item_bank FROM economy WHERE user_id = $1", ctx.author.id)
        if bank is None:
            raise BadArgument("You don't have an economy account created.")
        if bank == 0:
            raise BadArgument("You don't have any bank items to use.")
        if bank < 0:
            raise BadArgument("Your balance is negative dude :skull:")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a number")
        if argument.lower() == "all":
            amount = math.floor(bank * 100) / 100
        elif argument.lower() == "half":
            amount = math.floor(bank / 2 * 100) / 100
        else:
            try:
                amount = float(argument)
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a number")
        if argument[::-1].find(".") > 2:
            raise BadArgument("The number can't have more than **2** decimals")
        if amount < 0:
            raise BadArgument(f"You can't use less than **0** 💵")
        if amount == 0:
            raise BadArgument(f"You can't use **0** 💵")
        if bank < amount:
            raise BadArgument("You don't have enough money in your **pocket** to use")
        return amount
    
class VaultDepositAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        check = await ctx.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        company = await ctx.bot.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", ctx.author.id)
        if not company:
            raise BadArgument("You are not part of a company.")
        limit = await ctx.bot.db.fetchrow("SELECT * FROM company_upgrades WHERE level = $1", company["level"]) 
        cash = Decimal(check["cash"])
        vault_limit = Decimal(limit["vault"])
        vault_current = Decimal(company["vault"])
        available_space = vault_limit - vault_current
        if available_space <= 0:
            raise BadArgument("Company vault is already full!")
        if cash == 0:
            raise BadArgument("You don't have any money in your **pocket** to use.")
        if cash < 0:
            raise BadArgument("Your balance is negative dude :skull:")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a number")
        multipliers = {'k': Decimal(1_000), 'm': Decimal(1_000_000), 'b': Decimal(1_000_000_000)}
        if argument.lower() == "all":
            amount = min(cash, available_space)
        elif argument.lower() == "half":
            amount = min((cash / Decimal(2)).quantize(Decimal('0.00'), rounding=ROUND_DOWN), available_space)
        elif argument.endswith('%'):
            try:
                percentage = Decimal(argument[:-1]) / Decimal(100)
                if percentage < Decimal(0.01) or percentage > Decimal(1):
                    raise BadArgument("Percentage must be between 1% and 100%")
                amount = (cash * percentage).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
            except InvalidOperation:
                raise BadArgument(f"**{argument}** is **not** a valid percentage")
        else:
            try:
                if argument[-1].lower() in multipliers:
                    multiplier = multipliers[argument[-1].lower()]
                    amount = (Decimal(argument[:-1]) * multiplier).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                else:
                    amount = Decimal(argument).quantize(Decimal('0.00'), rounding=ROUND_DOWN)
                if len(str(amount).split('.')[-1]) > 2:
                    raise BadArgument("The number **cannot** have more than **2** decimals")
            except InvalidOperation:
                raise BadArgument(f"**{argument}** is **not** a number")
        if amount < 0:
            raise BadArgument(f"You can't use less than **0** 💵")
        if amount == 0:
            raise BadArgument(f"You can't use **0** 💵")
        if amount > available_space:
            amount = available_space
        if cash < amount:
            raise BadArgument("You don't have enough money in your **pocket** to use")
        return float(amount)
       
class VaultWithdrawAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        company = await ctx.bot.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", ctx.author.id)
        if not company:
            raise BadArgument("You are not part of a company.")
        if company["vault"] == 0:
            raise BadArgument("Your company vault is empty.")
        if company["vault"] < 0:
            raise BadArgument("Your company vault is negative dude :skull:")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a valid number")

        multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}

        if argument.lower() == "all":
            amount = math.floor(company["vault"] * 100) / 100
        elif argument.lower() == "half":
            amount = math.floor((company["vault"] / 2) * 100) / 100
        elif argument.endswith('%'):
            try:
                percentage = float(argument[:-1])
                if percentage < 1 or percentage > 100:
                    raise BadArgument("Percentage must be between 1% and 100%")
                amount = math.floor((company["vault"] * (percentage / 100)) * 100) / 100
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a valid percentage")
        elif any(argument.lower().endswith(mult) for mult in multipliers):
            try:
                for mult in multipliers:
                    if argument.lower().endswith(mult):
                        argument = argument.lower().replace(mult, '')
                        amount = float(argument) * multipliers[mult]
                        break
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a valid number")
        else:
            try:
                amount = float(argument)
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a valid number")

        if isinstance(amount, float) and str(amount)[::-1].find(".") > 2:
            raise BadArgument("The number can't have more than **2** decimals")
        if amount < 0:
            raise BadArgument("You can't withdraw less than **0** 💳")
        if amount == 0:
            raise BadArgument("You can't withdraw **0** 💳")
        if company["vault"] < amount:
            raise BadArgument("Your company vault doesn't have enough money to withdraw")
        return amount

class ProjectContributeAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        check = await ctx.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", ctx.author.id)
        company = await ctx.bot.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", ctx.author.id)
        if not company:
            raise BadArgument("You are not part of a company.")
        company_project = await ctx.bot.db.fetchrow("SELECT * FROM company_projects_started WHERE company_id = $1 AND active = $2", company["id"], True)
        if not company_project:
            raise BadArgument("Your company doesn't have an active project.")
        project = await ctx.bot.db.fetchrow("SELECT * FROM company_projects WHERE name = $1", company_project["project_name"])
        if not project:
            raise BadArgument("The project doesn't exist.")
        cash = check["cash"]
        participants = json.loads(company_project['participant'])
        spent = participants.get(str(ctx.author.id), 0)
        total_spent = company_project['money']
        cost = float(project['cost'])
        limit = cost / 2
        available_space = cost - total_spent
        available_user_space = limit - spent
        if available_space <= 0:
            raise BadArgument("Your company project is already fully funded!")
        if available_user_space <= 0:
            raise BadArgument("You have reached your maximum contribution limit!")
        if cash == 0:
            raise BadArgument("You don't have any money in your **pocket** to use.")
        if cash < 0:
            raise BadArgument("Your balance is negative dude :skull:")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a valid number")
        multipliers = {'k': 1000, 'm': 1000000, 'b': 1000000000}
        if argument.lower() == "all":
            amount = min(math.floor(cash * 100) / 100, available_user_space)
        elif argument.lower() == "half":
            amount = min(math.floor(cash / 2 * 100) / 100, available_user_space)
        elif argument.endswith('%'):
            try:
                percentage = float(argument[:-1])
                if percentage < 1 or percentage > 100:
                    raise BadArgument("Percentage must be between 1% and 100%")
                amount = math.floor((cash * (percentage / 100)) * 100) / 100
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a valid percentage")
        elif any(argument.lower().endswith(mult) for mult in multipliers):
            try:
                for mult in multipliers:
                    if argument.lower().endswith(mult):
                        argument = argument.lower().replace(mult, '')
                        amount = float(argument) * multipliers[mult]
                        break
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a valid number")
        else:
            try:
                amount = float(argument)
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a valid number")
        if isinstance(amount, float) and str(amount)[::-1].find(".") > 2:
            raise BadArgument("The number can't have more than **2** decimals")
        if amount > available_user_space:
            amount = available_user_space
        if amount > available_space:
            amount = available_space
        if cash < amount:
            raise BadArgument("You don't have enough money in your **pocket** to contribute")
        if amount <= 0:
            raise BadArgument(f"You can't contribute less than **0** 💵")
        if amount == 0:
            raise BadArgument(f"You can't contribute **0** 💵")
        return amount
    
class ProjectCollectAmount(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        company = await ctx.bot.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", ctx.author.id)
        if not company:
            raise BadArgument("You are not part of a company.")
        earnings = await ctx.bot.db.fetchrow("SELECT * FROM company_earnings WHERE company_id = $1 AND user_id = $2", company['id'], ctx.author.id)
        if not earnings:
            raise BadArgument("You have no earnings to collect.")
        if argument.lower() in ["nan", "inf"]:
            raise BadArgument(f"**{argument}** is **not** a number")
        if argument.lower() == "all":
            amount = earnings['amount']
        elif argument.lower() == "half":
            amount = earnings['amount'] / 2
        elif argument.endswith('%'):
            try:
                percentage = float(argument[:-1])
                if percentage < 1 or percentage > 100:
                    raise BadArgument("Percentage must be between 1% and 100%")
                amount = earnings['amount'] * (percentage / 100)
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a valid percentage")
        elif 'k' in argument.lower():
            try:
                argument = argument.lower().replace('k', '')
                amount = float(argument) * 1000
            except ValueError:
                raise BadArgument(f"**{argument}k** is **not** a valid number")
        else:
            try:
                amount = float(argument)
            except ValueError:
                raise BadArgument(f"**{argument}** is **not** a number")
        if isinstance(amount, float) and str(amount)[::-1].find(".") > 2:
            raise BadArgument("The number can't have more than **2** decimals")
        if amount < 0:
            raise BadArgument(f"You can't collect less than **0** 💵")
        if amount == 0:
            raise BadArgument(f"You can't collect **0** 💵")
        if amount > earnings['amount']:
            raise BadArgument("You can't collect more than your earnings.")
        return amount

class Punishment(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if not argument in ['ban', 'kick', 'strip', 'none']:
          raise BadArgument(f"**{argument}** is **not** a valid punishment\n> Valid punishments: `ban`, `kick`, `strip` & `none`")
        return argument

class Streamers(Converter):
    async def convert(self, ctx: EvelinaContext, argument: str):
        if argument.startswith("https://twitch.tv"):
            url = urlparse(argument)
            return url.path.strip("/")
        return argument