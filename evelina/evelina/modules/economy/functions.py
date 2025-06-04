import io
import uuid
import json
import random
import datetime

from PIL import Image, ImageDraw, ImageFont
from decimal import Decimal

from discord import Embed, User, ButtonStyle, Interaction, TextStyle, Guild
from discord.ui import View, Button, TextInput, Modal, button, Button
from discord.ext.commands import AutoShardedBot as AB

from modules.styles import emojis, colors

class EconomyMeasures:
    def __init__(self: "EconomyMeasures", bot: AB):
        self.bot = bot

    async def get_investment(self, name: str) -> dict:
        return await self.bot.db.fetchrow("SELECT * FROM economy_investments WHERE LOWER(name) = LOWER($1)", name)
    
    async def get_id_investment(self, id: int) -> dict:
        return await self.bot.db.fetchrow("SELECT * FROM economy_investments WHERE id = $1", id)

    async def get_user_investment(self, user_id: int) -> dict:
        return await self.bot.db.fetchrow("SELECT * FROM economy_investments_started WHERE user_id = $1 AND active = True", user_id)

    async def get_company(self, name: str) -> dict:
        return await self.bot.db.fetchrow("SELECT * FROM company WHERE LOWER(name) = LOWER($1)", name)
    
    async def get_tag_company(self, tag: str) -> dict:
        return await self.bot.db.fetchrow("SELECT * FROM company WHERE LOWER(tag) = LOWER($1)", tag)
    
    async def get_user_company(self, user_id: int) -> dict:
        return await self.bot.db.fetchrow("SELECT * FROM company WHERE $1 = ANY(members)", user_id)
    
    async def get_pending_request(self, user_id: int, company_id: int) -> dict:
        request = await self.bot.db.fetchrow("SELECT * FROM company_requests WHERE user_id = $1 AND company_id = $2", user_id, company_id)
        if request:
            return True
        return False
    
    async def get_pending_invites(self, user_id: int, company_id: int) -> dict:
        invite = await self.bot.db.fetchrow("SELECT * FROM company_invites WHERE user_id = $1 AND company_id = $2", user_id, company_id)
        if invite:
            return True
        return False
    
    async def get_level_info(self, level: int) -> dict:
        return await self.bot.db.fetchrow("SELECT * FROM company_upgrades WHERE level = $1", level)
    
    async def get_user_rank(self, user_id: int) -> int:
        user = self.bot.get_user(user_id)
        if not user:
            user = await self.bot.fetch_user(user_id)
        company = await self.get_user_company(user.id)
        if not company:
            return 0
        roles = company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        if user.id == company["ceo"]:
            return 4
        if user.id in roles.get('Manager', []):
            return 3
        if user.id in roles.get('Senior', []):
            return 2
        if user.id in company["members"]:
            return 1
        return 0

    async def get_user_networth(self, user_id: int) -> int:
        user = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user_id)
        if not user:
            return 0
        networth = user["cash"] + user["card"]
        lab = await self.bot.db.fetchrow("SELECT * FROM economy_lab WHERE user_id = $1", user_id)
        if lab:
            base_lab_cost = 5000000
            total_upgrade_cost = 0
            for level in range(1, lab["upgrade_state"] + 1):
                _, _, upgrade_cost = await self.calculate_lab_earnings_and_upgrade(user_id, level)
                total_upgrade_cost += upgrade_cost
            networth += base_lab_cost + total_upgrade_cost
        business = await self.get_user_business(user_id)
        if business:
            system_business = await self.get_system_business_by_id(business["business_id"])
            if system_business:
                networth += system_business["cost"] + await self.calculate_business_earning(user_id, business["last_collected"], system_business["earnings"])
        return networth
    
    async def deposit_vault(self, company: dict, user: User, amount: float, type: str) -> None:
        await self.bot.db.execute("UPDATE company SET vault = vault + $1 WHERE id = $2", amount, company["id"])
        await self.bot.db.execute("INSERT INTO company_vault (company_id, user_id, amount, type, created) VALUES ($1, $2, $3, $4, $5)", company["id"], user.id, amount, type, datetime.datetime.now().timestamp())
        await self.bot.db.execute("UPDATE economy SET cash = cash - $1 WHERE user_id = $2", amount, user.id)

    async def withdraw_vault(self, company: dict, user: User, amount: float, type: str) -> None:
        await self.bot.db.execute("UPDATE company SET vault = vault - $1 WHERE id = $2", amount, company["id"])
        await self.bot.db.execute("INSERT INTO company_vault (company_id, user_id, amount, type, created) VALUES ($1, $2, $3, $4, $5)", company["id"], user.id, amount, type, datetime.datetime.now().timestamp())
        await self.bot.db.execute("UPDATE economy SET cash = cash + $1 WHERE user_id = $2", amount, user.id)

    async def add_vault(self, company: dict, user: User, amount: float, type: str) -> None:
        await self.bot.db.execute("UPDATE company SET vault = vault + $1 WHERE id = $2", amount, company["id"])
        await self.bot.db.execute("INSERT INTO company_vault (company_id, user_id, amount, type, created) VALUES ($1, $2, $3, $4, $5)", company["id"], user.id, amount, type, datetime.datetime.now().timestamp())

    async def remove_vault(self, company: dict, user: User, amount: float, type: str) -> None:
        await self.bot.db.execute("UPDATE company SET vault = vault - $1 WHERE id = $2", amount, company["id"])
        await self.bot.db.execute("INSERT INTO company_vault (company_id, user_id, amount, type, created) VALUES ($1, $2, $3, $4, $5)", company["id"], user.id, amount, type, datetime.datetime.now().timestamp())

    async def clear_company(self, company: dict) -> None:
        await self.bot.db.execute("DELETE FROM company WHERE id = $1", company["id"])
        await self.bot.db.execute("DELETE FROM company_earnings WHERE company_id = $1", company["id"])
        await self.bot.db.execute("DELETE FROM company_requests WHERE company_id = $1", company["id"])
        await self.bot.db.execute("DELETE FROM company_vault WHERE company_id = $1", company["id"])
        await self.bot.db.execute("DELETE FROM company_voters WHERE company_id = $1", company["id"])
        
    async def get_user_business(self, user_id):
        return await self.bot.db.fetchrow("SELECT * FROM economy_business WHERE user_id = $1", user_id)
    
    async def get_system_business(self, name):
        return await self.bot.db.fetchrow("SELECT * FROM economy_business_list WHERE LOWER(name) = LOWER($1)", name)
    
    async def get_system_business_by_id(self, id):
        return await self.bot.db.fetchrow("SELECT * FROM economy_business_list WHERE business_id = $1", id)
    
    async def get_all_businesses(self):
        return await self.bot.db.fetch("SELECT * FROM economy_business_list ORDER BY business_id ASC")

    async def get_used_card(self, user_id: int, business: str):
        card_used = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user_id, business)
        if card_used:
            card_user = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user_id, card_used["card_id"])
            if card_user:
                card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
                if card_info:
                    name = card_info["name"]
                    stars = card_info["stars"]
                    storage = card_user["storage"]
                    multiplier = card_user["multiplier"]
                    return name, stars, storage, multiplier
        return None, None, None, None

    async def calculate_lab_earnings_and_upgrade(self, user_id: int, upgrade_state: int):
        hours = 6
        multiplier = 1
        card_used = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user_id, "lab")
        if card_used:
            card_user = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user_id, card_used["card_id"])
            if card_user:
                card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
                if card_info:
                    hours = card_user["storage"]
                    multiplier = card_user["multiplier"]
        base_earnings_per_hour = 10000 + (5000 * upgrade_state)
        earnings_multiplier = 1 + (0.1 * upgrade_state)
        earnings_per_hour = base_earnings_per_hour * earnings_multiplier
        earnings_per_hour *= multiplier
        earnings_cap = earnings_per_hour * hours
        next_upgrade_cost = (base_earnings_per_hour * 24) * (1 + 0.1 * upgrade_state)
        return earnings_per_hour, earnings_cap, next_upgrade_cost
    
    async def calculate_business_earning(self, user_id: int, last_collected, hourrevenue):
        earnings = 0
        hours = 6
        multiplier = 1
        card_used = await self.bot.db.fetchrow("SELECT * FROM economy_cards_used WHERE user_id = $1 AND business = $2", user_id, "business")
        if card_used:
            card_user = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE user_id = $1 AND card_id = $2", user_id, card_used["card_id"])
            if card_user:
                card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1", card_user["id"])
                if card_info:
                    hours = card_user["storage"]
                    multiplier = card_user["multiplier"]
        time_difference = datetime.datetime.now().timestamp() - last_collected
        if time_difference >= 3600:
            earnings = hourrevenue * (time_difference // 3600)
        earnings_cap = hourrevenue * hours
        if earnings > earnings_cap:
            earnings = earnings_cap
        earnings *= multiplier
        return earnings
    
    def calculate_rounded_target_revenue(self, level):
        return round(10_000 * (level + 1) ** 1.3, -4)

    def calculate_max_bet(self, target):
        return round(target * 0.05, -4)

    def get_revenue_and_bet(self, level):
        target_revenue = self.calculate_rounded_target_revenue(level)
        max_bet = self.calculate_max_bet(target_revenue)
        return target_revenue, max_bet
    
    async def update_economy_level(self, user: User, guild: Guild, money: int):
        user_data = await self.bot.db.fetchrow("SELECT money_amount, economy_level FROM economy_users WHERE user_id = $1 AND guild_id = $2", user.id, guild.id)
        if not user_data:
            return
        current_money = user_data["money_amount"]
        current_level = user_data["economy_level"]
        new_money = current_money + money
        target_revenue, _ = self.get_revenue_and_bet(current_level)
        if new_money >= target_revenue:
            new_level = current_level + 1
            return await self.bot.db.execute("UPDATE economy_users SET money_amount = $1, economy_level = $2 WHERE user_id = $3 AND guild_id = $4", new_money, new_level, user.id, guild.id)
        else:
            return await self.bot.db.execute("UPDATE economy_users SET money_amount = $1 WHERE user_id = $2 AND guild_id = $3", new_money, user.id, guild.id)

    async def create_id_card(self, company, card_id, max_storage, multiplication, name, rarity, image_url, type):
        if type == "gold":
            if str(company).lower() == "scientist":
                template_path = f"./data/images/cards/card_scientist_gold{rarity}.png"
                company_formated = "Lab"
            elif str(company).lower() == "manager":
                template_path = f"./data/images/cards/card_manager_gold{rarity}.png"
                company_formated = "Business"
            elif str(company).lower() == "security":
                template_path = f"./data/images/cards/card_security_gold{rarity}.png"
                company_formated = "Personal"
        elif type == "pink":
            if str(company).lower() == "scientist":
                template_path = f"./data/images/cards/card_scientist_pink{rarity}.png"
                company_formated = "Lab"
            elif str(company).lower() == "manager":
                template_path = f"./data/images/cards/card_manager_pink{rarity}.png"
                company_formated = "Business"
            elif str(company).lower() == "security":
                template_path = f"./data/images/cards/card_security_pink{rarity}.png"
                company_formated = "Personal"
        elif type == "blackice":
            if str(company).lower() == "scientist":
                template_path = f"./data/images/cards/card_scientist_blackice{rarity}.png"
                company_formated = "Lab"
            elif str(company).lower() == "manager":
                template_path = f"./data/images/cards/card_manager_blackice{rarity}.png"
                company_formated = "Business"
            elif str(company).lower() == "security":
                template_path = f"./data/images/cards/card_security_blackice{rarity}.png"
                company_formated = "Personal"
        elif type == "standard":
            if str(company).lower() == "scientist":
                template_path = f"./data/images/cards/card_scientist{rarity}.png"
                company_formated = "Lab"
            elif str(company).lower() == "manager":
                template_path = f"./data/images/cards/card_manager{rarity}.png"
                company_formated = "Business"
            elif str(company).lower() == "security":
                template_path = f"./data/images/cards/card_security{rarity}.png"
                company_formated = "Personal"
        template_image = Image.open(template_path).convert("RGBA")
        draw = ImageDraw.Draw(template_image)
        font_small = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 40)
        font_large = ImageFont.truetype("data/fonts/ChocolatesBold.otf", 90)
        font_sign = ImageFont.truetype("data/fonts/sign.ttf", 80)
        company_pos = (675, 520)
        id_pos = (1160, 520)
        max_storage_pos = (675, 620)
        multiplication_pos = (1160, 620)
        name_pos = (620, 320)
        sign_pos = (730, 720)
        image_pos = (50, 150)
        image_size = (543, 609)
        if type == "gold":
            draw.text(company_pos, f"{company_formated}", font=font_small, fill="#717171")
            draw.text(id_pos, f"{card_id}", font=font_small, fill="#717171")
            draw.text(max_storage_pos, f"{max_storage}", font=font_small, fill="#717171")
            if str(company).lower() != "security":
                draw.text(multiplication_pos, f"{multiplication}", font=font_small, fill="#717171")
        elif type == "pink":
            draw.text(company_pos, f"{company_formated}", font=font_small, fill="#ffffff")
            draw.text(id_pos, f"{card_id}", font=font_small, fill="#ffffff")
            draw.text(max_storage_pos, f"{max_storage}", font=font_small, fill="#ffffff")
            if str(company).lower() != "security":
                draw.text(multiplication_pos, f"{multiplication}", font=font_small, fill="#ffffff")
            image_pos = (50, 150)
        elif type == "blackice":
            draw.text(company_pos, f"{company_formated}", font=font_small, fill="#ffffff")
            draw.text(id_pos, f"{card_id}", font=font_small, fill="#ffffff")
            draw.text(max_storage_pos, f"{max_storage}", font=font_small, fill="#ffffff")
            if str(company).lower() != "security":
                draw.text(multiplication_pos, f"{multiplication}", font=font_small, fill="#ffffff")
            image_pos = (49, 150)
        elif type == "standard":
            draw.text(company_pos, f"{company_formated}", font=font_small, fill="#bdaa85")
            draw.text(id_pos, f"{card_id}", font=font_small, fill="#bdaa85")
            draw.text(max_storage_pos, f"{max_storage}", font=font_small, fill="#bdaa85")
            if str(company).lower() != "security":
                draw.text(multiplication_pos, f"{multiplication}", font=font_small, fill="#bdaa85")
        draw.text(name_pos, str(name).upper(), font=font_large, fill="#282627")
        if type == "gold":
            for offset in range(-2, 3):
                draw.text((sign_pos[0] + offset, sign_pos[1]), name, font=font_sign, fill="#000001")
                draw.text((sign_pos[0], sign_pos[1] + offset), name, font=font_sign, fill="#000001")
        elif type == "pink":
            for offset in range(-2, 3):
                draw.text((sign_pos[0] + offset, sign_pos[1]), name, font=font_sign, fill="#ffffff")
                draw.text((sign_pos[0], sign_pos[1] + offset), name, font=font_sign, fill="#ffffff")
        elif type == "blackice":
            for offset in range(-2, 3):
                draw.text((sign_pos[0] + offset, sign_pos[1]), name, font=font_sign, fill="#ffffff")
                draw.text((sign_pos[0], sign_pos[1] + offset), name, font=font_sign, fill="#ffffff")
        elif type == "standard":
            for offset in range(-2, 3):
                draw.text((sign_pos[0] + offset, sign_pos[1]), name, font=font_sign, fill="#bdaa85")
                draw.text((sign_pos[0], sign_pos[1] + offset), name, font=font_sign, fill="#bdaa85")
        image_data = await self.bot.session.get_bytes(image_url)
        if image_data:
            with Image.open(io.BytesIO(image_data)) as img:
                img = img.resize(image_size)
                template_image.paste(img, image_pos)
        image_binary = io.BytesIO()
        template_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        return image_binary
    
    async def upgrade_cards_for_stars(self, ctx, type, storage_range, multiplier_range, protection_range, star_label, next_star):
        business = str(type).replace("manager", "business").replace("security", "personal").replace("scientist", "lab")
        card_data = await self.bot.db.fetch("SELECT * FROM economy_cards_user WHERE user_id = $1 AND active = True AND business = $2 AND background = $3", ctx.author.id, business, "standard")
        if not card_data:
            return await ctx.send_warning("You don't have any cards.")
        cards_to_upgrade = []
        for card in card_data:
            card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE id = $1 AND business = $2", card['id'], business)
            if card_info and card_info['stars'] == next_star - 1:
                cards_to_upgrade.append(card)
        if len(cards_to_upgrade) < 10:
            return await ctx.send_warning(f"You don't have enough cards to upgrade to {star_label}.")
        for card in cards_to_upgrade[:10]:
            await self.bot.db.execute("UPDATE economy_cards_user SET active = False WHERE card_id = $1", card['card_id'])
        card_info = await self.bot.db.fetchrow("SELECT * FROM economy_cards WHERE stars = $1 AND business = $2 ORDER BY RANDOM() LIMIT 1", next_star, business)
        if not card_info:
            return await ctx.send_warning(f"No cards found for {star_label} star level.")
        while True:
            card_id = random.randint(100000, 999999)
            check_if_item_card_exists = await self.bot.db.fetchrow("SELECT * FROM economy_cards_user WHERE card_id = $1", card_id)
            if not check_if_item_card_exists:
                break
        card_storage = random.randint(*storage_range)
        card_multiplier = round(random.uniform(*multiplier_range), 1)
        card_protection = random.randint(*protection_range)
        card_image = card_info['image']
        if business == "lab" or business == "business":
            item_card = await self.create_id_card(type, card_id, f"{card_storage}h", f"{card_multiplier}x", card_info['name'], next_star, card_image, "standard")
        else:
            item_card = await self.create_id_card(type, card_id, f"{card_protection}%", "N/A", card_info['name'], next_star, card_image, "standard")
        file_data = item_card.getvalue()
        file_code = f"{str(uuid.uuid4())[:8]}"
        file_name = f"{file_code}.png"
        content_type = "image/png"
        upload_res = await self.bot.r2.upload_file("evelina", file_data, file_name, content_type, "card")
        if upload_res:
            file_url = f"https://cdn.evelina.bot/card/{file_name}"
        await self.bot.db.execute(
            "INSERT INTO economy_cards_user (id, user_id, card_id, business, storage, multiplier, image) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            card_info['id'], ctx.author.id, card_id, business, card_storage, card_multiplier, file_url
        )
        embed = Embed(title=f"{card_info['name']} | {star_label}", color=colors.NEUTRAL)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
        embed.set_image(url=file_url)
        return await ctx.send(embed=embed)
        
    async def logging(self, user: User, amount: Decimal, action: str, type: str) -> None:
        user_data = await self.bot.db.fetchrow("SELECT * FROM economy WHERE user_id = $1", user.id)
        await self.bot.db.execute("INSERT INTO economy_logs (user_id, amount, action, type, created, cash, card) VALUES ($1, $2, $3, $4, $5, $6, $7)", user.id, amount, action, type, datetime.datetime.now().timestamp(), user_data['cash'], user_data['card'])

    async def logging_lab(self, user: User, moderator: User, amount: Decimal, action: str, upgrade_state: int,) -> None:
        await self.bot.db.execute("INSERT INTO economy_logs_lab (user_id, moderator_id, amount, action, upgrade_state, created) VALUES ($1, $2, $3, $4, $5, $6)", user.id, moderator.id, amount, action, upgrade_state, datetime.datetime.now().timestamp())

    async def logging_business(self, user: User, moderator: User, amount: Decimal, action: str, business: str) -> None:
        await self.bot.db.execute("INSERT INTO economy_logs_business (user_id, moderator_id, amount, action, business, created) VALUES ($1, $2, $3, $4, $5, $6)", user.id, moderator.id, amount, action, business, datetime.datetime.now().timestamp())

class EconomyQuestsMeasures:
    def __init__(self: "EconomyQuestsMeasures", bot: AB):
        self.bot = bot

    async def add_win_game(self, user: User, mode: str) -> None:
        user_quest = await self.get_user_quest(user)
        if user_quest:
            quest = await self.get_quest(user_quest['id'])
            if quest:
                if quest['type'] == "win-game":
                    if quest['mode'] == mode:
                        if quest['amount'] > user_quest['amount']:
                            await self.bot.db.execute("UPDATE quests_user SET amount = amount + 1 WHERE user_id = $1 AND completed = $2 AND id = $3", user.id, False, user_quest['id'])

    async def add_win_money(self, user: User, mode: str, amount: Decimal) -> None:
        user_quest = await self.get_user_quest(user)
        if user_quest:
            quest = await self.get_quest(user_quest['id'])
            if quest:
                if quest['type'] == "win-money":
                    if quest['mode'] == mode:
                        if quest['amount'] > user_quest['amount']:
                            await self.bot.db.execute("UPDATE quests_user SET amount = amount + $1 WHERE user_id = $2 AND completed = $3 AND id = $4", amount, user.id, False, user_quest['id'])
                    elif quest['mode'] == "any":
                        if quest['amount'] > user_quest['amount']:
                            await self.bot.db.execute("UPDATE quests_user SET amount = amount + $1 WHERE user_id = $2 AND completed = $3 AND id = $4", amount, user.id, False, user_quest['id'])

    async def add_deposit_money(self, user: User, mode: str, amount: Decimal) -> None:
        user_quest = await self.get_user_quest(user)
        if user_quest:
            quest = await self.get_quest(user_quest['id'])
            if quest:
                if quest['type'] == "deposit-bank-money":
                    if quest['mode'] == mode:
                        if quest['amount'] > user_quest['amount']:
                            await self.bot.db.execute("UPDATE quests_user SET amount = amount + $1 WHERE user_id = $2 AND completed = $3 AND id = $4", amount, user.id, False, user_quest['id'])
                elif quest['type'] == "deposit-vault-money":
                    if quest['mode'] == mode:
                        if quest['amount'] > user_quest['amount']:
                            await self.bot.db.execute("UPDATE quests_user SET amount = amount + $1 WHERE user_id = $2 AND completed = $3 AND id = $4", amount, user.id, False, user_quest['id'])

    async def add_collect_money(self, user: User, mode: str, amount: Decimal) -> None:
        user_quest = await self.get_user_quest(user)
        if user_quest:
            quest = await self.get_quest(user_quest['id'])
            if quest and quest['type'].startswith("collect-"):
                if quest['mode'] == mode or quest['mode'] == "any":
                    if quest['amount'] > user_quest['amount']:
                        if quest['type'].endswith("-money"):
                            await self.bot.db.execute("UPDATE quests_user SET amount = amount + $1 WHERE user_id = $2 AND completed = $3 AND id = $4", amount, user.id, False, user_quest['id'])
                        elif quest['type'].endswith("-amount"):
                            await self.bot.db.execute("UPDATE quests_user SET amount = amount + $1 WHERE user_id = $2 AND completed = $3 AND id = $4", 1, user.id, False, user_quest['id'])

    async def get_random_quest(self, difficulty: str) -> dict:
        quest = await self.bot.db.fetchrow(f"SELECT * FROM quests WHERE difficult = $1 ORDER BY RANDOM() LIMIT 1", difficulty)
        if quest:
            return dict(quest)
        return None
    
    async def get_quest(self, id: int) -> dict:
        quest = await self.bot.db.fetchrow(f"SELECT * FROM quests WHERE id = $1", id)
        if quest:
            return dict(quest)
        return None
    
    async def get_user_quest(self, user: User) -> dict:
        quest = await self.bot.db.fetchrow(f"SELECT * FROM quests_user WHERE user_id = $1 AND completed = $2", user.id, False)
        if quest:
            return dict(quest)
        return None

class RequestModal(Modal, title="Search for a request"):
    text = TextInput(label="Username", style=TextStyle.short, required=True)

    def __init__(self, view: "RequestView"):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: Interaction) -> None:
        search_term = self.text.value.lower()
        matching_index = None
        for index, request in enumerate(self.view.requests):
            user = await self.view.bot.fetch_user(request["user_id"])
            if user and search_term in user.name.lower() or user and search_term in user.display_name.lower():
                matching_index = index
                break
        if matching_index is not None:
            self.view.current_index = matching_index
            await self.view.update_message(interaction)
        else:
            await interaction.warn(f"No matching user found for **{self.text}**", ephemeral=True)

class RequestView(View):
    def __init__(self, ctx, requests, company, bot: AB):
        super().__init__()
        self.ctx = ctx
        self.requests = requests
        self.company = company
        self.bot = bot
        self.current_index = 0
        self.economy = EconomyMeasures(self.bot)
        self.cash = "💵"

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.warn("You are not the **author** of this embed", ephemeral=True)
            return False
        return True

    async def update_message(self, interaction: Interaction):
        if self.requests:
            embed = Embed(title=f"Join Requests", color=colors.NEUTRAL)
            embed.set_author(name=f"{self.company['name']} | {self.company['tag']}", icon_url=self.company['icon'] if self.company['icon'] else None)
            embed.add_field(name="User", value=f"<@{self.requests[self.current_index]['user_id']}>", inline=True)
            networth = await self.economy.get_user_networth(self.requests[self.current_index]['user_id'])
            embed.add_field(name="Networth", value=f"{self.bot.misc.humanize_number(networth)} {self.cash}", inline=True)
            embed.add_field(name="Created", value=f"<t:{self.requests[self.current_index]['created']}:f>", inline=True)
            embed.add_field(name="Application", value=f"```{self.requests[self.current_index]['text'] if self.requests[self.current_index]['text'] else 'N/A'}```", inline=False)
            user = self.bot.get_user(self.requests[self.current_index]['user_id']) or await self.bot.fetch_user(self.requests[self.current_index]['user_id'])
            embed.set_thumbnail(url=user.avatar.url if user.avatar else user.default_avatar.url)
            embed.set_footer(text=f"Page {self.current_index + 1}/{len(self.requests)} ({len(self.requests)} entries)")
            for button in self.children:
                button.disabled = False
            if interaction.response.is_done():
                return await interaction.followup.edit_message(message_id=interaction.message.id, embed=embed, view=self)
            else:
                return await interaction.response.edit_message(embed=embed, view=self)
        else:
            try:
                return await interaction.message.delete()
            except Exception:
                pass

    @button(emoji=emojis.LEFT, style=ButtonStyle.blurple, custom_id="prev")
    async def prev(self, interaction: Interaction, button: Button):
        self.current_index = (self.current_index - 1) % len(self.requests)
        await self.update_message(interaction)

    @button(emoji=emojis.SEARCH, style=ButtonStyle.grey, custom_id="goto")
    async def goto(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(RequestModal(self))

    @button(emoji=emojis.RIGHT, style=ButtonStyle.blurple, custom_id="next")
    async def next(self, interaction: Interaction, button: Button):
        self.current_index = (self.current_index + 1) % len(self.requests)
        await self.update_message(interaction)

    @button(label="Accept", style=ButtonStyle.green, custom_id="accept")
    async def accept(self, interaction: Interaction, button: Button):
        company = await self.economy.get_user_company(self.requests[self.current_index]['user_id'])
        if company:
            return await interaction.warn(f"<@{self.current_index['user_id']}> is already in a company.", ephemeral=True)
        limits = await self.economy.get_level_info(self.company['level'])
        if len(self.company["members"]) >= limits['members']:
            return await interaction.warn(f"Your company is already at the maximum member limit of **{limits['members']}**", ephemeral=True)
        user_id = self.requests.pop(self.current_index)['user_id']
        await self.bot.db.execute("DELETE FROM company_requests WHERE user_id = $1 AND company_id = $2", user_id, self.company['id'])
        await self.bot.db.execute("UPDATE company SET members = array_append(members, $1) WHERE id = $2", user_id, self.company['id'])
        await interaction.approve(f"Accepted <@{user_id}> into the company.", ephemeral=True)
        if not self.requests:
            return await interaction.message.delete()
        if self.current_index >= len(self.requests):
            self.current_index = 0
        if len(self.requests) == 1:
            self.current_index = 0
        await self.update_message(interaction)

    @button(label="Deny", style=ButtonStyle.red, custom_id="deny")
    async def deny(self, interaction: Interaction, button: Button):
        user_id = self.requests.pop(self.current_index)['user_id']
        await self.bot.db.execute("DELETE FROM company_requests WHERE user_id = $1 AND company_id = $2", user_id, self.company['id'])
        await interaction.approve(f"Denied <@{user_id}>'s request.", ephemeral=True)
        if not self.requests:
            return await interaction.message.delete()
        if self.current_index >= len(self.requests):
            self.current_index = 0
        if len(self.requests) == 1:
            self.current_index = 0
        await self.update_message(interaction)

class CompanyRequestModal(Modal, title="Request to join"):
    text = TextInput(label="Application", placeholder="Why do you want to join?", style=TextStyle.long, required=True)

    def __init__(self, view: "CompanyInfoView"):
        super().__init__()
        self.view = view

    async def on_submit(self, interaction: Interaction) -> None:
        await self.view.bot.db.execute("INSERT INTO company_requests (company_id, user_id, text, created) VALUES ($1, $2, $3, $4)", self.view.company['id'], interaction.user.id, self.text.value, datetime.datetime.now().timestamp())
        return await interaction.approve(f"Successfully sent a request to join **{self.view.company['name']}**.", ephemeral=True)

class CompanyInfoView(View):
    def __init__(self, ctx, company, bot: AB):
        super().__init__()
        self.ctx = ctx
        self.company = company
        self.bot = bot
        self.economy = EconomyMeasures(self.bot)
        self.cash = "💵"

    @button(label="Join", style=ButtonStyle.green, custom_id="join")
    async def join(self, interaction: Interaction, button: Button):
        company = await self.economy.get_user_company(interaction.user.id)
        if company:
            return await interaction.warn(f"You are already in a company.", ephemeral=True)
        if self.company['privacy'] == 'private':
            return await interaction.warn(f"This company is private. You need an invite to join.", ephemeral=True)
        if self.company['privacy'] == 'request':
            return await interaction.response.send_modal(CompanyRequestModal(self))
        limits = await self.economy.get_level_info(self.company['level'])
        if len(self.company["members"]) >= limits['members']:
            return await interaction.warn(f"Company is already at the maximum member limit of **{limits['members']}**", ephemeral=True)
        await self.bot.db.execute("UPDATE company SET members = array_append(members, $1) WHERE id = $2", interaction.user.id, self.company['id'])
        return await interaction.approve(f"Successfully joined **{self.company['name']}**.", ephemeral=True)
    
    @button(label="Members", style=ButtonStyle.blurple, custom_id="members")
    async def members(self, interaction: Interaction, button: Button):
        roles = self.company.get('roles', {})
        if isinstance(roles, str):
            roles = json.loads(roles)
        ranks = {
            self.company['ceo']: "CEO",
            **{user_id: "Manager" for user_id in roles.get('Manager', [])},
            **{user_id: "Senior" for user_id in roles.get('Senior', [])},
        }
        rank_priority = {"CEO": 1, "Manager": 2, "Senior": 3, "Employee": 4}
        sorted_members = sorted(self.company['members'], key=lambda x: rank_priority.get(ranks.get(x, "Employee")))
        members_by_rank = {
            "CEO": [],
            "Manager": [],
            "Senior": [],
            "Employee": []
        }
        rank_emojis = {
            "CEO": "👑",
            "Manager": "💼",
            "Senior": "🔧",
            "Employee": "👤"
        }
        for member_id in sorted_members:
            rank = ranks.get(member_id, "Employee")
            members_by_rank[rank].append(f"<@{member_id}>")
        embed = Embed(title=f"Members", color=colors.NEUTRAL)
        embed.set_author(name=f"{self.company['name']} | {self.company['tag']}", icon_url=self.company['icon'] if self.company['icon'] else None)
        for rank, members in members_by_rank.items():
            if members:
                embed.add_field(name=f"{rank_emojis[rank]} {rank}", value=" ".join(members), inline=True)
            else:
                embed.add_field(name=f"{rank_emojis[rank]} {rank}", value="N/A", inline=True)
        return await interaction.response.send_message(embed=embed, ephemeral=True)